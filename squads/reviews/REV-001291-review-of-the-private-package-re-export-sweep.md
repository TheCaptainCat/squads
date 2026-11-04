---
id: REV-1291
sequence_id: 1291
type: review
title: Review of the private-package re-export sweep
status: Approved
author: reviewer
refs:
- FEAT-1288
- TASK-1289
description: Guard, resolver, stores, behaviour, startup and docs of the re-export
  sweep
subentities:
- local_id: F1
  title: Guard accepts an underscore name re-exported by an init
  status: Verified
  severity: low
- local_id: F2
  title: No-reach-in rule misses a literal import_module call
  status: Verified
  severity: low
- local_id: F3
  title: Some test module-object imports skip the one-alias naming ruling
  status: Verified
  severity: low
- local_id: F4
  title: Dead inits_with_code helper left in the import-edge guard
  status: Verified
  severity: info
- local_id: F5
  title: Two comments still point to code moved out of the cli and workflow inits
  status: Verified
  severity: info
created_at: '2026-11-04T14:33:48Z'
updated_at: '2026-11-04T15:17:32Z'
target_ref: b0c9ecaa..fe524f16
---
<!-- sq:body -->
## Scope

Batch review of the private-package re-export sweep, `b0c9ecaa..fe524f16` on release/0.20: the guard and resolver, the three moves (`_config.py`, `_cli/_app.py` + `_cli/_entry.py`, `_workflow/_bundled.py`), every package init, the store classes, the test aliases, and the documents (CLAUDE.md, CONTRIBUTING.md, README.md, docs/, GUIDE-79). Design authority: ADR-1287 with op-pierre's rulings on it and on TASK-1289.

## What was driven

All probes ran on extracted copies of both builds under `~/.cache/sq-review` (each with its own `uv sync --all-extras`), never on the repository.

- **Guard falsification.** I planted 21 violations one at a time in the fe524f16 copy and ran the import-edge guard after each. These fail as they should: code in an init, a relative import in an init, an init taking a name from a grandchild, reach-in from `src` (from-import, module-object import, `import a.b.c`, in a function, under `TYPE_CHECKING`, into a nested package), reach-out (own init, enclosing init), an unused re-export, a re-export used only by tests, a sibling cycle inside a package, a top-level package cycle, and test name-imports from a module path (at top level and in a function). Two pass when they should fail (findings F1 and F2).
- **Resolver-backed guards.** None passes vacuously. For each one I planted an import whose spelling names only a package init, while the defining module is forbidden. Each plant made its guard fail: the renderer guard and the TUI transitive guard (`from squads._cli import build_console`, defined in `_cli/_common.py`), the write guard (`BoardStore(...).post` through `squads._board`), the command-endpoint guard (`HttpApi` and `Connect` through `squads._api`), and the services guard.
- **Behaviour.** I ran 47 read commands and 18 write commands with both builds, in local mode, on a migrated copy of this squad: outputs, error messages, exit codes and `--json` shapes. After normalising timestamps, hashes and paths, the outputs are identical, and the squad trees differ only in timestamps. The checked moves are pure moves: `_cli/__init__` to `_app.py` (the side-effect imports went to `_entry.py`), `_workflow/__init__` to `_bundled.py`, `_models/_config.py` to `_config.py`. The deleted `_common.print_comments` cluster had no caller in the old tree.
- **Startup.** The shim's import set is unchanged (3 modules). `sq --help` loads no `_services`, `_daemon` or `_tui` module, and neither does `import squads._cli`. Median of 21 interleaved runs: `sq --help` 605 ms before, 626 ms after (+21 ms, within the ADR's 25 ms estimate); `list --json` and `task show` within noise; `import squads._cli` alone +140 ms, because the renderer, DTO and `_api._client` modules now load eagerly (local commands loaded them anyway).
- **Stores.** `BoardStore`, `MemoryStore` and `CredentialStore` keep the same files, locks, errors and messages. `ServiceCore.__init__` builds them from `self.paths`. No module-level state was added. `vulture` reports nothing new compared with the old build.
- **Aliases.** Outside a package, `src` has no import alias beyond the rulings: the `ops`/`markers`/`attrs` namespaces and pre-existing aliases (`Envelope`, `run_cli`, `cli_main`). Test aliases: see F3.
- **Gates.** `ruff check` and `ruff format --check` pass on fe524f16. `sq check` passes on the board.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1291 add-finding "…" --severity medium`; track with `sq review 1291 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Guard accepts an underscore name re-exported by an init

<!-- sq:finding:F1:body -->
**Where.** `tests/meta/test_package_import_edges_match_the_recorded_table.py`: `init_shape` and `exact_surface`.

