## End-to-End Flow (LLM → Guardrails → Deterministic SQL)

This project follows a **contract-first architecture** where the LLM is used only for
**intent parsing**, while SQL generation and execution remain fully deterministic
and validated.

### Sequence Overview

1. **User Question → Orchestrator**

   * A natural-language question is received from the client/UI.

2. **Orchestrator → LLM (JSON-only Prompt)**

   * The LLM is instructed to return **ONLY a structured JSON object** (`SQLRequest`).
   * The model is **not allowed to generate SQL**.
   * This step converts human intent into a machine-validated query plan.

3. **Schema Validation (Pydantic)**

   * The Orchestrator validates the LLM output using:

   ```python
   SQLRequest.model_validate(llm_output)
   ```

   * Any malformed or hallucinated structure is rejected before reaching the database.

4. **MCP SQL Tool Guardrail Validation**
   The tool enforces strict allow-lists:

   * ✅ Allowed dataset(s)
   * ✅ Allowed metrics
   * ✅ Allowed dimensions
   * ✅ Allowed `order_by` fields
   * ✅ Maximum `GROUP BY` width
   * ✅ Hard row `LIMIT` caps

   This guarantees that only pre-approved analytical queries can run.

5. **Deterministic SQL Builder**

   * The tool converts `SQLRequest` → SQL using a **pure function** (`build_sql`).
   * No LLM involvement.
   * Queries are:

     * `SELECT`-only
     * Fully parameterized
     * Injection-safe
     * Predictable and testable

6. **Safe Execution Layer**

   * Query executes with:

     * Timeout protection
     * Row-limit enforcement
     * Structured result capture

   The tool returns a **SQLResponse** containing evidence:

   ```json
   {
     "ok": true,
     "query": "...",
     "params": {...},
     "columns": [...],
     "rows": [...],
     "row_count": 5,
     "elapsed_ms": 42
   }
   ```

7. **Orchestrator → Final Answer (Grounded)**

   * The Orchestrator formats a human-readable answer
     **strictly based on returned rows**.
   * Responses can cite:

     * Executed SQL
     * Returned data
     * Row counts / aggregations

---

## Why This Architecture?

| Concern            | Traditional LLM-SQL | This Project    |
| ------------------ | ------------------- | --------------- |
| Hallucinated SQL   | ❌ Common            | ✅ Impossible    |
| SQL Injection Risk | ❌ Possible          | ✅ Eliminated    |
| Observability      | ❌ Weak              | ✅ Full Evidence |
| Determinism        | ❌ No                | ✅ Yes           |
| Production Safety  | ❌ Risky             | ✅ Guardrailed   |

---

## Design Principle

> **LLM decides *what you want*.
> Code decides *what is allowed*.**

The LLM translates language → intent.
The MCP tool enforces policy → builds SQL → executes safely.

---

## Result

This separation enables:

* Production-grade reliability
* Auditable analytics workflows
* Explainable answers grounded in data
* Safe integration of LLM reasoning without giving it database control

---

## Simplified Sequence Diagram

```
User Question
      ↓
LLM (Intent Only)
      ↓
Validated SQLRequest
      ↓
Guardrails + Whitelists
      ↓
Deterministic SQL Builder
      ↓
Safe Execution
      ↓
Evidence (SQLResponse)
      ↓
Grounded Answer
```
