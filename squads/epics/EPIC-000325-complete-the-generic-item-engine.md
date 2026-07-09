---
id: EPIC-325
sequence_id: 325
type: epic
title: Complete the generic item engine
status: Ready
author: product-owner
refs:
- EPIC-206
- ADR-322
- ADR-323
- EPIC-280
- FEAT-231
description: 'Finish the spec-is-sole-vocabulary arc: generic types/statuses/sub-entity
  kinds/badges, reserved surface = meta-types + agent-lifecycle only'
created_at: '2026-07-07T14:37:01Z'
updated_at: '2026-07-07T14:37:33Z'
---
<!-- sq:body -->
## Vision

EPIC-206 made the workflow engine config-driven — types, statuses, and machines
live in a loaded spec — while keeping the bundled default byte-identical to
today. But two vocabulary backbones survived that move as hardcoded Python:
the `ItemType`/`Status` enums (and their duplicate reserved-prefix/folder maps)
still gate what a spec can declare, and the `Priority`/`Severity` enums still
hardcode the two flat presentation axes. ADR-322 and ADR-323 (both Accepted)
settle how to finish the job. This epic is the umbrella for actually doing it:
making the loaded spec the **sole vocabulary authority** on every axis —
types, statuses, sub-entity kinds, and badge axes (priority/severity/custom) —
so that the **only** reserved surface left in the engine is the three
meta-types (`role`/`skill`/`operator`) plus their agent-lifecycle statuses
(`Draft`/`Active`/`Archived`).

## Who needs this

Any team that wants to fully own its vocabulary without forking squads:
dropping a built-in type, renaming a status, or defining a badge axis that
isn't "priority" or "severity" should be a spec edit, never a code change.
Today it still isn't, because the two enum pairs this epic removes are the
last hardcoded floors underneath the config-driven engine EPIC-206 promised.

## What this ties together

Two implementation features carry the actual engine work, each implementing
one of the governing decisions:

- **the ADR-322 feature** — delete `ItemType`/`Status` and their duplicate
  reserved-vocab maps; the spec's `items`/`statuses` tables become the sole
  vocabulary; the reserved floor narrows to the three meta-types + their
  agent-lifecycle statuses; sub-entity/finding statuses bind by machine role
  (start state on create, a `completion` flag for the done-toggle) instead of
  a hardcoded `Status.DONE`/`Status.TODO` literal.
- **the ADR-323 feature** — introduce the Collection/Field/Badge model;
  priority and severity ship as bundled default collections/fields instead of
  the `Priority`/`Severity` enums; the CLI's `--<field>`/`--min-<field>`/sort/
  column support derives generically from whatever fields a type declares.

The ADR-323 feature depends on the ADR-322 feature landing first — badge
fields are declared per `spec.items[...]`/`spec.subentity_kinds[...]`, so they
need the generic, string-keyed item/type model the 322 feature produces
rather than the old enum-gated one.

Downstream of both, already tracked and left where they are:

- **EPIC-280** (custom sub-entity kinds + vocabulary rename migrations) —
  stays parented under EPIC-206 for provenance; referenced here, not
  re-parented. Its FEAT-212 (custom sub-entity kinds) needs re-baselining
  against ADR-323's Field schema before dispatch (see FEAT-212 for the note).
- **FEAT-231** (ground-up test battery) — the parallel test track. Runs
  alongside the old suite until it reaches coverage parity; the enum/badge
  golden-test fallout from the two engine features is owned inside those
  features, not deferred to FEAT-231.

## Sequence (informational — tasks are the tech lead's call)

1. ADR-322 impl feature — generic type/status engine.
2. ADR-323 impl feature — badge collections (depends on 1).
3. FEAT-212 — custom sub-entity kinds (re-baselined against 1+2 first).
4. FEAT-281 — vocabulary rename migrations (needs 1's generic engine).
5. FEAT-231 — test battery rebuild, running behind the old suite until parity.

## Non-goals

- Re-parenting EPIC-280 or its features under this epic — they keep their own
  EPIC-206 provenance; this epic only references them for sequencing.
- Anything in FEAT-231's scope beyond noting it rides alongside — the test
  rebuild is QA's initiative, not owned here.

## Provenance

Completes the "spec is the sole vocabulary" arc opened under EPIC-206 and
carried forward by ADR-232 (de-typing) and ADR-274 (the EPIC-280 split);
ADR-322 and ADR-323 are the governing decisions for the two features this
epic ties together.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
