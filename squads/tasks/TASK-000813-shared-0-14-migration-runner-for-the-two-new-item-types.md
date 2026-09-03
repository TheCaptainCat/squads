---
id: TASK-813
sequence_id: 813
type: task
title: Shared 0.14 migration runner for the two new item types
status: InProgress
parent: FEAT-693
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-320:implements
- TASK-812:depends-on
- FEAT-321:depends-on
- ADR-775
- REV-808
- TASK-831:depends-on
- TASK-832:depends-on
- MILE-836:targets
- TASK-849:depends-on
description: The single schema bump, registry entry and runner carrying both the contract
  and milestone types into 0.14, plus the folder creation, surface regeneration and
  manual runbook entry
subentities:
- local_id: ST1
  title: Schema bump and the shared registry entry
  status: Done
- local_id: ST2
  title: Create both new types' folders on an existing squad
  status: Done
- local_id: ST3
  title: Regenerate and verify the agent-facing surface
  status: Done
- local_id: ST4
  title: Manual runbook entry for both new types
  status: Done
- local_id: ST5
  title: Frozen corpus fixture tests/fixtures/corpus/v0_14
  status: Done
created_at: '2026-08-25T18:12:45Z'
updated_at: '2026-09-01T08:10:00Z'
---
<!-- sq:body -->
## Scope

ADR-320 §F. The single schema migration that carries **both** new item types into the 0.14
release: `contract` (`PRD`, FEAT-321) and the milestone type (`MILE`, this feature).

## One runner, shared — and what that obliges every breakdown to do

The operator ruled one bump and one migration for both types, so the two features land in the
same release (recorded on ADR-320, 2026-08-24: "Schema: 0.14 carries ONE bump for both new item
types (PRD and MILE) in a single migration, so FEAT-321 and FEAT-693 land in the same release").
ADR-320 §F states the same and adds the general form: **any other schema-level change shipping in
0.14 joins this runner rather than adding a second bump.**

**This item is the release's one runner. A breakdown of either feature extends it; it does not
author a second one.** That obligation is the reason this is tracked here rather than inside
either type's own delivery — a runner authored twice is two bumps, and two bumps is precisely
what was ruled against. Concretely: the milestone half and the contract half each add their own
folder and their own generated surface to *this* runner's deterministic step and to *this*
runner's manual entry. It is parented here because this feature owns the milestone type; the
contract half is no less its business for that.

Both features are now broken down, and neither breakdown authors a runner: the milestone type's
delivery and the contract type's delivery each declare their type and stop at the spec, leaving
the folder creation, the surface regeneration on an existing squad and the bump here. Both are
recorded as `depends-on` — the two type declarations are inputs this runner does not author, and
it cannot create a folder for a type the spec does not declare.

It also means this item cannot be closed by delivering one half. It closes when both types'
folders, both types' generated surfaces and one manual entry covering both are in place behind a
single registry step.

**A third claimant may join before the cut.** FEAT-694 retires the materialised sub-entity
summary and head regions, which is on-disk format and owes a corpus-wide edit of its own; the
operator has kept that work in this release. If it lands here, it joins this runner under §F's
general form rather than adding a second bump — and this item's acceptance grows with it rather
than a second registry entry appearing. Nothing about that work is authored here.

## Why this is not merely release plumbing

ADR-775 amendment A4 discharges REV-808's F3 — a pre-0.14 squad holding a spelled default ref
kind on disk and in its index — **on this runner existing**. The mechanism:
`run_pending_migrations` (`_services/_maintenance.py`, verified) applies each pending runner, then
calls `repair()` **before** stamping the new schema, and the root CLI callback refuses every
command on a squad whose schema is behind. So a pre-0.14 squad cannot reach a mutating command
without first running `sq migrate up`, and that run re-derives its index from the folded disk.

The migration *is* the corrective sweep, which is why A4 rules out any ref-canonicalisation step
of its own, any `manual` clause about it and any release note. **Nothing about refs is added to
this runner.** What matters is that a runner exists in this release at all: without one,
`run_pending_migrations` has nothing to apply, `repair()` never runs, and an accepted ruling has
no mechanism underneath it.

## The bump: `0.11 → 0.14`, and the three places that encode it

**Settled.** ADR-320 §F is amended in place and its amendment note A1/A2 carries the argument:
the bump is `0.11 → 0.14` on `_models/_schema.py::SCHEMA_VERSION` (currently `"0.11"`, verified).
Confirmed from the tags rather than from the convention text — v0.12.0 and v0.13.1 both ship
`SCHEMA_VERSION = "0.11"`, so a schema numbered `0.12` would name a release that shipped and
introduced nothing, the one reading the alpha convention forbids.

Gaps are the convention, not a concession: the registry runs 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 0.8,
0.10, 0.11 — no 0.6 and no 0.9, because those releases introduced no schema change. Skipping 0.12
and 0.13 applies the same rule. And the convention binds **forward**: a new schema number takes
the release that introduces it, and a release may introduce more than one. Schema `0.4` is the
one recorded exception — v0.4.0 ships `SCHEMA_VERSION = "0.3"`, and both the 0.3→0.4 and 0.4→0.5
runners shipped inside release 0.5.0 — so do not read a release number backwards out of an
intermediate label.

**Three places encode the number and must move together:**

1. the runner module `_migrations/_v0_11_to_v0_14.py`;
2. its registry entry — `version="0.14.0"`, `from_schema="0.11"`, `to_schema="0.14"`;
3. the corpus fixture `tests/fixtures/corpus/v0_14`, which
   `tests/integration/test_migration_corpus.py`'s standing rule requires of every schema bump.
   The fixture name follows the **schema number**, not the release count — `tests/fixtures/corpus/`
   holds `v0_1`, `v0_2`, `v0_3`, `v0_4`, `v0_5`, `v0_7`, `v0_8`, `v0_10`, `v0_11` today (verified),
   the same series with the same gaps.

Nothing else moves: ordering goes through `schema_tuple`, so `(0, 14)` sorts after `(0, 11)`
exactly as `(0, 12)` would; the existing registry guard already ties the highest registered
`to_schema` to `SCHEMA_VERSION`; and no test, doc or runbook pins the retired number.

## The deterministic step

No existing item data is rewritten, so the run itself is light:

- **Create each new type's folder**, matching what `init` does per declared type (`init` and
  `adopt` both loop `for ts in effective_spec.items.values()` and `mkdir` each folder —
  `_services/_service.py`, verified). Those loops run at creation time only, so an existing squad
  gets no folder for a type added later — the runner owes it. Idempotent: a squad that already
  has the folder is unaffected.
