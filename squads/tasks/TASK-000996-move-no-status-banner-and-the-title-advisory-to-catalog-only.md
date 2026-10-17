---
id: TASK-996
sequence_id: 996
type: task
title: Move no_status_banner and the title advisory to catalog-only
status: Done
parent: FEAT-899
author: tech-lead
assignee: python-dev
priority: low
refs:
- ADR-864:implements
description: Both checks leave the floor and the work bundle, the add-<kind> advisory
  follows selection, and this project selects both in its first workflow override
subentities:
- local_id: ST1
  title: Take no_status_banner off the floor
  status: Done
  story: US1
- local_id: ST2
  title: Resolve the title threshold only for a type that selects it
  status: Done
  story: US2
- local_id: ST3
  title: Take subentity_title_max out of the work bundle
  status: Done
  story: US2
- local_id: ST4
  title: Select both checks in this project's workflow override
  status: Done
  story: US3
created_at: '2026-10-11T21:10:16Z'
updated_at: '2026-10-12T05:33:34Z'
---
<!-- sq:body -->
## Scope

Two per-item checks run in every squad with no way to turn them off: `no_status_banner` sits
in `COMMON_CORE`, so every type of every category runs it, and `subentity_title_max` sits in
the `work` entry of `CATEGORY_BUNDLES`. ADR-864 places both in the catalog-only tier: a type
runs one only when its own `validators` list names it. This task:

- takes `no_status_banner` off the floor and `subentity_title_max` out of the `work` bundle;
- makes the title advisory that `add-<kind>` prints follow the same selection, at the same
  number `sq check` uses;
- selects both for this project in `squads/.overrides/workflow.toml`, the first override
  file in this repository, so neither rule weakens here.

It covers stories 1 to 3 of FEAT-899. Story 4 (documentation) is TASK-997.

Not changed: the selection grammar, either member's message, either member's default level
(`warn`), the default number (120), the banner detector, `VALIDATOR_CONTEXT`, the gate, and
every other member of the floor and the bundles.

## Subtasks, in build order

- **ST1, take `no_status_banner` off the floor** (US1).
- **ST2, resolve the title threshold only for a type that selects it** (US2). The resolver
  changes first, so `sq check` and the create-time advisory never disagree at any commit.
- **ST3, take `subentity_title_max` out of the `work` bundle** (US2).
- **ST4, select both in this project's workflow override** (US3), with the whole-squad
  comparison.

One developer, one pass, one review at the end: every subtask edits the same two tables in
`_workflow/_models.py`. The whole-squad comparison test of ST4 is written before ST1, on the
untouched tree, because its expected list is what the engine reported before the change.

## Working in the validator worktree

The code is edited, and every `uv run` command is run, in the validator worktree. The board
is not operated from there.

- **No board item is created in the worktree, with any build.** A worktree mints numbers
  from its own copy of `squads/.squads.json`, and two trees creating items claim the same
  number. Driven: a scratch copy of this squad gave the number 996 to the first item created
  in it, which is the number the main tree gave this task.
- **Board writes are made from the main checkout, with the released tool:**
  `cd /home/pchat/projects/squads && pwd && ~/.local/bin/sq task 996 ...`. This covers the
  task status, each subtask status, subtask comments and the handoff comment. Never a bare
  `sq`, never `uv run sq`, never with the worktree as the working directory. The `sq check`
  of the gates is run the same way.
- A defect found on the way is described in a comment on this task. It is not filed from the
  worktree.
- **The dev build is never pointed at this repository's squad, in either tree.** A dev-build
  probe runs in a scratch squad or a scratch copy nested under the session scratchpad:
  print the working directory before any writing command and chain with `&&`.
- The one file under `squads/` this task changes is `squads/.overrides/workflow.toml`,
  written as a plain file in the worktree (ST4). Stage named paths only: `src/`, `tests/`
  and that file. Nothing else under `squads/` is staged from the worktree, whose copy of the
  board is behind the main tree's.

## The selection table

One parametrised table is the backbone of this task's tests. ST1 creates it for
`no_status_banner`; ST2 and ST3 add the `subentity_title_max` rows and the advisory
surfaces; ST4 reuses its fixtures. A row that needs its own fixture still goes through the
same assertions as its neighbours.

- **Types, by category (rows).** `work` hosting a kind: `feature` (story), `task` (subtask),
  `review` (finding). `work` hosting none: `epic`, which ships its own `validators` list,
  and `bug`. `records`: `decision`, `guide`. `roster`: `role`, `skill` (ships its own list),
  `operator`. Declared by a project override: one `work` type, one `records` type, and one
  `records` type that hosts a kind.
- **Selection shapes (columns).**
  - unselected: the bundled spec, no override;
  - the bare name;
  - with a number: `subentity_title_max:80` (for `no_status_banner` a number is refused at
    load, "takes no param");
  - with a level suffix: `@warn`, `@error`;
  - number and level: `subentity_title_max:80@error`;
  - selected on a different type only;
  - a type that replaces its bundled list without the splat form
    (`[items.epic] validators = ["no_status_banner"]`), and the same with it
    (`["$(*items.epic.validators)", "no_status_banner"]`).
