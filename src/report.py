"""输出：异常报告（CSV）+ 管理总结（Markdown）。

所有数字都来自 reconcile 引擎的异常列表，这里只做统计与落盘，不产生新数字。
"""
from __future__ import annotations

import csv
from collections import defaultdict

import pandas as pd

from . import ai_layer
from .config import OUTPUT_DIR


def build_stats(exceptions: list[dict]) -> dict:
    """从异常列表做纯统计（确定性，非 AI）。"""
    total = len(exceptions)
    net_impact = round(sum(e["financial_impact_myr"] for e in exceptions), 2)
    positive_total = round(sum(e["financial_impact_myr"] for e in exceptions if e["financial_impact_myr"] > 0), 2)
    negative_total = round(sum(e["financial_impact_myr"] for e in exceptions if e["financial_impact_myr"] < 0), 2)
    open_count = sum(1 for e in exceptions if e["resolution_status"] == "OPEN")

    by_type: dict[str, list] = defaultdict(lambda: [0, 0.0])
    for e in exceptions:
        by_type[e["exception_type"]][0] += 1
        by_type[e["exception_type"]][1] += e["financial_impact_myr"]
    by_type = {k: (v[0], round(v[1], 2)) for k, v in by_type.items()}

    return {
        "total_exceptions": total,
        "net_impact": net_impact,
        "positive_total": positive_total,
        "negative_total": negative_total,
        "open_count": open_count,
        "by_type": by_type,
    }


def write_report(exceptions: list[dict], assumptions: dict) -> None:
    """落盘 output/exceptions.csv 与 output/summary.md。"""
    OUTPUT_DIR.mkdir(exist_ok=True)

    # ---- CSV 异常报告 ----
    csv_path = OUTPUT_DIR / "exceptions.csv"
    columns = [
        "movement_id", "invoice_line_id", "exception_type", "charge_type",
        "airline_code", "billed_airline_code", "expected_amount",
        "actual_amount", "financial_impact_myr", "evidence_ref",
        "resolution_status", "credit_note_id",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for e in sorted(exceptions, key=lambda x: (-x["financial_impact_myr"], x["movement_id"])):
            writer.writerow({k: e.get(k, "") for k in columns})

    # ---- 管理总结（Markdown）----
    stats = build_stats(exceptions)
    summary = ai_layer.summarize(stats)

    # 精选 6~10 个有代表性的例子，附 AI 草拟说明
    examples = _pick_examples(exceptions)
    if examples:
        summary += "\n\n## 代表性案例（AI 草拟的退款/争议说明）\n\n"
        for i, exc in enumerate(examples, 1):
            summary += f"**案例 {i}**：{ai_layer.explain_exception(exc)}\n\n"

    summary_path = OUTPUT_DIR / "summary.md"
    summary_path.write_text(summary, encoding="utf-8")

    # 顺带打印到控制台，方便直接看结果
    print(summary)
    print(f"\n[已写出] {csv_path}")
    print(f"[已写出] {summary_path}")


def _pick_examples(exceptions: list[dict], max_n: int = 8) -> list[dict]:
    """挑选有代表性的例子：优先选已解决的重复、错记航司、大额漏收，尽量覆盖不同类型。"""
    seen_types: set[str] = set()
    picked: list[dict] = []
    # 优先级：先展示「已解决」的例子（体现 credit note 逻辑），再按金额绝对值排
    ordered = sorted(exceptions, key=lambda e: (-abs(e["financial_impact_myr"]), e["movement_id"]))
    for e in ordered:
        if e["exception_type"] not in seen_types and len(picked) < max_n:
            picked.append(e)
            seen_types.add(e["exception_type"])
    return picked
