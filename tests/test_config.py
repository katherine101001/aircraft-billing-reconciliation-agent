"""Boundary tests for config.py: reading assumptions + the strongly-typed parse helpers."""
from __future__ import annotations

from datetime import date

from src.config import as_date, as_enum_set, as_float, as_int, load_assumptions


def test_load_assumptions_reads_real_file():
    a = load_assumptions()
    assert a["amount_tolerance"] == "0.05"
    assert a["free_parking_minutes"] == "60"
    assert a["data_snapshot_date"] == "2026-07-01"


def test_as_float():
    assert as_float({"k": "0.05"}, "k") == 0.05


def test_as_int():
    assert as_int({"k": "60"}, "k") == 60


def test_as_date():
    assert as_date({"k": "2026-07-01"}, "k") == date(2026, 7, 1)


def test_as_enum_set_single():
    assert as_enum_set({"k": "LANDING"}, "k") == {"LANDING"}


def test_as_enum_set_multiple():
    assert as_enum_set({"k": "COMPLETED,DIVERTED"}, "k") == {"COMPLETED", "DIVERTED"}


def test_as_enum_set_strips_whitespace():
    assert as_enum_set({"k": " A , B ,C "}, "k") == {"A", "B", "C"}
