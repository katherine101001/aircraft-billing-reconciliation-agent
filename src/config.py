"""Reads the reconciliation rules (assumptions.csv).

Governance requirement: all business inputs (rates, thresholds, dates, billing
rules) must be read from the data files, never hardcoded in code. This module
is the single place that reads assumptions.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

# Project root (one level above src/)
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"


def load_assumptions(path: Path | None = None) -> dict:
    """Read assumptions.csv into {key: value} (values kept as raw strings)."""
    path = path or (DATA_DIR / "assumptions.csv")
    assumptions: dict[str, str] = {}
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            assumptions[row["key"]] = row["value"]
    return assumptions


# ---------- Parse strongly-typed values from assumptions ----------

def as_float(assumptions: dict, key: str) -> float:
    return float(assumptions[key])


def as_int(assumptions: dict, key: str) -> int:
    return int(assumptions[key])


def as_date(assumptions: dict, key: str) -> date:
    return date.fromisoformat(assumptions[key])


def as_enum_set(assumptions: dict, key: str) -> set[str]:
    """Parse a comma-separated value like 'COMPLETED,DIVERTED' into a set."""
    return {s.strip() for s in assumptions[key].split(",")}