**Scenario.** ADR-1287 section 1, CLAUDE.md and CONTRIBUTING.md all state that an underscore name is never re-exported. The guard does not hold that rule. I planted `from squads._board._store import _hash_id as _hash_id` in `src/squads/_board/__init__.py` and `from squads._board import _hash_id` in `src/squads/_services/_board.py`, then ran the guard module: 51 passed. `init_shape` checks only the `Name as Name` spelling and the direct-child source. `exact_surface` sees an outside user, so it accepts the name. The same gap lets an init re-export a child's private submodule (`from squads._api._dto import _items as _items`). Today no init re-exports an underscore name, so the gap is latent.

**Fix.** In `init_shape`, refuse a non-namespace re-export whose bound name starts with `_`, with a message saying the name must lose its underscore. Add the case to `test_the_init_shape_rule_accepts_re_exports_and_refuses_code`.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-11-04T14:52:38Z] `python-dev` Elias Python:
  - init_shape now refuses an init re-exporting an underscore name (private submodule included); planted-case rows added to the init-shape test.
- [2026-11-04T15:11:23Z] `reviewer` Paul Reviewer:
  - Verified on a 70546bf9 copy: underscore name re-exported by _board init (with an outside user), _items and _base private submodules re-exported by _api/_dto and _api inits, and an unaliased underscore name each fail the guard; baseline with ops/markers/attrs passes (48 passed).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — No-reach-in rule misses a literal import_module call

<!-- sq:finding:F2:body -->
**Where.** `tests/meta/test_package_import_edges_match_the_recorded_table.py`: `_Walker.visit_Call`.

**Scenario.** The walker records a literal `importlib.import_module("squads._models._item")` as an edge, but it never calls `_bind`, so the call never becomes a `Statement` and rules 2 and 3 do not see it. I planted `importlib.import_module('squads._models._item')` at module top in `src/squads/_cli/_common.py`: the guard passed (51 passed). The other import guards (`tests/_import_scan.py` and the guards built on it) count a literal `import_module` call as an import, so this guard is the only one that misses it. Today `src` selects modules by name only through variables (`LAZY_GROUPS`, `CONNECTORS`), so nothing breaches.

**Fix.** In `visit_Call`, also bind the literal target, `self._bind(literal, None, node.lineno)`, so a literal import of a module path inside another package counts as a reach-in. Add one synthetic case.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-11-04T14:52:39Z] `python-dev` Elias Python:
  - _Walker.visit_Call binds a literal import_module target, so rules 2 and 3 see it; new test plants one from outside the package.
- [2026-11-04T15:11:24Z] `reviewer` Paul Reviewer:
  - Verified: literal import_module of squads._models._item from _cli/_common (top) and _services/_board (in a function), and from-importlib import_module of squads._board._store from _views, each fail as reach-in; a literal load inside _models and the by-name loads in src (_ops, _app, _registry, _converters, _transform) pass.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Some test module-object imports skip the one-alias naming ruling

<!-- sq:finding:F3:body -->
**Where.** Test module-object imports that the op-pierre ruling on TASK-1289 (one alias per module, `<package>_<module>` without underscores) did not reach:

- `tests/_write_guard.py:13`, `tests/conftest.py:17`, `tests/daemon/test_remote_refusals.py:13`: `from squads import _aio`
- `tests/daemon/test_remote_refusals.py:14`: `from squads._api import ... _client`
- `tests/meta/test_every_dto_field_is_json_native.py:12-13`: `import squads._api._dto as dto_package`, `from squads._api._dto import _base`
- `tests/meta/test_the_operation_table_lists_every_operation_its_groups_define.py:9-10`: `import squads._api as api_package`, `from squads._api import Operation, _ops` (elsewhere the tests read this module as the `ops` namespace)
- `tests/meta/test_the_parser_reads_only_the_documents_the_vocabulary_hash_covers.py:11`: `_vocabulary`
- `tests/meta/test_every_cli_command_is_named_in_agent_guidance.py:12`: `_managed_region`
- `tests/cli/test_docs_ui.py:9`, `tests/meta/test_bundled_docs_registry.py:13`, `tests/meta/test_documented_commands_resolve_against_cli.py:11`: `from squads import _docfiles`
- `tests/meta/test_roster_group_verbs_match_the_live_command_table.py:11`, `tests/meta/test_the_openapi_document_describes_every_operation.py:68`: `_participants`
- `tests/meta/test_index_reconcile_resolves_no_vocabulary.py:10`: `import squads._index._reconcile as reconcile`

**Scenario.** I listed every test import that binds a `squads` module object, with an AST scan of `tests/`. Every other module follows the ruling (`squads_clock`, `cli_common`, `services_checkrules`, ...). The modules above keep the bare underscore name or an older alias, so a reader still meets two spellings for one module.

