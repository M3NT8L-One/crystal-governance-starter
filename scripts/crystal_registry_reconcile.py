#!/usr/bin/env python3
"""Plan or apply reversible Crystal registry reconciliation."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crystal_health_check import entry_is_excluded, safe_identifier, session_identifier_collisions


def reconcile_registry(
    root: Path,
    profile: str = "default",
    *,
    dry_run: bool = True,
    protect_sessions: list[str] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    profile = safe_identifier(profile, "default")
    profile_dir = root / "profiles" / profile
    registry_path = profile_dir / "registry.json"
    protected = {safe_identifier(item, "session") for item in (protect_sessions or [])}
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        return {
            "ok": False,
            "profile": profile,
            "dry_run": dry_run,
            "error": exc.__class__.__name__,
            "registry": "registry.json",
        }
    sessions = registry.get("sessions") if isinstance(registry, dict) else None
    if not isinstance(sessions, dict):
        return {
            "ok": False,
            "profile": profile,
            "dry_run": dry_run,
            "error": "registry sessions is not an object",
            "registry": "registry.json",
        }
    collisions = session_identifier_collisions(sessions)
    if collisions:
        return {
            "ok": False,
            "profile": profile,
            "dry_run": dry_run,
            "error": "session identifier collision",
            "collision_count": len(collisions),
            "registry": "registry.json",
        }

    session_root = profile_dir / "sessions"
    if not session_root.exists():
        return {
            "ok": False,
            "profile": profile,
            "dry_run": dry_run,
            "error": "FileNotFoundError",
            "session_root": "sessions",
        }
    if not session_root.is_dir():
        return {
            "ok": False,
            "profile": profile,
            "dry_run": dry_run,
            "error": "NotADirectoryError",
            "session_root": "sessions",
        }
    try:
        directories = {item.name for item in session_root.iterdir() if item.is_dir()}
    except OSError as exc:
        return {
            "ok": False,
            "profile": profile,
            "dry_run": dry_run,
            "error": exc.__class__.__name__,
            "session_root": "sessions",
        }
    registered = {safe_identifier(str(item), "session") for item in sessions}
    candidates: dict[str, dict[str, Any]] = {}
    for raw_id, raw_entry in sorted(sessions.items()):
        safe_id = safe_identifier(str(raw_id), "session")
        if safe_id in protected:
            continue
        reasons: list[str] = []
        if not isinstance(raw_entry, dict):
            reasons.append("invalid_registry_entry")
        else:
            if entry_is_excluded(raw_entry):
                reasons.append("excluded_actor")
            if raw_entry.get("retired") is True or str(raw_entry.get("status") or "").lower() == "retired":
                reasons.append("stale_registry_entry")
        if safe_id not in directories:
            reasons.append("missing_session_directory")
        if reasons:
            candidates[safe_id] = {
                "session_id": safe_id,
                "reasons": reasons,
                "registered": True,
                "directory_exists": safe_id in directories,
            }
    for safe_id in sorted(directories - registered - protected):
        candidates[safe_id] = {
            "session_id": safe_id,
            "reasons": ["orphan_session_directory"],
            "registered": False,
            "directory_exists": True,
        }

    result: dict[str, Any] = {
        "ok": True,
        "profile": profile,
        "dry_run": dry_run,
        "registry": "registry.json",
        "protected": sorted(protected),
        "candidate_count": len(candidates),
        "summary": _summary(candidates),
        "candidates": list(candidates.values())[:100],
        "applied": False,
        "archive": "",
        "receipt": "",
    }
    if dry_run or not candidates:
        return result

    stamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_rel = Path("archive") / f"registry-reconcile-{safe_identifier(stamp, 'run')}"
    archive = profile_dir / archive_rel
    if archive.exists():
        result.update({"ok": False, "error": "archive already exists"})
        return result
    receipt_rel = archive_rel / "receipt.json"
    receipt_path = profile_dir / receipt_rel
    registry_before = archive / "registry.before.json"
    registry_after = archive / "registry.after.json"
    planned_moves = [
        {
            "session_id": safe_id,
            "from": str(Path("sessions") / safe_id),
            "to": str(archive_rel / "sessions" / safe_id),
        }
        for safe_id, item in candidates.items()
        if item["directory_exists"]
    ]
    receipt: dict[str, Any] = {
        "version": 1,
        "status": "planned",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "registry": "registry.json",
        "archive": str(archive_rel),
        "registry_before": str(archive_rel / "registry.before.json"),
        "registry_after": str(archive_rel / "registry.after.json"),
        "candidates": list(candidates.values()),
        "planned_moves": planned_moves,
        "moves": [],
        "restore": {
            "registry_snapshot": str(archive_rel / "registry.before.json"),
            "session_archive": str(archive_rel / "sessions"),
        },
    }
    moves: list[dict[str, str]] = []
    try:
        archive.mkdir(parents=True)
        shutil.copy2(registry_path, registry_before)
        _atomic_write_json(receipt_path, receipt)

        for move in planned_moves:
            source = profile_dir / move["from"]
            destination = profile_dir / move["to"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            moves.append(move)
            receipt.update({"status": "applying", "moves": list(moves)})
            _atomic_write_json(receipt_path, receipt)

        updated_sessions = dict(sessions)
        removed_count = 0
        for safe_id, item in candidates.items():
            if not item["registered"]:
                continue
            for raw_id in list(updated_sessions):
                if safe_identifier(str(raw_id), "session") == safe_id:
                    updated_sessions.pop(raw_id, None)
                    removed_count += 1
                    break
        updated_registry = dict(registry)
        updated_registry["sessions"] = updated_sessions
        updated_registry["updated_at"] = datetime.now(timezone.utc).isoformat()
        _atomic_write_json(registry_after, updated_registry)
        receipt.update(
            {
                "status": "ready",
                "moves": list(moves),
                "removed_registry_count": removed_count,
                "remaining_registry_sessions": len(updated_sessions),
            }
        )
        _atomic_write_json(receipt_path, receipt)
        _atomic_write_json(registry_path, updated_registry)
        receipt.update(
            {
                "status": "complete",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        _atomic_write_json(receipt_path, receipt)
    except (OSError, shutil.Error) as exc:
        rollback_errors = _rollback_apply(
            profile_dir=profile_dir,
            registry_path=registry_path,
            registry_before=registry_before,
            moves=moves,
        )
        status = "rollback_failed" if rollback_errors else "rolled_back"
        receipt.update(
            {
                "status": status,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "failure": exc.__class__.__name__,
                "moves": list(moves),
                "rollback_errors": rollback_errors,
            }
        )
        try:
            _atomic_write_json(receipt_path, receipt)
        except OSError as receipt_exc:
            rollback_errors.append(f"receipt:{receipt_exc.__class__.__name__}")
            status = "rollback_failed"
        result.update(
            {
                "ok": False,
                "status": status,
                "error": exc.__class__.__name__,
                "archive": str(archive_rel),
                "receipt": str(receipt_rel),
                "moved_directories": len(moves),
                "rollback_errors": rollback_errors,
            }
        )
        return result

    result.update(
        {
            "applied": True,
            "status": "complete",
            "archive": str(archive_rel),
            "receipt": str(receipt_rel),
            "moved_directories": len(moves),
            "removed_registry_entries": removed_count,
            "remaining_registry_sessions": len(updated_sessions),
        }
    )
    return result


def _rollback_apply(
    *,
    profile_dir: Path,
    registry_path: Path,
    registry_before: Path,
    moves: list[dict[str, str]],
) -> list[str]:
    errors: list[str] = []
    for move in reversed(moves):
        source = profile_dir / move["from"]
        destination = profile_dir / move["to"]
        try:
            if not destination.exists():
                continue
            if source.exists():
                errors.append("move:source_exists")
                continue
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination), str(source))
        except (OSError, shutil.Error) as exc:
            errors.append(f"move:{exc.__class__.__name__}")
    if registry_before.exists():
        try:
            original = json.loads(registry_before.read_text(encoding="utf-8"))
            if not isinstance(original, dict):
                errors.append("registry:invalid_snapshot")
            else:
                _atomic_write_json(registry_path, original)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"registry:{exc.__class__.__name__}")
    return errors


def _summary(candidates: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in candidates.values():
        for reason in item["reasons"]:
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="examples/sample-crystal-home")
    ap.add_argument("--profile", default="default")
    ap.add_argument("--protect-session", action="append", default=[])
    ap.add_argument("--apply", action="store_true", help="Apply the plan; default is dry-run")
    args = ap.parse_args()
    root = Path(args.root).expanduser()
    if not root.is_dir():
        ap.error("--root must be an existing directory")
    result = reconcile_registry(
        root,
        args.profile,
        dry_run=not args.apply,
        protect_sessions=args.protect_session,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
