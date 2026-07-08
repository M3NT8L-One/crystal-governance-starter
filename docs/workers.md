# Worker Model And Setup

Crystal uses three worker roles. They are not extra chat participants. They
maintain the living context files that the live Crystal plugin can render into
the next model request.

This starter documents the contracts and governance checks. A live Crystal
runtime still needs a context plugin or sidecar that runs the workers.

## Worker Summary

| Worker | Tier | Main job | Normal trigger | Writes |
|---|---|---|---|---|
| Facet | fast/small | Patch hot sections from a new turn | Every turn or two when there is meaningful delta | Session `CRYSTAL.md` |
| Crystallizer | medium | Rewrite a large session doc toward the lower watermark | Upper watermark, N turns, or quality flag | Session `CRYSTAL.md` |
| Gem Cutter | strong/governance | Prune, reconcile, and sync after meaningful diffs | Quiet cadence, usually after idle | `PROFILE_CRYSTAL.md`, session docs, sync/review packet |

## Data Flow

```text
user-facing turn completes
  -> deterministic extraction finds handles, decisions, constraints, open loops
  -> Facet patches selected hot sections
  -> Crystallizer rewrites the session doc only when compaction is due
  -> Gem Cutter wakes on cadence, checks hashes, and usually exits quietly
  -> next request reads Profile Crystal + Session Crystal + hot tail
```

The main agent should see the latest completed Crystal state. It should not
wait on a long worker run unless the runtime chooses to make that a hard gate.

## Facet

Facet is the fast live maintainer. It keeps the session `CRYSTAL.md` useful
while work is active.

Recommended inputs:

- profile and session id;
- selected current sections, not the whole doc by default;
- compact user and assistant text from the new turn;
- deterministic extracted delta;
- sanitized tool summaries, not raw tool payloads;
- source/evidence handles.

Rules:

- Patch only hot sections such as objective, working state, constraints,
  decisions, open loops, handles, and hot delta.
- Skip model work if deterministic extraction finds no meaningful delta.
- Preserve evidence handles for important claims.
- Redact secret-like values and avoid private paths in shared examples.
- Return compact structured status, not chat prose.
- Escalate to Crystallizer when the patch is too complex.

Typical trigger:

```yaml
facet:
  cadence: every_turn_or_two
  skip_if_no_meaningful_delta: true
  update_mode: hot_sections_only
  raw_tool_payloads: unavailable
  tool_context: sanitized_summaries
```

## Crystallizer

Crystallizer is the medium whole-doc compactor. It keeps a session doc from
ballooning or drifting while preserving the live working state.

Recommended inputs:

- full current session `CRYSTAL.md`;
- relevant Profile Crystal slice when needed;
- sync events or closeout notes when relevant;
- target budget;
- source/evidence handles.

Rules:

- Rewrite the whole session doc toward the lower watermark, commonly 50%.
- Preserve objective, active state, constraints, decisions, open loops, and
  active handles.
- Drop stale, superseded, redundant, and low-value detail.
- Keep contradictions visible.
- Do not silently write permanent memory, skills, or profile facts.
- Return revised Markdown plus compact status metadata.

Typical trigger:

```yaml
crystallizer:
  trigger:
    - session_doc_budget_percent >= 0.75
    - turns_since_medium_compact >= 24
    - quality_flags include drift_or_contradiction
  target_budget_percent: 0.50
  realtime_steering: false
```

## Gem Cutter

Gem Cutter is the governance worker. It should be quiet, diff-aware, and
mostly idle-focused.

Recommended inputs:

- changed profile/session hashes since the last tick;
- changed Crystal slices, not every full doc by default;
- sync queue events;
- conflict candidates;
- idle/activity state;
- evidence handles.

Rules:

- Exit quietly when nothing changed.
- Defer deep prune while the session is active unless safety or budget requires
  action.
- Reconcile only related sessions.
- Produce reviewable prune/sync/promote output.
- Do not delete raw transcript or evidence.
- Do not silently write permanent memory, facts, or skills.

Typical trigger:

```yaml
gem_cutter:
  cadence: 30m
  wake_if:
    - profile_or_session_crystal_hash_changed_since_last_tick
  no_op_if:
    - no_crystal_diff_since_last_tick
    - active_session_not_idle_enough_for_deep_prune
  idle_deep_prune_after_minutes: 60
```

## Minimal Setup Checklist

1. Create a Crystal state root with `profiles/<profile>/PROFILE_CRYSTAL.md`.
2. Create one `sessions/<session_id>/CRYSTAL.md` per active session.
3. Track `meta.json` with last processed turn, doc hash, token estimate,
   activity state, render state, and worker locks.
4. Run Facet after successful user-facing turns.
5. Run Crystallizer when the session doc crosses the upper watermark or a
   quality trigger fires.
6. Run Gem Cutter from a quiet scheduled tick.
7. Render only completed Crystal state into the next request.
8. Run this starter's read-only governance checks against a staging copy before
   checking live state.

## Prompt Contracts

The contracts below are safe starter versions. Adapt model names, schemas, and
routes for your runtime.

### Facet Contract

```text
You are Facet, Crystal's fast live maintainer. Merge the new turn into selected
CRYSTAL.md hot sections. Use only compact user/assistant text, deterministic
delta, sanitized tool summaries, and evidence handles. Return structured
section patches only. Do not paste raw tool output, logs, diffs, tables, or
secrets. Escalate if the update is too complex.
```

### Crystallizer Contract

```text
You are Crystallizer, Crystal's medium whole-doc compactor. Rewrite the session
CRYSTAL.md toward the target budget while preserving objective, active state,
constraints, decisions, open loops, and evidence handles. Drop stale and
redundant detail. Keep contradictions visible. Do not write memory.
```

### Gem Cutter Contract

```text
You are Gem Cutter, Crystal's governance worker. First reason from hashes,
manifests, diffs, sync events, and conflict candidates. If nothing changed,
exit quietly. If active, inspect or defer. If idle and relevant, prune, sync,
and produce reviewable promotion proposals with evidence handles. Do not steer
the live agent or silently mutate durable memory.
```
