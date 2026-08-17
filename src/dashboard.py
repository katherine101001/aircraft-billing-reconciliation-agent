"""Generate a self-contained HTML dashboard from output/exceptions.csv.

Run after the engine has produced the report:

    python -m src.main          # writes output/exceptions.csv + summary.md
    python -m src.dashboard     # writes output/dashboard.html

The dashboard is a single file (no server, no external assets): it embeds the
exception rows as JSON and renders a KPI row, a diverging bar chart of net impact
by type, and a filterable/sortable table. Every figure comes from the engine's
output — nothing is typed by hand here.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from .config import OUTPUT_DIR


def _money(n: float) -> str:
    """Format a MYR amount with an explicit sign and thousands separators."""
    s = f"{abs(n):,.2f}"
    return f"+{s}" if n > 0 else f"-{s}"


def _read_rows(csv_path: Path) -> list[dict]:
    rows = []
    with open(csv_path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append({
                "movement_id": r["movement_id"],
                "invoice_line_id": r["invoice_line_id"],
                "exception_type": r["exception_type"],
                "charge_type": r["charge_type"],
                "airline_code": r["airline_code"],
                "billed_airline_code": r["billed_airline_code"],
                "expected_amount": round(float(r["expected_amount"] or 0), 2),
                "actual_amount": round(float(r["actual_amount"] or 0), 2),
                "financial_impact_myr": round(float(r["financial_impact_myr"] or 0), 2),
                "evidence_ref": r["evidence_ref"],
                "resolution_status": r["resolution_status"],
                "credit_note_id": r["credit_note_id"],
            })
    return rows


def _build_stats(rows: list[dict]) -> dict:
    total = len(rows)
    net = round(sum(r["financial_impact_myr"] for r in rows), 2)
    pos = round(sum(r["financial_impact_myr"] for r in rows if r["financial_impact_myr"] > 0), 2)
    neg = round(sum(r["financial_impact_myr"] for r in rows if r["financial_impact_myr"] < 0), 2)
    resolved = sum(1 for r in rows if r["resolution_status"] != "OPEN")
    open_ = total - resolved

    by_type: dict[str, list] = defaultdict(lambda: [0, 0.0])
    for r in rows:
        by_type[r["exception_type"]][0] += 1
        by_type[r["exception_type"]][1] += r["financial_impact_myr"]
    by_type_list = [
        {"type": t, "count": c, "net": round(n, 2)}
        for t, (c, n) in sorted(by_type.items(), key=lambda kv: -kv[1][1])
    ]

    return {
        "total": total, "net": net, "pos": pos, "neg": neg,
        "resolved": resolved, "open": open_, "by_type": by_type_list,
    }


def _dot(cls: str) -> str:
    return f'<span class="dot {cls}"></span>'


def _render_kpis(stats: dict) -> str:
    net_dot = "pos" if stats["net"] > 0 else ("neg" if stats["net"] < 0 else "zero")
    return "".join([
        f'<div class="kpi"><div class="label">Total exceptions</div>'
        f'<div class="value">{stats["total"]}</div><div class="sub">across the snapshot period</div></div>',
        f'<div class="kpi"><div class="label">Net financial impact</div>'
        f'<div class="value">{_dot(net_dot)}{_money(stats["net"])} MYR</div>'
        f'<div class="sub">negative = owed back to airlines</div></div>',
        f'<div class="kpi"><div class="label">Under-billed (leakage)</div>'
        f'<div class="value">{_dot("pos")}{_money(stats["pos"])} MYR</div>'
        f'<div class="sub">owed to the operator</div></div>',
        f'<div class="kpi"><div class="label">Over-billed</div>'
        f'<div class="value">{_dot("neg")}{_money(stats["neg"])} MYR</div>'
        f'<div class="sub">owed back to airlines</div></div>',
        f'<div class="kpi"><div class="label">Resolved</div>'
        f'<div class="value">{_dot("good")}{stats["resolved"]}</div>'
        f'<div class="sub">by a matching credit note</div></div>',
        f'<div class="kpi"><div class="label">Still open</div>'
        f'<div class="value">{_dot("warn")}{stats["open"]}</div>'
        f'<div class="sub">needs refund or rebill</div></div>',
    ])


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reconciliation Dashboard — Cendana Airports</title>
<style>
  :root {
    color-scheme: light;
    --page: #f9f9f7;
    --surface: #fcfcfb;
    --ink: #0b0b0b;
    --ink-2: #52514e;
    --muted: #898781;
    --grid: #e1e0d9;
    --axis: #c3c2b7;
    --border: rgba(11, 11, 11, 0.10);
    --pos: #2a78d6;       /* diverging: positive / leakage */
    --neg: #e34948;       /* diverging: negative / over-billed */
    --good: #0ca30c;      /* status: resolved */
    --warn: #fab219;      /* status: open */
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--page); color: var(--ink);
         font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
  .wrap { max-width: 1220px; margin: 0 auto; padding: 32px 24px 72px; }
  header h1 { font-size: 22px; margin: 0 0 6px; font-weight: 650; }
  header .sub { margin: 0 0 4px; color: var(--ink-2); font-size: 13px; }
  header code { font-size: 12px; background: var(--surface); border: 1px solid var(--border);
                padding: 1px 5px; border-radius: 4px; }

  .kpis { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-top: 24px; }
  .kpi { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
  .kpi .label { font-size: 12px; color: var(--ink-2); }
  .kpi .value { font-size: 21px; font-weight: 650; margin-top: 6px; font-variant-numeric: tabular-nums; }
  .kpi .sub { font-size: 11px; color: var(--muted); margin-top: 3px; }
  .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 7px; vertical-align: middle; }
  .dot.pos { background: var(--pos); } .dot.neg { background: var(--neg); }
  .dot.zero { background: var(--axis); } .dot.good { background: var(--good); } .dot.warn { background: var(--warn); }

  .section { margin-top: 34px; }
  .section h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em;
                color: var(--ink-2); margin: 0 0 12px; font-weight: 650; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; }

  .bar-row { display: flex; align-items: center; gap: 14px; margin: 9px 0; }
  .bar-label { width: 190px; text-align: right; font-size: 12px; color: var(--ink);
               font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace; }
  .bar-track { flex: 1; position: relative; height: 22px; }
  .bar-zero { position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background: var(--axis); }
  .bar { position: absolute; top: 4px; bottom: 4px; border-radius: 4px; }
  .bar.pos { background: var(--pos); } .bar.neg { background: var(--neg); }
  .bar.zero { background: var(--axis); width: 4px; margin-left: -2px; }
  .bar-val { width: 120px; font-size: 12px; color: var(--ink-2); font-variant-numeric: tabular-nums; }

  .filters { display: flex; flex-wrap: wrap; gap: 10px; margin: 14px 0; align-items: center; }
  .filters label { font-size: 12px; color: var(--ink-2); display: flex; flex-direction: column; gap: 3px; }
  .filters select, .filters input { font: inherit; font-size: 13px; padding: 6px 8px;
      border: 1px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--ink); }
  .filters input { min-width: 220px; }
  .count { margin-left: auto; font-size: 12px; color: var(--muted); }

  .table-scroll { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--grid); white-space: nowrap; }
  th { color: var(--ink-2); font-weight: 600; font-size: 12px; cursor: pointer; user-select: none; }
  th:hover { color: var(--ink); }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .mono { font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace; font-size: 12px; }
  .type-badge { display: inline-block; font-size: 11px; font-family: ui-monospace, monospace;
                padding: 2px 7px; border-radius: 999px; background: var(--page);
                border: 1px solid var(--border); }
  .st-badge { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; }
  .impact-cell { display: inline-flex; align-items: center; gap: 6px; }
  .muted { color: var(--muted); }
  .arrow { color: var(--ink-2); }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Aircraft Billing &amp; Movement Reconciliation</h1>
    <p class="sub">Cendana Airports — exceptions dashboard · snapshot period 2026-01-01 ~ 2026-06-30</p>
    <p class="sub">Generated from <code>output/exceptions.csv</code> · every figure comes from the engine run</p>
  </header>

  <div class="kpis">__KPI__</div>

  <div class="section">
    <h2>Net financial impact by exception type (MYR)</h2>
    <div class="card" id="chart"></div>
  </div>

  <div class="section">
    <h2>Exceptions</h2>
    <div class="filters">
      <label>Type
        <select id="f-type"><option value="">All types</option></select>
      </label>
      <label>Airline
        <select id="f-airline"><option value="">All airlines</option></select>
      </label>
      <label>Status
        <select id="f-status">
          <option value="">All</option>
          <option value="OPEN">Open</option>
          <option value="RESOLVED">Resolved</option>
        </select>
      </label>
      <label>Search
        <input id="f-search" type="text" placeholder="movement / invoice / evidence / airline">
      </label>
      <span class="count" id="count"></span>
    </div>
    <div class="card table-scroll">
      <table>
        <thead>
          <tr>
            <th data-sort="movement_id">Movement</th>
            <th data-sort="exception_type">Type</th>
            <th>Charge</th>
            <th>Airline</th>
            <th class="num" data-sort="expected_amount">Expected</th>
            <th class="num" data-sort="actual_amount">Actual</th>
            <th class="num" data-sort="financial_impact_myr">Impact</th>
            <th>Evidence</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
  const DATA = __DATA__;
  const BYTYPE = __BYTYPE__;

  const fmt = n => Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const sign = n => n > 0 ? '+' : (n < 0 ? '-' : '');
  const money = n => sign(n) + fmt(n);

  // ---- bar chart ----
  function renderChart() {
    const maxAbs = Math.max(...BYTYPE.map(d => Math.abs(d.net)), 1);
    document.getElementById('chart').innerHTML = BYTYPE.map(d => {
      if (d.net === 0) {
        return `<div class="bar-row">
          <div class="bar-label">${d.type}</div>
          <div class="bar-track"><div class="bar-zero"></div><div class="bar zero" style="left:50%"></div></div>
          <div class="bar-val">0.00</div></div>`;
      }
      const side = d.net > 0 ? 'pos' : 'neg';
      const w = (Math.abs(d.net) / maxAbs) * 50;
      const pos = d.net > 0
        ? `left:50%; width:${w}%`
        : `right:50%; width:${w}%`;
      return `<div class="bar-row">
        <div class="bar-label">${d.type}</div>
        <div class="bar-track"><div class="bar-zero"></div><div class="bar ${side}" style="${pos}"></div></div>
        <div class="bar-val">${money(d.net)}</div></div>`;
    }).join('');
  }

  // ---- table ----
  let sortKey = 'financial_impact_myr';
  let sortDir = -1;

  function filtered() {
    const t = document.getElementById('f-type').value;
    const a = document.getElementById('f-airline').value;
    const s = document.getElementById('f-status').value;
    const q = document.getElementById('f-search').value.trim().toLowerCase();
    return DATA.filter(d => {
      if (t && d.exception_type !== t) return false;
      if (a && d.airline_code !== a && d.billed_airline_code !== a) return false;
      if (s === 'OPEN' && d.resolution_status === 'RESOLVED_BY_CREDIT_NOTE') return false;
      if (s === 'RESOLVED' && d.resolution_status !== 'RESOLVED_BY_CREDIT_NOTE') return false;
      if (q) {
        const hay = (d.movement_id + ' ' + d.invoice_line_id + ' ' + d.evidence_ref + ' '
          + d.airline_code + ' ' + d.billed_airline_code).toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }

  function renderTable() {
    const rows = filtered().slice().sort((x, y) => {
      const a = x[sortKey], b = y[sortKey];
      if (typeof a === 'string') return sortDir * a.localeCompare(b);
      return sortDir * (a - b);
    });
    document.getElementById('count').textContent = rows.length + ' of ' + DATA.length + ' rows';
    document.getElementById('tbody').innerHTML = rows.map(d => {
      const air = d.billed_airline_code
        ? `${d.airline_code} <span class="arrow">←</span> ${d.billed_airline_code}` : d.airline_code;
      const imp = d.financial_impact_myr;
      const dot = imp > 0 ? 'pos' : (imp < 0 ? 'neg' : 'zero');
      const isResolved = d.resolution_status !== 'OPEN';
      const st = isResolved
        ? `<span class="st-badge"><span class="dot good"></span>resolved</span>`
        : `<span class="st-badge"><span class="dot warn"></span>open</span>`;
      const ev = d.evidence_ref || '<span class="muted">— none —</span>';
      return `<tr>
        <td class="mono">${d.movement_id}</td>
        <td><span class="type-badge">${d.exception_type}</span></td>
        <td>${d.charge_type}</td>
        <td>${air}</td>
        <td class="num">${fmt(d.expected_amount)}</td>
        <td class="num">${fmt(d.actual_amount)}</td>
        <td class="num"><span class="impact-cell"><span class="dot ${dot}"></span>${money(imp)}</span></td>
        <td class="mono">${ev}</td>
        <td>${st}</td></tr>`;
    }).join('');
  }

  // ---- filters ----
  function populate() {
    const types = [...new Set(DATA.map(d => d.exception_type))].sort();
    const airlines = [...new Set(DATA.flatMap(d => [d.airline_code, d.billed_airline_code].filter(Boolean)))].sort();
    const tsel = document.getElementById('f-type');
    types.forEach(t => tsel.insertAdjacentHTML('beforeend', `<option value="${t}">${t}</option>`));
    const asel = document.getElementById('f-airline');
    airlines.forEach(a => asel.insertAdjacentHTML('beforeend', `<option value="${a}">${a}</option>`));
  }

  document.querySelectorAll('th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const k = th.dataset.sort;
      if (sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = -1; }
      renderTable();
    });
  });
  ['f-type', 'f-airline', 'f-status', 'f-search'].forEach(id =>
    document.getElementById(id).addEventListener('input', renderTable));

  renderChart();
  populate();
  renderTable();
</script>
</body>
</html>
"""


def main() -> None:
    csv_path = OUTPUT_DIR / "exceptions.csv"
    if not csv_path.exists():
        print("output/exceptions.csv not found. Run `python -m src.main` first.")
        return

    rows = _read_rows(csv_path)
    stats = _build_stats(rows)
    html = (
        _HTML_TEMPLATE
        .replace("__KPI__", _render_kpis(stats))
        .replace("__DATA__", json.dumps(rows))
        .replace("__BYTYPE__", json.dumps(stats["by_type"]))
    )

    out_path = OUTPUT_DIR / "dashboard.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"[wrote] {out_path}")


if __name__ == "__main__":
    main()
