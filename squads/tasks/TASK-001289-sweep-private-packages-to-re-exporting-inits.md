---
id: TASK-1289
sequence_id: 1289
type: task
title: Sweep private packages to re-exporting inits
status: InProgress
parent: FEAT-1288
author: tech-lead
refs:
- ADR-1287:implements
description: Guard, three moves and a leaf-first sweep of every private package to
  the ADR-1287 re-export rule; docs corrected
subentities:
- local_id: ST1
  title: Guard, resolver, PENDING and the three moves
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST2
  title: Sweep _models
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST3
  title: Sweep _workflow, _roles and _interactions
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST4
  title: Sweep _api/_dto and _api
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST5
  title: Sweep _rendering, _index, _sources, _overrides, _board, _memory
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST6
  title: Sweep _backends, _migrations, _tui and _services
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST7
  title: Sweep _cli/_render, _cli, _daemon; delete PENDING
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST8
  title: Correct the documents stating the old rule
  status: Done
  assignee: tech-writer
  maps_to: US2
created_at: '2026-11-04T11:07:46Z'
updated_at: '2026-11-04T14:13:23Z'
priority: medium
---
<!-- sq:body -->
## Goal

Bring every private package under `src/squads` to the ADR-1287 rule: each package init re-exports exactly the names other packages import, an importer writes one import statement per package, and the guard in `tests/meta/test_package_import_edges_match_the_recorded_table.py` holds init shape, no reach-in, no reach-out and exact surface. The design is ADR-1287 (rule, cycles, startup limits, guard, documents, sweep plan) with op-pierre's four accepted points; it is not restated here.

- `ops` (`_api/_ops`) and `markers` are the only namespace re-exports; every other cross-package module-object import becomes a name import.
- Inits hold only re-export statements and an optional docstring: `_cli/__init__` code moves to `_cli/_app.py`, `_workflow/__init__` code to `_workflow/_bundled.py`.
- `_models/_config.py` moves to `squads/_config.py`; the edge table gains the `_config` node.
- ADR-78 is related, not superseded; its no-re-export sentence is already narrowed in place.

## Sweep mechanics

ST1 lands the guard with every package in a transitional `PENDING` set that rules 1 to 4 skip. Each later subtask sweeps its packages leaf-first in the ADR-1287 section 6 order: writes the package init, rewrites every outside import of its modules in `src` (module top, in-function and `TYPE_CHECKING`), rewrites the test name-imports, and deletes the package from `PENDING`. ST7 deletes `PENDING`. Both import forms work while a package is pending, so the order inside a subtask is free as long as each package leaves `PENDING` green.

## Rules for every subtask

- **Pure move.** No behaviour change: no logic, signature, message or output edits, no renames beyond what the rule requires (an outside-used underscore name losing its underscore). A diff line that is not an import, an init re-export, a moved block or a guard/table entry needs a reason in the handback.
- **One developer, one subtask.** Each subtask fits one fresh developer and leaves the gate green on its own: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, `tests/meta`, and `sq check`. The main loop runs the full suite.
- **Startup bench.** Each subtask runs `scripts/bench_local_mode.py` against the build before it. A result beyond run-to-run noise stops the subtask: report the numbers and the module responsible, do not land it. The remedy is to move the heavy module out of the package (as with `_config`), not to exempt it.
- Comments and docstrings stay short and state present truth: no ticket IDs, no history.

## Interaction with TASK-1286

TASK-1286 (scoped sources) is paused until this task lands. Its in-flight code in the `_sources` package (and the `_services` source modules, the source DTOs and renderers) follows the rule: ST5 sweeps `_sources` as committed, and when TASK-1286 resumes, its new and changed modules import through package inits and add their outside-used names to the `_sources` re-exports, held by the guard.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1289 add-subtask "<title>"`; track with `sq task 1289 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Guard, resolver, PENDING and the three moves

<!-- sq:subtask:ST1:body -->
**Packages.** None swept: this lands the guard, the resolver, `PENDING` and the three moves (ADR-1287 section 6, step 0; sections 2 and 4).

