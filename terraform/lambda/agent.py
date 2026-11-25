"""
Zest - the Citrus & Co. customer-intelligence agent.

One Lambda, many "actions". Every action is a tool the agent (or you, from the
CLI) can call:

  health            probe every dependency and report what is broken
  search_products   product search in Aurora PostgreSQL        (Data API)
  customer_profile  customer + recent orders from Aurora        (Data API)
  similar_notes     semantic search over support notes          (pgvector)
  search_docs       policy / product docs                       (Bedrock Knowledge Base)
  remember          store one conversation turn                 (DynamoDB)
  recall            load recent conversation turns              (DynamoDB)
  get_state         read the session's working state            (DynamoDB)
  set_state         write the session's working state           (DynamoDB)
  ask               full agent loop: Claude + all tools + memory

Invoke example:
  aws lambda invoke --function-name <name> \
      --cli-binary-format raw-in-base64-out \
      --payload '{"action":"search_products","query":"drone","category":"outdoor"}' out.json
"""

import contextlib
import datetime as dt
import json
import os
import time
import uuid

import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-east-1")

rds_data = boto3.client("rds-data")
ddb = boto3.client("dynamodb")
bedrock_runtime = boto3.client("bedrock-runtime")
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")

_ser = TypeSerializer()
_deser = TypeDeserializer()


def env(name, default=""):
    return os.environ.get(name, default)


def log(event, **fields):
    """Structured JSON log line -> easy CloudWatch Logs Insights queries."""
    print(json.dumps({"event": event, **fields}, default=str))


# --------------------------------------------------------------------------
# Aurora PostgreSQL via the RDS Data API
# --------------------------------------------------------------------------

def _param(name, value):
    if value is None:
        return {"name": name, "value": {"isNull": True}}
    if isinstance(value, bool):
        return {"name": name, "value": {"booleanValue": value}}
    if isinstance(value, int):
        return {"name": name, "value": {"longValue": value}}
    if isinstance(value, float):
        return {"name": name, "value": {"doubleValue": value}}
    return {"name": name, "value": {"stringValue": str(value)}}


def sql(statement, **params):
    """Run one SQL statement through the Data API and return rows as dicts."""
    started = time.perf_counter()
    resp = rds_data.execute_statement(
        resourceArn=env("DB_CLUSTER_ARN"),
        secretArn=env("DB_SECRET_ARN"),
        database=env("DB_NAME", "agentdb"),
        sql=statement,
        parameters=[_param(k, v) for k, v in params.items()],
        formatRecordsAs="JSON",
    )
    rows = json.loads(resp.get("formattedRecords") or "[]")
    log("sql", ms=round((time.perf_counter() - started) * 1000, 1), rows=len(rows),
        statement=" ".join(statement.split())[:200])
    return rows


def search_products(query, category=None, max_price=None, limit=10):
    """Find products whose name contains `query` (case-insensitive)."""
    limit = max(1, min(int(limit or 10), 25))
    where = ["name ILIKE '%' || :q || '%'"]
    params = {"q": query, "lim": limit}
    if category:
        where.append("category = :category")
        params["category"] = category
    if max_price is not None:
        where.append("price <= CAST(:max_price AS numeric)")
        params["max_price"] = float(max_price)
    return sql(
        "SELECT product_id, sku, name, category, brand, price, rating, stock "
        "FROM products WHERE " + " AND ".join(where) + " "
        "ORDER BY rating DESC, product_id LIMIT :lim",
        **params,
    )


def customer_profile(customer_id):
    customer = sql(
        "SELECT customer_id, full_name, segment, region, lifetime_value "
        "FROM customers WHERE customer_id = :cid",
        cid=customer_id,
    )
    if not customer:
        return {"error": f"no customer {customer_id}"}
    orders = sql(
        "SELECT o.order_id, o.ordered_at, o.status, o.quantity, o.amount, p.name AS product "
        "FROM orders o JOIN products p ON p.product_id = o.product_id "
        "WHERE o.customer_id = :cid ORDER BY o.ordered_at DESC LIMIT 5",
        cid=customer_id,
    )
    return {"customer": customer[0], "recent_orders": orders}


# --------------------------------------------------------------------------
# pgvector - semantic search over support notes
# --------------------------------------------------------------------------

def embed(text):
    body = {"inputText": text, "dimensions": int(env("EMBED_DIMENSIONS", "1024")), "normalize": True}
    resp = bedrock_runtime.invoke_model(modelId=env("EMBED_MODEL_ID"), body=json.dumps(body))
    return json.loads(resp["body"].read())["embedding"]


