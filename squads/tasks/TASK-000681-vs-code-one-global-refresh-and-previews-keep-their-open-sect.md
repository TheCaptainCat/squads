---
id: TASK-681
sequence_id: 681
type: task
title: 'VS Code: one global refresh, and previews keep their open sections'
status: Done
author: tech-lead
refs:
- BUG-679:fixes
- BUG-680:fixes
description: Every refresh action refreshes all three trees plus open previews through
  one command, a preview keeps its open folds across a refresh, and the preview gains
  an in-content refresh action left of the nav arrows.
subentities:
- local_id: ST1
  title: One global refresh command, all callers routed through it
  status: Done
- local_id: ST2
  title: Capture and replay preview fold state
  status: Done
- local_id: ST3
  title: In-content refresh action left of the nav arrows
  status: Done
- local_id: ST4
  title: Dev-host verification of both behaviours
  status: Done
  assignee: op-pierre
created_at: '2026-07-28T08:04:21Z'
updated_at: '2026-07-29T08:26:19Z'
---
<!-- sq:body -->
Make "refresh" mean one thing in the VS Code extension: every refresh action refreshes all three
trees **and** any open preview panels, and a preview keeps the sections the reader had open.

Fixes BUG-679 and BUG-680.

## Why these are one task, not two

They look separable — wiring three commands together, versus capturing `<details>` state — and they
were filed separately. But Pierre's addition to BUG-679 couples them: a global refresh now *includes*
open previews, and BUG-680 is what happens to a preview when it refreshes.

Ship BUG-679 alone and the reported annoyance gets **worse**. Today the three tree buttons don't
touch an open preview at all, so clicking one never collapses anything; the collapse only happens
when the file watcher fires. After a global refresh, every click collapses every open sub-entity body
and graph fold in every open preview. A fix that trades three clicks for a collapsed preview is not
an improvement — BUG-680 is a precondition for BUG-679's new behaviour being worth having, not a
neighbour of it.

They also share the function (`refreshOpenPreviews` is what 679 must start calling and what 680 must
fix), the file, and the dev-host verification session — and that session is on the operator's
machine, the scarcest resource here. Two tickets means two rounds of it.

## 1. One global refresh

The behaviour already exists, in exactly one place: `extension.ts`'s `.squads.json` watcher handler
calls all three providers' `refresh()` plus `previewManager.refreshOpenPreviews()`. No manual command
does the equivalent — `squads.refreshTree`, `squads.refreshMeta` and `squads.refreshRecords` each
refresh only their own provider.

So the shape is extraction, not invention: **one command that refreshes all three trees and every
open preview**, with every entry point routing through it — the three view-title buttons, the new
in-content preview action, and the watcher handler. One definition of "refresh everything", four
callers.

Decisions to make explicitly rather than leave to the diff:

- **Keep the three command ids** (`squads.refreshTree`/`refreshMeta`/`refreshRecords`) bound to their
  view-title buttons, or collapse them to one id contributed to all three views? Keeping them is
  less churn and keeps each view's `when` clause simple; collapsing them makes the shared behaviour
  obvious in `package.json`. Either is fine — pick one, say why in the commit, and do not leave two
  of them wired one way and one the other.
- **Command titles are user-visible** in the Command Palette. "Refresh Tree" that refreshes
  everything is a lie; retitle whatever survives so the palette entry matches what it does.
- The watcher handler must call the same command rather than keeping its own copy of the four calls,
  or the two definitions drift the next time something is added to a refresh.

## 2. A preview keeps its open sections

`refreshOpenPreviews()` rebuilds the sub-entities / discussion / graph HTML and swaps it in with a
plain `innerHTML` assignment. Nothing captures which `<details>` were open, so they all revert to
their rendered default.

What actually collapses, per the filing: individual sub-entity body folds (`sq-subentity-body`) and
the two per-diagram graph folds (`sq-graph`). The two wrapper sections ("Sub-entities (N)",
"Discussion (N)") hardcode `open` on every render, so they are unaffected — "all collapsible
elements" is broader than what is broken, and a fix that only restores the wrappers would fix
nothing.

