from __future__ import annotations

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date, timedelta
from typing import List


@st.cache_data(ttl=300)
def fetch_current_prices(tickers: tuple[str, ...]) -> dict[str, float]:
    """Fetch latest closing price for each ticker."""
    prices = {}
    if not tickers:
        return prices
    data = yf.download(list(tickers), period="2d", auto_adjust=True, progress=False)
    if data.empty:
        return prices
    close = data["Close"] if "Close" in data.columns else data
    for ticker in tickers:
        try:
            col = close[ticker] if ticker in close.columns else close
            val = col.dropna().iloc[-1]
            prices[ticker] = float(val)
        except Exception:
            prices[ticker] = 0.0
    return prices


@st.cache_data(ttl=3600)
def fetch_price_history(
    tickers: tuple[str, ...],
    start: date,
    end: date,
) -> pd.DataFrame:
    """
    Returns a DataFrame indexed by date with one column per ticker (closing prices).
    """
    if not tickers:
        return pd.DataFrame()
    data = yf.download(
        list(tickers),
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        auto_adjust=True,
        progress=False,
    )
    if data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"]
    else:
        close = data[["Close"]].rename(columns={"Close": tickers[0]})

    close.index = pd.to_datetime(close.index).date
    return close
