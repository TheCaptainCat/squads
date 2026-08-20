---
id: FEAT-642
sequence_id: 642
type: feature
title: 'Make read surfaces sub-entity-aware: mine, workload, inbox, JSON'
status: Done
author: product-owner
description: Route work by sub-entity assignee/mention; carry sub-entity discussion
  into JSON
subentities:
- local_id: US1
  title: 'mine: surface sub-entity-only assignments'
  status: Done
- local_id: US2
  title: 'workload: count sub-entity assignments'
  status: Done
- local_id: US3
  title: 'inbox: attribute hits to the sub-entity that matched'
  status: Done
- local_id: US4
  title: 'show --json: carry sub-entity discussion, incl. VS Code preview'
  status: Done
- local_id: US5
  title: standalone sub-entity show --json
  status: Done
created_at: '2026-07-24T07:28:33Z'
updated_at: '2026-08-03T14:39:22Z'
---
<!-- sq:body -->
A sub-entity (story/subtask/finding) carries its own `assignee` and its own discussion, but the
read surfaces treat it as second-class. `sq mine` and `sq workload` filter/bucket on the item's
own assignee only, so an actor assigned only a subtask (not its parent) is never routed that work.
`sq show --json` drops sub-entity discussion entirely, and there is no machine-readable surface
for a single sub-entity at any level — so a JSON-driven consumer, including the VS Code item
preview, can't see a decision recorded as a comment on a story or finding.

`sq inbox` is mention-driven, not assignee-driven, and already detects a mention placed inside a
sub-entity's discussion — it just can't say which sub-entity matched. This feature attributes that
hit to the sub-entity it came from; it does not turn inbox into an assignment queue.

Scope: make `mine` and `workload` match on sub-entity assignment as well as item assignment,
attribute `inbox` hits to the matched sub-entity, carry sub-entity discussion into `show --json`
(item-level and standalone), and render that discussion in the VS Code preview.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 642 add-story "As a <role>, I want … so that …"`; track with `sq feature 642 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | mine: surface sub-entity-only assignments |
| US2 | Done |  | workload: count sub-entity assignments |
| US3 | Done |  | inbox: attribute hits to the sub-entity that matched |
| US4 | Done |  | show --json: carry sub-entity discussion, incl. VS Code preview |
| US5 | Done |  | standalone sub-entity show --json |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — mine: surface sub-entity-only assignments

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As an actor assigned only a sub-entity (not its parent item), I want that work to show up in my
`sq mine` queue, so I don't lose track of it just because the parent belongs to someone else.

`sq mine <slug>` matches when the slug owns the item **or** owns one of its sub-entities. In
`--json` the item stays the row (a homogeneous array of item objects, additive-only) — a matched
sub-entity is never an array element in its own right; it lands as a new key on the item object
naming which sub-entity(ies) matched. The table names the matched sub-entities too, so a roll-up
row is never indistinguishable from a direct item assignment.

Default (non-`--all`) visibility follows whichever assignment matched, evaluated independently:

- The item-level match uses the item's own status, as today.
- A sub-entity-level match uses that sub-entity's own status.

The row shows if at least one matching reason is open. So: an open sub-entity assigned to the slug
keeps the row visible even when the parent item's own status is settled. Conversely, a settled
sub-entity assigned to the slug does not by itself keep the row visible when the parent isn't also
assigned to the slug and open — the slug's actual piece of work is done, so there's nothing there
for them to act on. `--all` bypasses this predicate exactly as it does for item-level matches today.

Operator slugs (`op-<slug>`) work identically to role slugs.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — workload: count sub-entity assignments

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As anyone reading `sq workload`, I want actors who own only sub-entities to appear with a count,
so workload isn't blind to subtask-level assignment.

Sub-entity assignment counts are published as their own additive columns/keys, separate from the
existing `open`/`closed`/`total`. Those existing columns keep meaning exactly what they mean today
— item counts, nothing folded in. An actor who owns both a parent item and one of its sub-entities
gets counted once in the item columns and once in the sub-entity columns; they are never merged
into a single number, which would double-count that actor and silently change what an
already-published column means.

Same open/settled derivation as the item counts, resolved through the spec rather than a hardcoded
status list. Roster-category items stay excluded, as they are today.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — inbox: attribute hits to the sub-entity that matched

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As an actor scanning my `sq inbox`, I want a hit inside a sub-entity's discussion to name which
sub-entity it matched, so I can tell an item-level mention from a mention on a specific
story/subtask/finding.

`inbox` stays mention-driven — it answers "who was called out", not "who owns this". It already
detects a mention placed inside a sub-entity's discussion; the gap is attribution, not detection.
Each hit gains an additive locator naming the matched region, reusing the vocabulary `sq search
--json` already publishes for this — `<kind>:<local_id>:discussion#<n>` — rather than inventing a
second spelling. An item-level mention keeps reporting without that locator, so the two are
distinguishable.

This story is attribution only. Turning `inbox` into an assignment queue — surfacing sub-entities
by who owns them rather than who was mentioned — is a different view with a different spec and is
explicitly out of scope here.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — show --json: carry sub-entity discussion, incl. VS Code preview

<!-- sq:story:US4:head -->
**Status:** 🟢 Done
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As a JSON-driven consumer — including the VS Code item preview — I want every sub-entity entry to
carry its discussion, so a decision recorded as a comment on a story, subtask or finding isn't
invisible outside the human-readable render.

