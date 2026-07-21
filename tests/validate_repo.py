#!/usr/bin/env python3
from __future__ import annotations

import ast
import argparse
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH_LEAK_PATTERNS = [
    re.compile(r"/Users/[A-Za-z0-9_.-]+"),
    re.compile(r"/home/[A-Za-z0-9_.-]+"),
    re.compile(r"[A-Za-z]:\\\\Users\\\\[A-Za-z0-9_.-]+"),
]
PERSONAL_MARKERS = (
    "Ro" + "cky",
    "Ai" + "den",
    "Ro" + "cky-Shared",
    "Coin" + "base",
    "Kra" + "ken",
    "Tele" + "gram",
)
FORBIDDEN = [
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA )?" + "PRIVATE" + r" KEY-----"),
    *PATH_LEAK_PATTERNS,
    *(re.compile(re.escape(marker), re.I) for marker in PERSONAL_MARKERS),
]
SKIP_DIRS = {".git", "reports", "state", "logs", "sessions", "profiles", "cache", "__pycache__", ".ruff_cache"}
REPORT_FORBIDDEN = PATH_LEAK_PATTERNS


def repo_files() -> list[Path]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            text=True,
        )
        return [ROOT / line for line in output.splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError):
        return [
            path
            for path in ROOT.rglob("*")
            if path.is_file() and not any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts)
        ]


def checked_files():
    for path in repo_files():
        if path.is_file() and not any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            yield path


def scan_static_files() -> list[str]:
    errors: list[str] = []
    for path in checked_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(ROOT)
        for pattern in FORBIDDEN:
            if pattern.search(text):
                errors.append(f"sensitive pattern in {rel}: {pattern.pattern}")
    return errors


def exception_names(node: ast.AST | None) -> set[str]:
    if node is None:
        return {"<bare>"}
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    if isinstance(node, ast.Tuple):
        names: set[str] = set()
        for item in node.elts:
            names.update(exception_names(item))
        return names
    return {node.__class__.__name__}


def scan_python_code_flags() -> list[str]:
    errors: list[str] = []
    for path in checked_files():
        if path.suffix != ".py":
            continue
        rel = path.relative_to(ROOT)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(rel))
        except SyntaxError as exc:
            errors.append(f"syntax error in {rel}:{exc.lineno}: {exc.msg}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                errors.append(f"assert statement in runtime code at {rel}:{node.lineno}")
            if isinstance(node, ast.ExceptHandler):
                names = exception_names(node.type)
                if names & {"<bare>", "Exception", "BaseException"}:
                    errors.append(f"broad exception handler at {rel}:{node.lineno}")
    return errors


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scan_read_error_redaction() -> list[str]:
    errors: list[str] = []
    private_path = Path("/" + "Users" + "/example/private/PROFILE_CRYSTAL.md")
    module = load_module(ROOT / "scripts/crystal_governance_audit.py")
    text, read_error = module.read_text(private_path)
    message = f"Could not read file: {read_error}"
    if text is not None or not read_error:
        errors.append("read_text did not return sanitized error for missing private path")
    for pattern in REPORT_FORBIDDEN:
        if pattern.search(message):
            errors.append(f"read error leaks path: {pattern.pattern}")
    return errors


def scan_generated_reports(report_dir: Path) -> list[str]:
    errors: list[str] = []
    for path in report_dir.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(ROOT)
        for pattern in REPORT_FORBIDDEN:
            if pattern.search(text):
                errors.append(f"unredacted generated report path in {rel}: {pattern.pattern}")
    return errors


def scan_governance_contracts() -> list[str]:
    errors: list[str] = []
    combined = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "README.md",
            "docs/architecture.md",
            "docs/profile-session-scope.md",
            "docs/operations-health-and-reconcile.md",
            "docs/workers.md",
            "docs/efficiency-and-savings.md",
            "policies/crystal-governance/scope-rules.yaml",
            "examples/crystal.workers.example.yaml",
            "skills/devops/crystal-governance-starter/SKILL.md",
        )
    )
    required = (
        "94.1%",
        "about 30% net logical tokens saved",
        "25–35%",
        "default Hermes compression",
        "meaningful_turns_since_attempt: 6",
        "accumulated_tool_results_since_success: 12",
        "cooldown_turns: 2",
        "complete context-engine lane",
        "raw Hermes transcript",
        "Profile-hub freshness is a separate health plane",
        "last_activity_at",
        "two distinct recent session IDs",
        "unbound context engine",
        "bg-review",
        "excluded_compressor_state_sync: bidirectional",
    )
    for text in required:
        if text not in combined:
            errors.append(f"missing current Crystal governance contract: {text}")
    if "every_turn_or_two" in combined:
        errors.append("stale Facet cadence every_turn_or_two is still present")

    canonical_contract_keys = (
        "ambient_process_identity_may_bind_unbound_engine",
        "missing_or_malformed_activity_sorts_oldest",
        "allow_when_exact_in_newest",
        "distinct_recent_sessions_required",
        "same_session_repetition_counts_once",
        "freshness_anchor",
        "volatile_matching",
        "read_only_audit_may_sync_profile_hub",
        "synchronized_state_fields",
    )
    deprecated_contract_keys = (
        "ambient_parent_identity_may_authorize_unbound_engine",
        "distinct_recent_sessions_for_older_durable_claim",
        "forbidden_during_read_only_audit",
    )
    for rel_path in (
        "policies/crystal-governance/scope-rules.yaml",
        "examples/crystal.workers.example.yaml",
    ):
        content = (ROOT / rel_path).read_text(encoding="utf-8")
        for key in canonical_contract_keys:
            if key not in content:
                errors.append(f"{rel_path}: missing canonical contract key {key}")
        for key in deprecated_contract_keys:
            if key in content:
                errors.append(f"{rel_path}: contains deprecated contract key {key}")

    def list_below(text: str, key: str) -> list[str]:
        lines = text.splitlines()
        key_indexes = [index for index, line in enumerate(lines) if line.strip() == f"{key}:"]
        if len(key_indexes) != 1:
            return []
        key_index = key_indexes[0]
        key_indent = len(lines[key_index]) - len(lines[key_index].lstrip())
        values: list[str] = []
        for line in lines[key_index + 1 :]:
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())
            if stripped and indent <= key_indent:
                break
            if stripped.startswith("- "):
                values.append(stripped[2:])
        return values

    policy = (ROOT / "policies/crystal-governance/scope-rules.yaml").read_text(encoding="utf-8")
    workers = (ROOT / "examples/crystal.workers.example.yaml").read_text(encoding="utf-8")
    policy_fields = list_below(policy, "synchronized_state_fields")
    worker_fields = list_below(workers, "synchronized_state_fields")
    if not policy_fields or policy_fields != worker_fields:
        errors.append("policy and worker example synchronized_state_fields differ")
    return errors


