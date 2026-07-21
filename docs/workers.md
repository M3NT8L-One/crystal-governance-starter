# Worker Model And Setup

Crystal uses three worker roles. They are not extra chat participants. They
maintain the living context files that the live Crystal plugin can render into
the next model request.

This starter documents the contracts and governance checks. A live Crystal
runtime still needs a context plugin or sidecar that runs the workers.

## Worker Summary

| Worker | Tier | Main job | Normal trigger | Writes |
|---|---|---|---|---|
| Facet | fast/small | Authoritative hot-section operations; prefer-recent working state | 6 meaningful turns since attempt, 12 accumulated tools since success, or lifecycle/quality reason; 2-turn cooldown | Session `CRYSTAL.md` |
| Crystallizer | medium | Whole-doc rewrite: pressure compact **or** earlier quality hygiene | Upper watermark, every ~12 turns, or quality hygiene after ~6 turns | Session `CRYSTAL.md` |
| Gem Cutter | strong/governance | Prune, reconcile, and sync after meaningful diffs | Quiet cadence; idle plus diff/pressure gate | `PROFILE_CRYSTAL.md`, session docs, sync/review packet |

## Data Flow

```text
user-facing turn completes
  -> deterministic extraction finds handles, decisions, constraints, open loops
  -> deterministic tick merges bounded, redacted state
  -> Facet runs only when cadence, tool pressure, lifecycle, or quality is due
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

Facet receives a frozen decision snapshot. Cadence means meaningful turns
**since the last attempt**. Tool pressure means accumulated results **since the
last successful attempt**. Neither is a lifetime sticky trigger.

Rules:

- Return authoritative operations `{section, action, bullets}` rather than an
  unconstrained replacement document.
- Snapshot sections—objective, working state, open loops, and Hot Delta—allow
  `replace` or `clear`.
- Use `clear` only with explicit evidence that the snapshot lane is empty or
  completed; omitted output is not a clear instruction.
- Durable sections—constraints, decisions, and handles—allow `merge` only.
- Reject unknown sections and stale/drop-zone writes.
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
- A valid idempotent operation is success even when bytes do not change. Empty
  or invalid operations are failure and must retain pending reasons/tool pressure.
- If another turn queues work while Facet is running, clear only the decision's
  reasons and subtract only its represented tool count.

Typical trigger:

```yaml
facet:
  meaningful_turns_since_attempt: 6
  accumulated_tool_results_since_success: 12
  cooldown_turns: 2
  also_due_on: [lifecycle_transition, quality_reason]
  skip_if_no_meaningful_delta: true
  output_schema: authoritative_operations
  snapshot_actions: [replace, clear]
  durable_actions: [merge]
  unknown_section_action: reject
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
- When changed and idle, spend a model call only if the document exceeds the
  idle target or quality flags are present. A changed, clean, small document is
  a zero-model `idle_clean_noop`.
- Reconcile only related sessions.
- Order profile-hub inputs by `last_activity_at`, use the newest session as the
  volatile head, and require independent support from two distinct recent
  session IDs for a durable historical claim absent from that head.
- Age sync events against newest activity and classify volatility with whole
  tokens or narrow phrases, not substring matches.
- Produce reviewable prune/sync/promote output; do not run profile-hub sync from
  a promised read-only audit.
- Do not delete raw transcript or evidence.
- Do not silently write permanent memory, facts, or skills.
- Seal the document hash after rewrite and again after profile/hub sync so the
  next unchanged tick is a true `noop_unchanged`.

Typical trigger:

```yaml
gem_cutter:
  cadence: 30m
  wake_if:
    - profile_or_session_crystal_hash_changed_since_last_tick
  no_op_if:
    - no_crystal_diff_since_last_tick
    - active_session_not_idle_enough_for_deep_prune
    - changed_but_clean_and_under_idle_target
  model_work_if:
    - changed_and_idle_and_over_idle_target
    - changed_and_idle_and_quality_flags_present
  idle_deep_prune_after_minutes: 60
```

## Minimal Setup Checklist

1. Create a Crystal state root with `profiles/<profile>/PROFILE_CRYSTAL.md`.
2. Create one `sessions/<session_id>/CRYSTAL.md` per active session.
3. Track `meta.json` with last processed turn, `last_activity_at`, doc hash,
   token estimate, activity state, render state, turns since medium compact, and
   worker locks.
4. Run deterministic extraction after meaningful user-facing turns; queue Facet
   through stateful 6/12/2 cadence, accumulated tools, lifecycle, and quality.
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
You are Facet, Crystal's fast live maintainer. Return authoritative operations
with section, action, and bullets. Use replace/clear only for snapshot sections
(objective, working state, open loops, Hot Delta) and merge only for durable
sections (constraints, decisions, handles). Prefer the newest accurate state;
supersede near-duplicate rephrases instead of stacking them. Use only compact
user/assistant text, deterministic delta, sanitized tool summaries, and evidence
handles. Never return raw tool output, logs, diffs, tables, secrets, unknown
sections, or stale/drop-zone writes. Omit a section when evidence is
insufficient. Escalate if the update is too complex.
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
