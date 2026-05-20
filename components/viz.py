from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

_PALETTE = [
    "#4F8EF7", "#F7894F", "#4FF7A0", "#F74F8E",
    "#A04FF7", "#F7D94F", "#4FD9F7", "#F74F4F",
]
_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=13),
    margin=dict(l=0, r=0, t=32, b=0),
    colorway=_PALETTE,
)


def _is_datetime(s: pd.Series) -> bool:
    return pd.api.types.is_datetime64_any_dtype(s) or "date" in str(s.name).lower()


def _is_numeric(s: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(s)


def _is_categorical(s: pd.Series) -> bool:
    return s.dtype == object or pd.api.types.is_categorical_dtype(s)


def _fmt(n: float) -> str:
    """Human-readable large numbers."""
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if abs(n) >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:,.2f}"



def _nl_summary(question: str, df: pd.DataFrame) -> str:
    try:
        from core.llm_client import call_llm

        preview = df.head(5).to_markdown(index=False)
        prompt = (
            f"The user asked: '{question}'\n\n"
            f"The query returned this data:\n{preview}\n\n"
            "Write ONE concise sentence (max 30 words) summarising the key insight. "
            "Be specific — mention numbers, names, or trends. No preamble."
        )
        return call_llm(
            system="You are a data analyst writing one-sentence insights. Reply with only the insight sentence.",
            user=prompt,
            temperature=0.2,
        )
    except Exception:  
        return ""


def render(df: pd.DataFrame, question: str = "", sql: str = "") -> None:
    if df is None or df.empty:
        st.info("Query returned no rows.")
        return

    if df.shape == (1, 1):
        val = df.iloc[0, 0]
        col_name = df.columns[0]
        st.metric(label=col_name.replace("_", " ").title(), value=_fmt(float(val)) if isinstance(val, (int, float)) else str(val))
        _action_row(df, sql)
        return
    if question:
        summary = _nl_summary(question, df)
        if summary:
            st.caption(f"{summary}")

    with st.expander("Raw data", expanded=True):
        st.dataframe(df, use_container_width=True, hide_index=True)
    if len(df.columns) >= 2:
        x, y = df.columns[0], df.columns[1]
        fig = None

        if _is_datetime(df[x]) and _is_numeric(df[y]):
            fig = px.line(df, x=x, y=y, markers=True)
            fig.update_traces(line_color=_PALETTE[0], line_width=2)

        elif _is_numeric(df[x]) and _is_numeric(df[y]):
            fig = px.scatter(df, x=x, y=y, trendline="ols" if len(df) >= 10 else None)

        elif _is_categorical(df[x]) and _is_numeric(df[y]):
            n_cats = df[x].nunique()
            if n_cats <= 8:
                tab_bar, tab_pie = st.tabs(["Bar", "Pie"])
                with tab_bar:
                    fig_bar = px.bar(df.sort_values(y, ascending=False), x=x, y=y)
                    fig_bar.update_layout(**_LAYOUT)
                    st.plotly_chart(fig_bar, use_container_width=True)
                with tab_pie:
                    fig_pie = px.pie(df, names=x, values=y, hole=0.35)
                    fig_pie.update_layout(**_LAYOUT)
                    st.plotly_chart(fig_pie, use_container_width=True)
                _action_row(df, sql)
                return
            else:
                # Horizontal bar for many categories
                fig = px.bar(
                    df.sort_values(y, ascending=True).tail(20),
                    x=y, y=x, orientation="h",
                )

        if fig is not None:
            fig.update_layout(**_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

    _action_row(df, sql)


def _action_row(df: pd.DataFrame, sql: str) -> None:
    """CSV download + copy-SQL buttons."""
    cols = st.columns([1, 1, 4])

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    cols[0].download_button(
        label="⬇ CSV",
        data=csv_buf.getvalue(),
        file_name="results.csv",
        mime="text/csv",
        use_container_width=True,
    )

    if sql:
        with cols[1].popover("📋 SQL"):
            st.code(sql, language="sql")