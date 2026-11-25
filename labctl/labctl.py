#!/usr/bin/env python3
"""
labctl - the Operation Tangerine lab controller 🍊

  python3 labctl/labctl.py status                 # what is deployed + agent health
  eval "$(python3 labctl/labctl.py env)"          # export CLUSTER_ARN, LAMBDA_NAME, ... into your shell
  python3 labctl/labctl.py db-setup [step ...]    # schema | seed | kb | indexes | playground
  python3 labctl/labctl.py embed-notes            # pgvector: embed 30 support notes with Titan V2
  python3 labctl/labctl.py kb-sync [--full]       # start + watch a KB ingestion job (--full re-ingests everything)
  python3 labctl/labctl.py invoke <action> [json] # call the Zest agent Lambda
  python3 labctl/labctl.py sql "<statement>"      # run SQL through the Data API
  python3 labctl/labctl.py mcp-json [--client X]  # print a working MCP config (spoiler!)

  python3 labctl/labctl.py drills                 # list break-fix drills
  python3 labctl/labctl.py break <drill>          # inject a fault
  python3 labctl/labctl.py check <drill>          # grade your fix

  python3 labctl/labctl.py exam start             # 140-minute mock exam lab: inject ALL faults
  python3 labctl/labctl.py exam answer q1 "..."   # submit an answer you found via MCP
  python3 labctl/labctl.py exam check             # score the 7 challenges

Resource names come from `terraform output -json lab` (run from ../terraform),
or from a JSON file you point LAB_OUTPUTS at.

Reset button: `terraform apply` restores IAM, Lambda env vars and the Data API;
`labctl db-setup schema seed kb-rebuild` + `labctl kb-sync --full` restore the database.
"""

import argparse
import functools
import json
import os
import pathlib
import random
import re
import subprocess
import sys
import time
import urllib.parse

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:  # pragma: no cover
    sys.exit("labctl needs boto3:  python3 -m pip install boto3")

ROOT = pathlib.Path(__file__).resolve().parent.parent
TF_DIR = ROOT / "terraform"
SQL_DIR = ROOT / "sql"
STATE_DIR = ROOT / ".labctl"
MCP_DIR = ROOT / "labs" / "mcp"
EXAM_MINUTES = 140

# ----------------------------------------------------------------- output --

USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def c(text, code):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def orange(t):
    return c(t, "38;5;208")


def green(t):
    return c(t, "32")


def red(t):
    return c(t, "31")


def dim(t):
    return c(t, "2")


def bold(t):
    return c(t, "1")


def banner(text):
    print(orange("━" * 64))
    print(orange(f"🍊 {text}"))
    print(orange("━" * 64))


def die(msg):
    print(red(f"✖ {msg}"))
    sys.exit(1)


# ------------------------------------------------------------- lab config --

@functools.lru_cache(maxsize=None)
def lab():
    path = os.environ.get("LAB_OUTPUTS")
    if path:
        data = json.loads(pathlib.Path(path).read_text())
    else:
        try:
            raw = subprocess.run(
                ["terraform", f"-chdir={TF_DIR}", "output", "-json"],
                check=True, capture_output=True, text=True,
            ).stdout
        except FileNotFoundError:
            die("terraform not found. Install it, or export LAB_OUTPUTS=<file from `terraform output -json lab`>.")
        except subprocess.CalledProcessError as e:
            die(f"`terraform output` failed - did you run `terraform apply` in {TF_DIR}?\n{e.stderr}")
        data = json.loads(raw or "{}")
    if "lab" in data:
        data = data["lab"].get("value", data["lab"])
    if not data.get("cluster_arn"):
        die("No lab outputs found. Run `terraform apply` in the terraform/ folder first.")
    return data


@functools.lru_cache(maxsize=None)
def aws(service):
    return boto3.session.Session(region_name=lab()["region"]).client(service)


def client_error(e):
    err = e.response.get("Error", {})
    return f"{err.get('Code')}: {err.get('Message', '')}"


# ---------------------------------------------------------------- Data API --

def run_sql(statement, secret_arn=None, params=None, quiet=True):
    kwargs = dict(
        resourceArn=lab()["cluster_arn"],
        secretArn=secret_arn or lab()["admin_secret_arn"],
        database=lab()["db_name"],
        sql=statement,
        formatRecordsAs="JSON",
        continueAfterTimeout=True,
    )
    if params:
        kwargs["parameters"] = params
    for attempt in range(8):
        try:
            resp = aws("rds-data").execute_statement(**kwargs)
            return json.loads(resp.get("formattedRecords") or "[]")
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "DatabaseResumingException" and attempt < 7:
                if not quiet:
                    print(dim("  …Aurora is resuming from auto-pause, retrying in 10s"))
                time.sleep(10)
                continue
            raise


