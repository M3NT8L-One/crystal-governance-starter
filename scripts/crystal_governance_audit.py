#!/usr/bin/env python3
"""Read-only Crystal living-doc governance audit."""
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(api[_-]?key|password|secret|token)\s*[:=]"),
    re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA )?" + "PRIVATE" + r" KEY-----"),
]
PRIVATE_PATH_PATTERNS = [
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
STALE_PATTERNS = [
    re.compile(r"\b(today|tonight|currently|right now|temporary|for now)\b", re.I),
    re.compile(r"\b(done|fixed|completed|phase [0-9]+|PR #[0-9]+)\b", re.I),
]
CHATTER_PATTERNS = [
    re.compile(r"\b(mic check|status check|reply exactly|tool_choice)\b", re.I),
    re.compile(r"\bwhat do you suggest\b", re.I),
]
SESSION_SECTIONS = [
    "Current Objective",
    "Current Working State",
    "Important Constraints",
    "Decisions and Rationale",
    "Active Open Loops",
    "Relevant Files / Artifacts / Handles",
    "Recent Useful Context / Hot Delta",
]
PROFILE_SECTIONS = [
    "Profile-Wide Current State",
    "Shared Decisions / Constraints",
    "Active Session Handles",
    "Cross-Session Conflicts / Handoffs",
]
ALLOWED_SYNC_KINDS = {"decision", "constraint", "active_handle", "handoff", "conflict", "closeout"}
SKIP_DIRS = {".git", "reports", "logs", "cache", "__pycache__", ".ruff_cache"}

Finding = dict[str, Any]


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8", errors="replace"), None
    except OSError as exc:
        return None, exc.__class__.__name__


def finding(surface: str, severity: str, path: str, kind: str, message: str, line: int | None = None) -> Finding:
    item: Finding = {"surface": surface, "severity": severity, "path": path, "type": kind, "message": message}
    if line is not None:
        item["line"] = line
    return item


def profile_dirs(root: Path) -> list[Path]:
    profiles = root / "profiles"
    if not profiles.exists():
        return []
    return sorted(path for path in profiles.iterdir() if path.is_dir() and not should_skip(path.relative_to(root)))


def line_findings(surface: str, root: Path, path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    rel = str(path.relative_to(root))
    for idx, line in enumerate(text.splitlines(), 1):
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(finding(surface, "high", rel, "secret_like", "Secret-looking text found.", idx))
        for pattern in PRIVATE_PATH_PATTERNS:
            if pattern.search(line):
                findings.append(finding(surface, "high", rel, "private_path", "Private absolute path found.", idx))
        lowered = line.lower()
        if any(marker.lower() in lowered for marker in PERSONAL_MARKERS):
            findings.append(finding(surface, "medium", rel, "personal_marker", "Operator-specific or private project marker found.", idx))
        for pattern in STALE_PATTERNS:
            if pattern.search(line):
                findings.append(finding(surface, "advisory", rel, "stale_language", "Time-sensitive or run-status wording found.", idx))
        for pattern in CHATTER_PATTERNS:
            if pattern.search(line):
                findings.append(finding(surface, "advisory", rel, "chat_or_api_noise", "Chat/API noise usually does not belong in durable Crystal context.", idx))
        if surface != "sync_queue" and len(line) > 260:
            findings.append(finding(surface, "advisory", rel, "long_line", "Long line found; consider compacting or moving detail to evidence.", idx))
    return findings


def parse_markdown_sections(text: str) -> set[str]:
    sections: set[str] = set()
    for line in text.splitlines():
        if line.startswith("## "):
            sections.add(line[3:].strip())
    return sections


def audit_markdown_doc(root: Path, path: Path, surface: str, required_sections: list[str], max_chars: int) -> list[Finding]:
    rel = str(path.relative_to(root))
    text, read_error = read_text(path)
    if read_error:
        return [finding(surface, "medium", rel, "read_error", f"Could not read file: {read_error}")]
    if text is None:
        return []
    findings = line_findings(surface, root, path, text)
    sections = parse_markdown_sections(text)
    for section in required_sections:
        if section not in sections:
            findings.append(finding(surface, "medium", rel, "missing_section", f"Missing section: {section}"))
    if len(text) > max_chars:
        findings.append(finding(surface, "medium", rel, "oversized_doc", "Crystal document is large; review compaction and render policy."))
    return findings


def iter_session_docs(profile_dir: Path) -> Iterable[Path]:
    sessions = profile_dir / "sessions"
    if not sessions.exists():
        return []
    return sorted(path / "CRYSTAL.md" for path in sessions.iterdir() if path.is_dir())


def audit_profile(root: Path, profile_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    rel_profile = str(profile_dir.relative_to(root))
    profile_doc = profile_dir / "PROFILE_CRYSTAL.md"
    if not profile_doc.exists():
        findings.append(finding("profile", "medium", rel_profile + "/PROFILE_CRYSTAL.md", "missing_profile_crystal", "Profile Crystal is missing."))
    else:
        text, read_error = read_text(profile_doc)
        if text is None or read_error:
            findings.append(finding("profile", "medium", str(profile_doc.relative_to(root)), "read_error", f"Could not read file: {read_error}"))
        else:
            if text.lstrip().startswith("# Profile Crystal Hub"):
                findings.append(finding("profile", "advisory", str(profile_doc.relative_to(root)), "legacy_title", "Use '# Profile Crystal: <profile>' instead of legacy hub title."))
            findings.extend(audit_markdown_doc(root, profile_doc, "profile", PROFILE_SECTIONS, 16_000))

    shared_doc = profile_dir / "CRYSTAL.md"
    if shared_doc.exists():
        findings.append(finding("state", "medium", str(shared_doc.relative_to(root)), "shared_mutable_doc", "Profile-level CRYSTAL.md found; use per-session CRYSTAL.md docs instead."))

    sessions_dir = profile_dir / "sessions"
    if not sessions_dir.exists():
        findings.append(finding("state", "medium", rel_profile + "/sessions", "missing_sessions_dir", "Profile has no sessions directory."))
        return findings

    session_docs = list(iter_session_docs(profile_dir))
    if not session_docs:
        findings.append(finding("session", "medium", str(sessions_dir.relative_to(root)), "missing_session_docs", "No per-session CRYSTAL.md docs found."))
    for doc_path in session_docs:
        if not doc_path.exists():
            findings.append(finding("session", "medium", str(doc_path.relative_to(root)), "missing_session_crystal", "Session CRYSTAL.md is missing."))
            continue
        findings.extend(audit_markdown_doc(root, doc_path, "session", SESSION_SECTIONS, 28_000))
        meta = doc_path.parent / "meta.json"
        if not meta.exists():
            findings.append(finding("session", "advisory", str(meta.relative_to(root)), "missing_meta", "Session meta.json is missing."))
    findings.extend(audit_sync_queue(root, profile_dir))
    return findings


def audit_sync_queue(root: Path, profile_dir: Path) -> list[Finding]:
    path = profile_dir / "sync_queue.jsonl"
    rel = str(path.relative_to(root))
    if not path.exists():
        return [finding("sync_queue", "advisory", rel, "missing_sync_queue", "sync_queue.jsonl is missing.")]
    text, read_error = read_text(path)
    if read_error:
        return [finding("sync_queue", "medium", rel, "read_error", f"Could not read file: {read_error}")]
    if text is None:
        return []
    findings = line_findings("sync_queue", root, path, text)
    for idx, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            findings.append(finding("sync_queue", "medium", rel, "invalid_jsonl", "Sync queue line is not valid JSON.", idx))
            continue
        kind = str(event.get("kind", ""))
        if kind not in ALLOWED_SYNC_KINDS:
            findings.append(finding("sync_queue", "medium", rel, "unknown_sync_kind", f"Unknown sync event kind: {kind}", idx))
        for key in ["event_id", "profile", "source_session", "summary", "evidence", "targeting", "created_at"]:
            if key not in event:
                findings.append(finding("sync_queue", "advisory", rel, "missing_sync_field", f"Sync event missing field: {key}", idx))
        if isinstance(event.get("summary"), str) and len(event["summary"]) > 500:
            findings.append(finding("sync_queue", "advisory", rel, "long_sync_summary", "Sync event summary is long; keep cross-session deltas compact.", idx))
    return findings


def audit_root(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    profiles = profile_dirs(root)
    if not profiles:
        findings.append(finding("state", "medium", "profiles/", "missing_profiles", "No profiles directory found."))
        return findings
    for profile_dir in profiles:
        findings.extend(audit_profile(root, profile_dir))
    return findings


def write_reports(out: Path, root: Path, findings: list[Finding], include_absolute_paths: bool = False) -> dict[str, Any]:
    root_display = str(root) if include_absolute_paths else "<audit-root>"
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": root_display,
        "root_path_redacted": not include_absolute_paths,
        "finding_count": len(findings),
        "high_count": sum(1 for item in findings if item.get("severity") == "high"),
        "medium_count": sum(1 for item in findings if item.get("severity") == "medium"),
        "advisory_count": sum(1 for item in findings if item.get("severity") == "advisory"),
        "findings": findings,
    }
    (out / "crystal-governance-audit.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Crystal Governance Summary", "", f"Root: `{root_display}`", f"Findings: {len(findings)}", ""]
    for item in findings[:100]:
        loc = item.get("path", "") + ((":" + str(item["line"])) if "line" in item else "")
        lines.append(f"- **{item['severity']}** `{item['type']}` {loc} - {item['message']}")
    (out / "crystal-governance-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="Crystal state root to inspect")
    ap.add_argument("--out", default="reports/crystal-governance", help="Directory for JSON/Markdown reports")
    ap.add_argument("--include-absolute-paths", action="store_true", help="Write absolute root path into reports. Defaults to redacted for safer sharing.")
    args = ap.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        ap.error("--root must be an existing directory")
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    summary = write_reports(out, root, audit_root(root), args.include_absolute_paths)
    print(json.dumps({key: summary[key] for key in ["finding_count", "high_count", "medium_count", "advisory_count"]}, sort_keys=True))


if __name__ == "__main__":
    main()