**Files and guards.**
- `tests/meta/test_package_import_edges_match_the_recorded_table.py`: drop `INITS_WITH_CODE`; add the four rules (init shape, no reach-in, no reach-out, exact surface, the last naming the `LAZY_GROUPS` and `_sources/_registry.py` tables in its message) with every private package in `PENDING`; add `test_every_package_level_is_acyclic`; add the `_config` node and its edges to `EDGES`.
- `tests/_import_scan.py`: one resolver that follows each init's re-export statements back to the defining module.
- The guards that name a module inside a package use the resolver: `test_the_cli_and_the_terminal_ui_write_no_file_themselves.py`, `test_the_command_endpoint_never_calls_the_daemon_or_starts_a_process.py` (`squads._api._client`, `squads._cli._remote`), `test_renderers_read_neither_the_vocabulary_nor_the_configuration.py` (`squads._config` replaces `squads._models._config`), `test_the_cli_imports_the_service_layer_only_in_the_local_api_factory.py`. Each keeps a known-positive case so it cannot pass vacuously.
- Moves: `src/squads/_models/_config.py` to `src/squads/_config.py` (its six `src` importers change one line each); `_cli/__init__.py` code (Typer app, root callback, `LAZY_GROUPS`, eager command-module side-effect imports) to `src/squads/_cli/_app.py`; `_workflow/__init__.py` code (`bundled_spec`, `dropped_via_selected`, the bundled-spec constant, `__all__` removed) to `src/squads/_workflow/_bundled.py`. Both inits keep only re-exports of what outside modules import. The entry point `squads.__main__:main` and `_shim`'s import of `squads._cli` keep working.
- `test_no_unallowlisted_module_level_mutable_state.py`: the allowlist entries for `_cli/__init__.py` and `_workflow/__init__.py` move with their code. `test_lazy_command_groups_match_the_typer_groups.py` and the shim guards follow `LAZY_GROUPS` to `_cli/_app.py`.

**Acceptance.**
- The guard runs all four rules plus per-level acyclicity, with every package in `PENDING`; the three moved modules and the resolver are in place.
- pyright, ruff (check and format), `tests/meta` and `sq check` green.
- `scripts/bench_local_mode.py` against the previous build shows no startup regression beyond noise; otherwise stop and report.
- Pure move: no behaviour change.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Sweep _models

<!-- sq:subtask:ST2:body -->
**Packages.** `_models` (ADR-1287 section 6, step 1: 223 `src` statements in 93 files, 10 test statements), including `markers` re-exported as a namespace (`from squads._models import _markers as markers`).

**Files and guards.**
- `src/squads/_models/__init__.py`: re-exports, one aliased line per outside-used name, from direct children only.
- Every `src` module outside `_models` that imports a `_models` module path (module top, in-function, `TYPE_CHECKING`); module-object imports such as `_attributes as attrs` become name imports.
- Test name-imports of `_models` module paths.
- `tests/meta/test_package_import_edges_match_the_recorded_table.py`: `_models` leaves `PENDING`.
- If the subtask outgrows one session, split it by importing package as ADR-1287 allows; both forms work until `_models` leaves `PENDING`.

**Acceptance.**
- The guard drops `_models` from `PENDING` and holds it.
- pyright, ruff (check and format), `tests/meta` and `sq check` green.
- `scripts/bench_local_mode.py` against the previous build shows no startup regression beyond noise; otherwise stop and report.
- Pure move: no behaviour change.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Sweep _workflow, _roles and _interactions

<!-- sq:subtask:ST3:body -->
**Packages.** `_workflow`, `_roles`, `_interactions`, in that order (ADR-1287 section 6, steps 2, 4 and 5: 69 + 70 + 52 `src` statements, 27 + 12 + 9 test statements). `_workflow` re-exports from `_bundled.py` the names ST1 moved there.

**Files and guards.**
- `src/squads/_workflow/__init__.py`, `src/squads/_roles/__init__.py`, `src/squads/_interactions/__init__.py`: re-exports only.
- Every `src` import of their module paths from outside each package; `_loader as workflow_loader` and similar module-object imports become name imports. The in-function cycle-avoiding imports (`_workflow -> _migrations`, `_workflow -> _overrides`, `_interactions -> _overrides`) stay in their functions and keep their current spelling until the target package is swept.
- Test name-imports of these packages' module paths.
- The guard: the three packages leave `PENDING`.

**Acceptance.**
- The guard drops `_workflow`, `_roles` and `_interactions` from `PENDING`.
- pyright, ruff (check and format), `tests/meta` and `sq check` green.
- `scripts/bench_local_mode.py` against the previous build shows no startup regression beyond noise; otherwise stop and report.
- Pure move: no behaviour change.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Sweep _api/_dto and _api

<!-- sq:subtask:ST4:body -->
**Packages.** `_api/_dto`, then `_api` with `ops` re-exported as a namespace (`from squads._api import _ops as ops`) (ADR-1287 section 6, step 3: 24 + 231 `src` statements in 8 + 77 files, 22 test statements). `_api/__init__` re-exports DTOs from `squads._api._dto`, never from its modules.

