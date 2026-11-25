# 🍊 Operation Tangerine

A 4-day bootcamp to prepare for the **[AWS Databases for Agentic AI Demonstrated](https://skillbuilder.aws/learn/2MHE4K7STM/aws-databases-for-agentic-ai-demonstrated/NYCNC3CU6X)** exam lab on AWS Skill Builder. That exam is a 140-minute, hands-on lab in a live AWS account: you restore a broken AI customer-intelligence agent by fixing Aurora PostgreSQL, pgvector, DynamoDB, Bedrock Knowledge Bases, MCP servers and slow queries.

| Day | Theme | You learn |
|---|---|---|
| 1 | 🚀 Launch Pad | The agentic data layer, IAM, Secrets Manager, networking, Lambda, CloudWatch, the PEEL break-fix method |
| 2 | 🔐 The Vector Vault | Aurora Serverless v2 + Data API, embeddings, pgvector operators and HNSW/IVFFlat, Bedrock Knowledge Bases on Aurora |
| 3 | 🔌 Memory Lane & the MCP Bridge | DynamoDB agent memory, Aurora + DynamoDB MCP servers, EXPLAIN / pg_trgm / composite indexes |
| 4 | ⚡ Operation Tangerine | Drill Roulette, a triple-fault speedrun, and a graded 140-minute mock exam lab |

26 labs · 10 break-fix drills · 24 quiz questions · XP and ranks saved in the browser.

## Repository layout

```
docs/          GitHub Pages site (plain HTML/CSS/JS, no build step)
terraform/     The lab environment: Aurora PG Serverless v2 (Data API), DynamoDB, S3 docs,
               Lambda agent "Zest" (+ Anthropic SDK layer), IAM, CloudWatch dashboard,
               optional Bedrock Knowledge Base
  lambda/      agent.py: 10 actions (SQL tools, pgvector search, KB retrieval, memory, Claude agent loop)
  sample-docs/ Policy and product docs (+ .metadata.json sidecars) for the Knowledge Base
sql/           Schema, seed data (300k rows), KB vector store, index solutions, pgvector playground
labctl/        labctl.py: seeds data, injects faults, grades fixes, runs the mock exam
labs/mcp/      Where MCP configs are written during Day 3 / Day 4
```

## Quick start (students)

Prerequisites: an AWS **sandbox** account, AWS CLI v2, Terraform ≥ 1.6, Python 3.9+ with pip, `uv`/`uvx` (Day 3).
In the Bedrock console, turn on access to *Titan Text Embeddings V2* and the Claude model used by the agent.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars    # set region + student_id
terraform init && terraform apply               # ~15 min

cd ..
python3 -m pip install --user boto3     # or inside a venv
alias labctl="python3 $(pwd)/labctl/labctl.py"
eval "$(labctl env)"
labctl db-setup        # schema + seed data
labctl status          # everything ✔ except knowledge_base (built on Day 2)
```

Then open the site and start Day 1. Tear down with `terraform destroy` (delete any Knowledge Base you created in the console first).
Expect roughly $2–4 per day while the environment runs, mostly Aurora at 0.5 ACU.

## Publish the site with GitHub Pages

1. Push this repository to GitHub.
2. **Settings → Pages → Build and deployment → Source: Deploy from a branch**, branch `main`, folder **`/docs`**.
3. The site appears at `https://<user>.github.io/<repo>/` within a minute or two.

The site is static. Fonts load from Google Fonts and syntax highlighting from cdnjs (Prism 1.29.0). Progress, XP and the exam clock live in each visitor's `localStorage`.

To preview locally: `python3 -m http.server -d docs 8000`, then open http://localhost:8000.

## How the break-fix drills work

`labctl break <drill>` changes live AWS state on purpose: it edits IAM inline policies by statement `Sid`, edits Lambda env vars, switches the Data API off, or drops and reshapes database objects.
`labctl check <drill>` grades the result with the IAM policy simulator, `describe-*` calls, catalog queries, `EXPLAIN` plans and real agent invocations.
`labctl exam start` injects ten faults across all seven objectives. `labctl exam check` scores the seven challenges.

**Reset button:** `terraform apply` restores IAM, Lambda configuration and the Data API. `labctl db-setup schema seed kb-rebuild indexes` followed by `labctl kb-sync --full` restores the database and the Knowledge Base. Bedrock sync is incremental, so `--full` touches the docs to force a re-ingest. The setup page has a staged version that doesn't pre-solve later labs.

## Notes for instructors

- Run Lab 1.1's `terraform apply` early on Day 1. Module 2 (IAM) is timed to fill the Aurora build wait.
- Several students can share one account: give each a unique `student_id`.
- `enable_claude_agent = false` skips the Anthropic SDK layer (no local pip needed). Only the `ask` action needs it.
- The agent's `ask` action calls Claude in Amazon Bedrock with the Anthropic Python SDK (`AnthropicBedrockMantle`); the model ID is the `agent_model_id` variable. None of the exam objectives depend on it.
- MCP server flags and tool sets change between versions. Have students run `uvx awslabs.postgres-mcp-server@latest --help` and list tools with MCP Inspector.

---

Independent study material, not affiliated with or endorsed by AWS. Citrus & Co. and Zest are fictional.
