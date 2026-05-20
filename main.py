"""Streamlit entry point for the LLM Analytics Assistant."""
import streamlit as st

from components import chat_ui, session
from core.sql_generator import generate_and_run

st.set_page_config(page_title="Analytics Assistant", page_icon="📊", layout="wide")
st.title("LLM Analytics Assistant")
st.caption("Ask any question about TheLook Ecommerce — answered in SQL + chart.")

session.init()
chat_ui.render_history()

question = st.chat_input("e.g. Top 10 products by revenue last month")
if question:
    try:
        with st.spinner("Generating SQL and querying BigQuery..."):
            sql, df = generate_and_run(question, session.get_history())
        session.add_turn(question, sql, ok=True)
        chat_ui.render_result(question, sql, df)
    except Exception as e: 
        session.add_turn(question, sql=str(e), ok=False)
        st.error(f"Failed: {e}")
