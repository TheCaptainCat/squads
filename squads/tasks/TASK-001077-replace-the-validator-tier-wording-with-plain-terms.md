---
id: TASK-1077
sequence_id: 1077
type: task
title: Replace the validator tier wording with plain terms
status: Ready
author: tech-lead
priority: low
refs:
- ADR-864
- MILE-1051:targets
description: 'Wording only: always on, on by default for a category, opt-in, file
  checks'
subentities:
- local_id: ST1
  title: Rename ADR-864's title and tiering-test heading, and use the plain terms
    in its body
  status: Todo
  assignee: architect
- local_id: ST2
  title: Use the plain terms in validator docstrings, comments and the assertion message
  status: Todo
  assignee: python-dev
- local_id: ST3
  title: Use the plain terms in the adopter docs
  status: Todo
  assignee: tech-writer
created_at: '2026-10-16T20:59:53Z'
updated_at: '2026-10-24T19:46:27Z'
---
<!-- sq:body -->
Drop the word "tier" for validators and use plain terms. Wording only: no behaviour, name, or output change.

## Term mapping

| Current wording | Plain term |
|---|---|
| floor tier (ADR-864's "Floor") | **always on** |
| category bundle tier | **on by default for a category** |
| catalog-only tier | **opt-in** |
| "tier 1" of `sq check` (the raw-text scan of every file) | **file checks** |
| "tier 2" of `sq check` (the per-item validator catalog) | the validator catalog (no tier number) |
| "the tiering test" (ADR-864) | the placement test |

ADR-864's separate *level* floor (`VALIDATOR_LEVEL_FLOOR`: a selection may raise a member's level but never lower it) is a different concept. It keeps its name unless the architect decides otherwise.

## Occurrences in scope

Found with `rg -n -i '\btier' src tests docs CLAUDE.md`, keeping only validator uses. Line numbers move, so rerun the search rather than trusting a list.

- ADR-864: the title ("Validator catalog: three tiers, declared levels, no injected Python"), the "The tiering test" heading, and the body's "Three tiers", "tier it belongs in", and "the tier that makes..." prose.
- `src/squads/_services/_validators.py`: the module docstring ("file-level tier", "a second, always-on tier", "tier-1 finding", "both tiers").
- `src/squads/_services/_maintenance.py`: the `_scan_for_check` docstring ("Tier 1 of sq check's two finding tiers", "This tier runs first").
- `src/squads/_views.py`: two docstrings ("the check tier").
- `src/squads/_models/_item.py`: "the file-level check tier".
- `src/squads/_workflow/_models.py`: the assertion message "placed in exactly one tier" and the comment "the same tiering test".
- `tests/cli/test_content_writes_on_a_generated_role_or_skill_are_refused_cli.py`: a docstring ("the check tier").
- `docs/internals.md`: "It runs in two tiers".

## Out of scope (a different concept, stays)

- `docs/stability.md` stability tiers, plus the links to them in `docs/README.md`, `docs/faq.md`, `docs/workflow.md`, `src/squads/_rendering/templates/workflow.md.j2` and its goldens and content store.
- `docs/migration.md` on-disk-state tiers.
- The memory and board "lighter tier than an item" wording in `src/squads/_memory/_model.py`, `src/squads/_cli/_memory.py`, `tests/service/test_memory_storage.py` and `tests/service/test_board_storage.py`.
- The name-resolution "Tier 3" comment in `tests/service/test_operator_named_roles_survive_sync.py`.

## Acceptance

- `rg -n -i '\btier' src tests docs CLAUDE.md` returns no validator use of "tier". Only the out-of-scope hits above remain.
- The architect has renamed ADR-864's title (and so its filename) and the "The tiering test" heading, and the body uses the plain terms. A dated discussion comment records the rename.
- Docstrings, comments, and the assertion message in `src/`, and the one test docstring, use the plain terms. Tests and goldens still pass unchanged.
- The adopter docs (`docs/internals.md`, plus any "category bundle" or "catalog-only" phrasing in `docs/overrides.md`) use the plain terms.
- `sq check` is clean.

## Tests

Wording only, so no new tests. The `rg` gate in Acceptance is the check, and the existing tests and goldens must pass unchanged.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1077 add-subtask "<title>"`; track with `sq task 1077 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Rename ADR-864's title and tiering-test heading, and use the plain terms in its body

<!-- sq:subtask:ST1:body -->
Rename the title (and so the filename) and the "The tiering test" heading. Replace "Three tiers", "Floor", "Category bundle", "Catalog-only" and "tier" in the prose with: always on, on by default for a category, opt-in. Leave the level floor (a selection may raise a level but never lower it) as is, or rename it in the same pass if it reads better. Record the rename in a dated discussion comment. No change to what the decision says.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Use the plain terms in validator docstrings, comments and the assertion message

<!-- sq:subtask:ST2:body -->
Covers the in-scope lines in the task body: _services/_validators.py (module docstring), _services/_maintenance.py (the _scan_for_check docstring), _views.py, _models/_item.py, _workflow/_models.py (the assertion message and the tiering-test comment), and the docstring in tests/cli/test_content_writes_on_a_generated_role_or_skill_are_refused_cli.py. Call "tier 1" file checks and "tier 2" the validator catalog. Wording only: no identifiers, behaviour or output change. Run the pyright, ruff and pytest gates.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Use the plain terms in the adopter docs

<!-- sq:subtask:ST3:body -->
docs/internals.md line 150 ("It runs in two tiers"): call the two parts file checks and the validator catalog. In docs/overrides.md, align any "category bundle" or "catalog-only" phrasing with: always on, on by default for a category, opt-in. Do not touch the stability tiers (docs/stability.md and the links to it) or the on-disk-state tiers in docs/migration.md.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T21:00:22Z] `tech-lead` Olivia Lead:
  - Left unparented. EPIC-540 has two open features: FEAT-901 (opt-in per-item checks) and FEAT-902 (squad-global checks). Each covers one set of validators and both target 0.16 (MILE-934). This wording pass runs across the whole catalog and is planned for 0.17 (MILE-1051). Putting it under either feature would keep a 0.16 feature open for 0.17 work. Asked for by op-pierre on ADR-864, 2026-10-16.
- [2026-10-24T19:46:27Z] `tech-lead` Olivia Lead:
  - Refreshed the occurrence list (line numbers had moved, one test docstring added) and added a Tests line: no new tests, the rg gate is the check. Moved to Ready.
<!-- sq:discussion:end -->
