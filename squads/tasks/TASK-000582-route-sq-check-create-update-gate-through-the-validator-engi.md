---
id: TASK-582
sequence_id: 582
type: task
title: Route sq check + create/update gate through the validator engine
status: Done
parent: FEAT-568
author: tech-lead
refs:
- ADR-541
- TASK-581:depends-on
description: Wire common core + category bundles, retire the _check_* / hardcoded
  gate; engine is the sole source, byte-identical
created_at: '2026-07-22T10:33:01Z'
updated_at: '2026-07-22T11:46:31Z'
---
<!-- sq:body -->
## Scope

Make the `ValidatorEngine` the single source of `sq check` output and of the
create/update gate, and retire the now-duplicated `_check_*` methods — **without
changing output** (the two new `no_parent` enforcements are deliberately
withheld to a separate task; see Dependencies).

- Populate `COMMON_CORE` = `item_status_valid`, `dangling_ref`, `ref_kind_valid`,
  `no_status_banner`, `agent_registered`.
- Populate `CATEGORY_BUNDLES`:
  - `records` = common core + `supersedes_incoming` (gated on the type declaring
    a `supersedes` ref rule). **No `no_parent` here yet** — withheld to stay
    byte-identical until FEAT-572 lands.
  - `work` = common core + the parent-eligibility validator (`parent_in`, reading
    the structured `parents`; lenient empty-list preserved) + `subentity_status_valid`
    + `subentity_body_written` + `subentity_title_max` + `subtask_story_mapping`
    (each a no-op for a type with no `subentity_kind`/non-`subtask` kind).
    **No `no_parent` on epic yet** — withheld (see Dependencies).
  - `roster` = common core only.
- Engine builds the real `ValidatorContext`: precompute `registered_slugs`,
  `supersedes_incoming`, and `on_disk_bodies` once per `report()`; wire the
  on-disk-body validators to consume the `on_disk` map (drop the Phase-A
  `del on_disk`/`del index` no-ops).
- Retire the `_check_*` calls in `check()`, replacing them with the engine. The
  `_check_items` **drift** sub-check + marker/no-`id` + override checks stay (not
  catalog members) — decompose `_check_items` so only its status/parent/ref/agent
  branches move to the engine and the drift residue remains.
- Retire the create/update hardcoded gate (`_check_parent`/`_check_author`/
  `_check_assignee` in `_base.py`, called from create and `_items.py` update /
  reparent) so create/update and `sq check` share one engine with no duplicated
  rule logic. Preserve the exact abort messages/exit behaviour.

## Byte-identical requirement

With the bundled spec and no override, the engine-produced report must equal
today's `sq check` output — see the two @architect points on the feature:
(1) issue **ordering** (`sq check` prints in production order, unsorted) and
(2) the `parent_in` param-vs-structured-field question. Resolve per the
architect's answer before claiming byte-identical.

## Acceptance

- `uv run sq check` (and `--json`) on this repo is byte-identical to `main`
  (capture `main`'s output first; diff). The two new enforcements are NOT in
  this task.
- create/update/reparent gate messages + exit codes unchanged (targeted tests).
- Grep proves no `_check_*` method that maps to a catalog entry still runs (no
  double-run); the drift/marker/override residue still runs.
- Full suite green; pyright + ruff clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 582 add-subtask "<title>"`; track with `sq task 582 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T11:14:02Z] Elias Python:
  - Wired COMMON_CORE + records/work/roster CATEGORY_BUNDLES (no_parent withheld); engine is now sole source for sq check + create/update/link gate; retired _check_reconciliation/_check_items(status/parent/ref/agent)/_check_subtask_stories/_check_subentity_status/_check_decisions/_check_unwritten_subentity_bodies/_check_status_banners/_check_backends/_check_subentity_title_lengths (drift-only residue kept in _check_items).
  - gate() only aborts on error-level issues (warn never blocks, matching sq check's own exit-code semantics); kept _check_author/_check_assignee (participant, skill-excluded, self-author bootstrap) SEPARATE from the catalog's agent_registered (warn, roster-inclusive) — folding them together would silently start accepting a skill as author at create/update, a real regression, not a message-text nuance. _check_parent shrunk to existence-only (ItemNotFoundError preserved), type-eligibility now parent_in/no_parent via gate().
  - Added the deterministic sort at the sq check report boundary (_cli/_main.py::_check_issue_sort_key): no-item/squad-global leading block, then by sequence, error<warn, then message; applies to console+--json, not gate(). No existing golden needed re-sorting (tests/goldens/check_squad.json's order already matched); added dedicated sort-order tests.
  - Verified: sq check on this repo byte-identical (still clean); full suite green; pyright/ruff/format clean.
<!-- sq:discussion:end -->
