---
id: TASK-1252
sequence_id: 1252
type: task
title: Spec-derived aliases, neutral grammar, headings and override squad
status: InReview
parent: FEAT-1249
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-1250:implements
- MILE-1241:targets
description: Aliases from the active spec, maps_to_parent and target kind, heading
  key, generated text from the spec, the override test squad
subentities:
- local_id: ST1
  title: Override test squad and its fixture
  status: Done
  story: US10
- local_id: ST2
  title: Root aliases from the active spec
  status: Done
  story: US2
- local_id: ST3
  title: Neutral grammar names and the target kind
  status: Done
  story: US4
- local_id: ST4
  title: Container heading key on sub-entity kinds
  status: Done
  story: US5
- local_id: ST5
  title: Generated agent text from the spec
  status: Done
  story: US5
created_at: '2026-10-29T19:55:07Z'
updated_at: '2026-10-29T21:10:20Z'
---
<!-- sq:body -->
## Goal

The spec grammar names mechanisms, not bundled instances; root aliases resolve from the active spec; container headings and the generated agent text come from the spec; and the permanent override test squad exists for every later task to test on (ADR-1250 sections 1, 3, 5 and 10; FEAT-1249 US2, US4, US5, US10).

None of this depends on the storage change running beside it, so the two land in parallel.

## Scope

- Root aliases (section 5): `RESERVED_CLI_ALIASES` and `reserved_alias_owner` go; the bundled groups and their aliases register from `bundled_spec()`; spec load checks an alias against `RESERVED_CLI_VERBS`, the declared type names and the other declared types' aliases, all in the active spec.
- Neutral grammar (section 1): `maps_parent_story` becomes `maps_to_parent`, the validator `subtask_story_mapping` becomes `subentity_mapping`, the transform function `milestone_rollup` becomes `status_rollup` (the bundled view keeps its declared name). An override spelling an old name is refused at load with a message naming the neutral one. The `sq workflow subentity-kinds --json` column is renamed with the key.
- Target kind (section 3): the kind hosted by the host type's `parent_required` type, exposed as one spec method the CLI, import and validators of the later tasks call. Spec load refuses a mapping kind hosted by a type with no `parent_required`, or whose `parent_required` type hosts no kind, naming the type and both remedies.
- Container heading (section 3): a `heading` key on `[subentity_kinds.<kind>]`, the title-cased `plural` when absent; the bundled spec declares the three bundled headings; the code table goes.
- Generated text (section 1): the squads skill, the CLAUDE.md section, the workflow cheatsheet and `_interactions/_cheatsheet.py` build every example and parenthetical from the active spec.
- The override test squad (section 10), checked in beside the bundled test squad.

## Expected files

- `src/squads/_workflow/_models.py`, `_workflow/_validity.py`, `_workflow/_validator_names.py`, `_workflow/_loader.py`
- `src/squads/_cli/__init__.py`, `_cli/_common.py`
- `src/squads/_specs/workflow.toml`
- `src/squads/_view_transforms.py`, `src/squads/_views.py`
- `src/squads/_services/_validators.py`, `_subentities.py`, `_item_dto.py`, `_catalogs.py`, `src/squads/_api/_dto/_workflow.py`, `src/squads/_discussion.py`, `src/squads/_cli/_items.py` (the `maps_parent_story` rename only)
- `src/squads/_rendering/templates/views/squads_skill.md.j2`, `templates/claude/claude_section.md.j2`, `templates/workflow.md.j2`, `src/squads/_interactions/_cheatsheet.py`, `_rendering/templates_manifest.json`, `_rendering/content_store.json` (regen)
- `tests/fixtures/override_squad/` (new: the override `workflow.toml`), `tests/_squads.py`, `tests/conftest.py`
- `tests/meta/test_reserved_cli_aliases_matches_the_bundled_alias_table.py` (goes with the table), `tests/meta/test_bundled_container_headings_stay_paired_with_their_plural.py`
- `tests/cli/test_root_options.py`, `tests/cli/test_workflow.py`, `tests/cli/test_skill.py`, `tests/cli/test_override.py`

## Runs beside

The storage task. Shared: `_workflow/_validity.py` (different functions) and the `maps_parent_story` token sites in `_services/_subentities.py`, `_services/_validators.py`, `_services/_item_dto.py`, `_discussion.py`, `_cli/_items.py`, where the storage task edits adjacent `story` lines. Whichever merges second rebases.

## Tests (about 9 new)

Listed per subtask. Build the override squad first (ST1), so the other subtasks test on it.

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

