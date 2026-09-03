---
id: FEAT-690
sequence_id: 690
type: feature
title: See memory and board in the extension and sq ui
status: Draft
author: product-owner
refs:
- EPIC-316
- MILE-836:targets
description: Read-only oversight views for per-role memory (hygiene audit) and the
  team board in both browse clients
subentities:
- local_id: US1
  title: Memory hygiene-oversight view (sq ui first, extension once list --json carries
    created_at)
  status: Todo
- local_id: US2
  title: Team board view (both clients, low cost, no named urgency — sequence after
    memory)
  status: Todo
created_at: '2026-07-29T10:03:25Z'
updated_at: '2026-09-01T08:05:48Z'
---
<!-- sq:body -->
Surface the team's two CLI-only knowledge surfaces — per-role **memory** and the team **board** —
as read views in both browse clients (the VS Code extension and `sq ui`), without adding any
write path.

## The job memory is actually for

The brief behind this is not "a human wants to look something up" — it's oversight: agents are
sloppy about memory upkeep, and today nobody notices a stale, wrong, duplicated, or contradicting
entry — or a role whose notebook should have grown from a session's work and didn't — because
seeing that requires deliberately running `sq memory <role> list` per role in a terminal, which
nobody does as a matter of habit. That reframes what "good" looks like:

- **Overview and comparison beat deep reading of one entry.** Sloppiness shows up as a pattern
  across entries (three near-duplicate summaries, a role with zero entries after weeks of active
  work, an entry nobody has touched in a month) — not usually inside a single entry read in
  isolation. A design optimized for "select one memory, read its body" would miss the actual job.
  Reading one full body is still useful, but as a *second step* after something at the overview
  level looks off — not the primary interaction.
- **Metadata matters as much as content.** Entry count per role, and how long ago each entry was
  last touched, are hygiene signals in their own right, independent of what any entry says.

## What `list --json` actually returns (checked, not assumed)

`sq memory <role> list --json` today returns only `slug`, `filename`, `description` (the
summary) — no `created_at`. That rules out "the staleness signal is already free" — it isn't from
the CLI's JSON surface. But it's a *shallow* gap, not a missing feature: `Service.memory_list()` —
the in-process call, source of the CLI's own data — already returns a full `MemoryEntry` per
entry, `created_at` included (`src/squads/_memory/_model.py`); the CLI command handler
(`_cli/_memory.py::list_memories`) hand-picks three fields into its `--json` branch and drops the
rest. `show` (not `--json`-able at all) is the only place `created_at` reaches a human today, and
only one entry at a time. This asymmetry drives the whole recommendation below.

## Recommendation

**Memory first, with staleness/count visible at a glance across the whole roster; board second,
and I'm not going to manufacture urgency for it that wasn't given.**

**Memory — shape.** Nest memory as children of each **Role** and **Operator** node in the
existing Roster tree/group (not Skill — skills carry no notebook). This is still the right
structural home: a memory literally is that role's own notebook, and Roster already has one node
per role/operator with `slug` already in hand from the listing both clients already fetch
(`SqListItem.slug` / `Item.slug`) — no extra lookup to know whose notebook is whose.

What changes from a naive "expand to see, click to read" tree is the fetch and default-visibility
policy, because the job here is comparison, not lookup:

- **Fetch eagerly, not lazily, as part of the Roster refresh.** A lazy per-node fetch optimizes for
  "the human opens one role's branch to look something up" — exactly the shape this isn't. Roster
  size is small (roles + operators, typically well under 20 identities), so eagerly firing one
  `sq memory <slug> list` per identity (extension: N small subprocess calls; `sq ui`: N in-process
  directory reads, effectively free) is cheap enough to buy "see the whole roster's hygiene at
  once" instead of "expand every node by hand before you can compare anything."
- **Show the glance-level signal on the role/operator node itself**, before anyone expands it:
  entry count, and (once the CLI gap below is closed) how long since the most recent entry. A role
  active for weeks with a `(0)` next to its name is the single most useful thing this feature
  produces, and it costs nothing beyond the eager fetch already described.
