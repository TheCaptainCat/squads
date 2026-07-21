---
id: TASK-552
sequence_id: 552
type: task
title: Active-spec / active-dir seam onto RequestContext
status: Draft
parent: FEAT-533
author: tech-lead
description: 'US5: move _active_spec/_active_dir onto the context; ~15 get_active_spec
  sites read off it'
created_at: '2026-07-21T21:33:15Z'
updated_at: '2026-07-21T21:35:46Z'
---
<!-- sq:body -->
Implements FEAT-533 **US5**. The second CLI-edge seam onto the **same** `RequestContext` primitive
TASK-550 builds. The larger of the two remaining ambient globals. Follows Robert's seam decision.

## Scope

Move `_cli/_common._active_spec` and `_active_dir` off module globals and onto `RequestContext`.

### active_spec (the larger consumer surface — ~15 sites)

- Add `active_spec: WorkflowSpec | None` to `RequestContext`.
- `_cli/_common.get_active_spec()` reads it off the context; `set_active_spec()` rebinds the field.
- **Preserve the fallback contract exactly**: `get_active_spec()` returns the **bundled** spec when
  nothing is bound yet (parse-time validators `parse_type`/`parse_status`, outside a squad). Keep
  the `_active_spec is not None else bundled_spec()` semantics, now against the context field.
- Route every consumer to read via `get_active_spec()` (they already do, so mostly the backing
  store changes). Explicitly handle the two reach-ins:
  - `_cli/__init__.py::_CustomTypeGroup._resolve_spec_for_ctx` reads `common._active_spec` directly
    (`reportPrivateUsage`) — change it to read the context (via `get_context()` / a thin accessor),
    not the module attribute.
  - `_CustomTypeGroup._custom_cmd_cache` / `_CustomCreateGroup._custom_cmd_cache` are class-scope
    in-process code caches — part of the surface to reconcile, but they stay caches (see TASK-549
    allowlist); just ensure they are keyed/cleared correctly against the context, not the old
    global.
- `_bind_active_spec` in `main_callback` becomes "seed the context's `active_spec`", not "assign a
  module global". `_workflow/__init__` consumers, `_cli/_items`, `_cli/_create`, `_cli/_workflow_cmd`,
  `_cli/_main` all read through `get_active_spec()`.

### active_dir

- Add `active_dir: str | None` to `RequestContext`.
- `set_active_dir()` rebinds it; `get_service()`, `version_notice()`, `require_current_schema()`
  read it off the context (today they read the `_active_dir` module global).
- `open_service(dir_override)` still takes the dir explicitly — `get_service()` reads the context
  and passes it in. Nothing below `open_service` reads the ContextVar; `Service` keeps owning
  `spec`/`store` by attribute (ADR-249 unchanged — spec appears in both context and Service by
  design: context is the parse-time/edge SOURCE that seeds Service).

### CLI edge

`main_callback` folds `set_active_dir` + `_bind_active_spec` into the one
`bind_context(RequestContext(...))` seed (joining TASK-550's clock/actor fields), so the edge is
the single place the context is seeded per invocation. `_bind_active_spec` must still **fail soft**
to the bundled spec on any resolution error (outside a squad, invalid override).

### conftest

Fold the `_reset_active_spec` reset (and the `_custom_cmd_cache` clears it does) into the single
context-reset fixture TASK-551 introduces — coordinate ownership so the two do not double-define it.

## Acceptance

- `_active_spec` and `_active_dir` are **gone as module globals** — both on `RequestContext`.
- Fallback preserved: `get_active_spec()` outside a squad / before seeding returns the bundled
  spec; `_bind_active_spec` fails soft to bundled on error.
- Two logically concurrent contexts resolving two differently-customized squads each see their own
  spec + dir; neither observes the other's.
- Custom-type lazy dispatch (`sq <custom-type> …`, `sq create <custom-type> …`) still works and
  `sq --help` custom-type listing is byte-identical for non-custom squads.
- A one-shot CLI invocation is unchanged. Full suite green; `sq check` clean.

## Dependencies / order

After TASK-550 (needs the primitive). Coordinates the shared context-reset fixture with TASK-551.
Can run parallel to TASK-553 (disjoint fields) if fixture ownership is settled first.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 552 add-subtask "<title>"`; track with `sq task 552 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
