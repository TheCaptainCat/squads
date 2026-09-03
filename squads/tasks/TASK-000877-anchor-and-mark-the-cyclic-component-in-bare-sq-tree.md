---
id: TASK-877
sequence_id: 877
type: task
title: Anchor and mark the cyclic component in bare sq tree
status: Ready
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-870:fixes
- TASK-849:depends-on
description: Bare tree omits every item in or under a parent cycle at exit 0; anchor
  each cyclic component at a cycle member, mark the anchor, and pin coverage against
  list.
subentities:
- local_id: ST1
  title: Anchor each cyclic component in the bare tree's roots
  status: Todo
- local_id: ST2
  title: Mark the anchor in the rendering and on the wire
  status: Todo
- local_id: ST3
  title: Pin coverage and bare-versus-targeted agreement
  status: Todo
created_at: '2026-09-02T10:08:03Z'
updated_at: '2026-09-02T10:09:55Z'
---
<!-- sq:body -->
## What is wrong

On a corpus carrying a parent cycle, bare `sq tree` renders a tree that looks complete,
exits 0, and leaves out every item in the cycle and everything hanging beneath it. The
measurement is seven items returned by `sq list` against one rendered by `sq tree`, on a
fixture of a five-item cycle plus one item hanging off it. Nothing on the tree surface
says anything is missing.

Rooting explicitly inside the cycle already renders the whole component correctly,
truncated at the repeat. So the component is renderable and the descent terminates; only
the bare form's root computation drops it.

The cause is that the bare form's roots are the parentless forest. Every cycle member has
a parent by definition — another cycle member — so nothing anchors the component, and
everything below it is likewise never parentless.

## The decision being implemented

A cyclic component must appear in bare `sq tree`, anchored at a cycle member and truncated
at the repeat exactly as a tree rooted inside the cycle already renders it.

**The exit code does not change.** A tree that rendered everything asked for did not fail.
The exit-code table is read by wrapper scripts and by the VS Code client, and it is not in
scope here on any argument. The integrity check stays the diagnostic for the condition and
keeps its own exit code; no new check rule ships with this.

Three properties are required:

1. **Coverage.** At equal filters and with no depth bound, every item `sq list` returns
   appears somewhere in `sq tree`. Seven-versus-one becomes seven-versus-seven. Ancestors
   pulled in as path-only anchors may make the tree a superset; it may never be a subset.
2. **The anchor is deterministic and is a cycle member** — the lowest sequence number
   among the items that close the loop.
3. **The anchor is marked as an anchor**, in the rendering and in `--json`. An unmarked
   anchor replaces a quiet omission with a quiet fabrication, which is not an improvement.

## The trap in property 2 — read this twice

"Lowest sequence number among the items that close the loop" is **not** the same rule as
"lowest unrendered item in the keep set", and the second one is the rule an implementer
derives from a summary.

They differ exactly where it hurts. An item hanging *below* the cycle with a lower
sequence number than any cycle member satisfies the second rule and not the first. Under
the second rule that item anchors itself, and then renders a second time as a child when
the descent reaches it through the cycle — the same item at two places in one tree, which
the indentation presents as two different nodes.

The anchor must be chosen from the set of items that are *on* the cycle. Each omitted item
appears exactly once.

Two corollaries that follow and are easy to miss:

- **Per component, not per corpus.** Two disjoint cycles need two anchors. "The lowest
  sequence among cycle members" read globally anchors one component and leaves the other
  exactly as broken as it is today.
- **One anchor per component is sufficient, and this is provable rather than hopeful.**
  Every omitted item is either a cycle member or a descendant of one — a cycle member's
  parent is always another cycle member, so nothing in the component sits *above* the
  cycle. The existing descent from any single member therefore reaches the whole
  component. Do not add per-item anchoring on top.

## Where the code actually is, and four things the summary will not tell you

Read these before designing. Each was verified against the source, and three of them
contradict something a reasonable implementer would assume.

