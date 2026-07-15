import pytest

from core.sql_validator import SQLValidationError, validate


def test_select_passes():
    validate("SELECT * FROM `p.d.t` LIMIT 10")


def test_cte_passes():
    validate("WITH a AS (SELECT * FROM `p.d.t`) SELECT * FROM a")


def test_union_passes():
    validate("SELECT * FROM `p.d.t` UNION ALL SELECT * FROM `p.d.t2`")


def test_string_literal_containing_keyword_passes():
    """A keyword inside a string literal must not trip the validator —
    this is exactly the case a regex blocklist gets wrong."""
    validate("SELECT * FROM `p.d.t` WHERE note = 'please DROP TABLE nicely'")


def test_sql_comment_containing_keyword_passes():
    validate("SELECT * FROM `p.d.t` -- DROP TABLE t, just kidding")


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE x",
        "delete from x where 1=1",
        "UPDATE x SET a=1",
        "TRUNCATE TABLE x",
        "INSERT INTO x VALUES (1)",
        "MERGE INTO x USING y ON x.id=y.id WHEN MATCHED THEN UPDATE SET a=1",
        "ALTER TABLE x ADD COLUMN c INT64",
        "CREATE TABLE x (a INT64)",
    ],
)
def test_destructive_root_statement_blocked(sql):
    with pytest.raises(SQLValidationError):
        validate(sql)


def test_multi_statement_injection_blocked():
    with pytest.raises(SQLValidationError):
        validate("SELECT 1; DROP TABLE x")


def test_multi_statement_both_benign_still_blocked():
    with pytest.raises(SQLValidationError):
        validate("SELECT * FROM `p.d.t`; SELECT * FROM `p.d.t2`")


def test_ddl_hidden_inside_cte_blocked():
    with pytest.raises(SQLValidationError):
        validate("WITH a AS (DELETE FROM `p.d.t` RETURNING *) SELECT * FROM a")


def test_empty_sql_blocked():
    with pytest.raises(SQLValidationError):
        validate("")
    with pytest.raises(SQLValidationError):
        validate("   ")


def test_unparseable_sql_blocked():
    with pytest.raises(SQLValidationError):
        validate("SELECT SELECT FROM FROM WHERE (((")
