---
id: TASK-46
sequence_id: 46
type: task
title: Shared item-address resolver + typed-surface type enforcement
status: Done
parent: FEAT-19
author: tech-lead
assignee: python-dev
priority: high
refs:
- TASK-47:blocks
subentities:
- local_id: ST1
  title: 'Shared resolver: typed (live-DB type check) + type-less variants, both-forms
    unknown-item errors'
  status: Done
  story: US1
- local_id: ST2
  title: Close the silent type-mismatch hole on the item-verb surface (13 is FEAT-000013,
    not a task)
  status: Done
  story: US3
created_at: '2026-06-11T13:59:31Z'
updated_at: '2026-06-11T14:32:38Z'
---
<!-- sq:body -->
## Goal
One shared item-address resolver in `_cli/_common.py` (next to `resolve_item_id`/`resolve_slug_or_raise` — one idiom), plus **typed-surface type enforcement** against the live DB. This is the foundation; TASK-47 (the adoption sweep) is blocked on it.

## Background — the current hole
`resolve_item_id` (`src/squads/_cli/_common.py:231`) normalizes `13` → `TASK-000013` purely by prefix string-munging — it never checks the live DB. `SquadsDB.get`'s `_seq()` (`src/squads/_models/_index.py:57`) then looks up by **bare sequence ignoring type**, so `sq task 13 show` silently displays **FEAT-13**. A full ID with a wrong prefix already errors at the string layer, but a bare number that resolves to a *different* type's item slips straight through. Decision on record: **type mismatch is an ERROR** (op-pierre, 2026-06-10).

## What to build
1. **Resolver(s) in `_cli/_common.py`** — keep the single idiom alongside `resolve_item_id`/`resolve_slug_or_raise`:
   - **Typed resolve** (for `sq <type> <n>`): resolve the token to a full id, then verify the resolved item's **ACTUAL type against the live DB**. On mismatch raise `SquadsError` naming the real item and type, e.g. `13 is FEAT-000013 (feature), not a task`. A full ID whose prefix contradicts the command stays an error (existing behaviour, keep the wording aligned).
   - **Type-less resolve** (consumed by TASK-47 for tree root / ref targets / `--parent`): a bare number resolves to **whatever item owns that sequence**, no type word required. Land the function here so the sweep can wire it in; it needs DB access.
   - **Unknown-item errors mention BOTH accepted forms** (full ID and bare number).
2. Resolving against the live DB means these helpers need the `Service`/`SquadsDB` — thread it through cleanly (mirror how `resolve_slug_or_raise(slug, svc)` already takes `svc`). Don't reach past the service layer.
3. Wire the **item-verb argument** (the one surface already going through `resolve_item_id`) onto the new typed resolve so `sq task 13 show` errors instead of showing FEAT-13. (Broad adoption across the other surfaces is TASK-47.)

## Constraints
- Additive for valid invocations: accepting both forms must break no existing correct call; only the silent type-mismatch path changes (now errors — intended).
- Raise `SquadsError` (CLI `@handle_errors` → clean message + exit 1), never bare exceptions.
- Keep the import graph acyclic; strict `pyright` + `ruff` clean.

## Acceptance (US1 + US3)
- `sq <type> <n>` accepts `13`, `000013`, `TYPE-000013` (US1) and errors on type mismatch naming the actual item+type, e.g. `13 is FEAT-000013 (feature), not a task` (US3).
- The `sq task 13 show` silent-obey hole is closed.
- Unknown-item errors mention both forms.

## Tests (per CLAUDE.md: service-level + CLI smoke)
- Extend the existing `test_resolve_item_id` in `tests/test_cli.py:232` as the seed — add type-mismatch-against-live-DB cases and both-forms cases.
- CLI smoke: create a feature, then assert `sq task <feat-num> show` errors with the "is … (feature), not a task" message; assert the valid both-forms paths succeed.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 46 add-subtask "<title>"`; track with `sq task 46 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Shared resolver: typed (live-DB type check) + type-less variants, both-forms unknown-item errors | US1 |
| ST2 | Done |  | Close the silent type-mismatch hole on the item-verb surface (13 is FEAT-13, not a task) | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Shared resolver: typed (live-DB type check) + type-less variants, both-forms unknown-item errors

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a CLI user, I want to name an item by full ID or bare number in any command, so that one habit works everywhere
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Close the silent type-mismatch hole on the item-verb surface (13 is FEAT-13, not a task)

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a user who typos the type, I want sq to tell me 13 is a feature instead of silently obeying, so that I never act on the wrong item
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T14:08:09Z] Elias Python:
  - Implementation complete. Two new resolver functions in `src/squads/_cli/_common.py` alongside the existing `resolve_item_id`/`resolve_slug_or_raise` idiom:
  - `resolve_item_id_typed(token, item_type, svc)` — lexical resolution + live DB type check (one `store.load()` per call). Accepts 35 / 000035 / TASK-000035. Bare number that belongs to a different type raises e.g. '2 is FEAT-000002 (feature), not a task'. Unknown item errors name both forms (full ID and bare number). Full ID with wrong prefix preserved as before.
  - `resolve_item_id_any(token, svc)` — type-less: resolves bare number or full ID to whatever item owns that sequence. Mismatched prefix on a full ID raises an error naming the actual item. Ready for TASK-47's adoption sweep.
  - Wired `resolve_item_id_typed` into `_cli/_items.py`'s `_resolve` callback (line ~64) — the one item-verb surface. `sq task 13 show` now errors when 13 is a feature; closes the silent type-mismatch hole.
  - Tests: `test_resolve_item_id_typed` (service-level), `test_resolve_item_id_any` (service-level), `test_item_verb_type_enforcement` (CLI smoke) in tests/test_cli.py. All gates green: 250 passed, 1 skipped; pyright 0 errors; ruff clean.
  - @tech-lead ready for review.
- [2026-06-11T14:23:14Z] Paul Reviewer:
  - Review REV-48: ChangesRequested. F1 (medium) lands here — resolve_item_id_typed full-ID branch must do the DB lookup and emit '<tok> is <id> (<type>), not a <type>' (same as the bare-number branch) instead of 'not a task (expected TASK-…)'. Also F2 unknown-item wording consistency. Staying InReview. @python-dev see REV-48 findings.
<!-- sq:discussion:end -->
