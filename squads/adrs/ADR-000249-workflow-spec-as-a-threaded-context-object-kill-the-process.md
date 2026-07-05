---
id: ADR-249
sequence_id: 249
type: decision
title: 'Workflow spec as a threaded context object: kill the process-global singleton
  (executes ADR-214 §1)'
status: Accepted
author: architect
refs:
- ADR-214:addresses
- FEAT-210:addresses
description: 'Assessment ADR (Draft): de-globalize the workflow-spec singleton into
  a Service-owned/threaded context per ADR-214 §1. Go/no-go for Pierre.'
created_at: '2026-06-30T09:47:54Z'
updated_at: '2026-06-30T09:54:38Z'
---
<!-- sq:body -->
> **STATUS: Draft / assessment.** This ADR is an architectural assessment for Pierre's go/no-go.
> Drafting is not a greenlight to implement (project norm: drafting ≠ implementation). No production
> code is to change on the strength of this draft. It executes the destination already pinned by
> **ADR-214 §1** ("F3+ threads a per-`Service` spec instance"); on acceptance it would supersede
> ADR-214 §1's threading clause.

## Context

FEAT-209 (F3, shipped) introduced a **process-global workflow-spec singleton** in
`src/squads/_workflow/__init__.py` as a *deliberate narrow rebind*, explicitly because ADR-214 §1
pinned the real destination ("F3+ threads a per-`Service` spec instance") but F3 didn't need to pay
for it yet. The global mechanism today:

- `_BUNDLED_SPEC: WorkflowSpec` (`__init__.py:39`) — loaded once at import.
- `_active_spec: list[WorkflowSpec]` (`:40`) — a **one-element list used as a mutable cell** so
  `use_spec()` can rebind by writing `_active_spec[0]` without reassigning a module name.
- `WORKFLOWS` / `SUBENTITY_WORKFLOWS` / `ALLOWED_PARENTS` (`:119-121`) — dicts **mutated in place**
  by `use_spec()` (`clear()`+`update()`, `:161-166`) so import-time captures stay live.
- `TERMINAL: frozenset` (`:124`) + `_terminal_ref: list[frozenset]` (`:125`) — frozenset is
  immutable so it's swapped via the `_terminal_ref[0]` cell **and** the module name reassigned
  (`global TERMINAL`, `:150,169-170`), leaving a documented stale-import footgun (`:92-93`).
- `use_spec(spec)` / `reset_spec()` (`:133-178`) — rebind/reset the cell + derived constants.
- `active_spec()` / `bundled_spec()` (`:181-197`) — public accessors that returned, replacing
  private `_active_spec[0]` reach-ins.
- ~13 free functions (`:205-287`) that each read `_active_spec[0]` / `_terminal_ref[0]` /
  `WORKFLOWS`.

`open_service()` (`_services/_service.py:165-212`) calls `use_spec(merged_spec)` (or
`use_spec(bundled_spec())` on the no-override fast path) once per invocation. Test isolation rests
entirely on the `_reset_workflow_spec` **autouse** fixture (`tests/conftest.py:78-90`).

This is process-global mutable state. It is correct today only because `sq` is a single-shot CLI:
one `open_service()` per process, no concurrency, no second squad in the same process. It is a
latent hazard for: a future library/daemon API, in-process tests that open two squads, and
threaded/async use. Pierre wants to do the real ADR-214 thing now: a spec **owned by `Service`** and
**threaded along the lifecycle**, deleting the module-level globals.

---

## Finding 1 — Pivotal question (a): are the pydantic models coupled to the spec? **NO. Fully decoupled.**

Confirmed concretely:

- `_models/_item.py` and `_models/_subentity.py` have **zero** imports of `_workflow` (grep clean).
- Their only validators (`_item.py:133` `_coerce_str_fields`, `_subentity.py:31` `_coerce_status`)
  do a pure StrEnum→`str` coercion + `isinstance(str)` guard. **No vocabulary lookup at construction
  time.** Post-FEAT-208 the fields are plain `str` (de-typed); nothing in model construction reaches
  workflow vocab.