- **Expanding a node lists its entries as children**, each showing slug + summary (already
  available) and age (once the CLI gap is closed) — this is the within-role comparison step, and
  it's exactly where a human eyeballing short, punchy summaries (already the house convention for
  memory entries) spots the duplicate or the contradiction, without opening anything.
- **Sort children oldest-touched first**, not alphabetically, once age is available — staleness
  should be the default reading order, not something you have to notice yourself.
- **Opening one entry to read its full body is the deepest, most detail-only step** — the "I
  noticed something, now let me confirm it" move, not the primary interaction. `sq ui` can do this
  today with zero CLI change (below). The extension cannot yet, and that specific gap is now
  correctly sized as secondary, not blocking.

**Memory — CLI dependency, sized precisely.** There are two different-sized gaps here, and they
gate different amounts of value:

1. **Small, additive: put `created_at` into `sq memory <role> list --json`.** The data already
   exists on every `MemoryEntry` the service returns; this is exposing a field, not building
   anything new. This alone unlocks the count+staleness overview — the primary oversight job — for
   the extension. Without it, the extension's memory branch can still ship (count + summaries), just
   without the age signal that makes "stale" visible rather than merely "old, maybe."
2. **Larger, separate: `sq memory <role> show <slug> --json` doesn't exist** (exits 2 today). This
   gates only the secondary "open one entry, read its full body" step in the extension.

**`sq ui` needs neither.** It runs in-process against `Service`, which already exposes
`memory_list()` (summary + `created_at`, right now) and `memory_show()` (full body, right now).
The TUI can ship the complete experience — overview, staleness sort, and drill-to-body — with no
CLI change at all. That makes it the obvious first slice.

**Read-only boundary — and an honest caveat.** Noticing a bad entry is the goal; deleting or
rewriting it is `sq memory forget` / a fresh `sq memory <role> add`, both mutations, both out of
scope for either client today. Naming this plainly rather than blurring it: a read-only oversight
view is real value — it turns an invisible problem into one a human runs into during ordinary
browsing, which is the actual behavior change — but it's honestly partial. Spotting the stale entry
in the UI still means dropping to a terminal to act on it. That's worth building anyway (visibility
is the precondition for anyone ever fixing anything), but a write path (`forget`/`add` from either
client) is the natural follow-on this surfaces, not a bar this feature clears on its own.

