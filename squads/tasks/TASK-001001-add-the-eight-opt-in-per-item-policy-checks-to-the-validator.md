---
id: TASK-1001
sequence_id: 1001
type: task
title: Add the eight opt-in per-item policy checks to the validator catalog
status: InProgress
parent: FEAT-901
author: tech-lead
assignee: python-dev
priority: low
refs:
- ADR-864:implements
- BUG-1003:fixes
description: 'Eight catalog-only members from ADR-864 Part 2 and the blocked flag
  on a status role, in two parts: what changes no bundled file first, the flag and
  its check after the version bump'
subentities:
- local_id: ST1
  title: 'item_title_max: flag an item title over the declared length'
  status: Done
  story: US1
- local_id: ST2
  title: 'ref_rule_target_typed: flag an edge to a type its rule excludes'
  status: Done
  story: US2
- local_id: ST3
  title: 'body_written: flag an item body still at its scaffold'
  status: Done
  story: US3
- local_id: ST4
  title: 'description_present: flag an item with no summary'
  status: Done
  story: US4
- local_id: ST5
  title: 'assignee_present: flag an active item with no assignee'
  status: Done
  story: US5
- local_id: ST6
  title: 'blocked_has_blocker: flag a blocked item with no dependency edge'
  status: Todo
  story: US6
- local_id: ST7
  title: 'settled_requires_discussion: flag a settled item with no comment'
  status: Done
  story: US7
- local_id: ST8
  title: 'external_id_not_in_title: flag a tracker id in a title'
  status: Done
  story: US8
- local_id: ST9
  title: Prove the two-check selection on a copy of this squad
  status: Done
  story: US9
- local_id: ST10
  title: Let a status role declare that it means blocked
  status: Todo
  story: US11
- local_id: ST11
  title: Run only the checks that can refuse at the create/update gate
  status: Done
  story: US8
created_at: '2026-10-12T05:46:24Z'
updated_at: '2026-10-15T19:12:45Z'
---
<!-- sq:body -->
## Scope

ADR-864 Part 2 names eight per-item checks that are policies, not defects. A type runs one
only when its own `validators` list names it. This task adds the eight to the catalog, gives
a status role the flag one of them reads, and proves on a copy of this repository's squad the
selection this project makes at release preparation.

- The members: `item_title_max:<n>`, `ref_rule_target_typed`, `body_written`,
  `description_present`, `assignee_present`, `blocked_has_blocker`,
  `settled_requires_discussion`, `external_id_not_in_title:<regex>`.
- Each defaults to `warn`, sits in no floor and no bundle, and holds no level floor, so
  `@error` is accepted on all eight.
- They apply to `work` and `records` types only. Naming one on a roster type is refused at
  spec load, and so is a selection the spec's own declarations make unable to fire.
- It covers stories 1 to 9 and 11 of FEAT-901. ST1 to ST9 carry the story of the same
  number; ST10 is story 11; ST11 belongs to story 8.
- ST2 also fixes BUG-1003: the existing `ref_rule_target_present` and the new
  `ref_rule_target_typed` read a bare ref through one shared function.

Not in this task:

- `squads/.overrides/workflow.toml` is not edited, and no test reads it to find any of the
  eight names. This repository's own selection is the release-preparation acceptance in the
  feature body.
- `label_declared`, and the squad-scope members of ADR-982.
- A create-time advisory for an item title. The finding is `sq check`'s, and at `@error`
  the gate's.
- Any new verb, on any type.
- A gate on `ref add` or `ref rm`. Neither goes through the gate today.
- The two existing members that compare a status role by name (`supersedes_incoming` with
  `superseded`, `ref_rule_target_present` with `done`). They are left as they are and are not
  a model: nothing this task adds compares a role name.
- Anything under `clients/`. The VS Code client's reading of the role catalog is another
  owner's; ST10 says what to report.
- `docs/` and `CHANGELOG.md`: TASK-1002, the tech writer's.

## Subtasks, in build order

**Part one: changes no bundled file.**

- **ST11, the gate runs only the checks that can refuse** (US8). Engine only, first, so
  every later door table is written against the gate as it ends up.
- **ST1, `item_title_max`** (US1). Builds the shared test table, the required-parameter
  machinery and the refusal of a selection that cannot fire.
- **ST2, `ref_rule_target_typed`** (US2), with the BUG-1003 fix.
- **ST3, `body_written`** (US3). Reads the item's file.
- **ST4, `description_present`** (US4).
- **ST5, `assignee_present`** (US5).
- **ST7, `settled_requires_discussion`** (US7). Reads the item's file.
- **ST8, `external_id_not_in_title`** (US8). Reuses ST1's parameter machinery.
- **ST9, the two-check selection on a copy of this squad** (US9). Its "before" readings are
  taken before the first edit.

**Hard stop.** ST10 and ST6 are not started until the manager has confirmed, in a comment on
this task, that the working version is 0.16.0 and that `release/0.16` carries the bump. At
the stop the developer posts the part-one handoff and waits. Part one is complete on its
own: seven members, every invariant below holding over the seven, nothing depending on part
two.

**Part two: changes a bundled file.**

- **ST10, a status role declares that it means blocked** (US11). The flag, the bundled line,
  the role catalog's sixth key.
- **ST6, `blocked_has_blocker`** (US6). Reads the flag, and adds one aggregate to the
  validator context.

One developer, one commit per subtask: every subtask edits the same name tables in
`_workflow/_models.py` and the same catalog in `_services/_validators.py`.

## Working in the validator worktree

The code is edited, and every `uv run` command is run, in the validator worktree. The board
is not operated from there.

- **Check the fork point before the first edit.** In the worktree,
  `git merge-base release/0.16 HEAD` must print the commit `git rev-parse release/0.16`
  prints. If it does not, merge `release/0.16` into the branch (`git merge release/0.16`, no
  rebase) and check again. Repeat the check before each handoff and when resuming after the
  hard stop: `release/0.16` moves while this is built, and a merge is followed by a fresh run
  of the targeted tests.
- **Take the baseline on the untouched tree.** Run the targeted selection of the gates
  section once and keep its summary line, and run
  `uv run --all-extras pytest tests/test_scale.py --run-slow` once and keep that one too. A
  test that is red there is reported in a comment on this task and is not fixed here.
- **No board item is created in the worktree, with any build.** A worktree mints numbers
  from its own copy of `squads/.squads.json`, and two trees creating items claim the same
  number.
- **Board writes are made from the main checkout, with the released tool:**
  `cd /home/pchat/projects/squads && pwd && ~/.local/bin/sq task 1001 ...`. This covers the
  task status, each subtask status, subtask comments and the handoff comments. Never a bare
  `sq`, never `uv run sq`, never with the worktree as the working directory. The `sq check`
  of the gates is run the same way.
- **The dev build is never pointed at this repository's squad, in either tree.** A dev-build
  probe runs in a scratch squad or a scratch copy nested under the session scratchpad, never
  directly under `/tmp` (the test suite resolves a squad left there by walking up) and never
  inside a checkout. Print the working directory before any writing command and chain with
  `&&`. No `sq migrate up` and no `sq repair` on this repository's squad.
- Nothing under `squads/` is staged from the worktree. Stage named paths only (`src/`,
  `tests/`, and in part two the regenerated manifest and content store). Commit messages are
  one past-tense line with no trailer.
- A defect found in something this task does not add is described in a comment on this task.
  It is not filed from the worktree and not fixed here, unless a subtask says so.

## What a member registers

The import-time asserts refuse a partial registration, so each subtask lands all of this for
its member in one commit.

- `_workflow/_models.py`:
  - `VALIDATOR_NAMES`, and `DEFAULT_VALIDATOR_LEVEL` at `warn`;
  - `UNGUARDED_VALIDATOR_NAMES`: the member sits in no bundle and no floor, so it is
    effective only where a type names it and no category reassignment can take it away (the
    `parent_present` shape). One bullet in the comment above that constant covers the eight;
    each subtask adds its name to that bullet, not a bullet of its own;
  - not in `COMMON_CORE`, `CATEGORY_BUNDLES`, `VALIDATOR_LEVEL_FLOOR` or
    `SUBENTITY_VALIDATOR_NAMES`;
  - the set of names the roster refusal covers (below);
  - for the two that take a parameter (ST1, ST8): `PARAMETERIZED_VALIDATOR_NAMES` and
    `SINGLE_SELECTION_VALIDATOR_NAMES` (one value per type; the existing repeat-selection
    check then refuses a second entry), and a resolver method on `WorkflowSpec`. ST6 takes no
    parameter.
- `_services/_validators.py`:
  - the member function and its `CATALOG` entry;
  - its level through `_resolved_level(ctx, "<name>")`, never a literal;
  - a `VALIDATOR_CONTEXT` entry only for the two that read the file (ST3, ST7).
- Two `tests/meta` guards hold this to the code and must stay green:
  `test_validator_context_requirements_match_what_each_member_reads.py` (a member that reads
  `ctx.raw_text` reads it in its own function body, never through a helper that takes the
  context) and `test_validator_level_is_resolved_not_hardcoded_per_member.py`.
- No bundled TOML names any of the eight.

## A selection that cannot fire is refused at load

A selected check that the squad's own declarations make unable to fire is refused at spec
load, and `sq workflow lint` reports it as an error. Whether the corpus holds an offender is
never part of the test. Each message names the type, the entry and the declaration that is
missing.

- **Any of the eight on a roster type** (`role`, `skill`, `operator`). The eight are
  policies about the work an item tracks; a roster entry is configuration. The names this
  rule covers are one frozenset in `_workflow/_models.py`, which each subtask extends, so the
  rule is one place and no member carries a roster test of its own.
- **`ref_rule_target_typed`** on a type that declares no ref rule with a target (ST2).
- **`assignee_present`** on a type whose lifecycle holds no status of a role declaring
  `live = true` (ST5).
- **`blocked_has_blocker`** on a type whose lifecycle holds no status of a role declaring
  `blocked = true`, or in a spec that declares no dependency-role ref kind (ST6).
- These are Plane-1 checks beside `_check_ref_rule_targets`, fed the items, lifecycles,
  statuses, roles and ref kinds `_validate` already holds. ST1 writes the function with the
  roster rule; ST2, ST5 and ST6 each add a clause.

Under the bundled spec, read from `_specs/workflow.toml`, the cells are:

- `item_title_max`, `body_written`, `description_present`, `settled_requires_discussion`,
  `external_id_not_in_title`: accepted on the nine `work` and `records` types, refused on the
  three roster types.
- `ref_rule_target_typed`: accepted on `feature` (its `implements` rule targets `contract`);
  refused on every other type.
- `assignee_present`: accepted on `epic`, `feature`, `task`, `bug`, `review`, `contract`,
  `milestone`; refused on `decision` and `guide`, whose lifecycles hold no live status, and
  on the roster types.
- `blocked_has_blocker`: accepted on `epic`, `feature`, `task`, `bug`; refused on `review`,
  `decision`, `contract`, `milestone`, `guide`, whose lifecycles hold no `Blocked`, and on
  the roster types.

## Roles are read by flag

Nothing this task adds compares a role name or a status name. A role declares what it means:
`live` for active (the reading `first_active_status` and `live_statuses` already use),
`settled` for settled, and the new `blocked` for blocked. Each member reads the flag off
`spec.role_for(item.status)`. No role-name constant is added beside `FALLBACK_ROLE_NAME`.

## Gate participation

A member runs at the create/update gate when two things hold: `VALIDATOR_CONTEXT` declares no
requirement the gate does not hold, and its resolved level for the item's type is `error`
(ST11).

- **Why the level decides.** The gate discards every `warn` finding, so running a member
  that cannot refuse buys nothing and costs time under the index lock. With an adopter's
  regular expression in the catalog it is more than time: a pattern that backtracks would
  hang every gated write of a selecting type at the default level, with the lock held.
  Skipping members that cannot refuse changes no gate decision and confines that exposure to
  a type that selects the check at `@error`, where the adopter asked for it to guard writes.
- **Can refuse a write at `@error`** (they read the item, the spec and the index, which the
  gate holds): `item_title_max`, `ref_rule_target_typed`, `description_present`,
  `assignee_present`, `blocked_has_blocker`, `external_id_not_in_title`. The gate then
  refuses a create, `update`, `status`, `link` or retype whose resulting item is in the
  reported state, and accepts the write that takes the item out of it. At `warn` they are
  not evaluated on a write.
- **Report only** (they declare `RAW_TEXT`, which the gate does not hold): `body_written`,
  `settled_requires_discussion`. At `@error` they make `sq check` exit 3 and refuse no write
  on any door.
- `ref add` and `ref rm` do not go through the gate (`_services/_refs.py` holds no gate
  call). A member whose state a ref verb changes is reported by `sq check` after the verb,
  and at `@error` refuses the item's next gated write.
- For each member that can refuse, the handoff carries a door table (create, `update`,
  `status`, `sq import`) at `@error`: refused or accepted, with the message, as driven. The
  three roster types are rows of every table, as load refusals.

## The selection table

`tests/_selection_table.py` stays the one backbone. It is extended, not copied.

- **Type rows.** Add `contract` and `milestone` to `BUNDLED_ROWS`, so the table holds every
  bundled type. The modules that already parametrise over it gain the two rows. If one of
  them turns red on a new row, that is a finding about the member that module tests: report
  it, do not skip the row.
- **A member registry.** One entry per member of this task: its selecting entries per
  selection shape, a builder that plants one offender and one clean neighbour on a row, the
  fixed message fragment that identifies its findings, and for each type row whether the
  plain entry loads or is refused. ST1 creates it; each later subtask adds its entry.