def similar_notes(query, k=5):
    vec = json.dumps(embed(query))
    return sql(
        "SELECT note_id, customer_id, note, "
        "round((1 - (embedding <=> CAST(:v AS vector)))::numeric, 4) AS similarity "
        "FROM support_notes WHERE embedding IS NOT NULL "
        "ORDER BY embedding <=> CAST(:v AS vector) LIMIT :k",
        v=vec, k=max(1, min(int(k or 5), 20)),
    )


# --------------------------------------------------------------------------
# Bedrock Knowledge Base (vectors live in Aurora: bedrock_integration.bedrock_kb)
# --------------------------------------------------------------------------

def search_docs(query, category=None, k=5):
    kb_id = env("KB_ID")
    if not kb_id:
        raise RuntimeError("KB_ID is not set on this Lambda. Create the Knowledge Base and wire its ID in.")
    vector_cfg = {"numberOfResults": max(1, min(int(k or 5), 10))}
    if category:
        vector_cfg["filter"] = {"equals": {"key": "category", "value": category}}
    resp = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={"vectorSearchConfiguration": vector_cfg},
    )
    return [
        {
            "text": r["content"].get("text", "")[:900],
            "score": r.get("score"),
            "source": r.get("location", {}).get("s3Location", {}).get("uri"),
            "metadata": {k2: v for k2, v in (r.get("metadata") or {}).items() if not k2.startswith("x-amz")},
        }
        for r in resp.get("retrievalResults", [])
    ]


# --------------------------------------------------------------------------
# DynamoDB - agent memory
# --------------------------------------------------------------------------

def _now():
    return dt.datetime.now(dt.timezone.utc)


def _expires_at(days=None):
    days = float(days if days is not None else env("MEMORY_TTL_DAYS", "7"))
    return str(int(_now().timestamp() + days * 86400))


def remember(session_id, role, content, customer_id=None):
    ts = _now().isoformat(timespec="milliseconds").replace("+00:00", "Z")
    item = {
        "session_id": {"S": session_id},
        "sk": {"S": f"MSG#{ts}#{uuid.uuid4().hex[:6]}"},
        "role": {"S": role},
        "content": {"S": content[:20000]},
        "expires_at": {"N": _expires_at()},
    }
    if customer_id:
        item["customer_id"] = {"S": customer_id}
    ddb.put_item(TableName=env("MEMORY_TABLE"), Item=item)
    return {"stored": item["sk"]["S"]}


def recall(session_id, limit=10):
    resp = ddb.query(
        TableName=env("MEMORY_TABLE"),
        KeyConditionExpression="session_id = :s AND begins_with(sk, :p)",
        ExpressionAttributeValues={":s": {"S": session_id}, ":p": {"S": "MSG#"}},
        ScanIndexForward=False,  # newest first ...
        Limit=max(1, min(int(limit or 10), 50)),
    )
    turns = [
        {"role": i["role"]["S"], "content": i["content"]["S"], "at": i["sk"]["S"].split("#")[1]}
        for i in resp.get("Items", [])
    ]
    return list(reversed(turns))  # ... returned oldest first


def get_state(session_id):
    resp = ddb.get_item(
        TableName=env("MEMORY_TABLE"),
        Key={"session_id": {"S": session_id}, "sk": {"S": "STATE"}},
        ConsistentRead=True,
    )
    item = resp.get("Item")
    if not item:
        return {}
    return {k: _deser.deserialize(v) for k, v in item.items() if k not in ("session_id", "sk")}


def set_state(session_id, state, customer_id=None):
    item = {k: _ser.serialize(v) for k, v in (state or {}).items()}
    item.update({
        "session_id": {"S": session_id},
        "sk": {"S": "STATE"},
        "updated_at": {"S": _now().isoformat()},
        "expires_at": {"N": _expires_at()},
    })
    if customer_id:
        item["customer_id"] = {"S": customer_id}
    ddb.put_item(TableName=env("MEMORY_TABLE"), Item=item)
    return {"stored": "STATE"}


# --------------------------------------------------------------------------
# health - the first thing to run when something is broken
# --------------------------------------------------------------------------

