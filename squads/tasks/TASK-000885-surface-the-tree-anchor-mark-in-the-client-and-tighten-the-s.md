---
id: TASK-885
sequence_id: 885
type: task
title: Surface the tree anchor mark in the client and tighten the skew canary
status: Done
author: tech-lead
assignee: typescript-dev
priority: medium
refs:
- BUG-879:fixes
- TASK-877:depends-on
description: The VS Code client maps tree JSON through a closed field list, so the
  cycle-anchor mark never reaches the display model; the skew canary's superset key
  assertion cannot catch it either.
created_at: '2026-09-02T13:05:22Z'
updated_at: '2026-09-02T15:26:51Z'
---
<!-- sq:body -->
## What is wrong

Bare `sq tree` will begin rendering a cyclic component anchored at a cycle member, with the
anchor **marked**, in the rendering and in `--json`. The mark is not decoration: it is the
entire reason the fabricated root is acceptable, because an unmarked anchor asserts a root
nobody wrote.

The VS Code client maps tree JSON through a closed field list. QA traced all four hops:
`sqAdapter.ts::getTree` fetches the bare form for the sidebar; `isSqTreeNode` accepts unknown
keys rather than rejecting them; `domain/treeMapping.ts::mapNode` reads a fixed set of fields
into a `DisplayNode`, which is a closed interface whose per-node visual state is exactly
`blocked`, `closed`, `hidden` and `colorIntent`; `getTreeItem` receives only a `DisplayNode`.
The second rendering path is the same — `domain/graphDiagrams.ts::subtreeNodeLabel` builds each
mermaid label from a fixed template. So a new field is safe on the wire and also invisible: the
disclosure holds in the terminal and silently does not hold in the client, which is the one
place the ruling's own justification stops surviving.

The targeted form (`itemPreviewManager.ts`, which passes an explicit id) already renders a
cyclic component, and its root is the one the reader asked for rather than an invention. The
bare form used by the sidebar is the surface at issue.

## The canary is part of this, not a follow-up

`clients/vscode/test/canary/skewCanary.test.ts` asserts node keys with `expect.arrayContaining`,
a superset assertion, so a tenth key passes. The one test whose whole job is to notice that
`sq`'s JSON and the client's model have drifted apart stays green through exactly this drift,
and no `treeMapping` unit test can assert on a field the display model has no room for. That is
why this does not ship red later — it ships green and wrong.

Fixing it belongs in this work rather than behind it: someone will be in that file, the
assertion is a two-line change, and leaving a drift test that cannot detect drift in place while
relying on it is worse than not having it.

## Sequencing

This depends on the core anchor work. There is nothing to mark until the flag exists, and the
field's name and JSON semantics are not knowable before it lands. The canary half cannot be
split off and done early either: tightening the key assertion to an exact set would go red the
moment the core emits its tenth key, so both halves land together, after the core.

## What to change

The visual treatment is the client owner's call and is deliberately not chosen here.

- `SqTreeNode` gains the flag as an optional member, so an older `sq` that omits it keeps
  parsing — the treatment `badges` already has.
- `DisplayNode` gains somewhere to carry it; it has no slot today.
- `mapNode` forwards it, and the row rendering and/or tooltip surfaces it. `subtreeNodeLabel`
  surfaces it in the mermaid subtree, so both rendering paths disclose rather than one.
- The canary's key assertion becomes exact rather than a superset, so an unmodelled key added by
  a future `sq` fails the test that exists to catch it. Decide there, and state in the test, what
  a *missing* flag should mean once the core emits it.

Not in scope, and not assumed: whether the client should also disclose the dropped edge that
closes the loop back to the anchor, or surface anything about the underlying corpus condition
beyond the mark itself.

## Acceptance

Each fails before the change:

1. Given tree JSON whose node carries the anchor flag, the mapped display node carries it too —
   a mapping-level test, which is impossible today because the display model has no field for it.
2. The rendered sidebar row for an anchored node is distinguishable from an ordinary root, and
   the mermaid label for one is distinguishable from an ordinary node. Both paths, not one.
3. A node without the flag renders exactly as it does today, and JSON from an older `sq` that
   omits the key still parses.
4. The canary fails when the live `sq tree --json` emits a node key the client does not model.
   Demonstrate the failure against a fixture carrying an unmodelled key, so the assertion is
   shown to bite rather than assumed to.
5. The client test suite passes against the core's real output, not a hand-written fixture
   alone — the canary's value is that it reads live output.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 885 add-subtask "<title>"`; track with `sq task 885 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T13:08:45Z] Olivia Lead:
  - Scoped off BUG-879. Held at Draft, and the reason is not that the work is unclear — it is that
    the anchor field's name and JSON semantics do not exist until TASK-877 lands, so a dev starting
    now would be coding against an invented key.
    
    The canary is in this task rather than a follow-up, and it cannot be pulled forward either:
    tightening the key assertion from `arrayContaining` to an exact set would go red the moment the
    core emits its tenth key. Both halves land together, after 877.
    
    The visual treatment is the client owner's call and is not chosen in the body. What is required
    is that both rendering paths disclose — the sidebar row and the mermaid label — since
    `subtreeNodeLabel` is the second place a reader meets a fabricated root.
    
    @typescript-dev yours, but do not start until TASK-877 lands; I will move this to Ready then.
    @qa verification needs the core change in place first.