**Files and guards.**
- `src/squads/_api/_dto/__init__.py`, `src/squads/_api/__init__.py`: re-exports only.
- Every `src` import of `_api` and `_api/_dto` module paths from outside each package; the 22 `ops` importers write `from squads._api import ops`.
- Test name-imports of these module paths.
- The guard: `_api/_dto` and `_api` leave `PENDING`. The command-endpoint guard keeps resolving `squads._api._client` through the resolver.
- If the subtask outgrows one session, split it by importing package as ADR-1287 allows.

**Acceptance.**
- The guard drops `_api/_dto` and `_api` from `PENDING`.
- pyright, ruff (check and format), `tests/meta` and `sq check` green.
- `scripts/bench_local_mode.py` against the previous build shows no startup regression beyond noise (ADR-1287 measured `_api._client` at about +3 ms over `sq --help`); otherwise stop and report.
- Pure move: no behaviour change.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Sweep _rendering, _index, _sources, _overrides, _board, _memory

<!-- sq:subtask:ST5:body -->
**Packages.** `_rendering`, `_index`, `_sources` (with the connector subpackages `_gitlab`, `_github`, `_jira`, whose inits already re-export and must meet rule 1), `_overrides`, `_board`, `_memory`, in that order (ADR-1287 section 6, steps 6 to 10: 14 + 30 + 25 + 4 + 8 `src` statements, 2 + 3 + 4 + 7 + 1 test statements).

**Files and guards.**
- The six package inits and the three connector inits: re-exports only. `_sources/__init__` never imports a connector subpackage: `_sources/_registry.py` selects them by name.
- Every `src` import of their module paths from outside each package; `_credentials as credentials`, `_store as board_store` and similar become name imports. The in-function imports reaching `_overrides` (from `_workflow/_loader.py`, `_interactions/_loader.py`) import from the `_overrides` init and stay in their functions.
- Test name-imports of these module paths.
- The guard: the packages leave `PENDING`. The CLI/TUI no-write guard keeps matching the board and memory writers through the resolver.

**Acceptance.**
- The guard drops `_rendering`, `_index`, `_sources` and its connector subpackages, `_overrides`, `_board` and `_memory` from `PENDING`.
- pyright, ruff (check and format), `tests/meta` and `sq check` green.
- `scripts/bench_local_mode.py` against the previous build shows no startup regression beyond noise; otherwise stop and report.
- Pure move: no behaviour change. `_sources` is swept as committed; TASK-1286's later work follows the rule.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Sweep _backends, _migrations, _tui and _services

<!-- sq:subtask:ST6:body -->
**Packages.** `_backends/_claude_code`, `_backends/_agents_md`, then `_backends`; `_migrations`; `_tui`; `_services` (ADR-1287 section 6, steps 11 to 14: 13 + 9 + 1 + 4 `src` statements, 1 + 0 + 2 + 13 test statements).

**Files and guards.**
- The package inits: re-exports only. `_backends/_registry.py`, inside `_backends`, imports from `squads._backends._claude_code`; `_migrations` imports `from squads._backends`.
- `_services`, `_tui` keep being reached only through their current in-function imports (`_cli/_calls.local_api()`, `_cli/_ui.py`), now spelled through the package init. The `_workflow -> _migrations` in-function hint import imports from the `_migrations` init.
- Test name-imports of these module paths; tests that monkeypatch import the module object.
- The guard: the packages leave `PENDING`. The CLI-to-services guard keeps holding `local_api()` as the only `_services` reach through the resolver.

**Acceptance.**
- The guard drops the `_backends` packages, `_migrations`, `_tui` and `_services` from `PENDING`.
- pyright, ruff (check and format), `tests/meta` and `sq check` green.
- `scripts/bench_local_mode.py` against the previous build shows no startup regression beyond noise (`_services` is 72 ms over `sq --help` if pulled in eagerly); otherwise stop and report.
- Pure move: no behaviour change.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Sweep _cli/_render, _cli, _daemon; delete PENDING

<!-- sq:subtask:ST7:body -->
**Packages.** `_cli/_render`, then `_cli`, then `_daemon`; then the transitional `PENDING` set is deleted (ADR-1287 section 6, steps 15 and 16 without the documents: 49 + 1 + 1 `src` statements, 11 + 8 test statements).

