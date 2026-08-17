# Bug Priority List (P0 / P1 / P2)

> Purpose: answer two questions —
> 1. "Given the current tests, up to which stage are there zero bugs?"
> 2. "Where could bugs start to appear?"

---

## Conclusion up front (the confirmation you asked for)

✅ **Confirmed: in the engine core, on the current dataset, no P0 or P1 bug will appear.**
Evidence: 88 tests all pass + 100% coverage + the end-to-end anchors (92 exceptions / net −24,779.10 /
wrong-airline net 0) all match. This section has no known P0/P1 bug.

⚠️ **But "no P0/P1 will appear" has a precondition — held by a person, not by the code:**

| Precondition | What happens if it is not met | Seam |
|---|---|---|
| Don't change the data; if you do, re-run tests + re-check the anchors | New status / new column / new date format → P1 | ① |
| The AI layer only writes words, never touches numbers | LLM computes numbers → P0 | ② |
| Every deck number is copied cell-by-cell from the CSV and re-checked | Wrong transcription / wrong sign → P0 | ③ |

Hold these three, and P0/P1 won't appear; drop them, and seam ③ (transcribing deck numbers)
is where a P0 is most likely to surface right now.

---

## 1. First, agree on the terms: what "zero bugs" means

"Zero bugs" is not a phrase to use loosely. In this project it means precisely:

> **The deterministic engine core** (the part that computes money), under the conditions
> "**the current 6 data files + 88 tests + 100% coverage**", has all its written code paths
> executed and its results matching the acceptance anchors — therefore **no known bug**.

It does **not** mean "mathematically proven correct for any input". To be honest:

- **100% coverage = every line ran at least once**, not "every line is correct under every possible input".
- The "zero bugs" we can claim is **bounded**: same data, same rules, same Python environment.

Beyond that boundary lies the "seams" in section 3.

---

## 2. What P0 / P1 / P2 mean (for this project)

| Level | Meaning | Test |
|---|---|---|
| **P0** | Blocking: directly "computes money wrong" or "fails to deliver" | Financial number wrong, governance red line broken, report won't run |
| **P1** | High: shakes trust in the result, but not wholly wrong | Wrong classification, wrong boundary value, wrong parse on new data, environment won't run |
| **P2** | Low: affects wording/UX, **does not affect numbers** | AI prose, README wording, logs, comments |

> In one line: **P0 is "the number is wrong", P1 is "classification / boundary / environment is
> wrong", P2 is "the wording is off".**

---

## 3. Where the zero-bug boundary is (the core answer)

Draw the pipeline as a line and mark which section is locked by tests and which are risk seams:

```
[data CSVs] → [load parse] → [rate_card lookup] → [billing_rules compute expected]
      ↑                                              ↓
   seam ①                                      [reconcile compare]
  (new data)                                          ↓
                                             [credit note resolve]
                                                      ↓
                                               [report stats + write]
                                                      ↓
   seam ②                                         [ai_layer write words]
  (real LLM)                                           ↓
                                                      ↓
   seam ③                                      [deck / docs hand-copied numbers]
  (human transcription)
```

- ✅ **Green zone (locked, zero bugs)**: `load → rate_card → billing_rules → reconcile → credit
  note → report stats`. This is the "engine core", locked by 88 tests + 100% coverage; no known bug
  on the current data.
- ⚠️ **Seam ①**: the moment the data is replaced by new data.
- ⚠️ **Seam ②**: the moment `ai_layer` goes from mock to a real LLM.
- ⚠️ **Seam ③**: the moment a person copies engine numbers into the deck / README.

---

## 4. Where bugs could start to appear (classified)

### Seam ① — Data replaced (highest risk: new data = new states = new boundaries)

**Trigger**: the examiner swaps in a different `movements.csv` / `billing_ledger.csv`, or changes
`rate_card.csv` / `assumptions.csv`.

| Level | Possible bug | Why | Consequence |
|---|---|---|---|
| **P1** | A `status` or `charge_type` value we haven't seen | The engine only branch-tested the known enums; a new enum may take the wrong branch or be missed | Wrong classification / missed finding |
| **P1** | Different date format (e.g. `03/01/2026` vs `2026-03-01`) | `load.py` parsing is written for the current format | Parse error or date misread |
| **P1** | Different column names / missing columns | Table reads align to `DATA_DICTIONARY.md` column names | Direct `KeyError` crash |
| **P0** | `assumptions.csv` thresholds/period changed but acceptance not re-run | Governance requires reading at run time; change it and everything shifts | Financial numbers all move, anchors no longer match |

**Guard**: after `python -m src.main`, spot-check against the anchors in `tests/test_end_to_end.py`
plus a manual sample of the new data.

---

### Seam ② — AI layer wired to a real model (currently mock, numbers unaffected)

**Current state**: `src/ai_layer.py` is a mock with hard-coded text that **does not touch numbers**.
So today it is P2 or no risk at all.

**Trigger**: the mock is later replaced by a real LLM call.

| Level | Possible bug | Consequence |
|---|---|---|
| **P2** | LLM wording/formatting is off | Only affects readability, no financial figure changes |
| **P1** | Call failure / timeout / token limit interrupts `summary.md` generation | Report incomplete, but `exceptions.csv` is already written |
| **P0** | ⚠️ If the LLM is asked to "compute" or "change" numbers | Violates the red line "AI layer writes words, never touches numbers" → wrong money |

**Iron rule**: the AI layer always receives the engine's computed numbers and only explains them in
words. Hold that line, and seam ② produces no P0.

---

### Seam ③ — Human transcription (highest P0 risk at exam time, but outside code tests)

**Trigger**: manually copying numbers when making the deck, writing the README, or presenting.

| Level | Possible bug | Consequence |
|---|---|---|
| **P0** | A deck number doesn't match `output/exceptions.csv` / `summary.md` (mis-copied, mis-rounded, wrong sign) | The examiner immediately sees "report and code disagree" and distrusts the whole work |
| **P0** | Saying "net impact −24,779.10" as "owed −24,779.10" or dropping the sign | The financial meaning is reversed |
| **P1** | A cited `evidence_ref` / amount doesn't match a specific CSV row | Can't be traced back to source evidence when challenged |

**Guard**: every number that goes into the deck must point to a specific CSV row and note its source
file. Use `PPT_PLAN.md` to check cell by cell.

---

## 5. One-line summary

| Question | Answer |
|---|---|
| Up to which stage are there zero bugs? | The **engine core** (the money-computing section), on the current data + 88 tests + 100% coverage |
| Where do bugs start to appear? | Three seams: **① new data ② real LLM ③ human transcription** |
| Which is the most to watch? | **Seam ③ (human transcription)** — outside code test coverage, yet the first thing an examiner sees |
| Which red line is most worth holding? | "AI layer writes words, never numbers" + "deck numbers match engine output cell by cell" |
