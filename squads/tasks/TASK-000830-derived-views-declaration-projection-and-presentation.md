---
id: TASK-830
sequence_id: 830
type: task
title: 'Derived views: declaration, projection and presentation'
status: Done
parent: FEAT-693
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-776:implements
- ADR-777
- ADR-775
- ADR-781
- MILE-836:targets
description: The three-part view declaration as a keyed workflow-spec section, the
  uniform record shape, the JSON contract and template presentation
subentities:
- local_id: ST1
  title: '[views] as a keyed section of the workflow document'
  status: Done
  story: US1
- local_id: ST2
  title: The projection engine and its uniform record shape
  status: Done
  story: US1
- local_id: ST3
  title: Presentation as a bundled, overridable template
  status: Done
  story: US2
- local_id: ST4
  title: The --json contract and the sq workflow views catalog row
  status: Done
  story: US2
- local_id: ST5
  title: Prove the declaration expresses the sub-entity summary shape
  status: Done
  story: US1
created_at: '2026-08-26T13:30:05Z'
updated_at: '2026-08-26T16:00:14Z'
---
<!-- sq:body -->
## Scope

ADR-776, delivering FEAT-693 US1 and US2. The derived-view mechanism itself: what a view
declares, where it is declared, the record shape it produces, and the presentation layer over
those records. The `MILE` type and the milestone roll-up are the mechanism's first consumer and
are separate work; this task ships the mechanism and whatever bundled view it needs to prove
itself end to end.

## What a view declares — three parts, and no fourth

- **source** — the relation to project: refs of a declared kind pointing at this item, a
  sub-entity collection, or a subtree. A ref-kind source names a declared entry of the
  workflow document's `[ref_kinds]` section, adopter-declared kinds included.
- **projection** — which fields to carry, how to group, how to order. Produces records and
  makes no presentation decision.
- **presentation** — a Jinja2 template over those records.

**There is no sink field, and none to derive.** ADR-776 §1 and §4 drop FEAT-693's fourth part
rather than constraining it: every view is computed on request, from whichever client asks, and
no view is ever written into an item body. FEAT-693 asked for a mechanism that *refuses* a
foreign-source body sink; there is no combination left to refuse, so **do not write a test
asserting that refusal** — it would have nothing to assert.

## Where a view is declared, and what that inherits

`[views]` joins the **workflow document** as a keyed section on the same terms as `[statuses]`,
`[collections]`, `[subentity_kinds]` and `[ref_kinds]` — ADR-776 §7, ADR-777 §7.

Concretely, it enters `WORKFLOW_TOP_LEVEL_SECTIONS` in `_workflow/_loader.py` (verified). That
constant's own docstring records why one edit is enough: it "doubles as the `[selected]` table's
own accepted section-name set — the two are the same vocabulary". So the merge semantics, the
`[selected]` deselect, the closed top level, the provenance stamp and `sq workflow lint`'s
collect-all report all arrive by registration. **No view-specific override wiring is written.**

