---
id: FEAT-901
sequence_id: 901
type: feature
title: 'Part 2 catalog-only validators: title, body, description, blockers'
status: Ready
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
updated_at: '2026-10-09T17:04:05Z'
---
<!-- sq:body -->
## Why

ADR-864 Part 2 names eight catalog-only, per-item validators that exist for adopters whose
teams and conventions differ from ours -- judgement calls about the work, not universal
defects, so each sits behind an opt-in rather than in a floor or bundle.

## Scope (all warn-level by default, catalog-only; delivered under the assignment grammar of FEAT-898)

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
- `settled_requires_discussion` -- an item at a settled status with an empty discussion.
- `external_id_not_in_title:<regex>` -- a title carrying a foreign tracker's identifier.

Shared across all eight:

- A member is effective for a type only when that type's `validators` list names it; a squad that
  selects nothing sees no new finding. A project may raise any of them to `error` with the
  `@error` suffix.
- Each states, as the ADR requires of a new member, the context it needs and its consistency-
  clause bucket; a member that needs the on-disk text sits out the create/update gate, like
  `subentity_body_written` and `no_status_banner` do.
- Statuses are matched by the role the spec gives them (active, blocked, settled), never by a
  status name.

**This project selects `item_title_max` and `body_written`** (ADR-864's own call): our items are
agent-authored, and a 200-character title passes clean today. The selection goes in this
project's own `.overrides/workflow.toml`, never in the bundled spec, which ships to every adopter.
That file is introduced by the re-tiering feature (FEAT-899); until it exists this feature creates
it.

## Excluded on a prerequisite, not on scope

`label_declared` is **not** in this feature. It presupposes a declared label vocabulary --
labels are free strings today with no spec vocabulary behind them. ADR-864 names it as a catalog
member with a prerequisite, not a candidate ready to build; it stays out of the 0.16 release and
blocks nothing above it.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 901 add-story "As a <role>, I want … so that …"`; track with `sq feature 901 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — item_title_max: flag over-long item titles

<!-- sq:story:US1:body -->
As a team whose items are agent-authored, I want a warn advisory on an item title over a declared length, so a 200-character title doesn't pass clean the way it does today.

Acceptance:
- Warn, catalog-only. The number is a required parameter, item_title_max:<n>; a bare selection, zero, or a non-integer is refused at spec load naming the entry, the way a missing ref_rule_target_present target is.
- Fires per item, mirroring the sub-entity title check's shape and message style: a title of n characters is clean, n+1 characters warns, and the message carries the length and the threshold.
- A squad that does not select it sees nothing, even for a 200-character title.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — ref_rule_target_typed: flag a ref pointing at the wrong type

<!-- sq:story:US2:body -->
As a project that declares typed ref rules, I want an edge that carries a declared rule's kind but points at a type the rule doesn't target flagged, so a misdirected edge is visible -- kind validity today only checks membership, and the currency check reports an absence, never a wrong-type target.

Acceptance:
- Warn, catalog-only. Fires on an edge whose kind has a declared ref rule with target types, when the pointed-at item is of a type outside those targets; the message names the edge, its kind and the allowed target types.
- Silent on an edge that satisfies its rule, on a kind with no declared rule, and on a dangling target (dangling_ref already reports that; no double report).
- Test shape: a feature holding an implements edge to a task while a contract-targeting rule is declared.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — body_written: flag an item body still at the placeholder

<!-- sq:story:US3:body -->
As a team that creates items in batches ahead of writing them, I want an item body still sitting at its rendered placeholder flagged, mirroring the existing sub-entity subentity_body_written check.

Acceptance:
- Warn, catalog-only; the item-level twin of subentity_body_written, using the same placeholder-detection mechanism.
- Fires on an item created without a body; silent once any body is written; silent on a roster item whose body is generated.
- Needs the on-disk text, so it reports in sq check and does not run at the create/update gate.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — description_present: flag an item with no summary

<!-- sq:story:US4:body -->
As a team running a large board, I want an item with no summary line flagged, since the summary is what every list view shows.

Acceptance:
- Warn, catalog-only; fires when an item's description (summary) field is empty or whitespace, silent when it holds any text.
- The finding is clearable with the verb that sets the summary (sq <type> <n> update --desc).
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — assignee_present: flag an active item with nobody on it

<!-- sq:story:US5:body -->
As a team mixing human and agent assignment, I want an item at an active-role status with nobody assigned flagged.

Acceptance:
- Warn, catalog-only; fires when the item's status resolves to the spec's active role and the assignee is empty; silent once assigned, and silent at any status whose role is not active.
- Keys off the status's declared role, never a literal status name: a project that renames its in-progress status gets the same behaviour.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — blocked_has_blocker: flag a blocked item with no dependency edge

<!-- sq:story:US6:body -->
As a team that uses the blocked status as a real signal, I want an item at a blocked-role status with no dependency edge in either direction flagged, so the blocker can't exist only in somebody's head.

Acceptance:
- Warn, catalog-only; fires when the item's status resolves to the spec's blocked role and it has neither an outgoing nor an incoming edge of a dependency-role ref kind (blocks, depends-on in the bundled spec, resolved by the kind's declared role, not its name).
- Silent when either direction has such an edge; silent at statuses whose role is not blocked; an edge of another kind (related, targets) does not satisfy it.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — settled_requires_discussion: flag a settled item with no discussion

<!-- sq:story:US7:body -->
As a team using the corpus as an audit record, I want an item at a settled status with an empty discussion flagged, so 'why did this close' stays answerable later.

Acceptance:
- Warn, catalog-only; fires when the item's status resolves to a settled role and its discussion holds no comment at all; silent once one comment exists.
- Evaluated by sq check, from the item's on-disk discussion; it does not block or delay the status transition itself.
- Keys off the status's declared settled role, never a literal status name.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — external_id_not_in_title: flag a foreign tracker id baked into a title

<!-- sq:story:US8:body -->
As a team mirroring another issue tracker, I want a title carrying that tracker's identifier flagged against a declared pattern, so the identifier lives in a ref instead of baked into a title that outlives the mirror.

Acceptance:
- Warn, catalog-only; the pattern is a required parameter, external_id_not_in_title:<regex>; a bare selection or a regex that does not compile is refused at spec load naming the entry, and a pattern containing the reserved @ is refused with that reason.
- Fires when the item's title matches the regex (search, not full-match); silent otherwise; the message names the matched text.
- Test shape: a pattern for a typical tracker key (letters, hyphen, digits) against a title that carries one and a title that does not.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — This project selects item_title_max and body_written

<!-- sq:story:US9:body -->
As this project, I want item_title_max and body_written selected in our own override, since our items are agent-authored and a long title or placeholder-body item passes clean today without them.

Acceptance:
- The selection lives in this project's own .overrides/workflow.toml, not in the bundled spec; a fresh sq init does not select either member.
- item_title_max is selected at 120 on every item type, a number no current item title exceeds (measured: zero of the corpus's item titles are over 120, seven over 100); tightening toward the roughly-70 convention is a separate, deliberate step. body_written is selected on every work and records type.
- Each type keeps its other bundled validators (replacing a type's validators list without the splat form drops them).
- A bare sq check on this repo is clean after the change: any existing item the selection flags is fixed in the same change, or raised to the manager with its count before landing -- not left as warnings.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T15:35:18Z] Nina Product:
  - 2026-10-09 readiness pass: eight members match ADR-864 Part 2 (parent_acyclic is the only one that pre-exists, and it is not in this feature). Fixed 0.15 reference, made role-keyed matching explicit, gave each story testable boundaries and parameter-refusal rules, chose item_title_max:120 for this project (zero corpus titles over 120), and pointed selection at the project override. Moved to Ready. Note for @tech-lead: this and FEAT-899 both need squads/.overrides/workflow.toml; whichever lands first creates it.
- [2026-10-09T17:04:05Z] Pierre Chat:
  - 2026-10-09: the project override is the right home for this project's selections (see FEAT-899), and item_title_max:120 stands.
<!-- sq:discussion:end -->
