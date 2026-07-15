---
id: TASK-378
sequence_id: 378
type: task
title: 'Memory storage: entry model, file I/O, shared .index.jsonl generator'
status: Draft
parent: FEAT-315
author: tech-lead
description: Lightweight memory-entry model, per-file read/write, and the shared regenerated-whole
  .index.jsonl generator
subentities:
- local_id: ST1
  title: Write a memory as a slug-named .md; no global-counter id
  status: Todo
  story: US1
- local_id: ST2
  title: Shared whole-folder .index.jsonl generator with header stamp
  status: Todo
  story: US1
- local_id: ST3
  title: Forget removes the memory file (real deletion)
  status: Todo
  story: US4
- local_id: ST4
  title: Off-counter, outside .squads.json; repair leaves it alone
  status: Todo
  story: US5
created_at: '2026-07-15T07:46:25Z'
updated_at: '2026-07-15T07:46:45Z'
---
<!-- sq:body -->
Build the storage/model layer for agent memory, on the storage/id model fixed by the accepted decision (ADR-314): one slug-named markdown file per memory under `squads/agents/memory/<role>/`, off the global counter and outside `.squads.json`.

## Scope

- **Memory-entry model** — a lightweight model of its own (title/one-line summary, created_at, optional tags over a freeform body). NOT the `Item` model; no schema-version, status machine, sub-entities, refs, or workflow. No global-counter id is allocated.

- **File read/write** — write a memory as `<slug>.md` (slug derived from the fact) with light frontmatter over an agent-owned, marker-free body; read one back by slug; delete one by slug. Content `.md` files are the source of truth and stay greppable/hand-editable.

- **Shared `.index.jsonl` generator** — regenerated WHOLE from a folder's `.md` files on every add/forget/edit and on `sq sync` (never appended/hand-edited). JSON Lines, one object per entry line, entry schema `{slug, filename, description}` with description drawn from the content frontmatter. First line is a header record `{schema: "squads.index/1", generated: <stamp>}`; the `generated` field is a plain-text do-not-hand-edit stamp that honours the generated-file contract in JSON (no HTML marker possible in JSONL). The generator is **backend-neutral** (like the managed-region writer) and **common to both the memory and board features** — build it once here; the board storage task reuses it.

## Notes

- Slug is the stable, meaningful address; line position in the index is not load-bearing for memory recall.

- Merge behaviour is git's: independent adds are separate files (no conflict), same-memory edits are honest conflicts, deletes merge cleanly — no gitattribute dependency.

- `sq repair` must neither rebuild nor disturb anything here (memory is outside `.squads.json`).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 378 add-subtask "<title>"`; track with `sq task 378 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Write a memory as a slug-named .md; no global-counter id | US1 |
| ST2 | Todo |  | Shared whole-folder .index.jsonl generator with header stamp | US1 |
| ST3 | Todo |  | Forget removes the memory file (real deletion) | US4 |
| ST4 | Todo |  | Off-counter, outside .squads.json; repair leaves it alone | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Write a memory as a slug-named .md; no global-counter id

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As an agent, I can jot a small learned fact to my role's memory so it persists for future runs
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
`add` derives a slug from the fact and writes `squads/agents/memory/<role>/<slug>.md` with light frontmatter (summary, created_at) over a freeform body. No id is drawn from the global sequence counter. `--file` supplies a longer body in place of inline text (the file holds raw markdown only).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Shared whole-folder .index.jsonl generator with header stamp

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As an agent, I can jot a small learned fact to my role's memory so it persists for future runs
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Regenerate a folder's `.index.jsonl` whole from its `.md` files (never append/hand-edit) on add/forget/edit and `sq sync`. One JSON object per entry line, schema `{slug, filename, description}`; first line a header `{schema: "squads.index/1", generated: <stamp>}` where `generated` is the plain-text do-not-hand-edit stamp honouring the generated-file contract. Backend-neutral; reused by the board storage layer.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Forget removes the memory file (real deletion)

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US4 — As an agent or operator, I can prune a stale or wrong memory so the pool stays trustworthy
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
`forget <slug>` deletes the `<slug>.md` file (a real removal, history retained in git) and triggers index regeneration. A read never deletes.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Off-counter, outside .squads.json; repair leaves it alone

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
**Implements:** US5 — As a teammate, committed per-role memory arrives on checkout and merges cleanly across branches
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Memory lives entirely outside `.squads.json` and off the global counter. `sq repair` neither rebuilds nor disturbs memory files or their `.index.jsonl`. Committed (not gitignored) so a checkout inherits the pool; git resolves merges at the file level.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
