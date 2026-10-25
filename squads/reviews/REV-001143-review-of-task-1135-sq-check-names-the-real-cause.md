---
id: REV-1143
sequence_id: 1143
type: review
title: 'Review of TASK-1135: sq check names the real cause'
status: Approved
author: reviewer
refs:
- TASK-1135
subentities:
- local_id: F1
  title: 'Field-line regex lets authored lines read as scaffold: data loss'
  status: Verified
  severity: high
- local_id: F2
  title: 'Field sentinel is whitespace: start/end-of-line fields not matched'
  status: Verified
  severity: medium
- local_id: F3
  title: Re-scaffold at the field change is simpler; retype residue remains
  status: Verified
  severity: medium
- local_id: F4
  title: Container remedy still blames a nonexistent override
  status: Verified
  severity: medium
- local_id: F5
  title: Missing sub-entity discussion pair is not reported
  status: Verified
  severity: high
- local_id: F6
  title: Body write names the body pair when the whole block is missing
  status: Verified
  severity: low
- local_id: F7
  title: CHANGELOG region and scaffold entries overclaim
  status: Verified
  severity: low
- local_id: F8
  title: 'Check docstrings: split sentence, parsed-file member'
  status: Verified
  severity: info
- local_id: F9
  title: Finding order within an item is undocumented
  status: Verified
  severity: info
- local_id: F10
  title: Missing discussion pair fails check after migrate on adopter files
  status: Verified
  severity: high
created_at: '2026-10-25T16:42:27Z'
updated_at: '2026-10-25T17:45:06Z'
target_ref: f64955ab
---
<!-- sq:body -->
## Scope

Commit f64955ab on release/0.17: the five TASK-1135 subtasks (per-file check text on a number clash, the stray-skill remedy, missing sub-entity and discussion regions, the scaffold matcher, import finding order), their tests and the four CHANGELOG lines under 0.17.0 Fixed.

## Method

Every claim below was driven with the dev build (`uv run --all-extras sq -C <scratch>`) in scratch squads, and where it matters, compared with the released 0.16.0 tool. The commit's six new test files pass at -n 4 (37 passed). Full suite not run.

## What holds

- ST1: BUG-993's exact scenario (TASK-2 plus a referrer, then a valid BUG-2 file copied in from a second squad) now prints only the shared-number error. Confirmed: no code change was needed, and the added rows are regression rows.
- ST2: driven in a claude_code squad. Before `sq sync` it prints "no healthy file holds managed skill 'sq-task'; delete this file and run `sq sync`". After sync it prints "a stray copy ... healthy in SKILL-000019-sq-task.md; delete this file". `sq repair` gives the same line. The remedy is right.
- ST5: the sort key is total (the message breaks ties) and `sorted` is stable, so import and check print in the same order.

## What does not

See the findings. The two high ones are a gate regression for adopters (ST3) and a data-loss path in the overwrite guard (ST4).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1143 add-finding "…" --severity medium`; track with `sq review 1143 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Field-line regex lets authored lines read as scaffold: data loss

<!-- sq:finding:F1:body -->
**Where.** `scaffold_matcher` / `_line_pattern` in `src/squads/_rendering/_engine.py`, read by the overwrite guard in `_items.py` and by `body_written`.

**Mechanism.** A template line that interpolates a declared attribute becomes the regex `<fixed>.*?<fixed>`. Every body line that fullmatches one of these patterns is dropped before the remaining lines are compared with the shared scaffold lines. Nothing ties a dropped line to a field value, or limits how many lines one template line can absorb. So any authored line shaped like the field line disappears from the comparison.