- **Input shapes.** Banner: a body opening with `STATUS:`, with a bold `**Status:**`, with
  `## Status`, with `### Status`; a description opening with `STATUS:`; a mention in the
  middle of a body; no body. Title length: one under, at, and one over the threshold, at 120
  and at a declared number.
- **Surfaces.** `Service.check()` (level, item id, message); `sq check` text with its bare
  exit code; `sq check --json`. For the title member also: `BlockResult.title_advisory`, the
  text `add-<kind>` prints, the `title_advisory` key of `add-<kind> --json`, the reflog
  delta, and the warnings of `sq import`.
- **Invariants, asserted for every row.**
  - Unselected: no finding and no advisory, on every input shape.
  - Selected: the finding carries the message text and, with no level suffix, the level
    (`warn`) that the member produced before this task.
  - `add-<kind>` produces the advisory if and only if a following `check()` reports the
    title finding for that sub-entity, and both name the same number.
  - The type's other effective validators are exactly what its category and its own list
    give. The two replaced-list rows state it for `no_parent`.
- **Negatives run selected.** A case that expects silence (a mid-body mention, a title at
  the threshold) passes for the wrong reason on a type that does not run the check. Every
  negative is asserted on a type that selects the member.

## Building at the released version

The package reads 0.15.0 and stays there until release preparation. Do not bump it.

- **No bundled byte changes.** This task edits no file under `_specs/` and no template under
  `_rendering/templates/`: neither name appears in the bundled `workflow.toml`, `roles.toml`,
  `playbook.toml` or any template (searched, with the same pattern validated against
  `_workflow/_models.py`). The override scaffold text in `_overrides/_service.py` is not
  edited either.
- **So no manifest-freshness check turns red.** `tests/meta/test_override_manifest_and_stamp_freshness.py`
  passes in full, and the CI `manifest freshness` step is unaffected. A failure in that
  module is a real failure for this task, not an expected one. If the work turns out to need
  a bundled-byte change, stop and report it before making it.
- The manifest is not regenerated: do not run `scripts/gen_template_manifest.py` in write
  mode, `scripts/seed_content_store.py` or `scripts/bump_version.py`.
- **The schema may be ahead in the worktree.** If the branch carries a later schema than the
  released tool's, the dev build refuses a copy of this squad until it is migrated. ST4 says
  what to do; it is never `sq migrate up` on this repository's squad.

## What was driven, and what is left to confirm

Driven on 2026-10-11 with the released tool (`~/.local/bin/sq`, 0.15.0), on a scratch copy
of this repository's squad (`squads/`, `.squads.toml`, `.claude/`, `CLAUDE.md`) and in a
fresh scratch squad.

- **The override of ST4 loads under the released tool and changes nothing there.**
  `sq workflow lint`: "workflow spec OK", exit 0. `sq override list`: `workflow`, base
  version 0.15.0, state `current`, exit 0. `sq check`: "no issues", exit 0, as without the
  file.
- **With known positives planted**, a 121-character subtask title, a decision body opening
  with `## Status`, a bug description opening with `STATUS:`, and a 120-character title that
  must stay silent: `sq check --json` is byte-identical with and without the file. Three
  warnings, each reported once. Naming a member the floor or the bundle already carries does
  not report it twice.
- **`sq sync` is unaffected.** With the file present a sync changes no file, and removing
  the file then syncing changes no generated file.
- **A splat needs a bundled list to address.** `"$(*items.task.validators)"` is refused:
  "dangling splat path 'items.task.validators' has no counterpart in the bundled base".
  Only `epic` and `skill` ship a `validators` list.
- **A replaced list loses its bundled entry silently.**
  `[items.epic] validators = ["no_status_banner"]` loads with no error or warning.
- **A validator name the tool does not know stops every command.** With
  `"item_title_max:120"` in the file: "validators entry 'item_title_max:120' names an
  unknown validator", `sq check` exits 3 and every other command exits 1.
- **A hosting type in `records` may satisfy the sub-entity clause with this member alone.**
  `[items.review] category = "records"` with `validators = ["subentity_title_max"]` loads;
  with no `validators` it is refused. ST3 keeps that.
- **The create-time advisory fires where the check does not run.** On
  `[items.review] category = "records"` with `validators = ["subentity_status_valid"]`,
  `add-finding` with a 121-character title prints the advisory and `sq check` is silent.
  ST2 closes that.
- **Not driven:** anything with the dev build. What the changed engine reports with the
  file is ST4's to prove.

## Moved to release preparation

Not acceptance of this task:

- `sq check` on this repository under the 0.16.0 build, after the operator migrates the
  squad. Until then the board runs the released tool, whose floor and bundle still carry
  both members, so the file's entries are redundant there and harmless (driven).
- If the bundled `workflow.toml` changes anywhere in the release, the file's 0.15.0 stamp
  reports "may be stale" under 0.16.0: `sq override diff workflow`, then
  `sq override update workflow`.
- Entries naming a validator the released tool does not know join the file only then.

## Acceptance (whole task)

- Each subtask's own acceptance holds, and every acceptance bullet of stories 1 to 3 is
  pinned by a named test. The handoff maps bullet to test.
