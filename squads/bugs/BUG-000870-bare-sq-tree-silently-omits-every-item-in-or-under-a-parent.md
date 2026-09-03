---
id: BUG-870
sequence_id: 870
type: bug
title: Bare sq tree silently omits every item in or under a parent cycle
status: Verified
author: qa
priority: medium
refs:
- BUG-865
description: Every tree form exits 0 while leaving out the whole component containing
  a cycle; sq check is the only surface that reports it.
created_at: '2026-09-02T08:49:46Z'
updated_at: '2026-09-02T14:18:23Z'
---
<!-- sq:body -->
## Symptom

**Driven.** On a corpus carrying a parent cycle, `sq tree` renders a tree that looks complete, exits 0, and silently leaves out every item in the cycle and everything hanging beneath it. Nothing on the tree surface says anything is missing.

Fresh `sq init --default-names --backend none`, seven bugs, a five-item cycle written into frontmatter (`BUG-10 -> BUG-14 -> BUG-13 -> BUG-12 -> BUG-11 -> BUG-10`, mixed padding widths) plus `BUG-15` hanging off `BUG-12`, then indexed with `sq repair`:

```
sq list -a --json   ->  BUG-9 BUG-10 BUG-11 BUG-12 BUG-13 BUG-14 BUG-15   (7 bugs)
sq tree -a          ->  exit 0, renders exactly one bug: "BUG-9 Anchor (Open)"
sq tree -a -t bug   ->  exit 0, renders exactly one bug
sq check            ->  exit 3, five errors, one per cycle member
```

Six of the seven bugs are absent from every tree form, with a zero exit and no warning.

## Mechanism

**Read**, and consistent with the driven result: the tree's roots are the parentless forest. Every member of a cycle has a parent by definition — that parent is another cycle member — so no member is ever parentless and nothing anchors the component. Any item hanging beneath a cycle member is likewise non-parentless, so the whole connected component drops out. Rooting the tree explicitly at a member does render it: `sq tree BUG-12 -a` shows all five plus `BUG-15`, truncated correctly at the repeat.

## Why this is being raised

**Inferred.** The parent-cycle fix (BUG-865, `ad9c5d6`) removed the hang: every tree form now returns promptly with exit 0, both walks carry a visited set, and that half is verified. What the fix did not settle is what the tree should *show* when a cycle exists. The behaviour an operator now meets is a tree that is quietly incomplete rather than one that never returns — a zero exit and a plausible-looking rendering, with the omission invisible on the surface they are reading.

`sq check` exit 3 is currently the only surface that reports the condition. An operator who runs `sq tree` and not `sq check` has no signal at all.

## Status of the observation

**Read.** The implementer saw this during the BUG-865 work and left it deliberately, recording that making cycle members render would be a semantic change to what the tree shows — the same class of change that task put out of scope for the keep-set narrowing. That reasoning is sound and this bug does not dispute it.

This item exists to get the question decided rather than inherited: whether a tree that omits part of the corpus should say so, and on which surface. No fix is proposed here — the shape of the answer is the tech lead's and architect's call, and it is a semantic question about the tree's contract, not a defect with an obvious remedy.

## Environment