def health(_event=None):
    checks = {}

    def probe(name, fn):
        try:
            fn()
            checks[name] = "ok"
        except ClientError as e:
            err = e.response.get("Error", {})
            checks[name] = f"{err.get('Code')}: {err.get('Message', '')}"
        except Exception as e:  # noqa: BLE001 - we want every failure reported
            checks[name] = f"{type(e).__name__}: {e}"

    def kb_probe():
        if not env("KB_ID"):
            raise RuntimeError("KB_ID not set")
        search_docs("return policy", k=1)

    probe("aurora_connect", lambda: sql("SELECT 1 AS ok"))
    probe("aurora_products", lambda: sql("SELECT product_id FROM products LIMIT 1"))
    probe("memory_write", lambda: ddb.put_item(
        TableName=env("MEMORY_TABLE"),
        Item={"session_id": {"S": "__health__"}, "sk": {"S": "STATE"},
              "checked_at": {"S": _now().isoformat()}, "expires_at": {"N": _expires_at(1 / 24)}}))
    probe("memory_read", lambda: ddb.query(
        TableName=env("MEMORY_TABLE"),
        KeyConditionExpression="session_id = :s",
        ExpressionAttributeValues={":s": {"S": "__health__"}}, Limit=1))
    probe("embeddings", lambda: embed("ping"))
    probe("knowledge_base", kb_probe)

    return {"healthy": all(v == "ok" for v in checks.values()), "checks": checks}


# --------------------------------------------------------------------------
# ask - the agent loop (Claude in Amazon Bedrock + tools + DynamoDB memory)
# --------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Zest, the customer-intelligence agent for Citrus & Co., an online retailer.
You help support and sales staff answer questions about customers, orders, products and store policy.

Use the tools for every fact: product data and orders come from Aurora PostgreSQL, policies and
product guides come from the knowledge base, and past support notes come from semantic search.
If a tool returns an error, say which data source failed and what the error was, so the staff
member can fix it - do not guess the missing data.

