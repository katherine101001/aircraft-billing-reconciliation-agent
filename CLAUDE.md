# CLAUDE.md — 项目指令与开发诉求

## 项目是什么

CEAI 面试开发题「Aircraft Billing and Movement Reconciliation Agent」。
本质是**数据对账 / 财务审计**题：用确定性引擎比对 `movements.csv`（实际起降真相）
与 `billing_ledger.csv`（财务开单），找出差异、算财务影响（MYR）、挂证据引用，
AI 层只负责把结果写成文字、不碰数字。

## 用户画像与开发诉求（重要）

- 用户是**开发小白 + 航空零知识**，需要我用**产品经理视角**从零讲解，中文交流。
- 遇到业务概念（MTOW / 廊桥 / 备降 / credit note 等）要先解释清楚，不要默认用户懂。
- 代码注释用中文，变量/函数名用英文，可读性优先，用户要能向考官解释每一行。
- 截止日期紧：**约 4 天（~2026-08-17）**，优先跑通核心引擎出报告，PPT 用引擎真实数字。

## 关键约定（治理红线，不可违反）

1. **禁止硬编码**任何业务数字/日期/阈值 —— 全部从 `rate_card.csv` + `assumptions.csv` 运行时读取。
2. 报告和 PPT 里的每个数字都必须来自引擎输出，且与那次运行一致。
3. 只对账快照期间（2026-01-01 ~ 2026-06-30），用 `data_snapshot_date`，不用今天。
4. 差异 ≤ `amount_tolerance`(0.05) 是舍入，**不报**。
5. credit note 只有 `related_invoice_line_id` 精确匹配且金额覆盖才解决异常，空 line_id 不解决。
6. 错记航司 = 1 条异常、净影响 0，但要同时给出「退款给错航司 + 重开给正确航司」。

## 计费规则速查（核心算法）

- LANDING = ceil(MTOW) × 日期敏感单价（03-31 前 12.00，04-01 起 13.50）
- PARKING = ceil((停留分钟 − 60 宽限) / 15) × 8.00，宽限内不收
- AEROBRIDGE = ceil(停留分钟 / 60) × 120.00，仅 CONTACT 机位
- PSC = 离港旅客 × (DOMESTIC 11 / INTERNATIONAL 35)，货机 0 人 不收
- CANCELLED 全不收；DIVERTED 只收起降费

## 代码结构

- `src/config.py` 读 assumptions；`src/load.py` 读 6 表；`src/rate_card.py` 查价；
  `src/billing_rules.py` 算「应该收」；`src/reconcile.py` 对账主循环 + credit note 解决；
  `src/ai_layer.py` 只写文字（当前 mock）；`src/report.py` 输出；`src/main.py` 入口。
- 运行：`python -m src.main`，输出到 `output/exceptions.csv` + `output/summary.md`。

## 已踩过的坑

见 `AI_USAGE_LOG.md`。重点记住：**跑通 ≠ 正确**，异常类型之间有互斥/归属关系，
必须回头核对 CSV 输出，确认同一笔事实没被重复归类。
