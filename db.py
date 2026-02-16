"""Database connection and setup."""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import create_engine
from sqlalchemy.engine.base import Engine

from config import settings


def mysql_uri() -> str:
    """Build MySQL connection URI from settings."""
    return (
        f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
    )


_engine: Engine | None = None


def get_engine() -> Engine:
    """Get or create SQLAlchemy engine for deterministic SQL execution."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            mysql_uri(),
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=2,
        )
    return _engine


def execute_query(
    sql: str,
    params: dict[str, Any],
    timeout_sec: int,
    limit: int,
) -> tuple[list[str], list[list[Any]], list[str]]:
    """
    Execute parameterized SELECT with timeout and row limit.
    Returns (columns, rows, warnings). Rows may be truncated to limit.
    """
    engine = get_engine()
    warnings: list[str] = []
    with engine.connect() as conn:
        # MySQL: set statement timeout (ms). Some versions use max_execution_time.
        try:
            conn.execute(text("SET max_execution_time = :ms"), {"ms": timeout_sec * 1000})
        except Exception:
            pass  # older MySQL may not support; rely on app-level timeout if needed
        result = conn.execute(text(sql), params)
        columns = list(result.keys())
        rows_raw = result.fetchmany(limit + 1)
        if len(rows_raw) > limit:
            rows = [list(r) for r in rows_raw[:limit]]
            warnings.append("truncated_to_limit")
        else:
            rows = [list(r) for r in rows_raw]
    return columns, rows, warnings
