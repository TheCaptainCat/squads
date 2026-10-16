---
id: TASK-990
sequence_id: 990
type: task
title: Make a developer a role that declares a capability
status: Done
parent: FEAT-986
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-984:implements
- BUG-985:fixes
- REV-956:addresses
- TASK-989:depends-on
- TASK-954:depends-on
- TASK-1004:depends-on
description: Capabilities on roles and *<name> in the playbook, every consumer on
  the resolved role, the is_dev attribute dropped through a contribution to the 0.16
  step
subentities:
- local_id: ST1
  title: Require the catalog and playbook on the role derivation path
  status: Done
- local_id: ST2
  title: Declare capabilities and resolve them onto the role
  status: Done
  story: US1
- local_id: ST3
  title: Read the developer template from the resolved catalog
  status: Done
  story: US8
- local_id: ST4
  title: Expose capabilities in --json and role text output
  status: Done
  story: US9
- local_id: ST5
  title: Address a capability from the playbook with *<name>
  status: Done
  story: US1
- local_id: ST6
  title: Switch every consumer to the resolved role
  status: Done
  story: US2
- local_id: ST7
  title: Name roles from the roster in generated text
  status: Done
  story: US7
- local_id: ST8
  title: Drop the is_dev attribute and add the 0.16 contribution
  status: Done
  story: US4
- local_id: ST9
  title: Report suffix-only -dev roles and pin their transitions
  status: Done
  story: US3
- local_id: ST10
  title: Add sq dev add --slug and stop reading the suffix
  status: Done
  story: US5
- local_id: ST11
  title: Resolve an unknown slug to nothing
  status: Done
  story: US6
created_at: '2026-10-09T20:28:02Z'
updated_at: '2026-10-16T21:01:48Z'
---
<!-- sq:body -->
## Scope

"Is this role a developer?" has two answers today, a stored role attribute (`is_dev`) and a
slug spelling (`slug.endswith("-dev")`), and they disagree for the same role in one squad. This
task replaces both with one declared, resolved fact (ADR-984, order of work, steps 4 to 6):

- a role declares `capabilities`; the playbook addresses a capability with `*<name>`;
- the capability is computed once, in `resolve_role_for_item`, and travels on `RoleDef` and
  `RoleView`; nothing below the resolver decides anything from a slug string;
- a developer is either templated (`sq dev add`, selected by the `tech` attribute) or declared
  (a role file with the capability), and both are treated alike on every surface;
- the `is_dev` attribute is removed, with its pinned declaration, and existing squads are
  migrated by the release's one 0.15 to 0.16 step, to which this task adds one contribution.

