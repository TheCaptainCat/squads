---
id: FEAT-948
sequence_id: 948
type: feature
title: 'Required views: a declared, enforced document invariant'
status: Draft
parent: EPIC-897
author: product-owner
refs:
- MILE-867:targets
- ADR-880:implements
subentities:
- local_id: US1
  title: A view can require its tag, with hosts derived not declared
  status: Todo
- local_id: US2
  title: A body replace cannot silently drop a required host's tag
  status: Todo
- local_id: US3
  title: The append guard and view rm stay scoped to what they protect
  status: Todo
- local_id: US4
  title: sq check reports a document that has lost its required tag
  status: Todo
- local_id: US5
  title: Bundled views declare required; hardcoded write refusals retire
  status: Todo
- local_id: US6
  title: Convergence licence narrows; legacy reclaim moves to a migration
  status: Todo
created_at: '2026-09-15T07:18:30Z'
updated_at: '2026-09-15T08:25:54Z'
---
<!-- sq:body -->
## Outcome

A view declaration can be **required**. When it is, every document the tool's own placement
authority seeds its tag onto must keep that tag: a body replace that would drop it is refused
outright, `sq view rm` will not take it off, and `sq check` reports an error-level finding on a
host that has lost it anyway. Whether a document is a required view's host is **derived**, never
declared separately — from a type's creation template, or from the roster writer's own
classification for a role, a permanently-system skill, and a per-item-type skill — so the
requirement can never outrun what creation already produces.

This is the enforcement half of ADR-880's tag mechanism. FEAT-905 built the tag itself (the
placement verb, read-time expansion, check integration); FEAT-907 seeds and migrates the
milestone roll-up tag. This feature makes losing a required tag impossible to do silently, across
every bundled view: the milestone roll-up and the five roster views (a role's own definition, and
the four system-adjacent skills).

## Why

Two guards on a body are distinct, and only one is forceable. Overwriting an existing authored
body is *protected* — `--force` is exactly the consent that lifts that protection. Producing a
body that omits a required view's tag is *forbidden* — a document invariant, not prose an author
is consenting to lose, so no flag lifts it. That forbidding rule already ships today, hardcoded
per type inside the body-write closure, for a role and for a permanently-system skill. This
feature turns it into a declared, per-view flag instead, so the same rule reaches
`milestone_rollup` — the one bundled view a body write can actually reach — without adding a new
hardcoded branch, and so a future bundled or adopter-declared view gets the same protection by
setting one field.

## Scope

- A `required: bool` field on the view declaration, defaulting to false — a key of the view
  itself, never a per-type attachment axis.
- One host-set helper that answers, from a document's **type and slug alone**, whether it must
  carry a given required view's tag. It composes the existing creation-template seeding lookup
  and the roster writer's own tag classification rather than re-implementing either.
