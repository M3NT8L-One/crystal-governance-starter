# Crystal Context

## Current Objective

- Verify activity-aware rendering and Gem Cutter governance cadence.

## Current Working State

- Active sessions may render a broader Profile Crystal slice while work is moving.
- Idle sessions can accept tighter Gem Cutter pruning after a quiet window.

## Important Constraints

- Gem Cutter should exit quietly when Crystal state has not changed.
- Durable memory, skill, or profile promotion still requires review.

## Decisions and Rationale

- Use `active_fuller`, `steady`, `idle_clean`, and `checkpoint_only` as render states.
- Keep cumulative token accounting as telemetry rather than a primary behavior trigger.

## Active Open Loops

- Review medium/high governance findings before applying live-state changes.

## Relevant Files / Artifacts / Handles

- artifact: docs/gem-cutter-cadence.md
- artifact: policies/crystal-governance/scope-rules.yaml

## Recent Useful Context / Hot Delta

- Gem Cutter is scheduled, diff-aware, and mostly idle-focused.
