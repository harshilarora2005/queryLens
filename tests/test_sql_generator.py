"""Smoke tests for sql_generator. Mocks the LLM and BigQuery layers."""
from unittest.mock import patch

import pandas as pd

from core import sql_generator


def test_generate_sql_strips_markdown_fences():
    fake = "```sql\nSELECT 1\n```"
    with patch.object(sql_generator, "call_llm", return_value=fake):
        assert sql_generator.generate_sql("ping") == "SELECT 1"


def test_generate_and_run_retries_on_error():
    sqls = iter(["SELECT bad", "SELECT 1"])

    def llm(system, user, temperature=0.0):
        return next(sqls)

    calls = {"n": 0}

    def run(sql):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("syntax error")
        return pd.DataFrame({"x": [1]})

    with patch.object(sql_generator, "call_llm", side_effect=llm), \
         patch.object(sql_generator, "run_query", side_effect=run):
        sql, df = sql_generator.generate_and_run("ping")
    assert sql == "SELECT 1"
    assert len(df) == 1
