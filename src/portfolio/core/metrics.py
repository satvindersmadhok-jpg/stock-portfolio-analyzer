from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import List
from scipy.optimize import brentq

from .models import Transaction
from .calculator import build_holdings


def compute_xirr(transactions: List[Transaction], current_value: float, today: date) -> float | None:
    """
    XIRR via Brent's method.
    Cash flows: BUY = negative (money out), SELL = positive (money in).
    Final cash flow: +current_portfolio_value on today.
    Returns annualised rate or None if unable to converge.
    """
    cash_flows: list[tuple[date, float]] = []

    for tx in transactions:
        if tx.transaction_type.upper() == "BUY":
            cash_flows.append((tx.date, -tx.quantity * tx.price))
        else:
            cash_flows.append((tx.date, tx.quantity * tx.price))

    if not cash_flows:
        return None

    cash_flows.append((today, current_value))
    cf_df = pd.DataFrame(cash_flows, columns=["date", "amount"]).sort_values("date")
    t0 = cf_df["date"].iloc[0]
    days = [(d - t0).days for d in cf_df["date"]]
    amounts = cf_df["amount"].tolist()

    def npv(rate: float) -> float:
        return sum(a / (1 + rate) ** (d / 365.0) for a, d in zip(amounts, days))

    try:
        result = brentq(npv, -0.999, 100.0, maxiter=1000)
        return result
    except Exception:
        return None


def compute_portfolio_trend(
    transactions: List[Transaction],
    price_history: pd.DataFrame,
) -> pd.DataFrame:
    """
    Returns a DataFrame with columns: date, market_value, invested_capital.
    Reconstructs day-by-day portfolio by replaying transactions against historical prices.
    """
    if not transactions or price_history.empty:
        return pd.DataFrame(columns=["date", "market_value", "invested_capital"])

    sorted_txs = sorted(transactions, key=lambda t: t.date)
    start = sorted_txs[0].date
    end = date.today()

    all_dates = pd.date_range(start=start, end=end, freq="B").date
    rows = []
    holdings: dict[str, float] = {}   # ticker -> qty
    total_invested = 0.0

    tx_map: dict[date, list[Transaction]] = {}
    for tx in sorted_txs:
        tx_map.setdefault(tx.date, []).append(tx)

    for d in all_dates:
        for tx in tx_map.get(d, []):
            t = tx.ticker.upper()
            if tx.transaction_type.upper() == "BUY":
                holdings[t] = holdings.get(t, 0.0) + tx.quantity
                total_invested += tx.quantity * tx.price
            else:
                holdings[t] = max(0.0, holdings.get(t, 0.0) - tx.quantity)
                total_invested -= tx.quantity * tx.price  # reduce invested by cost basis approximation

        market_value = 0.0
        for ticker, qty in holdings.items():
            if qty <= 0:
                continue
            if ticker in price_history.columns:
                try:
                    price_series = price_history[ticker]
                    available = price_series[:d].dropna()
                    if not available.empty:
                        market_value += qty * float(available.iloc[-1])
                except Exception:
                    pass

        rows.append({"date": d, "market_value": market_value, "invested_capital": max(0.0, total_invested)})

    return pd.DataFrame(rows)


def compute_summary(transactions: List[Transaction], current_prices: dict[str, float]) -> dict:
    total_invested = sum(
        tx.quantity * tx.price for tx in transactions if tx.transaction_type.upper() == "BUY"
    )
    total_proceeds = sum(
        tx.quantity * tx.price for tx in transactions if tx.transaction_type.upper() == "SELL"
    )

    holdings, _ = build_holdings(transactions)
    active = holdings[holdings["quantity"] > 0]

    current_portfolio_value = sum(
        row["quantity"] * current_prices.get(row["ticker"], 0.0)
        for _, row in active.iterrows()
    )

    realized_pnl = holdings["realized_pnl"].sum()
    unrealized_pnl = sum(
        row["quantity"] * (current_prices.get(row["ticker"], 0.0) - row["avg_cost"])
        for _, row in active.iterrows()
    )
    total_return = realized_pnl + unrealized_pnl

    xirr = compute_xirr(transactions, current_portfolio_value, date.today())

    return {
        "total_invested": total_invested,
        "total_proceeds": total_proceeds,
        "current_portfolio_value": current_portfolio_value,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_return": total_return,
        "xirr": xirr,
    }
