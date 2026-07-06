---
id: REV-302
sequence_id: 302
type: review
title: sq renumber core (TASK-297/298/299) vs ADR-295
status: Approved
author: reviewer
refs:
- FEAT-288:addresses
subentities:
- local_id: F1
  title: 'sq-item IDs embedded in source (worst: CLI --help)'
  status: Fixed
  severity: high
- local_id: F2
  title: Padded-filename seam test would pass even if filenames regressed to unpadded
  status: Fixed
  severity: low
- local_id: F3
  title: renumber not wrapped in a single IndexStore.transaction()
  status: Fixed
  severity: low
created_at: '2026-07-06T09:31:27Z'
updated_at: '2026-07-06T09:56:17Z'
---
<!-- sq:body -->
Independent review of the `sq renumber` core (TASK-297 executor extraction, TASK-298 offset planner, TASK-299 CLI verb) against the ratified ADR-295. I did not write this code and read the full working-tree diff, the store/index internals it leans on, and rendered the CLI help.

## Verdict: ChangesRequested

The implementation is substantively correct against every load-bearing choice in ADR-295. One must-fix (source-embedded item-ID references, flagged directly by the operator) and two minor findings hold it back from Approved. No correctness defect was found in the shift/offset/executor logic.

## What was verified clean

- **CLI surface (§1).** `sq renumber` is a standalone top-level verb, not a `repair` mode; `--from` is required; `--onto`/`--by` are mutually exclusive (rejected at the CLI with a usage error and again in the planner with `SquadsError`). Root `--help` lists it and the subcommand help carries the `git show <ref>:squads/.squads.json | jq .counter` recipe.
- **Git-agnostic (§2).** No `subprocess`/`import git`/`os.system`/merge-base anywhere in the new code path — only integers cross in. The only "subprocess"/"git" tokens in the changed lines are prose in a docstring and an unrelated pre-existing comment.
- **Disjoint offset (§3).** `--onto M` computes `delta = max(M, C) + 1 - from_seq` with `C` read as this branch's own counter — the max is genuinely over BOTH `M` and `C` (tested for M>C, M<C, M==C, and asserts the landed block clears `max(M,C)`). `--by n` validates `from_seq + n > C` and refuses with `SquadsError` reporting the minimum safe offset; the refuse happens in `_offset_plan` strictly before `_apply_remap`, so no file is touched (asserted by before/after filesystem + index snapshots). Because the new range is strictly above the old local range, no new id string equals any old one, so single-pass `rewrite_ids` is order-independent — confirmed: remap keys land in [from_seq, C], values in [from_seq+delta, C+delta] with from_seq+delta > C, disjoint.
- **Executor extraction (§5).** The apply-path (`rewrite_ids` -> rename at filename padding -> `sequence_id` resync) is genuinely lifted into `_apply_remap`; both `_renumber` (repair path) and `renumber` (new verb) call it — no duplicated loop. The executor is counter-neutral (never touches `SquadsDB.counter`); the bump lives on `sq renumber` via the disk-rescan rebuild, per the tech-lead's ratified reading. `repair --renumber` behavior is preserved: the old inline `found_seqs` set is now `set(db.items)` (both are the sequence-id key set), so missing-file detection is unchanged; the collision test passes.
- **Filename seam (§3/ADR-282).** Renames mint at filename padding via `format_item_id(prefix, seq, db.padding)` (=6) while frontmatter/refs/prose take the unpadded `DISPLAY_ID_PADDING` (=0) form. Confirmed `DISPLAY_ID_PADDING = 0`, `DEFAULT_ID_PADDING = 6`, and the planner uses each in the right place.
- **Invariants / reflog.** The reflog is left entirely untouched — `rewrite_ids` only globs item `.md` files, never `.reflog.jsonl`, consistent with ADR-295 §4's "leave historical lines literal"; the `renumber` bridging event is correctly deferred to TASK-300. `overwrite` writes no reflog op, so the rebuild emits nothing (asserted: no `repair` op, `sq check` clean). SquadsError for user errors, clock not needed. pyright strict + ruff both clean; the targeted test subset is green.

## Findings

See the finding sub-entities: F1 (must-fix), F2, F3.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 302 add-finding "…" --severity high`; track with `sq review 302 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | sq-item IDs embedded in source (worst: CLI --help) |
| F2 | 🟢 low | Fixed |  | Padded-filename seam test would pass even if filenames regressed to unpadded |
| F3 | 🟢 low | Fixed |  | renumber not wrapped in a single IndexStore.transaction() |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — sq-item IDs embedded in source (worst: CLI --help)

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**Must-fix (operator-flagged, non-negotiable).** This diff introduces sq-item-ID references into source. Per the repo's no-ticket-IDs-in-code rule, the decision pointer belongs in the sq item / PR, not the shipped source — and the CLI-help case is a user-facing leak (an operator running `sq renumber --help` sees a raw ADR id).

