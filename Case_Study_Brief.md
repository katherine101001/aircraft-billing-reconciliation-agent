# Case Study: Aircraft Billing and Movement Reconciliation Agent

**Role:** AI Engineer (Graduate)
**Duration:** One week
**Tools:** AI-assisted development required (Claude Code, Codex, Antigravity, or similar)

---

## 1. Why we run this exercise

We build AI systems that sit on top of real business data and turn messy operational
records into decisions people can trust. A lot of that work is not fancy modelling. It is
careful data handling, sound logic, and an AI layer that explains findings without inventing
numbers. This case study is a small, honest version of that work.

We care less about a perfect score and more about how you think, how you use AI tools to move
fast, and whether we can trust the output you produce. Treat it as a week on a real client,
not an exam.

---

## 2. The scenario (fictional)

**Cendana Airports Berhad** is an airport operator. It charges airlines for aeronautical
services every time an aircraft uses the airport: landing, parking at a stand, use of a
passenger boarding bridge (aerobridge), and a passenger service charge (PSC) on departing
passengers.

Today the billing process is manual. Operations records each aircraft movement. Finance keys
in charges and checks them by hand across a few departments. It is slow, it is error prone,
and when an airline disputes a charge and asks for a credit note, staff struggle to pull the
evidence that proves the movement actually happened as billed.

The result is the problem the revenue assurance team lives with: delayed billing, charges
that are wrong or missed entirely, revenue leakage, and disputes that are hard to defend.

**Your mission:** build a system that reconciles the aircraft movement log against the billing
ledger, finds every discrepancy, quantifies the financial impact, and links each finding back
to the movement evidence so a credit note or a dispute can be defended.

> This is a fictional dataset. Cendana Airports, the airlines, and all records are invented for
> this exercise. Any resemblance to a real operator or carrier is coincidental.

---

## 3. What you are given

All files are in the `data/` folder. Field definitions are in `data/DATA_DICTIONARY.md`. Read
the data dictionary before you write code.

| File | What it holds |
|---|---|
| `movements.csv` | The aircraft movement log: one row per turnaround, with times, stand, aircraft, pax, status, and an evidence reference (~240 rows) |
| `billing_ledger.csv` | Every charge line Finance raised (~700 rows) |
| `rate_card.csv` | Official charges per service, with effective-date windows and conditions |
| `airlines.csv` | The airline master (names, type, home country, credit terms) |
| `credit_notes.csv` | Adjustments already issued against invoices |
| `assumptions.csv` | The rules of the reconciliation (snapshot date, tolerance, grace period, billing rules) |
| `aircraft_billing_workbook.xlsx` | The same six tables as tabs, if you prefer Excel input |

Use the CSVs or the Excel workbook. They hold the same data.

---

## 4. How charges are supposed to work

Read these rules from the data (`rate_card.csv` and `assumptions.csv`), do not hardcode them.

- **Only billable movements get charged.** The billable statuses are in `assumptions.csv`.
  Cancelled movements should carry no charges.
- **Landing** is charged per tonne of the aircraft's maximum take-off weight (MTOW), rounded
  up to the whole tonne. The per-tonne rate depends on the movement date, and it changes part
  way through the period. Use the rate in force on the day the aircraft landed.
- **Parking** is charged only for time beyond a free grace period (see `assumptions.csv`),
  billed per 15-minute block. A turnaround inside the grace period carries no parking charge.
- **Aerobridge** is charged per hour, and only for aircraft on a contact stand. Aircraft on a
  remote stand use no bridge and must not be charged for one.
- **PSC** is charged per departing passenger. The rate depends on whether the flight is
  domestic or international. A movement with no departing passengers (for example, a cargo
  flight) carries no PSC.
- **Diverted flights** are a special case. They are billable for the landing charge only, not
  for parking, aerobridge, or PSC. The rule is in `assumptions.csv`.
