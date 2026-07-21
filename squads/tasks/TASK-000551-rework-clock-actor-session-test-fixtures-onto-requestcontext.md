---
id: TASK-551
sequence_id: 551
type: task
title: Rework clock/actor/session test fixtures onto RequestContext
status: Done
parent: FEAT-533
author: tech-lead
assignee: python-dev
description: 'US2: frozen_time + leak-guards rebind the context, not module globals;
  enables concurrent tests'
created_at: '2026-07-21T21:33:14Z'
updated_at: '2026-07-21T22:07:41Z'
---
<!-- sq:body -->
Implements FEAT-533 **US2** (conftest rework). Genuine fixture rewiring, not a rename — the reason
US2 was split out. Rides on TASK-550's `RequestContext`.

## Why this is real work

`tests/conftest.py::frozen_time` monkeypatches `clock.now` **directly**
(`monkeypatch.setattr(clock, "now", lambda: fixed)`) — it does not go through
`_clock._override`/`set_now`, so it will not exercise the new context seam. Once time lives in
`RequestContext`, the seams must rebind **the context**, not a module global or a monkeypatched
function, so tests (like requests) can run truly concurrently without sharing an override cell.

## Scope

- **`frozen_time`**: stop monkeypatching `clock.now`; instead rebind the context's `clock_override`
  field (e.g. `bind_context(replace(get_context(), clock_override=fixed))`, or a
  `_context` test helper) for the duration of the test, restoring the prior context after. Keep the
  same returned `fixed` datetime so existing tests reading it are unchanged.
- **Collapse the three leak-guards** — `_reset_clock_override`, `_reset_actor`,
  `_reset_session_seed` (all autouse, all resetting `_clock`/`_actor` module globals today) — into
  **one** autouse context-reset/rebind fixture that binds a fresh default `RequestContext` before
  each test and restores/clears after. This is the single-object payoff of the chosen shape.
- Reconcile with `_reset_active_spec` and `_reset_engine_state`: `_active_spec`/`_active_dir` move
  to the context in TASK-552 and their reset folds into the same context-reset fixture **then**;
  in THIS task leave the `_active_spec`/`_active_dir` and `_env_cache` resets as-is (TASK-552 /
  TASK-554 own those). Note the seam so the two tasks don't collide.
- `ContextVar` + `anyio`/threads: verify the context propagates correctly across the
  `_aio.to_thread` / `runner.invoke`-in-thread paths (`invoke`, `run_in_thread` fixtures). A
  ContextVar is copied into a new thread's context by `contextvars` only if propagated explicitly;
  confirm the CLI-in-thread invocations still seed their own context at the callback edge (they go
  through `main_callback`, so they do) and that async tests reading `clock.now()` see the fixture's
  rebind. Fix any propagation gap here.

## Acceptance

- `frozen_time` freezes time via the context; every test currently using it still passes with the
  same frozen value.
- The three separate clock/actor/session leak-guards are replaced by one context-reset fixture; no
  test leaks forged time / actor / session into the next (run the suite under `-n auto` AND `-n0`).
- No test reaches into `_clock._override` / `_actor._override` etc. (they no longer exist).
- Full suite green; `sq check` clean.

## Dependencies / order

After TASK-550 (needs `RequestContext` + accessors). Sequence before or alongside TASK-552 but
coordinate the shared context-reset fixture ownership (this task creates it; TASK-552 folds
spec/dir reset into it).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 551 add-subtask "<title>"`; track with `sq task 551 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T21:58:31Z] Elias Python:
  - frozen_time now rebinds RequestContext.clock_override (dataclasses.replace) instead of monkeypatching clock.now; restores the prior context after.
  - Collapsed _reset_clock_override/_reset_actor/_reset_session_seed into one autouse _reset_context fixture: binds a fresh RequestContext() before AND after each test. _reset_active_spec/_reset_engine_state left untouched (TASK-552/554 own that fold-in).
  - Propagation gap found and fixed: main_callback's apply_timestamp(None) used to force-clear clock_override every invocation, which clobbered frozen_time's rebind on the very first CliRunner.invoke() inside a test (e.g. golden_squad's multi-step setup) - real system-clock freeze got wiped mid-test. Fixed by making apply_timestamp's --at-absent branch a no-op (leaves the ambient value alone) instead of force-clearing; a fresh process/context already starts at None so nothing real changes, only in-process multi-invocation test sequences. Confirmed no test relies on the old clear-to-real-time-after-an-explicit---at-in-the-same-test behavior (grepped every --at-using test file).
  - ContextVar propagation itself confirmed fine: anyio.to_thread.run_sync/asyncio.Task both copy_context() at creation, so invoke/run_in_thread and asyncio task-group concurrency both see the seeding context correctly (proven by tests/unit/test_request_context_isolation.py).
  - Gates: pyright clean, ruff check/format clean. tests/unit+service+cli+integration+tui+meta all green under -n auto; tests/unit+cli also green under -n0 (leak-guard ordering check).
<!-- sq:discussion:end -->
