"""Hermes companion plugin for Crystal governance starter checks.

This plugin is intentionally read-only. It registers an operator CLI command
that runs the starter repo's audit scripts against a Crystal state root.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


PLUGIN_NAME = "crystal-governance"
SAMPLE_ROOT = Path("examples/sample-crystal-home")
DEFAULT_OUT = Path("reports/crystal-governance")


def register(ctx: Any) -> None:
    ctx.register_cli_command(
        name="crystal-governance",
        help="Inspect Crystal living-context governance state",
        setup_fn=_setup_cli,
        handler_fn=_handle_cli,
        description=(
            "Read-only Crystal governance companion. Runs sample demos, "
            "audits Profile Crystal/session docs/sync queues, drafts review "
            "cards, and prints a quiet triage wake summary."
        ),
    )


def _setup_cli(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="command")

    status = sub.add_parser("status", help="Show plugin paths and available checks")
    status.add_argument("--json", action="store_true", help="Print machine-readable status")

    demo = sub.add_parser("demo", help="Run checks against the bundled sample Crystal state")
    demo.add_argument("--out", default=str(DEFAULT_OUT), help="Report output directory")
    demo.add_argument("--include-absolute-paths", action="store_true", help="Include absolute paths in generated reports")

    check = sub.add_parser("check", help="Run checks against a Crystal state root")
    check.add_argument("--root", required=True, help="Crystal state root containing profiles/")
    check.add_argument("--out", default=str(DEFAULT_OUT), help="Report output directory")
    check.add_argument("--include-absolute-paths", action="store_true", help="Include absolute paths in generated reports")

    cards = sub.add_parser("card-drafts", help="Create card drafts from an existing report directory")
    cards.add_argument("--report-dir", default=str(DEFAULT_OUT), help="Existing report directory")
    cards.add_argument("--out", default=str(DEFAULT_OUT / "kanban-card-drafts.jsonl"), help="Card draft JSONL path")
    cards.add_argument("--min-severity", choices=["advisory", "medium", "high"], default="medium")
    cards.add_argument("--include-absolute-paths", action="store_true", help="Include absolute report paths in card drafts")

    triage = sub.add_parser("triage", help="Print a wake summary only when attention is needed")
    triage.add_argument("--report-dir", default=str(DEFAULT_OUT), help="Existing report directory")
    triage.add_argument("--medium-threshold", type=int, default=1)
    triage.add_argument("--include-absolute-paths", action="store_true", help="Include absolute report path in wake summary")


def _handle_cli(args: argparse.Namespace) -> int:
    command = args.command or "status"
    root = _repo_root()
    if command == "status":
        return _status(root, json_mode=bool(getattr(args, "json", False)))
    if command == "demo":
        return _run_script(
            root,
            "run_crystal_checks.py",
            "--root",
            str(SAMPLE_ROOT),
            "--out",
            str(args.out),
            *(_path_flag(args)),
        )
    if command == "check":
        return _run_script(
            root,
            "run_crystal_checks.py",
            "--root",
            str(args.root),
            "--out",
            str(args.out),
            *(_path_flag(args)),
        )
    if command == "card-drafts":
        return _run_script(
            root,
            "seed_kanban_cards.py",
            "--report-dir",
            str(args.report_dir),
            "--out",
            str(args.out),
            "--min-severity",
            str(args.min_severity),
            *(_path_flag(args)),
        )
    if command == "triage":
        return _run_script(
            root,
            "crystal_triage_gate.py",
            "--report-dir",
            str(args.report_dir),
            "--medium-threshold",
            str(args.medium_threshold),
            *(_path_flag(args)),
        )
    print(f"Unknown crystal-governance command: {command}", file=sys.stderr)
    return 2


def _repo_root() -> Path:
    env_root = os.environ.get("CRYSTAL_GOVERNANCE_STARTER_ROOT", "").strip()
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def _status(root: Path, *, json_mode: bool = False) -> int:
    payload = {
        "plugin": PLUGIN_NAME,
        "repo_root": str(root),
        "plugin_dir": str(Path(__file__).resolve().parent),
        "sample_root": str(root / SAMPLE_ROOT),
        "scripts_dir": str(root / "scripts"),
        "read_only": True,
        "commands": ["status", "demo", "check", "card-drafts", "triage"],
    }
    if json_mode:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(f"{PLUGIN_NAME} plugin")
    print(f"  repo_root : {payload['repo_root']}")
    print(f"  sample    : {payload['sample_root']}")
    print(f"  scripts   : {payload['scripts_dir']}")
    print("  mode      : read-only")
    print("  commands  : status, demo, check, card-drafts, triage")
    return 0


def _path_flag(args: argparse.Namespace) -> list[str]:
    return ["--include-absolute-paths"] if bool(getattr(args, "include_absolute_paths", False)) else []


def _run_script(root: Path, script_name: str, *script_args: str) -> int:
    script = root / "scripts" / script_name
    if not script.exists():
        print(
            f"{PLUGIN_NAME}: cannot find {script}. "
            "Set CRYSTAL_GOVERNANCE_STARTER_ROOT to the starter repo root.",
            file=sys.stderr,
        )
        return 2
    result = subprocess.run([sys.executable, str(script), *script_args], cwd=root, check=False)
    return int(result.returncode)
