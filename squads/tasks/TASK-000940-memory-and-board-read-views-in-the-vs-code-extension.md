---
id: TASK-940
sequence_id: 940
type: task
title: Memory and board read views in the VS Code extension
status: Done
parent: FEAT-690
author: tech-lead
assignee: typescript-dev
refs:
- TASK-939:depends-on
subentities:
- local_id: ST1
  title: sqAdapter fetches and guards for the memory JSON surfaces
  status: Done
  story: US1
- local_id: ST2
  title: Eager memory children under Roster identities
  status: Done
  story: US1
- local_id: ST3
  title: Open a memory entry body from the Roster tree
  status: Done
  story: US1
- local_id: ST4
  title: Team board webview panel behind one command
  status: Done
  story: US2
created_at: '2026-09-14T12:14:27Z'
updated_at: '2026-09-15T07:44:24Z'
---
<!-- sq:body -->
The TypeScript half: per-role memory nested under the extension's Roster tree, and the team
board as a single webview panel behind one command. Read-only, no write path.

Unlike `sq ui`, the extension reaches everything through `sq --json` subprocess calls, so its
depth depends on what the CLI exposes: the count + summary level needs no CLI change at all,
the staleness signal needs `created_at` on `sq memory <role> list --json`, and the
drill-to-body needs `sq memory <role> show <slug> --json`, which does not exist today. Build
each level only once its CLI surface is there — a "select entry, nothing opens" interaction is
worse than no interaction.

The board needs nothing new from the CLI: `sq board list --json` already returns `n`, `id`,
`author`, `posted_at`, `until` and the full `body` inline.

## Files

- `clients/vscode/src/types.ts` — the memory row and memory detail shapes.
- `clients/vscode/src/sqAdapter.ts` — type guards + fetches, following the existing
  `getList` / `getWorkflowRaw` shapes and their `SqOutcome` handling.
- `clients/vscode/src/domain/metaView.ts` — `itemToLeaf` currently always sets
  `children: []`; that is the line this changes.
- `clients/vscode/src/metaTreeDataProvider.ts` — the eager per-identity fetch, alongside the
  existing catalog fan-out in `refresh()`.
- `clients/vscode/src/domain/displayNode.ts` — a node kind for a memory entry.
- `clients/vscode/src/itemPreviewManager.ts` — a board panel slot mirroring
  `activeWorkflowPanel`, rendered through the existing markdown-to-HTML path.
- `clients/vscode/src/commands.ts`, `clients/vscode/src/commandIds.ts`,
  `clients/vscode/package.json` — the board command and its menu entry.
- `clients/vscode/test/`.

## Design constraints

**TypeScript version is pinned.** `clients/vscode` is held at TypeScript 6.0.3 because
typescript-eslint — the type-aware strict lint gate — peer-caps at `<6.1.0`. Do not bump it,
and do not weaken the lint layer to move it.

**A memory node is not an item.** `DisplayNode.itemId` is what tree selection opens as an item
preview; a memory node must carry `null` there (the same treatment synthetic group and error
nodes already get) and route elsewhere, so selecting one never spawns `sq show` on a
non-existent id. Check the selection wiring in `extension.ts` / `commands.ts`, not just the
node shape.

**The identity's slug is already in hand.** `SqListItem.slug` on a roster row is the role slug
the memory pool is keyed on (`manager`, `tech-lead`, `op-pierre`) — no extra lookup. Roles and
operators have notebooks; skills do not, so the Skills bucket gains no children.

**Fetch eagerly, and only for what is shown.** The view's job is comparing hygiene across the
whole roster at a glance, so children come down with the Roster refresh rather than on
expansion. `showArchived` / `statusFilter` already narrow the item list before bucketing — fetch
only for the identities that survive that, so a filtered view does not pay for hidden ones.
Fan the calls out alongside the existing catalog `Promise.all`.

**A failed per-identity fetch degrades locally.** One identity whose memory fetch fails must
not blank or break the Roster tree; it loses its children and says so, the same graceful
degradation the catalog fetches already get (`NO_LABELS`, `NO_ROLES`, and friends).

**Board panel tier.** One command, one owned panel slot, reusing the markdown-to-HTML machinery
the item preview already has — the same tier as the existing workflow cheatsheet. No new tree,
no activity-bar slot, no toolbar of its own.

**Keep the domain layer vscode-free.** Anything worth unit-testing (the parent-node label, the
child ordering, the age formatting, the notice list shaping) belongs under `src/domain/` so it
runs under vitest with no VS Code host, matching how `metaView` / `listView` / `markdown` are
already split from their thin providers.

## Acceptance criteria