**Files and guards.**
- `src/squads/_cli/_render/__init__.py`, `src/squads/_cli/__init__.py` (re-exports of `_app.py` only), `src/squads/_daemon/__init__.py`: re-exports only. The lazy command modules `LAZY_GROUPS` names and `_cli/_remote.py` are never imported by the `_cli` init.
- Every `src` import of these module paths from outside each package; `_common as common` and similar become name imports, or stay sibling module-object imports inside `_cli`. The in-function `_cli -> _daemon` import (`_cli/_daemon.py`, `run_daemon`) imports from the `_daemon` init and stays in its function.
- Test name-imports; tests that need a lazy command module's name import the module object.
- The guard: `PENDING` and every reference to it are deleted, so rules 1 to 4 apply to every package.

**Acceptance.**
- No `PENDING` set remains; the four rules and per-level acyclicity hold over every private package.
- pyright, ruff (check and format), `tests/meta` and `sq check` green.
- `scripts/bench_local_mode.py` against the previous build, and once against the build before ST1, shows no startup regression beyond noise; otherwise stop and report.
- Pure move: no behaviour change.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Correct the documents stating the old rule

<!-- sq:subtask:ST8:body -->
**Scope.** Correct every document that states the old no-re-export rule, as listed in ADR-1287 section 5. Runs after ST7, against the swept tree.

**Files.**
- `CLAUDE.md` (repository file, outside the managed region): the "Module privacy convention" paragraph (no-re-export sentence, example import, list of non-empty inits, connector-subpackage exception); the `_models/` line (`_config` gets its own top-level entry); the `_workflow/` line (`_bundled.py`, re-exported); the `_cli/` line and the `LAZY_GROUPS` sentence (`_cli/_app.py`); the renderer guard sentence (`squads._config`). Lines naming a module file as where code lives stay.
- `CONTRIBUTING.md`: the "Private layout" bullet and the lazy-command-table sentence naming `_cli/__init__.py`.
- GUIDE-79 "Cross-cutting conventions": points to ADR-1287 (through `sq guide 79 body`).
- `docs/internals.md` (private-layout note), `docs/stability.md` Tier 4, and the README conventions paragraph: adopter-facing, no internal references, no repo process; no import path becomes public API.

**Acceptance.**
- Every document above states the ADR-1287 rule; `rg -n "re-export" CLAUDE.md CONTRIBUTING.md docs README.md` shows no sentence of the old rule.
- Item bodies set through `sq` read back with no stray wrapper tags; `sq check` green.
- No code changes.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T11:21:58Z] `python-dev` Elias Python:
  - ST1 landed (uncommitted in the tree).
    
    - Moves: `_models/_config.py` to `squads/_config.py`; `_cli/__init__` code to `_cli/_app.py`; `_workflow/__init__` code to `_workflow/_bundled.py`. Inits now hold only re-exports: `_cli` (`app`, `main`, `run`) and `_workflow` (`bundled_spec`, `dropped_via_selected`, `CATEGORIES`, `ROSTER_*`, `WorkflowSpec`).
    - Deviation: new `_cli/_entry.py`. With the code in `_app.py`, the eager command modules (`_main`, `_import`, `_ui`) import `app` from `_app` while `_app` imported them, a `_app`/`_main` cycle at the `_cli` level that `test_every_package_level_is_acyclic` refuses. `_entry` now imports `_app` and registers the three modules; `_cli/__init__` re-exports from `_entry`. `_app` no longer imports them.
    - Guard: PENDING lists every private package except the three connector subpackages and `_specs`, which already satisfy the four rules and start outside it. Rule 4 skips the unused-re-export half for a package that is itself selected by name (the connectors); by-name modules are derived from the string constants of `_cli/_app.py`, `_sources/_registry.py`, `_sources/_converters.py` plus `_cli/_remote`.
    - Resolver: `tests/_import_scan.py` follows re-exports (`reexports`, `defining`); used by the write guard, the command-endpoint guard, the renderer guard and the services guard, with known-positive tests.
    - Gates: pyright, ruff check and format clean; `tests/meta` + `tests/cli/test_source*.py` 865 passed; `tests/daemon` 97 passed.
    - Bench (31 and 61 runs, HEAD vs tree on a migrated scratch copy): new/old median show 1.127/0.968, list 1.007/0.976, tree 0.944/0.959; within noise.
