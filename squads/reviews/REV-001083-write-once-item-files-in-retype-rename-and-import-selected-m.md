---
id: REV-1083
sequence_id: 1083
type: review
title: Write-once item files in retype, rename and import; selected-menu fix
status: Approved
author: reviewer
refs:
- TASK-992
- BUG-1081
- MILE-934:targets
subentities:
- local_id: F1
  title: A failing import that renames a file still moves it on disk; repair is still
    needed
  status: Verified
  severity: medium
- local_id: F2
  title: Held texts live on the Service, not threaded or on the transaction, with
    no nesting guard
  status: Verified
  severity: medium
- local_id: F3
  title: The write guard ignores item-file writes made outside any unit, migration
    runners included
  status: WontFix
  severity: low
- local_id: F4
  title: conftest docstring still names a write-guard allowlist that no longer exists
  status: Verified
  severity: low
- local_id: F5
  title: Selected-menu fix verified; lint stops at a squad refusal and hides other
    selected errors
  status: WontFix
  severity: info
created_at: '2026-10-16T22:00:50Z'
updated_at: '2026-10-16T22:15:07Z'
---
<!-- sq:body -->
Review of TASK-992 (write each item file once per transaction: retype, rename_type, rename_status, import) and the BUG-1081 fix, on branch `worktree-agent-a0f8c17233ea0ade9`, commits 4a8bdc9d..c520f5a3 over 33d4ba4e.

## What was checked, and how

- **Byte identity (driven).** Old (33d4ba4e) and new (c520f5a3) trees exported side by side and run through one probe under a frozen clock: retype, rename_type (two tasks that ref and mention each other, a review referring to both, a subtask carried), rename_status, and a 10-event import (create, comment, body, ref, status, add-finding, a sub-entity comment, a renaming retitle, a comment after it). Each run twice: LF files, and every item file converted to CRLF first. All eight pairs: item files, index and reflog byte-identical.
- **The guard (driven).** Falsified: making the held write also go to disk turns 12 failures and 26 errors red in the import tests, naming the method, file and count. Ran `tests/service` and `tests/integration` from an exported copy with the ledger instrumented to log item writes made outside any unit: 1 failure, environmental (a test reads the live repo's `squads/.overrides`, absent from the export).
- **Import failure (driven).** An event raising after a renaming retitle: index and reflog unchanged, `_pending_texts` reset to `None`, but the file has already moved (F1).
- **BUG-1081 (driven).** `selected.bogus` now lists eight sections without `squad`; `selected.squad` keeps its specific refusal on both the load path and `sq workflow lint`.
- **Comments and docstrings.** Added lines read in full; one stale mention (F4).

## Recommended verdict

ChangesRequested: F1 and F2 are medium. The rule itself holds on every transactional path the suite drives, and the output is byte-identical.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1083 add-finding "…" --severity medium`; track with `sq review 1083 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A failing import that renames a file still moves it on disk; repair is still needed

<!-- sq:finding:F1:body -->
**Claim under test.** The handoff and the test docstring say an import that fails partway leaves no file behind and needs no repair: "a failing import now leaves no file behind"; "no file of the import reaches disk, so there is no partly applied import to repair".

**Driven.** Probe: one task, then an import of [update title, comment, status]. Make `_set_status_core` raise. Result on c520f5a3:

- task files before `TASK-000009-alpha.md`, after `TASK-000009-alpha-renamed.md`: the file moved, with its old bytes inside;
- index and reflog unchanged, `_pending_texts` back to `None`;
- a fresh Service: `comment` on the task refuses with "TASK-9's file is missing from its indexed location ... run `sq repair`".

The old code leaves the same moved file (plus the landed prefix of writes), so this is not a regression. But the atomicity the change claims does not hold for any import that renames a file, `sq repair` is still needed there, and the fault table's own invariant ("every item file equals its bytes before the method or its final bytes") fails for this row: the new path holds neither.

**Cause.** `ServiceCore._move_item_file` holds the *text* but performs the physical `path_rename` immediately, mid-transaction.

**Fix.** Defer the move too: record (old, new) in the held state and apply rename-then-write per file at flush. Add a fault row with a renaming event before the raise (the current fault scenario, "interleaved across three items", has no rename). Correct the docstring and the adopter-visible note for the tech writer.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T22:10:16Z] `python-dev` Elias Python:
  - Fixed in 5a55c391: moves are held and applied rename-then-write at the flush. Falsification: renaming immediately again turns 1 test red (the new fault row with a rename).
