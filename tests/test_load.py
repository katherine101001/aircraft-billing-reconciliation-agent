"""Boundary tests for load.py: date parsing, the 9999-12-31 sentinel, credit-note blank
line-id fill, and column completeness."""
from __future__ import annotations

from datetime import date

import pandas as pd

from src.load import (
    load_airlines,
    load_billing_ledger,
    load_credit_notes,
    load_movements,
    load_rate_card,
)


def test_load_movements_parses_datetimes():
    df = load_movements()
    assert not df.empty
    assert pd.api.types.is_datetime64_any_dtype(df["arrival_datetime"])
    assert pd.api.types.is_datetime64_any_dtype(df["departure_datetime"])


def test_load_rate_card_handles_open_ended_sentinel():
    # Key: the 9999-12-31 sentinel parses without overflow (pandas nanosecond cap is ~year 2262)
    df = load_rate_card()
    assert df["effective_to"].max() == date(9999, 12, 31)
    assert all(isinstance(d, date) for d in df["effective_from"])
    assert all(isinstance(d, date) for d in df["effective_to"])


def test_load_credit_notes_line_id_are_strings():
    notes = load_credit_notes()
    assert len(notes) > 0
    for n in notes:
        assert isinstance(n["related_invoice_line_id"], str)


def test_load_billing_ledger_has_required_columns():
    df = load_billing_ledger()
    for col in ["invoice_line_id", "movement_id", "charge_type", "quantity", "unit_rate", "amount_billed"]:
        assert col in df.columns


def test_load_airlines_has_code_and_name():
    df = load_airlines()
    assert not df.empty
    assert "airline_code" in df.columns
    assert "airline_name" in df.columns