- **Refusal cells.** A cell where the member cannot fire asserts the load refusal, through
  the loader and through `sq workflow lint`, with the type and the entry named. It plants
  nothing. The three roster rows are refusal cells for all eight members.
- **Message fragments.** `CheckIssue` carries no rule name, so a test finds a member's
  findings by a fragment of its message. Each member's message holds one fixed fragment that
  no other member's message contains. One test asserts this pairwise over all the fragments
  the module defines, the banner, sub-entity title and sub-entity body ones included.
- **`override_toml`** writes each entry as a TOML basic string. An entry holding a backslash
  (ST8's patterns) must be written as a TOML literal string.
- **Selection shapes (columns), for every member:** unselected (the bundled spec, no
  override); selected with its plain entry; `@warn`; `@error`; selected on a different type
  only; and, on `epic`, a list that replaces the bundled one without the splat form and one
  with it. The two members with a parameter add the parameter shapes of their subtask.
- **Surfaces.** `Service.check()` (level, item id, message); `sq check` text with its bare
  exit code; `sq check --json`; for a member that can refuse, the service call and the CLI
  verb that the gate refuses; `sq import` for ST1 and ST3. For the import, expected and to be
  driven either way: a warning at `warn`; at `@error` the finding in the result's findings
  for a report-only member, and a refusal by the pre-pass for one that can refuse.

## Test rules

- No assertion reads the package version, and none compares an override stamp with it.
- An equality over a `check()` list is over that list filtered to the members under test, by
  their fragments. A later selection in any override must not turn it red.
- A guard over a type's validators compares name, parameter and resolved level, never the
  name alone.
- A row that states another type is unaffected plants the offender on that other type and
  asserts it reports nothing.
- **Negatives run selected.** Every case that expects silence is asserted on a type that
  selects the member, sharing its fixture with a positive.
- No test reads `squads/.overrides/workflow.toml` to find one of the eight names. A test
  that selects one writes its own override text.
- A test file and a test are named by what they assert. No ticket id in a name.
- A CLI test reads the bare exit code, never one taken through a pipe.
- A setup step that fails fails the test: no fixture swallows an error from a create, a body
  write or an override load.

## Invariants (pipeline level)

- **The bundled spec selects none of the eight.**
  `tests/unit/test_bundled_types_effective_validator_sets.py` passes with its expected tuples
  unedited.
- **A squad that selects nothing reports nothing new.** A fixture squad holding an offender
  of every member on every type row that accepts it, under the bundled spec, returns no
  finding carrying any of the fragments.
  `tests/integration/test_a_squad_selecting_both_checks_reports_each_offender_once_at_warn.py`
  keeps its expected list.
- **Selection is per type.** For every member, a type that does not name it is silent while
  another type that names it reports.
- **Every cell is decided.** For every member and every type row, the plain entry either
  loads or is refused, as the registry says, and a refused spec is refused by
  `sq workflow lint` too.
- **Gate and report agree.** For each member that can refuse, at `@error`, over its whole
  input family: the gate refuses a write exactly when `check()` on the resulting state would
  report the member's finding. For the two report-only members, no door refuses at any level.
- **The gate decides as it did** (ST11): over the whole catalog, a member at `warn` is not
  called by the gate and a member at `error` is.
- **Check and overwrite guard agree** (ST3): `body_written` reports an item exactly when a
  plain body write without `--force` is accepted as a first write.
- **Both ref-rule checks read a bare ref alike** (ST2): an edge that satisfies
  `ref_rule_target_present` is never reported by `ref_rule_target_typed`.
- **The catalog stays closed.** The import-time asserts and the two `tests/meta` guards hold
  after every commit.

## Bundled bytes and the version

**Part one changes no bundled byte:** no file under `_specs/`, no template under
`_rendering/templates/`, not `templates_manifest.json`, not `content_store.json`, not the
override scaffold text. The eight names appear in none of them, and no command lists the
catalog.

- So part one does not wait for the working-version bump, and no manifest-freshness check
  turns red because of it. A failure in
  `tests/meta/test_override_manifest_and_stamp_freshness.py` during part one is a real
  failure. If part one turns out to need a bundled-byte change, stop and report it before
  making it.
- In part one, do not run `scripts/gen_template_manifest.py` in write mode.
- The version may move under the branch through a merge of `release/0.16`. Nothing in this
  task may depend on which version is running.

**Part two changes one bundled file**, `_specs/workflow.toml` (ST10: one key on
`[roles.blocked]` and the comment above the role table). It is built only at 0.16.0, because
the manifest script replaces the entry of whichever version is running, and at 0.15.0 that
would overwrite a released entry.

- After merging `release/0.16`, confirm in the worktree that `[project].version` in
  `pyproject.toml` reads 0.16.0 before the first edit of ST10.
- Once the bundled line is in, these apply and are part of ST10:
  - `python scripts/gen_template_manifest.py` (write mode) regenerates the 0.16.0 entry of
    `templates_manifest.json` and inserts the new revision into `content_store.json`; both
    files are committed with the change;
  - `python scripts/gen_template_manifest.py --check` passes (the CI `manifest freshness`
    step);
  - `tests/meta/test_override_manifest_and_stamp_freshness.py` passes in full;
  - the goldens that hold the role catalog follow the sixth key
    (`tests/goldens/workflow_roles.json`, `tests/cli/test_json_output_shape.py`);
  - `tests/meta`, `tests/integration` and `tests/cli` are run whole, since a golden that pins
    rendered output names none of the changed keys.
- Never, in either part: `scripts/seed_content_store.py`, `scripts/bump_version.py`, a
  change to `SCHEMA_VERSION`. No frontmatter key, index field or migration step comes from
  this task.

## Read, not driven

Each of these is a reading of the source at `75f53462`. No behaviour was run. Each is the
developer's to prove before building on it.

- **The gate doors.** `ValidatorEngine.gate` is called from item create
  (`_services/_base.py`), the `status` verb, the shared update core that the importer's
  pre-pass also runs, `link` (`_services/_items.py`) and retype (`_services/_retype.py`). No
  ref verb calls it.
- **What the gate runs.** `gate()` runs every effective member the context allows and only
  then keeps the `error` findings. It computes `registered_slugs` and
  `supersedes_incoming_seqs` on every call, each a walk of the whole index.
- **The scaffold is derived.** `ServiceCore.pristine_body` re-renders the type's creation
  template for the item and returns its body region; `_body_mutate` compares prose with view
  tags stripped on both sides. Neither is reachable from the validator module today.
- **Role flags.** `RoleSpec` carries `settled`, `hidden`, `color` and `live`.
  `WorkflowSpec.live_statuses` and `first_active_status` read `live`; the validation pass has
  `_status_live` and `_status_settled` for use before a spec object exists. The engine
  compares a role name in two members only, and those are not a model.
- **Role parsing.** `_parse_role` validates a role table with `RoleSpec.model_validate` and
  plain `bool` fields, which accepts some strings and integers as booleans.
- **The role catalog.** `ROLE_CATALOG_FIELDS` and `_role_catalog` in `_cli/_workflow_cmd.py`
  hold five keys; the human table has five columns.
- **The VS Code canary.** `clients/vscode/test/canary/skewCanary.test.ts` compares the
  `active` row of `sq workflow roles --json` with an exact five-key object.
- **This repository's override in a test.**
  `tests/cli/test_this_repositorys_workflow_override_loads_clean_cli.py` copies
  `squads/.overrides/workflow.toml`, stamped 0.15.0, and asserts `sq override list` shows it
  as `current`. Drift is decided on the bundled document's content.
- **A bare ref has no kind.** `split_ref` returns an empty kind for a bare ref, and
  `_ref_rule_target_present` compares that raw kind with its rules' kinds (BUG-1003, driven
  there with the released tool).
- **A digit `int()` rejects.** `_check_validator_param` tests `param.isdigit()` and then
  calls `int(param)`. `str.isdigit()` is true for a superscript digit, which `int()` refuses,
  so `subentity_title_max:²` would raise instead of being refused.
- **The comment parser.** `discussion.split_discussion` returns the comments of a discussion
  region and drops lines that precede the first comment header.

## Acceptance (whole task)

- Each subtask's own acceptance holds, and every acceptance bullet of stories 1 to 9 and 11
  is pinned by a named test or, for story 9's scratch copy, by a recorded driven step. The
  handoff maps bullet to test.
- **Table-driven tests over the named families** of each subtask, not one test per branch.
- The invariants above are each a test.
- **A falsified test per subtask.** Break the change on purpose, watch the named rows go
  red, restore, watch them go green. The handoff records, for each subtask, what was broken
  and the test ids that went red.
- **A service-level test and a CLI smoke test for every member.**
- **At the hard stop:** `git diff --stat release/0.16...HEAD -- squads/ src/squads/_specs
  src/squads/_rendering/templates src/squads/_rendering/templates_manifest.json
  src/squads/_rendering/content_store.json` prints nothing.
- **At the end:** the same command lists `src/squads/_specs/workflow.toml`, the manifest and
  the content store, and nothing under `squads/` or `templates/`.
- **Two handoffs for the tech writer (TASK-1002)**, one at the stop and one at the end,
  together listing every adopter-visible fact:
  - each member's entry form, its exact message, its refusals at spec load with their exact
    text (parameter refusals, cannot-fire refusals, the roster refusal), and what clears each
    finding;
  - the door table at `@error`, and this sentence about the gate, checked against the build:
    a check selected at `warn` is not evaluated on a write; the pattern of
    `external_id_not_in_title` runs on every `sq check`, and on a gated write of an item only
    when its type selects the check at `@error`, where the write holds the index lock while
    the pattern runs; nothing bounds a match, so a pattern that backtracks can hang
    `sq check`, and at `@error` the write;
  - that active means a role declaring `live = true`, settled a role declaring
    `settled = true`, blocked a role declaring `blocked = true`, and what a squad that
    declares its own roles must add before it can select `blocked_has_blocker`;
  - the sixth key of `sq workflow roles --json` and the new column of the text table;
  - every limit a subtask asks to be reported.

## Gates and working rules

- `uv run --all-extras pyright`, `uv run --all-extras ruff check .` and
  `uv run --all-extras ruff format --check .` are clean, run from the worktree root. A bare
  `uv run` prunes the optional `tui` extra and reports false import errors. `sq check` is
  clean, run from the main checkout as above.
- Run `uv run --all-extras pytest tests/meta` after every subtask: each one changes a
  module-level table, and the mutable-state guard and the catalog guards live there.
- Run targeted tests only: `tests/meta`, `tests/unit`, the new modules, and the union found
  by searching `tests/` for each name the subtask changed (`VALIDATOR_NAMES`,
  `UNGUARDED_VALIDATOR_NAMES`, `PARAMETERIZED_VALIDATOR_NAMES`, `VALIDATOR_CONTEXT`,
  `ValidatorContext`, `_run_per_item`, `gate(`, `pristine_body`, `_check_validator_param`,
  `supersedes_incoming_seqs`, `ROLE_CATALOG_FIELDS`, `RoleSpec`, `_selection_table`, each
  member name, each message fragment). Redirect to a file and read the summary line from the
  file; no `-q` on the command line. Report the selectors. The manager runs the full suite
  afterwards.
- Read `tests/CONVENTIONS.md` before adding a test module: each test lives in the one layer
  its claim needs.
- Comments and docstrings are one or two sentences, with no release versions, ticket ids or
  history. Several comments on this path enumerate catalog members or describe what the gate
  runs (the context docstring, `report()`, `gate()`, the engine's class and module
  docstrings, `_check_validators_assignment`, `RefRule`, `RoleSpec`): the ones this task
  makes false are rewritten to what the code does now, not extended.
- No ticket ids in source or in test names.
- `type X = ...` for aliases. A multi-exception handler is parenthesised and carries
  `# fmt: skip`. No `from __future__ import annotations`.
- User-facing errors are `SquadsError` subclasses; dynamic text printed to the console goes
  through `e()`.
- No module-level mutable state beyond the tables this task extends. A new constant is a
  string, a number or a frozenset.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1001 add-subtask "<title>"`; track with `sq task 1001 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — item_title_max: flag an item title over the declared length

<!-- sq:subtask:ST1:body -->
**Goal.** A `work` or `records` type that names `item_title_max:<n>` reports each of its
items whose title is longer than `n` characters. A type that does not name it reports nothing
at any length. Naming it on a roster type is refused at load.

**Reads.** `item.title`, and the number from the type's own entry. Nothing from the file and
nothing from the index, so at `@error` it can refuse a write.

**Approach**

- Register the member as the task body lists, with `PARAMETERIZED_VALIDATOR_NAMES` and
  `SINGLE_SELECTION_VALIDATOR_NAMES`.
- **The parameter is required.** Unlike `subentity_title_max`, there is no default number.
  Refused at spec load (`_check_validators_assignment` / `_check_validator_param`), naming
  the type and the entry, in the wording of the missing `ref_rule_target_present` target:
  - the bare name, and `item_title_max:` with nothing after the colon: the threshold is
    missing; name it as `item_title_max:<n>` or drop the entry;
  - zero, a negative number, a decimal, a word, a number with a space: not a positive
    integer.
- Where "this member requires its parameter" is decided is one place, which ST8 reuses. The
  existing refusal for `ref_rule_target_present` in `_check_ref_rule_targets` keeps its site
  and its text: the adopter docs quote it.
- **One positive-integer parser** serves this member and `subentity_title_max`. It accepts
  ASCII decimal digits only. The present test is `param.isdigit()` followed by `int(param)`;
  `isdigit()` is true for a superscript digit that `int()` refuses, so that input raises
  instead of being refused (read, not driven). The handoff states what
  `subentity_title_max:²` did before this subtask and what it does after.
