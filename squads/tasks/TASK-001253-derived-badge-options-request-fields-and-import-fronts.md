---
id: TASK-1253
sequence_id: 1253
type: task
title: Derived badge options, request fields and import fronts
status: InReview
parent: FEAT-1249
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-1250:implements
- MILE-1241:targets
- TASK-1251:depends-on
- TASK-1252:depends-on
description: create/update/list/tree flags from declared fields, generic requests,
  list column, import add-<kind> and selectors
subentities:
- local_id: ST1
  title: Derived flags on create and item update
  status: Done
  story: US1
- local_id: ST2
  title: Derived filters on list and tree
  status: Done
  story: US1
- local_id: ST3
  title: List badge column from the spec
  status: Done
  story: US1
- local_id: ST4
  title: Derived-flag and import-key collisions
  status: Done
  story: US6
- local_id: ST5
  title: Import fronts and selectors per declared kind
  status: Done
  story: US3
created_at: '2026-10-29T19:55:08Z'
updated_at: '2026-10-29T21:32:00Z'
---
<!-- sq:body -->
## Goal

Item-level badge options, request fields and import keys are derived from the declared fields and kinds, with no field or kind named in code (ADR-1250 sections 2 and 4; FEAT-1249 US1 item level, US3).

## Scope

- `create`, item `update`, `list` and `tree` derive `--<code>`, `--no-<code>` and `--min-<code>` from the declared fields at parameter resolution; the static `--priority`, `--no-priority`, `--min-priority`, the hidden-flag refresh and the `priority` request fields go.
- `--set`, `--unset`, `--badge`, `--min-badge` and `--sort` refuse an undeclared code naming the declared ones.
- The `list` table's one badge column follows the spec.
- Spec load refuses a derived flag or import key that collides with a fixed name on its surface (section 6, third bullet).
- `sq import` takes `add-<kind>` and the `<kind>` selector for every declared kind, `add-sub` with `maps_to` and `fields`, and badge fields by code in `fields` / `unset_fields` on `create` and `update`.

Sub-entity options (`add-<kind>`, `<kind> <k> update`, the mapping option) are the next task's, which runs beside this one.

## Expected files

- `src/squads/_cli/_create.py`, `_cli/_main.py`, `_cli/_common.py`, `_cli/_items.py` (item `update` only, around the priority help and the update command)
- `src/squads/_api/_dto/_item_writes.py` (item create and update requests only)
- `src/squads/_services/_items.py`, `_services/_item_write_ops.py` (item create and update handlers only)
- `src/squads/_services/_item_dto.py` (the list column definition only), `src/squads/_cli/_render/_items.py` if the header needs it
- `src/squads/_services/_import_model.py`, `_services/_import.py`
- `src/squads/_workflow/_validity.py` (derived-flag and import-key collisions)
- `src/squads/_tui/_filter.py` if it reads the priority filter
- `tests/meta/test_priority_kwarg_goes_through_declared_field_gate.py` (goes or is rewritten with the static flag)
- `tests/cli/test_create.py`, `test_item_verbs.py`, `test_list.py`, `test_tree.py`, `test_import.py`, `test_override.py`

## Runs beside

The mapping, labels and wire-shape task. Shared files, different functions: `_cli/_items.py` (this task the item `update` command; that task `_register_add` / `_register_update` for kinds), `_api/_dto/_item_writes.py` (item requests here; sub-entity requests there), `_services/_item_write_ops.py` (item create/update here; sub-entity handlers there), `_services/_item_dto.py` (the column list here; the sub-entity projection there). Agree the merge order at dispatch; the second rebases.

## Tests (about 14 new)

Listed per subtask, on the override test squad unless the case is the bundled spelling.

## Size

L.

## Working rules

- Work in your own git worktree off `origin/release/0.19`. At most two Python developers run in parallel on this feature; the "Runs beside" line says who shares files with you.
- Gates before handback: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, the tests your diff selects plus the floor (`tests/meta`, `tests/cli`, `tests/check` for any change under `_specs/`, `_rendering/templates/` or `_cli/`), and `sq check` clean for the items you touched. The main loop runs the full suite.
- Tests follow ADR-1172 as amended: CLI surface cases with `@pytest.mark.covers(...)`, one case per behaviour plus its boundary refusals, no unit tests on internal functions, no shape tables. A check rule gets its `@pytest.mark.breaches(...)` case. Once the override test squad exists, the override-side cases run on it rather than on a squad built inline. Falsify each new test once (break the code, see it red, restore) and say so in the handback.
- Any edit under `src/squads/_rendering/templates/` runs `python scripts/gen_template_manifest.py` in the same change (the working version is 0.19.0, so the regen writes the 0.19.0 key).
- Comments and docstrings: one or two sentences, present tense, no ticket IDs, release versions or history. No ticket IDs or process words in test names.
- No bundled type, kind, field, collection, status or alias literal in code outside `_specs/` and `_migrations/`: derive it from the active spec (ADR-1250 section 1).
- CHANGELOG and adopter docs are the tech writer's. Report every adopter-visible change (what an adopter now does or sees differently, and why) in your handback comment; do not edit `CHANGELOG.md` or `docs/`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1253 add-subtask "<title>"`; track with `sq task 1253 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Derived flags on create and item update

