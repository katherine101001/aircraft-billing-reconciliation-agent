"""加载 6 张数据表。

数据同时以 CSV 和 Excel 提供，这里统一读 CSV（内容一致）。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from .config import DATA_DIR


def load_movements() -> pd.DataFrame:
    """起降日志。arrival/departure 解析为 pandas 时间戳。"""
    df = pd.read_csv(DATA_DIR / "movements.csv", encoding="utf-8-sig")
    df["arrival_datetime"] = pd.to_datetime(df["arrival_datetime"])
    df["departure_datetime"] = pd.to_datetime(df["departure_datetime"])
    return df


def load_billing_ledger() -> pd.DataFrame:
    """财务账本。movement_id 可能指向不存在的 movement。"""
    return pd.read_csv(DATA_DIR / "billing_ledger.csv", encoding="utf-8-sig")


def load_rate_card() -> pd.DataFrame:
    """费率卡。effective_from/effective_to 转成 date，用于日期窗口匹配。"""
    df = pd.read_csv(DATA_DIR / "rate_card.csv", encoding="utf-8-sig")
    # 用原生 date 解析（pandas 的纳秒时间戳无法表示 9999-12-31 这个"开放结束"哨兵值）
    df["effective_from"] = df["effective_from"].apply(date.fromisoformat)
    df["effective_to"] = df["effective_to"].apply(date.fromisoformat)
    return df


def load_airlines() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "airlines.csv", encoding="utf-8-sig")


def load_credit_notes() -> list[dict]:
    """冲销单，返回 list[dict]，方便按 related_invoice_line_id 匹配。"""
    df = pd.read_csv(DATA_DIR / "credit_notes.csv", encoding="utf-8-sig")
    df["related_invoice_line_id"] = df["related_invoice_line_id"].fillna("").astype(str)
    return df.to_dict("records")
