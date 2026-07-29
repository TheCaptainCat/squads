---
id: TASK-688
sequence_id: 688
type: task
title: 'VS Code: narrow the Roster view by status and hide archived'
status: Done
parent: FEAT-621
author: tech-lead
refs:
- BUG-687:depends-on
description: 'Give the Roster view the ability to narrow that Work Items has, in the
  dimensions a fixed-bucket tree actually has: hide archived entries and filter to
  one status, with visible active state.'
subentities:
- local_id: ST1
  title: Hide archived roster entries
  status: Done
- local_id: ST2
  title: Status filter on the Roster view
  status: Done
- local_id: ST3
  title: Visible filter state, and clear
  status: Done
- local_id: ST4
  title: Dev-host verification per increment
  status: Done
  assignee: op-pierre
created_at: '2026-07-29T08:55:21Z'
updated_at: '2026-07-29T12:46:09Z'
---
<!-- sq:body -->
Let a reader narrow the VS Code **Roster** view the way they can already narrow Work Items — hide
what is retired, and restrict to one status.

## What parity means here, and what it does not

Established by reading both surfaces rather than from the feature's summary. The Roster tree is not a
spec-driven hierarchy; it is three fixed buckets (Roles / Skills / Operators) that are already
collapsible. So the four affordances Work Items has do **not** map across one-for-one:

| Work Items has | Meaningful for the Roster? |
|---|---|
| **Show closed items** (hides non-open statuses) | **Yes — the real parity item.** `Archived` is a terminal status (`is_open("Archived")` is `False`, status role `retired`), so the existing hide-what's-finished semantics already have exactly the right meaning for roster items. An archived role currently sits in the list forever with no way to hide it. |
| **Filter by status** | **Yes.** "Show only Active roles", "find the Draft skill I left unfinished" — impossible today, and the roster has a real three-state lifecycle (`Draft → Active → Archived`). |
| **Group by type** | **No.** The tree is already grouped by type. This would be a toggle between the current shape and the current shape. |
| **Filter by type** | **Barely, and deliberately out of scope** — see below. |

**Filter-by-type is a non-goal, on purpose.** The three buckets *are* the type dimension, and they
collapse. A type filter would hide two folders the reader can already close, and its only real gain is
a flat single-type list instead of a folder to expand. That is a small win for a new command, a new
QuickPick, and a new piece of state to display and clear. Left out so the two affordances that matter
land first — and if Pierre wants it after seeing those, it is a clean addition on top rather than
something the design has to be reworked for.

So: **parity means the same ability to narrow, expressed in the dimensions this tree actually has —
not the same four buttons.**

## The state-visibility requirement, folded in

Whatever this adds must show when it is on. BUG-687 is open right now on exactly this: the Work
Items tree's `Group by type` and `Show closed items` render identically whether active or not, because
VS Code appears not to render a `toggled` state for icon-only actions in a view title's `navigation`
group — the manifest is already correct and the affordance simply may not exist by that route.

Ada is fixing that, likely by swapping the icon on state via two menu entries with opposite `when`
clauses. **Adopt whatever pattern that fix lands; do not invent a second one.** If it has not landed
when this starts, coordinate rather than guessing — two different state-affordance idioms in one
toolbar is worse than waiting.

The requirement stated plainly: after any increment here, a reader glancing at the Roster toolbar can
tell whether a filter is active without opening a menu.

## Built for live review

Pierre is reviewing from the dev host as this is built, so each subtask is independently visible and
checkable on its own, in order, and the body of each says what to look at. A first increment that puts
one working affordance in the tree is worth more than a complete implementation delivered at the end.

## Scope

- **VS Code only.** The TUI half of the parent feature is a separate matter — see the note on
  FEAT-621; there is no separate Roster surface in `sq ui` and its single filter screen already covers
  roster items.
- Not the Records view, which has the same gap (only `squads.refreshAll` is contributed to it) but is
  not this feature.
- No change to what the Roster tree *contains*, only to what it shows.
- TypeScript stays at 6.0.3 — typescript-eslint peer-caps below 6.1.

## Acceptance

- An archived role, skill or operator can be hidden and shown again from the Roster toolbar.
- The Roster view can be restricted to a single status, and cleared back.
- Both states are visible in the toolbar without opening a menu, using the same idiom as the Work
  Items tree after BUG-687.
- The Work Items and Records views are unaffected — their toolbars, state and behaviour unchanged.
- A roster with nothing archived and no filter set looks and behaves exactly as it does today.
- `npm run check` and `npm test` clean in `clients/vscode`, with the filter/predicate logic unit-tested
  vscode-free in `src/domain/` as the existing filter and tracker logic is.
- Verified on the Windows dev host per increment, not only at the end.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 688 add-subtask "<title>"`; track with `sq task 688 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Hide archived roster entries |  |
| ST2 | Done |  | Status filter on the Roster view |  |
| ST3 | Done |  | Visible filter state, and clear |  |
| ST4 | Done | op-pierre | Dev-host verification per increment |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Hide archived roster entries

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Hide-archived on the Roster view. First because it is the smallest thing that is visibly, obviously
working.