It fixes the colour half of BUG-985 (a developer's model stays as stored, by decision) and
covers stories 1 to 9 of FEAT-986. Story 10 (documentation) is TASK-991.

## The code this task starts from

- **Item metadata is flat** (ADR-1007). A role's `is_dev`, `tech` and `model` are top-level
  frontmatter keys, declared under `[items.role.attributes]` in `_specs/workflow.toml` and read
  through `_models/_attributes.py` (`AttributeKey`, and the accessors `attrs.is_dev`,
  `attrs.tech`, `attrs.model`). `tech` is already declared `settable = false`, so `sq update
  --set tech=...` on a role is refused today. `ExtraKey`, `X.IS_DEV` and `extra.<key>` no longer
  exist; this body names attributes by their top-level key.
- **`is_dev` is a pinned role attribute** (`PINNED_ROSTER_ATTRIBUTES` in
  `_workflow/_models.py`), kept only because the engine still reads it. ST8 removes the pin and
  the declaration with the last reader.
- **The roster views and the role derivations have moved** (TASK-989): `RoleView` and
  `OperatorView` are in `_roles/_projection.py`; `DEV`, `is_dev_slug`, `create_lanes`,
  `allowed_create_types`, `item_types_for_role`, `skills_for_role`, `item_skill_role_sections`
  and `example_assignee_slug` are in `_interactions/_role_guidance.py`. The import-graph guard
  is `tests/meta/test_package_import_edges_match_the_recorded_table.py`.
- **The 0.16 step is a list of contributions** in `_migrations/_v0_15_to_v0_16.py`
  (`CONTRIBUTIONS`: `comment-headers`, then `flat-frontmatter`). This task appends one.
- **The working version reads 0.16.0.**
- **Two rulings of 2026-10-16 bound this task:**
  - *A role's stored name is its name* (op-pierre, on TASK-1059 and ADR-777). It is set at
    creation and no configuration change renames it. No subtask here renames a role: a `[dev]`
    or per-slug change reaches an existing developer's colour and definition, never its name.
  - *Every role needs its model* (op-pierre, on BUG-1065). Fixing that is BUG-1065's, not this
    task's. This task keeps a developer's stored model as it is (ST3) and does not widen or
    restructure the developer-only model column (ST8).
- Not built in parallel with FEAT-961 (pronouns) or the `[defaults]` table of ADR-981: they
  extend the same role models and the same closed key space.

## Subtasks, in build order

The order is the decision's. It is one task, reviewed at two commit points, after ST4 and
after ST7, and at the end. At each, the suite is green.

**Declare and resolve; nothing reads the capability yet.**

- **ST1, required arguments on the derivation path** (no story; the slice of REV-956
  finding 6 this change touches).
- **ST2, declare capabilities and resolve them onto the role** (US1).
- **ST3, read the developer template from the squad's resolved catalog** (US8, BUG-985).
- **ST4, `capabilities` in `--json` and in role text output** (US9).

**Switch the consumers; delete the spellings.**

- **ST5, address a capability from the playbook with `*<name>`** (US1).
- **ST6, every consumer reads the resolved role** (US2).
- **ST7, generated text names roles from the roster** (US7).

**Storage, fallbacks and the migration.**

- **ST8, drop the `is_dev` attribute and add the contribution to the 0.16 step** (US4).
- **ST9, a suffix-only `-dev` role is ordinary, and the migration reports it** (US3).
- **ST10, `sq dev add --slug`, and no read path consults the suffix** (US5).
- **ST11, an unknown slug resolves to nothing** (US6).

One developer, one pass: every subtask edits the same three modules
(`_interactions/_role_guidance.py`, `_roles/_resolver.py`, `_roles/_catalog.py`).

**New state, and why.** The task adds no stored key to any item and nothing to the index.
It adds one key to the role documents (`capabilities`, ST2), which is the decision itself, and
one field to `RoleDef` and `RoleView` carrying the resolved value, because the functions that
answer for a role receive a `RoleDef` or the roster of `RoleView`s and must not re-resolve it.
It removes one stored key (`is_dev`, ST8).

## The shape-by-surface table

One parametrised table is the backbone of this task's tests. ST6 owns it; ST3, ST5, ST7, ST9
and ST10 add columns or rows to it instead of writing a test per branch.

- **Role shapes (rows):** templated (`sq dev add --tech rust`); declared (a role file with
  `capabilities = ["dev"]`, activated with `sq role activate`, slug not ending in `-dev`);
  suffixed (a project role whose slug ends in `-dev`, no capability, not created by
  `sq dev add`); bundled (`architect`).
- **Surfaces (columns):** the role's pointer skill list; the per-type skill's capability
  section; the `CLAUDE.md` and `AGENTS.md` shared section and its delegate example; the
  create lane; `sq dev list`; the example assignee in generated text.
- **Rosters the table runs over:** the four shapes together; only a declared developer; only
  a suffixed role; no developer at all.
- **Invariant, asserted for every row:** templated and declared give identical answers on
  every surface, and suffixed and bundled give identical answers on every surface.
- It starts from the characterisation tables TASK-989 wrote for the moved derivations; the
  rows this task changes are the suffixed and declared ones.

## Migration

- **The step exists.** `SCHEMA_VERSION = "0.16"`, the `MIGRATIONS` entry, `migrate()`,
  `run_contributions`, `Planned` and the report channel (`MigrationOutcome.report`, printed by
  `sq migrate up`) are in place. This task edits none of them. Its whole change to the
  migration is one `Contribution` appended to `CONTRIBUTIONS`, after `flat-frontmatter`, and its
  rows in the contribution tests.
- **How the step runs it.** Every planning function runs first and reads only. If any plan
  carries a failure the run refuses with nothing written by this step. Otherwise the writers
  run in tuple order and the report lines of every plan are printed under the step's line.
  `MANUAL` and `SUMMARY` are assembled from the contributions.
- **This task's contribution.**
  - *Planning function:* the read-only report of suffix-only roles (ST9). It carries no
    failure: a role that needs a hand edit does not stop a migration. No override file is
    opened for writing. A migration runner is the one place that may know the retired
    spelling.
  - *Writing function:* none. The `flat-frontmatter` writer lifts `extra.is_dev` to a
    top-level `is_dev` like any other key. ST8 adds `is_dev` to `RETIRED_ROLE_KEYS`
    (`_models/_metadata.py`) and removes its declaration from the bundled role type, so the
    rebuild that `run_pending_migrations` runs after the runners strips it from every role file
    and from the index, as it strips the other retired role keys. The contribution's
    postcondition (no role item carries `is_dev`) therefore holds after `sq migrate up`, not
    after `migrate()` alone. If a contribution test checks a postcondition straight after
    `migrate()`, report it; do not move the removal into a writer to fit.
  - *The frozen key set of `flat-frontmatter`* (`_RETIRED_ROLE_KEYS` in the step module) is
    that contribution's and is not edited.
  - *`MANUAL` section.* Its facts are acceptance and its wording is the tech writer's to
    tighten, through a comment on this task: a developer is now a role that declares a
    capability; `sq migrate up` removes a stored marker from developer items and changes
    nothing else in them; a role it reports keeps working as an ordinary role and regains the
    developer guidance when its role file declares the capability and `sq sync` runs, and there
    is no automatic fix; an override file written for a developer not yet added is now
    reported by `sq check`, and the ways out are `sq dev add` or removing the file; an existing
    developer picks up a project `[dev]` colour on the next `sq sync` and keeps the model and
    the name it was created with; a stamped catalog, playbook, workflow or per-slug role
    override reports "may be stale" because the bundled documents changed (`sq override diff`,
    then `sq override update`).
  - *Summary clause:* the developer marker is dropped from role items, and roles named `-dev`
    that declare no capability are reported.
- **What the planning function is given, and reads for itself.**
  - *The run's `MigrationContext`*: the paths, the workflow spec and the playbook the run
    resolved. It carries no role catalog. The report needs the `[dev]` table's capabilities and
    each candidate role's resolved definition, and reads both through the role loader and the
    role resolver given `ctx.paths.squad_dir`. The runner guard
    (`tests/meta/test_migration_runners_use_the_runs_resolved_vocabulary.py`) bans the spec and
    playbook resolvers, not these two. Do not widen the context; if the guard refuses them,
    report and add no exemption.
  - *A reconciled index.* Before the first runner the index is rebuilt from the item files,
    and a file that cannot be given an entry has already stopped the run. The planning
    function takes its list of role items from that index.
  - *Files not yet flattened.* Planning runs before the `flat-frontmatter` writer, so each
    role file still holds its keys under `extra`. The planner reads each role file's
    frontmatter and passes it through `flatten_frontmatter` (with `_file_slug`), the pure
    per-file transform that contribution exposes, then reads top-level `slug` and `tech` from
    the result. It writes no second file reader and parses no `extra` itself.
  - *A corpus that fits the vocabulary* has been checked before the first runner. This
    contribution retires an attribute, which that check does not judge, so it declares nothing
    for it.
  - *The remedy rule.* Report lines are printed only for a run that completes, so the report
    may name `sq sync`. The `MANUAL` text is read through `sq migrate chlog`.
- **Fixtures.** `tests/fixtures/corpus/v0_15_discussions/` holds one templated developer
  (`python-dev`, added without `--model`); its migrated copy under
  `tests/goldens/migrated_corpus/v0_15_discussions/` carries `is_dev: true` today, and loses
  that line in ST8. ST8 adds a frozen 0.15 corpus written by the released tool for the shapes
  that one lacks, and regenerates the `v0_16` fixture by its README's rule.
- **This repository's own squad.** It is migrated once, by the operator, at release
  preparation, after FEAT-976 has added its contribution. The developer never runs
  `sq migrate up`, `sq repair` or `sq sync` on it, with any build, and does not run the dev
  build at the repository root at all. The proof that it migrates is made on a copy: copy
  `squads/` and `.squads.toml` into a scratch directory, run the dev build's `migrate up`,
  `sync` and `check` there, and record the result in the handoff (both developer items lose
  the key, `sq check` is clean, the list of files that changed).

## Bundled files and the manifest

The working version reads 0.16.0, which has no tag, so the manifest is maintained in the
ordinary way while this task changes bundled bytes (`_specs/roles.toml`,
`_specs/playbook.toml`, `_specs/workflow.toml`, templates under `_rendering/templates/`).

- **Regenerate with each change.** A commit that changes a bundled document or template
  also carries the result of `scripts/gen_template_manifest.py`. The generator replaces the
  0.16.0 entry and leaves the others alone: `git diff v0.15.0 --
  src/squads/_rendering/templates_manifest.json` shows the 0.16.0 entry and nothing else.
- **The freshness checks stay green.** `tests/meta/test_override_manifest_and_stamp_freshness.py`
  passes, and so does `scripts/gen_template_manifest.py --check`, which is what the CI
  `manifest freshness` step runs.
- **A file changed twice leaves a blob behind (read, not run).** The generator never deletes
  from the content store. `workflow.toml` and several templates already changed at 0.16.0, so
  this task's first change to any of them leaves the earlier 0.16.0 revision referenced by no
  entry, and `test_every_stored_blob_is_referenced_by_at_least_one_index_entry` fails. The
  remedy is the store rebuild, `scripts/seed_content_store.py --rebuild`, which reads the
  release tags and takes 0.16.0 from the working tree. If it refuses, report; do not edit
  either JSON file by hand. The release gate (`--release-gate`) stays a release-preparation
  step.
- **Override drift is observable with this build.** An override stamped 0.15.0 reports
  `drifted` in `sq override list` and "may be stale" in `sq check` once its bundled
  counterpart changes. Prove it in the suite, with overrides stamped 0.15.0 and the control
  stamped at the running version (`current`, silent), for the catalog, the playbook, a
  per-slug role file and (ST7) a template; and once by hand on a scratch squad that the
  released tool initialised and scaffolded, run with the dev build.
- **Upgrade fixtures come from the released tool** (`~/.local/bin/sq`, 0.15.0, in a scratch
  squad): a squad and its overrides as 0.15.0 wrote them are what an adopter upgrades from.

## What was driven, and what is left to confirm

Driven in scratch squads on 2026-10-09, with the dev build at `d07b0e50` (before the flat
frontmatter) and a scratch copy of the package carrying the stated one-line change.

- **The retired-key sweep removes `is_dev` with no runner code (driven, nested shape).** With
  the key added to the retired role keys, `sq repair` removed it from two developer files and
  from the index and kept `tech` and `model`.
- **A second rebuild then deletes `model` (driven, nested shape).** The sweep reads `is_dev` to
  decide whether `model` is a stored key (today `_retired_role_keys` in
  `_services/_maintenance.py`, through `RoleDef.stored_attribute_keys(is_dev=...)`). Once the
  marker is gone the developer reads as a non-developer and the next rebuild strips `model` (an
  operator's `--model opus` was lost). With that read changed to "carries `tech`", two rebuilds
  left `model` in place and the second wrote nothing. ST8 changes every shape read in the same
  commit as the retired key.
- **Changed bundled bytes make a stamped override report drift (driven).** Catalog and
  playbook overrides stamped 0.15.0, bundled `roles.toml` and `playbook.toml` each changed by
  one line: at running version 0.16.0, `sq override list` shows both as `drifted` and
  `sq check` warns "may be stale" for each, exit 0.
- **Not driven:** any of this on the flat shape; `sq migrate up` end to end with this
  contribution; the per-slug role override stamp and the template override stamp, which use the
  same predicate (read, `_overrides/_service.py`); `sq sync`'s wording for the same drift. ST8
  and ST7 confirm these as their first step, with the unpatched build.

## Acceptance (whole task)

- The manifest carries a 0.16.0 entry for every artifact this task changed, its 0.15.0
  entry is byte-identical to the tag, and the freshness tests and
  `scripts/gen_template_manifest.py --check` pass.
- Drift is observed with the unpatched build, on a scratch squad upgraded from 0.15.0, for
  a catalog, a playbook, a per-slug role and a template override.
- Not acceptance of this task: the migration of this repository's own squad, which is the
  operator's step at release preparation. Story 4's bullet about it is met on the scratch
  copy.
- Story 4's bullet that `tech` is not settable through the update verbs is already met by the
  flat frontmatter's `settable = false`; ST8 keeps a row that pins it and adds no code for it.
- Each subtask's own acceptance holds, and every acceptance bullet of stories 1 to 9 is
  pinned by a named test. The handoff maps bullet to test.
- **Table-driven tests over named shape families**, as each subtask lists, with the
  shape-by-surface table as the shared backbone. A row that needs its own fixture still goes
  through the same assertions as its neighbours.
- **Pipeline-level invariants**, each stated in its subtask: sync is a fixed point; migrate
  then sync converges on what a fresh init produces for the same roster; migrate is
  idempotent and never touches `tech`, `model` or the stored name; the index is rebuildable
  from the files with identical values.
- **A falsified test per subtask.** Break the change on purpose, watch the new test go red,
  restore it, watch it go green. The handoff records what was broken and the name of the
  test that went red, for each subtask.
- **A service-level test and a CLI smoke test for every behaviour change.** CLI tests assert
  the bare exit code and the printed text, never an exit code read through a pipe.
- **Generated files are diffed, with the roster held constant**, whenever an item-facing
  surface changes (ST5, ST6, ST7, ST8): for a fixed roster, compare the `.claude/` tree and
  the managed regions produced by a fresh `sq init` against those produced by `sq migrate up`
  then `sq sync` on a squad the previous release initialised. The two must be byte-identical
  to each other, and their diff against the previous release's output must contain only the
  changes the subtask names.
- `rg -n 'endswith\("-dev"\)|removesuffix\("-dev"\)|is_dev_slug|AttributeKey\.IS_DEV|attrs\.is_dev|dev_base_for_slug|"\*dev"' src/squads`
  finds nothing outside `_migrations/` and `_specs/`, checked against the known positives of
  the commit before. The scan also collapses wrapped lines, or it proves nothing.

## Gates and working rules

- `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .` and `~/.local/bin/sq check` are clean before
  handback. A bare `uv run` prunes the optional `tui` extra and reports false import errors.
- Any change under `_specs/`, `_rendering/templates/` or `_cli/` runs `tests/meta`,
  `tests/integration` and `tests/cli`. Beyond that floor, derive the selection from the
  diff: grep each changed name (spec key, template path, payload field, function) across
  `tests/` and run that union, redirected to a file and read from the file. Report the
  selectors. The manager runs the full suite afterwards.
- Run `uv run --all-extras pytest tests/meta` whenever a module-level constant is added (the
  mutable-state guard), a bundled document or template changes (the manifest freshness
  guard, after regenerating), the migration module changes, or an import edge changes (the
  import-graph guard).
- Comments and docstrings are one or two sentences, with no release versions, ticket ids or
  history. The migration runner is the one exception for versions. Several docstrings on
  this path explain the marker at length; they are rewritten to what the code does now, not
  extended.
- No ticket ids in source or in test file names: name a test file by the behaviour it pins.
- `type X = ...` for aliases. A multi-exception handler is parenthesised and carries
  `# fmt: skip`. No `from __future__ import annotations`. Time goes through `clock`.
- User-facing errors are `SquadsError` subclasses. Dynamic text printed to the console goes
  through `e()`. Attribute keys come from `AttributeKey`; a retired key that loses its member
  is spelled once, by name, beside `RETIRED_ROLE_KEYS`.
- Durable text of the `CLAUDE.md` managed region is edited in
  `templates/claude/claude_section.md.j2`, never in the rendered file.
- Do not edit `CHANGELOG.md` or anything under `docs/`. The handoff lists every
  adopter-visible change for the tech writer (TASK-991): each new key, flag, message and
  exit code, each generated-text change, and the migration's report and manual text.
- The hand-written part of `CLAUDE.md` is not edited here. The handoff lists each of its
  sentences this task makes false (the `*dev` sentinel line, `dev_role()`), with the wording
  proposed.
- Probe in a scratch squad nested under the session scratchpad, never at `/tmp` and never in
  this repository's own squad: print the working directory before any writing command and
  chain with `&&`.
- The dev build is not run at the repository root. This repository's squad is behind it: it
  refuses every command there but `sq migrate up`, and that one would migrate the live
  board. Board updates and the `sq check` gate go through the released tool,
  `~/.local/bin/sq`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 990 add-subtask "<title>"`; track with `sq task 990 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Require the catalog and playbook on the role derivation path

<!-- sq:subtask:ST1:body -->
**Goal.** A caller on the role-derivation or developer-template path cannot get an answer
from the bundled catalog or playbook by leaving an argument out. This is the slice of REV-956
finding 6 that the capability work touches; it has no story because nothing an adopter sees
changes.

**Approach**

- `_interactions/_role_guidance.py`: `create_lanes`, `laned_types`, `in_lane_owner`,
  `allowed_create_types`, `item_types_for_role` and `skills_for_role` take `spec` and
  `playbook` as required parameters. Their fallbacks to `bundled_spec()` and to the bundled
  playbook singleton are deleted. `is_lane_exempt` takes the default slug as a required
  parameter, and `catalog_default_slug` takes the catalog it reads.
- `_roles/_resolver.py`: `role_base_from_item` and `resolve_dev_role` take `squad_dir` as a
  required parameter (`None` stays a legal explicit value: "no squad, the bundled catalog").
- `BackendContext.resolved_skills_for` (`_backends/_base.py`) names the bundled documents
  explicitly at that one call until ST6 hands it the resolved role. `BackendContext`'s own
  `spec` and `playbook` defaults, `ServiceCore.__init__`'s, and the other parameters and
  shims of finding 6 are out of scope and stay on REV-956.
- Production call sites pass what they already hold (`Service.spec`, `Service.playbook`,
  `paths.squad_dir`). Test call sites pass `bundled_spec()` and the bundled playbook
  explicitly, which is what they mean. No assertion changes.
- Three production constructions build a `Service` with no playbook
  (the `Service(sp, spec=...)` calls in `_cli/_common.py` and `_cli/_main.py`: `sq repair`
  and the degraded `sq check` paths). They are not changed here. If a row of the table below, or of the
  shape-by-surface table later, answers wrongly on those paths, report it; do not widen the
  scope.

**Tests**

- New table: production surface by active document. Surfaces: a role's pointer skill list
  after `sq sync`; the create lane and skills on `sq role <slug> show` (text and `--json`);
  the out-of-lane warning on `sq create`; the config-integrity rules of `sq check`.
  Documents: bundled; a playbook override that adds a guide for a bundled role on a type it
  does not cover; the same guide with `authors = true`; a workflow override that drops a
  type. Each cell asserts the answer comes from the active documents.
- Invariant: for the fixed roster of the task body, generated files are byte-identical
  before and after this subtask.

**Falsify.** Restore a `= None` default with its bundled fallback on `skills_for_role` and
drop the playbook argument at one production call site. The row for that surface under the
override document goes red. Restore.

**Acceptance**

- `rg "(PlaybookSpec|WorkflowSpec) \| None = None" src/squads/_interactions/_role_guidance.py`
  finds nothing, checked against a known positive in `_badges.py`.
- pyright strict is clean with no call relying on an omitted document.

Gates and working rules: the task body.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-16T18:54:08Z] Elias Python:
  - Falsification count 3. Broke: skills_for_role in the service resolver called with the bundled documents instead of the active ones. Red: test_every_surface_answers_from_the_active_documents for the two playbook-guide rows and the workflow-drops row (3 of 4 rows). Restored, 4 green. Table: tests/integration/test_role_derivations_answer_from_the_active_documents.py. Generated files for a fixed roster (init --roles all + one developer) diff clean against HEAD output.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Declare capabilities and resolve them onto the role

<!-- sq:subtask:ST2:body -->
**Goal.** A role definition carries `capabilities`, declared in the catalog documents,
validated at load, and resolved once onto `RoleDef` and `RoleView`. No consumer reads it yet.

**Approach**

- `_roles/_models.py`: `RoleSpec.capabilities: list[str] = []` and
  `DevPoolSpec.capabilities: list[str] = []`. Both models forbid unknown keys, so the key
  space widens by exactly this name.
- `_specs/roles.toml`: `[dev]` declares `capabilities = ["dev"]`. The eight bundled roles
  declare none. This is the first bundled-byte change of the task: regenerate the manifest
  in the same commit, as "Bundled files and the manifest" in the task body describes, and
  check that a catalog override and a per-slug role file stamped 0.15.0 now report "may be
  stale". Update the golden lock in `tests/unit/test_role_catalog_artifact.py` and the
  roles scaffold body in `_overrides/_service.py` if it documents the `[dev]` keys.
- `_roles/_loader.py`: a name must match `[a-z0-9][a-z0-9-]*`. Check it for every `[[roles]]`
  entry and for `[dev]` in `_validate`, with the existing error prefix that names the file.
  `_roles/_resolver.py::_apply_override` makes the same check for a per-slug role file and
  names that file, as a hand-written sentence like the model check beside it, not a pydantic
  dump. One definition of the pattern, used by both.
- `_roles/_catalog.py`: `RoleDef.capabilities: tuple[str, ...] = ()`. `role_spec_to_def`
  carries it; `dev_role_from_pool` takes it from the pool spec it is given;
  `RoleDef.from_item` yields none. It is **not** added to `_ATTRIBUTE_FIELDS` and no role
  attribute is declared for it: nothing new is stored on an item.
- `_roles/_projection.py`: `RoleView.capabilities`. `ServiceCore._role_view` copies it from
  the role `resolve_role_for_item` returned, which stays the one place it is computed.
- A per-slug override merges over its base through the shared engine, so `capabilities` in a
  role file replaces the base list, and the splat form appends to it.

**Tests**

- Table: declaration site by value shape. Sites: a `[[roles]]` entry in the catalog
  override; a per-slug file for a new project role; a per-slug file over a bundled role; a
  per-slug file over a templated developer; the `[dev]` table in the catalog override; no
  declaration. Value shapes: absent; empty list; one name; two names; a repeated name; the
  splat-append form; and the refused ones: uppercase, leading hyphen, a space, the empty
  string, a non-string element, a non-list value. Each cell states the resolved
  `RoleDef.capabilities` and `RoleView.capabilities`, or exit 1 and the file the error names.
- Invariants: for every live role, `RoleView.capabilities` equals
  `resolve_role_for_item(item).capabilities`; and declaring or changing a capability then
  running `sq sync` adds no key to any item file or to `.squads.json` (hash the squad tree
  minus generated output, and delete the index and `sq repair` to the same values).
- CLI smoke: `sq check` and `sq sync` exit 1 on a malformed name and print the file.

**Falsify.** Remove the name check: the refused rows go red. Then drop the field from
`_role_view`: the view column goes red. Restore each.

**Acceptance**

- Story 1, first two bullets.
- Generated files for the fixed roster are byte-identical before and after (no consumer is
  switched), and the handoff notes for the writer that an older package refuses a catalog or
  role document that carries the key.

Gates and working rules: the task body.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-16T18:54:10Z] Elias Python:
  - Falsification count 43. Broke (a) the capability name check in the catalog loader and the role-file resolver: 22 red (every malformed-name row at every declaration site, plus the sq check and sq sync smoke tests); (b) dropped capabilities from the service role view: 21 red (every view column that declares a capability). Restored, 64 green. Table: tests/service/test_a_role_declares_capabilities_that_resolve_onto_the_role.py (5 declaration sites x 12 value shapes, plus the no-stored-state invariant, hash of item files and index, delete index then sq repair).
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Read the developer template from the resolved catalog