- Every role and operator node in the Roster tree shows its memory count before expansion; a
  role with an empty pool reads as zero rather than as a missing signal. Skill nodes are
  unchanged.
- Once the CLI carries `created_at`, the same node also shows how long ago its most recent
  entry was written, and expanding it lists entries oldest-touched first, each with slug,
  summary and age. Until then the children are summary-only and ordering is stable and stated.
- Selecting a memory entry never attempts to open it as an item preview.
- Once `sq memory <role> show <slug> --json` exists, selecting an entry opens its full body.
  Before that, the entry is not presented as openable.
- A Roster refresh with a filter applied issues memory fetches only for the identities that
  survive the filter.
- An identity whose memory fetch fails still renders, without children, and the failure is
  surfaced rather than swallowed; the rest of the tree is unaffected.
- A `Squads: Open Team Board` command opens a single webview panel listing current notices
  newest-first with author, posted-at, expiry where set, and the body rendered as markdown.
  Re-invoking it reveals and refreshes the existing panel instead of opening a second.
- Notice bodies, memory summaries and memory bodies containing HTML-significant characters are
  escaped, not injected.
- `npm run check` and `npm test` are clean in `clients/vscode`.
- New vitest coverage for the domain-layer pieces above. Name tests by behaviour; no ticket ids
  in source or filenames.

## Sequencing

The memory work here depends on the Python task's two `sq memory` JSON additions. The board
panel does not depend on anything and can land first if that is convenient.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 940 add-subtask "<title>"`; track with `sq task 940 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sqAdapter fetches and guards for the memory JSON surfaces

<!-- sq:subtask:ST1:body -->
Add the memory row and memory detail shapes to `clients/vscode/src/types.ts` and their type guards plus fetches to `clients/vscode/src/sqAdapter.ts`, following the existing `getList` shape and its `SqOutcome` classification. Tolerate an older `sq` that omits `created_at` the same way `badges` and `anchor` are already tolerated — absent is valid, present-and-wrong-type is a rejection. The detail fetch is only useful once the CLI ships `sq memory <role> show <slug> --json`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Eager memory children under Roster identities

<!-- sq:subtask:ST2:body -->
`itemToLeaf` in `clients/vscode/src/domain/metaView.ts` always sets `children: []`; that is the line this changes. Give role and operator leaves a count on the label, entries as children with slug, summary and age, ordered oldest-touched first. Skills keep no children. The fetch fans out in `metaTreeDataProvider.refresh()` alongside the existing catalog `Promise.all`, and only for identities that survive `showArchived` / `statusFilter` — a filtered view should not pay for hidden ones.

A memory node carries `itemId: null`, the treatment synthetic group and error nodes already get, so tree selection never spawns `sq show` on a non-existent id; verify the selection wiring in `extension.ts` and `commands.ts`, not just the node shape. One identity whose fetch fails loses its children and says so; the rest of the tree is unaffected. Label text, child ordering and age formatting are pure functions under `src/domain/` so they run under vitest with no VS Code host.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Open a memory entry body from the Roster tree

<!-- sq:subtask:ST3:body -->
The drill-in step, and the one piece that genuinely waits on the CLI: it needs `sq memory <role> show <slug> --json`, which does not exist today. Until that lands, a memory entry is not presented as openable — a select-and-nothing-happens interaction is worse than none. When it lands, open the full body through the markdown-to-HTML path the item preview already uses, with the summary, timestamp and tags in the header. HTML-significant characters in a body are escaped, not injected.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Team board webview panel behind one command

