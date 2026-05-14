"""Blocks destructive SQL before execution."""
import re

BLOCKED = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|UPDATE|INSERT|MERGE|ALTER|CREATE)\b",
    re.IGNORECASE,
)


def validate(sql: str) -> None:
    if BLOCKED.search(sql):
        raise ValueError("Destructive SQL blocked by validator")