- **The refusal of a selection that cannot fire starts here.** Write the Plane-1 function
  the task body describes, with its first rule: a member of the covered-names frozenset
  named on a roster type is refused, the message naming the type, the entry and the reason
  (the check applies to `work` and `records` types). This member is the set's first name.
  Members outside the set (`no_status_banner`, `item_skill_shadowed`, every other existing
  one) stay selectable on a roster type exactly as before.
- `WorkflowSpec.item_title_max(item_type) -> int | None`, the shape of
  `item_subentity_title_max`: `None` when the type is not declared or its effective set does
  not hold the member, otherwise the number of the type's own entry.
- `_services/_validators.py::_item_title_max`: no issue on `None`; one issue when
  `len(item.title) > n`. The message follows the sub-entity title message and carries the
  length and the threshold, for example
  "advisory: title is 121 chars (threshold: 120) — an item title is a one-line handle; put
  the detail in the body". Its fixed fragment is the part no other message holds.
- `tests/integration/test_a_squad_selecting_both_checks_reports_each_offender_once_at_warn.py`
  filters the report on "(threshold:", which this message shares. Tighten that filter to a
  fragment only the sub-entity title message carries. Its expected list does not change.

**At the gate.** With `item_title_max:80@error`: a create with an 81-character title is
refused with the member's message and leaves no file and no index entry; an `update` or
`status` on an item already over the number is refused; `update --title` to 80 characters or
fewer is accepted and is the way out. At `warn` the member is not evaluated on a write.

**Tests**

- Create the member registry and the fragment test in `tests/_selection_table.py`, add the
  `contract` and `milestone` rows, and add this member's entry.
- **Type rows:** every `work` and `records` row accepts; the three roster rows are refusal
  cells, asserted through the loader and through `sq workflow lint`.
- **The roster rule leaves the rest alone:** `no_status_banner` on each roster type still
  loads and reports, as the existing modules assert unedited.
- **Selection shapes:** unselected; `:120`; `:80`; `:80@warn`; `:80@error`; another type
  only (both types driven); on `epic`, the list replaced without the splat form (an epic
  then accepts a parent) and with it (a parent is still refused).
- **Title shapes**, at 80 and at 120: one under, at, one over; a 200-character title; the
  same three lengths made of a non-ASCII letter (the count is characters, not bytes); a
  retitle that crosses the number in each direction.
- **Load refusals** (unit, one table): the bare name; the empty parameter; `0`; `-5`; `1.5`;
  `abc`; a number with a leading space; a superscript digit; two entries with different
  numbers (refused as a repeat); `:80@fatal`; the entry on `role`, on `skill`, on `operator`.
  Accepted: `:1`, `:80`, `:80@warn`, `:80@error`. A leading zero (`:080`) is driven and its
  outcome reported, matching what `subentity_title_max` does.
- **Surfaces:** `Service.check()`; `sq check` text and `--json` with the bare exit code
  (0 at `warn`, 3 at `@error`); `sq workflow lint` for one parameter refusal and one roster
  refusal; create, `update` and `status` at `@error` (service and CLI); `sq import` of an
  item over the number, at `warn` and at `@error`.
- **Invariants** of the task body: unselected silence on every accepting row; the
  effective-set pin unedited; every cell decided; gate and report agree over the title
  shapes.

**Falsify.** Compare with `>=` in the member: every "at the number" row goes red. Restore.
Make the resolver return 120 whatever the entry says: the `:80` rows go red between 81 and
120 characters. Restore. Drop the missing-parameter refusal: the bare and empty rows go red.
Restore. Put the name in the `work` bundle: the unselected rows and the effective-set pin go
red. Restore. Take the name out of the covered-names set: the three roster cells go red.
Restore.

**Acceptance**

- Story 1, all four bullets.
- `tests/meta` passes with the new set members, the covered-names set and the resolver in
  place.

Gates and working rules: the task body.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — ref_rule_target_typed: flag an edge to a type its rule excludes

<!-- sq:subtask:ST2:body -->
**Goal.** A type that names `ref_rule_target_typed` reports each outgoing edge of its items
whose kind has a typed ref rule on that type while the edge points at an item of another
type. It and the existing `ref_rule_target_present` read a bare ref the same way, which
fixes BUG-1003.

**Reads.** `item.refs`, the declaring type's `ref_rules`, the pointed-at item's type through
`ctx.index`, and the spec's default ref kind. The gate holds the index, so at `@error` it can
refuse a write.

**Approach**

- **One shared reading of an item's outgoing refs.** A function in
  `_services/_validators.py` returns each ref as (target id, kind), with an unspelled kind
  resolved to `spec.default_ref_kind()`, as `_services/_refs.py` does. Both ref-rule members
  call it; neither calls `split_ref` on its own.
- **`_ref_rule_target_present` moves onto that reading in the same commit.** Today it
  compares the raw kind, and a bare ref has none, so an edge of the default kind never
  satisfies a rule declared on that kind, whichever way the edge was added (BUG-1003: a
  default kind spelled out is stored bare). Its message, its level, its inertness
  precondition and every other result stay as they are.
- The rules the new member reads are the source item's own type's
  (`spec.item_ref_rules(item.type)`). Allowed targets per kind are the `target` values of
  that type's rules of that kind which declare one.
- **Only a typed rule counts.** A rule with no `target` says nothing about targets: it
  neither makes its kind checked nor widens what a typed rule of the same kind accepts.
- A kind with no typed rule is skipped. A target the index does not hold is skipped:
  `dangling_ref` reports it, once.
- One issue per misdirected edge. The message names the edge (the target id), its kind, the
  type it points at and the allowed target types, sorted.
- **Refused at load on a type that declares no ref rule with a target**: a clause added to
  the cannot-fire function ST1 wrote, the message naming the type, the entry and the missing
  declaration (a `ref_rules` entry with a `target`). Refused on a roster type by the roster
  rule; add the name to the covered-names set.
- **Dropping the target type.** `[selected]` dropping a type strips the rules that targeted
  it (`_strip_ref_rule_targets_of_dropped_types`). A type left with no typed rule that still
  names this member is then refused. Drive that case and put the message in the handoff: an
  adopter must be able to tell from it that the rule went with the dropped type.
- It takes no parameter: `ref_rule_target_typed:contract` is refused with the existing
  "takes no param" message.
- No issue when `ctx.index` is `None`, as `dangling_ref` does.
- The `RefRule` docstring says a typed rule restricts nothing on its own. Keep that true and
  name this member, in one clause, as the check a type selects to have it reported.

**At the gate.** With `@error`: a create carrying a misdirected `--ref` is refused. `ref add`
is not gated, so it writes the edge; `sq check` then exits 3 and the item's next `status` or
`update` is refused until `ref rm` removes the edge. Drive each door and report it. No gate
is added to a ref verb.

**Tests**

- **Rule shapes, for the new member:**
  - the story's shape: `feature` (bundled rule `implements` targeting `contract`) holding an
    `implements` edge to a task (reported), to a contract (silent), to a decision (reported);
  - two typed rules of one kind with different targets: each target silent, a third type
    reported, the message listing both;
  - a typed and an untyped rule of one kind: a wrong-type target is still reported;
  - a kind with an untyped rule only, on a type that also has a typed rule of another kind:
    silent;
  - a kind with no rule (`depends-on`, `targets`): silent;
  - a typed rule on the default kind: a bare ref and the spelled form behave alike, reported
    on a wrong type and silent on the right one;
  - a project-declared kind and a project-declared target type;
  - a dangling target: silent here, and `dangling_ref` reports it exactly once;
  - three misdirected edges on one item: three findings.
- **BUG-1003's reproduction, for `ref_rule_target_present`:** a type with a rule on the
  default kind targeting `milestone` and the member selected. A delivered item with a bare
  edge to a milestone is silent; with the default kind spelled out, silent; with no edge,
  reported. The control, a rule on a non-default kind: an edge of that kind is silent, a
  bare edge and no edge are reported.
- **Both members on one type:** over the edge shapes above, an edge that satisfies
  `ref_rule_target_present` is never reported by `ref_rule_target_typed`.
- **Type rows:** `feature` accepts under the bundled spec; every other bundled `work` and
  `records` row is a refusal cell until its override declares a typed rule, and accepts once
  it does; the roster rows are refusal cells; the target type dropped through `[selected]`
  is a refusal row.
- **Selection shapes:** unselected (the bundled `feature` with a misdirected edge reports
  nothing); bare; `@warn`; `@error`; another type only (both types driven); with a parameter
  (load refusal).
- **Surfaces:** `Service.check()`; `sq check` text and `--json` with the bare exit code;
  `sq workflow lint` for the no-typed-rule refusal; `ref add` followed by `sq check`; create
  with `--ref`; the doors at `@error`.
- The existing tests of `ref_rule_target_present` pass unedited.
- **Invariants** of the task body.

**Falsify.** Remove the dangling-target skip: the dangling row reports twice or raises.
Restore. Make the shared reading return the raw kind: the default-kind rows of both members
go red. Restore. Put `_ref_rule_target_present` back on `split_ref`: BUG-1003's two rows go
red while the new member's stay green. Restore. Let an untyped rule widen the allowed
targets: its row goes red. Restore. Drop the no-typed-rule refusal: its cells go red.
Restore.

**Acceptance**

- Story 2, all five bullets.
- BUG-1003's expected result holds on the dev build, re-driven in a scratch squad with the
  bug's own override and edges; the handoff records the `sq check` output.

Gates and working rules: the task body.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — body_written: flag an item body still at its scaffold

<!-- sq:subtask:ST3:body -->
**Goal.** A `work` or `records` type that names `body_written` reports each of its items
whose body is still the scaffold its creation template rendered. It is the item-level twin of
`subentity_body_written`. Naming it on a roster type is refused at load.

**Reads.** The item's on-disk text (`ctx.raw_text`, its `sq:body` region) and the scaffold a
fresh item of that type would carry. It declares `RAW_TEXT`, so it reports in `sq check` and
does not run at the create/update gate.

**What the context does not carry.** A sub-entity's placeholder is one string on its kind.
An item's scaffold is not: it differs per type, interpolates the item, and a project can
replace the template under `.overrides/templates/items/`. It is derived today by
`ServiceCore.pristine_body(item)`, which re-renders the creation template through the
squad-aware loader, and compared in `_body_mutate` with view tags stripped from both sides.
The validator module cannot import `_services/_base.py`, which imports the engine.

**Approach**

- Move the derivation into a function of `(item, spec)` in a module both
  `_services/_base.py` and `_services/_validators.py` can import with no cycle and no upward
  edge (candidate: beside `creation_template_name` in `_rendering/_engine.py`).
  `ServiceCore.pristine_body` becomes a delegate with the same contract: `None` when the
  template no longer renders for the item.
- Extract the predicate "this body is unwritten" (body text and scaffold in, a boolean out):
  view tags stripped from both sides, prose compared after stripping whitespace, an empty
  prose counted as unwritten, an absent scaffold (`None`) counted as written. `_body_mutate`
  and the member both call it. One definition, so what the overwrite guard lets a plain body
  write replace is exactly what the check reports.
- `_services/_validators.py::_body_written`:
  - reads `ctx.raw_text` in its own body (the `tests/meta` guard refuses a helper that reads
    it) and passes the text on;
  - `VALIDATOR_CONTEXT["body_written"]` is `RAW_TEXT`;
  - silent when the file carries no `sq:body` region, as the sub-entity twin is;
  - one issue otherwise when the predicate holds. Its fragment must not contain, or be
    contained in, the sub-entity twin's "still the placeholder stub": both can fire on one
    item.
- **Roster types are refused at load, not skipped in the member.** Add the name to the
  covered-names set of ST1's roster rule. A role's body is one view tag and an operator's is
  rendered text, so such a file equals its scaffold by construction and every one would be
  reported; a custom skill is a roster item and is refused with the rest. The member carries
  no category test of its own.
- It takes no parameter.
- The scaffold is rendered once per item of a selecting type, per `sq check`. ST9 measures
  the cost on the board copy; do not optimise before that number exists.
