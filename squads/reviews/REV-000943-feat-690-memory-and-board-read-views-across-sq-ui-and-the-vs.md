---
id: REV-943
sequence_id: 943
type: review
title: FEAT-690 memory and board read views across sq ui and the VS Code extension
status: Approved
author: reviewer
refs:
- FEAT-690:addresses
subentities:
- local_id: F1
  title: sq ui attaches memory by slug, not item type
  status: Fixed
  severity: medium
- local_id: F2
  title: Extension memory count silently under-reports a degraded pool
  status: Fixed
  severity: medium
- local_id: F3
  title: Extension board panel goes blank when one notice is unreadable
  status: Fixed
  severity: medium
- local_id: F4
  title: Memory panel title drops the role once the fetch succeeds
  status: Fixed
  severity: low
- local_id: F5
  title: 'sq ui: a zero-memory identity renders as an empty expandable branch'
  status: Fixed
  severity: low
- local_id: F6
  title: New memory show --json surface is undocumented
  status: Fixed
  severity: low
- local_id: F7
  title: Memory bracket-safety is correct but untested
  status: Fixed
  severity: info
created_at: '2026-09-14T13:29:22Z'
updated_at: '2026-09-15T12:42:19Z'
---
<!-- sq:body -->
One batch review across the whole of FEAT-690 — both delivered halves together: the Python
half (`sq memory` JSON additions, `sq ui` memory-under-roster and the board screen) and the
TypeScript half (the extension's Roster memory children, memory-entry panel and board panel).

Reviewed as an uncommitted working tree against the feature's own stated job — comparison
across the roster, not deep-reading one entry — rather than against the subtask checklists.
Gates were run by the main loop and are not re-verified here; this pass looks for what the
tests do not cover.

## What was checked and came back clean

- **Read-only contract.** No write path crept in on either client. Every `sq` subcommand the
  adapter can spawn is a read (`tree`/`list`/`search`/`show`/`workflow`/`graph`/`memory
  list`/`memory show`/`board list`); the TUI calls no `memory_add`/`memory_forget`/
  `board_post`/`board_clear`, and nothing in either client mutates an item.
- **Bracket / markup safety, driven rather than read.** The tree leaf label, the identity
  glance suffix and the memory reader header were fed a summary and tags carrying
  `[bold red]…[/]`, `[/dim]` and `[x]`: every one rendered the text literally, with styling
  carried as spans rather than parsed out of content. `Text.assemble` and `Content.from_markup`
  template variables are used correctly throughout. The TS side routes every free-form string
  through `renderMarkdownToHtml` (which escapes) or a plain `TreeItem.label`; the tooltip path
  applies `escapeTooltipMarkdown` to the summary.
- **Age formatting.** Both implementations pick the coarsest fitting unit with the same unit
  table, clamp a future timestamp to zero, and degrade to "unknown age" on an unparseable
  value — `clock.parse_iso` raises only `ValueError` (it normalises tzinfo before subtracting,
  so no `TypeError` escapes) and `new Date(...)` is NaN-checked. They agree.
- **Ordering.** Oldest-first with a slug tiebreak in both clients; newest-first with an id
  tiebreak for the board in both. The `localeCompare`-vs-codepoint difference between them was
  checked against hyphenated and underscored slug pairs and diverges only on case, which
  slugification makes unreachable.
- **Project rules.** No `from __future__ import annotations`; PEP-695 `type` aliases
  (`NodeData`, `MemoryBySlug`); `clock.now()` throughout, no `datetime.now()`; no ticket ids in
  source or test names; no marker regions touched. (The disproving greps were validated against
  a known positive first.)
- **Filter scoping.** Both clients fetch only for identities surviving the active filter, and
  both derive eligibility from the same predicate the view itself uses rather than a second
  notion of "visible".

## Findings

Seven findings, none critical or high. Three are medium: one correctness defect in `sq ui`'s
tree attachment, and two degraded-read divergences where the extension is strictly worse than
`sq ui` at exactly the signal this feature exists to produce. Three are low and one is info
(a coverage gap on behaviour I confirmed is correct).

The verdict and the per-finding detail are in the findings themselves.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 943 add-finding "…" --severity medium`; track with `sq review 943 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — sq ui attaches memory by slug, not item type

<!-- sq:finding:F1:body -->
`sq ui` decides whether a Roster leaf gets a memory signal by looking its slug up in the
pool map, not by checking the item's type. In `src/squads/_tui/_tree.py::_attach`:

```python
role_slug = node.item.extra.get(X.SLUG)
if isinstance(role_slug, str):
    pool = memory.get(role_slug)
    if pool is not None:
        ...
```

Skills carry `extra[X.SLUG]` too (`_services/_roster.py::add_skill` sets it, as do the two
seeding paths in `_services/_maintenance.py`), so any skill whose slug collides with a
role's or operator's slug picks up that identity's notebook.

**Driven, not inferred.** A role `manager` and a skill also slugged `manager` (reachable:
`sq skill add "manager"` slugifies the name and only checks for a slug clash *within* skills),
one memory in the `manager` pool, through the real `populate_tree`:

```
'ROLE-1 Catherine Manager (Active)  memory: 1 · 8mo ago'
  'a-fact  s  (8mo ago)'    data=MemoryNodeData(role_slug='manager', entry_slug='a-fact')
'SKILL-2 manager (Active)  memory: 1 · 8mo ago'
  'a-fact  s  (8mo ago)'    data=MemoryNodeData(role_slug='manager', entry_slug='a-fact')
```

The skill node shows a count, an age, and an openable child that belongs to someone else.
This breaks TASK-939's acceptance criterion "Skill nodes gain no children" and, worse for the
feature's actual job, puts a second copy of one identity's notebook on screen in a view whose
whole purpose is comparing notebooks across identities — a duplicate the reader has no way to
recognise as an artefact.

`roster_identity_slugs` gets this right (it gates on `ROSTER_ROLE`/`ROSTER_OPERATOR`); the
render side simply does not re-apply that gate. The extension does re-apply it —
`domain/metaView.ts::itemToLeaf` computes the pool as
`isMemoryEligibleType(item.type) ? memory.pools.get(item.slug) : undefined` — and
`test/metaView.test.ts`'s "never appends a suffix, or gives children, to a Skill leaf" drives
exactly this shape (a pool keyed at the skill's own slug) and passes. So the two clients
disagree, and the one with the test is the correct one.

**Second face of the same root cause.** `_attach` reaches the memory branch only in the
`else` of `if node.children:`. Roster types declare `parents = []` in the bundled spec, so no
role can have item children today — but a squad that declares its own type parented to `role`
would silently lose the count+age suffix *and* the children on every identity, with no error
and nothing in the code marking the assumption. Gating on type rather than on "this node
happens to be a leaf" fixes both faces at once.

**Test-shape note.** `tests/tui/test_memory_view.py::test_a_skill_node_gains_no_memory_signal_or_children`
uses `add_skill("Do the thing")` → slug `do-the-thing`, which cannot collide with `manager`.
The test proves the mechanism for the non-colliding shape and cannot fail for the colliding
one. The shape to add is the colliding slug, mirroring the TS test that already drives it.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Extension memory count silently under-reports a degraded pool

<!-- sq:finding:F2:body -->
The identity's entry count is the primary hygiene signal this feature exists to produce.
In the extension that count is silently wrong whenever a pool holds a file `sq` could not
read, with nothing on screen distinguishing it from a genuinely smaller notebook.

`sq memory <role> list --json` (`src/squads/_cli/_memory.py::list_memories`) drops an
unreadable entry from the array, names it on **stderr**, and exits **0**. The adapter's
`getMemoryList` does not inspect stderr on a zero exit — its own doc comment says so — so
`MemoryFetchResult` has no partial state at all, and `memoryGlanceText` renders the shortened
count as if it were the whole pool.

`sq ui` does not have this problem: `Service.memory_list` hands back
`(entries, unreadable)` in-process and `_attach_memory_children` appends a
"N memory files could not be read — listing partial" leaf. So the two clients disagree on the
same underlying data — one says "3 memories", the other says "3 memories, listing partial".

This is the failure mode TASK-939's own design constraints name in as many words ("a shortened
list with nothing said about it is the failure mode to avoid"), applied to the Python half and
not to the TypeScript half. It matters more here than it would on an ordinary list, because a
role whose count reads low is precisely the thing a reader is meant to act on: an
under-reported count manufactures the exact signal the feature is built to detect.

**Where the fix belongs.** Not in the client, most likely: the CLI is the asymmetry.
`memory list --json` signals degradation on stderr with exit 0; `board list --json` signals it
on stderr with exit 1 (see F3). Neither is consumable by a client that only reads stdout and
the exit code. One coherent contract — a documented way for a `--json` reader to learn that a
listing is partial — would let both clients reach `sq ui`'s behaviour, and would settle F3 at
the same time. Worth raising with the operator as a CLI-surface decision rather than patching
the extension to parse stderr.

Untested either way: there is no vitest coverage of a degraded memory pool, because there is
currently nothing for it to assert.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Extension board panel goes blank when one notice is unreadable

<!-- sq:finding:F3:body -->
One unreadable notice file hides the *entire* board in VS Code.

`sq board list --json` (`src/squads/_cli/_board.py::list_notices`) writes every readable
notice to stdout as valid JSON, prints the unreadable ones to stderr, and then
`raise typer.Exit(1)`. `sqAdapter`'s `runSqRaw` checks the exit code before it ever looks at
stdout, and `classifyNonZeroExit` turns exit 1 into `runtime-error` — so `renderBoardHtml`
takes its failure branch and the panel renders "Squads: unable to load the board" plus the
stderr text. Every notice that *was* read is discarded.

`sq ui`'s `BoardScreen` renders the readable notices and adds a "N notice files could not be
read — listing partial" line under them. Same data, opposite outcome: the client that can
still show you the team's notices shows none of them.

The handback called this "pre-existing CLI behavior, not something this task's scope covers or
regresses", and the exit code is indeed pre-existing. The *outcome* is not: this client is the
first consumer of that surface, and it consumes it in the way that loses the most. A notice
board that goes blank is also a worse failure than a stale one — the point of a broadcast
notice is that someone reads it before starting work.

Two ways out, in preference order:

1. Fix the CLI contract (shared with F2): give `--json` readers a supported way to see a
   partial listing, so both clients can degrade the way `sq ui` already does. This is the same
   decision F2 needs, and settling it once settles both.
2. Failing that, have `getBoardList` attempt a stdout parse on exit 1 before classifying, and
   surface the stderr text alongside the notices rather than instead of them. Narrower, but it
   puts board-specific exit-code knowledge into an adapter that deliberately pins none.

Flagging it rather than accepting it because the scope argument only covers who introduced the
exit code, not whether the panel should go blank.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Memory panel title drops the role once the fetch succeeds

<!-- sq:finding:F4:body -->
`itemPreviewManager.ts::renderMemoryEntry` opens the panel titled
`memoryEntryPanelTitle(roleSlug, entrySlug)` — `"tech-lead: promote-tasks-before-dispatch"` —
and then, on a successful fetch, overwrites it:

```ts
if (outcome.kind === 'success') {
  title = outcome.data.slug;
}
```

So the role is present only while the fetch is in flight or when it fails, and the settled
title is the bare entry slug. The panel is a **single reused slot** (by design — the doc
comment explains why), so a reader drilling from `manager`'s notebook into `tech-lead`'s sees
the same tab, retitled, with nothing left naming whose notebook is open.

That lands badly against this feature's stated job: the thing a reader is hunting is
duplicated and contradicting entries *across* roles, which by construction means two entries
whose slugs and summaries look alike. The one piece of context that disambiguates them is the
one the title drops the moment the content arrives.

The pre-fetch fallback is already the right string. Low severity and a one-line fix — keep
`memoryEntryPanelTitle(roleSlug, outcome.data.slug)` on success rather than replacing the
whole title. (`renderMemoryEntryHtml`'s `# ${entry.slug}` header has the same gap, though the
tab title is the part that stays visible when the panel is not focused.)
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — sq ui: a zero-memory identity renders as an empty expandable branch

<!-- sq:finding:F5:body -->
In `sq ui`, an identity whose pool was fetched is attached with `parent.add(...)` regardless of
whether the pool has anything in it, so a role reading `memory: 0` gets a disclosure triangle
that opens onto nothing:

```python
pool = memory.get(role_slug)
if pool is not None:
    entries, unreadable = pool
    label.append_text(_memory_glance_suffix(entries))
    branch = parent.add(label, node.item.id, expand=False)   # branch even when entries == []
```

Driven through the real `populate_tree` with an empty pool:

```
'ROLE-1 Empty Role (Active)  memory: 0'   allow_expand=True   children=0
'SKILL-2 Some Skill (Active)'             allow_expand=False  children=0
```

The extension renders the same identity as a leaf — `treeItemRendering.ts` maps
`children.length === 0` to `TreeItemCollapsibleState.None` — so this is also a small client
divergence.

Cosmetic, but it sits on the exact node the feature exists to draw attention to: "a role
active for weeks with a `(0)` next to its name is the single most useful thing this feature
produces" (the feature body). A `0` you can nonetheless expand invites a click that answers
nothing, which is the opposite of a glance-level signal. Guard the `add` on
`entries or unreadable` and fall through to `add_leaf` otherwise.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — New memory show --json surface is undocumented

<!-- sq:finding:F6:body -->
`sq memory <role> show <slug> --json` is a new public machine-readable surface, and nothing
adopter-facing records it.

- `docs/stability.md` enumerates the supported `--json` shapes and, for memory and the board,
  names exactly three: "**Notices and memory:** `board list --json`, `memory list --json`,
  `memory search --json`". `memory show --json` is absent, so it ships outside the contract
  that section defines — and the same section closes with "Every shape above is covered by a
  regression test, so it cannot drift on you unnoticed", a claim the new shape is now outside.
  The new `created_at` key on `memory list --json` is likewise unmentioned (a field addition,
  which that document does say is allowed between majors — but it is the field the extension's
  whole staleness signal depends on, so it is worth naming).
- `CHANGELOG.md`'s `## [0.15.0]` section carries the view-tags work and nothing about either
  client's memory/board surfaces or the two CLI additions, against this repo's standing rule
  that an entry lands with the work rather than being batched at release.
- `README.md`'s one-line description of `sq ui` still reads "the item tree, filters, full-text
  search, and a reader pane for any item", and the extension's "work items, records, and roster
  as activity-bar trees" — neither mentions memory or the board.

None of this is a code defect and none of it was in either task's acceptance criteria, which
is why it reached the end of the build unnoticed. Filing it so it gets a home rather than
being rediscovered at release: the changelog prose belongs to the tech writer, and
`docs/stability.md` wants the same pass.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Memory bracket-safety is correct but untested

<!-- sq:finding:F7:body -->
TASK-939's acceptance criteria say "A memory summary, memory body or notice body containing
square brackets renders literally in every one of those surfaces." The delivered bracket test
(`tests/tui/test_board_screen.py::test_a_notice_body_with_brackets_renders_literally`) covers
the notice body only. `tests/tui/test_memory_view.py` has no bracket case, and the change to
`tests/tui/test_bracket_content_renders_safely.py` is a type annotation, not new coverage —
so the memory tree label, the glance suffix and the memory reader header are uncovered.

**The behaviour is correct** — I drove it rather than reading it. A summary of
`a [bold red]summary[/] with [/dim] and [x] brackets` and a tag of `[tag]`, through the real
`_memory_leaf_label`, `_memory_glance_suffix` and `_glance_line`:

```
TREE LABEL plain: 's-1  a [bold red]summary[/] with [/dim] and [x] brackets  (8mo ago)'
  spans: [Span(0, 3, 'bold'), Span(58, 67, 'dim')]     # styling carried as spans, not parsed
READER HEADER plain: 's-1  ·  2026-01-01T00:00:00Z  ·  tags: [tag], ok'
```

So this is a coverage gap, not a defect, and it is filed as `info` on that basis. It is worth
closing anyway: these are the two places where the next change would most plausibly reintroduce
a markup string (a label is "just a string" until it is not), and the whole point of the
existing bracket-safety test file is that this repo has been bitten by it before. Two
assertions on the memory surfaces, matching the notice-body one already written.

Same shape on the TS side: `renderMemoryEntryHtml` is tested for HTML escaping of the **body**
but not of the **summary**, which travels the same `renderMarkdownToHtml` path and is equally
free-form. Lower value than the Python gap (one code path, already proven for one input), but
the same one-line addition.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-14T13:33:17Z] Paul Reviewer:
  - Batch review of FEAT-690 done — both halves in one pass, REV-943, status ChangesRequested. @manager
    
    Verdict: the feature substantially does the oversight job its body describes. Count + age sit on every Role/Operator node before anything is expanded, on both clients; entries sort oldest-touched first with a slug tiebreak; a quiet notebook reads as "0" rather than as nothing. The read-only boundary holds — every sq subcommand either client can spawn is a read, and the TUI calls no memory/board mutation. Nothing here blocks the release on its own.
    
    Seven findings, none critical or high:
    - F1 medium — `sq ui` attaches memory by slug lookup rather than item type, so a skill sharing a role's slug shows that role's notebook, count and openable children. Driven through the real `populate_tree`, not inferred. Breaks TASK-939's "skill nodes gain no children"; the extension gates on type and its own test drives exactly this shape. Same root cause silently drops the whole signal if a squad ever parents a type to `role`.
    - F2 medium — the extension's count silently under-reports a pool with an unreadable file (`memory list --json` exits 0, names it on stderr, the adapter doesn't read stderr). `sq ui` says "listing partial". An under-reported count manufactures the exact signal this feature exists to detect.
    - F3 medium — one unreadable notice blanks the extension's whole board (`board list --json` writes valid JSON then exits 1; the adapter discards stdout on non-zero). `sq ui` shows the readable notices plus a partial note.
    - F4/F5/F6 low, F7 info — memory panel title drops the role on success; a zero-memory identity is an expandable branch with nothing in it (sq ui only); `memory show --json` is missing from docs/stability.md's `--json` enumeration and nothing landed in the 0.15.0 changelog; memory bracket-safety is correct (I drove it) but untested.
    
    F2 and F3 are the same decision wearing two hats: the CLI has no way for a `--json` reader to learn a listing is partial, and signals it two different ways (exit 0 + stderr, exit 1 + stderr). Settling that once fixes both and is an operator-level call, not an extension patch — worth ruling on before anyone writes code for either.
    
    Clean dimensions, stated plainly: read-only contract, bracket/markup safety in both clients, age formatting parity, ordering parity, filter scoping, and the project rules (no `__future__` annotations, PEP-695 aliases, `clock.now()`, no ticket ids). The disproving greps were validated against a known positive first.
    
    `sq check` clean.
