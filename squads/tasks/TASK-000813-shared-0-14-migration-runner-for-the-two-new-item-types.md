---
id: TASK-813
sequence_id: 813
type: task
title: Shared 0.14 migration runner for the two new item types
status: Draft
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
description: The single schema bump, registry entry and runner carrying both the contract
  and milestone types into 0.14, plus the folder creation, surface regeneration and
  manual runbook entry
subentities:
- local_id: ST1
  title: Schema bump and the shared registry entry
  status: Todo
- local_id: ST2
  title: Create both new types' folders on an existing squad
  status: Todo
- local_id: ST3
  title: Regenerate and verify the agent-facing surface
  status: Todo
- local_id: ST4
  title: Manual runbook entry for both new types
  status: Todo
created_at: '2026-08-25T18:12:45Z'
updated_at: '2026-08-25T18:20:14Z'
---
<!-- sq:body -->
## Scope

ADR-320 §F. The single schema migration that carries **both** new item types into the 0.14
release: `contract` (`PRD`, FEAT-321) and the milestone type (`MILE`, this feature).

## One runner, shared — and what that obliges a later breakdown to do

The operator ruled one bump and one migration for both types, so the two features land in the
same release (recorded on ADR-320, 2026-08-24: "Schema: 0.14 carries ONE bump for both new item
types (PRD and MILE) in a single migration, so FEAT-321 and FEAT-693 land in the same release").
ADR-320 §F states the same and adds the general form: **any other schema-level change shipping in
0.14 joins this runner rather than adding a second bump.**

**This item is the release's one runner. A later breakdown of either feature extends it; it does
not author a second one.** That obligation is the reason this is tracked here rather than inside
either type's own delivery — a runner authored twice is two bumps, and two bumps is precisely
what was ruled against. Concretely: the milestone half and the contract half each add their own
folder and their own generated surface to *this* runner's deterministic step and to *this*
runner's manual entry. It is parented here because this feature owns the milestone type; the
contract half is no less its business for that.

It also means this item cannot be closed by delivering one half. It closes when both types'
folders, both types' generated surfaces and one manual entry covering both are in place behind a
single registry step.

## Why this is not merely release plumbing

ADR-775 amendment A4 discharges REV-808's F3 — a pre-0.14 squad holding a spelled default ref
kind on disk and in its index — **on this runner existing**. The mechanism:
`run_pending_migrations` (`_services/_maintenance.py:802-831`, verified) applies each pending
runner, then calls `repair()` (`:813`) **before** stamping the new schema (`:814`), and the root
CLI callback refuses every command on a squad whose schema is behind. So a pre-0.14 squad cannot
reach a mutating command without first running `sq migrate up`, and that run re-derives its index
from the folded disk.

The migration *is* the corrective sweep, which is why A4 rules out any ref-canonicalisation step
of its own, any `manual` clause about it and any release note. **Nothing about refs is added to
this runner.** What matters is that a runner exists in this release at all: without one,
`run_pending_migrations` has nothing to apply, `repair()` never runs, and an accepted ruling has
no mechanism underneath it.

## The bump, and a number that needs confirming before the file is named

ADR-320 §F states the bump as **`0.11 → 0.12`** on `_models/_schema.py::SCHEMA_VERSION`
(currently `"0.11"`).

That conflicts with the stated convention in the same module, and the dev must not pick a side on
their own, because the runner's filename encodes it (`_v0_11_to_v0_12.py` versus
`_v0_11_to_v0_14.py`). The module docstring says the schema version "tracks the **alpha release
that introduced it**", and all eight registry entries follow it exactly — `0.2.0` → `"0.2"`,
`0.10.0` → `"0.10"`, `0.11.0` → `"0.11"`. Releases 0.12 and 0.13 shipped without a schema change,
so under that convention a migration shipping in 0.14.0 stamps `"0.14"`, and stamping `"0.12"`
would name a release that shipped and did not introduce it.

Either the number moves or the convention is narrowed in this same change. This is the
architect's to confirm; it is raised on this item's discussion. Everything else below is
unaffected by which way it goes.

## The deterministic step

No existing item data is rewritten, so the run itself is light:

- **Create each new type's folder**, matching what `init` does per declared type
  (`_services/_service.py:158-160`; `adopt` at `:223-226`). Those loops run at creation time only,
  so an existing squad gets no folder for a type added later — the runner owes it. Idempotent:
  a squad that already has the folder is unaffected.