- **Regenerate the managed agent-facing surface** so the new per-type skills, their `.claude`
  pointers and the `CLAUDE.md` / `AGENTS.md` regions appear (ADR-320 §E).

`_v0_10_to_v0_11.py` is the model for the shape of a light runner — including saying in its own
docstring what it does *not* do and why — but this one is not a no-op: it writes folders and
regenerates.

## Verify the generated artifacts on migrate, not only on init

ADR-320 §E makes this an explicit rule, and names why: "a type addition that wired only the
`init` path and left `migrate` unregenerated has bitten this project before".

So the check is by comparison and by test: a squad migrated with `sq migrate up` and a squad
created fresh with `sq init` must end with the **same** on-disk generated surface for both new
types — skill bodies, pointer filenames, pointer targets and descriptions, and the managed
regions. Compare them, do not eyeball one. Hold the roster constant across the two squads:
generated per-type skill text is roster-dependent, so a dev-less fresh squad diffed against a
dev-bearing one reports differences that are not regressions.

## The manual runbook entry

One entry covering both types: the runbook tells an adopting squad that the two types now exist
and, optionally, to seed initial items for their current capabilities. A migration cannot author
functional truth on their behalf.

It carries nothing about ref encoding — A4 rules that out, because it would instruct an adopter to
run the repair `sq migrate up` had just run for them.

## Release mechanics, inherited rather than restated

- Editing `workflow.toml` and `playbook.toml` and adding item templates forces a
  template-manifest regeneration, and the version bump comes first. **That ordering is already
  satisfied — `pyproject.toml` reads 0.14.0, which is not a shipped release. Do not run
  `scripts/bump_version.py`.**
- The regeneration replaces the `0.14.0` index entry wholesale, so whichever task regenerates
  last must do so with every other 0.14.0 change already in the tree. Only that entry may move.
- The generator no longer sweeps the content store (ADR-777 D3). A blob left unreferenced by a
  regeneration is expected residue between releases — `--check` reports it and passes — and is
  cleared at the cut by `python scripts/seed_content_store.py --rebuild`, which
  `gen_template_manifest.py --release-gate` requires. Do not add a deletion to clear one.