<!-- sq:subtask:ST3:body -->
**Goal.** An existing developer's definition is regenerated from the `[dev]` table of the
catalog the squad resolves, on every read. BUG-985 is fixed: a project `[dev]` override no
longer reverts on `sq sync`.

**Approach**

- `_roles/_resolver.py`: `dev_base_from_item(item, squad_dir)` builds its base with
  `dev_role_from_pool(tech, load_role_catalog(squad_dir).dev, ...)`. `role_base_from_item`
  passes its `squad_dir` through. `resolve_dev_role` takes the same one path for a squad and
  for no squad.
- `_roles/_catalog.py`: `dev_role()`, the shim bound to the bundled catalog, is deleted with
  its imports. `dev_role_from_pool` is the only constructor.
- The stored name stays the developer's name (op-pierre, 2026-10-16): `dev_base_from_item`
  keeps passing the item's `title` as the name, so no pool is drawn for an existing developer,
  and the stored name stays pinned over every layer, a per-slug `full_name` included.
- The developer's capabilities now arrive from `[dev].capabilities` of the resolved catalog
  by the same path, which is what ST6 relies on.
- The `model` attribute stays the stored value for a developer (ADR-984, "Left out"; story 8):
  `sq dev add` stores the catalog default when `--model` is omitted, and the resolver reads
  it back. A `[dev]` override therefore reaches an existing developer for what the template
  supplies (colour) and never changes its model; only a developer added afterwards takes a
  new `[dev].model`. The table below pins "the stored model wins" as rows of its own, so the
  behaviour is stated, not accidental.
- `sq role <slug> show` prints the colour on its text card (`_cli/_role.py`), so the card and
  the pointer can be compared. The `--json` payload gains no key here.

**Tests**

- The reproduction in BUG-985 runs as written, as a CLI test: pointer at haiku and pink
  after `sq dev add`, after the first `sq sync` and after the second.
- Table, added to the shape-by-surface file: `[dev]` override state when the developer is
  added (none; colour and model) by what changes afterwards (nothing; override added;
  colour changed; model changed; override removed) by per-slug role file (absent; sets
  colour; sets model; sets `full_name`). Columns: pointer `model` and `color` after one sync
  and after two, the same two values on `sq role <slug> show`, and the stored name, which is
  unchanged in every row.
- The same rows once more with a project catalog that changes `name_pool`: a developer added
  earlier keeps its name, and the next `sq dev add` draws from the project pool.
- Invariants: sync is a fixed point (the second sync changes no file, by hash), and for
  every row the pointer and `sq role <slug> show` agree on model and colour.
- If the AGENTS.md backend renders either value, it gets a column; if it renders neither,
  the handoff says so.

**Falsify.** Point `dev_base_from_item` back at the bundled catalog: every "colour changed"
and "override added" row goes red. Restore. Then take the developer's model from `[dev]`
instead of from the item: the "model changed" rows go red. Restore.

**Acceptance**

- Story 8, all bullets, stated both ways and each pinned by a named row:
  - **the colour follows.** For an existing developer, a `[dev]` colour added or changed
    after the developer was created is on its pointer after the next `sq sync`, a second
    sync changes nothing, and `sq role <slug> show` prints the same colour.
  - **the stored model does not change.** Changing `[dev].model` (haiku to opus) leaves each
    existing developer's stored `model`, its pointer and its `sq role <slug> show` on the
    stored model across two syncs. Only a developer added afterwards gets opus.
- The colour lines of BUG-985's reproduction pass. Its model rows are behaviour by decision:
  they are pinned as written above, not changed.
- `rg "def dev_role\b|dev_role\(" src/squads` finds nothing, checked against the commit
  before.
- Adopter-visible, for the handoff: an existing developer picks up a project `[dev]`
  colour on the next `sq sync` and keeps the model it was created with;
  `sq role <slug> show` prints the colour.

