# PPT 制作清单（照抄即用）

> 🇨🇳 中文版（Chinese version）｜英文版见 [`PPT_PLAN.md`](PPT_PLAN.md)。

> 这份文件 = 你 12 页 PPT 的「逐页剧本 + 数字抄写表」。
> 每个数字都已从**引擎真实输出**核对过（来源见每页右侧）。你只管照抄，不用再自己算。

---

## 铁律（先读这 3 条，违反就扣分）

1. **PPT 上每一个数字都必须来自引擎输出**（`output/exceptions.csv` + `output/summary.md`），禁止手打/四舍五入/凭感觉。
2. **对账期间写 2026-01-01 ~ 2026-06-30**（快照期间，来自 `assumptions.csv`），**不能用「今天」的日期**。
3. **别吹 AI**：AI 只写文字、不碰数字。这一条题目反复强调，说错直接扣「AI 集成质量」的分。

---

## 数字速查表（全 PPT 的所有数字，一页抄全）

| 指标 | 数字 | 来源文件 |
|---|---|---|
| 异常总数 | **92 条** | `output/summary.md` |
| 净财务影响 | **-24,779.10 MYR**（负数=净多收，应退航司） | 同上 |
| 漏收/少收（应补收，leakage） | **+58,824.70 MYR** | 同上 |
| 多收/错收（应退航司，overbilling） | **-83,603.80 MYR** | 同上 |
| 已被 credit note 解决 | **5 条** | 同上 |
| 仍未解决敞口 | **87 条** | 同上 |

### 按异常类型分布（净额）

| 类型 | 中文含义 | 条数 | 净 MYR | 方向 |
|---|---|---|---|---|
| MISSING_CHARGE | 漏收（该收没开单） | 20 | +42,821.00 | 漏收 |
| WRONG_RATE | 单价错 | 16 | +7,811.40 | 漏收 |
| WRONG_AIRLINE | 开给错航司 | 7 | 0.00 | 中性（退款+重开） |
| WRONG_QUANTITY | 数量错 | 14 | -411.50 | 多收 |
| REMOTE_AEROBRIDGE | 远机位收廊桥费 | 6 | -6,600.00 | 多收 |
| DIVERTED_OVERCHARGE | 备降多收 | 5 | -6,961.00 | 多收 |
| CANCELLED_CHARGED | 取消航班仍收费 | 6 | -13,446.00 | 多收 |
| DUPLICATE | 重复开单 | 8 | -16,332.00 | 多收 |
| ORPHAN_CHARGE | 无对应起降的孤儿单 | 10 | -31,661.00 | 多收 |

> ⚠️ **重要提醒（考官可能加总）**：上面「漏收 58,824.70 / 多收 83,603.80」是**逐条正/负金额求和**，而「按类型表」是**每类净额**，两者**不会逐项加总相等**——因为 WRONG_QUANTITY 里既有少开（正）也有多开（负），净额只显示 -411.50。若被问到，你回答：「总数是逐条求和，类型表是净额，二者口径不同，都是引擎同一份输出算的」。

---

## 逐页清单（12 页）

### 第 1 页｜标题 Title

- **建议标题（英文）**：`Aircraft Billing & Movement Reconciliation`
- **副标题**：`Finding every gap between the movement log and the billing ledger — and pricing it`
- **署名 + 日期**：你的名字；日期可写实际汇报日（标题页的日期是「汇报日」，不是对账日，这条不违反红线）。
- **口播（中文）**：一句话说清楚——「我做的系统，把机场的『实际起降记录』和『财务开单』两张表对起来，找出所有不一致，并算出每一处值多少钱。」

---

### 第 2 页｜问题 The problem

- **标题**：`Two records that should agree — but don't`
- **正文要点（英文，照抄）**：
  - Operations logs every aircraft movement; Finance keys in charges **by hand**.
  - The two should match exactly. They don't.
  - Missed or wrong charges → **revenue leakage** + **disputes airlines can't defend against**.
- **可放一个具体对比**（用第 8 页案例）：
  - 起降记录说：航班 KP8359，**298 名离港旅客**（国际）
  - 账单里：**没有 PSC 这一行** → 白白漏收 **10,430.00 MYR**
- **口播**：现在是手工对账，慢、容易错、出了问题拿不出证据。这就是「营收保障团队」每天头疼的事。

---

### 第 3 页｜方法 Approach

