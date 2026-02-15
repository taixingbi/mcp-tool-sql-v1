"""FastAPI + MCP server. Production: deterministic sql_query tool (contract-first, no LLM SQL)."""
import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

from config import settings
from orchestrator import question_to_sql_request
from schemas import SQLRequest
from sql_runner import run_request

mcp = FastMCP(
    settings.mcp_name,
    stateless_http=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    ),
)


def _format_answer(columns: list, rows: list[list]) -> str:
    """Format columns and rows as a short text answer."""
    if not rows:
        return "No results found."
    lines = []
    for i, row in enumerate(rows[:20], 1):
        parts = [f"{col}={row[j]}" for j, col in enumerate(columns)]
        lines.append(f"{i}. " + ", ".join(parts))
    if len(rows) > 20:
        lines.append(f"... and {len(rows) - 20} more.")
    return "\n".join(lines)


def _envelope(
    question: str,
    answer: str,
    sql: str | None,
    metadata_extra: dict,
    error: str | None = None,
) -> dict:
    """Response envelope: metadata (everything else), error, data (question, answer)."""
    metadata = {"sql": sql or "", **metadata_extra}
    return {
        "metadata": metadata,
        "error": error,
        "data": {"question": question, "answer": answer} if error is None else None,
    }


def _metadata(sql: str | None = None) -> dict:
    return {"sql": sql or ""}


# ---------------------------------------------------------------------------
# Production: deterministic SQL tool (contract-first, no LLM SQL)
# ---------------------------------------------------------------------------


class SqlQueryArgs(BaseModel):
    """Input for sql_query: structured SQLRequest from orchestrator."""
    request: dict = Field(..., description="SQLRequest JSON: dataset, metrics, dimensions, filters, limit, order_by")
    request_id: Optional[str] = Field(None, description="Optional request id for tracing")
    session_id: Optional[str] = Field(None, description="Optional session id for correlation")


@mcp.tool()
async def sql_query(args: SqlQueryArgs) -> dict:
    """
    MCP tool: deterministic SQL. Accepts SQLRequest (structured intent), builds parameterized
    SELECT from whitelist, executes with guardrails.
    Response: { metadata: { sql, ... }, error: null, data: { question, answer } }
    """
    request_id = args.request_id or str(uuid.uuid4())
    question = f"Structured query: dataset={args.request.get('dataset', '')}"

    try:
        req = SQLRequest.model_validate(args.request)
        resp = await asyncio.to_thread(run_request, req, request_id)
        answer = _format_answer(resp.columns, resp.rows) if resp.ok else "No results."
        extra = {"version": settings.app_version, "request_id": request_id, **resp.model_dump()}
        return _envelope(question, answer, resp.query, extra, error=None)
    except Exception as e:
        return _envelope(question, "", None, {"version": settings.app_version, "request_id": request_id}, error=f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# sql_agent: question → LLM intent → SQLRequest → run_request (same envelope)
# ---------------------------------------------------------------------------


class SqlAgentArgs(BaseModel):
    question: str = Field(..., description="Natural language question (e.g. List 5 job titles in Ventura)")
    request_id: Optional[str] = Field(None, description="Optional request id for tracing")
    session_id: Optional[str] = Field(None, description="Optional session id for correlation")


@mcp.tool()
async def sql_agent(args: SqlAgentArgs) -> dict:
    """
    MCP tool: natural language question → LLM intent (SQLRequest) → deterministic SQL.
    Input must include "question". Response: { metadata: { sql, ... }, error: null, data: { question, answer } }
    """
    request_id = args.request_id or str(uuid.uuid4())
    question = args.question

    try:
        req = await asyncio.to_thread(question_to_sql_request, args.question)
        resp = await asyncio.to_thread(run_request, req, request_id)
        answer = _format_answer(resp.columns, resp.rows) if resp.ok else "No results."
        extra = {"version": settings.app_version, "request_id": request_id, **resp.model_dump()}
        return _envelope(question, answer, resp.query, extra, error=None)
    except Exception as e:
        return _envelope(question, "", None, {"version": settings.app_version, "request_id": request_id}, error=f"{type(e).__name__}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],
)
app.mount("/mcp", mcp.streamable_http_app())


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mcp": settings.mcp_name,
        "version": settings.app_version,
        "langchain_project": settings.langchain_project,
        "mysql_database": settings.mysql_database,
        "mysql_user": settings.mysql_user,
    }
