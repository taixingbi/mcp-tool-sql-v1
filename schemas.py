"""Contract-first API: strict JSON schemas for SQL tool input/output."""
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# SQLRequest (input) — machine-checkable, stable
# ---------------------------------------------------------------------------

AggOp = Literal["avg", "min", "max", "sum", "count"]


class MetricSpec(BaseModel):
    """Aggregation over a numeric column."""
    name: str = Field(..., description="Column or metric name (e.g. base_salary, amount)")
    agg: AggOp = Field(..., description="Aggregation: avg, min, max, sum, count")


class OrderBySpec(BaseModel):
    """Sort by a field (must be in allowed list)."""
    field: str = Field(..., description="Column or computed alias to order by")
    dir: Literal["asc", "desc"] = Field("desc", description="Sort direction")


class NumericRange(BaseModel):
    """Numeric filter: gte/lte (inclusive)."""
    gte: int | float | None = None
    lte: int | float | None = None


class SQLRequestFilters(BaseModel):
    """Structured filters; keys and value shapes validated against dataset."""
    location: list[str] | None = Field(None, description="e.g. jurisdiction / location codes")
    job_title_contains: list[str] | None = Field(None, description="Substrings for job title")
    year: NumericRange | None = None
    # Extensible: add more as needed per dataset
    extra: dict[str, Any] | None = None


class SQLRequest(BaseModel):
    """Strict input schema for the SQL MCP tool. Orchestrator produces this."""
    version: str = Field("v1", description="Schema version")
    dataset: str = Field(..., description="Whitelisted dataset / view name (e.g. gov_jobs)")
    metrics: list[MetricSpec] = Field(..., min_length=1, max_length=8)
    dimensions: list[str] = Field(default_factory=list, max_length=8)
    filters: SQLRequestFilters | None = None
    limit: int = Field(100, ge=1, le=500, description="Max rows (capped by server)")
    order_by: list[OrderBySpec] = Field(default_factory=list, max_length=4)


# ---------------------------------------------------------------------------
# SQLResponse (output) — evidence, not prose
# ---------------------------------------------------------------------------

class SQLResponse(BaseModel):
    """Structured result: query, params, rows, metadata. No free-form prose."""
    ok: bool = Field(..., description="Whether the query ran successfully")
    request_id: str | None = Field(None, description="Request id for tracing")
    query: str = Field("", description="Executed SQL (parameterized form)")
    params: dict[str, Any] = Field(default_factory=dict, description="Bound parameters")
    columns: list[str] = Field(default_factory=list, description="Result column names")
    rows: list[list[Any]] = Field(default_factory=list, description="Result rows (list of lists)")
    row_count: int = Field(0, description="Number of rows returned")
    elapsed_ms: int = Field(0, description="Execution time in milliseconds")
    warnings: list[str] = Field(default_factory=list, description="e.g. truncated_to_limit")
    fingerprint: str | None = Field(None, description="sha256 of query+params for cache/audit")
