from __future__ import annotations
import pandas as pd
import json
import re
from pathlib import Path
from config import settings
from core.llm_client import call_llm
from core.sql_validator import validate
from core.bq_executor import run_query

SCHEMA_PATH = Path("config/schema_metadata.json")
SCHEMA = json.loads(SCHEMA_PATH.read_text())

MAX_RETRIES = settings.MEMORY_TURNS;
HISTORY_CHAR_LIMIT = 2_000  


def _system_prompt() -> str:
    examples = "\n\n".join(
        f"Q: {ex['question']}\nSQL: {ex['sql']}"
        for ex in SCHEMA.get("few_shot_examples", [])
    )
    tables_json = json.dumps(SCHEMA["tables"], indent=2)
    return f"""You are a BigQuery SQL expert. Convert the user question to valid
BigQuery Standard SQL. Return ONLY the SQL query — no explanation, no markdown fences.

Rules:
- Use fully-qualified table names exactly as shown in the schema (e.g. `llm-analytics-dev.ecommerce.orders`).
- Use BigQuery Standard SQL dialect only.
- Never use DROP, DELETE, UPDATE, TRUNCATE, INSERT, MERGE, ALTER, or CREATE.
- Always include a LIMIT clause unless the query uses a top-level aggregation (GROUP BY or aggregate function without GROUP BY).
- Prefer DATE_TRUNC for time-series bucketing.
- Cast STRING timestamp columns with TIMESTAMP() or PARSE_TIMESTAMP before date operations.
- Return columns in a logical order: dimension first, then metrics.

Schema:
{tables_json}

Few-shot examples:
{examples}
"""


_FENCE = re.compile(r"^```(?:sql)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _clean(sql: str) -> str:
    return _FENCE.sub("", sql).strip().rstrip(";")


def _build_user_message(question: str, history: list[dict]) -> str:
    """Inject history with role labels; truncate to HISTORY_CHAR_LIMIT."""
    if not history:
        return question

    parts: list[str] = []
    total = 0
    for h in reversed(history[-MAX_RETRIES * 2:]):
        chunk = f"User: {h['q']}\nAssistant SQL: {h['sql']}\n"
        if total + len(chunk) > HISTORY_CHAR_LIMIT:
            break
        parts.append(chunk)
        total += len(chunk)

    prefix = "\n".join(reversed(parts))
    return f"{prefix}\nUser: {question}" if prefix else question


def generate_sql(question: str, history: list[dict] | None = None) -> str:
    """Returns a validated SQL string. Raises on failure."""
    user = _build_user_message(question, history or [])
    sql = _clean(call_llm(_system_prompt(), user))
    validate(sql)
    return sql


def generate_and_run(
    question: str, history: list[dict] | None = None
) -> tuple[str, "pd.DataFrame"]:  # noqa: F821
    """Generate SQL, run it, self-heal on BigQuery errors (up to MAX_RETRIES).

    Always returns (sql_string, dataframe) — sql_string is never None.
    Raises RuntimeError if all retries are exhausted.
    """
    sql = generate_sql(question, history)
    last_err: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            df = run_query(sql)
            return sql, df
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt == MAX_RETRIES:
                break
            fix_prompt = (
                f"The following BigQuery SQL failed with this error:\n"
                f"SQL:\n{sql}\n\nError: {e}\n\n"
                "Fix the SQL so it runs successfully. "
                "Return ONLY the corrected SQL, no explanation."
            )
            sql = _clean(call_llm(_system_prompt(), fix_prompt))
            validate(sql)

    raise RuntimeError(
        f"Query failed after {MAX_RETRIES} retries. "
        f"Last error: {last_err}"
    )