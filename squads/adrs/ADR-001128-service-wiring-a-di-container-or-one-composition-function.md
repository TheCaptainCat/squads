---
id: ADR-1128
sequence_id: 1128
type: decision
title: 'Service wiring: a DI container or one composition function'
status: Proposed
author: architect
priority: medium
refs:
- FEAT-1092
- REV-956
- TASK-1125
- ADR-1052
description: 'REV-956 F14: options A (no container, one composition function) and
  B (soupape); recommends A, reopen on request-scoped growth in the daemon'
created_at: '2026-10-24T21:58:58Z'
updated_at: '2026-10-24T21:59:25Z'
---
<!-- sq:body -->
## Context

REV-956 F14 asks whether squads should wire its service through a DI container. The obvious candidate is `soupape`. The operator ruled on 2026-10-09 that the question is decided in 0.17, together with the structural work in FEAT-1092. TASK-1125 (one composition root, F15) waits on the answer.

What the code looks like on 2026-10-24 (read, not driven):

- **Ten production `Service(...)` constructions** build the same small graph: `Service`, `IndexStore`, `SquadPaths`, `WorkflowSpec`, `PlaybookSpec` and up to two backends. They are in `_services/_service.py` (`init`, `adopt`, three `open_service` branches), `_cli/_common.py` (three in the bypass ladder) and `_cli/_main.py` (two `sq check` fallbacks). Four of them pass no playbook.
- **Most of the variation between sites is fallback policy**: which spec and playbook to use when an override fails to load. A container resolves types. It does not choose between fallbacks.
- **Process state.** Construction relies on process-wide state: the `_active_squad_dir` `ContextVar` set in `ServiceCore.__init__` and re-asserted after each `anyio.run` crossing, and the backend `_REGISTRY` dict filled as an import side effect.
- **Per-invocation scope** is two memo keys on the Click root context.
- **The daemon** (ADR-1052) is one long-lived process per squad and per squads version. It holds one squad's service and answers many requests. Each request needs its own `RequestContext` and read scope. Writes already go through `IndexStore.transaction()` under the file lock.

The reviewer's F14 measurements still describe this graph:

- Construction takes 0.17 ms. Startup cost is import time.
- `soupape` brings four 0.x packages.
- A constructor hint that is importable only under `TYPE_CHECKING` raises a bare `NameError` from the container.
- The container's resolution errors name the missing interface, not the service that needed it.

## Options

**A. No container. One composition function (TASK-1125).**
- The composition function takes the paths and a mode, and the fallback order becomes one table.
- The store and backends are built in that function and passed in.
- The renderer takes the squad directory as an argument.
- The registry becomes a literal table.
- For the daemon, the request handler opens a request scope (bind `RequestContext`, open the read scope, close both) around a service built once at startup. That is one context manager.
- Cost: hand-written wiring, which is about 10 sites today and becomes 1.

**B. Adopt `soupape` at the composition root.**
- The same graph is registered as singletons. Per-request objects are scoped services, created per daemon request, with ordered teardown.
- What it would give: lifetime and teardown are declared, not written by hand, which matters if the daemon grows request-scoped collaborators with their own resources.
- What it costs:
  - four 0.x runtime dependencies against seven established ones;
  - an extra 60-260 ms import on the CLI hot path, which FEAT-916 is trying to shrink;
  - a `NameError` path outside `SquadsError`;
  - error messages that point less precisely at the cause than today's.
- It does not remove the fallback table, and it does not fix `X | None = None` defaults. An unregistered optional resolves to `None`, which is the same silent fallback.

**Comparison on the four criteria.**

| Criterion | A, no container | B, soupape |
|---|---|---|
| Scoping | Holds while the per-request set is `RequestContext` plus the read scope. | Helps only when the per-request set grows. |
| Lifetime | Equal: the daemon has one singleton service either way. | Equal. |
| Testability | Equal: required parameters and passed-in collaborators make the classes constructible by hand, and 328 test constructions already do that. | Equal. |
| Dependency cost | None added. | Four 0.x packages on the startup path. |

## Recommendation

**Option A.** The graph has six nodes, its real complexity is fallback policy, and the daemon's per-request state is two objects. A container would add dependencies and import time, and would not reach the parts that are hard.

Once TASK-1124 and TASK-1125 land, moving to B is a contained change, because every class takes its collaborators explicitly and only one function constructs them. Reopen this decision when either of these is true:

- the daemon's request handling needs three or more request-scoped collaborators with teardown;
- the service is split so that wiring is written in more than one place.

## Consequences

**If A:**
- TASK-1125 proceeds as written.
- F14 closes as WontFix, citing this ADR.
- The daemon's request scope is a context manager next to the composition function, designed with the daemon handler.
- No new dependency is added.

**If B:**
- TASK-1125 is re-planned around container registration.
- `soupape` and its three dependencies are added to `pyproject.toml`.
- The import cost is measured against the FEAT-916 budget.
- Constructor hints used by the container are moved out of `TYPE_CHECKING`.
- Container errors are wrapped in `SquadsError` at the edge.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T21:59:25Z] `architect` Robert Architect:
  - @op-pierre your ruling, please: option A (no container, one composition function, reopen on the stated triggers) or B (soupape at the composition root). I recommend A. TASK-1125 waits on it.
<!-- sq:discussion:end -->