- [2026-09-14T13:48:08Z] Olivia Lead:
  - Authored TASK-944 (Draft, parent FEAT-690, `fixes` ref here) covering F1, F4, F5, F6, F7 as five subtasks — one coherent surface: the type gate and the zero-pool leaf in `_tui/_tree.py::_attach`, the extension panel title, the docs/changelog/README gap, and the bracket-safety coverage. Acceptance per finding names the files; the F1 case is briefed to use colliding slugs, since the existing skill test cannot fail for the broken shape.
    
    F2 and F3 are deliberately out of scope and left Open: they are the one CLI-contract question (how a `--json` reader learns a listing is partial, signalled two different ways today), pending an operator ruling. @manager — the ruling gates both, and whichever way it goes it lands as its own task, not as an extension patch.
    
    No finding marked Fixed — nothing is fixed yet. `sq check` clean.
- [2026-09-14T13:50:11Z] Pierre Chat:
  - Ruling on F2/F3 (degraded --json reads): fix the CLI contract in 0.15. Both surfaces get a
    consistent degradation signal and a way for a --json reader to learn a listing is partial;
    the extension then reads it instead of under-reporting a degraded memory count and blanking
    the board on one unreadable notice. This is in scope for this release, not deferred to 0.16.
- [2026-09-14T13:59:10Z] Olivia Lead:
  - Restructured against op-pierre's ruling on this review (F2/F3: fix the CLI contract in 0.15, not defer). The single task is now three, one per owner role, each carrying a `fixes` ref here and all Draft:
    
    - **TASK-944** (python-dev) — F1 type gate, F5 zero-pool leaf, F7 Python half, plus the F2/F3 CLI contract: one degradation signal both listings give a `--json` reader from stdout, and the regression cover for the `memory show --json` shape (moved off the writer — a writer should not be on the hook for making a coverage claim true).
    - **TASK-945** (typescript-dev) — F4 panel title, F7 TS half, and the consuming half of F2/F3: a degraded pool reads as partial rather than smaller, and the board renders its readable notices instead of blanking when `classifyNonZeroExit` sees the non-zero exit. Depends-on TASK-944; the adapter takes the signal's shape from that handback rather than gaining per-command exit-code knowledge.
    - **TASK-946** (tech-writer) — F6, across `docs/stability.md`, the 0.15.0 changelog and the two README client lines. Depends-on both, so the `--json` contract is documented once after it settles.
    
    F5's edge case is pinned in the acceptance criteria: only a genuinely empty pool collapses to a leaf — an identity whose files are all unreadable keeps its branch, because the partial-listing notice is a real child and hiding it would hide the reason the count reads zero.
    
    No finding marked Fixed and no status changed here — nothing is fixed yet. @manager the three are ready for the Draft-to-Ready gate in dependency order. `sq check` clean.
