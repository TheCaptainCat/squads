---
id: TASK-355
sequence_id: 355
type: task
title: Extract rename-safe per-item retype primitive
status: Done
parent: FEAT-281
author: tech-lead
subentities:
- local_id: ST1
  title: Extract reusable per-item type-rewrite primitive from retype()
  status: Todo
  story: US1
created_at: '2026-07-09T21:34:34Z'
updated_at: '2026-07-13T09:27:35Z'
---
<!-- sq:body -->
Enabler for rename-type (TASK-356). Refactor _services/_retype.py so the per-item rewrite sequence inside retype() becomes a reusable primitive that the bulk rename path can call without retype()'s single-item reclassification guardrails.

Extract the mutate-one-item core (currently inline in RetypeMixin.retype, lines ~135-174) into a module-level async helper, e.g. _apply_type_change(db, item, new_type, *, carry_status: bool). It must: stamp prefix_for(new_type, spec), recompute the unpadded id, move the file (padded stem via format_item_id), update frontmatter, ensure the sub-entity container, and bump updated_at. Status handling becomes a parameter: retype() keeps its carry-or-reset via _carry_or_reset_status; the rename caller passes carry_status=True (carry unconditionally).

Separate the two seams so the bulk path stays O(N), not O(N^2): (a) per-item self-rewrite (frontmatter/file/status) and (b) a batchable edge remap. Today retype() calls rewrite_ids over all squad files once per item; the rename path must build ONE combined {old_id:new_id} remap across every renamed item and do a single rewrite_ids pass, then one _resync_edges pass. Factor the edge-rewrite so both a single {old:new} (retype) and a bulk dict (rename) work through the same code.

Keep the reflog+comment emitters reusable: _append_retype_comment and the store._log('retype', ...) call should be parameterizable enough that rename can emit its own op/message per item (see TASK-356/357). Either generalize them (op arg, message builder) or leave them retype-specific and have rename supply its own — dev's call, note it in the PR.

HARD CONSTRAINT: retype() behaviour and its audit trail (reflog line + discussion comment) must be byte-identical after the refactor. This is a pure extraction — no functional change. tests/test_retype.py must pass unchanged.

Files owned: src/squads/_services/_retype.py; tests/test_retype.py (only if the extraction needs new unit coverage of the primitive — do not weaken existing assertions). Do NOT touch _workflow/_models.py.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 355 add-subtask "<title>"`; track with `sq task 355 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Extract reusable per-item type-rewrite primitive from retype() | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Extract reusable per-item type-rewrite primitive from retype()

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Extracted the per-item type-rewrite core out of `retype()` into a reusable `_apply_type_change(...)` primitive (prefix/id/status/file-move/frontmatter/sub-entity container), with status carry made a parameter, and generalised `_resync_edges`/`rewrite_ids` to take a `{old:new}` remap so both retype (one entry) and the bulk rename path (N entries) share one O(N) edge-rewrite pass. Pure extraction — `retype()` behaviour and its audit trail (reflog line + comment) stay byte-identical.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T00:31:38Z] Operator:
  - Extracted `_apply_type_change(paths, spec, db, item, new_type, *, carry_status)` — the per-item self-rewrite core (prefix/id/status/file-move/frontmatter/sub-entity container); retype() now just resolves carry_status via _carry_or_reset_status and calls it.
  - Generalized _resync_edges to take a {old:new} remap dict + exclude set (one pass over db.items regardless of remap size); added _remap_ref via split_ref/make_ref for correct multi-key ref rewriting. rewrite_ids was already remap-dict-capable, no change needed there — it's the shared batchable file-rewrite seam for both retype (1-entry dict) and the future bulk rename (N-entry dict).
  - Left _append_retype_comment/store._log('retype', ...) retype-specific rather than generalizing the op/message — rename's audit shape (per-item reflog+comment, but building one combined id remap first) looked different enough that a shared parameterized emitter would just be a thin wrapper; TASK-356/357 can lift the same discussion.format_comment/store._log pattern with their own message.
  - Pure extraction, byte-identical: tests/test_retype.py (34 tests) unchanged and green; pyright/ruff/ruff-format clean; test_squad_ref_hygiene.py green. Reviewer: check _remap_ref's split_ref/make_ref reconstruction is truly equivalent to the old startswith(old_id+':') string-slice for the ID:kind case (I verified by hand, no new test added since behavior is unchanged).