**The forest rule is already wider than "parentless".** The parent→children grouping
buckets an item under `None` when its stored parent does not resolve to a member of the
candidate set — so the root set is already "no resolvable parent in view", not
"parentless". Extending it to "no resolvable acyclic path to a root" widens a rule that
already covers the analogous case, rather than inventing one. Start there.

**Detect on the candidate set, not on the corpus.** The candidate set drops
hidden-by-default items unless closed items are included, and the grouping resolves
parents only within it. A cycle in the corpus is not necessarily a cycle in the view: if
one member is filtered out, the survivors form a chain whose top has no resolvable parent
in view, so it already becomes a root and already renders. Detecting cycles against the
full index would fabricate an anchor for a component that is not broken, and could pick an
anchor that is not in the view at all. The graph the anchor is computed on must be the same
graph the roots come from.

**`path_only` is not on the wire.** The decision describes the anchor flag as sitting
"beside `path_only`" in `--json`. It does not, because `path_only` is not emitted at all —
the JSON node carries id, type, title, status, priority, assignee, blocked, badges and
children, and nothing else. `path_only` exists only on the internal node and as a dim style
in the terminal rendering. Ship the anchor flag, because the disclosure requirement applies
to a JSON consumer independently. Do **not** add `path_only` to the wire as a rider — that
is a separate widening of a published shape and nobody has asked for it. Say in your
handoff that the asymmetry is deliberate, so the next reader does not file it as an
oversight.

**The anchor and `path_only` can be true at once.** Under a filter that matches something
below the cycle, the cycle members enter the keep set as ancestors, so the chosen anchor is
a path-only node *and* the anchor. The terminal label helper currently takes `path_only`
as its only state and dims on it. Handle the two as independent flags that can combine,
not as alternatives — and check what the combination looks like when rendered, because a
dimmed anchor marker is easy to produce and hard to read.

## Accepted failure modes — disclose, do not fix

These were weighed and accepted. Do not try to engineer them away, and do not treat either
as a defect found in review.

- **The anchor is a fabrication.** In a five-item cycle every member is an equally good
  root, so the choice is a tiebreak and not a truth. A reader treating the root level as
  "the top of the hierarchy" gets one invented root per cyclic component. This is accepted
  *because it is disclosed*, which is the entire reason property 3 exists. A reader can
  recover from a marked anchor; they cannot recover from an item that does not exist.
- **The rendering drops one edge.** Any tree drawing of a cycle must omit the edge closing
  back to the anchor, so the tree under-reports the relation it draws. The integrity check
  names both endpoints and is where the full edge set lives.

## Known gap, out of scope, but state it in your handoff

The VS Code client maps the JSON tree through a fixed field list and will ignore an
unknown field, so adding the flag is safe on the wire — but it means the client will render
the fabricated anchor as an ordinary root with **no visual distinction**. The disclosure
that justifies the whole design is satisfied in the terminal and silently not satisfied in
the client.

That is a TypeScript change in the client, a different owner and a different tree, and it
is not being folded in here. It does need its own item. Do not touch the client; do call
it out when you hand back, so it is filed rather than discovered.

## Acceptance

The fixture is the driven one from the report: seven items, a five-item cycle with mixed
zero-pad widths written into frontmatter plus one item hanging off a cycle member, indexed
through a rebuild. Build it as a fixture, not as a hand-run.

- **Coverage, falsifiable.** At equal filters and with no depth bound, the set of ids
  returned by `sq list` equals or is contained in the set of ids rendered by `sq tree`.
  Seven and seven on the fixture. Assert on id sets, not on counts — a count matches by
  accident.
- **Bare equals the union of the targeted trees, on existence.** For every id `sq list -a`
  returns, `sq tree <id> -a` renders it and bare `sq tree -a` renders it. The two forms may
  differ in scope; they may never differ in whether an item exists. This is the clause that
  makes the coverage property specific rather than aspirational, and it is falsifiable
  today: it fails on the fixture before the fix.
- **Each item appears exactly once** in the bare rendering. Assert it directly by counting
  occurrences per id across the whole rendered tree — this is the assertion that catches
  the wrong anchor rule, and a test that only checks presence will pass with the bug in.
