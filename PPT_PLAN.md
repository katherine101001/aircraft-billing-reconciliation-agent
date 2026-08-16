# Deck Plan (copy-ready)

> English version · 中文版见 [`PPT_PLAN_zh.md`](PPT_PLAN_zh.md)
>
> This file is the slide-by-slide script for your ≤12-slide deck, plus the numbers to copy.
> Every number below has been checked against the **engine's real output** (source noted per slide).
> Copy them as-is; don't recompute.

---

## Golden rules (read first — breaking any of these loses points)

1. **Every number on a slide must come from the engine output** (`output/exceptions.csv` +
   `output/summary.md`). Never hand-type, re-round, or guess.
2. **The reconciliation period is 2026-01-01 ~ 2026-06-30** (the snapshot period in
   `assumptions.csv`). **Never use "today's" date.**
3. **Don't oversell the AI**: the AI writes words only, never numbers. Saying otherwise directly
   hurts the "AI integration quality" score.

---

## Number cheat-sheet (every number in the deck, in one table)

| Metric | Value | Source file |
|---|---|---|
| Total exceptions | **92** | `output/summary.md` |
| Net financial impact | **-24,779.10 MYR** (negative = net over-billed, owed back to airlines) | same |
| Under-billed / leakage (owed to operator) | **+58,824.70 MYR** | same |
| Over-billed (owed back to airlines) | **-83,603.80 MYR** | same |
| Resolved by credit note | **5** | same |
| Still open | **87** | same |

### Breakdown by exception type (net)

| Type | Plain meaning | Count | Net MYR | Direction |
|---|---|---|---|---|
| MISSING_CHARGE | Charge due but never billed | 20 | +42,821.00 | leakage |
| WRONG_RATE | Wrong unit rate | 16 | +7,811.40 | leakage |
| WRONG_AIRLINE | Billed to the wrong airline | 7 | 0.00 | neutral (refund + rebill) |
| WRONG_QUANTITY | Wrong quantity | 14 | -411.50 | over-billed |
| REMOTE_AEROBRIDGE | Aerobridge charged on a remote stand | 6 | -6,600.00 | over-billed |
| DIVERTED_OVERCHARGE | Diverted flight over-charged | 5 | -6,961.00 | over-billed |
| CANCELLED_CHARGED | Cancelled flight still charged | 6 | -13,446.00 | over-billed |
| DUPLICATE | Duplicate billing | 8 | -16,332.00 | over-billed |
| ORPHAN_CHARGE | Billing line with no matching movement | 10 | -31,661.00 | over-billed |

> ⚠️ **Important (an examiner may add them up)**: the "leakage 58,824.70 / over-billing 83,603.80"
> totals are **sums of individual positive/negative lines**, while the "by type" table shows **net
> per type**, so the two won't reconcile line by line — because WRONG_QUANTITY contains both
> under-billed (positive) and over-billed (negative) lines. If asked, say: "The totals are
> per-line sums; the type table is net per type — two different cuts of the same engine output."

---

## Slide-by-slide (12 slides)

### Slide 1 — Title

- **Title**: `Aircraft Billing & Movement Reconciliation`
- **Subtitle**: `Finding every gap between the movement log and the billing ledger — and pricing it`
- **Name + date**: your name; the date can be the presentation day (the title-slide date is a
  presentation date, not a reconciliation date — this does not break the snapshot rule).
- **Say**: a deterministic engine that compares the movement log against the billing ledger, finds
  every mismatch, and prices each one.

### Slide 2 — The problem

- **Title**: `Two records that should agree — but don't`
- **Bullets**:
  - Operations logs every aircraft movement; Finance keys in charges **by hand**.
  - The two should match exactly. They don't.
  - Missed or wrong charges → **revenue leakage** + **disputes airlines can't defend against**.
- **Optional concrete contrast** (uses the Slide 8 example):
  - Movement says: flight KP8359, **298 departing passengers** (international)
  - Ledger: **no PSC line** → **10,430.00 MYR** simply unbilled.
- **Say**: today it's manual, slow, error-prone, and when an airline disputes a charge, staff can't
  easily pull the evidence that proves the movement happened as billed.