- [2026-11-04T11:28:41Z] `python-dev` Elias Python:
  - - ST2 landed (uncommitted in the tree): `_models` swept.
    - `_models/__init__` re-exports 73 names one aliased line each from direct children, plus `markers` as the namespace; `_models` left `PENDING`. Every outside importer (src and tests) goes through `squads._models`.
    - Deviation 1: the `_attributes as attrs` module-object imports (9 src files) became name imports. The roster accessors collide with locals (`model`, `template`, `origin`, `mission`...), so they are imported as `attr_<name>` aliases at the importer; `_models` exports the plain names.
    - Deviation 2: the `markers` line in the init carries `# noqa: F401` and a pyright ignore (a namespace alias reads as unused to both).
    - Tests: two meta tests that used the test-only `SKILL_GROUP_VERBS` read it through the `_participants` module object; the `_item as models_item` test import stays a module object.
    - Gates: pyright, ruff check and format clean; `tests/meta` 748 passed; `tests/cli/test_migrate.py` + `tests/daemon/test_remote_refusals.py` 69 passed.
    - Bench (31 runs, HEAD vs tree): new/old median show 0.912, list 0.929, tree 0.922; within noise.
- [2026-11-04T12:50:29Z] `python-dev` Elias Python:
  - - Part A (op-pierre ruling): `_models/_attributes` is re-exported as the namespace `attrs` (same noqa/pyright-ignore line as `markers`). The 9 importers are back to `from squads._models import attrs` and `attrs.X` call sites; `AttributeKey` stays a name import. The init dropped the 13 accessor and helper names no outside module imports by name (`agreements`, `can_spawn`, `capabilities`, `color`, `is_default`, `job_title`, `mission`, `model`, `origin`, `responsibilities`, `tech`, `template`, `flag_attribute`, `string_attribute`); `map_attribute`, `parse_invocable_choice` and the rest stay (name imports elsewhere). `grep -rn 'as attr_' src tests` = 0. Guard: `NAMESPACE_ALIASES` is now a dict alias to module (`ops`, `markers`, `attrs`).
    - ST3 landed (uncommitted): `_workflow`, `_roles`, `_interactions` have re-exporting inits, every outside import in src and tests goes through them, and the three left `PENDING`. 70 src files and 26 test files changed in total, Part A included.
    - Deviation 1: names only tests used (`BUNDLES`, `FIXED_IMPORT_KEYS`, `FIXED_OPTIONS`, `flag_name`, `COLOR_INTENTS`, `RESERVED_CLI_VERBS`, the validator-level tables, `validator_selection_key`) are not exported, per the exact-surface rule. Those 7 test files import the module object (`derived_names`, `workflow_models`, `validator_names`, `roles_catalog`) and write `module.NAME`. `role_guidance` (one test) became a name import of `allowed_create_types`; `_spec_documents` dropped `workflow_loader` for `load_workflow_spec`.
    - No import alias was needed; no name clash.
    - Gates: pyright 0 errors, ruff check and format clean; `tests/meta tests/check tests/cli tests/regressions tests/daemon` 2137 passed, 2 skipped, 0 failed (log: ~/.cache/sq-loop/st3.log).
    - Bench (31 runs, HEAD worktree vs tree, migrated copy): new/old median show 0.877, list 0.888, tree 0.890; within noise.
- [2026-11-04T12:53:38Z] `python-dev` Elias Python:
  - ST4 stopped before any edit: `RefEntry` is defined in both `_api/_dto/_refs.py` (used by `_cli/_render/_refs.py`, `_services/_item_read_dto.py`) and `_api/_dto/_skills.py` (used by `_services/_roster_ops.py`). Re-exporting both from `squads._api._dto` needs an import alias or a rename of the skill one (e.g. `SkillRefEntry`). Need a ruling. No other clash found across `_api/_dto` and `_api`.
