"""Streamlit entry point for the LLM Analytics Assistant."""
from __future__ import annotations

import time

import streamlit as st

from components import chat_ui, cost_badge, session
from components.session import STARTER_QUESTIONS
from core.bq_executor import estimate_cost, run_query
from core.sql_generator import generate_sql

st.set_page_config(
    page_title="Analytics Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stChatMessage { padding: 0.5rem 0; }
    .sidebar-section { font-size: 0.75rem; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 0.05em;
                    color: rgba(100,100,100,0.8); margin: 1rem 0 0.4rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

session.init()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Analytics Assistant")
    st.caption("TheLook Ecommerce · BigQuery")

    st.markdown('<p class="sidebar-section">Try asking</p>', unsafe_allow_html=True)
    for q in STARTER_QUESTIONS[:5]:
        if st.button(q, key=f"starter_{q[:20]}", use_container_width=True):
            st.session_state["pending_question"] = q

    saved = session.get_saved_queries()
    if saved:
        st.markdown('<p class="sidebar-section">Saved queries</p>', unsafe_allow_html=True)
        for i, sq in enumerate(saved):
            c1, c2 = st.columns([5, 1])
            if c1.button(
                sq["q"][:40] + ("…" if len(sq["q"]) > 40 else ""),
                key=f"saved_{i}",
                use_container_width=True,
            ):
                st.session_state["pending_question"] = sq["q"]
            if c2.button("🗑", key=f"del_{i}"):
                session.delete_saved(i)
                st.rerun()

    st.divider()
    st.caption("LLM Analytics Assistant · v2.0")

st.markdown("## Ask a question about your data")
st.caption("Powered by BigQuery SQL generation with self-healing retry. Charts auto-selected.")

chat_ui.render_history()

default_q = st.session_state.pop("pending_question", "")
question = (
    st.chat_input("e.g. Top 10 products by revenue last month", key="main_input")
    or default_q
)

if question:
    # ① Echo the user bubble immediately — don't wait for BigQuery
    chat_ui.echo_question(question)

    sql = ""
    t0 = time.perf_counter()

    try:
        with st.spinner("Generating SQL…"):
            sql = generate_sql(question, session.get_llm_history())

        try:
            with st.spinner("Estimating cost…"):
                cost = estimate_cost(sql)
            cost_badge.render(cost)
        except Exception:
            pass

        with st.spinner("Querying BigQuery…"):
            df = run_query(sql)

        elapsed = time.perf_counter() - t0

        session.add_turn(
            question,
            sql,
            ok=True,
            row_count=len(df) if df is not None else 0,
            df=df,
        )

        chat_ui.render_result(question, sql, df, elapsed=elapsed)

    except Exception as e:
        elapsed = time.perf_counter() - t0
        session.add_turn(question, sql=str(e), ok=False)
        st.error(f"**Could not generate a valid query.** {e}")
        st.caption(
            f"Failed after {elapsed:.1f}s. "
            "Try rephrasing your question or check the schema."
        )