---
id: TASK-831
sequence_id: 831
type: task
title: The MILE item type and its computed roll-up view
status: Done
parent: FEAT-693
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-776:implements
- ADR-775
- ADR-781
- TASK-830:depends-on
- MILE-836:targets
description: The milestone type, its lifecycle, target date and generated surface,
  with membership by targets refs and the roll-up as the first declared view
subentities:
- local_id: ST1
  title: Declare [items.milestone] and its lifecycle
  status: Done
  story: US3
- local_id: ST2
  title: The target date field and its generic --set path
  status: Done
  story: US3
- local_id: ST3
  title: Membership by targets refs, written only on the work item
  status: Done
  story: US3
- local_id: ST4
  title: Playbook entries and the generated sq-milestone surface
  status: Done
  story: US3
- local_id: ST5
  title: The milestone roll-up as the first declared view
  status: Done
  story: US4
created_at: '2026-08-26T13:32:03Z'
updated_at: '2026-08-26T16:02:03Z'
---
<!-- sq:body -->
## Scope

FEAT-693 US3 and US4: the `MILE` item type — its declaration, lifecycle, target date, folder,
item template and generated agent-facing surface — plus the milestone roll-up as the **first
declared consumer** of the view mechanism.

The mechanism itself is separate work and is an input here: this task declares a view, it does
not build the machinery that resolves one.

## The type

One `[items.milestone]` block plus one `[lifecycles.milestone]` block in
`src/squads/_specs/workflow.toml`, and nothing else. The type engine is config-driven — the CLI
group `sq milestone`, the folder and the ID prefix all follow from the declaration, with no
per-type module. `sq create` already lists exactly the declared types (driven), and `create()`
falls back to `items/_default.md.j2` for a type with no dedicated template.

- prefix `MILE`, folder `milestones`, aliases that are free today (check before choosing — the
  loader refuses a duplicate alias, prefix or folder, and `_check_validators_assignment`'s
  sibling duplicate checks in `_workflow/_loader.py` report each collision by name).
- `order` is a spaced float; pick one that puts a milestone where a reader expects it among the
  work types, and remember the values are deliberately spaced by 10 so nothing renumbers.
- Its own status vocabulary. Reuse existing status **names** where they read correctly rather
  than minting near-synonyms; every status a lifecycle names must be declared, both terminals
  must be reachable, and the lifecycle floor (ADR-696 §3) applies unchanged.
- Category: a milestone is not a build-lifecycle work item and hosts no sub-entities. Choose the
  category its declared behaviour actually needs — `CATEGORY_BUNDLES` in `_workflow/_models.py`
  (verified) is the authority on what each one turns on — and state the choice in the handoff.
  Declaring `subentity_kind` would be wrong: a milestone's members are other items, reached by
  ref, not sub-entities of its own file.

## The target date

A milestone carries a target date. There is no date field mechanism in the tree today, so this
adds one:

- a key on `_models/_extras.py::ExtraKey` (never a hand-written string — `Item.extra` keys live
  there by convention);
- registered in `_models/_metadata.py::_GENERIC_FIELDS`, which
  `tests/meta/test_dedicated_create_flags_stay_settable_via_generic_set.py` (verified) requires
  of any key a dedicated create flag writes. Its docstring records the exact bug this prevents:
  `guide --tech` wrote `extra["tech"]` with no `--set` path, so a squad that renamed the type
  lost the field entirely.
- Prefer the generic door. A dedicated `--target-date` create flag is bound to a literal type
  name, which is the coupling this project has been removing; the generic
  `sq milestone <n> update --set` path must work regardless.
- Validate and normalise the value on the way in, and report a rejected value rather than
  storing it. `sq check` must be able to tell an adopter their date is unparseable.

## Membership rides `targets`, and only the work item is written

The `targets` ref kind already ships, bundled and **navigational** — it declares no semantic
role and needs no engine binding (ADR-775 §4; verified in `src/squads/_specs/workflow.toml`).
This task wires it to milestone membership; it does not add the kind.

`sq <type> <n> ref add MILE-<n> --kind targets` writes **only the work item**. The milestone
file is untouched, membership is never persisted on the milestone, and it is recovered by
inverting the stored forward edges (`SquadsDB.backrefs`). Forward edges only — invariant 4.

## The roll-up view