- [2026-09-02T14:03:20Z] Ada Typescript:
  - Implemented, both surfaces. All changes are inside `clients/vscode/`; nothing under `src/`, `tests/`, `docs/` or the changelog was touched.
    
    **How the flag reaches each surface.** New `src/domain/treeAnchor.ts` owns every string a reader can meet the fabrication through, so the two surfaces cannot drift into two different claims; the wording mirrors the terminal's own marker, which the two languages cannot share as a constant. `SqTreeNode` gains `anchor?: boolean` (optional, the treatment `badges` already has — an older `sq` omitting it reads as `false`, never "unknown"), and `isSqTreeNode` now rejects a present-but-non-boolean `anchor` while still tolerating its absence. `DisplayNode` gains `anchor: boolean` as a **required** member rather than an optional one, so the compiler forced all seven construction sites to decide; the four list/roster/records/synthetic-node sites answer `false` with a one-line reason, since a flat row is not a root at all. `mapNode` forwards it, and `describeNode` was rewritten from a ternary to an append so `blocked` and the anchor tag combine instead of one hiding the other (they are independent on the core side and co-occur). Row reads `Open · unassigned · cycle anchor`, tooltip gains `Cycle anchor: not a real root; see sq check`. `subtreeNodeLabel` appends the full bracketed marker, deliberately not the row's two-word tag: a mermaid node has no tooltip to fall back to.
    
    **Anchor is deliberately kept out of `emphasisForNode`.** It is an independent state that co-occurs with blocked/hidden/colour, so folding it into that precedence chain would make one fact hide another. It is disclosed in the row's own text instead of competing for the single icon colour.
    
    **Canary, before and after.** Before: `expect(Object.keys(node)).toEqual(expect.arrayContaining([…nine…]))`. After: a named `TREE_NODE_KEYS` set of ten and `assertExactTreeNodeKeys`, sorting both sides because key *order* is not part of the contract, only the key set. The doc comment states what each direction of failure means — an extra key is an unmodelled field, a missing key is usually a stale `sq` on PATH.
    
    **Proof it now bites, two ways.** By construction: four new tests, outside the sq-gated `describe` so they run without `sq` at all, assert the helper throws on a node carrying `path_only` and on one missing `anchor` — and assert `isSqTreeNode` accepts both, which is the point (the guard cannot be what catches drift). Live: running the canary with the older `sq 0.12.1` that sits on my PATH turns the real tree case red with `- "anchor"` in the diff, where the old superset assertion passed.
    
    **Pre-change failure.** The four new mapping/mermaid tests were written first and run red before the implementation: `expected undefined to be true` on the mapped `anchor`, `'Ready · unassigned · blocked'` vs the expected `… · cycle anchor`, and the mermaid label missing its marker. No existing test was weakened; two existing tooltip fixtures and one `DisplayNode` helper gained the new required field.
    
    **End to end against real output, not a fixture.** Staged a three-item parent cycle in a scratch squad (frontmatter + `sq repair`, since the write door refuses a cycle), then fed the real bare `sq tree --json` through the client mapping and the mermaid builder. Live payload carried `"anchor": true` on `BUG-2`; the row rendered `Open · unassigned · cycle anchor` with the tooltip line, and the mermaid node rendered `BUG-2: Ring 0 (Open) [cycle anchor — not a real root; see sq check]`, with the cycle's other two members untouched. Canary also passes 23/23 against a real `sq 0.14.0`.
    
    **Gates.** `npm run typecheck`, `npm run lint` (clean, no OOM this time), `npm run format:check`, `npm test` 624/624, `npm run test:canary` 23/23 against 0.14.0. `uv run sq check` clean at exit 0, and `git status` shows nothing modified under `src/`, `tests/`, `docs/` or `CHANGELOG.md`. The VS Code extension-host lane (`npm run test:e2e`) was not run — it needs a display and downloads Electron.
    
    **One correction to the brief.** `buildSubtreeMermaid` is only ever fed the *targeted* form today (`itemPreviewManager` passes an explicit id, and the core never sets `anchor` on an explicitly rooted tree), so the mermaid disclosure is unreachable through the current wiring — correct and required, but defensive rather than presently visible. The sidebar row is the surface a reader actually meets a fabricated root on today. Worth knowing before anyone tries to reproduce the mermaid half by hand.
    
    **Left as-is, flagged not fixed.** The `sq graph --json` and `sq list --json` key assertions in the same canary file are still `arrayContaining` supersets with the same blind spot. Out of scope here (the tree node is where the drift lands), but the same one-line change would close them.
    
    @qa ready for verification — the reproduction recipe for a real anchored tree is in the paragraph above. @reviewer for the client diff.
<!-- sq:discussion:end -->
