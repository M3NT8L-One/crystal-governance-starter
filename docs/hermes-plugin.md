# Hermes Plugin Quickstart

This starter includes a lightweight Hermes companion plugin:

```text
hermes_plugin/crystal_governance/
  plugin.yaml
  __init__.py
```

The plugin is intentionally read-only. It does not replace the live
`crystal-v0` context engine. Instead, it gives an agent/operator a native
Hermes command surface for the governance layer:

```bash
hermes crystal-governance status
hermes crystal-governance demo
hermes crystal-governance check --root /path/to/crystal-state --out reports/local
hermes crystal-governance health --root /path/to/crystal-state --out reports/local/crystal-health.json
hermes crystal-governance triage --report-dir reports/local
```

## Relationship To Crystal

Use this split:

```text
crystal-v0 plugin
  live context injection, post-turn session doc updates, context.engine: crystal

crystal-governance plugin
  read-only governance audit, health checks, and triage summaries
```

That keeps the public starter safe: people can see the governance behavior
without granting it authority to mutate memory, profile docs, skills, or live
runtime state.

The companion plugin is not evidence that a live context-engine wrapper enforces
unbound-copy or background-review exclusion, or that wrapper and built-in
compressor state stay synchronized. Those implementation contracts and their
required stateful tests are described in `docs/architecture.md`; validate them in
the actual live integration before enabling it.

## Link Into Hermes

From this repository root:

```bash
mkdir -p "$HOME/.hermes/plugins"
ln -s "$PWD/hermes_plugin/crystal_governance" "$HOME/.hermes/plugins/crystal-governance"
hermes plugins list
hermes plugins enable crystal-governance
```

If your Hermes install uses a different plugin directory, symlink
`hermes_plugin/crystal_governance` into that directory instead.

The plugin locates this starter repo from the symlink target. If you copy only
the plugin folder without the rest of the repo, set:

```bash
export CRYSTAL_GOVERNANCE_STARTER_ROOT=/path/to/crystal-governance-starter
```

## Smoke Test

After enabling the plugin:

```bash
hermes crystal-governance status
hermes crystal-governance demo --out reports/plugin-demo
```

Expected behavior:

- `status` prints the repo root, sample root, script directory, and commands.
- `demo` runs the sample audit and health check, writes reports for the clean sample,
  and exits successfully.
- `health` reports `HEALTHY`, `DEGRADED`, or `UNHEALTHY` without changing state.

## Agent-Facing Prompt

Use this instruction when attaching the plugin to an agent:

```text
When asked to inspect Crystal governance, use `hermes crystal-governance status`
first. Use `demo` to understand the sample behavior. Use `check --root <state>`
for the audit and `health --root <state>` for registry/state health. Treat
outputs as review evidence; do not mutate Crystal state, memory, skills, or
profile docs unless the operator explicitly asks for a separate fix.
```