- A squad carrying a `.overrides/workflow.toml` sees a genuine, content-gated drift warning when
  this lands. That is the correct signal.

## Traps

- **The two type declarations are inputs this does not author.** ADR-320 §A settles the contract
  type as one `[items.contract]` block plus one `[lifecycles.contract]` block in
  `src/squads/_specs/workflow.toml`; the milestone type's equivalent is settled in its own
  delivery. The runner cannot create a folder for a type the spec does not declare, so both
  declarations land before it.
- **The migration import rule constrains this runner from the day it is written.** A runner reads
  the vocabulary of the schema version it transforms and may not reach into `_models` for a
  primitive whose behaviour the live tree can change; the frozen type table pattern the existing
  runners carry is the shape to follow, and
  `tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py` enforces it.
- **Runner modules are private.** Never `python -m` one — only through `sq migrate`.
- **No ref-canonicalisation step, no ref `manual` clause, no release note about ref encoding.**
  Ruled out by A4; adding one would describe a state the upgrade path does not let an adopter
  reach.

## Acceptance

- One `Migration` record in `_migrations/_registry.py` for the 0.14.0 release, one runner module
  `_v0_11_to_v0_14.py`, and one `SCHEMA_VERSION` bump to `"0.14"` — covering both new types.
- The three places encoding the number agree: the runner filename, the registry entry
  (`version="0.14.0"`, `from_schema="0.11"`, `to_schema="0.14"`), and the corpus fixture
  `tests/fixtures/corpus/v0_14`.
- `tests/integration/test_migration_corpus.py`'s standing per-bump fixture rule is satisfied by a
  real `v0_14` fixture, not by an exemption.
- `sq migrate up` on a squad at the previous schema creates both types' folders, is idempotent on
  a squad that already has them, and stamps the new schema.
- A migrated squad and a freshly `sq init`-ed squad end with an identical on-disk generated
  surface for both new types: skill bodies, pointer filenames, pointer targets, pointer
  descriptions, and the `CLAUDE.md` / `AGENTS.md` managed regions. Asserted by comparison, on both
  paths, with the roster held constant.
- `sq migrate chlog` prints one manual entry covering both types, and it says nothing about ref
  encoding.
- A squad stepped through `sq migrate up` comes out with `sq check` clean and an ordinary mutation
  succeeding — the property A4 leans on.
- The runner imports no primitive from `_models` whose behaviour the live tree can change, and the
  migration import guard passes over it.
- `scripts/bump_version.py` was not run; `pyproject.toml` still reads 0.14.0. The template
  manifest matches the tree, only its `0.14.0` entry moved, and its freshness guard passes.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 813 add-subtask "<title>"`; track with `sq task 813 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Schema bump and the shared registry entry

<!-- sq:subtask:ST1:body -->
Bump `_models/_schema.py::SCHEMA_VERSION` from `"0.11"` (verified) to `"0.14"`, and append one
`Migration` record to `_migrations/_registry.py` for the 0.14.0 release, covering **both** new
item types.

The number is **settled** — do not re-derive it. ADR-320 §F is amended in place and its
amendment note carries the argument: the bump is `0.11 → 0.14`, confirmed from the tags rather
than from the convention text, since v0.12.0 and v0.13.1 both ship `SCHEMA_VERSION = "0.11"` and
a schema numbered `0.12` would name a release that shipped and introduced nothing.

The record:

- `version = "0.14.0"` — the squads release that ships it, the axis `sq migrate help` and
  `sq migrate chlog` report on;
- `from_schema = "0.11"`, `to_schema = "0.14"`;
- `summary` is one line for `sq migrate help` and **must name both types**, because one record is
  all either type gets.

**Three places encode the number and move together**: the runner module
`_migrations/_v0_11_to_v0_14.py`, this registry entry, and the corpus fixture
`tests/fixtures/corpus/v0_14` (ST5). Nothing else moves — ordering goes through `schema_tuple`
so `(0, 14)` sorts after `(0, 11)`, and the existing registry guard already ties the highest
registered `to_schema` to `SCHEMA_VERSION`.

The runner is async or wrapped with `_wrap_sync`, per the registry's own contract (verified in
`_migrations/_registry.py`).