- Vocabulary validation moved to the **load boundary**: `_index/_store.py:38` `_validate_item_vocab(db)`
  reads `active_spec()` (`:55-57`) and is called from `IndexStore.load()` at `:169`. It checks item
  type, item status, and each sub-entity status against `spec.items` / `spec.statuses`,
  fail-closed with `SquadsError`.

**Consequence — this is the single most important fact for sizing the refactor.** Because models are
decoupled and validation is a store-boundary concern, the refactor **never touches model construction
and never needs pydantic `model_validate(..., context=...)` threading.** The whole context-threading
problem collapses to: get a `WorkflowSpec` into (1) the `IndexStore.load()` boundary, (2) the
`Service` mixins that call the free functions, and (3) the CLI parse/print helpers. `Item`/`SubEntity`
stay exactly as they are.

---

## Finding 2 — Pivotal question (b): the CLI import-time problem and the context mechanism

The Typer app **tree** is built at module import of `_cli/__init__.py`, before any `Service`/spec is
resolved. Two distinct import-time touch points:

1. **The item-app build loop** (`_cli/__init__.py:97,121-129`): `_ORDERED_WORK_TYPES = [t for t in
   ItemType if t in _work_types()]` then `for _type in _ORDERED_WORK_TYPES: build_item_app(_type)`.
   This calls `work_types()` (→ `_active_spec[0]`) **at import time**. Today it reads the *bundled*
   spec — which is fine for built-in types but is exactly the static-type-list limitation that
   **FEAT-210 must change** (it wants `spec.managed_types()` so custom types get a `sq <type>` app).

2. **The parse helpers** `parse_type` / `parse_status` (`_cli/_common.py:684-718`). These are *not*
   import-time — they already read `active_spec()` **lazily at call time** (`:690-692`, `:706-708`).
   But they run during **Click argument parsing**, which fires *before* the group callback body
   resolves the spec. Today that's invisible because the bundled spec is correct at import and the
   override is only installed later by `open_service`; under a strict "no global" model the spec must
   already be reachable when a callback/parser runs.

**The mechanism is already present in the codebase.** The root `--dir` callback
(`_cli/__init__.py:44-75`) already sets a per-invocation module global via
`common.set_active_dir(value)` (`_common.py:52-58`), and `get_service()` (`:403-404`) /
`require_current_schema` (`:460`) read it. The spec context is the *exact same shape of problem* as
`_active_dir`: one value, set once per invocation in the root callback, read by everything downstream.

So the realistic CLI mechanism is **a per-invocation context handle set in the root callback** — a
`contextvar` (or a typed `RequestContext` object stored on Typer's `ctx.obj` and/or a module-level
contextvar in `_common`) holding the active `WorkflowSpec` (and the `Service`). The root callback
resolves the squad, loads+merges+validates the spec **once**, and binds it. `parse_type`/`parse_status`
read the contextvar instead of `active_spec()`. The *static app-tree build loop* is the only piece
that genuinely cannot read a per-invocation context (it runs before any invocation) — and that is the
FEAT-210 problem, addressed below.

