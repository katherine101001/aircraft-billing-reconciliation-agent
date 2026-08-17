"""AI reasoning layer — writes the words only, never touches numbers or classification.

=====================================================================
  Boundary (hard requirement): the reconciliation engine (reconcile.py)
  decides the exception type and every amount; this module only generates
  strings. Its input is the exception dict produced by the engine and its
  output is text — it never modifies any number or classification field.
  When wiring in a real LLM, replace only explain_exception() and
  summarize(); everything else stays the same.
=====================================================================

Currently a MOCK implementation (no API key required). The real-model
insertion point is marked with a TODO.
"""
from __future__ import annotations

# Exception type -> plain business language (used by explain_exception)
TYPE_PLAIN_LANGUAGE = {
    "MISSING_CHARGE": "A charge that should have been billed was not",
    "WRONG_RATE": "Billed at the wrong unit rate",
    "WRONG_QUANTITY": "Billed with the wrong quantity",
    "WRONG_AMOUNT": "Unit rate and quantity correct, but the amount is miscalculated",
    "DUPLICATE": "The same movement and charge were billed twice",
    "ORPHAN_CHARGE": "A billing line references a movement that does not exist",
    "WRONG_AIRLINE": "The charge was billed to the wrong airline",
    "CANCELLED_CHARGED": "A cancelled movement was still charged",
    "REMOTE_AEROBRIDGE": "An aerobridge charge on a remote stand (no bridge available)",
    "DIVERTED_OVERCHARGE": "A diverted movement was charged for more than the landing",
    "PSC_ON_CARGO": "A cargo movement (no departing passengers) was charged PSC",
}


def explain_exception(exc: dict) -> str:
    """Translate one exception into a paste-ready explanation citing the evidence ref."""
    etype = exc["exception_type"]
    plain = TYPE_PLAIN_LANGUAGE.get(etype, etype)
    impact = exc["financial_impact_myr"]
    evidence = exc["evidence_ref"] or "none"

    if etype == "WRONG_AIRLINE":
        return (
            f"[{etype}] {plain}. Movement {exc['movement_id']} ({exc['airline_code']}) "
            f"{exc['charge_type']} charge of {exc['actual_amount']:.2f} MYR was billed to "
            f"{exc['billed_airline_code']}. Two actions required: refund "
            f"{exc['billed_airline_code']} and rebill {exc['airline_code']}. "
            f"Evidence: {evidence}."
        )

    direction = (
        "under-billed (owed to operator)" if impact > 0
        else "over-billed (owed back)" if impact < 0
        else "net zero"
    )
    return (
        f"[{etype}] {plain}. Movement {exc['movement_id']} {exc['charge_type']} charge: "
        f"expected {exc['expected_amount']:.2f} MYR, actual {exc['actual_amount']:.2f} MYR, "
        f"difference {abs(impact):.2f} MYR ({direction}). Evidence: {evidence}."
    )


def summarize(stats: dict) -> str:
    """Generate the natural-language management summary. All numbers come from `stats`
    (the engine's own statistics); this function never computes any amount itself."""
    lines = [
        "# Reconciliation summary (management view)",
        "",
        f"Found **{stats['total_exceptions']}** exceptions with a net financial impact of",
        f"**{stats['net_impact']:,.2f} MYR**.",
        "",
        f"- Under-billed (owed to operator): {stats['positive_total']:,.2f} MYR",
        f"- Over-billed (owed back to airlines): {abs(stats['negative_total']):,.2f} MYR",
        f"- Open (not yet resolved): {stats['open_count']}",
        "",
        "## Exceptions by type",
    ]
    for etype, (cnt, amt) in sorted(stats["by_type"].items(), key=lambda kv: -kv[1][1]):
        lines.append(f"- {etype}: {cnt} lines, {amt:,.2f} MYR")

    lines += [
        "",
        "## Recommended priorities",
        "1. Reconcile the largest open exceptions against the evidence first;",
        "2. Refund (negative) exceptions must be human-reviewed before being sent to an airline;",
        "3. This report is a recommendation; nothing reaches an airline without human sign-off.",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------------
# Real-model insertion point (TODO): swap the mock below for a real LLM call.
#   e.g. explain_exception = lambda exc: llm(EXPLAIN_PROMPT.format(exc=exc))
#   Note: the prompt only lets the model "phrase"; it never hands the model
#   the authority to decide amounts or classifications.
# ------------------------------------------------------------------