Answer in at most 150 words. Cite product SKUs, order IDs and document names when you use them."""

TOOLS = [
    {
        "name": "search_products",
        "description": "Search the product catalog by (partial) product name. Optional category and max price filters. Returns up to `limit` products sorted by rating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text the product name must contain, e.g. 'drone'."},
                "category": {"type": "string", "enum": ["electronics", "kitchen", "outdoor", "office", "apparel", "home", "audio", "fitness"]},
                "max_price": {"type": "number"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 25},
            },
            "required": ["query"],
        },
    },
    {
        "name": "customer_profile",
        "description": "Get a customer's profile (segment, region, lifetime value) and their 5 most recent orders. Customer IDs look like C00042.",
        "input_schema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
    },
    {
        "name": "search_docs",
        "description": "Search Citrus & Co. policy and product-guide documents (returns, warranty, shipping, loyalty club, product care). Optional category filter: policy, guide or faq.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "category": {"type": "string", "enum": ["policy", "guide", "faq"]},
            },
            "required": ["query"],
        },
    },
    {
        "name": "similar_notes",
        "description": "Semantic search over past support-ticket notes. Use it to find how similar problems were handled before.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "k": {"type": "integer", "minimum": 1, "maximum": 10}},
            "required": ["query"],
        },
    },
]

TOOL_FUNCS = {
    "search_products": lambda a: search_products(a["query"], a.get("category"), a.get("max_price"), a.get("limit", 10)),
    "customer_profile": lambda a: customer_profile(a["customer_id"]),
    "search_docs": lambda a: search_docs(a["query"], a.get("category")),
    "similar_notes": lambda a: similar_notes(a["query"], a.get("k", 5)),
}


def _claude_client():
    """Claude in Amazon Bedrock (bedrock-mantle). Auth = the Lambda role, via SigV4."""
    import anthropic  # provided by the Lambda layer

    fallback = env("FALLBACK_MODEL_ID")
    if fallback and hasattr(anthropic, "BetaRefusalFallbackMiddleware"):
        # Bedrock has no server-side `fallbacks` parameter, so the SDK's
        # client-side middleware retries a declined request on another model.
        return anthropic.AnthropicBedrockMantle(
            aws_region=REGION,
            middleware=[anthropic.BetaRefusalFallbackMiddleware([{"model": fallback}])],
        )
    return anthropic.AnthropicBedrockMantle(aws_region=REGION)


def _history_messages(session_id, question):
    """Turn DynamoDB memory into a valid alternating user/assistant message list."""
    messages = []
    for turn in recall(session_id, limit=10):
        if turn["role"] not in ("user", "assistant"):
            continue
        if not messages and turn["role"] != "user":
            continue
        if messages and messages[-1]["role"] == turn["role"]:
            messages[-1]["content"] += "\n" + turn["content"]
        else:
            messages.append({"role": turn["role"], "content": turn["content"]})
    if messages and messages[-1]["role"] == "user":
        messages[-1]["content"] += "\n" + question
    else:
        messages.append({"role": "user", "content": question})
    return messages


def ask(session_id, question, customer_id=None):
    import anthropic

    client = _claude_client()
    system = SYSTEM_PROMPT + (f"\n\nThe staff member is asking about customer {customer_id}." if customer_id else "")
    messages = _history_messages(session_id, question)
    tool_calls = []
    answer = None

    state_cm = anthropic.BetaFallbackState() if hasattr(anthropic, "BetaFallbackState") else contextlib.nullcontext()
    with state_cm:
        for _ in range(8):
            resp = client.beta.messages.create(
                model=env("AGENT_MODEL_ID", "anthropic.claude-opus-5-5"),
                max_tokens=16000,
                system=system,
                tools=TOOLS,
                messages=messages,
                output_config={"effort": "medium"},
            )
            if resp.stop_reason == "refusal":
                answer = "I can't help with that request."
                break
            if resp.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": resp.content})
                continue
            if resp.stop_reason != "tool_use":
                answer = "".join(b.text for b in resp.content if b.type == "text").strip()
                break

            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                started = time.perf_counter()
                try:
                    out = TOOL_FUNCS[block.name](block.input)
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": json.dumps(out, default=str)[:15000]})
                    ok, err = True, None
                except ClientError as e:
                    err = f"{e.response['Error']['Code']}: {e.response['Error'].get('Message', '')}"
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": err, "is_error": True})
                    ok = False
                except Exception as e:  # noqa: BLE001
                    err = f"{type(e).__name__}: {e}"
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": err, "is_error": True})
                    ok = False
                ms = round((time.perf_counter() - started) * 1000, 1)
                tool_calls.append({"tool": block.name, "input": block.input, "ok": ok, "ms": ms, "error": err})
                log("tool_call", tool=block.name, ok=ok, ms=ms, error=err)
            messages.append({"role": "user", "content": results})
        else:
            answer = "(stopped after 8 tool rounds)"

    remember(session_id, "user", question, customer_id)
    remember(session_id, "assistant", answer or "", customer_id)
    return {"answer": answer, "model": getattr(resp, "model", None), "tool_calls": tool_calls}


# --------------------------------------------------------------------------
# Lambda entry point
# --------------------------------------------------------------------------

ACTIONS = {
    "health": health,
    "search_products": lambda e: search_products(e["query"], e.get("category"), e.get("max_price"), e.get("limit", 10)),
    "customer_profile": lambda e: customer_profile(e["customer_id"]),
    "similar_notes": lambda e: similar_notes(e["query"], e.get("k", 5)),
    "search_docs": lambda e: search_docs(e["query"], e.get("category"), e.get("k", 5)),
    "remember": lambda e: remember(e["session_id"], e.get("role", "user"), e["content"], e.get("customer_id")),
    "recall": lambda e: recall(e["session_id"], e.get("limit", 10)),
    "get_state": lambda e: get_state(e["session_id"]),
    "set_state": lambda e: set_state(e["session_id"], e.get("state", {}), e.get("customer_id")),
    "ask": lambda e: ask(e.get("session_id", "sess-" + uuid.uuid4().hex[:8]), e["question"], e.get("customer_id")),
}


def handler(event, context=None):
    if isinstance(event, str):
        event = json.loads(event)
    if isinstance(event.get("body"), str):  # Function URL / API Gateway style
        event = json.loads(event["body"])

    action = event.get("action", "health")
    if action not in ACTIONS:
        return {"ok": False, "action": action, "result": {"error": "UnknownAction", "known": sorted(ACTIONS)}}

    started = time.perf_counter()
    try:
        result, ok = ACTIONS[action](event), True
    except ClientError as e:
        err = e.response.get("Error", {})
        result, ok = {"error": err.get("Code"), "message": err.get("Message")}, False
    except KeyError as e:
        result, ok = {"error": "MissingField", "message": f"event is missing {e}"}, False
    except Exception as e:  # noqa: BLE001
        result, ok = {"error": type(e).__name__, "message": str(e)}, False

    ms = round((time.perf_counter() - started) * 1000, 1)
    log("agent_action", action=action, ok=ok, duration_ms=ms,
        error=None if ok else result.get("error"), message=None if ok else result.get("message"))
    return {"ok": ok, "action": action, "duration_ms": ms, "result": result}