- [2026-11-04T13:02:59Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-04): the RefEntry clash in _api/_dto is settled by renaming the skills entry (_dto/_skills.py) to SkillRefEntry; no import alias.
- [2026-11-04T13:05:42Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-04): in ST6, rename the internal MovedFile and LeftReference records of _services/_duplicate_ids.py (e.g. FileMove, StaleReference) so _corpus_ops.py imports the DTOs without the LeftReferenceDto/MovedFileDto aliases.
- [2026-11-04T13:11:33Z] `python-dev` Elias Python:
  - - ST4 landed (uncommitted): `_api/_dto` and `_api` have re-exporting inits, every outside import in src and tests goes through them, and both left `PENDING`.
      - Inits: `_api/_dto` re-exports the DTOs from direct children; `_api` re-exports its own modules' names, the DTOs from `squads._api._dto`, and `ops` as the namespace (`from squads._api import ops`, 25 importers; same noqa/pyright-ignore line as `markers` and `attrs`).
      - Ruling applied: `_dto/_skills.RefEntry` renamed `SkillRefEntry` (class, its two fields, the import and two constructions in `_services/_roster_ops.py`); no import alias. The `LeftReferenceDto` and `MovedFileDto` aliases in `_corpus_ops.py` are untouched.
      - Deviation 1: `ROUTED_OPERATIONS` is not re-exported. It is a lazy attribute of `_ops` that builds every group, and a name import in the init made `import squads._api` load all `_ops_<group>` modules (the by-name loading guard failed). `_daemon/_app.py`, `_daemon/_openapi.py` and four tests read `ops.ROUTED_OPERATIONS` instead.
      - Deviation 2: names only tests used (`DTO`, `Timeout`, `OPERATIONS`, `OVERRIDE_DOCUMENT`) are not exported. Tests read `ops.OPERATIONS`, or import the module object (`_base`, `_api`, `_vocabulary`, `_client`, `_ops`).
      - Gates: pyright 0 errors, ruff check and format clean; `tests/meta tests/daemon tests/cross_process tests/check tests/cli/test_skill.py` 1090 passed, 2 skipped, 0 failed (log: ~/.cache/sq-loop/st4.log).
      - Bench (31 runs, HEAD worktree vs tree): new/old median show 0.871, list 0.962, tree 0.917; within noise.
- [2026-11-04T13:22:50Z] `python-dev` Elias Python:
  - - ST5 landed (uncommitted in the tree): `_rendering`, `_index`, `_sources`, `_overrides`, `_board`, `_memory` have re-exporting inits, every outside import in src and tests goes through them, and all six left `PENDING`. The connector inits already met the rule and are untouched. 51 src and 14 test files changed.
    - Deviation 1: `_services/_board.py`, `_memory.py` and the four `credentials` importers had module-object imports (`board_store`, `memory_store`, `credentials`); they became name imports, so `_board` exports `post`/`list_notices`/`clear` and `_memory` exports `add`/`read`/`search`/`forget`/`list_entries` bare. No clash, no alias. Candidate for a namespace ruling (`memory_store`-style) if the bare names read badly.
    - Deviation 2: the guard's by-name set no longer counts a table file's own module (`_converters` names itself in `CONVERTERS`; `load_converter` runs inside it). Otherwise `_sources` could not re-export `load_converter`.
    - Deviation 3: names only tests used (manifest/stamp helpers, `_load_manifest`, `_load_store`, `_env_cache`, `store_path`, `board_folder`) are not exported; those tests import the module object (`override_manifest`, `override_stamp`, `sources_credentials`, `board_store`, `rendering_engine`). One monkeypatch now targets `override_manifest`.
    - Gates: pyright 0 errors, ruff check and format clean, `sq check` clean; `tests/meta tests/check tests/daemon tests/regressions tests/cli` 2137 passed, 2 skipped (logs ~/.cache/sq-loop/st5-a.log, st5-b.log).
    - Bench (61 runs, HEAD worktree vs tree, migrated copy): new/old median show 0.988, list 0.980, tree 0.996; within noise (a first 31-run pass read show 1.073 with overlapping quartiles; the longer run settled it).
- [2026-11-04T13:41:47Z, edited 2026-11-04T13:42:38Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-04): the board, memory and credential stores become classes the service holds as instances: self.board and self.memory (built with the squad paths) and self.credentials (a CredentialStore, an instance even without state), so calls read self.board.post(author, text), self.memory.read(role, slug), self.credentials.read_entry(url). Methods keep short names; no module-level store functions remain for outside callers, no namespace re-export and no import alias.
- [2026-11-04T13:44:39Z] `python-dev` Elias Python:
  - - ST6 landed (uncommitted in the tree), plus Part A.2. The A.1 store renames were withdrawn mid-run and reverted; store function names are unchanged.
      - A.2: `_services/_duplicate_ids.py` records renamed `FileMove` and `StaleReference` (also in `_results.py`, `_maintenance.py`); `_corpus_ops.py` now imports the DTOs `MovedFile` and `LeftReference` with no aliases. DTO names and JSON output unchanged.
      - ST6: `_backends/_claude_code`, `_backends/_agents_md`, `_backends`, `_migrations`, `_tui`, `_services` have re-exporting inits, every outside import in src and tests goes through them, all left `PENDING` (now `_cli`, `_cli/_render`, `_daemon`). `_services` init exports only `LocalApi` and `RequestScope`; `local_api()` and `_ui.py` keep their in-function imports. `_backends` re-exports `oneline` from the `_claude_code` init for the two migration runners.
      - Deviation: names only tests used (`BINDINGS`, `CATALOG`, `Service`, `build_service`, `MaintenanceMixin`, `CollabMixin`, import events, check-rule tables) are not exported; 10 test files import the module object (`bindings`, `validators`, `check_rules`, `service`, `maintenance`, `collab`, `import_model`). No import alias, no name clash.
      - Gates: pyright 0 errors, ruff check and format clean, `sq check` clean; `tests/meta tests/check tests/cli tests/daemon tests/regressions` 2137 passed, 2 skipped, 0 failed (log ~/.cache/sq-loop/st6.log).
      - Bench (41 runs, HEAD worktree vs tree): new/old median show 0.966, list 0.892, tree 0.882; within noise.