Newly-added locations (only `+` lines from this working-tree diff — the pre-existing ADR-000181/ADR-000104/… citations on unchanged lines are the separate repo-wide reference-hygiene sweep's job, out of scope here):

- `src/squads/_cli/_main.py:436` — the `renumber` help docstring ends "…preserving referential intent (ADR-000295)." Confirmed present in rendered `sq renumber --help`. **Worst offender: user-facing.**
- `src/squads/_services/_maintenance.py` — new docstrings citing `ADR-000295` (§5/§1/§2/§3), `ADR-000282`, and `TASK-000300`, at roughly lines 621, 628, 635, 678, 704, 744, 750, 759, 766.
- `src/squads/_services/_results.py:167` — the `RenumberResult` / `Service.renumber()` docstring citing `ADR-000295`.

**Impact.** Ships internal identifiers on a user-facing surface (CLI help) and seeds more source-embedded IDs the reference-hygiene sweep will have to strip. **Recommendation:** keep the behavior/rationale in prose but drop the parenthetical ID citations; where a design pointer is genuinely useful for a future maintainer, it lives in the sq item, not the source. Prioritize `_main.py:436` (user-facing) — remove "(ADR-000295)" from the help text entirely.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-06T09:55:41Z] Elias Python:
  - Scrubbed ADR-000295/ADR-000282/TASK-000300 citations from every added src/ line (CLI help, _maintenance.py docstrings, RenumberResult docstring). Proof: git diff HEAD -- src/ | grep -nE '^+' | grep -E '(ADR|FEAT|TASK|REV|BUG|EPIC)-?0*[0-9]+' returns empty.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Padded-filename seam test would pass even if filenames regressed to unpadded

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**Weak guard on a load-bearing invariant.** The padded-filename seam (ADR-282: filenames stay padded to `db.padding`=6 while content is unpadded) is the load-bearing correctness property TASK-298 ST2 exists to protect, but the service test that supposedly covers it only asserts:

`svc.paths.abspath(new_bug_item.path).name.split("-")[1].isdigit()`

That checks the digit-run *exists*, not that it is padded to the squad's filename width. A regression that minted the rename stem at unpadded width (e.g. `BUG-14-shift-bug.md` instead of `BUG-000014-shift-bug.md`) would still yield `"14".isdigit() == True` and the test would pass — false confidence. The production code is correct (`_offset_plan` uses `format_item_id(prefix, seq, padding)` with padding from the index), so this is a test-strength gap, not a live bug.

Secondary coverage note: the intent-preservation tests cover shifted->shifted refs and a shifted->non-shifted parent link, but not the reverse (a non-shifted item referencing a shifted item). The code handles it — `rewrite_ids` runs over *all* item files — but it is unasserted.

**Impact.** The seam most likely to silently break (padding is the subtle half of ADR-282) is unguarded against a future refactor. **Recommendation:** assert `len(stem_digits) == db.padding` (or `== 6`) on the renamed file, and add a case where a below-`from_seq` item's ref to a shifted item is rewritten.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-06T09:55:42Z] Elias Python:
  - Strengthened test_renumber_shifts_block_and_preserves_referential_intent to assert the renamed file's digit-run length equals db.padding (not just .isdigit()), and added test_renumber_rewrites_an_unshifted_items_ref_to_a_shifted_item for the reverse referential-intent direction.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — renumber not wrapped in a single IndexStore.transaction()

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**Divergence from the task's literal wording (informational, not a blocker).** TASK-299 scope says: "Run the whole thing inside `IndexStore.transaction()` so the mutation is atomic and the refuse-path leaves the tree untouched." The implementation does not do that. `renumber` instead: loads the index (lock acquired+released), scans, runs `_offset_plan`, then `_apply_remap` rewrites+renames files with **no lock held**, then `_rebuild_index_from_disk` commits via `store.overwrite` (a separate locked write). The multi-file rewrite/rename and the index commit are therefore not a single atomic critical section.

Assessment: this is deliberate and mirrors the established `repair` / `repair --renumber` pattern exactly (that path also does file ops then `overwrite`, no wrapping transaction), and ADR-295 itself does not mandate a transaction — only the TASK-299 body prose does. The load-bearing safety the ADR *does* require is met: `_offset_plan` raises before any filesystem mutation, so the unsafe-`--by` refuse path leaves the tree untouched (verified by the before/after snapshot tests). For the single-user model there is no correctness regression; a crash mid-rename is recoverable by `sq repair`, identical to the existing `--renumber` risk profile.

**Impact.** None observed for the supported use; only a wording mismatch with the task and a (pre-existing, shared-with-repair) non-atomicity window. **Recommendation:** either wrap the apply+commit in a single `IndexStore.transaction()` to match TASK-299 literally, or (my preference) reconcile the task text to state it intentionally reuses repair's overwrite pattern — no code change needed. Recording it so the divergence is a decision on the record, not an oversight.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-06T09:55:43Z] Elias Python:
  - Reconciled TASK-299's body + ST1 subtask text to describe the actual commit pattern (unlocked rewrite/rename then a single locked IndexStore.overwrite via _rebuild_index_from_disk, mirroring sq repair) instead of claiming IndexStore.transaction(). No code change — code already met the load-bearing safety property (validate-before-mutate).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T09:56:17Z] Paul Reviewer:
  - F1 Fixed: sq-item-ID citations removed from src (CLI help string + new docstrings in _maintenance.py/_results.py) and from the two new test docstrings; added-line grep is clean. F2 Fixed: seam test now asserts len(digit_run)==db.padding, and a reverse-ref regression test (unshifted item referencing a shifted one) was added. F3 Fixed: TASK-299 body reconciled to the repair-mirroring apply-path pattern (unlocked file ops + single locked overwrite); code unchanged. Verified by manager: pyright/ruff clean, full suite green (0 failures), git-agnostic grep clean.
<!-- sq:discussion:end -->
