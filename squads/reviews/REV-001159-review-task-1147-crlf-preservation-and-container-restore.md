---
id: REV-1159
sequence_id: 1159
type: review
title: 'Review TASK-1147: CRLF preservation and container restore'
status: Approved
author: reviewer
refs:
- TASK-1147
subentities:
- local_id: F1
  title: CRLF files leak CR into --json bodies, show output and the template-body
    guard
  status: Verified
  severity: medium
- local_id: F2
  title: add-<kind> as the first write after a container loss still detaches the existing
    blocks
  status: Verified
  severity: medium
- local_id: F3
  title: Container restore can nest inside the discussion region or duplicate the
    heading
  status: Verified
  severity: low
- local_id: F4
  title: add-<kind> on a half-present container crashes with a KeyError traceback
  status: Verified
  severity: low
- local_id: F5
  title: Three mutants survive the new tests (CRLF heading regex, check half-present
    guard)
  status: Verified
  severity: low
- local_id: F6
  title: Skill restamp and skill region repair write item files without conforming
    line endings
  status: Verified
  severity: low
- local_id: F7
  title: Greedy alignment can flip untouched endings in a large mixed-ending file
  status: Verified
  severity: low
- local_id: F8
  title: 'Five mutants survive the fix tests: roster frontmatter and renumber seam
    routing, heading scope'
  status: Verified
  severity: low
- local_id: F9
  title: No test depends on the in-order reduction of unique anchors in the large-span
    alignment
  status: Verified
  severity: low
created_at: '2026-10-26T05:16:29Z'
updated_at: '2026-10-26T06:38:11Z'
---
<!-- sq:body -->
## Scope

Commit b7e8ba29 on release/0.17 (TASK-1147): ST1 reads item files verbatim and conforms every item and managed-region write to the on-disk line endings (`_aio.read_text`, `_sections.conform_line_endings`, `_itemfile.write_text`, `_managed_region.inject`, `place_view_tags`); ST2 restores a lost sub-entity container around the surviving blocks (`_discussion._restore_container`) and adds the `block_in_container` warn rule.

## Method

- Drove a dev-build scratch squad converted to CRLF through show, show --full, --json (item, sub-entity, list, tree, inbox, check), comment add/show/edit, status, update --title (rename), retype, add-subtask, add-finding, sub-entity body/status/comment, ref add, body, view disable/add, check, repair; a mixed-ending file; a 0.16 corpus converted to CRLF through `migrate up` and `sync`. Compared every output byte-wise against the LF twin.
- Swapped the parent commit's read back in to attribute each difference.
- Drove nine container-loss shapes (pair removed; pair and heading removed; a block moved past the discussion; blocks moved into the discussion; CRLF; out of order; one block removed with the pair; half-present pair; an author heading above the blocks), each followed by a sub-entity write and an `add-subtask`.
- Ran the dev build's `sq check` on a copy of this repo's corpus: zero `block_in_container` hits.
- Mutated a scratch copy of the code (15 mutants) against the five new or changed test files; 12 go red.
- Measured `conform_line_endings`: 28 ms on this repo's largest item (2,748 lines) converted to CRLF; quadratic on adversarial input (5k lines 1.3 s, 20k lines 17 s), and only when the file holds a CR.

## What holds

Untouched lines keep their bytes through every write verb, rename, retype, migrate up and the managed CLAUDE.md region. Inserted lines follow the stated dominant rule (a tie goes to LF). An undecodable existing file now fails the write with the clean `UndecodableFileError` line, exit 1. The extra read per write is inside the transaction lock and costs one small read; it does not touch the spec-document load counts. pyright, ruff and the targeted tests are green.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1159 add-finding "…" --severity medium`; track with `sq review 1159 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — CRLF files leak CR into --json bodies, show output and the template-body guard