**Write the runner to the migration import rule from the start.** A runner reads the vocabulary
of the schema version it transforms and may not reach into `_models` for a primitive whose
behaviour the live tree can change — carry frozen literals the way the existing runners carry
their frozen type tables, and keep
`tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py` passing. Retrofitting
that rule afterwards is how the existing runners acquired the defect it exists to prevent.

Done when one record, one runner module and one bump ship together, the three encodings agree,
the registry guard holds, and `sq migrate help` lists the step naming both types.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Create both new types' folders on an existing squad

<!-- sq:subtask:ST2:body -->
The runner's deterministic step: create each new type's folder on an existing squad.

`init` creates one folder per declared type, and `adopt` does the same — both loop
`for ts in effective_spec.items.values()` and `mkdir` each `ts.folder`
(`_services/_service.py`, verified), and both run at creation time only. A squad created before
these types existed therefore has no folder for either, and nothing else in the upgrade path
makes one. The runner owes it.

Requirements:

- **Idempotent.** A squad that already has the folder is unaffected; running the step twice
  changes nothing.
- **Both types, one step.** The contract folder and the milestone folder are created by the same
  run — that is what "one runner" means in practice.
- **Folder names come from the declarations**, not from literals invented here.
  `SquadPaths.folder_for` resolves a type's folder from the spec (`_paths.py`, verified — "the
  loaded spec is the sole vocabulary source for every type"), and the two type declarations are
  the input this step assumes.

No existing item data is rewritten, and no frontmatter shape changes. Say so in the runner's
docstring, the way `_v0_10_to_v0_11.py` says what it does not do and why — but note that this one
is not a no-op: it writes.

Nothing about ref encoding belongs here. `run_pending_migrations` calls `repair()` after the
runner and before stamping the new schema (`_services/_maintenance.py`, verified — `repair()` then
`_stamp_schema(SCHEMA_VERSION)`, in that order), which is what re-derives a stale index. A step of
this runner's own would duplicate it and could not resolve which kind carries the default without
reading the live spec, which the migration import rule forbids.

Done when `sq migrate up` on a pre-existing squad creates both folders, a second run changes
nothing, and the runner rewrites no item file.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Regenerate and verify the agent-facing surface

<!-- sq:subtask:ST3:body -->
Regenerate the managed agent-facing surface so both new types appear, and verify the result on
the **migrate** path and not only on `init`.

A new item type grows the managed surface: the per-type managed skill, its `.claude` pointer, and
the `CLAUDE.md` / `AGENTS.md` managed regions. All of it is generated and stamped as regenerated
by `sq sync`; a squad that migrates without it has the type but none of the guidance its agents
read.

**The verification rule is explicit in ADR-320 §E, and it names why**: "a type addition that wired
only the `init` path and left `migrate` unregenerated has bitten this project before".

`sq check` now verifies per-entry pointer **presence and currency** for every live roster entry —
that gate shipped separately and is not this task's to build. What this task owes is the on-disk
evidence that both types' artifacts pass it from either path, which the gate itself cannot give:
the gate answers "is a pointer present and current for this squad", not "do a migrated squad and
a fresh squad agree".

So compare, do not eyeball: a squad migrated with `sq migrate up` and a squad created fresh with
`sq init` must end with the **same** on-disk generated surface for both new types — skill body
files, pointer filenames, pointer targets, pointer descriptions, and the managed regions.
Assert the comparison in the suite so the two paths cannot drift later.

Hold the roster constant across the two squads when comparing. Generated per-type skill text is
roster-dependent, so a dev-less fresh squad diffed against a dev-bearing one reports differences
that are not regressions.

Done when both paths produce the same generated surface for both types, the comparison is
asserted rather than performed by hand, `sq sync` is a no-op on a freshly migrated squad, and
`sq check`'s per-entry pointer presence and currency gate is clean on both.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Manual runbook entry for both new types

<!-- sq:subtask:ST4:body -->
Write the runner's `manual` runbook entry — one entry covering both new types, surfaced by
`sq migrate chlog`.

What it says: the two types now exist, what each is for in one line, and — optionally — that the
squad may seed initial items for its current capabilities. A migration cannot author functional
truth on a team's behalf, which is exactly why this is a manual note rather than a deterministic
step.

What it must not say:

- **Nothing about ref encoding.** ADR-775 A4 rules out a manual clause for it, because it would
  instruct an adopter to run the repair `sq migrate up` had just run on their behalf. The same
  ruling excludes a release note.
- **No build-process narration.** The entry is read by an adopting team; it describes the tool,
  not how this release was assembled.
