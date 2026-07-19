#!/usr/bin/env python3
"""Report Crystal state and optional source health without changing either."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXCLUDED_ACTOR_KINDS = {
    "auxiliary_model",
    "background_reviewer",
    "background_worker",
    "cron",
    "cron_job",
    "evaluation",
    "internal",
    "kanban_worker",
    "maintenance",
    "scheduler",
    "scratch",
    "scratch_agent",
    "subagent",
}


def safe_identifier(value: str, fallback: str = "item") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip(".-")
    return cleaned[:160] or fallback


def session_identifier_collisions(sessions: dict[str, Any]) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for raw_id in sessions:
        safe_id = safe_identifier(str(raw_id), "session")
        normalized[safe_id] = normalized.get(safe_id, 0) + 1
    return {safe_id: count for safe_id, count in sorted(normalized.items()) if count > 1}


def inferred_actor_kind(entry: dict[str, Any]) -> str:
    aliases = {
        "aux": "auxiliary_model",
        "auxiliary_model": "auxiliary_model",
        "cron": "cron",
        "cron_job": "cron_job",
        "scheduler": "scheduler",
        "subagent": "subagent",
        "kanban": "kanban_worker",
        "kanban_worker": "kanban_worker",
        "maintenance": "maintenance",
        "eval": "evaluation",
        "evaluation": "evaluation",
        "background": "background_worker",
        "background_worker": "background_worker",
        "worker": "background_worker",
        "review": "background_reviewer",
        "reviewer": "background_reviewer",
        "background_reviewer": "background_reviewer",
        "scratch": "scratch",
        "scratch_agent": "scratch_agent",
        "internal": "internal",
    }
    observed = False
    for key in ("platform", "source", "session_type"):
        value = re.sub(r"[^a-z0-9]+", "_", str(entry.get(key) or "").lower()).strip("_")
        observed = observed or bool(value)
        if value in aliases:
            return aliases[value]
    return "frontdoor" if observed else "unknown"


def actor_kind_for_entry(entry: dict[str, Any]) -> str:
    recorded = re.sub(
        r"[^a-z0-9]+", "_", str(entry.get("actor_kind") or "").strip().lower()
    ).strip("_")
    return recorded or inferred_actor_kind(entry)


def entry_is_excluded(entry: dict[str, Any]) -> bool:
    return (
        actor_kind_for_entry(entry) in EXCLUDED_ACTOR_KINDS
        or inferred_actor_kind(entry) in EXCLUDED_ACTOR_KINDS
    )


def health_report(
    root: Path,
    profile: str = "default",
    *,
    source_root: Path | None = None,
    stale_lock_seconds: int = 900,
) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    profile = safe_identifier(profile, "default")
    checks: list[dict[str, Any]] = []
    profile_dir = root / "profiles" / profile
    _check(
        checks,
        name="profile_state",
        ok=profile_dir.is_dir(),
        detail={"profile": profile},
        severity="critical",
    )
    if profile_dir.is_dir():
        _state_checks(checks, profile_dir, stale_lock_seconds)
    if source_root is not None:
        _source_checks(checks, Path(source_root).expanduser().resolve())

    critical_failures = [
        str(check["name"])
        for check in checks
        if not check["ok"] and check["severity"] == "critical"
    ]
    degradations = [
        str(check["name"])
        for check in checks
        if not check["ok"] and check["severity"] == "warning"
    ]
    status = "UNHEALTHY" if critical_failures else "DEGRADED" if degradations else "HEALTHY"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": "<crystal-root>",
        "source_root": "<source-root>" if source_root is not None else None,
        "profile": profile,
        "ok": not critical_failures,
        "status": status,
        "critical_failures": critical_failures,
        "degradations": degradations,
        "checks": checks,
    }


def _state_checks(
    checks: list[dict[str, Any]],
    profile_dir: Path,
    stale_lock_seconds: int,
) -> None:
    stale_locks: list[str] = []
    lock_scan_error = ""
    try:
        for lock in profile_dir.rglob("*.lock"):
            try:
                is_stale = time.time() - lock.stat().st_mtime > stale_lock_seconds
            except OSError:
                is_stale = True
            if is_stale:
                stale_locks.append(str(lock.relative_to(profile_dir)))
    except OSError as exc:
        lock_scan_error = exc.__class__.__name__
    _check(
        checks,
        name="stale_locks",
        ok=not stale_locks and not lock_scan_error,
        detail={
            "count": len(stale_locks),
            "locks": stale_locks[:25],
            "error": lock_scan_error,
        },
        severity="critical",
    )

    registry_path = profile_dir / "registry.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        _check(
            checks,
            name="registry_readable",
            ok=False,
            detail={"path": "registry.json", "error": exc.__class__.__name__},
            severity="critical",
        )
        return
    sessions = registry.get("sessions") if isinstance(registry, dict) else None
    registry_ok = isinstance(sessions, dict)
    _check(
        checks,
        name="registry_readable",
        ok=registry_ok,
        detail={"path": "registry.json", "sessions": len(sessions or {})},
        severity="critical",
    )
    if not registry_ok:
        return

    collisions = session_identifier_collisions(sessions)
    _check(
        checks,
        name="session_identifier_collisions",
        ok=not collisions,
        detail={"collision_count": len(collisions)},
        severity="critical",
    )

    excluded: list[str] = []
    unclassified: list[str] = []
    retired: list[str] = []
    for session_id, raw_entry in sorted(sessions.items()):
        safe_id = safe_identifier(str(session_id), "session")
        if not isinstance(raw_entry, dict):
            excluded.append(safe_id)
            continue
        if actor_kind_for_entry(raw_entry) == "unknown":
            unclassified.append(safe_id)
        if entry_is_excluded(raw_entry):
            excluded.append(safe_id)
        if raw_entry.get("retired") is True or str(raw_entry.get("status") or "").lower() == "retired":
            retired.append(safe_id)
    _check(
        checks,
        name="excluded_actor_registry",
        ok=not excluded,
        detail={"count": len(excluded), "sessions": excluded[:25]},
        severity="warning",
    )
    _check(
        checks,
        name="unclassified_actor_registry",
        ok=not unclassified,
        detail={"count": len(unclassified), "sessions": unclassified[:25]},
        severity="warning",
    )

    session_root = profile_dir / "sessions"
    session_error = ""
    directories: set[str] = set()
    if not session_root.exists():
        session_error = "FileNotFoundError"
    elif not session_root.is_dir():
        session_error = "NotADirectoryError"
    else:
        try:
            directories = {item.name for item in session_root.iterdir() if item.is_dir()}
        except OSError as exc:
            session_error = exc.__class__.__name__
    _check(
        checks,
        name="session_directory_readable",
        ok=not session_error,
        detail={"directory_count": len(directories), "error": session_error},
        severity="critical",
    )
    if session_error:
        return
    registered = {safe_identifier(str(item), "session") for item in sessions}
    orphans = sorted(directories - registered)
    missing = sorted(registered - directories)
    _check(
        checks,
        name="session_registry_alignment",
        ok=not orphans and not missing,
        detail={
            "orphan_count": len(orphans),
            "orphan_sessions": orphans[:25],
            "missing_count": len(missing),
            "missing_sessions": missing[:25],
        },
        severity="warning",
    )
    _check(
        checks,
        name="registry_prune_backlog",
        ok=not retired,
        detail={"candidate_count": len(retired), "sessions": retired[:25]},
        severity="warning",
    )


def _source_checks(checks: list[dict[str, Any]], source_root: Path) -> None:
    status = _git(source_root, "status", "--porcelain")
    is_git = status is not None
    dirty = [line for line in (status or "").splitlines() if line.strip()]
    _check(
        checks,
        name="live_source_clean",
        ok=is_git and not dirty,
        detail={"git": is_git, "dirty_count": len(dirty)},
        severity="warning",
    )
    remotes = _git(source_root, "remote") if is_git else None
    names = [line.strip() for line in (remotes or "").splitlines() if line.strip()]
    _check(
        checks,
        name="source_durability",
        ok=bool(names),
        detail={"git": is_git, "remote_count": len(names)},
        severity="warning",
    )


def _git(source_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(source_root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def _check(
    checks: list[dict[str, Any]],
    *,
    name: str,
    ok: bool,
    detail: Any,
    severity: str,
) -> None:
    checks.append({"name": name, "ok": bool(ok), "severity": severity, "detail": detail})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="examples/sample-crystal-home")
    ap.add_argument("--profile", default="default")
    ap.add_argument("--source-root", help="Optional deployed source tree to inspect")
    ap.add_argument("--out", default="reports/crystal-governance/crystal-health.json")
    args = ap.parse_args()
    root = Path(args.root).expanduser()
    if not root.is_dir():
        ap.error("--root must be an existing directory")
    source = Path(args.source_root).expanduser() if args.source_root else None
    report = health_report(root, args.profile, source_root=source)
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "status": report["status"]}, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
