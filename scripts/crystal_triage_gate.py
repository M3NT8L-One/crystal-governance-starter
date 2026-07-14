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
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"_load_error": exc.__class__.__name__}
    if not isinstance(payload, dict):
        return {"_load_error": "InvalidReportType"}
    return payload


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
    if report.get("_load_error"):
        display_dir = str(report_dir) if args.include_absolute_paths else "<report-dir>"
        print(
            "WAKE: Crystal governance report unreadable: "
            f"error={report['_load_error']} report_dir={display_dir}"
        )
        return
    health = load(report_dir / "crystal-health.json")
    high = int(report.get("high_count", 0))
    medium = int(report.get("medium_count", 0))
    findings = int(report.get("finding_count", 0))
    reasons: list[str] = []
    if high > 0 or medium >= args.medium_threshold:
        reasons.append(f"audit high={high} medium={medium} total_findings={findings}")
    if not health:
        reasons.append("health report missing")
    elif health.get("_load_error"):
        reasons.append(f"health report unreadable error={health['_load_error']}")
    else:
        status = str(health.get("status") or "UNKNOWN")
        if status != "HEALTHY":
            degradations = ",".join(str(item) for item in health.get("degradations", [])) or "none"
            critical = ",".join(str(item) for item in health.get("critical_failures", [])) or "none"
            reasons.append(
                f"health status={status} degradations={degradations} critical_failures={critical}"
            )
    if reasons:
        display_dir = str(report_dir) if args.include_absolute_paths else "<report-dir>"
        print(
            "WAKE: Crystal governance attention needed: "
            + "; ".join(reasons)
            + f" report_dir={display_dir}"
        )


if __name__ == "__main__":
    main()
