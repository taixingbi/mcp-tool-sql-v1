"""Deterministic SQL builder. No LLM — request → validated, parameterized SELECT only."""
from __future__ import annotations

from typing import Any

from config import settings
from schemas import (
    AggOp,
    OrderBySpec,
    SQLRequest,
    SQLRequestFilters,
)


# Whitelisted datasets and their allowed columns/expressions.
# Only these can appear in generated SQL.
ALLOWED_DATASETS: dict[str, dict[str, Any]] = {
    "gov_jobs": {
        # View: job_descriptions JOIN salaries ON jurisdiction AND code = job_code
        "base": "job_descriptions j JOIN salaries s ON j.jurisdiction = s.jurisdiction AND j.code = s.job_code",
        "columns": {"jurisdiction", "code", "title", "description", "job_code", "grade", "amount", "id"},
        "metrics": {"amount"},  # numeric columns that can be aggregated
        "dimensions": ["jurisdiction", "title", "grade", "job_code", "code"],
        "order_fields": ["jurisdiction", "title", "grade", "job_code", "code", "amount"],  # + agg aliases added at build
        "filter_column_map": {
            "location": "j.jurisdiction",
            "job_title_contains": "j.title",
            "year": None,  # no year column in current schema; ignore or add if present
        },
    },
}


def _validate_request(req: SQLRequest) -> list[str]:
    """Validate request against whitelist. Returns list of error messages."""
    errors: list[str] = []
    if req.dataset not in ALLOWED_DATASETS:
        errors.append(f"dataset not allowed: {req.dataset}")
        return errors

    cfg = ALLOWED_DATASETS[req.dataset]
    allowed_metrics = cfg["metrics"]
    allowed_dimensions = set(cfg["dimensions"])
    allowed_order = set(cfg["order_fields"])

    for m in req.metrics:
        if m.name not in allowed_metrics:
            errors.append(f"metric not allowed: {m.name}")
    if len(req.dimensions) > settings.sql_max_group_by:
        errors.append(f"max dimensions (group_by) is {settings.sql_max_group_by}")

    for d in req.dimensions:
        if d not in allowed_dimensions:
            errors.append(f"dimension not allowed: {d}")

    agg_aliases: set[str] = set()
    for m in req.metrics:
        alias = f"{m.agg}_{m.name}"
        agg_aliases.add(alias)
    for ob in req.order_by:
        if ob.field not in allowed_order and ob.field not in agg_aliases:
            errors.append(f"order_by field not allowed: {ob.field}")

    return errors


def _build_select_list(req: SQLRequest) -> tuple[list[str], list[str], dict[str, Any]]:
    """Build SELECT list (with agg), GROUP BY list, and params. Returns (select_parts, group_by_parts, params)."""
    params: dict[str, Any] = {}
    select_parts: list[str] = []
    group_by_parts: list[str] = []

    for m in req.metrics:
        col = m.name
        agg = m.agg.upper()
        alias = f"{m.agg}_{m.name}"
        if col == "amount":
            select_parts.append(f"{agg}(s.amount) AS {alias}")
        else:
            select_parts.append(f"{agg}({col}) AS {alias}")

    for d in req.dimensions:
        if d in ("jurisdiction", "code", "title"):
            select_parts.append(f"j.{d}")
            group_by_parts.append(f"j.{d}")
        elif d in ("job_code", "grade"):
            select_parts.append(f"s.{d}")
            group_by_parts.append(f"s.{d}")
        else:
            select_parts.append(d)
            group_by_parts.append(d)

    return select_parts, group_by_parts, params


def _build_where(req: SQLRequest, params: dict[str, Any]) -> list[str]:
    """Build WHERE clauses from filters; add to params. Returns list of SQL conditions."""
    conditions: list[str] = []
    if not req.filters:
        return conditions

    f = req.filters
    if f.location:
        placeholders = ", ".join([f":loc_{i}" for i in range(len(f.location))])
        conditions.append(f"j.jurisdiction IN ({placeholders})")
        for i, v in enumerate(f.location):
            params[f"loc_{i}"] = v

    if f.job_title_contains:
        or_parts = []
        for i, sub in enumerate(f.job_title_contains):
            key = f"title_like_{i}"
            params[key] = f"%{sub}%"
            or_parts.append(f"j.title LIKE :{key}")
        if or_parts:
            conditions.append("(" + " OR ".join(or_parts) + ")")

    if f.year is not None:
        if getattr(f.year, "gte", None) is not None:
            params["year_gte"] = f.year.gte
            conditions.append("1 = 1")  # no year column; skip or add if you have one
        if getattr(f.year, "lte", None) is not None:
            params["year_lte"] = f.year.lte

    return conditions


def build_sql(req: SQLRequest) -> tuple[str, dict[str, Any], list[str]]:
    """
    Build a single parameterized SELECT from SQLRequest.
    Returns (sql, params, warnings). Raises ValueError if validation fails.
    """
    errs = _validate_request(req)
    if errs:
        raise ValueError("; ".join(errs))

    limit = min(req.limit, settings.sql_max_limit)
    warnings: list[str] = []
    if req.limit > settings.sql_max_limit:
        warnings.append("truncated_to_limit")

    cfg = ALLOWED_DATASETS[req.dataset]
    base = cfg["base"]

    select_parts, group_by_parts, params = _build_select_list(req)
    where_parts = _build_where(req, params)

    sql_select = ", ".join(select_parts)
    sql_from = "FROM " + base
    sql_where = "WHERE " + " AND ".join(where_parts) if where_parts else ""
    sql_group = "GROUP BY " + ", ".join(group_by_parts) if group_by_parts else ""
    sql_order = ""
    if req.order_by:
        order_clauses = []
        for ob in req.order_by:
            order_clauses.append(f"{ob.field} {ob.dir.upper()}")
        sql_order = "ORDER BY " + ", ".join(order_clauses)
    sql_limit = f"LIMIT {limit}"

    parts = ["SELECT", sql_select, sql_from]
    if sql_where:
        parts.append(sql_where)
    if sql_group:
        parts.append(sql_group)
    if sql_order:
        parts.append(sql_order)
    parts.append(sql_limit)

    sql = " ".join(parts)
    return sql, params, warnings
