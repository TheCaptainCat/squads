---
id: TASK-553
sequence_id: 553
type: task
title: Per-request squad resolution from client cwd
status: Done
parent: FEAT-533
author: tech-lead
description: 'US3: client cwd is an explicit resolution input, not Path.cwd() read
  from the process'
created_at: '2026-07-21T21:33:16Z'
updated_at: '2026-07-21T22:35:57Z'
---
<!-- sq:body -->
Implements FEAT-533 **US3**. Rides the `RequestContext` primitive (TASK-550). ADR-534 rule 1 +
requirement 2.

## Scope

Make squad resolution (`--dir` > `.squads.toml` walk-up > cwd) take the requesting **client's**
working directory as an **explicit input**, rather than reading the process cwd via `Path.cwd()`
inside `_paths.py`.

- Add `client_cwd: Path | None` to `RequestContext` (additive; `None` = "use the process cwd",
  the one-shot default).
- `_paths.find_config(start=None)` already accepts a `start` — the offender is that its callers
  pass nothing, so it defaults to `Path.cwd()`. `_paths.resolve(dir_override)` calls
  `find_config()` with no start and, in the not-initialized branch, uses `Path.cwd().resolve()`.
  Thread the client cwd from the context into these:
  - `resolve()` gains the client cwd as its resolution base (read from the context at the CLI edge,
    or passed explicitly). When the context carries no `client_cwd`, fall back to `Path.cwd()` so
    one-shot CLI behaviour is byte-identical (the client cwd IS the process cwd there).
  - The `.squads.toml` walk-up (`find_config`) and the `require_init=False` default-root branch
    both start from the client cwd, not `Path.cwd()`.
- Seed `client_cwd` at the CLI edge in `main_callback`'s `bind_context(RequestContext(...))`
  (from `Path.cwd()` for the one-shot CLI). A future server request handler supplies the client's
  cwd per request; nothing below reads `Path.cwd()` for resolution anymore.

**Do not** change the `--dir` override precedence or the traversal guard in
`SquadPaths.abspath`. Behaviour for a one-shot CLI invocation must be unchanged.

## Acceptance

- No `Path.cwd()` read remains in the squad-resolution path (`resolve`/`find_config`) except as the
  explicit one-shot fallback when the context carries no `client_cwd`.
- One process resolving two requests whose client cwds point at two different squads yields two
  independent `SquadPaths`, with neither remembered between requests (a focused test that binds two
  contexts with different `client_cwd` and asserts independent resolution).
- Every existing `--dir` / walk-up / outside-a-squad path behaves exactly as today for one-shot
  CLI use (existing `_paths` tests green unchanged).
- Full suite green; `sq check` clean.

## Dependencies / order

After TASK-550 (needs the primitive to carry `client_cwd`). Disjoint from TASK-552's fields; can
run in parallel with it once the shared fixture ownership is settled.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 553 add-subtask "<title>"`; track with `sq task 553 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T22:26:59Z] Elias Python:
  - Added RequestContext.client_cwd + resolve()'s client_cwd param (falls back to Path.cwd() when unset); open_service/get_service thread it through; main_callback seeds client_cwd=Path.cwd() into the same single bind_context() call from TASK-552. Added service-level tests for independent per-request cwd resolution + concurrent-task isolation; pyright/ruff/targeted pytest all green.
<!-- sq:discussion:end -->
