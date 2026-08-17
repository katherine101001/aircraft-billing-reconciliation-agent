# 飞机计费与起降对账系统（中文版）

一个**确定性对账引擎**：比对机场起降日志（`movements.csv`）与财务开单（`billing_ledger.csv`），
找出每一处差异、量化财务影响（MYR）、挂接证据引用，并由 AI 层把结果写成可交付的文字。

> 本系统只对账 `assumptions.csv` 中声明的快照期间（2026-01-01 ~ 2026-06-30）。
> 所有业务输入（费率、阈值、日期、计费规则）均从数据文件运行时读取，**不硬编码**。

---

## 目录结构

```
candidate_pack/
├── data/                  # 原始数据（只读，6 张 CSV）
├── src/
│   ├── config.py          # 读 assumptions.csv（对账规则）
│   ├── load.py            # 读 6 张表
│   ├── rate_card.py       # 按 charge_type + condition + 日期查单价
│   ├── billing_rules.py   # 计算「应该收取」的费用（核心算法）
│   ├── reconcile.py       # 对账主循环 + credit note 解决
│   ├── ai_layer.py        # AI 层（只写文字，当前为 mock）
│   ├── report.py          # 输出 exceptions.csv + summary.md
│   └── main.py            # 入口
├── output/                # 生成结果（运行后产生）
├── tests/                 # 88 个测试用例（python -m tests.run_all）
├── REQUIREMENTS_TRACEABILITY.md  # 需求 → 代码位置对照清单
├── requirements.txt
├── .env.example
└── README.md
```

---

## 环境要求

- Python 3.10+
- pandas >= 2.0

## 快速开始

### 前置条件

- **数据**：仓库自带 `data/` 文件夹（6 张 CSV），运行前确认它在项目根目录下。
- **Python**：3.10 及以上（本项目在 3.10.11 上验证）。
- **LLM API key（可选）**：不配置也能跑，AI 层会退化为 mock 文案（边界不变）。

### 复现步骤（确切命令）

```bash
# 0. 获取代码
git clone <你的仓库地址>        # 或解压 zip 到任意目录
cd candidate_pack

# 1. 安装依赖（只需 pandas）
pip install -r requirements.txt

# 2.（可选）配置 LLM API key；不配也能跑
#    cp .env.example .env        # 然后编辑 .env 填入 OPENAI_API_KEY

# 3. 运行对账引擎
python -m src.main
```

运行成功后，控制台会打印管理总结，并生成两个文件：

| 文件 | 内容 |
|---|---|
| `output/exceptions.csv` | 全部异常，每行含类型、期望值、实际值、财务影响、证据引用、解决状态 |
| `output/summary.md` | AI 生成的管理层总结 + 代表性案例说明 |

### 预期输出（复现校验）

用同一份数据运行，结果是**确定性的**，应与下表一致（可作为「是否跑对」的校验锚点）：

| 指标 | 值 |
|---|---|
| 异常总数 | 92 条 |
| 净财务影响 | -24,779.10 MYR |
| 漏收/少收（应补收） | 58,824.70 MYR |
| 多收/错收（应退航司） | 83,603.80 MYR |
| 已被 credit note 解决 | 5 条 |

若跑出的数字与此不同，请检查是否替换了 `data/` 下的数据文件，或改动了 `rate_card.csv` / `assumptions.csv`。

---

## 测试

```bash
# 跑全部测试（88 个用例）
python -m tests.run_all

# 看代码覆盖率（需先 pip install -r requirements-dev.txt）
python -m coverage run -m tests.run_all
python -m coverage report -m
```

共 **88 个用例**，覆盖计费规则、查价、对账判定、credit note 解决、AI 层、报告输出、配置/加载与端到端，全部应通过。
测试是「正确性」的可复现证据：任何改坏逻辑的改动都会让测试失配。

**覆盖率目标：100%**（`src/` 全部 271 条语句、84 个分支均被执行到）。
除 `src/main.py` 的 `if __name__ == "__main__"` 入口（由子进程测试触发）外，无任何「未覆盖」豁免。

---

## 需求 → 代码对照

见 `REQUIREMENTS_TRACEABILITY.md`：题目每条要求 → 具体代码位置，方便核对。

---

## 异常类型

引擎识别 11 类异常（见 `src/reconcile.py` 顶部注释）：

`MISSING_CHARGE`（漏收）、`WRONG_RATE`（错误单价）、`WRONG_QUANTITY`（错误数量）、
`WRONG_AMOUNT`（金额错）、`DUPLICATE`（重复开单）、`ORPHAN_CHARGE`（无对应起降）、
`WRONG_AIRLINE`（错记航司，净影响 0）、`CANCELLED_CHARGED`（取消航班收费）、
`REMOTE_AEROBRIDGE`（远机位廊桥）、`DIVERTED_OVERCHARGE`（备降多收费）、
`PSC_ON_CARGO`（货机旅客费）。

财务影响符号：**正数 = 钱应归运营方（漏收）；负数 = 钱应退航司（多收）**。
差异 ≤ `amount_tolerance`(0.05 MYR) 视为舍入，不标记。

---

## AI 层与边界

对账引擎（`reconcile.py`）决定异常类型和每一个金额；AI 层（`ai_layer.py`）只负责：
1. 把异常类型翻译成大白话；
2. 起草带证据号的退款/争议说明；
3. 生成管理总结。

**模型绝不设置或修改任何数字或分类。** 当前为 mock 实现，真实 LLM 的接入点在
`src/ai_layer.py` 底部以 `TODO` 标注，替换 `explain()` 与 `summarize()` 即可，边界不变。

---

## 治理与复现说明

- 报告中每个数字都来自 `src/reconcile.py` 的一次运行，未手工填入。
- 只对账 `reconciliation_period_start/end`，使用 `data_snapshot_date`，不使用今天日期。
- credit note 仅当其 `related_invoice_line_id` 精确匹配问题行、且金额与币种覆盖差异时，才将异常标记为 `RESOLVED_BY_CREDIT_NOTE`。
- 报告是给人工复核的建议，发往航司前需人工签字确认。

## AI 使用日志

见 `AI_USAGE_LOG.md`。
