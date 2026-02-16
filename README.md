# mcp-tool-sql

MCP server exposing **sql_query**: deterministic SQL tool (contract-first, no LLM SQL). Accepts SQLRequest JSON, returns SQLResponse (query, rows, metadata).

## Quick start

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` with `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`.

```bash
uvicorn main:app --reload --port 8000
```

**Health:**
```bash
curl http://localhost:8000/health
```

**Call tool (sql_query):**
```bash
curl -N -sS "http://localhost:8000/mcp/" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "sql_agent",
      "arguments": {
          "question": "List 5 job titles in Ventura",
          "request_id": "12345678",
          "session_id": "123456"
      }
    }
  }'
```

Response: `{ "data": SQLResponse (ok, query, columns, rows, row_count, elapsed_ms, warnings, fingerprint), "metadata": {...}, "error": null }`.

---

## Architecture (production)

Best-practice layering:

| Layer | Role |
|-------|------|
| **Orchestrator** (client/separate service) | Intent extraction (LLM) → SQLRequest JSON → call **sql_query** → explain + cite from rows |
| **sql_query** (MCP tool) | Validate request → build SQL from whitelist (no LLM) → execute with guardrails → return SQLResponse |

Pipeline:
```
Question → (Orchestrator) Intent → SQLRequest
    → (sql_query) validate → build SQL → execute → SQLResponse
    → (Orchestrator) explain + cite query/rows
```

- **SQLRequest** (input): `version`, `dataset`, `metrics` (name + agg), `dimensions`, `filters`, `limit`, `order_by`. Pydantic schema in `schemas.py`.
- **SQLResponse** (output): `ok`, `request_id`, `query`, `params`, `columns`, `rows`, `row_count`, `elapsed_ms`, `warnings`, `fingerprint`.
- **Guardrails**: SELECT-only, whitelisted tables/columns, LIMIT cap, timeout, parameterized queries only. Config: `sql_max_limit`, `sql_timeout_sec`, `sql_max_group_by`, `sql_max_filters`.

---

## Design

```
Client  →  POST /mcp/ (tools/call)  →  sql_query(SQLRequest)
       →  sql_runner.run_request()  →  MySQL
```

| Layer | Role |
|-------|------|
| **main.py** | FastAPI, MCP at `/mcp`, `sql_query` tool, `/health` |
| **schemas.py** | SQLRequest, SQLResponse (Pydantic) |
| **sql_builder.py** | Deterministic SQL from SQLRequest (whitelist only) |
| **sql_runner.py** | Execute with timeout, truncate, fingerprint → SQLResponse |
| **db.py** | MySQL URI, `get_engine()` / `execute_query()` |
| **config.py** | Settings + SQL guardrails (`sql_max_limit`, `sql_timeout_sec`, etc.) |

---

## Run

### Local
```bash
uvicorn main:app --reload --port 8000
```

### Docker
<!-- Build and run with .env; port 8000. -->
```bash
docker build -t mcp-server .
docker run -p 8000:8000 --env-file .env mcp-server
```

---

## Fly.io

<!-- Apps: mcp-tool-sql-v1-dev, mcp-tool-sql-v1-qa, mcp-tool-sql-v1-prod. -->
**Apps:** `mcp-tool-sql-v1-{dev|qa|prod}` · **URLs:** `https://mcp-tool-sql-v1-{env}.fly.dev`

### One-time setup
```bash
brew install flyctl
fly auth login
fly auth token   # → set as GitHub secret FLY_API_TOKEN for CI
```

### Create apps (once per env)
```bash
fly launch --name mcp-tool-sql-v1-dev
fly launch --name mcp-tool-sql-v1-qa
fly launch --name mcp-tool-sql-v1-prod
```

### Set secrets
<!-- Sync .env vars to Fly; use env_to_fly_secrets.sh if present. -->
Sync `.env` to an app (use script if present, or):
```bash
fly secrets set OPENAI_API_KEY=xxx MYSQL_HOST=xxx ... --app mcp-tool-sql-v1-dev
```

### Deploy
<!-- Manual deploy per app; CI deploys on push to main when FLY_API_TOKEN is set. -->
```bash
fly deploy --app mcp-tool-sql-v1-dev
```
Pushes to `main` auto-deploy via GitHub Actions when `FLY_API_TOKEN` is set.

### Call tool on Fly
Replace base URL with `https://mcp-tool-sql-v1-dev.fly.dev` in the curl example above.

### Fly health and tool (example)

**Health:**
```bash
curl https://mcp-tool-sql-v1-dev.fly.dev/health
```

**Call tool:**
```bash
curl -N -sS "https://mcp-tool-sql-v1-dev.fly.dev/mcp/" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "sql_agent",
      "arguments": {
          "question": "List 5 job titles in Ventura",
          "request_id": "12345678",
          "session_id": "123456"
      }
    }
  }'
```