**Pure parameter threading is not viable for the CLI surface** (Typer parser callbacks and the
import-time app build can't take a `spec` parameter). A contextvar-style per-invocation handle is the
honest minimum at the CLI boundary; below the CLI, parameter/attribute threading through `Service` is
clean.

---

## Global-state consumer map (grounded, per layer)

Free functions / dicts / accessors, by consumer layer (file:line):

- **Model layer:** **none.** (Finding 1.)
- **Store layer:** `_index/_store.py:55-57` — `_validate_item_vocab` reads `active_spec()`.
- **Service layer** (the bulk — all go through the free functions):
  - `_services/_base.py:41-45,206,279,402,450-451,461,467` — `initial_status`, `is_open`,
    `item_is_meta`, `parent_allowed`, `parent_hint` (ServiceCore create/list/parent-check).
  - `_services/_items.py:17,95,119,128,200,241` — `can_transition`, `item_is_meta`, `workflow_for`.
  - `_services/_maintenance.py:40-48,349,684,687,694-695,723,729,754,779,782` — the heaviest user:
    `item_is_meta`, `item_parent_required`, `item_ref_rules`, `item_subentity_kind`, `parent_allowed`,
    `parent_hint`, `status_role`, `subentity_workflow`, `workflow_for`, **plus** a direct
    `_wf.active_spec()` (`:349`). This is `sq check`.
  - `_services/_subentities.py:31,99,315,457` — `item_parent_required`, `subentity_can_transition`,
    `subentity_initial`.
  - `_services/_refs.py:22,194,421,476,481` — `is_open`.
  - `_services/_roster.py:12,137,140` — `is_open`, `item_is_meta`.
  - `_services/_collab.py:12,76` — `is_open`.
  - `_services/_retype.py:22,34,62,65,70,91-95` — `initial_status`, `parent_allowed`, `parent_hint`,
    `work_types`, `workflow_for`.
  - `_services/_service.py:185-210` — `open_service` orchestrates `use_spec`/`bundled_spec`.
- **CLI layer:**
  - `_cli/__init__.py:94,97,121` — import-time `work_types()` + app-build loop (Finding 2.1).
  - `_cli/_common.py:36,142,204,338,690,706` — `item_has_severity`, `item_subentity_kind`,
    `parse_type`, `parse_status`.
  - `_cli/_main.py:48,312,653,993,1015` — `is_open` (list filters); `bundled_spec`/`use_spec` reset
    in the `sq check` graceful-degrade path.
  - `_cli/_items.py:43` — `work_types` (item-app build helper).
- **Migrations layer:** `_migrations/_meta_compat.py:17,96` — `subentity_initial`.
- **Tests:** `_reset_workflow_spec` autouse fixture + 7 test files reference the singleton/dicts
  directly.

Roughly **~40 call sites across ~13 production modules**, concentrated in `_services/` (especially
`_maintenance.py`).

---

## Options

### Option A — Full `Service`-owned spec, threaded; CLI per-invocation context handle

The literal ADR-214 §1 destination.

- `Service` gains a `spec: WorkflowSpec` attribute (resolved in `open_service`, no global rebind).
- The ~13 free functions become **methods on `WorkflowSpec`** (most already exist there —
  `spec.parent_allowed`, `spec.can_transition`, `spec.work_types`, the capability flags). Service
  mixins call `self.spec.<method>` instead of the free functions. `is_open` becomes
  `spec.is_open(status)` (trivial: `status not in spec.terminal_set()`).
- `IndexStore` receives the spec (constructor arg or `load(spec)` param) so `_validate_item_vocab`
  takes it explicitly — removes the lazy `_workflow` import + cycle dance.
- CLI: root callback resolves+binds a per-invocation `WorkflowSpec` into a `contextvar` (or
  `ctx.obj`); `parse_type`/`parse_status`/`_common` printers read it. The module-level singleton,
  `_active_spec`, `use_spec`, `reset_spec`, the in-place dict mutation and `_terminal_ref` cell, and
  the autouse fixture **are deleted.**
- **Effort:** high. ~40 call sites + IndexStore signature + CLI context plumbing + delete the global
  machinery + rewrite the 8 test files that lean on the singleton.
- **Risk:** medium. Mechanical but broad; `_maintenance.py` (`sq check`) is dense. The subtle risk is
  the CLI parse-time ordering (parsers fire before the callback body) — must verify the contextvar is
  bound before any `parse_type` runs, or move type/status validation out of the Typer parser into the
  command body.
- **Blast radius:** every service mixin signature or call site; IndexStore; CLI common. Wide but shallow.
- **Test impact:** delete the autouse reset fixture (no more global to reset — a *correctness win*);
  rewrite 7 test files to construct/pass a spec; the FEAT-208 characterization + golden-lock + spine
  tests are the safety net. Net test count likely drops.
- **Does NOT solve** the import-time app-build loop (Finding 2.1) — that stays bundled-spec-driven
  until FEAT-210.

### Option B — Fold the de-globalization INTO FEAT-210 as its foundation

FEAT-210 already **must** rework the same import-time CLI registration to be spec-driven
(`spec.managed_types()` instead of the static loop) and already declares "the `WorkflowSpec` must be
loaded before the CLI app tree is built — a startup-ordering change." That startup-ordering change is
the *same* change Option A needs for the CLI. Doing the threading as 210's first task means 210
builds on a clean per-`Service`/per-invocation spec rather than reaching through a global.

- **Effort:** the threading effort is the same as A, but **shared** with work 210 must do anyway — no
  duplicated CLI-startup rework.
- **Risk:** medium-high *scheduling* risk — couples a large mechanical refactor to a user-visible
  feature in one feature's lifecycle; harder to land behavior-preserving in isolation; a regression in
  210 and a regression in the threading become hard to bisect apart.
- **Blast radius / test impact:** same as A, plus 210's renderer/skill/folder work on top.

### Option C — Lighter contextvar-only de-globalization (de-global without full method-threading)

Keep the free-function *interface* but back it with a `contextvar[WorkflowSpec]` instead of the
`_active_spec` list + in-place-mutated dicts. The root callback / `open_service` sets the contextvar;
free functions read `_active_spec_var.get()`.

- Removes the worst footguns: the mutable-cell list, the in-place dict mutation, the `TERMINAL`
  stale-import hazard, the `global` reassignment. Per-invocation isolation becomes real (contextvars
  are task-local), so the autouse reset fixture can go.
- **Effort:** low-medium. Touches only `_workflow/__init__.py` internals + the set-site in
  `open_service`; the ~40 call sites are **untouched** (same free-function API).
- **Risk:** low. Smallest blast radius; behavior-preserving by construction.
- **Limitation:** it **de-globalizes but does not thread** — the spec still isn't *owned by* `Service`,
  it's an ambient contextvar. That's a weaker form of ADR-214 §1 (ambient context, not explicit
  dependency). It also still does **not** solve the import-time app-build loop. It's a strict
  improvement over today and a clean stepping stone, but it is not "the real thing" Pierre asked for.

---

## Recommendation

**Option A, sequenced as a prerequisite ADR/feature done BEFORE FEAT-210 — not folded into it.**

Rationale:

1. **Finding 1 makes A tractable.** With models decoupled and vocab validation already at the store
   boundary, A is a wide-but-shallow mechanical refactor with a *strong existing safety net* (FEAT-208
   characterization + golden-lock + spine tests, AC "golden remains green"). There is no pydantic
   `context=` threading to invent. This is the moment it is cheapest to do.
2. **Keep it behavior-preserving and independently bisectable.** A de-globalization that changes *no*
   user-visible behavior should land on its own, golden-locked, so any regression is unambiguously the
   refactor. Folding it into 210 (Option B) entangles a mechanical refactor with a user-facing feature
   and makes regressions hard to attribute. **FEAT-210 entanglement verdict: (a) prerequisite, done
   first** — 210 then *consumes* a clean per-invocation spec for its `spec.managed_types()` app loop
   instead of having to both de-global *and* go dynamic in one feature.
3. **The import-time app-build loop (Finding 2.1) is explicitly left to FEAT-210.** Option A delivers
   the per-invocation spec context that 210's dynamic app build needs; it does not itself make the app
   tree dynamic. This is the correct seam: A owns "the spec is threaded/contextual, not global"; 210
   owns "the CLI app tree is built from the live spec." Clean split.
4. **Option C is the fallback** if Pierre wants the footgun gone with minimal churn and is willing to
   accept ambient-context rather than `Service`-owned. C is also a perfectly good *first step* of A
   (introduce the contextvar, then incrementally move free functions to `spec` methods) if he wants to
   de-risk by splitting A into two landings.

**Effort/risk read:** Option A ≈ a medium feature (1 focused task for the `_workflow` core +
IndexStore, 1 for the service-layer call-site sweep, 1 for the CLI context handle + parse helpers, 1
for the test rewrite), **medium risk, behavior-preserving, golden-locked.** Option C ≈ a small task,
low risk. The CLI parse-time ordering (parsers fire before the callback) is the one genuine design
detail to nail in either A or C — likely by binding the contextvar in the root callback before
subcommand parse, or relocating type/status validation from the Typer parser into the command body.

---

## Open questions for Pierre's go/no-go

- A vs. C: do you want the full `Service`-owned-and-threaded form (A), or is the ambient-contextvar
  de-globalization (C) enough for now (and A later / incrementally)?
- Confirm A-before-210 sequencing (vs. fold-in). My recommendation is **separate, first**.
- If A: are we comfortable deleting the `_reset_workflow_spec` autouse fixture and rewriting the 7
  singleton-touching test files in the same feature? (It's a net correctness win but it is churn on
  the EPIC-206 safety net — coordinate with the deferred test-suite rebuild.)

**This ADR is Draft. No implementation, no tasks, until Pierre greenlights.**
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T09:48:16Z] Robert Architect:
  - Draft assessment ADR for the workflow-spec de-globalization Pierre wants — executes ADR-214 §1 (per-Service/threaded spec), which it would supersede on acceptance. Grounded in the actual code, ~40 call sites across 13 modules inventoried per layer in the body. NOT a greenlight: drafting ≠ implementation, no tasks until Pierre's go/no-go.
  - Pivotal finding (a) — model coupling: NONE. _models/_item.py and _subentity.py have zero _workflow imports; their only validators do pure StrEnum→str coercion (no vocab lookup). FEAT-208 already moved all vocab validation to the load boundary (_index/_store.py:38 _validate_item_vocab, reads active_spec(), called from IndexStore.load():169). So the refactor never touches model construction and needs NO pydantic model_validate(context=) threading — this is what makes it tractable.
  - Pivotal finding (b) — CLI context mechanism: a per-invocation context handle (contextvar or ctx.obj) set in the root --dir callback, NOT pure parameter threading. The precedent already exists: the callback sets common.set_active_dir() the same way. parse_type/parse_status already read active_spec() lazily but fire during Click parse (before the callback body) — that ordering is the one detail to nail. The import-time app-build loop (_cli/__init__.py:97,121) is the only piece a per-invocation context can't reach — and that is FEAT-210's job, not this one.
  - FEAT-210 entanglement verdict: PREREQUISITE, done FIRST and separately — not folded in. 210 already must make the CLI app tree spec-driven (spec.managed_types()); this ADR gives it a clean per-invocation spec to build on, and keeps the mechanical de-global behavior-preserving + golden-locked + independently bisectable. Folding into 210 entangles a refactor with a user-facing feature.
  - Recommendation: Option A (full Service-owned + threaded spec; delete the singleton/_active_spec list/in-place dict mutation/_terminal_ref/use_spec/reset_spec/autouse fixture). Effort medium (~4 tasks: workflow core+IndexStore, service call-site sweep, CLI context handle, test rewrite), risk medium, behavior-preserving under the FEAT-208 characterization+golden safety net. Fallback Option C: contextvar-only de-global (low effort/risk) that keeps the free-function API and is also a clean first step of A. Open Qs for Pierre in the body: A vs C, sequencing confirm, and the autouse-fixture/7-test-file churn on the EPIC-206 net.