Gates and working rules: the task body.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-16T18:54:12Z] Elias Python:
  - Falsification count 22. Broke (a) dev_base_from_item pointed back at the bundled catalog: 13 red (override-added, colour-changed, override-removed rows); (b) model taken from the [dev] table instead of the item: 9 red (model-changed and override-removed rows). Restored, 26 green. Table: tests/cli/test_an_existing_developer_follows_the_resolved_dev_table.py. AGENTS.md renders neither model nor colour, so it has no column.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Expose capabilities in --json and role text output

<!-- sq:subtask:ST4:body -->
**Goal.** `capabilities` is readable on every role surface a tool or a person uses, as an
additive key.

**Approach**

- `--json`: `capabilities`, always present as an array (possibly empty), on `sq role catalog`
  and `sq role list` (`_cli/_role.py`), on `sq role <addr> show`
  (`_cli/_common.py::build_role_json_payload`, both the resolved branch and the fallback for
  a role with no definition left, which answers `[]`), and on each `roster[]` row of the
  `playbook` view payload (`_cli/_workflow_cmd.py`).
- Text: `sq role list` gains a column and the `sq role <slug> show` card gains a row.
- Nothing else in any payload changes name, type or position. `lane.roles[].slug` keeps its
  type and still carries `*dev` for the bundled guides.

**Tests**

- Table: surface (the four `--json` surfaces and the two text ones) by role shape (bundled;
  templated developer; declared with one capability; declared with two; a role whose backing
  definition is gone; a bundled role outside any squad, for `sq role catalog`). Each cell
  asserts the value and, for `--json`, that it is a list.
- Invariant over every `--json` surface: the key set before this subtask is a subset of the
  key set after it, with equal values for the old keys; the only new key is `capabilities`.
  Take the "before" payloads from the commit before, not from a hand-written list.
- The VS Code skew canary passes unchanged (`npm run test:canary` in `clients/vscode`). Run
  it if Node is available and report the result; if it was not run, say so.

**Falsify.** Omit the key from the fallback branch of `build_role_json_payload`: the row for
a role with no definition left goes red. Restore.

**Acceptance**

- Story 9, except the bullet about `is_dev` leaving the generic `show` and `list` item
  rows, which ST8 pins once the key is gone from the corpus.
- The handoff lists the four payloads and the two text outputs for the writer.

Gates and working rules: the task body.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-16T18:54:15Z] Elias Python:
  - Falsification count 2. Broke: omitted capabilities from the fallback branch of build_role_json_payload. Red: the role-show definition-gone cell and the dedicated fallback test. Restored, 25 green. Table: tests/cli/test_capabilities_are_readable_on_every_role_surface.py. Old keys unchanged: verified against payloads from the HEAD build on one scratch squad (role catalog, list, show; only new key is capabilities).
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Address a capability from the playbook with *<name>

<!-- sq:subtask:ST5:body -->
**Goal.** A playbook guide whose subject is `*<name>` addresses every live role that holds
capability `<name>`. `*dev` stops being a sentinel and becomes the first use of that form,
and the engine holds no capability name.

**Approach**

- `_interactions/_loader.py`: the subject of a guide is a role slug or `*<name>`, where
  `<name>` matches the capability pattern of ST2. `_check_slugs` exempts any well-formed
  `*<name>` from the catalog-slug check and refuses a malformed one (`*`, `*Dev`, `* dev`),
  naming the file. Both `DEV` constants are deleted. Existing overrides that name `*dev`
  load unchanged.
- `_interactions/_role_guidance.py`: one helper answers "which guides address this role",
  from the role's slug and its resolved capabilities. `item_types_for_role`,
  `allowed_create_types` and `in_lane_owner` use it, for any capability name.
- `orphaned_playbook_guides` (`_interactions/__init__.py`): the blanket `*dev` exemption
  goes. A capability-addressed guide declared by an override is reported when no live role
  holds the capability, on the terms a guide naming a non-live role already is; a bundled
  guide stays silent, as today. It needs the live roles' capabilities, so its
  `live_role_slugs` argument becomes the live roster. `orphaned_playbook_guide_message` gets
  wording for the capability case that names a remedy that works (declare the capability on
  a live role, or remove the guide). A role holding a capability no guide addresses is not
  reported.
- `item_skill_role_sections`: a capability-addressed guide renders only while at least one
  holder is live. Its heading names the capability as declared and lists the live holders
  (full name and slug, roster order). No label is declared and none is invented: the word
  "developers" leaves the code.
- `_interactions/_models.py`: the comments describing the sentinel are rewritten.

**Tests**

- The story's own case, as a row: a project declares `reviewer` on two roles and an override
  guide `*reviewer` on a type; both roles gain the type's skill, the section and (with
  `authors = true`) the create lane, with no code change.
- Table: guide subject (a role slug; `*dev` bundled; `*dev` in an override; `*<project
  name>` in an override; malformed) by holder state (two live holders; one live; one retired
  and none live; none declared) by `authors` (false; true). Columns: load result; the
  holders' pointer skills; the section and its heading; the create lane; the `sq check` and
  `sq sync` report.
- Invariant: for every guide, the roles that preload the type's skill, the roles the section
  lists and the roles whose lane gains the type are the same set.
- CLI smoke: `sq check` prints the orphan report for an override guide whose capability no
  live role holds, and is silent for the bundled `*dev` guides in a squad with no developer.

**Falsify.** Restore the blanket exemption for a `*`-prefixed subject in
`orphaned_playbook_guides`: the "none live, override" rows go red. Then compare the subject
to a literal `"*dev"` in the helper: every `*reviewer` row goes red. Restore each.

**Acceptance**

- Story 1, bullets three to six.
- `rg -n '"dev"|\*dev' src/squads --glob '!_specs/**' --glob '!_migrations/**'` finds no
  capability name in code or templates, checked against the commit before. `_migrations/` is
  excluded because a runner may know the retired convention.
- Generated files are diffed as the task body describes; the expected difference is the
  heading of the capability section in each per-type skill and nothing else.

Gates and working rules: the task body.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-10-16T19:45:46Z] Elias Python:
  - Falsification count 16. Broke (a) a blanket exemption for a *-prefixed subject in orphaned_playbook_guides: 8 red (the override rows with no live holder); (b) the capability test hard-coded to *dev: 8 red (every *audit and *reviewer row). Restored, 25 green. Table: tests/integration/test_a_playbook_guide_addresses_every_role_holding_a_capability.py (3 subjects x holder states x authors; four surfaces compared as one set, plus malformed subjects naming playbook.toml and the silent bundled *dev guides). The DEV constants are gone; no capability name remains in code or templates outside _specs and _migrations.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Switch every consumer to the resolved role

<!-- sq:subtask:ST6:body -->
**Goal.** Every consumer that asked "is this a developer?" of a slug string asks the resolved
role instead. A declared developer and a templated one get identical treatment on all six
surfaces, and the spelling test is deleted.

**Approach**

- `_interactions/_role_guidance.py`: `item_types_for_role`, `skills_for_role` and
  `allowed_create_types` take the resolved role (anything carrying `slug` and
  `capabilities`: `RoleDef` or `RoleView`) instead of a slug. `item_skill_role_sections` and
  `example_assignee_slug` read `capabilities` off the roster they already receive.
  `is_dev_slug` is deleted.
- "Developer", where the engine needs the word at all (`sq dev list`, the example assignee,
  the delegate example), means: a live role holding a capability that the resolved catalog's
  `[dev]` table declares. One helper answers it, taking the roster and the catalog. No
  capability name appears in it.
- Callers resolve before they ask:
  - `_services/_base.py`: `_resolve_role_skills`, `resolved_skills_for_role` and
    `_role_skills_map` pass the role resolved from the item; the lane check in the create
    path (`allowed_create_types(author, ...)`) resolves the author's role first, and an
    author that is not a role keeps today's answer.
  - `_services/_config_integrity.py`: both loops iterate resolved live roles.
  - `_backends/_base.py`: `BackendContext.resolved_skills_for` takes the role its caller
    already holds (`generate_role_entry` has the `RoleDef`), and the explicit bundled
    fallback of ST1 goes.
  - `_cli/_role.py` and `_cli/_common.py`: the create lane on the role card and in the
    `--json` payload comes from the resolved role. A slug with no role has an empty lane.
  - `_cli/_dev.py`: `sq dev list` lists the live roles the helper above selects, templated
    or declared; the Tech column is empty for a declared one.
- `templates/claude/claude_section.md.j2`: the Jinja `endswith("-dev")` loop goes. Whatever
  the template needs is computed in Python and handed to it (ST7 finishes the wording).

**Tests**

- This subtask owns the shape-by-surface table of the task body: four shapes, six surfaces,
  four rosters, and the pairwise-identity invariant on every row.
- Story 2's two edge rosters as rows: a squad whose only developer is declared still renders
  the capability section, a delegate example naming that role's slug, and its create lane; a
  squad with no holder renders none of them.
- Each surface is asserted through the service and through the CLI or the generated file an
  agent reads, not through the helper.
- Generated files are diffed as the task body describes. Expected difference against the
  previous release for the fixed roster: none beyond ST5's heading. For a roster with a
  suffixed role: its pointer loses the developer skills.

**Falsify.** In the helper, treat a slug ending in `-dev` as holding the capability: the
suffixed rows go red on every surface. Then make `sq dev list` filter on the `tech` attribute: the
declared row goes red. Restore each.

**Acceptance**

- Story 2, all bullets.
- `rg -n 'is_dev_slug|endswith\("-dev"\)' src/squads` finds nothing, checked against the
  commit before.
- Adopter-visible, for the handoff: `sq dev list` lists declared developers; a role whose
  slug ends in `-dev` without the capability loses the developer guidance.

Gates and working rules: the task body.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-10-16T19:45:49Z] Elias Python:
  - Falsification count 4. Broke (a) the addresses helper also counting a -dev slug as holding the capability: 2 red (the suffixed rosters); (b) sq dev list filtering on the tech attribute: 2 red (the declared rosters). Restored, 4 green. Table: tests/integration/test_a_declared_developer_is_treated_like_a_templated_one_on_every_surface.py (four rosters; pointer skills, section, create lane, sq dev list, example assignee, delegate examples; developers alike, ordinary roles alike). The derivations take the resolved role; is_dev_slug is deleted. Two suffix reads remain for ST11 (preview of an unadded dev slug in _cli/_common.py and _overrides/_service.py).
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Name roles from the roster in generated text

<!-- sq:subtask:ST7:body -->
**Goal.** No generated file states a slug pattern. Examples name concrete slugs of live
roles, computed in Python and handed to the templates.

**Approach**