- **Table-driven tests over the named families** of the selection table, not one test per
  branch.
- **Pipeline-level invariants:** the whole-squad comparison of ST4 (a squad that selects
  both reports exactly what it reported before the change); check and advisory agree on
  every row; for every bundled type, the effective validator set differs from the one before
  this task by exactly the two removed names.
- **A falsified test per subtask.** Break the change on purpose, watch the named test go
  red, restore it, watch it go green. The handoff records, for each subtask, what was broken
  and the tests that went red.
- **A service-level test and a CLI smoke test for every behaviour change.** CLI tests read
  the bare exit code, never one taken through a pipe.
- `rg -n '"(no_status_banner|subentity_title_max)"' src/squads/_workflow/_models.py` shows
  neither name inside `COMMON_CORE` or `CATEGORY_BUNDLES`, checked against the same search
  on the commit before.

## Gates and working rules

- `uv run --all-extras pyright`, `uv run --all-extras ruff check .` and
  `uv run --all-extras ruff format --check .` are clean, run from the worktree root. A bare
  `uv run` prunes the optional `tui` extra and reports false import errors. `sq check` is
  clean, run from the main checkout as above.
- Run `uv run --all-extras pytest tests/meta` whenever a module-level constant is added or
  changed (the mutable-state guard and the catalog guards live there).
- Run targeted tests only: `tests/meta`, plus the union found by searching `tests/` for each
  changed name (`COMMON_CORE`, `CATEGORY_BUNDLES`, `SUBENTITY_VALIDATOR_NAMES`,
  `UNGUARDED_VALIDATOR_NAMES`, `item_subentity_title_max`, `title_advisory`,
  `TITLE_ADVISORY_MAX`, both member names, both message texts). Redirect to a file and read
  the summary line from the file; no `-q` on the command line. Report the selectors. The
  manager runs the full suite afterwards.
- Comments and docstrings are one or two sentences, with no release versions, ticket ids or
  history. Several comments on this path explain the floor and the bundles at length: the
  ones this task makes false are rewritten to what the code does now, not extended.
- No ticket ids in source or in test names: name a test file by the behaviour it pins.
- `type X = ...` for aliases. A multi-exception handler is parenthesised and carries
  `# fmt: skip`. No `from __future__ import annotations`.
- User-facing errors are `SquadsError` subclasses; dynamic text printed to the console goes
  through `e()`.
- Do not edit `CHANGELOG.md` or anything under `docs/`. The handoff lists every
  adopter-visible change for the tech writer (TASK-997): the two checks that stop running
  by default, on which types; the advisory that stops with one of them; the line that
  restores each; and the exact text of any message that changed, or a statement that none
  did.
- The hand-written part of `CLAUDE.md` is not edited here. Its `sq check` gate section names
  the title rule; the handoff proposes the sentence saying both rules are this project's own
  selections in the override file.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 996 add-subtask "<title>"`; track with `sq task 996 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Take no_status_banner off the floor

<!-- sq:subtask:ST1:body -->
**Goal.** `no_status_banner` runs for a type only when that type's `validators` list names
it. Where it is named, it reports exactly what it reported before.

**Approach**

- `_workflow/_models.py`: remove the name from `COMMON_CORE`.
- Same module: add it to `UNGUARDED_VALIDATOR_NAMES`. The import-time closure
  (`_CLAUSE_GUARDED | COMMON_CORE | UNGUARDED_VALIDATOR_NAMES == VALIDATOR_NAMES`) fails
  otherwise. It is the `parent_present` shape: in no bundle, effective only where a type
  names it, so no category reassignment can take it away. One bullet in the comment above
  that constant, a sentence or two.
- It stays in `VALIDATOR_NAMES`, in `DEFAULT_VALIDATOR_LEVEL` (`warn`), in `CATALOG` and in
  `VALIDATOR_CONTEXT` (`RAW_TEXT`). `_no_status_banner`, `_opens_with_status_banner` and the
  two patterns in `_services/_validators.py` are not edited.
- No bundled TOML selects it. `_specs/workflow.toml` is not edited.
- Search `src/` for the name and for `COMMON_CORE`, and read each hit: a comment that calls
  the member a floor member, or says every type runs it, is corrected in place. A comment
  that cites it as an example of a warn-level member stays true.

**Tests**

- Create the selection table of the task body, with the `no_status_banner` rows: every type
  row, the unselected, bare, `@warn`, `@error`, other-type-only and both replaced-list
  shapes, and every banner input shape. A number on this member (`no_status_banner:5`) is a
  load refusal row.
- Expected, per shape:
  - unselected: no finding on any input, for every type row;
  - bare and `@warn`: the present message at `warn`, `sq check` exits 0;
  - `@error`: the same message at `error`, `sq check` exits 3, and the write that produced
    the body still succeeds (the member needs the file text, which the gate does not hold);
  - other type only: the selecting type reports, this one does not;
  - `epic` replaced without the splat: the banner is reported and an epic accepts a parent;
    with the splat: the banner is reported and a parent is still refused.
