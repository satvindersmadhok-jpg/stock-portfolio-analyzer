import streamlit as st

from portfolio.core.models import Transaction
from portfolio.tabs import transactions as tab_transactions
from portfolio.tabs import snapshot as tab_snapshot
from portfolio.tabs import performance as tab_performance


def main():
    st.set_page_config(
        page_title="Portfolio Analyzer",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        """
        <style>
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: 8px 24px;
            font-weight: 600;
        }
        div[data-testid="metric-container"] > div {
            border-radius: 10px;
            padding: 12px 16px;
            border: 1px solid #cbd5e1;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("📈 Stock Portfolio Analyzer")

    # Persist transactions across tabs via session state
    if "transactions" not in st.session_state:
        st.session_state.transactions: list[Transaction] = []

    tab1, tab2, tab3 = st.tabs(["📋 Transactions", "🥧 Portfolio Snapshot", "📊 Historical Performance"])

    with tab1:
        st.session_state.transactions = tab_transactions.render(st.session_state.transactions)

    with tab2:
        tab_snapshot.render(st.session_state.transactions)

    with tab3:
        tab_performance.render(st.session_state.transactions)


if __name__ == "__main__":
    main()