- `templates/claude/claude_section.md.j2`: the sentence "a developer's slug is `<tech>-dev`"
  goes (the roster printed above it gives every slug). The curated list of bundled slugs and
  the `<tech>-dev` placeholder go. The delegate examples arrive as a list computed in Python
  (`_interactions/_role_guidance.py`, called from the backend that builds the section's
  context): live role slugs only, never the default role itself, a developer included when
  one is live, at most four, in roster order. The selection rule is pinned by the table
  below and reported in the handoff.
- `example_assignee_slug`: prefers a live developer (the helper of ST6), then the first live
  role, then the `<slug>` placeholder the surrounding block already uses when the roster is
  empty. It never prints a slug that is not on the roster.
- `_specs/playbook.toml`: the six `<tech>-dev` placeholders in guide prose become a
  placeholder that names no spelling (suggested `<developer>`). The four `*dev` subjects
  stay.
- `templates/views/memory_skill.md.j2`: the literal `python-dev` example becomes a live slug
  from the roster the template already receives, or the `<role>` placeholder used on the
  same line.
- The per-type skill heading is ST5's. `AGENTS.md` and the squads skill take their example
  from the same functions; check both templates for a second copy of any sentence removed.
- Bundled bytes change here, in templates and in `playbook.toml`: regenerate the manifest in
  the same commit ("Bundled files and the manifest" in the task body), and update the
  goldens that pin rendered output (`tests/goldens`,
  `tests/unit/test_managed_section_and_cheatsheet_goldens.py`). First step: prove that a
  template override and a playbook override stamped 0.15.0 report "may be stale" after the
  change, in the suite and once by hand as the task body describes, and record the output.
  The playbook and catalog cases were driven on 2026-10-09 on a patched copy; the template
  case was only read.

**Tests**

- Table: roster by generated surface. Rosters: `sq init --roles all` with one templated
  developer; `--roles minimal`; `architect` plus `backend-engineer` (a declared developer);
  only a suffixed role beside the default; no role but the default; a squad that shares no
  slug with the bundled catalog. Surfaces: the `CLAUDE.md` managed section; `AGENTS.md`;
  each role pointer; each per-type skill; the squads skill; the memory skill.
- Assertions per cell: every slug the surface prints inside a command or an example is on
  the live roster; no `<tech>` placeholder; no sentence matching a slug pattern.
- The grep gate of the story, over rendered output for a fresh squad and for a squad with
  only a declared developer, matching on whitespace-collapsed text so a wrapped sentence
  cannot hide. Validate the pattern on the previous release's rendering first: it must hit.
- `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py` gains whatever its
  probe roster needs to cover the delegate example; do not weaken it.
- Generated files are diffed as the task body describes. The handoff lists every changed
  sentence, old and new, for the fixed roster.

**Falsify.** Put the curated slug list back in the template: the cells for the roster that
shares no slug with the catalog go red. Then make `example_assignee_slug` return a literal:
the same roster goes red on the squads skill. Restore each.

**Acceptance**

- Story 7, all bullets.
- No template contains `endswith`, `<tech>` or a bundled role slug outside a comment.
- This repository's rendered `CLAUDE.md` is not edited; it changes when the operator next
  syncs the squad.

Gates and working rules: the task body.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
- [2026-10-16T19:45:52Z] Elias Python:
  - Falsification count 8. Broke (a) example_assignee_slug returning a literal: 4 red (every roster without that slug); (b) the old <tech>-dev sentence put back in the CLAUDE.md template: 4 red. Restored, 5 green. Table: tests/integration/test_generated_text_names_only_live_roster_slugs.py (4 rosters over CLAUDE.md, AGENTS.md, pointers, every skill body; whitespace-collapsed scan validated against the old sentence). Not covered: a roster sharing no slug with the bundled catalog, which tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py keeps. Per-type skill lane commands still name bundled authoring slugs from the bundled playbook text (--author product-owner); outside this subtask.
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Drop the is_dev attribute and add the 0.16 contribution

<!-- sq:subtask:ST8:body -->
**Goal.** No role item carries `is_dev`, and the engine neither declares nor pins it.
"Templated" is derived: a role item that carries the `tech` attribute. Existing squads lose the
key through the release's 0.16 step, to which this subtask appends the contribution.

**First step: confirm what was driven, on the flat shape.** The task body records two results
driven before the flat frontmatter: the retired-key sweep strips `is_dev` with no runner code,
and a second rebuild deletes `model` unless the role's shape is read from `tech`. Reproduce
both on the real change: one `sq migrate up` on a scratch squad the released tool initialised
with two developers (one added with `--model opus`), then a second `sq repair`, hashing the
tree after each. Record the output in a subtask comment.

**Approach**

- **Storage.**
  - `_models/_attributes.py`: `AttributeKey.IS_DEV` and the `is_dev` accessor are deleted. If a
    named predicate for "carries `tech`" reads better than `attrs.tech(item) is not None` at the
    call sites below, it replaces the accessor in the same module; no other new helper.
  - `_models/_metadata.py`: `is_dev` joins `RETIRED_ROLE_KEYS`, spelled once, by name, beside
    it (the pattern the retired `skills` key already follows).
  - `_specs/workflow.toml`: the `is_dev` line leaves `[items.role.attributes]`.
    `_workflow/_models.py`: `is_dev` leaves `PINNED_ROSTER_ATTRIBUTES`. These two go in the
    same commit as the retired key: `_retired_role_keys` keeps any name the squad's spec
    declares on `role`, so a still-declared `is_dev` would never be swept.
  - `_roles/_catalog.py`: the keyword of `RoleDef.to_attributes` and `stored_attribute_keys`
    is renamed off "dev" (suggested: `templated`), with its docstrings, since the question it
    answers is "is `model` a stored key for this role". The developer-only `model` column
    (`_DEV_ATTRIBUTE_FIELDS`) keeps its meaning: making a model take effect on every role is
    BUG-1065's, and is not done here.
- **Every shape read changes together**, in the same commit as the retired key, to "the item
  carries `tech`": `_services/_maintenance.py::_retired_role_keys`, the `to_attributes` call
  in `_refresh_catalog_attributes`, `_itemfile.py::_exempt_attribute_keys`, the branch in
  `_roles/_resolver.py::role_base_from_item`, and the name-pool count in
  `_services/_roster.py::add_dev`, which also stops writing the marker. (`sq dev list` already
  reads the ST6 helper.)
- **The contribution.** One `Contribution` appended to `CONTRIBUTIONS` in
  `_migrations/_v0_15_to_v0_16.py`, after `flat-frontmatter`, as the task body's "Migration"
  section settles it: no writing function, its `MANUAL` section and its summary clause. The
  planning function is ST9's; until ST9 lands it returns an empty `Planned`. Nothing else in
  the migration is edited: not `migrate()`, `run_contributions`, the registry,
  `SCHEMA_VERSION`, `MigrationOutcome`, `flatten_frontmatter` or its frozen key set, or
  `_cli/_migrate.py`.
- **The removal itself** is the retired key plus the rebuild that runs after the runners,
  under the same resolved vocabulary. The contribution adds no index or frontmatter write.
- **A frozen 0.15 squad that holds developers**, `tests/fixtures/corpus/v0_15_developers/`,
  built the way `v0_15_discussions` was: by the released tool (`~/.local/bin/sq`) in a scratch
  squad under the session scratchpad, clock pinned on the corpus's convention, committed as
  written minus the reflog, never hand-edited, its build commands in the fixture README. It
  holds what `v0_15_discussions` lacks: a developer added with `--model`, one with a per-slug
  override, a retired developer, a project role whose slug ends in `-dev` created from a role
  file, the same retired, and a project role with another slug.
  `tests/integration/test_migration_corpus.py` gains its case. The migrated-output golden
  module (`tests/integration/test_migrate_up_output_is_unchanged_for_every_corpus.py`) covers
  squads without overrides only: if the new corpus cannot sit there as it stands, report it
  rather than dropping the override shapes.
- **Goldens and the `v0_16` fixture.** The `v0_16` fixture is regenerated by its README's rule,
  and the migrated-corpus goldens with `UPDATE_GOLDENS=1` on their module. Expected diff,
  confirmed line by line in the handoff: the `is_dev: true` line leaves
  `tests/goldens/migrated_corpus/v0_15_discussions/agents/roles/ROLE-000005-python-dev.md`;
  the new corpus gains its goldens, with no `is_dev` line in any developer file; `v0_16`
  does not change, since `v0_15` holds no developer. Any other change is a finding to explain
  before it is committed.
- **An un-migrated 0.16 file reads correctly.** A role file stamped 0.16 that still carries
  `is_dev: true` (as a pre-change dev build or the old `v0_16` fixture wrote it) keeps the key
  as an undeclared attribute until the next rebuild sweeps it, resolves through `tech`, and
  `sq check` is clean for it with the default validators.

**Tests**

- Table: corpus shape by step. Corpus shapes: no developer; one templated developer; two,
  one with `--model`; a developer with a per-slug override; a developer whose stored title
  is blank; a retired developer; a declared developer; a suffixed role. Steps:
  `sq migrate up`; a second `sq migrate up`; `sq repair`; delete the index then `sq repair`.
  Columns: which files changed (hash them), the attributes of each role in the file and in
  the index, the schema stamp, exit code and printed lines.
- Two rows whose outcome belongs to the steps before the runner, asserted here only for
  what this contribution adds to them. A developer file on disk but missing from the index:
  the reconcile gives it an entry and the key is stripped like any other. A role file with
  unreadable YAML beside a healthy developer: the run stops before the first runner,
  nothing is written and the healthy developer still carries the key; after the file is
  corrected a re-run strips it.
- Invariants, for every row: `tech`, `model` and the stored name are byte-identical before
  and after every step; the second and later steps change no file; the index after "delete
  then repair" equals the index before; no key appears in `.squads.json` that the files do
  not carry.
- The contribution tests gain this contribution's row, driven on the developers fixture:
  after one `sq migrate up` no role item carries `is_dev`, in file or index; every
  contribution runs in that one run.
- The assembled `MANUAL` holds this section once, after the flat-frontmatter section, and the
  summary holds this clause; `sq migrate chlog v0.15.0..v0.16.0` prints every section.
- Un-migrated read: the 0.16 file of the approach above resolves as a developer on every
  surface of the shape-by-surface table, and `sq check` is clean.
- Spec: the bundled `role` type declares no `is_dev`; a workflow override that omits it loads;
  `sq workflow types --json` lists no `is_dev` among the role attributes
  (`tests/cli/test_workflow_types_cli.py` updated, nothing else in the payload changed).
- Generic payloads: after migration the item rows of `sq list -t role --json` and of the
  generic `show --json` carry no `is_dev`, and no other key changed (story 9).
- `sq update --set tech=...` on a role is still refused with exit 1 and `sq dev add` still
  writes `tech` (already true; pinned here as one row).
