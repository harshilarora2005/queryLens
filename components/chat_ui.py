"""Chat thread renderer."""
import streamlit as st

from components import session, viz


def render_history() -> None:
    for turn in session.get_history():
        with st.chat_message("user"):
            st.write(turn["q"])
        with st.chat_message("assistant"):
            st.code(turn["sql"], language="sql")


def render_result(question: str, sql: str, df) -> None:
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        st.code(sql, language="sql")
        viz.render(df)