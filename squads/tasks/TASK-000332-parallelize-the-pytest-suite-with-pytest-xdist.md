---
id: TASK-332
sequence_id: 332
type: task
title: Parallelize the pytest suite with pytest-xdist
status: Draft
author: tech-lead
refs:
- FEAT-231
created_at: '2026-07-08T08:43:08Z'
updated_at: '2026-07-08T08:43:23Z'
---
<!-- sq:body -->
## Goal

Parallelize the pytest suite with `pytest-xdist` as a cheap, near-term wall-clock win. The full
suite is ~4 min today, dominated by scale tests that parallelize well. Agents re-run the suite
back-to-back regardless of instruction, so making a re-run cheap removes the thrash at the source
rather than relying on prompt discipline.

This is a standalone pre-win. It is **not** blocked by the full test-suite rebuild — it lands
first and the rebuild's larger parallelization/perf work builds on it. Target the 0.8 release.

## Scope

1. **Add `pytest-xdist` as a dev dependency** via uv (dev/test dependency group), lockfile updated.

2. **Enable core-parallel runs (`-n auto`).** Decide and document the policy:
   - either make `-n auto` the default in the `pytest` config (`pyproject.toml` `[tool.pytest.ini_options]`
     `addopts`), or keep it opt-in for local dev and wire `-n auto` explicitly into the CI invocation.
   - Whichever is chosen, record the rationale in the discussion and make the config self-documenting.
     (Note the interaction with any existing/planned `-m 'not slow'` default — the two addopts must
     compose, not clobber each other.)

3. **Find and fix tests that assume serial execution.** xdist runs tests across worker processes
   and WILL surface hidden ordering / shared-state coupling. Sweep and fix:
   - shared tmp / cwd state (the `project` / `svc` fixtures `chdir` into a per-test `tmp_path` — verify
     each worker gets its own isolated dir and nothing leaks across workers);
   - the `frozen_time` fixture and any clock injection (must be per-test, not process-global);
   - global-state or filelock contention in the index-store tests (concurrent `.squads.json`
     read-modify-write under the filelock is a correctness path — parallel workers must not corrupt
     or deadlock; if a test relied on single-process ordering, fix the test, not the lock);
   - any test that depends on execution order or leaks env/module state between functions.
   This one-time fixup is explicitly in scope.

4. **Preserve full-suite semantics.** The full sweep must still be runnable and documented (a clear
   invocation for "run everything, including slow/scale"), and results must be identical to the
   serial run — no test silently skipped or made conditional on worker count.

5. **Record before/after wall-clock** in this task's discussion as the acceptance signal (serial
   baseline vs `-n auto`, same machine).

## Acceptance criteria

1. Suite passes green under `-n auto` (all workers), locally and in CI.
2. A measurable wall-clock drop is recorded in the discussion (before/after, same machine).
3. `uv run pyright && uv run ruff check . && uv run ruff format --check .` all clean.
4. No test made flaky or order-dependent by parallelism — the suite passes repeatably under
   `-n auto` and the full sweep remains available and documented.

## Sequencing (dispatch discipline)

Dispatch this ONLY in a clean window with **no in-flight dev editing the tree**. It touches shared
files — `pyproject.toml`, the lockfile, `tests/conftest.py`, and CI config — and will collide with
any concurrent source edit. At authoring time TASK-329's dev is live in the tree, so this must wait
for a clean window.

Targets the 0.8 release. **Not** blocked on EPIC-325 — independent of the generic-engine work and
of the FEAT-231 rebuild (linked as related context only).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 332 add-subtask "<title>"`; track with `sq task 332 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
