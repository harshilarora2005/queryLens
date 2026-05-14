import pytest
from core.sql_validator import validate


def test_select_passes():
    validate("SELECT * FROM `p.d.t` LIMIT 10")


@pytest.mark.parametrize("sql", [
    "DROP TABLE x",
    "delete from x where 1=1",
    "UPDATE x SET a=1",
    "TRUNCATE TABLE x",
    "INSERT INTO x VALUES (1)",
    "MERGE INTO x ...",
    "ALTER TABLE x ADD COLUMN c INT64",
    "CREATE TABLE x (a INT64)",
])
def test_destructive_blocked(sql):
    with pytest.raises(ValueError):
        validate(sql)
