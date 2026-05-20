"""NL question -> BigQuery SQL with self-healing retry loop."""
from __future__ import annotations

import json
import re
from pathlib import Path

from core.llm_client import call_llm
from core.sql_validator import validate
from core.bq_executor import run_query

SCHEMA_PATH = Path("config/schema_metadata.json")
SCHEMA = json.loads(SCHEMA_PATH.read_text())

MAX_RETRIES = 2


def _system_prompt() -> str:
    examples = "\n\n".join(
        f"Q: {ex['question']}\nSQL: {ex['sql']}"
        for ex in SCHEMA.get("few_shot_examples", [])
    )
    return f"""You are a BigQuery SQL expert. Convert the user question to valid
BigQuery Standard SQL. Return ONLY the SQL query, no explanation, no markdown.

Rules:
- Use fully-qualified table names exactly as shown in the schema.
- Use BigQuery Standard SQL dialect.
- Never use DROP, DELETE, UPDATE, TRUNCATE, INSERT, MERGE, ALTER, or CREATE.
- Always include a LIMIT clause unless an aggregation is performed.
- Prefer DATE_TRUNC for time bucketing.

Schema:
{json.dumps(SCHEMA['tables'], indent=2)}

Few-shot examples:
{examples}
"""


_FENCE = re.compile(r"^```(?:sql)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def _clean(sql: str) -> str:
    return _FENCE.sub("", sql).strip().rstrip(";")


def generate_sql(question: str, history: list[dict] | None = None) -> str:
    history = history or []
    convo = "\n".join(f"User: {h['q']}\nSQL: {h['sql']}" for h in history[-4:])
    user = f"{convo}\n\nUser: {question}" if convo else question

    sql = _clean(call_llm(_system_prompt(), user))
    validate(sql)
    return sql


def generate_and_run(question: str, history: list[dict] | None = None):
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
            fix_prompt = (
                f"The following BigQuery SQL failed:\n{sql}\n\n"
                f"Error: {e}\n\nReturn a corrected SQL query only."
            )
            sql = _clean(call_llm(_system_prompt(), fix_prompt))
            validate(sql)

    raise RuntimeError(f"SQL failed after {MAX_RETRIES} retries: {last_err}")
