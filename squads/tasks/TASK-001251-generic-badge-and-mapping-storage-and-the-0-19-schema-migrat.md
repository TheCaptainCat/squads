---
id: TASK-1251
sequence_id: 1251
type: task
title: Generic badge and mapping storage, and the 0.19 schema migration
status: Draft
parent: FEAT-1249
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-1250:implements
- MILE-1241:targets
description: Badge values and the mapping stored flat under declared or neutral keys;
  schema 0.19 runner on a fixture corpus
subentities:
- local_id: ST1
  title: Item badge values stored as attributes
  status: Todo
  story: US6
- local_id: ST2
  title: Flat sub-entity entries with maps_to
  status: Todo
  story: US6
- local_id: ST3
  title: Stored-key collision rule at spec load
  status: Todo
  story: US6
- local_id: ST4
  title: Schema 0.19 runner on a fixture corpus
  status: Todo
  story: US6
created_at: '2026-10-29T19:55:06Z'
updated_at: '2026-10-29T19:55:29Z'
---
<!-- sq:body -->
## Goal

Badge values and the sub-entity mapping are stored under their declared or neutral keys, on items and on sub-entity entries, and an existing squad reaches schema 0.19 through `sq migrate up` (ADR-1250 sections 6 and 8, FEAT-1249 US6).

This task changes storage and the in-memory models only. The `--json` and render shapes stay as they are today, fed from the generic accessors; the wire and template-context change is a later task of this feature. Grammar renames (`maps_to_parent`, `subentity_mapping`, `status_rollup`) and the target-kind derivation are in the task that runs beside this one.

## Scope

- `Item.priority` and `Item.severity` go; `priority` and `severity` leave `CORE_KEYS`; every badge value lives in `Item.attributes`, read and written through `badge_value(code)` / `set_badge_value(code, value)`.
- A sub-entity entry has the core keys `local_id`, `title`, `status`, `assignee`, `maps_to`, `deferred_to`. `SubEntity.severity`, `SubEntity.story` and `SubEntity.extra` go; `SubEntity.attributes` holds every other key, declared field or unknown, and keeps unknown keys through every write and repair. `maps_to` is written only when set.
- One collision rule for stored keys at spec load (section 6, first two bullets): an item field code or attribute key against the item core keys, `path`, `prefix`, the row-added keys and the other fields of the type; a kind's field code against the sub-entity core keys, the keys `--json` adds to a sub-entity object (`body`, `badges`, `discussion`, `display`) and the other fields of the kind; a kind named `sub`. Derived-flag and import-key collisions belong to the badge-options task.
- `SCHEMA_VERSION` 0.19 and one runner, 0.17 to 0.19, in `_migrations/_registry.py`, with its `manual` step (section 8).

## Expected files

- `src/squads/_models/_item.py`, `_models/_subentity.py`, `_models/_attributes.py`, `_models/_index.py`, `_models/_schema.py`
- `src/squads/_migrations/_registry.py`, new `src/squads/_migrations/_v0_17_to_v0_19.py`
- `src/squads/_services/_items.py`, `_subentities.py`, `_refs.py`, `_item_read_dto.py`, `_item_dto.py`, `_validators.py`, `_import.py`, `_duplicate_ids.py`
- `src/squads/_discussion.py`
- `src/squads/_workflow/_validity.py` (the stored-key collision check only)
- `tests/fixtures/corpus/v0_17/` (new), `tests/cli/test_migrate.py`, `tests/cli/test_create.py`, `tests/cli/test_subentity_verbs.py`, `tests/cli/test_override.py`

## Runs beside

The spec-grammar task (aliases, neutral names, headings, generated text, override squad). Shared files: `_workflow/_validity.py` (different functions: this task the stored-key collision near the row-added keys, that task the alias check and the mapping clause), and line-level renames of `maps_parent_story` in `_services/_subentities.py`, `_services/_validators.py`, `_services/_item_dto.py`, `_discussion.py` and `_cli/_items.py`, where this task rewrites the adjacent `story` reads. Whichever merges second rebases; pyright finds any leftover name.

## Tests (about 10 new)

