---
id: TASK-990
sequence_id: 990
type: task
title: Make a developer a role that declares a capability
status: Draft
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
description: Capabilities on roles and *<name> in the playbook, every consumer on
  the resolved role, extra.is_dev dropped, the 0.16 migration step created
subentities:
- local_id: ST1
  title: Require the catalog and playbook on the role derivation path
  status: Todo
- local_id: ST2
  title: Declare capabilities and resolve them onto the role
  status: Todo
  story: US1
- local_id: ST3
  title: Read the developer template from the resolved catalog
  status: Todo
  story: US8
- local_id: ST4
  title: Expose capabilities in --json and role text output
  status: Todo
  story: US9
- local_id: ST5
  title: Address a capability from the playbook with *<name>
  status: Todo
  story: US1
- local_id: ST6
  title: Switch every consumer to the resolved role
  status: Todo
  story: US2
- local_id: ST7
  title: Name roles from the roster in generated text
  status: Todo
  story: US7
- local_id: ST8
  title: Drop extra.is_dev and create the 0.16 migration step
  status: Todo
  story: US4
- local_id: ST9
  title: Report suffix-only -dev roles and pin their transitions
  status: Todo
  story: US3
- local_id: ST10
  title: Add sq dev add --slug and stop reading the suffix
  status: Todo
  story: US5
- local_id: ST11
  title: Resolve an unknown slug to nothing
  status: Todo
  story: US6
created_at: '2026-10-09T20:28:02Z'
updated_at: '2026-10-11T20:24:56Z'
---
<!-- sq:body -->
## Scope

"Is this role a developer?" has two answers today, a stored marker (`extra.is_dev`) and a slug
spelling (`slug.endswith("-dev")`), and they disagree for the same role in one squad. This
task replaces both with one declared, resolved fact (ADR-984, order of work, steps 4 to 6):

- a role declares `capabilities`; the playbook addresses a capability with `*<name>`;
- the capability is computed once, in `resolve_role_for_item`, and travels on `RoleDef` and
  `RoleView`; nothing below the resolver decides anything from a slug string;
- a developer is either templated (`sq dev add`, selected by `extra.tech`) or declared (a
  role file with the capability), and both are treated alike on every surface;
- `extra.is_dev` is removed and existing squads are migrated by the release's one
  0.15 to 0.16 step, which this task creates.

