---
id: TASK-1104
sequence_id: 1104
type: task
title: Warn on settled reviews with open findings and on unowned types
status: InProgress
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
  status: InProgress
  story: US5
- local_id: ST2
  title: Add type_has_live_author, naming the catalog role to activate
  status: Done
  story: US5
- local_id: ST3
  title: Give every outstanding finding on this repo's settled reviews a real disposition
  status: Todo
  assignee: reviewer
  story: US5
- local_id: ST4
  title: Write the 0.17.0 CHANGELOG entries for the two new check rules
  status: Done
  assignee: tech-writer
  story: US5
- local_id: ST5
  title: Make type_has_live_author selectable and selected by default
  status: Done
  assignee: python-dev
  story: US5
- local_id: ST6
  title: Document type_has_live_author as on by default and deselectable
  status: Done
  assignee: tech-writer
  story: US5
created_at: '2026-10-24T10:04:02Z'
updated_at: '2026-10-25T00:58:23Z'
---
<!-- sq:body -->
## Goal

Two new `sq check` rules from REV-1099: F10 (a settled review that still holds an outstanding finding) and F3 (a type with open items that no active role authors). Then bring this repository's own squad back to a clean `sq check` under them.

## Approach

- **F10: a per-item validator, `subentities_settled_with_parent`** (`src/squads/_services/_validators.py`, `src/squads/_workflow/_models.py`). It reports an item whose status role is `settled` while one of its sub-entities rests in a status whose role is not settled. It names the count and the local ids. Both sides key on the status role, never on `Approved` or `Open`, as ADR-1102 requires. `Noted` and `Deferred` are therefore not outstanding, and `Fixed` (role `active`) is. Warn level. Register it in `CATALOG` (`_validators.py`) and in `VALIDATOR_NAMES` and `SUBENTITY_VALIDATOR_NAMES` (`src/squads/_workflow/_models.py`), and add a default level. An Approved review holding a Fixed finding is reported (op-pierre ruling on FEAT-1101).
  - Selection: the bundled spec selects it on `[items.review] validators` in `src/squads/_specs/workflow.toml`, not in the `work` category bundle. Measured on this repository's squad, the generic rule in the bundle would also fire on 46 Done features and 35 Done tasks with Todo stories or subtasks, and the feature's acceptance criteria say check stays clean otherwise. A project can add it to any other type.
  - This repository's `squads/.overrides/workflow.toml` replaces `[items.review] validators` whole with no splat, so it would silently drop the bundled selection. Open that list with `"$(*items.review.validators)"`, as `[items.epic]` already does. The CHANGELOG has to tell adopters the same.
  - No transition gate. ADR-1102 says review approval is not gated.
- **F3: a squad-global validator, `type_has_live_author`** (the rule in `src/squads/_services/_validators.py`; `SQUAD_GLOBAL_VALIDATOR_NAMES`, `SELECTABLE_SQUAD_GLOBAL_NAMES` and `DEFAULT_SQUAD_GLOBAL_LEVEL` at warn in `src/squads/_workflow/_models.py`). For each non-roster type holding at least one item at a non-settled status: intersect `in_lane_owner` (`src/squads/_interactions/_role_guidance.py`) with the live roster's slugs. It adds a slug-addressed subject whether or not that role is live, so the intersection is what counts. When it is empty, report the type. Name the playbook's in-lane authors that exist in the catalog but are not live, with the remedy `sq role activate <slug>`. A capability-addressed author (`*dev`) points at adding a developer instead. A type no playbook guide authors at all is reported with no role to name. Selectable and on by default: the bundled `[squad] validators` selects it, so it reaches every adopter, and a squad turns it off by leaving it out of its own `[squad] validators` (a squad whose types people write, or a `minimal`/`core` squad that leaves those types to the default role). `@error` raises it. An override that replaces `[squad] validators` keeps it by opening with `"$(*squad.validators)"`. Open items only: a type whose items are all settled (old reviews after the reviewer was retired on purpose) is not debt.
- **This repository's corpus** (ST3). With the rule above, 106 Approved reviews here hold findings that are not settled: 69 with only `Fixed`, 23 with `Open`, 14 with both. `sq check` must be clean in this repo, so each one needs a real disposition per finding (Verified, Noted, Deferred with `--deferred-to`, WontFix with reasoning), not a bulk close. That needs `Noted`/`Deferred`, hence the depends-on edge to TASK-1105. A JSONL file through `sq import -` keeps it to one transaction per batch. The operator authorised this cleanup (ruling on FEAT-1101).

