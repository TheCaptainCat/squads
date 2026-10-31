---
id: FEAT-900
sequence_id: 900
type: feature
title: 'field_value_declared: frontmatter values against declared collections'
status: Cancelled
parent: EPIC-540
author: product-owner
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
updated_at: '2026-10-16T20:07:10Z'
priority: low
---
<!-- sq:body -->
## Why

A badge or field value in frontmatter that is not a member of the collection its field
declares. Values set through the CLI are already parsed against the collection, but a
hand-edited file, a bulk import, or a collection narrowed in an override after the fact can all
leave a stale value behind, and nothing reads it back to notice. This is a defect wherever it
occurs; it has stayed invisible only because this project ships the collections it uses.

## Scope

- `error`-level, in the `work` and `records` category bundles (ADR-864's ruled tier), so it runs
  on every type of those two categories and on none of the `roster` types.
- Covers every declared field that names a collection, on an item and on a sub-entity (a story's
  or finding's own fields), not just `priority` and `severity`. An empty field is not a finding.
  Status values are out of scope: they already have their own checks (`item_status_valid`,
  `subentity_status_valid`).
- Needs nothing beyond the item and the spec, so it can run wherever the other frontmatter-only
  members run.
- The depended-on assignment grammar (FEAT-898) is delivered; this member is declared and
  selected under it like any other.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 900 add-story "As a <role>, I want … so that …"`; track with `sq feature 900 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Flag a frontmatter field value outside its declared collection

<!-- sq:story:US1:body -->
As anyone maintaining a squad with customized collections (badges, priorities, statuses), I want sq check to flag a frontmatter field value that is not a member of its field's declared collection, so a hand-edit, a bulk import, or a collection narrowed after the fact doesn't leave a silently-invalid value on an item.

Acceptance:
- Error-level: sq check exits 3 on a finding; the message names the item (or sub-entity), the field, the offending value and the collection.
- Runs by default on every work and records type, and on item fields and sub-entity fields alike; it fires for any field/collection pair, including a custom field a project declares, not only priority and severity.
- Test shapes: a hand-edited priority value outside its collection; a collection narrowed in an override after an item already carries a now-removed value; an invalid value on a sub-entity (a finding's severity); an empty field (no finding); a valid value (no finding); a roster-type item (not checked).
- Status values are not reported by this member.
- CLI writes are unaffected: a value the CLI accepts never triggers it.
- The way out exists: setting a valid value through the CLI on an item that currently carries a stale one succeeds, while an unrelated update to that item is refused until it is fixed.
- Proven on a scratch copy of this repository's squad (brought to the schema of the build under test if it differs): sq check there reports the same issues with the member as without it, so adopting it adds no finding to a squad whose values are all valid. This repository's own override is not edited by this feature, and the live board, run by the released tool until release preparation, is unaffected.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T15:35:14Z] `product-owner` Nina Product:
  - 2026-10-09 readiness pass: ADR-864 tier and FEAT-898 grammar confirmed as shipped; scoped to item and sub-entity fields, status excluded, recovery path and unchanged-sq-check acceptance added. Moved to Ready.
- [2026-10-12T05:25:57Z] `product-owner` Nina Product:
  - 2026-10-12: separated engine delivery from this project's own selection; the live override is read by the released 0.15.0 tool, so this repository's selection moves to a release-preparation step after the squad is migrated.
- [2026-10-12T05:26:08Z] `product-owner` Nina Product:
  - 2026-10-12: (correction for FEAT-900) only US1's last acceptance line changed: proof on a scratch copy of the squad; no project selection exists here, the member is in the bundles.
- [2026-10-16T19:58:53Z] `tech-lead` Olivia Lead:
  - Task TASK-1073 (Draft) carries the breakdown; dependencies in its body.
- [2026-10-16T20:07:07Z] `manager` Catherine Manager:
  - 2026-10-16: the goal is already met. The index load boundary refuses any stored field value outside its collection (_index/_store.py, items and sub-entities, custom fields included), so a validator member could never report: the load fails first (measured by python-dev on TASK-1073). Simplest rule kept: one membership check, at load, fail-closed. Cancelled; no scope is lost.
<!-- sq:discussion:end -->