It fixes the colour half of BUG-985 (a developer's model stays as stored, by decision) and
covers stories 1 to 9 of FEAT-986. Story 10 (documentation) is TASK-991.

## Before the first edit

- TASK-989 is merged: the import-graph guard exists, `RoleView` lives in `_roles/`, and the
  role derivations live in their own module. TASK-954 is merged: `run_pending_migrations`
  reconciles the index before the first runner, and this task adds a runner behind it.
- **The working version reads 0.15.0 and stays there** until release preparation. Do not
  bump it and do not wait for a bump. "Building at the released version" below says what
  follows from that.
- Not built in parallel with FEAT-961 (pronouns) or the `[defaults]` table of ADR-981: they
  extend the same role models and the same closed key space.

## Subtasks, in build order

The order is the decision's. It is one task, reviewed at two commit points, after ST4 and
after ST7, and at the end. At each, the suite is green apart from the manifest freshness
failures recorded under "Building at the released version".

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

- **ST8, drop `extra.is_dev` and create the 0.16 migration step** (US4).
- **ST9, a suffix-only `-dev` role is ordinary, and the migration reports it** (US3).
- **ST10, `sq dev add --slug`, and no read path consults the suffix** (US5).
- **ST11, an unknown slug resolves to nothing** (US6).

One developer, one pass: every subtask edits the same three modules
(`_interactions/_role_guidance.py`, `_roles/_resolver.py`, `_roles/_catalog.py`).

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
- It starts from the characterisation tables of TASK-989; the rows this task changes are the
  suffixed and declared ones.

## Migration and schema

- **One step for the release.** `SCHEMA_VERSION` becomes `"0.16"`. One new runner module,
  `_migrations/_v0_15_to_v0_16.py`, and one `Migration` entry in `_registry.py`
  (`version="0.16.0"`, `from_schema="0.15"`, `to_schema="0.16"`).
- **What the runner contains for this feature.**
  - No file write of its own. `extra.is_dev` joins the closed list of retired role keys in
    `_models/_metadata.py`, and the rebuild that `run_pending_migrations` runs after the
    runners strips it from every role file and from the index (see "What was driven").
  - A read-only report: every role item whose stored slug ends in `-dev`, carries no
    `extra.tech`, and whose resolved definition holds none of the capabilities the squad's
    resolved `[dev]` table declares. One line per slug, exit code unchanged, no override
    file read for writing or rewritten. A migration runner is the one place that may know
    the retired spelling.
  - The `MANUAL` text for this contribution: the remedy for a reported role (declare the
    capability in its role file, then `sq sync`); that an override file written for a
    developer not yet added is now reported by `sq check`; that an existing developer picks
    up a project `[dev]` override on the next `sq sync`; and that a stamped catalog,
    playbook or per-slug role override reports "may be stale" because the bundled documents
    changed (`sq override diff`, then `sq override update`).
- **How later contributors amend it.** The runner is written as a list of contributions,
  each with a read-only planning function, an optional writing function, a section of
  `MANUAL` and a clause of the summary line. `migrate()` runs every planning function before
  the first write, so a contribution that must refuse (the comment-header rewrite of
  FEAT-980) refuses with nothing written. FEAT-976 and FEAT-980 add their contribution to
  this module and edit this one registry entry. They add no second entry and do not touch
  `SCHEMA_VERSION`. The runner's test module is a table of contributions over corpus
  fixtures, so a later contributor adds a row and the "all contributions in one
  `sq migrate up`" assertion grows with it.
- **This repository's own squad.** It is migrated once, by the operator, at release
  preparation, after FEAT-976 and FEAT-980 have amended the runner. The developer never runs
  `sq migrate up`, `sq repair` or `sq sync` on it, with any build. The proof that it
  migrates is made on a copy: copy `squads/` and `.squads.toml` into a scratch directory,
  run the dev build's `migrate up`, `sync` and `check` there, and record the result in the
  handoff (both developer items lose the key, `sq check` is clean, the list of files that
  changed).

## Building at the released version

The package reads 0.15.0 while this task changes bundled bytes (`_specs/roles.toml`,
`_specs/playbook.toml`, templates under `_rendering/templates/`). Five things follow.

- **The manifest is not regenerated.** Do not run `scripts/gen_template_manifest.py` in
  write mode, `scripts/seed_content_store.py` or `scripts/bump_version.py`, and do not edit
  `templates_manifest.json` or `content_store.json` by hand. The generator replaces the
  index entry of the current version, which is the shipped 0.15.0 entry. At release
  preparation the bump script restores that entry from its tag, bumps the version and
  regenerates, which adds the 0.16.0 entry.
- **The manifest freshness checks fail from ST2 onward and stay failing until release
  preparation.** Read, not run: in `tests/meta/test_override_manifest_and_stamp_freshness.py`,
  `test_the_index_has_a_current_version_hash_for_every_overridable_bundled_artifact`
  ("manifest hashes are stale for" each changed key) and
  `test_artifact_changed_since_is_content_gated_for_every_kind` (for `roles.toml` and
  `playbook.toml`); and the `manifest freshness` step of the CI lint job, which runs the
  generator's `--check` on pushes and pull requests to `main`. After the first bundled-byte change, run `tests/meta` and record in
  a task comment every failing test and the artifact keys it names. That list is the
  expected set: it holds only freshness failures for artifacts this task changed, and it is
  recorded again when ST7 changes more. The guard is not edited, skipped or marked as an
  expected failure. Any other failure is real.
- **Override drift cannot be observed with this build.** The drift state compares the
  override's stamp with the running version first. While both read 0.15.0 an override
  reports `current` and `sq check` is silent, whatever the bundled bytes are (driven). So no
  test asserts drift through the real version. The behaviour is proven two ways:
  - in the suite, by a test that sets the running version the override service compares
    against to a later one, over overrides stamped 0.15.0, and asserts `drifted` in
    `sq override list` and "may be stale" in `sq check` for the catalog, the playbook, a
    per-slug role file and (ST7) a template, with the control at the real version
    (`current`, silent);
  - by hand, on a scratch copy of the built package with `__version__` set to `"0.16.0"` in
    the copy's `__init__.py`, run against a scratch squad whose overrides the released tool
    scaffolded. The output goes in the handoff.
- **A stamp written by this build is misleading.** `sq override scaffold` stamps 0.15.0 onto
  bytes that are no longer 0.15.0's, so the base content the store holds for that stamp is
  the released text, not the text scaffolded from. Upgrade fixtures and probes use a squad
  and overrides made by the released tool (`~/.local/bin/sq`, in a scratch squad). An
  existing test that needs the base content to equal the current content is reported, not
  patched around.
- **The registry entry names release 0.16.0 while the package reads 0.15.0.**
  `sq migrate up` and `sq migrate chlog` take their span from the registry, not from the
  running version (read). Report any test that ties the two.

**Moved to release preparation**, and not part of this task's acceptance:

- the manifest carries a 0.16.0 entry for the changed artifacts and its 0.15.0 entry is
  byte-identical to the tag (`scripts/gen_template_manifest.py --release-gate`);
- the two freshness tests above and the CI `manifest freshness` step pass;
- drift is observed with the unpatched build at 0.16.0, on a squad upgraded from 0.15.0, for
  a catalog, a playbook, a per-slug role and a template override;
- this repository's own squad is migrated, which is when story 4's last bullet becomes true
  of the live squad.

## What was driven, and what is left to confirm

Driven in scratch squads on 2026-10-09, with the dev build at `d07b0e50` and a scratch copy
of the package carrying the stated one-line change.

- **The retired-key sweep removes `is_dev` with no runner code (driven).** With `"is_dev"`
  added to `RETIRED_ROLE_EXTRA_KEYS`, `sq repair` (the rebuild `run_pending_migrations`
  calls) removed the key from two developer files and from the index and kept `tech` and
  `model`.
- **A second rebuild then deletes `extra.model` (driven).** `_retired_role_extra_keys` reads
  `extra.is_dev` to decide whether `model` is a stored key. Once the marker is gone the
  developer reads as a non-developer and the next rebuild strips `model` (an operator's
  `--model opus` was lost). With that one read changed to "carries `extra.tech`", two
  rebuilds left `model` in place and the second wrote nothing (identical tree hash). ST8
  changes all three shape reads in the same commit as the retired key.
- **Changed bundled bytes make a stamped override report drift (driven).** Catalog and
  playbook overrides stamped 0.15.0, bundled `roles.toml` and `playbook.toml` each changed by
  one line: at running version 0.16.0, `sq override list` shows both as `drifted` and
  `sq check` warns "may be stale" for each, exit 0. At running version 0.15.0 the same bytes
  report `current` and no warning.
- **Not driven:** `sq migrate up` end to end (no 0.16 runner exists yet); the per-slug role
  override stamp and the template override stamp, which use the same predicate (read,
  `_overrides/_service.py`); `sq sync`'s wording for the same drift. ST8 and ST7 confirm
  these as their first step.

## Acceptance (whole task)

- The lines under "Moved to release preparation" are not acceptance of this task.
- Each subtask's own acceptance holds, and every acceptance bullet of stories 1 to 9 is
  pinned by a named test. The handoff maps bullet to test.
- **Table-driven tests over named shape families**, as each subtask lists, with the
  shape-by-surface table as the shared backbone. A row that needs its own fixture still goes
  through the same assertions as its neighbours.
- **Pipeline-level invariants**, each stated in its subtask: sync is a fixed point; migrate
  then sync converges on what a fresh init produces for the same roster; migrate is
  idempotent and never touches `extra.tech` or `extra.model`; the index is rebuildable from
  the files with identical values.
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
- `rg -n 'endswith\("-dev"\)|removesuffix\("-dev"\)|is_dev_slug|X\.IS_DEV|dev_base_for_slug|"\*dev"' src/squads`
  finds nothing outside `_migrations/` and `_specs/`, checked against the known positives of
  the commit before. The scan also collapses wrapped lines, or it proves nothing.

## Gates and working rules

- `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .` and `sq check` are clean before handback. A
  bare `uv run` prunes the optional `tui` extra and reports false import errors.
- Any change under `_specs/`, `_rendering/templates/` or `_cli/` runs `tests/meta`,
  `tests/integration` and `tests/cli`. Beyond that floor, derive the selection from the
  diff: grep each changed name (spec key, template path, payload field, function) across
  `tests/` and run that union, redirected to a file and read from the file. Report the
  selectors. The manager runs the full suite afterwards.
- Run `uv run --all-extras pytest tests/meta` whenever a module-level constant is added (the
  mutable-state guard), a bundled document or template changes (to record the expected
  freshness failures again; the manifest is not regenerated), a migration module is added,
  or an import edge changes (the guard of TASK-989).
- Comments and docstrings are one or two sentences, with no release versions, ticket ids or
  history. The migration runner is the one exception for versions. Several docstrings on
  this path explain the marker at length; they are rewritten to what the code does now, not
  extended.
- No ticket ids in source or in test file names: name a test file by the behaviour it pins.
- `type X = ...` for aliases. A multi-exception handler is parenthesised and carries
  `# fmt: skip`. No `from __future__ import annotations`. Time goes through `clock`.
- User-facing errors are `SquadsError` subclasses. Dynamic text printed to the console goes
  through `e()`. `Item.extra` keys come from `ExtraKey`; a retired key that loses its member
  is spelled once, by name, beside the retired-key list.
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
  (`_cli/_common.py:1363`, `_cli/_main.py:1607` and `:1614`: `sq repair` and the degraded
  `sq check` paths). They are not changed here. If a row of the table below, or of the
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
  declare none. This is the first bundled-byte change of the task. The manifest is not
  regenerated: run `tests/meta` afterwards and record the expected freshness failures in a
  task comment, as "Building at the released version" in the task body describes. Update
  the golden lock in `tests/unit/test_role_catalog_artifact.py` and the roles scaffold body
  in `_overrides/_service.py` if it documents the `[dev]` keys.
- `_roles/_loader.py`: a name must match `[a-z0-9][a-z0-9-]*`. Check it for every `[[roles]]`
  entry and for `[dev]` in `_validate`, with the existing error prefix that names the file.
  `_roles/_resolver.py::_apply_override` makes the same check for a per-slug role file and
  names that file, as a hand-written sentence like the model check beside it, not a pydantic
  dump. One definition of the pattern, used by both.
- `_roles/_catalog.py`: `RoleDef.capabilities: tuple[str, ...] = ()`. `role_spec_to_def`
  carries it; `dev_role_from_pool` takes it from the pool spec it is given;
  `from_extra_or_item` yields none. It is **not** added to `_EXTRA_FIELD_KEYS`: nothing new
  is stored on an item.
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
- The developer's capabilities now arrive from `[dev].capabilities` of the resolved catalog
  by the same path, which is what ST6 relies on.
- `extra.model` stays the stored value for a developer (ADR-984, "Left out"; story 8):
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
  colour; sets model). Columns: pointer `model` and `color` after one sync and after two,
  and the same two values on `sq role <slug> show`.
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
    existing developer's `extra.model`, its pointer and its `sq role <slug> show` on the
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

