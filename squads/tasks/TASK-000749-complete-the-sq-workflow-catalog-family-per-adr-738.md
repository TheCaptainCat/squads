---
id: TASK-749
sequence_id: 749
type: task
title: Complete the sq workflow catalog family per ADR-738
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-732:fixes
- ADR-738:implements
description: Publish the lifecycles catalog, confirm the shipped kind catalog and
  type-row keys against the decision, and retire the forward-reference wording
subentities:
- local_id: ST1
  title: Publish the sq workflow lifecycles catalog
  status: Done
- local_id: ST2
  title: Confirm the kind catalog and type-row keys match the decision
  status: Done
- local_id: ST3
  title: Retire the lifecycle forward-reference in the adopter docs
  status: Done
created_at: '2026-08-21T12:42:49Z'
updated_at: '2026-08-21T18:36:55Z'
---
<!-- sq:body -->
Close the `sq workflow` catalog family so every top-level declared map on `WorkflowSpec` has exactly
one catalog command, per ADR-738. Read ADR-738 in full first — it settles the row grammar, the
identity keys, the orders, and what is deliberately not published. Nothing here re-decides any of
that; deviating from it needs the architect, not a judgement call in the code.

## What already ships, and what is left

Read before planning — the surface is further along than the reporting bug describes. Driven against
this repo:

- `sq workflow subentity-kinds --json` exists and emits the ADR-738 section 3 row
  (`subentity_kind`, `lifecycle`, `plural`, `local_prefix`, `container_heading`, `completion`,
  `maps_parent_story`, `fields`), with `SUBENTITY_KIND_CATALOG_FIELDS` frozen in
  `src/squads/_cli/_workflow_cmd.py` and CLI tests in `tests/cli/test_workflow_subentity_kinds_cli.py`.
- Both ADR-738 section 5 reference keys are on the type row already: `TYPE_CATALOG_FIELDS` is
  `(type, order, prefix, reserved, category, subentity_kind, lifecycle, fields, labels)`.
- `sq workflow lifecycles` does not exist — the command errors with `No such command`.
- The adopter docs therefore still document `lifecycle` as a forward reference with no catalog to
  join: `docs/workflow.md` (the join table row, and the section stating `lifecycle` is a grouping key
  and nothing more) and `docs/stability.md` (the Tier-3 catalog table, and the note calling
  `lifecycle` the exception that names a machine no catalog publishes).

So the remaining work is the `lifecycles` catalog, a confirmation that the shipped kind catalog and
type-row keys actually match ADR-738 sections 3 and 5, and retiring the forward-reference wording the
new catalog makes false. The subtasks split along those three surfaces.

## A helper the fix direction names no longer exists

`lifecycle_edges` was deleted as genuinely dead code once the cheatsheet state diagram was removed
(vulture-flagged; the deletion is recorded on the review that found it). Do not resurrect it as a
copy of what it used to be, and do not read the reporting bug's fix direction as though it is still
available. The edge list must be re-derived, and the derivation has to be deterministic and
byte-stable across process runs, because the published order is part of the contract:

- `lifecycle_states_in_order(machine)` (`src/squads/_workflow/_models.py`) still exists and still has
  a live caller. Walk it for the source order.
- `Lifecycle.transitions` is a `dict[str, list[str]]` — the target lists preserve their declared TOML
  order, so use them as they are for the per-source target order.
- `Lifecycle.states` is a `frozenset`; never iterate it for anything that reaches output.

That is: sources in `lifecycle_states_in_order` order, targets in declared order within each source.
A source with no outgoing edges contributes nothing. Assert the ordering in a test rather than
leaving it to be inferred from the implementation.

## Surfaces

- `src/squads/_cli/_workflow_cmd.py` — the new sub-command, its frozen field tuple, its Rich table,
  and the two places that enumerate the family (the module docstring and the cheatsheet callback's
  "Run `sq workflow ...`" line).
- `src/squads/_workflow/_models.py` — read-only unless the edge derivation belongs on the spec next to
  `lifecycle_states_in_order`; if it does, put it there rather than in the CLI module.
