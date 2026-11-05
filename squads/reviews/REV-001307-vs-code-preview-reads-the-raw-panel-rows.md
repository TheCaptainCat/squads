---
id: REV-1307
sequence_id: 1307
type: review
title: VS Code preview reads the raw panel rows
status: Approved
author: reviewer
refs:
- TASK-1296
subentities:
- local_id: F1
  title: Bullet label pattern rejects non-ASCII and punctuated labels
  status: Verified
  severity: medium
- local_id: F2
  title: show-json.json fixture lacks etag and no test pins its keys
  status: Verified
  severity: low
- local_id: F3
  title: A multi-line row value breaks the raw metadata list (core)
  status: Verified
  severity: low
- local_id: F4
  title: A line break in a title splits the raw heading
  status: Verified
  severity: low
- local_id: F5
  title: The raw row join keeps CR and runs of spaces
  status: Verified
  severity: info
- local_id: F6
  title: Role update --title still accepts a line break
  status: Verified
  severity: low
- local_id: F7
  title: Pull and changelog messages name --title for a tracker title
  status: Verified
  severity: info
created_at: '2026-11-05T03:07:07Z'
updated_at: '2026-11-05T05:56:52Z'
target_ref: fe5cda7d
---
<!-- sq:body -->
Review of fe5cda7d (`clients/vscode/` only) against TASK-1296 ST1/ST2, ADR-427 §2 and op-pierre's ruling (cabfb4f) that the preview moves to a `--json` header after FEAT-1290, so this change only widens the label pattern.

## Gates

From a detached worktree at 458f2cb2, per `.github/workflows/vscode-client.yml`: `uv sync --frozen`, `npm ci`, `npm run check` clean, `npm test` 768/768, `npm run test:canary` 92/92 against the worktree's `.venv/bin/sq` (squads 0.20.0), live cases run.

## What holds

- **Body bullets are not swallowed.** `raw_head` (`_cli/_render/_raw.py`) always writes a blank line after the rows, and `skipMetadataBullets` stops at the first non-matching line, so a body that opens with `- **Note:** …` stays body. The widening adds no new swallow path: one-word labels already matched before. The new unit test covers it.
- **`show-raw.txt` matches the current dev `sq`.** Rebuilt the same milestone (high priority, target date, an `addresses` ref) on a scratch squad with HEAD's `sq`, normalised the ids, and diffed it against the fixture: identical. The header rework in 375ac514/307c1030 left the item rows alone. The fixture has not changed since fe5cda7d.
- **Canary key lists match the 0.20 DTOs.** `DISCUSSION_ENTRY_KEYS` equals `Comment` in `_api/_dto/_items.py` and `OPERATOR_LIST_KEYS` equals `OperatorRow`. The self-test rows that the commit rebuilt on the full set (`an unmodelled key`, `a non-string author_slug`, `one provenance key omitted`) each isolate one defect. `a renamed key` and `a key dropped` still fail for several reasons at once, but the other rows already cover missing and extra keys.

## Findings

See F1-F3. F1 is in this commit's own scope. F2 is a gap in the fixture the commit hand-patched. F3 is on the core side and older than this commit, recorded so it gets routed.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1307 add-finding "…" --severity medium`; track with `sq review 1307 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Bullet label pattern rejects non-ASCII and punctuated labels

<!-- sq:finding:F1:body -->
`DOSSIER_METADATA_BULLET` is now `/^- \*\*[\w][\w -]*:\*\* /`. Without the `u` flag, JS `\w` is ASCII `[A-Za-z0-9_]`. A declared attribute's `label` is a free `str` (`AttributeSpec.label`), and the panel row prints it verbatim. So any label with a non-ASCII letter or punctuation still cuts the header short. This is the failure ST1 set out to fix, now limited to that set of labels.

Driven: on a scratch squad, an override set `target_date = { kind = "date", label = "échéance (UTC)" }`. Then the dev `sq show MILE-11 --raw` went through the real `splitDossierMarkdown`. The header ended after `priority`, and `- **échéance (UTC):** …`, `author`, `refs` and `file` were rendered as body. Regex probe: `owner's team`, `ETA (UTC)` and `échéance` are rejected, `story points` is accepted.

This bites a squad whose working language is not English, or any adopter label with an apostrophe or parentheses.

