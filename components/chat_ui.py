from __future__ import annotations

import streamlit as st
from components import session, viz


def _render_turn(turn: dict) -> None:
    with st.chat_message("user"):
        st.write(turn["q"])

    with st.chat_message("assistant"):
        if not turn.get("ok", True):
            st.error(turn["sql"])
            return

        st.code(turn["sql"], language="sql")

        # Re-render cached dataframe + chart if we stored it
        df = turn.get("df")
        if df is not None and not df.empty:
            viz.render(df, question=turn.get("q", ""), sql=turn.get("sql", ""))
        elif turn.get("ok"):
            st.caption("Query returned no rows.")


def render_history() -> None:
    """Replay all previous turns from session state."""
    for turn in session.get_history():
        _render_turn(turn)


def echo_question(question: str) -> None:
    """Immediately show the user bubble before processing starts."""
    with st.chat_message("user"):
        st.write(question)


def render_result(
    question: str,
    sql: str,
    df,
    elapsed: float = 0.0,
) -> None:
    with st.chat_message("assistant"):
        st.code(sql, language="sql")

        if df is None or df.empty:
            st.info("Query returned no rows — try a different date range or filter.")
        else:
            viz.render(df, question=question, sql=sql)

        if elapsed:
            st.caption(f"Completed in {elapsed:.1f}s · {len(df):,} rows" if df is not None and not df.empty else f"Completed in {elapsed:.1f}s")