- [2026-06-30T09:51:35Z] Catherine Manager:
  - Pierre (op-pierre) selected Option A: full Service-owned threaded WorkflowSpec — delete the process-global singleton (use_spec/reset_spec, in-place dict mutation, _terminal_ref, autouse reset fixture). Sequenced as a standalone prerequisite feature BEFORE FEAT-210, accepting the rewrite of the 7 singleton-touching test files. Greenlit for implementation.
- [2026-06-30T09:54:38Z] Olivia Lead:
  - Broke Option A down under FEAT-250 (grouping feature, parented to EPIC-206, addresses this ADR, blocks FEAT-210 — sq blocked now shows 210 waiting on it). Internal refactor, no user stories; acceptance = behaviour byte-identical (FEAT-208 characterization + golden-lock green) with the singleton deleted.
  - Four sequenced tasks (a→b→c→d, depends-on refs recorded): TASK-251 workflow core (free fns → spec methods + IndexStore takes the spec); TASK-252 service call-site sweep (Service.spec attr, ~40 sites incl. _maintenance/sq check + the _meta_compat migration); TASK-253 CLI per-invocation spec handle (root --dir callback binds it, parse_type/parse_status read it — Click parse-ordering nailed per Finding 2); TASK-254 test rewrite of the singleton-touching files + delete the _reset_workflow_spec autouse fixture.
  - Hard scope line carried in every task body: the import-time app-build loop (_cli/__init__.py for-loop) stays bundled-spec-driven and is FEAT-210's job — this feature owns 'spec is threaded/contextual', 210 owns 'app tree built from live spec'. Left all tasks Draft for Catherine to schedule.
<!-- sq:discussion:end -->