**Failure, driven (bundled review template, target_ref never set).** `sq create review r2`. The body is set to the scaffold's two fixed lines plus two authored lines: "**Target:** `src/lock.py`: acquire races with release under contention, fix is to take the pool lock before `_held`" and "**Target:** `src/pool.py`: same ordering bug in `drain`". Each line starts with `**Target:** ` and ends with a backtick, so it matches the Target pattern. Then `sq review 6 body -m replaced` exits 0 with "REV-6: body set". The authored text is gone, without `--force`. On 0.16 the exact comparison refused this write. `body_written` reads the same text as unwritten, so `sq check` reports an authored body as a stub.

This guard exists to prevent data loss, so it must err towards "authored". With an override template, the exposure grows: a field line whose fixed part is short, such as `- {{ x }}` or `**{{ x }}**`, would swallow every bullet or bold line. (That shape is masked today by the defect in F2.)

**Direction.** Let each variable template line absorb at most one body line, at the position where the template has it. Or match only the values the field can actually hold. Or drop the matcher for the simpler rule in F3. Add a test row: scaffold lines plus variable-shaped lines only, which must stay authored.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-25T16:56:25Z] `python-dev` Elias Python:
  - Fixed: scaffold_matcher and its line regexes are removed; the exact comparison is the only definition.
- [2026-10-25T17:11:15Z] `reviewer` Paul Reviewer:
  - Verified on df3109d2: the REV-6 shape (scaffold lines plus two authored lines shaped like the Target line) is refused by body -m without --force, before and after update --set target_ref; the body bytes are unchanged after the update. The matcher is gone and the exact comparison is the only rule.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Field sentinel is whitespace: start/end-of-line fields not matched

<!-- sq:finding:F2:body -->
**Where.** `_FIELD_MARK = "\x1ffield\x1f"` with `_scaffold_lines` (`line.strip()`) in `src/squads/_rendering/_engine.py`.

**Mechanism.** `\x1f` counts as whitespace (`"\x1f".isspace()` is True), so `str.strip()` eats the sentinel's trailing `\x1f` when the field ends a line, and its leading `\x1f` when the field starts one. `split(_FIELD_MARK)` then finds no mark, and the line becomes an exact literal pattern containing a stray `\x1ffield`. Measured: under an override with `- {{ item.target_ref }}`, the marked render gives `'- \x1ffield'`.

**Failure, driven.** In `squads/.overrides/templates/items/review.md.j2`, the Target line is changed to `**Target:** {{ item.target_ref }}`, the common shape of a field at the end of a line. Steps: `create review`, `update --set target_ref=abc`, body equal to that scaffold (`... **Target:** abc`), then `update --set target_ref=def` and `body -m changed`. Result: "Nothing was written ... pass `--force`", so BUG-1014 is still there. The same steps on the bundled template (field inside backticks) replace the body correctly.

So the fix works only when a field sits mid-line, and the ST4 tests cover only the bundled template. A field in a heading (`## {{ item.component }}`) or at the end of a line in any adopter override is not handled.

**Direction.** Use a sentinel that is not whitespace (a private-use code point, for example), or strip before marking. Add an override-template row with the field at the end of a line.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-25T16:56:28Z] `python-dev` Elias Python:
  - Fixed: the field sentinel is gone with the matcher; a test renders a template with a field at a line edge.
- [2026-10-25T17:11:17Z] `reviewer` Paul Reviewer:
  - Verified on df3109d2: the matcher and its sentinel are removed. With an override review template whose field ends the line, set and then change target_ref re-renders the line, and body -m replaces it.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Re-scaffold at the field change is simpler; retype residue remains

<!-- sq:finding:F3:body -->
**Where.** The ST4 design as a whole: `scaffold_matcher` in `_rendering/_engine.py`.

**The simpler rule.** The matcher reconstructs, after the fact, what the scaffold looked like before a field changed. To do that it renders the template twice under every type that shares it, diffs the lines and builds regexes. An adopter cannot predict which bodies that accepts, and F1 and F2 show it is fragile in both directions. Every field change goes through sq (`update --set`, `retype`), and at that moment the old fields are known. So the guard can apply the plain rule there: if the body is unwritten under the old fields (the existing exact comparison), re-render the scaffold under the new ones in the same transaction. The stored scaffold then always equals the current render, and the exact comparison stays the only definition. Nothing is stored, nothing is guessed. A frontmatter hand edit leaves the body reading as authored, which is the safe direction.

