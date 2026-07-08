# Gem Cutter Cadence

Gem Cutter is the governance operator for Crystal-style living docs.

It should be diff-aware and quiet:

```text
if Crystal did not change since the last Gem Cutter tick:
  exit quietly
elif the session is active:
  inspect, sync only urgent items, defer deep prune
else:
  prune, reconcile, and emit reviewable changes
```

## Good triggers

- profile or session Crystal changed since the last tick;
- session has been idle long enough for cleanup;
- doc exceeds a budget watermark;
- multiple sessions touched the same decision;
- sync queue has conflicts or high-confidence profile-wide deltas;
- operator asks for a checkpoint, handoff, or cleanup audit.

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
