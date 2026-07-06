---
id: FEAT-288
sequence_id: 288
type: feature
title: Pre-merge ID block-shift renumber (sq renumber)
status: Done
parent: EPIC-12
author: product-owner
refs:
- FEAT-283:depends-on
- ADR-282
- ADR-295:implements
description: Block-shift a branch's new IDs into a reserved range before merge, preserving
  referential intent
subentities:
- local_id: US1
  title: Pre-merge shift preserves referential intent
  status: Todo
- local_id: US2
  title: Shifted block is disjoint from the other branch's range
  status: Todo
- local_id: US3
  title: Reflog and inline ID mentions are rewritten, not just frontmatter
  status: Todo
- local_id: US4
  title: Filenames keep their padded width after a shift
  status: Todo
- local_id: US5
  title: Pre-merge shift and post-merge --renumber coexist
  status: Todo
created_at: '2026-07-03T08:18:39Z'
updated_at: '2026-07-06T10:18:42Z'
---
<!-- sq:body -->
Problem. squads allocates IDs from a single global monotonic counter in .squads.json. When two collaborators work on separate git branches/clones, each runs sq create and both mint the same sequence number (both branch at counter 287 -> both create item 288). On merge you get duplicate global IDs.

Today's sq repair --renumber is only a post-merge cleanup: its remap is keyed by the old ID string, and since both collided items share that string, rewrite_ids does a blind whole-word substitution that repoints EVERY reference to the one renamed winner. It guarantees uniqueness and no dangling refs, but it cannot preserve referential intent -- a ref that meant the item which kept the number gets silently moved to the renamed one. That existing behavior stays as the 'too late, make it valid' fallback.

Capability. A pre-merge block-shift renumber, run on the branch that yields, while every reference on that branch is still unambiguous. It reserves a contiguous ID block above the other branch's counter and offsets this branch's new items into it, so no two items ever claim the same number in one tree -- intent is preserved because the rewrite happens before the ambiguity exists.

Shape (capability + AC, not final CLI spec): a command/mode that block-shifts a contiguous ID range, e.g. sq renumber --from <id> --onto <counter> or --by <n>. The boundary ('which IDs are branch-local') comes from the operator naming it (the other branch's counter at branch time, readable via git show <mainref>:squads/.squads.json) or derived from git merge-base (items with sequence_id > base_counter).

Disjoint-block guarantee. Choose the offset so the shifted block lands strictly above the other branch's counter, so old and new ranges are disjoint. A single-pass whole-word substitution is then safe and iteration order is irrelevant -- the high-to-low ordering used by in-place shifts is only needed when ranges can overlap.

Reuse the existing machinery: file rename + rewrite_ids whole-word swap across frontmatter id:/refs, body prose, inline ID mentions, AND the append-only reflog (its target fields reference IDs -- must be included or history stops resolving), plus sequence_id resync and counter bump to the new max.

Filenames stay padded to the filename width (see FEAT-283/ADR-282) so on-disk lexical sort survives -- the rename seam reformats through the canonical format_item_id(prefix, seq, filename_padding).

Dependency. Sequenced after FEAT-283 (Unpadded display IDs, decoupled from filename padding; ADR-282). Once display/refs/prose are unpadded, the prose rewrite becomes a plain \bFEAT-210\b -> FEAT-220 integer swap -- the leading-zero capture group and the 'reformat to width' trap disappear for everything a human/ref touches, and uniform unpadding removes FEAT-210 vs FEAT-210 matcher-miss variance. Padding then only remains at the filename-rename seam.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 288 add-story "As a <role>, I want … so that …"`; track with `sq feature 288 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Pre-merge shift preserves referential intent |
| US2 | Todo |  | Shifted block is disjoint from the other branch's range |
| US3 | Todo |  | Reflog and inline ID mentions are rewritten, not just frontmatter |
| US4 | Todo |  | Filenames keep their padded width after a shift |
| US5 | Todo |  | Pre-merge shift and post-merge --renumber coexist |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Pre-merge shift preserves referential intent

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a collaborator merging branches, when I block-shift my branch's IDs before merging, refs that pointed at my items still point at my items after the shift (unlike post-merge --renumber, which can silently repoint a collided ref to the item that kept the number).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Shifted block is disjoint from the other branch's range

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As an operator naming the boundary (--from/--onto/--by, or derived via git merge-base), the tool refuses or computes an offset that lands my shifted block strictly above the other branch's counter, so old and new ranges never overlap and single-pass whole-word substitution is safe regardless of processing order.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Reflog and inline ID mentions are rewritten, not just frontmatter

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As an operator running the shift, every occurrence of a shifted ID is updated: frontmatter id:/refs, body prose mentions, AND the append-only reflog's target fields -- so history still resolves and no reference is left dangling or stale.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Filenames keep their padded width after a shift

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As an operator, after a block-shift the renamed files are still padded to the squad's filename width (format_item_id(prefix, seq, filename_padding)) so on-disk lexical sort is unaffected, even though display/prose forms may be unpadded per FEAT-283.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Pre-merge shift and post-merge --renumber coexist

<!-- sq:story:US5:head -->
**Status:** ⚪ Todo
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
As an operator, pre-merge block-shift is the preferred path when I control the yielding branch ahead of merge; post-merge sq repair --renumber remains available as the 'too late, make it valid' fallback for collisions that already happened -- the two are documented as complementary, not as one replacing the other.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-03T08:19:08Z] Nina Product:
  - Grammar-settling work under EPIC-12 (ID-space renumbering). Owes @manager a deferral note to FEAT-13 (stability-contract capstone) when that runs.
