# Data Dictionary

All data is fictional and generated for this exercise. Currency is MYR throughout. The data
is a fixed snapshot; the snapshot date and reconciliation period are in `assumptions.csv`. The
same six tables exist both as CSV files and as tabs in `aircraft_billing_workbook.xlsx`.

Read this before writing code. A few fields exist to be joined on, and a few exist to mislead a
careless reconciliation.

---

## movements.csv

The aircraft movement log. One row per turnaround (an arrival and its matching departure). This
is the record of what actually happened, and it is your source of truth for what should have
been billed.

| Column | Type | Notes |
|---|---|---|
| `movement_id` | string | Primary key, e.g. `MOV00123` |
| `flight_no` | string | The flight number, e.g. `CQ1234` |
| `airline_code` | string | The operating airline. Joins to `airlines.csv` |
| `aircraft_reg` | string | Aircraft registration. Informational |
| `aircraft_type` | string | ICAO-style type code, e.g. `A320`, `B77W` |
| `mtow_tonnes` | integer | Maximum take-off weight in tonnes. Drives the landing charge |
| `arrival_datetime` | datetime | `YYYY-MM-DD HH:MM`. Drives which landing rate applies |
| `departure_datetime` | datetime | `YYYY-MM-DD HH:MM`. With arrival, gives the parking duration |
| `stand` | string | Stand assigned, e.g. `A12` (contact) or `R05` (remote) |
| `stand_type` | string | `CONTACT` or `REMOTE`. Aerobridge is billable only for `CONTACT` |
| `pax_departing` | integer | Departing passengers. Drives PSC. `0` for cargo flights |
| `scope` | string | `DOMESTIC` or `INTERNATIONAL`. Drives the PSC rate |
| `status` | string | `COMPLETED`, `CANCELLED`, or `DIVERTED`. See billing rules below |
| `evidence_ref` | string | Reference to the movement evidence record, e.g. `EVD-20260214-0123`. Attach this to any finding so a dispute can be defended |

---

## billing_ledger.csv

The charge lines Finance raised. One row per charge line. This is what was actually billed, and
it is the record you are checking for errors.

| Column | Type | Notes |
|---|---|---|
| `invoice_line_id` | string | Primary key, e.g. `BL00123` |
| `invoice_id` | string | The invoice this line belongs to, e.g. `INV-202604-CQ` |
| `invoice_date` | date | `YYYY-MM-DD`, month-end of the billing cycle |
| `airline_code` | string | The airline billed. Should match the movement's airline |
| `movement_id` | string | The movement this line bills. May not always point to a real movement |
| `charge_type` | string | `LANDING`, `PARKING`, `AEROBRIDGE`, or `PSC` |
| `quantity` | integer | Units billed (tonnes, 15-minute blocks, hours, or passengers) |
| `unit_rate` | decimal | The rate billed. Should match the rate card for the charge, date, and condition |
| `amount_billed` | decimal | What the airline was charged for this line |
| `currency` | string | `MYR` |

Notes: a movement can generate several charge lines (one per applicable charge type). A movement
can appear on more than one line of the same type (that is a duplicate). A line can reference a
movement that does not exist. Not every applicable charge is present.

---

## rate_card.csv

The official charges. Rates can change over time and can depend on a condition, so each row has
an effective-date window and a condition.

| Column | Type | Notes |
|---|---|---|
| `charge_type` | string | `LANDING`, `PARKING`, `AEROBRIDGE`, or `PSC` |
| `basis` | string | How quantity is derived: `per_tonne`, `per_15min`, `per_hour`, or `per_pax` |
| `condition` | string | `ANY`, `CONTACT`, `DOMESTIC`, or `INTERNATIONAL`. Selects the right row |
| `effective_from` | date | First day this rate applies (inclusive) |
| `effective_to` | date | Last day this rate applies (inclusive). `9999-12-31` means open-ended |
| `unit_rate` | decimal | Price per unit |
| `currency` | string | `MYR` |

**How each charge is computed:**

- `LANDING`, `per_tonne`, condition `ANY`: quantity is `mtow_tonnes` rounded up to the whole
  tonne. The rate has two effective windows; use the one covering the arrival date. This is the
  date-aware pricing test.
- `PARKING`, `per_15min`, condition `ANY`: quantity is the parking time beyond the free grace
  period (in `assumptions.csv`), divided by 15 and rounded up. Inside the grace period there is
  no parking charge.
- `AEROBRIDGE`, `per_hour`, condition `CONTACT`: quantity is the parking time divided by 60,
  rounded up. Only for `CONTACT` stands. Never for `REMOTE`.
- `PSC`, `per_pax`, condition `DOMESTIC` or `INTERNATIONAL`: quantity is `pax_departing`, and
  the rate is chosen by the movement's `scope`.

---

## airlines.csv

The airline master.

| Column | Type | Notes |
|---|---|---|
| `airline_code` | string | Primary key |
| `airline_name` | string | Display name (fictional) |
| `airline_type` | string | `FULL_SERVICE`, `LOW_COST`, `CARGO`, or `CHARTER` |
| `home_country` | string | Two-letter country code |
| `credit_terms_days` | integer | Net payment terms |
| `active` | boolean | `true` or `false`. Some airlines are inactive |

Cargo airlines fly with no departing passengers, so their movements carry no PSC.

---

## credit_notes.csv

Adjustments already issued. A credit note reverses or reduces a charge already identified as
wrong. A credit note resolves a discrepancy only when its `related_invoice_line_id` matches the
problem line and its amount and currency cover the discrepancy. A credit note with a blank
`related_invoice_line_id` (for example a goodwill or manual adjustment) does not resolve a
specific exception on its own. Everything not specifically credited stays open.

| Column | Type | Notes |
|---|---|---|
| `cn_id` | string | Primary key, e.g. `CN-2026-0007` |
| `cn_date` | date | When the credit note was issued |
| `airline_code` | string | The airline credited |
| `related_invoice_id` | string | The invoice the credit relates to |
| `related_invoice_line_id` | string | The specific line, when known. May be blank |
| `reason_code` | string | e.g. `DUPLICATE`, `GOODWILL`, `SLA_BREACH`, `MANUAL_ADJ` |
| `amount` | decimal | Credit amount |
| `currency` | string | `MYR` |

---

## assumptions.csv

The rules of the reconciliation. Read these values at run time. Do not hardcode them.

| Column | Type | Notes |
|---|---|---|
| `key` | string | The assumption name |
| `value` | string | Its value |
| `unit` | string | Unit or type of the value |
| `note` | string | Plain-language explanation |

Keys you will use:

- `data_snapshot_date`: the data is pinned as of this date. Reconcile as of here, not today.
- `reconciliation_period_start` and `reconciliation_period_end`: the window to reconcile.
- `amount_tolerance`: differences at or below this (in MYR) are rounding, not exceptions.
- `billable_statuses`: only movements with these statuses are billable.
- `diverted_billable_charges`: which charges a diverted flight may carry (landing only).
- `free_parking_minutes`: parking is free up to this; charge only the excess.
- `aerobridge_requires`: the stand type an aerobridge charge requires (`CONTACT`).
- `landing_basis` and `psc_basis`: notes on how those two charges are computed.
- `currency`: the single currency for this dataset.