- [2026-07-10T00:32:06Z] Elias Python:
  - (re-attributing prior handoff comment — posted with the wrong --as by mistake)
  - Extracted _apply_type_change(paths, spec, db, item, new_type, *, carry_status) — the per-item self-rewrite core (prefix/id/status/file-move/frontmatter/sub-entity container); retype() now resolves carry_status via _carry_or_reset_status and calls it.
  - Generalized _resync_edges to a {old:new} remap dict + exclude set (one pass regardless of remap size); added _remap_ref via split_ref/make_ref for correct multi-key rewriting. rewrite_ids was already remap-dict-capable — the shared batchable file-rewrite seam for both retype (1-entry dict) and the future bulk rename (N-entry dict), no change needed.
  - Left _append_retype_comment/store._log('retype', ...) retype-specific rather than generalizing the op/message — rename's per-item audit trail can reuse the same discussion.format_comment/store._log pattern with its own message; a shared emitter looked like a thin wrapper not worth the indirection. Flagging for TASK-356/357.
  - Pure extraction, byte-identical: tests/test_retype.py (34 tests) unchanged and green; pyright/ruff/ruff-format clean; test_squad_ref_hygiene.py green. Reviewer: check _remap_ref's split_ref/make_ref reconstruction against the old startswith(old_id+':') slice for the ID:kind ref case.
- [2026-07-10T00:37:24Z] Paul Reviewer:
  - Reviewed uncommitted TASK-355 diff (independent, on committed FEAT-212). VERDICT: APPROVE. Pure, clean extraction — no functional drift. gates clean (pyright/ruff/format), test_retype.py 34/34 pass UNCHANGED, full suite green (exit 0, 0 failures). No findings.
  - retype() byte-identical: YES. Status equivalence holds exactly — _carry_or_reset_status's reset branch returns (True, spec.initial_status(new_type)) (_retype.py:150), and _apply_type_change sets item.status = spec.initial_status(new_type) iff  where carry_status = not status_reset — same condition, same value; the carry branch leaves status untouched in both. File move/prefix/id/frontmatter/container sequence extracted verbatim. Reflog+comment emitters untouched (still retype-specific) so the audit trail is unchanged.
  - _remap_ref equivalence (the correctness-critical bit): YES, exact for all three cases. split_ref('ID')->('ID','related'=DEFAULT_KIND) + make_ref(new,'related') collapses to bare new_id (== old r==old_id branch); 'ID:kind'->make_ref keeps 'new:kind' (== old startswith(old_id+':') branch); and split_ref partitions on the first ':' so a remap of TASK-1 never touches a ref to TASK-12 (matches the old startswith(old_id+':') guard, and is structurally more robust than the string-slice).
  - Seam for TASK-356/357 is clean/O(N): _apply_type_change is per-item and touches no other item's edges; rewrite_ids already takes a {old:new} dict; _resync_edges now takes (remap dict, exclude set) in one pass. A bulk caller can _apply_type_change each renamed item (carry_status=True), accumulate one combined {old:new}, then do a single rewrite_ids + single _resync_edges(exclude=all renamed seqs) — no O(N^2). Scope-disciplined: only _retype.py touched, _workflow/_models.py untouched; no ticket IDs in source; no existing test assertion weakened (test file unchanged).
- [2026-07-10T00:37:47Z] Paul Reviewer:
  - Correction (a shell glitch dropped words from the status-equivalence bullet above; restating cleanly): retype() status handling is byte-identical. In _apply_type_change, the reset assignment runs when NOT carry_status, and carry_status is passed as (NOT status_reset), so it runs exactly when status_reset is true — the same condition as the old code. The value assigned, spec.initial_status(new_type), equals the old reset-branch value returned by _carry_or_reset_status (True, spec.initial_status(new_type)). When carrying (status_reset false), neither old nor new touches item.status. Values and conditions match on both branches.
- [2026-07-10T00:38:24Z] Catherine Manager:
  - Reviewer-approved, no findings. retype() byte-identical (test_retype.py 34/34 unchanged); _remap_ref equivalence verified for bare/ID:kind/prefix-substring cases; O(N) bulk-rename seam confirmed clean for 356/357. Full suite green. Landing.
<!-- sq:discussion:end -->
