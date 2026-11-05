---
id: REV-1316
sequence_id: 1316
type: review
title: Board notice and memory summaries
status: Approved
author: reviewer
refs:
- TASK-1313
- TASK-1314
- ADR-1312
description: 'Review of FEAT-1311: board and memory summaries over a body, Python
  and VS Code client'
subentities:
- local_id: F1
  title: Raw board and memory lists print a partial list before exit 4
  status: Verified
  severity: medium
- local_id: F2
  title: memory list --raw breaks the bullet on a multi-line summary
  status: Verified
  severity: medium
- local_id: F3
  title: Migration tests parse files with a src helper and assert substrings
  status: Verified
  severity: medium
- local_id: F4
  title: Migration rewrites non-mapping and frontmatter-less notice files
  status: Verified
  severity: low
- local_id: F5
  title: 'sq ui board screen: no test, bold breaks on multi-paragraph summaries'
  status: Verified
  severity: low
- local_id: F6
  title: The splitlines line-break boundary is not pinned by any test
  status: Verified
  severity: low
- local_id: F7
  title: Three board and skill tests assert slices or substrings
  status: Verified
  severity: low
- local_id: F8
  title: board post strips leading indentation from the body
  status: Verified
  severity: low
- local_id: F9
  title: Raw list continuation falls out of items numbered 10 and above
  status: Verified
  severity: medium
- local_id: F10
  title: ADR-1312 §3 post/clear entry keys omit author_name
  status: Verified
  severity: low
- local_id: F11
  title: memory list --full test folds the --raw interaction into one case
  status: Verified
  severity: low
created_at: '2026-11-05T08:13:42Z'
updated_at: '2026-11-05T09:29:38Z'
target_ref: FEAT-1311
---
<!-- sq:body -->
Review of FEAT-1311's implementation against ADR-1312 (with op-pierre's copy-not-move ruling): TASK-1313 (620f37da, 27a73848, f9cc8727) and TASK-1314 (79ad3f6d), read from a detached worktree at a978906f.

## Scope checked

- Stored form, id hash, post/list/show/clear numbering, `--json` shapes, `BOARD_SHOW` (GET `/v1/board/{n}`) and its binding, write-time warnings, both always-on check rules, the 0.19 to 0.20 board step.
- The `sq ui` board screen, by reading the code and driving it with Textual's pilot from a scratch script.
- The VS Code client: guards, the id comparison on click, escaping, the canary key sets.
- Tests against ADR-1172, on the bundled and the override squad, with mutations run in a scratch copy.
- Layering, the import rules, comments and docstrings.

## Gates (run)

- pyright 0 errors; ruff check and ruff format clean.
- `tests/meta tests/cli tests/check tests/daemon tests/regressions -n 4`: 2294 passed, 4 skipped.
- `--squad override tests/cli tests/check -n 4`: 1253 passed, 171 skipped.
- Client: `npm run check` clean; `npm test` 785 passed; `npm run test:canary` 103 passed, none skipped, against the worktree's sq 0.20.0.

## Mutations (scratch copy)

- Expiry filter removed from the notice rule: red (`test_an_expired_notice_with_a_multi_line_summary_raises_nothing`).
- Migration key order swapped: red (`test_up_copies_each_notice_body_into_its_summary_and_keeps_the_body`).
- Line-break predicate narrowed to a bare newline: survives (finding).

## Correct as specified (verified)

The id hash covers author, posted_at, summary and body. `show` and `clear` resolve through the same `BoardStore.show`. An out-of-range `show` or `clear` exits 1 with empty stdout. `list --json` rows carry no body, and the `show --json` object carries `body` as an empty string when the notice has none. The post and clear entries gain `summary`. The rules are always on at warn. An archived role's memory remedy works. The migration skips a file that already has a `summary`, keeps the body and the filename, and names a YAML-broken file. The client escapes the summary, id and meta, keys opened notices by id, re-lists on an id mismatch, and its canary asserts exact key sets on live output and fixtures.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1316 add-finding "…" --severity medium`; track with `sq review 1316 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Raw board and memory lists print a partial list before exit 4

