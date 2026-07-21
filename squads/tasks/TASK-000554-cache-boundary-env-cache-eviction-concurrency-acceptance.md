---
id: TASK-554
sequence_id: 554
type: task
title: Cache boundary + env_cache eviction + concurrency acceptance
status: Draft
parent: FEAT-533
author: tech-lead
description: 'US4: prove code-vs-data cache line; bound the Jinja env cache; N-request
  multi-squad isolation test'
created_at: '2026-07-21T21:33:16Z'
updated_at: '2026-07-21T21:35:47Z'
---
<!-- sq:body -->
Implements FEAT-533 **US4**. The acceptance capstone — comes last. ADR-534 rules 2 and 3.

## Scope

### Codify the code-vs-data cache boundary

Draw the line hard and prove it: module/spec/definition caches (backend registry, bundled specs,
compiled Jinja environments) MAY persist across requests; squad **DATA** (items, index,
sub-entity state) MUST NEVER be cached across requests — every request re-reads through the
filelock'd `IndexStore` (Invariant #1, ADR-71). Add a test asserting a backend instance from
`get_backend()` holds no squad data between calls (stateless), guarding the registry against
drifting into a data cache.

### Bound / evict the Jinja env cache

`_rendering/_engine._env_cache` is a `dict[Path | None, Environment]` that grows **unbounded** per
distinct squad dir in a long-lived process and retains per-squad override loaders. It is a *code*
cache (compiled templates), keyed correctly, so it is semantically safe — this is a **resource**
fix, not a correctness one. Bound it: LRU eviction (a capacity cap) or tie entries to a squad-context
lifetime. Preserve `invalidate_squad_dir()` and the `set_active_squad_dir(None)` bundled-only path;
keep `_env_cache` on the TASK-549 allowlist (still a sanctioned code cache, now bounded).

### Concurrency-isolation acceptance test (the capstone)

A test proving the ADR-534 rule 3 property: **a long-lived process serving N interleaved requests
across ≥2 squads is semantically identical to N fresh single-shot processes.** Concretely:

- Two temp squads A and B, each initialized.
- Interleave requests (bind a fresh `RequestContext` per request — different `client_cwd`/dir,
  `--at`, actor, and, if customized, spec — within one process/event loop): a write to A committed
  by one request is read back by the **next** request for A, and is **never** observed by a
  concurrent request for B.
- Forged time, actor identity, active spec, and resolved dir for request A are invisible to B.

Exercise this through the service/CLI layer (per the testing guide), leaning on the async filelock
(FEAT-34 / ADR-153) for the writer serialization — this test proves isolation is not defeated
*above* the lock.

## Acceptance

- `_env_cache` is bounded (a test drives >cap distinct squad dirs and asserts eviction; the
  bundled-only and `invalidate_squad_dir` paths still work).
- The stateless-backend guard passes.
- The N-request multi-squad interleaving test passes: A's committed write is read by A's next
  request, never seen by a concurrent B request; ambient state (time/actor/spec/dir) does not
  cross between contexts.
- Full suite green (`-n auto` and `-n0`); `sq check` clean.

## Dependencies / order

**Last.** Requires TASK-550 (context), TASK-552 (spec/dir on context), TASK-553 (client-cwd
resolution) so the interleaving test can bind fully-independent per-request contexts. Runs
before/with TASK-549 (guard) — the guard's allowlist keeps the now-bounded `_env_cache`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 554 add-subtask "<title>"`; track with `sq task 554 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
