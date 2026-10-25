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
description: De-globalize the workflow-spec singleton into a Service-owned and threaded
  context, per ADR-214 §1.
created_at: '2026-06-30T09:47:54Z'
updated_at: '2026-10-25T21:36:59Z'
---
<!-- sq:body -->
## Context

ADR-214 §1 pins where the workflow spec lives at runtime: a spec instance **owned by `Service`** and
**threaded along the request**, not a process-global. A process-global spec singleton — a mutable
cell rebound per invocation, derived dicts mutated in place, a module-level frozenset swapped with a
stale-import hazard, and an autouse test fixture resetting it all — is correct only while `sq` is a
single-shot CLI: one service per process, no concurrency, no second squad in the same process. It is a
latent hazard for a library or daemon API, for in-process tests that open two squads, and for
threaded or async use. This decision executes ADR-214 §1.

Two facts size the change:

- **The pydantic models are not coupled to the spec.** `Item` and `SubEntity` import nothing from
  `_workflow`, and their validators do no vocabulary lookup; vocabulary validation happens at the
  index load boundary (ADR-232). So threading the spec never touches model construction and needs no
  `model_validate(..., context=...)`. The problem reduces to getting a `WorkflowSpec` into (1) the
  `IndexStore` load boundary, (2) the service mixins, and (3) the CLI parse/print helpers.
- **The CLI needs a per-invocation handle, not parameters.** Typer parser callbacks and the CLI's
  command-tree construction cannot take a `spec` parameter, and type/status parsing runs during Click
  argument parsing, before a command body runs. The precedent is the per-invocation value the root
  callback already binds — the active squad directory — which is the same shape of problem: one value,
  set once per invocation, read by everything downstream.

## Options considered

- **Option A — a `Service`-owned spec, threaded; a per-invocation context handle at the CLI.** The
  free functions become methods on `WorkflowSpec`; services call `self.spec.<method>`; `IndexStore`
  receives the spec explicitly; the CLI reads a per-invocation handle bound at the root. The
  singleton, its rebinding, the in-place dict mutation and the autouse reset fixture are deleted.
  Wide but shallow, behavior-preserving under the characterization and golden-lock safety net.
- **Option B — fold the de-globalization into FEAT-210** (custom types), which must also make the CLI
  command tree spec-driven. Rejected: it couples a large mechanical refactor to a user-visible
  feature, making a regression in either hard to bisect from the other.
- **Option C — an ambient `ContextVar` behind the unchanged free-function API.** De-globalizes without
  threading: the spec is still not *owned by* `Service`. A weaker form of ADR-214 §1, kept as the
  fallback and rejected as the destination.

## Decision

**Option A, as a standalone prerequisite of FEAT-210** (op-pierre). The workflow spec is owned by
the `Service` and threaded, and there is no process-global mutable spec:

- **Spec capabilities are methods on `WorkflowSpec`** (`spec.can_transition(...)`,
  `spec.parent_allowed(...)`, `spec.non_roster_types()`, the capability accessors). Service mixins
  call `self.spec.<method>`.
- **`IndexStore` takes the spec explicitly** and validates item vocabulary at load against it.
- **The CLI binds the active spec once per invocation** on the request context (ADR-534), resolved by
  the root callback before any subcommand parses; `_cli._common.get_active_spec()` reads it, falling
  back to the bundled spec only before one is bound, and refusing when the squad's override failed to
  resolve.
- **The bundled spec** is a separate, immutable value loaded once at import (`bundled_spec()`), passed
  explicitly only where the bundled document is meant.
- The singleton cell, its rebind/reset functions, the in-place dict mutation, the frozenset swap and
  the autouse reset fixture do not exist.

The CLI command tree being built from the live spec, so a custom type gets its own `sq <type>`
command, is FEAT-210's (ADR-263); this decision owns "the spec is threaded, not global".

## Consequences

- **Isolation is real.** Two squads in one process, concurrent requests, and tests each see their own
  spec; nothing needs resetting between tests.
- **One way to reach the spec**: `Service.spec` below the CLI, the per-invocation handle at the CLI,
  `bundled_spec()` where the bundled document is meant.
