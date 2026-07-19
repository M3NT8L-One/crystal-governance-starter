# Privacy And Redaction

Crystal docs often summarize active work. Treat them as sensitive by default.

## Never publish

- credentials, tokens, OAuth files, `.env`, API keys, private keys;
- private absolute paths or home-directory paths;
- raw session transcripts;
- local databases, caches, logs, locks, runtime registry state, reconciliation
  receipts, registry snapshots, and archived sessions;
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

## Apply redaction at every write boundary

Redacting model input is not enough. Use the same reviewed redaction helper for:

- deterministic turn extraction before merge;
- every Facet operation bullet before accept/write;
- Crystallizer and Gem Cutter output before replacement;
- quality evidence and generated reports.

Drop raw blobs and secret-only leftovers such as a bare redaction marker. Keep
mixed useful text with the sensitive value replaced. If a `replace` or `merge`
operation contains no clean useful bullets after redaction, reject the whole
operation so secret-only output cannot erase prior valid state. A `clear`
operation instead requires explicit evidence that the snapshot section is empty
or completed.

Test plain credential assignments, embedded secrets in otherwise useful text,
durable-section merges, private paths, and raw payload-shaped blobs. A narrow
check for one token prefix does not establish a safe living-document boundary.
