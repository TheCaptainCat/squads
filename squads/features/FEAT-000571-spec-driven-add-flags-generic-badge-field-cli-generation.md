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
updated_at: '2026-07-22T18:23:01Z'
---
<!-- sq:body -->
## Capability

Make the `add-*` sub-entity command builder (`add-finding`/`add-story`/`add-subtask`)
generate its `--flags` **dynamically from the active spec's badge/field
collections**, instead of hardcoding `--severity`/`--status` for whichever
sub-entity kinds happen to have needed them so far. Folds in REV-565 F14.

## Why (folds REV-565 F14)

F14 (Open, low): `add-finding`/`add-story`/`add-subtask` accept a title + body +
`--assignee`/`--story`, but not a full set of metadata flags inline — setting a
non-default status (or other badge field) needs a follow-up `update --force`.
Since the 0.11.1 field report, `add-finding` gained `--severity` inline, but that
was added as a **hardcoded, single-kind fix** — it doesn't generalize to a custom
spec that defines different/renamed badge collections (severity/status/priority
are spec vocabulary per ADR-323's badge-collections model, not fixed CLI
constants). This feature is the generic fix: derive the flag set from the spec.

## Scope

- The `add-*` command builder introspects the active spec's collections for the
  sub-entity kind being scaffolded (mirroring how the badge-collections model
  already lets a spec relabel/rename severity/status/priority) and generates one
  `--<field>` flag per collection that applies to that kind — generic, not a
  hardcoded `--severity`/`--status` pair.
- `--status` becomes available inline (closing the remaining explicit gap F14
  calls out), alongside whatever other badge fields the spec declares for that
  sub-entity kind.
- A provided value is validated against the same badge vocabulary `update` already
  enforces — no new validation path, just an earlier entry point.
- Verify parity across all three sub-entity kinds (`add-finding`/`add-story`/
  `add-subtask`) — F14's reviewer note flagged severity as already inline for
  findings only; this feature makes the mechanism generic across all three
  and across custom specs.

## Acceptance

- On the bundled spec, `add-finding`/`add-story`/`add-subtask` each expose
  `--status` inline (plus existing badge flags), with no behaviour change to the
  already-inline `--severity` on `add-finding`.
- On a spec that renames/relabels a badge collection (or adds a new one),
  `add-*`'s generated flags follow the spec — no hardcoded field name anywhere
  in the command builder for a sub-entity's badge fields.
- `sq check` clean; existing invocations without the new flags behave exactly as
  before (additive, no breaking change to existing scripts).

## Dependencies / ordering

- **Depends on FEAT-567 (Phase A)** loosely — this feature reads the spec's badge
  *field* collections (ADR-323 model), not the `category` axis directly, but is
  scoped into this Phase C batch per the tech-lead's cut; no hard blocking
  dependency on FEAT-567's engine, only on the shared spec object it also touches.
- **Phase C, parallelizable** against the other EPIC-538 Phase C features.
- Note: this does **not** address REV-565 F10 (unwritten-body stub warning) — that
  finding is triaged separately (Pierre: "add-finding/story/subtask take a body
  via stdin/file/inline; placeholder only when absent") and is not in this cut.
- Cross-ref: REV-565 F14 (folded in here).
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
