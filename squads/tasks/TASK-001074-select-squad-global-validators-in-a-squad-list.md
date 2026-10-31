---
id: TASK-1074
sequence_id: 1074
type: task
title: Select squad-global validators in a [squad] list
status: Done
parent: FEAT-902
author: tech-lead
refs:
- ADR-982:implements
- ADR-864:implements
description: The [squad] validators table, the always-on and selectable tiers with
  declared levels, and the five selectable members
subentities:
- local_id: ST1
  title: Add the typed [squad] table with an empty bundled validators list
  status: Done
  maps_to: US6
- local_id: ST2
  title: Partition squad-global members into tiers with one default-level table
  status: Done
  maps_to: US6
- local_id: ST3
  title: Refuse invalid [squad] selections at spec load and in workflow lint
  status: Done
  maps_to: US6
- local_id: ST4
  title: Run always-on plus selected members in sq check with one clock read
  status: Done
  maps_to: US6
- local_id: ST5
  title: Add children_settled_with_parent
  status: Done
  maps_to: US1
- local_id: ST6
  title: Add dependency_acyclic
  status: Done
  maps_to: US2
- local_id: ST7
  title: Add wip_limit with the shared active-item helper
  status: Done
  maps_to: US3
- local_id: ST8
  title: Add unassigned_active
  status: Done
  maps_to: US4
- local_id: ST9
  title: Add stale_active against the run's single clock instant
  status: Done
  maps_to: US5
- local_id: ST10
  title: Prove the selection on a scratch copy of this repository's squad
  status: Done
  maps_to: US6
created_at: '2026-10-16T19:58:12Z'
updated_at: '2026-10-16T21:16:06Z'
---
<!-- sq:body -->
## Scope

Deliver FEAT-902 as ADR-982 rules it: a `[squad]` table in the workflow document whose one key,
`validators`, selects squad-global members with the per-type grammar, an always-on/selectable
partition of the squad-global catalog, one default-level table for every squad-global member, and
the five selectable members. Covers stories 1 to 6.

- **Surface.** `squad` joins `WORKFLOW_TOP_LEVEL_SECTIONS` as a typed record (unknown keys
  refused); the bundled document ships `validators = []`; an override replaces the list whole and
  `"$(*squad.validators)"` extends it; `[selected]` refuses `squad`. Entries go through
  `parse_validator_entry`, no second grammar.
- **Tiers.** Always-on: every squad-global member that exists when this lands. That is six today,
  not the five the feature names: `roster_slug_valid` joined the catalog after the feature was
  written and is always-on on the same test (a defect in every squad). If FEAT-961's
  `display_config_valid` has landed, it is always-on too. Selectable: `children_settled_with_parent`,
  `dependency_acyclic`, `wip_limit:<n>`, `unassigned_active:<n>`, `stale_active:<days>`. The two
  sets are disjoint, their union is the squad-global catalog, and neither overlaps the per-item
  catalog: each asserted at import.
- **Levels.** One declared default-level table over the whole squad-global catalog, closed by
  assert, read through one resolver; no member writes a level literal. Always-on members keep
  today's levels (all `error` except `playbook_guide_role_live`, `warn`); the five selectable
  default to `warn`. `@error` at this scope only changes `sq check`'s exit code: squad-global
  members never run at the create/update gate.
- **Matching.** An active item is a `work`-category item at a status whose role declares
  `live = true`; settled is the role's `settled` flag; dependency edges are ref kinds whose role is
  dependency, oriented by their declared direction. No role, status or ref-kind name is matched.
- **Time.** `ValidatorEngine.report` reads the injectable clock once per run and hands the instant
  to members on `SquadGlobalContext`; `stale_active` calls no clock.
- **Finding `item`.** The parent id (children_settled_with_parent), the stale item id
  (stale_active), empty otherwise with the subjects in the message; never an assignee slug.

Binding rulings, not reopened: ADR-982 as accepted by op-pierre on 2026-10-09 (one staleness
threshold per squad, non-dialable always-on members) and confirmed on 2026-10-12 (active by the
`live` flag on work-category items; a selection that cannot fire is refused at load); op-pierre on
FEAT-902, 2026-10-09 (`unassigned_active:<n>` means more than n).