**The trees already solve this**, and their solution is the model: `domain/expansionTracker.ts`
records expansion by stable id and replays it on the next render, deliberately kept vscode-free so
the tracking logic unit-tests without an extension host. Do the same for the webview's folds — the
same shape, the same testability property, and preferably a shared abstraction if the two turn out to
want the same thing rather than two trackers that drift.

Note the ids have to be stable across a refresh for replay to work at all. Sub-entity folds key
naturally off the sub-entity's local id; the graph folds need whatever identifies a diagram. If an
element has no stable id today, giving it one is part of this work.

## 3. A refresh action on the preview, left of the nav arrows

**The nav arrows are not contributed commands, and this is the thing to know up front.** There is no
`editor/title` menu contribution for them — `package.json`'s `menus` block contains only the three
`view/title` entries for the trees. `squads.previewBack`/`previewForward` appear only under
`keybindings` (`alt+left`/`alt+right`). The arrows Pierre sees are rendered **inside the webview
page**: `.sq-nav-toolbar` / `.sq-nav-buttons` / `.sq-nav-button`, with clicks delegated via
`[data-sq-nav]` in `domain/previewDocument.ts`.

`domain/previewMessages.ts` records why, and it is not an accident to undo: VS Code's
`editor/title/navigation` menu "doesn't reliably surface inline buttons for a plain
`createWebviewPanel`, confirmed by screenshot", so the in-page toolbar is the primary surface.

Consequences for this work:

- **No `navigation@N` ordinal is involved.** "Left of the nav arrows" is markup order inside
  `.sq-nav-buttons` — prepend the button. Placement is the easy part.
- **The action cannot be a contributed command with an icon.** It has to be an in-content button that
  posts a message the extension host handles by invoking the global refresh command — the same
  pattern `NavigateHistoryMessage` already uses, so there is a template: a message type in
  `previewMessages.ts`, its parser, and a branch in the panel's `onDidReceiveMessage`.
- **The button lives inside the content it refreshes.** Confirm the delegated click handler still
  works after the swap rather than assuming it does — the delegation is on the document, so it should
  survive, but a refresh button that works once and then goes dead is the obvious failure here.
- Style it as a sibling of the existing nav buttons rather than a new visual language; the toolbar
  already has hover and disabled states, and this button needs no disabled state.

## Out of scope

- **Any change to TypeScript's version.** `clients/vscode` is held at 6.0.3 deliberately, because
  typescript-eslint — the type-aware strict gate — peer-caps below 6.1. Do not touch it.
- **Auto-refresh cadence or watcher behaviour.** The watcher already does the right thing; this only
  makes the manual path match it.
- **Scroll position, tab selection, or any other preview state** beyond `<details>` open state. If
  those turn out to be lost too, file them rather than widening this.

## Acceptance

- Clicking the refresh button on any of the three sections refreshes Work, Roster and Records, and
  every open preview panel.
- The in-content refresh action sits immediately left of the back/forward buttons and fires the same
  global refresh; it still works when clicked repeatedly, after the content it lives in has been
  swapped.
- A reader-opened sub-entity body stays open across a refresh — manual, in-content, or watcher-driven.
  Same for a graph fold.
- Sections the reader had *closed* stay closed; the fix restores prior state, it does not open
  everything.
- A preview for an item whose sub-entities changed since the last render behaves sensibly: folds that
  still exist keep their state, and a fold for a removed sub-entity does not linger in the tracker.
- The watcher handler and every button route through one refresh definition; no caller keeps its own
  list.
- Command Palette titles describe what the commands now do.
- `npm run typecheck`, `npm run lint` (max-warnings 0) and `npm test` clean in `clients/vscode`, with
  the tracking logic unit-tested without an extension host, as `expansionTracker.ts` is.
- Verified in a running dev host — see the manual step. Both bugs were filed from code inspection
  with the on-screen behaviour explicitly unverified, so this is the one thing that closes them.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 681 add-subtask "<title>"`; track with `sq task 681 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — One global refresh command, all callers routed through it

<!-- sq:subtask:ST1:body -->
One global refresh, four callers.