**Board — no comparable named problem, said plainly.** The brief that motivated memory ("agents
are sloppy with upkeep") doesn't extend to the board — I have no equivalent evidence of missed
notices being a live pain, and I'm not going to invent one just because both were asked about in
the same request. The board is still worth building, on its own (much weaker) merits: it's a
small, flat, already-fully-buildable read (`sq board list --json` returns every notice's full body
inline — no fetch-detail gap, no CLI dependency at all, on either client), and a human is more
likely to see a "read this before you start" notice inside a client they're already looking at
than by remembering to run a CLI command. But sequence it after memory, not alongside it.

**Board — shape.** A dedicated small surface, not a tree branch, on both clients — a notice has no
`category` (work/records/roster) and isn't an `Item`, so it doesn't fit either tree's existing
grouping machinery without bending it to a shape it wasn't built for:

- **`sq ui`**: a modal `Screen`, peer to the existing `FilterScreen`/`SearchScreen`, opened by a
  keybinding, listing notices newest-first with author/posted/expiry/body.
- **Extension**: one command (`Squads: Show Board`), opening a single lightweight webview panel —
  the same tier of surface `Squads: Show Workflow` already uses for the workflow cheatsheet: one
  command, one static-ish panel, no activity-bar slot, no new tree, no toolbar. The activity bar
  already carries three trees; a fourth is the most expensive way to show the least-structured,
  least-urgent data of the two.

## Alternatives considered and rejected

- **A dedicated cross-role "memory audit" table/view, separate from Roster.** Tempting given how
  much the comparison framing matters — but rejected: default-expanding Role/Operator nodes in the
  Roster tree (with the glance-level count+age already on the parent label) gets the same
  "see the whole roster's hygiene at once" outcome for no new view, no new fetch path, and it's the
  same tree a human already opens to look at team composition — which is conceptually where "is
  everyone's notebook in good shape" belongs. Flagging the tension honestly: if default-expanded
  memory children make the Roster tree feel noisy for its ordinary day-to-day browsing use, a
  separate compact audit view is the fallback — worth watching for once this ships, not something
  to pre-build speculatively.
- **Lazy-load memory children on node expansion** (my first instinct before the oversight
  reframing). Rejected once the job became "compare across the whole roster": lazy loading
  optimizes for single-role lookup, which is a real but secondary use, at the cost of the primary
  one (you'd have to expand every node by hand before any comparison is possible). Roster size is
  small enough that eager costs little.
- **A dedicated "Memory" tree/activity-bar view.** Rejected on cost: most roles carry a handful of
  entries; a whole new `TreeDataProvider` + activity-bar icon + toolbar is a lot of chrome for less
  content than one Roster bucket already holds, and it would separate memory from the roster
  identity it belongs to for no benefit the default-expansion approach doesn't already give.
- **Board nested inside an existing tree** (e.g. a synthetic bucket atop Work Items). Rejected: a
  notice isn't a work item, isn't a record, and isn't roster — bending an existing category to fit
  it is the same forced-symmetry move that produced a false premise in a feature reviewed earlier
  this release. It gets its own small, dedicated surface instead.
- **Building the extension's drill-to-body memory view now, against the missing `show --json`.**
  Rejected — a dead-end "select entry, nothing opens" interaction. This step is explicitly
  secondary now anyway; sequence the CLI flag whenever it's convenient, don't block the overview
  slice on it.
- **A write path** (`sq board post` / `sq memory add`/`forget` from either client). Out of scope by
  design — neither client mutates anything today, and named above as the honest, real follow-on
  this feature surfaces rather than solves.
- **Proposing board with equal urgency to memory just because both were asked about together.**
  Rejected per the brief above — memory has a named, felt problem behind it; board doesn't, and
  pretending otherwise would blur the one piece of information that actually settles priority.

## What this costs

- **`sq ui` memory-under-roster (overview + drill-to-body):** extends `_tree.py`'s tree-building
  for Role/Operator leaves (they've never had children before — `metaView`'s TS equivalent,
  `itemToLeaf`, always sets `children: []`, and the TUI's roster leaves are the same shape) with an
  eager `svc.memory_list()` call per identity, a glance-level count+age on the parent label, and a
  lightweight body view for the drill-in step (a memory has no sub-entities/discussion, so the
  existing three-tab `ReaderPanel` shape is the wrong fit for it as-is — needs its own small
  reader). No CLI dependency.
- **`sq ui` board screen:** one new modal `Screen`, one keybinding — same tier as `SearchScreen`.
  No CLI dependency.
- **Extension memory-under-roster (overview only, no CLI change needed beyond the small one):**
  extends `metaTreeDataProvider.ts`/`domain/metaView.ts` for eager per-node children instead of the
  current always-`children: []` leaves, a new `sqAdapter.ts` type guard + fetch for
  `sq memory <slug> list --json`, N extra subprocess spawns per Roster refresh (bounded by roster
  size). The count+summary level ships as soon as this lands; the age/staleness signal needs the
  small `created_at` CLI addition; the drill-to-body step needs the larger `show --json` addition
  and should simply wait for it rather than being half-built.
- **Extension board panel:** one new command + one new webview render path, reusing the
  markdown-to-HTML machinery the item preview panel already has; no new tree, no activity-bar
  cost, no `package.json` view/toolbar entries. No CLI dependency.

## Priority read

Build in this order: **(1) `sq ui` memory overview + drill-to-body — ships today, zero CLI
change, and is the direct answer to the named problem. (2) The small `created_at` addition to
`sq memory <role> list --json`, unlocking the extension's memory overview (count + staleness,
no body yet). (3) Extension memory-under-roster overview, once (2) lands. (4) `sq ui` board
screen and extension board panel — cheap, useful, no CLI dependency, but no named urgency behind
them either, so they land after memory, not alongside it. (5) `sq memory <role> show <slug>
--json`, whenever convenient — it only gates the extension's secondary drill-to-body step, which
was never the primary job here.** This isn't a "skip it" call for either piece — both are worth
building — but memory is the one with a real, stated problem behind it, and the honest ranking
reflects that rather than treating "the operator asked about both in one sentence" as evidence
they're equally urgent.

## Derived views: not the mechanism for this (checked against FEAT-693)

Derived views shipped since this feature was written (`[views.<name>]`, `ViewSpec.source.kind`
one of `ref` / `subentity` / `subtree` — `src/squads/_workflow/_models.py`, resolved by
`src/squads/_views.py::resolve_records`). All three source kinds project off an `Item`'s own
relations — its refs, its sub-entity collection, its subtree — everything read out of
`SquadsDB`. A memory entry and a board notice are neither: no counter-allocated id, no place in
the item index, no refs/sub-entities/subtree position to project from (`squads._memory`,
`squads._board`). The mechanism has no fourth source kind to bend toward them, and there's no
reason to invent one — `sq memory <role> list --json` and `sq board list --json` are already
flat, already-fetchable lists; a view adds grouping/ordering/presentation machinery neither
list needs. The CLI-surface gaps named above (`created_at` on memory's `list --json`, the
missing `show --json`) are the real, narrower fix — not a views entry. Confirmed by reading
`ViewSource`/`ViewSpec` and `_views.py` directly, not inferred from the feature name.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 690 add-story "As a <role>, I want … so that …"`; track with `sq feature 690 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Memory hygiene-oversight view (sq ui first, extension once list --json carries created_at) |
| US2 | Todo |  | Team board view (both clients, low cost, no named urgency — sequence after memory) |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Memory hygiene-oversight view (sq ui first, extension once list --json carries created_at)

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Nest per-role/operator memory as eager, glance-visible children in each client's Roster tree/group: entry count + staleness on the parent node, sorted-oldest-first entries on expand, drill-to-body as the secondary step. sq ui ships complete today (in-process Service, no CLI gap). The extension's overview (count + summary) needs no CLI change; its staleness signal needs created_at added to sq memory <role> list --json; its drill-to-body needs the separate sq memory <role> show <slug> --json addition — sequence accordingly, don't half-build the drill-in ahead of the CLI surface. Read-only: acting on a spotted entry (forget/add) is an explicit follow-on, out of scope here.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Team board view (both clients, low cost, no named urgency — sequence after memory)

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
A dedicated small read surface on each client, not a tree branch: a modal screen in sq ui (peer to FilterScreen/SearchScreen), a single webview panel behind one command in the extension (same tier as the existing workflow-cheatsheet panel). sq board list --json already returns each notice's full body inline, so this needs no CLI change on either client. Build after the memory story, not alongside it — there is no equivalent felt pain named for the board.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T07:41:51Z] Nina Product:
  - Refreshed against the current tree — every technical claim in the body still holds (verified, not assumed): sq memory list --json still hand-picks slug/filename/description dropping created_at, show --json still exits 2, board list --json already carries posted_at/until/author, the extension's metaTreeDataProvider.ts/domain/metaView.ts and sq ui's _tree.py/_reader.py/_filter.py/_search.py shapes described here are unchanged, and roster size (10 roles + 1 operator) still supports the eager-fetch call.
  - Added one new section answering a question the body left open: derived views (FEAT-693, shipped since this feature was written) don't apply — ViewSource.kind is ref/subentity/subtree, all Item-relation sources resolved off SquadsDB; memory entries and board notices are neither items nor indexed there. Confirmed by reading _workflow/_models.py::ViewSource and _views.py directly.
  - No story rewrite needed — US1/US2 premises are still accurate, left as-is per no-churn guidance. This is a refresh, not a reauthor: nothing here is stale or broken, the feature was simply missing the derived-views answer.
  - Splits cleanly by client for delivery, but the CLI is the shared dependency both lean on: sq ui needs zero CLI change (in-process Service already exposes created_at + full body); the extension's overview needs the small created_at addition to memory list --json, and its drill-to-body needs the separate memory show --json addition — both CLI-side, land once, unlock the extension regardless of which client builds first. Board needs no CLI change on either side.
  - Left Draft per instruction. @tech-lead for breakdown once greenlit.
<!-- sq:discussion:end -->
