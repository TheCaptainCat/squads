---
id: REV-1280
sequence_id: 1280
type: review
title: Stored view bodies (FEAT-1270, TASK-1275)
status: Approved
author: reviewer
refs:
- FEAT-1270
- TASK-1275
subentities:
- local_id: F1
  title: CRLF in a stored body is lost on read and makes set_view_body rewrite on
    every call
  status: Verified
  severity: medium
- local_id: F2
  title: views.<name> entry shape and transform body keyword are not recorded in any
    ADR
  status: Verified
  severity: medium
- local_id: F3
  title: 'Duplicate stored pairs: the check remedy drops the second body, round trip
    is refused'
  status: Verified
  severity: low
- local_id: F4
  title: A stored-view tag without its end tag is a check error no verb can clear
  status: Verified
  severity: low
- local_id: F5
  title: New CLI tests read item files and assert substrings, against ADR-1172 section
    5
  status: Verified
  severity: low
- local_id: F6
  title: The clean 0.19 fixture carries a pair for an undeclared view
  status: Verified
  severity: low
- local_id: F7
  title: CLAUDE.md architecture map does not name _view_bodies.py
  status: Verified
  severity: info
created_at: '2026-11-03T23:44:57Z'
updated_at: '2026-11-03T23:59:06Z'
---
<!-- sq:body -->
Batch review of FEAT-1270 (stored view bodies) as delivered by TASK-1275, against ADR-1274 §4, §12 (paired-tag findings) and §13, ADR-880 §4, ADR-776 §1 and ADR-1172. The change reviewed is the uncommitted working tree on `release/0.20`.

## What was checked

- The escape grammar: an exhaustive probe of every string of length 1 to 7 over `<`, `!`, `-`, `a` and a newline. `unescape(escape(x)) == x`, `decode_inner(encode_inner(x)) == x`, and no escaped text contains `<!--`. No failure.
- Pair recognition and the edges: a pair at the top and at the bottom of `sq:body`, a stored body with leading and trailing blank lines, a forged `sq:body` end tag, `<!!--` runs, nested or forged tags in an incoming body (a lone end tag, or a pair with another marker between its tags, is refused by `reject_markers`), a disabled pair, and a CRLF item file. All of these hold, except CRLF inside the stored text (F1).
- Body writes: an omitted pair comes back byte for byte, the `show --json` body round-trips, and an altered pair is refused. `strip_view_tags` takes a pair whole, so decision 3 holds and `reject_body_overwrite` needs no change.
- Reads never write: `show`, `--raw`, `show --json` and `sq workflow view` only read. The daemon GET test carries a pair.
- Check and repair: the four findings, `markers_balanced` exempting the view family, and the retired-region sweep never matching `sq:view:head`. The sweep property was falsified by monkeypatching the old `_retired_region_tags` back in: the clean-corpus migrate test goes red.
- The migration runner scans `db.items` after `plan_reconcile` has rebuilt the index from the files, and `_pre_runner_refusal` stops the run on any file it cannot index. That makes the scan as complete as the corpus is defined for every runner (the 0.19 runner does the same). The header regex matches the on-disk header grammar, and `split_lines` makes it CRLF-safe.
- Layering: five new import-edge rows, no cycle, and the guard passes. ruff and pyright are clean on the touched modules.
- Conventions: no ticket IDs, versions or history in the new docstrings (the runner is the exception). No bare type aliases. No status prose.

## The five flagged decisions

1. The `{"body", "data"}` entry under `views`: the shape is sound, but it is a wire-contract change that no ADR records (F2).
2. `body` as an opt-in transform keyword: agreed. It is additive, but ADR-1109's call signature needs the same in-place note (F2).
3. No change to `reject_body_overwrite`: confirmed.
4. An unpaired stored tag is kept by a body write: agreed for body writes. `view add` should complete the pair, because nothing else clears the error that `sq check` reports (F4).
5. `set_view_body` cases deferred to the pull task: agreed, as planned in ST3.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1280 add-finding "…" --severity medium`; track with `sq review 1280 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — CRLF in a stored body is lost on read and makes set_view_body rewrite on every call

<!-- sq:finding:F1:body -->
**Where:** `src/squads/_view_bodies.py:38` (`decode_inner`) and `src/squads/_services/_views.py:177` (the no-op test in `set_view_body`).

**Scenario (reproduced on a scratch squad, LF item file):** call `set_view_body("TASK-2", view, "line1\r\nline2")`.
- The file stores `line1\r\nline2` as given. `show --json` then returns `views.<name>.body == "line1\nline2"`, and the template receives the same text. ADR-1274 §4 says the round trip is exact for every input, and a projection reads text that differs from what was written.
- Calling `set_view_body` again with the same text is never a no-op. `with_view_inner` splices the raw `\r\n` inner into the LF-normalised `placed` region, while the comparison normalises only `current`. So the two never compare equal, and every call rewrites the file and appends a `view` reflog entry. In the probe the reflog went from 5 to 6 to 7 lines for identical calls, while LF-only text stayed at 8, 8, 8. Tracker descriptions commonly carry CRLF, so every pull would rewrite every such item.