The behaviour already exists in `extension.ts`'s `.squads.json` watcher handler, which calls all three
providers' `refresh()` plus `previewManager.refreshOpenPreviews()`. Extract that into a single command
and route every entry point through it: the three view-title buttons, the watcher handler, and (from
the sibling subtask) the in-content preview action.

The watcher must call the command rather than keep its own copy of the calls — otherwise there are two
definitions of "refresh everything" and the next thing added to one will be missed by the other. That
is the whole point of the extraction; a version where the watcher still has its own list has not
fixed anything structural.

Two decisions to make explicitly and record in the commit:

- **Keep three command ids or collapse to one?** Keeping `squads.refreshTree`/`refreshMeta`/
  `refreshRecords` bound to their own views is less churn and keeps each `when` clause simple;
  contributing one id to all three `view/title` entries makes the shared behaviour visible in
  `package.json`. Either is defensible. What is not: two wired one way and the third the other.
- **Retitle whatever survives.** The titles show in the Command Palette, and "Refresh Tree" for a
  command that refreshes three trees and every open preview is a lie the palette tells the user.

Order the work so a preview refresh is not made worse before it is made better: the fold-state fix is
the sibling subtask, and this change is what starts firing preview refreshes from a button. If they
land separately, land that one first.

Acceptance:
- One function/command defines "refresh everything"; the three buttons and the watcher all call it.
- No caller retains its own list of providers to refresh.
- Command Palette titles match the new behaviour.
- Clicking any section's refresh button visibly refreshes all three sections and every open preview.
- `npm run typecheck` / `npm run lint` (max-warnings 0) / `npm test` clean in `clients/vscode`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Capture and replay preview fold state

<!-- sq:subtask:ST2:body -->
A preview keeps the folds the reader had open, across every refresh.

`refreshOpenPreviews()` rebuilds the sub-entities / discussion / graph HTML and swaps it in with a
plain `innerHTML` assignment. Nothing captures which `<details>` were open, so every fold reverts to
its rendered default.

**What actually collapses**, and what does not: individual sub-entity body folds (`sq-subentity-body`)
and the two per-diagram graph folds (`sq-graph`). The two wrapper sections ("Sub-entities (N)",
"Discussion (N)") hardcode `open` on every render and are unaffected — so a fix that only handles the
wrappers fixes nothing visible. Work from the elements that regress, not from the phrase "all
collapsible".

**Model it on the trees**, which already solve this correctly: `domain/expansionTracker.ts` records
expansion by stable id and replays it on the next render, and is deliberately kept vscode-free —
plain ids in, plain ids out — so the tracking logic unit-tests with no extension host. Keep that
property; it is why the tree side has real coverage.

If the webview's needs turn out to be the same shape, prefer sharing the abstraction over a second
tracker that drifts from the first. If they differ, say how, so the next reader knows the duplication
is deliberate.

**Stable ids are the precondition.** Replay is impossible without them. Sub-entity folds key
naturally off the sub-entity's local id; the graph folds need whatever identifies a diagram. If an
element has no stable id today, adding one is part of this work, not a follow-up.

**Prune what no longer exists.** A preview refreshed after an item's sub-entities changed must not
carry tracked state for a removed fold — `ExpansionTracker` has a prune step for exactly this and it
is the part most likely to be skipped.

Restore *prior state*, not "everything open": a fold the reader deliberately closed must stay closed.

Acceptance:
- A reader-opened sub-entity body stays open across a refresh; so does a graph fold.
- A closed fold stays closed.
- Folds for removed sub-entities are dropped from tracking rather than accumulating.
- The tracking logic is unit-tested without an extension host.
- The capture happens before the swap and the replay after it, with no visible flash of collapsed
  content in between if that is avoidable.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — In-content refresh action left of the nav arrows

<!-- sq:subtask:ST3:body -->
A refresh action on the preview itself, immediately left of the back/forward buttons.

**Read this before looking for a menu contribution: there isn't one.** `package.json`'s `menus` block
contains only the three `view/title` entries for the trees. `squads.previewBack`/`previewForward`
appear solely under `keybindings` (`alt+left`/`alt+right`). The arrows are rendered **inside the
webview page** — `.sq-nav-toolbar` / `.sq-nav-buttons` / `.sq-nav-button`, clicks delegated through
`[data-sq-nav]` in `domain/previewDocument.ts`.