<!-- sq:subtask:ST1:body -->
`sq create <type>` takes `--<code>` for each field the type declares; `sq <type> <n> update` takes `--<code> <value>` for each declared field and `--no-<code>` for each optional one. A code with underscores gets a dashed flag. The static `--priority` / `--no-priority`, `_priority_help`, `_declares_priority` and the hidden-flag refresh go. `ItemCreateRequest.priority`, `ItemUpdateRequest.priority` and `clear_priority` go; values travel in the generic fields map and its unset list.

Expected: on the override squad `create initiative --urgency high` and `initiative 2 update --urgency low` / `--no-urgency` work, and `--priority` / `--no-priority` are unknown options (Click, exit 2). A bundled squad still takes `--priority`, derived.

Tests (3): derived create and update flags with `--no-<code>` on the override squad; `--priority` unknown, exit 2, on the override squad; a field code with an underscore gets a dashed flag.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Derived filters on list and tree

<!-- sq:subtask:ST2:body -->
`sq list` and `sq tree` take `--<code> <value>` for each field some non-roster type declares, and `--min-<code> <value>` for a field on an ordered collection; each means exactly `--badge <code>=<value>` / `--min-badge <code>=<value>`. The static `--priority` / `--min-priority` go. `--set`, `--unset`, `--badge`, `--min-badge` and `--sort` refuse a code no non-roster type declares, exit 1, naming the declared codes.

Expected: on the override squad `list --urgency high` and `list --min-urgency medium` match the `--badge` forms; `list --priority high` is an unknown option; `list --badge priority=high` exits 1 naming `urgency` and `impact`.

Tests (3): derived list and min flags equal the generic forms (one case on `list`, one on `tree`); generic forms refuse an undeclared code naming the declared ones.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — List badge column from the spec

<!-- sq:subtask:ST3:body -->
`sq list` shows one badge column: the first field on an ordered collection in type declaration order, headed by that field's label; none when no type declares a field. The fixed `Priority` column definition goes.

Tests (2): the override squad's list header is the `urgency` field's label; a squad declaring no field shows no badge column.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Derived-flag and import-key collisions

<!-- sq:subtask:ST4:body -->
Spec load refuses a derived name that collides with a fixed name on its surface, naming the surface and the fixed name: a field code or a target kind against the fixed options of the command it derives onto (`create`, `update`, `add-<kind>`, `<kind> <k> update`, `list`, `tree`), and a kind or field whose import key equals a fixed key of its op. Uses the target-kind method from the spec-grammar task.

Tests (2): a field code equal to a fixed option (for example `assignee` on `update`, or `status` on `list`); a field whose import key equals a fixed key of `add-<kind>`.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Import fronts and selectors per declared kind

<!-- sq:subtask:ST5:body -->
`sq import` follows the CLI: `add-<kind>` for every declared kind is `add-sub` with `kind` set, taking `add-sub`'s keys, each declared field as a top-level key under its code, and the target kind's name as a key when the kind maps. `add-sub` takes the mapping as `maps_to` and fields in `fields`. The `"<kind>": "<local-or-handle>"` comment selector exists for every declared kind; `sub: [kind, local-or-handle]` stays. `create` and `update` take badge fields by code in `fields` and `unset_fields`, with no key named after a field. An op or selector for an undeclared kind is unknown, and the refusal names the declared `add-<kind>` ops. The fixed `add-story` / `add-subtask` / `add-finding` models go; messages use the declared label and plural with no article chosen in code.

Expected: on the override squad `{"op": "add-outcome", ...}`, `{"op": "add-action", "outcome": "OC1", "impact": "..."}` and an `"outcome"` selector work; `add-story` is refused naming `add-outcome` and `add-action`. A bundled squad's existing import files run unchanged.

