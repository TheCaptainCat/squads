---
id: ADR-398
sequence_id: 398
type: decision
title: Per-item derived Mermaid :graph region — refresh model and worth-it call
status: Accepted
author: architect
refs:
- FEAT-377:addresses
description: 'US2 defer: ref graph is non-local (unlike the local :summary), no clean
  refresh; ship US1, constrain US2 to sync-time+gated if built'
created_at: '2026-07-15T13:55:59Z'
updated_at: '2026-07-15T14:00:32Z'
---
<!-- sq:body -->
# Context

FEAT-377 (US2) proposes a new per-item sq-managed `:graph` marker region: fenced Mermaid,
derived from the item's ref graph, living in the item `.md` body so the shape renders inline
in VSCode/GitHub without running `sq`. The feature frames it as "analogous to the sub-entity
`:summary` block" (`_discussion.render_summary` / `ensure_summary`). This ADR fixes whether we
build it, and if so its placement, refresh model, and gating — because a new derived region on
every item file touches the marker surface (invariant #3) and the generated-file contract
(invariant #7), and the refresh-trigger question has no clean answer inherited from the
summary precedent.

# The asymmetry that decides this

The stated analogy to the sub-entity `:summary` breaks on the one axis that matters —
**invalidation scope**:

- The `:summary` / `:head` regions are **local**. A parent's summary is a pure function of that
  same file's own frontmatter (`Item.subentities`). One mutation touches one file; the refresh
  is a single in-place `replace_section` inside the same write. That locality is why the
  precedent is cheap and always-correct.
- An item's ref graph is **non-local**. `Service.graph(id, direction="both")` walks *other*
  items' refs to find backrefs (`_in_neighbours` scans the whole index), and by default filters
  out closed neighbours (`include_closed=False`). So the rendered graph for item X changes when:
  a ref is added/removed on X, **or on any other item pointing at X**, **or** any neighbour
  within `depth` changes status (open↔closed). A single `add_ref A→B` changes the correct
  rendering of A, B, and their depth-bounded neighbours — an unbounded fan-out, not one file.

`add_ref`/`rm_ref` today rewrite only the source item's frontmatter (one file, one transaction).
Nothing in the current mutation paths rewrites a *neighbour's* body. So "regenerated on mutation,
like `:head`/`:summary`" (the US2 acceptance line) is not achievable with the summary's
machinery — that machinery is local by construction and the graph is not.

# Options considered

- **A — eager global correctness.** On every ref/status/create mutation, recompute and rewrite
  the `:graph` region of every affected item within `depth`. Correct, but write-amplifying
  (one edge → N body rewrites), lock-contending, and staleness-prone: miss one trigger (e.g. a
  neighbour's status change) and a wrong diagram gets committed. High cost, fragile.
- **B — local-only ego graph.** Render only the item's *own* outgoing refs, ignoring backrefs
  and neighbour status, so it becomes a pure function of the file's own frontmatter (local, like
  the summary). Cheap and always-correct — but the result is near-worthless: "my own out-refs"
  is already in the frontmatter and in `sq show`, and it hides exactly the relationships (who
  depends on me) that make a graph interesting.
- **C — sync-time only.** Regenerate `:graph` solely in `sq sync` (which already walks all
  items), not on mutation. Sidesteps the fan-out, but `sq sync` does not run on every mutation,
  so the committed `.md` carries a **silently stale** diagram between syncs. A wrong-looking
  committed diagram is worse than none.
- **D — no persisted per-item region.** Do not commit a `:graph` region at all. Serve the same
  need on demand: `sq graph <id> --md` (US1) produces a fenced Mermaid subtree to paste into a
  PR/issue/doc when you actually want one.

# Decision

1. **Ship US1** (fenced `sq graph` output) — unblocked, low cost, high value; it is the honest
   home for "I want a rendered graph": on demand, always fresh, scoped to whatever root/depth
   the operator asks for.
2. **Recommend deferring US2** as specified. The premise (analogy to `:summary`) does not hold
   on the invalidation axis, and every persistence option is flawed: A is write-amplifying and
   stale-prone, B is correct-but-worthless, C commits silently-stale diagrams. Against that
   cost, the value is marginal — most items carry 0–2 refs (a 0-edge Mermaid flowchart renders
   nothing; a 1–2 edge one is already legible as text), and the graphs worth seeing are
   feature/dependency subtrees, which US1 serves better on demand. A committed per-leaf-item
   graph is visual noise on hundreds of files for little gain.
3. **If US2 is built anyway**, constrain it to the only honest shape: option **C+gate** —
   regenerate at `sq sync` time only (documented as sync-derived, not mutation-fresh), **gated**
   to items that actually have a graph worth showing (≥1 ref or a hosted subtree), and empty →
   no region at all, mirroring how `set_head` omits an empty `:head`. Do **not** claim
   mutation-time freshness, and do **not** wire fan-out rewrites into `add_ref`/`rm_ref`.

# Consequences

- Nothing new is stored in frontmatter under any option — the graph is always rederived from
  refs (invariant #1 holds).
- Declining the persisted region keeps the item `.md` templates (`templates/items/*.md.j2`)
  and the ~380 on-disk item files untouched — no migration-shaped rollout of a new region, no
  new marker tag on every file.
- If C+gate is later chosen: it adds one new marker tag, one renderer wrapping
  `graph_to_mermaid` in a ` ```mermaid ` fence, placement between `:summary`/`:stories` and
  `## Discussion` (a derived region sits with the other derived regions, above agent prose),
  scaffolded lazily like `set_head`. It goes through `_sections` (marker-safe, invariant #3)
  and is covered by the existing "`.md` files are sq-managed — never hand-edit" contract that
  satisfies invariant #7 for the sibling derived regions.

# Related — US3 surface (recommendation, not a rule this ADR imposes)

US3's spec-derived diagrams (item-type hierarchy + per-type lifecycle) belong in the generated
cheatsheet `workflow.md.j2` **only**, not in `docs/`. That template is already spec-derived
(loops `spec.items`, `linearize_lifecycle`, `parent_chain`), already regenerated by `sq sync`
(embedded in the `squads` skill body and rendered live by `sq workflow`), and is the home of
FEAT-334's genericized cheatsheet — so hierarchy/lifecycle Mermaid there stays correct for a
customized vocab for free, and degrades to a plain code fence in the Rich terminal. `docs/` is
static, bundled-vocab, adopter-facing prose that is not regenerated per squad; putting the
spec-derived diagrams there would force hardcoding the bundled types, which the US3 acceptance
and EPIC-325/EPIC-335 forbid.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T14:00:32Z] Catherine Manager:
  - Accepted — op-pierre cancelled US2 on this analysis. US1 (on-demand fenced sq graph) ships; the per-item persisted :graph region is not built. US3 lands in workflow.md.j2 per the recommendation.
<!-- sq:discussion:end -->