- For a roster type, plant the banner where that type can carry one (body or description).
- Invariant: for every bundled type, `effective_validator_names(category, extra=validators)`
  under the bundled spec equals the tuple from before this subtask without
  `no_status_banner`, written as literal expected tuples.
- Service-level: `Service.check()`. CLI smoke: `sq check` and `sq check --json`, bare exit
  codes.
- These go red when the name leaves the floor, and are rewritten into the table or onto a
  selecting spec:
  - `tests/unit/test_validator_engine_scaffold.py::test_common_core_and_category_bundles_are_populated`;
  - the positive cases of `tests/service/test_status_banner_advisory_check.py`;
  - `tests/cli/test_status_banner_advisory_check_cli.py::test_check_prints_the_status_banner_issue_and_exits_0`
    and `::test_check_json_includes_the_status_banner_issue_at_warn_level`.
- The negative cases of those two files keep passing on the bundled spec and stop proving
  anything there: move them onto a selecting spec with the positives.
- `tests/service/test_validator_catalog_lift.py` calls the member through `CATALOG`
  directly and stays green; the closure tests in
  `tests/unit/test_a_category_reassignment_must_stay_internally_consistent.py` stay green
  with the name in its new bucket.

**Falsify.** Put the name back in `COMMON_CORE`: every unselected row and the effective-set
pin go red. Restore. Then delete the `validators` line from the selecting fixture: every
positive row goes red. Each negative shares its fixture with a positive, so a fixture that
stopped selecting cannot leave a negative passing unnoticed. Restore.

**Acceptance**

- Story 1, all four bullets. The fourth is the bare-name row loading with no unknown-name
  refusal.
- The name appears in `VALIDATOR_NAMES`, `DEFAULT_VALIDATOR_LEVEL` and
  `UNGUARDED_VALIDATOR_NAMES`, and not in `COMMON_CORE` or `CATEGORY_BUNDLES`.

Gates and working rules: the task body.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Resolve the title threshold only for a type that selects it

<!-- sq:subtask:ST2:body -->
**Goal.** One resolver answers both "does this type run the title check" and "at what
number", and `sq check` and `add-<kind>` both ask it. A type whose effective validator set
does not hold `subentity_title_max` gets no title advisory at create time.

**Why it is a change on its own.** `_add_block_core` compares the title against
`WorkflowSpec.item_subentity_title_max`, which returns 120 for any type, selected or not.
Driven with the released tool: on `[items.review] category = "records"` with
`validators = ["subentity_status_valid"]`, `add-finding` with a 121-character title prints
the advisory while `sq check` reports nothing.

**Approach**

- `_workflow/_models.py::WorkflowSpec.item_subentity_title_max` returns `int | None`:
  `None` when the type is not declared or its effective set does not hold the member
  (`_effective_bare_validators`, the one definition of "effective" the consistency pass
  already uses); otherwise the number of the type's own entry, or
  `DEFAULT_SUBENTITY_TITLE_MAX` when the selection carries none.
- `_services/_validators.py::_subentity_title_max` returns no issue on `None`. The engine
  only runs the member where it is effective, so this is the path a direct `CATALOG[...]`
  call takes.
- `_services/_subentities.py::_add_block_core` builds the advisory only when the resolver
  returns a number and the title is longer than it. `BlockResult.title_advisory`, the
  `title_advisory` key of `--json` and the reflog key keep their shape: absent when there is
  no advisory.
- The advisory does not read the level suffix. `subentity_title_max:80@error` gives the
  same advisory text as `subentity_title_max:80`, and `add-<kind>` is not refused (driven
  with the released tool: an 81-character `add-subtask` exits 0 and prints the advisory,
  and `sq check` then exits 3).
- The resolver has two callers in `src/`. pyright strict must show both handling `None`.
- `_interactions.TITLE_ADVISORY_MAX` stays, as the re-export of the default that tests build
  titles from. Its comment, the resolver docstring and the comment in `_add_block_core` are
  corrected to what the code does now.

**Tests**

- Add the advisory surfaces to the selection table: `BlockResult.title_advisory`, the text
  `add-<kind>` prints, `add-<kind> --json`, the reflog delta, and the warnings `sq import`
  returns for an imported sub-entity.
- Rows that change with this subtask alone: the `records` type hosting a kind, selecting
  another sub-entity check (no advisory at 121 characters); the same type selecting
  `subentity_title_max` bare (advisory at 121, none at 120) and `:80` (advisory at 81, none
  at 80).
- Rows for the three bundled hosting types, over each kind: bare, `:80`, `@warn`,
  `:80@error`, at one under, at, and one over the number.
- Invariant, every row: the advisory is produced if and only if a following `check()`
  reports the title finding for that sub-entity, and the two messages name the same number.
- Service-level: `add_story`, `add_subtask`, `add_finding` and `check()`. CLI smoke:
  `add-<kind>` text and `--json`, bare exit code 0 with and without the advisory.

**Falsify.** Make the resolver return `DEFAULT_SUBENTITY_TITLE_MAX` again for a type that
does not hold the member: the `records` hosting row goes red on the advisory surfaces.
Restore. Then make `_add_block_core` compare against `DEFAULT_SUBENTITY_TITLE_MAX`
directly: the `:80` rows go red between 81 and 120 characters. Restore.