- [2026-09-14T14:09:44Z] Robert Architect:
  - ADR-947 authored for F2/F3 (`addresses` this review and FEAT-690), left at its initial status — op-pierre accepts it, not me. @manager
    
    The contract: a **partial result** — valid payload in its frozen shape, entries missing because the corpus could not be fully read — exits a new code **`4`**, and under `--json` names what it left out in **one compact JSON line on stderr**, `{"omitted":[{"code","source","message"}]}`. Payload shapes do not change: they are bare arrays with nowhere to put a key, so no envelope, no added field, no sentinel row.
    
    Three corrections to the framing the review and the dispatch worked from:
    
    - **It is five commands, not two.** `_cli/_main.py::_report_unreadable` is already shared: `inbox`, `search`, `board list`, `memory list`, `memory search`. Four exit 1; the two memory commands exit 0. One contract, one violator.
    - **The posture is already written down and memory breaks it.** `docs/faq.md`'s table assigns code 1 to "a command that finished only partly and named what it could not read", and `UnreadableItems` in `_services/_results.py` says callers pair the degraded read with a non-zero exit. `memory list --json` exiting 0 is a defect against a documented contract, not a second opinion.
    - **"Tier 3 is additive, so just add a field" is not available.** Both payloads are bare JSON arrays (ADR-459 records that convention deliberately). There is no object to add a key to; the only payload route is an array→object retype, which Tier 3 forbids.
    
    Why a new code rather than 0 or 1: exit 1 conflates "here is nothing" with "here is most of it", so the extension blanking the board is *compliant* with ADR-427 §2, not buggy — the conservative reading is the only safe one. Exit 0 would fix that by making a consumer that ignores the new signal read a short answer as the whole answer, which is F2's defect preserved into the fix. Code 4 degrades conservatively for every existing consumer (unrecognised non-zero = error) and gives a shell the one bit it can act on without parsing.
    
    Costs, stated: `board list`/`inbox`/`search` go 1 → 4 (non-zero either way, no script's verdict flips); `memory list`/`memory search` go 0 → 4, which *does* flip a verdict pass → fail and is the flip the ruling asks for. And the frozen four-code table becomes five — an amendment, cheapest now, before 1.0.
    
    `sq check` and `sq repair`/`migrate up` are explicitly outside the class, with the membership test in the body. `docs/stability.md` and `docs/faq.md` must carry this as a **behaviour change**, not merely describe the new state — that is on TASK-946, and TASK-944's acceptance needs the `source`/`message` split (the memory and board stores hand back one pre-composed string today).
    
    `sq check` clean.
- [2026-09-15T12:42:18Z] Catherine Manager:
  - All seven findings fixed across TASK-944 (sq ui memory gate + the CLI contract), TASK-945 (the
    extension consuming it) and TASK-946 (the docs). Verified as the authoritative gate: full suite
    5099 passed / 0 failed, pyright 0 errors, ruff clean, extension typecheck/eslint/prettier clean
    with 688 vitest tests, sq check clean.
    
    F2/F3 grew well past the original two-command framing on op-pierre's ruling to fix the CLI
    contract in 0.15: they became ADR-947, a fifth exit code across five commands, and a documented
    behaviour change. The degraded path was driven end to end rather than read -- clean exits 0,
    degraded exits 4, one compact omissions line on stderr, stdout still a bare array.
<!-- sq:discussion:end -->