- **Limit, reported in the handoff and not fixed here:** an item whose scaffold changed
  after it was created (a template override edited later, a field the scaffold interpolates
  such as a review's `target_ref`) no longer equals its scaffold and reads as written. The
  overwrite guard gives the same answer for the same reason.

**At the gate.** None. With `@error`: a create with no body succeeds, `sq check` reports the
finding at `error` and exits 3, and no door refuses.

**Tests**

- **Scaffold shapes (type rows):** every bundled `work` and `records` type, each of which
  has its own template (`milestone`'s carries a view tag; `contract`'s and `milestone`'s hold
  two placeholder paragraphs; `decision`'s holds empty headings; `review`'s interpolates a
  field); a project-declared type, which renders the generic template naming the type; a
  type whose template is overridden under `.overrides/templates/items/`. The three roster
  rows are refusal cells.
- **Body states**, on every accepting row:
  - created with no body: reported;
  - created with a body (`-m`): silent;
  - written afterwards with the body verb: silent;
  - appended to the scaffold: silent;
  - replaced with text identical to the scaffold: reported;
  - the scaffold with only its surrounding whitespace changed: reported;
  - an empty body region (built in the test if no verb reaches it): reported;
  - no body region in the file: silent;
  - `milestone` with its tag and no prose written: reported; written, with the tag placed
    back: silent;
  - a template that fails to render: silent, and `check()` does not raise.
- **The twin on one item:** a task with an unwritten body and an unwritten subtask, with
  both members effective, reports two findings, one per member.
- **Selection shapes:** unselected; bare; `@warn`; `@error`; another type only (both types
  driven); with a parameter (load refusal); on each roster type (load refusal).
- **Surfaces:** `Service.check()`; `sq check` text and `--json` with the bare exit code;
  `sq import` of an item with no body, at `warn` and at `@error`; create at `@error`.
- **Invariant:** over every accepting row and every body state, the member reports exactly
  when `set_body` without `force` is accepted as a first write.
- The existing tests of the overwrite guard and of `pristine_body` are the net under the
  extraction: they pass unedited.

**Falsify.** Compare without stripping view tags in the member: the `milestone` rows go red.
Restore. Make the member's notion of unwritten differ from the guard's (treat an appended
scaffold as unwritten): the invariant goes red. Restore. Take the name out of the
covered-names set: the roster cells go red, and with the spec now loading, an untouched role
or operator is reported, which is the finding the refusal exists to prevent. Restore. Remove
the member from `VALIDATOR_CONTEXT`: the `tests/meta` context guard goes red. Restore.

**Acceptance**

- Story 3, all four bullets.
- `ServiceCore.pristine_body` and the body-overwrite refusal behave as before: same results,
  same message.
- `uv run --all-extras pyright` shows no new import cycle or private-usage report from the
  moved function.

Gates and working rules: the task body.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — description_present: flag an item with no summary

<!-- sq:subtask:ST4:body -->
**Goal.** A `work` or `records` type that names `description_present` reports each of its
items whose summary (the `description` field, the line list views show) is empty or
whitespace. Naming it on a roster type is refused at load.

**Reads.** `item.description`. Nothing else, so at `@error` it can refuse a write.

**Approach**

- `_services/_validators.py::_description_present`: one issue when
  `item.description.strip()` is empty.
- It takes no parameter. Add the name to the covered-names set of ST1's roster rule.
- The message names the command that sets the summary, built from the item's type and number
  as `_parent_cycle_message` builds its remedy (`sq <type> <n> update --desc "…"`). Every
  type the member can run on has that verb.

**At the gate.** With `@error`: a create without `--desc` is refused and one with it is
accepted; an `update` or `status` on an item with no summary is refused unless the same
command sets one; `update --desc ""` on an item that has one is refused. At `warn` the member
is not evaluated on a write.

**Tests**

- **Summary shapes:** never set; the empty string; spaces only; a tab or a newline only; a
  non-breaking space only; one visible character (silent); a summary set at create (silent);
  a summary set afterwards (the finding clears); a summary cleared afterwards (the finding
  returns).
- **Type rows:** every `work` and `records` row accepts, and on each the clearing step is
  the CLI verb the message names, which is the story's second bullet. The three roster rows
  are refusal cells.
- **Selection shapes:** unselected; bare; `@warn`; `@error`; another type only (both types
  driven); with a parameter (load refusal).
- **Surfaces:** `Service.check()`; `sq check` text and `--json` with the bare exit code;
  `sq create` with and without `--desc`, and `update`, at `@error`.
- **Invariants** of the task body, gate and report over the summary shapes.

**Falsify.** Test for an absent value only, without stripping: the spaces-only, tab-only and
non-breaking-space rows go red. Restore. Delete the `validators` line from the selecting
fixture: every positive row goes red, and no negative passes on its own, because each shares
its fixture with a positive. Restore.

**Acceptance**

- Story 4, all three bullets.

Gates and working rules: the task body.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — assignee_present: flag an active item with no assignee

<!-- sq:subtask:ST5:body -->
**Goal.** A type that names `assignee_present` reports each of its items whose status
resolves to a role declaring `live = true` while nobody is assigned.

**Reads.** `item.status`, the `live` flag of the role it resolves to, and `item.assignee`.
Nothing else, so at `@error` it can refuse a write.

**Approach**

- `_services/_validators.py::_assignee_present`: one issue when
  `spec.role_for(item.status).live` is true and `item.assignee` is empty. That is the
  engine's existing reading of an active status (`first_active_status`, `live_statuses`).
- **No role name and no status name is compared**, and no role-name constant is added. A
  status with no declared role resolves to the fallback role, which is not live, and is
  silent.
- **Refused at load on a type whose lifecycle holds no status of a live role**: a clause
  added to the cannot-fire function, using the validation pass's own `_status_live` over the
  lifecycle's states, the message naming the type, the entry and the missing declaration (a
  status of a role with `live = true`). Under the bundled spec that refuses `decision` and
  `guide`. Refused on a roster type by the roster rule; add the name to the covered-names
  set.
- It takes no parameter.
- The message names the status and says that nobody is assigned.

**At the gate.** With `@error`: `status InProgress` on an unassigned item is refused;
`update --status InProgress --assignee <slug>` in one command is accepted; clearing the
assignee of an item at a live status is refused; assigning first and then moving is the way
through. At `warn` the member is not evaluated on a write.

**Tests**

- **Status shapes, by flag:**
  - every bundled status of a live role that the row's lifecycle holds (`InProgress`,
    `InReview`, `ChangesRequested`, `Fixed`, `Active` on `contract`): reported when
    unassigned;
  - one status of each bundled role that is not live (pending, blocked, attention, done,
    in_force, retired, superseded): silent;
  - the bundled live role renamed by an override and still `live = true`: reported;
  - a project-declared role with `live = true` under another name, on a project-declared
    status: reported;
  - a role named `active` that declares `live = false`: silent. The roster lifecycle must
    keep a live status, so this spec gives the roster's status another live role;
  - a status renamed by an override and still on a live role: reported;
  - a project-declared status given no role: silent.
- **Assignee shapes:** none; the empty string; a role slug; an operator slug; a slug that is
  not registered (silent here: `agent_registered` reports that).
- **Type rows:** `epic`, `feature`, `task`, `bug`, `review`, `contract`, `milestone` and the
  project-declared rows accept; `decision` and `guide` are refusal cells, and each accepts
  once an override gives its lifecycle a status of a live role; the roster rows are refusal
  cells.
- **Selection shapes:** unselected; bare; `@warn`; `@error`; another type only (both types
  driven); with a parameter (load refusal).
- **Surfaces:** `Service.check()`; `sq check` text and `--json` with the bare exit code;
  `sq workflow lint` for the no-live-status refusal; `status` and `update` at `@error`,
  service and CLI.
- **Invariants** of the task body, gate and report over the status and assignee shapes.

**Falsify.** Compare the role name with "active" in place of the flag: the renamed-role row,
the project-role row and the `live = false` row go red. Restore. Treat only an absent
assignee as empty, not the empty string: that row goes red. Restore. Drop the
no-live-status refusal: the `decision` and `guide` cells go red. Restore.

**Acceptance**

- Story 5, all four bullets.

Gates and working rules: the task body.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — blocked_has_blocker: flag a blocked item with no dependency edge

<!-- sq:subtask:ST6:body -->
**Order.** Built after ST10, and only once the manager has given the confirmation the task
body's hard stop requires.

**Goal.** A type that names `blocked_has_blocker` reports each of its items whose status
resolves to a role declaring `blocked = true` while no edge of a dependency-role ref kind
touches it, in either direction.

**Reads.** `item.status` and the `blocked` flag of the role it resolves to (ST10), the kinds
of `item.refs`, the spec's dependency ref kinds, and whether any other item holds a
dependency edge to this one.

**What the context does not carry.** The validator context holds outgoing refs on the item
and nothing about incoming dependency edges. `SquadsDB.backrefs` answers that with a walk of
the whole index per call, which the context exists to avoid.

**Approach**

- Add one aggregate to `ValidatorContext`, in the shape of `supersedes_incoming`:
  `dependency_incoming: frozenset[int]`, the sequence numbers of every item that some item's
  ref of a dependency-role kind points at, by sequence number (`number_for_id`), so a ref
  stored at another id width still matches.
- **One builder returns both incoming-edge sets from one pass over the refs.** It replaces
  the pass that builds `supersedes_incoming` today; `report()` calls it once per run and
  `gate()` once per call. The gate therefore walks the index as many times as it did, and
  the member gets a true answer there. `supersedes_incoming_seqs` has callers in `tests/`:
  keep it as a thin reading of the shared builder or move those callers, and say which.
- It is **not** a `ContextRequirement`: both paths carry it, and an empty set is a real
  value (a squad with no dependency edge) that `held_context`'s truthiness test would read as
  absent and skip the member on.
- Search `src/` and `tests/` for `ValidatorContext(` and `_run_per_item(`: every caller is
  read, and `_import.py::_board_debt_findings` gets the aggregate through `report()`.
- `_services/_validators.py::_blocked_has_blocker`: no issue unless
  `spec.role_for(item.status).blocked` is true; satisfied by any outgoing ref whose kind is
  in `spec.dependency_ref_kinds()`, or by the item's sequence number being in
  `dependency_incoming`; one issue otherwise.
- **No role name, no status name and no kind name is compared.** Kinds are matched by their
  declared role. An unspelled ref is the default kind, which cannot carry the dependency
  role, so it never satisfies.
- An outgoing dependency edge to a missing item still counts as an edge (`dangling_ref`
  reports the target). An edge to or from a settled item counts too: this member asks
  whether the blocker is recorded, not whether it is open.
- **Refused at load**, each a clause of the cannot-fire function, the message naming the
  type, the entry and the missing declaration:
  - on a type whose lifecycle holds no status of a role declaring `blocked = true` (the
    message names the flag);
  - in a spec that declares no dependency-role ref kind;
  - on a roster type, by the roster rule (add the name to the covered-names set).
- It takes no parameter: `blocked_has_blocker:blocked` is refused with the existing "takes
  no param" message. It joins neither `PARAMETERIZED_VALIDATOR_NAMES` nor a selection set.
- The message names the status and the dependency kinds the spec declares.

**At the gate.** With `@error`: `status Blocked` is refused while no edge exists and
accepted once one does, whether the edge is the item's own or another item's pointing at it.
`ref rm` is not gated: removing the last edge, here or on another item, leaves a state
`sq check` reports and that refuses the item's next gated write. The way out is always on
the item: `ref add`, which is not gated, or a status move. At `warn` the member is not
evaluated on a write.

**Tests**

- **Edge shapes**, on an item at a status of a blocked-flag role:
  - no ref at all: reported;
  - an outgoing ref of each dependency kind: silent;
  - an incoming ref of each dependency kind from another item: silent;
  - both directions: silent;
  - only refs of other kinds (an unspelled one, `targets`, `implements`): reported;
  - a ref of a dependency kind that an override renamed: silent;
  - an outgoing dependency ref to an id that does not exist: silent here, `dangling_ref`
    reports;
  - an incoming ref written at another id width: silent;
  - an incoming ref from an item of another type, and from a settled item: silent;
  - the incoming ref removed from the other item: reported on the next check.
- **Status shapes, by flag:**
  - the bundled `Blocked` status: reported with no edge;
  - the bundled role renamed by an override and still `blocked = true`: reported;
  - a project-declared role with `blocked = true` under another name: reported;
  - a role named `blocked` whose flag is false: silent, and the selection is refused if no
    other status of the lifecycle is flagged;
  - one status of each role that does not declare the flag: silent with no ref.
- **Type rows:** `epic`, `feature`, `task`, `bug` accept under the bundled spec; `review`,
  `decision`, `contract`, `milestone`, `guide` are refusal cells, and each accepts once an
  override gives its lifecycle a status of a flagged role; the roster rows are refusal cells.
- **Spec shapes:** a spec with no dependency-role ref kind is refused for every selecting
  type; a squad that declares its own roles and flags none is refused, naming the flag, and
  loads once one role declares it.
- **Selection shapes:** unselected; bare; `@warn`; `@error`; another type only (both types
  driven); with a parameter (load refusal).
- **Surfaces:** `Service.check()`; `sq check` text and `--json` with the bare exit code;
  `sq workflow lint` for each refusal; `status` at `@error` with the edge added first on the
  item, and with it added on another item, service and CLI; `ref rm` then `sq check`.
- **The supersession half is unchanged:** the existing tests of `supersedes_incoming` pass
  unedited, apart from any caller of the builder that the Approach moves.
- **Invariants** of the task body, gate and report over the edge shapes. The fragment test,
  the unselected-squad test and the every-cell test now cover eight members.
- Run `uv run --all-extras pytest tests/test_scale.py --run-slow` once after this subtask
  and report its summary line beside the baseline's.

**Falsify.** Drop the incoming half of the member: the incoming rows go red. Restore. Leave
the aggregate at its empty default in `gate()`: the row "incoming edge only, `@error`,
`status Blocked` accepted" goes red while every `check()` row stays green. Restore. Compare
the role name with "blocked" in place of the flag: the renamed-role, project-role and
flag-false rows go red. Restore. Match the kind names literally: the renamed-kind row goes
red. Restore. Drop one supersession kind from the shared builder's pass: an existing
`supersedes_incoming` test goes red. Restore.

**Acceptance**

- Story 6, all five bullets.
- `gate()` walks the index no more times than before this subtask.
- With this subtask the eight are complete: the unselected reading of ST9 (its step 4) is
  taken again on the final tree and is still byte-identical.

Gates and working rules: the task body.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — settled_requires_discussion: flag a settled item with no comment

<!-- sq:subtask:ST7:body -->
**Goal.** A `work` or `records` type that names `settled_requires_discussion` reports each
of its items whose status resolves to a role declaring `settled = true` while its own
discussion holds no comment. Naming it on a roster type is refused at load.

**Reads.** `item.status`, the `settled` flag of the role it resolves to, and the item's
on-disk text (`ctx.raw_text`, its `sq:discussion` region). It declares `RAW_TEXT`, so it
reports in `sq check` and does not run at the create/update gate: a transition to a settled
status is never refused or delayed by it, at any level.

**Approach**

