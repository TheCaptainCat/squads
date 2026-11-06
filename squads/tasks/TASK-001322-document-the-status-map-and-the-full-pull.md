---
id: TASK-1322
sequence_id: 1322
type: task
title: Document the status map and the full pull
status: Draft
parent: FEAT-1320
author: tech-lead
assignee: tech-writer
refs:
- MILE-1319:targets
- TASK-1321:depends-on
description: docs/sources.md, docs/stability.md and the 0.20.1 CHANGELOG entry
subentities:
- local_id: ST1
  title: Document the status map in docs/sources.md
  status: Todo
  assignee: tech-writer
  maps_to: US5
- local_id: ST2
  title: Document sq source pull --full and its cost
  status: Todo
  assignee: tech-writer
  maps_to: US6
- local_id: ST3
  title: Add the status map grammar to docs/stability.md
  status: Todo
  assignee: tech-writer
  maps_to: US1
- local_id: ST4
  title: Write the 0.20.1 CHANGELOG entry
  status: Todo
  assignee: tech-writer
  maps_to: US5
created_at: '2026-11-06T15:26:53Z'
updated_at: '2026-11-06T15:37:21Z'
priority: high
---
<!-- sq:body -->
The adopter-facing text for the opt-in status map and `sq source pull --full`. The authority is the "Delivered text owed" list of ADR-1274 section 15. Write from what TASK-1321's handback reports as delivered, including its exact message and report-line texts, and check each claim against the built command (`uv run sq` in a scratch squad nested under the scratchpad, never at `/tmp` root) before writing it.

## Scope

- `docs/sources.md`:
  - the key-table row for `maps.statuses`;
  - the status sides in each connector's "Open or closed" line;
  - the list form and its per-type resolution;
  - the precedence rule (first match wins, in the connector's order), beside the side rule of the other maps, which keep "sides that disagree set nothing";
  - the status line of the pull report;
  - the ownership section's "Everything else stays the squad's" paragraph: status is squad-owned by default, tracker-driven only on a mapped source, and a manual move warns but is never refused;
  - `sq source pull --full`, with its cost and its override of hand-set statuses;
  - the upgrade note: items pulled before the map move with `--full`, at their issue's next change, or on `show --refresh`.
- `docs/stability.md`: the `maps.statuses` grammar and the status sides.
- `CHANGELOG.md`: the 0.20.1 entry, describing what an adopter now does differently. It also says that a 0.20.0 build refuses a `sources.toml` that declares the map, so every operator who pulls needs 0.20.1.

## Constraints

- No sq item IDs and no repository or dev-process content in these docs.
- Present truth only, outside the CHANGELOG.
- No status prose.

## Acceptance

- Every docs bullet of US5 and the cost bullet of US6 hold.
- Each documented example loads and behaves as described on the built command.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1322 add-subtask "<title>"`; track with `sq task 1322 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Document the status map in docs/sources.md

<!-- sq:subtask:ST1:body -->
`docs/sources.md`: the `maps.statuses` key row, the status sides per connector, the list form and per-type resolution, the precedence rule, the status line of the pull report, the ownership paragraph (squad-owned by default; a manual move warns and is never refused), and the upgrade note.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Document sq source pull --full and its cost

<!-- sq:subtask:ST2:body -->
`docs/sources.md`: `sq source pull --full`. What it reads (every held, selected issue in detail), that it overrides hand-set statuses on a mapped source with no warning before it runs, so `--dry-run` is the preview and the report lists the moves made, and its cost: one detail read per held issue (comments and links, often several requests) on top of the listing, subject to the tracker's rate limits, so name one source.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Add the status map grammar to docs/stability.md

<!-- sq:subtask:ST3:body -->
`docs/stability.md`: the `maps.statuses` grammar (side, then tracker value, then an ordered list or a bare string) and the status sides per connector version, in their order.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Write the 0.20.1 CHANGELOG entry

<!-- sq:subtask:ST4:body -->
`CHANGELOG.md`: the 0.20.1 entry for the status map and `--full`. Write it from the adopter's seat: what they now declare, what a pull does with it, and that a 0.20.0 build refuses a document declaring the map. No migration is needed.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