- **Wide, shallow churn** across the service mixins, `IndexStore` and the CLI helpers, carried by the
  characterization and golden-lock tests with behavior byte-identical.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T09:48:16Z] `architect` Robert Architect:
  - Draft assessment ADR for the workflow-spec de-globalization Pierre wants — executes ADR-214 §1 (per-Service/threaded spec), which it would supersede on acceptance. Grounded in the actual code, ~40 call sites across 13 modules inventoried per layer in the body. NOT a greenlight: drafting ≠ implementation, no tasks until Pierre's go/no-go.
  - Pivotal finding (a) — model coupling: NONE. _models/_item.py and _subentity.py have zero _workflow imports; their only validators do pure StrEnum→str coercion (no vocab lookup). FEAT-208 already moved all vocab validation to the load boundary (_index/_store.py:38 _validate_item_vocab, reads active_spec(), called from IndexStore.load():169). So the refactor never touches model construction and needs NO pydantic model_validate(context=) threading — this is what makes it tractable.
  - Pivotal finding (b) — CLI context mechanism: a per-invocation context handle (contextvar or ctx.obj) set in the root --dir callback, NOT pure parameter threading. The precedent already exists: the callback sets common.set_active_dir() the same way. parse_type/parse_status already read active_spec() lazily but fire during Click parse (before the callback body) — that ordering is the one detail to nail. The import-time app-build loop (_cli/__init__.py:97,121) is the only piece a per-invocation context can't reach — and that is FEAT-210's job, not this one.
  - FEAT-210 entanglement verdict: PREREQUISITE, done FIRST and separately — not folded in. 210 already must make the CLI app tree spec-driven (spec.managed_types()); this ADR gives it a clean per-invocation spec to build on, and keeps the mechanical de-global behavior-preserving + golden-locked + independently bisectable. Folding into 210 entangles a refactor with a user-facing feature.
  - Recommendation: Option A (full Service-owned + threaded spec; delete the singleton/_active_spec list/in-place dict mutation/_terminal_ref/use_spec/reset_spec/autouse fixture). Effort medium (~4 tasks: workflow core+IndexStore, service call-site sweep, CLI context handle, test rewrite), risk medium, behavior-preserving under the FEAT-208 characterization+golden safety net. Fallback Option C: contextvar-only de-global (low effort/risk) that keeps the free-function API and is also a clean first step of A. Open Qs for Pierre in the body: A vs C, sequencing confirm, and the autouse-fixture/7-test-file churn on the EPIC-206 net.
- [2026-06-30T09:51:35Z] `manager` Catherine Manager:
  - Pierre (op-pierre) selected Option A: full Service-owned threaded WorkflowSpec — delete the process-global singleton (use_spec/reset_spec, in-place dict mutation, _terminal_ref, autouse reset fixture). Sequenced as a standalone prerequisite feature BEFORE FEAT-210, accepting the rewrite of the 7 singleton-touching test files. Greenlit for implementation.
- [2026-06-30T09:54:38Z] `tech-lead` Olivia Lead:
  - Broke Option A down under FEAT-250 (grouping feature, parented to EPIC-206, addresses this ADR, blocks FEAT-210 — sq blocked now shows 210 waiting on it). Internal refactor, no user stories; acceptance = behaviour byte-identical (FEAT-208 characterization + golden-lock green) with the singleton deleted.
  - Four sequenced tasks (a→b→c→d, depends-on refs recorded): TASK-251 workflow core (free fns → spec methods + IndexStore takes the spec); TASK-252 service call-site sweep (Service.spec attr, ~40 sites incl. _maintenance/sq check + the _meta_compat migration); TASK-253 CLI per-invocation spec handle (root --dir callback binds it, parse_type/parse_status read it — Click parse-ordering nailed per Finding 2); TASK-254 test rewrite of the singleton-touching files + delete the _reset_workflow_spec autouse fixture.
  - Hard scope line carried in every task body: the import-time app-build loop (_cli/__init__.py for-loop) stays bundled-spec-driven and is FEAT-210's job — this feature owns 'spec is threaded/contextual', 210 owns 'app tree built from live spec'. Left all tasks Draft for Catherine to schedule.
- [2026-10-25T21:36:59Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten from an options assessment into the decision taken: Option A (op-pierre, 2026-06-30). It holds: Service.spec, `IndexStore(spec)`, `RequestContext.active_spec` with `get_active_spec()`, and no singleton. Removed the stale line-number inventory and the open questions.
<!-- sq:discussion:end -->
