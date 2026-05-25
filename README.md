# Analytics Assistant

Ask questions about e-commerce data in plain English. Get SQL + a chart.

Built on TheLook Ecommerce (BigQuery public dataset) — ~5M order items, 100K customers, global.

---

## What it does

Type something like *"which product categories had the highest return rate last quarter"* and the assistant:

1. Builds a schema-aware prompt (table defs + sample rows + few-shot examples)
2. Calls the LLM at temperature 0 to generate BigQuery SQL
3. Dry-runs the query first to show you the cost before executing
4. Runs a safety check to block any destructive statement
5. Executes against BigQuery and picks a chart type based on the result shape
6. If BigQuery rejects the SQL, feeds the error back to the LLM and retries (up to 2x)

Conversation memory keeps the last 4 turns in context so follow-up questions work naturally.

---

## Stack

- **BigQuery** — query engine and dataset
- **OpenAI / Gemini / Anthropic** — LLM provider (swap via `.env`, no code changes)
- **Streamlit** — UI
- **Plotly** — charts
- **APScheduler** — background schema refresh

---

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env
```

Fill in `config/.env`:

```
GCP_PROJECT_ID=your-project-id
LLM_PROVIDER=openai          # openai | gemini | anthropic
OPENAI_API_KEY=sk-...
GOOGLE_APPLICATION_CREDENTIALS=credentials/bq_key.json
```

Pull the live schema from BigQuery (writes `config/schema_metadata.json`):

```bash
python ingestion/schema_extractor.py
```

Run:

```bash
streamlit run main.py
```

---

## Project layout

```
├── main.py                        # Streamlit entry point
├── config/
│   ├── .env.example
│   └── schema_metadata.json       # injected into every LLM prompt
├── core/
│   ├── sql_generator.py           # prompt builder + retry loop
│   ├── sql_validator.py           # blocks DROP / DELETE / etc.
│   ├── bq_executor.py             # dry-run cost estimate + execution
│   └── llm_client.py              # OpenAI / Gemini / Anthropic wrapper
├── components/
│   ├── chat_ui.py                 # message rendering
│   ├── viz.py                     # auto chart selection
│   ├── cost_badge.py              # query cost display
│   └── session.py                 # conversation state
├── ingestion/
│   ├── schema_extractor.py        # pulls schema from live BQ tables
│   ├── schema_refresh.py          # APScheduler background refresh
│   └── load_to_bigquery.py        # optional: load CSVs into your own BQ project
└── tests/
    ├── test_sql_generator.py
    └── test_sql_validator.py
```

---

## A few things worth knowing

**Schema is injected, not fine-tuned.** The full table structure (column names, types, sample rows) goes into every prompt. This means schema changes are reflected immediately — just re-run `schema_extractor.py` or hit the refresh button in the sidebar. No retraining, no redeployment.

**The retry loop is error-aware.** When BigQuery rejects a query, the error message is pattern-matched against known failure modes (wrong argument count, bad column name, syntax error, etc.) and a targeted hint is added to the fix prompt. Generic "fix this" prompts don't work reliably — the hint is what makes the self-healing actually self-heal.

**Date anchoring.** The dataset isn't current (it runs to late 2023). On startup, the app queries the real `MIN`/`MAX` dates from the orders table and injects them into the system prompt, so "last 30 days" generates SQL anchored to the data's most recent date — not today.

**Cost visibility.** Every query runs a BigQuery dry-run before execution and displays the estimated scan size and USD cost. On a typical analytics question this is a few MB and rounds to < $0.01, well within the 1 TB/month free tier.

---

## Running tests

```bash
pytest tests/
```

Tests mock `bigquery.Client` so they run without a GCP connection.

---

## Switching LLM providers

Change one line in `config/.env`:

```
LLM_PROVIDER=gemini   # or openai
```
