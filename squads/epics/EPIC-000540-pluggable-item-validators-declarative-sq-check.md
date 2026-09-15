---
id: EPIC-540
sequence_id: 540
type: epic
title: Pluggable item validators (declarative sq check)
status: InProgress
author: product-owner
priority: medium
refs:
- EPIC-538
- ADR-864
description: Turn sq check + create/update gating into a declarative, pluggable validator
  catalog; parent_required becomes one validator; category defaults are validator
  bundles.
created_at: '2026-07-21T15:56:09Z'
updated_at: '2026-09-03T09:02:19Z'
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

## Seed catalog (delivered by FEAT-568)

The existing `_check_*` methods became the initial named validators, e.g.:

- `parent_required` / `parent_in:<types>` / `no_parent` — parent eligibility
- `subtask_story_mapping` — subtask maps to a parent story
- `subentity_body_written` — no unwritten placeholder sub-entity bodies
- `subentity_title_max:<n>` — over-long finding/story titles
- `no_status_banner` — no lifecycle/status prose in bodies
- `subentity_status_valid`, dangling parent, dangling ref, backend reconciliation
- `parent_acyclic` — a parent chain that closes on itself (landed after this epic first
  closed, as a bug fix; folded into the floor)

## Reopened for ADR-864's full catalog build-out

Closing this epic against the seed catalog was closing it against FEAT-568's children, not its
outcome. ADR-864 (accepted 2026-09-03) found the outcome incomplete: the catalog had no
**declared level, parameter/threshold, or required-context** dimension — an adopter can select
a validator but not say how much they mean it, which is why several real checks (the
contract-currency rule, the requires-a-parent check) either shipped bundled-and-noisy or stayed
unbundled entirely. It also names sixteen validators the corpus needs that were never built,
and two floor members (`no_status_banner`, the sub-entity title threshold) that fail this
framework's own floor-vs-catalog-only test.

This epic reopens to deliver that: the full ADR-864 build-out is now in scope, sequenced by
its accepted build order (see the features grouped under this epic).

## Acceptance (epic-level)

- Every rule `sq check` enforces today is expressed as a named validator; a bare
  `uv run sq check` on this repo reports the same issues it does now.
- A type's effective validator set is category defaults + its own additions; a validator not
  in the closed catalog fails closed.
- create/update and `sq check` share one validator engine — no rule logic duplicated between
  the gate and the report.
- Adopter-supplied validator *code* is rejected; only catalog validators, referenced by name
  and params, are allowed.
- A selection can declare its level (subject to a declared floor a selection may raise but not
  lower), and a threshold/parameter lives in the spec rather than a module constant.
- Every ADR-864 Part 2 member that is buildable today exists in the catalog, correctly tiered
  (floor / category bundle / catalog-only) per the ADR's tiering test.

## Dependencies / relationships

- **Sibling of EPIC-538** (spec customization, Done). 538's "records take no parent, enforced"
  was this framework's first customer — implemented as the `no_parent` validator rather than a
  hardcoded check.
- **Shares the foundational ADR-541** (architect): the category axis and the validator model
  were decided together — they compose.
- **ADR-864** rules the reopened scope: three tiers, declared levels, no injected Python. Its
  accepted build order is the sequencing for the features under this epic.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T15:56:27Z] Pierre Chat:
  - Split out from the EPIC-538 discussion: generalize parent_required into a pluggable, closed-catalog validator framework powering sq check + create/update gating. Sibling to EPIC-538 (its records-no-parent enforcement is the first customer, built as the no_parent validator). Category axis + validator model to be pinned together in one foundational ADR before features are cut.
- [2026-07-24T07:55:02Z] Catherine Manager:
  - Reconciled to Done — the pluggable-validator model shipped: FEAT-567 (ValidatorEngine dispatch) + FEAT-568 (named-validator catalog). Every sq check rule is a named catalog validator (same issues as before), effective set = category defaults + per-type additions with a closed catalog failing closed, create/update + sq check share one engine (no duplicated rule logic), and adopter-supplied validator code is rejected (catalog-by-name only). Acceptance met.
- [2026-09-03T09:01:43Z] Nina Product:
  - Epic-parentage call: reopened this epic (Done -> InProgress) rather than opening a new one, for ADR-864's full catalog build-out.
  - Its outcome statement -- turn sq check + create/update gating from hardcoded checks into a declarative, pluggable validator catalog, composable per type -- was closed on FEAT-568's seed catalog, but that seed never delivered the declared-level/parameter/required-context dimension ADR-864 identifies as the missing piece, and never built the Part 2 members. The outcome was not actually complete; closing it against FEAT-568's children rather than the outcome is the exact failure this team has been burned by before. Reopening says so honestly instead of inventing a second epic for the same outcome.
  - Contrast with EPIC-897 (new epic for ADR-880): that case has no existing epic whose stated outcome matches, so a new epic is the honest move there. Here one already exists and matches precisely.
<!-- sq:discussion:end -->
