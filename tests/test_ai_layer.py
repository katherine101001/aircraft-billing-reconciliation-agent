"""ai_layer.py 的边界测试：异常→文案、方向措辞、错记航司特例、总结格式。

核心验证点：AI 层只「写文字」，数字全部来自传入的异常 dict / stats，不自算。
"""
from __future__ import annotations

from src.ai_layer import TYPE_PLAIN_LANGUAGE, explain_exception, summarize


def _exc(**kw):
    base = {
        "movement_id": "MOV00069",
        "invoice_line_id": "BL001",
        "exception_type": "MISSING_CHARGE",
        "charge_type": "PSC",
        "airline_code": "FX",
        "billed_airline_code": "",
        "expected_amount": 10430.0,
        "actual_amount": 0.0,
        "financial_impact_myr": 10430.0,
        "evidence_ref": "EVD-20260304-0069",
        "resolution_status": "OPEN",
        "credit_note_id": "",
    }
    base.update(kw)
    return base


def test_type_plain_language_covers_all_11_types():
    all_types = {
        "MISSING_CHARGE", "WRONG_RATE", "WRONG_QUANTITY", "WRONG_AMOUNT", "DUPLICATE",
        "ORPHAN_CHARGE", "WRONG_AIRLINE", "CANCELLED_CHARGED", "REMOTE_AEROBRIDGE",
        "DIVERTED_OVERCHARGE", "PSC_ON_CARGO",
    }
    assert set(TYPE_PLAIN_LANGUAGE.keys()) == all_types


def test_explain_includes_evidence_ref():
    assert "EVD-20260304-0069" in explain_exception(_exc())


def test_explain_positive_impact_says_underbilled():
    assert "应收未收" in explain_exception(_exc(financial_impact_myr=10430.0))


def test_explain_negative_impact_says_refund():
    text = explain_exception(_exc(exception_type="DUPLICATE", financial_impact_myr=-3780.0,
                                  expected_amount=0.0, actual_amount=3780.0))
    assert "应退" in text


def test_explain_zero_impact_says_net_zero():
    text = explain_exception(_exc(exception_type="WRONG_AMOUNT", financial_impact_myr=0.0))
    assert "净影响为零" in text


def test_explain_wrong_airline_mentions_refund_and_rebill():
    exc = _exc(exception_type="WRONG_AIRLINE", airline_code="FX", billed_airline_code="QC",
               charge_type="LANDING", financial_impact_myr=0.0, actual_amount=4944.0,
               expected_amount=4944.0)
    text = explain_exception(exc)
    assert "退款" in text
    assert "重新开票" in text


def test_explain_missing_evidence_says_none():
    assert "无" in explain_exception(_exc(evidence_ref=""))


def test_explain_unknown_type_falls_back_to_raw_type():
    assert "SOMETHING_NEW" in explain_exception(_exc(exception_type="SOMETHING_NEW"))


def test_summarize_formats_given_numbers_without_recomputing():
    stats = {
        "total_exceptions": 92,
        "net_impact": -24779.10,
        "positive_total": 58824.70,
        "negative_total": -83603.80,
        "open_count": 87,
        "by_type": {"MISSING_CHARGE": (20, 42821.00), "DUPLICATE": (8, -16332.00)},
    }
    md = summarize(stats)
    assert "92" in md
    assert "-24,779.10" in md
    assert "58,824.70" in md
    assert "83,603.80" in md
    assert "MISSING_CHARGE" in md
    assert "DUPLICATE" in md
