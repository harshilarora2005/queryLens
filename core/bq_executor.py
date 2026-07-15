from __future__ import annotations

import pandas as pd
from dataclasses import dataclass
from google.cloud import bigquery
from config import settings
from core import rate_limiter
from google.oauth2 import service_account
import json
import os

_client = None

_PRICE_PER_TB = 5.0

def get_client() -> bigquery.Client:
    global _client

    if _client is None:
        project = settings.GCP_PROJECT_ID or None

        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")

        if service_account_json:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(service_account_json)
            )

            _client = bigquery.Client(
                project=project,
                credentials=credentials,
            )
        else:
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
        return self.gb < 1_000


class QueryTooExpensiveError(RuntimeError):
    """Raised when a query's estimated bytes processed exceeds the configured cap."""


def estimate_cost(sql: str) -> QueryCost:
    job_config = bigquery.QueryJobConfig(
        dry_run=True,
        use_query_cache=False,  
    )
    dry_run_job = get_client().query(sql, job_config=job_config)
    bytes_processed = dry_run_job.total_bytes_processed or 0
    estimated_usd = (bytes_processed / 1_000_000_000_000) * _PRICE_PER_TB
    return QueryCost(bytes_processed=bytes_processed, estimated_usd=estimated_usd)


def run_query(sql: str, max_bytes_billed: int | None = None) -> pd.DataFrame:
    cap = settings.MAX_BYTES_BILLED if max_bytes_billed is None else max_bytes_billed
    job_config = bigquery.QueryJobConfig(maximum_bytes_billed=cap)
    return get_client().query(sql, job_config=job_config).to_dataframe()


def estimate_and_run(sql: str) -> tuple[QueryCost, pd.DataFrame]:
    cost = estimate_cost(sql)

    if cost.bytes_processed > settings.MAX_BYTES_BILLED:
        raise QueryTooExpensiveError(
            f"This query would scan {cost.label()}, which exceeds the "
            f"configured cap of {settings.MAX_BYTES_BILLED / 1_000_000_000:.2f} GB. "
            "Try narrowing the date range or adding more filters."
        )

    rate_limiter.check_global_byte_budget(cost.bytes_processed)

    df = run_query(sql)
    rate_limiter.record_global_usage(cost.bytes_processed)
    return cost, df