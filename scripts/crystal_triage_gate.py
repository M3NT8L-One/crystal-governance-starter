#!/usr/bin/env python3
"""Quiet wake gate for Crystal governance audits."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report-dir", default="reports/crystal-governance")
    ap.add_argument("--medium-threshold", type=int, default=1)
    ap.add_argument("--include-absolute-paths", action="store_true", help="Print absolute report path in wake message. Defaults to redacted for safer sharing.")
    args = ap.parse_args()
    report_dir = Path(args.report_dir).expanduser().resolve()
    report = load(report_dir / "crystal-governance-audit.json")
    if not report:
        display_dir = str(report_dir) if args.include_absolute_paths else "<report-dir>"
        print(f"WAKE: Crystal governance report missing in {display_dir}")
        return
    high = int(report.get("high_count", 0))
    medium = int(report.get("medium_count", 0))
    findings = int(report.get("finding_count", 0))
    if high > 0 or medium >= args.medium_threshold:
        display_dir = str(report_dir) if args.include_absolute_paths else "<report-dir>"
        print(f"WAKE: Crystal governance attention needed: high={high} medium={medium} total_findings={findings} report_dir={display_dir}")


if __name__ == "__main__":
    main()
