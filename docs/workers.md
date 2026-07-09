# Worker Model And Setup

Crystal uses three worker roles. They are not extra chat participants. They
maintain the living context files that the live Crystal plugin can render into
the next model request.

This starter documents the contracts and governance checks. A live Crystal
runtime still needs a context plugin or sidecar that runs the workers.

## Worker Summary

| Worker | Tier | Main job | Normal trigger | Writes |
|---|---|---|---|---|
| Facet | fast/small | Prefer-recent hot-section merge; rolling Hot Delta | Every turn or two when there is meaningful delta | Session `CRYSTAL.md` |
| Crystallizer | medium | Whole-doc rewrite: pressure compact **or** earlier quality hygiene | Upper watermark, every ~12 turns, or quality hygiene after ~6 turns | Session `CRYSTAL.md` |
| Gem Cutter | strong/governance | Prune, reconcile, and sync after meaningful diffs | Quiet cadence, usually after idle | `PROFILE_CRYSTAL.md`, session docs, sync/review packet |

## Data Flow

```text
user-facing turn completes
  -> deterministic extraction finds handles, decisions, constraints, open loops
  -> Facet patches hot sections (prefer-recent supersede; Hot Delta = replace window)
  -> Crystallizer rewrites the session doc when pressure or hygiene is due
  -> Gem Cutter wakes on cadence, checks hashes, and usually exits quietly
  -> next request reads Profile Crystal + Session Crystal + hot tail
```

The main agent should see the latest completed Crystal state. It should not
wait on a long worker run unless the runtime chooses to make that a hard gate.

## Facet

Facet is the fast live maintainer. It keeps the session `CRYSTAL.md` useful
while work is active. Its failure mode is stacking near-duplicate bullets and
stale Hot Delta; design it to **supersede**, not archive.

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
- **Prefer-recent supersede:** newer bullets win over near-duplicate rephrases
  (do not keep five variants of the same objective).
- **Hot Delta is a rolling window:** full refresh from the newest turn lines,
  not an append-only archive of the session start.
- Keep tight section caps so Facet cannot quietly bloat a small doc.
- Skip model work if deterministic extraction finds no meaningful delta.
- Preserve evidence handles for important claims.
- **Scrub junk and secrets:** drop secret-like paths (for example SSH keys,
  auth/credential files, `.env`), system memory-review prompt echoes, and
  mangled/noise handles.
- Return compact structured status, not chat prose.
- Escalate to Crystallizer when the patch is too complex or quality debt piles up.

Typical trigger:

```yaml
facet:
  cadence: every_turn_or_two
  skip_if_no_meaningful_delta: true
  update_mode: hot_sections_only
  merge_mode: prefer_recent_supersede
  hot_delta_mode: replace_rolling_window
  raw_tool_payloads: unavailable
  tool_context: sanitized_summaries
  section_caps_example:
    current_objective: 6
    active_open_loops: 8
    handles: 16
    hot_delta: 6
```

## Crystallizer

Crystallizer is the medium whole-doc compactor. It has **two jobs**:

1. **Pressure compact** when the living doc fills the Crystal budget band
   (commonly rewrite from ~75% toward ~50% of the Crystal budget).
2. **Hygiene compact** earlier, while the doc is still small, when Facet has
   left quality debt (dupes, bloat near section caps, junk/secret handles,
   system-prompt echoes). Hygiene targets a **soft fraction of the current
   doc size** (for example ~0.62× current tokens), not a forced drop to the
   full 50% budget floor.

Recommended inputs:

- full current session `CRYSTAL.md`;
- relevant Profile Crystal slice when needed;
- sync events or closeout notes when relevant;
- target tokens and compact reason (`pressure` vs `hygiene`);
- source/evidence handles.

Rules:

- On **pressure**, rewrite toward the lower watermark (commonly 50% of Crystal budget).
- On **hygiene**, de-dupe aggressively, refresh Hot Delta to newest turns only,
  drop junk/secret handles, and collapse repeated objectives/open loops; do not
  grow the doc.
- Preserve objective, active state, constraints, decisions, open loops, and
  active handles.
- Drop stale, superseded, redundant, and low-value detail.
- Keep contradictions visible.
- Do not silently write permanent memory, skills, or profile facts.
- Return revised Markdown plus compact status metadata (`compact_reason` helps ops).

Typical trigger:

```yaml
crystallizer:
  trigger:
    - session_doc_budget_percent >= 0.75          # pressure
    - turns_since_medium_compact >= 12            # turn hygiene / compact cadence
    - quality hygiene after hygiene_min_turns (6):
        - dupe density / near-duplicate stacks
        - section counts near Facet caps with dups
        - junk or secret handles
        - system-prompt memory-review echoes
  pressure_target_budget_percent: 0.50
  hygiene_soft_target_fraction_of_current_doc: 0.62
  hygiene_min_turns: 6
  realtime_steering: false
```

Do **not** drop the upper watermark very low just to “clean earlier.” That
burns medium tokens on healthy small docs. Prefer Facet discipline plus
quality hygiene.

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
   activity state, render state, turns since medium compact, and worker locks.
4. Run Facet after successful user-facing turns (prefer-recent + Hot Delta replace).
5. Run Crystallizer on pressure **or** turn/quality hygiene triggers.
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
CRYSTAL.md hot sections. Prefer the newest accurate statement; supersede
near-duplicate rephrases instead of stacking them. Hot Delta must be a short
rolling window of the newest user/assistant lines (full refresh, not archive).
Use only compact user/assistant text, deterministic delta, sanitized tool
summaries, and evidence handles. Drop secret paths, system memory-review
prompts, and junk handles. Return structured section patches only. Do not paste
raw tool output, logs, diffs, tables, or secrets. Escalate if the update is too
complex.
```

### Crystallizer Contract

```text
You are Crystallizer, Crystal's medium whole-doc worker. Rewrite the session
CRYSTAL.md toward the target size. If this is a pressure pass, aim for the
configured lower watermark of the Crystal budget. If this is a hygiene pass,
aggressively de-dupe near-identical bullets, refresh Hot Delta to the newest
turns only, drop junk/secret handles, and collapse repeated objectives/open
loops without growing the doc. Preserve objective, active state, constraints,
decisions, open loops, and evidence handles. Drop stale and redundant detail.
Keep contradictions visible. Do not write memory.
```

### Gem Cutter Contract

```text
You are Gem Cutter, Crystal's governance worker. First reason from hashes,
manifests, diffs, sync events, and conflict candidates. If nothing changed,
exit quietly. If active, inspect or defer. If idle and relevant, prune, sync,
and produce reviewable promotion proposals with evidence handles. Do not steer
the live agent or silently mutate durable memory.
```