Tests (4): `add-<kind>` with field and target-kind keys plus the kind selector on the override squad; an undeclared op refused naming the declared ops; `add-sub` with `maps_to` and `fields`; `create` and `update` with `fields` / `unset_fields`.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T21:31:59Z] `python-dev` Elias Python:
  - @manager Implemented in the worktree branch `worktree-agent-a7714e69d7a42db55`, commit f6454033 (off origin/release/0.19).
    
    Gates: pyright 0 errors, ruff check and format clean, `pytest -n 4 tests/meta tests/cli tests/regressions tests/check` 1742 passed. Each new test was falsified once (break the code, see it red, restore).
    
    Adopter-visible changes (draft changelog lines):
    - BREAKING: the static `--priority`, `--no-priority` and `--min-priority` options are gone. `create`, `<type> <n> update`, `list` and `tree` now take `--<field>` for each declared field (`--<field>`/`--no-<field>` on update, `--min-<field>` on list and tree for an ordered field). A bundled squad still sees `--priority` because it declares a `priority` field; a squad without that field gets "No such option".
    - A field code with underscores gives a dashed flag (`work_size` is `--work-size`).
    - `list` and `mine` show one badge column: the first field on an ordered collection, headed by its label, and none when no type declares one.
    - `--badge`, `--min-badge` and `--sort` name the declared fields when refused; `update --set/--unset` refusals now list the declared badge fields beside the attributes.
    - `sq import`: `add-<kind>` exists for every declared kind (fields and the target kind's name as top-level keys), the `"<kind>": "<local>"` comment selector exists for every declared kind, an unknown op names the declared `add-<kind>` ops. BREAKING: `add-sub` takes the mapping as `maps_to` (was `story`).
    - Spec load refuses a field code, target kind or kind whose derived flag or import key equals a fixed option or key of its command or op.
    
    Per subtask:
    - ST1 create and update derive flags (`_cli/_field_options.py`, new); request fields `priority` and `clear_priority` removed; update routes values through `set_attributes`/`unset_attributes`. Tests: derived create/update flags with `--no-`, `--priority` unknown (exit 2), dashed flag for an underscored code, `--severity`/`--no-severity` on a bundled bug.
    - ST2 list and tree derive `--<code>` and `--min-<code>`. Tests: derived equals generic on list and on tree, generic forms refuse undeclared codes naming `urgency, work_size` (the fixture's declared type fields; `impact` is a kind field, not a filterable item field), bundled `--severity`/`--min-severity`.
    - ST3 `list_columns(spec)` and `mine_columns(spec)` replace the fixed tuples. Tests: override header is `Urgency`; a squad with no field shows no badge column.
    - ST4 `_workflow/_derived_names.py` (tables of fixed options and import keys, plus a `tests/meta` guard holding them to the live commands and event models). Tests: `force` and `sort` field codes; a kind field `handle` against the add-<kind> import keys. A code already refused as a reserved key is not reported twice.
    - ST5 `parse_events` takes the spec and folds `add-<kind>` and the kind selectors to the generic events at parse time; the per-kind event models are gone; per-op counts keep the op the file wrote. Tests: add-<kind> with field and target-kind keys plus the kind selector, unknown op/selector, add-sub with maps_to and fields, create/update with fields/unset_fields.
    
    Notes for the merge and follow-ups:
    - Test infra: the `invoke` fixture now computes reached pairs with the cwd squad's spec bound as the active spec (otherwise a call on the override squad reached nothing); `tests/meta` reference-verbs guard knows the derived update options.
    - Removed `tests/meta/test_priority_kwarg_goes_through_declared_field_gate.py` (its subject no longer exists) and the two dead allow-list entries in the field-code and kind-literal guards.
    - Minimal docs edit forced by a guard: `docs/adoption.md` `add-sub` row now lists `maps_to` instead of `story`. The tech writer still owes the import reference (add-<kind> rows are now per declared kind), the `--priority` mentions in docs, and the `--set` refusal text.
    - Left for TASK-1254: the `story=` keyword of `_add_block_model`/`_add_block_core`/`add_block` (import passes `event.maps_to` to it), sub-entity wire/row keys, the "a initiative" article in `require_settable`'s message, and the `maps_to_parent` target-kind flag registrars (the collision check already covers `--<target-kind>` and `--no-<target-kind>`).
    - Not touched: TUI/VS Code clients (the TUI filter has no priority read); tree text rendering and `ItemRow.priority`/`severity`/tree node `priority` stay for the wire-shape task.
<!-- sq:discussion:end -->
