"""Streamlit conversation memory (last N turns)."""
import streamlit as st

MAX_TURNS = 4


def init() -> None:
    if "history" not in st.session_state:
        st.session_state.history = []  # list[{q, sql, ok}]


def add_turn(question: str, sql: str, ok: bool) -> None:
    st.session_state.history.append({"q": question, "sql": sql, "ok": ok})
    st.session_state.history = st.session_state.history[-MAX_TURNS:]


def get_history() -> list[dict]:
    return st.session_state.get("history", [])