- [2026-07-05T20:55:10Z] Olivia Lead:
  - ADR VERDICT: an ADR is REQUIRED and must be Accepted before any implementation task is dispatched — mirroring how FEAT-283 built on ADR-282. No dev-ready tasks created yet (see task-shape sketch below). Reasoning: sq renumber is a NEW public CLI command entering the frozen 1.0 grammar surface, operating directly on the identity system, with several load-bearing design choices that are not mechanical and that touch two already-Accepted ADRs (114/117 reflog, 72 global counter). Pinning the CLI spec and these semantics in a dev task now would bake in unratified choices; the feature body itself says 'capability + AC, NOT final CLI spec.'
  - The ADR must decide: (1) FINAL CLI SPEC — the exact surface (--from/--onto/--by, which subset, their semantics, whether it's 'sq renumber' or a mode of 'sq repair'), so it enters the 1.0 grammar deliberately, not by dev improvisation. (2) BOUNDARY DERIVATION — how 'which IDs are branch-local' is determined: operator-named counter vs derived from git merge-base. CRITICAL: sq has ZERO git dependency today (verified — no subprocess/git invocation anywhere in src/). A merge-base derivation would introduce git-awareness into the tool for the first time — an architectural boundary decision, not an impl detail. The ADR must rule whether sq stays git-agnostic (operator supplies the boundary, e.g. via git show <ref>:squads/.squads.json read OUTSIDE sq) or takes on an optional git dependency.
  - The ADR must also decide: (3) DISJOINT-BLOCK GUARANTEE — how the offset is chosen/validated so the shifted block lands strictly above the other branch's counter, and what the command does when it can't guarantee disjointness (refuse vs compute). This is what makes the single-pass whole-word substitution safe regardless of order. (4) REFLOG REWRITE — the sharp one. ADR-117 establishes the reflog as append-only, advisory, and 'explicitly NOT a source of truth' (repair never reads it). FEAT-288 proposes rewriting historical reflog 'target' fields (and any IDs inside 'delta' payloads for ref/link ops) in place. That is in direct tension with the append-only contract. The ADR must rule: is an in-place history rewrite legitimate for a renumber (git-filter-branch analogy), or does the reflog get an append-only 'renumber' entry and leave old lines as-is (stale but honest)? Since the reflog is explicitly not a source of truth, leaving it un-rewritten may be defensible — but that contradicts the feature's 'history stops resolving' claim, so it needs an explicit ruling, not a dev's guess. (5) COEXISTENCE — how the pre-merge shift and post-merge 'repair --renumber' are documented as complementary (preferred path vs 'too late, make it valid' fallback), and whether they share the _renumber_plan/rewrite_ids machinery.
  - Reuse note for the ADR/impl: the machinery already exists — rewrite_ids in _itemfile.py (whole-word \bOLD\b→NEW swap over frontmatter id:/refs + prose) is used by both _services/_maintenance.py::_renumber (post-merge) and _services/_retype.py. The pre-merge shift should reuse _renumber_plan/rewrite_ids, extended with the reflog target/delta fields per decision (4) and sequence_id resync + counter bump to the new max. Filenames stay padded at the filename width via format_item_id(prefix, seq, filename_padding) per ADR-282 — the depends-on FEAT-283 (Done) already unpadded display/prose, so the prose rewrite is now a plain integer swap with no leading-zero trap; padding survives only at the filename-rename seam.
  - Eventual task shape (sketch only — do NOT create until the ADR is Accepted; then map subtasks to US1-US5): T-a 'Boundary resolution + disjoint-offset planner' (US2 — compute/validate the offset, refuse on overlap) — depends on ADR decisions 2+3; T-b 'Block-shift executor reusing rewrite_ids' (US1 — files+frontmatter+refs+prose, intent-preserving because it runs pre-ambiguity) — decision 1; T-c 'Reflog + inline-mention rewrite' (US3) — decision 4, the ADR gates this most; T-d 'Filename padding at the rename seam' (US4) — decision from ADR-282, likely folds into T-b; T-e 'Coexistence docs + repair --renumber delineation' (US5) — decision 5. @manager: route the ADR to the architect (Robert) and gate 288's implementation on its acceptance.
  - Deferral note owed: this is grammar-settling work under EPIC-12; per Nina it owes FEAT-13 (stability-contract capstone) a deferral note when that runs — the sq renumber CLI spec the ADR pins becomes part of the 1.0 grammar FEAT-13 freezes.
- [2026-07-06T08:48:33Z] Olivia Lead:
  - BREAKDOWN (Draft, awaiting @manager promotion to Ready at dispatch). ADR-295 Accepted, so tasks now created. 5 tasks under FEAT-288, mapping the ADR's five rulings to US1-US5:
  - TASK-297 Extract shared renumber executor from _renumber apply-path (US5) — pure refactor lifting rewrite_ids->rename->sequence_id resync into one executor both sq renumber and repair --renumber call (ADR §5). No behaviour change; repair stays green. No deps.
  - TASK-298 Disjoint block-shift offset planner --from/--onto/--by (US2 + US4) — operator integers -> validated disjoint offset (delta = max(M,C)+1-N for --onto; refuse unsafe --by, exit 1, no files touched) -> remap (unpadded) + padded renames (US4 seam). sq stays git-agnostic (ADR §2/§3). depends-on TASK-297.
  - TASK-299 Add sq renumber CLI verb (US1) — new top-level 1.0 verb wiring planner->executor, intent-preserving pre-merge shift, counter bump to new max, atomic transaction (ADR §1). NOT a mode of repair. depends-on TASK-297, TASK-298.
  - TASK-300 Append renumber reflog event; leave history literal (US3) — one summary {from,onto,by,remap} event, NO in-place rewrite of historical target/delta (ADR §4, the sharp one); verify inline-mention rewrite via rewrite_ids. depends-on TASK-299.
  - TASK-301 Coexistence docs (US5) — sq renumber preferred pre-merge vs repair --renumber fallback post-merge, complementary not replacement (ADR §5); --onto recipe via git show ...:squads/.squads.json | jq .counter, kept git-agnostic. depends-on TASK-299.
  - DISPATCH ORDER: TASK-297 first (enabling refactor) -> TASK-298 (planner) -> TASK-299 (verb) -> then TASK-300 and TASK-301 in parallel. 297+298 could overlap on one dev but 298 depends-on 297 for a stable executor/remap contract.
  - FEAT-13 DEFERRAL TOUCHPOINT (owed per Nina + ADR-295 Consequences): two new items enter the frozen 1.0 grammar — the sq renumber verb grammar (--from/--onto/--by) and the new renumber reflog op + its delta shape. TASK-301 carries the deferral note; @manager please ensure FEAT-13 records both when it runs.
- [2026-07-06T10:18:42Z] Catherine Manager:
  - FEAT-288 complete. Delivered as sq renumber (standalone verb) per ADR-295: TASK-297 shared apply-path executor (repair --renumber unchanged), TASK-298 disjoint offset planner (--onto auto delta=max(M,C)+1-N, --by refuses when N+n<=C with no files touched), TASK-299 the verb + counter bump, TASK-300 the single append-only renumber reflog event (history left literal), TASK-301 coexistence docs + FEAT-13 grammar deferral note. Verified: REV-302 Approved (F1 IDs-in-source / F2 test strength / F3 transaction-text all Fixed), focused reflog-delta review clean, QA passed US1/US2/US4 on a throwaway squad, full suite 1610 passed/1 skipped, pyright+ruff clean, git-agnostic gate clean. Owes FEAT-13 the verb + reflog-op grammar entries (recorded on FEAT-13). Changes are in the working tree, uncommitted.
<!-- sq:discussion:end -->
