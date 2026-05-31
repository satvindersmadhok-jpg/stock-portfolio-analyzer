from __future__ import annotations

import streamlit as st
import pandas as pd
from datetime import date

from ..core.models import Transaction
from ..core.calculator import transactions_to_df
from ..utils.csv_parser import parse_csv


def render(transactions: list[Transaction]) -> list[Transaction]:
    """Renders Tab 1. Returns the (possibly updated) transaction list."""

    st.subheader("Transaction History")

    # ── CSV Upload ──────────────────────────────────────────────────────────
    with st.expander("Upload CSV", expanded=not transactions):
        st.markdown(
            "Expected columns: `ticker`, `date`, `transaction_type` (BUY/SELL), `quantity`, `price`"
        )
        uploaded = st.file_uploader("Choose a CSV file", type="csv", key="csv_uploader")
        if uploaded:
            new_txs, errors = parse_csv(uploaded)
            if errors:
                for err in errors:
                    st.error(err)
            if new_txs:
                existing_keys = {
                    (t.date, t.ticker, t.transaction_type, t.quantity, t.price)
                    for t in transactions
                }
                added = 0
                for tx in new_txs:
                    key = (tx.date, tx.ticker, tx.transaction_type, tx.quantity, tx.price)
                    if key not in existing_keys:
                        transactions.append(tx)
                        existing_keys.add(key)
                        added += 1
                if added:
                    st.success(f"Imported {added} transaction(s).")
                else:
                    st.info("All rows already exist — nothing new imported.")

    # ── Manual Entry ────────────────────────────────────────────────────────
    with st.expander("Add Transaction Manually", expanded=False):
        with st.form("manual_entry", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                ticker = st.text_input("Ticker", placeholder="AAPL").strip().upper()
                tx_date = st.date_input("Date", value=date.today())
            with col2:
                tx_type = st.selectbox("Type", ["BUY", "SELL"])
                quantity = st.number_input("Quantity", min_value=0.0001, step=0.01, format="%.4f")
                price = st.number_input("Price (USD)", min_value=0.0001, step=0.01, format="%.2f")
            submitted = st.form_submit_button("Add Transaction", use_container_width=True)
            if submitted:
                if not ticker:
                    st.error("Ticker is required.")
                else:
                    transactions.append(Transaction(
                        date=tx_date,
                        ticker=ticker,
                        transaction_type=tx_type,
                        quantity=quantity,
                        price=price,
                    ))
                    st.success(f"Added: {tx_type} {quantity} {ticker} @ ${price:.2f}")

    # ── Transaction Table ────────────────────────────────────────────────────
    st.markdown("---")
    if not transactions:
        st.info("No transactions yet. Upload a CSV or add one manually above.")
        return transactions

    df = transactions_to_df(transactions)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["price"] = df["price"].map("${:,.2f}".format)
    df["quantity"] = df["quantity"].map("{:,.4f}".format)

    # colour BUY green, SELL red
    def colour_type(val):
        color = "#22c55e" if val == "BUY" else "#ef4444"
        return f"color: {color}; font-weight: bold"

    styled = (
        df.style
        .map(colour_type, subset=["transaction_type"])
        .set_properties(**{"text-align": "left"})
        .hide(axis="index")
    )
    st.dataframe(styled, use_container_width=True)

    # ── Clear all ────────────────────────────────────────────────────────────
    if st.button("Clear All Transactions", type="secondary"):
        transactions.clear()
        st.rerun()

    return transactions
