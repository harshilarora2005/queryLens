# LLM-Powered Analytics Assistant

Natural-language → BigQuery SQL → chart/table, powered by an LLM (OpenAI / Gemini / Anthropic).

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env   # fill in keys
python ingestion/schema_extractor.py
streamlit run main.py
```

## Layout

```
analytics_assistant/
├── main.py                       # Streamlit entry point
├── requirements.txt
├── config/
│   ├── .env.example
│   └── schema_metadata.json      # schema injected into LLM prompts
├── credentials/                  # bq_key.json (gitignored)
├── ingestion/
│   ├── load_to_bigquery.py
│   └── schema_extractor.py
├── core/
│   ├── llm_client.py             # provider-agnostic LLM call
│   ├── sql_generator.py          # NL -> SQL with retry loop
│   ├── sql_validator.py          # blocks destructive SQL
│   └── bq_executor.py            # runs SQL, returns DataFrame
├── components/
│   ├── chat_ui.py
│   ├── viz.py
│   └── session.py
└── tests/
    ├── test_sql_generator.py
    └── test_sql_validator.py
```

## Pipeline

1. Schema injection → 2. SQL generation (temp=0) → 3. Safety validation
→ 4. Error-recovery loop (up to 2 retries) → 5. Auto chart selection
→ 6. Conversation memory (last 4 turns).