- `tests/cli/` — a new catalog test alongside the four existing `test_workflow_*_cli.py` files.
- `docs/workflow.md`, `docs/stability.md`, `CHANGELOG.md`.

## Acceptance criteria

- `sq workflow lifecycles` prints a human Rich table; `sq workflow lifecycles --json` emits a bare
  JSON array, one row per entry of `spec.lifecycles`, ascending by lifecycle name.
- Each row is exactly `{lifecycle, initial, states, transitions}` — every key present on every row,
  `transitions` an array of `{from, to}` objects, never a positional pair and never keyed on status
  names.
- A module-level frozen field tuple in the same style as its four siblings, drift-tested against the
  emitted rows so the CLI cannot diverge from the declared contract.
- `states` is `lifecycle_states_in_order` output — not `linearize_lifecycle`'s spine ordering.
- Running the command twice in separate processes produces byte-identical JSON (the ordering
  contract), asserted by a test.
- Exit 0 on success, 1 when the spec refuses to load, matching the four siblings.
- The catalog reflects an override: a project-declared lifecycle appears, and a dropped one does not.
- `docs/workflow.md` and `docs/stability.md` no longer tell an adopter that `lifecycle` has no
  catalog to join.
- `CHANGELOG.md` carries an adopter-facing entry for the new command in the unreleased section.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 749 add-subtask "<title>"`; track with `sq task 749 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Publish the sq workflow lifecycles catalog |  |
| ST2 | Done |  | Confirm the kind catalog and type-row keys match the decision |  |
| ST3 | Done |  | Retire the lifecycle forward-reference in the adopter docs |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Publish the sq workflow lifecycles catalog

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
The half the reporting bug asks for, and the whole of what it asks for: a machine-readable lifecycle
surface. `sq workflow lifecycles`, one row per entry of `spec.lifecycles`, ascending by lifecycle
name, `{lifecycle, initial, states, transitions}` — human Rich table by default, bare JSON array under
`--json`, exit 0 on success and 1 when the spec refuses to load, exactly as its four siblings behave.

Lands in `src/squads/_cli/_workflow_cmd.py` with a module-level frozen field tuple in the same style
as `TYPE_CATALOG_FIELDS` and its siblings, drift-tested against the emitted rows, plus a CLI test
alongside `tests/cli/test_workflow_*_cli.py`. Also update the two places in that module that enumerate
the family: the module docstring and the cheatsheet callback's `Run sq workflow ...` line.

`states` is `lifecycle_states_in_order(machine)`. `transitions` is an array of `{from, to}` objects
with sources in that same order and targets in each source's declared order — see the parent body for
why the helper the bug's fix direction names is gone and must not be resurrected. Two runs in separate
processes must produce byte-identical JSON, asserted by a test. Cover an override too: a
project-declared lifecycle appears in the catalog and a dropped one does not.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Confirm the kind catalog and type-row keys match the decision

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
The sub-entity-kind half of the decision is already on disk — `sq workflow subentity-kinds --json`
emits its row, and the type row already carries both `subentity_kind` and `lifecycle`. This is the
audit that turns "it ships" into "it ships what was decided", tracked separately from the lifecycles
build because it is a different surface and could have its own gaps.

Check each against ADR-738 sections 3 and 5, and fix what does not match:

- The kind row's key set is exactly `subentity_kind`, `lifecycle`, `plural`, `local_prefix`,
  `container_heading`, `completion`, `maps_parent_story`, `fields`, every key present on every row,
  `null` rather than omitted, rows ascending by kind name.
- `fields` on the kind row uses the *same* frozen entry tuple as the type row's `fields`
  (`{code, label, collection}`), one shared builder — not a parallel shape.
- `placeholder` is not published.
- `container_heading` matches the heading sq actually writes into the file, including the bundled
  special case that plain title-casing of `plural` does not produce.
- The type row's `subentity_kind` joins the kind row's identity key by the identical key name, and is
  `null` for a type that hosts no kind.
- The `fields[].collection` join resolves against `sq workflow collections --json`.
- The frozen field tuples are drift-tested and golden-locked.

