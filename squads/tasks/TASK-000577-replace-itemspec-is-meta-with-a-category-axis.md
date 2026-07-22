---
id: TASK-577
sequence_id: 577
type: task
title: Replace ItemSpec.is_meta with a category axis
status: Done
parent: FEAT-567
author: tech-lead
description: 'US1: category Literal[roster|work|records] replacing is_meta; category-derived
  item_is_meta/work_types shims; bundled TOML regen (behaviour-preserving)'
created_at: '2026-07-22T09:26:31Z'
updated_at: '2026-07-22T10:25:29Z'
---
<!-- sq:body -->
Story US1 (category axis). Replace the `ItemSpec.is_meta: bool` flag with a `category` axis and keep every consumer behaviourally identical. Behaviour-preserving / no-enforcement (Phase A): the full suite stays green and `sq check` output is byte-identical.

## Scope

- `_workflow/_models.py`: replace `ItemSpec.is_meta: bool = False` with `category: Literal["roster", "work", "records"] = "work"`. The `Literal` itself gives free catalog-membership rejection at construction (a value outside the three fails to load with `SquadsError` via the loader's `model_validate` wrapping) — that is the Plane-1 category-catalog-membership check for this task; no separate validator method is required unless a `_CATEGORIES` helper reads cleaner.
- Rewrite the existing reserved-vocab floor in `WorkflowSpec._validate` (currently "meta-type `t` must declare `is_meta = true`") to assert each `META_TYPES` member declares `category == "roster"`. This is a behaviour-preserving migration of an existing load check, not new enforcement.
- Keep the accessors as `category`-derived shims so the ~15 consumer sites compile and behave identically:
  - `item_is_meta(t)` := `self.items[t].category == "roster"`
  - `work_types()` := non-roster types (`category != "roster"`, i.e. work + records) — preserving today's `not is_meta` set exactly.
  - Mirror the same shims in `_workflow/__init__.py`'s module-level free functions (`item_is_meta`/`work_types`).
- Three sites read the field directly (not through the accessor) and must switch to `item_is_meta(...)` / a `category`-derived expression: `_backends/_claude_code/_backend.py` (`ctype_spec.is_meta`), `_interactions/__init__.py` (`spec.items[ctype].is_meta`), `_cli/_workflow_cmd.py` (`spec.items[t].is_meta`, the `reserved` field of `sq workflow types`).
- `_workflow/default_workflow.toml`: regenerate the 10 `is_meta = …` lines to `category = '…'` per ADR-541 settled assignments — `roster` = role/skill/operator; `work` = epic/feature/task/bug/review; `records` = decision/guide. Update the header comment (line ~2) that lists `is_meta` among the encoded capability flags.
- Update the tests that reference `is_meta` to the `category` axis: `tests/unit/test_type_spec_capability_flags.py`, `test_workflow_reserved_vocab.py`, `test_lifecycle_reachability_lint.py`, `test_workflow_spec_models_fail_closed_on_unknown_keys.py`, `test_workflow_spec_artifact.py`, `test_item_and_subentity_templates_render_structurally.py`, `tests/cli/test_workflow_types_cli.py`.

## Out of scope (deferred)

- The loader `is_meta` read-compat shim + CHANGELOG deprecation note — sibling task.
- The broader roster-locked override refusal (no add/deactivate/field-merge/rename of a roster type) and category-reassignment well-formedness — these are ADR-541 enforcement, deferred (Phase B / later); do not add them here.
- Per-site reclassification of the ~15 consumers (roster-vs-not vs burn-down-vs-not) — Phase C (FEAT-573). The shims deliberately preserve today's lossy split.

## AST guard

If a `_CATEGORIES` frozenset (or similar) module-level constant is introduced in `_workflow/_models.py`, add its exact name to `ALLOWLIST["src/squads/_workflow/_models.py"]` in `tests/meta/test_no_unallowlisted_module_level_mutable_state.py` with a one-line reason. A `frozenset` literal is not flagged by the guard's mutable-binding check, but a `dict`/`list`/`set` literal would be — prefer `frozenset`/`tuple` for a fixed catalog; allowlist only if a mutable-shaped literal is genuinely needed.

## Acceptance

- `ItemSpec.category` exists (default `"work"`), populated for all built-in types per ADR-541; `is_meta` field is gone.
- A spec whose `category` names a value outside the three fails to load with a clean `SquadsError`.
- Each meta-type (role/skill/operator) still required to be `category = "roster"` at load (migrated floor).
- `item_is_meta()` / `work_types()` return identical sets to before across all types.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean.
- `uv run pytest` green; `sq check` output byte-identical to today.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 577 add-subtask "<title>"`; track with `sq task 577 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T09:37:17Z] Elias Python:
  - category axis lands: ItemSpec.category replaces is_meta, shims preserve item_is_meta()/work_types(), bundled TOML regenerated, 3 direct field-access sites + 3 Jinja templates updated, test sweep done; sq check byte-identical, pyright/ruff clean.
- [2026-07-22T09:47:29Z] Elias Python:
  - operator directive: renamed item_is_meta() -> item_is_roster() (definition + all call sites in src/tests), work_types() left as-is; no new 'meta' language introduced; re-verified sq check byte-identical + full gates after the rename.
<!-- sq:discussion:end -->