`Archived` is terminal — `is_open("Archived")` is `False`, status role `retired` — so this is the same
predicate the Work Items tree already applies for `Show closed items`, pointed at the Roster provider.
Reuse that predicate rather than testing for the literal string `"Archived"`: a project can rename or
add statuses through its workflow override, and the open/closed question is the spec's to answer.

Default: **hide** archived entries, matching Work Items' default of hiding closed items. That is a
visible change on any squad that has archived anything, which is the point — it should be obvious the
first time Pierre opens the view.

Contribute the toggle to `view/title` for `squadsMeta` only. Do not touch the `squadsTree` or
`squadsRecords` entries.

**State visibility is part of this subtask, not a follow-up.** Use whatever idiom BUG-687's fix lands
for the Work Items toggles — most likely two menu entries with opposite `when` clauses and distinct
codicons. If that has not landed yet, coordinate with Ada rather than inventing a second idiom.

**What Pierre should look at:** open the Roster view. Archive a role (`sq role <slug> …` moving it to
`Archived`), and confirm it disappears. Click the new toggle and confirm it comes back, and that the
toolbar button itself looks different in the two states. Nothing else in the view should move.

Acceptance:
- Archived roster entries are hidden by default and shown when toggled.
- The toggle's own appearance differs between states, using the Work Items idiom.
- The open/closed test comes from the spec, not a hardcoded status name.
- Only the Roster view's toolbar changes.
- The predicate is unit-tested vscode-free.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-07-29T09:29:38Z] Ada Typescript:
  - Hide-archived predicate reuses resolveRole(status).hidden (domain/statusRole.ts) — the same field the sq CLI's --all flag gates server-side (hidden_by_default), never the literal string 'Archived'. Default hidden; two-command icon-swap toggle (squads.toggleShowArchived/squads.hideArchived, context key squads.metaShowArchived) follows BUG-687's idiom exactly. Contributed to squadsMeta view/title only.
  - What to check in the dev host: open Roster, archive a role (sq role <slug> status Archived if available, or via workflow), confirm it disappears by default; click the toolbar toggle, confirm it reappears and the button's icon/title swap; confirm Work Items and Records toolbars are untouched.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Status filter on the Roster view

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Status filter on the Roster view.

A QuickPick over the statuses the roster types actually declare, restricting the tree to one status.
Follow `squads.filterByType`'s shape — it is the existing precedent for a filter QuickPick on a tree
view, including where it sits in the menu (`1_squads`, not `navigation`, so the toolbar does not fill
up with icons).

Source the status list from the spec, not a hardcoded list: read what the roster types declare so a
project that has customised the roster lifecycle gets its own statuses. The bundled set is
`Draft → Active → Archived`.

Two interactions to get right rather than discover on the dev host:

- **With hide-archived.** If the reader filters to `Archived` while archived entries are hidden, the
  tree would go empty — technically correct, and useless. Decide it deliberately: either selecting
  `Archived` implies showing archived, or the empty state says why it is empty. Either is fine; a bare
  empty tree is not. Record the choice at the call site.
- **Empty results generally.** Filtering to a status no roster entry has should say so, not render a
  blank panel that reads as "the roster is empty".

**What Pierre should look at:** filter to `Active` and confirm only active entries remain across all
three buckets; filter to `Draft` and confirm a half-finished skill shows up alone; then try `Archived`
and confirm the interaction above behaves the way it was decided rather than showing nothing.

