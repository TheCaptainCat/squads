---
id: TASK-000253
sequence_id: 253
type: task
title: 'CLI per-invocation spec context: root --dir callback binds it, parsers read
  it'
status: Done
parent: FEAT-000250
author: tech-lead
refs:
- TASK-000252:depends-on
created_at: '2026-06-30T09:53:05Z'
updated_at: '2026-06-30T10:20:03Z'
---
<!-- sq:body -->
**Part (c) of FEAT-000250 / ADR-000249 Option A. Sequence: after TASK-000252 (Service owns
the spec); before the test rewrite.**

Add a per-invocation CLI context handle for the active `WorkflowSpec`, set once in the root
`--dir` callback and read by the parse/print helpers — mirroring the existing `_active_dir`
mechanism.

## Scope

- **`src/squads/_cli/__init__.py`** — the root `--dir` callback (`:44-75`) already calls
  `common.set_active_dir(value)`. Extend it: after resolving the squad, **resolve + merge +
  validate the `WorkflowSpec` once and bind it** to a per-invocation handle (a `contextvar`
  in `_common`, and/or Typer `ctx.obj` — match the `_active_dir` precedent; a module-level
  `contextvar` in `_common` is the honest minimum).
- **`src/squads/_cli/_common.py`** — add `set_active_spec` / `active_spec`-style accessors
  next to `set_active_dir`/`get_active_dir`. `parse_type` (`:684`) and `parse_status` (`:699`),
  plus the `item_has_severity`/`item_subentity_kind` reads (`:36,142,204,338`), read the handle
  instead of the deleted `_workflow.active_spec()`.
- **`src/squads/_cli/_main.py`** (`is_open` list filters `:48,312,653`; the `sq check`
  graceful-degrade path that did `bundled_spec`/`use_spec` reset `:993,1015`) and
  **`_cli/_items.py`** (`work_types` `:43`) — read the handle / passed spec.

## The one genuine design detail — Click parse ordering

`parse_type`/`parse_status` are Typer **parser callbacks**: they fire during Click argument
parsing, which runs **before the group callback body** resolves the spec. ADR-000249 Finding 2
flags this. Two acceptable fixes — pick and document:
1. Bind the contextvar in the root callback **early enough** that it is set before any
   subcommand parser runs (verify the Click invocation order — the root callback's body must
   execute before subcommand arg parsing), **or**
2. Relocate type/status validation **out of the Typer parser into the command body** (where
   the spec is reliably bound).
Whichever is chosen, add a test that exercises a `sq <type>`/`--status` parse to prove the
handle is bound at parse time. There must be a safe fallback to the bundled spec when no squad
is resolved (e.g. `sq` run outside a squad), matching today's behaviour.

## Constraints / gotchas

- **Behaviour byte-identical** — pure refactor under FEAT-208 characterization + golden-lock.
- **Out of scope (hard line): the import-time app-build loop** (`_cli/__init__.py:97,121`
  `for _type in _ORDERED_WORK_TYPES: build_item_app(_type)`) stays **bundled-spec-driven**.
  Making it iterate `spec.managed_types()` is FEAT-210's job — do NOT touch it here. A
  per-invocation context cannot reach it anyway (it runs at import, before any invocation);
  that's the documented seam between this feature and 210.

## Acceptance

- Root callback binds the spec; parse/print helpers read it; parse-ordering proven by a test.
- `sq` outside a squad still works (bundled-spec fallback).
- `pyright` strict + `ruff` clean; full suite green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 253 add-subtask "<title>"`; track with `sq task 253 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
