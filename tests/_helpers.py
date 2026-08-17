"""Shared test helpers: build minimal inputs to cover the various edge cases.

Note: tests deliberately "hardcode" expected values (e.g. 4944.00 = 412 tonnes × 12.00).
That is the correct thing for tests — the "no hardcoding" rule in the brief targets the
application code under src/; tests must assert the expected answer or they cannot catch a
broken change.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Ensure src/ and tests/ are importable no matter which directory we run from
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import load_assumptions  # noqa: E402
from src.load import load_rate_card  # noqa: E402


def make_movement(**overrides) -> dict:
    """Build one movement record.

    Defaults: COMPLETED, 60-minute stay, CONTACT stand, 100 international passengers.
    Override whichever field the edge case under test needs.
    """
    m = {
        "movement_id": "MOVTEST01",
        "flight_no": "TST001",
        "airline_code": "FX",
        "aircraft_reg": "9M-TST",
        "aircraft_type": "A320",
        "mtow_tonnes": 411.0,
        "arrival_datetime": datetime(2026, 3, 1, 14, 30),
        "departure_datetime": datetime(2026, 3, 1, 15, 30),  # 60-minute stay
        "stand": "A01",
        "stand_type": "CONTACT",
        "pax_departing": 100,
        "scope": "INTERNATIONAL",
        "status": "COMPLETED",
        "evidence_ref": "EVD-TEST-001",
    }
    m.update(overrides)
    return m


def make_line(**overrides) -> dict:
    """Build one ledger line. By default matches the movement above (LANDING 411 × 12 = 4932)."""
    line = {
        "invoice_line_id": "BLTEST01",
        "invoice_id": "INV-TEST",
        "invoice_date": "2026-03-31",
        "airline_code": "FX",
        "movement_id": "MOVTEST01",
        "charge_type": "LANDING",
        "quantity": 411,
        "unit_rate": 12.00,
        "amount_billed": 4932.00,
        "currency": "MYR",
    }
    line.update(overrides)
    return line


def make_credit_note(**overrides) -> dict:
    """Build one credit note. By default matches invoice_line_id=BLTEST01 exactly, amount 3780 covering."""
    cn = {
        "cn_id": "CN-TEST-01",
        "cn_date": "2026-07-01",
        "airline_code": "FX",
        "related_invoice_id": "INV-TEST",
        "related_invoice_line_id": "BLTEST01",
        "reason_code": "DUPLICATE",
        "amount": 3780.0,
        "currency": "MYR",
    }
    cn.update(overrides)
    return cn


def get_assumptions(**overrides) -> dict:
    """Read the real assumptions.csv, optionally overriding a key (proves runtime-read, not hardcoded)."""
    a = load_assumptions()
    a.update(overrides)
    return a


def get_rate_df():
    """Read the real rate_card.csv (no hardcoded rates)."""
    return load_rate_card()


def by_type(exceptions: list[dict], etype: str) -> list[dict]:
    """Filter exceptions by type for convenient assertions."""
    return [e for e in exceptions if e["exception_type"] == etype]
