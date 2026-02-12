"""Configuration and environment settings."""
import os
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

    def require_openai_api_key(self) -> str:
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        return self.openai_api_key


settings = Settings()
