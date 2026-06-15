---
id: REV-000106
sequence_id: 106
type: review
title: Review of TASK-000102 + TASK-000103 — repad command and width-tolerant ID reading
  (FEAT-000027 completion)
status: Approved
author: reviewer
description: 'Joint review of the post-101 work: sq migrate repad and width-tolerant
  reads; one medium finding (spurious repair missing_ids after repad), one low (hand-rolled
  width in repad).'
subentities:
- local_id: F1
  title: repad leaves sq repair reporting EVERY item as a spurious 'missing' warning
  status: Verified
  severity: medium
- local_id: F2
  title: repad hand-rolls the zero-pad width instead of routing through format_item_id
  status: Verified
  severity: low
- local_id: F3
  title: End-to-end test does not exercise sq repair after repad, so the missing_ids
    regression slipped through
  status: Verified
  severity: low
created_at: '2026-06-14T21:56:33Z'
updated_at: '2026-06-14T22:06:18Z'
---
<!-- sq:body -->
## Scope

_TODO: what is under review?_
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 106 add-finding "…" --severity high`; track with `sq review 106 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Verified |  | repad leaves sq repair reporting EVERY item as a spurious 'missing' warning |
| F2 | 🟢 low | Verified |  | repad hand-rolls the zero-pad width instead of routing through format_item_id |
| F3 | 🟢 low | Verified |  | End-to-end test does not exercise sq repair after repad, so the missing_ids regression slipped through |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — repad leaves sq repair reporting EVERY item as a spurious 'missing' warning

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
PROBLEM: After `sq migrate repad <w>`, running `sq repair` prints a spurious 'indexed but no markdown file found (deleted?)' warning for EVERY item, even though all files are present and correct. Reproduced at the CLI level: after repad(7) on a 3-item squad, `sq repair` emits 'rebuilt index: 3 items, counter=3' followed by 3 warn lines (FEAT-0000002, ROLE-0000001, TASK-0000003).

FILE: src/squads/_services/_maintenance.py:179 (and the missing_ids diff at :219). repair() builds previous_ids = {it.id for it in prev.items.values()}. prev came from store.load(), so TASK-103's new _propagate_padding validator (_models/_index.py:58) has already set id_padding = db.padding (=7) on every prev item -> previous_ids are width-7 strings ('TASK-0000003'). found_ids is built from Item.from_frontmatter (line 197), which does NOT set id_padding, so items default to padding 6 and the frontmatter id is still width-6 -> found_ids are width-6 strings ('TASK-000003'). previous_ids - found_ids therefore equals the ENTIRE set, so missing_ids lists every item.

WHY IT MATTERS: This is exactly the full-ID-string-equality-across-widths failure mode TASK-103 set out to eliminate — this one call site was missed. It is the only id-string comparison left in the post-101 code that breaks across a repad boundary. sq check stays clean (it is seq-keyed), which is why the e2e test did not catch it, but `sq repair` (and any consumer of RepairResult.missing_ids — _cli/_main.py:352 surfaces them) is wrong. It also fires inside repad()'s own internal repair() call, where the bogus result is discarded — but the user's next `sq repair` is the visible symptom.

SUGGESTED FIX: compute missing_ids by sequence number, not full-ID string — mirror the width-tolerant treatment applied everywhere else: previous_seqs = {it.sequence_id for it in prev.items.values()}; found_seqs = {it.sequence_id for it in db.items.values()}; then report the difference (keeping a seq->fid map from prev for the message). Same pattern already used in _check_reconciliation (line ~388).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-06-14T22:06:11Z] Paul Reviewer:
  - Verified. repair() now keys the missing-file comparison by sequence_id (previous_seq_to_id: dict[int,str], found_seqs: set[int]), mirroring _check_reconciliation. Reproduced the original symptom is gone: ran the regression test against a deliberately-reverted F1 (old previous_ids/found_ids string sets) and it FAILED with missing_ids=['BUG-0000004','FEAT-0000002','ROLE-0000001','TASK-0000003'] — the whole corpus; with the fix in place missing_ids == [].
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — repad hand-rolls the zero-pad width instead of routing through format_item_id

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
PROBLEM: repad() formats the new digit-run by hand rather than through the canonical formatter. FILE: src/squads/_services/_maintenance.py:255 — new_id_part = f'{seq:0{new_padding}d}'.

