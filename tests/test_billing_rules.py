"""计费规则 compute_expected_charges 的边界测试。

只测「应该收多少钱」这一步，不涉及对账对比。
覆盖：MTOW 向上取整、日期敏感单价、免费停车宽限、15 分钟一档、
按小时取整的廊桥、CONTACT/REMOTE、PSC 国内/国际/货机、取消/备降、跨天停留。
"""
from __future__ import annotations

from datetime import datetime

from src.billing_rules import compute_expected_charges
from tests._helpers import get_assumptions, get_rate_df, make_movement


def _charges(m, **asmp):
    return compute_expected_charges(m, get_rate_df(), get_assumptions(**asmp))


def _amount(charges, charge_type):
    return next((c["amount"] for c in charges if c["charge_type"] == charge_type), 0.0)


def _types(charges):
    return [c["charge_type"] for c in charges]


# ---------- LANDING：MTOW 向上取整 + 日期敏感单价 ----------

def test_landing_ceil_rounds_up_fractional_mtow():
    m = make_movement(mtow_tonnes=411.3)
    assert _amount(_charges(m), "LANDING") == 4944.00  # ceil(411.3)=412 × 12.00


def test_landing_integer_mtow_unchanged():
    m = make_movement(mtow_tonnes=412.0)
    assert _amount(_charges(m), "LANDING") == 4944.00  # 412 × 12.00


def test_landing_rate_boundary_mar31_vs_apr1():
    # 日期敏感：3-31 收 12.00/吨，4-01 起 13.50/吨
    m1 = make_movement(arrival_datetime=datetime(2026, 3, 31, 14, 30))
    m2 = make_movement(arrival_datetime=datetime(2026, 4, 1, 14, 30))
    assert _amount(_charges(m1), "LANDING") == 4932.00  # 411 × 12.00（默认 MTOW=411）
    assert _amount(_charges(m2), "LANDING") == 5548.50  # 411 × 13.50


# ---------- PARKING：60 分钟宽限 + 15 分钟一档向上取整 ----------

def test_parking_inside_grace_is_free():
    m = make_movement(arrival_datetime=datetime(2026, 3, 1, 14, 0),
                      departure_datetime=datetime(2026, 3, 1, 15, 0))  # 正好 60 分钟
    assert _amount(_charges(m), "PARKING") == 0.0


def test_parking_one_minute_over_grace_charges_one_block():
    m = make_movement(departure_datetime=datetime(2026, 3, 1, 15, 31))  # 61 分钟
    assert _amount(_charges(m), "PARKING") == 8.00  # ceil(1/15)=1 × 8.00


def test_parking_exact_block_boundary():
    m = make_movement(departure_datetime=datetime(2026, 3, 1, 15, 45))  # 75 分钟 → 超 15
    assert _amount(_charges(m), "PARKING") == 8.00  # ceil(15/15)=1


def test_parking_just_over_block_boundary_rounds_up():
    m = make_movement(departure_datetime=datetime(2026, 3, 1, 15, 46))  # 76 分钟 → 超 16
    assert _amount(_charges(m), "PARKING") == 16.00  # ceil(16/15)=2


# ---------- AEROBRIDGE：仅 CONTACT + 按小时向上取整 ----------

def test_aerobridge_contact_one_hour():
    m = make_movement(departure_datetime=datetime(2026, 3, 1, 15, 30))  # 60 分钟
    assert _amount(_charges(m), "AEROBRIDGE") == 120.00  # ceil(60/60)=1 × 120


def test_aerobridge_hour_rounds_up():
    m = make_movement(departure_datetime=datetime(2026, 3, 1, 15, 31))  # 61 分钟
    assert _amount(_charges(m), "AEROBRIDGE") == 240.00  # ceil(61/60)=2 × 120


def test_aerobridge_remote_stand_not_charged():
    m = make_movement(stand_type="REMOTE", departure_datetime=datetime(2026, 3, 1, 16, 30))
    assert _amount(_charges(m), "AEROBRIDGE") == 0.0
    assert "AEROBRIDGE" not in _types(_charges(m))


# ---------- PSC：国内 11 / 国际 35 / 货机 0 人不收 ----------

def test_psc_international():
    m = make_movement(pax_departing=298, scope="INTERNATIONAL")
    assert _amount(_charges(m), "PSC") == 10430.00  # 298 × 35


def test_psc_domestic():
    m = make_movement(pax_departing=203, scope="DOMESTIC")
    assert _amount(_charges(m), "PSC") == 2233.00  # 203 × 11


def test_psc_cargo_zero_pax_not_charged():
    m = make_movement(pax_departing=0, scope="INTERNATIONAL")
    assert _amount(_charges(m), "PSC") == 0.0
    assert "PSC" not in _types(_charges(m))


# ---------- 状态规则 ----------

def test_cancelled_has_no_charges():
    m = make_movement(status="CANCELLED")
    assert _charges(m) == []


def test_diverted_only_landing():
    m = make_movement(status="DIVERTED",
                      departure_datetime=datetime(2026, 3, 1, 16, 30))  # 本应停车/廊桥
    assert _types(_charges(m)) == ["LANDING"]


# ---------- 跨天停留 ----------

def test_overnight_turnaround_duration():
    m = make_movement(arrival_datetime=datetime(2026, 3, 1, 23, 30),
                      departure_datetime=datetime(2026, 3, 2, 1, 30))  # 跨天 120 分钟
    assert _amount(_charges(m), "PARKING") == 32.00  # 超 60 → ceil(60/15)=4 × 8
