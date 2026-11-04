---
id: ADR-1287
sequence_id: 1287
type: decision
title: Private packages re-export their outside-used names
status: Accepted
author: architect
refs:
- GUIDE-79
- ADR-78
description: Every private package's init re-exports exactly the names other packages
  import, so an importer writes one statement per package; the guard holds init shape,
  no reach-in and an exact surface
created_at: '2026-11-04T10:58:24Z'
updated_at: '2026-11-04T12:42:18Z'
---
<!-- sq:body -->
## Context

ADR-78 made every implementation module and subpackage underscore-private and forbade package `__init__`s from re-exporting, so an importer names the defining module (`from squads._models._item import Item`). The privacy half holds. The no-re-export half makes every importer track the internal file layout of the packages it uses: moving a class between two modules of `_models` rewrites importers in every other package, and an importer of five names from one package writes up to five import lines. Of the private packages, 21 are imported from outside themselves, through about 830 import statements in `src` that name a module inside another package (measured below). The connector subpackages `_sources/_gitlab`, `_github` and `_jira` already re-export their public names.

op-pierre ruled on ADR-78 (2026-11-04) that the no-re-export rule binds only the top-level `squads/__init__` and public packages; every private subpackage re-exports the names other packages use. This decision states that rule precisely and the guard that holds it, and narrows ADR-78's no-re-export clause, which ADR-78 amends in place (related, not superseded). The rest of ADR-78 stands: underscore privacy, the acyclic graph, and the recorded package-edge table.

## Decision

### 1. The rule

- **Which packages.** Every private package under `src/squads` re-exports, nested ones included (`_api/_dto`, `_backends/_claude_code`, `_backends/_agents_md`, `_cli/_render`, the connector subpackages). The top-level `squads/__init__` does not: it holds `__version__` and `version_line` and nothing else, because the shim loads it on every command.
- **Which names.** Exactly the names a module outside the package imports from it, in `src`. Not the package's whole internal surface, and not names only tests use. A re-export no `src` module outside the package imports is dead and the guard refuses it. An underscore name is never re-exported: a name another package needs is package-public and loses its underscore (today no `src` module imports another package's underscore name; only tests do).
- **Spelling.** One statement per name, absolute, with the redundant alias that marks an explicit re-export: `from squads._models._item import Item as Item`. Ruff keeps each aliased import on its own line, so a re-export is one line of diff. No `__all__` (the one in `_workflow/__init__` goes) and no relative import (the edge walker refuses them).
- **Where an init takes a name from.** Only from its direct children: `_api/__init__` re-exports DTOs from `squads._api._dto`, which re-exports them from its own modules. A name travels up one level at a time.
- **What an init holds.** Only those re-export statements and an optional docstring. Code moves to a module: `_cli/__init__` (the Typer app, the root callback, `LAZY_GROUPS`, the side-effect imports of the eager command modules) moves to `_cli/_app.py`; `_workflow/__init__` (`bundled_spec`, `dropped_via_selected`, the bundled-spec constant) moves to `_workflow/_bundled.py`. The data package `_specs` keeps a docstring-only init.
- **What an importer writes.** A module outside a package imports through the init of the outermost package that holds the target and not the importer: `_cli/_items.py` writes `from squads._models import Item, SubEntity`; `_migrations` writes `from squads._backends import ClaudeCodeBackend`; `_backends/_registry.py`, inside `_backends`, writes `from squads._backends._claude_code import ClaudeCodeBackend`. Ruff merges the names of one package into one statement, so an importer has one import statement per package.
- **Inside a package.** A module imports its sibling modules directly (`from squads._backends._base import AgentBackend`) and never through its own package's init or an enclosing package's init. A module executes while its package's init is partly run, so a name taken from that init can be unbound; a direct sibling import cannot be.
- **Namespace imports.** A module of constants read as `ns.NAME` may be re-exported as a namespace under its unprefixed name, one line in the init: `from squads._api import _ops as ops` in `_api/__init__`, so an importer writes `from squads._api import ops`. This applies to the operation table (`ops`, 22 importing files reading about 350 constants) and the marker tags (`markers`, 24 files). Every other module-object import across a package (`_attributes as attrs`, `_credentials as credentials`, `_store as board_store`, `_loader as workflow_loader`, `_common as common`) becomes a name import. The cross-package alias form for top-level modules (`from squads import _clock as clock`) is unchanged: a top-level module is not a package.
- **TYPE_CHECKING and in-function imports** follow the same rule as top-level ones.
- **Tests.** A test imports a name through the init when the init re-exports it, and never writes `from squads._pkg._module import Name`. A test that monkeypatches, or needs a name the init does not re-export (an underscore helper, a name only tests use, a name of a lazily loaded command module), imports the module object: `from squads._cli import _create`, then `_create._CustomCreateGroup`. A patch targets the module where the name is looked up, which a re-export does not change.

