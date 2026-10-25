---
id: ADR-534
sequence_id: 534
type: decision
title: 'No module-level mutable state: per-request context, caches are code'
status: Accepted
author: architect
refs:
- FEAT-533:addresses
- ADR-71
- ADR-77
- ADR-214
- ADR-153
- ADR-249
- ADR-117
- ADR-1009
description: 'Generalize ADR-249 to all ambient request/squad state: no module-level
  mutable state, context resolved per request and threaded; caches hold code/definitions,
  never squad data; a long-lived process is observably identical to N fresh processes.'
created_at: '2026-07-21T12:44:46Z'
updated_at: '2026-10-25T21:33:10Z'
---
<!-- sq:body -->
## Context

A single-shot `sq` process makes import-time work and module-level state per-request by
accident: the process starts, resolves one squad, does one thing, exits. A long-lived process
serving more than one squad (the daemon, ADR-1052, and a squads server) breaks that assumption:
any module-level mutable value or mutable import-time side effect is then shared across
unrelated requests and squads, a cross-contamination and staleness bug.

ADR-249 removed one instance, the process-global workflow-spec singleton, by making the spec
`Service`-owned and threaded. This decision generalizes that rule from the workflow spec to
**all ambient request and squad state**, and pins the cache boundary FEAT-533 implements and
guards.

## Decision

Three binding rules for the engine below the CLI edge.

### 1. No module-level mutable state

Squad- or request-specific context is **resolved per request and carried in an explicit
request-scoped context, never a process singleton.** No such value is bound at import or stored
in a module global. That context is `RequestContext` in `_context.py`: one task-local
`ContextVar`, seeded and rebound only at the CLI edge (or a request handler), and read only
through its accessor functions. Its fields are the clock override (`--at`, the frozen-time test
seam), the acting actor and session lineage, the active workflow spec (and why a squad's
override failed to load, if it did), and the client's effective working directory
(`client_cwd`, computed once from the process cwd and any `-C` values, ADR-1009). The squad
directory is not a field: squad resolution is the `.squads.toml` walk-up from `client_cwd`.

Below `open_service`, values are threaded explicitly (`Service.spec`, `.playbook`, `.catalog`,
and the squad directory passed as an argument, for example to every template entry point);
nothing below it reads the `ContextVar` directly. Either way the value is task-local, never a
shared module name.

### 2. Caches hold code and definitions, never squad data

A durable cache across requests is permitted **only for code and immutable definitions**:
imported modules, backend classes (`_backends/_registry`), the bundled spec documents and other
bundled defaults, compiled Jinja `Environment`s. It is **forbidden for squad data**: items, the
index, sub-entity state, anything squad-specific. Squad data is re-read every request through the
filelock'd store. A request never serves another request's stale read, and a cached backend,
spec or environment holds no squad data between calls: backend instances are stateless, and a
per-squad cache such as the Jinja environment cache is keyed on the squad directory and bounded
(LRU), not a data store. This data-versus-code line is what the `tests/meta` mutable-state guard
checks: a module-level mutable binding fails the build unless it is allowlisted as a code
constant.

### 3. A long-lived process is observably identical to N fresh processes

The acceptance property the first two rules buy: **a single long-lived process serving N
interleaved requests across any number of squads is semantically indistinguishable from N fresh
single-shot processes.** A write to squad A committed by one request is read back by the next
request for A and never observed by a concurrent request for squad B; forged time, actor
identity, active spec and working directory for one request are invisible to every other. This
derives from ADR-71: if the durable truth is always re-read from the files under the lock and
nothing squad-specific is retained in process, process lifetime cannot change observable
behaviour.

## Reconciliation with the existing decision set

- **ADR-249 (refined).** Its ruling, the workflow spec `Service`-owned and threaded with the
  singleton deleted, stays in force as the first and reference instance. This decision
  generalizes the principle; it does not reopen 249.
- **ADR-214 §1 (carried forward).** The per-`Service` threading destination 214 pinned for the
  spec is the general rule for every ambient value.