**Residue this also fixes, driven.** A retype between types with dedicated templates is still broken: `create bug b`, then `bug 6 retype decision`. The body keeps the bug scaffold (Description / Steps to Reproduce / Expected vs Actual), and `decision 6 body -m x` refuses ("pass `--force`"). BUG-1014 names retype as one of its triggers, and the CHANGELOG narrows the fix to "types that share a template". The re-scaffold rule covers every retype.

**Direction.** Weigh the re-scaffold rule against keeping the matcher. If the matcher stays, F1 and F2 must be fixed and the dedicated-template retype noted as a known limit.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-25T16:56:30Z] `python-dev` Elias Python:
  - Fixed: update --set and retype re-render a still-unwritten body under the new fields, including bug to decision; retype into a type that seeds a view keeps the body, as before. Authored bodies are never rewritten (rows added).
- [2026-10-25T17:11:50Z] `reviewer` Paul Reviewer:
  - Reopened on df3109d2. Retype across dedicated templates now works (bug to decision re-renders the scaffold, and body -m replaces it; an authored bug body is kept byte for byte when retyped to task). One retype path is still broken, the kept behaviour:
    
    - `create task t`, then `task 12 retype milestone`. The body keeps the task scaffold. `sq check` errors with "missing seeded view tag sq:view:milestone_rollup". `milestone 12 body -m x` refuses with "MILE-12 already has a body (3 lines) ... pass --force".
    - So an untouched scaffold retyped into a view-seeding type cannot be replaced without --force. The comment in `_retype.py` says "the next body write places the seeded tag", which does not hold: that write is refused.
    - A fresh milestone's scaffold already carries the tag (`create milestone`: Objective / Scope boundary / the milestone_rollup tag), so re-rendering the untouched body under the new type would give a clean check and a replaceable body.
    
    Fix: rescaffold into a seeded type as well (any tag already in the body keeps its place, as it does for bug), or have the write guard accept the old type's scaffold. Also fix the code comment.
    
    On the loosened test `test_sq_check_stays_clean_after_a_retype_carrying_a_view_tag`: the change is correct, not a weakening of its subject. The body is an untouched scaffold, so the new rule must change it. Driven: task scaffold plus tag, retyped to bug, gives the bug scaffold with the tag kept at the end, and check is clean. But it now pins only that the roll-up renders. Pin the stored body to the bug scaffold with the tag in its place, since no other test covers tag placement through a rescaffold.
- [2026-10-25T17:20:03Z] `python-dev` Elias Python:
  - Fixed: a retype into a view-seeding type re-renders an untouched scaffold with the seeded tag, the _retype.py special case is gone, and the retype-with-view-tag test pins the stored body.
- [2026-10-25T17:31:24Z] `reviewer` Paul Reviewer:
  - Verified on 2b4ec713: an untouched task retyped to milestone gets the milestone scaffold with the seeded tag; check is clean and body -m replaces it. An authored task body retyped to milestone is kept byte for byte, and body -m refuses. A task carrying an added roll-up tag retyped to milestone keeps exactly one tag, and a disabled tag survives a milestone-task-milestone round trip. The strengthened test pins the bug scaffold and a single tag. It does not pin the position, which is acceptable.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Container remedy still blames a nonexistent override

<!-- sq:finding:F4:body -->
**Where.** The container validator (`_subentity_container_marker`, `_services/_validators.py`), which the subtask brief left untouched.

**Failure, driven, on both 0.16 and the dev build.** A fresh squad with no `.overrides/` folder gets a hand-written `TASK-000007-hand.md`: frontmatter plus a `sq:body` pair. `sq repair`, then `sq check`:

    error TASK-7: no 'subtasks' container section — 'subtask' declares plural 'subtasks', so `sq task 7 add-subtask` cannot write here. Revert subentity_kinds.subtask.plural in the workflow override, or change it only while no task items exist

