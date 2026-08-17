"""Entry point: load data → reconcile → resolve credit notes → write report.

Run:  python src/main.py
"""
from __future__ import annotations

import sys

# Windows consoles default to cp1252, which can't print non-ASCII characters; force UTF-8
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .config import load_assumptions
from .load import (
    load_billing_ledger,
    load_credit_notes,
    load_movements,
    load_rate_card,
)
from .reconcile import reconcile, resolve_credit_notes
from .report import write_report


def main() -> None:
    # 1) Load rules and data (all business inputs come from files, nothing hardcoded)
    assumptions = load_assumptions()
    rate_df = load_rate_card()
    movements_df = load_movements()
    ledger_df = load_billing_ledger()
    credit_notes = load_credit_notes()

    movements = movements_df.to_dict("records")
    ledger = ledger_df.to_dict("records")

    # 2) Deterministic reconciliation
    exceptions = reconcile(movements, ledger, rate_df, assumptions)

    # 3) Credit-note resolution
    exceptions = resolve_credit_notes(exceptions, credit_notes)

    # 4) Write the report (CSV + management summary)
    write_report(exceptions, assumptions)


if __name__ == "__main__":  # pragma: no cover — entry point, triggered by `python -m src.main` (see tests/test_main.py)
    main()
