"""BigQuery query execution. Returns a pandas DataFrame."""
from __future__ import annotations

import os
import pandas as pd
from dataclasses import dataclass
from google.cloud import bigquery
from config import settings

if settings.GOOGLE_APPLICATION_CREDENTIALS:
    os.environ.setdefault(
        "GOOGLE_APPLICATION_CREDENTIALS", settings.GOOGLE_APPLICATION_CREDENTIALS
    )

_client: bigquery.Client | None = None

_PRICE_PER_TB = 5.0

def get_client() -> bigquery.Client:
    global _client
    if _client is None:
        project = settings.GCP_PROJECT_ID or None
        _client = bigquery.Client(project=project)
    return _client


@dataclass
class QueryCost:
    bytes_processed: int
    estimated_usd: float

    @property
    def mb(self) -> float:
        return self.bytes_processed / 1_000_000

    @property
    def gb(self) -> float:
        return self.bytes_processed / 1_000_000_000

    def label(self) -> str:
        """Human-readable size label."""
        if self.bytes_processed < 1_000_000:
            return f"{self.bytes_processed / 1_000:.1f} KB"
        if self.bytes_processed < 1_000_000_000:
            return f"{self.mb:.1f} MB"
        return f"{self.gb:.2f} GB"

    def cost_label(self) -> str:
        if self.estimated_usd < 0.01:
            return "< $0.01"
        return f"${self.estimated_usd:.4f}"

    def within_free_tier(self) -> bool:
        """BigQuery gives 1 TB/month free."""
        return self.gb < 1_000


def estimate_cost(sql: str) -> QueryCost:
    """Dry-run the SQL and return estimated bytes + cost. Does not execute."""
    job_config = bigquery.QueryJobConfig(
        dry_run=True,
        use_query_cache=False,   # force a fresh estimate every time
    )
    dry_run_job = get_client().query(sql, job_config=job_config)
    bytes_processed = dry_run_job.total_bytes_processed or 0
    estimated_usd = (bytes_processed / 1_000_000_000_000) * _PRICE_PER_TB
    return QueryCost(bytes_processed=bytes_processed, estimated_usd=estimated_usd)


def run_query(sql: str) -> pd.DataFrame:
    """Execute validated SQL and return a DataFrame. Raises on error."""
    return get_client().query(sql).to_dataframe()


def estimate_and_run(sql: str) -> tuple[QueryCost, pd.DataFrame]:
    """Dry-run for cost, then execute. Returns (cost, dataframe)."""
    cost = estimate_cost(sql)
    df = run_query(sql)
    return cost, df