`domain/previewMessages.ts` records why, and it is a deliberate decision not to revisit here: VS
Code's `editor/title/navigation` menu "doesn't reliably surface inline buttons for a plain
`createWebviewPanel`, confirmed by screenshot", so the in-page toolbar is the primary surface. Do not
attempt to contribute this as an `editor/title` button on the assumption that the arrows are there.

So:

- **Placement is markup order** inside `.sq-nav-buttons` — prepend. No `navigation@N` ordinal, no
  menu `group`, no `when` clause. This is the easy part.
- **The action is a message, not a command invocation from the page.** Add a message type in
  `previewMessages.ts` with its parser, and a branch in the panel's `onDidReceiveMessage` that invokes
  the global refresh command — the same round trip `NavigateHistoryMessage` already makes. Follow that
  pattern rather than inventing a second one.
- **The button lives inside the content it refreshes.** Verify it still works when clicked twice in a
  row, after its own container has been swapped. The delegation is on the document so it should
  survive, but "works once then goes dead" is the obvious failure mode and it is invisible in a unit
  test.
- **Style it as a sibling** of the existing nav buttons, reusing their hover treatment. It needs no
  disabled state — unlike the arrows, which are disabled at the ends of history.

Acceptance:
- The action renders immediately left of the back/forward buttons and reads as part of the same
  toolbar.
- Clicking it performs the same global refresh as a tree section's button.
- It still works on the second and third click, after the content has been swapped.
- The message type has a parser and is handled the same way the existing nav message is; no new
  message-passing pattern is introduced.
- No `editor/title` menu contribution is added.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Dev-host verification of both behaviours

<!-- sq:subtask:ST4:body -->
Manual verification in a running dev host — the operator's machine, so an agent cannot close this.

It is not ceremony here: **both bugs were filed from code inspection with the on-screen behaviour
explicitly unverified**, and every claim in them about what the user sees is an inference. This step
is what actually closes them.

Launch via the Windows `code` CLI with `--disable-extensions`, recompiling first — not the WSLg Linux
test binary, which renders poorly and is not the authoritative visual check.

What to exercise:

1. **Global refresh from each section.** Click the refresh button on Work, then Roster, then Records
   in turn. Each should visibly refresh all three, not just its own.
2. **Global refresh reaches previews.** With a preview open, click a tree section's refresh — the
   preview should update.
3. **The in-content action.** Confirm it sits immediately left of the back/forward arrows and looks
   like part of the same toolbar rather than bolted on. Click it several times in a row.
4. **Folds survive, per trigger.** Open a sub-entity body and a graph fold, then refresh three ways:
   a tree button, the in-content action, and a watcher-driven refresh (run any `sq` write against the
   board while the panel is open — the trigger Pierre originally hit). The folds stay open in all
   three.
5. **Closed stays closed.** A fold the reader closed is still closed after a refresh.
6. **A changed item.** Add or remove a sub-entity while a preview of that item is open, then refresh —
   surviving folds keep their state and nothing lingers for the removed one.

Record the result on this ticket, with a screenshot for the toolbar placement — that one is a
judgement about appearance and prose cannot settle it.