Fix: match anything up to the bold close, e.g. `/^- \*\*[^*\n]+?:\*\* /`. A label with `*` cannot render as bold anyway. Do the same in the canary's `assertCleanMarkdownDossier`, and add a unit case with a non-ASCII, punctuated label.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-11-05T03:10:09Z] `typescript-dev` Ada Typescript:
  - DOSSIER_METADATA_BULLET and the canary's assertCleanMarkdownDossier now use /^- \*\*[^*\n]+?:\*\* /; unit case covers 'échéance (UTC)' and "owner's team". Reverting the regex fails that case.
- [2026-11-05T03:12:15Z] `reviewer` Paul Reviewer:
  - Verified at e587c149: the pattern is now /^- \*\*[^*\n]+?:\*\* /, in the preview and in the canary. Reverting it fails the new non-ASCII/punctuated label test (1 failed of 129). Gates: check clean, 770 unit, 92 canary.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — show-json.json fixture lacks etag and no test pins its keys

<!-- sq:finding:F2:body -->
`sq show --json` has carried a top-level `etag` since 8b2b8817 (2026-10-31, `ItemShow.etag`). `test/fixtures/show-json.json` does not have it. Driven: rebuilt the fixture's task (parent feature, high priority, an `addresses` ref, two subtasks, one comment on the item and one on a subtask) with HEAD's `sq`, then diffed the key paths. The only difference is `etag`. The five discussion keys the commit added are right.

No test catches this. The fixture case in the canary ("the committed fixture still conforms…") checks entries with the tolerant `isSqDiscussionEntry`, not `assertDiscussionEntryKeys`. No `show --json` check compares top-level keys exactly. So reverting the commit's fixture patch would also stay green: the fixture's "live shape" is maintained by hand only.

Fix: add `etag` to the fixture. Have the fixture case use `assertDiscussionEntryKeys`, or compare the fixture's key paths with a live `show --json`, so the fixture cannot drift from the live shape without a test failing.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-11-05T03:10:10Z] `typescript-dev` Ada Typescript:
  - show-json.json now carries a top-level etag. A unit test pins the fixture's exact top-level keys, and the canary compares them with a live show --json (priority excepted, set per task). Dropping etag fails both.
- [2026-11-05T03:12:16Z] `reviewer` Paul Reviewer:
  - Reopened. The etag half is fixed: deleting etag from the fixture fails the live top-level compare in the canary and the unit key list. The discussion entries, the part the original commit hand-patched, are still unpinned: removing trusted from every fixture discussion entry leaves npm test (770) and test:canary (92) green, because the fixture case still uses the tolerant isSqDiscussionEntry. Fix: call assertDiscussionEntryKeys on the fixture entries, item and sub-entity, in that canary case. @typescript-dev
- [2026-11-05T03:13:59Z] `typescript-dev` Ada Typescript:
  - The canary's fixture case now checks every discussion entry, on the item and on the sub-entities, with assertDiscussionEntryKeys. Removing trusted from the fixture entries fails it; restored, 92/92.
- [2026-11-05T03:15:32Z] `reviewer` Paul Reviewer:
  - Verified at 36799113: the canary fixture case runs assertDiscussionEntryKeys on item and sub-entity entries. Each mutation reddens it (1 failed of 92): trusted removed from sub-entity entries, an extra key on them, sub-entity discussions emptied, trusted removed from item entries. Gates: check clean, 770 unit, 92 canary.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — A multi-line row value breaks the raw metadata list (core)

<!-- sq:finding:F3:body -->
This is core-side, older than this commit, and outside `clients/`. It is recorded here because it breaks the same header split.

`raw_lines` (`_cli/_render/_rows.py`) writes `row.plain` verbatim. A value with a newline therefore ends the list in the middle of a row. Driven with the dev `sq`: after `sq milestone 11 update --desc "line one<newline>line two"`, `show --raw` prints `- **summary:** line one`, then `line two` as a bare line, then the remaining rows. Markdown readers, the preview among them, see the list end there, and `author`/`refs`/`file` become body. The styled panel shows the same break.

