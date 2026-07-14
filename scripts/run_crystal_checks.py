#!/usr/bin/env python3
"""Run starter Crystal governance checks."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(label: str, cmd: list[object], *, allowed_codes: tuple[int, ...] = (0,)) -> int:
    print(f"+ {label}")
    result = subprocess.run([str(part) for part in cmd], check=False)
    if result.returncode not in allowed_codes:
        raise subprocess.CalledProcessError(result.returncode, result.args)
    return int(result.returncode)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="examples/sample-crystal-home", help="Crystal state root to inspect")
    ap.add_argument("--profile", default="default", help="Profile to health-check")
    ap.add_argument("--source-root", help="Optional deployed source tree to health-check")
    ap.add_argument("--out", default="reports/crystal-governance", help="Directory for JSON/Markdown reports")
    ap.add_argument("--include-absolute-paths", action="store_true", help="Include absolute paths in reports/wake messages. Defaults to redacted for safer sharing.")
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    path_args = ["--include-absolute-paths"] if args.include_absolute_paths else []
    run("crystal_governance_audit", [py, here / "crystal_governance_audit.py", "--root", args.root, "--out", out, *path_args])
    health_args: list[object] = [
        py,
        here / "crystal_health_check.py",
        "--root",
        args.root,
        "--profile",
        args.profile,
        "--out",
        out / "crystal-health.json",
    ]
    if args.source_root:
        health_args.extend(["--source-root", args.source_root])
    health_code = run("crystal_health_check", health_args, allowed_codes=(0, 1))
    run("crystal_triage_gate", [py, here / "crystal_triage_gate.py", "--report-dir", out, *path_args])
    if health_code:
        raise SystemExit(health_code)


if __name__ == "__main__":
    main()
