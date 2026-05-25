from __future__ import annotations
import json
import logging
import threading
from datetime import datetime
from pathlib import Path

import streamlit as st

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path("config/schema_metadata.json")
_scheduler_started = False
_lock = threading.Lock()



def _do_refresh() -> bool:
    try:
        from ingestion.schema_extractor import main as extract_schema
        extract_schema()
        import core.sql_generator as gen
        with _lock:
            gen.SCHEMA = json.loads(SCHEMA_PATH.read_text())

        gen._fetch_date_range.clear()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state["schema_last_refreshed"] = now
        logger.info(f"Schema refreshed at {now}")
        return True

    except Exception as e:
        logger.warning(f"Schema refresh failed: {e}")
        st.session_state["schema_refresh_error"] = str(e)
        return False

def start(interval_hours: int = 24) -> None:
    global _scheduler_started
    if st.session_state.get("_schema_scheduler_started"):
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning(
            "apscheduler not installed — auto schema refresh disabled. "
            "Run: pip install apscheduler"
        )
        return

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _do_refresh,
        trigger="interval",
        hours=interval_hours,
        id="schema_refresh",
        replace_existing=True,
    )
    scheduler.start()

    st.session_state["_schema_scheduler_started"] = True
    st.session_state["schema_last_refreshed"] = "on startup"

    threading.Thread(target=_do_refresh, daemon=True).start()

    logger.info(f"Schema auto-refresh scheduled every {interval_hours}h")

def refresh_now() -> bool:
    """Trigger a manual refresh. Returns True on success."""
    return _do_refresh()