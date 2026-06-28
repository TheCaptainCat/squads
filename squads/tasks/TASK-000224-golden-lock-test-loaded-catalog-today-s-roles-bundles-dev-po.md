---
id: TASK-000224
sequence_id: 224
type: task
title: 'Golden-lock test: loaded catalog == today''s roles/bundles/dev pool; verify
  roles.toml ships'
status: Done
parent: FEAT-000219
author: tech-lead
subentities:
- local_id: ST1
  title: 'Golden-lock test: loaded catalog == frozen snapshot of today''s _catalog.py'
  status: Todo
  story: US2
- local_id: ST2
  title: 'Build test: roles.toml ships in the wheel'
  status: Todo
  story: US2
created_at: '2026-06-26T07:35:29Z'
updated_at: '2026-06-26T07:58:43Z'
---
<!-- sq:body -->
## Goal

Add the **golden-lock test** asserting the loaded `RoleCatalogSpec` reproduces today's `_catalog.py`
byte-for-byte, and verify `roles.toml` ships in the wheel. This is the regression gate that proves the
externalization (TASK-000222/223) is behavior-preserving.

Sequence: **third** — depends on TASK-000222 (TOML/models) and TASK-000223 (loader/rewire). Must stay
green going forward (and is the slug authority FEAT-000220 will validate against).

## What to build

- **Golden-lock test** (ADR §4): build the snapshot directly from today's `PREDEFINED` / `BUNDLES` /
  `DEV_NAME_POOL` and assert **structural equality** with the loaded `RoleCatalogSpec` across:
  - all 8 roles with EVERY field: slug, full_name, title, description, mission, responsibilities,
    agreements, model, color, is_default, can_spawn;
  - the three bundles and their exact membership;
  - the dev pool (12 names + dev defaults model/color).
  Plus a spot-check that `dev_role("dotnet", seq=0)` yields the identical `RoleDef`/role before and
  after the externalization. The test must FAIL if any field drifts. CI-enforced. (US2 acceptance.)
- **Packaging verification:** assert `roles.toml` is included in the built wheel (consistent with the
  templates-are-package-data invariant and FEAT-000207's TOML). Mirror the existing
  templates/workflow-toml-in-wheel build test; rely on `packages = ["src/squads"]` sweeping non-`.py`
  files — confirm, don't add a per-file include.

## Design constraints (ADR-000221)

- §4 golden-lock contract: build the snapshot from today's literals (independent source of truth), not
  from the spec. Behavior-preserving — this task adds tests + a packaging check only.

## Acceptance

1. Golden test exists, is CI-enforced, and fails on any drift between the loaded catalog and the
   frozen snapshot of today's `PREDEFINED`/`BUNDLES`/`DEV_NAME_POOL` (every role field, bundles, dev
   pool) — including the `dev_role(...)` spot-check. (FEAT-000219 AC#2, US2.)
2. A build/packaging test confirms `roles.toml` is present in the wheel.
3. `uv run pyright && uv run ruff check . && uv run pytest` all green. (AC#6.)
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 224 add-subtask "<title>"`; track with `sq task 224 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Golden-lock test: loaded catalog == frozen snapshot of today's _catalog.py | US2 |
| ST2 | Todo |  | Build test: roles.toml ships in the wheel | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Golden-lock test: loaded catalog == frozen snapshot of today's _catalog.py

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a maintainer, I want a golden test asserting the loaded catalog == today's hardcoded roles so regressions are caught
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Build test: roles.toml ships in the wheel

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a maintainer, I want a golden test asserting the loaded catalog == today's hardcoded roles so regressions are caught
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T07:49:50Z] Elias Python:
  - @manager TASK-222/223/224 complete — FEAT-000219 implemented and all gates green.
  - Files added/changed:
  -   src/squads/_roles/_models.py (NEW) — RoleSpec/DevPoolSpec/RoleCatalogSpec pydantic v2 frozen models capturing full RoleDef field set
  -   src/squads/_roles/roles.toml (NEW) — bundled catalog: 8 roles + 3 bundles + dev pool, transcribed byte-for-byte from _catalog.py literals
  -   src/squads/_roles/_loader.py (NEW) — load_role_catalog() via importlib.resources + tomllib; fail-closed validation (6 checks: unique slugs, required fields, at-most-one is_default, bundle referential integrity + all==full set, dev pool well-formed, model whitelist)
  -   src/squads/_roles/_catalog.py (REWIRED) — RoleDef dataclass kept (public surface unchanged); module-level _CATALOG singleton; PREDEFINED/BUNDLES/DEV_NAME_POOL/dev_role() backed by spec; to_extra/from_extra/logic all intact
  -   tests/test_role_catalog.py (NEW) — 12 tests: golden-lock (role count, order, all 8 roles x all 11 fields, PREDEFINED shim equality, 3 bundles, dev pool + DEV_NAME_POOL shim, dev_role spotcheck, default role, can_spawn set), importlib access, wheel packaging
  - No identity-comparison landmines found: _resolver.py uses 'base is None' (absence check, not RoleDef identity) and frozen-dataclass equality (==). No 'is' comparisons on RoleDef objects anywhere.
  - Gates: pytest -q exit 0 (all tests pass, 1 skip); pyright 0 errors; ruff check clean; ruff format --check 131 files already formatted. Existing tests pass UNCHANGED — no test file edited.
<!-- sq:discussion:end -->