- **Regenerate the managed agent-facing surface** so the new per-type skills, their `.claude`
  pointers and the `CLAUDE.md` / `AGENTS.md` regions appear (ADR-320 §E).

`_v0_10_to_v0_11.py` is the model for the shape of a light runner — including saying in its own
docstring what it does *not* do and why — but this one is not a no-op: it writes folders and
regenerates.

## Verify the generated artifacts on migrate, not only on init

ADR-320 §E makes this an explicit rule, and names why: "a type addition that wired only the
`init` path and left `migrate` unregenerated has bitten this project before". Pointer filenames,
targets and descriptions are not validated by `sq check` today.

So the check is by hand and by test: a squad migrated with `sq migrate up` and a squad created
fresh with `sq init` must end with the **same** on-disk generated surface for both new types —
skill bodies, pointer filenames, pointer targets and descriptions, and the managed regions.
Compare them, do not eyeball one.

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
  last must do so with every other 0.14.0 change already in the tree.
- A squad carrying a `.overrides/workflow.toml` sees a genuine, content-gated drift warning when
  this lands. That is the correct signal.

## Traps

- **The two type declarations are inputs this does not author.** ADR-320 §A settles the contract
  type as one `[items.contract]` block plus one `[lifecycles.contract]` block in
  `src/squads/_specs/workflow.toml`. The milestone type has no equivalent clause yet — ADR-776
  does not name it. Neither feature has been broken down. The runner cannot create a folder for a
  type the spec does not declare, so those declarations land first or with it.
- **The migration import rule constrains this runner from the day it is written.** A runner reads
  the vocabulary of the schema version it transforms and may not reach into `_models` for a
  primitive whose behaviour the live tree can change; the frozen type table pattern the existing
  runners carry is the shape to follow. That rule is being re-derived alongside this work, so
  write the runner to it rather than retrofitting it afterwards.
- **A regeneration in this release orphans a content-store blob** unless the generator's
  reachability sweep is in first: `_specs/workflow.toml`'s current content is named **only** by
  the `0.14.0` index entry, so editing it and regenerating leaves a blob nothing references and
  reds `tests/meta`. Recorded as a `depends-on`.
- **No ref-canonicalisation step, no ref `manual` clause, no release note about ref encoding.**
  Ruled out by A4; adding one would describe a state the upgrade path does not let an adopter
  reach.

## Acceptance

- One `Migration` record in `_migrations/_registry.py` for the 0.14.0 release, one runner module,
  and one `SCHEMA_VERSION` bump — covering both new types.
- The stamped schema value and the runner's filename agree with each other and with whichever way
  the number question above is settled; if the convention is the one that moves, the module
  docstring stating it is narrowed in this same change.
- `sq migrate up` on a squad at the previous schema creates both types' folders, is idempotent on
  a squad that already has them, and stamps the new schema.
- A migrated squad and a freshly `sq init`-ed squad end with an identical on-disk generated
  surface for both new types: skill bodies, pointer filenames, pointer targets, pointer
  descriptions, and the `CLAUDE.md` / `AGENTS.md` managed regions. Asserted by comparison, on both
  paths.
- `sq migrate chlog` prints one manual entry covering both types, and it says nothing about ref
  encoding.
- A squad stepped through `sq migrate up` comes out with `sq check` clean and an ordinary mutation
  succeeding — the property A4 leans on.
- The runner imports no primitive from `_models` whose behaviour the live tree can change, and the
  migration import guard passes over it.
- `scripts/bump_version.py` was not run; `pyproject.toml` still reads 0.14.0. The template
  manifest matches the tree and its freshness guard passes.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 813 add-subtask "<title>"`; track with `sq task 813 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Schema bump and the shared registry entry |  |
| ST2 | Todo |  | Create both new types' folders on an existing squad |  |
| ST3 | Todo |  | Regenerate and verify the agent-facing surface |  |
| ST4 | Todo |  | Manual runbook entry for both new types |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Schema bump and the shared registry entry

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Bump `_models/_schema.py::SCHEMA_VERSION` (currently `"0.11"`) and append one `Migration` record
to `_migrations/_registry.py` for the 0.14.0 release, covering **both** new item types.

