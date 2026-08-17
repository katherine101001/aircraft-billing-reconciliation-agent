# AI Usage Log

> The brief asks: which tools you used, for what, and one or two moments where the AI was wrong or
> unhelpful and how you caught it. This file records the mistakes Claude Code made while developing
> this system, for review.

## Tools used, and for what

- **Tool**: Claude Code (Claude, deepseek-v4-pro backend)
- **Used for**:
  1. Reading all documents and data, mapping out billing rules, discrepancy types, and data pitfalls;
  2. Writing the reconciliation engine (Python + pandas), 7 modules in total;
  3. Running and verifying the results, checking the exception list type by type;
  4. Writing this log and CLAUDE.md.

## Mistakes the AI made (and how each was caught)

### Mistake 1: `9999-12-31` date sentinel crashed the parser
- **What happened**: `rate_card.csv` uses `9999-12-31` in `effective_to` to mean "open-ended".
  pandas' `pd.to_datetime` uses nanosecond timestamps, whose upper limit is year 2262, so it threw
  `OutOfBoundsDatetime`.
- **How I caught it**: the first `python -m src.main` run errored immediately.
- **Fix**: parse the rate card's date windows with Python's native `datetime.date.fromisoformat`
  to sidestep the pandas timestamp limit.
- **Lesson**: sentinel dates (9999-12-31 / 0000-00-00) are common in real data — before parsing a
  date, think about the underlying representation's range.

### Mistake 2: Windows console threw `UnicodeEncodeError` on Chinese/currency symbols
- **What happened**: the engine produced correct results, but `print(summary)` failed because the
  console encoding was cp1252, which cannot encode Chinese characters or currency symbols.
- **How I caught it**: the run raised `UnicodeEncodeError: 'charmap' codec ...`.
- **Fix**: at the entry point, `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`.
- **Lesson**: file writes use `encoding="utf-8"`, but stdout on Windows is not UTF-8 by default —
  the two must be handled separately.

### Mistake 3 (the important one): wrong-airline cases were double-counted — a business-logic bug
- **What happened**: the first version of the engine reported **two** exceptions for a charge billed
  to the wrong airline:
  1. `MISSING_CHARGE` (the correct airline "didn't get billed" for that charge);
  2. `WRONG_AIRLINE` (the charge went to the wrong airline).
  The same problem was counted twice, and net financial impact was overstated by 21,861 MYR.
- **Why it was wrong**: the logic treated "missed charge" and "wrong airline" as two independent
  directions, but the brief says a wrong-airline charge is **one exception with net impact 0**:
  refund the wrongly-billed airline and rebill the correct one — no money is actually lost.
- **How I caught it**: not via a crash — by **manually reviewing `exceptions.csv` line by line** and
  noticing the same `movement_id` appearing with both `MISSING_CHARGE` and `WRONG_AIRLINE`. This is
  the classic "result looks fine but is actually wrong" case.
- **Fix**: record the charge types affected by a wrong airline at line level, and skip those types
  in the set-level "missed charge" check.
- **Lesson**: in reconciliation work, exception types can be **mutually exclusive / have ownership
  relationships**. Each type looking right in isolation does not mean the whole is right — you must
  go back and check that the same fact has not been classified twice.

## One-line summary

> "Runs without crashing" ≠ "correct". The two real bugs were not crashes — they were "the numbers
> look right but the semantics are wrong" — and they could only be caught by reviewing my own output
> against the business rules, one line at a time.
