---
id: BUG-656
sequence_id: 656
type: bug
title: 'Crash-window: persistent .md-vs-index drift if killed mid-write'
status: InProgress
author: qa
severity: medium
refs:
- BUG-668
created_at: '2026-07-24T14:38:30Z'
updated_at: '2026-07-27T14:52:24Z'
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

Medium, unchanged on review. This bug's own window assumes the `.md` write already
completed before the kill lands — not data loss (frontmatter is the source of truth per
invariant #1, and `sq repair` always heals it), just a real, durable inconsistency, and this
project's own workflow routinely backgrounds and stops agent/subagent processes mid-task —
exactly the kind of interruption that can land a process in this window. A kill *during* the
`.md` write itself is a distinct, worse failure (the write is non-atomic, so it can leave a
truncated or empty file that `sq repair` cannot reconstruct from) — tracked separately as
BUG-668.

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
- [2026-07-27T13:53:01Z] Pierre Chat:
  - Unparked: fix all three. Architect settles the .md-vs-index ordering/atomicity model in an ADR first, then implement.
- [2026-07-27T14:06:13Z] Robert Architect:
  - ADR-663 §1-2 settles the ordering: markdown ahead or equal, index commits last, never the reverse (option 1 as filed inverts it into the lossy direction). Adds atomic tmp+replace for every squad-data .md write — the real worst case in the window is a truncated source-of-truth file.
- [2026-07-27T14:26:21Z] Olivia Lead:
  - Broken down: TASK-664 closes this (ADR-663 §1+§2 — atomic temp+fsync+replace for every squad-data .md write, plus the markdown-ahead ordering rule at every mutation core, including the `remove_item(purge=True)` violation).
  - The bug's own fix option 1 (rename the .md in only after the index commit) is NOT what lands: the ADR rejects it as the lossy direction — repair would revert the mutation or resurrect a removed item.
- [2026-07-27T14:42:02Z] Mara Tester:
  - Severity kept at Medium on review: this bug's window is specifically post-write/pre-index-commit (repairable drift, no data loss); the worse pre-write-completion case (truncation destroying the .md itself) is now tracked separately at BUG-668/high, ref'd.
<!-- sq:discussion:end -->
