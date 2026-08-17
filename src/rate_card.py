"""Look up a unit rate from the rate card by (charge_type, condition, date).

This is where the "date-sensitive rate" lands: the LANDING unit rate changes with the
arrival date (rate_card.csv has two effective windows), matched via the
effective_from/effective_to window.
"""
from __future__ import annotations

from datetime import date

import pandas as pd


def lookup_rate(rate_df: pd.DataFrame, charge_type: str, condition: str, d: date) -> float:
    """Return the unit rate (MYR) for a charge_type on a given date under a condition.

    Match order: first filter candidate rows by charge_type + date window;
    then prefer an exact condition match, falling back to 'ANY'.
    """
    cand = rate_df[
        (rate_df["charge_type"] == charge_type)
        & (rate_df["effective_from"] <= d)
        & (rate_df["effective_to"] >= d)
    ]

    exact = cand[cand["condition"] == condition]
    if not exact.empty:
        return round(float(exact.iloc[0]["unit_rate"]), 2)

    any_row = cand[cand["condition"] == "ANY"]
    if not any_row.empty:
        return round(float(any_row.iloc[0]["unit_rate"]), 2)

    raise ValueError(
        f"No rate found for {charge_type}/{condition} @ {d} in the rate card"
    )
