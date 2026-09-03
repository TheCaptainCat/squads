---
id: BUG-879
sequence_id: 879
type: bug
title: VS Code tree ignores the cycle-anchor flag and shows a fabricated root
status: Verified
author: qa
priority: medium
severity: medium
refs:
- BUG-870
- TASK-877:depends-on
description: The client maps tree JSON through a closed field list, so the anchor
  mark never reaches the display model; the fabricated root renders as an ordinary
  one. Not reachable until the core change lands.
created_at: '2026-09-02T10:23:06Z'
updated_at: '2026-09-03T07:09:15Z'
---
<!-- sq:body -->
## Summary

The accepted answer to bare `sq tree` omitting a parent cycle is to render the component
anchored at a cycle member and **mark** the anchor, in the rendering and in `--json`. The
mark is not decoration: it is the entire reason the fabricated root is acceptable, because
an unmarked anchor asserts a root nobody wrote.

The VS Code client maps `sq tree --json` through a closed field list. An added `anchor`
key is safe on the wire — it is ignored, not rejected — but it is also *only* ignored: it
never reaches the display model, so the client will render the fabricated anchor as an
ordinary root with nothing to distinguish it. The disclosure holds in the terminal and
silently does not hold in the client, which is the one place the ruling's own justification
does not survive.

This is the client-side half of that work. It must land with or after the core change, not
before it, since there is nothing to mark until the flag exists.

## Not reachable today — stated plainly

**Driven.** The anchor flag does not exist. On the live repo corpus:

```
sq tree --json    # 125 roots; node keys, union over the whole tree:
#   assignee, badges, blocked, children, id, priority, status, title, type
```

That is exactly the client's field list and nothing more. No `anchor`, and no `path_only`
either.

**Read**, the core: nothing anchors a cyclic component yet — the bare form's roots are
still the parentless forest, so the component is omitted rather than fabricated. Nothing
in the client is wrong *today*; there is simply no fabricated root for it to fail to
disclose.

**Inferred**, and the reason this is filed now rather than after the fact: the moment the
core change lands, the client starts rendering invented roots with no signal, and it does
so silently — see the canary section below, which is the part that makes "we will notice"
false.

## What the client does with the tree JSON — verified

Traced end to end rather than off the one cited line. Four hops, all **read**, all in
`clients/vscode/src`:

**1. Fetch.** `sqAdapter.ts::getTree` builds `['tree', '--json']`, appending a root only
when one is passed and `--all` only when the show-closed toggle is on. `treeDataProvider.ts`
calls it with `root` as `undefined` — that is the **bare** form, the exact form the core
change alters. Its result goes straight into the display mapping.

The other consumer, `itemPreviewManager.ts`, passes an explicit id — the targeted form,
which already renders a cyclic component today and whose root is the one the reader asked
for rather than an invention.

**2. Shape guard.** `sqAdapter.ts::isSqTreeNode` accepts an object when `id`/`type`/`title`/
`status` are strings, `priority`/`assignee` are string-or-null, and `children` is an array
of nodes. It asserts nothing about keys it does not know. `types.ts` states the policy in
its own header — the interfaces are *"hand-trimmed to the fields the client actually reads;
they intentionally don't model every key `sq` may emit (extra/unknown keys are ignored, not
rejected)"*. So the tech lead's wire-safety claim is right, and it is the same property that
makes the field invisible.

`SqTreeNode` itself declares nine members: `id`, `type`, `title`, `status`, `priority`,
`assignee`, `blocked`, `badges?`, `children`. There is no `anchor` and no `path_only`.

**3. Display mapping.** `domain/treeMapping.ts::mapNode` constructs a `DisplayNode` from a
fixed set of reads — `node.id`, `node.title`, `node.status`, `node.assignee`, `node.blocked`,
`node.type`, `node.badges`, `node.children`. The row's secondary text comes from
`describeNode`, which is `status · assignee` plus `· blocked` when blocked, and the tooltip
comes from `buildTooltip` over a fixed argument object. Nothing forwards an unrecognised key,
and there is no free-form annotation slot to forward it into: `domain/displayNode.ts`'s
`DisplayNode` is a closed interface, and its per-node visual state is exactly `blocked`,
`closed`, `hidden` and `colorIntent`.

**4. Render.** `treeDataProvider.ts::getTreeItem` calls `toTreeItem(node, …)` with only a
`DisplayNode`, so hop 3 is the last place the field could have survived.

The second rendering path is the same story: `domain/graphDiagrams.ts::subtreeNodeLabel`
builds each mermaid node's label from a fixed template — `${id}: ${title} (${status})` plus
a `[blocked]` suffix — with no branch for anything else.

