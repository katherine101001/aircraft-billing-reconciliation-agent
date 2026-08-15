"""计费规则：给定一次起降，算出「应该收取」的每一项费用。

这是整个系统的核心。规则全部来自 rate_card + assumptions，
这里不出现任何硬编码的业务数字。

4 种费用（单价一律从 rate_card 查，此处不写死数值）：
  LANDING     数量 = ceil(mtow_tonnes)，单价按到达日期取
  PARKING     数量 = ceil(超出免费时长的分钟 / 15)，单价见 rate_card
  AEROBRIDGE  数量 = ceil(停留分钟 / 60)，仅 CONTACT 机位，单价见 rate_card
  PSC         数量 = 离港旅客数，单价按 DOMESTIC/INTERNATIONAL 取

状态规则（先于上面判断）：
  CANCELLED   不计费
  DIVERTED    只收起降费 LANDING
  COMPLETED   正常计费
"""
from __future__ import annotations

import math

from .config import as_enum_set, as_int
from .rate_card import lookup_rate


def compute_expected_charges(movement: dict, rate_df, assumptions: dict) -> list[dict]:
    """返回该 movement 应该产生的费用列表。

    每项形如 {charge_type, quantity, unit_rate, amount}，amount 保留 2 位小数。
    返回空列表表示该 movement 不应产生任何费用（如 CANCELLED）。
    """
    status = movement["status"]
    billable = as_enum_set(assumptions, "billable_statuses")
    if status not in billable:
        return []  # CANCELLED 等不可计费状态

    arrival = movement["arrival_datetime"]
    departure = movement["departure_datetime"]
    # 停留时长（分钟），跨天也正确
    dur_min = (departure - arrival).total_seconds() / 60.0
    arrival_date = arrival.date()

    free_min = as_int(assumptions, "free_parking_minutes")
    contact = assumptions["aerobridge_requires"].strip()  # "CONTACT"

    charges: list[dict] = []

    # 1) LANDING —— 所有可计费状态都收
    landing_qty = math.ceil(movement["mtow_tonnes"])
    landing_rate = lookup_rate(rate_df, "LANDING", "ANY", arrival_date)
    charges.append({
        "charge_type": "LANDING",
        "quantity": landing_qty,
        "unit_rate": landing_rate,
        "amount": round(landing_qty * landing_rate, 2),
    })

    # DIVERTED 只收起降费，其余全免
    diverted_charges = as_enum_set(assumptions, "diverted_billable_charges")
    if status == "DIVERTED":
        return charges

    # 2) PARKING —— 超出免费时长才收，每 15 分钟一档向上取整
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

    # 3) AEROBRIDGE —— 仅 CONTACT 机位
    if movement["stand_type"] == contact:
        qty = math.ceil(dur_min / 60.0)
        rate = lookup_rate(rate_df, "AEROBRIDGE", contact, arrival_date)
        charges.append({
            "charge_type": "AEROBRIDGE",
            "quantity": qty,
            "unit_rate": rate,
            "amount": round(qty * rate, 2),
        })

    # 4) PSC —— 仅离港旅客 > 0（货机为 0，不收）
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
