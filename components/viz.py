"""Auto-select a chart based on column types."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


def _is_datetime(s: pd.Series) -> bool:
    return pd.api.types.is_datetime64_any_dtype(s) or "date" in str(s.dtype).lower()


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
        st.plotly_chart(px.line(df, x=x, y=y), use_container_width=True)
    elif df[x].dtype == object or pd.api.types.is_categorical_dtype(df[x]):
        st.plotly_chart(px.bar(df, x=x, y=y), use_container_width=True)
