# Crystal Context

## Current Objective

- Prove the public Crystal governance starter can audit a small profile domain.

## Current Working State

- Profile Crystal and per-session docs use separate files.
- Sync queue entries are structured JSONL events.

## Important Constraints

- Do not publish credentials, raw transcripts, private paths, or local runtime state.
- Do not collapse unrelated sessions into one shared mutable document.

## Decisions and Rationale

- Keep one `CRYSTAL.md` per active session so local working context stays local.
- Route profile-wide context through `PROFILE_CRYSTAL.md` after review.

## Active Open Loops

- Run `python3 tests/validate_repo.py` before sharing changes.

## Relevant Files / Artifacts / Handles

- artifact: docs/profile-session-scope.md
- report: reports/crystal-governance

## Recent Useful Context / Hot Delta

- Facet should use sanitized tool summaries instead of raw tool payloads.
