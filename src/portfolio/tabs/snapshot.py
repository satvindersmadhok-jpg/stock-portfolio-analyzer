from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from ..core.models import Transaction
from ..core.calculator import build_holdings, active_holdings
from ..core.market_data import fetch_current_prices


_PLOTLY_TEMPLATE = "plotly_white"
_GREEN = "#22c55e"
_RED = "#ef4444"


def render(transactions: list[Transaction]) -> None:
    st.subheader("Portfolio Snapshot")

    if not transactions:
        st.info("Add transactions in the Transactions tab to see your portfolio snapshot.")
        return

    holdings, warnings = build_holdings(transactions)
    for w in warnings:
        st.warning(f"Data issue: {w}")
    active = active_holdings(holdings)

    if active.empty:
        st.info("No open positions — all holdings have been fully sold.")
        return

    tickers = tuple(active["ticker"].tolist())
    with st.spinner("Fetching current prices..."):
        prices = fetch_current_prices(tickers)

    active = active.copy()
    active["current_price"] = active["ticker"].map(lambda t: prices.get(t, 0.0))
    active["market_value"] = active["quantity"] * active["current_price"]
    active["unrealized_pnl"] = active["quantity"] * (active["current_price"] - active["avg_cost"])
    active["unrealized_pct"] = (
        (active["current_price"] - active["avg_cost"]) / active["avg_cost"] * 100
    ).where(active["avg_cost"] > 0, 0.0)

    total_value = active["market_value"].sum()

    # ── Pie Chart ──────────────────────────────────────────────────────────
    st.markdown("### Portfolio Allocation")
    fig_pie = go.Figure(
        go.Pie(
            labels=active["ticker"],
            values=active["market_value"],
            hole=0.45,
            textinfo="label+percent",
            textfont_size=14,
            marker=dict(line=dict(color="#ffffff", width=2)),
        )
    )
    fig_pie.update_layout(
        template=_PLOTLY_TEMPLATE,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=20, b=20, l=20, r=20),
        height=400,
        annotations=[dict(text=f"${total_value:,.0f}", x=0.5, y=0.5, font_size=18, showarrow=False)],
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # ── Holdings Table ─────────────────────────────────────────────────────
    st.markdown("### Holdings Breakdown")

    display = pd.DataFrame({
        "Ticker": active["ticker"],
        "Quantity": active["quantity"].map("{:,.4f}".format),
        "Avg Cost": active["avg_cost"].map("${:,.2f}".format),
        "Current Price": active["current_price"].map("${:,.2f}".format),
        "Market Value": active["market_value"].map("${:,.2f}".format),
        "Unrealized P&L": active["unrealized_pnl"],
        "Return %": active["unrealized_pct"],
        "Allocation %": (active["market_value"] / total_value * 100).map("{:.1f}%".format),
    })

    def colour_pnl(val):
        if isinstance(val, float):
            return f"color: {_GREEN}" if val >= 0 else f"color: {_RED}"
        return ""

    styled = (
        display.style
        .map(colour_pnl, subset=["Unrealized P&L", "Return %"])
        .format({"Unrealized P&L": "${:,.2f}", "Return %": "{:.2f}%"})
        .hide(axis="index")
        .set_properties(**{"text-align": "right"})
        .set_properties(subset=["Ticker"], **{"text-align": "left", "font-weight": "bold"})
    )
    st.dataframe(styled, use_container_width=True)

    # ── Summary row ────────────────────────────────────────────────────────
    total_cost = active["total_cost"].sum()
    total_unrealized = active["unrealized_pnl"].sum()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Market Value", f"${total_value:,.2f}")
    col2.metric("Total Cost Basis", f"${total_cost:,.2f}")
    col3.metric(
        "Total Unrealized P&L",
        f"${total_unrealized:,.2f}",
        delta=f"{total_unrealized / total_cost * 100:.2f}%" if total_cost else None,
    )
