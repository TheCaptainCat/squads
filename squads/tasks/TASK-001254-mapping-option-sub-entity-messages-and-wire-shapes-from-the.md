---
id: TASK-1254
sequence_id: 1254
type: task
title: Mapping option, sub-entity messages and wire shapes from the spec
status: Done
parent: FEAT-1249
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-1250:implements
- MILE-1241:targets
- TASK-1251:depends-on
- TASK-1252:depends-on
description: --<target-kind> option and labels, spec-worded messages, JSON shapes
  by badge code and maps_to, render context
subentities:
- local_id: ST1
  title: Mapping option named after the target kind
  status: Done
  story: US4
- local_id: ST2
  title: Clear flags for optional sub-entity fields
  status: Done
  story: US1
- local_id: ST3
  title: Messages and help from the spec
  status: Done
  story: US5
- local_id: ST4
  title: Wire shapes by badge code and maps_to
  status: Done
  story: US7
- local_id: ST5
  title: Template render context for fields and mapping
  status: Done
  story: US7
created_at: '2026-10-29T19:55:09Z'
updated_at: '2026-10-30T06:39:12Z'
---
<!-- sq:body -->
## Goal

Sub-entity options, labels and messages read in the declared vocabulary, and every `--json`, HTTP and render shape carries values by badge code and mapping, with no bundled field name as a key (ADR-1250 sections 2, 3 and 7; FEAT-1249 US1 sub-entity level, US4, US5 messages, US7 in Python).

## Scope

- `add-<kind>` and `<kind> <k> update`: the mapping option named after the target kind, `--no-<code>` for optional fields on update, help listing collection codes.
- Labels and messages: mapping column header, show and head label, not-found and validator messages from the target kind's label and `local_prefix`; every message uses the declared label and plural with no article chosen in code.
- Wire: item rows, tree and graph nodes, sub-entity objects, display and the sub-entity request fields; the TUI reads the new shapes.
- Render context: the sub-entity head and item templates take the declared fields as a list and the mapping as a pair.

The VS Code client moves to the new shapes in its own task (TypeScript), after this one.

## Expected files

- `src/squads/_cli/_items.py` (`_register_add`, `_register_update` and the sub-entity command bodies)
- `src/squads/_api/_dto/_items.py`, `_api/_dto/_tree.py`, `_api/_dto/_graph.py`, `_api/_dto/_item_writes.py` (sub-entity requests only)
- `src/squads/_services/_item_read_dto.py`, `_item_dto.py` (the sub-entity projection), `_refs.py`, `_subentities.py`, `_validators.py`, `_item_write_ops.py` (sub-entity handlers)
- `src/squads/_discussion.py`, `src/squads/_cli/_render/_subentities.py`, `_cli/_render/_items.py`
- `src/squads/_tui/_reader.py` and the TUI modules that read a sub-entity label or `priority`
- `src/squads/_rendering/templates/subentities/head.md.j2`, `templates/items/*.md.j2` that read a badge, `templates_manifest.json` (regen)
- `tests/cli/test_subentity_verbs.py`, `test_show.py`, `test_tree.py`, `test_graph.py`, `test_list.py`, `test_check.py`, `tests/check/` (the mapping rule), the goldens and `tests/meta` DTO guards

## Runs beside

The badge-options and import task. Shared files, different functions: `_cli/_items.py`, `_api/_dto/_item_writes.py`, `_services/_item_write_ops.py`, `_services/_item_dto.py` (see that task). Agree the merge order at dispatch; the second rebases.

## Tests (about 13 new, plus golden updates)

Listed per subtask, on the override test squad unless the case is the bundled spelling. Golden and `--json` fixture updates are expected and are not new cases.

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