- **ADR-77 (clock injectability preserved).** Every timestamp goes through `clock.now()` /
  `clock.iso()`; `--at` forges history for one request and the frozen-time fixture pins time. The
  override lives in the request-scoped context, so concurrent requests and tests never share one
  override cell.
- **ADR-153 (async core).** The async core provides the per-squad filelock and concurrency model;
  this decision keeps in-process ambient state per request too, so isolation is not defeated above
  the lock.

## Consequences

- A new feature that records request or squad context does so through `RequestContext` or
  explicit threading; a new module global holding such state is wrong by construction, and the
  guard fails the build.
- The frozen-time and actor test seams rebind the request-scoped context rather than
  monkeypatching a module global, which lets tests and requests run concurrently.
- Bundled specs, backend classes and compiled template environments may be cached process-wide;
  the burden is on proving a cache holds only code or definitions. `sq repair` and `sq check`
  (ADR-71) remain the proof that the durable truth is the files.
- A single CLI invocation is unaffected; the value is architectural, making the engine safe to
  host in a long-lived, multi-squad process.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T12:47:22Z] `architect` Robert Architect:
  - Generalizes ADR-249's narrow workflow-spec de-globalization to all ambient request/squad state (clock, actor+session, active spec, active/resolved dir, client cwd), pins the code-vs-data cache boundary FEAT-533 US1's guard enforces, and states the 'long-lived process ≡ N fresh processes' invariant (derived from ADR-71). Constrains FEAT-533. Origin of the ask: operator op-pierre.
  - Ref-kind note: intended relation to ADR-249 is 'refines/generalizes', but 'refines' isn't a valid kind (valid: duplicates, fixes, implements, related, scopes, supersedes). Did NOT use 'supersedes' — the adr lifecycle is Proposed→Accepted→Superseded, so a supersedes edge implies ADR-249 should move to Superseded, which is wrong: 249 is Accepted and implemented (FEAT-250) and stays in force as the first/reference instance. Recorded as 'related' + the refine/generalize relationship stated explicitly in the body (matches the ADR-282→ADR-104 'refines' precedent). Flag if you'd prefer the supersedes edge.
- [2026-07-21T20:55:42Z] `op-pierre` Pierre Chat:
  - Accepted. Gap review found ADR-534 accept-ready (sound rules, clean reconciliation with ADR-249/71/77/153); the three inventory nits — _overrides/_manifest.py::_manifest_cache, the 2nd backend's import-time register(), and _cli/_main.py::_is_tty — are all CODE and flow to FEAT-533 US1's guard allowlist, not blockers.
- [2026-08-03T12:30:52Z] `manager` Catherine Manager:
  - Carrier asymmetry between the two merged documents, recorded because it is currently justified by nothing written down. The merged workflow spec is carried on the request context AND on the service; the merged playbook only on the service. That is not arbitrary: the spec has dispatch-time consumers that run before any service exists — the CLI builds its own command tree from it, deciding which type commands to register and what badge help to render — whereas nothing consults the playbook to build the CLI, only to generate skill text once a service exists. Verified: zero playbook references in the command-tree construction. The rule that follows is that a document needs a context carrier only when something must read it before a service can be constructed. Worth stating in the decision text if a later pass touches this, because the next dispatch-time playbook consumer will otherwise either add a second carrier or reach for the bundled singleton.
- [2026-10-25T21:33:10Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the three rules are unchanged. The §1 inventory listed module globals that no longer exist (_clock._override, _actor session globals, _common._active_spec/_active_dir, the _rendering _active_squad_dir ContextVar); it now describes RequestContext in _context.py and its fields, folding the dated ADR-1009 note (client_cwd, no squad-dir field) and explicit squad-dir threading for templates. §2 names the tests/meta mutable-state guard and the LRU-bounded env cache. The daemon is cited as ADR-1052 instead of a fast-path under consideration.
<!-- sq:discussion:end -->
