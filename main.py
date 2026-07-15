from __future__ import annotations

import time

import streamlit as st

from components import chat_ui, session
from components.session import STARTER_QUESTIONS
from core import rate_limiter
from core.bq_executor import QueryTooExpensiveError, estimate_and_run
from core.sql_generator import generate_sql
from ingestion import schema_refresh

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

schema_refresh.start(interval_hours=24)

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
    st.markdown('<p class="sidebar-section">Schema</p>', unsafe_allow_html=True)

    last_refresh = st.session_state.get("schema_last_refreshed", "unknown")
    refresh_error = st.session_state.get("schema_refresh_error")

    if refresh_error:
        st.caption(f"⚠ Last refresh failed: {refresh_error}")
    else:
        st.caption(f"Last refreshed: {last_refresh}")

    if st.button("↺ Refresh schema now", use_container_width=True):
        with st.spinner("Refreshing schema from BigQuery…"):
            ok = schema_refresh.refresh_now()
        if ok:
            st.success("Schema refreshed.")
            st.session_state.pop("schema_refresh_error", None)
        else:
            st.error("Refresh failed — check logs.")
        st.rerun()

    st.divider()
    st.markdown('<p class="sidebar-section">Usage today</p>', unsafe_allow_html=True)
    _usage = rate_limiter.global_usage_snapshot()
    st.caption(
        f"{_usage['queries_today']}/{_usage['queries_limit']} queries · "
        f"{_usage['bytes_today'] / 1_000_000:.0f} MB / "
        f"{_usage['bytes_limit'] / 1_000_000_000:.1f} GB scanned"
    )
    st.progress(min(_usage["queries_today"] / max(_usage["queries_limit"], 1), 1.0))

    st.divider()
    st.caption("LLM Analytics Assistant · v2.0")

st.markdown("## Ask a question about your data")
st.caption("Powered by BigQuery SQL generation with self-healing retry. Charts auto-selected.")

chat_ui.render_history()

default_q = st.session_state.pop("pending_question", "")
question = (
    st.chat_input("e.g. Top 10 products by revenue last month", key="main_input") or default_q
)

if question:
    session.add_pending(question)

    with st.chat_message("user"):
        st.write(question)

    sql = ""
    t0 = time.perf_counter()

    try:
        rate_limiter.check_session_limit()
        rate_limiter.check_global_query_limit()
    except rate_limiter.RateLimitError as e:
        session.complete_turn(question, sql=str(e), ok=False)
        with st.chat_message("assistant"):
            st.warning(f"**Rate limit reached.** {e}")
        st.stop()

    rate_limiter.record_session_query()

    try:
        with st.chat_message("assistant"):
            with st.spinner("Generating SQL…"):
                sql = generate_sql(question, session.get_llm_history())

            st.code(sql, language="sql")

            with st.spinner("Estimating cost and querying BigQuery…"):
                cost, df = estimate_and_run(sql)

            from components.cost_badge import render as render_cost

            render_cost(cost)

            elapsed = time.perf_counter() - t0

            if df is None or df.empty:
                st.info("Query returned no rows — try a different date range or filter.")
            else:
                from components.viz import render as render_viz

                render_viz(df, question=question, sql=sql)

            rows = len(df) if df is not None and not df.empty else 0
            st.caption(
                f"Completed in {elapsed:.1f}s · {rows:,} rows"
                if rows
                else f"Completed in {elapsed:.1f}s"
            )

        session.complete_turn(
            question,
            sql,
            ok=True,
            row_count=len(df) if df is not None else 0,
            df=df,
        )

    except QueryTooExpensiveError as e:
        elapsed = time.perf_counter() - t0
        session.complete_turn(question, sql=sql or str(e), ok=False)
        with st.chat_message("assistant"):
            st.warning(f"**Query too expensive to run.** {e}")
            st.caption(f"Rejected after {elapsed:.1f}s — no cost was incurred.")

    except rate_limiter.RateLimitError as e:
        elapsed = time.perf_counter() - t0
        session.complete_turn(question, sql=sql or str(e), ok=False)
        with st.chat_message("assistant"):
            st.warning(f"**Rate limit reached.** {e}")
            st.caption(f"Rejected after {elapsed:.1f}s — no cost was incurred.")

    except Exception as e:
        elapsed = time.perf_counter() - t0
        session.complete_turn(question, sql=str(e), ok=False)
        with st.chat_message("assistant"):
            st.error(f"**Could not generate a valid query.** {e}")
            st.caption(
                f"Failed after {elapsed:.1f}s. Try rephrasing your question or check the schema."
            )