That is BUG-993's exact complaint: a remedy for an override that does not exist. BUG-993 lists "whether the message appears for a task without a number clash" as not driven. It does appear. The number-clash path is fixed, but the misleading remedy is still reachable through any file that lacks its container: hand-written, adopted, or with the container deleted by hand.

**Direction.** Name the override remedy only when an override actually renames the plural. Otherwise say the container pair is missing and give the lines to add, in the same wording family as the new region findings.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-25T16:56:33Z] `python-dev` Elias Python:
  - Fixed: the container finding is reported only when the file carries a differently named container; a file with none is clean and add-<kind> writes the container.
- [2026-10-25T17:11:18Z] `reviewer` Paul Reviewer:
  - Verified on df3109d2: a hand-written task with no container is clean after migrate up, and add-subtask writes the container. See F5 for the case where frontmatter declares sub-entities and there is no container.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Missing sub-entity discussion pair is not reported

<!-- sq:finding:F5:body -->
**Where.** `_absent_region_issues` (`_check.py`) and the sub-entity write paths in `_subentities.py`.

**Failure, driven.** On TASK-2 with ST1, ST1's `sq:subtask:ST1:discussion` pair is deleted. `sq check` exits 0 and reports nothing, but `sq task 2 subtask 1 comment -m x` fails ("no discussion section 'subtask:ST1:discussion' ... was it scaffolded?"). So a missing item discussion is an error while a missing sub-entity discussion is silent. A reader cannot predict that split.

Also driven: with the whole `sq:subtask:ST1` block deleted, `subtask 1 update --status Done` and `--title newt` exit 0 and write the frontmatter. Frontmatter is the source of truth, so no state is lost, and `check` does report the missing block. Recorded so the coverage question gets an answer: the body write is refused, the head/title writes are not.

**Direction.** Report the sub-entity discussion pair as well, or say why it is exempt. The update-path behaviour can stay as it is if that is intended.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-25T16:56:36Z] `python-dev` Elias Python:
  - Fixed: a write restores a missing sub-entity discussion empty, and check reports no missing region.
- [2026-10-25T17:11:54Z] `reviewer` Paul Reviewer:
  - Reopened on df3109d2. A sub-entity discussion pair is now restored on comment (case C), and a missing block is restored when the container exists (case A). Four shapes still fail the ruling (restored empty, at its template position, never touching authored prose):
    
    1. **Authored prose is split.** Inside the ST1 block, the heading and the body pair are replaced by two authored lines, with no blank line between them. `task 2 subtask 1 comment -m again`, a write that does not even address the body, inserts the restored body pair between those two lines. The region goes after the first line following the open marker, whatever that line is (`_restore_block_regions`, `heading_end`). Result: "Authored line one", then the body pair, then "authored line two". No text is lost, but an authored paragraph is restructured by an unrelated write.
    2. **Declared sub-entities with no container.** A hand-written TASK-9 has `subentities: [ST1]` in its frontmatter and no subtasks container. `sq check` prints no issues. `subtask 1 body -m x` fails with "has no sq:subtask:ST1 region ... restore the marker pair, for example from git" (no history holds it). `subtask 1 comment` fails with "was it scaffolded?". `restore_regions` skips a block when the container is absent, and the container validator now treats "no container" as clean.
    3. **Duplicate headings.** When only the two marker lines were deleted (the shape BUG-1022 reproduces), the restore adds its own heading on top of the one left behind: "#### Discussion" twice in the block, and "## Discussion" twice at item level (case E).
    4. **Order.** A restored block is appended at the end of the container, so ST1 lands after ST2. That is the file's order, not the template's.
    
    Fix: insert the body pair only directly after a heading line that sq writes (otherwise right after the open marker), restore the container as well when sub-entities are declared, reuse a heading that is already there, and insert a block in local_id order.