**Driven**, the negative, with the pattern validated against a known positive first: the
literal `blocked` appears 31 times across the client sources, so a case-insensitive word
search over `clients/vscode/src/**/*.ts` does find fields that are there. The same search
for `path_only` returns zero — consistent with it not being on the wire. `anchor` returns
thirteen hits, and all thirteen are HTML `<a>` anchors in the markdown/webview layer or a
comment about an anchored regex. The client has no notion of a tree anchor in any form.

## The existing skew canary will not catch this

**Read**, `clients/vscode/test/canary/skewCanary.test.ts`: for every node of a live
`sq tree --json`, it asserts `isSqTreeNode(node)` and then

```
expect(Object.keys(node)).toEqual(expect.arrayContaining([ …the nine fields… ]))
```

`arrayContaining` is a **superset** assertion. A tenth key satisfies it. The one test whose
whole job is to notice that `sq`'s JSON and the client's model have drifted apart stays green
through exactly this drift, and so does every unit test over `treeMapping`, since none of them
can assert on a field the display model has no room for.

So the failure mode is not "we ship it and a test goes red later". It is "we ship it, every
gate is green, and the terminal and the client disagree about whether a root is real".

## Why it matters, in the terms the ruling set

**Read**, the ruling being implemented: the fabrication is accepted *because* it is disclosed,
and a reader can recover from a marked anchor while they cannot recover from an item that does
not exist. Both halves of that trade are stated as depending on the mark.

In the client, only the first half arrives. A reader of the sidebar hierarchy gets the
component back — that is the improvement — but gets it presented as though someone had
deliberately made those items top-level, with no way to tell an anchor from a genuine root,
and with the one dropped edge (the one closing the loop back to the anchor) invisible. The
same reader in the terminal sees the mark and knows to go and look.

It is also worth being precise about the direction of the regression. Today the client's
behaviour matches the terminal's: both omit. After the core change and without this, the
client is the only surface presenting a fabricated hierarchy as fact — which is the specific
outcome the ruling declined when it rejected shipping an unmarked anchor.

## Scope

The change is in `clients/vscode`, which is TypeScript in another tree with another owner.
Sketching it only so the size is not mistaken, and deliberately not choosing the visual —
that is the client owner's call:

- `SqTreeNode` gains the flag as an optional member, so an older `sq` that omits it keeps
  parsing (the same treatment `badges` already has).
- `DisplayNode` gains somewhere to carry it, since it has no slot today.
- `mapNode` forwards it; the row rendering and/or tooltip surfaces it; `subtreeNodeLabel`
  surfaces it in the mermaid subtree.
- The canary's key assertion is the place to decide whether a *missing* flag should fail
  once the core emits it — the current `arrayContaining` shape cannot express that.

Not in scope here and not assumed: whether the client should also disclose the dropped
closing edge, or surface anything at all about the underlying corpus condition beyond the
mark itself.

## Environment

**Driven** where marked: `squads 0.14.0`, branch `release/0.14`, HEAD `be7f797`, bundled
workflow spec, no `.overrides/`. The `sq tree --json` key set was read from the live repo
corpus, no writes. The tree carried another agent's in-flight edits at the time; checked
rather than assumed — none of the twenty-one modified or untracked paths is under
`clients/`, so every client claim above is against committed code.

## Severity

Judged **medium**.

Not low: the mark is the stated precondition for the fabrication, not a nicety, so without
it the client ships the exact rendering the design ruling refused. It ships silently — the
skew canary passes a superset assertion and no other test can see the field — so the gap
does not announce itself at the moment it becomes real. And the surface it lands on is the
sidebar hierarchy, the client's primary way of reading structure.

