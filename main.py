"""FastAPI + MCP server."""
import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

from agent import answer_question
from config import settings

mcp = FastMCP(
    settings.mcp_name,
    stateless_http=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    ),
)


class SqlAgentArgs(BaseModel):
    question: str = Field(..., description="Natural language question")
    request_id: Optional[str] = Field(None, description="Optional request id for tracing")
    session_id: Optional[str] = Field(None, description="Optional session id for correlation")


def _metadata(request_id: Optional[str], session_id: Optional[str]) -> dict:
    return {
        "version": settings.app_version,
        "request_id": request_id,
        "session_id": session_id,
    }


@mcp.tool()
async def sql_agent(args: SqlAgentArgs) -> dict:
    """
    MCP tool: SQL agent that answers natural language questions using SQL.

    Response envelope:
    {
      data: { question, answer } | null,
      metadata: { version, request_id, session_id },
      error: string | null
    }
    """
    request_id = args.request_id or str(uuid.uuid4())
    session_id = args.session_id
    meta = _metadata(request_id, session_id)

    try:
        question = args.question
        answer = await asyncio.to_thread(
            answer_question,
            question,
            request_id=request_id,
            session_id=session_id,
        )
        return {"data": {"question": question, "answer": answer}, "metadata": meta, "error": None}
    except Exception as e:
        return {"data": None, "metadata": meta, "error": f"{type(e).__name__}: {e}"}


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
