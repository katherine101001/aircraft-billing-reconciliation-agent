"""Run all tests in one go.

Usage (from the project root):
    python -m tests.run_all

Prints PASS on success; prints FAIL and returns exit code 1 on failure (for CI / reviewer).
"""
from __future__ import annotations

import importlib
import sys

# Windows consoles default to cp1252; force UTF-8 so non-ASCII output doesn't error
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
            except Exception as e:  # noqa: BLE001 — non-assertion errors also count as failures
                print(f"  ERROR {label}  ->  {type(e).__name__}: {e}")
                failed += 1

    print(f"\n===== {passed} passed, {failed} failed =====")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