### 2. Cycles

Python runs every enclosing package's init before any submodule, so once inits re-export, importing anything from a package runs the modules that define its re-exported names. That closes a cycle only where the graph with packages collapsed to nodes has one. Measured on the current tree:

- **Between top-level packages, over top-level imports:** no strongly connected component (the edge guard's `TOP_EDGE_COMPONENT` is empty and holds it).
- **Inside each package, with its child modules and subpackages collapsed to nodes, over top-level imports:** acyclic at every level, for the root and all 25 private packages.
- **In-function imports kept to avoid a cycle:** exactly four edges would close one if moved to module top: `_cli -> _daemon` (`_cli/_daemon.py`, `run_daemon`), `_interactions -> _overrides` (`_interactions/_loader.py`), `_workflow -> _migrations` (`_workflow/_validity.py`, the reserved-command hint) and `_workflow -> _overrides` (`_workflow/_loader.py`, the override stamp check). None runs while a module is being imported; `import squads._workflow` runs `load_workflow_spec()` at import and that path reaches only `_context`, `_models` and `_parse_cache`.

The rule handles them with no special mechanism: an in-function import stays in the function and imports from the package init (`from squads._overrides import WORKFLOW_KEY, artifact_changed_since`). It loads the package's re-exported modules on the first call, when every init has finished. There is no lazy `__getattr__` and no exception list. The remaining in-function imports (`_cli` reaching `_services`, `_tui`, `_docfiles`, `_clock`; `_shim` reaching `_cli`; `_index` reaching `_actor`) close no cycle; they follow the same spelling. An in-function import between two modules of one package (`_cli/_common.py` reaching `_cli/_calls.py`) is a sibling import and stays direct.

One package relationship changes because of the rule: `_models/_config.py` (`SquadsConfig`) moves out of `_models` to a top-level module `squads/_config.py`. With a re-exporting `_models` init, any import of `_models` (and `_api` imports it) loads `_config`, and the terminal UI's transitive guard, which keeps `_tui` off the configuration model through every module it loads, would fail. Moving `_config` keeps that check as strong as it is; its six `src` importers change one line each and the edge table gains a `_config` node.

### 3. Startup cost

The cost of a re-exporting init is the modules it now loads that its importer did not need. Measured as the time to import every module of a package on top of the modules a command already loads today (median of five runs, local mode, this machine; `import squads._cli` takes about 300 ms):

| Package | over `sq --help` | over `sq list --json` |
|---|---|---|
| `_api` (without `_client`) | 4.5 ms | 0.0 ms |
| `_api._dto` | 1.9 ms | 1.0 ms |
| `_api._client` (the HTTP client) | about +3 ms | +0.3 ms |
| `_sources` (without connectors) | 5.3 ms | 0.4 ms |
| `_cli._render` | 3.4 ms | 1.7 ms |
| `_index`, `_overrides`, `_migrations`, `_memory`, `_board`, `_models` | 0.4 to 3.1 ms each | 0.0 to 0.3 ms |
| `_services` | 72 ms | 0.1 ms |
| `_daemon` | 168 ms | 88 ms |
| `_tui` (Textual) | 152 ms | 162 ms |

These are upper bounds: an init loads only the children whose names an outsider uses. What must stay out of an init's eager reach:

- **The shim's import set.** `squads/__init__`, `_shim`, `_endpoint`, `_daemon_start` and `_daemon_link` are top-level modules, not package members, and stay so: a package's init would join the shim's standard-library-only import set. `squads/__init__` does not re-export. `_endpoint` keeps its lean imports (no `dataclasses`, `typing`, `importlib.metadata`); it reaches `squads` and `_windows_owner` only in functions.
- **Modules selected by name at run time** are never imported by their package's init: the lazy command groups (the modules `LAZY_GROUPS` names, and `_cli/_remote.py`) and the connector subpackages the `_sources/_registry.py` table imports by name. No `src` module outside the package imports a name from them; the rule's "names an outsider uses" already keeps them out, and the guard derives the set from those two tables to say so in its message.
- **`_services`, `_daemon` and `_tui`** stay reached only through the in-function imports they have today (`_cli/_calls.local_api()`, `_cli/_daemon.py`, `_cli/_ui.py`) or from `_daemon`; `sq --help` loads none of them, and `_services` is the 72 ms that matters.

A package a command does not touch today stays untouched, so the added cost falls only on packages a command already loads in part. Summed over those, the upper bound is about 4 ms on a local `sq list` (renderers, DTOs, `_sources`, `_client`, `_migrations`) and about 25 ms on a local `sq --help`; a served command pays nothing, the daemon having loaded everything. These are per-package measurements, not an end-to-end run of the swept tree. Each sweep step runs `scripts/bench_local_mode.py` against the previous build, and a step whose bench moves beyond run-to-run noise stops for a decision before it lands (the remedy is to move the heavy module out of the package, as with `_config`, not to exempt it).

### 4. The guard

`tests/meta/test_package_import_edges_match_the_recorded_table.py` drops `INITS_WITH_CODE` and holds four rules, each derived from the tree, with no per-package list:

1. **Init shape.** Every `__init__.py` under `src/squads` other than `squads/__init__.py` holds an optional docstring and statements of the form `from squads.<pkg>.<child> import Name as Name`, where `<child>` is a direct child of that package, plus the namespace form `from squads.<pkg> import _child as child` for `ops` and `markers`. No other statement.
2. **No reach-in.** A `src` module outside a package does not import a module path inside it (`from squads._models._item import Item`, `import squads._models._item`, `from squads._models import _item`), at module top, in a function or under `TYPE_CHECKING`. A test does not `from`-import a name from a module path; it may import a module object.
3. **No reach-out.** A module does not import a name from the init of its own package or of an enclosing package. Importing a sibling module object through the package name (`from squads._cli import _calls as calls`) stays allowed: it binds the submodule, which a partly run init does not affect.
4. **Exact surface.** Every re-export is imported from that package by some `src` module outside it, and no `src` module outside it needs a name the init lacks (rule 2 covers the second half). A re-export from a module selected by name at run time fails with a message naming the table.

Alongside, `test_every_package_level_is_acyclic` holds the per-level acyclicity of section 2 over top-level imports, since a re-exporting nested init depends on it and the node-level component check cannot see inside a node.

**The edge table does not change shape.** The walker reduces an import to the node of the module it names, and `from squads._models import Item` reduces to `_models` as `from squads._models._item import Item` did, so the sweep leaves `EDGES` rows as they are. The rows that do change: the new `_config` node and its edges, and any `local` row whose last in-function import is removed. The walker's synthetic cases stay.

**Guards that match a module inside a package resolve re-exports.** A re-export hides the defining module from a guard that reads import statements by qualified name: `from squads._board import post` would pass a check written against `squads._board._store.post`. `tests/_import_scan.py` gains one resolver that follows each init's re-export statements back to the defining module, and the guards that name an inner module use it: the CLI and TUI no-write guard, the command-endpoint guard (`squads._api._client`, `squads._cli._remote`), the renderer guard (`squads._config` replaces `squads._models._config`) and the CLI-to-services guard. Without it each of them passes vacuously after the sweep. The mutable-state allowlist entries for `_cli/__init__.py` and `_workflow/__init__.py` move with their code.

### 5. Documentation to correct

- **CLAUDE.md** (the repository file; not the managed region, and the managed template `templates/claude/claude_section.md.j2` does not state the rule): the "Module privacy convention" paragraph (the no-re-export sentence, the example import, the list of non-empty inits, the connector-subpackage exception); the `_models/` line (`_config` moves out to its own top-level entry); the `_workflow/` line (`__init__ exposes bundled_spec()` becomes `_bundled.py`, re-exported); the `_cli/` line and the `LAZY_GROUPS in _cli/__init__.py` sentence (`_cli/_app.py`); the renderer guard sentence (`squads._config`). Architecture-map lines that name a module file as the place code lives (`_index/_store.py`, `_services/_bindings.py`, …) stay true and do not change; only lines that show an import spelling or an init's content do.
- **CONTRIBUTING.md** "Private layout" bullet (the no-re-export sentence and the init list), and the lazy-command-table sentence that names `_cli/__init__.py`.
- **docs/internals.md** (the private-layout note), **docs/stability.md** Tier 4 (it states that internal modules are not re-exported by package inits; the point it serves, that no import path is public API, stands) and the **README** conventions paragraph. These are adopter-facing and go to the technical writer.
- **GUIDE-79** "Cross-cutting conventions" ("package inits that don't re-export") points to this decision.

### 6. Sweep plan

One step per package, leaves first along the top-edge order, each step green on the gate (pyright, ruff, `tests/meta`, the full suite, `sq check`). Each step writes the package's init, rewrites every outside import of its modules in `src` and the test name-imports, and deletes the package from a transitional `PENDING` set that rules 1 to 4 skip. Step 0 lands the guard with every package in `PENDING`; the last step deletes the set, so a swept package cannot regress meanwhile.

Counts are distinct import statements that name a module path inside the package from outside it (`src` statements / `src` files / test name-import statements):

| Step | Package | src stmts | src files | test stmts |
|---|---|---|---|---|
| 0 | Guard, resolver, `PENDING`; move `_models/_config.py` to `squads/_config.py`, `_cli/__init__` to `_cli/_app.py`, `_workflow/__init__` code to `_workflow/_bundled.py` | 6 | 6 | — |
| 1 | `_models` | 223 | 93 | 10 |
| 2 | `_workflow` | 69 | 56 | 27 |
| 3 | `_api/_dto`, then `_api` (with `ops`) | 24 + 231 | 8 + 77 | 22 |
| 4 | `_roles` | 70 | 31 | 12 |
| 5 | `_interactions` | 52 | 23 | 9 |
| 6 | `_rendering` | 14 | 11 | 2 |
| 7 | `_index` | 30 | 25 | 3 |
| 8 | `_sources` | 25 | 10 | 4 |
| 9 | `_overrides` | 4 | 4 | 7 |
| 10 | `_board`, `_memory` | 4 + 4 | 2 + 2 | 1 |
| 11 | `_backends/_claude_code`, `_backends/_agents_md`, then `_backends` | 1 + 1 + 11 | 11 | 1 |
| 12 | `_migrations` | 9 | 6 | 0 |
| 13 | `_tui` | 1 | 1 | 2 |
| 14 | `_services` | 4 | 3 | 13 |
| 15 | `_cli/_render`, then `_cli` | 49 + 1 | 16 + 1 | 11 |
| 16 | `_daemon`; delete `PENDING`; docs (section 5) | 1 | 1 | 8 |

About 830 `src` statements and 130 test statements change; ruff merges many of them, so the line count after is lower. Steps 1 and 3 are the large ones and can each be split by importing package without breaking greenness, since both import forms work until the package leaves `PENDING`.

## Consequences

- An importer names the package, not the module: one import statement per package, and moving code between modules of a package changes only that package's init.
- Every package has a stated internal surface, the set of its re-exports, held exact by the guard in both directions. Still nothing is public: every package is underscore-private, and docs/stability.md keeps no import path in the contract.
- Importing from a package loads every module whose names it re-exports. The graph stays acyclic at every package level, which a guard now holds, and the shim's import set and the lazy command and connector tables are kept out of reach by construction.
- Guards that name a module inside a package depend on one re-export resolver; a new guard of that kind uses it too.
- Two inits that hold code lose it to a module (`_cli/_app.py`, `_workflow/_bundled.py`), and the configuration model becomes a top-level module.

## Amendments

- 2026-11-04: per op-pierre's acceptance ruling, this decision relates to ADR-78 rather than superseding it; ADR-78's no-re-export clause is narrowed in place to the top-level `squads/__init__` and public packages.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T10:58:44Z] `architect` Robert Architect:
  - Drafted from measurements on release/0.20: per-level acyclicity, the four cycle-avoiding in-function edges, per-package import cost, and import-statement counts per package (scripts in the session scratchpad, not committed).
  - @op-pierre open points: (1) namespace re-exports for ops and markers only, (2) init holds re-exports only, moving _cli/__init__ to _cli/_app.py and _workflow/__init__ to _workflow/_bundled.py, (3) _models/_config.py to squads/_config.py, forced by the TUI transitive guard, (4) supersedes vs amend-and-relate for ADR-78 under the board rule. @tech-lead the sweep plan in section 6 is ready to cut into a task once accepted.
- [2026-11-04T11:05:11Z] `op-pierre` Pierre Chat:
  - Accepted (2026-11-04) with the four recommendations: ops and markers re-exported as namespaces, every other cross-package module import a name import; inits hold only re-exports (code moves to _cli/_app.py and _workflow/_bundled.py); _models/_config.py moves to squads/_config.py; ADR-78 is related, not superseded, and its no-re-export sentence is narrowed in place.
- [2026-11-04T11:06:45Z] `architect` Robert Architect:
  - Applied op-pierre's acceptance ruling: the ref to ADR-78 is related (supersedes dropped), Context now says this decision narrows ADR-78's clause rather than replacing it, and an Amendments line records it. ADR-78 carries the matching amendment.
- [2026-11-04T12:42:18Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-04): _models/_attributes is re-exported as the namespace attrs, like markers, so its accessors stay attrs.X at call sites; no attr_<name> import aliases.
<!-- sq:discussion:end -->