- **The anchor is a cycle member**, and is the lowest sequence number among them. Include a
  case where an item below the cycle has a lower sequence number than every cycle member;
  this case fails under the wrong rule and passes under the right one, and without it the
  wrong rule ships green.
- **Two disjoint cycles get two anchors**, both rendered, no item duplicated across them.
- **The anchor is marked** in the terminal rendering and as a field in `--json`.
- **The exit code is 0**, unchanged, on every form. Read it from a bare invocation
  (`cmd >/dev/null 2>&1; echo $?`), never through a pipe — a pipeline reports the last
  element's status.
- **A corpus with no cycle renders identically to before.** This is the regression that
  matters most: the change is in the root computation, which every tree call goes through.
  Pin it against the existing behaviour, not against a fresh reading of it.
- **Depth still wins.** A depth bound legitimately makes the tree a subset of the list;
  that is existing behaviour and is not a coverage violation. Do not write the coverage
  assertion in a form that a depth bound falsifies.
- **The tests fail before the fix.** Break it, watch each go red, restore it, watch it go
  green, and report both. Name tests by behaviour — no ticket identifier in a test name, a
  file name, or a source comment.
- `uv run --all-extras pytest`, `ruff check .`, `ruff format --check .`, `pyright` and
  `sq check` all clean. `--all-extras` on each; a bare `uv run` prunes the optional tui
  extra and pyright then reports hundreds of false import errors.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 877 add-subtask "<title>"`; track with `sq task 877 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Anchor each cyclic component in the bare tree's roots

<!-- sq:subtask:ST1:body -->
The core change, in the root computation the bare form uses.

Extend the rule that produces the forest from "no resolvable parent in view" to "no
resolvable acyclic path to a root". The grouping already buckets an item whose stored
parent does not resolve inside the candidate set as a root, so this widens a rule that
already covers the analogous case rather than introducing a new concept.

Compute the cycle membership on the **candidate set** — the same filtered graph the roots
come from — not on the full index. A cycle in the corpus is not necessarily a cycle in the
view: with one member filtered out, the survivors form a chain whose top already has no
resolvable parent in view, already becomes a root, and already renders correctly today.
Detecting against the index would fabricate an anchor for a component that is not broken,
and could name an anchor that is not in the view at all.

Choose the anchor from the items that are **on** the cycle — lowest sequence number among
them — and do this per component. Re-read the trap section in the task body before writing
the selection: the plausible-looking alternative rule renders one item twice.

Identity is the sequence number, not the id string, throughout. The stored parent may
carry a different zero-pad width than the item's own id, which is why the surrounding
resolution already works that way, and the fixture deliberately mixes widths.

Do not add per-item anchoring. One anchor per component reaches the whole component,
because nothing in the component sits above the cycle.

Done when: the fixture renders all seven items from the bare form at exit 0, each exactly
once; two disjoint cycles produce two anchors; a corpus with no cycle renders identically
to before; and the anchor is a cycle member even when a lower-sequence item hangs below
the cycle.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Mark the anchor in the rendering and on the wire

<!-- sq:subtask:ST2:body -->
Disclosure. This is the half that makes the fabricated root defensible, so it is not
cosmetic and does not get deferred to a follow-up.

Mark the anchor in the terminal rendering and as a field in `--json`.

Two facts about the current surfaces that the decision's wording does not reflect, both
verified:

- **`path_only` is not on the wire.** The JSON node carries id, type, title, status,
  priority, assignee, blocked, badges and children, and nothing else; `path_only` lives
  only on the internal node and as a dim style in the terminal. So "a flag beside
  `path_only`" describes a neighbour that does not exist. Add the anchor flag — the
  disclosure requirement applies to a JSON consumer on its own merits — and do **not** add
  `path_only` to the wire while you are there. That is a separate widening of a published
  shape that nobody has asked for. Note the asymmetry in your handoff so the next reader
  does not file it as an oversight.
- **The anchor and `path_only` can both be true.** Under a filter matching something below
  the cycle, the cycle members enter the keep set as ancestors, so the anchor is a
  path-only node as well. The terminal label helper currently takes `path_only` as its
  only state and dims on it. Treat them as independent flags that combine, and look at the
  rendered result — a dimmed anchor marker is easy to produce and hard to read.