**Fix:** pick one line-ending rule and apply it on both sides. The simplest is to normalise CRLF to LF in `set_view_body` before `encode_inner`, so the file's own EOL governs as everywhere else, and to compare the result like for like. Have the architect state the rule in ADR-1274 §4 ("exact up to line endings"). Add a CRLF case to the pull task's escape round-trip test.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-11-03T23:54:45Z] `reviewer` Paul Reviewer:
  - Reopened. CRLF is fixed: three identical set_view_body calls on line1 CRLF line2 left the reflog at 4, 4, 4, and no CR reached the file. But ADR-1274 section 14 says every lone CR becomes LF on write, and src/squads/_services/_views.py:156 only replaces CRLF.
  - Reproduced: setting a CR b leaves a lone CR on disk. Repeating the same call rewrites the file and logs again (reflog 4 to 5). A following call with a LF b is then skipped as unchanged, so the stray CR stays.
  - Fix: normalise both, for example text.replace("\r\n", "\n").replace("\r", "\n") before encode_inner. Add the lone-CR case to the pull task round-trip test.
- [2026-11-03T23:59:05Z] `reviewer` Paul Reviewer:
  - Verified on c663edcf. set_view_body now normalises lone CR as well. Calling it with a CR b, a CR b, then a LF b left the reflog at 4, 4, 4 with no CR on disk.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — views.<name> entry shape and transform body keyword are not recorded in any ADR

<!-- sq:finding:F2:body -->
**Where:** `src/squads/_views.py` `view_data` (the `{"body": body, "data": out}` entry) and `src/squads/_transform.py` (`body` keyword); flagged by the developer as decision 1 and 2.

**What:** ADR-1109's `show --json` section binds `views` as "view name to transform output", and says a placed view with no transform is left out. ADR-1274 §4 adds only that the unescaped body sits "inside that view's entry under `views`". The delivered shape changes ADR-1109's contract for stored views in three ways, and no ADR records any of them:
- a stored view's entry is `{"body", "data"}`, so a transform's output moves under `data`;
- a transform-less stored view now gets an entry;
- transforms take a `body` keyword.

ADR-1109 has no narrowing note, and ADR-1274's Consequences do not list it. `docs/stability.md:1120` ("Each value is the JSON the transform returned") and `docs/workflow.md:465` would become false. Grammar and format decisions in this repo must land in an ADR.

**Judgement on the shape:** keep it. It leaves every non-stored view byte for byte as it is, so the bundled goldens hold. It gives a transform-less stored view (`source_description` has no transform) a place for its body, and the key the body sits under is fixed rather than one that a transform's own output could collide with.

**Fix:** @architect records the entry shape and the `body` keyword in ADR-1274 §4 (or §14) and adds a dated narrowing note to ADR-1109's `show --json` and call-signature text. @tech-writer then refreshes `docs/stability.md` and `docs/workflow.md`. No code change.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-11-03T23:47:56Z] `architect` Robert Architect:
  - Recorded in ADR-1274 section 14 (2026-11-04, the stored-view views entry and the transform body keyword, shape kept), with dated notes on ADR-1109 Call and show --json; @tech-writer docs/stability.md:1120 and docs/workflow.md:465 need the stored-view entry shape and the body keyword.
- [2026-11-03T23:54:46Z] `reviewer` Paul Reviewer:
  - Verified: ADR-1274 section 14 records the stored entry shape {body, data}, the entry without a transform, and the body keyword. ADR-1109 carries dated in-place notes on the call signature and the show --json section. The docs/stability.md and docs/workflow.md refresh is the writer step.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Duplicate stored pairs: the check remedy drops the second body, round trip is refused

<!-- sq:finding:F3:body -->
**Where:** `src/squads/_view_bodies.py:90` (`collapse_pairs` keeps the first pair per view via `setdefault`) against `src/squads/_view_tags.py:130` (`altered_view_pairs` keeps the last, via a dict comprehension). `place_view_tags` re-inserts one tag per view.

**Scenario (reproduced):** a hand edit or a merge leaves two pairs of one stored view in `sq:body`, holding FIRST and SECOND.
- `sq check` reports the duplicate and names `sq task 2 view add imported_description` as the remedy. Running it keeps FIRST and deletes SECOND and its end tag without a word. Any `body -m` does the same. US2 says a body write cannot lose a stored view body.
- `show --json` then `body --file <that body> --force` is refused with "differs from the one stored". The incoming FIRST pair is compared with the stored SECOND, so the documented round trip fails on this file.