The record's `version` is the squads release that ships it — `"0.14.0"` — and `from_schema` is
`"0.11"`. Its `summary` is one line for `sq migrate help` and must name both types, because one
record is all either type gets.

**The `to_schema` value needs confirming before the runner module is named**, since the filename
encodes it. ADR-320 §F states the bump as `0.11 → 0.12`. The `_schema.py` module docstring states
the convention that the schema version "tracks the alpha release that introduced it", and all
eight existing registry entries follow it exactly — `0.2.0` → `"0.2"`, `0.10.0` → `"0.10"`,
`0.11.0` → `"0.11"`. Releases 0.12 and 0.13 shipped with no schema change, so under that
convention a migration shipping in 0.14.0 stamps `"0.14"`. Either the number moves or the
convention is narrowed in this same change; it is raised on this item's discussion for the
architect.

Whichever way it goes, three things must agree: the stamped `SCHEMA_VERSION`, the record's
`to_schema`, and the runner module's filename.

The runner is async or wrapped with `_wrap_sync`, per the registry's own contract.

**Write the runner to the migration import rule from the start.** A runner reads the vocabulary of
the schema version it transforms and may not reach into `_models` for a primitive whose behaviour
the live tree can change — carry frozen literals the way the existing runners carry their frozen
type tables. That rule is being re-derived alongside this work, and retrofitting it afterwards is
how the existing runners acquired the defect it exists to prevent.

Done when one record, one runner module and one bump ship together, the three values agree, and
`sq migrate help` lists the step naming both types.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Create both new types' folders on an existing squad

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
The runner's deterministic step: create each new type's folder on an existing squad.

`init` creates one folder per declared type (`_services/_service.py:158-160`), and `adopt` does
the same (`:223-226`) — both at creation time only. A squad created before these types existed
therefore has no folder for either, and nothing else in the upgrade path makes one. The runner
owes it.

Requirements:

- **Idempotent.** A squad that already has the folder is unaffected; running the step twice
  changes nothing.
- **Both types, one step.** The contract folder and the milestone folder are created by the same
  run — that is what "one runner" means in practice.
- **Folder names come from the declarations**, not from literals invented here. `folder_for`
  resolves a type's folder from the spec (`_paths.py:74-85`), and the declarations are the input
  this step assumes.

No existing item data is rewritten, and no frontmatter shape changes. Say so in the runner's
docstring, the way `_v0_10_to_v0_11.py` says what it does not do and why — but note that this one
is not a no-op: it writes.

Nothing about ref encoding belongs here. `run_pending_migrations` runs `repair()` after the runner
and before stamping (`_services/_maintenance.py:813-814`), which is what re-derives a stale index;
a step of this runner's own would duplicate it and could not resolve which kind carries the
default without reading the live spec, which the migration import rule forbids.

Done when `sq migrate up` on a pre-existing squad creates both folders, a second run changes
nothing, and the runner rewrites no item file.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Regenerate and verify the agent-facing surface

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Regenerate the managed agent-facing surface so both new types appear, and verify the result on
the **migrate** path and not only on `init`.

A new item type grows the managed surface: the per-type managed skill, its `.claude` pointer, and
the `CLAUDE.md` / `AGENTS.md` managed regions. All of it is generated and stamped as regenerated
by `sq sync`; a squad that migrates without it has the type but none of the guidance its agents
read.

**The verification rule is explicit in ADR-320 §E, and it names why**: "a type addition that wired
only the `init` path and left `migrate` unregenerated has bitten this project before". Pointer
filenames, targets and descriptions are not validated by `sq check` today, so a wrong or missing
pointer passes every gate.

So compare, do not eyeball: a squad migrated with `sq migrate up` and a squad created fresh with
`sq init` must end with the **same** on-disk generated surface for both new types — skill body
files, pointer filenames, pointer targets, pointer descriptions, and the managed regions.
Assert the comparison in the suite so the two paths cannot drift later.

Hold the roster constant across the two squads when comparing. Generated per-type skill text is
roster-dependent, so a dev-less fresh squad diffed against a dev-bearing one reports differences
that are not regressions.

Done when both paths produce the same generated surface for both types, the comparison is
asserted rather than performed by hand, and `sq sync` is a no-op on a freshly migrated squad.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Manual runbook entry for both new types

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST4:head:end -->

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
<!-- sq:discussion:end -->
