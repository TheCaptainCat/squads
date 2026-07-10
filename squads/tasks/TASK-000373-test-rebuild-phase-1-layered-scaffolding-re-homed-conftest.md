---
id: TASK-373
sequence_id: 373
type: task
title: 'Test rebuild Phase 1: layered scaffolding + re-homed conftest'
status: Draft
parent: FEAT-231
author: tech-lead
created_at: '2026-07-10T04:48:19Z'
updated_at: '2026-07-10T04:49:52Z'
---
<!-- sq:body -->
## Phase 1 — Layered scaffolding + re-homed conftest

Second phase of the FEAT-231 rebuild. **Nothing from the old suite is deleted or moved.** This
phase stands up the new tree so it runs green-empty alongside the existing flat suite, ready for
Phase 2 to author into.

### Scope
- Create the four-layer directory structure per the feature's Principle 2:
  - `tests/unit/` — pure functions, models, spec logic; no `project` fixture, in-process values.
  - `tests/service/` — `Service` façade + `IndexStore`; `svc` fixture; assert return values +
    frontmatter.
  - `tests/cli/` — `CliRunner` invocations; `project` fixture; assert exit code, stdout, generated
    files.
  - `tests/integration/` — multi-step workflows + migration round-trips; cross-layer by design.
- Author `tests/CONVENTIONS.md` (initial version; finalized in Phase 4): naming rules
  (behavior-named, no dev-archaeology — realizes US1), which fixtures belong in which layer, how to
  add a layer, and the golden-snapshot protocol (pin all inputs, source of truth is the input spec,
  one golden per distinct rendering path, goldens live under `tests/goldens/`, updated intentionally).
- Re-home the shared `conftest.py`, carrying its hard-won guards **verbatim in behaviour**:
  - the pre-import `FORCE_COLOR`/`CLICOLOR_FORCE`/`PY_COLORS` strip (module-level Console latches
    color at import) plus the autouse per-test re-strip and `COLUMNS=80` width pin;
  - the leak-guards: clock override reset, ambient actor reset, `_active_spec`/`_active_dir` +
    custom-command cache resets, rendering-engine ContextVar/`_env_cache` reset;
  - the `frozen_time`, `project`, `svc`, `runner`, `invoke`, `run_in_thread` fixtures.
  Decide layout: a single root `tests/conftest.py` for cross-layer fixtures + per-layer `conftest.py`
  for layer-scoped ones (document the split in CONVENTIONS.md).
- Carry `tests/fixtures/corpus/*` **verbatim** (frozen migration-input snapshots — v0_1..v0_8) and
  keep the corpus README's standing "add a fixture on every schema bump" rule. Do NOT regenerate.
- Keep `pyproject.toml` `testpaths`/`-n auto` working so both old and new trees collect and run
  together, green. (The `addopts = -m 'not slow'` flip is deferred to Phase 2, where scale tests
  get marked.)

### Dependencies
Depends on Phase 0 (inventory informs the taxonomy). Blocks Phase 2.

### Acceptance
- New `tests/{unit,service,cli,integration}/` collect and run green-empty alongside the old suite.
- `CONVENTIONS.md` present with naming + fixture + golden rules.
- conftest guards preserved (prove FORCE_COLOR strip + leak-guards still active).
- corpus fixtures carried byte-identical; `uv run sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 373 add-subtask "<title>"`; track with `sq task 373 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