**Fix:** refuse a write while a view has two pairs whose bodies differ, naming both, rather than collapsing them. At least make `altered_view_pairs` and `collapse_pairs` agree on which pair is the stored one. The duplicate message could also say that the collapse keeps the first pair's body. Low, because the body is a cache that a refresh restores.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-11-03T23:54:47Z] `reviewer` Paul Reviewer:
  - Verified on the original reproduction. With FIRST and SECOND pairs, view add now refuses with "two stored bodies that differ" and SECOND survives. Two identical pairs still collapse, with no loss. altered_view_pairs keeps the first pair, like collapse_pairs.
  - Note: in that conflict state, body --file with the show --json body is refused by the altered-pair check first, with the "differs from the one stored" message rather than the duplicate one. Nothing is written, so it is not reopened.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — A stored-view tag without its end tag is a check error no verb can clear

<!-- sq:finding:F4:body -->
**Where:** `src/squads/_view_tags.py:296` (`_pair_inners`: "A tag a stored view already has without an end tag stays unpaired") and `src/squads/_services/_check.py:159` (the finding's message).

**Scenario (reproduced):** remove a stored view's end tag. `sq check` reports `error ... stored view 'imported_description' has a tag ... with no end tag ...` (exit 3). Then:
- `view add` answers "already present, unchanged";
- `view disable` followed by `view add` rewrites the opening tag;
- `sq check` still reports the same error.

No verb clears it, and the message names no remedy, so this repo's must-pass gate can be left red with a hand edit as the only way out.

**Fix:** let `view add` on a stored view whose tag has no end tag complete it into an empty pair directly after the tag. This consumes no text, and the developer's decision 4 still holds for plain body writes. Name that command in the check message. If the design prefers to leave it, the message must at least say what to do.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-11-03T23:54:48Z] `reviewer` Paul Reviewer:
  - Verified. The check message now names the view add command, view add completes the open-only tag into an empty pair, and sq check is then clean. Reproduced on the scratch squad; test_view_add_completes_the_open_only_tag_of_a_stored_view passes.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — New CLI tests read item files and assert substrings, against ADR-1172 section 5

<!-- sq:finding:F5:body -->
**Where:** `tests/cli/test_item_verbs.py:1317, 1332-1339, 1352, 1376/1389` and `tests/cli/test_show.py:59, 299-301, 310/315/317`.

**What:** ADR-1172 §5 has a case read state through the CLI and assert whole output. A test may open an item file only to arrange a state that no CLI path produces. These cases do more than that:
- `_task_with_stored_body` and `_readable_task_with_stored_body` read the file back and assert a count;
- the add/disable case asserts substrings (`in` and `not in`) on file text;
- the omitted-pair case repeats its whole `show --json` assertion as a redundant `stored.pair() in path.read_text()`;
- the refusal case and the JSON case compare `read_bytes()`;
- the `--raw` case asserts `stored.RENDERED in text`, `OPEN_TAG not in text` and `"<!!--" not in text`, all substrings that would survive wrong surrounding output;
- the JSON case uses `shown["body"].endswith(...)`.

**Fix:** writing the pair into the file stays, since no verb writes a stored body yet. Read everything back through `show --json` and compare the whole `body` (it carries the stored pair byte for byte), and compare the `--raw` output as whole lines. The refusal case can assert the body is unchanged through `show --json`. Whether a read wrote is already held by the daemon GET test's snapshot, so the JSON case does not need its own byte comparison.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-11-03T23:54:49Z] `reviewer` Paul Reviewer:
  - Reopened, narrowly. The cited instances are fixed: state is read through show --json with whole-value equality, and the --raw case compares whole lines. Two leftovers sit in tests added by the fix.
  - tests/cli/test_item_verbs.py, test_view_add_completes_the_open_only_tag_of_a_stored_view: assert out[0] == 0 checks only the exit code. ADR-1172 section 5 wants the whole output, which is the "view ... placed in sq:body" line.
  - tests/cli/test_repair.py, test_repair_leaves_the_pair_of_a_stored_view_named_head_alone: the comment "once matched the retired badge-region sweep" is history. State the present reason, for example that the retired-region sweep matches tags ending in :head by shape.
- [2026-11-03T23:59:05Z] `reviewer` Paul Reviewer:
  - Verified on c663edcf. The view add case asserts the whole output, and the repair-test comment states the present reason. The duplicate-pair case now also asserts the duplicate message for body --file. Targeted run: 18 passed.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — The clean 0.19 fixture carries a pair for an undeclared view

<!-- sq:finding:F6:body -->
**Where:** `tests/fixtures/corpus/v0_19/features/FEAT-000002-user-login.md:20-22` and `tests/cli/test_migrate.py` (`test_up_stamps_a_clean_0_19_squad_...`).

**What:** the "clean 0.19" fixture holds a `sq:view:head` pair. A 0.19 squad cannot hold a pair (ADR-1274 §13: a 0.19 build reads a pair as an unbalanced tag), and the fixture declares no `head` view. Traced, not run: on the migrated squad, `_view_pair_issues` (`src/squads/_services/_check.py`) reports a `markers_balanced` error for it, "view 'head' has a tag pair ..., but is not declared stored", because `head` is not in `spec.views`. The pair is there to prove the retired-region sweep leaves it alone, and that part works: I falsified it by restoring the old `_retired_region_tags`, and the test goes red. But the fixture is not the clean corpus its test name claims. It is also the corpus that later tasks extend for their pre-flight cases, and any of them that runs `sq check` on it would start from an error.

**Fix:** declare `head` as a stored view in the fixture's `.overrides/workflow.toml` (with a template), so the corpus is check-clean once migrated, and say in a fixture comment why the view is named `head`. Alternatively, keep the pair in a second fixture used only by the sweep case.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-11-03T23:54:50Z] `reviewer` Paul Reviewer:
  - Verified. The pair is gone from the v0_19 fixture, and the sweep property moved to test_repair_leaves_the_pair_of_a_stored_view_named_head_alone on a declared stored view. Falsified: with the old _retired_region_tags monkeypatched in, that test fails, and it passes on the fix.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — CLAUDE.md architecture map does not name _view_bodies.py

<!-- sq:finding:F7:body -->
**Where:** `CLAUDE.md`, the architecture section's `_views.py` paragraph, which lists `_view_tags.py` and `_view_remedies.py`.

**What:** the new top-level module `src/squads/_view_bodies.py` holds the escape grammar, pair recognition and `ViewPair`. Nothing in the architecture map names it, so the next reader looking for where a stored body is parsed has no pointer to it. Also, `_check.py`, `_views.py`, `_view_tags.py` and `_services/_views.py` each call `find_view_pairs` on their own, so the map is the only place where the boundary between the three view modules is written down.

**Fix:** add one sentence next to `_view_tags.py`, for example: "`_view_bodies.py` holds the stored-view pair: its escape grammar and recognition." Cleanup only.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-11-03T23:54:51Z] `reviewer` Paul Reviewer:
  - Verified: CLAUDE.md names _view_bodies.py beside _view_tags.py.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-03T23:45:26Z] `reviewer` Paul Reviewer:
  - Recommended verdict: ChangesRequested (two medium, four low, one info; no high). Not self-approving.
  - @python-dev F1, F3, F4, F5, F6 and F7 are code, test or CLAUDE.md fixes on TASK-1275.
  - @architect F2: record the stored-view entry shape under views and the transform body keyword in ADR-1274, with an in-place note on ADR-1109; then @tech-writer refreshes docs/stability.md and docs/workflow.md. F1 also needs the line-ending rule stated in ADR-1274 section 4.
  - For the source-record task: when source becomes a typed core key, a 0.19 file with a scalar source value may fail the pre-runner reconcile as unindexable, so the refusal would come before this runner and hide its remedy. The body_written rule also strips pairs, so an item holding only a stored body reads as unwritten. Not reproducible yet, so not filed as findings.