- [2026-11-04T13:52:19Z] `python-dev` Elias Python:
  - - Store classes landed (uncommitted), per the store ruling. The service holds `self.board` (BoardStore), `self.memory` (MemoryStore) and `self.credentials` (CredentialStore); the module-level store functions are gone.
      - `BoardStore(paths)`: `post`, `list_notices`, `clear`, plus `folder` (property) and `notice_path`. `MemoryStore(paths)`: `add`, `read`, `list_entries`, `search`, `forget`, plus `role_folder`/`memory_path`. `CredentialStore()`: `read_entry`, `write_entry`, `remove_entry`, `has_entry`, and `path()` (was `store_path`). Same files, modes, locks, errors, messages.
      - Pure helpers stay module-private functions (no store meaning): `normalise_base_url`, `_hash_id`, `_is_expired`, `_short_slug`. Inits export `BoardStore`, `MemoryStore`, `CredentialStore` (the four credential function exports left `_sources`).
      - Construction: `ServiceCore.__init__` builds all three beside `RosterProjection` (adding three `build_service` parameters would pass max-args 8). No name clash with existing `board`/`memory`/`credentials` on `Service` or its mixins.
      - Threaded: `_fetch.require_credential` and `resolve_identity_handles` take the `CredentialStore` first (callers `_source_links`, `_roster_ops`); `_pull`, `_source_links`, `_sources_ops` use `self.credentials`. No other non-service caller exists (`_overrides`, daemon do not touch the stores).
      - Tests: three files build `CredentialStore()` / `BoardStore(project)`; the writers guard names `BoardStore`/`MemoryStore` classes.
      - Gates: pyright 0, ruff check and format clean, `sq check` clean; `tests/meta tests/check tests/cli tests/daemon tests/regressions` 2137 passed, 2 skipped (log ~/.cache/sq-loop/stores.log). Bench (41 runs, HEAD worktree vs tree): new/old median show 0.971, list 0.993, tree 0.945; within noise.
- [2026-11-04T13:55:54Z] `python-dev` Elias Python:
  - ST7 stopped before any edit (tree reverted to HEAD): two name clashes in _cli/_render would force an import alias when the init re-exports. render_search is defined in _render/_search.py (used by _main.py) and in _render/_memory.py (used by _memory.py). render_updated is defined in _render/_writes.py (used by _items.py) and in _render/_roster.py (used by _operator.py, _skill.py, _role.py). No other clash across _cli/_render, _cli, _daemon. Options: (1) rename the memory one to render_memory_search and the roster one to render_roster_updated (the writes one keeps its name); (2) rename the other two instead (render_item_search, render_item_updated); (3) do not export one of each, and have its importers import the module object (_memory, _roster). Recommend 1, in line with the SkillRefEntry ruling. Need a ruling.
- [2026-11-04T13:56:11Z] `manager` Catherine Manager:
  - ST7 clashes settled under op-pierre's SkillRefEntry precedent (rename the narrower one, no alias): _render/_memory.render_search -> render_memory_search, _render/_roster.render_updated -> render_roster_updated; the _search and _writes versions keep their names.
