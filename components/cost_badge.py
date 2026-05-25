from __future__ import annotations

import streamlit as st
from core.bq_executor import QueryCost


def render(cost: QueryCost) -> None:
    """Display a compact cost pill above the query result."""
    if cost.mb < 100:
        bg, text_color, icon = "#E1F5EE", "#0F6E56", "✦"
    elif cost.mb < 500:
        bg, text_color, icon = "#FAEEDA", "#854F0B", "⚠"
    else:
        bg, text_color, icon = "#FCEBEB", "#A32D2D", "▲"

    free_tier_note = " · free tier" if cost.within_free_tier() else ""

    st.markdown(
        f"""
        <div style="
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: {bg};
            color: {text_color};
            font-size: 12px;
            font-weight: 500;
            padding: 4px 10px;
            border-radius: 999px;
            margin-bottom: 8px;
            font-family: monospace;
        ">
            <span>{icon}</span>
            <span>{cost.label()} scanned · {cost.cost_label()}{free_tier_note}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )