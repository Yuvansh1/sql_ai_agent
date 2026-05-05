"""
Streamlit UI for the SQL Agent (Ollama edition).
Run: streamlit run app/main.py
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from agent.sql_agent import SQLAgent

st.set_page_config(page_title="SQL AI Agent", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    .sql-box {
        background: #1e1e1e; color: #d4d4d4;
        padding: 1rem; border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem; white-space: pre-wrap; margin: 0.5rem 0;
    }
    .explanation-box {
        background: #f0f7ff; border-left: 4px solid #0066cc;
        padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin: 0.5rem 0;
    }
    .status-ok  { color: #16a34a; font-weight: 600; }
    .status-err { color: #dc2626; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# session state
for k, v in {"agent": None, "connected_model": None, "history": [], "prefill": "", "run_question": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# sidebar
with st.sidebar:
    st.title("⚙️ Setup")
    ollama_ok = SQLAgent.is_running()

    if ollama_ok:
        st.markdown('<p class="status-ok">● Ollama is running</p>', unsafe_allow_html=True)
        models = SQLAgent.list_models()
        selected = st.selectbox("Model", models if models else ["llama3.2"], index=0)

        if st.button("Connect", type="primary", use_container_width=True):
            st.session_state.agent = SQLAgent(model=selected)
            st.session_state.connected_model = selected
            st.session_state.history = []

        if st.session_state.connected_model:
            st.success(f"Connected: {st.session_state.connected_model}")
    else:
        st.markdown('<p class="status-err">● Ollama not running</p>', unsafe_allow_html=True)
        st.info("Run `ollama serve` in a terminal, then refresh.")

    st.divider()
    st.subheader("📋 Schema")
    with st.expander("View tables"):
        st.markdown("""
**customers** — id, name, email, country, joined_at
**products** — id, name, category, price, stock
**orders** — id, customer_id, status, created_at
**order_items** — id, order_id, product_id, quantity, unit_price
        """)

    st.divider()
    st.subheader("💡 Try asking")
    examples = [
        "Top 5 customers by total revenue",
        "Monthly revenue for 2024",
        "Best selling product categories",
        "Countries with the most orders",
        "Products low on stock",
        "Average order value by country",
        "How many cancelled orders are there?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=f"ex__{ex}"):
            if st.session_state.agent is None and ollama_ok and models:
                st.session_state.agent = SQLAgent(model=selected)
                st.session_state.connected_model = selected
            st.session_state.run_question = ex

    st.divider()
    if st.button("🗑️ Clear history", use_container_width=True):
        st.session_state.history = []
        if st.session_state.agent:
            st.session_state.agent.reset()
        st.rerun()

# main
st.title("🤖 SQL AI Agent")
st.caption("Ask questions in plain English — powered by Ollama, 100% local.")

if not st.session_state.agent:
    st.info("Click **Connect** in the sidebar, or click any example question to start.")
    st.stop()

st.caption(f"Model: `{st.session_state.connected_model}`")

question = st.text_input(
    "Ask a question about your data",
    value=st.session_state.run_question or "",
    placeholder="e.g. Who are the top 5 customers by revenue?",
)

ask_clicked = st.button("Ask", type="primary")

# run if Ask clicked, or if an example button set run_question
if (ask_clicked or st.session_state.run_question) and question.strip():
    st.session_state.run_question = None
    with st.spinner("Thinking..."):
        result = st.session_state.agent.ask(question.strip())
    st.session_state.history.insert(0, result)

# results
if st.session_state.history:
    latest = st.session_state.history[0]
    st.divider()

    if latest.success:
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", latest.row_count)
        c2.metric("Columns", len(latest.columns))
        c3.metric("Status", "✅ Success")

        st.markdown(f'<div class="explanation-box">💬 {latest.explanation}</div>', unsafe_allow_html=True)

        with st.expander("🔍 Generated SQL", expanded=True):
            st.markdown(f'<div class="sql-box">{latest.sql}</div>', unsafe_allow_html=True)

        if latest.data:
            df = pd.DataFrame(latest.data, columns=latest.columns)
            st.dataframe(df, use_container_width=True, height=350)
            st.download_button("⬇️ Download CSV", df.to_csv(index=False), "results.csv", "text/csv")
        else:
            st.info("Query ran successfully but returned no rows.")
    else:
        st.error(f"❌ {latest.error}")
        if latest.sql:
            st.markdown(f'<div class="sql-box">{latest.sql}</div>', unsafe_allow_html=True)

    if len(st.session_state.history) > 1:
        st.divider()
        st.subheader("🕘 Previous questions")
        for r in st.session_state.history[1:]:
            icon = "✅" if r.success else "❌"
            with st.expander(f"{icon} {r.question}"):
                if r.success:
                    st.markdown(f'<div class="sql-box">{r.sql}</div>', unsafe_allow_html=True)
                    st.caption(r.explanation)
                    if r.data:
                        st.dataframe(pd.DataFrame(r.data, columns=r.columns), use_container_width=True)
                else:
                    st.error(r.error)