- [2026-10-16T22:14:26Z] `reviewer` Paul Reviewer:
  - Verified on 9740ed99: an import of retitle, comment and a raising status leaves the squad tree byte-identical (on c520f5a3 the file had moved), a later comment works without repair, and the same import without the fault lands the renamed file.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Held texts live on the Service, not threaded or on the transaction, with no nesting guard

<!-- sq:finding:F2:body -->
**Design under test.** `ServiceCore._pending_texts` plus the `_deferred_item_writes` context manager: a mutable attribute on the Service that switches five helper methods between pass-through and hold.

**What holds (read and driven).**
- Reset on every exit: `finally` sets `None` on a normal exit, a raise in the block, a raise during the flush, and cancellation. Driven for the raise case.
- No leak between two sequential operations: each exit resets.
- The flush runs in the inner context manager, so it precedes the index commit.

**What does not.**
- **The task's own rule.** TASK-992 says: "a buffer is threaded or carried on an object the transaction already owns". The Service is neither, and the operator prefers threaded context to mutable service state.
- **No nesting guard.** Entering the block while it is already open replaces the outer dict with `{}`. On the inner exit it sets `None`. The outer block's held texts are lost silently, and its later writes go straight to disk. One caller today, so this cannot happen yet, but nothing refuses it.
- **Discipline-only coverage.** Any writing half that reads with `_aio.read_text`, or writes with `update_frontmatter` or `write_text` directly, sees or clobbers stale disk inside the block. Five such direct sites remain in the same mixins: `_refs.py` remove_ref, `_subentities.py` remove_block, and `_items.py` 475/494/902. The guard catches the double write only if a test drives that op through an import.
- `_write_new_item_file` re-implements `write_new`'s composition (`join_frontmatter`).

**Proposed.** Carry the buffer on the transaction-owned object (the store's active-transaction context), or pass it explicitly to the cores. Refuse to open a second block while one is open. Whichever shape is chosen, make the held state own the moves too (F1).
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T22:10:18Z] `python-dev` Elias Python:
  - Fixed in 6e740363: the held state lives on the transaction context (HeldItemFiles), a second hold is refused, and the five direct writes (link, unlink, remove_ref, remove_block, delete severing) go through the hold. Falsification: dropping the nesting refusal turns 1 test red.
- [2026-10-16T22:14:29Z] `reviewer` Paul Reviewer:
  - Verified: the hold lives on the transaction context; a nested hold and a hold outside a transaction are both refused (driven). link, unlink, rm_ref, remove_block and remove_work_item --force severing outside an import leave a tree byte-identical to c520f5a3. tests/service and tests/integration: 5850 passed, 1 environmental failure (reads the live repo override).
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — The write guard ignores item-file writes made outside any unit, migration runners included

<!-- sq:finding:F3:body -->
**Gap.** `WriteLedger.note_write` returns early when no unit is open (`if unit is None: return`), so an item-file write outside any `transaction()` or repair rebuild is checked for neither the once rule nor the before-commit rule.

**Measured (driven).** I instrumented an exported copy of the ledger to log every out-of-unit item-file write with its service call chain, then ran `tests/service` and `tests/integration`. Item files are written outside any unit by:

- `renumber` (`_apply_remap`), and `repair`'s renumber path (`_renumber_files`);
- `sync`'s `_backfill_roster_body_tags` and `_restamp_managed_skill_frontmatter`;
- `memory_add` and `board_post`;
- `run_pending_migrations`;
- `refresh_managed` (from `init`, from `adopt`, and after the commit from `_project_roster_transition`).