- Generated files are diffed as the task body describes (init against migrate then sync).
- A copy of this repository's squad, in scratch: `migrate up`, `sync`, `check`. Record which
  files changed and that `sq check` is clean. Never the live squad, with any build: the
  operator migrates it once, at release preparation.

**Falsify.** Leave `_retired_role_keys` reading the marker: the "second step changes no file"
invariant and the `model` invariant go red on the `--model` row. Then remove the key from the
retired set: the "no role item carries the key" column goes red. Then leave `is_dev` declared
on the bundled `role` type: the same column goes red. Restore each.

**Acceptance**

- Story 4, all bullets. The bullet about a squad carrying every contribution is met here
  for the comment-header, flat-frontmatter and this contribution; FEAT-976 adds its row. The
  bullet about this repository's squad is met here on the scratch copy.
- `tests/meta` passes: the runner guard, the migration-import guard, the `from_frontmatter`
  call-site table and the import-graph guard.
- The diff of this subtask under `src/squads/_migrations/` and `src/squads/_cli/_migrate.py`
  is the appended contribution and nothing else.
- `rg -n 'AttributeKey\.IS_DEV|attrs\.is_dev|is_dev=' src/squads` finds nothing, checked
  against the commit before.
- Adopter-visible, for the handoff: the `MANUAL` text, the summary clause, and `is_dev`
  leaving the role attributes (`sq workflow types --json`, the pinned set).

Gates and working rules: the task body.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
- [2026-10-16T20:23:17Z] Elias Python:
  - Falsification count 15. Broke (a) is_dev out of the retired role keys: 8 red (the marker stays on every developer row, plus the POSTCONDITIONS row); (b) the templated predicate always false: 7 red (a developer loses its model on the second rebuild). Restored, 21 green. Table: tests/cli/test_migrate_up_drops_the_developer_marker_cli.py (7 corpus shapes x migrate up, second migrate up, repair, delete index then repair: file hashes, name/tech/model, index values), a file missing from the index, unreadable YAML beside a healthy developer, and a 0.16 file still carrying the marker (reads through tech, check clean). Fixture tests/fixtures/corpus/v0_15_developers written by the released tool (README lists the commands); v0_16 regenerated by the README rule and is byte-identical. Dry run on a copy of the real squad (scratchpad real_copy, -C resolved to the copy, git status squads unchanged afterwards): migrate up, sync and check exit 0 and clean; both developer items (python-dev, typescript-dev) lost is_dev and kept title, model, tech; 948 files changed on migrate (4295 headers in 921 files, 27 flattened, 2 roles lost the marker), a second migrate changed nothing. The contribution is developer-capability; the manifest and content store were regenerated (the store rebuild was needed for workflow.toml).
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Report suffix-only -dev roles and pin their transitions

<!-- sq:subtask:ST9:body -->
**Goal.** A project role whose slug ends in `-dev`, not created by `sq dev add` and declaring
no capability, is an ordinary role. `sq migrate up` tells the operator which roles that
changes, and rewrites nothing for them.

**Approach**

- The behaviour itself is ST6's (the suffixed row of the shape-by-surface table). This
  subtask pins the transitions and adds the migration report.
- The report is the planning function of the contribution ST8 appends to the 0.16 step.
  For every role item, live or retired, whose slug ends in `-dev`, which carries no `tech`, and whose resolved definition holds none of the capabilities the squad's
  resolved `[dev]` table declares, it emits one line naming the slug and the line to add to
  its role file. A retired role is reported too, marked as retired, since it would come
  back without the guidance. The capability names come from the resolved catalog, so the
  line is right for a project that renamed them. A role with no definition at all (no catalog
  entry, no per-slug file) holds no capability and is reported the same way. The suffix the
  report reads lives in the runner; ST10's proposed-slug constant is the only other copy, and
  nothing reads it.
- Its inputs, as the task body's "Migration" section sets them out: the list of role items
  from the index the run reconciled; `slug` and `tech` from each role file's frontmatter
  passed through `flatten_frontmatter`, since the files are not flattened yet when it plans; the `[dev]` capabilities through the role loader and each candidate's
  definition through the role resolver, both given the context's squad directory. It
  resolves no workflow spec and no playbook.
- Its plan carries report lines and no failure. A per-slug role file that does not load does
  not stop the run either: that role gets a report line saying its definition could not be
  read, so the operator checks it after migrating.
- The lines travel on the plan's report, which the step prints under its own line when the
  run completes and not otherwise. That is why the remedy may name `sq sync`, which is
  refused while the squad is behind. This subtask edits no part of the report channel.
- No override file is opened for writing.
- The `MANUAL` section states the remedy and that there is no automatic fix.

**Tests**

- Transition table, on one suffixed role: as created (ordinary on all six surfaces, still on
  the roster, still assignable); after `capabilities = ["dev"]` is added to its role file and
  `sq sync` runs (identical to a declared developer on all six); after the line is removed
  and `sq sync` runs (ordinary again). The reverse row: a role not ending in `-dev` that
  declares the capability.