- The shared body-write closure (covering both the single-item body command and the bulk
  importer's body operation) refuses a **replace** that would leave a required host without its
  tag — unconditionally, before and independent of `--force`. `--append` is untouched by this
  rule, because it keeps the whole existing region and cannot drop a tag the body already had.
- The append refusal that already protects a tool-converged roster body (a role's or a system
  skill's) survives as its own rule, keyed on the same host classification — never on a type
  literal — since that region is silently reconverged by repair and appended prose beside the tag
  would otherwise be lost with no warning.
- `sq view rm` refuses to remove a required view's tag from one of its hosts. Every other removal
  — an undeclared name, a source that cannot apply to this host, or a non-required view — stays
  free exactly as it does today.
- An unconditional, error-level `sq check` finding, in the always-on per-file scan rather than the
  selectable validator catalog, reports a host document that no longer carries its required tag,
  naming the remedy (`sq view add`). Nothing is reported for a non-required view.
- All six bundled views — `role_definition`, `squads_skill`, `greeting_skill`, `memory_skill`,
  `item_skill`, and `milestone_rollup` — declare `required = true`.
- The hardcoded role and system-skill body refusals retire into the general rule, for replace
  only. The role-authoring remedy (declare the definition in `.overrides/roles.toml`, or a
  project-defined role's own override file) moves onto `sq role <slug> show`'s empty-body hint,
  since a refusal message composed from a view's name can no longer carry a per-role sentence.

## Acceptance

- A body replace on a milestone, a role, or a permanently-system skill that would drop its
  required tag is refused, and `--force` does not lift it — including a pristine, never-written
  body on such a document.
- The same document accepts an `--append` that leaves the tag in place.
- The bulk importer's body operation is refused by the same rule as the single-item body command —
  one shared closure, not two implementations.
- `sq view rm` refuses on a declared, required host, and still works on every other tag: an
  undeclared name, a source inapplicable to the host, a non-required view, and a hand-placed tag
  on a document that is not one of the view's hosts.
- A retype that carries a required tag into a type the view no longer applies to produces a
  readable document and a reported `sq check` finding — no refusal and no rewrite; retype's own
  behaviour is unchanged.
- A view dropped from the project's selection, and a `required = true` view that nothing yet
  seeds, both bind nothing and are reported nowhere.
- `sq check` reports every host document missing its required tag, unconditionally and at error
  level, and reports nothing for a non-required view.
- `sq role <slug> show` still surfaces the role-authoring remedy once the generalised refusal
  message stops carrying it.
- `uv run sq check` is clean on this corpus.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 948 add-story "As a <role>, I want … so that …"`; track with `sq feature 948 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — A view can require its tag, with hosts derived not declared

<!-- sq:story:US1:body -->
As an adopter declaring a view, I want to mark it required and have its host set derived from what the tool's own placement authority (a creation template, or the roster writer's classification for a role/system skill) already seeds the tag onto, so the requirement can never outrun what creation produces.

Acceptance: required: bool on the view declaration, default false; a required=true view that nothing yet seeds loads cleanly and binds nothing; the host set is computed from a document's type and slug alone, never its content; one helper composes the creation-template lookup and the roster writer's classification rather than re-deriving either.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — A body replace cannot silently drop a required host's tag

<!-- sq:story:US2:body -->
As the owner of a milestone, a role, or a system skill, I want a body replace that would drop a required view's tag refused outright — independent of --force and before the authored-body overwrite guard — so I can never write a document that reads as empty of that view.

Acceptance: replace is refused unconditionally on a required host, --force does not lift it, and a pristine never-written body on a required host is refused too; the same refusal covers the bulk importer's body operation through the shared closure; --append on the same document still succeeds.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — The append guard and view rm stay scoped to what they protect

<!-- sq:story:US3:body -->
As the maintainer of a role or system-skill body, I want the append refusal that protects a tool-converged region to survive as its own rule (not the required-view rule), and sq view rm to refuse only on a declared required host, so every other tag removal — an undeclared name, an inapplicable source, a non-required view — keeps working exactly as it does today.

Acceptance: append on a role/system-skill body is refused via the sweep's own classification, never a type literal; view rm refuses only when the named view is declared, required, and this document is one of its hosts; every other removal stays free.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — sq check reports a document that has lost its required tag

<!-- sq:story:US4:body -->
As anyone running sq check, I want an unconditional, error-level finding naming a host document that no longer carries its required view's tag, with the remedy (sq view add), so the loss is visible instead of a document quietly reading as empty of that view.

Acceptance: the finding fires in the always-on per-file scan (needs no resolved item, fires on a file too broken to parse), is never a selectable validator, and reports nothing for a non-required view.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Bundled views declare required; hardcoded write refusals retire

<!-- sq:story:US5:body -->
As a maintainer of squads, I want role_definition, squads_skill, greeting_skill, memory_skill, item_skill, and milestone_rollup to all declare required=true, and the hardcoded role/system-skill refusals in the body-write closure to retire into the general required-host rule for replace only, so the same mechanism that protects every other required host also protects these instead of two special-cased branches.

Acceptance: all six declarations carry required=true; the ROSTER_ROLE and is_system_skill branches in the body-write closure are gone, replaced by the general rule, for replace only — append is untouched and stays refused on a role/permanently-system-skill body under its own rule; the retirement is a narrowing rather than a like-for-like swap, so a role whose role_definition view is dropped from selection, a permanently-system skill whose view is dropped, and a stale historically-bundled sq-<type> skill whose type is no longer declared are all admitted to a write the old branches refused; the role-authoring remedy is reachable from sq role <slug> show's empty-body hint instead of the refusal message.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Convergence licence narrows; legacy reclaim moves to a migration

<!-- sq:story:US6:body -->
As a maintainer of squads, I want the repair sweep's convergence licence for a role or permanently-system-skill body to require the region be empty or already tagged before converging it, and the one-time pre-0.14 plain-prose reclaim that licence performs today to move into a migration step, so a body dropped from a required view, authored by hand, and later restored to required keeps that authored prose through a subsequent sync, repair, and version-drift convergence pass.

Acceptance: _converge_body_tag uses strict_empty=True for role_definition and for every SYSTEM_SKILL_VIEW_NAMES entry, at both call sites in _services/_maintenance.py; a body taken through drop (view unselected) then author (prose written by hand) then re-add (view reselected) then a version-drift convergence pass keeps the author's prose intact, with the view's tag placed beside it rather than replacing it; the pre-0.14 legacy reclaim — a marker-free, non-empty sq:body on a role or permanently-system skill converged to that document's own view tag — runs once as a migration step, is idempotent, and reports the count of bodies it changes; applied to this corpus the migration step changes nothing, since every role and permanently-system-skill body here already carries its tag.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T07:20:20Z] Nina Product:
  - New feature authored under EPIC-897 per Olivia's parenting recommendation and op-pierre's fourth-amendment ruling on ADR-880: the required-view flag, its derived host set, the write refusal, view rm narrowing, the tier-1 check finding, and the set_body retirement. Refs: MILE-867 (targets), ADR-880 (implements).
  - Five stories: US1 the required flag + derived host set, US2 the replace refusal, US3 the append/view-rm scoping, US4 the sq check finding, US5 all six bundled views + set_body retirement. FEAT-907's US4 folds into this breakdown (broadened past the milestone-only frame).
  - Left Draft — promotion at dispatch is mine. @manager for scheduling once Olivia reparents TASK-942 here and remaps its subtask story mappings.
- [2026-09-15T08:25:54Z] Nina Product:
  - US5's acceptance was incomplete: it named the six required declarations and the set_body retirement but not the convergence-licence narrowing and migration reclaim the tech lead has since mapped to it (per ADR-880's fifth amendment).
  - Split: US5 stays the write-path half (declarations + retirement, reworded as a narrowing not a substitution). New US6 covers the repair-sweep half: strict_empty convergence for role/system-skill bodies, and the pre-0.14 reclaim moving to a migration -- with explicit acceptance that an author's prose survives a drop then author then re-add then convergence round trip.
  - @manager TASK-942's subtask mapping needs one change: ST11 and ST12 (currently mapped to US5) should map to US6 instead; ST1/ST2/ST3/ST4/ST5/ST6/ST7 mappings are unaffected. No existing stories renumbered.
<!-- sq:discussion:end -->
