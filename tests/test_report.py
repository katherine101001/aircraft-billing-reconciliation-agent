"""report.py 的边界测试：统计（build_stats）、样例挑选（_pick_examples）、落盘（write_report）。

write_report 通过临时目录 + 重定向 stdout 测试，不污染真实 output/。
"""
from __future__ import annotations

import contextlib
import csv
import io
import tempfile
from pathlib import Path

import src.report as report
from src.report import _pick_examples, build_stats


def _exc(**kw):
    base = {
        "movement_id": "MOV00001", "invoice_line_id": "", "exception_type": "MISSING_CHARGE",
        "charge_type": "LANDING", "airline_code": "FX", "billed_airline_code": "",
        "expected_amount": 4944.0, "actual_amount": 0.0, "financial_impact_myr": 4944.0,
        "evidence_ref": "EVD-1", "resolution_status": "OPEN", "credit_note_id": "",
    }
    base.update(kw)
    return base


def test_build_stats_counts_and_sums():
    exc = [
        _exc(financial_impact_myr=100.0, exception_type="MISSING_CHARGE"),
        _exc(financial_impact_myr=-50.0, exception_type="DUPLICATE",
             resolution_status="RESOLVED_BY_CREDIT_NOTE"),
        _exc(financial_impact_myr=-25.0, exception_type="DUPLICATE"),
    ]
    s = build_stats(exc)
    assert s["total_exceptions"] == 3
    assert s["net_impact"] == 25.0
    assert s["positive_total"] == 100.0
    assert s["negative_total"] == -75.0
    assert s["open_count"] == 2
    assert s["by_type"]["MISSING_CHARGE"] == (1, 100.0)
    assert s["by_type"]["DUPLICATE"] == (2, -75.0)


def test_pick_examples_distinct_types_within_max():
    exc = [
        _exc(exception_type="MISSING_CHARGE", financial_impact_myr=1000.0),
        _exc(exception_type="MISSING_CHARGE", financial_impact_myr=2000.0),
        _exc(exception_type="DUPLICATE", financial_impact_myr=-500.0),
        _exc(exception_type="WRONG_AIRLINE", financial_impact_myr=0.0),
    ]
    picked = _pick_examples(exc, max_n=8)
    types = [e["exception_type"] for e in picked]
    assert len(types) == len(set(types)) == 3  # 3 种类型各选 1，不重复
    assert set(types) == {"MISSING_CHARGE", "DUPLICATE", "WRONG_AIRLINE"}


def test_pick_examples_prefers_larger_absolute_impact():
    exc = [
        _exc(exception_type="A", financial_impact_myr=10.0),
        _exc(exception_type="B", financial_impact_myr=1000.0),
    ]
    assert _pick_examples(exc, max_n=8)[0]["exception_type"] == "B"


def _with_report(exc, check):
    """在临时目录里跑 write_report，并在目录仍存活时执行 check（读取落盘文件）。

    TemporaryDirectory 退出 with 块就会删目录，所以读取必须发生在 with 之内。
    """
    with tempfile.TemporaryDirectory() as d:
        old = report.OUTPUT_DIR
        report.OUTPUT_DIR = Path(d)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                report.write_report(exc, {})
            check(Path(d))
        finally:
            report.OUTPUT_DIR = old


def test_write_report_writes_csv_and_summary():
    def check(d):
        rows = list(csv.DictReader(open(d / "exceptions.csv", encoding="utf-8-sig")))
        assert len(rows) == 1
        assert rows[0]["movement_id"] == "MOV00001"
        assert rows[0]["exception_type"] == "MISSING_CHARGE"
        assert (d / "summary.md").exists()
    _with_report([_exc()], check)


def test_write_report_empty_exceptions_still_writes_header():
    def check(d):
        rows = list(csv.DictReader(open(d / "exceptions.csv", encoding="utf-8-sig")))
        assert len(rows) == 0  # 只有表头，无数据行（覆盖 examples 为空的分支）
        assert (d / "summary.md").exists()
    _with_report([], check)
