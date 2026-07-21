---
id: FEAT-533
sequence_id: 533
type: feature
title: 'Statelessness: one process, many squads, per-request context'
status: Draft
parent: EPIC-31
author: architect
refs:
- FEAT-33
- FEAT-34
- ADR-153
description: Make a long-lived sq process able to host multiple squads concurrently
  by resolving all squad-specific context per request and holding nothing mutable
  at module level
subentities:
- local_id: US1
  title: Static-state inventory and enforcement guard
  status: Todo
- local_id: US2
  title: Request-scoped ambient context (clock, actor, active spec, active dir)
  status: Todo
- local_id: US3
  title: Per-request squad resolution from the client cwd
  status: Todo
- local_id: US4
  title: Code-vs-data cache boundary and concurrency-isolation acceptance
  status: Todo
created_at: '2026-07-21T12:37:58Z'
updated_at: '2026-07-21T12:39:50Z'
---
<!-- sq:body -->
## Problem

Every `sq` invocation is a fresh OS process today, so import-time work and module-level
state are effectively per-request by accident: the process starts, resolves one squad,
does one thing, and exits. The moment a single process becomes **long-lived and serves
more than one squad** — the squads server (FEAT-33) and the local daemon fast-path we are
weighing to kill agent-loop latency (N sequential `sq` calls each paying ~1s of Python
import) — that accident becomes a class of bug: any module-level mutable value or
import-time side-effect is now shared across unrelated requests and across squads.

This feature is the architectural precondition for both. It does not build the server; it
makes the engine **safe to run inside one**. The guarantee we are buying: *a long-lived
process serving N squads must be semantically identical to N fresh single-shot processes.*

## Requirements

1. **No module-level mutable state; no import-time side-effects for anything mutable or
   squad-specific.** Squad config, resolved paths, the active workflow/badge/collection
   spec, the roster, the clock, and the acting-actor identity must not live in module
   globals or be bound at import. They are resolved per request and threaded through an
   explicit request-scoped context, not read from a process singleton. (Standing project
   rule: thread a context object; no module-level mutable globals; no `reportPrivateUsage`
   reach-ins.)

2. **Per-request squad resolution from the client's cwd.** The active squad
   (`--dir` > `.squads.toml` walk-up > cwd) is resolved per request from *the client's*
   working directory, never from the server process's cwd and never remembered between
   requests. Two requests for two different squads handled by one process resolve fully
   independently.

3. **Context loaded on request; cacheable as code, never as data.** Draw the line hard:
   caching imported *modules* and immutable *spec/definition* objects across requests is
   fine (they are code). Caching squad *data* — items, the index, sub-entity state — across
   requests is not: every request re-reads through the filelock'd store (Invariant #1,
   frontmatter is the source of truth). No request may serve another request's stale read.

4. **Concurrency isolation.** Two concurrent requests against two different squads share no
   mutable state. Actor identity, forged time (`--at`), the active spec, and the resolved
   squad dir for request A are invisible to request B. This leans on the async-core
   locking model (FEAT-34 / ADR-153): the per-squad filelock serializes writers; this
   feature ensures the in-process ambient state above is per-request too, so isolation is
   not defeated above the lock.

## The concrete surface (grounded in the tree)

An audit of the current tree. The engine's **service layer is already clean** and is the
model to extend: `Service.spec` holds the per-invocation spec (defaulting to the bundled
one), `Service.store = IndexStore(..., spec=self.spec)`, and every service call site uses
`self.spec.<method>` and re-reads the store per call. The rendering engine
(`_rendering/_engine.py`) already uses a `ContextVar` (`_active_squad_dir`) — the correct,
concurrency-safe pattern. The offenders are the ambient "set once at the CLI root callback,
cleared by a `try/finally`" globals, which are safe **only** because the process is
one-shot.

### Must become per-request (mutable, squad/request-specific — DATA)

- **`_clock.py` `_override`** — a plain module global holding forged time (`--at` / the
  frozen-time test override). Shared across concurrent requests; request A's `--at` bleeds
  into request B. The frozen-time test mechanism monkeypatches this same global, so the
  test suite also cannot run truly concurrently against it.
