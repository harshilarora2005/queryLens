"""BigQuery query execution. Returns a pandas DataFrame."""
from __future__ import annotations

import os
import pandas as pd
from google.cloud import bigquery
from config import settings

if settings.GOOGLE_APPLICATION_CREDENTIALS:
    os.environ.setdefault(
        "GOOGLE_APPLICATION_CREDENTIALS", settings.GOOGLE_APPLICATION_CREDENTIALS
    )

_client: bigquery.Client | None = None


def get_client() -> bigquery.Client:
    global _client
    if _client is None:
        project = settings.GCP_PROJECT_ID or None  
        _client = bigquery.Client(project=project)
    return _client


def run_query(sql: str) -> pd.DataFrame:
    """Execute validated SQL and return a DataFrame. Raises on error."""
    return get_client().query(sql).to_dataframe()