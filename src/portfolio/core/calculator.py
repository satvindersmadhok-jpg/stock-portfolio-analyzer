from __future__ import annotations

import pandas as pd
from typing import List, Dict
from .models import Transaction


def build_holdings(transactions: List[Transaction]) -> tuple[pd.DataFrame, list[str]]:
    """
    Returns (holdings_df, warnings).
    holdings_df has one row per ticker: quantity, avg_cost, total_cost, realized_pnl.
    Uses weighted-average cost basis. Warns on oversell.
    """
    state: Dict[str, dict] = {}
    warnings: list[str] = []

    for tx in sorted(transactions, key=lambda t: t.date):
        ticker = tx.ticker.upper()
        if ticker not in state:
            state[ticker] = {"quantity": 0.0, "total_cost": 0.0, "realized_pnl": 0.0}

        s = state[ticker]

        if tx.transaction_type.upper() == "BUY":
            s["total_cost"] += tx.quantity * tx.price
            s["quantity"] += tx.quantity
        else:  # SELL
            if tx.quantity > s["quantity"] + 1e-9:
                warnings.append(
                    f"{ticker} on {tx.date}: tried to sell {tx.quantity:.4g} "
                    f"but only {s['quantity']:.4g} held — capped at available quantity."
                )
                tx = type(tx)(tx.date, tx.ticker, tx.transaction_type, s["quantity"], tx.price)
            if s["quantity"] > 0:
                avg_cost = s["total_cost"] / s["quantity"]
                s["realized_pnl"] += tx.quantity * (tx.price - avg_cost)
                s["total_cost"] -= avg_cost * tx.quantity
                s["quantity"] -= tx.quantity
                if s["quantity"] < 1e-9:
                    s["quantity"] = 0.0
                    s["total_cost"] = 0.0

    rows = []
    for ticker, s in state.items():
        qty = s["quantity"]
        cost = s["total_cost"]
        rows.append({
            "ticker": ticker,
            "quantity": qty,
            "avg_cost": (cost / qty) if qty > 0 else 0.0,
            "total_cost": cost,
            "realized_pnl": s["realized_pnl"],
        })

    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["ticker", "quantity", "avg_cost", "total_cost", "realized_pnl"]
    )
    return df, warnings


def active_holdings(holdings: pd.DataFrame) -> pd.DataFrame:
    """Filters to tickers where quantity > 0."""
    return holdings[holdings["quantity"] > 0].copy()


def transactions_to_df(transactions: List[Transaction]) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame(columns=["date", "ticker", "transaction_type", "quantity", "price"])
    return pd.DataFrame([
        {
            "date": t.date,
            "ticker": t.ticker.upper(),
            "transaction_type": t.transaction_type.upper(),
            "quantity": t.quantity,
            "price": t.price,
        }
        for t in transactions
    ]).sort_values("date", ascending=False).reset_index(drop=True)
