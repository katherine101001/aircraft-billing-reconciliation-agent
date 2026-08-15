"""费率卡 lookup_rate 的边界测试。

覆盖：日期敏感、精确条件优先于 ANY、窗口闭区间（含边界）、
开放结束哨兵 9999-12-31、找不到费率时报错。
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
    # effective_to=9999-12-31 是「开放结束」，远未来日期也应匹配
    assert lookup_rate(get_rate_df(), "LANDING", "ANY", date(2026, 12, 31)) == 13.50


def test_psc_exact_condition_preferred():
    assert lookup_rate(get_rate_df(), "PSC", "DOMESTIC", date(2026, 6, 1)) == 11.00
    assert lookup_rate(get_rate_df(), "PSC", "INTERNATIONAL", date(2026, 6, 1)) == 35.00


def test_window_bounds_are_inclusive():
    # effective_from 当天即生效（闭区间）
    assert lookup_rate(get_rate_df(), "PARKING", "ANY", date(2026, 1, 1)) == 8.00
    # LANDING 的第一档到 2026-03-31 当天仍生效（effective_to 含边界）
    assert lookup_rate(get_rate_df(), "LANDING", "ANY", date(2026, 3, 31)) == 12.00


def test_missing_rate_raises():
    # PSC 只有 DOMESTIC/INTERNATIONAL 两个条件，不存在 CARGO 或 ANY 兜底 → 应报错
    try:
        lookup_rate(get_rate_df(), "PSC", "CARGO", date(2026, 6, 1))
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass


def test_any_fallback_when_exact_condition_missing():
    # 构造一个只有 ANY 兜底行的费率表：查特定条件时，精确匹配失败 → 退回 ANY
    import pandas as pd
    df = pd.DataFrame([{
        "charge_type": "TEST",
        "condition": "ANY",
        "effective_from": date(2026, 1, 1),
        "effective_to": date(9999, 12, 31),
        "unit_rate": 9.99,
    }])
    assert lookup_rate(df, "TEST", "SPECIAL", date(2026, 6, 1)) == 9.99
