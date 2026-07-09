---
id: TASK-332
sequence_id: 332
type: task
title: Parallelize the pytest suite with pytest-xdist
status: Done
author: tech-lead
refs:
- FEAT-231
created_at: '2026-07-08T08:43:08Z'
updated_at: '2026-07-09T09:10:11Z'
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
- [2026-07-09T08:35:29Z] Hugo Ops:
  - Added pytest-xdist>=3.8.0 as a dev dependency (uv add --dev pytest-xdist; uv.lock updated).
  - Policy: -n auto is now the DEFAULT in [tool.pytest.ini_options] addopts ("-q -n auto"), not opt-in/CI-only. Rationale (also inlined as a comment in pyproject.toml): every bare 'uv run pytest' — local dev, agents, and the CI workflow (.github/workflows/test.yml just runs 'uv run pytest') — shares one invocation, so putting it in addopts is a single source of truth with nothing extra to wire into CI. It composes cleanly with an added -k/-m/path selector or --lf (xdist only changes HOW selected tests run, not WHICH), so a future -m 'not slow' default would still combine fine. -n0 / -p no:xdist opts back into serial for --pdb or an uncontended timing read.
  - Serial-assumption sweep (by inspection, confirmed empirically on targeted runs): the project/svc fixtures (tests/conftest.py) are function-scoped and chdir into a fresh tmp_path per test via monkeypatch (auto-reverted); every IndexStore test constructs its own tmp_path-rooted .squads.json + .lock (grepped tests/test_index.py — no shared/hardcoded path); frozen_time is a function-scoped monkeypatch.setattr, not process-global. The four module-scoped fixtures in the suite (test_workflow_spec.py, test_role_catalog.py, test_playbook.py, test_workflow_capability_flags.py) only load read-only specs (load_workflow_spec/load_role_catalog/load_playbook) with no mutation, so per-worker-process module scope is safe. No session-scoped fixtures exist anywhere in tests/. The backend registry (_backends/_registry.py) is populated once at import time and never mutated by any test. FORCE_COLOR-stripping is unaffected (still autouse + session-start env pop in conftest.py, unrelated to worker count). Found no test that assumes serial ordering or leaks state across tests — no fixes were needed beyond adding xdist and flipping addopts.
  - Verification: fast gates clean (pyright / ruff check / ruff format --check). Targeted parallel runs under -n auto, twice, both green with no flakiness: tests/test_index.py + test_service.py + test_reflog_core.py + test_workflow_spec.py + test_role_catalog.py + test_playbook.py + test_custom_type_cli.py + test_multi_active_backends.py -> run1 74 passed in 5.5s wall, run2 74 passed in 4.6s wall. The slow-marked scale tests (tests/test_scale.py -m slow, wall-clock-bounded assertions) also ran green twice under -n auto (22s and 37s wall respectively, variance from worker contention as expected) with no bound violations, thanks to the existing 10-25x margin. -k selection composes fine with -n auto (targeted prefix/index subset, 50 passed). Did not run the full suite here — the harness auto-backgrounds it and a subagent can't resume off that, so the full-suite before/after wall-clock is left for the main loop to run and record as the authoritative gate.
  - Leaving InReview; no serial-run wall-clock number recorded by me — main loop to capture full-suite before/after.
- [2026-07-09T08:54:45Z] Hugo Ops:
  - Fixed a real determinism gap the coordinator's full-parallel run surfaced: test_cli.py::test_ref_add_help_references_workflow asserts a raw substring in Rich-rendered --help text, which wraps depending on console width (fails at COLUMNS=108/120, passes at 80/96/104/112) — nondeterministic under an inherited/varying COLUMNS, not an isolation bug. Fixed systematically (the width analogue of the existing FORCE_COLOR pin): the autouse _neutralize_forced_color fixture in tests/conftest.py now also does monkeypatch.setenv("COLUMNS", "80") + monkeypatch.delenv("LINES", raising=False), pinning Rich/Typer's console width for every test regardless of the invoking terminal or xdist worker.
  - Verified: reverting just the conftest fix reproduces the failure at COLUMNS=108 (assert 'sq workflow' in ... fails on the wrapped help text); with the fix, COLUMNS=108 and COLUMNS=120 both pass -n0. Full tests/test_cli.py under -n2: green (no regression).
  - Also corrected a doc bug in the addopts comment (pyproject.toml) and its CLAUDE.md echo: both wrongly said '-n0 / -p no:xdist' force serial — -p no:xdist only unloads the xdist plugin, it does not strip -n auto out of addopts, so it errors as an unrecognized argument. Both now say only -n0 forces serial, with a one-line note on why -p no:xdist doesn't.
  - Fast gates re-verified clean: pyright / ruff check / ruff format --check. Did not touch the full-suite run — leaving that to the main loop.
  - Leaving InReview.
<!-- sq:discussion:end -->
