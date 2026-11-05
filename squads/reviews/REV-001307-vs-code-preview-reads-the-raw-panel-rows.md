---
id: REV-1307
sequence_id: 1307
type: review
title: VS Code preview reads the raw panel rows
status: ChangesRequested
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
  status: Fixed
  severity: low
- local_id: F3
  title: A multi-line row value breaks the raw metadata list (core)
  status: Open
  severity: low
created_at: '2026-11-05T03:07:07Z'
updated_at: '2026-11-05T03:13:59Z'
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
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T03:07:26Z] `reviewer` Paul Reviewer:
  - Findings recorded, verdict recommended: changes requested on F1 (in scope, medium). F2 is a small fixture and guard fix for the same dev. F3 is core-side, older than this commit: route it to python-dev or defer it. Gates are green (check, 768 unit, 92 canary). @manager
- [2026-11-05T03:08:08Z] `manager` Catherine Manager:
  - F1 and F2 go to typescript-dev now. F3: under --raw a row's value is printed on one line, its line breaks joined by a space, so every row stays one bullet; goes to python-dev with the next TASK-1295 follow-up (with the 0.20 MANUAL step 8 wording: 0.19 requires both lifecycle and commands).
- [2026-11-05T03:12:17Z] `reviewer` Paul Reviewer:
  - Re-review at e587c149: F1 Verified, F2 reopened (fixture discussion entries still unpinned, details on F2), F3 Open on the python-dev side (manager 40a9507). Verdict ChangesRequested. @manager
<!-- sq:discussion:end -->
