"""FastAPI + MCP server."""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from mcp.server.fastmcp import Context, FastMCP
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


@mcp.tool()
async def sql_agent(
    args: SqlAgentArgs,
    ctx: Optional[Context] = None,
) -> dict:
    """
    MCP tool: SQL agent that answers natural language questions using SQL.

    Response envelope:
    {
      data: { question, answer } | null,
      metadata: { version },
      error: string | null
    }
    """

    try:
        question = args.question
        answer = answer_question(question)
        return {
            "data": {"question": question, "answer": answer},
            "metadata": {"version": settings.app_version},
            "error": None,
        }
    except Exception as e:
        return {
            "data": None,
            "metadata": {"version": settings.app_version},
            "error": f"{type(e).__name__}: {e}",
        }


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
