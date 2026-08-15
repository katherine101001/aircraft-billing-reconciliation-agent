"""读取对账规则（assumptions.csv）。

治理要求：所有业务输入（费率、阈值、日期、计费规则）必须从数据文件读取，
不得硬编码在代码里。本模块是唯一读取 assumptions 的地方。
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

# 项目根目录（src/ 的上一级）
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"


def load_assumptions(path: Path | None = None) -> dict:
    """把 assumptions.csv 读成 {key: value}（value 保持原始字符串）。"""
    path = path or (DATA_DIR / "assumptions.csv")
    assumptions: dict[str, str] = {}
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            assumptions[row["key"]] = row["value"]
    return assumptions


# ---------- 从 assumptions 解析出强类型值 ----------

def as_float(assumptions: dict, key: str) -> float:
    return float(assumptions[key])


def as_int(assumptions: dict, key: str) -> int:
    return int(assumptions[key])


def as_date(assumptions: dict, key: str) -> date:
    return date.fromisoformat(assumptions[key])


def as_enum_set(assumptions: dict, key: str) -> set[str]:
    """把 'COMPLETED,DIVERTED' 这种逗号分隔值解析成集合。"""
    return {s.strip() for s in assumptions[key].split(",")}
