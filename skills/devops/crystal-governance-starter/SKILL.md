# Crystal Governance Starter

Use this skill when reviewing or maintaining Crystal-style living context docs.

## Operating Rules

1. Treat Crystal state as sensitive by default.
2. Read `PROFILE_CRYSTAL.md`, per-session `CRYSTAL.md`, sync queue entries, and reports before proposing changes.
3. Keep Profile Crystal small and profile-wide.
4. Keep session Crystal docs local to one conversation.
5. Move cross-session context through structured sync events and review.
6. Do not promote raw tool output, private paths, credentials, or chat/API noise.
7. Use sanitized tool summaries for Facet-style maintenance.
8. Prefer-recent Facet merges; Hot Delta is a rolling replace window, not an archive.
9. Crystallizer: pressure compact and earlier quality hygiene (not only 75% fill).
8. Let Gem Cutter perform diff-aware prune/sync work only when Crystal changed and the session is suitable for cleanup.
9. Durable memory, skill, fact, or profile promotions require explicit review.

## Workflow

```bash
python3 scripts/run_crystal_checks.py --root examples/sample-crystal-home --out reports/demo
```

For a real state root, run the same command against a staging copy first.

When findings appear:

1. Confirm the finding.
2. Fix the smallest relevant surface.
3. Rerun the audit.
4. Close with evidence.