WHY IT MATTERS: Both the TASK-102 scope ('renames every item file to the new width via format_item_id, no hand-rolled width') and Elias's own handoff comment claim it uses format_item_id's canonical formatter — but the code does not. CLAUDE.md requires all :0Nd formatting to route through format_item_id, and REV-000105 specifically eliminated stragglers like this. Functionally correct here, so consistency/convention only, not a correctness bug.

SUGGESTED FIX: base = format_item_id(item_type.prefix, seq, new_padding); new_name = f'{base}-{slug_part}.md' if slug_part else f'{base}.md'.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-06-14T22:06:12Z] Paul Reviewer:
  - Verified. repad() builds the new filename via format_item_id(item_type.prefix, seq, new_padding) at _maintenance.py:260; the f'{seq:0{new_padding}d}' straggler is gone. Grep across src/ confirms the only :0Nd run is inside format_item_id itself (_item.py:26, the canonical formatter).
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — End-to-end test does not exercise sq repair after repad, so the missing_ids regression slipped through

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
PROBLEM: test_end_to_end_repad_resolution (tests/test_service.py:980) is otherwise strong — it covers parent resolution, refs_in, backrefs, both old- and new-width CLI addressing, and svc.check() clean — but it never runs svc.repair() / 'sq repair' after the repad and asserts missing_ids == []. That is precisely the gap that let F1 through: check() is seq-keyed and stays clean, while repair()'s missing_ids is the broken path.

WHY IT MATTERS: The joint acceptance for FEAT-000027 includes 'rebuilds the index ... sq check is clean and every old-width ref still resolves'. repair() is the index rebuild; its spurious-missing output is a user-visible regression that the acceptance suite does not guard against.

SUGGESTED FIX: extend the e2e test (or add one) that calls svc.repair() after repad(7) and asserts rr.missing_ids == [] (and/or that 'sq repair' CLI output contains no 'no markdown file found' warning). Pairs with the F1 fix.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-06-14T22:06:12Z] Paul Reviewer:
  - Verified. test_repair_after_repad_no_spurious_missing (tests/test_service.py:1042) builds a feat/task/bug squad with a fixes-ref, repads to width 7, then calls repair() and asserts rr.missing_ids == []. Confirmed empirically it fails against the F1 bug and passes with the fix — it genuinely guards the broken path (check() is seq-keyed and stayed clean, which is what let F1 through originally).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-14T21:57:33Z] Paul Reviewer:
  - VERDICT: ChangesRequested. One medium regression (F1) blocks; two low findings (F2 convention, F3 test gap) ride along. The width-tolerant reading design is correct and well-centralised — seq_for_id, _id_matches((prefix,seq)), _propagate_padding, and the seq-keyed check reconciliation all hold up, cross-type false positives are guarded and tested (test_index.py:257), and Invariant 4 is intact (no inverted edges persisted; id_padding never serialises — confirmed in goldens + committed index). The F1/F3 fold-ins from REV-000105 landed correctly (renumber threads db.padding; the repair padding guard collapsed to a single max()). The repad command, byte-untouched contents, and refuse-to-lower are all correct and tested.
  - WHAT BLOCKS: F1 — after repad, 'sq repair' reports EVERY item as a spurious missing-file warning, because repair()'s previous_ids (built from store.load() items, now carrying id_padding=new-width via _propagate_padding) are compared as full-ID strings against found_ids built from from_frontmatter (old-width). This is the one id-string-equality-across-widths site TASK-103 missed; fix is to compare by sequence_id like _check_reconciliation already does. sq check stays clean (seq-keyed), which is why the e2e test (F3) didn't catch it.
  - @python-dev — please fix F1 (medium, lands in TASK-103's _propagate_padding/repair seam), F2 (low, TASK-102: route repad's width through format_item_id), and F3 (low, TASK-103: extend the e2e test to assert repair().missing_ids == [] post-repad). All three are small. Gate is currently green (578 passed/1 skipped, pyright+ruff clean) but the F1 regression is latent behind output the e2e test doesn't assert on.
- [2026-06-14T22:06:18Z] Paul Reviewer:
  - APPROVED. Focused verification pass complete: all three findings (F1 medium/blocking, F2 low, F3 test) verified and closed. Full gate green on the uncommitted working tree: 579 passed, 1 skipped; pyright 0 errors; ruff check + format clean. F1's original symptom empirically confirmed gone (regression test fails against a reverted fix, passes with it). No regressions introduced. TASK-000102 and TASK-000103 ready to merge.
<!-- sq:discussion:end -->
