"""入口：加载数据 → 对账 → 解决 credit note → 输出报告。

运行：  python src/main.py
"""
from __future__ import annotations

import sys

# Windows 控制台默认 cp1252，无法打印中文/货币符号；强制用 UTF-8
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .config import load_assumptions
from .load import (
    load_billing_ledger,
    load_credit_notes,
    load_movements,
    load_rate_card,
)
from .reconcile import reconcile, resolve_credit_notes
from .report import write_report


def main() -> None:
    # 1) 加载规则与数据（业务输入全部来自文件，不硬编码）
    assumptions = load_assumptions()
    rate_df = load_rate_card()
    movements_df = load_movements()
    ledger_df = load_billing_ledger()
    credit_notes = load_credit_notes()

    movements = movements_df.to_dict("records")
    ledger = ledger_df.to_dict("records")

    # 2) 确定性对账
    exceptions = reconcile(movements, ledger, rate_df, assumptions)

    # 3) credit note 解决判定
    exceptions = resolve_credit_notes(exceptions, credit_notes)

    # 4) 输出报告（CSV + 管理总结）
    write_report(exceptions, assumptions)


if __name__ == "__main__":
    main()
