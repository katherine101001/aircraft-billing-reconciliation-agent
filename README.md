# Aircraft Billing & Movement Reconciliation Agent

> English version · 中文版见 [`README_zh.md`](README_zh.md)

A **deterministic reconciliation engine** that compares the airport movement log (`movements.csv`)
against the billing ledger (`billing_ledger.csv`), finds every discrepancy, quantifies the
financial impact (MYR), attaches an evidence reference, and lets the AI layer turn the results
into deliverable prose.

> This system reconciles only the snapshot period declared in `assumptions.csv`
> (2026-01-01 ~ 2026-06-30). All business inputs (rates, thresholds, dates, billing rules) are
> read from the data files at run time — **nothing is hardcoded**.

---

## Directory structure

```
candidate_pack/
├── data/                  # Raw data (read-only, 6 CSVs)
├── src/
│   ├── config.py          # Reads assumptions.csv (reconciliation rules)
│   ├── load.py            # Reads the 6 tables
│   ├── rate_card.py       # Looks up unit rate by charge_type + condition + date
│   ├── billing_rules.py   # Computes expected charges (core algorithm)
│   ├── reconcile.py       # Main reconciliation loop + credit note resolution
│   ├── ai_layer.py        # AI layer (writes words only, currently a mock)
│   ├── report.py          # Writes exceptions.csv + summary.md
│   └── main.py            # Entry point
├── output/                # Generated results (produced on run)
├── tests/                 # 88 test cases (python -m tests.run_all)
├── REQUIREMENTS_TRACEABILITY.md  # Requirement → code location map
├── BUG_PRIORITY.md        # P0/P1/P2 bug classification
├── PPT_PLAN.md            # Slide-by-slide deck plan (numbers from engine output)
├── AI_USAGE_LOG.md        # AI usage log
├── requirements.txt
├── .env.example
└── README.md
```

> Docs are bilingual: the `_zh.md` files are the Chinese versions of the same document
> (e.g. `README_zh.md`, `REQUIREMENTS_TRACEABILITY_zh.md`).

---

## Requirements

- Python 3.10+
- pandas >= 2.0

## Quick start

### Prerequisites

- **Data**: the repo ships with the `data/` folder (6 CSVs); confirm it sits in the project root.
- **Python**: 3.10 or later (verified on 3.10.11).
- **LLM API key (optional)**: the AI layer falls back to mock text without one (the boundary is unchanged).

### Reproduce (exact commands)

```bash
# 0. Get the code
git clone <your-repo-url>        # or unzip to any directory
cd candidate_pack

# 1. Install dependencies (only pandas is needed)
pip install -r requirements.txt

# 2. (Optional) configure an LLM API key; it runs without one
#    cp .env.example .env        # then edit .env and fill in OPENAI_API_KEY

# 3. Run the reconciliation engine
python -m src.main
```

On success, the console prints the management summary and generates two files:

| File | Contents |
|---|---|
| `output/exceptions.csv` | Every exception: type, expected value, actual value, financial impact, evidence reference, resolution status |
| `output/summary.md` | AI-generated management summary + representative case explanations |

### Expected output (reproducibility check)

Running on the same data is **deterministic** and should match the table below
(a useful "did I run it right" anchor):

| Metric | Value |
|---|---|
| Total exceptions | 92 |
| Net financial impact | -24,779.10 MYR |
| Under-billed (owed to operator) | 58,824.70 MYR |
| Over-billed (owed back to airlines) | 83,603.80 MYR |
| Resolved by credit note | 5 |

If your numbers differ, check whether you replaced files under `data/`, or changed
`rate_card.csv` / `assumptions.csv`.

---

## Tests

```bash
# Run all tests (88 cases)
python -m tests.run_all

# Measure coverage (install first: pip install -r requirements-dev.txt)
python -m coverage run -m tests.run_all
python -m coverage report -m
```

**88 cases**, covering billing rules, rate lookup, reconciliation, credit note resolution,
the AI layer, report output, config/loading, and end-to-end — all should pass.
The tests are the reproducible proof of correctness: any change that breaks the logic makes them fail.

**Coverage target: 100%** (all 271 statements and 84 branches under `src/` are exercised).
Except for `src/main.py`'s `if __name__ == "__main__"` entry (triggered by a subprocess test),
there are no "uncovered" exemptions.

---

## Requirement → code mapping

See `REQUIREMENTS_TRACEABILITY.md`: every brief requirement → its concrete code location.

---

## Exception types

The engine recognises 11 exception types (see the header comment in `src/reconcile.py`):

`MISSING_CHARGE`, `WRONG_RATE`, `WRONG_QUANTITY`, `WRONG_AMOUNT`, `DUPLICATE`,
`ORPHAN_CHARGE`, `WRONG_AIRLINE` (net impact 0), `CANCELLED_CHARGED`,
`REMOTE_AEROBRIDGE`, `DIVERTED_OVERCHARGE`, `PSC_ON_CARGO`.

Financial impact sign: **positive = money owed to the operator (under-billed);
negative = money owed back to the airline (over-billed)**.
A difference ≤ `amount_tolerance` (0.05 MYR) is rounding and is not flagged.

---

## AI layer and the boundary

The reconciliation engine (`reconcile.py`) sets the exception type and every amount; the AI
layer (`ai_layer.py`) only:
1. translates the exception type into plain language;
2. drafts a refund/dispute explanation citing the evidence reference;
3. produces the management summary.

**The model never sets or changes any number or classification.** It is currently a mock; the
real-LLM insertion point is marked with a `TODO` at the bottom of `src/ai_layer.py` — replace
`explain()` and `summarize()`, and the boundary stays the same.

---

## Governance & reproducibility notes

- Every number in the report comes from a single run of `src/reconcile.py`; nothing is typed in by hand.
- Only the `reconciliation_period_start/end` is reconciled, using `data_snapshot_date`, never today's date.
- A credit note resolves an exception only when its `related_invoice_line_id` exactly matches the
  problem line and its amount and currency cover the difference.
- The report is a recommendation for human review; nothing is sent to an airline without sign-off.

## AI usage log

See `AI_USAGE_LOG.md`.
