---
id: TASK-000050
sequence_id: 50
type: task
title: Ref-kind vocabulary constant + validation at all authoring entry points
status: Done
parent: FEAT-000035
author: tech-lead
assignee: python-dev
priority: high
refs:
- TASK-000051:blocks
subentities:
- local_id: ST1
  title: Define VALID_REF_KINDS (closed eight) in _models/_item.py; validate --kind
    in add_ref, rejecting unknowns with the valid list
  status: Done
  story: US1
- local_id: ST2
  title: 'Keep bare ref add first-class: default related validates trivially, no nudge,
    no warning'
  status: Done
  story: US2
- local_id: ST3
  title: Wire depends-on/supersedes/duplicates as accepted kinds at ref add and create
    --ref id:kind; authorable from the dependent
  status: Done
  story: US4
created_at: '2026-06-11T20:21:59Z'
updated_at: '2026-06-11T20:43:22Z'
---
<!-- sq:body -->
Make the ref-kind vocabulary a finite, single-source-of-truth list and enforce it at every authoring entry point. Per **ADR-000049** (Proposed): the 1.0 vocabulary is **explicitly CLOSED** — eight kinds, no project-config lookup on the validation path, no custom-kind escape hatch.

## The eight kinds (the closed set)
`related`, `blocks`, `depends-on`, `implements`, `fixes`, `addresses`, `supersedes`, `duplicates`.

Three are **new** this feature (decided with op-pierre 2026-06-11):
- **`supersedes`** — `DEC-B supersedes DEC-A`, stored on the newer decision.
- **`depends-on`** — stored on the *dependent*; semantic inverse of `blocks` (`A depends-on B` ≡ `B blocks A`). Exists so a dependency is authorable from the item you're drafting without editing the blocker.
- **`duplicates`** — `BUG-B duplicates BUG-A`, stored on the later filing.

## Scope
- Define the vocabulary in **ONE place in code** — colocate with `split_ref`/`make_ref`/`DEFAULT_KIND` at the top of `src/squads/_models/_item.py` (e.g. a frozen `VALID_REF_KINDS: frozenset[str]` or a small enum — your call, but no scattered string literals). `related` (== `DEFAULT_KIND`) must be a member.
- Validate `--kind` at the authoring surfaces. Unknown kind → clean `SquadsError` (subclass; caught by `@handle_errors`) listing the valid kinds. Validate in the **service** (`_services/_refs.py::add_ref`) so both CLI paths and any future caller are covered:
  - `sq <type> <n> ref add --kind` — `src/squads/_cli/_items.py` (~line 231; recently rewired through `resolve_item_id_any`). Note the embedded-kind path (`target` may arrive as `ID:kind`).
  - `sq create … --ref id:kind` — `src/squads/_cli/_create.py` (~line 64, `split_ref` → `make_ref`).
- **Untyped refs stay first-class (US2).** A bare `ref add <id>` with no `--kind` defaults to `related` and must remain frictionless — no nudge to over-type, no warning. Default `related` validates trivially as a member.
- **Format is unchanged** — kinds are additive; `schema_version` stays `0.3`, no migration. (Verified: `make_ref`/`split_ref` and the inline `"ID:kind"` format are untouched.)

## Out of scope (→ TASK-000051)
Consumers (`depends-on` in `sq blocked`, `supersedes`/unknown-kind warnings in `sq check`) and the docs kinds table. This task is constant + entry-point validation only.

## Acceptance
- Unknown `--kind` (e.g. `banana`, typo `fixe`) rejected at `ref add` AND at `create --ref` with the valid list; exit 1.
- All eight kinds accepted (incl. the three new ones).
- Bare `ref add <id>` (no `--kind`) unchanged — still creates a `related` edge silently.

## Tests (per CLAUDE.md: a service test + a CLI smoke test)
- Service: `add_ref` accepts each of the eight kinds; rejects an unknown with `SquadsError` whose message lists valid kinds.
- CLI: `ref add --kind banana` → exit 1, message names the valid kinds; `ref add --kind supersedes` → ok; bare `ref add` → ok (related). `create --ref ID:banana` → exit 1.
- Assert frontmatter after a typed add (valid `"ID:kind"`, markers intact).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 50 add-subtask "<title>"`; track with `sq task 50 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Define VALID_REF_KINDS (closed eight) in _models/_item.py; validate --kind in add_ref, rejecting unknowns with the valid list | US1 |
| ST2 | Done |  | Keep bare ref add first-class: default related validates trivially, no nudge, no warning | US2 |
| ST3 | Done |  | Wire depends-on/supersedes/duplicates as accepted kinds at ref add and create --ref id:kind; authorable from the dependent | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Define VALID_REF_KINDS (closed eight) in _models/_item.py; validate --kind in add_ref, rejecting unknowns with the valid list

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a user adding a typed ref, I want a typo'd kind rejected on the spot with the valid vocabulary, so that I can't silently create an edge nothing consumes
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Keep bare ref add first-class: default related validates trivially, no nudge, no warning

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a user linking context, I want plain untyped refs to stay first-class, so that not every link needs a taxonomy decision
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Wire depends-on/supersedes/duplicates as accepted kinds at ref add and create --ref id:kind; authorable from the dependent

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US4 — As a user drafting an item that needs another one first, I want to record depends-on from the item I'm editing, so that dependencies are authorable without touching the blocker
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T20:30:51Z] Elias Python:
  - Implementation complete. VALID_REF_KINDS (frozenset, eight kinds) colocated with split_ref/make_ref/DEFAULT_KIND in src/squads/_models/_item.py. Validation at both authoring entry points: add_ref in _services/_refs.py (covers sq <type> ref add --kind) and svc.create in _services/_base.py (covers sq create --ref id:kind). Unknown kind → SquadsError listing all valid kinds. Bare ref add stays frictionless (DEFAULT_KIND, no nudge). Three new kinds (supersedes, depends-on, duplicates) accepted and round-trip through frontmatter. Help text updated to list all eight. Schema version unchanged (additive).
  - Scattered 'related' literals in CLI (_items.py, _common.py) and service (_refs.py add_ref default) routed through DEFAULT_KIND. Blocks comparison in blocked() left as-is (consumer, not authoring — scope of TASK-000051).
  - Gates green: 265 passed (1 skipped), pyright 0 errors, ruff clean, sq check no issues. @tech-lead ready for review.
- [2026-06-11T20:43:22Z] Paul Reviewer:
  - Done via REV-000052 (Approved). Constant + validation at add_ref and create verified live and by tests.
<!-- sq:discussion:end -->
