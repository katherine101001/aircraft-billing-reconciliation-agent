"""Reconciliation main loop: compares movements (the truth) against the
billing_ledger (what to check) line by line.

Outputs a structured list of exceptions. Each exception is a dict with:
  movement_id, invoice_line_id, exception_type, charge_type,
  airline_code, billed_airline_code, expected_amount, actual_amount,
  financial_impact_myr, evidence_ref, resolution_status, credit_note_id

Financial-impact sign convention (from the brief):
  positive = money owed to the operator (under-billed / missed, to collect)
  negative = money owed back to the airline (over-billed / wrong)

Exception types (11):
  MISSING_CHARGE       a due charge was never billed (leakage)
  WRONG_RATE           wrong unit rate used
  WRONG_QUANTITY       wrong quantity used
  WRONG_AMOUNT         quantity and rate both right, amount still doesn't match
  DUPLICATE            the same movement + charge_type billed twice
  ORPHAN_CHARGE        a billing line points to a movement that doesn't exist
  WRONG_AIRLINE        billed to the wrong airline (net impact 0, but refund + rebill)
  CANCELLED_CHARGED    a cancelled movement was charged
  REMOTE_AEROBRIDGE    an aerobridge charge on a remote stand
  DIVERTED_OVERCHARGE  a diverted movement charged for more than the landing
  PSC_ON_CARGO         a cargo movement (0 pax) charged PSC
"""
from __future__ import annotations

from collections import defaultdict

from .billing_rules import compute_expected_charges
from .config import as_date, as_enum_set, as_float


def _make_exception(**kwargs) -> dict:
    """Build one exception, filling in the default fields."""
    exc = {
        "movement_id": "",
        "invoice_line_id": "",
        "exception_type": "",
        "charge_type": "",
        "airline_code": "",
        "billed_airline_code": "",
        "expected_amount": 0.0,
        "actual_amount": 0.0,
        "financial_impact_myr": 0.0,
        "evidence_ref": "",
        "resolution_status": "OPEN",
        "credit_note_id": "",
    }
    exc.update(kwargs)
    return exc


