---
id: ADR-534
sequence_id: 534
type: decision
title: 'No module-level mutable state: per-request context, caches are code'
status: Proposed
author: architect
refs:
- FEAT-533:addresses
- ADR-71
- ADR-77
- ADR-214
- ADR-153
- ADR-249
description: 'Generalize ADR-249 to all ambient request/squad state: no module-level
  mutable state, context resolved per request and threaded; caches hold code/definitions,
  never squad data; a long-lived process is observably identical to N fresh processes.'
created_at: '2026-07-21T12:44:46Z'
updated_at: '2026-07-21T12:47:22Z'
---
<!-- sq:body -->
## Context

Every `sq` invocation is a fresh OS process today, so import-time work and module-level state
are per-request by accident: the process starts, resolves one squad, does one thing, exits.
The roadmap breaks that assumption — the squads server (FEAT-33) and the local daemon
fast-path under consideration (to kill agent-loop latency: N sequential `sq` calls each paying
~1s of Python import) both make **one process long-lived and serving more than one squad**.
The moment that holds, any module-level mutable value or mutable import-time side-effect is
shared across unrelated requests and across squads — a cross-contamination and staleness bug.

ADR-249 already killed one instance of this: the process-global workflow-spec singleton, made
`Service`-owned and threaded (executing the destination ADR-214 §1 pinned — "F3+ threads a
per-`Service` spec instance"). But 249's decision was scoped narrowly to *the workflow spec*.
The same hazard lives in the other ambient "set once at the CLI root callback, cleared by a
`try/finally`" globals, safe today only because the process is single-shot. This decision
generalizes 249's rule from the workflow spec to **all ambient request/squad state**, and
pins the cache boundary that FEAT-533 (the feature this constrains) implements and guards.

## Decision

Three binding rules for the engine below the CLI edge.

### 1. No module-level mutable state

Squad- or request-specific context — the clock, the acting actor plus session lineage, the
active workflow/badge/collection spec, the active/resolved squad directory, and the resolved
client cwd — is **resolved per request and threaded through an explicit request-scoped
context, never a process singleton.** No such value is bound at import or stored in a module
global. The `Service`-owned-and-threaded shape from ADR-249 is the model: the service layer
already carries `Service.spec` and passes it down; this rule extends the same discipline to
every remaining ambient value.

The concrete surface this governs (inventory from FEAT-533), all currently module globals set
once at the CLI root callback:

- `_clock.py::_override` — forged/frozen time (`--at`, the frozen-time test seam).
- `_actor.py::_override`, `_session_id`, `_parent_session_id` — acting-actor identity and
  session lineage (the attribution path).
- `_cli/_common.py::_active_spec` — the active (possibly customized) squad spec, read by the
  CLI helper call sites via `get_active_spec()`.
- `_cli/_common.py::_active_dir` — the resolved squad folder.
- `_paths.py::resolve()` and the `.squads.toml` walk-up defaulting to `Path.cwd()` — the
  client's cwd must be an explicit input to resolution, not read from the process.

The `ContextVar` already used for `_rendering/_engine.py::_active_squad_dir` is the sanctioned
pattern at the CLI/ambient boundary; explicit parameter/attribute threading is preferred below
it. Either way the value is task-local, never a shared module name.

### 2. Caches hold code and definitions, never squad data

A durable cache across requests is permitted **only for code and immutable definitions** —
imported modules, backend *classes* (`_backends/_registry`), the bundled `WorkflowSpec` and
the other bundled defaults, compiled Jinja `Environment`s. It is **forbidden for squad data** —
items, the index, sub-entity state, anything squad-specific. Squad data is re-read every
request through the filelock'd store. A request may never serve another request's stale read,
and a cached backend/spec/env instance must hold no squad data between calls (backend instances
stay stateless; per-squad caches such as the Jinja env cache are keyed and bounded, not a data
store). This data-vs-code line is the constraint FEAT-533 US1's enforcement guard checks
against.

### 3. A long-lived process is observably identical to N fresh processes

The invariant the first two rules buy, stated as the acceptance property: **a single
long-lived process serving N interleaved requests across any number of squads is semantically
indistinguishable from N fresh single-shot processes.** A write to squad A committed by one
request is read back by the next request for A and is never observed by a concurrent request
for squad B; forged time, actor identity, active spec, and resolved squad dir for one request
are invisible to every other. This derives directly from ADR-71 (frontmatter is the source of
truth; the index is a rebuildable cache): if the durable truth is always re-read from the
files under the lock and nothing squad-specific is retained in process, process lifetime
cannot change observable behavior.

## Reconciliation with the existing decision set

- **ADR-249 (refined).** 249's specific ruling — the workflow spec is `Service`-owned and
  threaded, the singleton machinery deleted — stays in force unchanged as the first and
  reference instance. This decision generalizes its principle to all ambient state; it does
  not supersede or reopen 249.
- **ADR-214 §1 (carried forward).** 214 §1 pinned "F3+ threads a per-`Service` spec instance"
  and 249 executed it for the spec. This decision adopts the same threading destination as the
  general rule for every ambient value, not just the spec.
- **ADR-77 (clock injectability preserved).** Time stays injectable through `_clock`: all
  timestamps route through `clock.now()`/`clock.iso()`, `--at` forges history for one request,
  and the frozen-time test fixture pins time. The only change is *where the override lives* —
  it moves from the `_clock._override` module global into the request-scoped context, so the
  override is per request rather than process-wide. Injectability and the `--at`/frozen-time
  seams are unchanged; concurrent requests (and concurrent tests) simply stop sharing one
  override cell. Rule 1 refines ADR-77's mechanism without weakening it.
- **ADR-153 (async core, related).** The async conversion provides the per-squad filelock and
  the concurrency model this rule assumes; this decision ensures the in-process ambient state
  above is per-request too, so isolation is not defeated *above* the lock. The two are
  complementary preconditions for server-mode concurrency.

## Consequences

- Every new feature that records request/squad context does so through the request-scoped
  context or explicit threading — a new module global holding such state is wrong by
  construction, and FEAT-533's guard fails the build if one is added.
- The frozen-time and actor test seams rebind the request-scoped context rather than
  monkeypatching a module global, which is what lets tests (and requests) run concurrently
  without sharing state.
- Bundled specs, backend classes, and compiled template environments may still be cached
  process-wide; the burden shifts to proving a cache holds only code/definitions, never squad
  data. `sq repair`/`sq check` (ADR-71) remain the proof that the durable truth is the files,
  not any in-process cache.
- This is an enabling constraint, not a user-visible change: a single CLI invocation behaves
  exactly as before. The value is architectural — the engine becomes safe to host in a
  long-lived, multi-squad process (FEAT-33 and the daemon fast-path).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T12:47:22Z] Robert Architect:
  - Generalizes ADR-249's narrow workflow-spec de-globalization to all ambient request/squad state (clock, actor+session, active spec, active/resolved dir, client cwd), pins the code-vs-data cache boundary FEAT-533 US1's guard enforces, and states the 'long-lived process ≡ N fresh processes' invariant (derived from ADR-71). Constrains FEAT-533. Origin of the ask: operator op-pierre.
  - Ref-kind note: intended relation to ADR-249 is 'refines/generalizes', but 'refines' isn't a valid kind (valid: duplicates, fixes, implements, related, scopes, supersedes). Did NOT use 'supersedes' — the adr lifecycle is Proposed→Accepted→Superseded, so a supersedes edge implies ADR-249 should move to Superseded, which is wrong: 249 is Accepted and implemented (FEAT-250) and stays in force as the first/reference instance. Recorded as 'related' + the refine/generalize relationship stated explicitly in the body (matches the ADR-282→ADR-104 'refines' precedent). Flag if you'd prefer the supersedes edge.
<!-- sq:discussion:end -->
