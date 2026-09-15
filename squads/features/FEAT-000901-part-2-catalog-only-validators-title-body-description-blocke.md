---
id: FEAT-901
sequence_id: 901
type: feature
title: 'Part 2 catalog-only validators: title, body, description, blockers'
status: Draft
parent: EPIC-540
author: product-owner
priority: low
refs:
- ADR-864:implements
- FEAT-898:depends-on
- MILE-934:targets
description: Eight opt-in per-item checks from ADR-864 Part 2; this project selects
  item_title_max and body_written
subentities:
- local_id: US1
  title: 'item_title_max: flag over-long item titles'
  status: Todo
- local_id: US2
  title: 'ref_rule_target_typed: flag a ref pointing at the wrong type'
  status: Todo
- local_id: US3
  title: 'body_written: flag an item body still at the placeholder'
  status: Todo
- local_id: US4
  title: 'description_present: flag an item with no summary'
  status: Todo
- local_id: US5
  title: 'assignee_present: flag an active item with nobody on it'
  status: Todo
- local_id: US6
  title: 'blocked_has_blocker: flag a blocked item with no dependency edge'
  status: Todo
- local_id: US7
  title: 'settled_requires_discussion: flag a settled item with no discussion'
  status: Todo
- local_id: US8
  title: 'external_id_not_in_title: flag a foreign tracker id baked into a title'
  status: Todo
- local_id: US9
  title: This project selects item_title_max and body_written
  status: Todo
created_at: '2026-09-03T09:02:34Z'
updated_at: '2026-09-09T14:46:12Z'
---
<!-- sq:body -->
## Why

ADR-864 Part 2 names eight catalog-only, per-item validators that exist for adopters whose
teams and conventions differ from ours -- judgement calls about the work, not universal
defects, so each sits behind an opt-in rather than in a floor or bundle.

## Scope (all warn-level, catalog-only; depends on FEAT-898)

- `item_title_max:<n>` -- item titles are unchecked today (sub-entity titles already are); a
  200-character item title passes clean.
- `ref_rule_target_typed` -- an edge carrying a declared rule's kind but pointing at a type the
  rule does not target (kind validity checks membership only; the currency check reports an
  absence, never a misdirected edge).
- `body_written` -- the item-level twin of the existing sub-entity `subentity_body_written`; an
  item body still sitting at the rendered placeholder.
- `description_present` -- an item with no summary line, which is what every list view shows.
- `assignee_present` -- an item at an active-role status with nobody on it.
- `blocked_has_blocker` -- an item at a blocked-role status with no dependency edge in either
  direction.
- `settled_requires_discussion` -- an item reaching a settled status with an empty discussion.
- `external_id_not_in_title:<pattern>` -- a title carrying a foreign tracker's identifier.

**This project selects `item_title_max` and `body_written` at minimum** (ADR-864's own call):
our items are agent-authored, and a 200-character title passes clean today.

## Excluded on a prerequisite, not on scope

`label_declared` is **not** in this feature. It presupposes a declared label vocabulary --
labels are free strings today with no spec vocabulary behind them. ADR-864 names it as a
catalog member with a prerequisite, not a candidate ready to build; it stays out of 0.15 and
blocks nothing above it.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 901 add-story "As a <role>, I want … so that …"`; track with `sq feature 901 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — item_title_max: flag over-long item titles

<!-- sq:story:US1:body -->
As a team whose items are agent-authored, I want a warn advisory on an item title over a declared length, so a 200-character title doesn't pass clean the way it does today.

Acceptance: warn, catalog-only; declared threshold (spec field, not a constant); fires per item, mirroring the existing sub-entity title check's shape.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — ref_rule_target_typed: flag a ref pointing at the wrong type

<!-- sq:story:US2:body -->
As a project that declares typed ref rules, I want an edge that carries a declared rule's kind but points at a type the rule doesn't target flagged, so a misdirected edge is visible -- kind validity today only checks membership, and the currency check reports an absence, never a wrong-type target.

Acceptance: warn, catalog-only; fires on an edge whose kind names a ref_rule target type the pointed-at item does not match.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — body_written: flag an item body still at the placeholder

<!-- sq:story:US3:body -->
As a team that creates items in batches ahead of writing them, I want an item body still sitting at its rendered placeholder flagged, mirroring the existing sub-entity subentity_body_written check.

Acceptance: warn, catalog-only; item-level twin of subentity_body_written; same placeholder-detection mechanism.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — description_present: flag an item with no summary

<!-- sq:story:US4:body -->
As a team running a large board, I want an item with no summary line flagged, since the summary is what every list view shows.

Acceptance: warn, catalog-only; fires when an item's description/summary field is empty.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — assignee_present: flag an active item with nobody on it

<!-- sq:story:US5:body -->
As a team mixing human and agent assignment, I want an item at an active-role status with nobody assigned flagged.

Acceptance: warn, catalog-only; keys off the status's declared active role, never a literal status name.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — blocked_has_blocker: flag a blocked item with no dependency edge

<!-- sq:story:US6:body -->
As a team that uses the blocked status as a real signal, I want an item at a blocked-role status with no dependency edge in either direction flagged, so the blocker can't exist only in somebody's head.

Acceptance: warn, catalog-only; keys off the status's declared blocked role; checks for any blocks/depends-on edge in or out.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — settled_requires_discussion: flag a settled item with no discussion

<!-- sq:story:US7:body -->
As a team using the corpus as an audit record, I want an item reaching a settled status with an empty discussion flagged, so 'why did this close' stays answerable later.

Acceptance: warn, catalog-only; keys off the status's declared settled role; fires when the item's discussion has zero comments at the moment it settles or is checked.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — external_id_not_in_title: flag a foreign tracker id baked into a title

<!-- sq:story:US8:body -->
As a team mirroring another issue tracker, I want a title carrying that tracker's identifier flagged against a declared pattern, so the identifier lives in a ref instead of baked into a title that outlives the mirror.

Acceptance: warn, catalog-only; pattern is a declared parameter, e.g. external_id_not_in_title:<regex>.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — This project selects item_title_max and body_written

<!-- sq:story:US9:body -->
As this project, I want item_title_max and body_written selected in our own spec, since our items are agent-authored and a long placeholder-body item passes clean today without them.

Acceptance: this project's working spec selects both at sensible defaults; a bare uv run sq check surfaces any existing violation once selected (report the count with the change, per this project's own convention for waking a dormant validator).
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