<!-- sq:finding:F1:body -->
The read is now verbatim, but the consumers that parse a region out of the text still assume LF. `get_section` returns the raw inner text and its callers strip only `\n`, so on a CRLF item file the CR reaches every reader of a region. Driven on a dev-build scratch squad converted to CRLF, compared with its LF twin; the parent commit's read gives the LF output on the same files, so each of these is new in this commit:

- `--json` (item `show --json`, `show --full --json`, sub-entity `show --json`): every `body` is `"\r\nsb\r"` / `"\r\n## Description\r\n\r\n_TODO: describe this task._\r"` instead of `"sb"` / `"## Description\n\n_TODO: describe this task._"`. This is the machine surface the clients read.
- `show`, `show --full`: every region renders with extra blank lines; a milestone with its rollup view gains four. The sub-entity `show` prints a blank discussion instead of `(none)`.
- The template-body guard compares against an LF template, so `sq task 22 body -m new` on a CRLF task whose body is still the template refuses ("Nothing was written... pass --force"). On the LF twin, and on the parent build, it writes.

Titles, discussion entries, comment hashes and `sq check` are unaffected.

Failure scenario: a Windows checkout with autocrlf; the VS Code client reads `show --json` and displays or diffs bodies that start with a CRLF and end in a CR, and a new task's template body cannot be replaced without `--force`.

Fix direction: give the parsing reads an LF view (normalise in `get_section` or at the model/display read) while the write path keeps the verbatim text, and add the CRLF twin of the show/--json/body-guard rows to the existing table.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T05:39:33Z] `python-dev` Elias Python:
  - Fixed. _aio.read_text reads LF again (no reader sees a CR); verbatim=True is used only by the item write seam (conform against the on-disk bytes) and the managed-region inject. update_frontmatter and rewrite_ids now write through the conforming seam. Table: tests/cli/test_a_crlf_item_reads_like_its_lf_twin_cli.py (show, --full --comments, --json, --full --json, sub-entity show/--json, list, for task/feature/review) plus the template-body guard on a CRLF task.
- [2026-10-26T06:02:20Z] `reviewer` Paul Reviewer:
  - Verified on 3724d3a2: CRLF and LF twins give byte-identical output on every show/--json surface, list, tree, inbox, mine, blocked, check --json, role/skill show and workflow; the template-body guard accepts a CRLF template; writes, sync, repair and migrate up keep CRLF.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — add-<kind> as the first write after a container loss still detaches the existing blocks

<!-- sq:finding:F2:body -->
`restore_regions` runs only on the `_locked_section_edit` seam (body, comment, sub-entity body/status). `_add_block_core` (`_services/_subentities.py`) does not call it: when the container is missing it calls `ensure_subentity_container_text`, which appends a new heading and an empty pair, and the new block goes inside it.

Driven: task with ST1-ST3, the two `sq:subtasks` marker lines deleted, then `sq task 22 add-subtask "sub d"` as the first write. Result: a second `## Subtasks` heading and a fresh pair after the `## Discussion` region, holding only ST4; ST1-ST3 stay outside. That is BUG-1144's outcome unchanged, only reached through `add-<kind>` first rather than through a sub-entity body write first. The new rule warns on ST1-ST3 afterwards; the write itself succeeds.

The same path bypasses the refusal: with prose between the surviving blocks, `subtask 1 body` refuses as specified, but the following `add-subtask` succeeds and builds the same detached container.

The service test drives the body write first, so it does not see this path. Fix direction: route the missing-container case of `_add_block_core` through `_restore_container` (or `restore_regions`), and add an `add-<kind>`-first row per kind.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T05:39:34Z] `python-dev` Elias Python:
  - Fixed. _add_block_core restores a lost container through discussion.restore_container (same enclosure and refusal as the write seam). Rows: add-first per kind with heading kept/gone, and prose-between refuses an add per kind.
- [2026-10-26T06:02:21Z] `reviewer` Paul Reviewer:
  - Verified: add-first gives one heading with all blocks inside for subtask, story and finding (pair gone, heading gone, CRLF, out of order, only block); prose between blocks refuses on the add and the body paths.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Container restore can nest inside the discussion region or duplicate the heading

