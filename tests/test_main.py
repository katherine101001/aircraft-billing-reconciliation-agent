"""Boundary tests for main.py: the full pipeline (in-process) + the entry script (subprocess).

The subprocess test really runs `python -m src.main` once to prove the entry point works
(corresponding to the `if __name__ == "__main__"` branch, which is itself marked
`# pragma: no cover`).
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
    assert "Reconciliation summary" in out
    assert "net financial impact" in out


def test_main_entry_point_as_script():
    r = subprocess.run(
        [sys.executable, "-m", "src.main"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    assert r.returncode == 0, f"exit code {r.returncode}\nstdout={r.stdout}\nstderr={r.stderr}"
    assert "net financial impact" in r.stdout
