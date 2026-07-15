import json
from pathlib import Path

import pytest

from eval.grading import grade_sql


GOLDEN_SET_PATH = Path(__file__).parent.parent / "eval" / "golden_set.json"


def test_correct_sql_passes_full_spec():
    spec = {
        "required_tables": ["order_items", "products"],
        "required_columns": ["sale_price"],
        "requires_join": True,
        "requires_group_by": True,
        "requires_order_by": True,
        "requires_limit": True,
        "required_aggregations": ["SUM"],
    }
    sql = """
        SELECT p.category, SUM(oi.sale_price) AS revenue
        FROM `bigquery-public-data.thelook_ecommerce.order_items` oi
        JOIN `bigquery-public-data.thelook_ecommerce.products` p ON oi.product_id = p.id
        GROUP BY p.category
        ORDER BY revenue DESC
        LIMIT 5
    """
    result = grade_sql(sql, spec)
    assert result.passed, result.notes


def test_missing_join_fails_when_required():
    spec = {"required_tables": ["order_items"], "requires_join": True}
    sql = "SELECT * FROM `p.d.order_items`"
    result = grade_sql(sql, spec)
    assert not result.passed
    assert result.checks["join_present"] is False


def test_missing_group_by_fails_when_required():
    spec = {"required_tables": ["orders"], "requires_group_by": True}
    sql = "SELECT gender, COUNT(*) FROM `p.d.orders`"
    result = grade_sql(sql, spec)
    assert not result.passed
    assert result.checks["group_by_present"] is False


def test_wrong_table_fails():
    spec = {"required_tables": ["users"]}
    sql = "SELECT * FROM `p.d.orders`"
    result = grade_sql(sql, spec)
    assert not result.passed
    assert result.checks["required_tables_present"] is False


def test_missing_required_column_fails():
    spec = {"required_tables": ["orders"], "required_columns": ["gender"]}
    sql = "SELECT status FROM `p.d.orders`"
    result = grade_sql(sql, spec)
    assert not result.passed
    assert "gender" in result.notes[0]


def test_missing_aggregation_fails():
    spec = {"required_tables": ["orders"], "required_aggregations": ["SUM", "AVG"]}
    sql = "SELECT SUM(num_of_item) FROM `p.d.orders`"
    result = grade_sql(sql, spec)
    assert not result.passed
    assert result.checks["required_aggregations_present"] is False


def test_unparseable_sql_fails_immediately():
    spec = {"required_tables": ["orders"]}
    result = grade_sql("SELECT SELECT FROM FROM (((", spec)
    assert not result.passed
    assert result.checks == {"parses": False}


def test_qualified_and_unqualified_table_names_both_match():
    spec = {"required_tables": ["orders"]}
    for sql in [
        "SELECT * FROM orders",
        "SELECT * FROM `thelook_ecommerce.orders`",
        "SELECT * FROM `bigquery-public-data.thelook_ecommerce.orders`",
    ]:
        result = grade_sql(sql, spec)
        assert result.checks["required_tables_present"], f"Failed for: {sql}"


def test_minimal_spec_with_no_requirements_always_passes_if_parseable():
    spec = {}
    result = grade_sql("SELECT 1", spec)
    assert result.passed


def test_golden_set_loads_and_has_expected_shape():
    data = json.loads(GOLDEN_SET_PATH.read_text())
    assert "questions" in data
    assert len(data["questions"]) >= 15


def test_golden_set_all_ids_unique():
    data = json.loads(GOLDEN_SET_PATH.read_text())
    ids = [q["id"] for q in data["questions"]]
    assert len(ids) == len(set(ids)), "Duplicate ids in golden_set.json"


def test_golden_set_every_question_has_required_fields():
    data = json.loads(GOLDEN_SET_PATH.read_text())
    for q in data["questions"]:
        assert "id" in q
        assert "question" in q and q["question"].strip()
        gradable_keys = [
            "required_tables", "required_columns", "requires_join",
            "requires_group_by", "requires_order_by", "requires_limit",
            "required_aggregations",
        ]
        assert any(q.get(k) for k in gradable_keys), (
            f"Question {q['id']!r} has no gradable criteria"
        )