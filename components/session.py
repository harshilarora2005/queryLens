import streamlit as st
from config import settings

MAX_TURNS = settings.MEMORY_TURNS


def init() -> None:
    if "history" not in st.session_state:
        st.session_state.history = []


def add_turn(question: str, sql: str, ok: bool) -> None:
    st.session_state.history.append({"q": question, "sql": sql, "ok": ok})
    st.session_state.history = st.session_state.history[-MAX_TURNS:]


def get_history() -> list[dict]:
    return st.session_state.get("history", [])