- [2026-11-03T23:50:41Z] `python-dev` Elias Python:
  - Fixes for REV-1280 from @python-dev, uncommitted.
    - F1: set_view_body stores LF, so the body reads back equal up to line endings and a repeat call is a no-op (reflog unchanged on the second call).
    - F3: placement refuses a view holding two pairs with different text (names the view); altered_view_pairs and collapse_pairs both use the first pair.
    - F4: view add completes an open-only stored tag into an empty pair; the check message names that command.
    - F5: new cases read state through show --json and compare whole outputs.
    - F6: the 0.19 fixture no longer holds a pair; the sweep proof is a repair case with a stored view named head.
    - F7: CLAUDE.md names _view_bodies.py (hand-written part only).
    Adopter-visible: the two refusal/remedy messages above, and a duplicate-pair write is now refused instead of dropping the second body.
- [2026-11-03T23:54:58Z] `reviewer` Paul Reviewer:
  - Re-verification of the fix commit 9399c1ed: F2, F3, F4, F6 and F7 are Verified. F1 is reopened because the lone-CR half of the line-ending rule recorded in ADR-1274 section 14 is not implemented (reproduced), and F5 for two small leftovers in tests the fix added. Status ChangesRequested.
  - @python-dev F1: also normalise lone CR in set_view_body. F5: assert the whole view add output, and reword the repair-test comment.
<!-- sq:discussion:end -->
