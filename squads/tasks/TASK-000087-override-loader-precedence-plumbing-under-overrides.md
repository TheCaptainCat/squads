---
id: TASK-87
sequence_id: 87
type: task
title: Override loader + precedence plumbing under .overrides/
status: Done
parent: FEAT-14
author: tech-lead
priority: high
refs:
- TASK-88:blocks
- TASK-89:blocks
- REV-93:addresses
description: Engine ChoiceLoader (project override → bundled), squad-aware cache key,
  .overrides path resolution
subentities:
- local_id: ST1
  title: ChoiceLoader engine swap + squad-aware cache key
  status: Done
  story: US1
- local_id: ST2
  title: .overrides/ path resolution + traversal guard + partial-override test
  status: Done
  story: US1
created_at: '2026-06-12T20:56:38Z'
updated_at: '2026-07-06T15:19:38Z'
---
<!-- sq:body -->
Foundation task for FEAT-14 (ADR-85 §1, §2). Lay the override lookup path that both template and role overrides build on.

**Goal.** Make project templates under `<squad-dir>/.overrides/templates/` shadow bundled templates per-file, with the bundled template as fallback — `render(name, ...)` and all ~13 call sites byte-for-byte unchanged.

**Scope.** (1) Resolve/create the `.overrides/` umbrella under the squad folder via the existing `_paths.resolve()` walk-up, guarded by `abspath()` traversal check; the `templates/` sub-tree mirrors `_rendering/templates/` 1:1 so the override key IS the existing render() name. (2) In `_rendering/_engine.py`, replace the single `PackageLoader` with a `ChoiceLoader([FileSystemLoader(<squad-dir>/.overrides/templates), PackageLoader(...)])`. (3) Fix the `lru_cache(maxsize=1)` on the Environment — key it on the squad dir (or build per-resolve) so two squads in one process don't cross-contaminate.

**Precedence (ADR §2).** Per-file, project → bundled; presence of the file IS the override; no whole-squad mode, no manifest of what's overridden, no deep-merge — a template is overridden whole or not at all.

**Acceptance.** Dropping `items/task.md.j2` under `.overrides/templates/` changes only task bodies; every other template still resolves to the bundle. Covered by a service-level test (partial override: one file shadows, rest bundled) + a CLI smoke test. `render()` signature and call sites unchanged; cache no longer cross-contaminates across squads.

**Dependencies.** None — this is the foundation. T2 (roles) and T3 (override command group / staleness) both build on this loader and the `.overrides/` layout.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 87 add-subtask "<title>"`; track with `sq task 87 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | ChoiceLoader engine swap + squad-aware cache key | US1 |
| ST2 | Done |  | .overrides/ path resolution + traversal guard + partial-override test | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — ChoiceLoader engine swap + squad-aware cache key

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a project lead, I want to override item templates from squads/.templates/, so that generated items follow our house format
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Swap the _rendering/_engine.py single PackageLoader for a ChoiceLoader([FileSystemLoader(<squad-dir>/.overrides/templates), PackageLoader(...)]) so a project template shadows its bundled counterpart per-file with the bundle as fallback, and fix the lru_cache(maxsize=1) on the Environment to key on the squad dir (or build per-resolve) so two squads in one process don't cross-contaminate. render() signature and all ~13 call sites unchanged (US1).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — .overrides/ path resolution + traversal guard + partial-override test

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a project lead, I want to override item templates from squads/.templates/, so that generated items follow our house format
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Resolve/create the .overrides/ umbrella under the squad folder via _paths.resolve() walk-up, guarded by the abspath() traversal check, with templates/ mirroring _rendering/templates/ 1:1 so the override key is the existing render() name. Covered by a partial-override service test (dropping items/task.md.j2 shadows only task bodies; every other template still resolves to the bundle) plus a CLI smoke test (US1).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T21:07:07Z] Elias Python:
  - Implementation complete. Suite green: 401 passed, 1 skipped.
  - **What changed**
  - `_rendering/_engine.py`: Replaced the single `@lru_cache(maxsize=1)` `PackageLoader` setup with a per-squad-dir Environment cache. Added `set_active_squad_dir(path)` (contextvar-backed), `invalidate_squad_dir(path)`, and a `_make_env()` builder that constructs a `ChoiceLoader([FileSystemLoader(<squad_dir>/.overrides/templates), PackageLoader(...)])` when the overrides dir exists, falling back to the bare `PackageLoader` otherwise. `render()` signature and all ~13 call sites are byte-for-byte unchanged.
  - `_services/_base.py`: `ServiceCore.__init__` now calls `set_active_squad_dir(paths.squad_dir)` so every render in a service automatically resolves against that squad's overrides.
  - `tests/test_override_loader.py`: Six new tests — bundled render unchanged with no override, partial override (task shadows; bug still bundled), service-level create with override, service-level create bundled unchanged, cache isolation across two squad dirs, and a CLI smoke test.
  - All linters clean: `pyright` 0 errors, `ruff check` and `ruff format --check` both pass.
  - Ready for @reviewer. TASK-88 (role overrides) and TASK-89 (override command group) can now build on this loader.
- [2026-06-12T21:11:39Z] Paul Reviewer:
  - Reviewed under REV-93 — verdict: APPROVED. @tech-lead @python-dev
  - Per-file precedence matches ADR-85 §2 (project override → bundled, presence-is-the-override, no merge); render() and all call sites byte-for-byte unchanged; cross-squad isolation holds (Environment cache keyed by squad_dir, proven by test_env_cache_does_not_cross_contaminate). Verified green myself: 401 passed / 1 skipped, pyright 0 errors, ruff check + format clean.
  - One LOW, non-blocking finding (REV-93 F1): conftest has no autouse reset of engine module-state (_active_squad_dir ContextVar + _env_cache) the way it resets the clock — latent test-ordering coupling that will grow as T88/T89 add override tests. Suggest a teardown that calls set_active_squad_dir(None). Doesn't block this task.
  - Foundation is SAFE to build TASK-88 (role resolver) and TASK-89 (sq override group) on. One note for T89: the per-squad-dir env is cached at build time, so if sq override scaffold creates .overrides/ inside a live process the override won't be seen until invalidate_squad_dir() is called — the escape hatch exists and is documented; just wire it in if scaffold renders in the same process.
<!-- sq:discussion:end -->