Not in this task: writing `[squad]` into this repository's `squads/.overrides/workflow.toml`. The
released 0.15 tool reads that file and refuses an unknown top-level key. That is the manager's
release-preparation step in the feature body, after the operator migrates this squad.

## New state

One spec table (`[squad]`), which is the decision. No frontmatter key, no index field.

## Migration

None (ADR-982, Consequences). No contribution to `_migrations/_v0_15_to_v0_16.py` and no
POSTCONDITIONS row. The bundled document changes, so its golden lock, the manifest and the content
store are regenerated.

## Order and dependencies

Depends on the FEAT-900 task (TASK-1073): both edit `VALIDATOR_NAMES`-adjacent tables in
`_workflow/_models.py`, the catalogs in `_services/_validators.py` and the catalog guard tests, and
this task's partition assert must see the per-item catalog that task extends. One developer, in
sequence. No depends-on on TASK-990 or TASK-1069: their overlap is additive (`_services/_validators.py`
rules, `_specs/workflow.toml` attributes, the manifest), so this runs in a worktree and rebases,
regenerating the manifest at merge. FEAT-961's task may add one always-on member; whichever lands
second places it in the partition and the default-level table.

## Files

`_specs/workflow.toml`, `_workflow/_loader.py` (`WORKFLOW_TOP_LEVEL_SECTIONS`), `_workflow/_models.py`
(the `squad` record, the tier sets, the squad-global default-level table, Plane-1 checks in and
beside `_check_validators_assignment`), `_specmerge.py` only if the splat path needs it,
`_services/_validators.py` (the five members, `SquadGlobalContext`, `ValidatorEngine.report`),
`_services/_maintenance.py` (the `index_reconciled` hold-back in `check`), the bundled-spec golden,
`templates_manifest.json` and the content store. Tests under `tests/integration`, `tests/cli`,
`tests/meta`.

## Acceptance (whole task)

- Every acceptance bullet of FEAT-902 US1 to US6 is pinned by a named test; the handoff maps
  bullet to test. The release-preparation section of the feature is out.
- **Table-driven shape tests**, three backbone tables:
  - *Selection entry by outcome* (ST3): every refusal of US6 as a row, plus each of the five
    members at bare, `@warn` and `@error` loading clean. Columns: spec load, `sq workflow lint`,
    the message.
  - *Active-item counting* (shared by ST7 to ST9): rows are a work item at a live status, a role,
    a skill, an operator and a contract at `Active`, a records item at a live status, a project
    status whose role declares `live = true` under another name, a role named `active` declaring
    `live = false`, a settled item, an unassigned item. Columns: counted by `wip_limit`, by
    `unassigned_active`, measured by `stale_active`.
  - *Graph shapes* (ST6): two-cycle, three-cycle, self-block, diamond, a mixed `blocks` and
    `depends-on` cycle, a `related` cycle, a `targets` cycle, a long chain, a graph with two
    disjoint cycles.
- **Pipeline invariants:** a squad that selects nothing gets exactly the issues it got before
  (golden over a corpus fixture); two `sq check` runs over an unchanged corpus with nothing
  selected agree; no selection at any level changes a write's outcome.
- A falsified test per subtask, recorded in the handoff.
- The handoff gives the tech writer: the always-on list, the selectable list with parameters and
  default levels, that `@error` here only changes the exit code, and the override splat.

## Gates and working rules

TASK-990's "Gates and working rules" apply unchanged: pyright/ruff with `--all-extras`,
`~/.local/bin/sq check` clean, `tests/meta` on any module constant or bundled-byte change; test
selection derived from the diff, the manager runs the full suite; one-or-two sentence comments with
no versions or ticket ids; no ticket ids in test file names; no edits to `CHANGELOG.md`, `docs/`,
the hand-written `CLAUDE.md` or `squads/.overrides/`; probing only in a scratch squad under the
session scratchpad.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1074 add-subtask "<title>"`; track with `sq task 1074 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add the typed [squad] table with an empty bundled validators list

<!-- sq:subtask:ST1:body -->
**Goal.** The workflow document accepts a typed `[squad]` table with one key, `validators`, shipped empty, merged on the override contract every other key follows.

**Approach**

