---
id: FEAT-901
sequence_id: 901
type: feature
title: 'Part 2 catalog-only validators: title, body, description, blockers'
status: Done
parent: EPIC-540
author: product-owner
priority: low
refs:
- ADR-864:implements
- FEAT-898:depends-on
- MILE-934:targets
description: Eight opt-in per-item checks from ADR-864 Part 2; this project's own
  selection of two of them is a release-preparation step
subentities:
- local_id: US1
  title: 'item_title_max: flag over-long item titles'
  status: InProgress
- local_id: US2
  title: 'ref_rule_target_typed: flag a ref pointing at the wrong type'
  status: InProgress
- local_id: US3
  title: 'body_written: flag an item body still at the placeholder'
  status: InProgress
- local_id: US4
  title: 'description_present: flag an item with no summary'
  status: InProgress
- local_id: US5
  title: 'assignee_present: flag an active item with nobody on it'
  status: InProgress
- local_id: US6
  title: 'blocked_has_blocker: flag a blocked item with no dependency edge'
  status: Todo
- local_id: US7
  title: 'settled_requires_discussion: flag a settled item with no discussion'
  status: InProgress
- local_id: US8
  title: 'external_id_not_in_title: flag a foreign tracker id baked into a title'
  status: InProgress
- local_id: US9
  title: A squad selects item_title_max and body_written in its override
  status: InProgress
- local_id: US10
  title: Adopter documentation for the eight opt-in checks
  status: Todo
- local_id: US11
  title: A status role can declare that it means blocked
  status: Todo
created_at: '2026-09-03T09:02:34Z'
updated_at: '2026-10-16T22:50:29Z'
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
- `assignee_present` -- an item at a status whose role is live with nobody on it.
- `blocked_has_blocker` -- an item at a status whose role declares `blocked` with no dependency
  edge in either direction; it takes no parameter.
- `settled_requires_discussion` -- an item at a status whose role is settled with an empty
  discussion.
- `external_id_not_in_title:<regex>` -- a title carrying a foreign tracker's identifier.

Shared across all eight:

- A member is effective for a type only when that type's `validators` list names it; a squad that
  selects nothing sees no new finding. A project may raise any of them to `error` with the
  `@error` suffix.
- Each states, as the ADR requires of a new member, the context it needs and its consistency-
  clause bucket; a member that needs the on-disk text sits out the create/update gate, like
  `subentity_body_written` and `no_status_banner` do.
- Statuses are matched by the flag the status's role declares, never by a role name or a status
  name: `live` for active, `blocked` for blocked, `settled` for settled. A project that renames a
  role, or declares its own, gets the same behaviour once the role carries the flag.
- None of the eight applies to a roster type (role, skill, operator). The eight are policies about
  the work an item tracks -- its title, summary, assignee, blockers and discussion -- and a roster
  entry is configuration of the squad, not work. Naming any of the eight on a roster type is
  refused at spec load, naming the type and the entry.
- A selection that the spec's own declarations make unable to fire is refused at spec load, naming
  the type and the entry, and `sq workflow lint` reports it as an error. The cases: any of the
  eight on a roster type; `ref_rule_target_typed` on a type that declares no ref rule with a
  target; `assignee_present` on a type whose lifecycle holds no status of a live role;
  `blocked_has_blocker` on a type whose lifecycle holds no status of a role declaring `blocked`,
  or in a spec that declares no dependency-role ref kind. Whether the corpus currently holds an
  offender is never part of that test.

**This project's own selection is `item_title_max` and `body_written`** (ADR-864's own call): our
items are agent-authored, and a 200-character title passes clean today. The selection goes in this
project's own `.overrides/workflow.toml`, never in the bundled spec, which ships to every adopter.

## Engine delivery and this project's selection are separate

This feature delivers the eight members: a squad that names one in a type's `validators` list gets
it, as the stories specify. That is proven on scratch squads and in tests, including a scratch copy
of this repository's squad with the override extended there.

Writing this project's selection into this repository's own `squads/.overrides/workflow.toml` is
**not** part of the feature. Constraint: that file is read by the released tool (0.15.0) for as long
as that tool operates this board, and the released tool refuses an entry it does not know -- with a
new name in the file, `sq check` exits 3 and every other command exits 1, for everyone. The new
names can only be written there once the squad is migrated and the board runs on the new build.
That is a step of release preparation, stated below.

## Release-preparation acceptance for this repository