- A difference at or below the **tolerance** in `assumptions.csv` is rounding, not an
  exception. Do not flag it.
- A discrepancy is resolved only by a **credit note that matches the specific line**: its
  `related_invoice_line_id` equals the problem line, and its amount and currency cover the
  discrepancy. A credit note with a blank line reference does not resolve anything on its own.
  Everything else stays open.
- A charge **billed to the wrong airline** is net-zero to the operator, but it still needs
  two actions: a refund to the airline that was wrongly billed, and a rebill to the correct
  one. Count it as one exception, record the operator impact as zero, and surface both the
  refund and the rebill so nothing is lost.

You are expected to discover the *types* of discrepancy yourself. As a hint, expect a mix of
missed charges, wrong rates, wrong quantities, duplicates, charges with no matching movement,
charges billed to the wrong airline, charges against cancelled flights, aerobridge charges on
remote stands, and diverted flights charged for more than the landing.

---

## 5. What to build

### 5.1 Reconciliation engine (deterministic core)

A program (Python preferred, but your call) that ingests the data, applies the billing rules,
and emits a structured list of exceptions. Each exception should carry, at minimum: the
movement and invoice-line identifiers involved, the exception type, the expected value, the
actual value, the financial impact in MYR (positive when money is owed to the operator,
negative when it is owed back to an airline), and, where a movement exists, its **evidence
reference** so the finding can be defended in a dispute.

**Governance rule, non-negotiable:** do not hardcode business inputs (rates, thresholds,
dates, billing rules) or expected answers in your application code. Read them from the data
files at run time. Any figure you show in the report or the deck must come from your
reconciliation output and agree with that run. Materialised numbers in a report or on a slide
are fine as long as they were produced by your engine and match it, not typed in by hand. We
will read your code with this in mind.

### 5.2 AI reasoning layer

Your deterministic engine assigns the canonical exception type and the financial numbers. The
LLM's job is to put that into words, not to decide it. Use it to:

- Translate each exception's type into plain business language.
- Draft a short, professional explanation that a revenue analyst could paste into a credit-note
  request or a dispute response, citing the movement evidence reference.
- Produce a natural-language reconciliation summary for a manager: what was found, how much it
  is worth, and what to action first.

The boundary is firm: the engine determines the exception type and every figure; the model must
not set or change a number or the financial classification. Show us in your code where that
boundary sits. You do not need to hand-polish an explanation for all of them. Generating them
programmatically is fine, and for the writeup and deck a representative sample of six to ten
well-chosen examples is enough to show it works.

If you do not have an LLM API key, that is fine. You may stub the model with a clearly marked
mock function that returns a templated explanation, as long as your code shows exactly where a
real model would plug in. We are assessing the design of the boundary, not your API budget.

### 5.3 Output

At minimum, an **exceptions report** (CSV or Excel) and a short **management summary** (the
AI-written narrative, as text or Markdown). A small dashboard or UI is a nice-to-have, not a
requirement. Clarity beats polish.

---

## 6. Deliverables

Submit three things.

1. **The code**, in a Git repository (or a zip if you cannot share a repo). Include your
   `.env.example` with any keys named but no secrets committed.
2. **Run instructions**: a `README.md` that lets us clone, install, configure, and run your
   solution from scratch and reproduce your report. State the exact commands. Assume we have
   the data folder and an API key, nothing else.
3. **A presentation deck**, no more than **12 slides**. See `Presentation_Guide.md` for the
   suggested structure. Present it as if to the Cendana revenue assurance lead: what you found,
   what it is worth, how your system works, and what you would do next.

---

## 7. How you must use AI tools

This is an AI-assisted development role, so we want to see you use the tools well, not hide
them.

- Build with **Claude Code, Codex, Antigravity, or a comparable AI coding assistant.** Using
  them heavily is encouraged, not penalised.