- `_workflow/_loader.py`: `squad` joins `WORKFLOW_TOP_LEVEL_SECTIONS`. `_workflow/_models.py`: a `SquadSpec` record (`extra="forbid"`, `validators: list[str] = []`) on `WorkflowSpec`.
- `_specs/workflow.toml`: `[squad]` with `validators = []`. Regenerate the bundled-spec golden, the manifest and the content store.
- Override: a plain list replaces the bundled one; `"$(*squad.validators)"` extends it. `[selected]` refuses `squad` with a message saying the table has no entries to drop.
- An override that fails to load falls back to the bundled spec, as for every declaration.

**Tests**

- Table: override shape by resolved list. Shapes: no `[squad]`; empty list; a plain list; a splat plus one entry; an unknown key under `[squad]`; `[squad]` as a non-table; `[selected] squad = …`. Columns: load outcome, resolved list, message.
- A squad that selects nothing: `sq check` output identical to before on a corpus fixture.

**Falsify.** Accept unknown keys under `[squad]`: the unknown-key row loads. Restore.

**Acceptance.** FEAT-902 US6: the table, the empty bundled list, the override and splat, `[selected]` refusal, fallback on a failed override.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-16T20:31:48Z] `python-dev` Elias Python:
  - Done in c4c413d8 on worktree-agent-a4a6de4545a741fbd. Falsification: SquadSpec extra=ignore turns 1 new test red (unknown-key row).
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Partition squad-global members into tiers with one default-level table

<!-- sq:subtask:ST2:body -->
**Goal.** The squad-global catalog is partitioned into always-on and selectable tiers, and every member has one declared default level read through one resolver.

**Approach**

- `_workflow/_models.py`: `ALWAYS_ON_SQUAD_GLOBAL_NAMES` (every existing member, six today including `roster_slug_valid`) and `SELECTABLE_SQUAD_GLOBAL_NAMES` (the five). Asserts: disjoint; union equals `SQUAD_GLOBAL_VALIDATOR_NAMES`; disjoint from `VALIDATOR_NAMES`.
- A `DEFAULT_SQUAD_GLOBAL_LEVEL` table closed against the squad-global catalog by assert: today's levels for the always-on members, `warn` for the five.
- `_services/_validators.py`: every squad-global member takes its level from one resolver (the selection's `@level`, else the default); remove each level literal.
- Register the module constants with the `tests/meta` mutable-state guard as code constants.

**Tests**

- Catalog test: every squad-global member has a declared default; adding a name without a tier fails at import.
- AST guard: no squad-global member passes a level string literal to `CheckIssue`.
- Always-on levels unchanged: a corpus that triggers each always-on member reports the same levels as before.

**Falsify.** Put a level literal back in one member: the AST guard goes red. Remove `roster_slug_valid` from the always-on set: the import assert fails. Restore each.

**Acceptance.** FEAT-902 US6: the default-level bullet and the disjoint-tiers bullet.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-16T20:31:50Z] `python-dev` Elias Python:
  - Done in c4c413d8. Falsification: a level literal back in wip_limit turns 2 new tests red (AST guard); dropping roster_slug_valid from the always-on set fails the import-time asserts.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Refuse invalid [squad] selections at spec load and in workflow lint

<!-- sq:subtask:ST3:body -->
**Goal.** Every invalid `[squad].validators` entry is refused at spec load naming the entry, and reported by `sq workflow lint`.

**Approach**