_Add with `sq task 1254 add-subtask "<title>"`; track with `sq task 1254 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Mapping option named after the target kind

<!-- sq:subtask:ST1:body -->
The mapping option is named after the target kind (the spec method from the spec-grammar task): `add-<kind>` takes `--<target-kind> <local-or-id>`, `<kind> <k> update` takes `--<target-kind>` and `--no-<target-kind>`. Its help, the mapping column header, the show and head label and the not-found message name the target kind and take the prefix from its `local_prefix` ("outcome OC9 not found in INI-2", "as `OC<n>`"). `subentity_mapping` checks each mapping against the parent's sub-entities and names the target kind. The sub-entity request fields `story` / `clear_story` become `maps_to` / `clear_maps_to`. The TUI's sub-entity labels come from the target kind.

Expected: on the override squad `job 3 add-action "..." --outcome OC1` maps, `action 1 update --no-outcome` clears, `--story` is an unknown option; a bundled squad still takes `--story`, derived from kind `story`.

Tests (4): add and update with `--outcome` / `--no-outcome` and `--story` unknown on the override squad; the not-found message names the target kind and prefix; help, column header and show label name the target kind; `subentity_mapping` breach naming the target kind (`@pytest.mark.breaches`).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Clear flags for optional sub-entity fields

<!-- sq:subtask:ST2:body -->
`<kind> <k> update` takes `--no-<code>` for each optional field the kind declares (`add-<kind>` and update already derive `--<code>`). A code with underscores gets a dashed flag.

Tests (1): on the override squad, `action <k> update --no-impact` clears the field and the field is gone from the entry.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Messages and help from the spec

<!-- sq:subtask:ST3:body -->
Messages from the spec: every refusal and report names the declared label and `plural` and is phrased so no article is chosen in code ("a initiative" and "storys" cannot occur). The supersession validator message names the declared supersession ref kind instead of `supersedes`. `add-<kind> --help` lists the collection codes for each field as `create --help` does.

Tests (3): on the override squad, a sub-entity refusal that used to choose an article reads correctly for a vowel-initial label with an irregular plural; the supersession message names the override's kind; `add-action --help` lists the `impact` codes.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Wire shapes by badge code and maps_to

<!-- sq:subtask:ST4:body -->
Wire shapes (ADR-1250 section 7): item rows (`list`, `show`, `create`, `mine`) drop `priority` and `severity` as core keys, a stored badge value appears at the top level only when the file stores it, and `badges` carries every declared field; tree and graph nodes drop `priority`; sub-entity objects carry `local_id`, `title`, `status`, `assignee`, `maps_to`, `deferred_to`, then each stored attribute flat, then `body`, `badges`, `discussion`, `display`, with `maps_to` and `deferred_to` always present and `null` when unset, and no `severity`, `story` or `extra`; the row's `display.story` becomes `display.maps_to`. The daemon's routes serve the same DTOs. The TUI reads `badges`, `display` and `maps_to`. The `tests/meta` DTO guard still holds every field JSON-native.

Tests (3): a sub-entity object's key set and order with `maps_to` null and set; a tree node has no `priority` key and carries the field in `badges` on the override squad; an item row on the override squad has `urgency` at the top level only when stored. Golden updates as needed.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Template render context for fields and mapping

<!-- sq:subtask:ST5:body -->
Render context: the sub-entity head and the item templates receive the declared fields as a list of `{code, label, badge}` and the mapping as `{label, value}` (the target kind's label and the `maps_to` value). The names `severity`, `severity_label` and `story` go, and an item's `.priority` / `.severity` and a sub-entity's `.story` / `.extra` are no longer in the context, so an override template reading one fails under `StrictUndefined`. Regenerate the manifest.

Expected: a bundled squad's heads change at most in the mapping line's label, now taken from the target kind (report the change for the CHANGELOG); the override squad's heads show `urgency` / `impact` and the mapping under the target kind's label.

Tests (2): an action's head on the override squad shows its field and the mapping labelled `outcome`; an override head template reading `severity` fails to render, naming the undefined name.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T21:40:58Z] `python-dev` Elias Python:
  - - @manager Handback for TASK-1254, ready for review. Branch `worktree-agent-acc1e00b70709a963` (worktree `.claude/worktrees/agent-acc1e00b70709a963`), commits 2efe5348 and a2e8165e on top of origin/release/0.19. Gates: pyright 0 errors, ruff check and format clean, `pytest -n 4 tests` 1738 passed (twice; `tests/tui` does not exist in this tree).
    
    Per subtask
    - ST1 mapping option: `--<target-kind>` / `--no-<target-kind>` on `add-<kind>` and `<kind> <k> update`, derived from `mapping_target_kind` (`--outcome` on a job's action, `--story` on a subtask). Help, the summary column header, the show line (`outcome: OC1`) and the not-found message ("outcome OC9 not found in INI-8") name the target kind and its `local_prefix`. Request fields are `maps_to` / `clear_maps_to`. The `subentity_mapping` check names the target kind. Falsified: option name forced to a literal, not-found text forced to a literal, validator text forced to a literal.
    - ST2 clear flags: `--no-<code>` per optional field on update (dashed for underscores), new `unset_fields` on `SubentityUpdateRequest`, service refuses a required or undeclared code. Falsified by removing the flag params.
    - ST3 messages and help: sub-entity refusals use the declared kind name or plural with no article ("applies to action sub-entities in a deferred status", "has type X, which does not host <plural>", "has no <host> parent; set one before mapping <kind> to <id>"); `supersedes_incoming` names the declared supersession kind(s) ("no incoming replaces edge found"); `add-<kind> --help` lists each field's codes ("Impact: large|small."), as does update. Falsified (article text, supersession kind).
    - ST4 wire: item rows drop `priority`/`severity` as core keys (a stored value is a flat attribute after `id`); tree and graph nodes drop `priority`; sub-entity objects, list entries and `subentities` rows are `local_id, title, status, assignee, maps_to, deferred_to, <attributes flat>, [body, badges, discussion,] display`, with `display.maps_to` replacing `display.story`. `SubentityRow` adapter removed. Whole-JSON assertion for an action's `show --json`; key-order assertions for the list entry, item row and tree node. Falsified (order, extra key on row, extra key on tree node).
    - ST5 render context: the head template receives `fields` (list of code/label/badge) and `mapping` ({label, value} or none); `set_head` takes `field_values` and `mapping`. Bundled template regenerated (0.19.0 key). The head has no live caller (only the frozen 0.3 migration, updated to the new keywords), so its two tests call the renderer directly under tests/regressions. MANUAL text of the 0.19 runner now names `fields` and `mapping` and `item.badge_value('<code>')`; the migrate-help document in tests updated. Falsified (label, undefined-name guard).
    
    Test infrastructure change (needed so override-squad calls can carry covers markers): `tests/conftest.py::invoke` folds a call with the squad's own spec, and `tests/_cli_surface.reached_pairs` takes `known` (the bundled tree's pairs, read outside any squad) so a parameter derived from the squad's vocabulary counts as nothing and the call reaches the bare pair. TASK-1251's migration test now uses `--outcome`. New override-squad tests: 10 in `test_subentity_verbs.py`, 2 in `test_check.py`, 1 each in `test_list.py` and `test_tree.py`, 2 in tests/regressions. Existing goldens updated for the new shapes; the two dead entries in the bundled-kind-literal guard's allow-list were removed.
    
    Adopter-visible changes (draft changelog lines)
    - BREAKING (wire, `--json`, daemon): a sub-entity object has `maps_to` (always present, null when unset) in place of `story`; `severity` and `extra` are gone, every stored field sits flat after `deferred_to`; list entries and `subentities` rows have the same shape. `display.story` is `display.maps_to`; `sq <type> <n> <kind> <k> show --json` adds `display.maps_to_kind` (the target kind's name).
    - BREAKING (wire): item rows no longer carry `priority`/`severity` as always-present keys; a stored badge value appears at the top level only when the file stores it, and `badges` carries every declared field. Tree and graph nodes no longer carry `priority`; read `badges`.
    - `--<target-kind>` replaces a fixed `--story` spelling (still `--story` in a squad whose parent hosts `story`); `update` gains `--no-<field-code>` for optional sub-entity fields; field flags with underscores are dashed.
    - Sub-entity messages and the `subentity_mapping` / `supersedes_incoming` check messages use the declared vocabulary. The mapping column header is the target kind's title (`Story` in a bundled squad, unchanged). Bundled heads are unchanged except the mapping line label, which is the target kind's title instead of `Implements` (not reachable by a command today).
    - Template context: the sub-entity head no longer receives `severity`, `severity_label`, `story`; an override template reading them fails under StrictUndefined.
    
    VS Code-facing shape changes (TypeScript task)
    - Sub-entity: read `maps_to` (not `story`), field values from `badges` (or the flat key by code), no `severity`/`extra`; `display.story` -> `display.maps_to`; mapping label from `display.maps_to_kind` on a shown sub-entity, and the summary column header for lists. Item rows: no `priority`/`severity` keys, use `badges` and `display.badges`. Tree/graph nodes: no `priority`, use `badges`. Wire-key order is stable as listed above.
    
    Left / notes
    - `tests/cli` markers on override-squad tests reach only the pairs the bundled tree has (e.g. `<type> add-<kind> TITLE`, `<type> <kind> update` bare); the flags `--outcome`/`--no-impact` themselves cannot be declared as pairs.
    - Articles remain in item-type messages outside the sub-entity area (`_items.py`, `_base.py` priority gate, `_metadata.py`, `_retype.py`, `_workflow/_models.py parent_hint`); they belong to the badge-options/item side or are item-type, not sub-entity, text. Say if you want them swept here.
    - Import `event.story` is untouched (sibling task's fronts); only the two `_add_block_*` call sites now pass `maps_to=`. Expect a trivial rebase conflict there.
    - `sq check` on the repo squad is clean.
- [2026-10-29T22:00:43Z] `reviewer` Paul Reviewer:
  - Reviewed in REV-1259: changes requested, low findings F16 to F19 (tests, covers bare pairs, fixed articles, ADR-1250 section 7 wire and context gaps). The behaviour is sound on both squads (driven).
- [2026-10-30T06:39:11Z] `manager` Catherine Manager:
  - Reviewed and verified in REV-1259 (Approved 2026-10-30); full suites green at release/0.19. Accepted Done under the operator delegation for this drive.
<!-- sq:discussion:end -->