def wait_for_idle(timeout_s=900):
    """Block until no other client session in this database is running a statement."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        rows = run_sql("SELECT count(*) AS n FROM pg_stat_activity WHERE datname = current_database() "
                       "AND backend_type = 'client backend' AND state <> 'idle' AND pid <> pg_backend_pid()")
        if not rows or int(rows[0]["n"]) == 0:
            return
        time.sleep(10)
    die("a statement is still running after 15 minutes - check the RDS console")


def split_sql(text):
    chunks = re.split(r";[ \t]*(?:--[^\n]*)?(?:\n|$)", text)
    out = []
    for chunk in chunks:
        lines = chunk.strip().splitlines()
        while lines and (not lines[0].strip() or lines[0].strip().startswith("--")):
            lines.pop(0)  # drop leading comment / blank lines
        if lines:
            out.append("\n".join(lines).strip())
    return out


def kb_user_password():
    secret = aws("secretsmanager").get_secret_value(SecretId=lab()["kb_user_secret_arn"])
    return json.loads(secret["SecretString"])["password"]


def run_sql_file(name, replacements=None):
    text = (SQL_DIR / name).read_text()
    for key, value in (replacements or {}).items():
        text = text.replace("{{" + key + "}}", value)
    for stmt in split_sql(text):
        first = " ".join(stmt.split())[:90]
        try:
            started = time.time()
            rows = run_sql(stmt, quiet=False)
            took = time.time() - started
            print(green("  ✔ ") + first + dim(f"  ({took:.1f}s)"))
            if rows and stmt.lstrip().upper().startswith("SELECT"):
                for r in rows[:10]:
                    print(dim("      " + json.dumps(r, default=str)))
        except ClientError as e:
            msg = client_error(e)
            if "already exists" in msg:
                print(dim(f"  • {first}  (already exists - skipped)"))
            elif e.response["Error"]["Code"] == "StatementTimeoutException":
                # continueAfterTimeout=True: the statement keeps running server-side.
                print(orange(f"  ⏳ {first}\n      still running after 45s - waiting for it to finish"))
                wait_for_idle()
            else:
                print(red(f"  ✖ {first}\n      {msg}"))
                raise SystemExit(1)


# ---------------------------------------------------------------- Lambda --

def invoke(payload):
    resp = aws("lambda").invoke(FunctionName=lab()["lambda_name"], Payload=json.dumps(payload).encode())
    body = json.loads(resp["Payload"].read() or b"{}")
    if resp.get("FunctionError"):
        return {"ok": False, "result": body}
    return body


def lambda_env():
    cfg = aws("lambda").get_function_configuration(FunctionName=lab()["lambda_name"])
    return cfg.get("Environment", {}).get("Variables", {})


def set_lambda_env(**changes):
    variables = lambda_env()
    variables.update(changes)
    fn = lab()["lambda_name"]
    aws("lambda").update_function_configuration(FunctionName=fn, Environment={"Variables": variables})
    aws("lambda").get_waiter("function_updated").wait(FunctionName=fn)


# ------------------------------------------------------------------- IAM --

def _get_policy(role, policy):
    doc = aws("iam").get_role_policy(RoleName=role, PolicyName=policy)["PolicyDocument"]
    if isinstance(doc, str):
        doc = json.loads(urllib.parse.unquote(doc))
    return doc


def _put_policy(role, policy, doc):
    aws("iam").put_role_policy(RoleName=role, PolicyName=policy, PolicyDocument=json.dumps(doc))


def _as_list(value):
    return value if isinstance(value, list) else [value]


def edit_statement(role, policy, sid, mutate):
    """mutate(statement) -> statement or None (None removes it)."""
    doc = _get_policy(role, policy)
    new = []
    for st in _as_list(doc["Statement"]):
        if st.get("Sid") == sid:
            st = mutate(st)
        if st is not None:
            new.append(st)
    doc["Statement"] = new
    _put_policy(role, policy, doc)


def simulate(role_arn, actions, resources):
    resp = aws("iam").simulate_principal_policy(
        PolicySourceArn=role_arn, ActionNames=actions, ResourceArns=resources)
    return {r["EvalActionName"]: r["EvalDecision"] for r in resp["EvaluationResults"]}


# --------------------------------------------------------- check helpers --

class Results:
    def __init__(self):
        self.items = []

    def add(self, ok, label, detail=""):
        self.items.append((bool(ok), label, detail))
        mark = green("  ✔") if ok else red("  ✖")
        print(f"{mark} {label}" + (dim(f"  — {detail}") if detail else ""))
        return ok

    @property
    def passed(self):
        return all(ok for ok, _, _ in self.items)


def safe(fn, default=None):
    try:
        return fn()
    except ClientError as e:
        return default if default is not None else {"__error__": client_error(e)}
    except Exception as e:  # noqa: BLE001
        return default if default is not None else {"__error__": f"{type(e).__name__}: {e}"}


def health_checks():
    out = safe(lambda: invoke({"action": "health"}))
    if "__error__" in out:
        return {"__invoke__": out["__error__"]}
    return out.get("result", {}).get("checks", {"__invoke__": json.dumps(out)[:200]})


def memory_roundtrip():
    sid = f"labctl-check-{random.randint(1000, 9999)}"
    w = invoke({"action": "remember", "session_id": sid, "role": "user", "content": "roundtrip test"})
    if not w.get("ok"):
        return False, json.dumps(w.get("result"))[:200]
    r = invoke({"action": "recall", "session_id": sid})
    if not r.get("ok"):
        return False, json.dumps(r.get("result"))[:200]
    return bool(r["result"]), f"{len(r['result'])} turn(s) recalled"


def find_kb_id():
    kb = lambda_env().get("KB_ID") or lab().get("knowledge_base_id")
    if kb:
        return kb
    paginator = aws("bedrock-agent").get_paginator("list_knowledge_bases")
    for page in paginator.paginate():
        for summary in page.get("knowledgeBaseSummaries", []):
            detail = aws("bedrock-agent").get_knowledge_base(knowledgeBaseId=summary["knowledgeBaseId"])
            rds = detail["knowledgeBase"].get("storageConfiguration", {}).get("rdsConfiguration", {})
            if rds.get("resourceArn") == lab()["cluster_arn"]:
                return summary["knowledgeBaseId"]
    return ""


def kb_data_source(kb_id):
    sources = aws("bedrock-agent").list_data_sources(knowledgeBaseId=kb_id).get("dataSourceSummaries", [])
    return sources[0]["dataSourceId"] if sources else ""


def latest_ingestion(kb_id, ds_id):
    jobs = aws("bedrock-agent").list_ingestion_jobs(
        knowledgeBaseId=kb_id, dataSourceId=ds_id,
        sortBy={"attribute": "STARTED_AT", "order": "DESCENDING"}, maxResults=1,
    ).get("ingestionJobSummaries", [])
    return jobs[0] if jobs else None


def kb_rows():
    rows = run_sql("SELECT count(*) AS n FROM bedrock_integration.bedrock_kb")
    return int(rows[0]["n"]) if rows else 0


def plan_lines(query):
    rows = run_sql("EXPLAIN " + query)
    return [next(iter(r.values())) for r in rows]


SEARCH_WITH_CATEGORY = (
    "SELECT product_id, name, price, rating FROM products "
    "WHERE name ILIKE '%speaker%' AND category = 'audio' ORDER BY rating DESC, product_id LIMIT 10"
)
SEARCH_NAME_ONLY = (
    "SELECT product_id, name, price, rating FROM products "
    "WHERE name ILIKE '%drone 42%' ORDER BY rating DESC, product_id LIMIT 10"
)

# =================================================================== DRILLS ==
#
# Each drill: description, break(), check(results), hint.
# ============================================================================


def break_wrong_secret():
    set_lambda_env(DB_SECRET_ARN=lab()["kb_user_secret_arn"])


def check_wrong_secret(res):
    env_ok = lambda_env().get("DB_SECRET_ARN") == lab()["admin_secret_arn"]
    res.add(env_ok, "Lambda DB_SECRET_ARN points at the admin secret")
    h = health_checks()
    res.add(h.get("aurora_products") == "ok", "Agent can query the products table", h.get("aurora_products", ""))


def break_data_api():
    aws("rds").disable_http_endpoint(ResourceArn=lab()["cluster_arn"])


def check_data_api(res):
    cluster = aws("rds").describe_db_clusters(DBClusterIdentifier=lab()["cluster_id"])["DBClusters"][0]
    res.add(cluster.get("HttpEndpointEnabled"), "RDS Data API (HTTP endpoint) is enabled on the cluster")
    h = health_checks()
    res.add(h.get("aurora_connect") == "ok", "Agent reaches Aurora through the Data API", h.get("aurora_connect", ""))


def break_aurora_iam():
    def mutate(st):
        st["Action"] = [a for a in _as_list(st["Action"]) if a != "rds-data:ExecuteStatement"]
        return st
    edit_statement(lab()["lambda_role_name"], lab()["lambda_policy_name"], "AuroraDataApi", mutate)


def check_aurora_iam(res):
    d = simulate(lab()["lambda_role_arn"], ["rds-data:ExecuteStatement"], [lab()["cluster_arn"]])
    res.add(d.get("rds-data:ExecuteStatement") == "allowed", "Lambda role may call rds-data:ExecuteStatement on the cluster",
            d.get("rds-data:ExecuteStatement", ""))
    h = health_checks()
    res.add(h.get("aurora_connect") == "ok", "Agent reaches Aurora", h.get("aurora_connect", ""))


KB_TABLE_BROKEN = [
    "DROP TABLE IF EXISTS bedrock_integration.bedrock_kb",
    "CREATE SCHEMA IF NOT EXISTS bedrock_integration",
    "CREATE TABLE bedrock_integration.bedrock_kb (id uuid PRIMARY KEY, embedding vector(1536), "
    "chunks text, metadata json, custom_metadata jsonb)",
]


def break_vector_dims():
    for stmt in KB_TABLE_BROKEN:
        run_sql(stmt)


def check_vector_dims(res):
    cols = safe(lambda: run_sql(
        "SELECT a.attname AS col, format_type(a.atttypid, a.atttypmod) AS type FROM pg_attribute a "
        "WHERE a.attrelid = 'bedrock_integration.bedrock_kb'::regclass AND a.attnum > 0 AND NOT a.attisdropped"), [])
    types = {r["col"]: r["type"] for r in cols} if isinstance(cols, list) else {}
    res.add(bool(types), "Table bedrock_integration.bedrock_kb exists")
    want_dims = f"vector({lab().get('embedding_dimensions', 1024)})"
    res.add(types.get("embedding") == want_dims, f"embedding column is {want_dims} (matches Titan V2)",
            types.get("embedding", "missing"))
    res.add(types.get("id") == "uuid" and types.get("chunks") == "text" and types.get("metadata") in ("json", "jsonb"),
            "id uuid / chunks text / metadata json columns present")
    idx = safe(lambda: run_sql(
        "SELECT indexdef FROM pg_indexes WHERE schemaname = 'bedrock_integration' AND tablename = 'bedrock_kb'"), [])
    defs = [r["indexdef"].lower() for r in idx] if isinstance(idx, list) else []
    res.add(any("hnsw" in d and "embedding" in d and "vector_cosine_ops" in d for d in defs),
            "HNSW index on embedding using vector_cosine_ops")
    res.add(any("gin" in d and "chunks" in d for d in defs), "GIN text-search index on chunks (hybrid search)")
    priv = safe(lambda: run_sql(
        "SELECT has_schema_privilege('bedrock_user','bedrock_integration','USAGE') AS usage, "
        "has_table_privilege('bedrock_user','bedrock_integration.bedrock_kb','SELECT') AS sel, "
        "has_table_privilege('bedrock_user','bedrock_integration.bedrock_kb','INSERT') AS ins, "
        "has_table_privilege('bedrock_user','bedrock_integration.bedrock_kb','UPDATE') AS upd, "
        "has_table_privilege('bedrock_user','bedrock_integration.bedrock_kb','DELETE') AS del"), [])
    row = priv[0] if isinstance(priv, list) and priv else {}
    res.add(row and all(row.values()), "bedrock_user has USAGE + SELECT/INSERT/UPDATE/DELETE", json.dumps(row))


def break_memory_iam():
    def mutate(st):
        st["Action"] = ["dynamodb:GetItem"]
        return st
    edit_statement(lab()["lambda_role_name"], lab()["lambda_policy_name"], "AgentMemory", mutate)


def check_memory_iam(res):
    d = simulate(lab()["lambda_role_arn"], ["dynamodb:PutItem", "dynamodb:Query"], [lab()["memory_table_arn"]])
    res.add(d.get("dynamodb:PutItem") == "allowed", "Lambda role may PutItem on the memory table", d.get("dynamodb:PutItem", ""))
    res.add(d.get("dynamodb:Query") == "allowed", "Lambda role may Query the memory table", d.get("dynamodb:Query", ""))
    ok, detail = memory_roundtrip()
    res.add(ok, "remember → recall round-trip works", detail)


def break_memory_table():
    set_lambda_env(MEMORY_TABLE=lab()["memory_table"] + "-v2")


def check_memory_table(res):
    current = lambda_env().get("MEMORY_TABLE")
    res.add(current == lab()["memory_table"], "Lambda MEMORY_TABLE names the real table", current or "unset")
    ok, detail = memory_roundtrip()
    res.add(ok, "remember → recall round-trip works", detail)


def break_kb_role():
    edit_statement(lab()["kb_role_name"], lab()["kb_policy_name"], "KbSecret", lambda st: None)


def check_kb_role(res):
    d = simulate(lab()["kb_role_arn"], ["secretsmanager:GetSecretValue"], [lab()["kb_user_secret_arn"]])
    res.add(d.get("secretsmanager:GetSecretValue") == "allowed",
            "KB service role can read the bedrock_user secret", d.get("secretsmanager:GetSecretValue", ""))
    d2 = simulate(lab()["kb_role_arn"], ["rds-data:ExecuteStatement", "rds-data:BatchExecuteStatement"], [lab()["cluster_arn"]])
    res.add(all(v == "allowed" for v in d2.values()), "KB service role can use the Data API", json.dumps(d2))


def break_kb_id():
    set_lambda_env(KB_ID="")


def check_kb_id(res):
    kb = lambda_env().get("KB_ID", "")
    res.add(bool(kb), "Lambda KB_ID is set", kb or "empty")
    if kb:
        info = safe(lambda: aws("bedrock-agent").get_knowledge_base(knowledgeBaseId=kb)["knowledgeBase"])
        rds = (info.get("storageConfiguration") or {}).get("rdsConfiguration", {}) if "__error__" not in info else {}
        res.add(rds.get("resourceArn") == lab()["cluster_arn"], "KB stores its vectors in this Aurora cluster",
                info.get("__error__", rds.get("tableName", "")))
    r = safe(lambda: invoke({"action": "search_docs", "query": "How long is the return window for Zest Club members?"}))
    ok = isinstance(r, dict) and r.get("ok") and len(r.get("result") or []) > 0
    res.add(ok, "Agent search_docs returns results", "" if ok else json.dumps(r)[:200])


def check_kb_synced(res):
    kb = find_kb_id()
    res.add(bool(kb), "A Knowledge Base backed by this Aurora cluster exists", kb or "none found")
    if not kb:
        return
    ds = safe(lambda: kb_data_source(kb), "")
    res.add(bool(ds), "Knowledge Base has an S3 data source", ds or "none")
    if ds:
        job = safe(lambda: latest_ingestion(kb, ds), {}) or {}
        res.add(job.get("status") == "COMPLETE", "Latest ingestion (sync) job is COMPLETE", job.get("status", "never synced"))
        stats = job.get("statistics", {})
        res.add(stats.get("numberOfDocumentsFailed", 0) == 0, "No documents failed in the latest sync", json.dumps(stats))
    n = safe(kb_rows, -1)
    res.add(isinstance(n, int) and n > 0, "Vectors are present in bedrock_integration.bedrock_kb",
            f"{n} rows" if isinstance(n, int) and n >= 0 else "table not readable")
    if n == 0:
        print(dim("     Sync is incremental: if the table was recreated, run `labctl kb-sync --full`."))


def break_slow_search():
    for stmt in ["DROP INDEX IF EXISTS idx_products_name_trgm",
                 "DROP INDEX IF EXISTS idx_products_category_rating",
                 "DROP EXTENSION IF EXISTS pg_trgm CASCADE"]:
        run_sql(stmt)


def check_slow_search(res):
    ext = safe(lambda: run_sql("SELECT extname FROM pg_extension WHERE extname = 'pg_trgm'"), [])
    res.add(isinstance(ext, list) and len(ext) == 1, "pg_trgm extension is installed")
    for label, q in [("category + name search", SEARCH_WITH_CATEGORY), ("name-only search", SEARCH_NAME_ONLY)]:
        lines = safe(lambda q=q: plan_lines(q), [])
        seq = [ln for ln in lines if "Seq Scan on products" in ln]
        res.add(bool(lines) and not seq, f"{label} avoids a sequential scan of products",
                (lines[0].strip()[:90] if lines else "EXPLAIN failed"))
    r = safe(lambda: invoke({"action": "search_products", "query": "drone 42"}))
    ms = r.get("duration_ms", 99999) if isinstance(r, dict) else 99999
    res.add(isinstance(r, dict) and r.get("ok") and ms < 1500, "Agent product search answers in < 1.5 s", f"{ms} ms")


# ---------------------------------------------------------- MCP config --

def mcp_servers(region=None, cluster_arn=None, database=None, ddb_region=None):
    L = lab()
    return {
        "awslabs.postgres-mcp-server": {
            "command": "uvx",
            "args": [
                "awslabs.postgres-mcp-server@latest",
                "--resource_arn", cluster_arn or L["cluster_arn"],
                "--secret_arn", L["admin_secret_arn"],
                "--database", database or L["db_name"],
                "--region", region or L["region"],
                "--readonly", "True",
            ],
            "env": {"AWS_PROFILE": "default", "AWS_REGION": region or L["region"], "FASTMCP_LOG_LEVEL": "ERROR"},
        },
        "awslabs.dynamodb-mcp-server": {
            "command": "uvx",
            "args": ["awslabs.dynamodb-mcp-server@latest"],
            "env": {"DDB-MCP-READONLY": "true", "AWS_PROFILE": "default",
                    "AWS_REGION": ddb_region or L["region"], "FASTMCP_LOG_LEVEL": "ERROR"},
        },
    }


def wrong_region():
    return "us-west-1" if lab()["region"] != "us-west-1" else "us-east-2"


def break_mcp_config():
    MCP_DIR.mkdir(parents=True, exist_ok=True)
    broken = {"mcpServers": mcp_servers(
        region=wrong_region(),
        cluster_arn=lab()["writer_instance_arn"],   # instance ARN instead of cluster ARN
        database="postgres",                        # wrong database
        ddb_region=wrong_region(),
    )}
    path = MCP_DIR / "broken-mcp.json"
    path.write_text(json.dumps(broken, indent=2) + "\n")
    print(f"  Wrote {orange(os.path.relpath(path, ROOT))} - copy it into your MCP client config and fix it.")
    print(f"  Then grade it with: labctl check mcp-config --file <your fixed file>")


def _find_server(servers, needle):
    for name, cfg in servers.items():
        blob = name + " " + " ".join(cfg.get("args", []))
        if needle in blob:
            return cfg
    return None


def _arg(cfg, flag):
    args = cfg.get("args", [])
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


def _load_mcp_servers(res, file=None):
    path = pathlib.Path(file).expanduser() if file else MCP_DIR / "broken-mcp.json"
    if not path.exists():
        res.add(False, f"MCP config file {path} exists")
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        res.add(False, f"{path} is valid JSON", str(e))
        return None
    return data.get("mcpServers") or data.get("servers") or {}


def check_mcp_pg(res, file=None):
    servers = _load_mcp_servers(res, file)
    if servers is None:
        return
    L = lab()
    pg = _find_server(servers, "postgres-mcp-server")
    res.add(pg is not None, "Aurora PostgreSQL MCP server is configured")
    if pg:
        res.add(_arg(pg, "--resource_arn") == L["cluster_arn"], "--resource_arn is the CLUSTER ARN (…:cluster:…)",
                _arg(pg, "--resource_arn") or "missing")
        res.add(_arg(pg, "--secret_arn") == L["admin_secret_arn"], "--secret_arn is the admin secret")
        res.add(_arg(pg, "--database") == L["db_name"], f"--database is {L['db_name']}", _arg(pg, "--database") or "missing")
        res.add(_arg(pg, "--region") == L["region"], f"--region is {L['region']}", _arg(pg, "--region") or "missing")
        res.add(str(_arg(pg, "--readonly")).lower() == "true", "--readonly True", _arg(pg, "--readonly") or "missing")


def check_mcp_ddb(res, file=None):
    servers = _load_mcp_servers(res, file)
    if servers is None:
        return
    dd = _find_server(servers, "dynamodb-mcp-server")
    res.add(dd is not None, "DynamoDB MCP server is configured")
    if dd:
        region = (dd.get("env") or {}).get("AWS_REGION")
        res.add(region == lab()["region"], f"DynamoDB MCP AWS_REGION is {lab()['region']}", region or "missing")


def check_mcp_config(res, file=None):
    check_mcp_pg(res, file)
    check_mcp_ddb(res, file)


DRILLS = {
    "wrong-secret": ("Lambda points at the wrong Secrets Manager secret", break_wrong_secret, check_wrong_secret,
                     "Run the health action and read the aurora_* error. Which secret ARN is in the Lambda env vars, and which secret can the role read?"),
    "data-api": ("The Aurora Data API (HTTP endpoint) was switched off", break_data_api, check_data_api,
                 "BadRequestException… HttpEndpoint is not enabled. Serverless v2 uses `aws rds enable-http-endpoint`, not modify-db-cluster."),
    "aurora-iam": ("A Data API permission went missing from the agent role", break_aurora_iam, check_aurora_iam,
                   "AccessDeniedException names the exact action. Compare the AuroraDataApi statement with what the code calls."),
    "vector-dims": ("The KB vector table was recreated with the wrong shape", break_vector_dims, check_vector_dims,
                    "Titan Text Embeddings V2 → 1024 dims. Bedrock also needs the HNSW + GIN indexes and bedrock_user grants."),
    "memory-iam": ("The agent can read memory but not write it", break_memory_iam, check_memory_iam,
                   "remember fails with AccessDenied on PutItem; recall fails on Query. Fix the AgentMemory statement."),
    "memory-table": ("The agent is pointed at a memory table that doesn't exist", break_memory_table, check_memory_table,
                     "The policy is scoped to the real table, so a wrong name ALSO shows up as AccessDenied. Compare the table ARN in the error with $MEMORY_TABLE_ARN."),
    "kb-role": ("The Knowledge Base service role lost access to its DB secret", break_kb_role, check_kb_role,
                "Sync/creation fails mentioning Secrets Manager. The KB role needs GetSecretValue on the bedrock_user secret."),
    "kb-id": ("The agent forgot which Knowledge Base to use", break_kb_id, check_kb_id,
              "search_docs → 'KB_ID is not set'. Copy the KB ID from the Bedrock console into the Lambda env (or knowledge_base_id in tfvars)."),
    "slow-search": ("Product search got slow - indexes and pg_trgm are gone", break_slow_search, check_slow_search,
                    "EXPLAIN the search query. Leading-wildcard ILIKE needs pg_trgm + a GIN (gin_trgm_ops) index."),
    "mcp-config": ("A broken MCP config for the Aurora + DynamoDB MCP servers", break_mcp_config, check_mcp_config,
                   "Cluster ARN (not instance ARN), database agentdb, the lab's region - for both servers."),
}


def cmd_drills(_args):
    banner("Break-fix drills")
    for name, (desc, *_rest) in DRILLS.items():
        print(f"  {orange(name.ljust(14))} {desc}")
    print(dim("\n  labctl break <drill>   then   labctl check <drill>   (hint: labctl hint <drill>)"))


def cmd_break(args):
    if args.drill not in DRILLS:
        die(f"unknown drill {args.drill}. Try: labctl drills")
    desc, brk, _chk, _hint = DRILLS[args.drill]
    banner(f"BREAK: {args.drill}")
    print(f"  {desc}")
    brk()
    print(green("\n  💥 Fault injected. Something in Zest's data layer is now broken."))
    print(dim(f"  When you think it's fixed: labctl check {args.drill}"))


EXTRA_CHECKS = {"kb-synced": check_kb_synced, "mcp-pg": check_mcp_pg, "mcp-ddb": check_mcp_ddb}


def cmd_check(args):
    if args.drill in EXTRA_CHECKS:
        res = Results()
        banner(f"CHECK: {args.drill}")
        fn = EXTRA_CHECKS[args.drill]
        fn(res, args.file) if args.drill.startswith("mcp-") else fn(res)
    else:
        if args.drill not in DRILLS:
            die(f"unknown drill {args.drill}. Try: labctl drills")
        banner(f"CHECK: {args.drill}")
        res = Results()
        chk = DRILLS[args.drill][2]
        if args.drill == "mcp-config":
            chk(res, args.file)
        else:
            chk(res)
    print()
    print(green(bold("  🏆 FIXED! Nice work, Ranger.")) if res.passed else red(bold("  Not yet - keep digging.")))
    sys.exit(0 if res.passed else 1)


def cmd_hint(args):
    if args.drill not in DRILLS:
        die("unknown drill")
    print(orange("💡 ") + DRILLS[args.drill][3])


# ==================================================================== EXAM ==

ESCALATION_SESSION = "sess-escalation-042"

CHALLENGES = [
    ("1", "Restore the agent's access to Aurora PostgreSQL", [check_data_api, check_wrong_secret]),
    ("2", "Repair the pgvector document store", [check_vector_dims]),
    ("3", "Restore the agent's DynamoDB memory", [check_memory_iam, check_memory_table]),
    ("4", "Bring the Bedrock Knowledge Base on Aurora back online", [check_kb_role, check_kb_synced, check_kb_id]),
    ("5", "Configure the Aurora MCP server and investigate", ["mcp-pg", "q1"]),
    ("6", "Configure the DynamoDB MCP server and inspect agent state", ["mcp-ddb", "q2"]),
    ("7", "Optimize the agent's product search", [check_slow_search]),
]


def exam_state():
    path = STATE_DIR / "exam.json"
    return json.loads(path.read_text()) if path.exists() else {}


def save_exam_state(state):
    STATE_DIR.mkdir(exist_ok=True)
    (STATE_DIR / "exam.json").write_text(json.dumps(state, indent=2))


def seed_escalation():
    table = lab()["memory_table"]
    ddb = aws("dynamodb")
    ticket = f"TNG-{random.randint(1000, 9999)}"
    decoy = f"TNG-{random.randint(1000, 9999)}"
    now = int(time.time())
    exp = str(now + 14 * 86400)
    items = [
        {"session_id": ESCALATION_SESSION, "sk": "STATE", "customer_id": "C00042", "status": "escalated",
         "escalation_ticket": ticket, "sentiment": "frustrated", "open_issue": "Turbo Drone battery drains in 4 minutes",
         "expires_at": exp},
        {"session_id": ESCALATION_SESSION, "sk": "MSG#2026-11-20T15:02:11.000Z#a1b2c3", "role": "user",
         "content": "My drone battery dies after 4 minutes and nobody is helping me.", "customer_id": "C00042", "expires_at": exp},
        {"session_id": ESCALATION_SESSION, "sk": "MSG#2026-11-20T15:02:14.000Z#d4e5f6", "role": "assistant",
         "content": "I'm sorry! I've escalated this to a supervisor.", "customer_id": "C00042", "expires_at": exp},
        {"session_id": "sess-escalation-024", "sk": "STATE", "customer_id": "C00024", "status": "resolved",
         "escalation_ticket": decoy, "sentiment": "happy", "expires_at": exp},
    ]
    for it in items:
        ddb.put_item(TableName=table, Item={k: ({"N": v} if k == "expires_at" else {"S": v}) for k, v in it.items()})
    return ticket


def cmd_exam(args):
    if args.exam_cmd == "start":
        banner("OPERATION TANGERINE - mock exam lab")
        print("  This injects every fault at once into YOUR lab environment:")
        print("  database objects are dropped, IAM policies and Lambda settings are altered.")
        print(dim("  Reset any time with `terraform apply` + `labctl db-setup schema seed kb indexes`."))
        if not args.yes:
            if input(orange("\n  Type 'tangerine' to begin: ")).strip().lower() != "tangerine":
                die("aborted")
        steps = [
            ("Seeding the escalated customer session", seed_escalation),
            ("Product search indexes vanish", break_slow_search),
            ("Vector store gets the wrong shape", break_vector_dims),
            ("Agent points at the wrong secret", break_wrong_secret),
            ("Memory permissions shrink", break_memory_iam),
            ("Memory table name drifts", break_memory_table),
            ("KB service role loses its secret", break_kb_role),
            ("Agent forgets its Knowledge Base", break_kb_id),
            ("MCP config gets scrambled", break_mcp_config),
            ("Data API goes dark", break_data_api),
        ]
        for label, fn in steps:
            print(orange("  ⚡ ") + label)
            try:
                fn()
            except ClientError as e:
                print(red(f"     {client_error(e)}"))
        save_exam_state({"started_at": time.time(), "answers": {}})
        print(green(bold(f"\n  ⏱  Clock started: {EXAM_MINUTES} minutes. Read ALL the challenge guidance first.")))
        print(dim("  Grade any time: labctl exam check"))
        return

    if args.exam_cmd == "answer":
        state = exam_state()
        if not state:
            die("no exam in progress - run `labctl exam start`")
        state.setdefault("answers", {})[args.question] = args.value
        save_exam_state(state)
        print(green(f"  ✔ recorded {args.question} = {args.value!r}"))
        return

    if args.exam_cmd == "check":
        state = exam_state()
        banner("OPERATION TANGERINE - grading")
        if state.get("started_at"):
            elapsed = (time.time() - state["started_at"]) / 60
            left = EXAM_MINUTES - elapsed
            print(f"  Elapsed {elapsed:.0f} min - " + (green(f"{left:.0f} min left") if left > 0 else red("time is up!")))
        answers = state.get("answers", {})
        score = 0
        for num, title, checks in CHALLENGES:
            print(orange(f"\n  Challenge {num}: {title}"))
            res = Results()
            for chk in checks:
                if chk in ("mcp-pg", "mcp-ddb"):
                    file = args.file or str(MCP_DIR / "broken-mcp.json")
                    print(dim(f"    (grading MCP config: {file})"))
                    (check_mcp_pg if chk == "mcp-pg" else check_mcp_ddb)(res, file)
                elif chk == "q1":
                    try:
                        row = run_sql("SELECT c.segment, round(sum(o.amount)) AS total FROM orders o "
                                      "JOIN customers c ON c.customer_id = o.customer_id "
                                      "GROUP BY c.segment ORDER BY total DESC LIMIT 1")
                    except ClientError as e:
                        res.add(False, "Q1: segment with the highest total order amount", "can't grade yet: " + client_error(e))
                        continue
                    want = row[0]["segment"] if row else "?"
                    got = (answers.get("q1") or "").strip().lower()
                    res.add(got == want, "Q1: segment with the highest total order amount", got or "no answer submitted")
                elif chk == "q2":
                    item = aws("dynamodb").get_item(TableName=lab()["memory_table"],
                                                    Key={"session_id": {"S": ESCALATION_SESSION}, "sk": {"S": "STATE"}})
                    want = item.get("Item", {}).get("escalation_ticket", {}).get("S", "?")
                    got = (answers.get("q2") or "").strip().upper()
                    res.add(got == want, f"Q2: escalation ticket for {ESCALATION_SESSION}", got or "no answer submitted")
                else:
                    try:
                        chk(res)
                    except ClientError as e:
                        res.add(False, chk.__name__, client_error(e))
            if res.passed:
                score += 1
        pct = round(100 * score / len(CHALLENGES))
        print()
        print(orange("━" * 64))
        verdict = green(bold("PASS 🏆 Tangerine Legend!")) if pct >= 70 else red(bold("NOT YET - review the failed checks"))
        print(f"  Score: {bold(str(score))}/{len(CHALLENGES)} challenges ({pct}%)   {verdict}")
        print(dim("  (Mock threshold 70%. The real exam's scoring is not published.)"))
        print(orange("━" * 64))


# ================================================================ COMMANDS ==

def cmd_status(_args):
    L = lab()
    banner(f"Mission status - {L['name']} ({L['region']})")
    for key in ["cluster_id", "db_name", "memory_table", "lambda_name", "docs_bucket", "knowledge_base_id"]:
        print(f"  {key.ljust(18)} {L.get(key) or dim('(not set)')}")
    cluster = safe(lambda: aws("rds").describe_db_clusters(DBClusterIdentifier=L["cluster_id"])["DBClusters"][0], {})
    print(f"  {'cluster status'.ljust(18)} {cluster.get('Status', '?')}   Data API: "
          + (green("on") if cluster.get("HttpEndpointEnabled") else red("OFF")))
    print(orange("\n  Agent health"))
    for k, v in health_checks().items():
        print(("  " + green("✔ ") if v == "ok" else "  " + red("✖ ")) + k.ljust(16) + ("" if v == "ok" else dim(v[:110])))


def cmd_db_setup(args):
    steps = args.steps or ["schema", "seed"]
    files = {
        "schema": "01_schema.sql",
        "seed": "02_seed.sql",
        "indexes": "03_indexes_solution.sql",
        "kb": "04_kb_vector_store.sql",
        "playground": "05_pgvector_playground.sql",
    }
    for step in steps:
        if step == "kb-rebuild":
            banner("db-setup kb-rebuild  (DROP + recreate bedrock_integration.bedrock_kb)")
            run_sql("DROP TABLE IF EXISTS bedrock_integration.bedrock_kb")
            print(green("  ✔ ") + "DROP TABLE IF EXISTS bedrock_integration.bedrock_kb")
            step = "kb"
        if step not in files:
            die(f"unknown step {step}; choose from {', '.join(files)}, kb-rebuild")
        banner(f"db-setup {step}  ({files[step]})")
        repl = {"KB_USER_PASSWORD": kb_user_password()} if step == "kb" else None
        run_sql_file(files[step], repl)
    print(green("\n  Done."))


SUPPORT_NOTES = [
    ("C00001", "Customer's Turbo Drone battery lasts under 5 minutes. Battery degraded; shipped a warranty battery."),
    ("C00002", "Pro Headphones crackle in the left earcup. Firmware 4.2 fixed it."),
    ("C00003", "Charged twice for one order. Pending authorization dropped off after 4 days, no refund needed."),
    ("C00004", "Package stuck in transit for 12 days. Reshipped the order once at no cost."),
    ("C00005", "Wants to return a blender after 40 days. Zest Club Juice member, so the 45-day window applied."),
    ("C00006", "Tent pole snapped on first trip. Covered by 3-year pole warranty, replacement pole sent."),
    ("C00007", "Enterprise customer asked to pay by card. Explained net-30 invoicing, routed to finance."),
    ("C00008", "Smart Watch won't pair with phone. Reset pairing by holding power for 8 seconds."),
    ("C00009", "Asked for a price match with a marketplace seller. Declined - marketplaces are excluded."),
    ("C00010", "Very angry about a late delivery. Escalated to supervisor with ticket TNG-1007."),
    ("C00011", "Nano Drone drifts left while hovering. IMU recalibration on a flat surface fixed it."),
    ("C00012", "Kettle arrived with a dented lid. Order under $250 so sent an instant replacement."),
    ("C00013", "Monitor arrived cracked, order total $410. Issued an RMA before shipping the replacement."),
    ("C00014", "Wanted to change the shipping address after shipment. Pointed them to carrier redirect."),
    ("C00015", "Asked about accidental damage coverage. Sold Citrus Care+ at 12% of item price."),
    ("C00016", "Speaker battery only lasts 6 hours. Turbo Speaker should get 20 hours; warranty replacement."),
    ("C00017", "Returned sneakers that were final sale. Return refused per policy, offered store credit as courtesy."),
    ("C00018", "Loyalty points disappeared. Points expired after 18 months without purchases."),
    ("C00019", "Express shipping charged to a Pulp tier member. Refunded - Pulp gets free express shipping."),
    ("C00020", "Next-day shipping requested to latam region. Not available; upgraded to express."),
    ("C00021", "Drone flown 15 times, wants a refund. Not returnable; filed warranty claim for the gimbal instead."),
    ("C00022", "Router drops Wi-Fi every evening. Firmware update and channel change resolved it."),
    ("C00023", "Desk delivered missing screws. Shipped hardware kit with 2-day shipping."),
    ("C00024", "Happy customer praising fast delivery of a camera. No action needed."),
    ("C00025", "APAC order over $1,000 delayed at customs. Explained 1-3 day paperwork delay."),
    ("C00026", "Blender motor died after 3 years. Wonka blenders have a 5-year motor warranty; replaced."),
    ("C00027", "Jacket zipper broke after 2 months. Apparel 90-day defect warranty applied."),
    ("C00028", "Double charge settled on both transactions. Refunded duplicate, logged BILLING-DUP."),
    ("C00029", "Stark laptop charger failed after 30 months. Stark adds 12 months, so 3 years total coverage."),
    ("C00030", "Customer frustrated that headphones crackle even after firmware 4.2. Offered warranty replacement."),
]


def cmd_embed_notes(_args):
    banner("Embedding 30 support notes with Titan Text Embeddings V2")
    L = lab()
    br = aws("bedrock-runtime")
    run_sql("DELETE FROM support_notes")
    for cid, note in SUPPORT_NOTES:
        body = {"inputText": note, "dimensions": int(L.get("embedding_dimensions", 1024)), "normalize": True}
        vec = json.loads(br.invoke_model(modelId=L["embedding_model_id"], body=json.dumps(body))["body"].read())["embedding"]
        run_sql("INSERT INTO support_notes (customer_id, note, embedding) VALUES (:cid, :note, CAST(:emb AS vector))",
                params=[{"name": "cid", "value": {"stringValue": cid}},
                        {"name": "note", "value": {"stringValue": note}},
                        {"name": "emb", "value": {"stringValue": json.dumps(vec)}}])
        print(green("  ✔ ") + dim(f"{cid}  [{len(vec)} dims]  ") + note[:60] + "…")
    print(green("\n  Done. Try: labctl invoke similar_notes '{\"query\":\"my drone battery dies fast\"}'"))


def cmd_kb_sync(args):
    kb = args.kb or find_kb_id()
    if not kb:
        die("No Knowledge Base found. Create one (Lab 2.6) or pass --kb <id>.")
    ds = args.data_source or kb_data_source(kb)
    if not ds:
        die(f"Knowledge Base {kb} has no data source.")
    if args.full:
        touch_docs()
    banner(f"Syncing KB {kb} / data source {ds}")
    job = aws("bedrock-agent").start_ingestion_job(knowledgeBaseId=kb, dataSourceId=ds)["ingestionJob"]
    job_id = job["ingestionJobId"]
    while True:
        job = aws("bedrock-agent").get_ingestion_job(knowledgeBaseId=kb, dataSourceId=ds, ingestionJobId=job_id)["ingestionJob"]
        print(dim(f"  {time.strftime('%H:%M:%S')}  {job['status']}"))
        if job["status"] in ("COMPLETE", "FAILED", "STOPPED"):
            break
        time.sleep(10)
    print(json.dumps(job.get("statistics", {}), indent=2))
    for reason in job.get("failureReasons", []):
        print(red("  ✖ " + reason))
    print(green("  ✔ Sync complete") if job["status"] == "COMPLETE" else red(f"  Sync {job['status']}"))
    n = safe(kb_rows, -1)
    if isinstance(n, int) and n >= 0:
        print(f"  {n} vector rows in bedrock_integration.bedrock_kb")
        if n == 0 and job["status"] == "COMPLETE":
            print(orange("  ⚠ Sync is incremental and the docs didn't change, so nothing was re-ingested."))
            print(orange("    Recreated the table? Run: labctl kb-sync --full"))


def touch_docs():
    """Append a marker to every .md doc in S3 so Bedrock sees them as modified and re-ingests them."""
    s3 = aws("s3")
    bucket = lab()["docs_bucket"]
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    pages = s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix="docs/")
    keys = [o["Key"] for page in pages for o in page.get("Contents", []) if o["Key"].endswith(".md")]
    for key in keys:
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode()
        body = re.sub(r"\n<!-- reingest: [^>]* -->\n?$", "", body) + f"\n<!-- reingest: {stamp} -->\n"
        s3.put_object(Bucket=bucket, Key=key, Body=body.encode(), ContentType="text/markdown")
    print(dim(f"  touched {len(keys)} docs so the next sync re-ingests all of them"))


def cmd_invoke(args):
    payload = {"action": args.action}
    if args.payload:
        payload.update(json.loads(args.payload))
    print(json.dumps(invoke(payload), indent=2, default=str))


def cmd_sql(args):
    try:
        rows = run_sql(args.statement, quiet=False)
    except ClientError as e:
        die(client_error(e))
    for r in rows:
        print(json.dumps(r, default=str))
    print(dim(f"({len(rows)} rows)"))


def cmd_env(_args):
    """Print `export NAME=value` lines:  eval "$(labctl env)" """
    L = lab()
    for key, value in L.items():
        print(f"export {key.upper()}={json.dumps(str(value))}")
    print(f"export AWS_REGION={json.dumps(L['region'])}")
    print(f"export AWS_DEFAULT_REGION={json.dumps(L['region'])}")


def cmd_mcp_json(args):
    servers = mcp_servers()
    if args.client == "vscode":
        cfg = {"servers": {k: {"type": "stdio", **v} for k, v in servers.items()}}
    else:
        cfg = {"mcpServers": servers}
    print(json.dumps(cfg, indent=2))


def main():
    p = argparse.ArgumentParser(prog="labctl", description="Operation Tangerine lab controller 🍊")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("env", help='print export lines: eval "$(labctl env)"').set_defaults(fn=cmd_env)

    s = sub.add_parser("db-setup")
    s.add_argument("steps", nargs="*", help="schema seed kb kb-rebuild indexes playground (default: schema seed)")
    s.set_defaults(fn=cmd_db_setup)

    sub.add_parser("embed-notes").set_defaults(fn=cmd_embed_notes)

    s = sub.add_parser("kb-sync")
    s.add_argument("--kb")
    s.add_argument("--data-source")
    s.add_argument("--full", action="store_true", help="force re-ingestion of every doc (after the table was recreated)")
    s.set_defaults(fn=cmd_kb_sync)

    s = sub.add_parser("invoke")
    s.add_argument("action")
    s.add_argument("payload", nargs="?")
    s.set_defaults(fn=cmd_invoke)

    s = sub.add_parser("sql")
    s.add_argument("statement")
    s.set_defaults(fn=cmd_sql)

    s = sub.add_parser("mcp-json")
    s.add_argument("--client", choices=["kiro", "claude", "q", "vscode"], default="kiro")
    s.set_defaults(fn=cmd_mcp_json)

    sub.add_parser("drills").set_defaults(fn=cmd_drills)

    s = sub.add_parser("break")
    s.add_argument("drill")
    s.set_defaults(fn=cmd_break)

    s = sub.add_parser("check")
    s.add_argument("drill")
    s.add_argument("--file", help="MCP config file to grade (mcp-config, mcp-pg, mcp-ddb)")
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser("hint")
    s.add_argument("drill")
    s.set_defaults(fn=cmd_hint)

    s = sub.add_parser("exam")
    s.add_argument("exam_cmd", choices=["start", "answer", "check"])
    s.add_argument("question", nargs="?", choices=["q1", "q2"])
    s.add_argument("value", nargs="?")
    s.add_argument("--file", help="MCP config file to grade")
    s.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    s.set_defaults(fn=cmd_exam)

    args = p.parse_args()
    if args.cmd == "exam" and args.exam_cmd == "answer" and not (args.question and args.value):
        die('usage: labctl exam answer q1 "<value>"')
    try:
        args.fn(args)
    except ClientError as e:
        die(client_error(e))
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
