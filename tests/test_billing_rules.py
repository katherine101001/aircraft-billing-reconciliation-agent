"""Boundary tests for billing_rules.compute_expected_charges.

Only tests the "how much should be charged" step, not the reconciliation comparison.
Covers: MTOW rounding up, date-sensitive unit rate, free parking grace, 15-minute blocks,
hourly-rounded aerobridge, CONTACT/REMOTE, PSC domestic/international/cargo, cancelled/
diverted, and overnight stays.
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


# ---------- LANDING: MTOW rounded up + date-sensitive unit rate ----------

def test_landing_ceil_rounds_up_fractional_mtow():
    m = make_movement(mtow_tonnes=411.3)
    assert _amount(_charges(m), "LANDING") == 4944.00  # ceil(411.3)=412 × 12.00


def test_landing_integer_mtow_unchanged():
    m = make_movement(mtow_tonnes=412.0)
    assert _amount(_charges(m), "LANDING") == 4944.00  # 412 × 12.00


def test_landing_rate_boundary_mar31_vs_apr1():
    # date-sensitive: 12.00/tonne on 3-31, 13.50/tonne from 4-01
    m1 = make_movement(arrival_datetime=datetime(2026, 3, 31, 14, 30))
    m2 = make_movement(arrival_datetime=datetime(2026, 4, 1, 14, 30))
    assert _amount(_charges(m1), "LANDING") == 4932.00  # 411 × 12.00 (default MTOW=411)
    assert _amount(_charges(m2), "LANDING") == 5548.50  # 411 × 13.50


# ---------- PARKING: 60-minute grace + 15-minute blocks rounded up ----------

def test_parking_inside_grace_is_free():
    m = make_movement(arrival_datetime=datetime(2026, 3, 1, 14, 0),
                      departure_datetime=datetime(2026, 3, 1, 15, 0))  # exactly 60 minutes
    assert _amount(_charges(m), "PARKING") == 0.0


def test_parking_one_minute_over_grace_charges_one_block():
    m = make_movement(departure_datetime=datetime(2026, 3, 1, 15, 31))  # 61 minutes
    assert _amount(_charges(m), "PARKING") == 8.00  # ceil(1/15)=1 × 8.00


def test_parking_exact_block_boundary():
    m = make_movement(departure_datetime=datetime(2026, 3, 1, 15, 45))  # 75 minutes → 15 over
    assert _amount(_charges(m), "PARKING") == 8.00  # ceil(15/15)=1


def test_parking_just_over_block_boundary_rounds_up():
    m = make_movement(departure_datetime=datetime(2026, 3, 1, 15, 46))  # 76 minutes → 16 over
    assert _amount(_charges(m), "PARKING") == 16.00  # ceil(16/15)=2


# ---------- AEROBRIDGE: CONTACT only + hourly rounding up ----------

def test_aerobridge_contact_one_hour():
    m = make_movement(departure_datetime=datetime(2026, 3, 1, 15, 30))  # 60 minutes
    assert _amount(_charges(m), "AEROBRIDGE") == 120.00  # ceil(60/60)=1 × 120


def test_aerobridge_hour_rounds_up():
    m = make_movement(departure_datetime=datetime(2026, 3, 1, 15, 31))  # 61 minutes
    assert _amount(_charges(m), "AEROBRIDGE") == 240.00  # ceil(61/60)=2 × 120


def test_aerobridge_remote_stand_not_charged():
    m = make_movement(stand_type="REMOTE", departure_datetime=datetime(2026, 3, 1, 16, 30))
    assert _amount(_charges(m), "AEROBRIDGE") == 0.0
    assert "AEROBRIDGE" not in _types(_charges(m))


# ---------- PSC: domestic 11 / international 35 / cargo (0 pax) not charged ----------

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


# ---------- Status rules ----------

def test_cancelled_has_no_charges():
    m = make_movement(status="CANCELLED")
    assert _charges(m) == []


def test_diverted_only_landing():
    m = make_movement(status="DIVERTED",
                      departure_datetime=datetime(2026, 3, 1, 16, 30))  # would otherwise park/use bridge
    assert _types(_charges(m)) == ["LANDING"]


# ---------- Overnight stay ----------

def test_overnight_turnaround_duration():
    m = make_movement(arrival_datetime=datetime(2026, 3, 1, 23, 30),
                      departure_datetime=datetime(2026, 3, 2, 1, 30))  # overnight, 120 minutes
    assert _amount(_charges(m), "PARKING") == 32.00  # over 60 → ceil(60/15)=4 × 8
