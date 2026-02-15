# mcp-tool-sql

<!-- MCP server: one tool (sql_agent) that answers natural-language questions by running SQL via LangChain + OpenAI on MySQL. -->

MCP server that exposes a LangChain SQL agent as a tool. Query MySQL using natural language.

## Quick start

<!-- Install deps and run server; .env holds OpenAI + MySQL credentials. -->

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` with `OPENAI_API_KEY`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`.

```bash
uvicorn main:app --reload --port 8000
```

**Health:** `curl http://localhost:8000/health`

<!-- JSON-RPC tools/call with args.question; no trailing commas in JSON. -->
**Call tool:**
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
      "args": {
          "question": "List 5 job titles in Ventura",
          "request_id": "12345678",
          "session_id": "123456"
      }
    }
  }
}'
```

Response shape: `{ "data": { "question", "answer" }, "metadata": { "version" }, "error": null }`.

---

## Design

<!-- Request path: client → FastAPI /mcp → MCP sql_agent → agent.answer_question → LangChain agent + MySQL. -->

```
Client (curl/IDE)  →  POST /mcp/ (JSON-RPC tools/call)  →  sql_agent(question)
       →  LangChain SQL Agent  →  ChatOpenAI  →  MySQL  →  answer
```

| Layer | Role |
|-------|------|
| **main.py** | FastAPI app, MCP at `/mcp`, `sql_agent` tool, `/health` |
| **agent.py** | LangChain SQL agent, `answer_question(question)` |
| **db.py** | MySQL URI, `get_database()` (SQLDatabase) |
| **config.py** | Settings from env (OpenAI, MySQL, app version, etc.) |

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
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"sql_agent","arguments":{"args":{"question":"List 5 job titles in Ventura"}}}}'
```
