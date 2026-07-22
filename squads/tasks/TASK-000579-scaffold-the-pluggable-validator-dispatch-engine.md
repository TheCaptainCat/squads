---
id: TASK-579
sequence_id: 579
type: task
title: Scaffold the pluggable-validator dispatch engine
status: Done
parent: FEAT-567
author: tech-lead
description: 'US2: new _services/_validators.py (Validator protocol, ValidatorContext,
  closed catalog CODE constant, report+gate engine, per-item + squad-global classes);
  wired to run empty/stub set (byte-identical); AST-guard allowlist entry'
created_at: '2026-07-22T09:26:44Z'
updated_at: '2026-07-22T10:25:30Z'
---
<!-- sq:body -->
Story US2 (dispatch engine). Stand up the pluggable-validator dispatch engine scaffold per ADR-541 Axis B and Robert's D1/D2/D3 pins. Phase A wires the engine to run an empty/stub catalog (no-op) while today's `_check_*` methods still produce their output verbatim — no behaviour change. Phase B (FEAT-568) lifts the real checks into named validators.

## Why / boundary (Robert D1)

The engine lives in `_services/` (new `_services/_validators.py`), NOT `_models/` — it reads live item + index state (parent lookups, incoming-supersedes edges, registered-slug set, on-disk body text), exactly what `_maintenance.py`'s `_check_*` hold today via `self.store`/`self.paths`/`self.spec`. `_models`/`_workflow` value objects stay pure. `ItemSpec` carries the bare `category` name only (D2); the effective per-item validator set (common core + category bundle + type additions) is resolved at call time by the engine, never pre-baked onto the spec.

## Scope

- New `src/squads/_services/_validators.py`:
  - `ValidatorContext` — the inputs a validator reads: the item, the active spec, and precomputed squad-global inputs (registered-slug set, incoming-supersedes map, on-disk body map) mirroring how `_check_items`/`_check_decisions` precompute today.
  - `Validator` protocol over `ValidatorContext`, yielding `CheckIssue` (reuse `_services/_results.CheckIssue`).
  - The closed catalog as a module-level `dict[str, Validator]` CODE constant — immutable, shared, definition-time (fine under the `_context.py` CODE-vs-REQUEST split). Phase A: empty or stub entries only.
  - Two validator classes / one engine (D3): per-item validators (engine iterates `index.items`, resolves each item's effective set from its `category` + additions, runs AND-composed) and squad-global validators (a separate small registry run ONCE per invocation, not category-selectable, not removable).
  - Engine surface: `report(index, on_disk) -> list[CheckIssue]` (collects both classes) and `gate(item, index) -> None`-or-raise (runs only the one item's per-item set, stops at first violation). Same report/abort split as the existing workflow-lint.
- Wire the engine at its two call sites running the empty/stub set (proving the dispatch shape end to end, producing nothing):
  - `MaintenanceMixin.check()` — call `engine.report(...)` alongside the existing `_check_*` calls; with an empty catalog it contributes zero issues, so output stays byte-identical.
  - create/update gating — call `engine.gate(...)` in abort mode; with an empty per-item set it is a no-op.
- Do NOT populate the catalog or point any category bundle at a real validator (that is Phase B / FEAT-568). Do NOT remove or rewrite any `_check_*` method — they remain the source of `sq check` output this phase.

## AST guard (required)

Add the catalog dict's exact name to `tests/meta/test_no_unallowlisted_module_level_mutable_state.py` under a new `ALLOWLIST["src/squads/_services/_validators.py"]` entry, with a one-line reason (closed validator catalog — a definition-time immutable-once-built lookup table, not request-scoped state). A module-scope `dict` literal is flagged by construct 1 of the guard, so this entry is mandatory or the meta-test reddens.

## Acceptance

- `_services/_validators.py` exists with the `Validator` protocol, `ValidatorContext`, the module-level catalog constant, and an engine exposing `report(index, on_disk)` and `gate(item, index)`.
- The engine is instantiated and invoked from both `check()` (report) and create/update (gate), running the empty/stub set.
- `sq check` output is byte-identical to today (engine contributes nothing); create/update behaviour unchanged.
- New unit tests prove: `report()` over the empty catalog returns `[]`; `gate()` over an empty per-item set does not raise; the engine resolves an item's effective set from its `category` (shape test, even with stub bundles).
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; the AST-guard meta-test green with the new allowlist entry; `uv run pytest` green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 579 add-subtask "<title>"`; track with `sq task 579 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T09:47:28Z] Elias Python:
  - dispatch engine scaffold lands: _services/_validators.py (Validator/SquadGlobalValidator protocols, ValidatorContext, empty CATALOG/SQUAD_GLOBAL_CATALOG/CATEGORY_BUNDLES CODE constants, ValidatorEngine.report/gate), wired at sq check + create/update as a no-op; AST guard allowlisted + green; 9 new unit tests; sq check byte-identical.
- [2026-07-22T09:55:54Z] Elias Python:
  - Fix 1 done: stripped ADR-541/FEAT-567/FEAT-568 refs from src/ comments+docstrings (validators.py, _base.py, _maintenance.py, _items.py, _loader.py, _models.py) and the new test's docstring; hygiene meta-test green (10/10). Fix 2 BLOCKED: templates_manifest.json keys by squads.__version__ (0.11.1), and v0.11.1 is an already-shipped, pushed tag — regenerating would overwrite the released entry's hashes. Flagged to the coordinator/operator rather than run the regen script; test_override_manifest_and_stamp_freshness stays red pending a version-bump call.
- [2026-07-22T10:13:37Z] Elias Python:
  - Fix 2 unblocked per operator approval: pyproject.toml 0.11.1->0.12.0 (unreleased on release/0.12), manifest regen appended a 0.12.0 entry only (0.11.1 and all older entries byte-identical, diffed), CHANGELOG restructured to a proper 0.12.0 section (category-axis/validator-engine Added line + the is_meta deprecation note). Also caught+fixed 2 golden JSON fixtures (override_list/override_diff) whose pinned base_version was 0.11.1 -- regenerated just those two, diff confirms only the version string changed. All gates green; sq check stdout byte-identical (a new stderr-only version-drift notice now prints repo-wide, expected from the version bump itself, clears via sq sync -- not run, out of scope).
- [2026-07-22T10:24:30Z] Elias Python:
  - REV-580 F1 fixed: effective_validator_names' category_bundles param no longer binds the mutable CATEGORY_BUNDLES dict as a default -- now category_bundles: dict[...] | None = None, resolved to CATEGORY_BUNDLES inside when omitted. Behavior identical (still an empty-catalog no-op); all call sites (production + stub-bundle tests) unaffected. pyright/ruff/format clean, both targeted meta+scaffold tests green, sq check byte-identical.
<!-- sq:discussion:end -->