Acceptance:
- All six checks exercised on the Windows dev host and the result recorded on this ticket.
- A screenshot of the preview toolbar showing the new action's placement.
- Anything that looks wrong is recorded here rather than fixed ad hoc, so the dev picks it up.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-07-28T15:23:35Z] Pierre Chat:
  - Dev-host check on the Windows host: the button is present, placed and styled correctly beside the nav arrows, and clickable. Folds stayed expanded across a watcher-driven refresh.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-28T08:05:08Z] Olivia Lead:
  - One task, fixing both bugs — and the reason is a dependency, not convenience. Today the three tree buttons don't touch an open preview, so clicking one never collapses anything; the collapse only fires on the watcher. Land BUG-679's global refresh alone and every click starts collapsing every open sub-entity body and graph fold — trading three clicks for a collapsed preview makes Pierre's original complaint worse. BUG-680 is a precondition for 679's new behaviour being worth having. They also share refreshOpenPreviews(), the file, and the dev-host session, which is the scarce resource.
  - Answer to the toolbar question, and it inverts the concern: the nav arrows are NOT contributed commands. package.json's menus block has only the three view/title tree entries; previewBack/previewForward appear solely under keybindings. The arrows are rendered inside the webview page (.sq-nav-toolbar / .sq-nav-buttons / [data-sq-nav] delegation in domain/previewDocument.ts), and previewMessages.ts records why — VS Code's editor/title/navigation menu 'doesn't reliably surface inline buttons for a plain createWebviewPanel, confirmed by screenshot'. So: no navigation@N ordinal, placement is markup order (prepend). The catch is elsewhere — the action can't be a contributed command, it must post a message the host handles (the NavigateHistoryMessage pattern), and the button lives inside the content it refreshes, so it must survive its own swap. 'Works once then goes dead' is the failure mode, and it's invisible to a unit test.
  - Global-refresh shape is extraction, not invention: extension.ts's watcher handler already calls all three providers plus refreshOpenPreviews(). Two decisions left explicit rather than to the diff — keep three command ids or collapse to one, and retitle whatever survives since 'Refresh Tree' in the Command Palette would be a lie. The watcher must call the shared command rather than keep its own copy. ST4 is dev-host verification assigned @op-pierre: both bugs were filed from code inspection with on-screen behaviour explicitly unverified, so it is what actually closes them.
- [2026-07-28T14:45:36Z] Catherine Manager:
  - Dispatched to Ada for 0.12.3. Both bugs close together — the global refresh is only an improvement if previews keep their open sections, otherwise every click collapses them.
- [2026-07-28T15:08:49Z] Ada Typescript:
  - ST1-ST3 implemented and gates clean (compile/typecheck/lint/format/npm test/npm run test:canary).
  - ST1: collapsed the three refresh commands into one squads.refreshAll (title "Refresh All"), all three view/title entries now point at it. Orchestration extracted to a pure domain/refreshAll.ts (structural Refreshable/PreviewRefreshable interfaces, no vscode import) so it's unit-tested with fakes, not inline in the command callback. The watcher and the new in-content button both invoke the command by id (src/commandIds.ts) rather than each keeping a copy.
  - ST2: reused ExpansionTracker (same class the trees use) per open panel. Sub-entity body folds are keyed by local_id, the two graph folds by fixed ids 'children'/'refs' -- both now carry data-sq-fold-id and a real open attribute. The webview reports toggles via a new capture-phase 'toggle' listener (native toggle doesn't bubble) -> ToggleFoldMessage -> tracker.setExpanded. Tracker resets on any navigation to a different item (local_id isn't globally unique) and prunes against the fresh sub-entity/graph id set on every successful patch render -- skipped on a failed fetch so a transient error doesn't wipe tracked state.
  - ST3: refresh button prepended inside .sq-nav-buttons (markup order, no menu contribution, per the ticket's framing). Posts a RefreshMessage (same round trip as NavigateHistoryMessage) -> host executes squads.refreshAll. Delegation is on document, same mechanism the nav arrows already rely on.
  - Falsified both behaviours (break/restore, see my reply to the dispatcher for verbatim output): dropped the preview call from refreshAll -> refreshAll.test.ts failed; zeroed the open attribute in buildGraphSection and buildSubEntityHtml -> previewDocument.test.ts failed on the fold-restore assertions for both graph and sub-entity folds. All three restored and green.
  - Not verified by me: the button surviving a real content swap in a live webview, and the toolbar's visual placement/hover-styling -- that's ST4, on the dev host.
  - ST4 (@op-pierre) is the only remaining open item; task stays InProgress until that's recorded.
- [2026-07-28T15:16:45Z] Catherine Manager:
  - Dev-host verification in progress: checking the in-content refresh button, its survival across a content swap, and fold preservation on all three refresh triggers.
- [2026-07-28T15:22:44Z] Pierre Chat:
  - The in-content refresh button is a railguard, not a routine control: auto-refresh normally handles everything, and I only reached for a manual refresh once when the watcher failed. No visual feedback on click is acceptable for that role — the indication is the stale content updating.
<!-- sq:discussion:end -->
