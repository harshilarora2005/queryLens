import streamlit as st
from components import session, viz

def render_history() -> None:
    for turn in session.get_history():
        with st.chat_message("user"):
            st.write(turn["q"])
        with st.chat_message("assistant"):
            if turn["ok"]:
                st.code(turn["sql"], language="sql")
                if turn.get("rows"):
                    st.caption(f"{turn['rows']:,} rows returned")
            else:
                st.warning(f"Failed: {turn['sql']}")


def render_result(question: str, sql: str, df, elapsed: float = 0.0) -> None:
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        meta_parts = []
        if elapsed:
            meta_parts.append(f"⏱ {elapsed:.1f}s")
        if df is not None and not df.empty:
            meta_parts.append(f"{len(df):,} rows")
        if meta_parts:
            st.caption("  ·  ".join(meta_parts))

        st.code(sql, language="sql")

        col_save, _ = st.columns([1, 5])
        if col_save.button("Save query", key=f"save_{hash(question)}"):
            session.save_query(question, sql)
            st.toast("Query saved!")

        viz.render(df, question=question, sql=sql)