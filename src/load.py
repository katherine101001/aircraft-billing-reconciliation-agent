"""Loads the 6 data tables.

The data is provided as both CSV and Excel; here we uniformly read CSV
(the two hold the same content).
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from .config import DATA_DIR


def load_movements() -> pd.DataFrame:
    """Movement log. arrival/departure parsed as pandas timestamps."""
    df = pd.read_csv(DATA_DIR / "movements.csv", encoding="utf-8-sig")
    df["arrival_datetime"] = pd.to_datetime(df["arrival_datetime"])
    df["departure_datetime"] = pd.to_datetime(df["departure_datetime"])
    return df


def load_billing_ledger() -> pd.DataFrame:
    """Billing ledger. movement_id may point to a movement that does not exist."""
    return pd.read_csv(DATA_DIR / "billing_ledger.csv", encoding="utf-8-sig")


def load_rate_card() -> pd.DataFrame:
    """Rate card. effective_from/effective_to converted to date for window matching."""
    df = pd.read_csv(DATA_DIR / "rate_card.csv", encoding="utf-8-sig")
    # Use native date parsing (pandas nanosecond timestamps can't hold the 9999-12-31 "open-ended" sentinel)
    df["effective_from"] = df["effective_from"].apply(date.fromisoformat)
    df["effective_to"] = df["effective_to"].apply(date.fromisoformat)
    return df


def load_airlines() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "airlines.csv", encoding="utf-8-sig")


def load_credit_notes() -> list[dict]:
    """Credit notes, returned as list[dict] for matching by related_invoice_line_id."""
    df = pd.read_csv(DATA_DIR / "credit_notes.csv", encoding="utf-8-sig")
    df["related_invoice_line_id"] = df["related_invoice_line_id"].fillna("").astype(str)
    return df.to_dict("records")
