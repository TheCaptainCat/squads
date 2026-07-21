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
  title: Request-scoped context primitive + clock/actor seam
  status: Todo
- local_id: US3
  title: Per-request squad resolution from the client cwd
  status: Todo
- local_id: US4
  title: Code-vs-data cache boundary and concurrency-isolation acceptance
  status: Todo
- local_id: US5
  title: Active-spec / active-dir seam onto the request context
  status: Todo
created_at: '2026-07-21T12:37:58Z'
updated_at: '2026-07-21T20:58:23Z'
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
| US2 | Todo |  | Request-scoped context primitive + clock/actor seam |
| US3 | Todo |  | Per-request squad resolution from the client cwd |
| US4 | Todo |  | Code-vs-data cache boundary and concurrency-isolation acceptance |
| US5 | Todo |  | Active-spec / active-dir seam onto the request context |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Static-state inventory and enforcement guard

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Produce the definitive triage of every module-level binding in the engine, classified **data**
(must become per-request) vs **code/definition** (may stay), covering at least: `_clock._override`;
`_actor._override`/`_session_id`/`_parent_session_id`; `_cli/_common._active_spec`/`_active_dir`;
the `_paths` cwd default; `_backends/_registry` (`_REGISTRY`/`_loaded` + import-time `register()`);
`_workflow._BUNDLED_SPEC` and its derived constants/shims; `_roles/_catalog`,
`_interactions._PLAYBOOK_SPEC`, `_cli` create/root bundled specs; `_rendering/_engine._env_cache`;
`_overrides/_manifest._manifest_cache`.

**Workflow-constant reach is audit-only in this feature.** A grep confirms zero production
(`src/`) caller reaches the module-level free-function shims (`workflow.can_transition()`,
`is_open`, `parent_allowed`, …) or the derived constants (`WORKFLOWS`/`SUBENTITY_WORKFLOWS`/
`ALLOWED_PARENTS`/`TERMINAL`) — only the golden-lock tests reference them, and the service layer
already routes through `Service.spec`/`get_active_spec()`. So the deliverable here is to **confirm
no production caller reaches the bundled workflow constants as if they were the active spec
(audit-only)** — not a code reroute. The customization-exposed reroute (routing customized-spec
consumers off `WORKFLOWS`/`ALLOWED_PARENTS`/`TERMINAL`/`_PLAYBOOK_SPEC` so a customized squad's
own vocabulary is honoured) is a *consumer audit* handed to EPIC-538, not part of this story.

**Durable guard — pin the mechanism.** An AST meta-test that scans the engine modules for two
constructs at module scope: (a) top-level assignments binding a mutable type (`dict`/`list`/`set`
literal or constructor), and (b) `global` statements. It checks every hit against an explicit
allowlist of the sanctioned **code** caches, which are the only module-level mutable bindings we
accept:

- `_backends/_registry.py`: `_REGISTRY`, `_loaded`
- `_workflow/__init__.py`: `_BUNDLED_SPEC` + the derived `WORKFLOWS`, `SUBENTITY_WORKFLOWS`,
  `ALLOWED_PARENTS`, `TERMINAL`
- `_rendering/_engine.py`: `_env_cache`
- `_roles/_catalog.py`: `_CATALOG`, `_BY_SLUG`
- `_interactions/__init__.py`: `_PLAYBOOK_SPEC`
- `_cli/_create.py`: `_create_spec`
- `_cli/__init__.py`: `_spec`, `_STATIC_TYPES`
- `_overrides/_manifest.py`: `_manifest_cache`

The assertion: **no NEW module-level mutable binding exists outside that allowlist.** Adding a
convenient module global later fails the build until it is either moved to the request-scoped
context or (if genuinely a code/definition cache) added to the allowlist with a justification.
Ship a short documented triage rule (data → per-request context; code/definition → module level,
allowlisted) alongside the test so the classification does not rot. The guard, not the one-time
sweep, is the lasting output.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Request-scoped context primitive + clock/actor seam

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Introduce the request-scoped **context primitive** — the single object that carries per-request
ambient state — following the `ContextVar` precedent already proven in `_rendering/_engine.py`
(`_active_squad_dir`). Migrate the two purely-ambient seams onto it in this story:

- **Clock override** — `_clock._override` (the `--at` forge and the frozen-time test seam), today
  a plain module global read by `clock.now()`.
- **Actor identity + session lineage** — `_actor._override` and `_session_id`/`_parent_session_id`,
  the attribution path seeded once at the root callback.

**The conftest migration is real work, not a rename.** `tests/conftest.py::frozen_time`
monkeypatches `clock.now` directly (`monkeypatch.setattr(clock, "now", lambda: fixed)`) — it does
**not** go through `_clock._override`/`set_now`. Once time lives in the request-scoped context,
`frozen_time` must rebind *the context*, and the leak-guard fixtures (`_reset_clock_override`,
`_reset_actor`, `_reset_session_seed`) that currently reset module globals have to be reworked to
reset/rebind the context instead. Budget for genuinely rewiring these fixtures.