**Acceptance**

- Story 2, fourth bullet: on a type that selects the member, the advisory and `sq check`
  use the same number, one character over triggers both, at the threshold neither.
- Story 2, the advisory half of the third bullet, for a type outside the `work` bundle. ST3
  extends it to the bundled `work` types.
- No behaviour changes for a bundled `work` type in this subtask: its effective set still
  holds the member through the bundle.

Gates and working rules: the task body.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Take subentity_title_max out of the work bundle

<!-- sq:subtask:ST3:body -->
**Goal.** `subentity_title_max` runs for a type only when that type's `validators` list
names it. A bare selection resolves to 120; a selection with a number uses that number. With
ST2 in place the create-time advisory follows.

**Approach**

- `_workflow/_models.py`: remove the name from `CATEGORY_BUNDLES["work"]`.
  `DEFAULT_SUBENTITY_TITLE_MAX` stays 120 and becomes what a bare selection resolves to.
- **The sub-entity clause keeps accepting it.** `_clause_subentity_checked` refuses a type
  that hosts a kind while none of the four `SUBENTITY_VALIDATOR_NAMES` is effective. Driven
  with the released tool: a hosting type moved to `records` with
  `validators = ["subentity_title_max"]` loads. It must still load, so
  `SUBENTITY_VALIDATOR_NAMES` keeps its four names, as the set whose subject is the hosted
  kind, and the clause's message keeps listing four.
- **Its bookkeeping changes.** The member is no longer one a category can take away, so it
  leaves the set the clause is registered as guarding in `CONSISTENCY_CLAUSES` and joins
  `UNGUARDED_VALIDATOR_NAMES`, with one bullet of reasoning. Derive the guarded set from
  `SUBENTITY_VALIDATOR_NAMES` and the bundle table instead of writing a second literal list.
  Three properties hold afterwards and are already pinned in
  `tests/unit/test_a_category_reassignment_must_stay_internally_consistent.py`: every
  catalog member is in exactly one bucket; no guarded name is in `COMMON_CORE`; every
  guarded name is in some bundle.
- `test_the_work_bundle_supplies_every_sub_entity_validator_the_clause_looks_for` in that
  file states a relation that no longer holds as written. Restate it as the two it
  protects: the `work` bundle supplies every guarded sub-entity name, and at least one name
  the clause accepts, so a bundled `work` type hosting a kind is not refused by its own
  spec.
- The docstring of `effective_validator_names` uses "a category's bare
  `subentity_title_max`" as its example of a suffix overriding a bundled entry. Replace the
  example with a member a bundle still carries. Search `src/` for the name and for
  `CATEGORY_BUNDLES` and correct each comment this makes false, in place.
- No bundled TOML selects it. `_specs/workflow.toml` is not edited.

**Tests**

- Add the `subentity_title_max` rows to the selection table for every type row and every
  selection shape. The replaced-list shapes use `epic` (inert there, since it hosts no kind,
  and `no_parent` is kept or lost exactly as for the other member).
- Expected, per shape, on `feature`, `task` and `review`:
  - unselected: a 121-character title gives no finding and no advisory, on every surface;
  - bare: finding and advisory at 121, neither at 120, message naming 120, level `warn`;
  - `:80`: both at 81, neither at 80, message naming 80;
  - `@warn`: as bare; `:80@error`: the finding at `error`, `sq check` exits 3;
  - other type only: the selecting type reports and advises, this one does neither.
- Load rows: a `records` type hosting a kind with `validators = ["subentity_title_max"]`
  loads; with no `validators` it is refused with the clause's present message.
- A type hosting no kind that selects the member (`bug`) loads and reports nothing.
- Invariant: for every bundled type, the effective set under the bundled spec equals the
  tuple from before this subtask without `subentity_title_max`, as literal expected tuples
  (extend the pin ST1 wrote).
- Service-level and CLI smoke as in ST2, plus `sq check` and `sq check --json`.
- These go red when the name leaves the bundle, and are rewritten into the table or onto a
  selecting spec:
  - `tests/service/test_subentity_title_length_advisory.py`, the over-threshold and reflog
    cases;
  - `tests/cli/test_subentity_title_advisory_cli.py`, the three over-threshold and check
    cases;
  - `tests/service/test_subentity_title_max_threshold_is_spec_resolved.py::test_the_bundled_default_message_text_is_unchanged`,
    and `::test_a_type_declaring_no_override_reproduces_the_bundled_default_exactly`, whose
    premise becomes "unselected, nothing fires at any length; bare, 120";
  - `tests/service/test_validator_catalog_lift.py::test_subentity_title_max_flags_an_over_long_title`,
    which calls the member on a bundled `feature` and needs a selecting spec once the
    resolver returns `None` there.
- The at-or-below-threshold cases of the first two files keep passing on the bundled spec
  and stop proving anything: move them onto a selecting spec.

**Falsify.** Put the name back in the `work` bundle: the unselected rows on `feature`,
`task` and `review` and the effective-set pin go red. Restore. Then drop the name from the
names the clause accepts: the `records` hosting load row goes red. Restore.

**Acceptance**