- **标题**：`How it works: four steps`
- **画一个简单流程（别写文字墙）**：
  ```
  Ingest  →  Reconcile  →  Explain  →  Report
  读 6 表    算差异        AI 写文字    输出 CSV+总结
  ```
- **要点**：
  - **Ingest**：读 6 张表（起降、账单、费率卡、航司、credit note、假设）
  - **Reconcile**：确定性引擎逐条比对，算出「应该收 vs 实际收」
  - **Explain**：AI 把异常翻译成商业语言 + 起草退款说明
  - **Report**：输出 `exceptions.csv` + `summary.md`
- **口播**：重点是——**算钱的是确定性引擎，不是 AI**。AI 只负责把结果写成别人看得懂的话。

---

### 第 4 页｜核心结果 Headline result ⭐（最该记住的一页）

- **标题**：`92 discrepancies, -24,779.10 MYR net`
- **放 3 个大数字（越大越好）**：
  - **92** 处异常
  - **-24,779.10 MYR** 净财务影响
  - **5** 条已被 credit note 解决（87 条待处理）
- **补充一行**：漏收 +58,824.70 / 多收 -83,603.80
- **口播**：整个系统跑下来，找到 92 处不一致，净影响是**该退给航司 24,779.10 MYR**（负号 = 多收了）。

---

### 第 5 页｜钱在哪 Where the money is

- **标题**：`Leakage vs overbilling`
- **左栏 = 漏收（leakage，该收没收）**：
  - 合计 **+58,824.70 MYR**
  - 大头：漏收 MISSING_CHARGE **+42,821.00**、单价错 WRONG_RATE **+7,811.40**
- **右栏 = 多收（overbilling，该退航司）**：
  - 合计 **-83,603.80 MYR**
  - 大头：孤儿单 ORPHAN_CHARGE **-31,661.00**、重复单 DUPLICATE **-16,332.00**、取消仍收 CANCELLED_CHARGED **-13,446.00**
- **一条中性**：错记航司 WRONG_AIRLINE 7 条、净 **0.00**，但要「退款 + 重开」两件事都做。
- **口播**：多收的比漏收的还多，所以净结果是「退钱」。其中最大的一笔是「孤儿单」——账单里引用了根本不存在的起降记录。

---

### 第 6 页｜怎么配对的 How the matching works

- **标题**：`The rules the engine applies`
- **要点（英文照抄 + 中文自记）**：
  - **Date-aware rates**：LANDING 单价 03-31 前 **12.00**，04-01 起 **13.50**（从 `rate_card.csv` 读，不硬编码）
  - **Derived quantities**：PARKING 扣 **60 分钟宽限**；AEROBRIDGE 只有 **CONTACT 机位**才收；PSC 按离港旅客 ×（国内 **11** / 国际 **35**）
  - **Tolerance**：差异 ≤ **0.05** 算舍入，**不报**
  - **Credit notes**：只有 `related_invoice_line_id` 精确匹配 + 金额覆盖才算解决
- **口播**：这页证明我不是「碰运气对上」，而是每条计费规则都吃透了——包括最容易错的「备降只收起降费」「远机位不收廊桥」。

---

### 第 7 页｜AI 层 The AI layer（关键：说清边界）

- **标题**：`The engine sets the numbers. The model writes the words.`
- **AI 做什么**：
  - 把异常类型翻译成大白话（如 `MISSING_CHARGE` → 「该收的没开单」）
  - 起草一封财务能直接发给航司的退款/争议说明（引用证据号）
  - 写管理层总结
- **AI 不做什么（加粗强调）**：
  - ❌ **不决定异常类型**、❌ **不改任何数字**、❌ **不算财务影响**
- **口播**：这条边界是硬性的——引擎负责「对不对」，AI 只负责「好不好读」。哪怕 AI 没接（现在是 mock），数字也完全正确。

---

### 第 8 页｜一个真实案例 A worked example ⭐

- **标题**：`One exception, end to end`
- **用这一条（已核实）**：

| 字段 | 值 | 来源 |
|---|---|---|
| 航班 | KP8359（Kinabalu Pacific，A350） | `movements.csv` |
| 起降编号 | MOV00069 | 同上 |
| 状态 / 机位 | COMPLETED / CONTACT | 同上 |
| 离港旅客 | **298 人**，国际航线 | 同上 |
| 该收 PSC | 298 × 35.00 = **10,430.00 MYR** | 费率卡 |
| 账单里实际 | **无 PSC 行**（0.00） | `billing_ledger.csv` |
| 差距 | **+10,430.00 MYR**（漏收） | `exceptions.csv` 第 2 行 |
| 证据号 | **EVD-20260304-0069** | 同上 |
| 判定 | **MISSING_CHARGE**，OPEN | 同上 |

