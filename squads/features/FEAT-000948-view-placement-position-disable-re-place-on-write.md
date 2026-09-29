---
id: FEAT-948
sequence_id: 948
type: feature
title: 'View placement: position, disable, re-place on write'
status: Done
parent: EPIC-897
author: product-owner
refs:
- MILE-867:targets
- ADR-880:implements
subentities:
- local_id: US1
  title: Every document's seeded views are derived, never declared
  status: Done
- local_id: US2
  title: Every body write re-places view tags at their position
  status: Done
- local_id: US3
  title: Views are disabled, never deleted
  status: Done
- local_id: US4
  title: sq check and writes enforce one tag per seeded view
  status: Done
- local_id: US5
  title: 'Required flag retired: superseded by US1 and US7'
  status: Cancelled
- local_id: US6
  title: Migration reclaims legacy roster prose; dead skip channel removed
  status: Done
- local_id: US7
  title: Roster bodies hold no prose
  status: Done
- local_id: US8
  title: A view declares where its tag renders
  status: Done
created_at: '2026-09-15T07:18:30Z'
updated_at: '2026-09-29T09:29:10Z'
---
<!-- sq:body -->
## Outcome

A view declaration says where its tag renders: `top`, `bottom` (the default), or `after(<regex>)`,
which places the tag after the first matching line and falls back to `bottom` when nothing
matches. Every write to a document's body — a replace or an append alike — reads whatever view
tags the region already carries, strips them out, applies the prose edit, then puts every tag
back at its declared position, in declaration order, each keeping the state it had. A view that
the document is newly seeded with (its creation template, or its role/skill's own definition) is
inserted enabled if it had no tag at all. The same check runs after the write and inside `sq
check`: each of the document's seeded views appears exactly once, in either state, and no view
name appears twice.

A view is turned off, never removed: `view disable <name>` (`sq <type> <n> view disable <name>`,
or `sq role|skill <slug> view disable <name>` on a role or skill) swaps its tag to
`sq:view:<name>:disabled`, which renders nothing. What survives is the tag's state and the fact
that the view belongs on the document — never its location, which every write re-derives from the
view's declared position regardless. `view add <name>` is the only way back on, and also the way
to place the tag of a view the document does not carry yet. `view rm` is gone — there is nothing
left it would do that `disable` doesn't already do more safely.

A role's definition, a permanently-system skill's, and a per-item-type skill's each have exactly
one authoring surface — `.overrides/roles.toml` (or a project role's own override file) for a
role, the playbook overrides for a skill — so a body write is refused on all three, replace and
append alike, and `--force` does not lift it. Disabling the view is still allowed, which leaves
the document rendering an empty definition; writing one back by hand means dropping the view from
selection first.

Upgrading a squad initialised before 0.15 runs the same two migration steps it already runs
today, one of them widened: it places the roll-up tag on every existing milestone, and it
reclaims legacy plain prose into a tag on every role and permanently-system skill — now also on
every per-item-type skill, which carried that same 0.13-era rendered text verbatim once the tool
stopped touching it.

## Why

A tag fixed at the bottom of a region reads badly once the surrounding prose grows past it —
letting a view declare `top` or a landing spot next to the heading it belongs under is the
difference between a tag that reads as part of the document and one that reads as an
afterthought. Re-placing every tag on every write, rather than refusing whichever write would
have dropped one, means a document's seeded views are never something an author can lose by
mistake, and never something a flag has to opt into per view — every view the tool itself put on
a document stays there for good, at the place its declaration names.

Deleting a tag destroys the one thing a later `view add` cannot re-derive — whether the view was
ever placed on this document at all, and in what state — so a document only ever turns a view
off, never erases the fact that it belongs there. Where the tag sits is never at stake either
way, since every write re-places it at its view's declared position regardless of state. That
also keeps `sq check`'s job simple: a document that fails the exactly-once condition is a bug in
placement itself, never a state an author could have written.

A role, a skill's own definition, or a bundled per-item-type skill already has one validated place
where it is authored. Letting a body hold prose beside that same definition would give an agent
two sources for one thing, with no way to tell which one is current — refusing the write instead
of merging the two keeps the rendered definition as the only thing on the page.

## Scope

- A `position` field on a view declaration: `top`, `bottom` (default), or `after(<regex>)`
  against a Python `re` pattern, `MULTILINE` set, matched on the region's prose with every tag
  already stripped. A pattern that fails to compile is a spec-load error. A view name is
  restricted to a bare TOML key (`[A-Za-z0-9_-]+`, never `end`), enforced at load.
- A disabled state per tag (`sq:view:<name>:disabled`), recognised by the same marker machinery as
  the enabled form. The two verbs hang off the host, as every view verb does today
  (`sq <type> <n> view add|disable <name>`, `sq role <slug> view add|disable <name>`, `sq skill
  <slug> view add|disable <name>`): `view add` places or re-enables; `view disable` turns an
  enabled tag off or places a new one already off, and needs no gate. `view rm` is removed.
- One shared re-placement routine — read every tag and its state, strip, edit the prose, re-insert
  each at its view's position keeping its state, add any newly-seeded view enabled — used by
  `body` (replace and append), the bulk importer's body operation, `view add`/`view disable`, and
  the 0.14→0.15 migration's placement step alike.
- Same-state duplicates of one view collapse into a single tag on re-placement; conflicting states
  for one view refuse the write and name `view add`/`view disable` as the two ways to settle it.
  An undeclared view's tag goes to the bottom, after every declared view, keeping its relative
  order among other undeclared tags.
- The post-write and `sq check` condition: every view a document is seeded with (by its creation
  template, or by its role/skill's own classification) appears exactly once, counting both states
  together; no view name appears twice. Nothing is reported for a view the document isn't seeded
  with.
- A body write (replace or append) is refused, unconditionally and without `--force`, on any
  document whose role/skill classification names a declared view — a role, a permanently-system
  skill, or a per-item-type skill — naming that document's real authoring surface in the refusal.
  `view disable` stays available on these documents.
- The 0.14→0.15 migration's legacy-prose reclaim (already covering roles and permanently-system
  skills) is extended to per-item-type skills, and runs correctly across every pre-0.15 squad, not
  only ones migrated from the immediately preceding schema.
- The convergence machinery's now-unreachable non-strict path, its skip-reporting channel through
  `sq migrate up`/`sq sync`, and the tests that exist only to keep it reachable are removed.

## Acceptance

- A view declaring `position = "top"`, `"bottom"`, or `"after(<regex>)"` places its tag there on
  first creation and on every subsequent write; a pattern with no match falls back to `bottom`; a
  pattern that fails to compile is rejected at spec load.
- A replace or an append on any document re-places every tag the region already had, at its view's
  position, keeping each one's enabled/disabled state; a newly-seeded, previously untagged view is
  inserted enabled.
- A milestone's body can be replaced: the roll-up tag survives the replace at its position, and the
  new prose is not confined to appending after it.
- `view disable <name>` turns a tag off in place without removing it; `view add <name>` re-enables
  it or places it fresh; `view rm` no longer exists as a verb.
- Two same-state copies of one view's tag collapse to one on the next write; two conflicting-state
  copies refuse the write and name `view add` and `view disable`.
- `sq check` and the write-time check both report a document missing one of its seeded views'
  tags, or carrying one twice (in either state), and report nothing for a view the document is not
  seeded with.
- A body write is refused, replace and append alike, on a role, a permanently-system skill, and a
  per-item-type skill, `--force` included; the refusal names that document's real authoring
  surface; `view disable` still succeeds on the same document.
- A squad migrated from any pre-0.15 schema has every seeded view's tag placed once across roles,
  permanently-system skills, and per-item-type skills alike, and passes `sq check` clean
  afterward.
- `uv run sq check` is clean on this corpus.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 948 add-story "As a <role>, I want … so that …"`; track with `sq feature 948 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Every document's seeded views are derived, never declared

<!-- sq:story:US1:body -->
As an adopter, I want a document's seeded views computed automatically from its type and slug
alone — the creation template for an ordinary item, or the role/skill classification for a role,
a permanently-system skill, or a per-item-type skill — with no per-view flag to set, so a document
can never end up divorced from what creation already puts on it.

Acceptance: the seeded-view table applies uniformly — ordinary item from its creation template
(override-aware), role from `role_definition`, permanently-system skill from its own view, a skill
documenting a declared type from `item_skill`, a custom skill or a stale `sq-<type>` for an
undeclared type from none; a view dropped from `[selected]` seeds nothing anywhere; the
`ViewSpec.required` field is removed, with no override migration owed since it was never released;
the one helper that answers a document's seeded set is shared by the write path, `view
add`/`disable`, and `sq check`.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Every body write re-places view tags at their position

<!-- sq:story:US2:body -->
As the owner of any document — a milestone included — I want a body replace or append to keep
every existing view tag in place, at its declared position, rather than refuse the write or pin
new prose after the tag, so I can edit a document's prose without hunting for or losing what the
tool already put there.

Acceptance: replace and append both read every tag and its state, strip them, apply the prose
edit, then re-insert each at its view's position in declaration order, keeping its state, and add
any newly-seeded view enabled if it had no tag; a milestone's body accepts a replace, with the
roll-up tag surviving at its position rather than confining new prose to after it; two same-state
copies of one view's tag collapse to one on re-placement; a conflicting-state pair (one enabled,
one disabled) refuses the write and names `view add` and `view disable`; an undeclared view's tag
lands at the bottom, after every declared view's tag, keeping its relative order among other
undeclared tags; `--force` lifts neither the conflicting-state refusal nor the roster refusal
(US7); the bulk importer's body operation goes through the same routine as the single-item
command.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Views are disabled, never deleted

<!-- sq:story:US3:body -->
As an adopter who no longer wants a view's content rendered, I want to turn it off in place rather
than remove it, so I keep the option to turn it back on without re-declaring or re-placing
anything by hand.

Acceptance: `view disable <name>` (`sq <type> <n> view disable <name>`, or `sq role|skill <slug>
view disable <name>` on a role or skill) turns an enabled tag into `sq:view:<name>:disabled`, or
places a new disabled tag when the view had none, and needs no gate; disabling preserves the
tag's state and the fact that the view belongs on the document, never its location — every write
re-derives that from the view's declared position regardless of state; a disabled tag renders
nothing at read time and is invisible to the dangling-name and inapplicable-source checks; `view
add <name>` is the only way to re-enable a disabled tag, or to place the tag of a view the
document doesn't carry yet; `view rm` no longer exists as a verb; the standing repair sweep never
re-enables or rewrites a disabled tag.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — sq check and writes enforce one tag per seeded view

<!-- sq:story:US4:body -->
As anyone running `sq check`, I want every document checked for carrying each of its seeded
views' tags exactly once, in either state, with duplicates counted by view name regardless of
state, so a document can never silently end up missing a definition or rendering two of the same
one.

Acceptance: the same condition runs at the end of every write, before the commit, and inside `sq
check`'s tier-1 file scan; a document missing a seeded view's tag, or carrying one view's tag
twice (counting both states together), is reported at error level naming both remedies (`view
add`, `view disable`); nothing is reported for a view the document is not seeded with; a write
that would fail the post-write condition is refused and nothing is written — reachable only as a
placement bug, never as a state an author could produce.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Required flag retired: superseded by US1 and US7

<!-- sq:story:US5:body -->
Cancelled: `required` is retired as a per-view flag — every declared view's host set is now
derived unconditionally (US1), so there is nothing left to declare on the six bundled views. The
surviving half of this story, retiring the hardcoded role/system-skill write refusals, is
superseded by US7, which extends that refusal to append as well as replace.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Migration reclaims legacy roster prose; dead skip channel removed

<!-- sq:story:US6:body -->
As an adopter upgrading from any pre-0.15 squad, I want the 0.14→0.15 migration to place every
seeded view's tag over the 0.13-era rendered text on every role, permanently-system skill, and
per-item-type skill — not only the first two — so no bundled definition is left carrying stale
prose after the upgrade, and I want the now-unreachable non-strict convergence path removed rather
than kept alive by tests that only feed it.

Acceptance: the reclaim step's legacy-view set gains per-item-type skills, alongside roles and
permanently-system skills, under the same licence — classify by roster view name, replace a
marker-free non-empty region with the tag, skip marker-shaped content, never touch a custom skill;
the step places tags through the shared re-placement routine, so a tag-only or bottom-positioned
result is byte-identical to today's anchor; the reclaim runs correctly regardless of the migration
chain's own intermediate index state, including a squad migrated from schema v0.1 onward;
`_converge_body_tag`'s non-strict branch, `_strict_body_convergence`, `RepairResult.skipped` and
its CLI reporting, and the tests kept only to exercise that path are removed; a squad migrated
from any pre-0.15 schema passes `sq check` clean afterward.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — Roster bodies hold no prose

<!-- sq:story:US7:body -->
As anyone reading a role's, a permanently-system skill's, or a per-item-type skill's definition, I
want its body to hold only the tool's own rendering, never author-written prose beside it, so
there is exactly one place — the role or playbook overrides — where that definition is authored
and read.

Acceptance: a body write, replace or append, is refused unconditionally and without `--force` on
any document whose role/skill classification names a declared view; the refusal names that
document's real authoring surface — `.overrides/roles.toml`, or a project role's own override
file, for a role; the playbook overrides for a skill; `sq role <slug> show` and the skill
equivalent surface the same remedy from their empty-body hint; `view disable` still succeeds on
these documents, leaving them rendering an empty definition; the only way to author one of these
bodies by hand is to drop its view from `[selected]` first, which removes the document from this
rule.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — A view declares where its tag renders

<!-- sq:story:US8:body -->
As an adopter declaring a view, I want to say whether its tag lands at the top of a document, the
bottom, or right after a line I match with a pattern, so the tag reads as part of the document
instead of as an afterthought appended past everything else.

Acceptance: `position` accepts `top`, `bottom` (the default when omitted), or `after(<regex>)`;
`after(<regex>)` matches against the region's prose with every tag already stripped, using Python
`re` with `MULTILINE` set, and places the tag on its own line after the end of the first match,
falling back to `bottom` when nothing matches; a pattern that fails to compile is rejected at spec
load; several views resolving to the same position place their tags in declaration order; a view
name is restricted to a bare TOML key (`[A-Za-z0-9_-]+`) and must not be `end`, enforced at spec
load; `position` belongs to the view's declaration, never to any one document, so no per-document
location survives a body write.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->
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
- [2026-09-25T13:05:17Z] Nina Product:
  - Rewrote FEAT-948 for ADR-880's seventh amendment (`required` retired; views gain `position`;
    disable-not-delete; every body write re-places tags). Old-to-new story mapping for TASK-942's
    subtask remap:
    
    - US1 (rewritten): flag+host-derivation → unconditional seeded-view derivation (§1).
    - US2 (rewritten): replace refusal → the shared re-placement routine, fixes the milestone body
      (§4).
    - US3 (rewritten): append/view-rm scoping → `view add`/`view disable`, `view rm` retired (§3).
    - US4 (rewritten): required-tag check finding → exactly-once/no-duplicate check (§5).
    - US5 (Cancelled): bundled `required=true` declarations — no flag left to declare; its surviving
      half (hardcoded refusal retirement) moved to US7.
    - US6 (rewritten): convergence narrowing + migration move → migration now also reclaims
      per-item-type skills, dead non-strict channel deleted outright (§6, §7; folds in REV-964 F2/F5).
    - US7 (new): roster bodies (role/system-skill/per-item-type skill) refuse replace and append
      unconditionally (§8; REV-964 F7, option A).
    - US8 (new): `position` field — top/bottom/after(regex) (§2).
    
    @tech-lead please remap TASK-942's subtasks against this: anything against old US1-US4/US6 stays
    on the same story number (subject continuity); anything against old US5 needs re-pointing to US7
    or dropping if it only covered the flag declarations; new subtask coverage is needed for US7 and
    US8. @manager for visibility.
- [2026-09-29T09:29:10Z] Catherine Manager:
  - Done. TASK-942 delivered every story; REV-964 and REV-967 are Approved with all findings fixed and verified; the full suite passes (6265), pyright, ruff and sq check are clean. Accepted under the delegation for reviewed, non-visual work.
<!-- sq:discussion:end -->