- "Settled" is the flag on the role, `spec.role_for(item.status).settled`, not a role name
  and not a status name. In the bundled spec it covers the `done`, `in_force`, `retired` and
  `superseded` roles; a project-declared role with `settled = true` is covered the same way.
- `_services/_validators.py::_settled_requires_discussion`:
  - reads `ctx.raw_text` in its own body and takes the discussion region with
    `sections.get_section(text, markers.DISCUSSION)`;
  - counts comments with `discussion.split_discussion`, never with a pattern of its own: the
    comment header format is that parser's to define, and a second pattern would drift from
    it;
  - one issue when the status is settled and the parser returns no comment. A file with no
    discussion region holds no comment and is reported.
- **The item's own discussion only.** A comment on one of its stories, subtasks or findings
  does not count, and one top-level comment on the item clears the finding.
- `VALIDATOR_CONTEXT["settled_requires_discussion"]` is `RAW_TEXT`.
- It takes no parameter. Add the name to the covered-names set of ST1's roster rule. No
  other load refusal applies: every lifecycle already has to reach a settled status.
- The message names the status and says the discussion holds no comment.

**At the gate.** None. With `@error`: the transition to a settled status succeeds, `sq check`
then reports the finding at `error` and exits 3, and one comment clears it.

**Tests**

- **Status shapes, by flag:**
  - one status of each bundled settled role that the row's lifecycle reaches (for example
    `Done`, `Cancelled`, `Accepted`, `Superseded`, `Approved`, `Published`): reported with an
    empty discussion;
  - one status of each non-settled role (pending, active, blocked, attention): silent;
  - a settled role renamed by an override: reported;
  - a status renamed by an override and still on a settled role: reported;
  - a project-declared role with `settled = true` on a project-declared status: reported.
- **Discussion shapes**, on a settled item:
  - the region as created, empty: reported;
  - whitespace only: reported;
  - one comment: silent;
  - several comments, one with several bullets and one with a fenced code block: silent;
  - a comment written as an operator: silent;
  - text in the region with no comment header: reported;
  - a settled feature whose only comment sits on one of its stories: reported; the same for
    a task and a subtask, a review and a finding;
  - one top-level comment added to that item: the finding clears;
  - a comment added after the item settled: the finding clears.
- **Type rows:** every `work` and `records` row accepts; the three roster rows are refusal
  cells.
- **Selection shapes:** unselected; bare; `@warn`; `@error`; another type only (both types
  driven); with a parameter (load refusal).
- **Surfaces:** `Service.check()`; `sq check` text and `--json` with the bare exit code; the
  `status` verb to a settled status at `@error`, service and CLI, exit 0.
- **Invariants** of the task body: no door refuses at any level.

**Falsify.** Compare the role name with `done` in place of the settled flag: the
`Cancelled`, `Accepted`, renamed-role and declared-role rows go red. Restore. Test that the
region is non-empty in place of parsing it: the row with text and no comment header goes
red. Restore. Count sub-entity comments too: the story, subtask and finding rows go red.
Restore. Remove the member from `VALIDATOR_CONTEXT`: the `tests/meta` context guard goes red.
Restore.

**Acceptance**

- Story 7, all five bullets.

Gates and working rules: the task body.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — external_id_not_in_title: flag a tracker id in a title

<!-- sq:subtask:ST8:body -->
**Goal.** A `work` or `records` type that names `external_id_not_in_title:<regex>` reports
each of its items whose title matches the pattern, naming the matched text. Naming it on a
roster type is refused at load.

**Reads.** `item.title`, and the pattern from the type's own entry. Nothing from the file and
nothing from the index, so at `@error` it can refuse a write.

**Approach**

- Register the member as the task body lists, with `PARAMETERIZED_VALIDATOR_NAMES` and
  `SINGLE_SELECTION_VALIDATOR_NAMES`: one pattern per type, and several trackers are one
  alternation. Add the name to the covered-names set of ST1's roster rule.
- **The parameter is a regular expression, required, and compiled at load.** Refused at spec
  load, naming the type and the entry, through the machinery ST1 put in place:
  - the bare name, and `external_id_not_in_title:` with nothing after the colon: the pattern
    is missing;
  - a pattern `re.compile` rejects: the refusal carries the compile error's own text.
- **The reserved `@`.** `parse_validator_entry` cuts an entry at its first `@`, so a pattern
  cannot hold one: `external_id_not_in_title:user@host` parses as the pattern `user` at the
  level `host`. For this member, an entry whose level part is not a declared level is refused
  with one message that covers both readings: `@` separates the pattern from the level
  (`error` or `warn`), it cannot appear in the pattern, and a literal `@` is written `\x40`.
  The generic unknown-level message is not emitted beside it. An entry such as
  `...:foo@warn` is the pattern `foo` at `warn` and is accepted; that is the grammar, and the
  handoff states it for the writer.
- `WorkflowSpec.item_external_id_pattern(item_type) -> str | None`, the shape of ST1's
  resolver. It takes the parameter whole from `parse_validator_entry`: everything after the
  first colon is the pattern, further colons included.
- `_services/_validators.py::_external_id_not_in_title`: no issue on `None`; `re.search` of
  the pattern in the title, with no flags (an adopter writes `(?i)` in the pattern); one
  issue on a match, naming the matched text and the pattern.
- **Nothing bounds a match, and that is the adopter's own risk.** No timeout, no length cap
  and no rewriting of the pattern is added. What the engine does about it is ST11: a member
  that cannot refuse is not run on a write, so the pattern runs under the index lock only
  for a type that selects the check at `@error`. The handoff carries the sentence the task
  body gives for the writer, checked against the build.
- **TOML quoting.** A backslash in a TOML basic string must be doubled; a literal string
  (single quotes) takes the pattern as written. The table writes this member's entries as
  literal strings. An entry in a basic string with a single backslash fails in the TOML
  parser before the spec is read: drive it once and record the message an adopter sees.

**At the gate.** With `@error`: a create whose title matches is refused with the member's
message; an `update` or `status` on a matching item is refused; a retitle that no longer
matches is accepted and is the way out. At `warn` the member is not evaluated on a write.

**Tests**

- **Pattern shapes:**
  - the story's shape, a tracker key (letters, hyphen, digits): a title carrying one is
    reported with the key named, a title without one is silent;
  - the key at the start, in the middle and at the end of the title: reported (search, not
    full match);
  - an anchored pattern: reported only where the anchor allows;
  - a pattern containing a colon: used whole;
  - a pattern with `\x40`: reports a title containing `@`. This row is what entitles the
    refusal message to offer that spelling; if it fails, the message offers nothing;
  - `(?i)` inline: reports a lower-case key that the plain pattern leaves silent;
  - an alternation of two trackers: either is reported;
  - two keys in one title: one finding, naming the first match;
  - a pattern and a title with square brackets: the `sq check` text shows both intact.
- **Where the pattern runs**, with the member's function wrapped to count calls: `check()`
  calls it for every item of a selecting type at either level; a gated write calls it at
  `@error` and does not call it at `warn`.
- **Load refusals** (unit, one table): the bare name; the empty parameter; an unterminated
  character set; an unbalanced parenthesis; `user@host`; `a@b@error`; a valid pattern with
  `@fatal`; two entries with different patterns (refused as a repeat); a valid entry on
  `role`, on `skill`, on `operator`. Accepted: a valid pattern alone, with `@warn`, with
  `@error`.
- **Type rows:** every `work` and `records` row accepts; the three roster rows are refusal
  cells.
- **Selection shapes:** unselected; pattern alone; `@warn`; `@error`; another type only
  (both types driven); on `epic`, the list replaced without and with the splat form.
- **Surfaces:** `Service.check()`; `sq check` text and `--json` with the bare exit code;
  `sq workflow lint` for one refusal; create, `update` and `status` at `@error`.
- **Invariants** of the task body, gate and report over the pattern shapes.

**Falsify.** Use `re.match` in the member: the middle and end rows go red. Restore. Make the
resolver split the parameter again on a colon: the colon row goes red. Restore. Drop the
compile check at load: the unterminated-set row goes red; note in the handoff what the
runtime does with that pattern while the check is off. Restore. Emit the generic
unknown-level message for `user@host`: its row goes red. Restore.

**Acceptance**

- Story 8, all four bullets.
- The handoff carries the warning sentence for the writer, with "at `@error`" as the build
  behaves.

Gates and working rules: the task body.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Prove the two-check selection on a copy of this squad

<!-- sq:subtask:ST9:body -->
**Goal.** A squad that selects `item_title_max:120` and `body_written` on every `work` and
`records` type gets both findings and keeps every validator its types ran before; its roster
types keep their lists unchanged; and a squad that selects neither sees nothing. Proven in
tests on a fixture squad, and driven on a scratch copy of this repository's squad. This
repository's own override file is not edited.

**Approach: the automated half**

- **The override text is written by the test, from the bundled spec.** A function in
  `tests/_selection_table.py` builds it: for each bundled `work` or `records` type, the splat
  of its bundled list where it ships one, then `item_title_max:120`, then `body_written`. The
  roster types get no table. It never reads `squads/.overrides/workflow.toml`: that file
  gains these entries at release preparation, and a test that extended it would then select
  each twice.
- A second variant adds `no_status_banner` on every type, roster types included, and
  `subentity_title_max:120` on the `work` types, the selections a squad may already hold, to
  show the four live together and that a roster list naming an older check still loads.
- **A table over every bundled type** (one test asserts every bundled type has a row):
  - the merged spec's effective validators contain the bundled spec's, compared as (name,
    parameter, resolved level);
  - on the nine `work` and `records` types, `item_title_max` is effective with parameter 120
    at `warn`, `spec.item_title_max(<type>)` is 120, and `body_written` is effective at
    `warn`;
  - on the three roster types neither name is effective and the effective set equals the
    bundled one;
  - under the bundled spec neither name is effective for any type.
- **A fixture squad**, one `work` or `records` row at a time: an item with a 121-character
  title, one with a 120-character title, one with no body written, one with a body. The
  comparison is the report filtered to the two members' fragments against a literal expected
  list of (level, item id, message): 121 warns and 120 is clean; an unwritten body warns. The
  squad also holds one role, one skill and one operator as created, and none of them appears
  in the list.
- **Roster refusal.** The generated override with either entry added to a roster type is
  refused at load, naming the type and the entry.
- **Unselected.** The same fixture squad with no override, and a fresh `sq init`, report no
  finding carrying either fragment, and no `.overrides/workflow.toml` exists after `sq init`.
- **CLI smoke**, in a test squad carrying the generated override: `sq workflow lint` exits 0
  with no error or warning; `sq override list` exits 0 and shows `workflow` as `current`;
  `sq check` exits 0 with the two warnings printed; `sq check --json` carries the item ids.

**Approach: the driven half, on a scratch copy**

Every step runs in a directory nested under the session scratchpad. Each writing command is
preceded by `pwd` in the same `&&` chain. The dev build is the worktree's, run with the copy
as the working directory.

1. **Before the first edit of the task**, at the verified fork point, extract the committed
   board: `git archive HEAD squads .squads.toml .claude CLAUDE.md | tar -x -C <scratch>/copy`.
   Tracked files only: a plain copy of `.claude/` would bring the worktrees directory with
   it. Record the commit.
2. In the copy, with the dev build of the untouched tree: `sq check --json`, saved as the
   "before" reading with its bare exit code. Time one `sq check`.
3. If the dev build refuses the copy because the branch carries a later schema, run the dev
   build's `sq migrate up` in the copy, then take step 2. Never in a checkout.
4. **After the last subtask of part one**, on a fresh extraction of the same commit
   (migrated the same way if step 3 applied), with no change to its override:
   `sq check --json` is byte-identical to the "before" reading. That is the story's last
   bullet on the real corpus: a squad that selects nothing reports the same issues before and
   after. If `release/0.16` was merged into the branch in between, the "before" reading is
   retaken with a build of the merged base that holds none of this task's commits (an archive
   of it, extracted and synced in the scratchpad). The same reading is taken once more at the
   end of part two.
5. In the copy's own `squads/.overrides/workflow.toml`, add `"item_title_max:120"` and
   `"body_written"` to the nine `work` and `records` tables, leaving every existing line and
   the three roster tables as they are. `sq workflow lint` reports the spec valid and exits
   0; `sq override list` shows `workflow` as `current`. Loaded with `load_workflow_spec` on
   the copy, each type's effective validators contain the bundled spec's, compared as (name,
   parameter, level).
6. `sq check --json` on the extended copy, before planting anything. Record, per member and
   per type, how many findings the existing corpus produces, with the ids when there are
   twenty or fewer. That count is what release preparation needs before the selection lands
   here. Time one `sq check` and report it beside step 2's.
7. Plant with the dev build: a 121-character and a 120-character title on a `work` type and
   on a `records` type; an item with no body on a `work` type and on a `records` type. Then:
   121 warns and 120 is clean; both unwritten bodies warn; no role, skill or operator is
   reported by either member; each finding carries the planted id; `sq check` exits 0.
8. Remove the two entries from one type's table in the copy: that type's planted findings go
   and the other type's stay.
9. Add `"body_written"` to the copy's `[items.role]` table: `sq workflow lint` refuses the
   spec, naming `role` and the entry. Remove it again.
10. In the worktree: `git diff --stat release/0.16...HEAD -- squads/` prints nothing. From
    the main checkout, the released tool's `sq check` is clean.

The handoff records each command with its exit code and labels every claim driven or read.

**Falsify.** In the generated override, drop the splat on `epic`: its containment row goes
red. Restore. Change `:120` to `:121`: the fixture comparison goes red on the 121-character
item of every row. Restore. Drop `body_written` from one `records` type: its table row and
its fixture row go red. Restore.

**Acceptance**

