"""对账主循环 reconcile 的边界测试：逐类异常 + 关键互斥关系。

覆盖：11 类异常中的 9 类（本数据集实际出现的），以及
「错记航司不能同时算漏收」这个最容易出错的互斥逻辑、容差边界、期间过滤、符号约定。
"""
from __future__ import annotations

from datetime import datetime

from src.reconcile import reconcile
from tests._helpers import by_type, get_assumptions, get_rate_df, make_line, make_movement


def _run(movements, ledger, **asmp):
    return reconcile(movements, ledger, get_rate_df(), get_assumptions(**asmp))


def test_missing_charge():
    # 该收 LANDING 4944，但账单里没有任何行
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0)
    exc = _run([m], [])
    miss = by_type(exc, "MISSING_CHARGE")
    assert len(miss) == 1
    assert miss[0]["charge_type"] == "LANDING"
    assert miss[0]["financial_impact_myr"] == 4944.00
    assert miss[0]["evidence_ref"] == "EVD-TEST-001"  # 必须挂证据号


def test_wrong_rate():
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0)
    line = make_line(charge_type="LANDING", quantity=412, unit_rate=10.00, amount_billed=4120.00)
    wr = by_type(_run([m], [line]), "WRONG_RATE")
    assert len(wr) == 1
    assert wr[0]["financial_impact_myr"] == 824.00  # 4944 - 4120


def test_wrong_quantity():
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0)
    line = make_line(charge_type="LANDING", quantity=410, unit_rate=12.00, amount_billed=4920.00)
    wq = by_type(_run([m], [line]), "WRONG_QUANTITY")
    assert len(wq) == 1
    assert wq[0]["financial_impact_myr"] == 24.00  # 4944 - 4920


def test_wrong_amount():
    # 单价对、数量对，但金额算错 —— 这是真实数据里未出现的那一类
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0)
    line = make_line(charge_type="LANDING", quantity=412, unit_rate=12.00, amount_billed=4950.00)
    wa = by_type(_run([m], [line]), "WRONG_AMOUNT")
    assert len(wa) == 1
    assert wa[0]["financial_impact_myr"] == -6.00  # 4944 - 4950


def test_duplicate():
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0)
    l1 = make_line(invoice_line_id="BL-A", charge_type="LANDING", quantity=412,
                   unit_rate=12.00, amount_billed=4944.00)
    l2 = make_line(invoice_line_id="BL-B", charge_type="LANDING", quantity=412,
                   unit_rate=12.00, amount_billed=4944.00)
    dup = by_type(_run([m], [l1, l2]), "DUPLICATE")
    assert len(dup) == 1
    assert dup[0]["invoice_line_id"] == "BL-B"  # 第 2 行算重复
    assert dup[0]["financial_impact_myr"] == -4944.00


def test_orphan_charge():
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0)
    line = make_line(movement_id="MOVGHOST", charge_type="LANDING", amount_billed=5000.00)
    orph = by_type(_run([m], [line]), "ORPHAN_CHARGE")
    assert len(orph) == 1
    assert orph[0]["financial_impact_myr"] == -5000.00


def test_wrong_airline_net_zero_and_not_double_counted():
    # 该收的 LANDING 被开到了 QC 头上：只算 1 条异常，净影响 0，且不能同时报漏收
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0)  # 航司 FX
    line = make_line(airline_code="QC", charge_type="LANDING", quantity=412,
                     unit_rate=12.00, amount_billed=4944.00)
    exc = _run([m], [line])
    assert len(exc) == 1, f"期望 1 条，实际 {len(exc)} 条（错记航司被重复计数了）"
    wa = by_type(exc, "WRONG_AIRLINE")[0]
    assert wa["financial_impact_myr"] == 0.0
    assert wa["billed_airline_code"] == "QC"
    assert by_type(exc, "MISSING_CHARGE") == []  # 关键互斥断言