<!-- sq:finding:F1:body -->
ADR-1294 §1, restated by ADR-1312 §4: a raw list prints nothing on stdout unless the whole list was read. Both raw lists the role skill renders break this when a file cannot be read.

- `sq board list --raw` with one unreadable notice prints the notices it could read and exits 4. Driven on a migrated 0.19 copy: stdout carried 7 items plus the closing line, and stderr the parse error.
- `sq memory <role> list --raw` with one unreadable memory does the same: the readable bullets, then exit 4.

Both commands share one path: `render_notices`/`render_memories(..., raw=True)` run before `calls.finish`, and `finish` sets exit 4 only after stdout has been written. The role-skill pointer's `|| echo "squads could not read …"` fallback (`_pointer_lines.skill_lines`) relies on an empty stdout, so a session receives a partial list followed by the "could not read" line.

This behaviour existed before FEAT-1311 (the base `list` command has the same order). The coordinator's ruling: ADR-1294 stands. Fix: with `--raw`, print nothing on stdout when the response has omissions, and keep exit 4 and the stderr lines. Add one CLI case per command and update the docs line that describes the exit-4 behaviour.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — memory list --raw breaks the bullet on a multi-line summary

<!-- sq:finding:F2:body -->
`render_memories(raw=True)` prints each memory as ``- `<slug>`: <description>``, with no handling of a multi-line description. Driven: a memory added with summary `A\nB` lists as

```
- `x`: A
B
```

The `B` line is not indented, so it falls out of the bullet and the markdown of the role skill's memory index breaks. ADR-1312 makes a multi-line summary an accepted, warned state for both tiers, and it gives the board's raw list a continuation rule (further lines indented under the item, `_raw_notice`). The memory raw list has no such rule.

Fix: indent each further line of the description by two spaces under its bullet, the same shape `_raw_notice` uses for the board. Add one `memory list --raw` case. ADR-1312 §4 covers only the board, so an amendment or a note from the architect may be needed.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Migration tests parse files with a src helper and assert substrings

<!-- sq:finding:F3:body -->
ADR-1172 §5: a migration test reads the files `sq migrate up` rewrote "as plain text and compares whole files or the whole frontmatter, never through an internal function such as a frontmatter parser", and asserts "whole message lines, never a substring".

The three new cases in `tests/cli/test_migrate.py` break this:

- `_notice()` reads each board file through `squads._sections.split_frontmatter`, a `src` import, and the key order is asserted on the dict that parser returns.
- `"summarised notice 2222222222" in result.output` and `"left notice board/5555555555.md as it was: malformed frontmatter" in result.output` are substring checks on the run's report.
- `'schema_version = "0.20"' in …splitlines()` is a membership check.
- `[… for i in checked if "notice" in i["rule"]]` filters the check output by a substring of the rule name.

Fix: compare each rewritten notice file as whole text, which also pins the key order and the YAML form of a multi-line summary. Assert the run's report lines as whole lines, and the check output as a whole list or by exact rule name.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Migration rewrites non-mapping and frontmatter-less notice files

<!-- sq:finding:F4:body -->
`_summarise_notices` treats two kinds of file as readable notices and rewrites them, against ADR-1312 §6 ("a file that does not read or parse is left untouched"):

- **Non-mapping frontmatter** (for example `---\n- a list\n---`): `split_frontmatter` returns `{}` for a non-dict block, so the step writes `summary: <body>` in place of the original block. The original frontmatter is lost. Driven on a 0.19 copy.
- **No frontmatter at all**: the step wraps the whole text in a new `summary:` frontmatter, with no author or posted_at.

A notice whose body is empty also migrates to `summary: ''`. `board list --raw` then prints `7.  — manager`, and nothing warns, although `board post` refuses a blank summary.

All three cases are contrived (no CLI path writes them), so the severity is low. Fix: treat a file with no frontmatter or a non-mapping one as unreadable and name it in the report. Then decide (architect) whether an empty body gets a placeholder summary or a report line.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — sq ui board screen: no test, bold breaks on multi-paragraph summaries

