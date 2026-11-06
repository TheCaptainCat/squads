---
id: TASK-1322
sequence_id: 1322
type: task
title: Document the status map and the full pull
status: InReview
parent: FEAT-1320
author: tech-lead
assignee: tech-writer
refs:
- MILE-1319:targets
- TASK-1321:depends-on
- REV-1323:addresses
description: docs/sources.md, docs/stability.md and the 0.20.1 CHANGELOG entry
subentities:
- local_id: ST1
  title: Document the status map in docs/sources.md
  status: Done
  assignee: tech-writer
  maps_to: US5
- local_id: ST2
  title: Document sq source pull --full and its cost
  status: Done
  assignee: tech-writer
  maps_to: US6
- local_id: ST3
  title: Add the status map grammar to docs/stability.md
  status: Done
  assignee: tech-writer
  maps_to: US1
- local_id: ST4
  title: Write the 0.20.1 CHANGELOG entry
  status: Done
  assignee: tech-writer
  maps_to: US5
created_at: '2026-11-06T15:26:53Z'
updated_at: '2026-11-06T16:31:04Z'
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
`docs/sources.md`: `sq source pull --full`. What it reads (every held, selected issue in detail), that it overrides hand-set statuses on a mapped source with no warning before it runs, so `--dry-run` is the preview and the report lists the moves made, and its cost: one detail read per held issue the source selects (comments and links, often several requests) on top of the listing, subject to the tracker's rate limits, so name one source.
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
- [2026-11-06T16:02:08Z] `tech-writer` Theo Writer:
  - @manager TASK-1322 is written, ST1 to ST4 Done. Not committed.
    
    **Files changed**
    - `docs/sources.md`: intro line on status; key-table row for `maps.statuses.<side>`; the ranked-sides note beside the peer-sides rule; the load-check paragraph; the `sq source list` table and `--json` gain the Status map column and `status_map`; `pull` synopsis gains `--full`; the `refreshed` counter, the report-lines list, "What a later pull does", the leave-the-selection table and the edited-comment and added-link notes; a new `### The full pull` (what it reads, writes only what differs, overrides hand-set statuses with `--dry-run` as the preview, its cost, name one source); a new `## The status map` (shape, sides per connector in order, ordered lists and per-type resolution, first match wins, fall-through, a side that maps but does not fit stops the walk, conflicts, when it applies, out-of-filter/gone, no transition rule, report lines, the manual-move warning, the load errors, and a section on declaring a map on a source that already has items, with the 0.20.1 requirement); the ownership section's "Status is the squad's, driven by a declared map" paragraph; `show --refresh` and `relink` apply the map; each connector's "Open or closed" line names its status sides; the probes section covers `maps.statuses.status` and `labels` keys.
    - `docs/stability.md`: a "The status map" grammar bullet under the spec documents; `--full` in the source command synopsis; `status_map` appended to the `sq source list --json` shape.
    - `CHANGELOG.md`: `## [0.20.1]` with Migration (no schema change; 0.20.0 refuses a document declaring the map, so every operator who pulls needs 0.20.1; how to move items pulled earlier), Added (the map, when it applies, load errors, `--full`) and Changed (the warning, the list column); compare link `v0.20.0...HEAD`.
    
    **How it was checked.** I drove the built `sq` against the loopback GitLab tracker on scratch squads nested under the scratchpad (since removed). The runs confirmed: creation at the mapped status; state before labels; fall-through; no-fit stops the walk and leaves the initial status; the label-conflict line; moved and would-move lines; a hand-set status held by a plain pull and reverted by `--full`; a second `--full` writes nothing; the warning on `status` and `update --status`, and none when the status does not change or the source has no map; `show --refresh` applying the map; every load error text; the `sources_loads` rule; and the `Status map` column. I also checked that released 0.20.0 refuses the document (`unknown key 'statuses' in 'maps'`) while its `sq list` still works. The Jira probe line comes from the test fixture and `_tracker_probes.py`. `sq check` is clean, and the docs meta tests pass.
    
    **Discrepancies between the code and ADR-1274 section 15 / FEAT-1320**
    1. The conflict line names the statuses found (`status left alone, its labels map to InProgress, Ready`). The ADR says the line names the values found. The docs follow the code. It matches the existing field-conflict line, so the ADR wording may be the thing to amend.
    2. `--dry-run` does not show the status a created item will get. The would-create line lists only the issues. US2 asks only that moves be shown, so this is not a breach, but a preview cannot show creation statuses.
    3. The warning also fires on `update --status`, which the ADR does not name (it names `sq <type> <n> status`). This is consistent with the feature, and the docs cover both.
- [2026-11-06T16:12:05Z] `tech-writer` Theo Writer:
  - @manager The REV-1323 docs fixes are done. Not committed. F2 is Fixed: CHANGELOG.md and docs/sources.md now say that 0.20.0 sq check exits 3 on a squad declaring the map, so CI that runs sq check needs 0.20.1 too, while item commands keep working. I verified this myself against ~/.local/bin/sq 0.20.0 on a nested scratch squad with -C: check exited 3, source list 1, list 0. F3 docs part: the full-pull wording in both files now says "every held issue the source still selects" and that out-of-filter and gone items are not moved. My part is noted on F3. F1 is not documented; I am waiting for the developer handback. sq check is clean.
- [2026-11-06T16:14:45Z] `tech-writer` Theo Writer:
  - @manager The REV-1323 F1 behaviour is now documented. Not committed. In docs/sources.md: the creation bullet of "When the map applies" covers a refused status; a new "A status the squad's checks refuse is left alone" paragraph covers error-level checks only, and says the rest of the refresh lands and the move is tried again when the map next applies; the report-lines block gains the refused line. The CHANGELOG 0.20.1 "When the map applies" bullet gains the same line, and says a created item starts at its initial status. I checked the line format against Compiler.refusal, move_status and create in _pull.py, and confirmed that ValidatorEngine.gate evaluates error-level members only. The example reason is the one from the reviewer's run.
- [2026-11-06T16:25:24Z] `tech-writer` Theo Writer:
  - @manager REV-1323 F6 is Fixed and not committed. docs/sources.md ("The squad's checks still apply to a mapped status") and the CHANGELOG 0.20.1 bullet now cover three cases: the mapped status passes and the item moves, the status is the cause and the line appears while the rest lands, or the item is refused at both and gets no status line, with its other changes gated like any write. I checked them against move_status and create with the F5 change in the tree. Case three does not claim the issue is always dropped, because a record-only change gets no drop line (see F5's scenario).
<!-- sq:discussion:end -->