- Keep a short **AI usage log** (half a page is fine, in the README or a separate file): which
  tools you used, for what, and one or two moments where the AI was wrong or unhelpful and how
  you caught it. We care about that last part. Knowing when to distrust the tool is the skill.
- The work must be yours to explain. In the review we may ask you to walk through any part of
  the code and change it live.

---

## 8. Constraints and ground rules

- Do not hardcode business inputs or expected answers in code (see 5.1). Figures in the report
  and deck must come from your run and agree with it. This is the single most important rule.
- Read rates, thresholds, dates, and billing rules from `rate_card.csv` and `assumptions.csv`.
  Do not bury them in code.
- Handle the data snapshot correctly. The data is pinned as of the snapshot date in
  `assumptions.csv`. Reconcile the stated period only. Do not use today's date.
- Because the agent touches money, assume a human reviews before anything reaches an airline.
  Your report is a recommendation for a person, not an automated action. Note in your design
  where a human sign-off would sit.
- Attach the movement evidence reference to every finding that has a matching movement. This is
  what lets a dispute be defended. A charge with no matching movement (and so no evidence) is
  itself a finding worth flagging.
- If something in the data is genuinely ambiguous, make a reasonable call, write it down, and
  move on. Documented assumptions are fine. Silent guesses are not.

---

## 9. Stretch goals (optional, only if the core is solid)

Do these only after the core works end to end. A rock-solid core beats a shaky pile of extras.

- A simple evaluation harness: a set of expected exceptions you assert against, so a code change
  that breaks the logic is caught.
- A movement-monitoring view: surface operational anomalies in the movement log itself, such as
  a very long stand occupancy or an unusually short turnaround.
- A small dashboard (a single HTML page or Streamlit app) to browse exceptions by airline or
  type, with the evidence reference on each.
- Per-airline dispute packs, grouping every open exception for one carrier into one export.

---

## 10. Suggested one-week plan

You have a week of calendar time, but this is not meant to consume it. Aim for roughly 12 to
16 hours of focused work. If you find yourself heading well past that, stop, write down what
you would have done with more time, and submit what you have. We would rather see a clear,
honest core than an exhausted candidate. The plan below is a guide, not a rule.

- **Day 1:** Read everything. Load the data. Explore it. Write down the discrepancy types you
  can see by eye and the billing rules you will apply.
- **Day 2 to 3:** Build the deterministic engine. Get the matching, the date-aware landing
  rate, the grace period on parking, the contact-stand rule on aerobridge, and the diverted
  rule right. Produce a first exceptions report.
- **Day 4:** Add the AI layer: classification, per-exception explanations with the evidence
  reference, the management summary. Lock the boundary so the model never sets a number.
- **Day 5:** Harden it. Edge cases, tolerance, credited items, cancelled and diverted flights.
  Write the README so a stranger can run it.
- **Day 6:** Build the deck. Rehearse the story with the numbers your own system produced.
- **Day 7:** Buffer, polish, final check that nothing is hardcoded.

---

## 11. How we will assess you

We score five areas. The detailed rubric is internal, but you should know what we weigh:

1. **Correctness of the reconciliation** (did you find the real discrepancies, and avoid false
   alarms).
2. **Data and governance discipline** (nothing hardcoded, figures traceable, snapshot,
   tolerance, and the billing rules handled right).
3. **Quality of the AI integration** (useful, grounded, model never invents numbers, evidence
   attached).
4. **Engineering craft** (readable code, a README that actually runs, sensible structure).
5. **Communication** (the deck and summary tell a clear story a manager could act on).

We would rather see an honest, well-reasoned partial solution than an over-claimed one. If you
ran out of time on something, say so and tell us what you would have done.

---

## 12. Submission

Send us the repository link (or zip), and the deck as PDF or PPTX, by the deadline agreed with
your contact. Make sure the README lets us reproduce your report without you in the room.

Good luck. Build something you would be comfortable defending to a client.
