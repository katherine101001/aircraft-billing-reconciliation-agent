"""Boundary tests for rate_card.lookup_rate.

Covers: date-sensitive rates, exact condition preferred over ANY, closed window bounds
(inclusive), the open-ended 9999-12-31 sentinel, and error on missing rate.
"""
from __future__ import annotations

from datetime import date

from src.rate_card import lookup_rate
from tests._helpers import get_rate_df


def test_landing_rate_before_apr():
    assert lookup_rate(get_rate_df(), "LANDING", "ANY", date(2026, 3, 31)) == 12.00


def test_landing_rate_from_apr():
    assert lookup_rate(get_rate_df(), "LANDING", "ANY", date(2026, 4, 1)) == 13.50


def test_landing_rate_far_future_open_ended():
    # effective_to=9999-12-31 is "open-ended"; far-future dates should still match
    assert lookup_rate(get_rate_df(), "LANDING", "ANY", date(2026, 12, 31)) == 13.50


def test_psc_exact_condition_preferred():
    assert lookup_rate(get_rate_df(), "PSC", "DOMESTIC", date(2026, 6, 1)) == 11.00
    assert lookup_rate(get_rate_df(), "PSC", "INTERNATIONAL", date(2026, 6, 1)) == 35.00


def test_window_bounds_are_inclusive():
    # effective_from takes effect on that same day (closed interval)
    assert lookup_rate(get_rate_df(), "PARKING", "ANY", date(2026, 1, 1)) == 8.00
    # LANDING's first tier is still in force on 2026-03-31 itself (effective_to is inclusive)
    assert lookup_rate(get_rate_df(), "LANDING", "ANY", date(2026, 3, 31)) == 12.00


def test_missing_rate_raises():
    # PSC only has DOMESTIC/INTERNATIONAL conditions; no CARGO or ANY fallback → should error
    try:
        lookup_rate(get_rate_df(), "PSC", "CARGO", date(2026, 6, 1))
        assert False, "should raise ValueError"
    except ValueError:
        pass


def test_any_fallback_when_exact_condition_missing():
    # Build a rate table with only an ANY fallback: a specific condition misses exact match → falls back to ANY
    import pandas as pd
    df = pd.DataFrame([{
        "charge_type": "TEST",
        "condition": "ANY",
        "effective_from": date(2026, 1, 1),
        "effective_to": date(9999, 12, 31),
        "unit_rate": 9.99,
    }])
    assert lookup_rate(df, "TEST", "SPECIAL", date(2026, 6, 1)) == 9.99