- Plane-1 checks in `_workflow/_models.py`, beside `_check_validators_assignment`, using `parse_validator_entry`:
  1. unknown name;
  2. a per-item name under `[squad]` (message: it belongs on a type's `validators` list), and the reciprocal for a squad-global name on a type's list, in place of "unknown validator";
  3. an always-on name;
  4. a parameter on a member that takes none; a missing or malformed parameter on one that requires it (`wip_limit` and `stale_active` a positive integer, `unassigned_active` a non-negative integer);
  5. a level other than `error` or `warn`;
  6. the same bare name twice, whatever the parameters;
  7. a selection that cannot fire: `wip_limit`, `unassigned_active` or `stale_active` when no work-category type's lifecycle holds a status of a live role; `dependency_acyclic` when no ref kind declares the dependency role. The corpus is never consulted.

**Tests**

- The selection-entry table of the task body: one row per refusal above (with `wip_limit:0`, `wip_limit:-1`, `wip_limit:x`, bare `wip_limit`, `unassigned_active:0` valid, `stale_active:1.5`, `index_reconciled`, `body_written`, `foo`, `dependency_acyclic@info`, `wip_limit:3` twice, `wip_limit:3` with `wip_limit:4`), plus clean loads for each member at bare, `@warn` and `@error` in a spec that can fire it.
- A type list naming `wip_limit:3`: refused with the reciprocal message.
- Cannot-fire rows: a spec whose work types have no live status; a spec with no dependency ref kind.

**Falsify.** Drop the cannot-fire check: those rows load. Restore.

**Acceptance.** FEAT-902 US6: the refusal bullets, the reciprocal messages, the cannot-fire bullet.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-16T20:31:52Z] `python-dev` Elias Python:
  - Done in c4c413d8. Falsification: dropping the active-item cannot-fire check turns 3 new tests red; dropping the dependency one turns 1 red.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Run always-on plus selected members in sq check with one clock read

<!-- sq:subtask:ST4:body -->
**Goal.** `sq check` runs the always-on members plus the squad's selection in declared order, at the resolved levels, with one clock read per run; nothing squad-global runs at the create/update gate.

**Approach**

- `_services/_validators.py`: `ValidatorEngine.report` builds the effective set (always-on, then the selection), strips the parameter for the catalog lookup, and reads `clock.now()` once into a new `SquadGlobalContext` field; members read the parameter from their own selection entry.
- `_services/_maintenance.py`: the existing `index_reconciled` hold-back in `check` keeps working with the effective set.
- Confirm by test that `gate()` never calls a squad-global member.

**Tests**

- Table: selection by run. Rows: nothing selected; one member; all five; one at `@error`. Columns: which members ran, finding levels, `sq check` exit code, and a create plus an update on an offending item (never refused).
- Two runs over an unchanged corpus with nothing selected agree (exact issue lists).

**Falsify.** Run the selection at the gate: the never-refused column goes red. Restore.

**Acceptance.** FEAT-902 US6: the never-at-the-gate bullet and the selected-level bullet; the shared acceptance line of US1 to US5.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-16T20:31:54Z] `python-dev` Elias Python:
  - Done in c4c413d8. Falsification: running selectable members whether or not selected turns 6 new tests red. Squad-global members never run at the gate: gate() holds none and a counting member is never called.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Add children_settled_with_parent

<!-- sq:subtask:ST5:body -->
**Goal.** `children_settled_with_parent` flags, once per parent, a parent at a settled status with at least one child at a status that is not settled.

**Approach**

- One pass over the index: for each item whose status's role declares `settled = true`, collect children (items whose `parent` is it) whose status's role does not. Sub-entities are not children. Any parent type.
- Finding: `item` is the parent id; the message lists the open children; level from the resolver.

**Tests**

- Table: parent status by children. Parent: settled, open, cancelled (settled). Children: none; all settled; one open; several open; a cancelled child; a child at a project status whose role declares `settled = true` under another name; open sub-entities only. Per cell: finding or none, item, message.
- Parents of three types (epic, feature, a project-declared type).

**Falsify.** Match the status name `Done` instead of the flag: the project-status row goes red. Count sub-entities: the sub-entity row goes red. Restore each.

**Acceptance.** FEAT-902 US1, all bullets except the scratch-copy bullet (ST10).
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-10-16T20:31:56Z] `python-dev` Elias Python:
  - Done in c4c413d8. Falsification: matching the status name Done turns 2 new tests red; counting sub-entities as children turns 1 red.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Add dependency_acyclic

<!-- sq:subtask:ST6:body -->
**Goal.** `dependency_acyclic` reports each cycle among dependency edges once, naming the items on it, and terminates on any graph.

**Approach**

- Build the graph from refs whose kind declares the dependency role, each oriented by its declared direction (so `blocks` and `depends-on` agree). Ignore every other kind.
- Find cycles with an iterative strongly-connected-components pass (no recursion limit); one finding per non-trivial component or self-loop, `item` empty, members named in the message in a stable order.

**Tests**

- The graph-shape table of the task body. Per row: finding count, named items, `item` empty.
- A 2,000-node chain closing on itself completes without recursion error.

