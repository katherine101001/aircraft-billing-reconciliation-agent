"""Output: the exceptions report (CSV) + management summary (Markdown).

Every number comes from the reconcile engine's exception list; this module only
computes statistics and writes files — it produces no new numbers.
"""
from __future__ import annotations

import csv
from collections import defaultdict

import pandas as pd

from . import ai_layer
from .config import OUTPUT_DIR


def build_stats(exceptions: list[dict]) -> dict:
    """Pure statistics over the exception list (deterministic, not AI)."""
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
    """Write output/exceptions.csv and output/summary.md to disk."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    # ---- CSV exceptions report ----
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

    # ---- Management summary (Markdown) ----
    stats = build_stats(exceptions)
    summary = ai_layer.summarize(stats)

    # Pick 6~10 representative examples with AI-drafted notes
    examples = _pick_examples(exceptions)
    if examples:
        summary += "\n\n## Representative examples (AI-drafted refund / dispute notes)\n\n"
        for i, exc in enumerate(examples, 1):
            summary += f"**Example {i}**: {ai_layer.explain_exception(exc)}\n\n"

    summary_path = OUTPUT_DIR / "summary.md"
    summary_path.write_text(summary, encoding="utf-8")

    # Also print to console for a quick view
    print(summary)
    print(f"\n[wrote] {csv_path}")
    print(f"[wrote] {summary_path}")


def _pick_examples(exceptions: list[dict], max_n: int = 8) -> list[dict]:
    """Pick representative examples: prefer resolved duplicates, wrong-airline and
    large missed charges, covering as many distinct types as possible."""
    seen_types: set[str] = set()
    picked: list[dict] = []
    # Priority: show "resolved" examples first (showcases the credit-note logic), then sort by absolute impact
    ordered = sorted(exceptions, key=lambda e: (-abs(e["financial_impact_myr"]), e["movement_id"]))
    for e in ordered:
        if e["exception_type"] not in seen_types and len(picked) < max_n:
            picked.append(e)
            seen_types.add(e["exception_type"])
    return picked
