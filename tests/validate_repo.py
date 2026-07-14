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
    errors = scan_static_files() + scan_python_code_flags() + scan_read_error_redaction()
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