Listed per subtask. Existing `--json` and render goldens must pass unchanged: that is the proof the wire shape did not move.

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

_Add with `sq task 1251 add-subtask "<title>"`; track with `sq task 1251 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Item badge values stored as attributes

<!-- sq:subtask:ST1:body -->
`priority` and `severity` stop being item core keys and model slots. Every badge value lives in `Item.attributes` and is read and written through `badge_value` / `set_badge_value`; every reader of `.priority` / `.severity` moves to the accessor (`_services/_items.py`, `_refs.py`, `_item_read_dto.py`).

Expected: a bundled squad's item frontmatter is byte-identical to today (`priority: high` at the top level); a field declared by an override is stored the same way under its code; `--json` output is unchanged.

Tests (1): an override declaring a field `urgency` on a type, `create ... --set urgency=<code>` stores `urgency:` at the top level and `show --json` reports it in `badges`. The bundled case is held by the existing create and show goldens.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Flat sub-entity entries with maps_to

<!-- sq:subtask:ST2:body -->
A sub-entity entry is flat: core keys `local_id`, `title`, `status`, `assignee`, `maps_to`, `deferred_to`; every other key is an attribute in `SubEntity.attributes`. `severity`, `story` and `extra` go from the model; `maps_to` is the one typed mapping slot and is written only when set. The loose-spelling normaliser keeps dropping an empty field value and no longer builds `extra`. Callers that set or read the mapping (`_services/_subentities.py`, `_validators.py`, `_discussion.py`, `_item_dto.py`, `_import.py`) use `maps_to`; the `story` keys on request and response DTOs stay until the wire task renames them.

Expected: `add-finding --severity high` writes `severity: high` flat on the entry; `add-subtask --story US1` writes `maps_to: US1`; a hand-added unknown key on an entry survives an update of that entry and `sq repair`.

Tests (2): a flat field and `maps_to` written on the entry (read back with `show --json` and the file's frontmatter); an unknown key on an entry kept through `<kind> <k> update` and `repair`.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Stored-key collision rule at spec load

<!-- sq:subtask:ST3:body -->
Spec load refuses a stored-key collision, naming the key and what it collides with: an item field code or attribute key equal to an item core key, `path`, `prefix`, a row-added key or another field or attribute of the same type; a kind field code equal to a sub-entity core key, `body`, `badges`, `discussion`, `display` or another field of the same kind; a kind named `sub`. Checked against the active spec only. `extra` leaves the reserved set.

Tests (3, refusals at `sq workflow` or any command on an override): item field code equal to a core key; kind field code equal to `badges`; a kind named `sub`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Schema 0.19 runner on a fixture corpus

<!-- sq:subtask:ST4:body -->
`SCHEMA_VERSION` becomes 0.19, with one runner from 0.17 in `_migrations/_registry.py`. The runner walks every item file of every type, roster included, and rewrites only `subentities` entries: `story: X` becomes `maps_to: X`, each `extra` key moves to the entry's top level and `extra` goes, an empty `severity` is dropped. Item top-level keys, body bytes and markers are untouched. It scans first and refuses, exit 1 with nothing written, an entry holding both `story` and `maps_to`, or an `extra` key equal to a sub-entity core key or to a key already at the entry's top level, naming the item and the key. An entry with neither `story` nor `extra` stays byte-identical. The `manual` step lists the override spellings refused at load (`maps_parent_story`, `subtask_story_mapping`, the transform `milestone_rollup`), the removed template context names and their replacements per ADR-1250 section 7, and that reflog entries keep their recorded keys.

Fixture: a 0.17-shaped corpus under `tests/fixtures/corpus/v0_17/` carrying a subtask with `story`, a finding with `severity`, an entry with `extra`, an entry with an empty `severity`, and a roster item.

Tests (4): `migrate up` on the fixture rewrites the entries as above, leaves bodies and item keys byte-identical and rebuilds `.squads.json`; refusal on `story` plus `maps_to`; refusal on an `extra` key clashing with a top-level key; a second run leaves every file byte-identical.

This repository's own squad is migrated later, at the release cut (see the guards-and-suite task); do not run the runner on `squads/`.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