def test_wrong_airline_plus_genuine_missing():
    # 同一航班：LANDING 开错航司，同时 PARKING/AEROBRIDGE 真的漏收
    m = make_movement(stand_type="CONTACT", pax_departing=0,
                      arrival_datetime=datetime(2026, 3, 1, 14, 0),
                      departure_datetime=datetime(2026, 3, 1, 17, 0))  # 180 分钟
    line = make_line(airline_code="QC", charge_type="LANDING", quantity=412,
                     unit_rate=12.00, amount_billed=4944.00)
    exc = _run([m], [line])
    assert by_type(exc, "WRONG_AIRLINE")[0]["charge_type"] == "LANDING"
    missing_types = [e["charge_type"] for e in by_type(exc, "MISSING_CHARGE")]
    assert set(missing_types) == {"PARKING", "AEROBRIDGE"}  # 只漏这两类，LANDING 不算漏


def test_cancelled_charged():
    m = make_movement(status="CANCELLED", stand_type="REMOTE", pax_departing=0)
    line = make_line(charge_type="LANDING", amount_billed=4944.00)
    cc = by_type(_run([m], [line]), "CANCELLED_CHARGED")
    assert len(cc) == 1
    assert cc[0]["financial_impact_myr"] == -4944.00


def test_remote_aerobridge():
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0)  # 期望只有 LANDING
    land = make_line(invoice_line_id="BL-LAND", charge_type="LANDING", quantity=412,
                     unit_rate=12.00, amount_billed=4944.00)
    bridge = make_line(invoice_line_id="BL-BRIDGE", charge_type="AEROBRIDGE", quantity=2,
                       unit_rate=120.00, amount_billed=240.00)
    ra = by_type(_run([m], [land, bridge]), "REMOTE_AEROBRIDGE")
    assert len(ra) == 1
    assert ra[0]["financial_impact_myr"] == -240.00
    assert by_type(_run([m], [land, bridge]), "MISSING_CHARGE") == []  # LANDING 已正确开单


def test_diverted_overcharge():
    m = make_movement(status="DIVERTED", stand_type="REMOTE", pax_departing=0,
                      departure_datetime=datetime(2026, 3, 1, 16, 30))  # 120 分钟
    land = make_line(invoice_line_id="BL-LAND", charge_type="LANDING", quantity=411,
                     unit_rate=12.00, amount_billed=4932.00)
    park = make_line(invoice_line_id="BL-PARK", charge_type="PARKING", quantity=4,
                     unit_rate=8.00, amount_billed=32.00)
    do = by_type(_run([m], [land, park]), "DIVERTED_OVERCHARGE")
    assert len(do) == 1
    assert do[0]["charge_type"] == "PARKING"
    assert do[0]["financial_impact_myr"] == -32.00


def test_psc_on_cargo():
    m = make_movement(pax_departing=0, stand_type="REMOTE")  # 货机：0 旅客
    land = make_line(invoice_line_id="BL-LAND", charge_type="LANDING", quantity=411,
                     unit_rate=12.00, amount_billed=4932.00)
    psc = make_line(invoice_line_id="BL-PSC", charge_type="PSC", quantity=50,
                    unit_rate=35.00, amount_billed=1750.00)
    pc = by_type(_run([m], [land, psc]), "PSC_ON_CARGO")
    assert len(pc) == 1
    assert pc[0]["financial_impact_myr"] == -1750.00


def test_tolerance_at_boundary_not_flagged():
    # 差异正好 0.05 → 视为舍入，不报
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0)
    line = make_line(charge_type="LANDING", quantity=412, unit_rate=12.00, amount_billed=4944.05)
    assert _run([m], [line]) == []


def test_tolerance_just_over_boundary_flagged():
    # 差异 0.06 > 0.05 → 报，且单价、数量都对，判定为 WRONG_AMOUNT
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0)
    line = make_line(charge_type="LANDING", quantity=412, unit_rate=12.00, amount_billed=4944.06)
    wa = by_type(_run([m], [line]), "WRONG_AMOUNT")
    assert len(wa) == 1
    assert wa[0]["financial_impact_myr"] == -0.06


