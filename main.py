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
    SELECT from whitelist, executes with guardrails, returns evidence (query, rows, metadata).
    No LLM-generated SQL. Orchestrator should call this with machine-produced SQLRequest.
    Response: { data: SQLResponse | null, metadata: { sql }, error: string | null }
    """
    request_id = args.request_id or str(uuid.uuid4())

    try:
        req = SQLRequest.model_validate(args.request)
        resp = await asyncio.to_thread(run_request, req, request_id)
        return {"data": resp.model_dump(), "metadata": _metadata(resp.query), "error": None}
    except Exception as e:
        return {"data": None, "metadata": _metadata(), "error": f"{type(e).__name__}: {e}"}


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
