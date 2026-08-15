# Presentation Guide

Your deck is capped at **12 slides**. Fewer is fine. Present it as if to the Cendana Airports
revenue assurance lead: a busy manager who wants to know what you found, what it is worth, and
whether they can trust it. Lead with the finding, not the tooling.

Every number on your slides must come from your own reconciliation engine. If a figure is
not produced by your code from the source data, leave it off.

## Suggested structure

1. **Title.** The problem in one line, your name, the date.
2. **The problem.** Two records that should agree but do not, and why that costs money and
   creates dispute risk. One or two sentences.
3. **Approach.** How your system works at a glance: ingest, reconcile, explain, report. A
   simple diagram beats a wall of text.
4. **Headline result.** The single most important number: total exceptions found and the net
   financial impact. This is the slide they remember.
5. **Where the money is.** A breakdown by exception type or by account. What is leakage
   (unbilled) versus overbilling (owed back to clients).
6. **How the matching works.** The core logic: date-aware rates, derived quantities,
   tolerance, credited items excluded. Show you understood the rules.
7. **The AI layer.** What the LLM does, and, importantly, what it does not do. Make the
   boundary clear: the engine sets the numbers, the model writes the words.
8. **A worked example.** One real exception end to end: the movement, the billing line, the
   gap, the money, the evidence reference, and the AI-drafted explanation a finance person would
   send to the airline.
9. **Trust and governance.** Why the output is defensible: nothing hardcoded, every figure
   traceable, evidence attached to each finding, a human reviews before anything reaches an
   airline.
10. **Limitations and assumptions.** What you assumed, what is out of scope, where you would
    be careful. Honesty scores here.
11. **What I would do next.** If this were week two, what would you build or harden.
12. **Close.** The one thing you want them to take away.

## What we are looking for

- A clear story that a non-technical manager could follow.
- Numbers that match what your code actually produced.
- Evidence you understood the governance rules, not just the happy path.
- Honesty about limits. We trust people who tell us what does not work yet.

## What loses points

- Hardcoded or unexplained figures.
- More slides about your tools than about the finding.
- Claiming the AI does things it cannot, or hiding where numbers came from.
- A deck that looks polished but says nothing a manager could act on.