**Extensibility is a requirement of the primitive.** The context must be open to more fields
without a redesign: EPIC-538 will later fold the playbook spec (and other customization vocab)
into this same context. Design the container so adding a field is additive.

**Undecided design point — for the architect (flag, do not decide here).** ADR-534 sanctions both
a `ContextVar` at the CLI/ambient edge *and* explicit parameter/attribute threading below it, but
does not pick the context's concrete shape. The open question the architect should settle before
build: is the request-scoped context **one `ContextVar` holding a single context object** at the
CLI edge, **N separate `ContextVar`s** (one per ambient value), or **folded into `Service`** (the
ADR-249 threaded-attribute shape)? This choice governs both this story and the active-spec/
active-dir sibling story, so it wants deciding once, up front.

Acceptance: two logically concurrent contexts with different `--at`/actor/session values do not
observe each other's values; a single one-shot CLI invocation behaves exactly as today.
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

<!-- sq:story:US5 -->
### US5 — Active-spec / active-dir seam onto the request context

<!-- sq:story:US5:head -->
**Status:** ⚪ Todo
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
The second half of the former oversized US2 (its sibling is the context-primitive + clock/actor
story): move the two remaining CLI-edge ambient globals onto the **same request-scoped context**
primitive that sibling story builds.

- **`_cli/_common._active_spec`** — the active (possibly customized) squad `WorkflowSpec`, set by
  `set_active_spec()` and read everywhere via `get_active_spec()`. This is the larger of the two:
  ~15 `get_active_spec()` consumer call sites across the CLI helpers (`_common`, `_items`,
  `_create`, `_workflow_cmd`, `_main`) plus `_workflow/__init__` and the lazy-dispatch path in
  `_cli/__init__::_CustomTypeGroup` reach for it. Each must read the spec off the context rather
  than a module global. The `_CustomTypeGroup`/`_CustomCreateGroup` reach-in
  (`common._active_spec`) and their `_custom_cmd_cache` ClassVars are part of the surface.
- **`_cli/_common._active_dir`** — the resolved squad folder from `--dir`, set once by the root
  callback and read by `get_service()`, `version_notice()`, `require_current_schema()`.

The CLI edge (`main_callback` in `_cli/__init__.py`) stays the **single place** that seeds the
context per invocation — `set_active_dir` / `_bind_active_spec` become "seed the context", not
"assign a module global". The context's concrete shape is the architect design point flagged on
the sibling story; this story consumes whatever that decision produces.

Note the fallback contract must survive: `get_active_spec()` returns the bundled spec when nothing
is bound yet (parse-time validators, outside a squad), and `_bind_active_spec` fails soft to the
bundled spec on any resolution error — both behaviours are preserved against the context.

Acceptance: two logically concurrent contexts resolving two differently-customized squads each see
their own spec and dir; neither observes the other's, and a one-shot CLI invocation is unchanged.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T12:39:49Z] Robert Architect:
  - Driver: agent-loop latency (N sequential sq calls each paying ~1s of Python import) is pushing us toward a long-lived server/daemon (FEAT-33). The precondition for a long-lived process serving more than one squad is zero static squad state — hence this feature. Leans on the async-core locking model (FEAT-34 / ADR-153).
  - Origin of the ask: operator op-pierre.
- [2026-07-21T12:39:50Z] Robert Architect:
  - ADR recommendation: yes — the invariant 'no module-level mutable state; squad/request context is resolved per request and threaded, never a process singleton; caches may hold code/definitions but never squad data' is a standing rule, and rules belong in an ADR, not just a feature body (features are history, ADRs impose rules). It would formalize the data-vs-code triage as a durable constraint the enforcement guard (US1) checks against. Recommend a companion ADR; not creating it here — Pierre's call.
- [2026-07-21T20:08:03Z] Pierre Chat:
  - Sequenced as Phase 1 ahead of the spec-customization epics (EPIC-538 rides this seam). See EPIC-538 for the full sequencing note.