**Falsify.** Skip orientation: the mixed `blocks` and `depends-on` row goes red. Include `related`: the related-cycle row goes red. Restore each.

**Acceptance.** FEAT-902 US2, all bullets.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-10-16T20:31:58Z] `python-dev` Elias Python:
  - Done in c4c413d8. Falsification: skipping orientation turns 1 new test red (mixed blocks/depends-on); including every ref kind turns 2 red. A 2,000-node cycle completes (iterative SCC).
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Add wip_limit with the shared active-item helper

<!-- sq:subtask:ST7:body -->
**Goal.** `wip_limit:<n>` flags once per assignee holding more than n active items.

**Approach**

- One helper, `active_items(index, spec)`, shared with ST8 and ST9: work-category items at a status whose role declares `live = true`.
- Group by assignee; skip unassigned; report each assignee over n. `item` empty; the message names the assignee and the count.

**Tests**

- The active-item counting table of the task body (wip column).
- Boundaries: exactly n clean, n+1 flagged; two assignees over the cap give two findings.

**Falsify.** Count by the status name `Active`: the role and contract rows are counted. Restore.

**Acceptance.** FEAT-902 US3, all bullets.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
- [2026-10-16T20:32:00Z] `python-dev` Elias Python:
  - Done in c4c413d8. Falsification: counting active by status name turns 12 new tests red.
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Add unassigned_active

<!-- sq:subtask:ST8:body -->
**Goal.** `unassigned_active:<n>` reports one line when more than n active items have no assignee.

**Approach**

- Reuse `active_items`. Count those with no assignee; when the count exceeds n, one finding with `item` empty, the count, and the first few ids in a stable order.
- Independent of the per-item `assignee_present`: either, both or neither may be selected.

**Tests**

- The active-item counting table (unassigned column).
- Boundaries: `:0` with one unassigned flags; `:2` with two is clean, with three flags.
- Both this and `assignee_present` selected: each reports on its own terms.

**Falsify.** Use at-least instead of more-than: the boundary row goes red. Restore.

**Acceptance.** FEAT-902 US4, all bullets.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
- [2026-10-16T20:32:02Z] `python-dev` Elias Python:
  - Done in c4c413d8. Falsification: at-least instead of more-than turns 13 new tests red.
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Add stale_active against the run's single clock instant

<!-- sq:subtask:ST9:body -->
**Goal.** `stale_active:<days>` flags each active item whose `updated_at` is more than the given days before the run's single clock instant.

**Approach**

- Reuse `active_items`. Compare `updated_at` with the instant on `SquadGlobalContext` (ST4); the member calls no clock. `item` is the stale item's id.

**Tests**

- Frozen clock (`frozen_time` fixture): untouched days+1 warns; exactly days is clean.
- Two items in one run measured against the same instant (advance the frozen clock between member calls and show no effect).
- The active-item counting table (stale column).

**Falsify.** Call `clock.now()` inside the member: the same-instant test goes red. Restore.

**Acceptance.** FEAT-902 US5, all bullets.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
- [2026-10-16T20:32:04Z] `python-dev` Elias Python:
  - Done in c4c413d8. Falsification: calling clock.now() inside the member turns 2 new tests red; report() reads the clock once per run (tested).
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — Prove the selection on a scratch copy of this repository's squad

<!-- sq:subtask:ST10:body -->
**Goal.** On a scratch copy of this repository's squad, the selection works and the live board is untouched.

**Method**

- Copy `squads/` and `.squads.toml` under the session scratchpad. If the schema differs from the build under test, migrate the copy with the dev build (`uv run --project <repo> sq -C <copy> migrate up`).
- `sq check` on the copy with nothing selected: same issues as before the feature (diff recorded).
- Extend the copy's override with `[squad] validators = ["$(*squad.validators)", "children_settled_with_parent", "dependency_acyclic"]`; `sq workflow lint` reports it valid; `sq check` reports the settled parents with open children and any dependency cycles. Record the counts and ids on this subtask for the manager's release-preparation step; fix nothing here.