Each `subentities` entry in `sq show <id> --json` and `sq <type> <n> show --json` gains an
additive `discussion` array, shaped like the item-level one (`{author, ts, body}`, same ordering),
generic across every sub-entity kind. Added unconditionally; `show --json` stays byte-identical
across `--raw`/`--comments`/`--full`.

The VS Code preview renders this per sub-entity pane, mirroring the existing item-level discussion
block (markup, escaping, fold behaviour): a comment appears with author and timestamp, a
comment-less sub-entity renders exactly as before, and a payload from an older `sq` with no
`discussion` key still renders — an absent or empty discussion folds away to nothing rather than
blanking the pane.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — standalone sub-entity show --json

<!-- sq:story:US5:head -->
**Status:** 🟢 Done
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
As a script or integration, I want `sq <type> <n> <kind> <k> show --json` to work, so I can read
one sub-entity as machine-readable JSON without fetching the whole parent item and filtering its
`subentities` array myself.

The command emits exactly the object shape that sub-entity's entry carries in the parent item's
`show --json` (including the `discussion` array), built from one shared construction path used by
both surfaces so the two shapes cannot drift apart. Available for every declared sub-entity kind,
with no per-kind branch; a nonexistent local id fails cleanly.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T09:37:08Z] Pierre Chat:
  - Scheduled for 0.13.
- [2026-07-30T07:57:44Z] Pierre Chat:
  - Next after FEAT-691 in 0.13, ahead of FEAT-644 and FEAT-321.
- [2026-08-03T07:50:43Z] Pierre Chat:
  - Scope this together with the missing sub-entity discussion on the machine-readable surfaces. Both are the same theme — sub-entities are second-class in the read surfaces — so one pass is cheaper than two and closes the webview gap at the same time.
- [2026-08-03T08:00:06Z] Olivia Lead:
  - Broken into TASK-729 (Python read surfaces: mine, workload, inbox attribution, sub-entity discussion in show --json, standalone sub-entity --json) and TASK-730 (VS Code preview rendering). Subtasks carry no story mapping because this feature has no stories declared — @product-owner, add them and I will map.
  - Three things this body leaves for you to settle, flagged in TASK-729 rather than guessed: whether a settled parent still shows in mine when my sub-entity is open (and the converse), whether sub-entity counts fold into workload existing columns or get their own, and whether inbox is meant to gain assignment semantics at all — it is mention-driven today and already detects sub-entity mentions, it just cannot name which sub-entity matched.
- [2026-08-03T08:04:53Z] Nina Product:
  - Ruling (a) - mine cross-status visibility: default (non --all) visibility follows whichever assignment matched, evaluated independently - item-level match uses the item own status, sub-entity match uses that sub-entity own status; the row shows if at least one matched reason is open.
  - Direction 1 - settled parent, open sub-entity assigned to the slug: shows. The slug still has open work (the sub-entity), and hiding the row because the parent happens to be settled would bury it.
  - Direction 2 (converse) - open parent, sub-entity assigned to the slug is settled, parent not itself assigned to the slug: does not show. The slug piece is done; the parent being open (someone elses work) is not a reason for it to sit in this slug queue. --all bypasses this predicate exactly as it does today.
- [2026-08-03T08:05:00Z] Nina Product:
  - Ruling (b) - workload granularity: separate additive columns, not folded into open/closed/total. Folding changes the meaning of columns already published as stable (they stop meaning item counts) and double-counts an actor who owns both a parent and its sub-entity - clarity and compatibility both point the same way.
  - Ruling (c) - inbox scoping: confirmed, attribution only. Inbox stays mention-driven; this feature names which sub-entity a hit matched using the sq search locator vocabulary, and does not add assignment semantics to inbox. An assignment-queue inbox would be a different view with its own spec - not this feature.
- [2026-08-03T08:05:16Z] Nina Product:
  - @tech-lead stories US1-US5 are in, mapped to the read surfaces in scope; rulings (a)/(b)/(c) above.
- [2026-08-03T12:49:09Z] Pierre Chat:
  - Design conclusion following from the loop-hygiene question: sq mine should display mentions as well as assignments. Being mentioned is a reason an item needs you, so mine is the one view answering what needs me — whether because it is assigned or because someone called me out. This completes rather than reverses the inbox ruling in this feature: inbox stays mention-driven and does not become an assignment queue; mine gains the mention axis. Consequence for the orchestration loop: one command per agent rather than two, and sq mine becomes the honest check for whether an agent is already loaded before it is spawned.
- [2026-08-03T12:52:37Z] Pierre Chat:
  - Reversing the previous note: do not change mine to carry mentions. The two views answer different questions at different granularities — mine is a queue of item rows, inbox is the matching comment lines with their text — so folding mentions into mine would duplicate items across both views while losing nothing that inbox already does better. Instead, have agents run both on spawn. Neither command changes.
- [2026-08-03T14:39:16Z] Catherine Manager:
  - All five stories delivered and closed: TASK-729 (mine/workload/inbox/show --json, review REV-734 Approved) and TASK-730 (VS Code preview, verified visually by op-pierre in the extension dev host). BUG-727 and BUG-728 Verified.
<!-- sq:discussion:end -->
