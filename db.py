"""Database connection and setup."""
from langchain_community.utilities import SQLDatabase

from config import settings


def mysql_uri() -> str:
    """Build MySQL connection URI from settings."""
    return (
        f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
    )


def get_database() -> SQLDatabase:
    """Create and return SQLDatabase instance."""
    return SQLDatabase.from_uri(mysql_uri(), include_tables=settings.allowed_tables)
