"""AI 推理层 —— 只负责「把话写出来」，绝不参与任何数字计算或分类。

=====================================================================
 边界（题目硬性要求）：对账引擎（reconcile.py）决定异常类型和每个金额；
 本模块只做「字符串生成」，输入是引擎产出的异常 dict，输出是文本，
 不修改任何数字或分类字段。接入真实 LLM 时，只替换 explain() 与
 summarize() 的实现，其余逻辑不变。
=====================================================================

当前为 MOCK 实现（无需 API key）。真实模型接入点已用 TODO 标注。
"""
from __future__ import annotations

# 异常类型 → 大白话业务语言（供 explain 使用）
TYPE_PLAIN_LANGUAGE = {
    "MISSING_CHARGE": "该航班应收取的费用未开单，属于漏收",
    "WRONG_RATE": "开单使用了错误的单价",
    "WRONG_QUANTITY": "开单使用了错误的计费数量",
    "WRONG_AMOUNT": "单价与数量均正确，但金额计算有误",
    "DUPLICATE": "同一航班同一费用被重复开单",
    "ORPHAN_CHARGE": "开单引用了不存在的起降记录，无法对应到任何航班",
    "WRONG_AIRLINE": "费用开到了错误的航空公司头上",
    "CANCELLED_CHARGED": "对已取消的航班收取了费用",
    "REMOTE_AEROBRIDGE": "远机位航班被收取了廊桥费（远机位不提供廊桥）",
    "DIVERTED_OVERCHARGE": "备降航班被收取了起降费以外的费用",
    "PSC_ON_CARGO": "货机（无离港旅客）被收取了旅客服务费",
}


def explain_exception(exc: dict) -> str:
    """把一条异常翻译成一段可粘贴给客户的说明，引用证据号。"""
    etype = exc["exception_type"]
    plain = TYPE_PLAIN_LANGUAGE.get(etype, etype)
    impact = exc["financial_impact_myr"]
    evidence = exc["evidence_ref"] or "无"

    if etype == "WRONG_AIRLINE":
        return (
            f"【{etype}】{plain}。航班 {exc['movement_id']}（{exc['airline_code']}）的"
            f"{exc['charge_type']}费用 {exc['actual_amount']:.2f} MYR 被误开给了"
            f"{exc['billed_airline_code']}。需两笔动作：向 {exc['billed_airline_code']} 退款，"
            f"并向 {exc['airline_code']} 重新开票。证据号 {evidence}。"
        )

    direction = "应收未收" if impact > 0 else ("应退" if impact < 0 else "净影响为零")
    return (
        f"【{etype}】{plain}。航班 {exc['movement_id']} 的 {exc['charge_type']} 费用，"
        f"期望 {exc['expected_amount']:.2f} MYR，实际 {exc['actual_amount']:.2f} MYR，"
        f"差额 {abs(impact):.2f} MYR（{direction}）。证据号 {evidence}。"
    )


def summarize(stats: dict) -> str:
    """生成给管理层的自然语言总结。数字全部由 stats 传入（来自引擎统计），
    本函数不自行计算任何金额。"""
    lines = [
        "# 对账总结（管理层版）",
        "",
        f"本次对账共发现 **{stats['total_exceptions']}** 处异常，",
        f"净财务影响 **{stats['net_impact']:,.2f} MYR**。",
        "",
        f"- 漏收/少收（应补收）：{stats['positive_total']:,.2f} MYR",
        f"- 多收/错收（应退航司）：{abs(stats['negative_total']):,.2f} MYR",
        f"- 尚未解决的敞口：{stats['open_count']} 条",
        "",
        "## 按异常类型分布",
    ]
    for etype, (cnt, amt) in sorted(stats["by_type"].items(), key=lambda kv: -kv[1][1]):
        lines.append(f"- {etype}：{cnt} 条，合计 {amt:,.2f} MYR")

    lines += [
        "",
        "## 建议优先处理",
        "1. 金额最大的未解决异常优先核对证据；",
        "2. 涉及退款（负向）的异常需先经人工复核，再向航司发出；",
        "3. 本报告为建议，发往航司前必须有人工签字确认。",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------------
# 真实模型接入点（TODO）：把下面的 mock 换成真实 LLM 调用。
#   例：explain_exception = lambda exc: llm(EXPLAIN_PROMPT.format(exc=exc))
#   注意：prompt 只让模型「措辞」，绝不把金额/分类的判定权交给模型。
# ------------------------------------------------------------------
