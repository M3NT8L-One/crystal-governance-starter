# Setup Guide

## 1. Start with the sample state

```bash
python3 scripts/run_crystal_checks.py --root examples/sample-crystal-home --out reports/demo
```

The sample intentionally has no medium or high findings and reports `HEALTHY`.
Reports are written under `reports/demo/`, which is ignored by git.

## 2. Understand the checked shape

The audit expects a Crystal state root shaped like:

```text
profiles/
  default/
    PROFILE_CRYSTAL.md
    sync_queue.jsonl
    sessions/
      session-alpha/
        CRYSTAL.md
        meta.json
```

If your runtime stores state elsewhere, point `--root` at a staging copy or at
the directory that contains `profiles/`.

## 3. Run read-only checks on a staging copy

```bash
python3 scripts/run_crystal_checks.py \
  --root /path/to/staged-crystal-state \
  --out reports/staged
```

By default, reports redact absolute root and report paths. Use
`--include-absolute-paths` only for private local debugging.

## 4. Review findings and health

Findings are grouped by surface:

- `profile`: profile-wide `PROFILE_CRYSTAL.md`
- `session`: per-session `CRYSTAL.md` docs
- `sync_queue`: cross-session sync proposals
- `state`: missing or risky state layout
- `repo`: pre-share validation of this starter repo

Medium and high findings should be reviewed before being fixed in live state.
Health reports distinguish operational failures (`UNHEALTHY`) from visible
maintenance debt (`DEGRADED`). See `operations-health-and-reconcile.md`.

## 5. Understand the worker setup

Read `docs/workers.md` before wiring live maintenance. The short version:

- A deterministic tick patches bounded, redacted state after meaningful turns.
- Facet's small-model pass is stateful by default: six meaningful turns since attempt,
  twelve accumulated tool results since success, or a lifecycle/quality reason,
  with a two-turn cooldown.
- Crystallizer rewrites on pressure (~75%→~50%) or earlier quality hygiene (turn/quality gates).
- Gem Cutter runs from a quiet cadence and only does meaningful work when
  Crystal changed, the session is idle, and size or quality pressure exists.

Use `examples/crystal.workers.example.yaml` as a starting contract for routes,
triggers, locks, and render targets.

Before enabling a live integration, positively classify front-door actors and
gate both hooks and the complete context-engine lane. Real subagent, cron, and
worker smokes must create no Crystal directory or registry entry. An unbound
copied engine must ignore ambient parent identity, and an exact `bg-review`
thread must remain excluded even when it retains the parent session identity.
For excluded actors, verify bidirectional host-to-fallback threshold, latch,
usage, error, probe, and session-binding state—not only method routing. Preserve
raw Hermes transcripts as authoritative evidence.

Record `last_activity_at` for every session. Profile-hub promotion should use the
newest activity as the volatile head and require two-session corroboration for
older durable claims. Check profile-hub freshness separately from core health,
and never invoke a profile-hub writer during a promised read-only audit.

Read `docs/efficiency-and-savings.md` before publishing efficiency estimates. Short
sessions below the first compression boundary may see no savings or slight
maintenance overhead.

## 6. Dry-run registry reconciliation

When health reports registry drift, run the standalone reconciliation planner
against the staging copy:

```bash
python3 scripts/crystal_registry_reconcile.py \
  --root /path/to/staged-crystal-state \
  --profile default
```

The dry run can include stale registered entries as well as orphan directories.
Protect every non-target candidate, rerun the dry run, and require one exact
target before `--apply`. Apply mode archives session evidence and writes a
restoration receipt; never use bare deletion.

## 7. Wire a quiet cron

Use `cron/crystal-governance.example.yaml` as a template. A good default is:

```text
run audit + health -> write reports -> print nothing unless findings or degradation exist
```

Keep cron read-only. Let a human or review agent apply fixes.

## 8. Link the Hermes companion plugin

For a native agent/operator command surface, link the bundled read-only plugin:

```bash
python3 scripts/link_hermes_plugin.py
hermes plugins enable crystal-governance
hermes crystal-governance demo --out reports/plugin-demo
```

See `docs/hermes-plugin.md` for the command list and agent-facing prompt.

## 9. Keep publication separate from live state

Before sharing any Crystal setup:

```bash
python3 tests/validate_repo.py
```

The validator scans tracked and untracked non-ignored files, runs the sample
checks, and verifies that generated reports do not leak private absolute paths.
