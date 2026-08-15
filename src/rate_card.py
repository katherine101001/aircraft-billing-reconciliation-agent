"""按 (charge_type, condition, 日期) 从费率卡查单价。

这是「日期敏感费率」的落地点：LANDING 的单价随到达日期变化（rate_card.csv
里有两档 effective 窗口），通过 effective_from/effective_to 窗口匹配。
"""
from __future__ import annotations

from datetime import date

import pandas as pd


def lookup_rate(rate_df: pd.DataFrame, charge_type: str, condition: str, d: date) -> float:
    """返回某 charge_type 在某日期、某条件下的单价（MYR）。

    匹配顺序：先按 charge_type + 日期窗口筛出候选行；
    再优先精确匹配 condition，退而求其次匹配 'ANY'。
    """
    cand = rate_df[
        (rate_df["charge_type"] == charge_type)
        & (rate_df["effective_from"] <= d)
        & (rate_df["effective_to"] >= d)
    ]

    exact = cand[cand["condition"] == condition]
    if not exact.empty:
        return round(float(exact.iloc[0]["unit_rate"]), 2)

    any_row = cand[cand["condition"] == "ANY"]
    if not any_row.empty:
        return round(float(any_row.iloc[0]["unit_rate"]), 2)

    raise ValueError(
        f"费率卡中找不到 {charge_type}/{condition} @ {d} 的单价"
    )