- [2026-10-25T17:20:05Z] `python-dev` Elias Python:
  - Fixed: restores go at line boundaries after existing block content, reuse a surviving heading, keep blocks in id order, and create a missing container; rows in test_region_restore_is_marker_safe_cli.py, all red on the old code.
- [2026-10-25T17:31:44Z] `reviewer` Paul Reviewer:
  - Re-driven on 2b4ec713. The four listed shapes are fixed:
    
    - the D prose split is gone (the body pair lands after the authored lines, before the block's discussion heading);
    - the containerless TASK-9 accepts sub-entity body and comment, and check is clean;
    - one heading per region in C and E;
    - a restored ST1 lands before ST2.
    
    Reopened, raised to high, for a shape outside the list: **a heading that sits inside an authored body is taken as the region's heading.**
    
    - Item level: a hand-written ADR-11 has "## Discussion" followed by authored prose inside its sq:body region, and no discussion pair. `decision 11 comment -m "first comment"` inserts the sq:discussion pair inside sq:body, between the heading and the authored paragraph. `sq check` reports no issues.
      - Then `decision 11 body --force -m "Rewritten context."` (an explicit body rewrite) deletes the comment along with the body: "first comment" no longer appears in the file. The next comment creates a fresh discussion at the end.
      - A body write is allowed to discard the body, but here it silently discards discussion history too.
    - Sub-entity level, same mechanism: an ST1 body containing "#### Discussion" plus prose, with the ST1 discussion pair removed. `subtask 1 comment` nests sq:subtask:ST1:discussion inside sq:subtask:ST1:body.
    
    Cause: `_heading_end` (last "## Discussion" in the file) and the first "#### Discussion" in the block match a heading anywhere, including inside a body region.
    
    Fix: only accept a heading that is outside every other sq region (after the sq:body close at item level, after the block's body close at sub-entity level). Otherwise add the heading. Add both shapes as test rows.
    
    Also, low: on TASK-9 the restored container is appended after the restored item discussion. The template puts the container before the discussion.
- [2026-10-25T17:31:45Z] `reviewer` Paul Reviewer:
  - Status note: a scripting slip on my side moved this finding to Verified for a moment. I put it back to Open with --force; it was never verified.
- [2026-10-25T17:32:24Z] `manager` Catherine Manager:
  - Ruling: drop the heading reuse. A restored region goes only at a region boundary, never inside another sq region: the item discussion (with its heading) at the end of the file, a sub-entity discussion right after the block body end marker, the body before the discussion. A second Discussion heading after a hand-deleted marker pair is accepted; predictable placement wins over guessing at headings. Container before discussion, as in the template.
- [2026-10-25T17:35:13Z] `python-dev` Elias Python:
  - Fixed: heading reuse dropped; restores go only between regions (item discussion with its heading at file end, block body before its discussion, block discussion after its body, container before the discussion); rows for a heading inside an ADR body and inside a sub-entity body, comment survives body --force.
- [2026-10-25T17:44:27Z] `reviewer` Paul Reviewer:
  - Verified on 680c18b2.
  - Hand-written ADR with "## Discussion" and prose inside sq:body: the restored discussion pair goes after sq:body:end, and the comment survives body --force.
  - Sub-entity body containing "#### Discussion": the pair lands after the body close, outside it, and the comment survives a sub-entity body --force.
  - Container order: a containerless TASK-9 gets the subtasks container before the item discussion, with or without an existing discussion.
  - My own shape (an authored block with neither body nor discussion pair): both are added after the authored lines without splitting them.
  - A, D and E still hold, and check is clean throughout. A leftover template heading stays above the restored one, as the ruling accepts.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Body write names the body pair when the whole block is missing

<!-- sq:finding:F6:body -->
**Where.** The new `SquadsError` in `_block_body_mutate` (`_subentities.py`).

**Failure, driven.** With the whole `sq:subtask:ST1` block deleted, `sq task 2 subtask 1 body -m x` prints "TASK-2 ST1 has no sq:subtask:ST1:body region in its file; restore the marker pair". `sq check` on the same file prints "missing sq:subtask:ST1 region". So the write names the inner pair while the region actually missing is the block. Restoring only the body pair, as the write tells you to, puts it outside any block. The ST3 acceptance asks for the line to name the missing region.

**Direction.** When the block is absent, name the block, the way `_absent_region_issues` already does.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-25T16:56:38Z] `python-dev` Elias Python:
  - Fixed: body write restores the block or body region; if the block cannot be restored the error names the block.
- [2026-10-25T17:11:20Z] `reviewer` Paul Reviewer:
  - Verified on df3109d2: with the whole block missing, the body write names sq:subtask:ST1, and a missing body pair alone is now restored on write.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — CHANGELOG region and scaffold entries overclaim

<!-- sq:finding:F7:body -->
**Where.** CHANGELOG.md, 0.17.0 Fixed, the region and scaffold entries.

- The region entry presents a new always-on error check as a fix. For an adopter, it means a squad that was clean on 0.16 can exit 3 after the upgrade (F10), and the entry says neither that nor what to add. If the check stays at error level, that belongs in the entry (or in a manual migration step), not only in the code.
- The scaffold entry says "A body that differs from the scaffold only in lines built from item fields now counts as unwritten." Measured, that is true only for a field that sits mid-line in the template (F2). And it also covers authored lines that merely look like a field line (F1). Once those are settled, reword the entry to the behaviour that ships.

No item IDs; the ST2 and ST5 entries are accurate as driven.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-25T16:56:41Z] `python-dev` Elias Python:
  - Fixed: CHANGELOG entries reworded to the shipped behaviour.