- Story 9, except the bullet about `extra.is_dev` leaving the generic `show` and `list`
  payloads, which ST8 pins once the key is gone from the corpus.
- The handoff lists the four payloads and the two text outputs for the writer.

Gates and working rules: the task body.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
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
suffixed rows go red on every surface. Then make `sq dev list` filter on `extra.tech`: the
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
- Bundled bytes change here, in templates and in `playbook.toml`. The manifest is not
  regenerated: record the expected freshness failures again ("Building at the released
  version" in the task body), and update the goldens that pin rendered output
  (`tests/goldens`, `tests/unit/test_managed_section_and_cheatsheet_goldens.py`). First
  step: prove that a stamped template override and a stamped playbook override report "may
  be stale" after the change, by the two methods the task body gives (the in-suite test
  with a later running version, and the scratch copy at `0.16.0`), and record the output.
  The playbook and catalog cases were driven on 2026-10-09; the template case was only read.

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
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Drop extra.is_dev and create the 0.16 migration step

<!-- sq:subtask:ST8:body -->
**Goal.** No role item carries `extra.is_dev`. "Templated" is derived: a role item that
carries `extra.tech`. Existing squads are migrated by the release's one 0.15 to 0.16 step,
which this subtask creates.

**First step: confirm what was driven.** The task body records two results from a patched
scratch copy: the retired-key sweep strips `is_dev` with no runner code, and a second
rebuild deletes `extra.model` unless the role's shape is read from `extra.tech`. Reproduce
both on the real change before writing the runner: one `sq migrate up` on a scratch squad
the released tool initialised with two developers (one added with `--model opus`), then a
second `sq repair`, hashing the tree after each. Record the output in a subtask comment.