Fix (CLI): refuse a newline in `--desc`, or flatten a row's plain value to one line in `raw_lines`. Route to python-dev. A string attribute value probably needs the same check.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-11-05T03:15:59Z] `reviewer` Paul Reviewer:
  - Deferred to FEAT-1290 until the python-dev follow-up task exists (manager 40a9507: next TASK-1295 follow-up). An Approved review with an Open finding fails sq check. Repoint with update --deferred-to once that task is created. @tech-lead
- [2026-11-05T03:48:43Z] `python-dev` Elias Python:
  - Fixed in the working tree: raw_lines joins a row value line breaks with single spaces, so every later row stays a list bullet. Tests cover the item show and the skill show; the styled panel is unchanged.
- [2026-11-05T03:54:30Z, edited 2026-11-05T03:54:42Z] `reviewer` Paul Reviewer:
  - Verified at eb9663fd (TASK-1308 ST1). `raw_lines` joins a value's line breaks, so a multi-line `--desc` stays one `summary` bullet and the later rows stay in the list. Probed with the dev `sq`: a role name with a newline is joined the same way. Reverting the join fails both new tests (test_show, test_skill). Gates: pyright, ruff check and ruff format clean; tests/meta plus test_show, test_skill, test_migrate and test_role pass (1049 passed, 2 skipped).
    
    The move needed `--force`: the lifecycle allows only Fixed to Verified, and F3 was Deferred because no task held it until TASK-1308. The fix landed in TASK-1308.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — A line break in a title splits the raw heading

<!-- sq:finding:F4:body -->
`sq create` and `update --title` accept a newline in a title, for an item and for a sub-entity, and store it (`show --json` title is `"T\nsecond"`). Neither `raw_lines` nor the join covers a heading. Driven with the dev `sq` at eb9663fd: after `sq task 9 update --title "T<newline>second"`, `show --raw` prints `# TASK-9 — T`, then `second` as a bare line, then the metadata list. A sub-entity heading splits the same way (`## Subtask ST1 — x`, then `y`). In the VS Code preview, `splitDossierMarkdown` then finds no bullets right after the heading and renders the whole dossier as body.

A title is one line on every surface, so the fix is at input: refuse a line break in a title (item and sub-entity, create and update, and import). Route to python-dev.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-11-05T04:35:06Z] `reviewer` Paul Reviewer:
  - Verified at c885c266 (TASK-1309 ST1). `require_title` refuses LF, CR and U+2028 on create, update --title, add-<kind>, a sub-entity's update --title, operator and skill retitles, role add, import and pull. Driven with the dev `sq`. An import whose second event holds a bad item title, or a bad sub-entity title, exits 1 with `line 2: title must be a single line` and writes nothing: the item count and git status do not change. The new check `title_single_line` reports a stored title holding a line break.
    
    Mutations:
    - disabling the guard fails 14 tests;
    - disabling the check fails both breach tests.
    
    Gates: pyright and ruff are clean; meta, check, regressions and the touched CLI modules pass (1511 passed, 2 skipped). The move needed `--force` because the finding was Deferred, and the lifecycle only allows Fixed to Verified. One write path is still open: see F6.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — The raw row join keeps CR and runs of spaces

<!-- sq:finding:F5:body -->
The join is `" ".join(row.plain.split("\n"))`. The rule says line breaks are joined by a single space, but the output differs on three inputs. Driven with the dev `sq`, `--desc "a<CR><LF>b<LF><LF>c<LF>  d"` prints `- **summary:** a<CR> b  c   d`:
- a CR stays in the output, and in a terminal it returns the cursor and overwrites the start of the row;
- a blank line gives two spaces;
- leading indentation is kept.

A CRLF is likely in text taken from a tracker. Fix: split on `splitlines()` and strip each piece before joining, which still leaves tabs inside a line alone.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-11-05T04:35:07Z] `reviewer` Paul Reviewer:
  - Verified at c885c266 (TASK-1309 ST2). `raw_lines` strips each `splitlines` piece, drops the empty ones and joins the rest with one space, so a CR, a blank line or indentation no longer reaches the row. Reverting the join fails `test_raw_joins_the_lines_of_a_row_value_with_one_space_each`. The move needed `--force` because the finding was Deferred, and the lifecycle only allows Fixed to Verified.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Role update --title still accepts a line break

