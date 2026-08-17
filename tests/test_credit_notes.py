"""Boundary tests for resolve_credit_notes.

Covers: exact line match, full amount coverage, currency must be MYR, blank line id does not
resolve, non-matching line id does not resolve, partial-then-full coverage, and exceptions
without a line id cannot be resolved.
"""
from __future__ import annotations

from src.reconcile import resolve_credit_notes
from tests._helpers import make_credit_note


def _exc(**kw):
    base = {
        "movement_id": "MOV00001",
        "invoice_line_id": "BL123",
        "exception_type": "DUPLICATE",
        "charge_type": "LANDING",
        "airline_code": "FX",
        "billed_airline_code": "",
        "expected_amount": 0.0,
        "actual_amount": 3780.0,
        "financial_impact_myr": -3780.0,
        "evidence_ref": "EVD-1",
        "resolution_status": "OPEN",
        "credit_note_id": "",
    }
    base.update(kw)
    return base


def test_exact_match_and_full_cover_resolves():
    exc = _exc()
    resolve_credit_notes([exc], [make_credit_note(related_invoice_line_id="BL123", amount=3780.0)])
    assert exc["resolution_status"] == "RESOLVED_BY_CREDIT_NOTE"
    assert exc["credit_note_id"] == "CN-TEST-01"


def test_amount_too_small_stays_open():
    exc = _exc()
    resolve_credit_notes([exc], [make_credit_note(related_invoice_line_id="BL123", amount=3779.99)])
    assert exc["resolution_status"] == "OPEN"


def test_wrong_currency_stays_open():
    exc = _exc()
    resolve_credit_notes([exc], [make_credit_note(related_invoice_line_id="BL123",
                                                  amount=3780.0, currency="USD")])
    assert exc["resolution_status"] == "OPEN"


def test_blank_line_id_does_not_resolve():
    exc = _exc()
    resolve_credit_notes([exc], [make_credit_note(related_invoice_line_id="", amount=9999.0)])
    assert exc["resolution_status"] == "OPEN"


def test_different_line_id_does_not_resolve():
    exc = _exc()  # invoice_line_id = BL123
    resolve_credit_notes([exc], [make_credit_note(related_invoice_line_id="BL999", amount=3780.0)])
    assert exc["resolution_status"] == "OPEN"


def test_exception_without_line_id_cannot_be_resolved():
    exc = _exc(invoice_line_id="", exception_type="MISSING_CHARGE", financial_impact_myr=4944.0)
    resolve_credit_notes([exc], [make_credit_note(related_invoice_line_id="BL123", amount=4944.0)])
    assert exc["resolution_status"] == "OPEN"


def test_partial_then_full_cover_resolves():
    exc = _exc()
    cns = [
        make_credit_note(cn_id="CN-SMALL", related_invoice_line_id="BL123", amount=1000.0),
        make_credit_note(cn_id="CN-FULL", related_invoice_line_id="BL123", amount=3780.0),
    ]
    resolve_credit_notes([exc], cns)
    assert exc["resolution_status"] == "RESOLVED_BY_CREDIT_NOTE"
    assert exc["credit_note_id"] == "CN-FULL"