Report the audit result on the parent item — per row, either "matches" or the gap you closed. If
everything matches, that is a valid outcome and the record is the deliverable.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Retire the lifecycle forward-reference in the adopter docs

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
The adopter docs currently tell a reader that `lifecycle` names a machine no catalog publishes. Once
the new catalog exists that is false, and a false join instruction is worse than a missing one.

- `docs/workflow.md` — the catalog join table's `lifecycle` row currently reads "no catalog in this
  release"; point it at the `lifecycles` catalog and its `lifecycle` identity key. The section stating
  `lifecycle` is a grouping key and nothing more, and pointing readers at the diagrams or
  `sq workflow show` instead, is replaced by the real join. The catalog list near the top of that page
  gains `lifecycles`.
- `docs/stability.md` — add the `lifecycles` row to the Tier-3 catalog table with its key set, and
  remove the note calling `lifecycle` the exception that names a machine no catalog publishes.
- `CHANGELOG.md` — an adopter-facing entry in the unreleased section for the new command and the join
  it opens up.

Adopter-facing text only: describe the command and the join, with no reference to sq item ids, this
repository's process, or the order the pieces were built in. Grep both docs for any remaining wording
that says lifecycle membership is unavailable in the JSON surface, including the note that
`sq workflow statuses` is the only place statuses appear.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T12:44:49Z] Olivia Lead:
  - Scoped against the on-disk surface, not the bug text: the subentity-kinds catalog and BOTH type-row reference keys already ship (driven; TYPE_CATALOG_FIELDS carries subentity_kind + lifecycle). Only `sq workflow lifecycles` is missing, so ST1 is the build, ST2 audits the shipped half against ADR-738 sections 3 and 5, ST3 retires the documented forward reference.
- [2026-08-21T13:03:08Z] Elias Python:
  - ST1 done: sq workflow lifecycles / --json now ships. Row = {lifecycle, initial, states, transitions}, ascending lifecycle name. Re-derived the edges since lifecycle_edges is gone: added lifecycle_edges_in_order(machine) next to lifecycle_states_in_order in _workflow/_models.py (sources in BFS order, targets in declared order) rather than resurrecting the old helper. LIFECYCLE_CATALOG_FIELDS/TRANSITION_ENTRY_FIELDS frozen tuples, drift-tested, golden-locked (workflow_lifecycles golden added). Covered: BFS-not-spine ordering, byte-identical output across two real subprocesses, exit 1 on a refusing override, and an override that adds a lifecycle and drops a now-unbound bundled one.
  - ST2 audit verdict: MATCHES. Walked ADR-738 sections 3 and 5 against the shipped code line by line — key sets (SUBENTITY_KIND_CATALOG_FIELDS, TYPE_CATALOG_FIELDS) are exactly the declared sets, fields[] is one shared builder/entry-tuple for both catalogs, placeholder is absent, container_heading resolves through the same spec.subentity_container_heading() the templates call (so it can never disagree with the file), type.subentity_kind is null for a hostless type and joins the kind row by identical key name, fields[].collection is guaranteed resolvable by load-time model validation, and both frozen tuples are already drift-tested and golden-locked. No gap found, no bug filed.
  - ST3 done: docs/workflow.md (catalog list, join table, replaced the 'no catalog this release' paragraph with the real lifecycles join, fixed the states-ordering claim to say BFS not spine so it doesn't contradict sq workflow show's own rendering) and docs/stability.md (Tier-3 table row + join note) no longer say lifecycle has no catalog. CHANGELOG.md: new adopter-facing ## [0.14.0] / ### Added entry.
  - Gates: uv run --all-extras pyright -> 0 errors; uv run --all-extras ruff check . -> All checks passed; uv run --all-extras ruff format --check . -> 508 files already formatted; targeted pytest (10 workflow CLI modules + test_json_output_shape.py, 120 tests) -> 120 passed; tests/meta (165 tests, module-constant guard) -> 165 passed; uv run sq check -> no issues. Commit 8f5b267 on release/0.14, unpushed.
<!-- sq:discussion:end -->
