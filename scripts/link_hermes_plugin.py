#!/usr/bin/env python3
"""Link the Crystal governance companion plugin into a Hermes plugin directory."""
from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SOURCE = ROOT / "hermes_plugin" / "crystal_governance"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--plugins-dir",
        default=str(Path.home() / ".hermes" / "plugins"),
        help="Hermes user plugin directory",
    )
    ap.add_argument("--name", default="crystal-governance", help="Symlink name")
    ap.add_argument("--force", action="store_true", help="Replace an existing symlink at the target")
    args = ap.parse_args()

    plugins_dir = Path(args.plugins_dir).expanduser()
    target = plugins_dir / args.name
    plugins_dir.mkdir(parents=True, exist_ok=True)

    if target.exists() or target.is_symlink():
        if target.is_symlink() and args.force:
            target.unlink()
        else:
            print(f"Target already exists: {target}")
            print("Use --force to replace an existing symlink.")
            return 2

    os.symlink(PLUGIN_SOURCE, target)
    print(f"Linked {target} -> {PLUGIN_SOURCE}")
    print("Next: hermes plugins list && hermes plugins enable crystal-governance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