- [2026-11-04T14:04:56Z] `python-dev` Elias Python:
  - - ST7 landed (uncommitted in the tree): `_cli/_render`, `_cli`, `_daemon` have re-exporting inits and `PENDING` is deleted, so the four rules and per-level acyclicity hold for every private package.
      - Ruling applied (Catherine, option 1): `_render/_memory.render_search` is now `render_memory_search` and `_render/_roster.render_updated` is `render_roster_updated`, with their callers. No import alias.
      - `_cli/_render` init re-exports 85 renderer names; `_common.py` and `_workflow_cmd.py` now take them by name instead of the `comment_render`, `write_render` and `render` module objects. The `_cli` init gains `build_console` (re-exported from `_common`) for `_daemon/_proxies.py`; `_daemon` init exports `run_daemon`, and `_cli/_daemon.py` imports it from the init inside its function.
      - Deviation 1: `_common.print_comments` and the `_is_styled`, `_render_comments_plain`, `_render_comments_styled` helpers it alone used had no callers in src or tests, and the name clashed with the renderer `print_comments`; the dead cluster is deleted.
      - Deviation 2: names only tests used (`LAZY_GROUPS`, `main_callback`, `build_app`, `Daemon`, `fingerprint`, `DaemonState` and the like) are not exported; 16 test files import the module object (`cli_app`, `cli_remote`, `daemon_lifecycle`, ...).
      - Deviation 3: two `"""None"""` init docstrings (`_daemon`, `_interactions`) from the rewrite script now read as real docstrings.
      - Guard: `PENDING`, its test and the `pending` parameters are gone; the synthetic-package tests drop the pending cases.
      - Gates: pyright 0 errors, ruff check and format clean, `sq check` clean; `tests/meta tests/check tests/cli tests/daemon tests/regressions tests/cross_process` 2163 passed, 2 skipped, 0 failed (log ~/.cache/sq-loop/st7.log).
      - Bench (41 runs, tree as new): vs HEAD show 1.055, list 1.006, tree 0.921 (show re-run with 61 runs: 0.926, 0.988, 0.990); vs the build before the sweep (b0c9ecaa) show 0.868, list 0.950, tree 0.905. Within noise; worktrees removed.
- [2026-11-04T14:07:24Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-04): tests keep importing private module objects under an alias (no pyright private-usage exceptions), but each module gets one alias used everywhere, named <package>_<module> without underscores (e.g. cli_common, cli_app, api_api).
- [2026-11-04T14:11:03Z] `tech-writer` Theo Writer:
  - - ST8 done (uncommitted in the tree), docs only, every path and name checked against `src/`.
      - `CLAUDE.md`: the module-privacy paragraph states the rule (re-export from direct children only, one statement per package, sibling imports inside a package, `ops`/`markers`/`attrs` namespaces, top-level `squads/__init__` exempt, by-name modules never imported by an init, test import forms) and names the guard's rules in place of the old init list. Map: `_models` imports only `_clock`, `_errors`, `_util`; new `_config.py` entry; `_workflow/_bundled.py`; `_cli/_app.py` + `_cli/_entry.py`, with `LAZY_GROUPS` in `_app.py`; renderer guard names `squads._config`; connector subpackages imported by name from `_registry.py`; `ServiceCore` holds `self.board`/`self.memory`/`self.credentials` (`BoardStore`, `MemoryStore`, `CredentialStore`).
      - `CONTRIBUTING.md`: the Private layout bullet and the `LAZY_GROUPS` row now in `_cli/_app.py`.
      - `docs/internals.md` layout note, `docs/stability.md` Tier 4, README conventions paragraph: state the rule with no import path made public.
      - `docs/backends.md`: the add-a-backend example imported through module paths (and took `RoleView` from `_backends._base`); now `from squads._models import Item`, `from squads._roles import RoleDef, RoleView`, a `_cursor/__init__` re-export, and the registry importing from `squads._backends._cursor`.
      - GUIDE-79: cross-cutting conventions cite ADR-1287 (ref added); the models paragraph no longer lists the config or the enums. Body read back identical, zero wrapper tags.
      - Gate: `tests/meta` 747 passed (log `~/.cache/sq-loop/st8-meta.log`); `sq check` clean.
- [2026-11-04T14:12:53Z] `tech-writer` Theo Writer:
  - Follow-up docs: GUIDE-79 sub-entities paragraph says badges and the roll-up table are computed on read and a write re-renders only the heading; docs/internals.md section 11 says squads.__main__:main runs squads._shim:main (daemon, else squads._cli:main); CLAUDE.md and CONTRIBUTING.md state the test module-object alias rule (one alias, <package>_<module>, per the op-pierre ruling). tests/meta 747 passed; sq check clean.
- [2026-11-04T14:13:23Z] `python-dev` Elias Python:
  - Test module aliases renamed to one per module, <package>_<module> with underscores dropped (37 modules, 29 test files, incl. two fixture strings). Also dropped "swept" from three guard test names in the import-edges table test. Gates green: pyright 0 errors, ruff check and format clean, pytest -n 4 2163 passed 2 skipped, 0 failed.
<!-- sq:discussion:end -->