Done by the manager at release preparation, **after the operator has migrated this repository's
squad** (the operator's step, once, after every contributor has amended the migration) and the board
runs on the new build:

- `squads/.overrides/workflow.toml` selects `item_title_max:120` and `body_written` on every
  work and records type; roster types are not given either. A type's list that does not open with the splat of
  its bundled list keeps its other entries by naming them again (replacing a list without the splat
  drops the bundled ones).
- A bare `sq check` on this repository is clean afterwards: the item titles over 120 characters and
  the bodies still at the placeholder are counted on the migrated squad first; each one is fixed in
  the same step, or its count is raised to the operator before the selection lands. At the last
  measurement no item title was over 120 and seven were over 100.
- `sq workflow lint` reports the override valid on the new build.

## Build constraint

The `blocked` flag (story 11) changes the bundled workflow document, so the part of this feature
that changes a bundled file is built after the working version is bumped. The other stories change
no bundled file.

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
- Naming the member on a roster type (role, skill, operator) is refused at spec load, naming the type and the entry, and reported by sq workflow lint; the member is never evaluated on a roster item.
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
- Only a ref rule that declares target types counts: an edge whose kind has a rule with no target types is silent. Selecting it on a type that declares no ref rule with a target is refused at spec load, naming the type and the entry, and reported by sq workflow lint as an error.
- Naming the member on a roster type (role, skill, operator) is refused at spec load, naming the type and the entry, and reported by sq workflow lint; the member is never evaluated on a roster item.
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
- Fires on an item created without a body; silent once any body is written.
- Needs the on-disk text, so it reports in sq check and does not run at the create/update gate.
- Naming the member on a roster type (role, skill, operator, a custom skill included) is refused at spec load, naming the type and the entry, and reported by sq workflow lint; the member is never evaluated on a roster item.
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
- Naming the member on a roster type (role, skill, operator) is refused at spec load, naming the type and the entry, and reported by sq workflow lint; the member is never evaluated on a roster item.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — assignee_present: flag an active item with nobody on it

<!-- sq:story:US5:body -->
As a team mixing human and agent assignment, I want an item at a live status with nobody assigned flagged.

Acceptance:
- Warn, catalog-only; fires when the item's status resolves to a role declaring live = true and the assignee is empty; silent once assigned, and silent at any status whose role is not live.
- Keys off the flag the status's role declares, never a role name or a literal status name: a project that renames its in-progress status, or its live role, or declares a role of its own with live = true, gets the same behaviour; a role named active that declares live = false is not matched.
- Selecting it on a type whose lifecycle holds no status of a live role is refused at spec load, naming the type and the entry.
- Naming the member on a roster type (role, skill, operator) is refused at spec load, naming the type and the entry, and reported by sq workflow lint; the member is never evaluated on a roster item.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — blocked_has_blocker: flag a blocked item with no dependency edge

<!-- sq:story:US6:body -->
As a team that uses the blocked status as a real signal, I want an item at a blocked status (its role declares blocked) with no dependency edge in either direction flagged, so the blocker can't exist only in somebody's head.

Acceptance:
- Warn, catalog-only; fires when the item's status resolves to a role declaring blocked = true and it has neither an outgoing nor an incoming edge of a dependency-role ref kind (blocks, depends-on in the bundled spec, resolved by the kind's declared role, not its name).
- Silent when either direction has such an edge; silent at statuses whose role does not declare blocked; an edge of another kind (related, targets) does not satisfy it.
- Naming the member on a roster type (role, skill, operator) is refused at spec load, naming the type and the entry, and reported by sq workflow lint; the member is never evaluated on a roster item.
- The member takes no parameter: an entry with one is refused at spec load, as for any member that takes none.
- Selecting it on a type whose lifecycle holds no status of a role declaring blocked, or in a spec that declares no dependency-role ref kind, is refused at spec load, naming the type and the entry. The flag itself is story 11.
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
- Warn, catalog-only; fires when the item's status resolves to a role declaring settled = true and its discussion holds no comment at all; silent once one comment exists.
- Evaluated by sq check, from the item's on-disk discussion; it does not block or delay the status transition itself.
- Keys off the settled flag the status's role declares, never a role name or a literal status name.
- Counts the item's own discussion only: a settled item whose only comment sits on one of its stories (or other sub-entity) is flagged, and one top-level comment on the item clears it.
- Naming the member on a roster type (role, skill, operator) is refused at spec load, naming the type and the entry, and reported by sq workflow lint; the member is never evaluated on a roster item.
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
- Naming the member on a roster type (role, skill, operator) is refused at spec load, naming the type and the entry, and reported by sq workflow lint; the member is never evaluated on a roster item.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — A squad selects item_title_max and body_written in its override

<!-- sq:story:US9:body -->
As a squad whose items are agent-authored, I want to select item_title_max and body_written in my own override, so a long title or a placeholder-body item no longer passes clean -- proven here on a copy of this repository's own squad, which is the squad that will make this selection at release preparation.

