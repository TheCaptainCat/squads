---
id: TASK-301
sequence_id: 301
type: task
title: 'Coexistence docs: sq renumber vs repair --renumber'
status: Done
parent: FEAT-288
author: tech-lead
refs:
- TASK-299:depends-on
description: Preferred pre-merge vs fallback post-merge; FEAT-13 deferral note
subentities:
- local_id: ST1
  title: Pre-merge shift and post-merge --renumber documented as complementary
  status: Done
  story: US5
created_at: '2026-07-06T08:47:59Z'
updated_at: '2026-07-06T10:06:44Z'
---
<!-- sq:body -->
Document `sq renumber` and `sq repair --renumber` as a **complementary pair, not a
replacement** (ADR-295 §5), and record the FEAT-13 deferral touchpoint for the new grammar.

## Scope
- User-facing docs + help: `sq renumber` (pre-merge) is the **preferred path** when the
  operator controls the yielding branch before merge — it preserves referential intent
  because it runs while refs are unambiguous. `sq repair --renumber` (post-merge) remains
  the **"too late, make it valid" fallback** for collisions that already landed: it
  guarantees uniqueness and no dangling refs but cannot preserve intent (its remap is keyed
  by the shared old-ID string).
- Include the boundary recipe (sq stays git-agnostic): read the other branch's counter with
  `git show <mainref>:squads/.squads.json | jq .counter` and pass it as `--onto`.
- Respect the docs conventions: shipped `docs/` must not cite sq item IDs or carry
  external/github URLs — state the guarantees on their own terms. The sq-item references
  here live only in this task/comment, not in the shipped prose.
- Record the **FEAT-13 deferral note**: both the `sq renumber` verb grammar (`--from/--onto/
  --by`) and the new `renumber` reflog op + its delta shape enter the frozen 1.0 grammar and
  must be listed when FEAT-13 (stability-contract capstone) runs. (Nina flagged this on
  FEAT-288; ADR-295 §4 and Consequences flag the reflog-op half.)

## Acceptance
- Docs/help present the two verbs as complementary with the preferred/fallback framing and
  the `--onto` recipe.
- No sq item IDs or external URLs leak into shipped `docs/`.
- The FEAT-13 deferral touchpoint is captured (comment on FEAT-13 / the deferral ledger the
  team uses), covering both the verb grammar and the `renumber` reflog op.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 301 add-subtask "<title>"`; track with `sq task 301 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Pre-merge shift and post-merge --renumber documented as complementary | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Pre-merge shift and post-merge --renumber documented as complementary

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US5 — Pre-merge shift and post-merge --renumber coexist
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Done when docs/help present sq renumber (preferred pre-merge, intent-preserving) and sq repair --renumber (post-merge 'too late, make it valid' fallback) as a complementary pair, not a replacement (ADR-295 §5), including the git-agnostic --onto recipe (git show <mainref>:squads/.squads.json | jq .counter). Shipped docs/ carry no sq item IDs or external URLs, and the FEAT-13 deferral note (the new verb grammar + the new renumber reflog op/delta shape) is recorded.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T10:06:44Z] Theo Writer:
  - Documentation complete and shipped.
  - Additions: (1) FAQ expanded with a new 'Handling ID collisions' section covering both pre-merge `sq renumber` (preferred, intent-preserving) and post-merge `sq repair --renumber` (fallback, lossy but guaranteed valid). (2) Recipes.md now includes a 'Block-shift IDs before merging' recipe with the git-agnostic boundary derivation (get destination's counter via `git show` and `jq`). (3) FEAT-13 deferral note recorded covering the new verb grammar and reflog op schema.
  - No sq item IDs or external URLs in shipped prose per docs conventions (verified via grep). Ready for review.
<!-- sq:discussion:end -->
