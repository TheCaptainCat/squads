---
id: FEAT-000288
sequence_id: 288
type: feature
title: Pre-merge ID block-shift renumber (sq renumber)
status: Draft
parent: EPIC-000012
author: product-owner
refs:
- FEAT-000283:depends-on
- ADR-000282
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
updated_at: '2026-07-03T08:19:08Z'
---
<!-- sq:body -->
Problem. squads allocates IDs from a single global monotonic counter in .squads.json. When two collaborators work on separate git branches/clones, each runs sq create and both mint the same sequence number (both branch at counter 287 -> both create item 288). On merge you get duplicate global IDs.

Today's sq repair --renumber is only a post-merge cleanup: its remap is keyed by the old ID string, and since both collided items share that string, rewrite_ids does a blind whole-word substitution that repoints EVERY reference to the one renamed winner. It guarantees uniqueness and no dangling refs, but it cannot preserve referential intent -- a ref that meant the item which kept the number gets silently moved to the renamed one. That existing behavior stays as the 'too late, make it valid' fallback.

Capability. A pre-merge block-shift renumber, run on the branch that yields, while every reference on that branch is still unambiguous. It reserves a contiguous ID block above the other branch's counter and offsets this branch's new items into it, so no two items ever claim the same number in one tree -- intent is preserved because the rewrite happens before the ambiguity exists.

Shape (capability + AC, not final CLI spec): a command/mode that block-shifts a contiguous ID range, e.g. sq renumber --from <id> --onto <counter> or --by <n>. The boundary ('which IDs are branch-local') comes from the operator naming it (the other branch's counter at branch time, readable via git show <mainref>:squads/.squads.json) or derived from git merge-base (items with sequence_id > base_counter).

Disjoint-block guarantee. Choose the offset so the shifted block lands strictly above the other branch's counter, so old and new ranges are disjoint. A single-pass whole-word substitution is then safe and iteration order is irrelevant -- the high-to-low ordering used by in-place shifts is only needed when ranges can overlap.

Reuse the existing machinery: file rename + rewrite_ids whole-word swap across frontmatter id:/refs, body prose, inline ID mentions, AND the append-only reflog (its target fields reference IDs -- must be included or history stops resolving), plus sequence_id resync and counter bump to the new max.

Filenames stay padded to the filename width (see FEAT-000283/ADR-000282) so on-disk lexical sort survives -- the rename seam reformats through the canonical format_item_id(prefix, seq, filename_padding).

Dependency. Sequenced after FEAT-000283 (Unpadded display IDs, decoupled from filename padding; ADR-000282). Once display/refs/prose are unpadded, the prose rewrite becomes a plain \bFEAT-210\b -> FEAT-220 integer swap -- the leading-zero capture group and the 'reformat to width' trap disappear for everything a human/ref touches, and uniform unpadding removes FEAT-210 vs FEAT-000210 matcher-miss variance. Padding then only remains at the filename-rename seam.
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
As an operator, after a block-shift the renamed files are still padded to the squad's filename width (format_item_id(prefix, seq, filename_padding)) so on-disk lexical sort is unaffected, even though display/prose forms may be unpadded per FEAT-000283.
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
  - Grammar-settling work under EPIC-000012 (ID-space renumbering). Owes @manager a deferral note to FEAT-000013 (stability-contract capstone) when that runs.
<!-- sq:discussion:end -->
