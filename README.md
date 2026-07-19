# Crystal Governance Starter

A sanitized starter kit for governing Crystal-style living context docs.

This repo is intentionally generic. It shows the pattern without shipping
private session transcripts, profile state, local paths, credentials, runtime
databases, or operator-specific rules.

Broader Hermes memory, skill, cron, and Kanban governance stays in the separate
[Hermes Governance Starter](https://github.com/M3NT8L-One/hermes-governance-starter).
This repository is dedicated to Crystal living-context governance and its
efficiency model.

## What this gives you

- **Profile crystal governance**: keep `PROFILE_CRYSTAL.md` small, scoped, and reviewable.
- **Session crystal governance**: keep per-session `CRYSTAL.md` docs useful without letting raw transcript noise become durable context.
- **Sync queue review**: route only high-value cross-session decisions, constraints, handles, handoffs, conflicts, and closeouts.
- **Front-door isolation**: enable Crystal only for positively classified human-facing sessions and keep background actors out of hooks and the complete context-engine lane.
- **Worker contracts**: document stateful Facet cadence, authoritative section operations, Crystallizer pressure/hygiene, and Gem Cutter spend gates.
- **Token economics**: estimate history, total-request, full-day net, and billable-equivalent savings without turning a boundary ratio into a daily claim.
- **Hermes plugin scaffold**: expose read-only audit, health, and triage checks through `hermes crystal-governance ...`.
- **Operational health**: classify registry/state/source checks as `HEALTHY`, `DEGRADED`, or `UNHEALTHY` with count-only source metadata.
- **Reversible registry reconciliation**: dry-run drift plans, collision refusal, explicit apply, rollback, timestamped archives, and restoration receipts.
- **Pre-share validation**: scan this repo and generated reports for secrets, private paths, personal markers, and runtime-state leakage.

## Mental model

```text
Profile Crystal    = profile-wide continuity and cross-session decisions
Session Crystal    = local working context for one conversation
Sync queue         = structured proposals crossing session boundaries
Facet              = stateful small-model refinement (6 turns / 12 tools / 2-turn cooldown)
Crystallizer       = pressure compact (~75%→~50%) or earlier quality hygiene
Gem Cutter         = changed + idle + size/quality-gated governance prune and sync
Governance         = scope, hygiene, redaction, review, and cleanup
```

The goal is not to remember everything.

The goal is controlled continuity: bounded living docs, clean handoffs,
reviewed cross-session promotion, and no accidental publication of private
runtime material.

## Repository layout

```text
docs/             Architecture, setup, and operating model
policies/         Example Crystal scope, redaction, and stale-pattern policies
scripts/          Generic audit, health, triage, and reconcile scripts
hermes_plugin/    Read-only Hermes companion plugin scaffold
cron/             Example quiet Gem Cutter governance cron
skills/           Starter skill for Crystal governance workflows
examples/         Tiny safe Crystal home and transcript fixtures
.github/          CI validation workflow
```

## Quick start

Requires Python 3.10 or newer. No third-party Python packages are required.

```bash
git clone https://github.com/M3NT8L-One/crystal-governance-starter.git
cd crystal-governance-starter
python3 scripts/run_crystal_checks.py --root examples/sample-crystal-home --out reports/demo
python3 scripts/crystal_registry_reconcile.py --root examples/sample-crystal-home
```

You should see JSON and Markdown reports under `reports/demo/`. Review
generated reports before sharing them. Absolute root/report paths are redacted
by default unless you pass `--include-absolute-paths`.

## Reproduce the pattern in your Crystal setup

1. Read `docs/setup-guide.md`.
2. Read `docs/workers.md` for Facet, Crystallizer, and Gem Cutter setup.
3. Read `docs/efficiency-and-savings.md` before quoting efficiency numbers.
4. Read `docs/operations-health-and-reconcile.md` for health and reversible registry maintenance.
5. Read `docs/hermes-plugin.md` if you want a native Hermes command surface.
6. Copy or adapt `skills/devops/crystal-governance-starter/SKILL.md` into your local skill library.
7. Copy or adapt the policy examples under `policies/crystal-governance/`.
8. Run the read-only checks against `examples/sample-crystal-home`.
9. Run the checks against a copied or staged Crystal state directory.
10. Only then point the checks at live Crystal state.

## Hermes plugin smoke path

From the repo root:

```bash
python3 scripts/link_hermes_plugin.py
hermes plugins enable crystal-governance
hermes crystal-governance status
hermes crystal-governance demo --out reports/plugin-demo
```

The plugin is read-only. It makes the starter easy to inspect from an agent,
but it does not replace the live `crystal-v0` context-engine plugin. The
standalone registry reconciliation script is dry-run by default and is not
exposed through the plugin.

## Potential token savings

Crystal mainly reduces repeated conversation-history input after a long session crosses a compression boundary. In one measured busy-session calibration, Crystal reduced the replaceable history slice by **94.1%** across three boundaries. That is not a daily savings figure: default Hermes also compresses, while the fixed system/tool prompt, early calls, maintenance workers, and provider cache semantics remain.

For two long, genuinely busy front-door sessions, the defensible planning estimate is:

- **about 30% net logical tokens saved** as a single planning number;
- **25–35%** as a normal busy-day range;
- potentially **35–45%** for very long, tool-heavy sessions;
- near **0%**, or slight overhead, for short sessions below the first boundary.

Logical-token savings are not automatically billable or dollar savings. See [`docs/efficiency-and-savings.md`](docs/efficiency-and-savings.md) for the four accounting layers, formulas, assumptions, telemetry, and cache caveats.

## Using with real Crystal state

Do **not** point this at live Crystal state until you understand what it reads
and writes. Audit, health, triage, and plugin commands are read-only except for
their report output. `crystal_registry_reconcile.py` is dry-run by default;
`--apply` moves selected state into an archive and updates the registry.

```bash
python3 scripts/run_crystal_checks.py \
  --root /path/to/crystal-state \
  --out reports/local-crystal
```

Expected inspected shape:

```text
profiles/<profile>/PROFILE_CRYSTAL.md
profiles/<profile>/registry.json
profiles/<profile>/sessions/<session_id>/CRYSTAL.md
profiles/<profile>/sessions/<session_id>/meta.json
profiles/<profile>/sync_queue.jsonl
```

## Safety defaults

This starter intentionally excludes:

- credentials, tokens, OAuth files, `.env`, API keys
- private profile content, private memory, and raw transcripts
- sessions, logs, local databases, caches, and runtime lock files
- local absolute paths and machine-specific handles
- operator-specific business rules or personal project names
- any authority to perform irreversible or external side effects

Governance should make living context safer and more maintainable. It should
not become an unreviewed promotion path for private context.

## Core pattern

1. A quiet cron or manual check runs deterministic read-only audit and health checks.
2. If audit is clean and health is `HEALTHY`, it stays silent.
3. If findings exceed a threshold or health degrades, triage prints a short wake summary.
4. Registry drift is dry-run planned before any change; apply archives evidence and writes a receipt.
5. Findings are fixed, verified, and closed with evidence.
6. Crystal docs stay useful because temporary reports, tool noise, and local
   runtime details are not promoted by accident.

## Validation

```bash
python3 tests/validate_repo.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The validator exercises the sample Crystal checks, verifies the current 6/12/2
scope and efficiency contracts, and scans this repository for obvious
secret-like strings, private absolute paths, personal markers, and
generated-report path leaks. The operation tests verify front-door actor
classification, health classification, quiet triage, dry-run safety, protected
sessions, archival movement, and restoration receipts.

See `docs/architecture.md` and `docs/workers.md` for the full setup.
