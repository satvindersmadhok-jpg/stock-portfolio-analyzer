from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from datetime import date

from ..core.models import Transaction
from ..core.calculator import build_holdings, active_holdings
from ..core.market_data import fetch_current_prices, fetch_price_history
from ..core.metrics import compute_summary, compute_portfolio_trend


_PLOTLY_TEMPLATE = "plotly_dark"
_GREEN = "#22c55e"
_RED = "#ef4444"
_BLUE = "#60a5fa"
_AMBER = "#f59e0b"


def _metric_card(col, label: str, value: str, delta: str | None = None, positive: bool | None = None):
    if delta is not None and positive is not None:
        colour = _GREEN if positive else _RED
        col.markdown(
            f"""
            <div style="background:#1e1e2e;border-radius:10px;padding:18px 20px;border:1px solid #2d2d44;">
                <div style="font-size:13px;color:#9ca3af;margin-bottom:4px;">{label}</div>
                <div style="font-size:24px;font-weight:700;color:#f1f5f9;">{value}</div>
                <div style="font-size:13px;color:{colour};margin-top:4px;">{delta}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        col.markdown(
            f"""
            <div style="background:#1e1e2e;border-radius:10px;padding:18px 20px;border:1px solid #2d2d44;">
                <div style="font-size:13px;color:#9ca3af;margin-bottom:4px;">{label}</div>
                <div style="font-size:24px;font-weight:700;color:#f1f5f9;">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render(transactions: list[Transaction]) -> None:
    st.subheader("Historical Performance")

    if not transactions:
        st.info("Add transactions in the Transactions tab to see performance metrics.")
        return

    holdings, warnings = build_holdings(transactions)
    for w in warnings:
        st.warning(f"Data issue: {w}")
    active = active_holdings(holdings)
    tickers = tuple(active["ticker"].tolist()) if not active.empty else ()

    with st.spinner("Fetching market data..."):
        prices = fetch_current_prices(tickers) if tickers else {}

    summary = compute_summary(transactions, prices)

    # ── Metric Cards ────────────────────────────────────────────────────────
    st.markdown("### Key Metrics")
    c1, c2, c3 = st.columns(3)
    c4, c5 = st.columns(2)

    _metric_card(c1, "Total Lifetime Investment", f"${summary['total_invested']:,.2f}")
    _metric_card(c2, "Total Proceeds from Sales", f"${summary['total_proceeds']:,.2f}")
    _metric_card(c3, "Current Portfolio Value", f"${summary['current_portfolio_value']:,.2f}")

    total_return = summary["total_return"]
    total_invested = summary["total_invested"]
    return_pct = (total_return / total_invested * 100) if total_invested else 0.0
    _metric_card(
        c4,
        "Total Return (Realized + Unrealized)",
        f"${total_return:,.2f}",
        delta=f"{'+' if return_pct >= 0 else ''}{return_pct:.2f}% of invested",
        positive=total_return >= 0,
    )

    xirr = summary["xirr"]
    if xirr is not None:
        xirr_str = f"{xirr * 100:.2f}%"
        _metric_card(
            c5,
            "XIRR (Annualised Return)",
            xirr_str,
            delta="annualised IRR on cash flows",
            positive=xirr >= 0,
        )
    else:
        _metric_card(c5, "XIRR", "N/A", delta="insufficient data")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Trend Chart ─────────────────────────────────────────────────────────
    st.markdown("### Portfolio Trend")

    all_tickers = tuple(set(t.ticker.upper() for t in transactions))
    start_date = min(t.date for t in transactions)
    end_date = date.today()

    with st.spinner("Building portfolio trend (this may take a moment on first load)..."):
        history = fetch_price_history(all_tickers, start_date, end_date)
        trend = compute_portfolio_trend(transactions, history)

    if trend.empty:
        st.warning("Could not build trend — no price history available.")
        return

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=trend["date"],
        y=trend["market_value"],
        name="Market Value",
        line=dict(color=_BLUE, width=2.5),
        fill="tonexty" if False else None,
        hovertemplate="<b>Market Value</b><br>%{x}<br>$%{y:,.2f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=trend["date"],
        y=trend["invested_capital"],
        name="Invested Capital",
        line=dict(color=_AMBER, width=2, dash="dot"),
        hovertemplate="<b>Invested Capital</b><br>%{x}<br>$%{y:,.2f}<extra></extra>",
    ))

    # shade profit/loss area between the two lines
    fig.add_trace(go.Scatter(
        x=list(trend["date"]) + list(trend["date"])[::-1],
        y=list(trend["market_value"]) + list(trend["invested_capital"])[::-1],
        fill="toself",
        fillcolor="rgba(34,197,94,0.08)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False,
        hoverinfo="skip",
    ))

    fig.update_layout(
        template=_PLOTLY_TEMPLATE,
        xaxis_title="Date",
        yaxis_title="Value (USD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        margin=dict(t=40, b=40, l=40, r=20),
        height=450,
        yaxis=dict(tickprefix="$", tickformat=",.0f"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # ── Realized vs Unrealized breakdown ───────────────────────────────────
    st.markdown("### P&L Breakdown")
    pb1, pb2 = st.columns(2)
    realized = summary["realized_pnl"]
    unrealized = summary["unrealized_pnl"]
    pb1.metric(
        "Realized P&L",
        f"${realized:,.2f}",
        delta=f"{'+' if realized >= 0 else ''}{realized / total_invested * 100:.2f}%" if total_invested else None,
    )
    pb2.metric(
        "Unrealized P&L",
        f"${unrealized:,.2f}",
        delta=f"{'+' if unrealized >= 0 else ''}{unrealized / total_invested * 100:.2f}%" if total_invested else None,
    )
