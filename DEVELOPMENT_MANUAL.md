# 开发手册 — 飞机计费与起降对账系统

> 这是你这一周照着做的开发手册。每一节都是一份可勾选的 checklist。
> 数据来源、规则、陷阱全部整理自 `Case_Study_Brief.md` + `DATA_DICTIONARY.md` + 6 个数据文件。
> 遇到任何不确定，先回来查这份手册，不要凭感觉写。

---

## 0. 一句话项目目标

读入 6 张表，用确定性引擎算出「每个航班应该收多少钱」，和财务账（billing_ledger）对比，
找出**每一处对不上的地方**，算清财务影响（MYR），挂上证据引用（evidence_ref），
再由 AI 层把结果写成大白话给管理层看。

---

## 1. 交付物清单（就 3 样，缺一不可）

- [ ] **代码** — Git 仓库或 zip，含 `.env.example`（只写 key 名字，不写真实密钥）
- [ ] **README.md** — 陌生人从零 clone → 装依赖 → 配置 → 运行 → 复现报告，写确切命令
- [ ] **PPT** — 不超过 12 页，面向收入保障负责人，所有数字来自自己的引擎

**额外（会被打分）：**
- [ ] **AI 使用日志**（半页）：用了什么工具、干什么、1~2 个「AI 说错/没用、我怎么发现的」时刻

---

## 2. 数据源清单（6 张表，CSV 和 Excel 是同一份，选 CSV 即可）

| 文件 | 行数 | 作用 | 主键 |
|---|---|---|---|
| `movements.csv` | 240 | 实际起降日志（**真相来源**） | `movement_id` |
| `billing_ledger.csv` | 707 | 财务开的每一行费用（**待查对象**） | `invoice_line_id` |
| `rate_card.csv` | 6 | 官方单价（带日期窗口和条件） | (charge_type+condition+日期) |
| `airlines.csv` | 14 | 航空公司主数据 | `airline_code` |
| `credit_notes.csv` | 9 | 已开出的冲销单 | `cn_id` |
| `assumptions.csv` | 12 | 对账规则（快照日期/容忍度/宽限期…） | `key` |
| `aircraft_billing_workbook.xlsx` | — | 同上 6 张表（可忽略） | — |

### 字段速查

**movements.csv**（一行 = 一次起降周转）
```
movement_id, flight_no, airline_code, aircraft_reg, aircraft_type,
mtow_tonnes, arrival_datetime, departure_datetime, stand, stand_type,
pax_departing, scope, status, evidence_ref
```
- `stand_type`: CONTACT（靠桥）/ REMOTE（远机位）
- `scope`: DOMESTIC / INTERNATIONAL
- `status`: COMPLETED / CANCELLED / DIVERTED
- `evidence_ref`: 证据引用，形如 `EVD-20260209-0001`，**每个有 movement 的异常必须带上**

**billing_ledger.csv**（一行 = 一笔费用）
```
invoice_line_id, invoice_id, invoice_date, airline_code,
movement_id, charge_type, quantity, unit_rate, amount_billed, currency
```
- `movement_id` **可能指向不存在的 movement**（孤儿账）
- 同一 movement 同一 charge_type 出现多次 = 重复收费

**rate_card.csv**
```
charge_type, basis, condition, effective_from, effective_to, unit_rate, currency
```

**credit_notes.csv**
```
cn_id, cn_date, airline_code, related_invoice_id,
related_invoice_line_id, reason_code, amount, currency
```
- `related_invoice_line_id` 可能为空

**assumptions.csv** — 关键 key 值（运行时读，别硬编码）：
```
data_snapshot_date         = 2026-07-01
reconciliation_period_start = 2026-01-01
reconciliation_period_end   = 2026-06-30
amount_tolerance            = 0.05 MYR
billable_statuses           = COMPLETED,DIVERTED
diverted_billable_charges   = LANDING
free_parking_minutes        = 60
aerobridge_requires         = CONTACT
landing_basis               = per_tonne_mtow
psc_basis                   = per_departing_pax
currency                    = MYR
```

---

## 3. 计费规则（核心算法，逐个实现并写单测）

> 规则必须从 `rate_card.csv` + `assumptions.csv` 读取，**禁止硬编码**。
> 设 `dur_min = departure_datetime - arrival_datetime`（分钟）。