- Report table: role shape (suffixed and live; suffixed and retired; suffixed with the
  capability already declared; templated; a bundled role; a suffixed role whose role file no
  longer loads; a suffixed role with no definition left) by catalog (bundled `[dev]`; a project `[dev]` declaring another capability
  name) by run outcome (completes; refused by another contribution's planning function).
  Columns: reported or not, the printed line, exit code, and a hash of everything under
  `.overrides/` before and after.
- Invariant: the live slugs the migration reports are exactly the roles whose pointer skill
  list shrinks across the upgrade, measured by diffing the pointers the previous
  release generated against the ones generated after `sq migrate up` and `sq sync`.
- Invariant: on a run that another contribution refuses, none of this contribution's lines
  is printed.
- CLI smoke: `sq migrate up` prints the slug; `sq migrate chlog` over the step prints the
  remedy.

**Falsify.** Drop the "no `tech`" clause: the templated row is reported and goes red.
Then report only live roles: the retired row goes red. Then return the lines as failures
instead of report lines: the completed-run rows go red, since the run now refuses. Restore
each.

**Acceptance**

- Story 3, all bullets (the documentation bullet is TASK-991's).
- `tests/meta` passes with no exemption added for this contribution in the guard that a
  runner uses the run's resolved vocabulary.
- Adopter-visible, for the handoff: the exact report line and the `MANUAL` wording.

Gates and working rules: the task body.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
- [2026-10-16T20:23:20Z] Elias Python:
  - Falsification count 6. Broke (a) the held-capability test reduced to any capability: 1 red; (b) the templated branch (tech) removed from the planner: 5 red. Restored, 16 green. The planner reads each role file through flatten_frontmatter, reports roles named -dev that hold no capability the [dev] table declares (retired and no-role-file-left noted), carries no failure and writes nothing; a squad with none prints no report. The transition is pinned: declaring the capability then syncing gives a role named -dev the developer skills, dropping it takes them away.
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — Add sq dev add --slug and stop reading the suffix

<!-- sq:subtask:ST10:body -->
**Goal.** `sq dev add` proposes a slug and accepts an explicit one. Existing slugs never
change, and no read path consults the suffix.

**Approach**

- `_cli/_dev.py`: `sq dev add` gains `--slug`, documented in `--help`.
  `Service.add_dev(tech, *, name, model, slug)` and `resolve_dev_role` take it.
- Without `--slug`, the proposed slug is `<slugified tech>-dev` as today
  (`sq dev add --tech Node.js` proposes `node-js-dev`). That default is the one place the
  suffix is still written outside the migration runner: name it as a constant whose comment
  says it is a proposed spelling.
- An explicit slug is compared exactly, as `sq operator add --slug` does. The reserved-slug
  refusal (`operator`, `squads`, anything starting with `op-`) already sits at the seam
  every role creation passes through (`reserved_role_slug_problem` in `_models/_participants.py`,
  called from the create path in `_services/_base.py`). This subtask writes no check of
  its own: it makes sure the explicit slug reaches that seam, and pins the refusal for the
  new flag.
- `test_no_roster_verb_but_a_creation_verb_declares_a_slug_option`
  (`tests/cli/test_a_roster_slug_is_fixed_at_creation_cli.py`) fails on any `--slug` option under
  the roster groups outside an allowlist of creation verbs. `dev add` joins that allowlist, in the same
  commit as the flag.
- The per-slug override file merged at creation is the one named after the slug actually
  used, explicit or proposed.
- The duplicate check stays `_refuse_duplicate_slug`: an explicit slug is checked as given;
  a proposed one also against the earlier slug rule, as today. A second developer for one
  tech succeeds with `--slug`.
- The name-pool position counts the role items that carry the `tech` attribute (ST8).

**Tests**

- Table: `--tech` shape (`python`; `Node.js`; an accented name; surrounding whitespace) by
  `--slug` (absent; a fresh slug; the slug of an existing developer; the slug of an existing
  bundled role; `operator`; `squads`; `op-x`; an uppercase or spaced value) by squad state
  (no developer for that tech; one already). Columns: exit code, message, the stored
  attributes, the pointer file name, the full name drawn from the pool.
- `--name`, `--model` and the pool behave as before: the rows without `--slug` produce the
  same stored item and pointer as the previous release (compare against output generated by
  the commit before).
- Existing slugs across the upgrade: for a squad the previous release initialised with two
  developers, every developer keeps its slug, pointer file name, name and reflog history
  across `sq migrate up` and `sq sync`, and the pointer is byte-identical except for the
  sentences ST7 lists.
- Invariant: renaming a templated developer's role file, pointer or slug spelling in a
  fixture changes no answer on any surface, because nothing reads the spelling. Run the
  shape-by-surface table once more with a templated developer added as `--slug backend`.
- CLI smoke: `sq dev add --help` shows `--slug`.

**Falsify.** Route the explicit slug around the creation seam: the three reserved rows go
red. Then derive the override file name from the tech instead of the slug: the `--slug` row
with a per-slug file goes red. Restore each.

**Acceptance**

- Story 5, all bullets.
- Adopter-visible, for the handoff: the flag, its refusals, and that a second developer for
  one tech is possible.

Gates and working rules: the task body.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
- [2026-10-16T20:23:23Z] Elias Python:
  - Falsification count 6. Broke sq dev add --slug not reaching the stored slug: 6 red. Restored, 17 green. Table: tests/cli/test_dev_add_takes_a_slug_and_no_read_path_reads_the_suffix_cli.py (default, free and tech-bearing slug; refusals for the operator prefix, the grammar and a taken slug; the per-slug role file follows the stored slug). dev add joined the --slug allowlist of the roster-slug test.
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->

<!-- sq:subtask:ST11 -->
### ST11 — Resolve an unknown slug to nothing

<!-- sq:subtask:ST11:body -->
**Goal.** A slug that names no role resolves to nothing, whatever its spelling. The generated
preview for a `<tech>-dev` slug with no roster item is withdrawn.

**Approach**

- `_roles/_resolver.py`: `dev_base_for_slug` is deleted. It is the last function that turns
  a slug's spelling into a definition.
- Its three callers lose their spelling branch:
  - `_cli/_common.py::role_base_for_show` returns no base without an item, so
    `sq role <slug> show` (text and `--json`) exits 1 with the ordinary unknown-role error.
    `dev_preview_full_name` and the "unassigned, run `sq dev add`" card line in
    `_cli/_role.py` go with it.
  - `_overrides/_service.py::_shadowed_bundled_role_toml`: a slug that is neither bundled nor
    on the roster has no shadow baseline, so `sq override scaffold --role <slug>` exits 1
    the same way. A templated developer that is on the roster takes its baseline from its
    item (`role_base_from_item`).
  - `_overrides/_service.py::_check_role_override_resolves`: a partial
    `.overrides/roles/<slug>.toml` for a slug with no item and no catalog entry is reported,
    because it is resolved as a new role and is missing its required fields. `go-dev.toml`
    and `data-lead.toml` are reported alike.
- `sq dev add --tech go` still merges such a file at creation (`resolve_dev_role`), and
  `sq check` is clean afterwards.

**Tests**

- Table: slug shape (`go-dev`; `data-lead`; a bundled slug never activated; a templated
  developer on the roster; a retired developer) by override file (absent; partial; complete
  as a new role; malformed) by command (`sq role <slug> show`; the same with `--json`;
  `sq override scaffold --role <slug>`; `sq override diff`; `sq check`; `sq sync`). Columns:
  exit code and message.
- Invariant: for every slug with no roster item and no catalog entry, the row for a `-dev`
  spelling and the row for any other spelling are identical in every column.
- The sequence of the story: partial `go-dev.toml` (reported by `sq check`), then
  `sq dev add --tech go` (the file's fields are merged into the developer), then `sq check`
  clean.
- CLI tests assert the bare exit code.

**Falsify.** Restore the spelling branch in `_check_role_override_resolves`: the
`go-dev.toml` row stops being reported and the pairwise invariant goes red. Restore.

**Acceptance**

- Story 6, all bullets (the documentation bullet is TASK-991's).
- `rg -n 'dev_base_for_slug|dev_preview_full_name' src tests` finds nothing, checked against
  the commit before.
- Adopter-visible, for the handoff: the two exit-1 paths and the new `sq check` report, with
  the message text.

Gates and working rules: the task body.
<!-- sq:subtask:ST11:body:end -->

#### Discussion

<!-- sq:subtask:ST11:discussion -->
- [2026-10-16T20:23:26Z] Elias Python:
  - Falsification count 2. Broke the suffix read back into the override check (a generated base for an unadded -dev file): 2 red. Restored, 17 green. dev_base_for_slug, dev_preview_full_name and the three suffix reads are gone; role show on a slug nothing declares exits 1 for every spelling; a role file for an unadded dev slug is a new role that needs its fields, reported by sq check.
<!-- sq:subtask:ST11:discussion:end -->
<!-- sq:subtask:ST11:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T20:39:45Z] Olivia Lead:
  - 2026-10-09: authored from ADR-984 order of work, steps 4 to 6, covering stories 1 to 9; BUG-985 is fixed by ST3. Left in Draft; nothing promoted, no developer briefed. Open points before a developer can start, for op-pierre through @manager:
    
    1. **Working version.** `pyproject.toml` still reads 0.15.0 on `release/0.16`. This task changes bundled bytes, and the manifest generator would overwrite the shipped 0.15.0 entry. Who bumps to 0.16.0, and when?
    2. **This repository's squad.** The task proves the migration on a scratch copy only. Proposed: the live `sq migrate up` runs once, at release preparation, after FEAT-976 and FEAT-980 have amended the runner. The released 0.15.0 tool that runs the board cannot read a 0.16 squad, and one late run needs no temporary migration.
    3. **Story 8 against the decision.** Story 8's second and third bullets say a `[dev]` model change reaches an existing developer. ADR-984 ("Left out") and the feature's own exclusions keep `extra.model` as stored at `sq dev add`, so only the colour follows. ST3 follows the decision and pins "the stored model wins". @product-owner to reword the two bullets or reopen the exclusion.
    4. **One task or three.** The eleven subtasks have two points where the suite is green and the tree can be committed (after ST4, after ST7). They stay one task because one developer edits the same three modules throughout; splitting at those points is mechanical if preferred.
    
    Calls made in the bodies, to overturn if wrong: the "no capability name in code" grep excludes `_migrations/` as well as `_specs/`; the migration also reports retired suffix-only roles; `sq role show` prints colour on the text card and `--json` gains no `color` key; the delegate example is at most four live slugs in roster order, never the default role, with a developer included.
- [2026-10-11T20:15:30Z] Pierre Chat:
  - 2026-10-11: the working version stays 0.15.0 until release preparation. This task does not bump it and does not wait for a bump; the developer does not regenerate the template manifest.
- [2026-10-11T20:23:52Z] Olivia Lead:
  - 2026-10-11: brought in line with op-pierre's rulings of the same date (MILE-934). Still Draft.
    
    - **Working version.** The stop-and-report instruction is gone. The developer does not bump the version and does not regenerate the manifest. A new section, "Building at the released version", records what follows; ST2 and ST7 point at it.
    - **What follows, for whoever runs the suite.** From ST2 until release preparation two tests in `tests/meta/test_override_manifest_and_stamp_freshness.py` fail, and so does the CI `manifest freshness` step (read from the test and the workflow, not run). The developer records the exact set after the first bundled-byte change; the guard is not edited or skipped. If a standing red there is not acceptable, that needs a ruling before ST2, not before the task starts. @manager
    - **Drift.** It cannot be observed while stamp and running version both read 0.15.0, so it is proven by an in-suite test that sets a later running version and by a scratch copy at 0.16.0.
    - **Moved to release preparation:** the 0.16.0 manifest entry and the untouched 0.15.0 entry; the freshness tests and the CI step passing; drift observed with the unpatched build at 0.16.0; the live migration of this repository's squad.
    - **Live squad.** One `sq migrate up` by the operator at release preparation, after FEAT-976 and FEAT-980 amend the runner. The developer proves the migration on a scratch copy only.
    - **Model.** ST3's acceptance now states both directions: the colour follows a `[dev]` override on sync for an existing developer; the stored model does not change. It matches story 8 as reworded.
    - **One task**, reviewed after ST4, after ST7 and at the end.
    - Added to the handoff list: the hand-written `CLAUDE.md` sentences this task makes false (the `*dev` sentinel line, `dev_role()`). They are listed, not edited, since only TASK-989 has that file in scope.
- [2026-10-11T20:24:56Z] Catherine Manager:
  - Correction of attribution: keeping this as one task, reviewed at its commit points, is the manager's call, not a ruling by the operator. I relayed it to the tech lead as his answer in error.
- [2026-10-12T06:34:29Z] Olivia Lead:
  - 2026-10-12: brought in line with op-pierre's ruling of this date on MILE-934 (FEAT-980 first, then the bump to 0.16.0, then TASK-989 and this task). Still Draft. This replaces the parts of my 2026-10-11 comment about building at 0.15.0.
    
    - **Migration.** The task no longer creates the step or touches `SCHEMA_VERSION`. It adds one contribution to the runner FEAT-980 creates: the retired `is_dev` key, the read-only report of suffix-only `-dev` roles, a `MANUAL` section and a summary clause. ST8 and ST9 are rewritten and ST8 is retitled. A `depends-on` edge to FEAT-980 stands in until its task exists.
    - **What the contribution assumes** from the steps TASK-954 puts before the runner is written into the body: one context with the run's spec and playbook, a reconciled index, a corpus already checked against the vocabulary, nothing written on a refusal, and the remedy rule. Two consequences: the report is printed only when the run completes, because its remedy names `sq sync`; and the resolved role catalog is added to the context, since the report needs the `[dev]` table and ADR-955 A5 has every document a runner loads resolved once before the first write. @architect if A5 should be read otherwise for the role catalog.
    - **Manifest.** "Building at the released version" is replaced by "Bundled files and the manifest": regenerate with each bundled change, freshness checks green, drift observable with the dev build. One thing read and not run: an artifact changed twice at 0.16.0 leaves an unreferenced blob that fails one retention test until the store is rebuilt.
    - **Back in this task's acceptance:** the 0.16.0 manifest entry with the 0.15.0 entry untouched; the freshness tests and the generator's check passing; drift observed with the unpatched build for a catalog, a playbook, a per-slug role and a template override. Still at release preparation: the migration of this repository's own squad.
    - Unchanged: the model rule and ST3's two-way acceptance, the hazard that a second rebuild deletes `extra.model` unless the shape reads change with the retired key, the ban on running migrate, repair or sync on the live squad, and one task reviewed at its commit points.
- [2026-10-12T06:58:46Z] Olivia Lead:
  - 2026-10-12: aligned with TASK-1004, which now creates the 0.16 migration step. Still Draft.
    
    - **Migration section.** Rewritten: the step, `SCHEMA_VERSION`, `migrate()` and the report channel are TASK-1004's and this task edits none of them. It appends one contribution to the tuple and one row to the runner's test table. Planning function: the read-only report of suffix-only roles, with no failure in its plan. Writing function: none; the key leaves through the retired-key list and the rebuild after the runners. The `MANUAL` facts and the summary clause are stated, with the wording left to the tech writer through a comment here.
    - **ST8.** No longer adds the report channel or anything else outside the contribution. It gains a frozen 0.15 fixture with developers, written by the released tool: no corpus fixture holds a developer today, so my earlier line about goldens changing "for every corpus that holds a developer" covered nothing. It regenerates the `v0_16` fixture and the migrated-corpus goldens.
    - **ST9.** The report travels on the plan's report lines, which the step prints only for a run that completes. Role identity is read from each role file's frontmatter, as TASK-1004's contribution reads names, not from index entries.
    - **ST10.** The reserved-slug refusal is TASK-1004's (ST3), at the seam every role creation passes through; this subtask no longer writes one. `dev add` joins the allowlist of TASK-1004's test that fails on any `--slug` option under the roster groups.
    - **Gates.** `sq check` is now spelled `~/.local/bin/sq check`, with a rule that the dev build is not run at the repository root: from TASK-1004 on it refuses everything there but `sq migrate up`.
    - **Refs.** `depends-on FEAT-980` replaced by `depends-on TASK-1004`.
- [2026-10-12T06:58:50Z] Olivia Lead:
  - 2026-10-12, for @architect: my question of this morning about the role catalog, restated against the contributions shape. It replaces the earlier wording.
    
    The retirement's planning function needs two things `MigrationContext` does not carry: the capabilities the squad's resolved `[dev]` table declares, and the resolved definition of each role whose slug ends in `-dev`. Both come from the role catalog override and the per-slug role files.
    
    The task is now written this way: the planning function reads them itself, through the role loader and the role resolver given `ctx.paths.squad_dir`. That keeps the change to "one contribution and one row", it is read-only, and it runs before any write of the step. The catalog has in fact loaded once already by then, because resolving the playbook reads it for its list of role slugs (read in `_interactions/_loader.py`, not driven), so a catalog override that does not load stops the run before the first runner either way.
    
    Two things to rule:
    
    1. ADR-955 A5 says the vocabulary is resolved once, before the first write, together with every other document a pending runner loads. Does the role catalog have to travel on `MigrationContext` for that to hold? If so the change is to the context and to `run_pending_migrations`, outside the contribution, and per-slug role files would still be read by the resolver at planning time.
    2. Should the static guard on runners ban the role loader and resolver as it bans the spec and playbook resolvers? As written, the task tells the developer to report, not to add an exemption, if it does.
- [2026-10-16T18:21:55Z] Olivia Lead:
  - 2026-10-16: refreshed against today's release/0.16 (flat frontmatter, the contributions-based 0.16 step, TASK-989's moves, the stored-name rule, the BUG-1065 model ruling). Scope unchanged; no new stored state.
  - Removed as done: the merge and version-bump preconditions (TASK-989, TASK-954, TASK-1004 Done; working version 0.16.0); `tech` leaving the settable role fields (already `settable = false`, ST8 keeps one pinning row); the claim that no corpus fixture holds a developer (`v0_15_discussions` has `python-dev`, whose migrated golden loses `is_dev: true` in ST8).
  - Re-pointed: `extra.*`/`ExtraKey`/`X.IS_DEV` to top-level attributes, `AttributeKey` and `attrs.*` in `_models/_attributes.py`; `RETIRED_ROLE_KEYS`, `_retired_role_keys`, `_refresh_catalog_attributes`, `_exempt_attribute_keys`, `to_attributes`/`stored_attribute_keys`, `RoleDef.from_item`, `_ATTRIBUTE_FIELDS`; ST1 drops stale line numbers; ST10 names the reserved-slug seam and the `--slug` allowlist test.
  - ST8: one `Contribution` appended after `flat-frontmatter`, no writer; `is_dev` joins `RETIRED_ROLE_KEYS` and leaves both `[items.role.attributes]` and `PINNED_ROSTER_ATTRIBUTES` in the same commit (a still-declared name is never swept). The flat contribution's frozen key set is not edited. Model stays developer-only here; BUG-1065 is not folded in.
  - ST9: the planner reads `slug`/`tech` through `flatten_frontmatter`, since it plans before the flat writer; it also reports a suffixed role with no definition left. ST3: the stored name is pinned in every row.
  - My 2026-10-12 @architect question on the role catalog and `MigrationContext` is settled by the guard as landed: it bans the spec and playbook resolvers, not the role loader or resolver, so the planner reads the catalog itself and the context is not widened. Moved to Ready. @manager
- [2026-10-16T18:54:44Z] Elias Python:
  - Checkpoint after ST1 to ST4 (tree uncommitted, suite not run by me beyond the targeted floor). Adopter-visible changes so far, for the writer:
    
    - New role document key `capabilities`, a list of names matching `[a-z0-9][a-z0-9-]*` (lowercase letters, digits, hyphens, not starting with a hyphen). It is accepted on a `[[roles]]` entry and on `[dev]` in `.overrides/roles.toml`, and in a per-slug `.overrides/roles/<slug>.toml`. A per-slug value replaces the base list; the splat form `["$(*self)", "x"]` appends; a repeated name resolves once. The bundled `[dev]` table declares `capabilities = ["dev"]`; the eight bundled roles declare none. A malformed name is refused naming the file, by `sq check` (exit 3, its error code) and `sq sync` (exit 1). An older package refuses a catalog or role document that carries the key.
    - A wrong-typed value on a `[[roles]]` entry (for example `capabilities = "dev"`) now names `.overrides/roles.toml` in the error, as every other catalog error does.
    - `capabilities` is an additive key, always an array, in `sq role catalog --json`, `sq role list --json`, `sq role <slug> show --json` (empty for a role whose definition is gone), and each `roster[]` row of a `playbook` view payload. No other key changed.
    - Text: `sq role list` gains a Capabilities column; the `sq role <slug> show` card gains `capabilities:` and `color:` rows. `--json` gains no `color`.
    - Fixes the colour half of BUG-985: an existing developer's definition is regenerated from the `[dev]` table of the squad's resolved catalog, so a `[dev]` colour added or changed after the developer was added reaches its pointer on the next `sq sync`, and a second sync changes nothing. The stored model and the stored name do not change: a `[dev]` model change reaches only developers added afterwards, and a changed `name_pool` feeds only the next `sq dev add`.
    - Override drift: with the bundled `roles.toml` changed, a catalog override and a per-slug role file stamped 0.15.0 report `drifted` in `sq override list`; stamped at the running version they report `current`. `sq check` prints "may be stale" for workflow and playbook overrides only; it has no such line for role documents (read in the code, driven in the suite).
    - New-role scaffold and the catalog scaffold comment document `capabilities`.
    
    For the hand-written part of CLAUDE.md, listed not edited (ST5 and later make these false; nothing in ST1 to ST4 does): the `*dev` sentinel line and the `dev_role()` mention.
- [2026-10-16T19:04:24Z] Paul Reviewer:
  - Checkpoint ST1-ST4 reviewed in REV-1068: 2 medium (F1 lane-exemption bundled fallback, F2 false sq check drift claim), 6 low. @python-dev @manager
- [2026-10-16T19:45:55Z] Elias Python:
  - Correction to my ST1 to ST4 note for the writer: `sq check` does warn "may be stale" for role documents. A catalog override (`.overrides/roles.toml`) and a per-slug role file stamped at the previous release warn (exit 0) once the bundled `roles.toml` changed; the same holds for the playbook override and a template override when their bundled counterparts changed. All four also show as `drifted` in `sq override list`; stamped at the running version they are silent.
    
    ST5 to ST7, adopter-visible, for the writer:
    
    - A playbook guide subject can be `*<name>`: it addresses every live role whose `capabilities` list holds that name. A bundled guide `*dev` is the same form; nothing in the engine knows the name `dev`. Guides addressed to a capability render their section only while a live role holds it, under a heading naming the capability and listing the holders ("## For `*dev`: Elias Python (`python-dev`), ..."); the old heading "For developers" is gone from the per-type skills.
    - A capability subject is checked at load: `*Dev`, `*`, `* dev` are refused, naming `.overrides/playbook.toml`. Any error in a merged playbook now starts with the override file's path.
    - `authors = true` on a capability guide puts the type in the create lane of every holder (`sq role <slug> show`, the out-of-lane advisory on `sq create`).
    - `sq check` and `sq sync` warn about an override guide whose capability no live role holds ("names no live role ... declare `capabilities = [\"<name>\"]` on a live role, or remove the guide"); a bundled capability guide stays silent when nobody holds it.
    - A developer is a live role holding a capability the `[dev]` table declares: `sq dev list` lists templated and declared developers alike (live ones only), and a role merely named `...-dev` without the capability loses the developer guidance (pointer skills, section, example assignee).
    - Generated text: the CLAUDE.md sentence "a developer's slug is `<tech>-dev`" is gone; the delegate examples are up to four live roles in roster order (never the default role, a developer included when one is live); the example `--assignee` is a live developer, else the first live role; the six `<tech>-dev` placeholders in the bundled playbook guide text read `<developer>`; the memory skill no longer names `python-dev`.
    - Hand-written CLAUDE.md sentences made false, not edited: the `_interactions/` bullet ("`*dev` sentinel = any `<tech>-dev` role") should read "a guide subject is a role slug or `*<capability>`"; the `_roles/_catalog.py` bullet loses `dev_role()`. Proposed wording for the first: "which roles interact with each item type (a guide addresses a role slug, or every role holding a capability with `*<capability>`)".
- [2026-10-16T20:23:28Z] Elias Python:
  - ST8 to ST11, adopter-visible, for the writer:
    
    - `sq migrate up` (0.16 step, contribution "developer-capability"): removes the stored `is_dev` key from role items and changes nothing else in them; a developer keeps its name, `tech` and `model`. The MANUAL section (`sq migrate chlog v0.15.0..v0.16.0`) states the facts: a developer is a role that declares a capability the `[dev]` table declares; a reported role keeps working as an ordinary role and regains the developer guidance when its role file declares the capability and `sq sync` runs (no automatic fix); an override file for a developer not yet added is now reported by `sq check` (ways out: `sq dev add` or remove the file); an existing developer picks up a project `[dev]` colour on the next `sq sync` and keeps its model and name; stamped catalog, playbook, workflow and per-slug role overrides report "may be stale". Summary clause: "The developer marker is dropped from role items, and roles named -dev that declare no capability are reported."
    - Report line printed by the run, only when it applies: "N role(s) named -dev hold no developer capability and are now ordinary roles; declare the capability in the role file and run `sq sync` to restore the developer guidance:" followed by one indented slug per line, with "(retired)" and "(no role file left)" notes.
    - `sq dev add --slug <slug>` stores the developer under that slug (default `<tech>-dev`); the slug follows the same rules as any role (grammar, not `op-` prefixed, not taken).
    - `is_dev` is no longer a declared role attribute; a role is templated when it carries `tech`. A 0.16 role file that still carries `is_dev: true` keeps it as an undeclared key until the next rebuild.
    - A role file for a `-dev` slug that is not on the roster is no longer previewed against a generated developer: `sq role <slug> show` says no such role, and `sq check` reports the file as a new role missing its required fields.
    - Per-type skills write a reference to a role the squad lacks (`--author tech-lead`, `@reviewer` and the like) as `<slug>`.
    - Merged-playbook errors name the override file once; `sq role catalog --json` capabilities are the catalog document's value.
    
    Hand-written CLAUDE.md sentences these make false (not edited): line 88 "`dev_role()`" (gone; developers are built from the `[dev]` table of the resolved catalog); lines 89-90 "`*dev` sentinel = any `<tech>-dev` role" (proposed: "a guide subject is a role slug, or `*<capability>` for every role holding it"). The `<tech>-dev` sentences at lines 309 and 341 are inside the managed region and regenerate on the next `sq sync`.
- [2026-10-16T21:01:48Z] Catherine Manager:
  - Done: REV-1068 approved; committed fce1019d; merged suite 11742 passed, 0 failed (8cc6d3b5).
<!-- sq:discussion:end -->