def reconcile(movements: list[dict], ledger: list[dict], rate_df, assumptions: dict) -> list[dict]:
    """Reconciliation entry point. Returns the exception list (credit-note resolution
    not applied yet; see resolve_credit_notes)."""
    tolerance = as_float(assumptions, "amount_tolerance")
    period_start = as_date(assumptions, "reconciliation_period_start")
    period_end = as_date(assumptions, "reconciliation_period_end")

    mov_by_id = {m["movement_id"]: m for m in movements}

    # Group the ledger by movement_id so each movement can quickly reach its own lines
    ledger_by_movement: dict[str, list[dict]] = defaultdict(list)
    orphan_lines: list[dict] = []
    for line in ledger:
        mid = str(line["movement_id"]).strip()
        if mid in mov_by_id:
            ledger_by_movement[mid].append(line)
        else:
            orphan_lines.append(line)  # points to a movement that doesn't exist

    exceptions: list[dict] = []

    # ---------- 1) Orphan charges: no matching movement ----------
    for line in orphan_lines:
        exceptions.append(_make_exception(
            movement_id=line["movement_id"],
            invoice_line_id=line["invoice_line_id"],
            exception_type="ORPHAN_CHARGE",
            charge_type=line["charge_type"],
            airline_code=line["airline_code"],
            actual_amount=float(line["amount_billed"]),
            financial_impact_myr=round(-float(line["amount_billed"]), 2),  # shouldn't be charged, refund
        ))

    # ---------- 2) Per-movement reconciliation ----------
    for m in movements:
        # Only reconcile movements within the snapshot period (by arrival date)
        if not (period_start <= m["arrival_datetime"].date() <= period_end):
            continue

        lines = ledger_by_movement.get(m["movement_id"], [])
        expected_list = compute_expected_charges(m, rate_df, assumptions)
        expected = {e["charge_type"]: e for e in expected_list}

        status = m["status"]
        valid_lines: list[dict] = []
        # Track charge types billed to the wrong airline: these are not counted as
        # missed charges, to avoid double-counting with WRONG_AIRLINE
        wrong_airline_types: set[str] = set()

        # --- 2a) Line-level checks: is each ledger line itself valid ---
        for line in lines:
            charge_type = line["charge_type"]
            actual_amt = float(line["amount_billed"])

            # Billed to the wrong airline: net impact 0, but needs refund + rebill
            if line["airline_code"] != m["airline_code"]:
                wrong_airline_types.add(charge_type)
                exceptions.append(_make_exception(
                    movement_id=m["movement_id"],
                    invoice_line_id=line["invoice_line_id"],
                    exception_type="WRONG_AIRLINE",
                    charge_type=charge_type,
                    airline_code=m["airline_code"],          # correct airline
                    billed_airline_code=line["airline_code"],  # the wrongly-billed airline
                    expected_amount=expected.get(charge_type, {}).get("amount", 0.0),
                    actual_amount=actual_amt,
                    financial_impact_myr=0.0,                # net 0
                    evidence_ref=m["evidence_ref"],
                ))
                continue

            # Charged a cancelled movement
            if status == "CANCELLED":
                exceptions.append(_make_exception(
                    movement_id=m["movement_id"],
                    invoice_line_id=line["invoice_line_id"],
                    exception_type="CANCELLED_CHARGED",
                    charge_type=charge_type,
                    airline_code=m["airline_code"],
                    actual_amount=actual_amt,
                    financial_impact_myr=round(-actual_amt, 2),
                    evidence_ref=m["evidence_ref"],
                ))
                continue

            # Diverted movement over-charged (only LANDING allowed)
            diverted_charges = as_enum_set(assumptions, "diverted_billable_charges")
            if status == "DIVERTED" and charge_type not in diverted_charges:
                exceptions.append(_make_exception(
                    movement_id=m["movement_id"],
                    invoice_line_id=line["invoice_line_id"],
                    exception_type="DIVERTED_OVERCHARGE",
                    charge_type=charge_type,
                    airline_code=m["airline_code"],
                    actual_amount=actual_amt,
                    financial_impact_myr=round(-actual_amt, 2),
                    evidence_ref=m["evidence_ref"],
                ))
                continue

            # Aerobridge charged on a remote stand
            if charge_type == "AEROBRIDGE" and m["stand_type"] == "REMOTE":
                exceptions.append(_make_exception(
                    movement_id=m["movement_id"],
                    invoice_line_id=line["invoice_line_id"],
                    exception_type="REMOTE_AEROBRIDGE",
                    charge_type=charge_type,
                    airline_code=m["airline_code"],
                    actual_amount=actual_amt,
                    financial_impact_myr=round(-actual_amt, 2),
                    evidence_ref=m["evidence_ref"],
                ))
                continue

            # Cargo movement (0 pax) charged PSC
            if charge_type == "PSC" and m["pax_departing"] == 0:
                exceptions.append(_make_exception(
                    movement_id=m["movement_id"],
                    invoice_line_id=line["invoice_line_id"],
                    exception_type="PSC_ON_CARGO",
                    charge_type=charge_type,
                    airline_code=m["airline_code"],
                    actual_amount=actual_amt,
                    financial_impact_myr=round(-actual_amt, 2),
                    evidence_ref=m["evidence_ref"],
                ))
                continue

            valid_lines.append(line)

        # --- 2b) Set-level checks: expected vs valid lines ---
        by_type: dict[str, list[dict]] = defaultdict(list)
        for line in valid_lines:
            by_type[line["charge_type"]].append(line)

        for charge_type, exp in expected.items():
            acts = by_type.get(charge_type, [])
            exp_amt = exp["amount"]

            if len(acts) == 0:
                # A charge billed to the wrong airline is not a missed charge
                # (its refund + rebill is already handled under WRONG_AIRLINE)
                if charge_type in wrong_airline_types:
                    continue
                # A due charge was never billed at all
                exceptions.append(_make_exception(
                    movement_id=m["movement_id"],
                    exception_type="MISSING_CHARGE",
                    charge_type=charge_type,
                    airline_code=m["airline_code"],
                    expected_amount=exp_amt,
                    financial_impact_myr=round(exp_amt, 2),  # missed, to collect
                    evidence_ref=m["evidence_ref"],
                ))

            elif len(acts) == 1:
                a = acts[0]
                actual_amt = float(a["amount_billed"])
                diff = round(exp_amt - actual_amt, 2)

                # difference within tolerance → rounding, don't flag
                if abs(diff) <= tolerance:
                    continue

                # Decide which of the three went wrong
                if round(float(a["unit_rate"]), 2) != round(exp["unit_rate"], 2):
                    etype = "WRONG_RATE"
                elif int(a["quantity"]) != int(exp["quantity"]):
                    etype = "WRONG_QUANTITY"
                else:
                    etype = "WRONG_AMOUNT"

                exceptions.append(_make_exception(
                    movement_id=m["movement_id"],
                    invoice_line_id=a["invoice_line_id"],
                    exception_type=etype,
                    charge_type=charge_type,
                    airline_code=m["airline_code"],
                    expected_amount=exp_amt,
                    actual_amount=actual_amt,
                    financial_impact_myr=diff,
                    evidence_ref=m["evidence_ref"],
                ))

            else:
                # Duplicate billing: the first line is primary, the rest are duplicates
                for extra in acts[1:]:
                    extra_amt = float(extra["amount_billed"])
                    exceptions.append(_make_exception(
                        movement_id=m["movement_id"],
                        invoice_line_id=extra["invoice_line_id"],
                        exception_type="DUPLICATE",
                        charge_type=charge_type,
                        airline_code=m["airline_code"],
                        actual_amount=extra_amt,
                        financial_impact_myr=round(-extra_amt, 2),  # over-billed, refund
                        evidence_ref=m["evidence_ref"],
                    ))

    return exceptions


def resolve_credit_notes(exceptions: list[dict], credit_notes: list[dict]) -> list[dict]:
    """Determine whether each exception has been resolved by a credit note.

    Resolution rule (from the brief): a credit note's related_invoice_line_id
    must exactly equal the problem line, and its amount + currency must cover the
    difference. A credit note with an empty line_id resolves nothing.
    """
    cn_by_line: dict[str, list[dict]] = defaultdict(list)
    for cn in credit_notes:
        lid = cn["related_invoice_line_id"].strip()
        if lid:
            cn_by_line[lid].append(cn)

    for exc in exceptions:
        lid = exc["invoice_line_id"]
        if not lid or lid not in cn_by_line:
            continue
        for cn in cn_by_line[lid]:
            covers = (
                cn["currency"] == "MYR"
                and float(cn["amount"]) >= abs(exc["financial_impact_myr"])
            )
            if covers:
                exc["resolution_status"] = "RESOLVED_BY_CREDIT_NOTE"
                exc["credit_note_id"] = cn["cn_id"]
                break

    return exceptions