class FakePluginContext:
    def __init__(self) -> None:
        self.commands: dict[str, tuple[object, object]] = {}

    def register_cli_command(self, name: str, help: str, setup_fn: object, handler_fn: object, description: str) -> None:
        self.commands[name] = (setup_fn, handler_fn)


def run_plugin_demo(report_dir: Path) -> list[str]:
    errors: list[str] = []
    module = load_module(ROOT / "hermes_plugin/crystal_governance/__init__.py")
    ctx = FakePluginContext()
    module.register(ctx)
    command = ctx.commands.get("crystal-governance")
    if command is None:
        return ["crystal-governance plugin did not register CLI command"]
    setup_fn, handler_fn = command
    if not callable(setup_fn) or not callable(handler_fn):
        return ["crystal-governance plugin registered non-callable command handlers"]
    parser = argparse.ArgumentParser()
    setup_fn(parser)
    status_code = handler_fn(parser.parse_args(["status", "--json"]))
    if status_code != 0:
        errors.append(f"crystal-governance status returned {status_code}")
    demo_code = handler_fn(parser.parse_args(["demo", "--out", str(report_dir)]))
    if demo_code != 0:
        errors.append(f"crystal-governance demo returned {demo_code}")
    health_code = handler_fn(
        parser.parse_args(
            [
                "health",
                "--root",
                str(ROOT / "examples/sample-crystal-home"),
                "--out",
                str(report_dir / "plugin-health.json"),
            ]
        )
    )
    if health_code != 0:
        errors.append(f"crystal-governance health returned {health_code}")
    return errors


def main() -> int:
    errors = (
        scan_static_files()
        + scan_python_code_flags()
        + scan_read_error_redaction()
        + scan_governance_contracts()
    )
    report_dir = ROOT / "reports/test"
    errors.extend(run_plugin_demo(report_dir))
    errors.extend(scan_generated_reports(report_dir))
    audit = report_dir / "crystal-governance-audit.json"
    data = json_load(audit)
    if int(data.get("high_count", 0)) or int(data.get("medium_count", 0)):
        errors.append("sample audit produced medium/high findings")
    health = json_load(report_dir / "crystal-health.json")
    if health.get("status") != "HEALTHY" or not bool(health.get("ok")):
        errors.append("sample health check was not healthy")
    plugin_health = json_load(report_dir / "plugin-health.json")
    if plugin_health.get("status") != "HEALTHY" or not bool(plugin_health.get("ok")):
        errors.append("plugin health command was not healthy")
    if errors:
        print("\n".join(errors))
        return 1
    print("validation ok")
    return 0


def json_load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
