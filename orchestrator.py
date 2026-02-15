"""Orchestrator: natural language question → SQLRequest (LLM) → for use with run_request."""
from __future__ import annotations

import json
import re

from langchain_openai import ChatOpenAI

from config import settings
from schemas import SQLRequest

_SYSTEM = """You convert natural language questions about job/salary data into a strict JSON request.

Dataset is "gov_jobs": job_descriptions (jurisdiction, code, title, description) joined with salaries (jurisdiction, job_code, grade, amount).

Output ONLY a single JSON object with this shape (no markdown, no explanation):
{
  "version": "v1",
  "dataset": "gov_jobs",
  "metrics": [{"name": "amount", "agg": "avg"}],
  "dimensions": ["jurisdiction", "title"],
  "filters": {"location": ["ventura"], "job_title_contains": null},
  "limit": 10,
  "order_by": []
}

Rules:
- metrics: always at least one; "name" must be "amount", "agg" one of: avg, min, max, sum, count.
- dimensions: optional list from: jurisdiction, title, grade, job_code, code.
- filters.location: list of jurisdiction names (e.g. ["ventura"], ["sanbernardino","sdcounty"]). Use lowercase.
- filters.job_title_contains: optional list of substrings to match in title (e.g. ["engineer"]).
- limit: integer 1-200; use 5 when user says "5 job titles" or "list 5".
- order_by: optional list of {"field": "avg_amount" or dimension name, "dir": "asc" or "desc"}.
- If the user asks for "job titles" or "list jobs", use dimensions ["jurisdiction", "title"] and a small limit.
- Infer location from phrases like "in Ventura" → location ["ventura"], "San Bernardino" → ["sanbernardino"]."""


def question_to_sql_request(question: str) -> SQLRequest:
    """Convert natural language question to SQLRequest using LLM. Raises on parse/validation error."""
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0,
        api_key=settings.require_openai_api_key(),
    )
    response = llm.invoke(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": question}]
    )
    text = (response.content or "").strip()
    # Strip optional markdown code block
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    raw = json.loads(text)
    return SQLRequest.model_validate(raw)