- Story 9, all four bullets: the first two by the table, the fixture and steps 5 to 9; the
  third by the unselected tests and step 4; the fourth by step 10.
- No test added by this task reads this repository's override file.

Gates and working rules: the task body.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — Let a status role declare that it means blocked

<!-- sq:subtask:ST10:body -->
**Order.** First subtask of part two. It is not started until the manager has confirmed, in a
comment on this task, that the working version is 0.16.0 and that `release/0.16` carries the
bump. Then: merge `release/0.16`, check the fork point, and check that `[project].version` in
the worktree's `pyproject.toml` reads 0.16.0. This subtask edits a bundled file.

**Goal.** A status role can declare that it means blocked, with a boolean `blocked` key
beside `settled`, `hidden`, `color` and `live`. The bundled `blocked` role declares it. The
role catalog shows it. Nothing reads it yet; ST6 is its first reader.

**Approach**

- `_workflow/_models.py::RoleSpec` gains `blocked`, default false. No floor and no
  cross-check: nothing in the engine requires a blocked role to exist. Its part of the class
  docstring is a sentence: the role's statuses mean the item is waiting on something else.
- **A non-boolean value is refused at load, naming the role and the key.** `_parse_role`
  validates with `RoleSpec.model_validate` and plain `bool` fields, which accepts some
  strings and integers (read, not driven), so the new field needs a strict boolean. What
  `live = "yes"` does today is driven and reported in the handoff, not changed.
- A validation-pass reading beside `_status_live` (the same lookup, the `blocked` flag), for
  ST6's load refusal, and whatever accessor on `WorkflowSpec` ST6 will read, in the shape of
  the `live` ones.
- `_specs/workflow.toml`: `[roles.blocked]` gains `blocked = true`, and the comment above the
  role table gains one clause for the flag. No other bundled role declares it. This is the
  only bundled file the task edits.
- `_cli/_workflow_cmd.py`: `ROLE_CATALOG_FIELDS` grows to six with `blocked` last;
  `_role_catalog` emits it on every row; the human table gains a column; the command's
  docstring names the key. The five existing keys keep their names, types, values and order.
- **No other consumer reads the flag.** `sq blocked` and the `blocked` key of
  `sq tree --json` are computed from dependency edges and stay unrelated to it.
- **Bundled bytes.** After the bundled line is in, run the manifest steps of the task body
  ("Bundled bytes and the version") and commit the regenerated manifest and content store
  with this subtask.
- **Two things this subtask reports and does not fix:**
  - `clients/vscode/test/canary/skewCanary.test.ts` compares the `active` row of the role
    catalog with an exact five-key object, and the client has its own row type and fixture
    (read, not driven). A sixth key is expected to turn that comparison red. Nothing under
    `clients/` is edited here; say in the handoff whether the canary was run and what it
    did, so the client change can land with this one.
  - `tests/cli/test_this_repositorys_workflow_override_loads_clean_cli.py` copies this
    repository's override, stamped 0.15.0, and asserts `sq override list` shows it as
    `current`. Drift is decided on the bundled document's content, so this edit is expected
    to turn it red unless an earlier change already did. `squads/.overrides/workflow.toml`
    is not edited from here: report the result and stop on that test for the manager.

**Tests**

- **Declaration shapes** (unit, one table): omitted (false); `true`; `false`; a string;
  an integer; a list. The three non-booleans are refused, naming the role and the key.
- **Spec shapes:**
  - the bundled spec: exactly one role declares the flag, the one named `blocked`;
  - an override that changes only another key of the bundled `blocked` role: the flag
    survives the merge;
  - an override that declares a role of its own with `blocked = true`: flagged;
  - a squad that declares its own roles and drops the bundled one: no role is flagged, and
    the spec loads.
- **The catalog:** `sq workflow roles --json` rows carry exactly the six keys in order, with
  `blocked` true on the bundled `blocked` row and false on the other seven; the five earlier
  keys of every row equal what they were (compare with the golden before it is regenerated);
  the text output shows the column; a project-declared flagged role shows in both.
- **Nothing else reads it.** On one squad with dependency edges and items at `Blocked`:
  `sq blocked` and `sq tree --json` give the same output with the flag true on the role
  those statuses carry and with an override setting it to false.
- **Upgrade.** A squad whose override predates the flag loads unchanged, and its
  `sq check --json` is byte-identical before and after this subtask.
- **Freshness**, as the task body lists: the manifest check, the freshness module, the role
  catalog goldens, and `tests/meta`, `tests/integration` and `tests/cli` run whole.
- Service-level: the spec accessors. CLI smoke: `sq workflow roles`, `--json`, and
  `sq workflow lint` on a non-boolean value, bare exit codes.

**Falsify.** Make the field a plain boolean: the string and integer rows go red. Restore.
Emit the key only where it is true: the six-key row test goes red on seven rows. Restore.
Leave the manifest unregenerated: `scripts/gen_template_manifest.py --check` and the
freshness module go red. Restore. Read the flag in `sq blocked`'s computation: the
nothing-else-reads-it test goes red. Restore.

**Acceptance**

- Story 11, all six bullets. The sixth, the record in the documentation, is the handoff line
  to TASK-1002: the key, its default, the bundled role that declares it, the sixth catalog
  key, and what a squad that declares its own roles must add.
- `git diff --stat` for this commit lists `_specs/workflow.toml`, the manifest, the content
  store, the role model, the catalog command, the goldens and tests, and nothing under
  `squads/`, `clients/` or `_rendering/templates/`.

Gates and working rules: the task body.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->

<!-- sq:subtask:ST11 -->
### ST11 — Run only the checks that can refuse at the create/update gate

<!-- sq:subtask:ST11:body -->
**Order.** First subtask of the task, before any member is added. It changes the engine only.

**Goal.** At the create/update gate, a member whose resolved level for the item's type is
`warn` is not run. The gate refuses exactly the writes it refused before.

**Why.** `ValidatorEngine.gate` runs every effective member the context allows and only then
keeps the `error` findings (read, not driven), so a member that cannot refuse still runs
under the index lock on every gated write. ST8 puts an adopter's regular expression in the
catalog, and nothing bounds a match: at the default level a pattern that backtracks would
hang every write of a selecting type with the lock held, which blocks every other mutation
of the squad. With this subtask that can happen only where the type selects the check at
`@error`. It also takes every other advisory member off the write path, for every squad.

**Approach**

- `_services/_validators.py::ValidatorEngine._run_per_item` takes one more keyword, set by
  `gate()` and not by `report()`: when it is set, a member is skipped unless
  `_resolved_level(ctx, bare)` is `error`. The resolver is the one each member already uses
  for its own findings, so the gate and the member cannot disagree about the level.
- The skip sits beside the existing context filter (`VALIDATOR_CONTEXT`), in the same loop,
  and is decided per bare name, once.
- `gate()` keeps its filter on `error` findings.
- `report()` is unchanged: `sq check` and the importer's findings run every effective member
  at every level.
- **The one outcome that differs, and is intended:** a `warn`-level member that raises no
  longer aborts a write. Say so in the handoff.
- The docstrings of `gate()`, of the class and of the module say what the gate runs now, in a
  sentence or two each.

**Tests**

- **Over the whole catalog, one table** (unit, with each member's function wrapped to count
  calls, passed through the engine's `catalog` argument): for every member name, at `warn`
  the gate does not call it; at `error` the gate calls it. A member's level is set through
  the type's `validators` entry, and for a member whose floor forbids `warn` the row is
  `error` only.
- **Decisions are unchanged:** for each existing member that has a gate test, the write that
  was refused at `error` is still refused with the same message, and the write that was
  accepted at `warn` is still accepted. The existing modules assert this and pass unedited,
  `tests/service/test_declared_validator_level_governs_report_and_gate.py` among them.
- **A member that needs context the gate lacks** is still skipped at `error`
  (`subentity_container_marker`, `no_status_banner@error`).
- **A raising member:** a stub registered under a `warn`-level name that raises does not
  abort a gated write, and does abort when the name is selected at `@error`.
- **`report()` still runs everything:** the same wrapped catalog, through `report()`, calls
  every effective member at both levels.
- Service-level: `Service.create` and `Service.update` on a type with one member at `warn`
  and one at `@error`. CLI smoke: the same through `sq create` and
  `sq <type> <n> update`, bare exit codes.
- A stub test that registers an `error` finding under a name whose resolved level is `warn`
  describes a state the level guard forbids. If one turns red, move it onto a declared level
  and list it in the handoff.

**Falsify.** Remove the skip: the "not called at `warn`" rows go red and every decision test
stays green, which is the proof that no decision depended on it. Restore. Invert it (skip at
`error`): the existing gate refusal tests go red. Restore. Apply it in `report()` too: the
`warn` findings of `sq check` disappear and the existing check tests go red. Restore.

**Acceptance**

- The targeted baseline of the task body passes after this subtask with no test edited,
  apart from any stub test moved as described.
- The handoff states, for the tech writer: a check selected at `warn` is not evaluated on a
  write.

Gates and working rules: the task body.
<!-- sq:subtask:ST11:body:end -->

#### Discussion

<!-- sq:subtask:ST11:discussion -->
<!-- sq:subtask:ST11:discussion:end -->
<!-- sq:subtask:ST11:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-12T05:48:42Z] Olivia Lead:
  - 2026-10-12: breakdown of FEAT-901 drafted. Both tasks are Draft and unassigned, nothing is promoted and no developer is briefed. @manager
    
    - TASK-1001 (python developer) covers stories 1 to 9, one subtask per story, ST1 to ST9 in story order. TASK-1002 (tech writer) depends on it and on TASK-997, which rewrites the same docs section. FEAT-901 has no documentation story, so TASK-1002's subtasks map to none.
    - One developer task: all eight members edit the same name tables and the same catalog, with one owner and one shipping increment.
    - Two members need something the validator context does not carry. `body_written`: the scaffold is derived by a service method the validator module cannot import, so it moves to a shared function and the "unwritten" test is shared with the body-overwrite guard. `blocked_has_blocker`: incoming dependency edges, added as one aggregate supplied on the report path and the gate path. The other six read what the context holds.
    - No bundled byte changes (no spec file, template, content store or scaffold text), so this does not wait for the working-version bump.
    - Everything about the code in these bodies is read at 4b23b04c, not driven. The task body lists the readings the developer must prove.
    - Calls made in drafting that the architect may want to overrule: (1) `assignee_present` and `blocked_has_blocker` are the first engine bindings to the role names `active` and `blocked`; a spec with no role of that name leaves the member silent and still loads. (2) Six members run at the create/update gate, `blocked_has_blocker` among them, which costs one more index walk per gated write for every squad. (3) The pattern of `external_id_not_in_title` is compiled at load and nothing bounds its cost at run time.
    - Calls the product owner may want to overrule: (4) no CLI verb changes a roster item's title, summary or assignee, so a finding of four of these members on a roster type has no verb that clears it; `body_written` is silent on every roster type, a custom skill included. (5) `settled_requires_discussion` counts the item's own discussion, not a sub-entity's. (6) For `ref_rule_target_typed` only a rule that declares a target counts, and a selection that can never fire loads without a refusal.
    - One existing defect read on the way: `subentity_title_max` with a non-ASCII digit as its number would raise instead of being refused. ST1 closes it with the parser both members share.