The marker's job is to stop a reader concluding that the anchor is a root somebody wrote.
Whatever form it takes should read that way to someone who has never heard of this change.

Done when: the anchor is visibly marked in the terminal and carries a field in `--json`;
the combined anchor-and-path-only case renders legibly; `path_only` is still absent from
the wire; and the JSON addition is purely additive, with every existing field unchanged in
name and meaning.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Pin coverage and bare-versus-targeted agreement

<!-- sq:subtask:ST3:body -->
Turn the two properties into assertions that fail today, so the class is pinned rather
than this instance patched.

**Coverage.** At equal filters and with no depth bound, the ids `sq list` returns are
contained in the ids `sq tree` renders. Assert on id sets, never on counts — a count
matches by accident, and the fixture is small enough that it would.

Scope the assertion so a depth bound cannot falsify it. A depth bound legitimately makes
the tree a subset of the list; that is existing, correct behaviour. Driven on the live
repository corpus for calibration: list and tree agree exactly with no depth bound, and
the tree drops to well under the list at depth 1. Write the invariant for the no-depth
case only, or it will be red for a reason that is not a bug.

**Bare equals the union of the targeted trees, on existence.** For every id the list
returns, the tree rooted at that id renders it and the bare tree renders it. The two forms
may differ in scope — which subtree you asked about — never in whether an item exists.
This is the clause that makes coverage specific instead of aspirational, and it fails on
the fixture before the fix.

**Exactly once.** Count occurrences per id across the whole bare rendering and assert one.
This is the assertion that catches the wrong anchor rule; a test that only checks presence
passes with the bug in. Include the case where an item below the cycle has a lower
sequence number than every cycle member — without it, the wrong rule ships green.

**Exit code unchanged at 0** on every form, read from a bare invocation and never through
a pipe.

Falsify each one before handing back: break the fix, watch it go red, restore it, watch it
go green, and report both with what it printed.

Done when: the coverage and agreement invariants exist as tests, are shown red before the
fix and green after, and are written so a depth bound does not falsify them.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T10:09:55Z] Olivia Lead:
  - Scoped from BUG-870 against the architect's ruling, which is adopted as written. No design
    call is left open for the implementer; the four places the ruling's wording does not match
    the code are resolved in the body rather than left to be rediscovered.
    
    **Ordering: this lands after the corpus strip, not before.** Recorded as a depends-on edge
    so the board shows it rather than only this comment. Four reasons, in the order they
    weigh:
    
    - **A live file collision, not a hypothetical one.** The strip work currently has the CLI
      main module open in the working tree for its repair announcement, and this change has to
      edit the tree command in that same file. Two agents mutating one file is the pattern that
      has already produced a spurious review finding on this project.
    - **One variable at a time through the read path.** The strip rewrites over a thousand
      files and its diff gets reviewed through the read surfaces. Changing what the tree
      renders mid-flight means a reviewer cannot tell a strip artefact from a tree-semantics
      change.
    - **Reversibility asymmetry.** The strip is a wide corpus rewrite; this is code-local and
      revertible in one commit. Land the irreversible, wide-blast-radius change first, while
      the read path is still the known-good one that was used to verify it.
    - **Nothing is lost by going second.** The fixture is a synthetic seven-item scratch squad,
      so this needs no particular state of the real corpus. And the gain does not apply to the
      strip's own verification anyway: the cycle validator is on the floor at error level and
      the integrity check is clean here, so this repository's corpus has no cycle and its tree
      is unaffected by this change either way.
    
    The strip is already in review, so this is a short sequence rather than a real block.
    
    Two things to hold the implementer to on handoff, both in the acceptance: the anchor test
    must include an item below the cycle with a lower sequence number than every cycle member
    (without it the wrong anchor rule passes green), and the client gap must be reported, not
    fixed here.
    
    @python-dev ready for dispatch once the strip lands.
<!-- sq:discussion:end -->
