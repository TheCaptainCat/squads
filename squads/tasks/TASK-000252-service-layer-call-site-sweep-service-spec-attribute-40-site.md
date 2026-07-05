---
id: TASK-252
sequence_id: 252
type: task
title: 'Service-layer call-site sweep: Service.spec attribute, ~40 sites read self.spec'
status: Done
parent: FEAT-250
author: tech-lead
refs:
- TASK-251:depends-on
created_at: '2026-06-30T09:53:04Z'
updated_at: '2026-06-30T10:14:17Z'
---
<!-- sq:body -->
**Part (b) of FEAT-250 / ADR-249 Option A. Sequence: after TASK-251 (needs the
spec methods + IndexStore signature), before the CLI task.**

Give `Service` an owned `spec: WorkflowSpec` attribute and sweep the ~40 service-layer
call sites to read `self.spec.<method>` instead of the module-level free functions.

## Scope

- **`src/squads/_services/_service.py`** — `open_service` resolves + merges + validates the
  spec **once** and stores it on the `Service` (no global rebind; the `use_spec`/`bundled_spec`
  orchestration at `:185-210` goes away). `Service` constructs/holds its `IndexStore` with that
  spec (per TASK-251's signature). The spec is owned by `Service`.
- **Call-site sweep** (per ADR-249's grounded inventory — verify against current code):
  - `_services/_base.py` (`ServiceCore`: `initial_status`, `is_open`, `item_is_meta`,
    `parent_allowed`, `parent_hint`)
  - `_services/_items.py` (`can_transition`, `item_is_meta`, `workflow_for`)
  - `_services/_maintenance.py` — **heaviest, this is `sq check`**: `item_is_meta`,
    `item_parent_required`, `item_ref_rules`, `item_subentity_kind`, `parent_allowed`,
    `parent_hint`, `status_role`, `subentity_workflow`, `workflow_for`, plus the direct
    `_wf.active_spec()` reach-in (`:349`).
  - `_services/_subentities.py`, `_refs.py`, `_roster.py`, `_collab.py`, `_retype.py`
    (`is_open`, capability flags, `work_types`, `initial_status`, etc.)
- **`src/squads/_migrations/_meta_compat.py`** (`subentity_initial` at `:17,96`) — migrations
  don't have a `Service`; thread a spec explicitly (pass the bundled/loaded spec into the
  migration helper) rather than reaching a global.

## Constraints / gotchas

- **Behaviour byte-identical** — pure refactor under FEAT-208 characterization + golden-lock.
- The mixins compose into the flat `Service` façade (`_base.ServiceCore` + per-concern mixins);
  `self.spec` must be reachable from every mixin — put it on `ServiceCore`.
- Wide but shallow; mechanical. `_maintenance.py` is dense — sweep it carefully and lean on
  `sq check` characterization tests.
- Out of scope: CLI parse/print helpers and the import-time app-build loop (task c / FEAT-210);
  test rewrite (task d).

## Acceptance

- `Service` owns its `spec`; no service module imports the deleted free functions.
- `pyright` strict + `ruff` clean; full suite green (characterization + golden-lock + `sq check`).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 252 add-subtask "<title>"`; track with `sq task 252 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
