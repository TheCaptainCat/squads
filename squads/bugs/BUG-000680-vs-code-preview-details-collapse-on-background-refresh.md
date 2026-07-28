---
id: BUG-680
sequence_id: 680
type: bug
title: 'VS Code: preview details collapse on background refresh'
status: InProgress
author: qa
severity: medium
refs:
- BUG-679
created_at: '2026-07-28T07:32:45Z'
updated_at: '2026-07-28T14:45:34Z'
---
<!-- sq:body -->
Observed (Pierre): sub-entity bodies collapse back on refresh; expectation is that collapsible
elements stay open across a refresh.

Established from code inspection:

The three activity-bar trees (Work / Roster / Records) are NOT affected. Every refresh —
manual button or the file-watcher's auto-refresh — fires a full-root `onDidChangeTreeData`,
but `ExpansionTracker` (`clients/vscode/src/domain/expansionTracker.ts`, unit-tested) already
records `onDidExpandElement`/`onDidCollapseElement` and replays it in `toTreeItem`, so node and
group expand/collapse state on all three trees survives a full-root refresh today. This part
already works and needs no fix.

The real break is a different surface: the item-preview webview (`itemPreviewManager.ts`).
`refreshOpenPreviews()` — invoked only by the `.squads.json` file watcher's `onIndexChanged`
(`extension.ts`), never by any of the three manual tree-refresh buttons — re-renders the open
panel's article/sub-entities/discussion HTML from scratch and `postMessage`s it to the
webview. The webview's inline script (`previewDocument.ts`'s `clientScript`) patches it in with
a plain `innerHTML` swap of the `#sq-subentities`/`#sq-article`/`#sq-discussion` mount points.

The freshly-built HTML for a sub-entity body (`buildSubEntityHtml`) and for each graph diagram
(`buildGraphsHtml`'s per-diagram `<details class="sq-graph">`) never carries an `open`
attribute, and nothing captures which `<details>` were open in the DOM before the swap — there
is no id-based identity or state map for these nodes at all, unlike the tree's
`ExpansionTracker`. So any sub-entity body or graph fold the reader had opened collapses back
to its default-closed state on the next patch. This is a DOM-region-replace-with-no-state-
capture bug, not an element-identity problem: `<details>` open/closed state isn't keyed by id in
the first place, and the trees prove the ids-plus-tracking pattern already works elsewhere in
this codebase when it's actually applied.

The two wrapper sections ("Sub-entities (N)", "Discussion (N)") are unaffected — both hardcode
`open` on every render regardless of prior state, so they don't visibly collapse. The elements
that do collapse are: individual sub-entity body folds (`sq-subentity-body` — matches what
Pierre saw directly), and, per code, the two per-diagram graph folds (`sq-graph` — not directly
observed, but going through the exact same swap with the same missing state capture).

Trigger, as coded today: only the automatic `.squads.json`-watcher refresh of an already-open
preview panel (e.g. a background `sq` write while the panel is open) reaches this path. None of
the three manual tree-section refresh buttons touch an open preview at all right now (see the
companion bug on refresh scope) — so the collapse Pierre saw traces to the background/auto-
refresh path, not a click on a tree's own refresh icon, even though both surface under the
umbrella of "refresh."

Expected: a sub-entity body (and, per code, the per-diagram graph folds) that a reader had
opened stays open across a preview patch refresh.

Scope: confined to the item-preview webview's `<details>` regions. The three activity-bar trees
already preserve expand/collapse state correctly across every refresh, manual or automatic —
"all collapsible" is broader than what's actually broken.

Not verified: a visual repro in a running dev host — no GUI session available for this filing;
based on inspection of the message-passing code and the absence of any open-state capture/
restore around the `innerHTML` swap.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-28T07:32:56Z] Pierre Chat:
  - The subentity bodies collapse on refresh, all collapsible should stay open on refresh
- [2026-07-28T07:59:28Z] Pierre Chat:
  - Confirmed the trigger: the webview, refreshing while an agent was running sq — so the watcher was firing on the index changing. Not a click on any refresh button.
- [2026-07-28T07:59:29Z] Catherine Manager:
  - Trigger confirmed by the operator, which makes this routine rather than an edge case: agents mutate the index continuously in this repo's normal workflow, so any preview left open collapses its sub-entity bodies and graph folds repeatedly through a session — exactly when someone is watching a preview to follow an agent's work.
<!-- sq:discussion:end -->