**Approach**

- Storage (`_models/_extras.py`, `_models/_metadata.py`, `_roles/_catalog.py`):
  - `ExtraKey.IS_DEV` is deleted. The retired key is spelled once, by name, beside
    `RETIRED_ROLE_EXTRA_KEYS`, and joins that set (the pattern `extra.skills` already
    follows).
  - `Field(X.TECH)` leaves `_ROLE_FIELDS`: `extra.tech` is no longer settable on a role
    item, and the refusal names `sq dev add`. The generic field of the same name for work
    types stays.
  - `RoleDef.to_extra`, `stored_extra_keys` and the developer-only key table are renamed
    off "dev" (suggested: `templated`), since the question they answer is "is `model` a
    stored key for this role".
- The three shape reads change together, to "the item carries `extra.tech`":
  `_services/_maintenance.py::_retired_role_extra_keys`, the `to_extra` call in
  `_refresh_catalog_extra`, and `_itemfile.py::_exempt_extra_keys`. So do the resolver's
  branch in `role_base_from_item` and the name-pool count in `Service.add_dev`, which stops
  writing the marker.
- Schema and runner, as the task body's "Migration and schema" section settles them:
  `SCHEMA_VERSION = "0.16"`; `_migrations/_v0_15_to_v0_16.py` with the contribution list,
  the planning-before-writing order and its `MANUAL`; one registry entry. This feature's
  contribution writes nothing itself. The runner returns its report lines through
  `MigrationOutcome` (a new field with an empty default, so no released runner changes),
  `MigrationRun` carries them and `sq migrate up` prints them. The summary line and the
  `MANUAL` section are written so a later contributor appends to them.