<!-- sq:finding:F3:body -->
`_restore_container` encloses the surviving blocks wherever they are and reuses a heading only when the last `## ` heading above the first block is the container's own. Two shapes this misses, both driven on the dev build:

- Blocks inside another region (all three blocks moved above `sq:discussion:end`): the container and a new `## Subtasks` heading are written inside the discussion region, and the original `## Subtasks` heading above stays. Afterwards `sq check` reports no issue at all, since the block is now inside its container and the nesting is not checked. This contradicts the `restore_regions` docstring ("A region goes only between existing regions, never inside one").
- An author heading between the container heading and the first block (`## Subtasks`, the hint, `## Notes`, then the blocks): a second `## Subtasks` is written under `## Notes`. ST2's spec says no duplicate heading is written.

Fix direction: refuse, like the prose-between case, when the first block's position is inside another region; and look for the container's own heading anywhere between the preceding region and the first block rather than only at the last heading.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-26T05:39:35Z] `python-dev` Elias Python:
  - Fixed. Blocks inside another top-level region refuse the restore; the container heading is looked for between the previous region close and the first block. Rows: blocks inside the discussion, author heading above the blocks (one container heading).
- [2026-10-26T06:02:22Z] `reviewer` Paul Reviewer:
  - Verified: blocks inside the discussion or the body region refuse with one line per kind; an author heading above the blocks gives one container heading.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — add-<kind> on a half-present container crashes with a KeyError traceback

<!-- sq:finding:F4:body -->
With only the `sq:subtasks:end` line removed (half-present container), `restore_regions` skips as documented and the sub-entity body write succeeds, but `sq task 22 add-subtask "sub d"` dies with a Rich traceback ending in `KeyError: "section 'subtasks' not found"` from `_sections.append_to_section`, called by `_add_block_core`. Exit code is not the clean `SquadsError` exit.

The parent build fails the same way, so this predates the commit, but it sits on the surface ST2 changed and ST2's contract asks for one error line when the container cannot be restored. `sq check` does report the unclosed marker.

Fix direction: in `_add_block_core`, raise a `SquadsError` naming the item and the half-present container (the `stale_container_tags` branch already does this for one shape), and add the half-present row to the restore test.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-26T05:39:37Z] `python-dev` Elias Python:
  - Fixed. add-<kind> on a half-present container raises one SquadsError line naming the item and container. Row per kind and per missing marker; the write seam leaves it untouched.
- [2026-10-26T06:02:24Z] `reviewer` Paul Reviewer:
  - Verified: either marker missing gives one SquadsError line on add, per kind; the write seam leaves the file alone.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Three mutants survive the new tests (CRLF heading regex, check half-present guard)

<!-- sq:finding:F5:body -->
Mutating a scratch copy against the five new or changed test files, three mutants survive:

- M11: drop `\r?` from the heading regex in `_restore_container`'s no-survivors branch (`rf"^## {re.escape(heading)}[ \t]*\r?$"`). On a CRLF file whose container was removed with its only block, the heading is then not found and a second one is written. No test drives that branch on CRLF.
- M13: drop the half-present guard in `_blocks_outside_container_issues`. Every block then also warns next to the unclosed-marker error. No test covers a half-present container in the check rule.
- M15: replace `_pair_absent` with the old `get_section(...) is None` in `restore_regions`. It survives, probably because `stale_container_tags` already returns for a half-present pair; if the two are equivalent, the change is not needed, and if they are not, a row should show the difference.

Fix direction: add the CRLF no-survivors row and the half-present check row; state, or remove, the reason for the M15 change.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-26T05:39:38Z] `python-dev` Elias Python:
  - Fixed. M11 is gone: reads are LF, so the CR-tolerant heading regex was dead and is removed; an only-block CRLF row now drives that branch end to end. M13 and M15 each go red on the new half-present rows (re-mutated: 6 rows red each). Also conform_line_endings is linear now (equal head/tail trimmed, small middle fully diffed, large middle matched greedily): 40k-line CRLF file with scattered edits in 0.12 s, row in tests/unit/test_conform_line_endings.py (not tests/test_scale.py).