## Tests

One table per behaviour. A row exists only if breaking the fix turns it red, so check each one that way. Rows are boundaries and failures, never a cross product. Service level only: `sq check` output and exit codes are unchanged, so the CLI adds nothing here. Run `tests/meta` (registries, the import-edge table, the mutable-state guard for any new module constant), `tests/integration` and `tests/cli`, because a bundled spec changes.

- **F10, `subentities_settled_with_parent`**. Rows: an Approved review with an Open finding warns, naming the count and local ids; an Approved review whose only outstanding finding is Fixed warns (op-pierre ruling: Fixed counts); an Approved review whose findings are all Verified, WontFix, Noted or Deferred is silent; a Rejected review (role `retired`) with an Open finding warns; an InReview review with an Open finding is silent; a type that does not select the rule is silent; a project status with another name and the `done` role, on a type that selects the rule, warns.
- **F3, `type_has_live_author`**. Rows: sole author live, silent; sole author archived with an open item, warns and names `sq role activate <slug>`; sole author archived with only settled items, silent; two authors with one live, silent; a `*dev` author and no developer, warns and says to add a developer; a custom type no playbook guide authors, warns and names no role. Selection rows: a squad whose `[squad] validators` leaves the rule out is silent with an unauthored open item; `type_has_live_author@error` reports at error; an override list opening with `"$(*squad.validators)"` keeps it.
- **This repository**: after ST3, `sq check` here is clean with both rules on. That is the acceptance for ST3, not a test.

## Generated output

The bundled `workflow.toml` changes, so regenerate any golden pinning `sq workflow` / `sq check --json` output and the template manifest if the spec is in it.

## CHANGELOG substance (0.17.0)

The developer reports and the tech writer writes the entry (ST4).

- Added: `sq check` warns when a settled review (bundled: Approved) still holds a finding that is not settled (Open or Fixed). The rule is `subentities_settled_with_parent`, selected on the review type, and any type can select it. If your override replaces `[items.review] validators`, open the list with `"$(*items.review.validators)"` to keep it.
- Added: `sq check` warns when a type has open items but no active role authors it, naming the role to activate. The rule is `type_has_live_author`, selected in the bundled `[squad] validators`; leave it out of your own `[squad] validators` to turn it off, or open that list with `"$(*squad.validators)"` to keep it.
- No migration.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1104 add-subtask "<title>"`; track with `sq task 1104 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add subentities_settled_with_parent and select it on the bundled review type

<!-- sq:subtask:ST1:body -->
Closes REV-1099 F10. A per-item warn rule: an item at a settled status holding a sub-entity at a status that is not settled, keyed on status roles only (ADR-1102), so Noted and Deferred count as settled and Fixed does not: an Approved review holding a Fixed finding is reported (op-pierre ruling). Register it in the name sets and the catalog. Select it on `[items.review] validators` in the bundled spec, and open this repo's `[items.review]` override with the splat so it keeps the selection. Tests: the F10 rows in the task's Tests section.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add type_has_live_author, naming the catalog role to activate

<!-- sq:subtask:ST2:body -->
Closes REV-1099 F3. An always-on squad-global warn rule: a non-roster type with at least one open item where no live role is an in-lane author (intersect `in_lane_owner` with the live roster). The message names the catalog author to activate (`sq role activate <slug>`), or says to add a developer for a `*dev` lane. Tests: the F3 rows in the task's Tests section, service level only.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Give every outstanding finding on this repo's settled reviews a real disposition

<!-- sq:subtask:ST3:body -->
Keeps `sq check` clean in this repository once REV-1099 F10's rule lands. 106 Approved reviews here hold findings that are not settled (69 Fixed only, 23 Open, 14 both, measured on 2026-10-24). Give each finding Verified, Noted, Deferred with `--deferred-to`, or WontFix with reasoning, never a bulk close. Batches can go through `sq import -`. Needs TASK-1105 (Noted, Deferred) merged first. The operator authorised this cleanup on FEAT-1101.
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

