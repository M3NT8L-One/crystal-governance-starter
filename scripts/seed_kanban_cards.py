#!/usr/bin/env python3
"""Convert Crystal governance findings into generic Kanban-card JSONL drafts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SEVERITY_ORDER = {"advisory": 0, "medium": 1, "high": 2}
Finding = dict[str, Any]


def load_findings(path: Path) -> list[Finding]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("findings", []))


def should_include(item: Finding, min_severity: str) -> bool:
    severity = str(item.get("severity", "advisory"))
    return SEVERITY_ORDER.get(severity, 0) >= SEVERITY_ORDER[min_severity]


def build_card(item: Finding, report_dir: Path, include_absolute_paths: bool = False) -> dict[str, Any]:
    severity = str(item.get("severity", "advisory"))
    risk = "high" if severity == "high" else "medium" if severity == "medium" else "low"
    source_report_dir = str(report_dir) if include_absolute_paths else "<report-dir>"
    return {
        "title": f"Crystal governance: {item.get('type')} in {item.get('path')}",
        "risk": risk,
        "target_surface": item.get("surface"),
        "source_report_dir": source_report_dir,
        "body": {
            "finding": item,
            "acceptance": [
                "Confirm the finding or mark it false positive with reason.",
                "Apply the smallest scoped fix or write a proposal.",
                "Rerun the Crystal governance audit.",
                "Attach evidence before closing.",
            ],
            "reviewer_required": risk in {"high", "medium"},
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report-dir", default="reports/crystal-governance")
    ap.add_argument("--out", default="reports/crystal-governance/kanban-card-drafts.jsonl")
    ap.add_argument("--min-severity", choices=["advisory", "medium", "high"], default="medium")
    ap.add_argument("--include-absolute-paths", action="store_true", help="Write absolute report paths into card drafts. Defaults to redacted for safer sharing.")
    args = ap.parse_args()
    report_dir = Path(args.report_dir).expanduser().resolve()
    findings = load_findings(report_dir / "crystal-governance-audit.json")
    cards = [
        build_card(item, report_dir, args.include_absolute_paths)
        for item in findings
        if should_include(item, args.min_severity)
    ]
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(card, sort_keys=True) + "\n" for card in cards), encoding="utf-8")
    out_display = str(out) if args.include_absolute_paths else "<out>"
    print(json.dumps({"cards_written": len(cards), "min_severity": args.min_severity, "out": out_display}, sort_keys=True))


if __name__ == "__main__":
    main()