_Add with `sq task 1252 add-subtask "<title>"`; track with `sq task 1252 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Override test squad and its fixture

<!-- sq:subtask:ST1:body -->
The audit override squad becomes a permanent test squad beside the bundled one: a checked-in override `workflow.toml` under `tests/fixtures/override_squad/`, a builder in `tests/_squads.py` that inits a squad, installs the override and creates a populated set of items, and an `override_project` fixture next to `populated_project`.

The override drops every bundled work-item type, sub-entity kind and badge field and declares: `initiative` (kind `outcome`, field `urgency` on an ordered collection, `heading` declared) and `job` (kind `action`, field `impact`, `parent_required = "initiative"`, `maps_to_parent = true`); a reference type with a supersession ref kind; a kind with a field and a deferred status; create-time attributes on each kind; a field code with an underscore; and the alias `f` on `initiative`. The builder creates items through the service or CLI without a mapping, so it does not depend on the mapping option.

Tests (1): the built override squad passes `sq check` clean and `sq workflow` lists only its own vocabulary.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Root aliases from the active spec

<!-- sq:subtask:ST2:body -->
The root command table resolves a type token through the active spec's aliases. The bundled groups and aliases register from `bundled_spec()`; `RESERVED_CLI_ALIASES` and `reserved_alias_owner` go, with their `tests/meta` table guard. Spec load checks an alias against `RESERVED_CLI_VERBS`, the declared type names and the other declared types' aliases in the active spec, so an alias whose bundled owner the override drops is free.

Expected: with `feature` dropped, an override giving `initiative` the alias `f` loads and `sq f 2 show` shows the initiative; with `feature` kept, shadowing `f` is refused at load naming `feature`; a bundled squad resolves every bundled alias as today.

Tests (2): reused alias of a dropped type runs the new owner (on the override squad); shadowing a kept owner's alias refused, naming the owner.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Neutral grammar names and the target kind

<!-- sq:subtask:ST3:body -->
`maps_parent_story` becomes `maps_to_parent`, the validator `subtask_story_mapping` becomes `subentity_mapping`, the transform function `milestone_rollup` becomes `status_rollup`; the bundled spec uses the neutral names and keeps `[views.milestone_rollup]`. An override spelling an old name is refused at load with a message naming the neutral one. The subentity-kinds catalog column becomes `maps_to_parent`.

One spec method returns a kind's target kind: the kind hosted by the host type's `parent_required` type. Spec load refuses a mapping kind hosted by a type with no `parent_required`, or whose `parent_required` type hosts no kind, naming the type and both remedies (declare `parent_required`, or drop `maps_to_parent`).

Tests (3): an override spelling each old name is refused naming its neutral name (one case, the three spellings as rows); a mapping kind on a type without `parent_required` is refused naming both remedies; `sq workflow subentity-kinds --json` reports `maps_to_parent` (update of the existing case).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Container heading key on sub-entity kinds

<!-- sq:subtask:ST4:body -->
`[subentity_kinds.<kind>]` takes an optional `heading`; when absent the container heading is the title-cased `plural`. The bundled spec declares `User Stories`, `Subtasks` and `Findings`; `_BUNDLED_CONTAINER_HEADINGS` goes, and its `tests/meta` pairing guard goes or is rewritten against the spec. Report the new key for the writer's `docs/overrides.md` entry.

Tests (1): on the override squad, a kind with a declared `heading` and a kind without one render their container headings (declared text; title-cased plural).
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Generated agent text from the spec

<!-- sq:subtask:ST5:body -->
The generated agent text derives every example and parenthetical from the active spec: the squads skill's addressing example is built from the first aliased type and the kind it hosts (no `sq f 26 story 4 show` on a squad without them), the "(story/subtask/finding blocks)" parenthetical lists the declared kinds, the per-kind comment hint table keyed by bundled kind names goes (a generic hint, or text derived from the kind), and every mapping mention names the target kind's option. Same for the CLAUDE.md section, `workflow.md.j2` and `_interactions/_cheatsheet.py`. Regenerate the manifest.

Expected: a bundled squad's generated text reads as today apart from wording made generic; the override squad's names none of the dropped types, kinds, fields or aliases.

Tests (1): on the override squad, `sq skill squads show` and the CLAUDE.md section name no dropped word, checked against the names the bundled spec declares and the override drops (not a literal list).
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T21:01:29Z] `python-dev` Elias Python:
  - @manager Handback for TASK-1252: commit f31e2951 on branch worktree-agent-a79a454ba3f87496e (worktree /home/pchat/projects/squads/.claude/worktrees/agent-a79a454ba3f87496e, based on origin/release/0.19). Gates run: pyright, ruff check, ruff format --check clean; `pytest -n 4 tests/meta tests/cli tests/regressions tests/check` 1713 passed. Full suite is yours.
    
    **ST1 override squad.** `tests/fixtures/override_squad/{workflow,playbook}.toml`, builder `init_overridden` in `tests/_squads.py`, populated builder `tests/_override_populated.py` (INI-8, JOB-9, REC-10), `override_project` fixture in `tests/cli/conftest.py`. The override keeps only role/skill/operator and declares initiative (outcome, urgency, heading, alias f), job (action, impact, work_size, parent_required, maps_to_parent), record (replaces ref kind), a deferred-status lifecycle on action, create-time attributes of every kind (date, list, str, bool). Test: checks clean and lists only its vocabulary.
    
    **ST2 aliases.** RESERVED_CLI_ALIASES / reserved_alias_owner and their meta guard are gone. Spec load checks an alias against RESERVED_CLI_VERBS, declared type names and the other declared aliases. The root table re-routes a token the active spec gives to another type (`common.retargeted_type`). Tests: reused alias runs the new owner (override squad); shadowing a kept owner's alias is refused naming it.
    
    **ST3 neutral names.** maps_to_parent, subentity_mapping, status_rollup (bundled view keeps its name). Old spellings are refused at load and in `sq workflow lint`, naming the neutral one. `WorkflowSpec.mapping_target_kind(kind)` is the one target-kind method; load refuses a mapping kind whose host has no parent_required or whose parent_required type hosts no kind, naming both remedies. Catalog column renamed. Tests: three renamed spellings as rows; two refusal rows.
    
    **ST4 heading.** `heading` key on `[subentity_kinds.<kind>]`; absent means the title-cased plural; bundled declares the three; code table and its pairing guard removed. Test on the override squad (declared vs derived).
    
    **ST5 generated text.** squads skill, CLAUDE.md section, workflow cheatsheet derive the mapping option, example and kind list from the spec (new `cheatsheet_alias_example`); the per-kind hint table is gone. Static prose that used dropped-type words was reworded (greeting example, "review points", "findings", "decision", "stability contract", "e.g. a bug"). Test: on the override squad, `sq skill squads show` and CLAUDE.md name no word the bundled spec declares and the override drops.
    
    **Falsification.** Each new test was run red once: playbook removed (ST1), retargeting disabled (alias reuse), duplicate-alias check disabled, rename check returning nothing, mapping-target check removed, heading ignored, and a hardcoded `story` put back in the CLAUDE.md template. Restored after each.
    
    **Left for others / notes.**
    - `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py` still keeps its literal sets (ADR-1250 section 9, a later guard task).
    - `sq list` on the override squad still shows a Priority column and `Story` header (the derived-options task).
    - The 0.19.0 manifest key and content_store were regenerated once from a clean checkout; the 0.18.0 block is untouched. The bundled spec digest in `tests/cli/test_workflow.py` changed with workflow.toml.
    - This repository's own CLAUDE.md managed section and skills need `sq sync` (templates changed); I did not touch `squads/`.
    
    **Draft changelog lines (adopter-visible).**
    - Root type aliases come from the squad's workflow spec: an override that drops `feature` can give `f` to another type; keeping the owner and reusing its alias is refused at load.
    - Renamed spec grammar: the kind key `maps_parent_story` is `maps_to_parent`, the validator `subtask_story_mapping` is `subentity_mapping`, and the bundled view transform function `milestone_rollup` is `status_rollup` (the view keeps its name). An override spelling an old name is refused with a message naming the new one. `sq workflow subentity-kinds --json` reports `maps_to_parent`.
    - A kind with `maps_to_parent = true` needs a host type whose `parent_required` type hosts a sub-entity kind; otherwise the spec is refused at load, naming both remedies.
    - New optional `heading` key on `[subentity_kinds.<kind>]` sets the container heading; without it the heading is the title-cased `plural` (docs/overrides.md entry for the writer). An override that renames a bundled kind's `plural` now keeps the bundled `heading` until it declares its own.
    - The squads skill, CLAUDE.md section and workflow cheatsheet read every example from the squad's own vocabulary instead of bundled type and kind names.
- [2026-10-29T21:10:20Z] `reviewer` Paul Reviewer:
  - Generated-text rewording reviewed in REV-1259 F8 (medium): derive the review gate, findings and tree fields from the spec instead of neutral words.
<!-- sq:discussion:end -->