- Story 2, first three bullets; with ST2, the fourth.
- The name appears in `VALIDATOR_NAMES`, `PARAMETERIZED_VALIDATOR_NAMES`,
  `SINGLE_SELECTION_VALIDATOR_NAMES`, `DEFAULT_VALIDATOR_LEVEL`,
  `SUBENTITY_VALIDATOR_NAMES` and `UNGUARDED_VALIDATOR_NAMES`, and in no entry of
  `CATEGORY_BUNDLES`.
- `uv run --all-extras pytest tests/meta` passes: a derived module-level constant is still
  a module-level constant for the mutable-state guard.

Gates and working rules: the task body.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Select both checks in this project's workflow override

<!-- sq:subtask:ST4:body -->
**Goal.** This project runs both checks at the strength it ran them before, selected in its
own `squads/.overrides/workflow.toml`. The bundled spec selects neither, and a fresh
`sq init` produces a squad that runs neither.

**The file.** It lands with this task: the released tool accepts it and reports the same
with and without it (driven, task body). Write it in the worktree as a plain file, with
exactly this content:

```toml
# squads:override-base:0.15.0
# This project's own validator selections, on top of what each type's category turns on.
#
# One table per item type, one entry per line. A `validators` array replaces the bundled
# one whole, so a type that ships its own list (epic, skill) opens with the splat of it.

[items.epic]
validators = [
  "$(*items.epic.validators)",
  "no_status_banner",
  "subentity_title_max:120",
]

[items.feature]
validators = [
  "no_status_banner",
  "subentity_title_max:120",
]

[items.task]
validators = [
  "no_status_banner",
  "subentity_title_max:120",
]

[items.bug]
validators = [
  "no_status_banner",
  "subentity_title_max:120",
]

[items.decision]
validators = [
  "no_status_banner",
]

[items.contract]
validators = [
  "no_status_banner",
]

[items.milestone]
validators = [
  "no_status_banner",
]

[items.review]
validators = [
  "no_status_banner",
  "subentity_title_max:120",
]

[items.guide]
validators = [
  "no_status_banner",
]

[items.role]
validators = [
  "no_status_banner",
]

[items.skill]
validators = [
  "$(*items.skill.validators)",
  "no_status_banner",
]

[items.operator]
validators = [
  "no_status_banner",
]
```

**Why this shape**

- `no_status_banner` on all twelve bundled types: the floor ran it on every one.
  `subentity_title_max:120` on the five `work` types: the bundle carried it for those, at
  120. On `epic` and `bug` it is inert, as it was.
- The splat only on `epic` and `skill`: a splat of a list the bundled type does not declare
  is refused (driven), and a list written without it silently loses the bundled entry.
- One table per type and one entry per line, so a later selection is one added line and
  never a rewritten list. The header names no particular check for the same reason.
- **Only names the released tool knows.** Every agent operates this board with the released
  tool until release preparation, and an entry naming a validator that tool does not know
  stops every `sq` command (driven). Both names here exist in it.
- **The stamp.** `0.15.0` is true while the bundled `workflow.toml` is byte-identical to the
  release: in the worktree, `git diff --stat v0.15.0 -- src/squads/_specs/workflow.toml`
  must print nothing before the file is written. If it prints something, report it and do
  not stamp.

**Tests**

- **Whole-squad comparison (the pipeline invariant).** Write this test first, on the
  untouched tree: a squad with one offender and one clean neighbour per input shape (a
  story, a subtask and a finding at 121 and at 120 characters; a body banner and a
  description banner on one item of each bundled type that can carry one), no override, and
  the full `check()` result as a literal expected list. It is green before ST1. After ST3
  the same squad, with this repository's override file copied into its `.overrides/`, must
  return the identical list: same issues, same levels, same messages, same order. With no
  override the list is empty.
- **The repository's file keeps what the bundled spec turns on.** A `tests/meta` test loads
  the bundled spec and the spec merged with `squads/.overrides/workflow.toml` through
  `load_workflow_spec`, and asserts over a table keyed by bundled type:
  - the effective set under the merged spec contains the effective set under the bundled
    spec (a dropped `no_parent` or `item_skill_shadowed` fails here; neither `sq check` nor
    `sq workflow lint` can report it);
  - `no_status_banner` is effective for all twelve types;
  - `item_subentity_title_max` is 120 for the five `work` types and `None` for the others;
  - every type the bundled spec declares has a row, so a type added later cannot be missed.
  The table is the place a later selection adds its row.
- **A fresh squad selects neither.** After `sq init`: no `.overrides/workflow.toml` exists,
  and neither name is in any type's effective set.
- CLI smoke, in a test squad carrying the file: `sq workflow lint` exits 0 with no error or
  warning; `sq override list` exits 0 and shows `workflow` as `current`; `sq check` exits 0.

**Driven proof, recorded in the handoff**

1. Copy the worktree's `squads/`, `.squads.toml`, `.claude/` and `CLAUDE.md` into a scratch
   directory nested under the session scratchpad. Without the last two the backend check
   reports missing pointers and drowns the comparison.
2. With the released tool, plant known positives in the copy: a 121-character and a
   120-character title on a subtask, a story and a finding; a decision body opening with
   `## Status`; a bug description opening with `STATUS:`. An empty result compared with an
   empty result proves nothing.