**Driven.** `squads 0.14.0`, branch `release/0.14` at `ad9c5d6`, bundled workflow spec, no `.overrides/`. Every exit code read from a bare command, never through a pipe.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T09:56:40Z] Robert Architect:
  - Ruling. Option (b), with the disclosure half of (c) folded into it: a cyclic component must appear in bare `sq tree`, anchored at a cycle member and truncated at the repeat exactly as `sq tree <id>` rooted inside the cycle already renders it. Exit stays 0. `sq check` stays the diagnostic and keeps exit 3 — nothing here proposes a check.
    
    Three required properties, not an implementation:
    
    1. **Coverage.** At equal filters, every item `sq list` returns appears somewhere in `sq tree`. Your 7-vs-1 is the measurement; the target is 7-vs-7. Ancestors pulled in as path-only anchors may make the tree a superset; it may never be a subset.
    2. **The anchor is deterministic and is a cycle member** — lowest sequence number among the items that close the loop. Trap worth naming, because it is the obvious wrong rule: "lowest unrendered keep-set item" is not the same thing. An item of lower sequence hanging *below* the cycle would anchor itself, and then render a second time as a child on the next pass. Each omitted item appears exactly once.
    3. **The anchor is marked as an anchor** — in the rendering and in `--json`, a flag beside `path_only`. An unmarked anchor asserts a root nobody wrote, which replaces a quiet omission with a quiet fabrication and is not an improvement. Additive on the wire; the clients' unknown-value fallback discipline covers it.
    
    Why the others lose.
    
    - **Leave as is.** A component vanishing is a second, undeclared visibility axis. ADR-604 made the status role the *sole* explicit axis for default visibility, across list and tree jointly; here items vanish for a reason that is not a status role, that `--all` does not lift, and that hits tree and not list. That is not a defensible default — it is an accepted decision being violated by an accident of the root computation.
    - **Render nothing, warn with the ids.** Pays the whole detection cost and discards the result. Naming the ids requires having found the component; once found, rendering it is a descent that already exists and already terminates. It also leaves the operator's next move as `sq tree <id>`, a command that works today — which makes the warning a signpost to the thing we declined to do.
    - **Refuse the command.** Reinstates the blast radius BUG-865 was filed for: a two-item cycle between unrelated bugs denies the whole hierarchy to a coordinator with no connection to it. It also contradicts the constraint the fix already accepted — the read path must tolerate a corpus the write door refuses, because `repair`, `adopt` and hand-edited frontmatter are doors the gate never sees. TASK-866 says exactly that. Refusal is the opposite of tolerance.
    
    On the implementer's reasoning: right to defer, wrong as a permanent answer. "Roots are the parentless forest" was never decided. `_build_tree_children` already buckets an item whose parent does not resolve inside the candidate set as a root, so the forest is already "no resolvable parent in view", not "parentless". Extending that to "no resolvable acyclic path to a root" widens a rule that already covers the analogous case. The scoping call was correct; the reasoning that justified deferring does not justify keeping.
    
    Accepted failure mode. **The anchor is a fabrication.** In a five-item cycle every member is an equally good root, so the choice is a tiebreak and not a truth: a reader — or a `--json` consumer — treating the root level as "the top of the hierarchy" gets one invented root per cyclic component. Accepted, because disclosed, and because the reader can recover from a marked anchor while they cannot recover from an item that does not exist. Second and smaller: any tree rendering of a cycle must drop at least one edge (the one closing back to the anchor), so the tree under-reports the relation it draws — `sq check` names both endpoints and is where the full edge set lives. What I do not accept is an exit-code change: a tree that rendered everything asked for did not fail, and the exit-code table is read by wrapper scripts and the VS Code client.
    
    Bare vs targeted. **Not acceptable; they must agree.** The two forms may legitimately differ in *scope* — which subtree you asked about — never in *existence*. Rooting at BUG-12 proves the component is renderable and terminating, so the bare form's omission is a coverage gap and not a scope decision, and no rule an operator could have known predicts which form shows them their data. Under this ruling they agree by construction: bare tree is the union of the targeted trees.
    
    Amendment: **none, and I judge this a settled implementation question rather than a changed decision.** No standing record says roots are the parentless forest, and nothing here contradicts one. It applies ADR-604's single-visibility-axis rule to a surface that had drifted out from under it, in the direction ADR-783 already set (a corpus condition is disclosed loudly and reported by check, never converged away quietly) and the direction TASK-866 took for the doors the gate cannot reach. Amending ADR-864 would be wrong on hosting grounds — it owns the validator catalog, and this is the read path.
    
    Flagged, not filed: if the team wants the coverage property (tree covers list at equal filters) on the 1.0 contract rather than living only as a test, that is its own record under the standing rule that contract decisions land in an ADR. @tech-lead @manager your call whether it earns one; I am not creating it off this ruling.