One `[views]` declaration: source is the inversion of `targets` edges pointing at this milestone;
the projection groups members **delivered and outstanding with counts**, because what is left is
the question a milestone exists to answer; presentation is a template under
`_rendering/templates/views/`.

**Delivered versus outstanding is resolved from the spec, never from a status name.** A member's
group comes from its own status's declared **role** (`spec.status_role`), the way
`supersedes_incoming` resolves its own condition (`_services/_validators.py`, verified). A
milestone can hold members of several types on several lifecycles, so a literal `"Done"` would
silently mis-group a bug or a decision.

Nothing is written to the milestone file when membership changes, and no run ever materialises
the roll-up — it is rendered fresh from the current corpus on every request, `--json` included.

## The generated agent-facing surface

A new item type grows the managed surface, all of it regenerated by `sq sync` and stamped in
place as such: new `[types.milestone]` entries in `src/squads/_specs/playbook.toml` driving a
managed `sq-milestone` skill (real body under `squads/agents/skills/`, thin `.claude` pointer),
the `CLAUDE.md` and `AGENTS.md` managed regions, and a dedicated `items/milestone.md.j2`.

Under ADR-781 the pointer carries only what the host must read before anything can run — its
`name`, its `description`, and the command that renders the definition
(`sq skill sq-milestone show`). **No `@` path into the squad directory, and no copy of the skill
body.**

Verify the on-disk output for **both** `sq init` **and** `sq migrate up`. ADR-320 §E names why
this is a rule rather than a habit: a type addition that wired only the `init` path and left
`migrate` unregenerated has bitten this project before. Hold the roster constant across the two
squads when comparing — generated per-type skill text is roster-dependent, so a dev-less fresh
squad diffed against a dev-bearing one reports differences that are not regressions.

## Release mechanics

Editing `workflow.toml` and `playbook.toml` and adding templates forces a **manifest
regeneration** (`python scripts/gen_template_manifest.py`). Only the `0.14.0` entry may move;
**do not run `scripts/bump_version.py`** — `pyproject.toml` already reads `0.14.0`. The generator
no longer sweeps the content store (ADR-777 D3), so an unreferenced blob is expected residue
between releases; it is cleared at the cut by `python scripts/seed_content_store.py --rebuild`,
which `gen_template_manifest.py --release-gate` requires. Do not add a deletion to clear one.

## Traps

- **The migration is not authored here.** The folder creation, the schema bump and the surface
  regeneration on an existing squad belong to the release's single shared runner. Adding a second
  runner or a second bump is precisely what was ruled against.
- **No roll-up text is ever written into the milestone's body.** There is no sink to declare and
  none to choose.
- **`workflow.toml` is the release's most contended file** — the view mechanism and the contract
  type both edit it. Do not run concurrently with either.

## Acceptance

- A milestone can be created, carries a target date, and moves through its own declared status
  vocabulary; both terminals are reachable.
- The target date is settable at create and afterwards through the generic `--set` door, is
  registered in `_GENERIC_FIELDS`, and an unparseable value is refused with a message naming the
  field rather than stored.
- `sq <type> <n> ref add MILE-<n> --kind targets` leaves the milestone's `.md` file byte-identical
  — asserted, not eyeballed — and the milestone's members are recovered by inversion.
- Showing a milestone renders its members grouped delivered and outstanding with counts, computed
  fresh on every request; no region of the milestone file ever holds that text.
- `--json` emits the same projection as records, with no presentation output.
- Grouping resolves through declared status roles; no status-name literal appears in the view
  resolution path.
- The type carries its folder, its item template, its `[types.milestone]` playbook entries and a
  generated `sq-milestone` skill whose `.claude` pointer names `sq skill sq-milestone show` and
  carries no local file path.
- The generated surface is identical between a freshly `sq init`-ed squad and one reached through
  the release's migration, asserted by comparison with the roster held constant, and it passes
  `sq check`'s per-entry pointer presence and currency gate from day one.
- The template manifest matches the tree, its freshness check passes, only the `0.14.0` entry
  moved, and `scripts/bump_version.py` was not run.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 831 add-subtask "<title>"`; track with `sq task 831 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare [items.milestone] and its lifecycle

