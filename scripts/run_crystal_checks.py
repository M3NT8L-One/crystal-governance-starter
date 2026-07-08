#!/usr/bin/env python3
"""Run starter Crystal governance checks."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(label: str, cmd: list[object]) -> None:
    print(f"+ {label}")
    subprocess.check_call([str(part) for part in cmd])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="examples/sample-crystal-home", help="Crystal state root to inspect")
    ap.add_argument("--out", default="reports/crystal-governance", help="Directory for JSON/Markdown reports")
    ap.add_argument("--include-absolute-paths", action="store_true", help="Include absolute paths in reports/wake messages. Defaults to redacted for safer sharing.")
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    path_args = ["--include-absolute-paths"] if args.include_absolute_paths else []
    run("crystal_governance_audit", [py, here / "crystal_governance_audit.py", "--root", args.root, "--out", out, *path_args])
    run("crystal_triage_gate", [py, here / "crystal_triage_gate.py", "--report-dir", out, *path_args])


if __name__ == "__main__":
    main()