- **No sq item IDs and no ADR references.** It is adopter-facing text.

Keep it short. A runbook entry that lists optional steps at length reads as required work.

Done when `sq migrate chlog` for the release prints one entry naming both types, it says nothing
about ref encoding, and it carries no internal references.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Frozen corpus fixture tests/fixtures/corpus/v0_14

<!-- sq:subtask:ST5:body -->
Add the frozen corpus fixture `tests/fixtures/corpus/v0_14` that
`tests/integration/test_migration_corpus.py`'s standing rule requires of every schema bump.

**The fixture name follows the schema number, not the release count.** `tests/fixtures/corpus/`
holds `v0_1`, `v0_2`, `v0_3`, `v0_4`, `v0_5`, `v0_7`, `v0_8`, `v0_10`, `v0_11` today (verified) —
the same series with the same gaps, because 0.6 and 0.9 introduced no schema change and neither
did 0.12 or 0.13. Read the existing fixtures and its `README.md` before authoring a new one; the
shape is set by what is already there, not by this task.

This is the third of the three places encoding the number, alongside the runner module filename
and the registry entry. They move together, and a fixture named for the release count rather than
the schema would put the series out of step with the registry it mirrors.

Satisfy the rule with a **real fixture**, not an exemption: a frozen squad at schema `0.11` that
the runner is driven over, proving the upgrade path from real on-disk bytes rather than from a
constructed in-memory board. The fixture must exercise both halves — the migrated squad ends with
both new types' folders present and both types' generated surfaces in place.

Done when `tests/fixtures/corpus/v0_14` exists, the corpus test drives the new runner over it and
passes, no exemption or skip was added to satisfy the standing rule, and the fixture's name
matches the schema number the registry entry stamps.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T18:14:19Z] Olivia Lead:
  - Parented to FEAT-693 because that feature owns the milestone type, and worded so the shared-runner ruling survives a later breakdown: this item IS the release one runner, a later breakdown of either feature EXTENDS it rather than authoring a second, and it cannot close by delivering one half - both folders, both generated surfaces and one manual entry covering both, behind a single registry step. A runner authored twice is two bumps, which is what the operator ruled against.
  - Recorded that this is not release plumbing: ADR-775 A4 discharges REV-808 F3 on this runner existing. Verified the mechanism at _services/_maintenance.py:802-831 - run_pending_migrations applies each pending runner, calls repair() at :813, then stamps at :814, and the root callback refuses commands on a behind-schema squad. Without a runner in this release there is nothing to apply, repair never runs, and an accepted ruling has no mechanism under it. No ref step, no ref manual clause, no release note - A4 rules all three out.
  - One number I did NOT settle. ADR-320 section F says the bump is 0.11 to 0.12, but _models/_schema.py own docstring says the schema version tracks the alpha release that introduced it, and all eight registry entries follow that exactly (0.2.0 -> 0.2, 0.10.0 -> 0.10, 0.11.0 -> 0.11). Releases 0.12 and 0.13 shipped with no schema change, so under the convention a migration shipping in 0.14.0 stamps 0.14, and 0.12 would name a release that shipped and did not introduce it. The runner filename encodes the answer, so a dev cannot pick. @architect either the number moves or the docstring is narrowed in the same change - nothing else in the task depends on which.
  - Depends-on TASK-812 for a concrete reason, not caution: this runner edits _specs/workflow.toml, whose current content is named ONLY by the 0.14.0 index entry, so regenerating the manifest afterwards leaves an unreferenced blob and reds tests/meta until the sweep lands. Also depends-on FEAT-321 - the two type declarations are inputs this task does not author, and neither feature is broken down yet; the milestone type has no ADR clause naming its declaration at all.
