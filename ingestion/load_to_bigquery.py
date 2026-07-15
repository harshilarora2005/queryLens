"""Load processed CSVs into your own BigQuery dataset.

Only needed if you don't want to use the public bigquery-public-data dataset.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv("config/.env")

PROJECT = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ.get("BQ_DATASET", "ecommerce")

client = bigquery.Client(project=PROJECT)


def load_csv_to_bq(csv_path: str, table_id: str) -> None:
    df = pd.read_csv(csv_path)
    job = client.load_table_from_dataframe(
        df,
        table_id,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
    )
    job.result()
    print(f"Loaded {len(df)} rows into {table_id}")


if __name__ == "__main__":
    raw = Path("data/processed")
    for name in ("orders", "order_items", "products", "users"):
        csv = raw / f"{name}.csv"
        if csv.exists():
            load_csv_to_bq(str(csv), f"{PROJECT}.{DATASET}.{name}")
        else:
            print(f"skip: {csv} not found")
