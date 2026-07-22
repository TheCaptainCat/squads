---
id: FEAT-571
sequence_id: 571
type: feature
title: 'Spec-driven add-* flags: generic badge/field CLI generation'
status: Done
parent: EPIC-538
author: product-owner
priority: low
refs:
- FEAT-567
- REV-565
created_at: '2026-07-22T08:39:38Z'
updated_at: '2026-07-22T18:40:12Z'
---
<!-- sq:body -->
## Capability

Make the `add-*` sub-entity command builder (`add-finding`/`add-story`/`add-subtask`)
generate its `--flags` **dynamically from the active spec's badge/field
collections**, instead of hardcoding `--severity`/`--status` per sub-entity kind.

## Why

`add-finding`/`add-story`/`add-subtask` accept a title + body + `--assignee`/`--story`,
but not a full set of metadata flags inline — setting a non-default status (or other
badge field) needs a follow-up `update --force`. Where a flag like `add-finding
--severity` was available inline, it was wired per-kind and did not generalize to a
custom spec that defines different/renamed badge collections (severity/status/priority
are spec vocabulary per ADR-323's badge-collections model, not fixed CLI constants).
This feature derives the flag set from the spec instead.

## Scope

- The `add-*` command builder introspects the active spec's collections for the
  sub-entity kind being scaffolded (mirroring how the badge-collections model
  already lets a spec relabel/rename severity/status/priority) and generates one
  `--<field>` flag per collection that applies to that kind — generic, not a
  hardcoded `--severity`/`--status` pair.
- `--status` becomes available inline, alongside whatever other badge fields the
  spec declares for that sub-entity kind.
- A provided value is validated against the same badge vocabulary `update` already
  enforces — no new validation path, just an earlier entry point.
- Parity across all three sub-entity kinds (`add-finding`/`add-story`/`add-subtask`):
  the mechanism is generic across all three and across custom specs.

## Acceptance

- On the bundled spec, `add-finding`/`add-story`/`add-subtask` each expose
  `--status` inline (plus existing badge flags), with no behaviour change to the
  already-inline `--severity` on `add-finding`.
- On a spec that renames/relabels a badge collection (or adds a new one),
  `add-*`'s generated flags follow the spec — no hardcoded field name anywhere
  in the command builder for a sub-entity's badge fields.
- `sq check` clean; existing invocations without the new flags behave exactly as
  before (additive, no breaking change to existing scripts).

## Dependencies

- Reads the spec's badge *field* collections (ADR-323 model), sharing the same
  spec object FEAT-567 touches; no hard dependency on FEAT-567's engine.
- Out of scope: the unwritten-body stub warning — a sub-entity takes a body via
  stdin/file/inline, and a placeholder is used only when absent.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 571 add-story "As a <role>, I want … so that …"`; track with `sq feature 571 story <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T18:23:01Z] Catherine Manager:
  - FEAT-571 Done: --status inline across add-finding/add-story/add-subtask, scope-validated against each kind's own lifecycle (the generic per-field --flag derivation already existed). Reviewed REV-618 (Approved, cross-lifecycle rejection verified); full suite green. Accepted under the standing non-visual delegation.
<!-- sq:discussion:end -->
