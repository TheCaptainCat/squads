---
id: BUG-879
sequence_id: 879
type: bug
title: VS Code tree ignores the cycle-anchor flag and shows a fabricated root
status: Open
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
updated_at: '2026-09-02T10:24:14Z'
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
<!-- sq:discussion:end -->
