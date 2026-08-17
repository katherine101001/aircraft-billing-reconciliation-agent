"""Billing rules: given a movement, compute every charge that *should* apply.

This is the core of the system. The rules all come from rate_card + assumptions;
no business number is hardcoded here.

4 charge types (unit rates are always looked up from rate_card, never written here):
  LANDING     quantity = ceil(mtow_tonnes), unit rate taken by arrival date
  PARKING     quantity = ceil(minutes beyond the free grace / 15), rate from rate_card
  AEROBRIDGE  quantity = ceil(duration minutes / 60), CONTACT stands only, rate from rate_card
  PSC         quantity = departing pax, rate by DOMESTIC/INTERNATIONAL

Status rules (checked before the above):
  CANCELLED   no charges
  DIVERTED    landing charge only
  COMPLETED   billed normally
"""
from __future__ import annotations

import math

from .config import as_enum_set, as_int
from .rate_card import lookup_rate


def compute_expected_charges(movement: dict, rate_df, assumptions: dict) -> list[dict]:
    """Return the list of charges this movement *should* incur.

    Each item is {charge_type, quantity, unit_rate, amount}; amount kept to 2 decimals.
    An empty list means the movement should incur nothing (e.g. CANCELLED).
    """
    status = movement["status"]
    billable = as_enum_set(assumptions, "billable_statuses")
    if status not in billable:
        return []  # CANCELLED and other non-billable statuses

    arrival = movement["arrival_datetime"]
    departure = movement["departure_datetime"]
    # Duration in minutes (correct even across midnight)
    dur_min = (departure - arrival).total_seconds() / 60.0
    arrival_date = arrival.date()

    free_min = as_int(assumptions, "free_parking_minutes")
    contact = assumptions["aerobridge_requires"].strip()  # "CONTACT"

    charges: list[dict] = []

    # 1) LANDING — applies to every billable status
    landing_qty = math.ceil(movement["mtow_tonnes"])
    landing_rate = lookup_rate(rate_df, "LANDING", "ANY", arrival_date)
    charges.append({
        "charge_type": "LANDING",
        "quantity": landing_qty,
        "unit_rate": landing_rate,
        "amount": round(landing_qty * landing_rate, 2),
    })

    # DIVERTED bills the landing charge only, everything else is waived
    diverted_charges = as_enum_set(assumptions, "diverted_billable_charges")
    if status == "DIVERTED":
        return charges

    # 2) PARKING — billed only beyond the free grace, per 15-minute block rounded up
    excess = dur_min - free_min
    if excess > 0:
        qty = math.ceil(excess / 15.0)
        rate = lookup_rate(rate_df, "PARKING", "ANY", arrival_date)
        charges.append({
            "charge_type": "PARKING",
            "quantity": qty,
            "unit_rate": rate,
            "amount": round(qty * rate, 2),
        })

    # 3) AEROBRIDGE — CONTACT stands only
    if movement["stand_type"] == contact:
        qty = math.ceil(dur_min / 60.0)
        rate = lookup_rate(rate_df, "AEROBRIDGE", contact, arrival_date)
        charges.append({
            "charge_type": "AEROBRIDGE",
            "quantity": qty,
            "unit_rate": rate,
            "amount": round(qty * rate, 2),
        })

    # 4) PSC — only when departing pax > 0 (cargo flights have 0, so none)
    if movement["pax_departing"] > 0:
        scope = movement["scope"]
        rate = lookup_rate(rate_df, "PSC", scope, arrival_date)
        charges.append({
            "charge_type": "PSC",
            "quantity": movement["pax_departing"],
            "unit_rate": rate,
            "amount": round(movement["pax_departing"] * rate, 2),
        })

    return charges
