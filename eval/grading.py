from __future__ import annotations

from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

AGG_FUNC_CLASSES = {
    "SUM": exp.Sum,
    "COUNT": exp.Count,
    "AVG": exp.Avg,
    "MAX": exp.Max,
    "MIN": exp.Min,
}


@dataclass
class GradeResult:
    passed: bool
    checks: dict[str, bool]
    notes: list[str] = field(default_factory=list)


def grade_sql(sql: str, spec: dict) -> GradeResult:
    checks: dict[str, bool] = {}
    notes: list[str] = []

    try:
        tree = sqlglot.parse_one(sql, read="bigquery")
    except Exception as e:
        return GradeResult(
            passed=False,
            checks={"parses": False},
            notes=[f"Failed to parse generated SQL: {e}"],
        )
    checks["parses"] = True

    full_refs: set[str] = set()
    for t in tree.find_all(exp.Table):
        parts = [p for p in (t.args.get("catalog"), t.args.get("db"), t.name) if p]
        full_refs.add(".".join(str(p).strip('"') for p in parts).lower())
        full_refs.add(str(t.name).strip('"').lower())

    required_tables = spec.get("required_tables", [])
    missing_tables = [
        t for t in required_tables
        if not any(t.lower() in ref for ref in full_refs)
    ]
    checks["required_tables_present"] = not missing_tables
    if missing_tables:
        notes.append(f"Missing expected table(s): {missing_tables}")

    column_refs = {str(c.name).strip('"').lower() for c in tree.find_all(exp.Column)}
    required_columns = spec.get("required_columns", [])
    missing_columns = [c for c in required_columns if c.lower() not in column_refs]
    checks["required_columns_present"] = not missing_columns
    if missing_columns:
        notes.append(f"Missing expected column(s): {missing_columns}")

    if spec.get("requires_join"):
        has_join = tree.find(exp.Join) is not None
        checks["join_present"] = has_join
        if not has_join:
            notes.append("Expected a JOIN, none found")

    if spec.get("requires_group_by"):
        has_group = tree.find(exp.Group) is not None
        checks["group_by_present"] = has_group
        if not has_group:
            notes.append("Expected GROUP BY, none found")

    if spec.get("requires_order_by"):
        has_order = tree.find(exp.Order) is not None
        checks["order_by_present"] = has_order
        if not has_order:
            notes.append("Expected ORDER BY, none found")

    if spec.get("requires_limit"):
        has_limit = tree.find(exp.Limit) is not None
        checks["limit_present"] = has_limit
        if not has_limit:
            notes.append("Expected LIMIT, none found")

    required_aggregations = spec.get("required_aggregations", [])
    if required_aggregations:
        found = {
            name for name, cls in _AGG_FUNC_CLASSES.items()
            if tree.find(cls) is not None
        }
        missing_agg = [a for a in required_aggregations if a not in found]
        checks["required_aggregations_present"] = not missing_agg
        if missing_agg:
            notes.append(f"Missing expected aggregation(s): {missing_agg}")

    passed = all(checks.values())
    return GradeResult(passed=passed, checks=checks, notes=notes)