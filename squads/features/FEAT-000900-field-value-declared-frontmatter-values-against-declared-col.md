---
id: FEAT-900
sequence_id: 900
type: feature
title: 'field_value_declared: frontmatter values against declared collections'
status: Draft
parent: EPIC-540
author: product-owner
priority: low
refs:
- ADR-864:implements
- FEAT-898:depends-on
- MILE-934:targets
description: 'Error-level validator, work+records bundles: a badge/field value not
  a member of its field''s declared collection'
subentities:
- local_id: US1
  title: Flag a frontmatter field value outside its declared collection
  status: Todo
created_at: '2026-09-03T09:02:33Z'
updated_at: '2026-09-09T14:46:07Z'
---
<!-- sq:body -->
## Why

A badge or field value in frontmatter that is not a member of the collection its field
declares. Values set through the CLI are already parsed against the collection, but a
hand-edited file, a bulk import, or a collection narrowed in an override after the fact can all
leave a stale value behind, and nothing reads it back to notice. This is a defect wherever it
occurs; it has stayed invisible only because this project ships the collections it uses.

## Scope

- `error`-level, in the `work` and `records` category bundles (ADR-864's ruled tier).
- Depends on FEAT-898 for the declared-context grammar the check runs under.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 900 add-story "As a <role>, I want … so that …"`; track with `sq feature 900 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Flag a frontmatter field value outside its declared collection

<!-- sq:story:US1:body -->
As anyone maintaining a squad with customized collections (badges, priorities, statuses), I want sq check to flag a frontmatter field value that is not a member of its field's declared collection, so a hand-edit, a bulk import, or a collection narrowed after the fact doesn't leave a silently-invalid value on an item.

Acceptance: error-level; runs on work and records category bundles by default; fires on any field-collection pair (not just priority/severity) since the badge-collections model generalized the mechanism; a value that was valid when set and later falls outside a narrowed collection is caught by this check, not silently carried; CLI-driven writes remain unaffected (they already validate at write time) -- this check catches what CLI validation cannot see.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