The only same-test, same-path repeats were in migration chains (several runners, which can be legitimate). So no hidden live defect was found, but none of these paths is proven by the guard either.

TASK-992's sequencing put the guard ahead of FEAT-976 so that it would measure the new migration writes. Migration-runner writes outside the runner's own transaction are exactly what it cannot see.

**Proposed.** Either treat a migration runner step (and each top-level service call that writes without a transaction) as a unit, or state in `_write_guard`'s docstring that out-of-unit writes are deliberately out of scope and list the paths. Do not leave the gap implicit.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T22:10:21Z] `python-dev` Elias Python:
  - Writes outside a transaction are outside the rule this task enforces; 9740ed99 states in the fixture docstring what the guard measures and what it does not. Falsification: n/a (documentation).
- [2026-10-16T22:14:39Z] `reviewer` Paul Reviewer:
  - Accepted as WontFix: the write_ledger docstring now names the unit, lists the out-of-unit writers (migration runners, sync, renumber, memory and board) and says units that raise are not measured. That was the documented alternative I offered.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — conftest docstring still names a write-guard allowlist that no longer exists

<!-- sq:finding:F4:body -->
The `write_ledger` fixture docstring in `tests/conftest.py` ends: "The rule and its allowlist live in `_write_guard`". The allowlist mechanism was removed in dd20eef5 and `_write_guard` has none, so for a reader the sentence points at something that does not exist. Drop "and its allowlist".

Also, `_apply_import`'s docstring says each touched file is "written once when the last event is applied". It is written when the deferred block closes, after the last event. Consider rewording it to say exactly that.

No ticket ids or release versions in the added comments or docstrings; the rest of the added prose reads as present truth.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T22:10:23Z] `python-dev` Elias Python:
  - Fixed in 9740ed99 (wording only). Falsification: n/a.
- [2026-10-16T22:14:42Z] `reviewer` Paul Reviewer:
  - Verified: the allowlist mention is gone, and _apply_import now says files are written when the deferred block closes after the last event.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Selected-menu fix verified; lint stops at a squad refusal and hides other selected errors

<!-- sq:finding:F5:body -->
**The fix is right (driven).** On c520f5a3, `[selected] bogus = [...]` lists `['collections', 'items', 'lifecycles', 'ref_kinds', 'roles', 'statuses', 'subentity_kinds', 'views']`, without `squad`. `[selected] squad = [...]` still gives the specific "the `[squad]` table has no entries to drop" refusal, on both the load path (`sq list`, exit 1) and `sq workflow lint`. `WORKFLOW_SELECTABLE_SECTIONS` is passed only as the `[selected]` menu, and `top_level_keys` stays the full set. The other consumer (`_raw_shadows_bundled`) correctly keeps the full set.

**Adjacent and pre-existing (not caused by the fix).** `sq workflow lint` claims to report every problem at once, but an override with both `squad = [...]` and `bogus = [...]` under `[selected]` reports only `selected.squad`. `bogus` surfaces only after the first error is fixed, whichever order the keys are in. Old and new code agree, so this belongs in a follow-up, not on this fix. Recording it so it gets a disposition.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T22:15:07Z] `manager` Catherine Manager:
  - Tracked as BUG-1084 (predates 0.16, targets MILE-1051).
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T22:02:30Z] `reviewer` Paul Reviewer:
  - Verdict ChangesRequested: F1 and F2 are medium (a failing import still moves renamed files on disk; the held texts sit on the Service with no nesting guard). F3 and F4 are low, F5 info. Byte identity against 33d4ba4e holds for retype, rename_type, rename_status and a 10-event import, on LF and CRLF files. The BUG-1081 fix is verified. @python-dev F1-F4; @manager F5 needs a home for the pre-existing lint short-circuit.
- [2026-10-16T22:14:44Z] `reviewer` Paul Reviewer:
  - Fixes verified (6e740363, 5a55c391, 9740ed99): F1, F2 and F4 are Verified, and F3 is accepted as WontFix with the scope now documented. Recommend Approved. F5 (info, an older lint short-circuit) stays Open until @manager gives it a home.
<!-- sq:discussion:end -->