<!-- sq:finding:F5:body -->
**Coverage.** No test drives the board screen. A test is feasible with what the repository already has. I drove it in-process with `SquadsApp(...).run_test()`, pressed `b` and read the `Markdown` widget's `source` and the `Static` lines, from a scratch script with no new dependency. The existing `covers("ui")` cases in `tests/cli/test_docs_ui.py` capture the app by monkeypatching `run`. One case can reuse that capture, run the app under the pilot and assert the whole board markdown. ADR-1172 §5 asks for what the user sees, so whether a widget's source counts is for the architect to say. If it does not, record the gap.

**Code (read and driven):**

- `_notice_block` wraps the summary in `**…**` as markdown. A migrated summary often holds a blank line, and then bold cannot span it: the screen shows literal `**Read the diff…` / `…tests it adds.**`. An empty summary shows `****`. The summary text is also not escaped as markdown. Render the summary as its own paragraph(s), or escape it and bold each line.
- `on_mount` counts an id mismatch or a failed `BOARD_SHOW` into `skipped`, but `_skipped_note` says "N notice file(s) could not be read". For a board that changed between the calls, that text is wrong.
- One `BOARD_SHOW` per row: each call reads the whole board again, so the cost is N+1 calls and N² file reads, and in remote mode N round trips. Acceptable at today's 22 notices; noted only.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — The splitlines line-break boundary is not pinned by any test

<!-- sq:finding:F6:body -->
ADR-1312 §1: "a line break is any separator `str.splitlines` splits on, as `title_single_line` reads a title". `has_line_break` implements this, but no test pins it.

- Mutation: `has_line_break` narrowed to `"\n" in text.strip()`. Every board, memory, check and migrate test still passed (scratch copy).
- The predicate is also a second copy: `_title_single_line` uses `title.splitlines() != [title]`, which differs on a trailing newline. Reuse one predicate, or say why the two differ.

Fix: one case where a summary split only by a non-`\n` separator (`\r` or `U+2028`) still warns. A single `board post` case is enough, since both rules share `has_line_break`.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Three board and skill tests assert slices or substrings

<!-- sq:finding:F7:body -->
Smaller test-shape points under ADR-1172 §5:

- `test_list_raw_numbers_match_the_ones_clear_takes` changed from a whole-output assertion to `result.output.splitlines()[:2]`. Restore the whole output; it is two lines and the closing line.
- `test_list_raw_indents_the_further_lines_of_a_multi_line_summary` asserts the output but not the exit code.
- `test_show_the_sq_memory_skill_teaches_the_board_by_summary_and_body` (`tests/cli/test_skill.py`) checks three substrings of the rendered skill. One of them depends on exact column padding (`sq board show <n>` followed by 42 spaces). Compare the whole board section of the skill instead.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — board post strips leading indentation from the body

<!-- sq:finding:F8:body -->
ADR-1312 §1: "The body is optional and stored as written." `BoardStore.post` stores `(body or "").strip()`. Driven: `-m '   indented body'` is stored as `indented body`. A body that opens with an indented code block loses its indentation. The previous text field was stripped too.

Fix: strip only the surrounding blank lines (`strip("\n")`, as the read path does), or have the architect narrow §1 to "stripped". Low.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Raw list continuation falls out of items numbered 10 and above

<!-- sq:finding:F9:body -->
ADR-1312 §4: with `--full`, each notice's body "follows its item, indented to stay inside it". `_raw_notice` indents the body, and the further lines of a multi-line summary, by a fixed three spaces. That fits `1.` to `9.` but not `10.` and above, where CommonMark requires four spaces.

Driven on a scratch squad with 11 notices, `board list --full --raw` printed:

```
10. Notice 10 — manager

   Body 10
11. Notice 11 — manager
```

Parsed with markdown-it (CommonMark), the list closes after item 10's summary. `Body 10` and item 11 then become one loose paragraph. The same break hits a multi-line summary at position 10 or later in plain `--raw`, the form the role skill renders. I missed this in the first round.

