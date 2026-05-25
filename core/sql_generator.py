from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from config import settings
from core.bq_executor import run_query
from core.llm_client import call_llm
from core.sql_validator import validate

SCHEMA_PATH = Path("config/schema_metadata.json")
SCHEMA = json.loads(SCHEMA_PATH.read_text())

MAX_RETRIES = 2              
HISTORY_TURNS = settings.MEMORY_TURNS
HISTORY_CHAR_LIMIT = 2_000

_ERROR_HINTS: list[tuple[re.Pattern, str]] = [
    (
        re.compile(r"PARSE_TIMESTAMP", re.I),
        "PARSE_TIMESTAMP requires 2 args: PARSE_TIMESTAMP(format, col). "
        "Prefer TIMESTAMP(col) instead — it handles the stored format automatically.",
    ),
    (
        re.compile(r"unrecognized name", re.I),
        "A column name is wrong. Cross-check every column name against the schema exactly.",
    ),
    (
        re.compile(r"no matching signature for function", re.I),
        "A function is called with the wrong argument types or count. "
        "Check the BigQuery Standard SQL function reference.",
    ),
    (
        re.compile(r"not found: table", re.I),
        "A table name is wrong. Use the exact fully-qualified names from the schema.",
    ),
    (
        re.compile(r"syntax error", re.I),
        "There is a SQL syntax error. Check for missing commas, unmatched parentheses, "
        "or invalid keywords.",
    ),
]


def _get_error_hint(error: str) -> str:
    for pattern, hint in _ERROR_HINTS:
        if pattern.search(error):
            return hint
    return "Fix the SQL so it runs successfully in BigQuery Standard SQL."


def _system_prompt() -> str:
    examples = "\n\n".join(
        f"Q: {ex['question']}\nSQL: {ex['sql']}"
        for ex in SCHEMA.get("few_shot_examples", [])
    )
    return f"""You are a BigQuery SQL expert. Convert the user question to valid
BigQuery Standard SQL. Return ONLY the SQL query — no explanation, no markdown fences.

Rules:
- Use fully-qualified table names exactly as shown in the schema.
- Use BigQuery Standard SQL dialect only.
- Never use DROP, DELETE, UPDATE, TRUNCATE, INSERT, MERGE, ALTER, or CREATE.
- Always include a LIMIT clause unless the query has a top-level aggregation.
- Prefer DATE_TRUNC for time-series bucketing.
- Return columns in a logical order: dimensions first, then metrics.

Timestamp handling (CRITICAL):
- Timestamp columns (created_at, returned_at, shipped_at, delivered_at) are stored
  as STRING in the format '2023-03-15 14:22:00+00:00'.
- Cast them with TIMESTAMP(col) before any date operation:
    DATE(TIMESTAMP(created_at))
    EXTRACT(YEAR FROM TIMESTAMP(created_at))
    DATE_TRUNC(DATE(TIMESTAMP(created_at)), MONTH)
- NEVER call PARSE_TIMESTAMP with one argument — it requires two:
    PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%E*S%Ez', created_at)
  But prefer TIMESTAMP(col) — it's simpler and handles the stored format.
- Date range filter: DATE(TIMESTAMP(created_at)) BETWEEN '2023-01-01' AND '2023-12-31'

Schema:
{json.dumps(SCHEMA["tables"], indent=2)}

Few-shot examples:
{examples}
"""


_FENCE = re.compile(r"^```(?:sql)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _clean(sql: str) -> str:
    return _FENCE.sub("", sql).strip().rstrip(";")


def _build_user_message(question: str, history: list[dict]) -> str:
    """Inject conversation history with char-budget trimming."""
    if not history:
        return question

    parts: list[str] = []
    total = 0
    for h in reversed(history[-HISTORY_TURNS:]):
        chunk = f"User: {h['q']}\nAssistant SQL: {h['sql']}\n"
        if total + len(chunk) > HISTORY_CHAR_LIMIT:
            break
        parts.append(chunk)
        total += len(chunk)

    prefix = "\n".join(reversed(parts))
    return f"{prefix}\nUser: {question}" if prefix else question


def generate_sql(question: str, history: list[dict] | None = None) -> str:
    """Generate and validate SQL. Raises on failure."""
    user = _build_user_message(question, history or [])
    sql = _clean(call_llm(_system_prompt(), user))
    validate(sql)
    return sql


def generate_and_run(
    question: str,
    history: list[dict] | None = None,
) -> tuple[str, pd.DataFrame]:
    """Generate SQL, execute it, self-heal on BigQuery errors up to MAX_RETRIES.

    Returns (sql_string, dataframe). Raises RuntimeError if all retries exhausted.
    """
    sql = generate_sql(question, history)
    last_err: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            df = run_query(sql)
            return sql, df
        except Exception as e:
            last_err = e
            if attempt == MAX_RETRIES:
                break

            # Pattern-match the error to give the LLM a targeted hint
            hint = _get_error_hint(str(e))
            fix_prompt = (
                f"The following BigQuery SQL failed:\n\n"
                f"SQL:\n{sql}\n\n"
                f"Error: {e}\n\n"
                f"Hint: {hint}\n\n"
                "Return ONLY the corrected SQL, no explanation."
            )
            sql = _clean(call_llm(_system_prompt(), fix_prompt))
            validate(sql)

    raise RuntimeError(
        f"Query failed after {MAX_RETRIES} retries. Last error: {last_err}"
    )