### 3.1 LANDING 起降费
```
quantity = ceil(mtow_tonnes)          # 数据里已是整数，等于原值
rate     = rate_card 里 charge_type=LANDING、condition=ANY、
           且 arrival 日期落在 [effective_from, effective_to] 的那行
amount   = quantity * rate
```
- ⚠️ 日期敏感：`01-01~03-31` 用 **12.00**，`04-01 起` 用 **13.50**

### 3.2 PARKING 停机费
```
excess = dur_min - free_parking_minutes      # free_parking_minutes = 60
if excess <= 0: amount = 0                   # 宽限期内不收钱
else:
    quantity = ceil(excess / 15)
    amount   = quantity * 8.00
```

### 3.3 AEROBRIDGE 廊桥费
```
if stand_type != aerobridge_requires (CONTACT): amount = 0    # 远机位不收
else:
    quantity = ceil(dur_min / 60)
    amount   = quantity * 120.00
```

### 3.4 PSC 旅客服务费
```
if pax_departing == 0: amount = 0           # 货机不收
else:
    rate = DOMESTIC → 11.00 / INTERNATIONAL → 35.00
    amount = pax_departing * rate
```

### 3.5 状态与计费范围（先于上面 4 条判断）
```
status == CANCELLED  → 不产生任何费用
status == DIVERTED   → 只产生 LANDING，其余 3 项全为 0
status == COMPLETED  → 正常按 3.1~3.4 计费
```
- 只有 `billable_statuses`（COMPLETED,DIVERTED）里的状态才计费

---

## 4. 对账规则（治理，逐条实现）

- [ ] **容忍度**：`|expected - actual| <= amount_tolerance(0.05)` → 是舍入，**不标记**
- [ ] **快照日期**：只对账 `reconciliation_period_start ~ end`，用 `arrival_datetime` 判断，**不用今天**
- [ ] **credit note 解决逻辑**：某异常被解决，当且仅当存在 credit note 满足
      `related_invoice_line_id == 该异常的问题行` 且 `金额+币种覆盖差异`。
      空 `related_invoice_line_id` 的 credit note **不解决任何具体异常**。
- [ ] **错记航空公司**：operator 净影响 = 0，但输出两条动作 ——
      ① 退给被错收的航司（负数）② 重开给正确航司（正数）。算 1 条异常。
- [ ] **人类审批节点**：报告中注明「发到航司前需人工复核」，你的输出只是建议，不是自动动作。

---

## 5. 异常类型清单（你要能全部识别）

> 这是「发现差异」的完整考点。每类都附检测逻辑 + 数据里我找到的真实实例，方便你验证引擎对不对。

| # | 异常类型 | 检测逻辑 | 数据里的实例 |
|---|---|---|---|
| 1 | 漏收费 MISSING_CHARGE | movement 该收某项费但 ledger 无此行 | `MOV00050` 漏 LANDING；`MOV00005` 漏 AEROBRIDGE |
| 2 | 错误单价 WRONG_RATE | ledger.unit_rate 不在对应 rate_card 窗口内 | `BL00037/311/314/331/482/680` 出现 10.20、14.40 |
| 3 | 错误数量 WRONG_QUANTITY | ledger.quantity != 期望 quantity | `BL00196`(65 vs 63)；`BL00648`(279 vs 280) |
| 4 | 重复收费 DUPLICATE | 同 movement+charge_type 出现 ≥2 行 | `BL00692~696`（5 条重复 LANDING） |
| 5 | 孤儿账 ORPHAN_CHARGE | ledger.movement_id 在 movements 里不存在 | `BL00700~709` 指向 MOV98739 等假 id |
| 6 | 错记航司 WRONG_AIRLINE | ledger.airline_code != movement.airline_code | `MOV00013`(VN) 起降费记到 KP；`MOV00076`(KP) 记到 SW |
| 7 | 取消航班收费 CANCELLED_CHARGED | status=CANCELLED 却有 ledger 行 | `BL00710~715`（MOV00038/53/89/118/158/228） |
| 8 | 远机位收廊桥 REMOTE_AEROBRIDGE | stand_type=REMOTE 却有 AEROBRIDGE 行 | `BL00716~721` |
| 9 | 备降多收费 DIVERTED_OVERCHARGE | status=DIVERTED 却收了非 LANDING | `BL00723/724/725/726`（停车费/PSC） |
| 10 | （**不要**标记）舍入差异 | 差异 ≤ 0.05 | `2904.02`、`2063.99`、`4211.99` 等一分两分差异 |

