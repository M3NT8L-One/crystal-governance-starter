# Privacy And Redaction

Crystal docs often summarize active work. Treat them as sensitive by default.

## Never publish

- credentials, tokens, OAuth files, `.env`, API keys, private keys;
- private absolute paths or home-directory paths;
- raw session transcripts;
- local databases, caches, logs, locks, and runtime registry state;
- personal project names or organization-specific rules that are not part of
  the generic starter;
- unreviewed model outputs that mention private context.

## Safer handles

Prefer generic handles in examples:

```text
artifact: project/src/module.py
report: reports/crystal/latest
session: session-alpha#turn-4
```

Avoid:

```text
artifact: <home>/private/project/src/module.py
report: <runtime-home>/logs/agent.log
```

## Report redaction

The scripts redact absolute root/report paths by default. Keep that default for
anything that may be shared.

Use `--include-absolute-paths` only for local private debugging.
