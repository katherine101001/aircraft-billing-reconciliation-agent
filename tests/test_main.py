"""main.py 的边界测试：完整流水线（进程内）+ 入口脚本（子进程）。

子进程测试真正以 `python -m src.main` 方式跑一次，证明入口可用（对应源码里的
`if __name__ == "__main__"` 分支，该分支本身用 `# pragma: no cover` 标注）。
"""
from __future__ import annotations

import contextlib
import io
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_main_runs_end_to_end_in_process():
    from src.main import main
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main()
    out = buf.getvalue()
    assert "对账总结" in out
    assert "净财务影响" in out


def test_main_entry_point_as_script():
    r = subprocess.run(
        [sys.executable, "-m", "src.main"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    assert r.returncode == 0, f"退出码 {r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"
    assert "净财务影响" in r.stdout
