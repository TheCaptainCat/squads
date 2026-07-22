---
id: FEAT-572
sequence_id: 572
type: feature
title: Migrate 5 parented ADRs to related refs
status: Draft
parent: EPIC-538
author: product-owner
priority: medium
refs:
- ADR-541
- FEAT-568
created_at: '2026-07-22T08:39:39Z'
updated_at: '2026-07-22T08:41:14Z'
---
<!-- sq:body -->
## Capability

Migrate the 5 ADRs that currently hold a `parent` to a `related` ref instead,
re-homing them onto the work item they actually inform — closing the live gap
ADR-541 and EPIC-538 both cite (records take no parent, but 5 ADRs hold one today
while `sq check` reports clean).

## Scope

- ADR-516 → `related` ref to EPIC-28
- ADR-527 → `related` ref to EPIC-28
- ADR-155 → `related` ref to EPIC-121
- ADR-158 → `related` ref to EPIC-121
- ADR-129 → `related` ref to FEAT-17
- For each: drop the `parent` field, add the equivalent `related` ref, verify no
  other tooling (rendering, `sq tree`) depended on the parent edge for that ADR.

## Acceptance

- All 5 ADRs have no `parent` and carry the listed `related` ref.
- `sq check` clean before and after (this migration removes the only 5 violations
  that the `records` `no_parent` validator default would otherwise flag).
- No other ADR gains or loses a parent as a side effect.

## Dependencies / ordering — critical sequencing note

- **Must land with-or-before FEAT-568's `records` `no_parent` category default**
  (EPIC-540 Phase B). ADR-541 is explicit: landing that default without this
  migration first would make this repo's own `sq check` non-clean — 5 pre-existing
  parented ADRs would suddenly be flagged. Do not merge FEAT-568's `no_parent`
  enforcement ahead of this feature; coordinate merge order with whoever picks up
  FEAT-568.
- Otherwise **Phase C, parallelizable** against the other EPIC-538 Phase C
  features (only the FEAT-568 ordering constraint above applies).
- Depends on FEAT-567 only in the sense of riding the same release; no functional
  dependency on the category axis itself (a straightforward ref migration).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 572 add-story "As a <role>, I want … so that …"`; track with `sq feature 572 story <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
