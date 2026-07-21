# Crystal Governance Architecture

## V0 shape

Crystal-style context works best as a profile domain with per-session living
docs:

```text
profiles/<profile>/
  PROFILE_CRYSTAL.md
  sync_queue.jsonl
  registry.json
  sessions/
    <session_id>/CRYSTAL.md
    <session_id>/meta.json
```

The profile document holds durable profile-wide continuity. Each session keeps
its own local working context. Cross-session facts move through a small sync
queue and review policy instead of direct doc-to-doc copying.

The raw Hermes transcript remains authoritative historical evidence. Crystal is
a bounded working-context layer, not a replacement transcript or permanent
memory system.

## Why governance is needed

Living context can drift in subtle ways:

- raw transcript chatter becomes durable context;
- local file paths or private handles leak into a shareable surface;
- background worker status gets promoted as profile truth;
- one session overwrites another session's working state;
- a stale profile hub looks trustworthy because core runtime checks are green;
- stale "currently" and "for now" claims survive after the run ends;
- Facet stacks near-duplicate objectives/open loops while the doc is still small;
- Hot Delta freezes early turns instead of rolling with the conversation;
- scheduled pruning runs even when nothing changed.

Governance keeps those failure modes boring and visible.

## Surfaces

| Surface | Use for | Avoid |
|---|---|---|
| `PROFILE_CRYSTAL.md` | profile-wide decisions, constraints, stable handles, handoff summary | raw transcript detail, temporary tool output, private paths |
| `CRYSTAL.md` | session-local current state, decisions, open loops, evidence handles | unrelated sessions, long logs, credentials |
| `sync_queue.jsonl` | proposed cross-session deltas with kind, summary, evidence, and targeting | prose dumps, unstructured reports |
| reports | temporary audit evidence | durable profile truth |

## Worker roles

```text
Facet
  stateful small-model operations; default 6 turns / 12 tools / 2-turn cooldown

Crystallizer
  pressure compact at upper watermark, or earlier quality hygiene (turn/quality gates)

Gem Cutter
  diff-aware idle governance; spend only when size or quality pressure exists
```

Facet and Crystallizer keep the session useful while work is active. Gem Cutter
should be quieter: check only after Crystal changed, prefer idle windows, and
spend a model call only when size or quality pressure exists.

See `workers.md` for worker inputs, triggers, prompt contracts, and setup.

## Scope rule

Enable Crystal only for positively classified human-facing front doors. Missing
platform and source identity fails closed. Keep subagents, auxiliary model
calls, cron/scheduler runs, Kanban workers, maintenance, evaluation, review, and
scratch sessions outside Crystal unless a reviewed policy explicitly includes
them.

An unbound context engine copied for background work must not inherit ambient
process identity from its parent front door. Until the copy has its own explicit
session binding, route it to ordinary Hermes compression. Also reject Hermes's
exact `bg-review` thread before ambient front-door classification: that worker
can retain the parent's platform and session identity even though it is not a
human-facing conversation. Do not exclude unrelated worker thread names by
substring.

There are two write boundaries:

1. pre/post-turn hooks must not create Crystal state for excluded actors;
2. the complete Crystal context-engine lane must delegate excluded actors to
   ordinary Hermes compression without Crystal telemetry or filesystem writes.

Method routing alone is insufficient if the wrapper and built-in compressor
split budgets and thresholds, token counters, post-compression latches,
effectiveness/error state, context-probe state, compression counts, or session
binding. Synchronize that state in both directions before and after every
excluded compressor call. Preserve positional and keyword session binding,
cache host binding before actor identity exists, and rebind after fallback
recreation. Prove the host-visible session ID and state match the built-in
compressor lifecycle. Routing mocks alone are not proof: exercise lowered
thresholds, preflight deferral, compaction latches, and real-usage latch clearing.

## Independent health planes

Profile-hub freshness is a separate health plane. A green plugin load, core
health check, test suite, session tick, or scheduled governance pass does not
prove that `PROFILE_CRYSTAL.md` reflects the current head session.

Report at least four verdicts separately: core state compatibility,
excluded-actor integrity, session continuity, and profile-hub freshness. Profile
promotion uses the newest session by `last_activity_at`; see
`docs/profile-session-scope.md` for recency, corroboration, and supersession
rules.

## Write integrity

- Lock the session document before metadata; never reverse the order.
- Update registries through one locked read-modify-write transaction.
- Mutate metadata under a lock rather than saving stale snapshots.
- On successful Facet work, clear only reasons and tool pressure represented by
  that decision so concurrent turns remain pending.
- Apply the same redaction boundary to deterministic extraction and
  model-authored operations. Reject secret-only authoritative operations rather
  than erasing prior valid state.
- Test heterogeneous writers, such as context rendering plus a maintainer tick.

See `workers.md`, `privacy-and-redaction.md`, and `efficiency-and-savings.md` for the
current starter contracts.

## Review loop

```text
read-only audit + health
  -> quiet if clean and HEALTHY
  -> wake if medium/high findings or health degradation exist
  -> review the smallest scoped issue
  -> dry-run reconciliation when registry drift is involved
  -> apply only after plan review; archive evidence and write a receipt
  -> rerun checks
  -> close with evidence
```

Audit, health, triage, and the Hermes companion plugin are read-only except for
report output. The standalone reconciliation script is dry-run by default;
explicit apply mode archives selected session evidence, updates the registry,
and rolls back moved evidence plus the registry snapshot on handled I/O failure.
It refuses normalized session-ID collisions, does not call external APIs, and
does not irreversibly delete session evidence.
