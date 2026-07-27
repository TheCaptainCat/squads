---
id: BUG-656
sequence_id: 656
type: bug
title: 'Crash-window: persistent .md-vs-index drift if killed mid-write'
status: Open
author: qa
created_at: '2026-07-24T14:38:30Z'
updated_at: '2026-07-24T14:40:13Z'
---
<!-- sq:body -->
## Symptom

An item's `.md` frontmatter shows the new status (e.g. `Done`) while `.squads.json` still
holds the old one — a *persistent* drift, present even with no other process touching the
board, only cleared by `sq repair`.

## Root cause

`.md` frontmatter and the index are written as two separate durability events, not one
atomic unit. In `ItemsMixin._set_status_core` (`src/squads/_services/_items.py:57-68`) the
`.md` write happens first, inside the transaction body:

```
await update_frontmatter(item_file(self.paths, item), item)   # _items.py:62
```

The index commit (`IndexStore._atomic_write`, a tmp-write + `os.replace`) only runs later,
after the yielded transaction body returns (`src/squads/_index/_store.py:303`). If the
process is killed (timeout, background-stop, OOM, container teardown) in the window between
those two lines, the `.md` write survives on disk but the index `os.replace` never runs.

## Repro

Monkeypatched the `update_frontmatter` call site (in-memory, in a disposable script — no
source file changed) so that immediately after the real frontmatter write completed, the
process sent itself `SIGKILL`. Ran it once against a throwaway squad's task (previously
`Ready`), setting status to `Done`. Result: process died (exit 137) right after the `.md`
write; the file showed `status: Done` while `.squads.json` still showed `Ready`; `sq check`
run afterward — with nothing else touching the board — reported the drift (persistent, not
self-healing like the check-time race); `sq repair` rebuilt the index and cleared it.

## Severity

Medium. Not data loss (frontmatter is the source of truth per invariant #1, and `sq repair`
always heals it), but it's a real, durable inconsistency, and this project's own workflow
routinely backgrounds and stops agent/subagent processes mid-task — exactly the kind of
interruption that can land a process in this window.

## Proposed fix

Make the `.md` write and the index commit all-or-nothing — options:
- Write the new `.md` to a temp path and rename it into place only *after* the index
  `os.replace` succeeds (or the reverse, with a clearly defined "which one is allowed to be
  ahead" direction, so a crash always leaves a describable, repair-safe state).
- Accept the current ordering as an intentional, bounded, always-repair-recoverable hazard
  and document it explicitly (e.g. in the `_store.py` module docstring) rather than change
  the write order.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T14:40:13Z] Pierre Chat:
  - Investigated + fix proposed; parked — not scheduled for 0.12.1.
<!-- sq:discussion:end -->