**已解决 vs 未解决**：第 4 类的 5 条重复（BL00692~696）已被 credit note（CN-2026-0001~0005）精确冲销，
应标记为「已解决/credited」，不计入未解决敞口。其余全部是 open。

---

## 6. 代码结构（推荐，先搭骨架再填肉）

```
candidate_pack/
├── src/
│   ├── config.py          # 读 assumptions.csv 成一个 dict（单例）
│   ├── load.py            # 读 6 张 CSV → DataFrame / 字典
│   ├── rate_card.py       # 查价：charge_type+condition+日期 → unit_rate
│   ├── billing_rules.py   # 4 种费的「应该收」计算 + 状态判断（核心）
│   ├── reconcile.py       # 主对账循环：逐 movement 比对 ledger，产出异常列表
│   ├── credit_notes.py    # credit note 匹配与「已解决」判定
│   ├── ai_layer.py        # LLM/mock 文案层（只写话，绝不算数）
│   └── report.py          # 输出 exceptions.csv + management summary
├── data/                  # 原始数据（只读）
├── output/                # 生成结果（exceptions.csv, summary.md）
├── tests/                 # 可选：验证引擎正确性
├── .env.example           # OPENAI_API_KEY= 之类
└── README.md
```

### 异常记录的最小字段（输出 CSV 每列）
```
movement_id, invoice_line_id, exception_type,
charge_type, expected_amount, actual_amount,
financial_impact_myr,       # 正=欠运营方，负=该退航司
airline_code, evidence_ref,  # 有 movement 时必带
resolution_status           # OPEN / RESOLVED_BY_CREDIT_NOTE
```

---

## 7. AI 层要求（边界是考点）

**AI 只做 3 件事，且绝不能碰数字：**
1. 把异常类型翻译成大白话（如 `REMOTE_AEROBRIDGE` → 「远机位被误收了廊桥费」）
2. 起草可粘贴的退款/争议说明，**引用 evidence_ref**
3. 生成给管理层的自然语言总结（发现了什么、值多少钱、先处理什么）

**铁律：**
- [ ] 引擎决定异常类型和每个金额；模型**不能改数字、不能改分类**
- [ ] 代码里要能一眼看到这个边界（例如引擎输出 dict → 传给 ai_layer 只做字符串拼接）
- [ ] 没有 API key 就用**明确标注的 mock 函数**返回模板文案，标清楚「真实模型从这里接入」
- [ ] 不用给所有异常手写说明，程序化生成即可；报告/PPT 里放 **6~10 个精选例子**即可

---

## 8. README 要求（让陌生人能复现）

必须包含且可照抄执行：
- [ ] 环境要求（Python 版本）
- [ ] 安装依赖：`pip install -r requirements.txt`（记得写 requirements.txt）
- [ ] 配置：复制 `.env.example` → `.env`，填 key（或注明「无 key 用 mock」）
- [ ] 运行：一条命令跑出报告，如 `python -m src.reconcile`
- [ ] 输出说明：`output/exceptions.csv`、`output/summary.md` 各是什么
- [ ] AI 使用日志

---

## 9. PPT 要求（≤12 页，面向收入保障负责人）

建议结构（照抄 Presentation_Guide）：
1. 标题（问题一句话 + 姓名 + 日期）
2. 问题（两本账对不上，为什么亏钱、为什么有争议风险）
3. 方法（ingest → reconcile → explain → report 流程图）
4. **头条结果**（异常总数 + 净财务影响，这是被记住的一页）
5. 钱在哪（按异常类型/账户拆：漏收 vs 多收）
6. 匹配逻辑（日期费率、推导数量、容忍度、credit note 排除）
7. AI 层（LLM 做什么、**不做什么**，边界）
8. 一个完整案例（movement → billing → 差额 → 金额 → evidence → AI 写的说明）
9. 信任与治理（无硬编码、数字可追溯、证据挂接、人工复核）
10. 局限与假设（诚实）
11. 下一步（如果还有第二周）
12. 收尾（一句话核心结论）

**红线：** 每页数字必须来自自己引擎；不要吹 AI 做不到的事；不要为了好看堆工具图。

---

## 10. 逐日开发 checklist（照着勾）

