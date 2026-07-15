from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv("config/.env")

BILLING_PROJECT = os.environ["GCP_PROJECT_ID"]
SOURCE_PROJECT = os.environ.get("BQ_SOURCE_PROJECT", "bigquery-public-data")
DATASET = os.environ.get("BQ_DATASET", "thelook_ecommerce")
TABLES = ("orders", "order_items", "products", "users")

OUT = Path("config/schema_metadata.json")


def main() -> None:
    client = bigquery.Client(project=BILLING_PROJECT)
    tables_meta = []
    for name in TABLES:
        ref = f"{SOURCE_PROJECT}.{DATASET}.{name}"
        table = client.get_table(ref)
        sample = client.query(f"SELECT * FROM `{ref}` LIMIT 2").to_dataframe()
        tables_meta.append(
            {
                "name": ref,
                "description": table.description or "",
                "columns": [{"name": f.name, "type": f.field_type} for f in table.schema],
                "sample_rows": sample.to_dict(orient="records"),
            }
        )

    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    existing["tables"] = tables_meta
    OUT.write_text(json.dumps(existing, indent=2, default=str))
    print(
        f"Wrote schema for {len(tables_meta)} tables -> {OUT} "
        f"(billing project: {BILLING_PROJECT}, source: {SOURCE_PROJECT}.{DATASET})"
    )


if __name__ == "__main__":
    main()