def test_tolerance_is_read_from_assumptions_not_hardcoded():
    # 把容差临时改成 0，则 0.05 的差异会从「舍入」变成「异常」→ 证明是运行时读的
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0)
    line = make_line(charge_type="LANDING", quantity=412, unit_rate=12.00, amount_billed=4944.05)
    wa = by_type(_run([m], [line], amount_tolerance="0"), "WRONG_AMOUNT")
    assert len(wa) == 1


def test_movement_outside_period_is_skipped():
    m = make_movement(arrival_datetime=datetime(2025, 12, 31, 14, 30))  # 期间外
    line = make_line(charge_type="LANDING", amount_billed=99999.00)  # 明显错
    assert _run([m], [line]) == []  # 期间外，完全跳过


def test_financial_impact_sign_convention():
    # 漏收 → 正（应补收）；多收/错收 → 负（应退）
    m_miss = make_movement(movement_id="MOV-MISS", mtow_tonnes=412.0,
                           stand_type="REMOTE", pax_departing=0)
    miss = by_type(_run([m_miss], []), "MISSING_CHARGE")[0]
    assert miss["financial_impact_myr"] > 0

    m_over = make_movement(movement_id="MOV-OVER", status="CANCELLED",
                           stand_type="REMOTE", pax_departing=0)
    over_line = make_line(movement_id="MOV-OVER", charge_type="LANDING", amount_billed=100.00)
    over = by_type(_run([m_over], [over_line]), "CANCELLED_CHARGED")[0]
    assert over["financial_impact_myr"] < 0


def test_clean_movement_no_exception():
    # COMPLETED + 4 种费用全部正确开单 → 0 异常（证明无误报）
    m = make_movement(mtow_tonnes=412.0, stand_type="CONTACT",
                      arrival_datetime=datetime(2026, 3, 1, 14, 0),
                      departure_datetime=datetime(2026, 3, 1, 16, 30))  # 150 分钟
    lines = [
        make_line(invoice_line_id="BL-L", charge_type="LANDING", quantity=412,
                  unit_rate=12.00, amount_billed=4944.00),
        make_line(invoice_line_id="BL-P", charge_type="PARKING", quantity=6,
                  unit_rate=8.00, amount_billed=48.00),
        make_line(invoice_line_id="BL-A", charge_type="AEROBRIDGE", quantity=3,
                  unit_rate=120.00, amount_billed=360.00),
        make_line(invoice_line_id="BL-S", charge_type="PSC", quantity=100,
                  unit_rate=35.00, amount_billed=3500.00),
    ]
    assert _run([m], lines) == []


def test_three_duplicates_two_flagged():
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0)
    lines = [make_line(invoice_line_id=f"BL-{i}", charge_type="LANDING", quantity=412,
                       unit_rate=12.00, amount_billed=4944.00) for i in range(3)]
    dup = by_type(_run([m], lines), "DUPLICATE")
    assert len(dup) == 2  # 第 2、3 行是重复


def test_cancelled_with_no_ledger_no_exception():
    m = make_movement(status="CANCELLED", stand_type="REMOTE", pax_departing=0)
    assert _run([m], []) == []  # 取消 + 无账单 → 无异常（不算漏收）


def test_multiple_charge_types_mixed():
    # LANDING 单价错 + PARKING 漏收同时发生 → 两条不同类型异常
    m = make_movement(mtow_tonnes=412.0, stand_type="REMOTE", pax_departing=0,
                      departure_datetime=datetime(2026, 3, 1, 16, 30))  # 120 分钟 → 停车 32
    line = make_line(charge_type="LANDING", quantity=412, unit_rate=10.00, amount_billed=4120.00)
    exc = _run([m], [line])
    assert len(by_type(exc, "WRONG_RATE")) == 1
    miss = by_type(exc, "MISSING_CHARGE")
    assert len(miss) == 1
    assert miss[0]["charge_type"] == "PARKING"
