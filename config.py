"""Configuration and environment settings."""
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv(override=True)


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


class Settings:
    """Single source for all app configuration."""

    # MySQL
    mysql_host: str = _env("MYSQL_HOST", "")
    mysql_port: int = int(_env("MYSQL_PORT", "3306"))
    mysql_user: str = _env("MYSQL_USER", "")
    mysql_password: str = _env("MYSQL_PASSWORD", "")
    mysql_database: str = _env("MYSQL_DATABASE", "")

    # OpenAI
    openai_api_key: str = _env("OPENAI_API_KEY", "")
    openai_model: str = _env("OPENAI_MODEL", "gpt-4o-mini")
    openai_temperature: float = float(_env("OPENAI_TEMPERATURE", "0"))

    # App & MCP
    db_name: str = _env("DB_NAME", "hunter")
    app_version: str = _env("APP_VERSION", "v:1.0")
    mcp_name: str = _env("MCP_NAME", "mcp-sql-agent")

    # Optional (health / future use)
    langchain_project: str = _env("LANGCHAIN_PROJECT", "")

    # Constants
    allowed_tables = None  # None = all tables
    default_limit: int = 10

    # SQL tool guardrails (hard enforcement)
    sql_max_limit: int = 200
    sql_timeout_sec: int = 2
    sql_max_group_by: int = 4
    sql_max_filters: int = 20

    def require_openai_api_key(self) -> str:
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        return self.openai_api_key


settings = Settings()


# ----------------------------
# LangSmith config
# ----------------------------
def _langsmith_config(
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict:
    tags = [
        t
        for t in (
            f"app_version:{settings.app_version}" if getattr(settings, "app_version", None) else None,
            f"mcp_name:{settings.mcp_name}" if getattr(settings, "mcp_name", None) else None,
            f"request_id:{request_id}" if request_id is not None else None,
            f"session_id:{session_id}" if session_id is not None else None,
        )
        if t is not None
    ]
    metadata = {k: v for k, v in (("request_id", request_id), ("session_id", session_id)) if v is not None}
    out: Dict[str, Any] = {}
    out["run_name"] = settings.mcp_name
    if tags:
        out["tags"] = tags
    if metadata:
        out["metadata"] = metadata
    return out
