---
id: EPIC-280
sequence_id: 280
type: epic
title: Custom sub-entity kinds & vocabulary rename migrations
status: Done
author: product-owner
refs:
- EPIC-206
created_at: '2026-07-02T09:24:53Z'
updated_at: '2026-07-10T01:56:48Z'
---
<!-- sq:body -->
## Vision

EPIC-206 makes the workflow engine (types, statuses, machines) config-driven while keeping the default spec byte-identical to today. That epic closes at F1-F5 + the config axis (roles/playbook) as a coherent, shippable unit. Two further capabilities were originally bundled into EPIC-206 as a stretch feature (F6) but are each a second deep-coupling surface comparable in blast radius to F1+F2 combined — per ADR-274, they are split out into this epic so EPIC-206 can close cleanly and these two get independent sequencing, spikes, and review proportional to their own risk.

## Who needs this

Projects that have adopted config-driven vocabulary (EPIC-206) and now want to go further:
- **Ops/SRE and compliance teams** that need a custom type's nested work items (e.g. an `action` kind on `incident`, or a `control` kind on a compliance type) to have their own machine and summary columns, not just reuse story/subtask/finding.
- **Any project admin evolving their vocabulary over time** — renaming a built-in type or status project-wide today requires manual file surgery; this epic makes that a safe, audited migration.

## The two features

1. **Custom sub-entity kinds** — let a custom type declare a brand-new sub-entity kind (its own machine, summary columns, and `add-<kind>` CLI verb) instead of only reusing story/subtask/finding. Touches the CLI app-build, `_discussion.py` column rendering, the service `add_*` methods, and the spec schema. Owns retiring `_SUBENTITY_PLURAL` (the last static per-type vocabulary artifact) via a `subentity_plural` accessor on the ADR-266 reserved-vocab resolver.
2. **Vocabulary rename migrations** — `sq migrate rename-type` / `rename-status`, built on the existing `retype` primitive (atomic ID/ref/parent/prose rewrite), exposed as an audited `sq migrate` runbook with a schema bump. Independent of (1); can ship first or in parallel.

## Dependencies

Both features require F4 (FEAT-210, Done) for custom types. The custom sub-entity-kinds feature additionally needs F5 (FEAT-211, InProgress) for the custom-status plumbing its declared machines rely on; the rename-migrations feature depends on F5 for renaming statuses specifically. Neither starts before F5 lands.

## Non-goals

- Rich per-role playbook sections for custom sub-entity kinds (stretch beyond this epic).
- Renaming squads' own meta-types (`skill`, `role`, `operator`) — special semantics, out of scope.

## Provenance

Split from EPIC-206's F6 (former FEAT-212) per ADR-274 (Accepted).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-02T09:26:23Z] Nina Product:
  - Created per ADR-274 (Accepted), executing the F6 scope split out of EPIC-206.
  - Re-parented FEAT-212 here, retitled to 'Custom sub-entity kinds for custom types', trimmed to US1's scope; it keeps ownership of retiring _SUBENTITY_PLURAL via the subentity_plural resolver accessor (Catherine's ownership note, preserved).
  - Created FEAT-281 'Vocabulary rename migrations (sq migrate rename-type/status)' here for the second half (former US2); both features depends-on FEAT-210 (Done) and FEAT-211 (InProgress) and stay Draft/Ready — neither starts until F5 lands.
  - Note: ADR-274 suggested EPIC-000213 as the number, but the global counter had moved past it by execution time (213 is BUG-213); the epic was created as EPIC-280. Numbers in the ADR text are illustrative, not reserved.
- [2026-07-10T01:56:46Z] Catherine Manager:
  - EPIC-280 complete: both children Done — FEAT-212 (custom sub-entity kinds, ADR-348 realized end-to-end) and FEAT-281 (vocabulary rename migrations: sq migrate rename-type/rename-status). BUG-362 (surfaced by 281's acceptance sweep) fixed and Verified along the way.
<!-- sq:discussion:end -->