- [2026-07-21T20:52:59Z] Olivia Lead:
  - Refined the stories for clean, one-task-sized decomposition (still Draft — no tasks, not Ready).
  - Split the oversized US2 into US2 (request-scoped context primitive + clock/actor seam, incl. the real conftest rework — frozen_time monkeypatches clock.now directly, not _override, so it's a genuine fixture migration) and US5 (active-spec/active-dir seam onto the same context). Both flag the context primitive must stay extensible so EPIC-538 can fold the playbook spec into it.
  - Narrowed US1's workflow-shim work to audit-only: grep confirms zero src callers reach the module free functions (workflow.can_transition() etc.) or the derived WORKFLOWS/ALLOWED_PARENTS/TERMINAL constants — only golden-lock tests do, and the service layer already routes through Service.spec. The customization-exposed reroute (honouring a customized squad's own vocab) is handed to EPIC-538's consumer audit, not this feature.
  - Pinned US1's guard mechanism: an AST meta-test scanning engine modules for module-scope mutable-type assignments (dict/list/set) or global statements, checked against an explicit allowlist of the sanctioned code caches (_REGISTRY/_loaded; _BUNDLED_SPEC + derived WORKFLOWS/SUBENTITY_WORKFLOWS/ALLOWED_PARENTS/TERMINAL; _env_cache; _CATALOG/_BY_SLUG; _PLAYBOOK_SPEC; _create_spec; _spec/_STATIC_TYPES; _manifest_cache). Asserts: no NEW module-level mutable binding outside the allowlist.
  - Flagged the one open design point for @architect on US2: whether the request-scoped context is a single ContextVar at the CLI edge, N ContextVars, or folded into Service (ADR-534 sanctions ContextVar-at-edge and threading below it, but doesn't pick the shape). Flagged, not decided — wants settling once before build since it governs US2 and US5.
- [2026-07-21T20:58:23Z] Robert Architect:
  - DESIGN DECISION (settles the US2/US5 open point flagged by @tech-lead): shape = (a) a SINGLE request-scoped context object held in ONE ContextVar, seeded at the CLI edge, read at the ambient boundary via thin accessor free-functions, and threaded into Service below. Rejected (b) N-ContextVars and (c) fold-into-Service.
  - Rationale: (c) is impossible — active_spec/active_dir are read at parse time (parse_type/parse_status, _CustomTypeGroup lazy dispatch) and by get_service()/version_notice()/require_current_schema() BEFORE any Service exists, and clock.now()/actor.current_session() are free-function reads from models with no Service handle; you can't thread a Service through Typer's parse machinery. (b) works mechanically and matches the _active_squad_dir precedent literally, but multiplies seed points, leak-guard reset fixtures, and gives a server no single per-request object to construct/bind — and it fails the extensibility bar: EPIC-538 folding the playbook spec + customization vocab means adding yet more vars. (a) is one object a server/test builds per request, one rebind in conftest, and additive extension (add a field). It is exactly ADR-534's 'ContextVar at the CLI/ambient edge + explicit threading below it', and it preserves ADR-249 unchanged (Service still owns spec/store by attribute).
  - THE SEAM — which values live in the ContextVar vs get threaded:
  - In the ContextVar (RequestContext object; the ambient values read by free functions or at parse time, i.e. no natural owner object at the read site): clock override (--at / frozen-time); actor identity + session lineage (session_id, parent_session_id); active WorkflowSpec; active/resolved squad dir; client cwd (US3 resolution input). These are reached ONLY through thin accessors that read the context — clock.now(), actor.current_actor()/current_session(), get_active_spec(), and the active-dir readers (get_service/version_notice/require_current_schema).
  - Threaded below the edge (ADR-249 shape, unchanged): the resolved WorkflowSpec and IndexStore live on Service as Service.spec/Service.store, plus SquadPaths. Nothing below open_service reads the ContextVar for spec — open_service reads the context to CONSTRUCT the Service, then Service owns its spec by attribute and threads it. So spec appears in both places by design, not duplication: the context is the parse-time/CLI-edge SOURCE that seeds Service; Service is the threaded carrier for the below-edge path.
  - clock/actor below the edge: Service.create()/_locked_section_edit() keep calling clock.now()/actor.current_session() as FREE FUNCTIONS (not threaded params) — only their backing store moves from a module global into the ContextVar. That is precisely ADR-77's injectable-clock seam preserved (the indirection stays; models never take a clock arg), and ADR-534's 'ADR-77 mechanism refined, not weakened'.
  - Boundary rule for the dev: the ContextVar is SEEDED/REBOUND only at the CLI edge (main_callback replaces its four seed calls — set_active_dir/apply_timestamp/set_actor/seed_session — with one bind_context(RequestContext(...))), by a server request handler, and by test fixtures. It is READ only through the accessor free-functions above. No code below open_service reads the ContextVar directly. Suggested home: a new _context.py holding RequestContext + the single ContextVar + bind/get; _clock and _actor keep their public function names (now reading the context), so their ~all call sites are untouched.
  - conftest migration (US2, real work): frozen_time rebinds the context's clock field (not monkeypatch clock.now); _reset_clock_override/_reset_actor/_reset_session_seed collapse into one context-reset/rebind fixture.
  - ADR? No — feature-level implementation decision. ADR-534 already pins the standing rule (no module-level mutable state; ContextVar-at-edge + threading-below; caches are code) and explicitly sanctions this pattern; choosing 'one object vs N vars' is the concrete container shape within it, not a new durable constraint. Capture the 'single RequestContext object, not per-value vars' convention in US1's documented triage rule so it doesn't rot; no new ADR needed.
<!-- sq:discussion:end -->