3. Released tool, with and without the file: `sq check --json` is byte-identical;
   `sq workflow lint` and `sq override list` exit 0.
4. Dev build, on the same copy, with the file: `sq check --json` is byte-identical to
   step 3. Without the file: every planted finding is gone and nothing else is reported.
5. If the dev build refuses the copy because the branch carries a later schema, run the dev
   build's `sq migrate up` on the copy, and take step 3's reading from the released tool on
   an unmigrated twin of it. Never on this repository's squad.

**Falsify.** In the repository's file, replace the `epic` list with one that has no splat:
the `tests/meta` containment row for `epic` goes red. Restore. Remove `"no_status_banner"`
from one records type: its row and the whole-squad comparison go red. Restore. Change
`:120` to `:121` on `task`: the whole-squad comparison goes red on the 121-character
subtask. Restore.

**Acceptance**

- Story 3, all four bullets. The third, on this repository, is step 3 for the released tool
  that runs the board and step 4 for the changed engine.
- `_specs/workflow.toml` is unchanged from the release, and so is the scaffold text of
  `sq override scaffold workflow`.
- What is left for release preparation is listed in the task body and is not acceptance
  here.

Gates and working rules: the task body.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-11T21:16:05Z] `tech-lead` Olivia Lead:
  - 2026-10-11: breakdown of FEAT-899 drafted, nothing promoted and no developer briefed. @manager
    
    - TASK-996 (python-dev) covers stories 1 to 3: ST1 story 1, ST2 and ST3 story 2, ST4 story 3. TASK-997 (tech-writer) covers story 4 and depends on this task.
    - The override of ST4 was driven with the released 0.15.0 tool on a scratch copy of this squad: lint, override list and check all clean, `sq check --json` byte-identical with and without the file over three planted findings, `sq sync` a fixed point. It lands with this task.
    - No bundled byte changes, so no manifest-freshness check is expected red.
    - Three calls made in the drafting that the operator or the architect may want to overrule: the 0.16 migration step gets no contribution and no manual text from this feature (story 4 says no migration is needed); a type hosting a kind may still satisfy the sub-entity clause by naming `subentity_title_max` alone, because that loads today; a `tests/meta` test reads this repository's own override file.
    - For FEAT-901: an entry naming a validator the released tool does not know stops every command on this board (driven with `item_title_max:120`), so its selections join the file at release preparation, not with the feature.
- [2026-10-11T21:17:38Z] `manager` Catherine Manager:
  - Promoted and dispatched under the operator's delegation of 2026-10-11 (the manager drives the build in the approved order; the validator features run in a second worktree). Three drafting questions go ahead on the tech lead's drafted answers and are raised with the operator: no contribution to the migration runner, a hosting type may still name the title check alone, and a tests/meta guard reads this repository's own override.