**Fix.** Rename these to the ruling's form (`squads_aio`, `api_client`, `dto_base`, `api_ops` or the `ops` namespace, `api_vocabulary`, `backends_managedregion`, `squads_docfiles`, `models_participants`, `index_reconcile`, and `api_dto`/`squads_api` for the package objects).
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-11-04T14:52:40Z] `python-dev` Elias Python:
  - Remaining test module imports renamed to <package>_<module> (squads_aio, squads_docfiles, api_client, api_vocabulary, apidto_base, api_dto, squads_api, models_participants, backends_managedregion, index_reconcile); the operation-table test reads ops.
- [2026-11-04T15:11:32Z] `reviewer` Paul Reviewer:
  - Reopened. Two cases break the ruling (an AST scan of every module-object import in tests): (1) tests/meta/test_every_dto_field_is_json_native.py:13 aliases _api._dto._base as apidto_base; every other alias names the immediate parent package only (api_dto for _api._dto, cli_common, daemon_app), so the consistent form is dto_base. (2) squads._migrations is still imported as migrations_pkg in tests/meta/test_a_migration_runner_never_raises_a_refused_command.py:9 and tests/meta/test_migration_runners_use_the_runs_resolved_vocabulary.py:9; the ruling form is squads_migrations. My original F3 list missed (2). @python-dev rename both; the other 46 aliased modules conform.
- [2026-11-04T15:13:27Z] `python-dev` Elias Python:
  - Renamed apidto_base to dto_base and migrations_pkg to squads_migrations; one alias per module confirmed across tests.
- [2026-11-04T15:15:23Z] `python-dev` Elias Python:
  - Also renamed import squads._shim as shim to squads_shim in tests/daemon/test_the_shim_over_the_loopback_port.py; both import forms re-checked, one alias per module.
- [2026-11-04T15:17:24Z] `manager` Catherine Manager:
  - Verified: every real test import of a private module, in both import forms, has one alias in the ruled form (53 modules); the remaining doubles are synthetic source strings the guard tests feed to the guard.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Dead inits_with_code helper left in the import-edge guard

<!-- sq:finding:F4:body -->
**Where.** `tests/meta/test_package_import_edges_match_the_recorded_table.py:246`, `inits_with_code`.

**Scenario.** The sweep deleted the test that called `inits_with_code` along with `INITS_WITH_CODE`, but the function stayed. `rg inits_with_code src tests` finds only its definition. The new `init_shape` rule replaces it.

**Fix.** Delete the function.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-11-04T14:52:41Z] `python-dev` Elias Python:
  - Deleted the unused inits_with_code helper.
- [2026-11-04T15:11:25Z] `reviewer` Paul Reviewer:
  - Verified: rg inits_with_code src tests finds nothing.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Two comments still point to code moved out of the cli and workflow inits

<!-- sq:finding:F5:body -->
**Where.**
- `src/squads/_services/_base.py:726-727`: the comment says `dropped_via_selected` lives in `_workflow/__init__.py`. It is now in `_workflow/_bundled.py`.
- `tests/meta/test_ambient_render_state_reset_is_exhaustive.py:18`: the comment points to `_cli/__init__.py`'s docstring for `main_callback`. The callback and its docstring are now in `_cli/_app.py`, and `_cli/__init__.py` holds only re-exports.

**Scenario.** The sweep moved the code and left these two comments behind. `rg "_cli/__init__|_workflow/__init__" src tests` finds only these two lines.

**Fix.** Point both comments to the module that now holds the code: `_workflow/_bundled.py` and `_cli/_app.py`.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-11-04T14:52:42Z] `python-dev` Elias Python:
  - Comments now name _workflow/_bundled.py and _cli/_app.py.
- [2026-11-04T15:11:26Z] `reviewer` Paul Reviewer:
  - Verified: both comments name the modules that now hold dropped_via_selected and main_callback; rg for the old init paths finds nothing.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T14:34:35Z] `reviewer` Paul Reviewer:
  - Five findings, all low or info; no correctness, behaviour or startup defect found. Recommended verdict: approve once F1 to F5 are fixed or waived. @tech-lead F1 and F2 tighten the guard; F3 to F5 are cleanups.
- [2026-11-04T14:34:54Z] `reviewer` Paul Reviewer:
  - ChangesRequested on low and info findings only. @python-dev F1 to F5 are small; F1 and F2 each need one synthetic guard case.
- [2026-11-04T15:17:32Z] `manager` Catherine Manager:
  - Approved: F1-F5 Verified; full suite 2180 passed.
<!-- sq:discussion:end -->