- The schema bump reaches every test and fixture that pins the current schema or builds an
  aged corpus. Derive the list by grepping the old version string across `tests/`.
- A build with this change reads a role item that still carries the marker: the key is
  ignored, the item resolves through `extra.tech`, and `sq check` is clean for it.

**Tests**

- Table: corpus shape by step. Corpus shapes: no developer; one templated developer; two,
  one with `--model`; a developer with a per-slug override; a developer whose stored title
  is blank; a retired developer; a declared developer; a suffixed role; a role file with
  unreadable YAML beside a healthy developer; a developer file that is on disk but missing
  from the index. Steps: `sq migrate up`; a second `sq migrate up`; `sq repair`; delete the
  index then `sq repair`. Columns: which files changed (hash them), the `extra` of each role
  in the file and in the index, the schema stamp, exit code and printed lines.
- Invariants, for every row: `extra.tech` and `extra.model` are byte-identical before and
  after every step; the second and later steps change no file; the index after "delete then
  repair" equals the index before; no key appears in `.squads.json` that the files do not
  carry.
- The runner test module is a table of contributions over corpus fixtures, with this
  feature's as its first row, and asserts one registry entry reaches the current schema.
- Un-migrated read: a squad stamped at the current schema whose developer file and index
  both still carry the marker resolves as a developer on every surface of the
  shape-by-surface table, and `sq check` is clean.
- Generic payloads: after migration the `extra` object of `sq list -t role --json` and of the
  generic `show --json` carries no `is_dev`, and no other key changed (story 9).
- `sq role <slug> update`-style writes of `tech` are refused with exit 1; `sq dev add` still
  writes it.
- Generated files are diffed as the task body describes (init against migrate then sync).
- A copy of this repository's squad, in scratch: `migrate up`, `sync`, `check`. Record which
  files changed and that `sq check` is clean. Never the live squad, with any build: the
  operator migrates it once, at release preparation.

**Falsify.** Leave `_retired_role_extra_keys` reading the marker: the "second step changes
no file" invariant and the `model` invariant go red on the `--model` row. Then remove the
key from the retired set: the "no role item carries the key" column goes red. Restore each.