Not high: it is unreachable until the core change lands, so nothing is wrong right now;
it cannot corrupt anything, change an exit code, or lose data; it only manifests on a corpus
that is already carrying a parent cycle, which `sq check` reports at exit 3 independently;
and the items themselves are all present and correct — it is the claim about which of them
is a root that is false.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T10:24:14Z] Mara Tester:
  - Filed off the gap flagged on the tree-omission ruling. Verified the client claim myself
    rather than transcribing it; it holds, and there is one thing worse than reported.
    
    - **Confirmed, read, traced through all four hops** in `clients/vscode/src`: bare fetch
      (`getTree` with no root, from `treeDataProvider`) -> shape guard (`isSqTreeNode`, which
      asserts nothing about unknown keys — `types.ts` states extra keys are ignored, not
      rejected) -> `treeMapping.mapNode`, which reads a fixed set of fields into a `DisplayNode`
      -> `getTreeItem`, which takes only a `DisplayNode`. `DisplayNode` is a closed interface
      with no annotation slot, so there is nowhere for the flag to survive even if it arrived.
      The mermaid path is the same: `subtreeNodeLabel` is a fixed template.
    - **Driven, the negative:** `sq tree --json` today emits exactly the nine keys the client
      models — no `anchor`, no `path_only`. So the condition genuinely is not reachable yet;
      the body says so up front. Pattern validated against a known positive (`blocked`, 31 hits)
      before letting the zero stand; `anchor` has thirteen hits in the client and all thirteen
      are HTML `<a>` anchors or a comment about an anchored regex.
    - **The part that was not in the flag: the skew canary will not catch it.** The test asserts
      the node's keys with `expect.arrayContaining(...)`, a superset assertion — a tenth key
      passes. The one test whose job is to notice sq/client drift stays green through exactly
      this drift, and no `treeMapping` unit test can assert on a field the display model has no
      room for. So this ships silently green rather than going red later.
    
    Severity medium, reasoning in the body: the mark is the stated precondition for accepting
    the fabrication, so without it the client ships the rendering the ruling refused, and it does
    so on the primary structure-reading surface without announcing itself — against nothing
    corrupted, no exit code moved, and nothing reachable until the core change lands.
    
    Linked `depends-on` to the tree task as well as `related` to the bug, since it must land
    with or after it — there is nothing to mark until the flag exists. That does make it show
    as blocked, correctly.
    
    @tech-lead for triage and for routing it to the client's owner; the scope sketch in the body
    is deliberately not a choice of visual treatment.
- [2026-09-02T13:07:59Z] Olivia Lead:
  - Triaged. **TASK-885**, typescript-dev, `fixes` this bug and `depends-on` TASK-877.
    
    **It stays Draft until 877 lands**, and that is a deliberate call rather than an oversight. The
    field's name and its JSON semantics are not knowable before the core work settles them, so a dev
    dispatched now would be coding against an invented key. The canary half cannot be split off and
    started early either, which is the part worth stating: tightening the key assertion from a
    superset to an exact set would go red the moment the core emits its tenth key. Both halves land
    together, after 877, and 885 goes Ready then.
    
    The canary is in the task, not behind it — your finding is the reason. A drift test that cannot
    detect drift is worse than no drift test, because it is being relied on, and someone will
    already be in that file.
    
    Your four-hop trace holds and I did not re-derive it; the scope sketch went into the task
    roughly as you wrote it, minus the visual treatment, which stays the client owner's call. One
    addition: the acceptance requires the mermaid path to disclose as well as the sidebar row, since
    `subtreeNodeLabel` is the second place a reader meets a fabricated root and a fix that covers
    only the tree view leaves half the surface asserting a root nobody wrote.
    
    @typescript-dev TASK-885 is yours; do not start until TASK-877 lands — I will move it to Ready.
    @qa verification on this one needs the core change in place first.
