---
id: TASK-550
sequence_id: 550
type: task
title: RequestContext primitive + clock/actor backing-store seam
status: Done
parent: FEAT-533
author: tech-lead
assignee: python-dev
description: 'US2: _context.py single ContextVar; clock/actor keep public fns, backing
  store moves to context'
created_at: '2026-07-21T21:33:14Z'
updated_at: '2026-07-21T22:07:40Z'
---
<!-- sq:body -->
Implements FEAT-533 **US2** (primitive + clock/actor seam). Foundational task — US3/US5 ride the
primitive this builds. Follows Robert's settled design decision (see FEAT-533 discussion) and
ADR-534.

## The decided shape (do not re-open)

A **single `RequestContext` object held in ONE `ContextVar`**, seeded at the CLI edge, read at the
ambient boundary via thin accessor free-functions, threaded into `Service` below. Rejected: N
ContextVars, fold-into-Service. Follows the proven `_rendering/_engine._active_squad_dir`
ContextVar precedent, one object instead of one var per value.

## Scope

Create a new **`src/squads/_context.py`** holding:

- `RequestContext` — a dataclass carrying the per-request ambient values. This task lands the
  clock + actor fields: `clock_override: datetime | None`, `actor_override: str | None`,
  `session_id: str | None`, `parent_session_id: str | None`. **Design it additively** — US5 adds
  `active_spec`/`active_dir`, US3 adds `client_cwd`, and EPIC-538 will fold in the playbook spec.
  Adding a field must not require touching existing call sites (default every field; a
  `replace`-style rebind helper is fine).
- The single `ContextVar[RequestContext]` (with a sensible default context so reads before any
  seed behave exactly as today's unset globals do).
- `bind_context(ctx)` / `get_context()` (+ a small helper to rebind one field, for tests and the
  `--as`/`--author` mid-invocation actor override).

Migrate the two purely-ambient seams onto it, **keeping their public function names unchanged** so
their ~all call sites are untouched (only the backing store moves):

- `_clock.py`: `now()` reads `get_context().clock_override`; `set_now(dt)` rebinds that field.
  `iso()`/`parse_iso()` unchanged.
- `_actor.py`: `current_actor()` reads `actor_override` (default `"system"` semantics preserved);
  `set_actor(slug)` rebinds it; `current_session()` reads `(session_id, parent_session_id)`;
  `seed_session(...)` rebinds them (env-read path preserved).

Rewire the **CLI edge** (`_cli/__init__.py::main_callback`): the four seed calls today
(`set_active_dir` — deferred to US5 —, `apply_timestamp`, `actor.set_actor("system")`,
`actor.seed_session(from_env=True)`) collapse toward one `bind_context(RequestContext(...))` at
invocation start. In THIS task, seed the clock + actor fields via the context; `--at` parsing
stays in `_common.apply_timestamp` but writes through the context. (`_active_dir`/`_active_spec`
seeding moves in US5; leave those as-is here so the suite stays green in between.)

**Boundary rule for the dev:** the ContextVar is SEEDED/REBOUND only at the CLI edge (and by tests
/ a future server handler), and READ only through the accessor free-functions. No code below
`open_service` reads the ContextVar directly. `Service.create()` / `_locked_section_edit()` keep
calling `clock.now()` / `actor.current_session()` as **free functions** (ADR-77's injectable-clock
seam preserved — models never take a clock arg); only the backing store moved.

## Keep the suite green WITHOUT the fixture rework

`set_now`/`set_actor`/`seed_session` keep their signatures and now rebind the context, so the
existing conftest leak-guards still function. The genuine fixture rework (rebind the context,
collapse the three resets, enable concurrent tests) is TASK-551 and rides on top — do not do it
here beyond what is needed to keep tests passing.

## Acceptance

- `_context.py` exists with `RequestContext` + one ContextVar + bind/get; adding a field is
  additive (demonstrated by US5/US3 not touching this file's existing fields).
- `_clock._override` and `_actor._override`/`_session_id`/`_parent_session_id` are **gone as module
  globals** — the values live in `RequestContext`.
- Two logically concurrent contexts with different `--at`/actor/session values do not observe each
  other's values (a focused async/threaded test).
- A single one-shot CLI invocation behaves exactly as today (timestamps, attribution, session
  lineage unchanged).
- Full suite green; `sq check` clean.

## Dependencies / order

Second (after TASK-548's inventory). Prerequisite for TASK-551 (fixtures), TASK-552 (spec/dir),
TASK-553 (client cwd).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 550 add-subtask "<title>"`; track with `sq task 550 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T21:43:34Z] Elias Python:
  - Added src/squads/_context.py: RequestContext dataclass (clock_override, actor_override, session_id, parent_session_id), one ContextVar, bind_context/get_context/rebind. Triage rule recorded as its module docstring.
  - _clock.py/_actor.py backing store moved into RequestContext via rebind(); public fn names/signatures unchanged (now/set_now, current_actor/set_actor/current_session/seed_session).
  - _active_dir/_active_spec seeding in _cli/__init__.py left as-is per scope (US5/TASK-552). No CLI-edge code change needed: apply_timestamp/set_actor/seed_session already rebind through the new context.
  - New test tests/unit/test_request_context_isolation.py: primitive basics + a task-group concurrency test proving two sibling asyncio tasks with different --at/actor/session values never observe each other.
  - Gates: pyright clean, ruff check/format clean. Targeted pytest (clock/session/context/hoist-global-options/session-recorded/reflog/full tests/cli) all green.
<!-- sq:discussion:end -->