**Acceptance.** FEAT-902 US1 scratch-copy bullet and US6 last bullet. `git status` shows no change under `squads/`. The tech-writer handoff of the task body is written.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
- [2026-10-16T20:32:06Z] `python-dev` Elias Python:
  - Done. Scratch copy of this squad, migrated with the dev build: sq check with nothing selected = 26 issues; with [squad] validators = splat + children_settled_with_parent + dependency_acyclic = 26 issues, diff empty (no settled parent with open children, no dependency cycle). workflow lint reports the override valid. Live squads/ untouched.
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T19:58:50Z] `tech-lead` Olivia Lead:
  - Broken down into ST1-ST10. No migration (bundled spec gains an empty [squad] table; golden and manifest regenerate). Depends on TASK-1073. The always-on tier is every existing squad-global member: six today, since roster_slug_valid joined the catalog after FEAT-902 was written, so US6 lists of five read as six. The live override selection stays the manager release-prep step. @manager
- [2026-10-16T20:06:38Z] `python-dev` Elias Python:
  - Not started: sequenced after TASK-1073, which is stopped on a duplicate-check finding (see its last comment).
- [2026-10-16T20:32:08Z] `python-dev` Elias Python:
  - Delivered in c4c413d8 (worktree-agent-a4a6de4545a741fbd). The body mentions no field_value_declared, so nothing to drop (TASK-1073 was cancelled). Always-on: index_reconciled, backend_reconciled, roster_config_integrity, default_designation_duplicated, roster_slug_valid (error), playbook_guide_role_live (warn). Selectable, default warn: children_settled_with_parent, dependency_acyclic, wip_limit:<n> (more than n per assignee, n>=1), unassigned_active:<n> (more than n, n>=0), stale_active:<days> (days>=1). At this scope @error only changes the sq check exit code. Override: [squad] validators replaced whole; the splat "$(*squad.validators)" extends. Full suite 11699 passed. The content-store orphan was cleared with seed_content_store --rebuild; regenerate the manifest at merge.
- [2026-10-16T20:50:17Z] `python-dev` Elias Python:
  - Review fixes in the follow-up commit on worktree-agent-a4a6de4545a741fbd. ST10 correction: the 26 issues in my dry run came from the copy having no .claude/ or CLAUDE.md (backend_reconciled errors and pointer warnings); after sync there are none, so 26 is not a baseline. The selection added nothing on the copy.
  - US-to-test map (tests/service unless noted): US1 children_settled_with_parent -> test_squad_global_members_by_shape: test_parent_status_by_children, test_the_open_children_are_named_in_the_message_and_counted, test_a_parent_is_reported_once_however_many_children_are_open. US2 dependency_acyclic -> same file: test_graph_shape_by_cycles, test_a_two_thousand_node_chain_closing_on_itself_is_one_cycle, test_a_cycle_among_settled_items_is_reported_like_any_other, test_a_group_larger_than_its_path_names_the_other_items. US3 wip_limit -> test_active_item_counting_by_measure, test_wip_limit_boundary_is_more_than_the_limit, test_two_assignees_over_the_cap_give_two_findings_in_slug_order. US4 unassigned_active -> test_active_item_counting_by_measure, test_unassigned_active_boundary_is_more_than_the_limit. US5 stale_active -> test_stale_active_boundary_is_more_than_the_days, test_stale_active_reads_the_instant_it_is_handed_and_calls_no_clock, and in test_squad_selection_in_sq_check: test_the_clock_is_read_once_per_run_and_every_item_is_measured_against_it. US6 -> test_squad_table_in_the_workflow_document (shape and entry tables, repeats, reciprocal, check fallback), tests/unit/test_squad_global_tiers_and_levels (tiers, defaults, no level literal), test_squad_selection_in_sq_check (selection by run, exit codes, writes never change, gate never runs squad-global, recorded baseline, two runs agree).
- [2026-10-16T21:01:49Z] `manager` Catherine Manager:
  - Done: REV-1076 approved; merged at 8cc6d3b5; full suite 11742 passed, 0 failed.
- [2026-10-16T21:16:06Z] `tech-writer` Theo Writer:
  - Documented: overrides.md "Squad-wide checks: the [squad] table" (always-on vs opt-in, parameters, boundaries, @error exit code only, load-time refusals), top-level and [selected] key lists, stability/internals wording, CHANGELOG 0.16 Added entry. Uncommitted. @manager
<!-- sq:discussion:end -->