- [2026-10-12T05:59:23Z] Robert Architect:
  - @tech-lead Rulings on the three drafting calls, 2026-10-12. Two are recorded as dated notes in ADR-864 Part 2 (at `blocked_has_blocker` and at `external_id_not_in_title`), with the squad-scope half in ADR-982 clause 4. The gate ruling is this comment. All code claims are read at `1b2e57e5`; nothing was driven. For op-pierre to confirm, since they amend two accepted decisions.
    
    **1. Roles: overruled. No role-name constant.**
    
    - ADR-696 section 3 already rules it: "No role name is engine-bound at all except the fallback role", on op-pierre's 2026-07-30 comment there ("do not key it off a role name"). `active` and `blocked` are keys of `[roles]`, an open map a project may rename or drop (read: `RoleSpec`, "Roles are an OPEN vocabulary"). What the engine binds to is a role's declared properties.
    - **`assignee_present` reads `spec.role_for(item.status).live`.** That is the engine's existing definition of an active status (read: `first_active_status`). No constant beside `FALLBACK_ROLE_NAME`.
    - **`blocked_has_blocker` takes the role as a required parameter: `blocked_has_blocker:<role>`.** No role property means "blocked", so the squad's own selection names the role, the way `ref_rule_target_present:<type>` names a type. Compare the status's resolved role name (a role-less status resolves to the fallback role) with the parameter.
    - **A selection that can never fire, or never be cleared, is refused at load** and so shown by `sq workflow lint`, on the precedent of `_check_ref_rule_targets` (read: "refused here rather than silently doing nothing forever"). Never silent, and never dependent on what the corpus holds.
    
    **2. `blocked_has_blocker` at the gate: confirmed, with no extra walk.**
    
    - ADR-541 gives one engine and two call sites, and ADR-864's correction lets a member sit out the gate only by declaring context the gate cannot hold. The gate holds the index, so there is nothing to declare.
    - A squad that selects it at `@error` wants exactly one thing: `status <blocked>` refused while no blocker is recorded. Report-only would accept that write and leave `sq check` to say so afterwards.
    - The cost objection is removed, not accepted: build `dependency_incoming` in the single pass over refs that already builds `supersedes_incoming`, on both paths. One builder returns both sets. `gate()` then walks the index as many times as it does today.
    - Known and accepted: ref verbs are ungated, so `ref rm` here or on another item can put an item into the state. The remedy is always on the item (`ref add`, ungated, or a status move), so nothing is stranded.
    
    **3. `external_id_not_in_title`: a template, not a regular expression.**
    
    - Nothing in the standard library bounds a `re` match. There is no timeout; a signal alarm works only on the main thread and not on Windows; a child process per gated write is out of proportion; a length cap does not help, because backtracking is exponential at thirty characters. Report-only would still hang `sq check`.
    - So no adopter text reaches `re` unescaped. The parameter is literal text plus `{d}` (one or more ASCII digits) and `{A}` (one or more ASCII upper-case letters). `{A}-{d}` is story 8's tracker key.
    - Matched anywhere in the title, never starting or ending inside a run of ASCII letters and digits, case-sensitive, first match reported. Either a hand scanner or an engine-built expression (`re.escape` for literals, possessive classes) is acceptable; cost is title length times template length.
    
    **What the subtasks must change**
    
    - **Task body.** "What a member registers": ST6 joins `PARAMETERIZED_VALIDATOR_NAMES` and `SINGLE_SELECTION_VALIDATOR_NAMES`; ST8 moves to `MULTI_SELECTION_VALIDATOR_NAMES` (several trackers are several entries, the union reported; an identical template twice is refused). "Role names" under "Read, not driven": replace with the reading above. Selection table: a member's plain entry is a load refusal on a type where it cannot fire, so those cells assert the refusal.
    - **ST2.** Selecting `ref_rule_target_typed` on a type that declares no ref rule with a target is refused at load. This reverses drafting call 6.
    - **ST5.** Bind to `live`; drop the constant and the `tests/meta` acceptance line about it. Refuse at load on a type whose lifecycle holds no live status (`spec.live_statuses(type)` empty; `decision` is one). Status shapes become: a role renamed by an override and still `live = true` reports; a project role with `live = true` under any name reports; a role named `active` with `live = false` is silent. Falsify by comparing the role name with "active": the renamed-role row goes red.
    - **ST6.** Entry form `blocked_has_blocker:<role>` with a resolver in ST1's shape. Refused at load: no parameter; an undeclared role; a role no status of the type's lifecycle carries; a spec with no dependency-role ref kind (drop "It loads"). One shared builder for both incoming-edge sets; keep the `test_scale` run and report it against the baseline. Add status shapes for a parameter naming a project role.
    - **ST8.** Replace the regex approach: template parser, refusals at load (empty; a stray or unknown brace; a placeholder directly followed by itself or by a literal of its own class), the boundary rule, multi-selection. Drop the `re.compile` refusal, `(?i)`, `\x40`, the colon row as a regex concern and the TOML literal-string rule for this member. The `@` message keeps its first half only: a template cannot contain `@`. Falsify by removing the boundary rule and by letting `{d}{d}` load.
    - **Handoff for TASK-1002.** The two entry forms, every refusal text, and the sentence that "active" means a role with `live = true`.
    
    **Not this task, reported for routing** (@manager): `supersedes_incoming` and `ref_rule_target_present` compare the role names `superseded` and `done` inline (read: `_services/_validators.py`). Both predate this and contradict the same ADR-696 clause. TASK-1001 leaves them alone and must not copy them.
    
    @product-owner FEAT-901 stories 2, 5, 6 and 8 need the matching wording (the load refusals, "a role declaring `live = true`", `blocked_has_blocker:<role>`, template for regex). I did not edit FEAT-901.
- [2026-10-12T06:25:17Z] Robert Architect:
  - @tech-lead This replaces my guidance of 05:59 today. op-pierre ruled at 06:19 (ADR-864 and ADR-982 discussions): the refusal rule is confirmed, the `:<role>` parameter and the template grammar are not. ADR-864 Part 2 and ADR-982 clause 4 each carry a dated correction beneath my notes. Code claims are read at `75f53462`; nothing was driven.
    
    **The rulings as they now stand**
    
    1. **Roles.** No role name is hard-wired. A role declares what it means with a flag: active is `live = true`, and blocked is a new `blocked` flag, uniform with `live`. `blocked_has_blocker` takes no parameter.
    2. **A selection that cannot fire, or cannot be cleared, is refused at load.** Confirmed, `ref_rule_target_typed` included.
    3. **`external_id_not_in_title` takes a regular expression.** A bad pattern is the adopter's own risk. Your original ST8 stands almost as drafted.
    4. **`blocked_has_blocker` runs at the gate**, with `dependency_incoming` built in the pass that already builds `supersedes_incoming`. Unchanged from my earlier comment.
    
    **New work: the `blocked` flag, and it changes bundled bytes**
    
    - `RoleSpec` gains `blocked: bool = False`, beside `live`. No floor and no cross-check: nothing in the engine requires a blocked role to exist.
    - `_specs/workflow.toml`: `[roles.blocked]` gains `blocked = true`. No other bundled role declares it.
    - Frozen surface: `ROLE_CATALOG_FIELDS` grows to six, `_role_catalog` emits `blocked` on every row, and the human table gains the column (read: `_cli/_workflow_cmd.py`). `docs/stability.md` lists the row's fields and is TASK-1002's. I did not check whether the VS Code client's row type is closed.
    - So the task body's "Bundled bytes and the version" section reverses. The task now edits a file under `_specs/`, its golden locks move, the acceptance line that the `_specs` diff prints nothing no longer holds, and **the task depends on the working-version bump** for the manifest and stamp.
    - Suggested shape: one subtask ahead of ST6, in its own commit, for the flag, the bundled line and the catalog key.
    - Upgrade, for the handoff: an override that keeps the bundled `blocked` role gets the flag through the merge. One that declares its own roles has no blocked role until it adds the flag; nothing changes for it until it selects the check, which is then refused.
    
    **ST5.** Read `spec.role_for(item.status).live`. No constant beside `FALLBACK_ROLE_NAME`, and drop the `tests/meta` acceptance line about one. Status shapes by flag: a renamed role still `live = true` reports; a project role with `live = true` under any name reports; a role named `active` with `live = false` is silent. Falsify by comparing the role name with "active".
    
    **ST6.** No parameter, so it stays out of `PARAMETERIZED_VALIDATOR_NAMES`. Read `spec.role_for(item.status).blocked`. Status shapes: the bundled status; a renamed role still flagged; a project role with `blocked = true` under another name reports; a role named `blocked` with the flag false is silent. One shared builder for both incoming-edge sets; keep the `test_scale` run against the baseline. Drop "It loads" for a spec with no dependency-role kind.
    
    **ST8.** Back to the regular expression: single selection, `re.compile` at load with the refusal carrying the compile error, `re.search` with no flags, the `@` refusal with `\x40`, TOML literal strings in the table. Two additions:
    
    - The handoff carries the warning the docs owe: nothing bounds a match, and a pattern that backtracks can hang `sq check` and a gated write, which holds the index lock.
    - Read, and it matters for that sentence: `gate()` runs every selected member and only then discards `warn` findings, so the pattern runs under the lock at `warn` too, not only at `@error`. Either say "at any level" in the handoff, or have `gate()` skip a member whose resolved level for the type is `warn`, which changes no outcome and confines the exposure to `@error`. Your call; say which in the handoff.
    
    **The load refusals, all of them**
    
    - `assignee_present` on a type whose lifecycle holds no status of a live role (`decision` is one).
    - `blocked_has_blocker` on a type whose lifecycle holds no status of a role declaring `blocked`; in a spec that declares no dependency-role ref kind; with a parameter (the existing "takes no param" refusal).
    - `ref_rule_target_typed` on a type that declares no ref rule with a target.
    - Any of the eight named on a roster type. FEAT-901 now says the eight never apply to a roster type and that such a list "still loads"; under the confirmed rule it is refused. I have asked the product owner to change that wording.
    - Each message names the type, the entry and the declaration that is missing. Selection-table cells for those types assert the refusal, in `sq workflow lint` too.
    
    **Task body, other edits.** "What a member registers": ST6 is not parameterised and ST8 stays single-selection. Replace the "Role names" reading: the engine reads role flags, and the two inline name comparisons are not a model.
    
    **Not in this change** (@manager, for routing as a review finding): `supersedes_incoming` compares the role name `superseded` and `ref_rule_target_present` compares `done`. Each needs its own answer, a flag or an existing property such as `is_delivered`, and each would add a frozen catalog key or change what an existing check reports. TASK-1001 leaves both alone.
