---
id: TASK-581
sequence_id: 581
type: task
title: Lift seed validators into the closed catalog (per-item + squad-global)
status: Done
parent: FEAT-568
author: tech-lead
refs:
- FEAT-567
- ADR-541
description: Name today's _check_* logic as closed-catalog validators (verbatim);
  catalog defined + unit-tested, engine still no-op
created_at: '2026-07-22T10:32:51Z'
updated_at: '2026-07-22T11:46:31Z'
---
<!-- sq:body -->
## Scope

Populate the closed per-item `CATALOG` and `SQUAD_GLOBAL_CATALOG` in
`_services/_validators.py` by lifting each of today's hardcoded `_check_*`
methods (`_services/_maintenance.py`) into a named validator, **logic verbatim**.
This task only *defines and unit-tests* the catalog entries — it does not yet
retire the `_check_*` calls or populate any bundle, so the engine stays a no-op
and `sq check` output is unchanged.

Named per-item validators → their source branch:

- `parent_in` / `no_parent` ← `_check_items` parent branch (dangling parent +
  `parent_allowed`/`parent_hint`). `parent_in` reads the **structured** `parents`
  field (reproducing today's lenient empty-list = "any parent or none");
  `no_parent` forbids any parent. See the @architect note on the feature re the
  `parent_in:<types>` notation — implement it reading the structured field, no
  duplicated param, pending that confirmation.
- `item_status_valid` ← `_check_items` "status invalid for type" branch.
- `dangling_ref` / `ref_kind_valid` ← `_check_items` ref loop.
- `agent_registered` ← `_check_items` author/assignee branch.
- `subtask_story_mapping` ← `_check_subtask_stories`.
- `subentity_status_valid` ← `_check_subentity_status`.
- `subentity_body_written` ← `_check_unwritten_subentity_bodies`.
- `subentity_title_max` ← `_check_subentity_title_lengths`.
- `no_status_banner` ← `_check_status_banners`.
- `supersedes_incoming` ← `_check_decisions`.

Squad-global validators → source:

- `index_reconciled` ← `_check_reconciliation`.
- `backend_reconciled` ← `_check_backends`.

Populate `ValidatorContext` with the real precomputed inputs the lifted
per-item validators need — `registered_slugs`, `supersedes_incoming`,
`on_disk_bodies` — so a validator reads the context instead of re-scanning the
index/disk. (The engine's population of these lands in the routing task; here
they are consumed only from directly-constructed contexts in unit tests.)

**Not in the seed catalog, left untouched:** `_scan_for_check` marker/no-`id`
errors, the `_check_items` status/parent **drift** sub-check (`_drift_issues`),
and the override-config checks. These are not named validators in ADR-541 and
stay where they are.

## Acceptance

- Every ADR-541 seed name resolves to a catalog entry; the two squad-global
  names resolve in `SQUAD_GLOBAL_CATALOG`.
- Per-validator unit tests: each validator reproduces its `_check_*`
  counterpart's issues **exactly** (same level, item id, message) on crafted
  fixtures, including the negative/empty cases.
- `CATEGORY_BUNDLES`/`COMMON_CORE` stay empty → engine contributes nothing →
  `uv run sq check` on this repo is unchanged (no double-run).
- Full suite green; `uv run pyright && uv run ruff check . && uv run ruff format
  --check .` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 581 add-subtask "<title>"`; track with `sq task 581 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T10:58:49Z] Operator:
  - Lifted all 12 seed + 2 squad-global validators verbatim into CATALOG/SQUAD_GLOBAL_CATALOG; VALIDATOR_NAMES/SQUAD_GLOBAL_VALIDATOR_NAMES + module-load guard added in _workflow/_models.py. Bundles/COMMON_CORE stay empty and squad_global's engine default is decoupled from SQUAD_GLOBAL_CATALOG, so sq check is unchanged (verified: identical output, full suite green, pyright/ruff clean). 38 new parity unit/service tests.
- [2026-07-22T10:58:59Z] Elias Python:
  - Lifted all 12 seed + 2 squad-global validators verbatim into CATALOG/SQUAD_GLOBAL_CATALOG; VALIDATOR_NAMES/SQUAD_GLOBAL_VALIDATOR_NAMES + module-load guard added in _workflow/_models.py. Bundles/COMMON_CORE stay empty and squad_global's engine default is decoupled from SQUAD_GLOBAL_CATALOG, so sq check is unchanged (verified: identical output, full suite green, pyright/ruff clean). 38 new parity unit/service tests.
<!-- sq:discussion:end -->
