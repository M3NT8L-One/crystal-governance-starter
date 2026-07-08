# Profile And Session Scope

## Rule

One profile owns profile-wide continuity. Each session owns its local working
context.

```text
PROFILE_CRYSTAL.md          stable profile-wide context
sessions/<id>/CRYSTAL.md    local session context
sync_queue.jsonl            proposed cross-session deltas
```

Do not make every live session write a single shared mutable `CRYSTAL.md`.

## What belongs in Profile Crystal

- stable profile-wide decisions;
- durable constraints;
- reusable handoff state;
- active handles that multiple sessions need;
- conflict summaries that need review.

## What belongs in Session Crystal

- current state for one conversation;
- session-local decisions and constraints;
- open loops;
- compact evidence handles;
- latest useful checkpoint.

## What belongs in the sync queue

Use structured JSONL events for cross-session movement:

```json
{
  "event_id": "evt-example-001",
  "profile": "default",
  "source_session": "session-alpha",
  "kind": "decision",
  "topic_keys": ["crystal", "scope"],
  "summary": "Only user-facing profile sessions write Crystal state by default.",
  "evidence": ["session-alpha#turn-4"],
  "targeting": "profile_hub",
  "confidence": 0.91,
  "created_at": "2026-01-01T00:00:00Z"
}
```

Good event kinds:

| Kind | Use |
|---|---|
| `decision` | durable project or profile decision |
| `constraint` | safety or design boundary |
| `active_handle` | file, branch, artifact, or report handle |
| `handoff` | another session should know this state |
| `conflict` | sessions disagree or a claim appears stale |
| `closeout` | concise outcome after work ends |

## Import policy

Import a sync event into another session only when at least one is true:

- same project or topic key;
- same active artifact handle;
- profile-wide decision or constraint;
- explicit handoff;
- conflict review;
- operator request;
- Gem Cutter marks the item as relevant.

Everything else stays local.