<!-- sq:subtask:ST4:body -->
One command (`squads.openBoard`, contributed in `clients/vscode/package.json` with a menu entry) opening a single owned webview panel, mirroring the `activeWorkflowPanel` slot in `clients/vscode/src/itemPreviewManager.ts`: re-invoking reveals and refreshes the existing panel rather than opening a second. Notices newest-first with author, posted-at, expiry where set, and the body rendered through the existing markdown-to-HTML machinery. No new tree, no activity-bar slot, no toolbar of its own. Needs no CLI change — `sq board list --json` already returns every notice body inline.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-14T13:11:08Z] Ada Typescript:
  - All 4 subtasks landed, inside `clients/vscode` only. TypeScript stayed pinned at 6.0.3; the type-aware lint layer was not touched or weakened.
    
    **Files changed**
    - `src/types.ts` — `SqMemoryListRow`, `SqMemoryDetail`, `SqBoardNotice`.
    - `src/sqAdapter.ts` — shape guards + `getMemoryList`/`getMemoryShow`/`getBoardList`.
    - `src/domain/memoryView.ts` (new) — eligibility, sort (oldest-first, slug tiebreak), age humanizing, glance/tooltip text, per-entry `DisplayNode`s, `renderMemoryEntryHtml`.
    - `src/domain/boardView.ts` (new) — newest-first sort, markdown build, `renderBoardHtml`.
    - `src/domain/displayNode.ts` — added `memoryRef` (role+entry slug) to `DisplayNode`; `itemId` stays `null` on every memory node. Exported `escapeTooltipMarkdown` for reuse.
    - `src/domain/metaView.ts`, `src/domain/listView.ts`, `src/domain/recordsView.ts`, `src/domain/treeMapping.ts` — wired `memoryRef: null` into every existing `DisplayNode` literal; `metaView.ts` threads a `MemoryRenderContext` (pools + `now`) into Role/Operator leaves.
    - `src/metaTreeDataProvider.ts` — eager per-identity `sq memory <role> list --json` fetch, scoped to slugs surviving the current filter (`memoryEligibleSlugs`), staged after the catalog round trip since eligibility needs `statusRoles`/`roleCatalog`.
    - `src/treeItemRendering.ts` — a memory node's click wires `squads.openMemoryEntry`, never `squads.openItemPreview`.
    - `src/itemPreviewManager.ts` — two new single-slot panels (`openBoard`/`renderBoard`, `openMemoryEntry`/`renderMemoryEntry`), same reuse-or-create shape as the existing workflow panel.
    - `src/commands.ts` — registers `squads.openMemoryEntry` (internal, tree-click only) and `squads.openBoard`.
    - `package.json` — `squads.openBoard` command + Work Items title-bar menu entry (`$(megaphone)`, after the workflow cheatsheet button).
    - `test/memoryView.test.ts`, `test/boardView.test.ts` (new), `test/metaView.test.ts`, `test/displayNode.test.ts` (extended).
    
    **Gates (real output)**
    - `npm run check` (typecheck + lint + format:check): clean.
    - `npm test`: 663 passed, 0 failed (was 624 before this task; +39 new).
    
    **Falsification** (break → red → restore → green, each verified directly):
    1. Reversed `sortMemoryEntries`'s comparator → red on ordering assertions in `memoryView.test.ts`. Restored → green.
    2. Made a failed pool synthesize a fake child instead of `[]` → red in both `memoryView.test.ts` and the `metaView.test.ts` integration test asserting a failed identity renders childless. Restored → green.
    3. Widened `MEMORY_ELIGIBLE_TYPES` to include `skill` → red on the "collects only role/operator slugs" test. Restored → green.
    4. Set `itemId` on a memory leaf instead of `null` → red at both the unit level (`memoryChildren`) and the `buildMetaView` integration level (the "never opens an item preview" test). Restored → green. This is the invariant `treeItemRendering.ts`'s click routing depends on.
    5. Bypassed `renderMarkdownToHtml` for the memory body (raw string concat) → red on the HTML-escaping test (`<script>` survived unescaped). Restored → green.
    6. Flipped the board sort direction → red on both `sortNoticesNewestFirst` and `buildBoardMarkdown` ordering tests. Restored → green.
    
    `treeItemRendering.ts` itself imports real `vscode` and isn't unit-tested under plain vitest — same pre-existing convention as the sibling `itemId` routing branch (only the extension-host e2e tier covers that file). Its correctness here rests on the domain-layer invariant above (falsified in #4) plus code review of the if/else-if branch order.
    
    **Not done / deferred**
    - `sq board list --json`'s CLI quirk (exits 1 on a partial/degraded read even though it already wrote valid JSON) means a degraded board read surfaces as a full panel failure rather than a partial listing — pre-existing CLI behavior, not something this task's scope covers or regresses.
    - No change to `test/canary/skewCanary.test.ts` — the real `sq` on PATH in this environment is a stale global install (schema v0.11) that predates this feature and isn't the dev tree, so I couldn't validate against it, and canary coverage wasn't in TASK-940's acceptance criteria.
    
    `sq check` is clean. Task and parent feature status left untouched, as directed.
    
    @manager
- [2026-09-14T13:12:34Z] Catherine Manager:
  - Verified as authoritative gate: extension typecheck + eslint (--max-warnings 0) + prettier clean; vitest 663 passed / 0 failed across 34 files; TypeScript pin intact at ^6.0.3. Scope confirmed clean — the diff touches clients/vscode only, the Python half is byte-identical to what TASK-939 left. Held at InReview rather than Done: visual surface, op-pierre eyeballs it in the dev host before it closes.
- [2026-09-15T07:44:21Z] Pierre Chat:
  - Looked at the dev host: the memory and board surfaces look good. Visual sign-off given.
<!-- sq:discussion:end -->
