---
id: TASK-1147
sequence_id: 1147
type: task
title: Keep line endings and sub-entity containers intact on write
status: Draft
author: tech-lead
priority: low
refs:
- MILE-1051:targets
- BUG-1141:fixes
- BUG-1144:fixes
description: CRLF survives read-modify-write; a restored container encloses its existing
  blocks
subentities:
- local_id: ST1
  title: Preserve CRLF line endings through read and write
  status: Todo
- local_id: ST2
  title: Enclose existing blocks when a container is restored
  status: Todo
created_at: '2026-10-25T19:56:57Z'
updated_at: '2026-10-25T19:57:16Z'
---
<!-- sq:body -->
## Goal

A write to an item file changes only the region it edits. Lines it does not touch keep their bytes, line endings included, and a restored sub-entity container holds every block of its kind. Two defects in the read-modify-write path, both python-dev.

## Read on release/0.17 HEAD (2026-10-25)

- `read_text` in `src/squads/_aio.py` reads with `Path.read_text(encoding="utf-8")`, which applies universal-newline translation, so a CRLF file is read as LF and written back as LF by any write, even a one-line comment. The write side already writes verbatim (`newline=""`). BUG-1141.
- `restore_regions` in `src/squads/_discussion.py` adds a missing container through `_restore_container` as an empty pair before the discussion, then restores only the blocks that are absent. A block that survived outside the lost container stays outside, the new container gets its own `## <heading>`, and the next `add-<kind>` lands inside the new pair. `sq check` reports nothing. BUG-1144.

## Gates

`uv run --all-extras pyright`, `ruff check .`, `ruff format --check .`, `pytest tests/meta tests/service tests/integration -n 4`; `~/.local/bin/sq check` clean. These paths sit on invariant 3 (marker-safe edits) and invariant 8 (markdown before the index): the subtasks change how text is read and placed, never the transaction order.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1147 add-subtask "<title>"`; track with `sq task 1147 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Preserve CRLF line endings through read and write

<!-- sq:subtask:ST1:body -->
Owner: python-dev. Fixes BUG-1141.

Read item files without newline translation (`newline=""` on the read, matching the write), and make sure frontmatter parsing, `_sections.find_markers` and section replacement accept `\r\n`. A write keeps the file's existing line endings on untouched lines; decide and state in the handoff what ending the inserted text uses (match the file's dominant ending is the expected answer).

Test: a table over write verbs (comment, body, status, add-subtask, sub-entity body) on a CRLF item file, asserting the CRLF count is preserved outside the edited region and that `sq check` and `sq repair` read the file cleanly. Include a mixed-ending file. The index and managed-region files go through the same reader; cover one of each.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Enclose existing blocks when a container is restored

<!-- sq:subtask:ST2:body -->
Owner: python-dev. Fixes BUG-1144.

When `restore_regions` restores a missing sub-entity container, the new pair encloses every existing block of that kind, in id order, under one `## <heading>`, and no duplicate heading is written. If the surviving blocks cannot be enclosed without moving prose that sits between them, refuse with one error line naming the item and the container instead of writing.

Where: `restore_regions` and `_restore_container` in `src/squads/_discussion.py`.

Test: the bug's repro (container pair removed, ST1 block left, then `subtask 1 body -m` and `add-subtask`) asserts one heading and both blocks inside the pair. Extend to the story and finding kinds, and to a container removed together with its only block. Consider whether `sq check` should report a block outside its container; if it should, add the rule here or say why not.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