- **附 AI 草拟的英文说明（可直接贴进 PPT）**：
  > Movement MOV00069 (flight KP8359) carried 298 departing international passengers on 2026-03-04, but no Passenger Service Charge was billed. Expected PSC is MYR 10,430.00 (298 × 35.00). No invoice line exists. We recommend raising a supplementary invoice for MYR 10,430.00. Evidence: EVD-20260304-0069.
- **口播**：这就是「证据链」——从航班的起降记录，到费率卡，到账单缺了这一行，再到证据号，整条链可追溯，退款/补收都能站得住。

---

### 第 9 页｜可信与治理 Trust & governance

- **标题**：`Why you can trust the output`
- **要点**：
  - **零硬编码**：费率、阈值、日期、规则全部运行时从 `rate_card.csv` / `assumptions.csv` 读
  - **每个数字可追溯**：报告里每个数字都对应 `exceptions.csv` 里具体某一行
  - **每条异常挂证据号**（有对应起降的）
  - **人工签字**：报告是「建议」，发往航司前必须人工复核
- **口播**：钱的事不能全自动。我的系统只做「找出问题 + 算出金额」，最后发不发给航司，**由人签字决定**。

---

### 第 10 页｜局限与假设 Limitations & assumptions

- **标题**：`What I assumed, and where I'd be careful`
- **要点（诚实分在这页，别吹）**：
  - AI 层目前是 **mock**（写死的模板文案），边界已留好、真模型可直接替换
  - 只对账**快照期间 2026-01-01 ~ 2026-06-30**，期间外的数据跳过
  - 数据若与 `DATA_DICTIONARY.md` 不一致，按字典为准；有歧义时在 `assumptions.csv` 里写明假设
  - 覆盖范围 = 6 张 CSV；没有做实时监控/dashboard（属加分项，非必需）
- **口播**：题目明确说「诚实的局部解 > 吹过头的完整解」。我把没做的和假设都摆出来，这是加分项。

---

### 第 11 页｜下一步 What I'd do next

- **标题**：`Week two, I would…`
- **要点**：
  - **接真 LLM**：把 mock 换成真实模型，让退款说明自动生成（边界不变）
  - **评估 harness**：已有 88 个测试 + 100% 覆盖，再补「黄金标准异常集」做回归
  - **Per-airline dispute pack**：把每家航司的未解决异常打包成一个导出
  - **简易 dashboard**：一个 HTML 页按航司/类型浏览异常
- **口播**：核心已经稳了，接下来是「加固 + 易用」，不是「重写」。

---

### 第 12 页｜收尾 Close

- **标题（一句话 takeaway，可照抄）**：
  > `The movement log and the ledger can now be reconciled in minutes — 92 discrepancies found, every one priced and evidenced.`
- **口播**：给我一个起降记录和一个账单，我还你一份「每条都算好钱、附好证据」的差异清单。

---

## 提交前核对清单（做完 PPT 逐条打钩）

- [ ] 92、-24,779.10、58,824.70、83,603.80、5 —— 这 5 个数字和 `output/summary.md` 一字不差
- [ ] 类型表里 9 类的条数/净额，和 `output/summary.md` 逐项一致
- [ ] 第 8 页案例：MOV00069 / 298 人 / 10,430.00 / EVD-20260304-0069，和 `exceptions.csv` 第 2 行一致
- [ ] 全片没有出现「今天」的日期，对账期间统一写 2026-01-01 ~ 2026-06-30
- [ ] 任何地方都没出现「AI 算出了某个数字」的说法（AI 只写文字）
- [ ] 页数 ≤ 12
- [ ] 导出为 PDF 或 PPTX

---

## 扣分红线（`Presentation_Guide.md` 原文对应的坑）

| 会扣分的 | 对应哪页 | 怎么避免 |
|---|---|---|
| 硬编码 / 无法解释的数字 | 第 4、5 页 | 每个数字标来源文件 |
| 讲工具比讲结果还多 | 第 3 页 | 图要简单，一句话带过 |
| 吹 AI 能做它做不到的事 | 第 7 页 | 明确「AI 不碰数字」 |
| 藏数字来源 | 全片 | 每页右下角标「来源：output/xxx」 |
| 漂亮但没干货 | 全片 | 每页都有「口播」里的一句话可落地 |
