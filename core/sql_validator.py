from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

_DISALLOWED_NODE_TYPES = (
    exp.Drop,
    exp.Delete,
    exp.Update,
    exp.Insert,
    exp.Merge,
    exp.Alter,
    exp.Create,
    exp.TruncateTable,
    exp.Command,
    exp.Grant,
)

_ALLOWED_ROOT_TYPES = (
    exp.Select,
    exp.Union,
    exp.Intersect,
    exp.Except,
)


class SQLValidationError(ValueError):
    """Raised when a query does not pass validation."""

def validate(sql: str) -> None:
    sql = sql.strip().rstrip(";")
    if not sql:
        raise SQLValidationError("Empty SQL.")

    try:
        parsed = sqlglot.parse(sql, read="bigquery")
    except ParseError as e:
        raise SQLValidationError(f"SQL failed to parse: {e}") from e

    statements = [stmt for stmt in parsed if stmt is not None]

    if not statements:
        raise SQLValidationError("No valid SQL statement found.")

    if len(statements) > 1:
        raise SQLValidationError(
            f"Multiple statements are not allowed ({len(statements)} found). "
            "Only a single SELECT query is permitted."
        )

    root = statements[0]

    if not isinstance(root, _ALLOWED_ROOT_TYPES):
        raise SQLValidationError(
            f"Only SELECT queries are allowed. Got: {type(root).__name__}"
        )

    for node in root.walk():
        current = node[0] if isinstance(node, tuple) else node

        if isinstance(current, _DISALLOWED_NODE_TYPES):
            raise SQLValidationError(
                f"Disallowed statement type found in query: {type(current).__name__}"
            )