<!-- sq:subtask:ST1:body -->
Add one `[items.milestone]` block and one `[lifecycles.milestone]` block to
`src/squads/_specs/workflow.toml`, plus a dedicated `_rendering/templates/items/milestone.md.j2`.
Nothing else declares the type: the `sq milestone` CLI group, the ID prefix and the folder all
follow from the declaration, and no per-type CLI module is written.

- **prefix `MILE`, folder `milestones`.** Pick aliases from what is actually free — the loader
  reports a duplicate prefix, folder or alias by name, and every existing type's aliases are in
  the same document.
- **`order`** is an explicit float spaced by 10 so a type can be inserted between two others
  without renumbering (the file's own comment, verified). Place a milestone where a reader
  expects it among the work types.
- **Its own status vocabulary.** Reuse existing status *names* where they read correctly rather
  than minting near-synonyms; every status a lifecycle names must be declared. Both terminals
  must be reachable — the lifecycle floor, unchanged.
- **Category.** A milestone is not a build-lifecycle work item and it hosts no sub-entities.
  `CATEGORY_BUNDLES` in `_workflow/_models.py` (verified) is the authority on what each category
  turns on; choose against that table and state the choice, with its consequences for the
  validator set, in the handoff comment.
- **Do not declare `subentity_kind`.** A milestone's members are other items reached by ref, not
  sub-entities of its own file — declaring a kind would give it a roll-up region it must never
  have.
- The item template steers the author toward what the milestone is *for*: its objective and its
  scope boundary. It must carry no status or lifecycle prose — the frontmatter `status:` field is
  the single source of truth, and a body that declares its own position goes stale the moment
  the real status changes.

Done when `sq create milestone` produces a `MILE`-prefixed item in `milestones/`, the type's CLI
group exists with no per-type module, `sq workflow types --json` and `sq workflow lifecycles
--json` both carry complete rows for it, and `sq check` is clean on a squad holding one.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — The target date field and its generic --set path

<!-- sq:subtask:ST2:body -->
Give a milestone a target date, and give the field a path that survives a rename of the type.

There is no date-field mechanism in the tree today, so this adds one:

- a key on `_models/_extras.py::ExtraKey` — `Item.extra` keys live there by convention and are
  never hand-written string literals at the call site;
- **registered in `_models/_metadata.py::_GENERIC_FIELDS`.**
  `tests/meta/test_dedicated_create_flags_stay_settable_via_generic_set.py` (verified) requires
  this of any key a dedicated create flag writes, and its docstring records the exact bug:
  `guide --tech` wrote `extra["tech"]` with no `--set` path, so a squad that renamed or replaced
  the `guide` type lost the field entirely — not settable at create, not settable afterwards.
  `tags` sat beside it, correctly registered, and kept working.
- **Prefer the generic door.** A dedicated `--target-date` create flag is bound to a literal type
  name, which is the coupling this project has been removing. Whatever you ship, the generic
  `sq milestone <n> update --set <field>=<value>` path must work.
- **Validate on the way in.** Normalise the accepted spelling, and refuse an unparseable value
  with a message that names the field — do not store it and leave a reader to discover it. Read
  the value back after writing and assert the stored form.

Time is injectable in this codebase: use `clock.now()`/`clock.iso()` rather than calling
`datetime.now()` directly, so the `frozen_time` fixture can pin anything date-dependent.

Done when a target date is settable at create and afterwards through `--set`, is registered in
`_GENERIC_FIELDS`, round-trips through frontmatter and the index unchanged, an unparseable value
is refused with a field-naming message, and the meta test above passes.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Membership by targets refs, written only on the work item

<!-- sq:subtask:ST3:body -->
Wire the already-shipped `targets` ref kind to milestone membership.

`targets` is declared and bundled today, **navigational** — it carries no semantic role and needs
no engine binding (ADR-775 §4; verified in `src/squads/_specs/workflow.toml`, where it declares
only `label` and `hint`). This subtask does not add the kind; it gives it its first consumer.

The rule that makes this worth doing at all: **`sq <type> <n> ref add MILE-<n> --kind targets`
writes only the work item.** The edge lives on the work item, so adding work to a milestone never
rewrites the milestone file, and membership is recovered by inverting the stored forward edges
(`SquadsDB.backrefs`). Forward edges only — backrefs are computed by inversion and never
persisted (invariant 4).

Assert it rather than trusting it: capture the milestone's `.md` bytes before and after a
membership change and require them identical. A test that only checks the ref list would pass
against an implementation that rewrote the milestone file with the same rendered content.

The kind must never be spelled as a Python literal in the resolution path.
`tests/meta/test_no_bundled_ref_kind_literal_outside_the_spec_layer.py` (verified) matches a bare
`ast.Constant` equal to any of the ten bundled kind names under `src/squads/` outside `_specs/`
and `_migrations/`; the view's own source declaration names the kind, and the engine reads it
from there.

Done when membership is recorded on the work item alone, the milestone file is byte-identical
across a membership change (asserted), members are recovered by inversion, and no kind literal
appears outside the spec layer.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Playbook entries and the generated sq-milestone surface

<!-- sq:subtask:ST4:body -->
Grow the managed agent-facing surface for the new type, and verify it on the migrate path as well
as on init.

- New `[types.milestone]` entries in `src/squads/_specs/playbook.toml` — per-role enter / do /
  handoff / watch guidance, following the shape every existing `[types.<name>]` block uses. They
  drive the managed `sq-milestone` skill: the real body is the skill item's own body under
  `squads/agents/skills/`, with a thin pointer in `.claude/`.
- **The pointer names a command, never a path.** Under ADR-781 it carries only what the host must
  read before anything can run — its `name`, its `description`, and `sq skill sq-milestone show`.
  No `@` reference into the squad directory and no copy of the skill body: a local path resolves
  to nothing when the CLI is a client to a server.
- The `CLAUDE.md` and `AGENTS.md` managed regions pick the type up through the shared
  `_managed_region.py` wrapper, which already stamps the "regenerated by `sq sync`" warning, so
  the new surface inherits that stamp for free (invariant 7).
- Generated agent text renders from the **active** spec, the active playbook and the live roster,
  never from bundled literals, so a squad that renames or drops the type gets text matching its
  own vocabulary. `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py` guards
  this.

**Verify on both paths, by comparison.** ADR-320 §E states the rule and names why: a type
addition that wired only the `init` path and left `migrate` unregenerated has bitten this project
before. A squad reached through the release's migration and a squad created fresh with `sq init`
must end with the **same** on-disk generated surface for the milestone type — skill body files,
pointer filenames, pointer targets, pointer descriptions, and the managed regions. Assert the
comparison in the suite so the two paths cannot drift later; do not eyeball one of them.

**Hold the roster constant across the two squads.** Generated per-type skill text is
roster-dependent, so a dev-less fresh squad diffed against a dev-bearing one reports differences
that are not regressions.

Done when the playbook entries drive a generated `sq-milestone` skill and pointer, the pointer
names the command and carries no local path, both paths produce the same surface under an
asserted comparison, `sq sync` is a no-op on a freshly migrated squad, and `sq check`'s per-entry
pointer presence and currency gate passes.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — The milestone roll-up as the first declared view

<!-- sq:subtask:ST5:body -->
Declare the milestone roll-up: the mechanism's first consumer, and the proof it works
end to end.

One `[views]` declaration in `src/squads/_specs/workflow.toml`:

- **source** — the inversion of `targets` edges pointing at this milestone;
- **projection** — members grouped **delivered** and **outstanding**, with counts, because what
  is left is the question a milestone exists to answer;
- **presentation** — a template under `_rendering/templates/views/`.

**Grouping resolves from the spec, never from a status name.** A member's group comes from its
own status's declared **role** (`spec.status_role`), the way `_supersedes_incoming` resolves its
own condition in `_services/_validators.py` (verified — it compares
`ctx.spec.status_role(item.status)` against a role, never a status spelling). This matters here
more than anywhere: a milestone can hold members of several types on several lifecycles, so a
literal `"Done"` would silently mis-group a bug, a decision or an adopter's custom type.

**Nothing is written to the milestone file, ever.** No membership change touches it and no run
materialises the roll-up; it renders fresh from the current corpus on every request, `--json`
included. There is no sink to declare and none to choose.

Ship the roll-up's own non-tabular presentation too if the mechanism's shipped set does not
already provide one — a single-line "N of M delivered" text rendering over the same records is
the obvious candidate and costs a second template, not a second projection.

Prove the adopter path with this view: override
`.overrides/templates/views/<name>.md.j2` in a test squad and assert the overridden wording is
what `sq milestone <n> show` prints.

Done when a milestone's members render grouped with counts on every request, `--json` emits the
same records with no presentation output, the milestone file is never written by the roll-up, the
grouping survives members of more than one type, and a project-level template override of the
roll-up is driven and wins.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T15:58:59Z] Elias Python:
  - Declared: prefix MILE, folder milestones, aliases mile/m, order 57 (contract 55, review 60), category records (no parent, no sub-entities — matches decision/contract/guide), lifecycle Draft->InProgress->Done(+Cancelled) reusing existing status names, both terminals reachable.
  - Target date: X.TARGET_DATE=target_date on ExtraKey, registered in _GENERIC_FIELDS with a new date Kind (_models/_metadata.py::coerce/_coerce_date, stdlib date.fromisoformat, normalises to YYYY-MM-DD, refuses naming the field). Settable at create via svc.create(extra=...) (the same generic door guide's --tech/--tag already use, unvalidated there same as everywhere else at create) and afterwards via the generic sq milestone <n> update --set target_date=... (validated). No dedicated --target-date create flag added.
  - Membership: targets is the already-shipped navigational kind, wired only by declaration — sq <type> <n> ref add MILE-n --kind targets works unmodified. Milestone file asserted byte-identical before/after ref add + member status changes (service test + a manual scratch-squad md5 check).
  - View: one [views.milestone_rollup] (source=ref:targets, fields id/type/status/status_role/title/assignee, group_by=status_role, order_by=type,id) plus a new items.milestone.views=["milestone_rollup"] reverse-attachment field on ItemSpec — the only way a view reaches a reader, since ViewSpec never names its own consumer type. sq milestone <n> show/--json now render/emit attached views generically (_cli/_common.py, any type declaring .views gets this for free, zero milestone-specific CLI code). Grouping resolves via spec.status_role (the ref-source record's status_role field), never a literal status name; proven with a task Done + a bug Verified both landing in Delivered.
  - Deselect-cascade: dropping milestone from [selected].items removes items.milestone.views with it (same key), and the loader (_prune_orphaned_type_owned_views, _workflow/_loader.py) then drops milestone_rollup itself from the merged spec's [views] table when no surviving type's .views still names it — an unrelated deselect, or a second type keeping the attachment, leaves it alone. No [selected].views line needed. I did NOT add a spec-build-time referential check for ItemSpec.views (WorkflowSpec._validate) — that check fired on every hand-built WorkflowSpec.model_validate(...) across the suite (73 failures/14 errors) since many spread bundled.items without bundled.views; a dangling name is instead refused where it's used, by resolve_view's existing 'no declared view' error.
  - sq check clean. tests/meta 259/259 green. Targeted run (tests/unit+cli+service+integration+tui): 4030 passed, 2 skipped, 0 failed — includes ~19 pre-existing fixtures updated for milestone (helpers' BUILTIN_PREFIX/FOLDER/TYPES/WORK_TYPES, RESERVED_CLI_ALIASES + its meta golden, lane-derivation product table, create-lane CLI/JSON, retype help truncation, workflow types/lifecycles/views goldens+CLI counts, cheatsheet+CLAUDE.md/AGENTS.md managed-section goldens, skills-for-role mapping, item-skill pointer frontmatter, playbook golden+count 8->9) plus new coverage (tests/service/test_milestone_type.py, tests/cli/test_milestone_cli.py, tests/unit/test_milestone_view_deselect_cascade.py). Playbook edit did drift 2 pointers (product-owner, tech-lead); sq sync cleared it. Manifest regenerated: only the 0.14.0 entry moved (verified programmatically); ran seed_content_store.py --rebuild to clear my own dev-time orphan residue before gating, confirmed by --release-gate passing orphan-free. pyright/ruff check/ruff format all clean.
  - Undone / handed off: the init-vs-migrate on-disk parity comparison (this task's own acceptance line) can't be exercised yet — the shared migration runner (TASK-813, still Ready) doesn't exist, so there is no migrate path to diff against init; that comparison is TASK-813's own stated ST3 obligation, not mine to fake here.
  - @olivia-lead for review; @op-pierre FYI — this is the first bundled view, so the attach/cascade pattern (ItemSpec.views + loader prune, no spec-time referential check) is now precedent for the next type that wants one.
- [2026-08-26T15:59:08Z] Elias Python:
  - Correcting the mention above (wrong slug format): @tech-lead for review.
<!-- sq:discussion:end -->
