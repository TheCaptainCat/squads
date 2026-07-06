---
id: TASK-47
sequence_id: 47
type: task
title: Adopt the shared resolver across all ID-accepting surfaces + uniform error
  wording
status: Done
parent: FEAT-19
author: tech-lead
assignee: python-dev
priority: high
subentities:
- local_id: ST1
  title: Wire all ID-accepting paths through the resolver
  status: Done
  story: US2
- local_id: ST2
  title: Uniform unknown-item error wording mentioning both accepted forms everywhere
  status: Done
  story: US3
created_at: '2026-06-11T13:59:33Z'
updated_at: '2026-07-06T15:17:49Z'
---
<!-- sq:body -->
## Goal
Route **every remaining ID-accepting surface** through the shared resolver from TASK-46 (typed surfaces → typed resolve with live-DB type check; type-less surfaces → type-less resolve), and make unknown-item error wording uniform (both accepted forms, everywhere). **Blocked by TASK-46** (the resolver must land first).

## Inventory to convert (verified by the manager)
Raw / unvalidated surfaces today:
- **create**: `--parent` + `--ref` — `_cli/_create.py:36,41,89`
- **update**: `--parent` — `_cli/_items.py:104`
- **ref add / ref rm targets** — `_cli/_items.py:231,243` (kind-agnostic — `ref add` does NOT enforce a type; per the feature body)
- **`sq tree <root>`** — `_cli/_main.py:151` (a bare number silently matches nothing today)
- **`sq list --parent`** — `_cli/_main.py:119`
- **`sq role regen/rm`**, **`sq skill show/regen/rm`**, **`sq operator rm`** — `_cli/_role.py`, `_skill.py`, `_operator.py`
- **subtask `--story`** is raw — validate it through the appropriate path.
Already fine (leave as-is): sub-entity `<k>` uses `resolve_local_id`.

## Design direction
- **Typed surfaces** (`sq <type> <n>` shaped): verify the resolved item's ACTUAL type against the live DB (handled by TASK-46's typed resolve).
- **Type-less surfaces** (tree root, ref targets, `--parent` *before* `parent_allowed` runs): resolve a bare number to whatever item owns it — no type word.
- `ref add` **stays kind-agnostic** (feature body): resolve the target to a real item, but don't constrain its type.
- **`--parent`**: resolve the bare number to a real item first (type-less), then let the existing `parent_allowed`/`parent_hint` workflow check do the parent-type validation — don't duplicate it.
- **Unknown-item errors mention BOTH forms** (full ID and bare number) on every surface.

## Constraints
- Additive: no existing valid invocation breaks (e.g. `sq tree FEAT-000013` keeps working; now `sq tree 13` works too).
- Raise `SquadsError` only; strict `pyright` + `ruff` clean; acyclic imports.

## Deferred / linkage
- The "document the addressing rule in the stability contract" acceptance is **deferred to FEAT-13** — do NOT write contract docs here. The rule is recorded on the feature; keep the ref. Out of scope for this task.

## Acceptance (US2 + US3 wording)
- `sq tree 13`, `sq list --parent 13`, `--parent 13`, `--ref 13`, `ref add 13`/`ref rm 13`, `sq role/skill/operator` targets, subtask `--story` — **all accept both full ID and bare number** (US2: copy-paste works on every command).
- Unknown-item errors name both accepted forms consistently (US3 wording).
- `sq tree 13` no longer silently matches nothing.

## Tests (per CLAUDE.md: service-level + CLI smoke across the WHOLE inventory)
- CLI smoke covering **every surface in the inventory above** with both forms (bare number + full ID), plus an unknown-item case asserting the both-forms error wording.
- Service-level coverage for the type-less resolve adoption where it has logic worth asserting.
- `uv run sq check` must stay clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 47 add-subtask "<title>"`; track with `sq task 47 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Wire all ID-accepting paths through the resolver | US2 |
| ST2 | Done |  | Uniform unknown-item error wording mentioning both accepted forms everywhere | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Wire all ID-accepting paths through the resolver

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a user copy-pasting an ID from a comment or tree, I want it accepted by every command including tree, --parent and ref add, so that handoffs never need manual reformatting
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Wire tree root, --parent, --ref, ref add/rm, list --parent, role/skill/operator targets, subtask --story through the resolver.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Uniform unknown-item error wording mentioning both accepted forms everywhere

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a user who typos the type, I want sq to tell me 13 is a feature instead of silently obeying, so that I never act on the wrong item
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Make unknown-item error wording uniform across every ID-accepting surface: each surface names both accepted forms (full ID and bare number) consistently, so the error is the same everywhere regardless of which command produced it (US3 wording).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T14:18:22Z] Elias Python:
  - Implementation complete. All surfaces wired through the shared resolver:
  - - _cli/_create.py: --parent and --ref via resolve_item_id_any; guide --parent also wired
  - - _cli/_items.py: update --parent via resolve_item_id_any; ref add/rm via resolve_item_id_any (split_ref guards kind); add-subtask/update-subtask --story via resolve_local_id
  - - _cli/_main.py: tree root_id and list --parent via resolve_item_id_any
  - - _cli/_role.py: regen/rm via resolve_item_id_typed(ROLE)
  - - _cli/_skill.py: add --parent via resolve_item_id_any; show/regen/rm via resolve_item_id_typed(SKILL)
  - - _cli/_operator.py: rm via resolve_item_id_typed(OPERATOR)
  - Extra surface found beyond inventory: skill add --parent (was raw) — wired.
  - Tests: 9 new CLI smoke tests covering every surface in the inventory; one existing assertion updated for improved tree error wording.
  - Gates: uv run pytest (259 passed), pyright clean, ruff clean. @tech-lead please review.
- [2026-06-11T14:23:14Z] Paul Reviewer:
  - Review REV-48: ChangesRequested. F2 (medium) lands across the swept surfaces — unify the unknown-item 'both forms' wording across resolve_item_id_any branches. Adoption sweep itself is correct and well-tested. Staying InReview. @python-dev see REV-48 findings.
<!-- sq:discussion:end -->