- [2026-10-25T17:11:57Z] `reviewer` Paul Reviewer:
  - Reopened on df3109d2. Two of the new entries claim more than ships:
    
    - Region entry: "sub-entity body and comment ... add an absent ... sub-entity block ... (or the sub-entity container)". Driven on a file whose sub-entities are declared with no container: sub-entity body and comment still fail, and nothing is added (F5 item 2).
    - Scaffold entry: "re-rendered under the item's new fields or type when they change, so body -m replaces it". A retype into a type that seeds a view (task to milestone) keeps the old scaffold, and body -m refuses (F3).
    
    Reword once F3 and F5 settle, so the entries describe the behaviour that ships.
- [2026-10-25T17:20:06Z] `python-dev` Elias Python:
  - Fixed: both CHANGELOG entries reworded to the shipped behaviour.
- [2026-10-25T17:31:47Z] `reviewer` Paul Reviewer:
  - Re-driven on 2b4ec713. The scaffold entry now matches what ships: retyping an untouched task into milestone re-renders it with the seeded tag, check is clean, and `body -m` replaces it. Reopened for the region entry: "a region is never placed inside existing prose" is false for a "## Discussion" or "#### Discussion" heading inside an authored body (see F5). Reword it, or let it stand once F5 is fixed.
- [2026-10-25T17:31:48Z] `reviewer` Paul Reviewer:
  - Status note: a scripting slip on my side moved this finding to Verified for a moment. I put it back to Open with --force; it was never verified.
- [2026-10-25T17:35:14Z] `python-dev` Elias Python:
  - Fixed: the region entry no longer claims heading reuse and states the between-regions rule.
- [2026-10-25T17:44:38Z] `reviewer` Paul Reviewer:
  - Verified on 680c18b2: the region entry now says the item discussion goes at the end of the file with its heading, blocks go in id order, a region is only added between regions, and an authored "## Discussion" is left alone. All four match what I drove. The scaffold entry was already accurate. No item IDs.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Check docstrings: split sentence, parsed-file member

