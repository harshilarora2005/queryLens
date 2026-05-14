"""BigQuery query execution. Returns a pandas DataFrame."""
from __future__ import annotations

import os
import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv("config/.env")

_client: bigquery.Client | None = None


def get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=os.environ["GCP_PROJECT_ID"])
    return _client


def run_query(sql: str) -> pd.DataFrame:
    return get_client().query(sql).to_dataframe()
