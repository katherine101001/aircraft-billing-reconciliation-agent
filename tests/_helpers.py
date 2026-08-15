"""测试共用工具：构造最小化的输入数据，方便覆盖各种边界情况。

说明：测试里会「硬编码」期望值（如 4944.00 = 412 吨 × 12.00）。
这是测试的正当做法 —— 题目禁止的「硬编码」针对的是 src/ 里的应用代码；
测试本来就要断言「期望答案」，否则无法发现代码改坏。
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# 无论从哪个目录运行，都保证能 import 到 src/ 与 tests/
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import load_assumptions  # noqa: E402
from src.load import load_rate_card  # noqa: E402


def make_movement(**overrides) -> dict:
    """构造一条起降记录。

    默认值：正常完成(COMPLETED)、停留 60 分钟、CONTACT 机位、100 名国际旅客。
    测哪个边界就覆盖哪个字段。
    """
    m = {
        "movement_id": "MOVTEST01",
        "flight_no": "TST001",
        "airline_code": "FX",
        "aircraft_reg": "9M-TST",
        "aircraft_type": "A320",
        "mtow_tonnes": 411.0,
        "arrival_datetime": datetime(2026, 3, 1, 14, 30),
        "departure_datetime": datetime(2026, 3, 1, 15, 30),  # 停留 60 分钟
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
    """构造一条账单行。默认与上面的默认 movement 匹配（LANDING 411 × 12 = 4932）。"""
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
    """构造一张冲销单。默认与 invoice_line_id=BLTEST01 精确匹配、金额 3780 覆盖。"""
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
    """读取真实 assumptions.csv，可临时覆盖某个键（测「运行时读取、非硬编码」）。"""
    a = load_assumptions()
    a.update(overrides)
    return a


def get_rate_df():
    """读取真实 rate_card.csv（不硬编码费率）。"""
    return load_rate_card()


def by_type(exceptions: list[dict], etype: str) -> list[dict]:
    """按异常类型筛选，方便断言。"""
    return [e for e in exceptions if e["exception_type"] == etype]