### Day 1 — 读数据 + 写清单
- [ ] 通读 `Case_Study_Brief.md` + `DATA_DICTIONARY.md` + 本手册
- [ ] 用 pandas 加载 6 张表，`print` 前几行 + `describe()` + 检查空值
- [ ] 手写：你能看到的差异类型 + 每类至少 1 个实例（对照第 5 节）
- [ ] 确定技术栈（Python + pandas，要不要 jupyter 探索）

### Day 2~3 — 确定性引擎
- [ ] `config.py` 读 assumptions
- [ ] `rate_card.py` 查价函数（含日期窗口）
- [ ] `billing_rules.py` 4 种费计算 + 状态判断
- [ ] `reconcile.py` 主循环：遍历所有 movement 算 expected，合并 ledger 算 actual
- [ ] 先跑出**漏收费 + 错误单价 + 错误数量**三类
- [ ] 再补**重复、孤儿账、错记航司、取消收费、远机位廊桥、备降多收费**
- [ ] 实现容忍度过滤（0.05）
- [ ] 产出第一版 `exceptions.csv`

### Day 4 — AI 层
- [ ] `ai_layer.py`：mock 函数 + 清晰标注真实模型接入点
- [ ] 异常类型 → 大白话映射
- [ ] 生成带 evidence_ref 的退款说明模板
- [ ] 生成 management summary
- [ ] 锁死边界（引擎算数，模型只写字）

### Day 5 — 硬化 + 文档
- [ ] credit note 解决逻辑 + resolution_status
- [ ] 快照日期/期间过滤
- [ ] 错记航司的 refund+rebill 双动作输出
- [ ] 边界情况全测一遍（空 movement、pax=0、REMOTE、DIVERTED、CANCELLED）
- [ ] 写 README + requirements.txt + .env.example + AI 使用日志

### Day 6 — PPT
- [ ] 用引擎跑出的真实数字填每一页
- [ ] 选 1 个完整案例做 worked example（第 8 页）
- [ ] 排练「给外行经理讲故事」

### Day 7 — 缓冲 + 终检
- [ ] 最后检查：grep 代码里有没有硬编码的 12.00 / 13.50 / 60 / 0.05 / 日期
- [ ] 从零跑一遍 README 命令，确认能复现
- [ ] 对照第 11 节自检

---

## 11. 提交前自检清单（对应 5 个评分维度）

**① 对账正确性**
- [ ] 真差异找全了吗？（对照第 5 节 9 类）
- [ ] 有假警报吗？（0.05 容忍度内的必须没报）
- [ ] credit note 精确匹配的 5 条重复已标「已解决」？

**② 数据与治理纪律**
- [ ] 代码里没有任何硬编码的业务数字/日期/阈值？
- [ ] 每个报告数字都能追溯到引擎某一行输出？
- [ ] 快照日期/期间/容忍度/宽限/可计费状态都用对了？

**③ AI 集成质量**
- [ ] 模型从不设置或修改数字/分类？
- [ ] 每条说明挂了 evidence_ref？
- [ ] 边界在代码里一眼可见？

**④ 工程素养**
- [ ] 代码可读、有注释、结构清晰？
- [ ] README 真能让人从零跑通？

**⑤ 沟通**
- [ ] PPT 讲得清「发现了什么、值多少钱、能不能信」？
- [ ] 数字和引擎输出一致？

---

## 12. 坑速查（开发时最容易翻车的地方）

1. **日期敏感费率**：3 月 vs 4 月起降费不同，别用一个固定价。
2. **0.05 容忍度是「反考」**：一堆 0.01/0.02 的差异必须忽略，误报就丢分。
3. **停车先减 60 分钟**：很多人直接 ceil(dur/15)，忘了宽限期。
4. **REMOTE 不收廊桥**：别看到 AEROBRIDGE 就照算。
5. **DIVERTED 只收起降费**：停车/廊桥/旅客费全为 0。
6. **CANCELLED 一分不收**：哪怕 ledger 有行也要标记出来。
7. **货机 pax=0 不收 PSC**：别对 0 人乘以费率。
8. **credit note 空 line_id 不解决异常**：GOODWILL/MANUAL_ADJ 不算数。
9. **错记航司净影响=0 但要有退款+重开两条动作**。
10. **孤儿账**（movement_id 不存在）本身就是要上报的发现。

---

*这份手册随项目更新。开发中每确认一条规则，就回来勾掉一项。*
