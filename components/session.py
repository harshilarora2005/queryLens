
import streamlit as st

MAX_TURNS = 4

STARTER_QUESTIONS = [
    "What was total revenue by month in 2023 for completed orders?",
    "Top 10 products by revenue in the last 30 days",
    "Which product categories have the highest return rate?",
    "How many new users signed up per month this year?",
    "What are the top 5 countries by number of orders?",
    "Average order value by gender in 2023",
    "Which traffic source drives the most completed orders?",
    "Show daily orders for the last 90 days",
]


def init() -> None:
    if "history" not in st.session_state:
        st.session_state.history = []
    if "saved_queries" not in st.session_state:
        st.session_state.saved_queries = []


def add_turn(question: str, sql: str, ok: bool, row_count: int = 0) -> None:
    st.session_state.history.append(
        {"q": question, "sql": sql, "ok": ok, "rows": row_count}
    )
    st.session_state.history = st.session_state.history[-MAX_TURNS:]


def get_history() -> list[dict]:
    return st.session_state.get("history", [])


def save_query(question: str, sql: str) -> None:
    saved = st.session_state.saved_queries
    # Deduplicate by question
    if not any(s["q"] == question for s in saved):
        saved.append({"q": question, "sql": sql})


def get_saved_queries() -> list[dict]:
    return st.session_state.get("saved_queries", [])


def delete_saved(index: int) -> None:
    saved = st.session_state.saved_queries
    if 0 <= index < len(saved):
        saved.pop(index)