- [2026-10-11T21:41:06Z] `python-dev` Elias Python:
  - - Built ST1 to ST4 in the worktree .claude/worktrees/agent-a240571530eba5b43 (branch worktree-agent-a240571530eba5b43, four commits on release/0.16, nothing pushed). Ready for review. @manager
    - ST1: `no_status_banner` left COMMON_CORE and joined UNGUARDED_VALIDATOR_NAMES. ST2: `WorkflowSpec.item_subentity_title_max` returns `int | None` (None when the type's effective set lacks the member); `sq check` and `_add_block_core` both ask it. ST3: `subentity_title_max` left the work bundle and joined UNGUARDED_VALIDATOR_NAMES; the sub-entity clause's guarded set is derived from SUBENTITY_VALIDATOR_NAMES and the bundles (`_BUNDLED_SUBENTITY_VALIDATOR_NAMES`); the four-name set and the clause message are unchanged. ST4: `squads/.overrides/workflow.toml` written with the exact text of the subtask (stamp 0.15.0; `git diff v0.15.0 -- src/squads/_specs/workflow.toml` is empty).
    - No bundled byte, template, scaffold text, SCHEMA_VERSION, version or manifest changed. tests/meta green.
    - Whole-squad comparison (tests/integration, written first on the untouched tree, green there): the 21 banner findings plus 3 title findings reported before the change are reported identically, same order, with the repo override after the change; with no override the squad now reports nothing.
    - Driven proof on a scratch copy (squads/, .squads.toml, .claude/, CLAUDE.md) with five planted positives (121-char story, subtask, finding; ADR body opening with a Status heading; bug description opening with STATUS:) plus 120-char neighbours: released 0.15.0 `sq check --json` byte-identical with and without the file; lint and override list exit 0, workflow shown as current; dev build with the file byte-identical to the released output; dev build without the file reports `[]`.
    - Falsified per subtask, all restored: ST1 name back in COMMON_CORE (unselected rows, effective-set pin, scaffold test red) and `validators` dropped from the selecting fixtures (every positive red); ST2 resolver back to returning the default (records-hosting unselected rows red) and `_add_block_core` comparing to 120 (all :80 rows red); ST3 name back in the work bundle (unselected rows on feature, task, review and the pin red) and name dropped from SUBENTITY_VALIDATOR_NAMES (the records-hosting-by-title-alone load test red); ST4 epic list without the splat (meta containment row for epic red; the whole-squad test stays green, because no epic in it carries a parent), no_status_banner removed from decision (its meta row and the whole-squad test red), `:121` on task (its meta row and the whole-squad test red).
    - Did not match the code: (1) the add-<kind> advisory text names the title length, not the threshold, so "both name the same number" is asserted on the trigger boundary (one under, at, one over), not on message text. (2) `tests/service/test_bulk_import_engine.py::test_board_debt_from_an_import_surfaces_as_a_warning_not_silent_debt` also went red at ST3 and is not in the subtask list; rewritten onto a selecting spec. (3) the `@error` import case reports through `applied.findings`, not `applied.warnings`.
    - Adopter-visible, for TASK-997: `no_status_banner` no longer runs on any type unless the type's validators list names it (was every type); `subentity_title_max` no longer runs on epic, feature, task, bug, review unless named (was the work bundle); `add-<kind>` prints its title advisory only on a type that names `subentity_title_max`, at that type's number. Restore with `"no_status_banner"` and `"subentity_title_max"` (or `"subentity_title_max:80"`) in `[items.<type>] validators`; a type that ships a list (epic, skill) opens it with `"$(*items.<type>.validators)"`. No message text, default level (warn) or default number (120) changed.
    - Proposed sentence for the hand-written sq check gate section of CLAUDE.md: the status-banner rule and the over-long sub-entity title rule are this project's own selections in squads/.overrides/workflow.toml, not defaults of the tool.
    - Not covered: no full-suite run (the manager runs it); a wider targeted sweep over unit, meta, service, cli and integration was run once while finding the rewrites; tests/tui not run.
- [2026-10-11T21:45:49Z] `python-dev` Elias Python:
  - - Rebased onto the right base by merge: release/0.16 merged into the worktree branch as ca990517 (a merge commit, my four commits untouched, no conflict). @manager
    - `_subentities.py`: the release side changed two other hunks (the duplicate-id refusal calls in the remove and block-write paths); mine is the advisory block in `_add_block_core`. Git merged them without conflict and I kept both.
    - No test went red against the new base: the wide selection (tests/unit, tests/meta, tests/service, tests/cli, tests/integration) is 6767 passed, 8 skipped, 0 FAILED. tests/tui not run.
    - Re-captured comparison: the whole-squad "before" list was re-run on an untouched archive of release/0.16 (no override, bundled spec) and equals the recorded list exactly (1 passed).
    - Stamp check: `git diff --stat v0.15.0..HEAD -- src/squads/_specs/ src/squads/_rendering/templates` is empty, so the 0.15.0 base stamp stays true. `git diff --stat release/0.16..HEAD -- squads/` lists only squads/.overrides/workflow.toml, which is byte-identical to the subtask text.
    - Gates on the merged tree: pyright 0 errors, ruff check clean, ruff format --check 710 files already formatted.
- [2026-10-11T22:23:29Z] `python-dev` Elias Python:
  - - Review findings F1 to F5 of REV-998 fixed in tests only, commit d7bad7bf on the worktree branch; no src/ change. All five findings are marked Fixed with a comment. @manager
    - F1: the stamp assertion is gone. F2: the whole-squad test (renamed to test_a_squad_selecting_both_checks_reports_each_offender_once_at_warn.py) filters the report to the two members' findings; a review banner item was added to the fixture (REV-36, appended so no id moved). F3: the repository-override guard compares (name, parameter, level) with a level column. F4: the other-type row also drives the unselecting type. F5: docstrings corrected, unused TITLE_MESSAGE and the redundant COMMON_CORE assert removed.
    - Falsifications: F3, epic list with no splat and no_parent@warn, title at @error, and no_status_banner@error on review: red were the merged-spec table rows for epic and review, the containment row for epic, and the whole-squad test. F4, resolver leaking another type's number: red were the three other-type rows (feature, task, review); a constant-80 leak also reddens the unselected rows. F1 and F2 on a scratch copy at version 0.16.0 with parent_present@warn added to task: both tests green (39 passed); removing no_status_banner from review, removing the title entry from task, or changing a title number each turn the comparison and/or the table red.
    - Wide selection: 6767 passed, 8 skipped, 0 FAILED. pyright 0 errors, ruff check clean, ruff format --check 710 files unchanged.
- [2026-10-12T05:21:31Z] `manager` Catherine Manager:
  - Merged into release/0.16 at 4b23b04c by fast-forward after REV-998 was Approved. Gates on the merged tree: full suite 7032 passed, 14 skipped; pyright, ruff check and ruff format clean. The live board loads the new override under the released tool: check clean, lint clean, override current. QA verifies stories 1 to 3 next.
- [2026-10-12T05:33:32Z] `manager` Catherine Manager:
  - Closing under the operator's standing delegation for reviewed, verified, non-visual work: REV-998 Approved at 4b23b04c, QA verified stories 1 to 3 of FEAT-899 against the merged build and the released tool, and the gates are green on the merged tree (7032 passed, 14 skipped; pyright and ruff clean).
<!-- sq:discussion:end -->