### Slide 3 — Approach

- **Title**: `How it works: four steps`
- **A simple flow (not a wall of text)**:
  ```
  Ingest  →  Reconcile  →  Explain  →  Report
  read 6 tables   compute gaps   AI writes words   CSV + summary
  ```
- **Points**:
  - **Ingest**: read 6 tables (movements, ledger, rate card, airlines, credit notes, assumptions)
  - **Reconcile**: the deterministic engine compares "expected vs actual" line by line
  - **Explain**: the AI translates each exception into business language + drafts a refund note
  - **Report**: outputs `exceptions.csv` + `summary.md`
- **Say**: the key point — **the numbers are computed by the deterministic engine, not the AI**.
  The AI only makes the result readable.

### Slide 4 — Headline result ⭐ (the slide they remember)

- **Title**: `92 discrepancies, -24,779.10 MYR net`
- **Three big numbers (make them large)**:
  - **92** exceptions
  - **-24,779.10 MYR** net financial impact
  - **5** resolved by credit note (87 still open)
- **Supporting line**: under-billed +58,824.70 / over-billed -83,603.80
- **Say**: the system found 92 discrepancies, with a net of **24,779.10 MYR owed back to airlines**
  (the negative sign means we over-billed).

### Slide 5 — Where the money is

- **Title**: `Leakage vs overbilling`
- **Left column = leakage (unbilled, owed to operator)**:
  - Total **+58,824.70 MYR**
  - Led by: MISSING_CHARGE **+42,821.00**, WRONG_RATE **+7,811.40**
- **Right column = overbilling (owed back to airlines)**:
  - Total **-83,603.80 MYR**
  - Led by: ORPHAN_CHARGE **-31,661.00**, DUPLICATE **-16,332.00**, CANCELLED_CHARGED **-13,446.00**
- **One neutral**: WRONG_AIRLINE, 7 lines, net **0.00**, but needs **both** a refund and a rebill.
- **Say**: we over-billed more than we under-billed, so the net is "money back". The single largest
  bucket is orphan charges — billing lines that reference movements that don't exist.

### Slide 6 — How the matching works

- **Title**: `The rules the engine applies`
- **Bullets**:
  - **Date-aware rates**: LANDING unit rate **12.00** before 03-31, **13.50** from 04-01 (read from
    `rate_card.csv`, not hardcoded)
  - **Derived quantities**: PARKING after a **60-minute grace**; AEROBRIDGE only on **CONTACT**
    stands; PSC = departing pax × (domestic **11** / international **35**)
  - **Tolerance**: a difference ≤ **0.05** is rounding, **not flagged**
  - **Credit notes**: resolve only via exact `related_invoice_line_id` match + amount coverage
- **Say**: this slide proves I didn't "get lucky" matching — each billing rule is understood,
  including the easy-to-get-wrong ones: "diverted = landing only" and "remote = no aerobridge".

### Slide 7 — The AI layer (key: make the boundary clear)