- [2026-10-26T06:02:25Z] `reviewer` Paul Reviewer:
  - Verified: M13 and M15 go red (6 rows each); the M11 branch is removed. Other survivors are filed as F8.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Skill restamp and skill region repair write item files without conforming line endings

<!-- sq:finding:F6:body -->
Two writers of item files still call `_aio.atomic_write_text` directly instead of `_itemfile.write_text`, so they do not conform to the file's line endings:

- `_restamp_managed_skill_frontmatter` (`_services/_maintenance.py`, the `atomic_write_text(folder / name, join_frontmatter(...))` call), which runs ahead of `sq sync`.
- The region-repair branch of the Claude Code backend's skill-body write (`_backends/_claude_code/_backend.py`, `atomic_write_text(body_path, text)` when the body region is absent or partial).

Driven on 3724d3a2: a CRLF squad, the `id:` line deleted from `SKILL-000009-greeting.md`, then `sq sync`. The file was restamped and came back with 0 CRLF and 24 LF; every line was flipped, not just the restamped frontmatter.

Both are repair paths for an already damaged file, hence low. Fix direction: route both through `_itemfile.write_text`, and add a CRLF row for the restamp.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-26T06:17:17Z] `python-dev` Elias Python:
  - Fixed. The skill restamp (_maintenance) now writes through _itemfile.write_text and the Claude Code skill body repair conforms to the on-disk bytes. Grep of direct writers: no other item or skill .md bypasses the seam; board notices, memory entries and override stamps are whole-file renders outside it and still write LF. Rows in tests/service/test_repair_writers_keep_the_files_line_endings.py (sync restamp, refresh_managed region repair); both go red when reverted.
- [2026-10-26T06:33:30Z] `reviewer` Paul Reviewer:
  - Verified on 5528700e: sync restamp of a CRLF skill with its id deleted keeps 24 CRLF, 0 LF; reverting either writer (M25, M26) turns its row red.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Greedy alignment can flip untouched endings in a large mixed-ending file

<!-- sq:finding:F7:body -->
When the edited middle of a file is larger than `_FULL_DIFF_CELLS`, `_align` matches each new line to the earliest unused equal old line. Content is always correct: a fuzz of 3,000 random mixed-ending files times edit, insert, duplicate-insert, delete and swap, at head, tail and middle, on both paths gives `out` equal to `new` once endings are normalised. But one early match to a far duplicate skips every old line in between, and those lines then take the dominant ending instead of their own.