<!-- sq:subtask:ST5 -->
### ST5 — Make type_has_live_author selectable and selected by default

<!-- sq:subtask:ST5:body -->
Closes REV-1131 F1. In `src/squads/_workflow/_models.py`, move `type_has_live_author` from `ALWAYS_ON_SQUAD_GLOBAL_NAMES` to `SELECTABLE_SQUAD_GLOBAL_NAMES`; default level stays warn. In the bundled `src/squads/_specs/workflow.toml`, set `[squad] validators = ["type_has_live_author"]`. The rule body and messages do not change. The engine already runs a selectable member only when selected and reads its `@<level>`.

Tests: the three selection rows in the task Tests section, in the existing type_has_live_author table. Keep the activation edits in the eight test files: the fixture squad still selects the rule. Regenerate the template manifest and any golden pinning `sq workflow` or `sq check --json`; run `tests/meta`, `tests/integration`, `tests/cli` and the fast gates.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Document type_has_live_author as on by default and deselectable

<!-- sq:subtask:ST6:body -->
After ST5. Reword the CHANGELOG 0.17.0 entry and `docs/overrides.md`: move the rule from the always-on table to the selectable squad-wide checks, say the bundled `[squad] validators` selects it, show turning it off (a `[squad] validators` list without it) and keeping it in a replacing list with `"$(*squad.validators)"`. The `minimal`-preset sentence names that opt-out. Quote only messages produced by the dev build.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T19:46:22Z] `tech-lead` Olivia Lead:
  - Realigned: registry paths, the F10 Fixed ruling and the ST3 authorisation applied; Tests rewritten as one table per behaviour, service level only. Moved to Ready; still blocked on TASK-1105.
- [2026-10-25T00:17:16Z] `python-dev` Elias Python:
  - Handoff for ST1 and ST2 (uncommitted in the tree). ST3 and ST4 untouched.
    
    **ST1, `subentities_settled_with_parent`.** Per-item warn rule in `_validators.py`, registered in `CATALOG`, `VALIDATOR_NAMES`, `DEFAULT_VALIDATOR_LEVEL`. Keyed on status roles on both sides, so Fixed counts as outstanding and Noted, Deferred, Verified, WontFix do not. Message: `status is Approved with 2 unsettled findings: F1, F3`. Selected on `[items.review] validators` in the bundled `workflow.toml`; manifest and content store regenerated with the two repo scripts.
    - Deviation: I did NOT add it to `SUBENTITY_VALIDATOR_NAMES`. Doing so made a review reassigned to `records` load silently (its own list now names a "sub-entity check"), which turned two existing refusal tests red, and it would let this policy rule stand in for `subentity_status_valid`. It is argued in the `UNGUARDED_VALIDATOR_NAMES` comment instead.
    - NOT done: this repo's `squads/.overrides/workflow.toml` still replaces `[items.review] validators` without the splat. Adding `"$(*items.review.validators)"` makes the released 0.16.0 `sq` refuse the whole workflow ("dangling splat path ... no counterpart in the bundled base"), so every board command fails. I reverted it; `~/.local/bin/sq check` is clean. The one-line splat has to land with the tool upgrade (with ST3). Until then `tests/meta/test_this_repositorys_workflow_override_keeps_what_the_bundled_spec_turns_on.py[review]` is red, and it is the only red test.
    
    **ST2, `type_has_live_author`.** Always-on squad-global warn rule. For each non-roster type with an item at a non-settled status, it intersects `in_lane_owner` with the live role slugs; empty means one finding per type, item column empty. Message: `type 'review' has 1 open item but no live role authors it — reactivate ...`. Remedies: a catalog author never activated gets `sq role activate <slug>`; an author with an archived roster entry gets `sq role <slug> status Active`, because `activate` refuses an existing non-live role (verified in a scratch squad); a `*dev` author gets `sq dev add --tech <tech>`; a type no guide authors gets no remedy. A broken roles override falls back to the bundled catalog (that override is its own finding).
    - Fallout in tests: minimal-roster squads that create a task or review now get the warning. 8 test files activate the author role before asserting a clean `check`, and `tests/goldens/check_squad.json` was regenerated with `UPDATE_GOLDENS=1`.
    
    **Tests.** `tests/service/test_a_settled_review_holding_an_unsettled_finding_is_reported.py` (8 rows) and `tests/service/test_a_type_with_open_items_and_no_live_author_is_reported.py` (8 rows). Mutation-checked: keying on the status name, keying the finding side on `Open`, dropping the bundled selection, dropping the live-slug intersection, counting settled items, and breaking each remedy branch each turn a row red. Last run of meta, unit, integration, cli, service, tui: 14077 passed, 1 failed (the override guard above), 13 skipped. pyright, ruff check and ruff format are clean.
    
    **Dev build on this repo** (read-only `check --json`, with the splat temporarily in the override): 107 reviews flagged, one more than the 106 measured on 2026-10-24; no `type_has_live_author` finding; one other pre-existing warning (`.claude/agents/tech-writer.md` pointer out of date). Without the splat the dev build flags none, because the override replaces the list.
    
    **CHANGELOG substance (ST4)**
    - Added: `sq check` warns when a settled review (bundled: Approved, Rejected) still holds a finding that is not settled (Open or Fixed). Rule `subentities_settled_with_parent`, selected on the review type; any type can select it. An override that replaces `[items.review] validators` must open the list with `"$(*items.review.validators)"` to keep it.
    - Added: `sq check` warns when a type has open items but no live role authors it, naming the role to activate or reactivate, or telling you to add a developer.
    - No migration. Docs: `docs/overrides.md` validator tables need both rules (tech writer).
