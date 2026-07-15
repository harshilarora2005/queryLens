from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

_root = Path(__file__).parent.parent
load_dotenv(_root / ".env")
load_dotenv(_root / "config" / ".env") 


def require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(
            f"Missing required environment variable: {key}\n"
        )
    return val


def get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


GCP_PROJECT_ID: str = get("GCP_PROJECT_ID", "")


BQ_SOURCE_PROJECT: str = get("BQ_SOURCE_PROJECT", "bigquery-public-data")


BQ_DATASET: str = get("BQ_DATASET", "thelook_ecommerce")
GOOGLE_APPLICATION_CREDENTIALS: str = get(
    "GOOGLE_APPLICATION_CREDENTIALS", "credentials/bq_key.json"
)

LLM_PROVIDER: str = get("LLM_PROVIDER", "openai").lower()
MEMORY_TURNS: int = int(get("MEMORY_TURNS", "4"))

MAX_BYTES_BILLED: int = int(get("MAX_BYTES_BILLED", str(1_000_000_000)))

SESSION_MAX_QUERIES: int = int(get("SESSION_MAX_QUERIES", "20"))
SESSION_WINDOW_MINUTES: int = int(get("SESSION_WINDOW_MINUTES", "60"))

GLOBAL_MAX_QUERIES_PER_DAY: int = int(get("GLOBAL_MAX_QUERIES_PER_DAY", "300"))
GLOBAL_MAX_BYTES_PER_DAY: int = int(get("GLOBAL_MAX_BYTES_PER_DAY", str(5_000_000_000)))

OPENAI_API_KEY: str = get("OPENAI_API_KEY")
OPENAI_MODEL: str = get("OPENAI_MODEL", "gpt-4o-mini")

GEMINI_API_KEY: str = get("GEMINI_API_KEY")
GEMINI_MODEL: str = get("GEMINI_MODEL", "gemini-1.5-flash")