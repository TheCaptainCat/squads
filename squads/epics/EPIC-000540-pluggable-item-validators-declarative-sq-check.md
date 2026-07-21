---
id: EPIC-540
sequence_id: 540
type: epic
title: Pluggable item validators (declarative sq check)
status: Draft
author: product-owner
priority: medium
refs:
- EPIC-538
description: Turn sq check + create/update gating into a declarative, pluggable validator
  catalog; parent_required becomes one validator; category defaults are validator
  bundles.
created_at: '2026-07-21T15:56:09Z'
updated_at: '2026-07-21T15:56:27Z'
---
<!-- sq:body -->
## Outcome

Turn `sq check` and create/update gating from a fixed pile of hardcoded checks into a
**declarative, pluggable validator framework**: each item type declares which validators
apply (with params), one engine runs them, and the same catalog powers both `sq check`
(report mode) and create/update-time gating (fail-closed). `parent_required` becomes one
validator among many.

## Why

Today the rules live in ~10 hardcoded `_check_*` methods in `_maintenance.py` plus scattered
create/update checks, and parent rules are only half-declarative (`parents` / `parent_required`
fields read by hardcoded logic). That's rigid: a type can't opt in or out of a rule, adopters
can't compose the rule set for a custom type, and adding a rule means editing the check pile.
A named validator catalog makes the constraint set data-driven and per-type composable.

## Design

- **Closed catalog, open assignment** — the same boundary as the category axis. Validator
  *logic* is hard-coded in squads; there is no adopter-supplied validator code (the no-eval
  line drawn for splat-refs applies here too). What is spec-declared is *which* validators a
  type runs, plus their params.
- **Composition with categories.** A category supplies a default validator bundle; a type's
  own `validators` list extends it (records → `no_parent`; work → `parent_in:<types>`). A
  category's behavioural defaults are *implemented as* validator bundles, not a parallel
  mechanism.
- **Rule data stays structured; validators are the checks that read it.** Keep `parents`,
  `parent_required`, title-max, etc. as structured spec fields; a validator references/reads
  them rather than re-encoding the rule as a string param. One home per rule, no drift.
- **One engine, two call sites.** `sq check` (collect all issues) and create/update
  (fail-closed on the first violation) run the same validators — the report-vs-abort split
  mirrors the existing workflow-lint pattern.

## Seed catalog (from today's checks)

The existing `_check_*` methods become the initial named validators, e.g.:

- `parent_required` / `parent_in:<types>` / `no_parent` — parent eligibility
- `subtask_story_mapping` — subtask maps to a parent story
- `subentity_body_written` — no unwritten placeholder sub-entity bodies
- `subentity_title_max:<n>` — over-long finding/story titles
- `no_status_banner` — no lifecycle/status prose in bodies
- `subentity_status_valid`, dangling parent, dangling ref, backend reconciliation

## Outcomes grouped under this epic

- A validator catalog (hard-coded, closed) plus a per-type `validators` declaration (spec).
- `sq check` re-expressed over the catalog; create/update gating shares the same engine.
- Category default validator bundles (records `no_parent`, work `parent_in`, …).
- No regression: the current check set is fully represented as validators, byte-identical
  behaviour for the bundled spec.

## Acceptance (epic-level)

- Every rule `sq check` enforces today is expressed as a named validator; a bare
  `uv run sq check` on this repo reports the same issues it does now.
- A type's effective validator set is category defaults + its own additions; a validator not
  in the closed catalog fails closed.
- create/update and `sq check` share one validator engine — no rule logic duplicated between
  the gate and the report.
- Adopter-supplied validator *code* is rejected; only catalog validators, referenced by name
  and params, are allowed.

## Dependencies / relationships

- **Sibling of EPIC-538** (spec customization). 538's "records take no parent, enforced" is
  this framework's first customer — implemented as the `no_parent` validator rather than a
  hardcoded check.
- **Shares the foundational ADR** (architect): the category axis and the validator model are
  decided together — they compose — before either epic's features are built.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T15:56:27Z] Pierre Chat:
  - Split out from the EPIC-538 discussion: generalize parent_required into a pluggable, closed-catalog validator framework powering sq check + create/update gating. Sibling to EPIC-538 (its records-no-parent enforcement is the first customer, built as the no_parent validator). Category axis + validator model to be pinned together in one foundational ADR before features are cut.
<!-- sq:discussion:end -->