- [2026-10-25T00:18:29Z] `python-dev` Elias Python:
  - The xfail(strict) marker on the review row of the override-keeps-bundled meta test goes with the splat and the tool upgrade, alongside ST3.
- [2026-10-25T00:30:53Z] `tech-writer` Theo Writer:
  - ST4 done (uncommitted). CHANGELOG 0.17.0 Added: one entry per rule, with the `$(*items.review.validators)` splat under **What to do**. Docs: overrides.md (settled-parent check paragraph, three bundled types with their own `validators` list plus a review splat example, `type_has_live_author` row in the always-on table, now ten, and a playbook rule), roles.md (retiring a type's only author), workflow.md (one line in the deferred-findings section). Every message quoted was produced by the dev build in a scratch squad, including the `@error` gate (`error: status is Done with 1 unsettled story: US1`, refused with `--force` too) and all three remedy wordings.
- [2026-10-25T00:45:12Z] `python-dev` Elias Python:
  - ST5 and REV-1131 F1-F3 done, uncommitted: type_has_live_author selectable and in bundled [squad] validators; reactivate remedy checks the lifecycle edge; capability lanes name holder roles. Manifest and store regenerated; meta, unit, integration, cli and targeted service files green apart from the strict xfail.
- [2026-10-25T00:58:23Z] `tech-writer` Theo Writer:
  - ST6 done (uncommitted): CHANGELOG 0.17.0 entry, docs/overrides.md and docs/roles.md reworded for `type_has_live_author` as selectable and bundled in `[squad] validators`.
  - overrides.md: row moved from the always-on table (now nine) to the selectable one (now six, marked bundled); example opens with the splat; new paragraph on turning it off (minimal/core, people-written types) and raising it with `@error` in place of the splat; refusal list says six and quotes the type-list refusal. Playbook rule: "or"-joined remedies, capability holders, add-a-developer, and the `--force` remedy, with one verified four-line example.
  - roles.md: retirement passage names the selecting list, the `--force` case, and the opt-out. CHANGELOG adds the opt-out, `@error`, the splat note, `--force` and capability-holder remedies, and the core-roster case.
  - Every quoted message and claim produced by the dev build in scratch squads (minimal, core, full, custom type, no-edge role lifecycle, all selection shapes incl. splat repeat refusal). @tech-lead ready for review alongside ST5.
<!-- sq:discussion:end -->