- [2026-08-25T18:20:14Z] Robert Architect:
  - Ruled: the bump is 0.11 to 0.14, and ADR-320 section F is amended in place - it no longer says 0.12. Name the runner _v0_11_to_v0_14.py and register it as version 0.14.0, from_schema 0.11, to_schema 0.14. I confirmed it from the tags rather than the convention text: v0.12.0 and v0.13.1 both ship SCHEMA_VERSION = 0.11, so a schema numbered 0.12 would name a release that shipped and introduced nothing.
  - Gaps are not a concession made for this bump - they are already how the series reads. The registry runs 0.1 0.2 0.3 0.4 0.5 0.7 0.8 0.10 0.11, with no 0.6 and no 0.9 because those releases introduced no schema change. Skipping 0.12 and 0.13 is the same rule.
  - One thing to know before you read the convention as a rule you can invert: schema 0.4 does NOT name release 0.4.0. v0.4.0 ships SCHEMA_VERSION = 0.3, and both the 0.3-to-0.4 and 0.4-to-0.5 runners shipped inside release 0.5.0. The convention binds forward - a new schema number takes the release that introduces it, and a release may introduce more than one - so do not read a release number backwards out of an intermediate label. Recorded on ADR-320 as the one exception in the series.
  - Beyond the number itself, one thing is added to your scope and nothing else changes. The standing rule in tests/integration/test_migration_corpus.py requires a new frozen fixture per schema bump, so this owes tests/fixtures/corpus/v0_14 - the fixture name follows the schema number, not the release count. Otherwise: ordering goes through schema_tuple so (0,14) sorts after (0,11) exactly as (0,12) would, the existing registry guard already ties the highest registered to_schema to SCHEMA_VERSION, and nothing in the tree, the docs or the runbooks pins the retired number. The three places encoding it - runner filename, registry entry, corpus fixture - move together.
- [2026-08-26T13:40:55Z] Olivia Lead:
  - - Reconciled against both breakdowns, which now exist: TASK-831 declares the milestone type and TASK-832 declares the contract type, and **neither authors a runner**. Both added as `depends-on` — the two type declarations are inputs this task does not author, and it cannot create a folder for a type the spec does not declare. The "a later breakdown extends this, it does not author a second one" clause held; nothing here was duplicated.
    - Folded in the architect's ruling and closed the open number. The bump is `0.11 → 0.14`, the runner is `_v0_11_to_v0_14.py`, and the "needs confirming" section is gone from the body rather than annotated — it was the one thing a dev could not pick, and leaving the question standing beside the answer is how a dev picks the wrong one.
    - Added ST5 for `tests/fixtures/corpus/v0_14`, which the standing rule in `test_migration_corpus.py` requires of every schema bump and which no subtask covered. Named the three encodings explicitly in both the body and ST1 so they move together: runner filename, registry entry, corpus fixture. Verified the fixture series on disk — `v0_1 v0_2 v0_3 v0_4 v0_5 v0_7 v0_8 v0_10 v0_11`, the same gaps as the registry, so the name follows the schema number and not the release count.
    - Corrected two stale claims the body and ST3 carried. `sq check` **does** verify per-entry pointer presence and currency now (that gate shipped separately), so ST3 no longer says a wrong pointer "passes every gate" — what this task owes is the init-versus-migrate comparison, which the gate cannot give because it answers "is this squad's pointer current", not "do the two paths agree". And ST2's `_services/_maintenance.py:813-814` citation was stale; `run_pending_migrations` now sits at :944 with `repair()` then `_stamp_schema` at :955-956, so the citations are by symbol rather than by line.
    - One flag rather than a scope change. FEAT-694 retires the materialised summary and head regions, which is on-disk format and owes a corpus-wide edit; the operator kept that work in this release. Under §F's general form it joins **this** runner rather than adding a second bump, so this item's acceptance grows if it lands. Recorded in the body as a possible third claimant; nothing about it is authored here. @op-pierre worth deciding before the cut.
- [2026-08-26T13:42:14Z] Catherine Manager:
  - Third claimant confirmed rather than open: the operator ruled the region retirement stays in 0.14, so its corpus-wide migration joins this runner as a third half alongside the milestone and contract folders. It cannot be closed by delivering two of the three.