Acceptance:
- The Roster view can be restricted to one status, sourced from the spec.
- The filter-plus-hide-archived interaction is handled deliberately and documented at the call site.
- An empty result explains itself.
- Buckets with no surviving entries either disappear or read clearly as empty — not as broken.
- The filtering logic is unit-tested vscode-free.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-07-29T09:30:46Z] Ada Typescript:
  - Status list sourced from sq workflow statuses --json (already fetched for statusRole join), not scoped per roster type — sq workflow types --json/roles --json expose no type->lifecycle->states mapping, and sq ui's own FilterScreen has the identical scoping (sorted(spec.statuses) over the whole spec, _tui/_filter.py) — so this mirrors an established precedent rather than inventing a narrower one. Means a status filter can genuinely match zero roster items (e.g. a decision-only status); tree renders 3 empty-but-labelled buckets plus the view description naming the filter, which reads as 'filtered, no matches' rather than broken.
  - Interaction decision: a status filter always overrides hide-archived (matches the sq CLI's own --status-reveals-hidden rule) — documented at the call site in domain/metaFilter.ts::matchesMetaFilter. Filtering to Archived shows archived entries even with the toggle off; the toggle's own on/off state is unchanged by this (it only matters again once the filter is cleared).
  - What to check in the dev host: filter to Active (all 3 buckets narrow); filter to Draft; filter to Archived with the toggle off and confirm archived entries show (not a blank tree).
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Visible filter state, and clear

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Make the Roster's filter state legible, and clearable.

Once two affordances exist, the reader needs to be able to see at a glance that the view is narrowed —
and get back to unnarrowed in one action.

**Active-state affordance.** Both the hide-archived toggle and the status filter must show when they
are on. The toggle follows BUG-687's idiom (icon swap). The status filter is a QuickPick, not a toggle,
so it needs its own signal — the Work Items tree's existing filter indicator is the precedent to
follow if it has one usable here; otherwise the view's description/message line is the cheap and
conventional place for "filtered: Active".

The requirement, restated because it is the one this feature must not repeat from BUG-687: a reader
glancing at the Roster toolbar can tell the view is narrowed **without opening a menu**.

**Clear.** A single action that returns the Roster to its default — status filter off, archived hidden.
Mirror `squads.clearFiltersAndGrouping`'s shape and menu placement; the Roster's version has no
grouping to clear, so name it for what it does rather than copying that command's title.

Note the asymmetry deliberately: default state is *hide archived*, so "clear" is not "show
everything". Clearing returns to the default, and if the reader wants archived entries visible that is
the toggle's job. Say so at the call site, because "clear filters" reading as "show all" is a
reasonable expectation to have to correct.

**What Pierre should look at:** with a status filter and the archived toggle both set, confirm the
toolbar makes both states obvious. Then clear, and confirm the view returns to exactly its
first-open appearance.

Acceptance:
- Both filter states are visible without opening a menu.
- One action returns the view to its default state.
- "Clear" is documented as returning to default, not to show-everything.
- The Work Items and Records toolbars are untouched.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-07-29T09:30:58Z] Ada Typescript:
  - Toggle's on/off state follows BUG-687's icon-swap pair (squads.toggleShowArchived/squads.hideArchived). The status filter has no icon pair to swap, so its state (and, once set, the toggle's) surfaces via the Roster TreeView's own .description — 'Filtered: <status>' takes priority, else 'Archived shown' when the toggle alone is on, else no description (default state) — a small grey label beside the view title, updated in extension.ts on every metaTreeDataProvider refresh.
  - Clear (squads.clearMetaFilter, 1_squads group, mirrors clearFiltersAndGrouping's placement) resets to the default — archived hidden, no status filter — not to show-everything; documented at the command's registration site in commands.ts.
  - What to check in the dev host: set both the toggle and a status filter, confirm the description text is visible without opening a menu; Clear Filter, confirm the view returns to its first-open appearance (no description, archived hidden).
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Dev-host verification per increment

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Assignee:** Pierre Chat
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Dev-host verification — the operator's machine, so an agent cannot close this.

Pierre is reviewing each increment live, so this subtask is the record of that rather than a single
pass at the end. Launch via the Windows `code` CLI with `--disable-extensions`, recompiling first — not
the WSLg Linux test binary, which renders poorly and is not the authoritative visual check.

Per increment, the check named in that subtask's body:

1. **Hide-archived** — archive a roster entry, confirm it vanishes; toggle, confirm it returns; confirm
   the button looks different in the two states.
2. **Status filter** — filter to `Active`, then `Draft`, then `Archived`; confirm each narrows
   correctly and that the archived-plus-hidden interaction behaves as decided rather than blanking.
3. **State visibility and clear** — with both set, confirm the toolbar makes it obvious; clear and
   confirm the view returns to its first-open appearance.

Across all three, watch two things the subtasks cannot assert for themselves:

- **The other two views are untouched.** Work Items and Records should look and behave exactly as
  before — same toolbar, same contents, same state after a reload.
- **It reads as one toolbar.** New affordances should look like they belong beside the existing ones,
  not bolted on. That is a judgement about appearance and only a person on the host can make it.

Record the result per increment on this ticket as it happens, with a screenshot for the toolbar states
— those are the part prose cannot settle. Anything that looks wrong goes here rather than being fixed
ad hoc, so the dev picks it up in the next increment.

Acceptance:
- Each increment verified on the Windows dev host as it lands, not batched at the end.
- Screenshots of the toolbar in default, filtered, and archived-shown states.
- Explicit confirmation that Work Items and Records are unaffected.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-07-29T12:46:08Z] Pierre Chat:
  - Verified on the stable dev host: the roster and records controls read and behave correctly.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T09:31:08Z] Ada Typescript:
  - Blocker for ST4's manual check, flagged rather than fixed (out of clients/vscode scope): sq role/skill/operator expose no CLI verb to change status at all — sq role <slug> --help only offers show/regen/rm (same for skill/operator), and the generic item 'status'/'update' subcommands (_cli/_items.py) aren't wired onto the roster's own Typer apps. There is currently no sq command to put a role/skill/operator into Archived (or any non-default status) to exercise the new hide-archived toggle or status filter live. Needs a python-dev follow-up (or a documented manual frontmatter edit for this one-off verification) before ST4 can be checked end-to-end.
- [2026-07-29T09:37:06Z] Pierre Chat:
  - The roster status/update CLI gap is deferred to 0.13, alongside FEAT-321, FEAT-642 and FEAT-644. Not fixing it in 0.12.3.
<!-- sq:discussion:end -->