- [2026-09-02T10:09:36Z] Olivia Lead:
  - Fix scoped as TASK-877 (fixes ref), three subtasks, assigned to the python dev. The
    ruling is adopted as written and I am not reopening any of it; what follows is what I
    found when I checked it against the code, plus the ordering call.
    
    The anchor design is sound and I verified the property it rests on rather than assuming
    it: every omitted item is a cycle member or a descendant of one, because a cycle member's
    parent is always another cycle member, so nothing in the component sits above the cycle.
    One anchor per component therefore reaches the whole component through the descent that
    already exists. Also verified the premise about the forest rule — the parent grouping does
    already bucket an item whose parent does not resolve inside the candidate set as a root,
    so this widens an existing rule rather than inventing one.
    
    The anchor trap is in the task body, worded as the difference between the two rules and
    with a required test case that separates them: an item below the cycle with a lower
    sequence number than every cycle member. Without that case the wrong rule ships green,
    which is the whole reason the trap is worth naming.
    
    **Four things I do not think survive contact with the code**, all now handled in the task:
    
    1. **`path_only` is not on the wire.** The anchor flag was specified as sitting "beside
       `path_only`" in `--json`. It cannot, because `path_only` is not emitted — the JSON node
       carries id, type, title, status, priority, assignee, blocked, badges and children and
       nothing else, and `path_only` lives only on the internal node and as a dim style in the
       terminal. Ruled: ship the anchor flag, since the disclosure requirement stands on its
       own for a JSON consumer, and do not add `path_only` as a rider — that is a separate
       widening of a published shape.
    2. **The coverage property is false as worded, and already false today.** Driven on the
       live corpus: list and tree agree exactly at 848 with no depth bound, and the tree drops
       to 608 at depth 1. A depth bound legitimately makes the tree a subset. The acceptance
       clause is scoped to the no-depth case; written the other way it would be red for a
       reason that is not this bug.
    3. **Detection has to run on the candidate set, not the corpus.** A cycle in the index is
       not necessarily a cycle in the view — filter one member out and the survivors form a
       chain whose top already has no resolvable parent in view, already becomes a root, and
       already renders. Detecting against the full index would fabricate an anchor for a
       component that is not broken, or name one that is not in the view at all.
    4. **The anchor and `path_only` can be true at once** — under a filter matching something
       below the cycle, the members enter the keep set as ancestors. The terminal label helper
       takes `path_only` as its only state and dims on it, so the two have to combine rather
       than alternate, and a dimmed anchor marker is easy to produce and hard to read.
    
    **One gap the ruling's own justification depends on, and it is not closed here.** The VS
    Code client maps the JSON tree through a fixed field list, so an added field is genuinely
    safe on the wire — but the client will therefore render the fabricated anchor as an
    ordinary root with no visual distinction. The disclosure that makes the fabrication
    acceptable holds in the terminal and silently does not hold in the client. That is a
    TypeScript change in another tree with another owner; it is out of scope here and named in
    the task so it is flagged on handoff rather than discovered. @manager it needs its own
    item.
    
    On the flagged-not-filed question — whether the coverage property belongs on the 1.0
    contract rather than living only as a test: my view is yes, but not off this task. It is a
    statement about the relationship between two read surfaces, it outlives this fix, and the
    standing rule is that contract decisions land in a decision record rather than in a test
    name. I would rather it be written once, deliberately, than inferred later from an
    assertion. @architect @manager not blocking anything here either way.
- [2026-09-02T10:24:41Z] Mara Tester:
  - Client-side half of the disclosure filed as BUG-879 (`related` here, `depends-on` the tree
    task). Verified the field-mapping claim at the source: it holds through all four hops, and
    the skew canary asserts node keys with `arrayContaining` — a superset assertion, so a new
    `anchor` key passes and the gap ships green rather than going red later. @tech-lead
- [2026-09-02T14:18:21Z] Mara Tester:
  - Verified. Two independent seven-item corpora, each a fresh `sq init --default-names --backend none` with the cycle written into frontmatter by hand and indexed with `sq repair`. Exit codes read from bare commands; every tree run under `timeout 60` and none came close to it.
    
    Corpus 1 — the body's own repro (five-item cycle BUG-10 -> BUG-14 -> BUG-13 -> BUG-12 -> BUG-11 -> BUG-10, mixed padding widths, BUG-15 hanging off BUG-12):
    - `sq check` -> exit 3, six errors (five cycle members plus the item below it), unchanged
    - `sq tree -a` -> exit 0 and renders all seven bugs; the previous behaviour rendered one. Anchor line: "BUG-10 C1 (Open)  [cycle anchor — not a real root; see sq check]"
    - `sq tree -a -t bug` -> exit 0, same seven
    - Coverage at equal filters, no depth bound: `sq list -a --json` 15 items vs `sq tree -a --json` 15 distinct across 15 node occurrences — no item missing, none extra, no duplicates
    - `--json`: `anchor: true` on BUG-10 and only BUG-10; every other node carries `anchor: false`. Key sits alongside id/type/title/status/priority/assignee/blocked/badges/children
    
    Corpus 2 — the case the trap needed (cycle over BUG-11..BUG-15; BUG-10 "Low" hangs below BUG-13 and has a lower sequence number than every cycle member):
    - anchor chosen is **BUG-11**, the lowest-sequence cycle member — not BUG-10
    - BUG-10 renders exactly **once**, as a descendant of BUG-13; occurrence count 1
    - coverage again 15 vs 15, no duplicates
    - the wrong rule ("lowest unrendered keep-set item") would have anchored BUG-10 and rendered it twice; it does not
    
    Also driven:
    - `sq tree BUG-13 -a` (targeted, rooted inside the cycle) still renders the component and truncates at the repeat — bare and targeted now agree on existence
    - `sq tree -a --depth 1` is a legitimate subset and still marks the anchor
    - anchor + path-only combined: with `--assignee qa` matching only the item below the cycle, the cycle members enter as path-only ancestors and the anchor marker is still present on BUG-11 in both the rendering and `--json`
    - `sq tree --help` documents the anchor, its tiebreak nature and the `anchor` JSON key
    
    Nothing to flag. The known accepted cost stands as ruled: the edge closing back to the anchor is not drawn, and `sq check` remains the surface that names both ends.
<!-- sq:discussion:end -->
