# Health And Reversible Registry Operations

This starter separates visibility from mutation:

- audit, health, triage, and Hermes plugin commands are read-only except for report output;
- registry reconciliation is a standalone script, dry-run by default;
- apply mode archives evidence and writes a restoration receipt instead of deleting it.

## Health states

Run the bundled state check:

```bash
python3 scripts/crystal_health_check.py \
  --root examples/sample-crystal-home \
  --profile default \
  --out reports/demo/crystal-health.json
```

Add `--source-root /path/to/deployed/source` to inspect Git cleanliness and
whether the source has at least one durability remote. Reports expose only dirty
and remote counts—not workspace filenames, paths, remote names, or URLs.

The status contract is:

| Status | Meaning | Examples |
|---|---|---|
| `HEALTHY` | No critical failures or maintenance degradations | readable aligned registry, no stale locks in the requested profile |
| `DEGRADED` | Service may continue, but maintenance debt is visible | registry drift, excluded or unclassified actors, retired entries, dirty source, missing remote |
| `UNHEALTHY` | Core state cannot be trusted | missing profile/session state, non-directory session root, unreadable registry, profile-scoped stale locks, colliding normalized session IDs |

`ok` is `true` for `HEALTHY` and `DEGRADED`; it is `false` for `UNHEALTHY`.
Lock checks are scoped to the selected profile, so another profile's lock cannot
contaminate its status. The triage gate wakes for either audit findings or
non-healthy status.

## Reconcile dry-run

Always start against a copied or staged state root:

```bash
python3 scripts/crystal_registry_reconcile.py \
  --root /path/to/staged-crystal-state \
  --profile default
```

Candidates can include:

- actors whose explicit or whole-field normalized type exactly matches an excluded auxiliary, subagent, background, cron, scheduler, Kanban, maintenance, evaluation, reviewer, internal, or scratch class;
- explicit retired registry entries;
- registry entries whose session directory is missing;
- orphan session directories not represented in the registry.

Protect a session from selection with a repeatable flag:

```bash
python3 scripts/crystal_registry_reconcile.py \
  --root /path/to/staged-crystal-state \
  --protect-session session-alpha
```

Dry-run does not create an archive, move directories, or rewrite the registry.

For a one-item repair, derive protection from the **complete dry-run candidate
set**, not only the orphans shown by a separate health command. Protect every
non-target candidate and rerun until the plan contains exactly one intended
target. Stale or invalid registered entries can otherwise broaden a seemingly
orphan-only apply.

## Apply and restore evidence

After reviewing a singleton plan, apply it explicitly:

```bash
python3 scripts/crystal_registry_reconcile.py \
  --root /path/to/staged-crystal-state \
  --profile default \
  --apply
```

Apply mode creates:

```text
profiles/<profile>/archive/registry-reconcile-<timestamp>/
  receipt.json
  registry.before.json
  registry.after.json
  sessions/<retired_session>/...
```

The receipt records candidate reasons, planned and completed directory moves,
registry counts, and restoration handles. It does not copy full registry entry
metadata into the plan or receipt. Distinct raw session IDs that normalize to
the same safe ID fail closed before planning.

After apply, verify one move, source/archive checksum equality, no unexpected
registry removal, the expected alignment-count delta, and no new missing
sessions. Meaningful or ambiguous state should be protected or explicitly
registered, not archived automatically.

Apply progresses through `planned`, `applying`, `ready`, and `complete` receipt
states. An I/O failure triggers best-effort reverse moves plus restoration from
`registry.before.json`; the receipt becomes `rolled_back` or `rollback_failed`.
A `rollback_failed` result requires manual restoration before another apply.
Restoration remains an operator-reviewed action: restore `registry.before.json`
and move archived session directories back only after verifying that the
destination is safe.

## Privacy boundary

Registry snapshots and archived sessions are private runtime artifacts. Receipts
and plans intentionally omit full registry entry metadata, while snapshots keep
the evidence needed for restoration. Do not commit or publish any of them. The
starter emits profile-relative paths and count-only source-health details so
routine reports do not leak local home-directory or source-tree paths.