Driven: 3,000 lines with alternating endings, a copy of line 2,800 inserted at line 10 and an edit at line 2,900. The greedy path flips the endings of 1,395 lines the write did not touch; the full diff flips 0. On the shape that occurs in practice (this repo's REV-926, 2,748 lines, CRLF with a 300-line LF tail, `updated_at` changed and a finding block inserted), both paths flip 0.

Only mixed-ending files above about 2,000 x 2,000 middle lines are exposed; in a single-ending file the dominant ending is the file's own. Fix direction: in the greedy path, anchor only on lines that are unique in both middles (patience-style), and leave the rest of each gap unpaired.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-26T06:17:18Z] `python-dev` Elias Python:
  - Fixed. The large-span alignment now splits at lines unique to both sides (longest in-order run), re-aligns each part (head/tail trim, full diff when small), and leaves anchorless parts unmatched; still n log n. Rows: the reviewer 3000-line alternating shape on both paths, and a seeded randomized property (20 seeds x 2 paths) that every untouched line keeps its ending; 19 rows red on the old greedy.
- [2026-10-26T06:33:31Z] `reviewer` Paul Reviewer:
  - Verified: the 3000-line alternating shape flips 0 lines on full, anchored and forced-anchored paths; a fuzz of 44,871 checks over 3 paths keeps content and every unambiguous ending; adversarial 40k lines in 1.3 s. The in-order reduction step has no row: filed as F9.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Five mutants survive the fix tests: roster frontmatter and renumber seam routing, heading scope

<!-- sq:finding:F8:body -->
Re-ran my mutations, plus new ones for the fix code, against the nine test files the two commits touch (285 tests). These survive:

- M21: `update_frontmatter` back to `_aio.atomic_write_text`. Only roster updates use it (`_services/_roster.py`). The behaviour is correct (driven: `sq role tech-lead update --model sonnet` on a CRLF role file keeps 21 CRLF and 0 LF), but no test drives it.
- M22: `rewrite_ids` back to `_aio.atomic_write_text` (renumber). Untested on CRLF.
- M23: the container-heading search widened from the gap after the previous region to the whole text above the first block. The author-heading row passes either way, so the scoping that keeps an author's own heading inside the body from being reused has no row.
- M19 (drop the skip-behind loop in the greedy path) and M20 (drop the head trim) also survive. Both look benign: the fuzz gives the same content, and the head trim only matters for speed.

The other 19 go red, including the earlier M13 and M15 and the new inside-region refusal, add-path half-present guard and full-diff threshold. Fix direction: add a CRLF row for a roster update and for renumber, and a row with a heading of the container's name inside the body region.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-26T06:17:20Z] `python-dev` Elias Python:
  - Fixed. Rows for update_frontmatter (role update on a CRLF file), rewrite_ids (retype mention rewrite in a CRLF file) and the container-heading search bound (a heading of the container name inside the body); each mutant now goes red. M19/M20 are benign as the reviewer said.
- [2026-10-26T06:33:32Z] `reviewer` Paul Reviewer:
  - Verified: M21, M22 and M23 each go red on the new rows.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — No test depends on the in-order reduction of unique anchors in the large-span alignment

<!-- sq:finding:F9:body -->
`_unique_anchors` cuts the unique-line pairs down to the longest run in which both indices increase (the bisect/link step). No test depends on that step. Mutant M30 returns every pair unreduced (`return pairs` before the run rebuild) and all 332 tests in the ten touched test files still pass, as does my random-edit fuzz.

The step carries correctness. Driven on 5528700e with the anchored path forced (`_FULL_DIFF_CELLS = -1`): 400 random mixed-ending files of 20-200 lines, with two unique lines swapped. With the run step, 8 trials flip some untouched line's ending, close to the full diff's 3, so a swap is ambiguous on either path. With M30, 174 trials flip one.

Failure scenario: a later edit drops or weakens the in-order reduction, and a write that reorders lines in a large mixed-ending file rewrites the endings of lines it did not touch, with the suite green.

Fix direction: add a row to `tests/unit/test_conform_line_endings.py` that swaps two unique lines in an anchored span (small `_FULL_DIFF_CELLS`) and asserts that every line other than the two keeps its ending. M28 (a duplicate line counted as unique) also survives; on my fuzz it gives the same output, so I count it as equivalent.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-26T06:36:39Z] `python-dev` Elias Python:
  - Fixed. New rows in tests/unit/test_conform_line_endings.py: the alignment must tile both texts in order when lines are swapped (60 seeded cases, small _FULL_DIFF_CELLS), plus a swap row asserting untouched endings. Removing the in-order reduction in _unique_anchors turns 59 tiling rows red. The ending-only row cannot see the step (its flips are no worse without it), so the tiling invariant carries the proof.
