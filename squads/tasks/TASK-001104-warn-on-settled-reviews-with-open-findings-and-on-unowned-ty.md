---
id: TASK-1104
sequence_id: 1104
type: task
title: Warn on settled reviews with open findings and on unowned types
status: Draft
parent: FEAT-1101
author: tech-lead
assignee: python-dev
refs:
- REV-1099:addresses
- TASK-1105:depends-on
description: New sq check rules for F10 and F3 from REV-1099.
subentities:
- local_id: ST1
  title: Add subentities_settled_with_parent and select it on the bundled review type
  status: Todo
  story: US5
- local_id: ST2
  title: Add type_has_live_author, naming the catalog role to activate
  status: Todo
  story: US5
- local_id: ST3
  title: Give every outstanding finding on this repo's settled reviews a real disposition
  status: Todo
  assignee: reviewer
  story: US5
- local_id: ST4
  title: Write the 0.17.0 CHANGELOG entries for the two new check rules
  status: Todo
  assignee: tech-writer
  story: US5
created_at: '2026-10-24T10:04:02Z'
updated_at: '2026-10-24T10:08:29Z'
---
<!-- sq:body -->
## Goal

Two new `sq check` rules from REV-1099: F10 (a settled review that still holds an outstanding finding) and F3 (a type with open items that no active role authors). Then bring this repository's own squad back to a clean `sq check` under them.

## Approach

- **F10: a per-item validator, `subentities_settled_with_parent`** (`src/squads/_services/_validators.py`, `src/squads/_workflow/_models.py`). It reports an item whose status role is `settled` while one of its sub-entities rests in a status whose role is not settled. It names the count and the local ids. Both sides key on the status role, never on `Approved` or `Open`, as ADR-1102 requires. `Noted` and `Deferred` are therefore not outstanding, and `Fixed` (role `active`) is. Warn level. Register it in `VALIDATOR_NAMES`, `CATALOG` and `SUBENTITY_VALIDATOR_NAMES`, and add a default level.
  - Selection: the bundled spec selects it on `[items.review] validators` in `src/squads/_specs/workflow.toml`, not in the `work` category bundle. Measured on this repository's squad, the generic rule in the bundle would also fire on 46 Done features and 35 Done tasks with Todo stories or subtasks, and the feature's acceptance criteria say check stays clean otherwise. A project can add it to any other type.
  - This repository's `squads/.overrides/workflow.toml` replaces `[items.review] validators` whole with no splat, so it would silently drop the bundled selection. Open that list with `"$(*items.review.validators)"`, as `[items.epic]` already does. The CHANGELOG has to tell adopters the same.
  - No transition gate. ADR-1102 says review approval is not gated.
- **F3: a squad-global validator, `type_has_live_author`** (`src/squads/_services/_validators.py`, `SQUAD_GLOBAL_VALIDATOR_NAMES`, `ALWAYS_ON_SQUAD_GLOBAL_NAMES`, `DEFAULT_SQUAD_GLOBAL_LEVEL` at warn). For each non-roster type holding at least one item at a non-settled status: intersect `in_lane_owner` (`src/squads/_interactions/_role_guidance.py`) with the live roster's slugs. It adds a slug-addressed subject whether or not that role is live, so the intersection is what counts. When it is empty, report the type. Name the playbook's in-lane authors that exist in the catalog but are not live, with the remedy `sq role activate <slug>`. A capability-addressed author (`*dev`) points at adding a developer instead. A type no playbook guide authors at all is reported with no role to name. Always-on, like `playbook_guide_role_live`: the shipped `[squad] validators` list is empty, so a selectable rule would never reach an adopter. Open items only: a type whose items are all settled (old reviews after the reviewer was retired on purpose) is not debt.
- **This repository's corpus** (ST3). With the rule above, 106 Approved reviews here hold findings that are not settled: 69 with only `Fixed`, 23 with `Open`, 14 with both. `sq check` must be clean in this repo, so each one needs a real disposition per finding (Verified, Noted, Deferred with `--deferred-to`, WontFix with reasoning), not a bulk close. That needs `Noted`/`Deferred`, hence the depends-on edge to TASK-1105. A JSONL file through `sq import -` keeps it to one transaction per batch. Mechanical bulk changes need the operator's go-ahead.

## Tests

Service-level plus a CLI smoke for each rule. Run `tests/meta` (registries, the import-edge table, the mutable-state guard for any new module constant), `tests/integration` and `tests/cli`, because a bundled spec changes. Falsify each test.

- F10: table over parent status role (settled done, settled retired, not settled) × sub-entity status role (attention, active, pending, done, retired, the ADR's deferred role). It warns only for settled with not settled. Also: a type not selecting the rule stays silent, a project override with a custom status name of a settled role fires, and the repo override with the splat keeps it.
- F3: table over roster states: sole author live (silent), sole author archived with an open item (warns, names the slug), archived author and only settled items (silent), two authors with one live (silent), a `*dev` author with no developer (warns, says add a developer), a custom type with no playbook author (warns, no role named). A CLI smoke reproduces the review's steps: create a review, archive `reviewer`, `sq check`.

## Generated output

The bundled `workflow.toml` changes, so regenerate any golden pinning `sq workflow` / `sq check --json` output and the template manifest if the spec is in it.

## CHANGELOG substance (0.17.0)

The developer reports and the tech writer writes the entry (ST4).

- Added: `sq check` warns when a settled review (bundled: Approved) still holds a finding that is not settled (Open or Fixed). The rule is `subentities_settled_with_parent`, selected on the review type, and any type can select it. If your override replaces `[items.review] validators`, open the list with `"$(*items.review.validators)"` to keep it.
- Added: `sq check` warns when a type has open items but no active role authors it, naming the role to activate.
- No migration.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1104 add-subtask "<title>"`; track with `sq task 1104 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add subentities_settled_with_parent and select it on the bundled review type

<!-- sq:subtask:ST1:body -->
Closes REV-1099 F10. A per-item warn rule: an item at a settled status holding a sub-entity at a status that is not settled, keyed on status roles only (ADR-1102), so Noted and Deferred count as settled and Fixed does not. Register it in the name sets and the catalog. Select it on `[items.review] validators` in the bundled spec, and open this repo's `[items.review]` override with the splat so it keeps the selection. Table over parent role × sub-entity role.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add type_has_live_author, naming the catalog role to activate

<!-- sq:subtask:ST2:body -->
Closes REV-1099 F3. An always-on squad-global warn rule: a non-roster type with at least one open item where no live role is an in-lane author (intersect `in_lane_owner` with the live roster). The message names the catalog author to activate (`sq role activate <slug>`), or says to add a developer for a `*dev` lane. A CLI smoke follows the review's reproduction.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Give every outstanding finding on this repo's settled reviews a real disposition

<!-- sq:subtask:ST3:body -->
Keeps `sq check` clean in this repository once REV-1099 F10's rule lands. 106 Approved reviews here hold findings that are not settled (69 Fixed only, 23 Open, 14 both, measured on 2026-10-24). Give each finding Verified, Noted, Deferred with `--deferred-to`, or WontFix with reasoning, never a bulk close. Batches can go through `sq import -`. Needs TASK-1105 (Noted, Deferred) merged first, and the operator's go-ahead for any bulk change.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Write the 0.17.0 CHANGELOG entries for the two new check rules

<!-- sq:subtask:ST4:body -->
Covers REV-1099 F10 and F3 in the CHANGELOG, from this task's CHANGELOG substance. Include the note that an override replacing `[items.review] validators` must open with the splat to keep the new rule.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