- [2026-08-26T16:28:25Z] Elias Python:
  - Runner built at src/squads/_migrations/_v0_11_to_v0_14.py, registered in _registry.py (version=0.14.0, from_schema=0.11, to_schema=0.14), SCHEMA_VERSION bumped 0.11->0.14 -- the three number sites agree.
  - Deterministic step: mkdir the two folders (resolved from the live spec per type, not frozen literals -- ST2's instruction), then a scoped regen mirroring init's own refresh_managed()+seed_bundled_skills() shape: ensure_scaffold + write_managed for every active backend (writes both skills' bodies, .claude pointers, and the compiled CLAUDE.md/AGENTS.md regions), then stamps a SKILL item for each of the two skills if not already indexed. Deliberately narrower than a full sync(): it does not touch existing roles' own pointers (their resolved preload-skill list) -- that stays sq sync's ongoing job, independent of any migration. No _models wire-encoding primitive imported; the meta guard passes.
  - Init-vs-migrate parity verified by a dedicated test (tests/integration/test_new_item_type_migration_surface_parity.py, 3 tests): both new types' folders exist on both paths, and the skill body prose + .claude pointer content are byte-identical between a fresh init and a stripped-then-migrated squad with the same roster. Also covers idempotency (migrating an already-current squad returns 0) and that migrate seeds a SKILL item for each new type.
  - Frozen corpus fixture added at tests/fixtures/corpus/v0_14 (schema 0.14: v0_11's content plus each new type's SKILL item/body/.claude pointer; no existing frontmatter shape changed), added to _CORPUS_CASES, README updated. Standing corpus suite: 21 passed (was 19; v0_11 now also exercises this runner end to end).
  - This repo's own squad: I ran sq migrate up on it (schema was still 0.11 on disk despite the folders/skills already existing from an earlier sq sync after the type declarations landed) -- confirmed a genuine near-no-op: only the schema stamp and an index repair() changed, zero .claude/ or CLAUDE.md diff, zero new md files. sq check: clean, no issues. Necessary because the SCHEMA_VERSION bump lives in the shared working tree -- leaving it unmigrated would hard-stop every other agent's sq command in this checkout (confirmed: tech-writer's concurrent TASK-833 run hit exactly that, now resolved).
  - One known gap: write_managed's WARN-only artifacts (e.g. a CLAUDE.md-had-no-markers contradiction notice) aren't surfaced through Migration.run's int-only return contract -- matches every other runner's contract, not something I changed, but worth naming since this runner is the first to call write_managed at all. Low real risk: an adopter's CLAUDE.md almost always already carries the managed section from a prior sq init/sync.
  - Manual runbook entry (sq migrate chlog) names both types in one line each plus the optional seed commands, nothing about ref encoding, no internal references -- see the runner's MANUAL constant.
  - Third claimant (the region-retirement migration) is NOT started -- nothing under _migrations/ or the schema/registry for it exists yet. It extends this SAME runner module/registry entry per the ruling; whoever picks it up adds its own deterministic step to _v0_11_to_v0_14.migrate() and its own corpus assertions to v0_14, not a new schema number.
  - Gates: tests/meta 259 passed; targeted set (migration corpus, registry, meta guard, schema-upgrade preservation, skill migration, reflog, docs cli, new parity suite) all green; uv run --all-extras pyright/ruff check/ruff format --check clean repo-wide. Did not run the full suite per brief -- leaving that to the main loop.
  - @tech-lead the runner + type-1/type-2 halves are complete and verified end to end on this repo; still needs the region-retirement (FEAT-694) half before the release-level acceptance ('closes when both types' folders, both types' generated surfaces and one manual entry covering both are in place behind a single registry step... grows with it rather than a second registry entry appearing') is fully met. Moving to InReview for that call.
- [2026-09-01T07:42:28Z] Catherine Manager:
  - Reopened: I closed this on the two type halves while its own acceptance says it cannot close on partial delivery, and the third claimant — the corpus-wide region strip — has no step in `migrate()` yet. The constraint that made this one item still binds: the region retirement extends this runner and this registry entry, and does not author a second bump. Closing it early was my error, not a scope change.
- [2026-09-01T08:01:04Z] Pierre Chat:
  - Fourth claimant: shrinking the role bodies of duplicated catalog data joins this runner. Still one bump, still one runner.
- [2026-09-01T08:10:00Z] Olivia Lead:
  - Reopened on the third claimant: FEAT-694's corpus-wide region strip is now TASK-849, which extends
    `_v0_11_to_v0_14.migrate()` and this entry rather than authoring a second runner or a second bump.
    Added `depends-on TASK-849` here so the board shows this cannot close first — its own acceptance
    already says it grows with the third claimant rather than a second registry entry appearing.
    
    One trap TASK-849 carries that is worth knowing here: this repository's squad is already stamped
    schema 0.14 (`squads/.squads.json`, `.squads.toml`), so `sq migrate up` is a no-op locally and the
    new step never runs on our own corpus through the ordinary path. TASK-849 ST5 handles it as a
    deliberate rewind-and-replay of this runner, which is safe because every step it already performs
    is documented and verified idempotent.
<!-- sq:discussion:end -->
