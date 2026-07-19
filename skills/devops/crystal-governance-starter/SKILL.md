---
name: crystal-governance-starter
description: Use when reviewing or maintaining Crystal-style bounded living-context documents, worker cadence, actor isolation, token economics, health, or reversible registry reconciliation.
version: 2.0.0
author: Crystal Governance Starter
license: MIT
metadata:
  hermes:
    tags: [crystal, context, continuity, governance, token-efficiency]
    lifecycle: starter
    risk_level: file_write_reversible
---

# Crystal Governance Starter

## When to Use

- Reviewing profile or session Crystal documents.
- Designing front-door-only Crystal scope and background-actor exclusion.
- Calibrating deterministic, Facet, Crystallizer, or Gem Cutter work.
- Estimating token savings versus default Hermes compression.
- Auditing health or planning reversible registry reconciliation.

Crystal is bounded working context. It is not permanent memory, a replacement transcript, or permission for high-risk actions.

## Operating Rules

1. Treat Crystal state as sensitive by default.
2. Keep raw Hermes transcripts as authoritative evidence.
3. Enable Crystal only for positively classified human-facing front doors; missing platform and source identity fails closed.
4. Exclude auxiliary models, subagents, cron/scheduler jobs, Kanban workers, maintenance, evaluation, review, and scratch actors at hooks and the complete context-engine lane.
5. For excluded actors, preserve ordinary built-in compression state while creating no Crystal telemetry, directory, or registry entry.
6. Keep Profile Crystal small and profile-wide; keep each session Crystal local to one conversation.
7. Move cross-session context through structured sync events and review.
8. Run deterministic bounded extraction after meaningful front-door turns.
9. Queue Facet through stateful defaults: six meaningful turns since attempt, twelve accumulated tool results since success, lifecycle/quality reasons, and a two-turn cooldown.
10. Facet returns authoritative operations: snapshot sections allow `replace`/`clear`; durable sections allow `merge`; unknown and stale sections are rejected.
11. Empty or invalid operations are failures. A successful idempotent operation may leave bytes unchanged.
12. Preserve pending work added by concurrent turns; clear only the reasons and tool pressure represented by the completed Facet decision.
13. Run Crystallizer on pressure (~75% toward ~50%), normal cadence, or earlier quality hygiene; keep the previous completed document if it fails.
14. Run Gem Cutter only after a diff and idle check. Spend a model call only for size or quality pressure; clean small state is a zero-model no-op.
15. Apply one redaction boundary to deterministic extraction and model-authored writes. Reject secret-only authoritative operations.
16. Lock document before metadata, mutate metadata under lock, and update registries through locked read-modify-write.
17. Durable memory, skill, fact, or profile promotion remains a separate reviewed action.
18. Treat `DEGRADED` as visible maintenance debt and `UNHEALTHY` as a service failure.
19. Fix drift producers before reconciliation. Protect every non-target in the full candidate set, require a singleton dry run, then archive with receipt and verification.

## Workflow

Run the safe sample checks:

```bash
python3 scripts/run_crystal_checks.py --root examples/sample-crystal-home --out reports/demo
```

For a real state root, run the same command against a staging copy first.

When findings or health degradation appear:

1. Confirm the evidence and health class.
2. Fix the smallest relevant producer or policy surface.
3. For registry drift, run `crystal_registry_reconcile.py` without `--apply`.
4. Protect every non-target candidate and require one exact target on the second dry run.
5. Apply only against staged state; require archive, receipt, checksums, and expected alignment delta.
6. If apply fails, require `rolled_back`; stop for manual restoration on `rollback_failed`.
7. Rerun audit and health checks.
8. Close with evidence; never publish receipts, snapshots, archived sessions, transcripts, or runtime state.

## Token-Savings Guidance

Keep four layers separate: gross history reduction, post-compression total-request reduction, full-day net logical-token reduction, and billable-equivalent/dollar reduction.

For two long busy front-door sessions, use **about 30% net logical tokens saved** as a planning number and **25–35%** as a normal range. Very long tool-heavy sessions can be higher. Short sessions below the first boundary can be near zero or slightly negative after maintenance.

The measured **94.1%** ratio applies only to the replaceable history slice. Never present it as daily savings. Include fixed system/tool input, default Hermes compression, early calls, worker maintenance, and provider cache semantics. See `docs/efficiency-and-savings.md`.

## Common Pitfalls

1. Putting Crystal into subagents or scheduled workers because the hooks appear excluded while the context engine still writes metadata.
2. Delegating compressor methods without synchronizing wrapper-visible thresholds and post-compression latches.
3. Running Facet every turn or using a lifetime sticky tool threshold instead of stateful 6/12/2 decisions.
4. Treating empty Facet operations as success and wiping pending work.
5. Redacting model input but accepting unredacted model-authored bullets.
6. Running Gem Cutter on unchanged or clean-small state.
7. Saving stale metadata snapshots or updating the registry without a lock.
8. Calling a 90%+ history ratio daily, billable, or dollar savings.
9. Applying registry reconciliation to a broad candidate set or deleting state without an archive receipt.

## Verification Checklist

- [ ] Positive front-door sessions create bounded Crystal state.
- [ ] Real excluded actors create no Crystal directory or registry entry.
- [ ] Excluded compression thresholds and latches remain coherent.
- [ ] Deterministic and model-authored writes share redaction and secret-only rejection.
- [ ] Facet cadence, success semantics, and concurrent pending-state behavior are tested.
- [ ] Crystallizer keeps the last completed document on failure.
- [ ] Gem Cutter is diff-aware, idle-aware, and quiet on unchanged or clean-small state.
- [ ] Document, metadata, and registry concurrency tests cover heterogeneous writers.
- [ ] Token claims include default compression, fixed prompt, maintenance, and cache caveats.
- [ ] Reconciliation is singleton, reversible, receipt-backed, and verified.