Fix: indent continuation and body lines by the width of the item's own marker (`len(f"{n}. ")`). Add one `--full --raw` case with ten or more notices, asserting the whole output.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — ADR-1312 §3 post/clear entry keys omit author_name

<!-- sq:finding:F10:body -->
ADR-1312 §3 says `board post` and `board clear` answer with "one object whose `entry` holds `id`, `summary`, `author`, `posted_at`, `until` and `body`". The code adds `author_name` to `Notice`, so both entries carry it as well (asserted in `test_post_json_prints_the_notice_written` and `test_clear_json_prints_the_notice_taken_down`). Code and ADR disagree. The likely fix is one word in §3 (architect).
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-11-05T09:19:34Z] `architect` Robert Architect:
  - Fixed: ADR-1312 §3 now lists `author_name` among the `board post`/`board clear` entry keys, matching `Notice`.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — memory list --full test folds the --raw interaction into one case

<!-- sq:finding:F11:body -->
`tests/cli/test_memory.py::test_list_full_prints_each_body_under_its_summary` runs both `--full` and `--full --raw` in one case, but declares only `covers("memory list", "--full")`. The two flags interact: `--raw` decides how `--full` lays out the body. ADR-1172 §1 asks for a test named for that interaction and carrying the pair in its marker. The board has it right: separate cases for `--full`, `--full --json` and `--full --raw`. Fix: split the raw half into its own case, `covers("memory list", "--full", "--raw")`.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T08:14:59Z] `reviewer` Paul Reviewer:
  - Verdict: ChangesRequested. The core of ADR-1312 is implemented correctly: the stored form, the id hash, shared show/clear numbering, the JSON shapes, `BOARD_SHOW` and its route, both always-on rules and the copy-not-move migration step. All gates are green on both squads, and the client is clean, with no findings.
    
    - Medium: F1 (raw lists print a partial list before exit 4, against ADR-1294 §1; this predates FEAT-1311, and the coordinator's ruling is that the ADR stands; the fix needs a docs line), F2 (`memory list --raw` breaks its bullet on a multi-line summary), F3 (the migration tests parse files with `split_frontmatter` and assert substrings, against ADR-1172 §5).
    - Low: F4 (the migration rewrites notice files with non-mapping or missing frontmatter; an empty body becomes an empty summary), F5 (`sq ui` board screen: a pilot test is feasible with the existing harness; bold breaks on multi-paragraph summaries; the skipped note's wording), F6 (no test pins the splitlines boundary; a mutation survived), F7 (slice and substring assertions in three tests), F8 (`post` strips the body's leading indentation).
    - F1, F2 and F4 need an architect call on ADR wording (the memory raw continuation rule, the empty-summary handling). @architect
    - The fix queue is for the python-dev on TASK-1313. Nothing in TASK-1314 needs a change. @tech-lead
    
    The review is ready for re-review once the fixes land. I do not approve my own review.
- [2026-11-05T08:15:42Z] `manager` Catherine Manager:
  - - Calls on REV-1316, so no ADR wording round is needed:
      - F1: `--raw` lists stay all-or-nothing per ADR-1294 §1 — nothing on stdout when a file cannot be read; the docs line follows.
      - F2: `memory list --raw` indents a multi-line summary's further lines the way the board list does.
      - F4: the migration leaves a notice file alone, and names it in its report, when its frontmatter is not a mapping, when it has no frontmatter, or when its body is empty (an empty summary would be refused by post).
      - F5: add an in-process `sq ui` board test with Textual's `run_test()`, and fix the rendering of blank lines and empty summaries and the skipped-note wording.
      - F6: one shared line-break helper for titles and summaries, with a test that pins CR and U+2028 for summaries.
      - F8: `board post` stores the body as written.
- [2026-11-05T08:30:53Z] `reviewer` Paul Reviewer:
  - Re-review at 77fdfdd9 (fresh worktree): F1 to F8 are all Verified. Recommended verdict: Approved. @manager, setting Approved is yours.
    
    - Gates: pyright, ruff check and ruff format are clean. Bundled run: 2301 passed, 4 skipped. Override run: 1260 passed, 171 skipped.
    - Mutations, run in a scratch copy, each turned its own test red:
      - the raw-list omission guard removed (F1);
      - the memory continuation indent removed (F2);
      - the mapping check dropped from the migration (F4);
      - the old bold rendering restored in `sq ui` (F5);
      - `has_line_break` narrowed to a bare newline (F6).
    - F5: the new `run_test()` case runs under the bundled squad (it is not skipped). It asserts the whole board markdown, newest first, with a blank-line summary bolded line by line and its markdown escaped.
    - F3 and F7: the tests compare whole files, report lines, config, check issue and skill section, with no src parser import.
    - Note, not a finding: under F4, a 0.19 notice with an empty body is left without a summary, so it lists with an empty summary. This follows the manager's call, and post cannot create such a notice.
- [2026-11-05T08:31:16Z] `manager` Catherine Manager:
  - Approved as second party: F1-F8 Verified, full suite green at 77fdfdd9 (2330 passed).
- [2026-11-05T09:18:10Z] `reviewer` Paul Reviewer:
  - Pass on the round after approval (257022c4, 1bffcf25; ADR-1312 as edited through 7d37d58d), in a fresh worktree at a0935259.
    
    - Gates: pyright, ruff check and ruff format are clean. Bundled run: 2306 passed, 4 skipped. Override run: 1265 passed, 171 skipped. Client: npm check clean, npm test 780 passed, canary 105 passed against the worktree sq.
    - Mutations, run in a scratch copy, each turned its tests red: `author_name` replaced by the slug; the closing line kept under `--full`; the memory body emitted without `--full`.
    - `author_name` resolved on a scratch squad: an operator's name and an archived role's name both resolve, and the slug is used when no roster entry exists.
    - The client renders every body through `renderMarkdownToHtml`, escapes the credits, and has no leftover click path. Its guard requires `body` and accepts a missing `author_name` from an older sq.
    - New: F9 (medium): continuation and body lines are indented three spaces, so they fall out of list items 10 and above. F10 (low): ADR-1312 §3's post/clear entry key list omits `author_name`. F11 (low): one `memory list --full` case also covers `--raw` without naming that interaction.
    - The review is Approved but now has open findings. @manager, whether it goes back for a fix round is your call. F9 is for python-dev, F10 for @architect.
- [2026-11-05T09:18:23Z, edited 2026-11-05T09:18:42Z] `reviewer` Paul Reviewer:
  - The review lifecycle has no transition out of Approved without --force, so I left the status as it is. sq check now warns that REV-1316 is Approved with unsettled findings (F9 to F11). Reopening it (forced) or settling F9 to F11 clears the warning. @manager, your call.
- [2026-11-05T09:19:16Z] `manager` Catherine Manager:
  - Reopened for F9-F11 found on the --full round: F9 and F11 to python-dev, F10 to the architect.
- [2026-11-05T09:29:21Z] `reviewer` Paul Reviewer:
  - Re-review at 7351c9a9: F9, F10 and F11 are Verified, so all eleven findings are Verified. Gates: pyright and ruff clean; bundled 2309 passed, 4 skipped; override 1268 passed, 171 skipped.
  - F9: a twelve-notice board list --full --raw, including a two-line summary at item 12, parses under markdown-it (CommonMark) as one ordered list of 12 items with no top-level paragraph. Restoring the fixed three-space pad turns both two-digit-marker tests red. F10: ADR-1312 §3 now lists author_name in the post and clear entry. F11: the --full --raw memory case is split out and declares both flags.
  - Recommended verdict: Approved. @manager, setting it is yours.
- [2026-11-05T09:29:38Z] `manager` Catherine Manager:
  - Approved as second party: F1-F11 Verified, full suite green at 7351c9a9 (2338 passed).
<!-- sq:discussion:end -->
