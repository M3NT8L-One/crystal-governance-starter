# Crystal Governance Starter

A sanitized starter kit for governing Crystal-style living context docs.

This repo is intentionally generic. It shows the pattern without shipping
private session transcripts, profile state, local paths, credentials, runtime
databases, or operator-specific rules.

## What this gives you

- **Profile crystal governance**: keep `PROFILE_CRYSTAL.md` small, scoped, and reviewable.
- **Session crystal governance**: keep per-session `CRYSTAL.md` docs useful without letting raw transcript noise become durable context.
- **Sync queue review**: route only high-value cross-session decisions, constraints, handles, handoffs, conflicts, and closeouts.
- **Gem Cutter cadence**: run quiet diff-aware pruning and reconciliation only when Crystal changed.
- **Pre-share validation**: scan this repo and generated reports for secrets, private paths, personal markers, and runtime-state leakage.

## Mental model

```text
Profile Crystal    = profile-wide continuity and cross-session decisions
Session Crystal    = local working context for one conversation
Sync queue         = structured proposals crossing session boundaries
Facet              = small per-turn hot merge
Crystallizer       = whole-doc compaction toward a lower watermark
Gem Cutter         = scheduled governance prune, sync, and conflict review
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
scripts/          Generic Crystal audit, triage, and card-draft scripts
cron/             Example quiet Gem Cutter governance cron
kanban/           Board pattern and card template for Crystal findings
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
```

You should see JSON and Markdown reports under `reports/demo/`. Review
generated reports/card drafts before sharing them. Absolute root/report paths
are redacted by default unless you pass `--include-absolute-paths`.

## Reproduce the pattern in your Crystal setup

1. Read `docs/setup-guide.md`.
2. Copy or adapt `skills/devops/crystal-governance-starter/SKILL.md` into your local skill library.
3. Copy or adapt the policy examples under `policies/crystal-governance/`.
4. Run the read-only checks against `examples/sample-crystal-home`.
5. Run the checks against a copied or staged Crystal state directory.
6. Only then point the checks at live Crystal state.
7. Route medium/high findings into a review board using `kanban/` templates.

## Using with real Crystal state

Do **not** point this at live Crystal state until you understand what it reads
and writes. The included audit scripts are read-only except for their output
directory.

```bash
python3 scripts/run_crystal_checks.py \
  --root /path/to/crystal-state \
  --out reports/local-crystal
```

Expected inspected shape:

```text
profiles/<profile>/PROFILE_CRYSTAL.md
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

1. A quiet cron or manual check runs a deterministic read-only audit.
2. If clean, it stays silent.
3. If findings exceed a threshold, a triage gate prints a short wake summary.
4. Triage creates or routes review cards.
5. Findings are fixed, verified, and closed with evidence.
6. Crystal docs stay useful because temporary reports, tool noise, and local
   runtime details are not promoted by accident.

## Validation

```bash
python3 tests/validate_repo.py
```

The validator exercises the sample Crystal checks and scans this repository
for obvious secret-like strings, private absolute paths, personal markers, and
generated-report path leaks.

See `docs/architecture.md` for the full setup.
