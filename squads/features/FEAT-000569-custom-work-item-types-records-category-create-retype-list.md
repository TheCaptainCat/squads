---
id: FEAT-569
sequence_id: 569
type: feature
title: 'Custom work-item types: records category create/retype/list'
status: Done
parent: EPIC-538
author: product-owner
priority: high
refs:
- FEAT-567
- FEAT-573
created_at: '2026-07-22T08:39:16Z'
updated_at: '2026-07-22T18:40:07Z'
---
<!-- sq:body -->
## Capability

Let an adopter define a wholly custom `records`-category work-item type (their own
durable-reference type alongside decision/contract/guide) with its own lifecycle,
and make `sq create` / `sq <type> retype` / `sq list` honor a type's `category`
generically instead of hardcoding the three bundled records types.

## Scope

- A project spec can declare a new item type with `category = "records"` (or
  `"work"`), its own lifecycle (statuses + transitions), prefix, and folder —
  reusing the generic-vocabulary override machinery together with the `category`
  axis (FEAT-567).
- `sq create <type>` works for a custom records type exactly as it does for a
  bundled one: allocates from the global counter, writes frontmatter with the
  declared `category`, refuses a parent if the effective validator set includes
  `no_parent` (the `no_parent` validator comes from FEAT-568's catalog; this
  feature does not itself add new validators — it makes create/retype/list
  category-generic).
- `sq <type> retype` and `sq list` read a type's `category` from the active spec
  rather than a hardcoded type-name list, so a custom records type is retypeable
  and listable on the same footing as decision/contract/guide.
- Backend pointer files / skill generation for a custom records type follow the
  same generic path as any other custom type (no records-specific special
  casing beyond what `category` already carries).

## Acceptance

- A spec defining a new `category = "records"` type loads, and `sq create`,
  `sq <type> retype`, and `sq list` all work on it without any code change —
  purely spec-driven.
- No remaining site hardcodes the three bundled records type names
  (`decision`/`contract`/`guide`) where "any records-category type" is meant.
- `sq check` clean; byte-identical behaviour for the bundled spec (no override
  present).

## Dependencies

- Depends on FEAT-567 for the `category` axis.
- Related: FEAT-573 (consumer audit reclassifying the existing `is_meta`-derived
  sites) touches overlapping call sites.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 569 add-story "As a <role>, I want … so that …"`; track with `sq feature 569 story <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T17:16:07Z] Catherine Manager:
  - FEAT-569 Done: custom records-category types are fully spec-driven — create/retype/list category-generic, retype work<->records with no_parent gated through the shared ValidatorEngine, end-to-end override-spec proof. Reviewed REV-614 (Approved, gate-ordering independently verified); full suite green. Accepted under the standing non-visual delegation.
<!-- sq:discussion:end -->