**Acceptance**

- Story 4, all bullets. The bullet about a squad carrying all three contributions is met
  here by the runner's shape and its contribution table; FEAT-976 and FEAT-980 add their
  rows. The bullet about this repository's squad is met here on the scratch copy.
- `tests/meta` passes with the new migration module, apart from the recorded freshness
  failures (the migration-import guard, the
  `from_frontmatter` call-site table).
- Adopter-visible, for the handoff: the schema step, the printed report, the `MANUAL` text,
  and the refusal on `tech`.

Gates and working rules: the task body.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
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
- The report is this feature's planning function in `_migrations/_v0_15_to_v0_16.py`: for
  every role item, live or retired, whose stored slug ends in `-dev`, which carries no
  `extra.tech`, and whose resolved definition holds none of the capabilities the squad's
  resolved `[dev]` table declares, emit one line naming the slug and the line to add to its
  role file. A retired role is reported too, marked as retired, since it would come back
  without the guidance. The capability names come from the resolved catalog, so the line is right for
  a project that renamed them. The suffix literal lives in the runner and nowhere else.
- No override file is opened for writing. The report does not change the exit code.
- The `MANUAL` section states the remedy and that there is no automatic fix.

**Tests**

- Transition table, on one suffixed role: as created (ordinary on all six surfaces, still on
  the roster, still assignable); after `capabilities = ["dev"]` is added to its role file and
  `sq sync` runs (identical to a declared developer on all six); after the line is removed
  and `sq sync` runs (ordinary again). The reverse row: a role not ending in `-dev` that
  declares the capability.
- Report table: role shape (suffixed and live; suffixed and retired; suffixed with the
  capability already declared; templated; a bundled role; a suffixed role whose role file no
  longer loads) by catalog (bundled `[dev]`; a project `[dev]` declaring another capability
  name). Columns: reported or not, the printed line, exit code, and a hash of everything
  under `.overrides/` before and after.
- Invariant: the live slugs the migration reports are exactly the roles whose pointer skill
  list shrinks across the upgrade, measured by diffing the pointers the previous
  release generated against the ones generated after `sq migrate up` and `sq sync`.
- CLI smoke: `sq migrate up` prints the slug; `sq migrate chlog` over the step prints the
  remedy.

**Falsify.** Drop the "no `extra.tech`" clause: the templated row is reported and goes red.
Then report only live roles: the retired row goes red. Restore each.

**Acceptance**

- Story 3, all bullets (the documentation bullet is TASK-991's).
- Adopter-visible, for the handoff: the exact report line and the `MANUAL` wording.

Gates and working rules: the task body.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
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
- An explicit slug is compared exactly, as `sq operator add --slug` does, and is checked
  against the reserved-slug rules of ADR-979: `operator`, `squads`, and anything starting
  with `op-` are refused with exit 1, and the message names the rule. Write that check as one
  function that other role-creation paths can call; FEAT-980 extends its callers.
- The per-slug override file merged at creation is the one named after the slug actually
  used, explicit or proposed.
- The duplicate check stays `_refuse_duplicate_slug`: an explicit slug is checked as given;
  a proposed one also against the earlier slug rule, as today. A second developer for one
  tech succeeds with `--slug`.
- The name-pool position counts the role items that carry `extra.tech` (ST8).

**Tests**

- Table: `--tech` shape (`python`; `Node.js`; an accented name; surrounding whitespace) by
  `--slug` (absent; a fresh slug; the slug of an existing developer; the slug of an existing
  bundled role; `operator`; `squads`; `op-x`; an uppercase or spaced value) by squad state
  (no developer for that tech; one already). Columns: exit code, message, the stored
  `extra`, the pointer file name, the full name drawn from the pool.
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

**Falsify.** Skip the reserved-slug check: the three reserved rows go red. Then derive the
override file name from the tech instead of the slug: the `--slug` row with a per-slug file
goes red. Restore each.

**Acceptance**

- Story 5, all bullets.
- Adopter-visible, for the handoff: the flag, its refusals, and that a second developer for
  one tech is possible.

Gates and working rules: the task body.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
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
<!-- sq:discussion:end -->
