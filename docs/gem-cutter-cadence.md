# Gem Cutter Cadence

Gem Cutter is the governance operator for Crystal-style living docs.

It should be diff-aware and quiet:

```text
if Crystal did not change since the last Gem Cutter tick:
  exit with noop_unchanged
elif the session is active:
  inspect, sync only urgent items, defer deep prune
elif the doc is clean and under the idle target:
  exit with idle_clean_noop (no model call)
else:
  prune, reconcile, sync, then seal the final post-sync hash
```

## Good triggers

- profile or session Crystal changed since the last tick;
- session has been idle long enough for cleanup;
- doc exceeds a budget watermark;
- multiple sessions touched the same decision;
- sync queue has conflicts or high-confidence profile-wide deltas;
- operator asks for a checkpoint, handoff, or cleanup audit.

For profile-hub promotion, order sessions by `last_activity_at` with a stable
session-ID tie-breaker. The newest session is authoritative for volatile state.
An older durable claim absent from that head requires corroboration from two
distinct recent session IDs; repeated events from one session count once. Age
events against newest activity and classify volatile text with whole tokens or
narrow phrases, not substring matches.

Profile-hub freshness is a separate verdict from core runtime health. A promised
read-only audit must not call profile sync or rewrite `PROFILE_CRYSTAL.md`.

## Bad triggers

- unchanged Crystal state;
- routine every-turn work that Facet should own;
- background worker chatter;
- cron output that has no durable user-facing value;
- raw transcript size alone without a reviewable target.

## Review packet

A useful Gem Cutter review packet includes:

- changed docs and hashes;
- findings by severity;
- proposed edits;
- stale or conflicting claims;
- evidence handles;
- verification command.

This repo's audit scripts can act as the deterministic front gate for that
packet.