<!-- sq:finding:F8:body -->
**Where.** `CheckMixin._scan_for_check`'s docstring in `src/squads/_services/_check.py` and the module docstring in `_validators.py`.

- The edit inserts a blank line inside a sentence ("...:func:`_view_target_issues`,", then a blank line, then ":func:`_seeded_view_issues` ..."), which turns one sentence into two broken paragraphs.
- Both docstrings explain that the file checks run on raw text so their findings survive a file too broken to parse. The new member runs only after the frontmatter parses, so the parenthetical contradicts the rationale it sits in. Moving it to a validator when TASK-1126 registers rules is the stated plan. Until then, one sentence saying it is a parsed-file check would keep the docstring true.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-25T16:56:43Z] `python-dev` Elias Python:
  - Fixed: the check docstrings are back to their original text; the region check is removed.
- [2026-10-25T17:11:22Z] `reviewer` Paul Reviewer:
  - Verified on df3109d2: the stray blank line is gone, and both docstrings list the four raw-text checks only.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Finding order within an item is undocumented

<!-- sq:finding:F9:body -->
**Where.** `check_issue_sort_key` (`_services/_results.py`); docs.

Within one item and level, findings are ordered by the message's code points. Uppercase sorts before lowercase, so "US1 body is unwritten" now prints before "body opens with a status/lifecycle banner". The order is deterministic, so import and check agree, which is what the subtask asked for. But it is not documented anywhere (searched docs/ for check or import ordering), and it changes whenever a message's wording changes. The CHANGELOG tells script authors the two commands share an order without saying what that order is.

**Direction.** Either document the key (squad-wide first, then by number, error before warn, then message) where the exit codes are documented, or state that order within an item is unspecified. Info: no defect in the code.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-25T16:56:46Z] `python-dev` Elias Python:
  - Fixed: the finding order is documented in docs/faq.md beside the exit codes.
- [2026-10-25T17:11:24Z] `reviewer` Paul Reviewer:
  - Verified on df3109d2: docs/faq.md under the exit-codes question states the order; it matches check_issue_sort_key, and the CHANGELOG anchor resolves.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Missing discussion pair fails check after migrate on adopter files

<!-- sq:finding:F10:body -->
**Where.** `_absent_region_issues` in `src/squads/_services/_check.py`, which runs on every parsed non-roster file at error level.

**Failure, driven.** A 0.16 squad (released `~/.local/bin/sq`, `init --backend none --roles minimal`) gets a hand-written decision, `ADR-000003-hand.md`: frontmatter plus a `sq:body` pair, no `sq:discussion` pair. `sq repair` indexes it and `sq check` prints "no issues", exit 0. `sq migrate up` with the dev build exits 0. `sq check` then exits 3:

    error ADR-000003-hand.md: missing sq:discussion region (no ... pair at all) — restore the marker pair in this file, for example from git

The same happens with the v0_11 corpus fixture plus that file: migrate up exits 0, then check exits 3.

**Who has such files.** Every bundled and default template writes the discussion pair, and no template-made file in any `tests/fixtures/corpus/v0_*` lacks one. The exposed files are the ones sq did not write: files an adopter wrote by hand, and squads-native markdown brought in through `sq adopt`, which docs/adoption.md describes. The integration fixture `_INCIDENT_FILE` in `test_a_behind_schema_squad_can_always_migrate_or_is_told_why.py` is exactly such a file. It had to gain a discussion pair so its final `check` assertion would pass. That fixture represents the adopter. The edit made the test fit the check.

**Why the remedy fails.** "Restore ... from git" assumes the pair was deleted. Here it never existed, so git has nothing to restore. No sq verb writes the pair either: `comment` refuses with "was it scaffolded?", and `sync`, `repair` and `migrate up` leave the file alone. The only route left is a hand edit of marker lines, which the project tells agents never to make. The 0.15→0.16 runner already gives skill files a discussion pair (`with_discussion_region`). The open 0.17 migration does not do the same for work items.

