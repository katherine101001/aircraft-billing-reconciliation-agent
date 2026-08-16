# Requirements Traceability

> English version · 中文版见 [`REQUIREMENTS_TRACEABILITY_zh.md`](REQUIREMENTS_TRACEABILITY_zh.md)
>
> A "map" for the reviewer: each hard requirement in `Case_Study_Brief.md` → the exact file and
> function that implements it. Indexed by `module.function`; line numbers are for orientation.
> All requirements are complete — no hard requirement is unimplemented.

---

## 5.1 Reconciliation engine (deterministic core)

| Brief requirement | Implementation | Notes |
|---|---|---|
| Ingest data (movements / ledger / rate / credit_notes …) | `src/load.py` (`load_movements`, `load_billing_ledger`, `load_rate_card`, `load_credit_notes`) | Unified CSV reads; dates parsed correctly |
| Apply billing rules to compute "what should be charged" | `src/billing_rules.py` (`compute_expected_charges`) | 4 charge types + status filtering |
| Compare line by line, emit structured exceptions | `src/reconcile.py` (`reconcile`) | Returns list[dict] |
| Each exception carries movement/id, type, expected, actual, impact, evidence | `src/reconcile.py` (`_make_exception`) | Default fields filled in |
| Sign convention (positive = owed to operator, negative = back to airline) | `src/reconcile.py` module docstring + `reconcile` | Every `financial_impact_myr` uses it consistently |
| Tolerance ≤ 0.05 is rounding, not flagged | `src/reconcile.py` (`reconcile` lines 210-212) | `abs(diff) <= tolerance` |

## 4 Billing rules (core algorithm, each traceable)

| Rule | Implementation |
|---|---|
| Only billable statuses are charged (CANCELLED is not) | `src/billing_rules.py:32-34` |
| LANDING = ceil(MTOW) × date-sensitive rate | `src/billing_rules.py:48-55` + `src/rate_card.py` (`lookup_rate`) |
| PARKING = 15-min blocks beyond grace × rate | `src/billing_rules.py:62-72` |
| AEROBRIDGE = per hour, CONTACT stands only | `src/billing_rules.py:74-83` |
| PSC = departing pax × domestic/international; 0 pax (cargo) = no charge | `src/billing_rules.py:85-94` |
| DIVERTED = landing charge only | `src/billing_rules.py:57-60` |
| Date-sensitive rate (12.00 before 03-31, 13.50 from 04-01) | `src/rate_card.py` (`lookup_rate`, window match on `effective_from/to`) |

## 11 exception types (`src/reconcile.py`)

| Exception type | Where it is decided (reconcile.py) |
|---|---|
| MISSING_CHARGE | set-level check, `len(acts) == 0` branch |
| WRONG_RATE / WRONG_QUANTITY / WRONG_AMOUNT | set-level check, three single-line-difference rulings |
| DUPLICATE | set-level check, `len(acts) > 1` branch |
| ORPHAN_CHARGE | grouping: `movement_id` not in `mov_by_id` |
| WRONG_AIRLINE (net 0, refund + rebill) | line-level check, airline-mismatch branch |
| CANCELLED_CHARGED / REMOTE_AEROBRIDGE / DIVERTED_OVERCHARGE / PSC_ON_CARGO | line-level checks, each branch |

## 5.2 AI reasoning layer

| Brief requirement | Implementation |
|---|---|
| Exception type → plain business language | `src/ai_layer.py:15-27` (`TYPE_PLAIN_LANGUAGE`) |
| Draft a paste-ready explanation citing the evidence ref | `src/ai_layer.py:30-50` (`explain_exception`) |
| Produce a natural-language management summary | `src/ai_layer.py:53-78` (`summarize`) |
| Boundary: engine sets numbers/types, model only writes | `src/ai_layer.py` module docstring (lines 1-8) |
| Real model insertion point (currently mock) | `src/ai_layer.py:10` (marked mock) + lines 81-85 (TODO) |

## 5.3 Output

| Requirement | Implementation | Artifact |
|---|---|---|
| Exceptions report (CSV) | `src/report.py` (`write_report`) | `output/exceptions.csv` |
| Management summary (Markdown) | `src/report.py` (`write_report`) + `src/ai_layer.py` (`summarize`) | `output/summary.md` |

## 8 Governance constraints (red lines)

| Constraint | Implementation |
|---|---|
| No hardcoded business inputs | All business numbers come from `data/*.csv`; `src/config.py` is the only reader of assumptions, `src/rate_card.py` the only rate lookup |
| Rates/thresholds/dates/rules read at run time | `src/config.py` + `src/rate_card.py` + `src/load.py` |
| Snapshot period, never today's date | `src/reconcile.py:56-57, 88` (filter by `reconciliation_period_start/end`) |
| 9999-12-31 open-ended sentinel parsed correctly | `src/load.py:30-32` (`date.fromisoformat` avoids pandas nanosecond overflow) |
| Evidence ref attached to every finding with a movement | `src/reconcile.py` (`evidence_ref` field on every exception) |
| Human sign-off point | `src/ai_layer.py:76` (summary declares "human sign-off before sending to airline") + `README.md` |

## 6 Deliverable status

| Deliverable | Status |
|---|---|
| Code (Git repo or zip) | ✅ Committed and pushed (GitHub) |
| README (reproduce from scratch) | ✅ `README.md` (with reproducibility anchor numbers) |
| Deck (≤12 slides) | ⏳ To be built by the candidate (see `PPT_PLAN.md`) |
| AI usage log | ✅ `AI_USAGE_LOG.md` (3 mistakes + how each was caught) |

---

## Appendix: key design decisions (documented assumptions)

The brief allows "make a reasonable call, write it down". This implementation's calls:

1. **Duplicates (DUPLICATE)**: multiple ledger lines for the same movement + charge_type — the
   first is the primary line, the rest are duplicates (`len(acts) > 1` branch).
2. **Wrong airline vs missed charge are mutually exclusive**: a charge billed to the wrong airline
   yields one `WRONG_AIRLINE` (net 0) and does **not** additionally yield a `MISSING_CHARGE`, to
   avoid double-counting the same fact (`wrong_airline_types` dedup at `reconcile.py:98, 192-193`).
3. **`airlines.csv` is not used in the core reconciliation**: the core rules only depend on the
   movement/ledger `airline_code`; the airline master is only used (optionally) to prettify names
   in AI prose — it never affects correctness.
4. **Credit note coverage**: `amount >= |financial_impact|` and currency MYR counts as covered
   (`reconcile.py:268-272`).

## Appendix: tests (reproducible correctness evidence)

Run `python -m tests.run_all` — **88 cases** covering billing rules, rate lookup, reconciliation,
credit note resolution, the AI layer, report output, config/loading, and end-to-end — all pass. See `tests/`.

Code coverage is **100%** (`src/`: 271 statements, 84 branches):
`python -m coverage run -m tests.run_all && python -m coverage report -m`.
