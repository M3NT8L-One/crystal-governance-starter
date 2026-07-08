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

## Why governance is needed

Living context can drift in subtle ways:

- raw transcript chatter becomes durable context;
- local file paths or private handles leak into a shareable surface;
- background worker status gets promoted as profile truth;
- one session overwrites another session's working state;
- stale "currently" and "for now" claims survive after the run ends;
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
  small hot merge after user-facing turns

Crystallizer
  whole-doc compaction when upper watermark or hygiene trigger fires

Gem Cutter
  diff-aware governance prune, sync, and conflict review
```

Facet and Crystallizer keep the session useful while work is active. Gem Cutter
should be quieter: wake only when Crystal changed, prefer idle windows for deep
prune, and emit reviewable changes.

## Scope rule

Attach Crystal governance to the user-facing profile that owns durable
continuity. Keep auxiliary workers, cron jobs, review agents, and scratch
sessions outside the Crystal write path unless explicitly enabled.

This prevents helper state from becoming profile truth.

## Review loop

```text
read-only audit
  -> quiet if clean
  -> wake if medium/high findings exist
  -> fix smallest scoped issue
  -> rerun audit
  -> close with evidence
```

The scripts in this repo implement the read-only audit and wake gate portions.
They do not call external APIs or mutate Crystal state.