- [2026-10-26T06:37:41Z] `reviewer` Paul Reviewer:
  - Verified on da1f550f. My shape (400 files of 20-200 lines, half duplicated short lines, half unique, random endings, two unique lines swapped) is a real gap: 8 flipped files with the in-order step on the forced-anchored path (3 with the full diff), 174 without it. The new tiling row catches the mutant: 59 of its cases go red without the step, and all 194 pass with it. No reopen needed.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T05:17:30Z] `reviewer` Paul Reviewer:
  - Review of b7e8ba29 done; five findings, recommended verdict ChangesRequested.
    - F1 (medium): CRLF regression on the read side. `--json` bodies carry CR, show doubles blank lines, the template-body guard refuses on a CRLF file. Confirmed new by swapping the parent read back in.
    - F2 (medium): BUG-1144 still reproduces when `add-<kind>` is the first write after a container loss; `_add_block_core` bypasses `restore_regions`, including its refusal.
    - F3 (low): a restore can nest the container inside the discussion region, or write a second heading when an author heading sits above the blocks.
    - F4 (low, predates the commit): half-present container plus `add-<kind>` crashes with a KeyError traceback.
    - F5 (low): three surviving mutants (CRLF heading regex, check half-present guard, `_pair_absent` swap).
    What holds: byte preservation through every write verb, rename, retype, migrate up, sync and the managed region; a clean error on undecodable files; `block_in_container` gives zero false hits on this repo's corpus; gates green. Details are in the review body. @tech-lead for the fix routing.
- [2026-10-26T06:02:33Z] `reviewer` Paul Reviewer:
  - Re-review of 3724d3a2. F1-F5 verified fixed, three new low findings (F6-F8), review stays InReview; no medium or high open.
    - F1: CRLF and LF twins give byte-identical output on show, --full --comments, --json, --full --json, sub-entity show and --json, list, tree, inbox, mine, blocked, check --json, role/skill show and workflow. The template-body guard accepts a CRLF template. Every write verb, rename, retype, sync, repair and a 0.16 to 0.17 migrate up keep CRLF, and the managed CLAUDE.md region stays CRLF.
    - F2: add-first gives one heading with every block inside, for subtask, story and finding, including heading-gone, CRLF, out-of-order and only-block shapes; prose between blocks refuses on both paths.
    - F3: blocks inside the discussion or the body refuse; an author heading above the blocks gives one heading.
    - F4: a half-present container (either marker) gives one SquadsError line per kind.
    - F5: M13 and M15 now go red; M11's branch is gone.
    - Timing row: the workload runs in 0.06 s against the 3 s bound, about 50x headroom on this shared box; a full-diff-only build takes 82 s, so the row catches a quadratic regression.
    - New: F6, two skill-file repair writers bypass the conforming seam (driven: a sync restamp flips a CRLF skill to LF); F7, the greedy path can misattribute endings on a large mixed-ending file (adversarial only, content always right); F8, five surviving mutants, three of them test gaps.
- [2026-10-26T06:33:35Z] `reviewer` Paul Reviewer:
  - Re-review of 5528700e. F6-F8 verified fixed; one new low finding (F9, a test gap); review stays InReview.
    - F6: CRLF squad, `id:` deleted from a skill file, then `sq sync`: restamped with 24 CRLF, 0 LF. M25/M26 (restamp and backend repair reverted to direct writes) go red.
    - F7: the 3,000-line alternating shape flips 0 lines on the full, anchored and forced-anchored paths. Fuzz of 2,500 random mixed files x 6 edit shapes x 3 paths (44,871 checks): content always right, endings right on every unambiguous shape. Adversarial 40k-line file (21 unique anchors, heavily duplicated 1,900-line gaps, scattered edits): 1.3 s.
    - F8: M21, M22 and M23 now go red.
    - Mutation total: 28 mutants on the ten touched test files (332 tests), 25 red. M24 (never full diff) is equivalent in output. M28 looks equivalent. M30 is filed as F9.
    - Board notices, memory entries and override stamps writing LF: acceptable. They are whole-file records outside TASK-1147's scope (item files, index, managed regions), git normalises them under autocrlf or eol attributes, and no agent-authored region inside an item is rewritten. If CRLF fidelity is ever wanted there, it is a separate bug, not a defect of this task.
- [2026-10-26T06:37:43Z] `reviewer` Paul Reviewer:
  - All nine findings verified fixed at da1f550f. Verdict: Approved.
<!-- sq:discussion:end -->
