"""Execute validated SQL with timeout, truncation, fingerprint. Returns SQLResponse."""
from __future__ import annotations

import hashlib
import json
import time

from config import settings
from db import execute_query
from schemas import SQLRequest, SQLResponse
from sql_builder import build_sql


def _fingerprint(query: str, params: dict) -> str:
    """Stable hash for cache and audit."""
    payload = json.dumps({"query": query, "params": params}, sort_keys=True)
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def run_request(req: SQLRequest, request_id: str | None = None) -> SQLResponse:
    """
    Validate → build SQL → execute with guardrails → return SQLResponse.
    SELECT-only, parameterized, timeout and limit enforced.
    """
    start = time.perf_counter()
    try:
        sql, params, build_warnings = build_sql(req)
    except ValueError as e:
        return SQLResponse(
            ok=False,
            request_id=request_id,
            query="",
            params={},
            columns=[],
            rows=[],
            row_count=0,
            elapsed_ms=int((time.perf_counter() - start) * 1000),
            warnings=[str(e)],
            fingerprint=None,
        )

    limit = min(req.limit, settings.sql_max_limit)
    try:
        columns, rows, run_warnings = execute_query(
            sql, params, timeout_sec=settings.sql_timeout_sec, limit=limit
        )
    except Exception as e:
        return SQLResponse(
            ok=False,
            request_id=request_id,
            query=sql,
            params=params,
            columns=[],
            rows=[],
            row_count=0,
            elapsed_ms=int((time.perf_counter() - start) * 1000),
            warnings=[f"execution_error: {e}"],
            fingerprint=_fingerprint(sql, params),
        )

    all_warnings = build_warnings + run_warnings
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    return SQLResponse(
        ok=True,
        request_id=request_id,
        query=sql,
        params=params,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        elapsed_ms=elapsed_ms,
        warnings=all_warnings if all_warnings else [],
        fingerprint=_fingerprint(sql, params),
    )
