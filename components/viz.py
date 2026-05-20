"""Auto-select a chart based on column types."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


def _is_datetime(s: pd.Series) -> bool:
    return pd.api.types.is_datetime64_any_dtype(s) or "date" in str(s.name).lower()


def _is_categorical(s: pd.Series) -> bool:
    return s.dtype == object or isinstance(s.dtype, pd.CategoricalDtype) or pd.api.types.is_string_dtype(s)


def render(df: pd.DataFrame) -> None:
    if df is None or df.empty:
        st.info("Query returned no rows.")
        return
    st.dataframe(df, use_container_width=True)
    if len(df.columns) < 2:
        return
    x, y = df.columns[0], df.columns[1]
    numeric_y = pd.api.types.is_numeric_dtype(df[y])
    if not numeric_y:
        return
    if _is_datetime(df[x]):
        fig = px.line(df, x=x, y=y, title=f"{y} over time")
        st.plotly_chart(fig, use_container_width=True)
    elif _is_categorical(df[x]):
        plot_df = df.sort_values(y, ascending=False).head(50)
        fig = px.bar(plot_df, x=x, y=y, title=f"{y} by {x}")
        st.plotly_chart(fig, use_container_width=True)