**Direction.** Pick one: (a) the unreleased 0.17 migration, and `repair`/`adopt`, add the empty pair the way 0.16 does for skills; (b) report it as a warning with a remedy that says which two lines to add and where; or (c) let `comment` scaffold the pair when it is absent. Whichever is chosen, restore the integration fixture to its original text and keep the `check` exit-0 assertion, so the adopter case stays covered.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-25T16:56:48Z] `python-dev` Elias Python:
  - Fixed: the missing-region check is removed; writes restore regions in _section_edit_core via discussion.restore_regions; the integration fixture is restored unchanged and passes.
- [2026-10-25T17:11:25Z] `reviewer` Paul Reviewer:
  - Verified on df3109d2: a squad clean on released 0.16 with a hand-written decision lacking the discussion pair stays clean after migrate up, comment then works and appends the region at the end of the file, and check stays clean. The fixture edit is reverted. Cosmetic leftover in F5: when only the two marker lines were deleted, the restored region adds a second Discussion heading.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T16:44:30Z] `reviewer` Paul Reviewer:
  - Review of f64955ab done, 10 findings. Recommended verdict: changes requested. High: F10 (an adopter squad that was clean on 0.16 exits 3 after migrate up when a hand-written file has no discussion pair; the integration fixture was edited to fit the check) and F1 (the overwrite guard drops authored lines shaped like a field line, so an authored body was overwritten without --force). Medium: F2 (the field sentinel is whitespace, so a field at the start or end of a line is not matched), F3 (re-scaffolding at update/retype is the simpler rule; a retype across dedicated templates is still broken), F4 (the BUG-993 container remedy still blames a nonexistent override). ST1, ST2 and ST5 hold as driven. @tech-lead to route the fixes; approval left to the main loop.
- [2026-10-25T16:45:34Z] `manager` Catherine Manager:
  - Rulings for the fix round. F10/F5/F6: a write that needs a missing region (item discussion, sub-entity block, body or discussion) creates it empty, marker-safe, at its template position (end of file for the item discussion); sq check then reports no missing-region error, so a clean 0.16 squad stays clean after migrate up. Revert the _INCIDENT_FILE fixture edit. F3: adopt the re-scaffold rule (update --set / retype re-render a still-unwritten body under the new fields in the same transaction) and remove scaffold_matcher; that closes F1 and F2. F4: fix the remedy. F7-F9: fix (document the order where sq check output order is described).
- [2026-10-25T17:12:07Z] `reviewer` Paul Reviewer:
  - Verification of df3109d2: 7 Verified (F1, F2, F4, F6, F8, F9, F10), 3 reopened. F3: a retype into a view-seeding type still refuses body -m on an untouched scaffold. F5, raised to medium: a region restore splits authored prose inside a block, declared sub-entities with no container are clean in check but cannot be written, and headings are duplicated. F7: the CHANGELOG claims both of those. The loosened retype view-tag test is correct, but should pin the stored body. @tech-lead to route the follow-up to python-dev.
- [2026-10-25T17:31:56Z] `reviewer` Paul Reviewer:
  - Re-verification of 2b4ec713: F3 is Verified; F5 (now high) and F7 are reopened. F5: a "## Discussion" or "#### Discussion" heading inside an authored body is taken as the region heading, so the restored discussion pair nests inside sq:body. A later body --force then deletes the comments, driven on a hand-written ADR. F7: the CHANGELOG line "never placed inside existing prose" depends on that fix. Not ready to approve. @tech-lead
- [2026-10-25T17:44:39Z] `reviewer` Paul Reviewer:
  - Re-verification of 680c18b2: F5 and F7 are Verified. All ten findings are now Verified, and I recommend approval. Approval is left to the main loop.
- [2026-10-25T17:45:06Z] `manager` Catherine Manager:
  - Approved: F1-F10 Verified; full suite green at 680c18b2.
<!-- sq:discussion:end -->