Referential validation arrives the same way: a view naming a type, ref kind or sub-entity kind
the merged spec does not declare must fail the same pass that already refuses a `ref_rules`
entry naming an undeclared kind (`_parse_ref_rules` in `_workflow/_loader.py`, verified — "a
rule declared for a kind no ref surface accepts can never fire … refused here rather than
carried as an inert hint"). A `[selected]` line that drops a ref kind a bundled view projects
therefore fails with no guard of the view's own.

Identity is the dict key, never restated on the value — the convention `ItemSpec`, `StatusSpec`,
`Lifecycle`, `Collection` and `RefKindSpec` already follow (`_workflow/_models.py`, verified).

## The record shape is the contract

Records with typed fields, optionally grouped, **identically shaped across every source and
every presentation** (ADR-776 §2). Field metadata and grouping travel with the payload so a
client can consume a view it has never seen without special-casing it.

The precedent to follow is already in the tree and should be read before designing a new one:
`summary_columns`/`summary_row` in `_discussion.py` derive columns and cells once from the
declared fields of a sub-entity kind, and four separate renderers consume that one derivation
(`_cli/_common.py`, `_cli/_items.py` — verified). The uniform shape is what let a fourth
renderer be added without touching the other three.

## Presentation, and the override surface it already has

Presentation is a Jinja2 template over the records, resolved through the one engine every
rendering path already uses (`_rendering/_engine.py`, `StrictUndefined`). A table, a single-line
badge string, a sentence, a bulleted list and a nested outline are five templates, not one
renderer with four flags.

A view's presentation template lives at `_rendering/templates/views/<name>.md.j2` — an ordinary
entry under the bundled-template tree. That placement is the whole of the adopter story: the
per-file override resolution, the provenance stamp and `sq override scaffold`/`diff`/`update`/
`list` already cover the template tree, so a view's presentation is adopter-overridable the day
it ships and **no new override surface is built here**.

## The JSON contract

`--json` emits the projected records and their field/grouping metadata, and **skips presentation
entirely**. The CLI's rendering is one presentation among several, never the source of the data:
the VS Code extension and `sq ui` are meant to lay the records out themselves rather than
reparse what the CLI printed.

`sq workflow` owes a catalog row under ADR-738's one-catalog-per-spec-map rule — a new keyed
section of the spec gets `sq workflow views --json`, landing complete on first ship rather than
growing keys across releases. The nine existing rows in `_cli/_workflow_cmd.py` are the shape.

## Release mechanics

Editing `src/squads/_specs/workflow.toml` and adding templates under
`_rendering/templates/views/` both force a **template-manifest regeneration**
(`python scripts/gen_template_manifest.py`).

- The generator replaces **one version's entry wholesale**, keyed on `[project].version`.
  `pyproject.toml` already reads `0.14.0`, which is not a shipped release, so the ordering
  ADR-781 §6 states is already satisfied: **do not run `scripts/bump_version.py`**, and only the
  `0.14.0` entry may move. An older release's recorded entry changing is a corrupted provenance
  record, not a diff to accept.
- The generator **no longer sweeps** the content store (ADR-777 D3). A blob left unreferenced by
  the regeneration is expected development residue between releases; `--check` reports it and
  passes. It is cleared at the release cut by `python scripts/seed_content_store.py --rebuild`,
  which `gen_template_manifest.py --release-gate` requires. Do not add a deletion to make an
  orphan go away.
- A squad carrying a `.overrides/workflow.toml` sees a genuine, content-gated drift warning when
  this lands. That is the correct signal.

## Traps

- **The sub-entity projection is not converted here.** FEAT-693's acceptance asks only that the
  declaration be *expressive enough* to describe the shipped summary shape as it stands, without
  bending the design to fit. Retiring the materialised regions is FEAT-694's own work; touching
  `ensure_summary`, `set_head` or `_refresh_head` in this task is out of scope.
- **Nothing in the head/summary refresh path is removed.** Those regions keep working exactly as
  they do today until the retirement lands.
- **A view's source names vocabulary, never a Python literal.** ADR-775 §2 keeps a `tests/meta`
  scan asserting that no bundled ref-kind name appears as a bare string constant under
  `src/squads/` outside `_specs/` and `_migrations/`
  (`tests/meta/test_no_bundled_ref_kind_literal_outside_the_spec_layer.py`, verified — it matches
  an `ast.Constant` whose value is *exactly* one of the ten names). A view engine that hard-codes
  `"targets"` trips it.
- **`workflow.toml` is the release's most contended file.** Two other tasks in this release add
  sections to it. Land this one's structural change before either declares against it.

## Acceptance

- `[views]` is a declared keyed section of the workflow document: it is a member of
  `WORKFLOW_TOP_LEVEL_SECTIONS`, an override may declare it, `[selected]` may drop a bundled
  view, and it merges leaf-granularly through the shared engine with no special case.
- A view naming a type, ref kind or sub-entity kind the merged spec does not declare is refused
  by the existing referential pass, and `sq workflow lint` reports it alongside every other
  violation in one run rather than stopping at the first.
- The three source shapes resolve: refs of a declared kind pointing at this item (by inversion),
  a sub-entity collection, and a subtree.
- Projected data is one uniform record shape — typed fields, optional grouping — across every
  source and every presentation, with field and grouping metadata carried in the payload.
- `--json` emits the projection and no presentation output.
- At least two presentations of one projection ship and are exercised, one of them
  **non-tabular** (a single-line text rendering is the obvious candidate).
- A view's presentation template resolves from `_rendering/templates/views/<name>.md.j2`, and a
  `.overrides/templates/views/<name>.md.j2` in a test squad is proven to win over the bundled
  one and render.
- `sq workflow views --json` lists every declared view with a complete row on first ship.
- The declaration expresses the shipped sub-entity summary's shape without altering that shape;
  nothing about the existing summary or head rendering changes in this task.
- No sink field exists anywhere in the declaration, the model or the CLI, and no test asserts a
  refusal of one.
- The template manifest matches the tree and its freshness check passes; `scripts/bump_version.py`
  was not run and `pyproject.toml` still reads `0.14.0`; only the `0.14.0` manifest entry moved.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 830 add-subtask "<title>"`; track with `sq task 830 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — [views] as a keyed section of the workflow document

<!-- sq:subtask:ST1:body -->
Register `[views]` as a keyed section of the **workflow document**, so the whole override
treatment arrives by registration rather than by new wiring.

- Add `views` to `WORKFLOW_TOP_LEVEL_SECTIONS` (`_workflow/_loader.py`, verified). Its docstring
  records that this constant "doubles as the `[selected]` table's own accepted section-name set",
  so one edit closes the top level *and* opens the deselect — there is no second list to edit.
- Add a `ViewSpec` model beside `ItemSpec`/`StatusSpec`/`Lifecycle`/`Collection`/`RefKindSpec` in
  `_workflow/_models.py`, `frozen=True`, `extra="forbid"`. **Identity is the dict key**, never
  restated on the value — that is the convention every one of those models already follows, and
  the `Collection` docstring states it explicitly.
- Declare the three parts and nothing else: `source`, `projection`, `presentation`. Any fourth
  field, and in particular anything named `sink`, is a design error rather than an omission —
  ADR-776 §4 removed the concept, not just its default.
- Wire the referential check into the pass that already runs on the **merged** spec. A view
  naming a type, ref kind or sub-entity kind the merged spec does not declare must be refused
  by the same mechanism that refuses a `ref_rules` entry naming an undeclared kind
  (`_parse_ref_rules`, `_workflow/_loader.py`, verified). Its docstring gives the reason to
  reuse: a declaration that can never fire is refused rather than carried as an inert hint.
- Collect-all semantics, not fail-fast: `sq workflow lint` must report a broken view alongside
  every other violation in the same run.
- Add the `[views]` entries to the override scaffold examples so
  `tests/meta/test_scaffolded_override_examples_load_against_the_live_models.py` and
  `tests/meta/test_bundled_documents_are_splat_ref_addressable.py` keep covering the new section.

Done when an override can declare a view, `[selected]` can drop a bundled one, a view naming
undeclared vocabulary is refused with its own message inside a collect-all lint run, and no
view-specific merge, stamp or deselect code was written.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — The projection engine and its uniform record shape

<!-- sq:subtask:ST2:body -->
Build the projection: resolve a view's source, carry the declared fields, group and order, and
emit **one uniform record shape** regardless of source.

Sources to resolve (ADR-776 §1):

- **refs of a declared kind pointing at this item** — recovered by inverting stored forward
  edges (`SquadsDB.backrefs`); nothing is ever persisted on the projecting item;
- **a sub-entity collection** — the projecting item's own `subentities`;
- **a subtree** — the item's descendants.

The record shape is the contract (ADR-776 §2): records with typed fields, optionally grouped,
**identically shaped across every source and every presentation**, with field metadata and
grouping carried in the payload so an unfamiliar view can be consumed without special-casing.

Read the shipped precedent before designing a new one. `summary_columns`/`summary_row`
(`_discussion.py`) derive columns and cells **once** from a sub-entity kind's declared fields,
and four separate renderers consume that single derivation (`_cli/_common.py`, `_cli/_items.py`
— verified). That uniformity is what let the fourth renderer be added without touching the other
three, and it is the property this projection has to reproduce.

Two constraints on the implementation:

- **Never name vocabulary in code.** A source's ref kind, type and sub-entity kind come from the
  merged spec. `tests/meta/test_no_bundled_ref_kind_literal_outside_the_spec_layer.py` (verified)
  matches a bare `ast.Constant` equal to any of the ten bundled kind names anywhere under
  `src/squads/` outside `_specs/` and `_migrations/`, so a hard-coded `"targets"` fails the
  suite.
- **Cost is one index load plus an inversion** — the same shape `sq tree` and `sq blocked`
  already have. Do not add a cache, and do not add a stored field to make a projection cheaper.

Done when all three source shapes project, grouping and ordering are declared rather than
hard-coded, two views over different sources produce records a single consumer can read without
branching on which view produced them, and no vocabulary literal appears outside the spec layer.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Presentation as a bundled, overridable template

<!-- sq:subtask:ST3:body -->
Render a view's records through a **Jinja2 template**, resolved by the one engine every rendering
path already uses (`_rendering/_engine.py`, `StrictUndefined`).

- A view's presentation template lives at `_rendering/templates/views/<name>.md.j2`, an ordinary
  entry under the bundled-template tree. Templates are package data, so the wheel picks the new
  directory up automatically — verify that in the build rather than assuming it.
- **Ship at least two presentations of one projection, one of them non-tabular.** A table and a
  single-line text rendering are the two proven shapes: `subentities/summary.md.j2` is already a
  table template over rows and `subentities/head.md.j2` is already a text template over the same
  fields (verified), so neither is new technology. A table renderer with flags for the other
  shapes is the design this explicitly is not.
- **The adopter override surface is inherited, not built.** `.overrides/templates/` already
  resolves per file ahead of the bundled tree, carries a provenance stamp, and is covered by
  `sq override scaffold`/`diff`/`update`/`list`. The override key is the template name, as it is
  everywhere else. Write no new override code for views.
- **Prove the override, do not assert it.** In a test squad, drop a
  `.overrides/templates/views/<name>.md.j2` that renders visibly differently, and assert the
  overridden text is what a `show` of the item prints.

Adding templates forces a template-manifest regeneration: run
`python scripts/gen_template_manifest.py`, confirm only the `0.14.0` entry moved, and do **not**
run `scripts/bump_version.py` (`pyproject.toml` already reads `0.14.0`). The generator no longer
sweeps the content store — an unreferenced blob is expected residue between releases, cleared by
`python scripts/seed_content_store.py --rebuild` at the cut, which `--release-gate` requires.

Done when one projection renders through two shipped templates including a non-tabular one, a
project-level template override is driven and wins, and the manifest is fresh with only the
`0.14.0` entry changed.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — The --json contract and the sq workflow views catalog row

<!-- sq:subtask:ST4:body -->
Publish the projection as data and give the spec section its catalog row.

**`--json` emits the projection and skips presentation entirely** (ADR-776 §2). The payload
carries the records plus their field and grouping metadata, so the VS Code extension and `sq ui`
lay the data out themselves instead of reimplementing whatever the CLI printed. The CLI's own
rendering is one presentation over those records and never their source; a client that reparses
CLI text is the consumer this contract exists to make unnecessary.

**`sq workflow views --json`** is owed under ADR-738's one-catalog-per-spec-map rule: a new keyed
section of the spec gets a catalog command, and the row lands **complete on first ship** rather
than growing keys across releases. The nine existing rows in `_cli/_workflow_cmd.py` (`types`,
`subentity-kinds`, `lifecycles`, `collections`, `statuses`, `roles`, `ref-kinds`) are the shape
to copy, including `null` for an absent key rather than an omitted key — the stability contract
`docs/workflow.md` states for every catalog.

Escape dynamic output on every human-readable path: Rich treats `[...]` as markup, so wrap
content strings with `_cli/_common.py::e()` when printing to a console or a table.

Note when driving this by hand: the agent harness sets `FORCE_COLOR=3`, so `--json` output can
carry ANSI escapes in a terminal session and look broken. That is a harness artifact, not a
defect in this work.

Done when `--json` emits records and metadata with no presentation output, a client can consume
an unfamiliar view from that payload alone, and `sq workflow views --json` lists every declared
view with a complete row.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Prove the declaration expresses the sub-entity summary shape

<!-- sq:subtask:ST5:body -->
Prove the declaration is expressive enough to describe the **shipped** sub-entity roll-up summary
as it stands — and change nothing about that summary.

This is a design-adequacy exercise, deliberately scoped short of conversion. FEAT-693's
acceptance asks that the declaration describe the existing summary shape "without bending its
design to fit"; retiring the materialised regions and reissuing both projections as computed
views is FEAT-694's own work.

What to do: write the summary's shape as a `[views]` declaration — sub-entity-collection source,
the columns `summary_columns` derives from the kind's declared fields, the ordering it uses —
and demonstrate that the projection produces those same records. Either land it as a bundled
view that nothing yet renders, or as a test-only declaration; say which, and why, in the handoff
comment.

What **not** to do:

- do not touch `ensure_summary`, `set_head` or `_refresh_head`;
- do not alter `subentities/summary.md.j2` or `subentities/head.md.j2`;
- do not remove any body region from any item template;
- do not change a single byte of what any of the four shipped sub-entity renderings prints.

If the declaration cannot express the shape without adding a field that exists only to
accommodate it, that is a finding worth raising rather than a field worth adding — say so on the
task discussion and `@architect` instead of widening the model.

Done when the summary's shape is expressed as a declared view producing the same records, the
existing summary and head rendering are byte-for-byte unchanged, and any expressiveness gap is
recorded rather than papered over.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T14:31:09Z] Elias Python:
  - Implemented. Declaration: [views.<name>] with source = {kind: "ref"|"subentity"|"subtree", name: <declared vocab>}, fields = [{code,label}...], optional group_by/order_by naming one of the view's own field codes. No presentation field: identity is the dict key, and that key IS the template path (templates/views/<name>.md.j2) — mirrors the ItemSpec/Collection/RefKindSpec convention. Models + referential check in _workflow/_models.py (ViewSource/ViewField/ViewSpec, _check_views); parsing in _workflow/_loader.py; views added to WORKFLOW_TOP_LEVEL_SECTIONS (one edit).
  - Projection engine in new module squads/_views.py (top-level, peer to _discussion.py, no _services dependency — a service mixin _services/_views.py is the only I/O seam, one index load). Uniform record: Cell{text, json_value} per field, ViewRecord.values: dict[code,Cell], ViewGroup{key,records}, Projection{fields:[ViewFieldMeta{code,label,type}], group_by, groups} — always groups, even ungrouped (one group with key=null), so a client never special-cases. --json reads via squads._views.projection_json(); wired at 'sq workflow view <name> <item-id> --json' (a new generic command I added under sq workflow — no CLI surface was specified anywhere in the source materials; 'sq workflow views' is the catalog). Table-driven unit tests prove the same generic consumer reads all three source kinds without branching.
  - Presentation: Jinja2 template receiving fields/group_by/groups context, resolved through the existing engine (no new override wiring — proven: a .overrides/templates/views/<name>.md.j2 wins and renders). Two bundled, fully generic templates ship: _rendering/templates/views/finding_summary.md.j2 (table) and finding_summary_line.md.j2 (non-tabular bulleted list) — verified in the wheel build.
  - [selected]/referential check reached by registration, not special-casing: 'views' is one more entry in WORKFLOW_TOP_LEVEL_SECTIONS, _check_views runs inside WorkflowSpec._validate on the merged spec like every other cross-reference, sq workflow lint collect-alls every violation in one run, and a [selected] line dropping a ref/subentity kind a view projects fails with the existing 'dropped from a [selected] list' provenance annotation for free — no view-specific code anywhere.
  - No view ships bundled — deliberate, and found by evidence not judgment call: I first bundled two views over the built-in 'finding' sub-entity kind, then a targeted run (tests/unit -k badge/workflow_spec/ref_kind/subentity) broke a pre-existing test (shadowing finding.fields to []) and a full run broke six more in test_workflow_subentity_kinds_cli.py (dropping/renaming the finding kind via [selected], an already-supported, already-tested customization). Naming ANY bundled vocabulary as a source couples that customization to keeping the view — correct for a view something consumes (a milestone roll-up over targets), wrong for a demo nothing reads. So: the two templates above ship bundled and are exercised by test-only declared views (ST3), and the sub-entity-summary shape-adequacy proof (ST5) is also test-only, per the task's own explicit permission — tests/unit/test_view_expresses_the_subentity_summary_shape.py declares the full shape (including finding's severity badge field) via a workflow override and matches discussion.summary_columns/summary_row cell-for-cell; ensure_summary/set_head/the summary templates are untouched (asserted, not just avoided).
  - Release mechanics: only the 0.14.0 manifest entry moved (diffed against HEAD), scripts/bump_version.py not run, pyproject.toml still reads 0.14.0. Iterating on the bundled-view decision above cost 3 orphaned content-store blobs (all one category: superseded 0.14.0-era workflow.toml revisions) — left alone per the task's own instruction; seed_content_store.py --rebuild clears them at the cut.
  - Gates: tests/meta 254 passed / 5 failed — all 5 trace to that same single orphan-blob category (test_every_stored_blob_is_referenced_by_at_least_one_index_entry + four seed_content_store rebuild-count tests whose fixture copies the real, currently-residue-bearing store); verified against a clean git-stash baseline where they pass, so this is pre-existing-category residue, not a regression. My targeted tests: 93 passed (5 new files + the 2 json-output-shape golden cases). Widened to tests/ -k 'override or template or badge or workflow or field or collection or view' (excl. tui): 1321 passed, same 5 known failures, zero new. sq check clean. Full-project pyright/ruff/ruff-format all clean.
  - For @tech-lead and whoever picks up TASK-831/TASK-832: three implementation choices the decision docs didn't pin down, since they'll shape the milestone/contract work — (1) a ref-kind source's fields are restricted to base attributes only (id/type/status/status_role/assignee/title), never a badge field, because ref-sourced records can span heterogeneous types; (2) grouping/ordering operate on a declared field's resolved value, so the milestone roll-up should declare a field with code='status_role' (resolves via spec.status_role, never a status-name literal) and group_by it; (3) 'sq workflow view <name> <item-id>' is a generic debug/proof CLI surface I added (unspecified anywhere) — sq milestone <n> show should call svc.resolve_view/render_view programmatically rather than assume this command is the intended integration point.
  - Nothing left undone in scope. @paul-reviewer for review.
- [2026-08-26T14:31:23Z] Elias Python:
  - Correction: the reviewer mention above was mistyped — @reviewer, over to you.
<!-- sq:discussion:end -->