- [2026-10-12T06:48:30Z] Olivia Lead:
  - 2026-10-12: both tasks brought in line with the rulings of this date (ADR-864, ADR-982, the architect's comment of 06:25 here, FEAT-901 stories 1 to 11, and the bump ruling on MILE-934). Both stay Draft and unassigned. @manager
    
    - **Two parts and a hard stop.** Part one changes no bundled file and can start now: ST11, ST1, ST2, ST3, ST4, ST5, ST7, ST8, ST9. Then the stop: ST10 and ST6 wait for a comment here confirming the working version is 0.16.0 and that release/0.16 carries the bump. Part one is complete on its own (seven members), so it can be reviewed and merged at the stop if that suits the review rule better than holding the worktree.
    - **New subtasks.** ST10 (story 11) is the `blocked` flag: the role model, the one bundled line, the sixth key of the role catalog, and the manifest and content store regenerated at 0.16.0. ST11 (story 8) is the gate change below.
    - **Roles by flag.** ST5 reads `live`, ST6 reads `blocked`, ST7 reads `settled`. No role-name constant, and ST6 takes no parameter. One builder returns both incoming-edge sets, so the gate walks the index no more than today.
    - **Refusals at load.** One Plane-1 function, written in ST1 with the roster rule and extended by ST2, ST5 and ST6. The task body lists the accept or refuse cell of every bundled type for every member, read from the bundled spec. This reverses my drafting call 6.
    - **The gate and the regex: I took the second option.** ST11 has the gate skip a member whose resolved level for the type is `warn`. It changes no gate decision, and it means an adopter's pattern runs under the index lock only where the type selects the check at `@error`, not at the default level. ST8 is the regular expression as first drafted. The handoff sentence for the writer says "on a gated write only at `@error`", and one more adopter-visible fact follows: a `warn`-level check that raises no longer aborts a write.
    - **BUG-1003 is fixed in ST2**, by one shared reading of a bare ref that both ref-rule checks use, with the bug's reproduction as test rows. The task carries the `fixes` ref.
    - **Story 9** now selects both checks on work and records types only; ST9 adds the roster refusal as a driven step.
    - Still read, not driven: every code claim, at 75f53462.
    
    For routing, none of it blocks part one:
    
    - **VS Code client** (read): the skew canary compares the `active` row of `sq workflow roles --json` with an exact five-key object, and the client has its own row type and fixture. The sixth key is expected to turn it red. It needs a typescript-dev change landing with ST10; nothing under `clients/` is in this task.
    - **This repository's override** (read): a `tests/cli` module copies it, stamped 0.15.0, and asserts `sq override list` shows `current`. Drift is decided on the bundled document's content, so the first change to the bundled workflow document after the bump (ST10 here, or an earlier one on the main stream) is expected to turn it red. Who restamps the live file, and whether the released tool accepts the new stamp, needs an answer before part two.
    - **Wording that follows the gate choice**: ADR-864's note and story 10 both say the pattern runs "on every gated write of an item of a selecting type". With ST11 it is every gated write of a type that selects it at `@error`. @architect @product-owner
    - **A consequence of the refusal rule**: dropping a rule's target type through `[selected]` strips the rule, and a type still naming `ref_rule_target_typed` is then refused. ST2 has the developer drive it and report the message.
- [2026-10-12T06:51:12Z] Catherine Manager:
  - 2026-10-12: promoted to Ready and assigned to @python-dev for part one only (ST11, ST1 to ST5, ST7 to ST9), in a fresh worktree forked from the release/0.16 tip. The hard stop before ST10 and ST6 stands until I confirm the 0.16.0 bump here. ST11's choice (the gate skips a member whose resolved level is warn) is with @architect for confirmation against ADR-864; I will post the answer here before ST8 depends on it.
- [2026-10-12T06:53:25Z] Robert Architect:
  - @python-dev @product-owner ST11 is confirmed: the create/update gate evaluates a per-item member only where its resolved level for the item's type is `error`. Build it as written. Read at the release/0.16 working tree, not driven.
    
    - **Consistent with ADR-864.** Its gate correction asks that sitting out the gate be a declared property and not an accident. The level is declared, checked at load, and read through `_resolved_level`, the resolver each member uses for its own findings (read: every member resolves under its own name), so the gate and a member cannot disagree.
    - **Nothing relies on a `warn` member running on a write.** `gate()` keeps `error` findings only, and no member has a side effect or a deliberate raise (read: `_services/_validators.py` has no `raise` in a member). A raise from a member is a defect; at `warn` it now shows in `sq check` and no longer refuses writes.
    - **No floor lifts a level after selection.** A selection below a floor is refused at load, so the resolved level is final. `parent_acyclic` always resolves to `error` and still runs on every write; `subentity_container_marker` still sits out for want of the file text.
    - **ADR-696 is not touched**: it governs what the loader validates, and ST11 relies on that validation (a level is a checked value) without adding to it.
    
    One precision for the test table: a member selected twice with different levels (`ref_rule_target_present` on two targets) has one resolved level, the first entry's, for the gate and for its findings alike. That is today's behaviour, not ST11's.
    
    ADR-864's note at `external_id_not_in_title` now carries the correction: the pattern runs on every `sq check`, and on a gated write only for a type that selects the check at `@error`. Story 10 of FEAT-901 needs the same sentence, and the tech writer's handoff line "a check selected at `warn` is not evaluated on a write" stands.
- [2026-10-15T19:12:45Z] Elias Python:
  - - 2026-10-15: part one handoff, stopped at the hard stop. ST1 to ST5, ST7, ST8, ST9 are Done (ST11 was already). ST6 and ST10 are not started. @manager
    
    **Where.** Worktree .claude/worktrees/agent-a973dcee573f937c0, branch worktree-agent-a973dcee573f937c0, 9 commits on release/0.16 90764251 (merge-base equals the tip, checked again at the end): 21669bf1 (ST11), 40f6d2d8 (ST1), fbd1328b (ST2), f78dd1f4 (ST3), b6f5313c (ST4), 82c9aba7 (ST5), c91bd314 (ST7), f5314aa9 (ST8), f586f8d5 + 1e95ac9f (ST9). The tree is clean. `git diff --stat release/0.16...HEAD -- squads/ src/squads/_specs src/squads/_rendering/templates templates_manifest.json content_store.json` prints nothing.
    
    **Gates (worktree).** pyright 0 errors, ruff check and format clean. Targeted: `pytest tests/meta tests/unit tests/service tests/cli tests/integration` = 8683 passed, 11 skipped, 1 xfailed, 0 failed (the xfail is the console defect below, strict). Baseline on the untouched tree, narrower selection (tests/meta, tests/unit and the 31 modules found by searching for the changed names): 3184 passed, 2 skipped. `tests/test_scale.py --run-slow`: 6 passed before, 6 passed after part one (19.7 s, 24.5 s). The full suite is yours. `sq check` in the main checkout: no issues.
    
    **Tests added**: about 1,730 collected cases in 36 files, table-driven over one registry in tests/_selection_table.py (Member: fragment, shapes, per-row cells, planter). Every row of BUNDLED_ROWS plus contract and milestone; the existing modules that use the rows passed on the two new rows with no edit. Generic modules over the registry: cells (load or refusal, through the loader and `sq workflow lint`), check() per shape and per row, selected-on-another-type-only, unselected squad, pairwise-unique message fragments. Per member: shape module, gate/report agreement at @error, CLI smoke, import door.
    
    **Falsification, per subtask** (broken, red ids, restored, green):
    - ST1: `>=` for `<=`: 132 red (at-the-number rows, retitle, create). Resolver returns 120: 119 red. Missing-parameter refusal off: 3 red (bare/empty rows). Name in the work bundle: 5 red (effective-set pin; the check() rows stay green because a bare entry has no number). Out of the roster set: 9 red (3 cells + 6 unit).
    - ST2: dangling skip removed: 3 red (raises). Shared reading returns raw kind: 6 red. present back on split_ref: 1 red (the BUG-1003 test holds both default-kind rows; the new member's tests stay green). Untyped rule widens: 3 red. No-typed-rule refusal off: 15 red.
    - ST3: member compares without stripping tags: 6 red (milestone). Appended scaffold counted as unwritten in the member only: 29 red (the guard-agreement invariant). Out of the roster set: 4 red. Out of VALIDATOR_CONTEXT: tests/meta context guard red.
    - ST4: no strip: 96 red. Selecting line deleted from the shapes fixture: 72 red (every positive; the 24 negatives share the fixture).
    - ST5: role name "active" for the flag: 3 red. Only an absent assignee counts as empty: 1 red. No-live-status refusal off: 5 red.
    - ST7: role name "done" for the flag: 34 red. Non-empty region instead of the parser: 1 red. Sub-entity comments counted: 3 red. Out of VALIDATOR_CONTEXT: meta guard red.
    - ST8: re.match: 62 red. Resolver splits on the colon: 5 red. Compile check off: 4 red. Generic level message for user@host: 6 red.
    - ST9: no splat on epic: 2 red. 120 to 121: 37 red. body_written off contract: 4 red.
    
    **Read, now driven.** BUG-1003 reproduced on the released-shape override in a scratch squad with the dev build: FEAT-22 (bare edge) and FEAT-23 (default kind spelled out) are no longer reported; FEAT-24 (no edge), BUG-25 (edge of another kind), BUG-27 (no edge) are. `ref add` stores both spellings bare, as the bug said. `subentity_title_max:²` before ST1: pydantic ValidationError out of spec load (not a SquadsError); after: the SquadsError "names a non-positive-integer subentity_title_max threshold '²'". `:080` loads as 80 for both members (ASCII digits, leading zero kept). Rule shapes of the gate, the scaffold derivation and the parser were read and then exercised by the tests above.
    
    **ST9 driven half** (scratch copies under the session scratchpad, dev build = the worktree, base build = an archive of 90764251). Commit used: 90764251 for the board and the base build. Step 2/4: base build `sq check --json` = `[]`, exit 0; dev build on a fresh extraction of the same commit = `[]`, byte-identical (cmp), exit 0. No schema stop. Time of one `sq check` on ~6,100 items: base 4.05, 4.04, 4.46 s; dev unselected 4.18, 4.02, 3.96 s. Step 5: added `item_title_max:120` and `body_written` to the nine work and records tables of the copy's override, nothing else: `sq workflow lint` exit 0 "no errors or warnings"; `sq override list` workflow current; load_workflow_spec: every type's effective set contains the bundled one as (name, parameter, level), item_title_max = 120 on the nine, None on role/skill/operator. Step 6 (the number release preparation needs): `sq check --json` on the extended copy = 10 findings, all body_written at warn: REV-48, 106, 150, 184, 186, 265, 285, 344, 736 and TASK-81; item_title_max:120 reports 0; no other finding. One `sq check`: 4.10 s. Step 7: planted a 121 and a 120 title on a task and on a decision, and an unwritten task and decision: exactly the two 121s and the two unwritten warn, 120s clean, no roster item reported, `sq check` exit 0. Step 8: removing the two entries from the task table clears the task findings (TASK-81 included), the decision ones and the 9 reviews stay. Step 9: body_written on [items.role] fails lint (exit 1) naming role and the entry; removed again, exit 0. Step 10: worktree diff on squads/ is empty; main-checkout `sq check` clean. The "taken again at the end of part two" reading is still owed after ST6/ST10.
    
    **Defects found in things this task does not add** (not fixed here):
    1. The `sq check` text print drops a backslash that precedes a square bracket. `e()` is rich.markup.escape and leaves `\[[A-Z]...` alone, and the console then consumes the backslash. A pattern such as `\[[A-Z]+-\d+\]` prints as `[[A-Z]+-\d+\]` in the text output; `--json` and the stored message are exact, and a title with brackets (`[ABC-1]`) prints intact. Pinned as a strict xfail in tests/cli/test_external_id_not_in_title_cli.py; it flips to a failure when fixed. Needs an owner (a few lines in _cli/_common.py::e).
    2. Messages quote the entry with repr, so a backslash in an entry shows doubled (`'external_id_not_in_title:[A-Z]+-\\d+'`). Consistent with the rest of the loader; the docs may want a sentence.
    3. With the pattern compile check off (falsification only) `sq check` dies with a PatternError traceback and a gated write at @error would raise; the load check is what prevents it.
    
    **For TASK-1002 (adopter-visible), all driven unless marked.**
    
    Entry forms, defaults and what clears each finding. All eight default to warn, sit in no bundle and no floor, take @error, apply to work and records types only.
    - item_title_max:<n>. Message: `advisory: title is 121 chars (threshold: 120) — an item title is a one-line handle; put the detail in the body`. Characters, not bytes. Clears: `update --title` to n characters or fewer.
    - ref_rule_target_typed (no parameter). Message: `implements edge to TASK-3 points at a task, but a feature's implements refs must point at a contract` (one finding per misdirected edge; several accepted types are joined with `/`). A bare ref is read as the spec's default kind. Only a rule that declares a target counts; an untyped rule neither checks its kind nor widens a typed one; a dangling target is left to dangling_ref. Clears: `ref rm` the edge or re-point it.
    - body_written (no parameter). Message: `body is unwritten (still the template scaffold) — write it with `sq task 5 body -m "..."``. Clears: write the body. It reports exactly when a plain `body` write without --force would be accepted as a first write (same predicate). Limit: an item whose scaffold changed after creation (a template override edited later, an interpolated field such as a review's target_ref) no longer equals its scaffold and reads as written. A template that no longer renders reads as written.
    - description_present (no parameter). Message: `description is empty — set it with `sq task 5 update --desc "..."``. Whitespace of any kind (including a non-breaking space) counts as empty. Clears: `update --desc`.
    - assignee_present (no parameter). Message: `status is InProgress but nobody is assigned`. "Active" means a status whose role declares live = true (never a role or status name); a status with no role resolves to the fallback role and is silent. Clears: `update --assignee`.
    - settled_requires_discussion (no parameter). Message: `status is Done but its discussion holds no comment`. "Settled" means a role declaring settled = true. Only the item's own discussion counts (comments on its stories, subtasks, findings do not); the parser decides what a comment is. Clears: one `comment` on the item.
    - external_id_not_in_title:<regex>. Message: ``title holds `ABC-123` (matches the external-id pattern `[A-Z]+-\d+`) — keep tracker ids out of the title``. re.search, no flags (write `(?i)` in the pattern), first match reported; everything after the first colon is the pattern; several trackers are one alternation. `@` is reserved for the level: a literal `@` is `\x40`. In TOML write the entry as a literal (single-quoted) string; a basic string with a single backslash fails in the TOML parser first: `Malformed workflow override <path>: Unescaped '\' in a string (at line 3, column 50)`. Clears: retitle.
    
    Load refusals, exact text (lint prints them in a table that wraps; the strings below are the findings):
    - `item 'task': validators entry 'item_title_max' is missing its required parameter — name it as 'item_title_max:<n>', or drop the validator; without a parameter it never fires` (also for `item_title_max:`; external_id_not_in_title shows `:<regex>`).
    - `item 'task': validators entry 'item_title_max:0' names a non-positive-integer item_title_max threshold '0'` (also -5, 1.5, abc, a leading or trailing space, a superscript or non-ASCII digit; the same wording and parser now serve subentity_title_max).
    - `item 'task': validators entry 'external_id_not_in_title:[abc' names an invalid regular expression '[abc': unterminated character set at position 0` (compile error text is Python's own).
    - `item 'task': validators entry 'external_id_not_in_title:user@host' reads 'host' as its level — '@' separates the pattern from the level ('error' or 'warn') and cannot appear in the pattern; write a literal '@' as \x40` (one message, no generic unknown-level message beside it; `foo@warn` is pattern foo at warn).
    - Second entry of item_title_max or external_id_not_in_title: the existing "selected more than once" refusal (differing numbers or patterns, or a differing level, are all repeats).
    - A parameter on a member that takes none: the existing `validator 'assignee_present' takes no param (got 'assignee_present:x')`.
    - Roster type: `item 'role': validators entry 'item_title_max:80' cannot apply to a roster type — item_title_max is a policy about tracked work and applies to 'work' and 'records' types only; drop the entry`. Covers role, skill, operator and the seven names built so far (the eighth, blocked_has_blocker, joins in part two). Other checks (no_status_banner, item_skill_shadowed, ...) stay selectable on a roster type.
    - `item 'task': validators entry 'ref_rule_target_typed' needs a ref_rules entry with a target, and 'task' declares none (a rule whose target type was dropped through [selected] is removed with it) — declare { kind = ..., target = ... } in its ref_rules, or drop the entry`. Under the bundled spec only feature loads it. Driven: `[selected]` dropping contract strips feature's rule and a feature still naming the check gets exactly this message.
    - `item 'decision': validators entry 'assignee_present' needs a status of a role declaring live = true, and the lifecycle 'adr' of 'decision' holds none — without one it never fires; drop the entry or give the lifecycle a status of a live role`. Under the bundled spec decision and guide refuse; epic, feature, task, bug, review, contract, milestone load.
    - Bundled cells: item_title_max, body_written, description_present, settled_requires_discussion, external_id_not_in_title load on the nine work and records types and refuse on the three roster types.
    
    Door table at @error (service and CLI driven; "refused" = the write is rejected with the finding text, nothing written):
    
    | check | create | update | status | sq import |
    |---|---|---|---|---|
    | item_title_max | refused over n | refused while over | refused while over | pre-pass refuses |
    | ref_rule_target_typed | refused with a misdirected --ref | refused while the edge exists | same | pre-pass refuses |
    | description_present | refused without a summary | refused unless the same command sets one; clearing refused | same | pre-pass refuses |
    | assignee_present | refused at an active status, unassigned | clearing refused | refused unless the same command assigns | pre-pass refuses |
    | external_id_not_in_title | refused on a match | refused while matching | same | pre-pass refuses |
    | body_written | accepted | accepted | accepted | applied, finding at error in the result |
    | settled_requires_discussion | accepted | accepted | accepted (CLI exit 0) | applied, finding at error in the result |
    
    Report-only members make `sq check` exit 3 at @error and refuse nothing. The three roster types are load refusals on every row. `ref add` and `ref rm` are not gated: the state they leave is reported by `sq check` (exit 3 at @error) and refuses the item's next gated write until the edge is removed (driven). Not driven for the import door: update-style import ops (the shared core is the same; create is what was driven).
    
    The gate sentence, checked: a check selected at warn is not evaluated on a write (counted calls: 0 at warn and plain, called at @error); the pattern of external_id_not_in_title runs on every `sq check` (called once per item of the selecting type at either level) and on a gated write only when its type selects the check at @error. That the write holds the index lock while it runs is read from the code (create/update run the gate inside the store transaction), not timed. Nothing bounds a match: a backtracking pattern can hang `sq check` and, at @error, the write. A warn-level check that raises no longer aborts a write (ST11).
    
    Part two still owes: the blocked flag, the role catalog's sixth key, `blocked_has_blocker`, the manifest and content store, and the end-of-part-two unselected reading. Waiting for your 0.16.0 confirmation.
<!-- sq:discussion:end -->