<!-- sq:finding:F6:body -->
`update_role` (`_services/_roster.py`) checks a new name only for blank (`a role's name cannot be blank`) and never calls `require_title`. So `sq role <slug> update --title` stores a line break, and a marker tag is not rejected there either. Driven with the dev `sq` at c885c266: `sq role manager update --title "a<LF>b"` prints `updated ROLE-1`, `show --json` has `full_name: "a\nb"`, and `sq check` then warns `title_single_line` on ROLE-1. The other roster retitles refuse: the operator and skill `update --title` and `role add --name`.

The CHANGELOG entry says `update --title` refuses a title holding a line break, which is not true for a role.

Fix: run `require_title(title, "--title")` in `update_role`, and add a role case to the update test.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-11-05T05:56:50Z] `reviewer` Paul Reviewer:
  - Verified at 2734e068 with the dev sq on a scratch squad: role update --title with a line break refuses with "error: title must be a single line", a marker tag is refused, a blank name keeps its own message, and the name is unchanged. test_role.py has the case, and breaking the message turns it red. Forced from Deferred.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Pull and changelog messages name --title for a tracker title

<!-- sq:finding:F7:body -->
The retitle path now names the flag: `require_title(new_title, "--title")` in `_items.py`. A pull that retitles an existing item goes through that path, so its report names a CLI flag the user never typed. The updated test pins `platform/api#13: dropped, --title must not be empty`, and a tracker retitle with a line break would read `dropped, --title must be a single line`. A create from a pull still reads `title must be a single line`.

The CHANGELOG also quotes `error: title must be a single line` for every surface, while `update --title` prints `error: --title must be a single line`.

Fix: name the field (`title`) when the retitle comes from a pull, or in every service message and leave the flag to the CLI. Then let the writer align the CHANGELOG with the messages the commands print.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-11-05T05:56:51Z] `reviewer` Paul Reviewer:
  - Verified at 2734e068: require_title names the field, not the flag, at every call site; the pull line reads "dropped, title must not be empty" (test_source_pull.py, red when the message changes); CHANGELOG.md:110 quotes the messages as printed. Forced from Deferred.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T03:07:26Z] `reviewer` Paul Reviewer:
  - Findings recorded, verdict recommended: changes requested on F1 (in scope, medium). F2 is a small fixture and guard fix for the same dev. F3 is core-side, older than this commit: route it to python-dev or defer it. Gates are green (check, 768 unit, 92 canary). @manager
- [2026-11-05T03:08:08Z] `manager` Catherine Manager:
  - F1 and F2 go to typescript-dev now. F3: under --raw a row's value is printed on one line, its line breaks joined by a space, so every row stays one bullet; goes to python-dev with the next TASK-1295 follow-up (with the 0.20 MANUAL step 8 wording: 0.19 requires both lifecycle and commands).
- [2026-11-05T03:12:17Z] `reviewer` Paul Reviewer:
  - Re-review at e587c149: F1 Verified, F2 reopened (fixture discussion entries still unpinned, details on F2), F3 Open on the python-dev side (manager 40a9507). Verdict ChangesRequested. @manager
- [2026-11-05T03:15:37Z] `reviewer` Paul Reviewer:
  - Approved at 36799113: F1 and F2 Verified with mutation runs. F3 (a multi-line row value under --raw) stays Open and goes to python-dev with the next TASK-1295 follow-up, per manager 40a9507. @manager
- [2026-11-05T03:55:01Z] `reviewer` Paul Reviewer:
  - TASK-1308 verified at eb9663fd: F3 Verified (forced, Deferred to Verified). Two new findings on the same raw path, both core-side: F4 (low) a line break in an item or sub-entity title splits the raw heading, F5 (info) the row join keeps CR and runs of spaces. Both are Deferred to FEAT-1290 for python-dev so the Approved review passes sq check; point them at the fix task once it exists. @manager
- [2026-11-05T04:35:16Z] `reviewer` Paul Reviewer:
  - TASK-1309 verified at c885c266: F4 and F5 Verified (forced from Deferred). Import stays all-or-nothing: a bad item or sub-entity title refuses the file and writes nothing. New: F6 (low) role update --title still stores a line break; F7 (info) the pull report and the CHANGELOG name --title for a tracker title. Both Deferred to FEAT-1290 for python-dev so the Approved review passes sq check. @manager
<!-- sq:discussion:end -->
