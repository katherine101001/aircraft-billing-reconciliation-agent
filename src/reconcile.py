"""对账主循环：把 movements（真相）与 billing_ledger（待查）逐条比对。

输出结构化异常列表。每个异常是一条 dict，含：
  movement_id, invoice_line_id, exception_type, charge_type,
  airline_code, billed_airline_code, expected_amount, actual_amount,
  financial_impact_myr, evidence_ref, resolution_status, credit_note_id

财务影响符号约定（来自题目）：
  正数 = 钱应归运营方（漏收/少收，该补收）
  负数 = 钱应退给航司（多收/错收）

异常类型（11 类）：
  MISSING_CHARGE      该收的费没开单（漏收）
  WRONG_RATE          单价用错
  WRONG_QUANTITY      数量用错
  WRONG_AMOUNT        数量/单价都对，金额仍对不上
  DUPLICATE           同一 movement 同一 charge_type 重复开单
  ORPHAN_CHARGE       开单指向不存在的 movement
  WRONG_AIRLINE       开到了错误的航司头上（净影响 0，但要退款+重开）
  CANCELLED_CHARGED   对取消航班收费
  REMOTE_AEROBRIDGE   远机位收了廊桥费
  DIVERTED_OVERCHARGE 备降航班收了起降费以外的费用
  PSC_ON_CARGO        货机（0 旅客）收了旅客服务费
"""
from __future__ import annotations

from collections import defaultdict

from .billing_rules import compute_expected_charges
from .config import as_date, as_enum_set, as_float


def _make_exception(**kwargs) -> dict:
    """构造一条异常，补齐默认字段。"""
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
    """对账入口。返回异常列表（未做 credit note 解决，见 resolve_credit_notes）。"""
    tolerance = as_float(assumptions, "amount_tolerance")
    period_start = as_date(assumptions, "reconciliation_period_start")
    period_end = as_date(assumptions, "reconciliation_period_end")

    mov_by_id = {m["movement_id"]: m for m in movements}

    # 把 ledger 按 movement_id 分组，方便每个 movement 快速取到自己的行
    ledger_by_movement: dict[str, list[dict]] = defaultdict(list)
    orphan_lines: list[dict] = []
    for line in ledger:
        mid = str(line["movement_id"]).strip()
        if mid in mov_by_id:
            ledger_by_movement[mid].append(line)
        else:
            orphan_lines.append(line)  # 指向不存在的 movement

    exceptions: list[dict] = []

    # ---------- 1) 孤儿账：无对应 movement ----------
    for line in orphan_lines:
        exceptions.append(_make_exception(
            movement_id=line["movement_id"],
            invoice_line_id=line["invoice_line_id"],
            exception_type="ORPHAN_CHARGE",
            charge_type=line["charge_type"],
            airline_code=line["airline_code"],
            actual_amount=float(line["amount_billed"]),
            financial_impact_myr=round(-float(line["amount_billed"]), 2),  # 不该收，应退
        ))

    # ---------- 2) 逐 movement 对账 ----------
    for m in movements:
        # 只对账快照期间内的起降（按到达日期判断）
        if not (period_start <= m["arrival_datetime"].date() <= period_end):
            continue

        lines = ledger_by_movement.get(m["movement_id"], [])
        expected_list = compute_expected_charges(m, rate_df, assumptions)
        expected = {e["charge_type"]: e for e in expected_list}

        status = m["status"]
        valid_lines: list[dict] = []
        # 记录被「错记航司」的费用类型：这些费用不算漏收，避免与 WRONG_AIRLINE 重复计数
        wrong_airline_types: set[str] = set()

        # --- 2a) 行级检查：每条 ledger 行本身是否合法 ---
        for line in lines:
            charge_type = line["charge_type"]
            actual_amt = float(line["amount_billed"])

            # 错记航司：净影响 0，但要退款 + 重开
            if line["airline_code"] != m["airline_code"]:
                wrong_airline_types.add(charge_type)
                exceptions.append(_make_exception(
                    movement_id=m["movement_id"],
                    invoice_line_id=line["invoice_line_id"],
                    exception_type="WRONG_AIRLINE",
                    charge_type=charge_type,
                    airline_code=m["airline_code"],          # 正确航司
                    billed_airline_code=line["airline_code"],  # 被错记的航司
                    expected_amount=expected.get(charge_type, {}).get("amount", 0.0),
                    actual_amount=actual_amt,
                    financial_impact_myr=0.0,                # net 0
                    evidence_ref=m["evidence_ref"],
                ))
                continue

            # 取消航班收费
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

            # 备降航班多收费（只允许 LANDING）
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

            # 远机位收廊桥费
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

            # 货机（0 旅客）收了 PSC
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

        # --- 2b) 集合级检查：expected 与合法行的比对 ---
        by_type: dict[str, list[dict]] = defaultdict(list)
        for line in valid_lines:
            by_type[line["charge_type"]].append(line)

        for charge_type, exp in expected.items():
            acts = by_type.get(charge_type, [])
            exp_amt = exp["amount"]

            if len(acts) == 0:
                # 被错记航司的费用不算漏收（已在 WRONG_AIRLINE 里处理退款+重开）
                if charge_type in wrong_airline_types:
                    continue
                # 该收的费完全没开单
                exceptions.append(_make_exception(
                    movement_id=m["movement_id"],
                    exception_type="MISSING_CHARGE",
                    charge_type=charge_type,
                    airline_code=m["airline_code"],
                    expected_amount=exp_amt,
                    financial_impact_myr=round(exp_amt, 2),  # 漏收，应补收
                    evidence_ref=m["evidence_ref"],
                ))

            elif len(acts) == 1:
                a = acts[0]
                actual_amt = float(a["amount_billed"])
                diff = round(exp_amt - actual_amt, 2)

                # 差异在容忍度内 → 舍入，不报
                if abs(diff) <= tolerance:
                    continue

                # 判定到底是哪错了
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
                # 重复开单：第一行算主行，其余是重复
                for extra in acts[1:]:
                    extra_amt = float(extra["amount_billed"])
                    exceptions.append(_make_exception(
                        movement_id=m["movement_id"],
                        invoice_line_id=extra["invoice_line_id"],
                        exception_type="DUPLICATE",
                        charge_type=charge_type,
                        airline_code=m["airline_code"],
                        actual_amount=extra_amt,
                        financial_impact_myr=round(-extra_amt, 2),  # 多收，应退
                        evidence_ref=m["evidence_ref"],
                    ))

    return exceptions


def resolve_credit_notes(exceptions: list[dict], credit_notes: list[dict]) -> list[dict]:
    """用 credit note 判定异常是否已被解决。

    解决条件（来自题目）：credit note 的 related_invoice_line_id 精确等于
    问题行，且金额 + 币种覆盖该差异。空 line_id 的 credit note 不解决任何异常。
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