- **Title**: `The engine sets the numbers. The model writes the words.`
- **What the AI does**:
  - Translates an exception type into plain language (e.g. `MISSING_CHARGE` → "a charge that should
    have been billed wasn't")
  - Drafts a refund/dispute note a finance person could paste (citing the evidence ref)
  - Writes the management summary
- **What the AI does NOT do (bold this)**:
  - ❌ **Does not decide the exception type**, ❌ **does not change any number**, ❌ **does not
    compute the financial impact**
- **Say**: this boundary is hard — the engine owns "is it right", the AI only owns "does it read
  well". Even with no AI wired up (current mock), the numbers are fully correct.

### Slide 8 — A worked example ⭐

- **Title**: `One exception, end to end`
- **Use this one (verified)**:

| Field | Value | Source |
|---|---|---|
| Flight | KP8359 (Kinabalu Pacific, A350) | `movements.csv` |
| Movement ID | MOV00069 | same |
| Status / stand | COMPLETED / CONTACT | same |
| Departing pax | **298**, international | same |
| Expected PSC | 298 × 35.00 = **10,430.00 MYR** | rate card |
| Billed | **no PSC line** (0.00) | `billing_ledger.csv` |
| Gap | **+10,430.00 MYR** (unbilled) | `exceptions.csv` row 2 |
| Evidence ref | **EVD-20260304-0069** | same |
| Ruling | **MISSING_CHARGE**, OPEN | same |

- **AI-drafted note (paste into the slide)**:
  > Movement MOV00069 (flight KP8359) carried 298 departing international passengers on
  > 2026-03-04, but no Passenger Service Charge was billed. Expected PSC is MYR 10,430.00
  > (298 × 35.00). No invoice line exists. We recommend raising a supplementary invoice for
  > MYR 10,430.00. Evidence: EVD-20260304-0069.
- **Say**: this is the "evidence chain" — from the movement record, to the rate card, to the missing
  ledger line, to the evidence ref. The whole chain is traceable, so a refund or rebill is defensible.

### Slide 9 — Trust & governance

- **Title**: `Why you can trust the output`
- **Points**:
  - **Zero hardcoding**: rates, thresholds, dates, and rules are read at run time from
    `rate_card.csv` / `assumptions.csv`
  - **Every number traceable**: each report figure maps to a specific row in `exceptions.csv`
  - **Evidence attached**: every finding with a movement carries its evidence ref
  - **Human sign-off**: the report is a recommendation; nothing reaches an airline without review
- **Say**: money handling is never fully automatic. My system finds and prices the problem; whether
  it goes to the airline is decided by a person signing off.

### Slide 10 — Limitations & assumptions

- **Title**: `What I assumed, and where I'd be careful`
- **Points (honesty scores here — don't oversell)**:
  - The AI layer is currently a **mock** (templated text); the boundary is in place and a real model
    drops in directly
  - Only the **snapshot period 2026-01-01 ~ 2026-06-30** is reconciled; data outside is skipped
  - Where the data differs from `DATA_DICTIONARY.md`, the dictionary governs; ambiguities are
    written down in `assumptions.csv`
  - Scope = the 6 CSVs; no real-time monitoring / dashboard (a nice-to-have, not required)
- **Say**: the brief explicitly prefers "an honest partial solution over an over-claimed one" — I
  put the unbuilt parts and assumptions on the table.

### Slide 11 — What I'd do next

- **Title**: `Week two, I would…`
- **Points**:
  - **Wire a real LLM**: replace the mock so refund notes auto-generate (boundary unchanged)
  - **Evaluation harness**: 88 tests + 100% coverage already; add a golden set of expected
    exceptions for regression
  - **Per-airline dispute pack**: group one carrier's open exceptions into a single export
  - **A small dashboard**: one HTML page to browse exceptions by airline/type
- **Say**: the core is solid; what's next is hardening and usability, not a rewrite.

### Slide 12 — Close

- **Title (one-line takeaway, copy-ready)**:
  > `The movement log and the ledger can now be reconciled in minutes — 92 discrepancies found,
  > every one priced and evidenced.`
- **Say**: give me a movement log and a ledger, and I'll return a list of differences — each priced,
  each evidenced.

---

## Pre-submission checklist (tick each one)

- [ ] The five numbers 92, -24,779.10, 58,824.70, 83,603.80, 5 match `output/summary.md` exactly
- [ ] The 9 type counts/net amounts match `output/summary.md` line by line
- [ ] Slide 8 example: MOV00069 / 298 pax / 10,430.00 / EVD-20260304-0069 matches `exceptions.csv` row 2
- [ ] No "today's" date anywhere; the period is consistently 2026-01-01 ~ 2026-06-30
- [ ] Nowhere does it claim "the AI computed a number" (the AI writes words only)
- [ ] ≤ 12 slides
- [ ] Exported as PDF or PPTX

---

## What loses points (`Presentation_Guide.md`)

| Loses points | Which slide | How to avoid |
|---|---|---|
| Hardcoded / unexplained figures | 4, 5 | Note the source file for every number |
| More slides about tools than findings | 3 | Keep the diagram simple, one sentence |
| Claiming the AI does what it can't | 7 | State clearly "the AI never touches numbers" |
| Hiding where numbers came from | all | Footnote "source: output/xxx" per slide |
| Polished but nothing actionable | all | Every slide has a one-line takeaway you can act on |