Acceptance:
- On a scratch copy of this repository's squad (brought to the schema of the build under test if it differs), with the override extended there, every work and records type's list reads item_title_max:120 and body_written (the roster types role, skill and operator keep their lists unchanged), and each type keeps its other bundled validators (replacing a type's validators list without the splat form drops them). The scratch override loads clean and sq workflow lint reports it valid.
- On that copy, an item with a 121-character title warns and a 120-character title is clean; an item at the placeholder body warns on a work or records type; roster items are not checked (the roster types' lists name neither member); the findings carry the item ids.
- The bundled spec selects neither member, and a fresh sq init does not either: a squad that selects nothing sees no finding from them.
- This repository's own squads/.overrides/workflow.toml is not edited by this feature, and a bare sq check on this repository's live board reports the same issues before and after the feature lands. The selection in that file is the release-preparation acceptance in the feature body, done after the squad is migrated.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->

<!-- sq:story:US10 -->
### US10 — Adopter documentation for the eight opt-in checks

<!-- sq:story:US10:body -->
As an adopter, I want the eight opt-in per-item checks described in the documentation, so I can decide which to select, at what level, and what each will ask of my team without reading the source.

Acceptance:
- One documentation section describes all eight members, each with: its entry form and parameter (item_title_max:<n> and external_id_not_in_title:<regex> require one; the other six take none), its default level (warn), whether it can refuse a write at @error or only makes sq check exit non-zero, what it checks, and what clears a finding.
- It states how to select: name the entry in a type's validators list in the project's workflow override, with the @warn or @error suffix, and the splat form that keeps a type's bundled list; and that a squad that selects nothing sees no new finding.
- It states that the eight apply to the work and records categories only and never to role, skill or operator items, and lists each load-time refusal of a selection the spec makes unable to fire, with its exact text: any member on a roster type; ref_rule_target_typed with no ref rule that declares a target; assignee_present with no live-role status in the type's lifecycle; blocked_has_blocker with no blocked-flag role in the lifecycle or no dependency-role ref kind.
- It quotes the load-time refusals of the two parameterized members exactly as the tool prints them (missing or non-positive threshold, missing, uncompilable or @-containing pattern).
- Every statement is checked against the built tool. The page names no work item, no release-build narration and nothing about this project's own board or override.
- It warns, for external_id_not_in_title, that nothing bounds a match: the pattern runs on every sq check, and on a gated write only for a type that selects the check at @error (a check selected at warn is not evaluated on a write); a write holds the index lock while it runs, and a pattern that backtracks can therefore hang both.
- The roles reference documents the blocked flag beside live and settled, including what a squad that declares its own roles must do before it can select blocked_has_blocker; docs/stability.md lists the new key on sq workflow roles --json.
<!-- sq:story:US10:body:end -->

#### Discussion

<!-- sq:story:US10:discussion -->
<!-- sq:story:US10:discussion:end -->
<!-- sq:story:US10:end -->

<!-- sq:story:US11 -->
### US11 — A status role can declare that it means blocked

<!-- sq:story:US11:body -->
As an adopter who wants blocked_has_blocker, I want a status role to declare that it means blocked, so the check finds my blocked statuses by what the role declares and not by a name.

Acceptance:
- A status-role declaration accepts a boolean key blocked, default false, beside settled, hidden, color and live. A role that omits it behaves exactly as before; a non-boolean value is refused at spec load naming the role and the key.
- The bundled blocked role declares blocked = true; no other bundled role does.
- sq workflow roles --json gains blocked as a key on every row (the sixth key); the existing keys keep their names, types and values, and the text output of sq workflow roles shows the flag.
- A squad that declares its own roles has no blocked role until one of them declares the flag. Nothing changes for such a squad on upgrade, its spec still loads, and selecting blocked_has_blocker is refused at load, naming the flag, until a role declaring it is carried by a status of the type's lifecycle.
- No other consumer reads the flag: sq blocked and the blocked key of sq tree --json give the same output whether a role declares blocked or not (tested by toggling it).
- The flag is a change to the bundled workflow document and to the frozen --json surface, which the documentation story records.
<!-- sq:story:US11:body:end -->

#### Discussion

<!-- sq:story:US11:discussion -->
<!-- sq:story:US11:discussion:end -->
<!-- sq:story:US11:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-09T15:35:18Z] Nina Product:
  - 2026-10-09 readiness pass: eight members match ADR-864 Part 2 (parent_acyclic is the only one that pre-exists, and it is not in this feature). Fixed 0.15 reference, made role-keyed matching explicit, gave each story testable boundaries and parameter-refusal rules, chose item_title_max:120 for this project (zero corpus titles over 120), and pointed selection at the project override. Moved to Ready. Note for @tech-lead: this and FEAT-899 both need squads/.overrides/workflow.toml; whichever lands first creates it.
- [2026-10-09T17:04:05Z] Pierre Chat:
  - 2026-10-09: the project override is the right home for this project's selections (see FEAT-899), and item_title_max:120 stands.
- [2026-10-12T05:26:01Z] Nina Product:
  - 2026-10-12: separated engine delivery from this project's own selection; the live override is read by the released 0.15.0 tool, so this repository's selection moves to a release-preparation step after the squad is migrated.
- [2026-10-12T05:54:58Z] Nina Product:
  - 2026-10-12: answered the tech lead's four questions in the stories: eight members apply to work and records only (roster silent), settled_requires_discussion counts the item's own discussion, a never-firing selection loads and shows as a lint note, and US10 (docs) appended.
- [2026-10-12T06:25:18Z] Robert Architect:
  - @product-owner Story wording that has to follow op-pierre's rulings of 2026-10-12 (ADR-864 discussion, 06:19) and the dated corrections now in ADR-864 Part 2. Two of them reverse text added here at 05:54 today.
    
    **1. A selection that cannot fire is refused at load. It is not a lint note.**
    
    - Shared rules, the bullet beginning "A selection that can never fire on a type": it is refused at spec load, naming the type and the entry, and `sq workflow lint` reports it as an error. Drop "since the rules it depends on can be declared later" and the note that leaves the exit code unchanged.
    - The cases: any of the eight named on a roster type; `ref_rule_target_typed` on a type none of whose ref rules declares a target; `assignee_present` on a type whose lifecycle holds no status of a live role; `blocked_has_blocker` on a type whose lifecycle holds no status of a role declaring `blocked`, or in a spec with no dependency-role ref kind.
    - Shared rules, the roster bullet: the eight still never apply to a roster type, but "loads without a refusal and the member stays silent on it" becomes "is refused at spec load".
    - Every story's last bullet ("an offender there is silent even when the type's list names the member, and the list still loads"): naming the member on a roster type is refused at spec load.
    - US2, the bullet ending "loads without a refusal and never fires; sq workflow lint reports that as a note": refused at spec load.
    - US10, the docs line saying such a selection "loads without a refusal and shows as a note": the docs list the refusals.
    
    **2. Roles are matched by a flag the role declares, never by a role name.**
    
    - Shared rules: "matched by the role the spec gives them (active, blocked, settled)" becomes: by the flag the status's role declares, `live` for active, `blocked` for blocked, `settled` for settled.
    - US5: "resolves to the spec's active role" becomes "resolves to a role declaring `live = true`". A project that renames the role, or declares its own, gets the same behaviour.
    - US6: "resolves to the spec's blocked role" becomes "resolves to a role declaring `blocked = true`". The member takes no parameter.
    - New scope, and it needs a home in a story (US6 or its own): status roles gain a `blocked` flag, a boolean defaulting to false. The bundled `blocked` role declares it. `sq workflow roles --json` gains `blocked` on every row. A squad that declares its own roles declares the flag on the one it means, and until it does, selecting `blocked_has_blocker` is refused.
    - This is a bundled-spec change and an addition to a frozen surface, so the body can no longer say the feature changes no bundled file, and the developer task now waits for the working-version bump.
    - US10: the roles reference and `docs/stability.md` gain the flag.
    
    **3. `external_id_not_in_title` stays a regular expression.** US8 stands as written, the `@` refusal included. One addition, in US10: the docs warn that nothing bounds a match, and that a pattern which backtracks can hang `sq check` and a gated write, which holds the index lock.
    
    The tech lead has the matching subtask changes on TASK-1001.
- [2026-10-12T06:31:50Z] Nina Product:
  - 2026-10-12: aligned with ADR-864 and ADR-982 rulings: selections that cannot fire and any member on a roster type are refused at load, roles matched by flag (live, blocked, settled), story 11 appended for the blocked flag, docs story extended, bundled-file build constraint added.
- [2026-10-12T06:54:35Z] Nina Product:
  - 2026-10-12: story 10 aligned with the gate ruling: the external_id_not_in_title pattern runs on every sq check and on a gated write only where the type selects it at @error.
- [2026-10-15T18:05:20Z] Catherine Manager:
  - Moved to InProgress with stories 1-5 and 7-9: TASK-1001 part one is being built against them. Stories 6 and 11 wait on the 0.16.0 bump stop; story 10 on the docs task.
<!-- sq:discussion:end -->