- [2026-09-02T15:42:51Z] Mara Tester:
  - Verified **on the sidebar half**, which is the half the bug is about. Being explicit about what I could and could not drive, since this is TypeScript in another tree.
    
    **Could not drive:** the VS Code extension host. No display, and the e2e lane downloads Electron. So I have not seen a rendered sidebar row or a real tooltip in a real window. Everything below is the domain layer and the wire, driven against real output.
    
    **Could drive, and did:**
    
    **1. A real anchored tree.** Staged a genuine three-item parent cycle in a scratch squad (BUG-21 -> BUG-23 -> BUG-22 -> BUG-21 via frontmatter, then `sq repair` on that scratch squad only). Live `sq tree --json`:
    
    - bare form: 21 roots, 23 nodes, key union is the ten including `anchor`; `anchor: true` on **BUG-21 only**.
    - `anchor` is present on every node, never absent — so the client reads a boolean, never "unknown".
    
    **2. The real payload through the client's actual mapping code.** Loaded `src/domain/treeMapping.ts`, `graphDiagrams.ts` and `treeAnchor.ts` through a Vite SSR loader from a script outside `clients/` (nothing in the client tree was created or edited) and fed them the live JSON:
    
    ```
    BUG-21 anchor=true   description: "Open · unassigned · cycle anchor"
                         tooltip: "BUG-21 (bug)  \nStatus: Open  \nAssignee: unassigned  \nCycle anchor: not a real root; see sq check"
    BUG-22 anchor=false  description: "Open · unassigned"
    BUG-23 anchor=false  description: "Open · unassigned"
    ```
    
    The mark reaches both the row description and the tooltip, on the anchor and nowhere else. That is the disclosure the ruling required, on the surface a reader actually meets a fabricated root on.
    
    **3. The mermaid unreachability claim — checked, and it holds.** Both legs, independently:
    
    - *Wiring:* `buildSubtreeMermaid` has exactly one production call site (`itemPreviewManager.ts:479`), fed from `getTree(..., id)` at line 457 — always an explicit id. The bare form goes only to `treeDataProvider.ts:281` (`root` = `undefined`), which never reaches mermaid.
    - *Core:* no targeted form sets `anchor` on any node. Drove `sq tree BUG-21/BUG-22/BUG-23 --json` — every cycle member, not just the anchor — plus `--all` on both forms. Anchored nodes: `[]` in every targeted case; `['BUG-21']` only in the bare form.
    
    Fed the mermaid builder both trees to show the code itself is right: given the bare tree it emits `BUG-21: Ring 0 (Open) [cycle anchor — not a real root; see sq check]`; given the targeted tree it emits no marker, because there is nothing to mark.
    
    So the implementer's disclosure is accurate: **the mermaid half is correct and presently unreachable — defensive, not visible.** The bug is verified on the sidebar half alone, and I am not claiming more than that.
    
    **4. The canary tightening — falsified in both directions.** Ran the exact-key helper's semantics against the superset it replaced, on identical inputs:
    
    ```
                                                  OLD superset   NEW exact
    node with an EXTRA unmodelled key (path_only)    green          RED
    node MISSING anchor (a stale sq on PATH)         green          RED
    node carrying anchor (current sq 0.14.0)         green          green
    ```
    
    The old assertion was green on all three — blind in both directions, exactly as the bug body said. Repeated the stale-`sq` check too: `npm run test:canary` against `sq 0.12.1` on PATH turns the tree case red at `assertExactTreeNodeKeys` with `- "anchor"` in the diff; against `sq 0.14.0` it is 23/23 green. (The 0.12.1 run also reds four workflow-catalog cases — pre-existing 0.12/0.14 drift, unrelated to this change.) The four key-set self-tests run without `sq` at all and pass.
    
    **Gates:** `npm test` 624/624, `npm run typecheck` exit 0, `npm run test:canary` 23/23 against 0.14.0, `uv run sq check` exit 0. Nothing under `src/`, `tests/`, `docs/` or `clients/` was modified by me.
    
    One residual left open by the fix, in a follow-up comment. @manager for the 0.14 sweep.
- [2026-09-02T15:43:07Z] Mara Tester:
  - Residual: the fix closed the symptom on the tree node and left the same cause in place on two sibling surfaces of the same file. The implementer flagged this and scoped it out, which I think was right for the task; recording it as a driven finding so it does not evaporate.
    
    `test/canary/skewCanary.test.ts` still asserts key sets with `expect.arrayContaining(...)` — the superset shape this bug was filed against — for:
    
    - `sq graph --json` nodes (9 keys: id, type, status, priority, assignee, edge_kind, direction, seen, children)
    - `sq list --json` rows (7 keys: id, labels, refs, path, created_at, updated_at, badges)
    - `sq workflow types --json` entries, and the badge/collection assertions below them
    
    The blindness is the same one, and I drove it above rather than inferring it: a superset assertion is green on an added key **and** on a removed one. So if `sq` grows a field on `graph` or `list` that the client does not model, the test whose whole job is to notice sq/client drift stays green — which is the exact sentence this bug's body was written around, still true for two of the three tree-adjacent surfaces.
    
    The tree node was the right one to fix first: it is where the anchor lands, and it is the one with a demonstrated consequence. The other two have no known unmodelled field today, so this is latent rather than live. `assertExactTreeNodeKeys` is already generic over its key list, so closing them is close to a one-line change each plus a named key set.
    
    Not filing an item — @manager to decide whether this is worth one, or whether it rides with whoever next touches the canary.
- [2026-09-03T07:09:15Z] Mara Tester:
  - Filed as **BUG-896** (low), `related` to this bug and `targets` MILE-867 for 0.15, per op-pierre's ruling. My earlier comment said "not filing" — superseded.
    
    The filing carries the old-vs-new table driven through the client's own matcher, and states plainly that the tree half is proven in both directions against a real stale `sq 0.12.1` — so it reads as an unapplied one-line change on two sibling surfaces, not as an open question about the approach.
<!-- sq:discussion:end -->
