---
id: TASK-1125
sequence_id: 1125
type: task
title: Build Service at one composition root, without module state
status: Draft
parent: FEAT-1092
author: tech-lead
priority: medium
refs:
- REV-956:addresses
- TASK-1124:depends-on
- ADR-1128:depends-on
description: 'REV-956 F15: one composition function, collaborators passed in, renderer
  squad dir explicit, literal backend table.'
subentities:
- local_id: ST1
  title: Route every Service construction through one function
  status: Todo
  story: US2
- local_id: ST2
  title: Pass store and backends in; make the registry a table
  status: Todo
  story: US2
- local_id: ST3
  title: Pass the squad directory to the renderer explicitly
  status: Todo
  story: US2
created_at: '2026-10-24T21:53:44Z'
updated_at: '2026-10-24T21:59:28Z'
---
<!-- sq:body -->
## Goal

Build `Service` in one place and drop the process-wide state construction leans on, with no change to what `sq` does. Finding F15, and the alternative REV-956 F14 owes if the DI container verdict is no.

## Re-measured on 2026-10-24 (working tree, read)

- Ten production `Service(...)` constructions: `init` and `adopt` (`src/squads/_services/_service.py:171`, `:260`), three `open_service` branches (`:341`, `:354`, `:371`), three in the CLI bypass ladder (`src/squads/_cli/_common.py:1623`, `:1632`, `:1637`) and two `sq check` fallbacks (`src/squads/_cli/_main.py:1544`, `:1551`). Four of them pass no playbook (`_common.py:1623`, `:1632`, `_main.py:1544`, `:1551`). After the structural task they pass the bundled playbook explicitly.
- Four CLI accessors: `get_service` (`_cli/_common.py:1497`), `_build_plain_service` (`:1538`), `get_service_bypassing_index_cross_check` (`:1563`) and `_build_bypass_fallback_service` (`:1614`).
- `ServiceCore.__init__` calls `set_active_squad_dir` (`src/squads/_services/_base.py:548`), and `get_service` re-asserts it on memo hits (`_cli/_common.py:1530`, `:1600`) because each `anyio.run` crossing copies the `ContextVar`. `render` (`src/squads/_rendering/_engine.py:287`) has 15 call sites outside the engine.
- The backend registry (`src/squads/_backends/_registry.py`) is a module-global `_REGISTRY` dict filled by importing two packages for their side effect, behind `global _loaded`.

## Approach

1. **One composition function** takes the squad paths and a mode (normal, skip the index cross-check, playbook unavailable, bundled fallback) and returns the service. All ten sites call it. The fallback order becomes one readable table in one module, replacing the try/except ladders in `_cli/_common.py` and `_cli/_main.py`. Each mode keeps exactly the spec and playbook today's site chooses. If a site's choice looks accidental, report it to the operator; do not change it here.
2. **Collaborators passed in.** The `IndexStore` and the backend list are constructed by the composition function and passed to `ServiceCore.__init__`, not built inside it.
3. **Renderer takes the squad directory.** `render` and `scaffold_body` take the squad directory from the caller that already holds `paths`. `set_active_squad_dir`, its `ContextVar`, both re-asserts and their docstring go. The Jinja environment cache is keyed on the same value, so the architect settles its keying before this step starts.
4. **Backend registry as a literal table.** A name-to-class mapping with no registration side effect. The active backends are instantiated once in the composition function. The two backend package inits lose their registration side effect, and CLAUDE.md's non-empty-init list and the mutable-state allowlist entry for `_REGISTRY` follow.

## Tests

The existing suite is the net, with no assertion edited.

- **One table, "service composition by mode"**, with only these rows: normal; index cross-check skipped; playbook override that fails to load; workflow override that fails to load (bundled fallback). Each row checks which spec and playbook the service holds and that it opens the squad given. The rows cover the four ad-hoc ladders this replaces. Add a row for a squad with a playbook override running `sq repair` after a cross-check refusal, which REV-956 inferred but never drove, so the behaviour is pinned rather than assumed.
- **Rendering under two squads in one process:** one test where two squads with different template overrides render in turn and each gets its own. This is the case the ambient squad directory exists for, and it must stay right without it.
- `tests/meta`: drop the `_REGISTRY` allowlist entry so the mutable-state guard enforces the removal.

Falsify each new row once by breaking the mode table or the render argument, and record the red in the handoff.

## Generated output

None. Generated files are byte-identical before and after on a pinned roster in a scratch squad. The template manifest is unchanged.

## CHANGELOG substance

No adopter-visible change; report that to the writer. CLAUDE.md's architecture section changes: the composition function, the inits, and the removal of the ambient render state.

## Order

After the structural task (it needs required parameters and the roster collaborator) and the decision on a DI container. Before the check-rule task, because both edit the `sq check` fallbacks in `_cli/_main.py`, and before the test-rebuild inventory (TASK-1111): the CLI gate and `-C` differential tables the rebuild ports run through exactly this construction path.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1125 add-subtask "<title>"`; track with `sq task 1125 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Route every Service construction through one function

<!-- sq:subtask:ST1:body -->
Write one composition function taking the squad paths and a mode (normal, index cross-check skipped, playbook unavailable, bundled fallback), with the fallback order as one table. Route all ten production `Service(...)` constructions and the four CLI accessors through it. Each mode keeps today's spec and playbook choice; report any choice that looks accidental instead of changing it. Add the composition-by-mode table.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Pass store and backends in; make the registry a table

<!-- sq:subtask:ST2:body -->
Construct the `IndexStore` and the backends in the composition function and pass them to `ServiceCore.__init__`. Turn `_backends/_registry.py` into a literal name-to-class table with no import side effect or `global` flag, and drop its mutable-state allowlist entry.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Pass the squad directory to the renderer explicitly

<!-- sq:subtask:ST3:body -->
Pass the squad directory to `render` and `scaffold_body` from callers that hold `paths`, after the architect has settled the Jinja environment cache keying. Remove `set_active_squad_dir`, its `ContextVar` and the two re-asserts in `_cli/_common.py`. Add the two-squads-in-one-process render test.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T21:56:15Z] `tech-lead` Olivia Lead:
  - @op-pierre this task waits on the DI container decision (REV-956 F14), which you ruled is made in 0.17 with this work. Recommendation: no container. Build the one composition function this task describes. The reviewer's measurements still hold: a six-node graph, 0.17 ms to construct, four 0.x packages to add, and a bare `NameError` on hints that are importable only under `TYPE_CHECKING`. The required parameters and the passed-in collaborators from TASK-1124 and this task make the classes injectable, so if the daemon's per-request scope turns out to need a scoped injector, it replaces one function when FEAT-33 is designed. Adopting soupape now would buy nothing that one function does not.
    @architect two inputs: record the DI decision as an ADR once op-pierre rules, and settle the Jinja environment cache keying before ST3 (renderer squad directory).
- [2026-10-24T21:59:27Z] `architect` Robert Architect:
  - @tech-lead the DI decision this task waits on is ADR-1128 (Proposed, recommends A, which is this task as written); ruling pending from op-pierre. Jinja cache keying is not covered there.
<!-- sq:discussion:end -->
