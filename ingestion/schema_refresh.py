from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path

import streamlit as st

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path("config/schema_metadata.json")
_lock = threading.Lock()


def _do_refresh() -> bool:
    with _lock:
        try:
            from ingestion.schema_extractor import main as extract_schema

            extract_schema()

            import core.sql_generator as gen

            gen.SCHEMA = json.loads(SCHEMA_PATH.read_text())
            gen._fetch_date_range.clear() # type: ignore[attr-defined]

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state["schema_last_refreshed"] = now
            logger.info(f"Schema refreshed at {now}")
            return True

        except Exception as e:
            logger.warning(f"Schema refresh failed: {e}")
            st.session_state["schema_refresh_error"] = str(e)
            return False

def _start_background_refresh() -> None:
    threading.Thread(target=_do_refresh, daemon=True).start()

@st.cache_resource
def _start_scheduler_once(interval_hours: int) -> bool:
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning(
            "apscheduler not installed — auto schema refresh disabled. Run: pip install apscheduler"
        )
        return False

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _do_refresh,
        trigger="interval",
        hours=interval_hours,
        id="schema_refresh",
        replace_existing=True,
    )
    scheduler.start()
    _start_background_refresh()

    logger.info(f"Schema auto-refresh scheduled every {interval_hours}h")
    return True


def start(interval_hours: int = 24) -> None:
    _start_scheduler_once(interval_hours)
    st.session_state.setdefault("schema_last_refreshed", "on startup")


def refresh_now() -> bool:
    return _do_refresh()
