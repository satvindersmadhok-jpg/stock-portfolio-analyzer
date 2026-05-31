from __future__ import annotations

import io
import pandas as pd
from typing import List

from ..core.models import Transaction


REQUIRED_COLS = {"ticker", "date", "transaction_type", "quantity", "price"}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase + strip column names, drop unnamed index columns."""
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    # Drop any column that looks like an unnamed row-index (e.g. "", "unnamed:_0")
    drop = [c for c in df.columns if c == "" or c.startswith("unnamed")]
    if drop:
        df = df.drop(columns=drop)
    return df


def parse_csv(file) -> tuple[List[Transaction], list[str]]:
    """
    Parse an uploaded CSV into Transaction objects.
    Handles: UTF-8 BOM, unnamed index columns, M/D/YYYY dates, mixed-case headers.
    Returns (transactions, errors).
    """
    errors: list[str] = []

    try:
        raw = file.read()
        # Decode and strip Excel BOM
        text = raw.decode("utf-8-sig").strip()

        # Fix: Excel sometimes wraps every row in outer quotes
        # e.g. '"1,AAPL,3/2/2024,BUY,10,185.07"' → '1,AAPL,3/2/2024,BUY,10,185.07'
        lines = text.splitlines()
        cleaned = []
        for line in lines:
            line = line.strip()
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1]
            cleaned.append(line)

        # Strip leading comma from header (e.g. ",Ticker,date,..." → "Ticker,date,...")
        if cleaned and cleaned[0].startswith(','):
            cleaned[0] = cleaned[0][1:]

        text = "\n".join(cleaned)

        df = pd.read_csv(io.StringIO(text))
    except Exception as e:
        return [], [f"Could not read CSV: {e}"]

    df = _normalize_columns(df)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        return [], [f"Missing columns: {', '.join(sorted(missing))}. Found: {', '.join(df.columns)}"]

    transactions: List[Transaction] = []
    for i, row in df.iterrows():
        row_num = i + 2  # 1-indexed + header row

        # Date — handles YYYY-MM-DD, M/D/YYYY, D/M/YYYY, etc.
        try:
            tx_date = pd.to_datetime(row["date"], dayfirst=False).date()
        except Exception:
            errors.append(f"Row {row_num}: invalid date '{row['date']}'")
            continue

        tx_type = str(row["transaction_type"]).strip().upper()
        if tx_type not in ("BUY", "SELL"):
            errors.append(f"Row {row_num}: transaction_type must be BUY or SELL, got '{tx_type}'")
            continue

        try:
            qty = float(row["quantity"])
            price = float(row["price"])
        except Exception:
            errors.append(f"Row {row_num}: quantity and price must be numbers")
            continue

        if qty <= 0 or price <= 0:
            errors.append(f"Row {row_num}: quantity and price must be positive")
            continue

        transactions.append(Transaction(
            date=tx_date,
            ticker=str(row["ticker"]).strip().upper(),
            transaction_type=tx_type,
            quantity=qty,
            price=price,
        ))

    return transactions, errors
