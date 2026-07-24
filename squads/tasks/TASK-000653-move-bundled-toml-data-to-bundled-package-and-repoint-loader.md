---
id: TASK-653
sequence_id: 653
type: task
title: Move bundled TOML data to _bundled package and repoint loaders
status: Done
parent: FEAT-652
author: tech-lead
subentities:
- local_id: ST1
  title: Move the three TOML files into a new _bundled package
  status: Done
- local_id: ST2
  title: Repoint the three loaders and update path/prefix references
  status: Done
- local_id: ST3
  title: Fix packaging so the wheel ships _bundled/*.toml
  status: Done
created_at: '2026-07-24T13:03:31Z'
updated_at: '2026-07-24T13:29:25Z'
---
<!-- sq:body -->
Move the three bundled TOML data files into a single `src/squads/_bundled/` package, drop the `default_` prefix, and repoint every loader + reference. Pure refactor — the loaded data is identical, only its on-disk home and filenames move.

## Implementation plan
1. Create `src/squads/_bundled/` with an empty `__init__.py` (the other source packages all have one, and `importlib.resources.files("squads._bundled")` needs the package to resolve).
2. `git mv` the three files into it, dropping the prefix on the first:
   - `_workflow/default_workflow.toml` → `_bundled/workflow.toml`
   - `_interactions/playbook.toml` → `_bundled/playbook.toml`
   - `_roles/roles.toml` → `_bundled/roles.toml`
3. Repoint the three loaders' `importlib.resources.files(...)` calls to `squads._bundled` and the new filenames:
   - `src/squads/_workflow/_loader.py`
   - `src/squads/_interactions/_loader.py`
   - `src/squads/_roles/_loader.py`
4. Update every docstring/comment that names the old path or the `default_` prefix. Grep surfaced: `_workflow/_loader.py`, `_workflow/_models.py` (~line 15), `_cli/__init__.py` (~line 382), `_interactions/__init__.py`, `_interactions/_loader.py`, `_roles/_catalog.py`, `_roles/_loader.py`. Re-grep for `default_workflow`, `playbook.toml`, `roles.toml`, and `_bundled` after the move to catch any stragglers.
5. Fix packaging so the wheel ships `_bundled/*.toml`: check `[tool.hatch.build.targets.wheel.force-include]` in `pyproject.toml` (~line 68) and any other artifacts / package-data globs. `uv build` and confirm the three TOMLs are present in the built wheel.
6. Grep `tests/` for the old filenames/paths and update any that reference them.

## Constraints
- No behavior change: loaded data must be byte-identical; no schema bump.
- Keep the import graph acyclic; no `from __future__ import annotations`.
- Strict pyright + ruff must stay clean (`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .`).
- Full suite green, including the build / skew-canary test.
- Not CHANGELOG-worthy as user-facing behavior; mention only as an internal/packaging note if at all — the operator decides.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 653 add-subtask "<title>"`; track with `sq task 653 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Move the three TOML files into a new _bundled package |  |
| ST2 | Done |  | Repoint the three loaders and update path/prefix references |  |
| ST3 | Done |  | Fix packaging so the wheel ships _bundled/*.toml |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Move the three TOML files into a new _bundled package

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Created src/squads/_bundled/ with __init__.py; git mv'd all three TOMLs in, dropping the default_ prefix on workflow.toml.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Repoint the three loaders and update path/prefix references

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Repointed the 3 loaders' importlib.resources.files() to squads._bundled + new filenames; updated stale default_workflow.toml/path mentions in _models.py, _cli/__init__.py, and tests (_helpers.py, test_status_semantic_role_active.py, test_bundled_toml_packaging.py).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Fix packaging so the wheel ships _bundled/*.toml

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
No pyproject change needed: hatchling's packages=["src/squads"] already auto-includes _bundled/*.toml. uv build + zipfile -l confirmed all 3 TOMLs ship at squads/_bundled/, no stale old-path entries; packaging test green.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T13:19:45Z] Elias Python:
  - Moved 3 TOMLs into src/squads/_bundled/ (git mv, workflow.toml dropped default_ prefix); repointed all 3 loaders (_workflow/_loader.py, _interactions/_loader.py, _roles/_loader.py) to importlib.resources.files("squads._bundled"); updated stale path/prefix mentions in _models.py, _cli/__init__.py, tests/_helpers.py, test_status_semantic_role_active.py, and tests/meta/test_bundled_toml_packaging.py. No pyproject change needed (hatchling packages=["src/squads"] auto-includes the new folder) — uv build + zipfile -l confirmed all 3 TOMLs ship at squads/_bundled/*.toml, no stale old-path entries. pyright/ruff/ruff-format clean; targeted tests (meta/unit/cli/integration/service, workflow|role|playbook|bundled filter) all green.
- [2026-07-24T13:29:20Z] Paul Reviewer:
  - Verified: git mv preserved history; old locations empty; zero dangling refs to old paths/prefix repo-wide (src/tests/docs/scripts/clients); all 3 loaders on squads._bundled; wheel ships _bundled/*.toml (old paths absent). Full suite green (one unrelated TUI xdist flake, passes isolated).
<!-- sq:discussion:end -->