- **`_actor.py` `_override`, `_session_id`, `_parent_session_id`** — ambient acting-actor
  identity and session lineage, module globals seeded once at the root callback. The worst
  offender in effect: it is *attribution*. Cross-contamination here mis-authors a comment
  or item. Must be request-scoped.
- **`_cli/_common.py` `_active_spec`** — the *active squad's* resolved spec (with its
  overrides), a module global set by `set_active_spec` and read by ~15 CLI helper call
  sites via `get_active_spec()`. Two squads in one process clobber each other's spec.
- **`_cli/_common.py` `_active_dir`** — the resolved squad folder from `--dir`, a module
  global set once by the root callback. Same problem; request-scoped.
- **`_paths.py` resolution via `Path.cwd()`** — `resolve()` / the `.squads.toml` walk-up
  default to the *process* cwd. In a server the process cwd is not the client's cwd; the
  client cwd must be an explicit input to resolution (Requirement 2), not read from the
  process.

### May stay at module level (immutable code / definitions — CODE), with a guard

- **`_backends/_registry.py` `_REGISTRY` + `_loaded` + the import-time `register()`
  side-effect in `_backends/_claude_code/__init__.py`.** This is a *code* cache: backend
  *classes*, populated once, idempotently, and instantiated fresh per call
  (`_REGISTRY[name]()`). Acceptable as-is. **Guard:** backend instances must stay stateless
  (hold no squad data between calls); enforce/assert that so the registry cannot become a
  data cache by drift.
- **`_workflow/__init__.py` `_BUNDLED_SPEC` and the derived `WORKFLOWS`/`SUBENTITY_WORKFLOWS`/
  `ALLOWED_PARENTS`/`TERMINAL` + the free-function shims** (`can_transition`, `is_open`, …).
  The bundled spec is immutable and correct **as the default**. The risk is not the
  constant; it is any caller that reaches for a module-level *shim* (`workflow.can_transition(...)`)
  instead of the active `spec.<method>` and thereby silently uses the *bundled* spec against
  a squad that customized its workflow. That is already a latent correctness bug for
  customized squads (memory: only role/skill/operator are reserved — work types are fully
  overridable) and gets far more exposed once one process serves several differently-customized
  squads. **Deliverable:** enumerate every remaining shim caller outside `Service`/the CLI
  edge and route it through the per-request spec.
- **`_roles/_catalog.py` `_CATALOG`/`_BY_SLUG`/`_PREDEFINED_BY_SLUG`,
  `_interactions/__init__.py` `_PLAYBOOK_SPEC`, `_cli/_create.py` `_create_spec`,
  `_cli/__init__.py` `_spec`/`_STATIC_TYPES`** — all bundled *defaults* loaded at import.
  Acceptable as defaults. Same audit as the workflow shims: confirm nothing consumes these
  as if they were the *active* (possibly customized) squad's catalog/playbook/type set. The
  Typer command tree built at import from `_STATIC_TYPES` is a CLI-surface concern (a server
  does not build a Typer tree) — flagged as adjacent, not in this feature's engine scope.
- **`_rendering/_engine.py` `_env_cache`** — a module dict of compiled Jinja `Environment`s
  keyed per squad dir. A *code* cache (compiled templates + the per-squad overrides loader),
  keyed correctly, so it is semantically safe. But it grows unbounded per distinct squad in
  a long-lived process and retains override loaders. **Deliverable:** bound/evict it (LRU or
  tie to a squad-context lifetime); not a correctness offender, a resource one.

### Durable enforcement (why this feature is a precondition, not a one-time sweep)

The valuable, lasting output is a **guard**, not just a cleanup: a test/lint that fails when
new module-level mutable state or a new mutable import-time side-effect is introduced in the
engine, and a documented triage rule (data → per-request context; code/definition → module
level allowed). Without the guard the property rots the next time someone adds a convenient
module global.

## Out of scope

- Building the server or the daemon transport (FEAT-33), and the async conversion itself
  (FEAT-34 / ADR-153) — this feature consumes the async locking model, it does not create
  it.
