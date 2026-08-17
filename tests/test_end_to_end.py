"""End-to-end integration tests: run the full pipeline on the real 6 tables and assert the
deterministic results.

These "anchor numbers" come from one correct run; any change that breaks the logic will
make them mismatch.
"""
from __future__ import annotations

from src.config import load_assumptions
from src.load import load_billing_ledger, load_credit_notes, load_movements, load_rate_card
from src.reconcile import reconcile, resolve_credit_notes


def _run_full():
    assumptions = load_assumptions()
    rate_df = load_rate_card()
    movements = load_movements().to_dict("records")
    ledger = load_billing_ledger().to_dict("records")
    credit_notes = load_credit_notes()
    exc = reconcile(movements, ledger, rate_df, assumptions)
    exc = resolve_credit_notes(exc, credit_notes)
    return exc


def test_end_to_end_total_count():
    exc = _run_full()
    assert len(exc) == 92, f"expected 92 exceptions, got {len(exc)}"


def test_end_to_end_net_impact():
    exc = _run_full()
    total = round(sum(e["financial_impact_myr"] for e in exc), 2)
    assert total == -24779.10, f"expected net impact -24779.10, got {total}"


def test_end_to_end_resolved_count():
    exc = _run_full()
    resolved = sum(1 for e in exc if e["resolution_status"] == "RESOLVED_BY_CREDIT_NOTE")
    assert resolved == 5, f"expected 5 resolved by credit note, got {resolved}"


def test_end_to_end_wrong_airline_net_zero():
    exc = _run_full()
    wa_total = round(sum(e["financial_impact_myr"] for e in exc
                         if e["exception_type"] == "WRONG_AIRLINE"), 2)
    assert wa_total == 0.0, f"wrong-airline net impact should be 0, got {wa_total}"


def test_end_to_end_no_rounding_false_alarm():
    exc = _run_full()
    small = [e for e in exc if e["exception_type"] != "WRONG_AIRLINE"
             and 0 < abs(e["financial_impact_myr"]) <= 0.05]
    assert small == [], f"rounding false alarms ≤0.05 exist: {small}"


# ---------- Global invariants (property checks over the whole output) ----------

def test_invariant_net_equals_positive_plus_negative():
    exc = _run_full()
    pos = round(sum(e["financial_impact_myr"] for e in exc if e["financial_impact_myr"] > 0), 2)
    neg = round(sum(e["financial_impact_myr"] for e in exc if e["financial_impact_myr"] < 0), 2)
    net = round(sum(e["financial_impact_myr"] for e in exc), 2)
    assert round(pos + neg, 2) == net


def test_invariant_sign_convention_by_type():
    exc = _run_full()
    overcharge_types = {"DUPLICATE", "ORPHAN_CHARGE", "CANCELLED_CHARGED",
                        "REMOTE_AEROBRIDGE", "DIVERTED_OVERCHARGE", "PSC_ON_CARGO"}
    for e in exc:
        if e["exception_type"] in overcharge_types:
            assert e["financial_impact_myr"] < 0, f"{e['exception_type']} should be negative (over-billed)"
        if e["exception_type"] == "MISSING_CHARGE":
            assert e["financial_impact_myr"] > 0, "missed charge should be positive (under-billed)"
        if e["exception_type"] == "WRONG_AIRLINE":
            assert e["financial_impact_myr"] == 0.0


def test_invariant_evidence_attached_except_orphan():
    exc = _run_full()
    for e in exc:
        if e["exception_type"] != "ORPHAN_CHARGE":
            assert e["evidence_ref"], f"{e['exception_type']} should carry an evidence ref"


def test_invariant_all_required_fields_present():
    exc = _run_full()
    required = ["movement_id", "invoice_line_id", "exception_type", "charge_type",
                "airline_code", "billed_airline_code", "expected_amount",
                "actual_amount", "financial_impact_myr", "evidence_ref",
                "resolution_status", "credit_note_id"]
    for e in exc:
        for k in required:
            assert k in e, f"missing field {k}"
