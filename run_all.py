"""Rebuild every deliverable from scratch, in order.

    .venv/Scripts/python.exe run_all.py

Roughly 12 minutes, dominated by the benchmark. Use --fast to skip the benchmark and
regenerate only the figures and pages from existing CSVs.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
if not Path(PY).exists():  # non-Windows or system interpreter
    PY = sys.executable

STEPS = [
    ("Train AI model (Deliverable 1)", "src/ai_model.py", False),
    ("Benchmark QAOA vs classical", "src/benchmark.py", True),
    ("Render figures", "src/figures.py", False),
    ("Write DELIVERABLE_4.md", "src/make_deliverable4.py", False),
    ("Write DELIVERABLE_4.html (the one-pager)", "src/make_onepager.py", False),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="skip the benchmark step")
    args = ap.parse_args()

    for i, (label, script, slow) in enumerate(STEPS, 1):
        if slow and args.fast:
            print(f"[{i}/{len(STEPS)}] {label} — SKIPPED (--fast)")
            continue
        print(f"[{i}/{len(STEPS)}] {label} …", flush=True)
        t0 = time.perf_counter()
        r = subprocess.run([PY, str(ROOT / script)], cwd=ROOT)
        if r.returncode != 0:
            print(f"    FAILED ({script}) with exit code {r.returncode}")
            return r.returncode
        print(f"    done in {time.perf_counter() - t0:.1f}s")

    print("\nAll deliverables rebuilt. Launch the demo with:")
    print("    .venv/Scripts/streamlit run app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