- The CLI's import-time Typer command-tree construction from the bundled type set. That is a
  `sq`-grammar / spec-customization concern (a server exposes endpoints, not a Typer tree)
  and belongs with the CLI/spec-driven work, not the engine statelessness precondition.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 533 add-story "As a <role>, I want … so that …"`; track with `sq feature 533 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Static-state inventory and enforcement guard |
| US2 | Todo |  | Request-scoped ambient context (clock, actor, active spec, active dir) |
| US3 | Todo |  | Per-request squad resolution from the client cwd |
| US4 | Todo |  | Code-vs-data cache boundary and concurrency-isolation acceptance |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Static-state inventory and enforcement guard

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Produce the definitive triage of every module-level binding in the engine, classified data (must become per-request) vs code/definition (may stay), covering at least: _clock._override; _actor._override/_session_id/_parent_session_id; _cli/_common._active_spec/_active_dir; the _paths cwd default; _backends/_registry (_REGISTRY/_loaded + import-time register()); _workflow._BUNDLED_SPEC and its free-function shims; _roles/_catalog, _interactions._PLAYBOOK_SPEC, _cli create/root bundled specs; _rendering/_engine._env_cache.

Deliver a durable guard: a meta test (and/or lint) that fails when new module-level mutable state or a new mutable import-time side-effect is introduced in the engine, plus a short documented triage rule so the classification does not rot. The guard, not the one-time sweep, is the lasting output.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Request-scoped ambient context (clock, actor, active spec, active dir)

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Replace the four ambient 'set once at the CLI root callback, cleared by try/finally' module globals with a single request-scoped context, following the ContextVar precedent already in _rendering/_engine.py: clock override (--at / frozen time), actor identity + session lineage (_actor), the active spec (_common._active_spec), and the active squad dir (_common._active_dir).

The CLI edge stays the single place that seeds the context per invocation; the frozen-time test fixture rebinds the context, not a bare module global, so tests (and concurrent requests) no longer share it. Acceptance: two logically concurrent contexts with different --at/actor/spec do not observe each other's values.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Per-request squad resolution from the client cwd

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
Make squad resolution (--dir > .squads.toml walk-up > cwd) take the requesting client's working directory as an explicit input rather than reading the process cwd via Path.cwd() in _paths.resolve()/the walk-up. In one-shot CLI use the client cwd IS the process cwd (no behaviour change); in a server the client supplies it per request.

Acceptance: one process resolving two requests whose client cwds point at two different squads yields two independent SquadPaths, with neither remembered between requests.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Code-vs-data cache boundary and concurrency-isolation acceptance

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
Codify and prove the cache boundary: module/spec/definition caches (the backend registry, the bundled specs, compiled Jinja environments) may persist across requests; squad DATA (items, index, sub-entity state) must never be cached across requests — every request re-reads through the filelock'd store (Invariant #1). Bound/evict the per-squad-dir Jinja _env_cache so a long-lived multi-squad process does not leak Environments.

Acceptance test: a long-lived process serving N interleaved requests across ≥2 squads is semantically identical to N fresh single-shot processes — a write to squad A committed by one request is read back by the next request for A, and never observed by a concurrent request for squad B.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T12:39:49Z] Robert Architect:
  - Driver: agent-loop latency (N sequential sq calls each paying ~1s of Python import) is pushing us toward a long-lived server/daemon (FEAT-33). The precondition for a long-lived process serving more than one squad is zero static squad state — hence this feature. Leans on the async-core locking model (FEAT-34 / ADR-153).
  - Origin of the ask: operator op-pierre.
- [2026-07-21T12:39:50Z] Robert Architect:
  - ADR recommendation: yes — the invariant 'no module-level mutable state; squad/request context is resolved per request and threaded, never a process singleton; caches may hold code/definitions but never squad data' is a standing rule, and rules belong in an ADR, not just a feature body (features are history, ADRs impose rules). It would formalize the data-vs-code triage as a durable constraint the enforcement guard (US1) checks against. Recommend a companion ADR; not creating it here — Pierre's call.
<!-- sq:discussion:end -->
