---
id: TASK-946
sequence_id: 946
type: task
title: Document the memory and board read views and the new --json shapes
status: Draft
parent: FEAT-690
author: tech-lead
assignee: tech-writer
refs:
- REV-943:fixes
- TASK-944:depends-on
- TASK-945:depends-on
subentities:
- local_id: ST1
  title: Name the new json shapes and the partial-listing contract
  status: Todo
- local_id: ST2
  title: Write the 0.15.0 changelog entry for the memory and board views
  status: Todo
- local_id: ST3
  title: Say what each client shows in the README descriptions
  status: Todo
created_at: '2026-09-14T13:55:18Z'
updated_at: '2026-09-14T13:58:37Z'
---
<!-- sq:body -->
Nothing adopter-facing records that either client can now show a role's memory notebook or the
team board, that `sq memory <role> show <slug> --json` exists, that `memory list --json` carries
`created_at`, or how a `--json` reader learns a listing is partial. None of it was in any
implementation task's acceptance criteria, which is why it reached the end of the build
unnoticed.

This is written once, after both implementation tasks land, because the `--json` degradation
contract it describes is being changed by them. The two handbacks are the source for what a
reader now sees; do not describe the shape from the code alone.

## What is missing, and where it goes

- **`docs/stability.md`** enumerates the supported `--json` shapes and, for memory and the
  board, names three: `board list --json`, `memory list --json`, `memory search --json`.
  `memory show --json` is absent, so it currently ships outside the contract that section
  defines. The section also closes by telling adopters every shape above is covered by a
  regression test — the covering tests are on the Python task, so the claim will be true.
  The partial-listing signal is part of the same contract and belongs in the same place: it is
  what a reader keys off to know its listing is incomplete.
- **`CHANGELOG.md`, `## [0.15.0]`** carries nothing about either client's memory or board read
  views, nor the CLI additions, against the standing rule that an entry lands with the work
  rather than being batched at release.
- **`README.md`**'s one-line descriptions of `sq ui` ("the item tree, filters, full-text search,
  and a reader pane for any item") and of the VS Code extension ("work items, records, and
  roster as activity-bar trees") mention neither memory nor the board.

## How to work it

- Adopter-facing prose throughout: what the tool does for the reader, and why they would reach
  for it. No item ids, no repo or build-process content, no narration of how the work was
  sequenced or reviewed.
- `created_at` on `memory list --json` is a field addition, which the stability document does
  say is allowed between majors — name it anyway, because the extension's entire staleness
  signal depends on it and a reader building against that surface needs to know it is there.
- Prefer describing the degraded-read behaviour as something the reader benefits from (a short
  listing says it is short) over describing the mechanism that carries it.
- Leave `sq check` clean before handing back.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 946 add-subtask "<title>"`; track with `sq task 946 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Name the new json shapes and the partial-listing contract

<!-- sq:subtask:ST1:body -->
`docs/stability.md` is where an adopter learns which machine-readable shapes they may build
against. Its memory-and-board line names three, and the newly shipped one is not among them.

Done when:

- `sq memory <role> show <slug> --json` is named in the `--json` enumeration alongside the
  shapes already there, described the way its neighbours are.
- `created_at` on `memory list --json` is named. It is a field addition, which that document
  already permits between majors, but it is the field an age or staleness display depends on, so
  a reader building against the surface should not have to discover it.
- The way a `--json` reader learns that a listing is partial is described once, as a property of
  both listing surfaces rather than as a quirk of either — taken from the implementation
  handbacks, not read off the code.
- Nothing in the section claims coverage that does not exist: the regression tests for these
  shapes land on the Python task, so check they are there before the claim stands over them.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Write the 0.15.0 changelog entry for the memory and board views

<!-- sq:subtask:ST2:body -->
`CHANGELOG.md`'s `## [0.15.0]` section carries the view-tags work and nothing about the memory
and board read views in either client, or the CLI additions behind them.

Done when:

- The section describes what an adopter can now do: see each role's and operator's memory
  notebook, and the team board, from the terminal browser and from the editor extension —
  written the way the entries around it are written, leading with the capability rather than the
  surface that carries it.
- The `--json` additions are covered in the same entry or beside it: the new `memory show`
  shape, `created_at` on `memory list`, and the partial-listing signal both listings now give a
  reader.
- No item ids, no reviewer or build-process narration, no sequencing story — the entry describes
  the release, not how it was produced.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Say what each client shows in the README descriptions

<!-- sq:subtask:ST3:body -->
`README.md` introduces both clients in one line each. `sq ui` reads "the item tree, filters,
full-text search, and a reader pane for any item"; the extension reads "work items, records, and
roster as activity-bar trees". Neither mentions the memory notebooks or the board, which are now
part of what each shows.

Done when:

- Both descriptions name the memory and board views, in the same register and roughly the same
  length as the lines they replace — this is an introduction, not a feature list.
- The read-only framing the extension line already carries is preserved.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
