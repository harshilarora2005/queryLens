"""Conversation memory and saved queries."""

from __future__ import annotations

import streamlit as st

from config import settings

MAX_TURNS = settings.MEMORY_TURNS

STARTER_QUESTIONS = [
    "What was total revenue by month in 2023?",
    "Top 10 products by revenue last 30 days",
    "Which product categories have the highest return rate?",
    "How many new users signed up per month in 2023?",
    "Average order value by country — top 10 countries",
    "Which brands generate the most profit?",
    "Orders by status breakdown",
    "Revenue by traffic source",
]


def init() -> None:
    if "history" not in st.session_state:
        st.session_state.history = []
    if "saved_queries" not in st.session_state:
        st.session_state.saved_queries = []
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = ""


def add_pending(question: str) -> None:
    """Add a skeleton turn immediately so render_history shows the user bubble
    on the next rerun even before processing completes."""
    # Avoid double-adding if already present (e.g. sidebar button double-trigger)
    history = st.session_state.setdefault("history", [])
    if history and history[-1].get("_pending") and history[-1]["q"] == question:
        return
    history.append({"q": question, "sql": "", "ok": None, "_pending": True, "df": None})


def complete_turn(
    question: str,
    sql: str,
    ok: bool,
    row_count: int = 0,
    df=None,
) -> None:
    """Replace the last pending turn with the real completed result."""
    history = st.session_state.setdefault("history", [])
    if history and history[-1].get("_pending") and history[-1]["q"] == question:
        history[-1] = {
            "q": question,
            "sql": sql,
            "ok": ok,
            "row_count": row_count,
            "df": df,
            "_pending": False,
        }
    else:
        # Fallback: just append (shouldn't normally happen)
        history.append(
            {
                "q": question,
                "sql": sql,
                "ok": ok,
                "row_count": row_count,
                "df": df,
                "_pending": False,
            }
        )


# Keep add_turn for any callers outside main.py
def add_turn(
    question: str,
    sql: str,
    ok: bool,
    row_count: int = 0,
    df=None,
) -> None:
    complete_turn(question, sql, ok, row_count, df)


def get_history() -> list[dict]:
    return st.session_state.get("history", [])


def get_llm_history() -> list[dict]:
    """Last MAX_TURNS successful completed turns for LLM context."""
    ok_turns = [
        h for h in st.session_state.get("history", []) if h.get("ok") and not h.get("_pending")
    ]
    return ok_turns[-MAX_TURNS:]


def get_saved_queries() -> list[dict]:
    return st.session_state.get("saved_queries", [])


def save_query(question: str, sql: str) -> None:
    saved = st.session_state.setdefault("saved_queries", [])
    if not any(s["q"] == question for s in saved):
        saved.append({"q": question, "sql": sql})


def delete_saved(index: int) -> None:
    saved = st.session_state.get("saved_queries", [])
    if 0 <= index < len(saved):
        saved.pop(index)
