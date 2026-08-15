"""一键运行所有测试。

用法（在项目根目录）：
    python -m tests.run_all

成功打印 PASS，失败打印 FAIL 并返回退出码 1（供 CI/考官核对）。
"""
from __future__ import annotations

import importlib
import sys

# Windows 控制台默认 cp1252，强制 UTF-8 以免打印中文/货币符号报错
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODULES = [
    "tests.test_config",
    "tests.test_load",
    "tests.test_rate_card",
    "tests.test_billing_rules",
    "tests.test_reconcile",
    "tests.test_credit_notes",
    "tests.test_ai_layer",
    "tests.test_report",
    "tests.test_main",
    "tests.test_end_to_end",
]


def main() -> int:
    passed = 0
    failed = 0

    for modname in MODULES:
        mod = importlib.import_module(modname)
        tests = [(n, f) for n, f in sorted(vars(mod).items())
                 if n.startswith("test_") and callable(f)]
        for name, fn in tests:
            label = f"{modname}.{name}"
            try:
                fn()
                print(f"  PASS  {label}")
                passed += 1
            except AssertionError as e:
                print(f"  FAIL  {label}  ->  {e}")
                failed += 1
            except Exception as e:  # noqa: BLE001 —— 非断言异常也记为失败
                print(f"  ERROR {label}  ->  {type(e).__name__}: {e}")
                failed += 1

    print(f"\n===== 共 {passed} 通过，{failed} 失败 =====")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
