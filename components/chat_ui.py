"""Chat thread renderer."""

from __future__ import annotations

import streamlit as st

from components import session, viz


def _render_turn(turn: dict) -> None:
    """Render one completed history turn."""
    if turn.get("_pending"):
        return

    with st.chat_message("user"):
        st.write(turn["q"])

    with st.chat_message("assistant"):
        if not turn.get("ok"):
            st.error(turn["sql"])
            return

        st.code(turn["sql"], language="sql")

        df = turn.get("df")
        if df is not None and not df.empty:
            viz.render(df, question=turn.get("q", ""), sql=turn.get("sql", ""))
        else:
            st.caption("Query returned no rows.")

        row_count = turn.get("row_count", 0)
        if row_count:
            st.caption(f"{row_count:,} rows")


def render_history() -> None:
    """Replay all previous completed turns from session state.
    The current in-flight turn is excluded (it's pending) and rendered
    inline by main.py instead."""
    history = session.get_history()

    turns_to_show = [t for t in history if not t.get("_pending")]
    for turn in turns_to_show:
        _render_turn(turn)
