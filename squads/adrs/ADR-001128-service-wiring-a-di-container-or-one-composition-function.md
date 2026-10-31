---
id: ADR-1128
sequence_id: 1128
type: decision
title: 'Service wiring: a DI container or one composition function'
status: Accepted
author: architect
refs:
- FEAT-1092
- REV-956
- TASK-1125
- ADR-1052
description: 'REV-956 F14: no DI container; one composition function builds Service
  and loads each spec document once per invocation'
created_at: '2026-10-24T21:58:58Z'
updated_at: '2026-10-25T21:41:31Z'
priority: medium
---
<!-- sq:body -->
## Context

REV-956 F14 asks whether squads should wire its service through a DI container, the obvious candidate being `soupape`. The question was decided together with the structural work in FEAT-1092, and TASK-1125 (one composition root, F15) builds the answer.

What the code looks like (read, not driven, 2026-10-24):

- **Ten production `Service(...)` constructions** build the same small graph: `Service`, `IndexStore`, `SquadPaths`, `WorkflowSpec`, `PlaybookSpec` and up to two backends. They are in `_services/_service.py` (`init`, `adopt`, three `open_service` branches), `_cli/_common.py` (three in the bypass ladder) and `_cli/_main.py` (two `sq check` fallbacks). Four of them pass no playbook.
- **Most of the variation between sites is fallback policy**: which spec and playbook to use when an override fails to load. A container resolves types; it does not choose between fallbacks.
- **Process state.** Construction relies on the `_active_squad_dir` `ContextVar` set in `ServiceCore.__init__` and re-asserted after each `anyio.run` crossing, and on the backend `_REGISTRY` dict filled as an import side effect.
- **Per-invocation scope** is two memo keys on the Click root context.
- **The spec documents** (workflow spec, role catalog, playbook) are loaded by whichever caller needs them: module-level singletons at import, the CLI help path, `open_service`, and per-call loaders such as the role resolver's `load_role_catalog(squad_dir)`. Nothing owns how often they load.
- **The daemon** (ADR-1052) is one long-lived process per squad and per squads version. It holds one squad's service and answers many requests, each with its own `RequestContext` and read scope. Writes already go through `IndexStore.transaction()` under the file lock.

The F14 measurements of `soupape` against this graph: construction takes 0.17 ms, so startup cost is import time; `soupape` brings four 0.x packages; a constructor hint importable only under `TYPE_CHECKING` raises a bare `NameError` from the container; and its resolution errors name the missing interface, not the service that needed it.

## Decision

**No DI container. `Service` is built by one composition function.**

- The composition function takes the squad paths and a mode (normal, index cross-check skipped, playbook unavailable, bundled fallback) and returns the service. Every construction site calls it, and the fallback order is one table in one module.
- It builds the `IndexStore` and the active backends and passes them in. `ServiceCore.__init__` constructs no collaborator.
- The renderer takes the squad directory as an argument; the `_active_squad_dir` `ContextVar` and its re-asserts go.
- The backend registry is a literal name-to-class table with no registration side effect.
- In the daemon, the request handler opens a request scope (bind `RequestContext`, open the read scope, close both) around the service built once at startup. That scope is one context manager beside the composition function.

**The composition root owns the spec documents.** The workflow spec, the role catalog and the playbook are each loaded **exactly once per invocation**, on every path that uses them, and not at all on a path that does not (a bare `sq --version` loads none). This holds for ordinary commands, `--help` and completion, `sq check` and every fallback mode, not only for `--help`. Concretely, per invocation and per document:

- the packaged TOML is parsed at most once;
- the project override, when present, is read at most once;
- each distinct model (the bundled one, and the merged one when an override exists) is built at most once, from those parses.

A document may be resolved lazily, on first use, as TASK-1125 does for the role catalog so that a malformed roles override fails where it fails today; lazy resolution is memoised at the composition root, so the first use is the only load. Code below the root receives the loaded document; it does not call a loader with a squad directory to get it again. In the daemon the documents are loaded with the service at startup and a request does not reload them; how an edited override reaches a running daemon is settled with the daemon handler (ADR-1052).

## Why

- The graph has six nodes and its real complexity is fallback policy, which a container does not reach.
- The daemon's per-request state is two objects, `RequestContext` and the read scope; one context manager covers it.
- A container would add four 0.x runtime dependencies and 60-260 ms of import on the CLI hot path that FEAT-916 is shrinking, a `NameError` path outside `SquadsError`, and error messages that point less precisely at the cause.
- Testability is equal either way: required parameters and passed-in collaborators make every class constructible by hand, as the 328 test constructions already do.
- One composition function is also the one place a load-once guarantee can be enforced; with loads spread across callers, nothing can.

## Consequences

- TASK-1125 proceeds as written, and its acceptance includes the load-once guarantee above, proved by a test that counts parses, override reads and model builds per document for each command path.
- REV-956 F14 closes as WontFix, citing this decision.
- No dependency is added.
- The daemon's request scope is designed with the daemon handler, next to the composition function.
- Moving to a container later is a contained change: every class takes its collaborators explicitly and one function constructs them.
- **Reopen trigger.** This decision is reopened when either holds:
  - the daemon's request handling needs three or more request-scoped collaborators with teardown;
  - the service is split so that wiring is written in more than one place.

## Option considered and rejected

**Adopt `soupape` at the composition root.** The same graph registered as singletons, per-request objects as scoped services with ordered teardown. Its gain is declared lifetime and teardown, which matters only once the daemon grows request-scoped collaborators with their own resources (the reopen trigger). Rejected for the dependency and import cost, the error paths above, and because it removes neither the fallback table nor the silent `X | None = None` fallback: an unregistered optional resolves to `None`.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T21:59:25Z] `architect` Robert Architect:
  - @op-pierre your ruling, please: option A (no container, one composition function, reopen on the stated triggers) or B (soupape at the composition root). I recommend A. TASK-1125 waits on it.
- [2026-10-25T10:45:51Z] `op-pierre` Pierre Chat:
  - Ruling: option A, one composition function, no DI container (no soupape).
- [2026-10-25T10:51:41Z] `architect` Robert Architect:
  - 2026-10-25: body rewritten to record the op-pierre ruling (option A, no container), with the soupape option kept as considered and rejected and the reopen trigger as a consequence. Added his acceptance rule from TASK-1123 as part of the decision: the composition root loads the workflow spec, the role catalog and the playbook exactly once per invocation on every path that uses them, defined per document as one parse of the packaged TOML, one read of the override, one build of each distinct model. Moved to Accepted. Measured today on release/0.17 HEAD the rule does not hold yet; counts are on TASK-1125.
- [2026-10-25T21:41:31Z] `architect` Robert Architect:
  - Audited 2026-10-25: holds. compose_service/build_service in _services/_service.py, the Mode table (it also has MIGRATE beside the four modes named here), the fallback tables and the literal backend registry; TASK-1125 is Done.
<!-- sq:discussion:end -->
