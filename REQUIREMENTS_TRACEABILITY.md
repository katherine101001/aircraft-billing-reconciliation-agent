# 需求 → 代码对照清单（Requirements Traceability）

> 给考官看的「寻路地图」：题目 `Case_Study_Brief.md` 的每一条硬性要求，
> 在代码里具体落在哪个文件、哪个函数。按「模块.函数」索引，行号为辅助定位。
> 全部要求均已完成，无未实现的硬性项。

---

## 5.1 对账引擎（确定性核心）

| 题目要求 | 实现位置 | 说明 |
|---|---|---|
| 读入数据（movements / ledger / rate / credit_notes 等） | `src/load.py`（`load_movements`、`load_billing_ledger`、`load_rate_card`、`load_credit_notes`） | 统一读 CSV，日期字段正确解析 |
| 应用计费规则算「应该收多少」 | `src/billing_rules.py`（`compute_expected_charges`） | 4 种费用 + 状态过滤 |
| 逐条比对、产出结构化异常列表 | `src/reconcile.py`（`reconcile`） | 返回 list[dict] |
| 每条异常含：movement/id、类型、期望值、实际值、财务影响、证据号 | `src/reconcile.py`（`_make_exception`） | 默认字段补齐 |
| 财务影响符号约定（正=该归运营方，负=该退航司） | `src/reconcile.py` 模块 docstring + `reconcile` | 每处 `financial_impact_myr` 计算一致 |
| 金额容差 ≤ 0.05 视为舍入、不报 | `src/reconcile.py`（`reconcile` 第 210-212 行） | `abs(diff) <= tolerance` |

## 4 计费规则（核心算法，逐条可查）

| 规则 | 实现位置 |
|---|---|
| 仅 billable 状态计费（CANCELLED 不计） | `src/billing_rules.py:32-34` |
| LANDING = ceil(MTOW) × 日期敏感单价 | `src/billing_rules.py:48-55` + `src/rate_card.py`（`lookup_rate`） |
| PARKING = 超出宽限的 15 分钟档 × 单价 | `src/billing_rules.py:62-72` |
| AEROBRIDGE = 按小时、仅 CONTACT 机位 | `src/billing_rules.py:74-83` |
| PSC = 离港旅客 × 国内/国际，货机 0 人不收 | `src/billing_rules.py:85-94` |
| DIVERTED 只收起降费 | `src/billing_rules.py:57-60` |
| 日期敏感单价（3-31 前 12 / 4-01 起 13.5） | `src/rate_card.py`（`lookup_rate`，按 `effective_from/to` 窗口匹配） |

## 11 类异常判定（`src/reconcile.py`）

| 异常类型 | 判定位置（reconcile.py） |
|---|---|
| MISSING_CHARGE | 集合级检查，`len(acts) == 0` 分支 |
| WRONG_RATE / WRONG_QUANTITY / WRONG_AMOUNT | 集合级检查，单行差异的三种判定 |
| DUPLICATE | 集合级检查，`len(acts) > 1` 分支 |
| ORPHAN_CHARGE | 分组时 `movement_id` 不在 `mov_by_id` |
| WRONG_AIRLINE（净 0，退款+重开） | 行级检查，航司不匹配分支 |
| CANCELLED_CHARGED / REMOTE_AEROBRIDGE / DIVERTED_OVERCHARGE / PSC_ON_CARGO | 行级检查各自分支 |

## 5.2 AI 推理层

| 题目要求 | 实现位置 |
|---|---|
| 异常类型 → 大白话业务语言 | `src/ai_layer.py:15-27`（`TYPE_PLAIN_LANGUAGE`） |
| 起草可粘贴的说明 + 引用证据号 | `src/ai_layer.py:30-50`（`explain_exception`） |
| 生成管理层自然语言总结 | `src/ai_layer.py:53-78`（`summarize`） |
| 边界：引擎定数字/分类，模型只写字 | `src/ai_layer.py` 模块 docstring（第 1-8 行） |
| 真实模型接入点（当前 mock） | `src/ai_layer.py:10`（标注 mock）+ 第 81-85 行（TODO） |

## 5.3 输出

| 要求 | 实现位置 | 产物 |
|---|---|---|
| 异常报告（CSV） | `src/report.py`（`write_report`） | `output/exceptions.csv` |
| 管理总结（Markdown） | `src/report.py`（`write_report`）+ `src/ai_layer.py`（`summarize`） | `output/summary.md` |

## 8 治理约束（红线）

| 约束 | 实现位置 |
|---|---|
| 不硬编码业务输入 | 全部业务数字来自 `data/*.csv`；`src/config.py` 唯一读 assumptions，`src/rate_card.py` 唯一查价 |
| 费率/阈值/日期/规则运行时读取 | `src/config.py` + `src/rate_card.py` + `src/load.py` |
| 快照期间、不用今天日期 | `src/reconcile.py:56-57, 88`（按 `reconciliation_period_start/end` 过滤） |
| 9999-12-31 开放结束哨兵正确解析 | `src/load.py:30-32`（用 `date.fromisoformat` 避开 pandas 纳秒上限） |
| 挂证据号到每条有 movement 的发现 | `src/reconcile.py`（`evidence_ref` 字段随每条异常输出） |
| 人工签字落点 | `src/ai_layer.py:76`（总结里声明「发往航司前须人工签字」）+ `README.md` |

## 6 交付物状态

| 交付物 | 状态 |
|---|---|
| 代码（Git 仓库或 zip） | ⚠️ 待 `git init` 初始化并提交（引擎已 100% 完成） |
| README（从零复现） | ✅ `README.md`（含预期输出校验锚点） |
| PPT（≤12 页） | ⏳ 由候选人制作 |
| AI 使用日志 | ✅ `AI_USAGE_LOG.md`（3 个错误 + 如何发现） |

---

## 附：关键设计判断（documented assumptions）

题目允许「合理判断 + 写下来」。本实现的判断如下：

1. **重复开单（DUPLICATE）**：同一 movement 同一 charge_type 的多条账，第 1 条算主行、其余算重复（`reconcile.py` 的 `len(acts) > 1` 分支）。
2. **错记航司 vs 漏收的互斥**：一笔费用被开错航司时，只报 1 条 `WRONG_AIRLINE`（净 0），**不再**额外报 `MISSING_CHARGE`，避免同一事实重复计数（`reconcile.py:98, 192-193` 的 `wrong_airline_types` 去重）。
3. **`airlines.csv` 未用于核心对账**：核心判定只依赖 movement/ledger 的 `airline_code`，航司名册仅用于（可选）AI 文案的航司全名润色，不影响正确性。
4. **credit note 覆盖判定**：`amount >= |financial_impact|` 且币种为 MYR 即视为覆盖（`reconcile.py:268-272`）。

## 附：测试（可复现的正确性证据）

运行 `python -m tests.run_all`，共 **88 个用例**覆盖计费规则、查价、对账判定、credit note 解决、AI 层、报告输出、配置/加载、端到端，全部通过。见 `tests/`。

代码覆盖率达 **100%**（`src/` 271 条语句、84 个分支）：`python -m coverage run -m tests.run_all && python -m coverage report -m`。
