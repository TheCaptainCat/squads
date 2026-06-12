---
id: REV-000061
sequence_id: 61
type: review
title: 'Review: FEAT-000026 rendered show output'
status: Approved
author: reviewer
refs:
- FEAT-000026:addresses
subentities:
- local_id: F1
  title: 'Plain-output escaping leak: sub-entity pane titles double-escaped in piped/NO_COLOR/--raw
    path'
  status: Fixed
  severity: medium
- local_id: F2
  title: 'Nit: badge/column duplication between _common.py and _discussion.py'
  status: Fixed
  severity: low
- local_id: F3
  title: 'Nit: test gap — no assertion for literal-bracket fidelity in plain pane
    titles'
  status: Fixed
  severity: low
created_at: '2026-06-12T09:32:57Z'
updated_at: '2026-06-12T09:43:19Z'
---
<!-- sq:body -->
Scope: FEAT-000026 implementation (TASK-000058 render core, 059 --full dossier, 060 US6 docs sweep). Reviewed the uncommitted working-tree diff.

Verdict: ChangesRequested — one plain-output fidelity bug; everything else (parser, four-cell semantics, JSON independence, --raw, root show, docs sweep, all gates green: 333 passed, pyright clean, ruff clean) is correct and the styled rendering quality is excellent.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 61 add-finding "…" --severity high`; track with `sq review 61 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Fixed |  | Plain-output escaping leak: sub-entity pane titles double-escaped in piped/NO_COLOR/--raw path |
| F2 | 🟢 low | Fixed |  | Nit: badge/column duplication between _common.py and _discussion.py |
| F3 | 🟢 low | Fixed |  | Nit: test gap — no assertion for literal-bracket fidelity in plain pane titles |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Plain-output escaping leak: sub-entity pane titles double-escaped in piped/NO_COLOR/--raw path

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
src/squads/_cli/_common.py: _subentity_pane_title (line ~148) runs e() on local_id/title/assignee/story because the result feeds a Rich Panel title (correct for the styled path). But the plain branch of _print_full_panes (line ~213) prints that same pre-escaped string with console.print(..., markup=False).

Effect: a sub-entity title containing markup-like brackets renders the Rich-escape backslashes literally in piped / NO_COLOR / --raw output. Reproduced with a subtask titled 'Danger [red]x[/red] and [x] checkbox':

```

styled : ST1 — Danger [red]x[/red] and [x] checkbox  Todo   (correct, literal brackets)

plain  : === ST1 — Danger \[red]x\[/red] and \[x] checkbox  Todo ===   (leaked backslashes)

```

This breaks the 'piped/--raw/NO_COLOR is plain and byte-stable' acceptance criterion (the plain text is not the true title). The same e()+markup=False anti-pattern exists in _render_comments_plain (line ~101) for the comment header; harmless today only because timestamps and roster author names are never tag-like, but it should be fixed for consistency.

Fix: the plain renderers should print the raw (un-e()'d) values. Either pass raw strings to the plain path, or build the plain title/header from the model fields directly without e().
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Nit: badge/column duplication between _common.py and _discussion.py

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
src/squads/_cli/_common.py: _status_badge_for_pane (line ~165) duplicates _discussion._status_badge (same regex camel-split + STATUS_EMOJI lookup); _SUMMARY_COLS_BY_KIND (line ~284) duplicates _discussion._SUMMARY_COLS verbatim.

Non-blocking. Consider reusing the _discussion helpers/constant to keep the badge vocabulary and column order in one place (they will drift independently otherwise).
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Nit: test gap — no assertion for literal-bracket fidelity in plain pane titles

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
tests/test_show_render.py has strong split_discussion and four-cell coverage but no test asserts that a sub-entity title (or comment) containing markup brackets like [red] or [x] renders the LITERAL brackets in the plain/piped path.

That gap is why F1 slipped through. Add a plain-path test with a bracket-bearing sub-entity title asserting the literal '[red]' appears (no backslash) in piped output.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T09:33:35Z] Paul Reviewer:
  - ChangesRequested — one medium fidelity bug (F1) plus two low nits (F2 duplication, F3 test gap). @python-dev please address F1; F2/F3 at your discretion.
  - F1 is the only behavioural blocker: in the plain/piped/NO_COLOR/--raw path, sub-entity pane titles leak Rich-escape backslashes for bracket-bearing titles (e.g. shows backslash-red instead of literal [red]). Styled path is correct. Fix is to feed the plain renderers raw un-escaped values. See F1 for repro and the same latent pattern in the comment plain header.
  - Everything else passed: split_discussion is a faithful inverse of format_comment (verified roundtrip incl. multi-line, fenced code with internal blanks, colon-in-author, fake-header-in-body); the four-cell matrix is exact (--comments=main only, --full=subs no comments, combined=subs+their comments then main last); --json byte-identical across flags; --raw and unknown-id error are clean; root sq show resolves full ID and bare number for any type; US6 docs sweep regenerates cleanly across all 7 sq-type skills + squads.md + CLAUDE.md and sq sync is idempotent.
- [2026-06-12T09:40:09Z] Elias Python:
  - F1 fixed: restructured the escaping boundary so plain renderers never receive pre-escaped values. _subentity_pane_title was renamed to _subentity_pane_title_raw — it builds the title from raw fields with no e() applied. The styled path calls e(raw_title) at the Panel boundary (the single place where Rich markup is in effect). _render_comments_plain likewise changed to use cmt.timestamp and cmt.author directly (no e()) since markup=False is in effect there. A bracket-bearing title like 'Danger [red]x[/red] and [x] checkbox' now appears verbatim in piped/NO_COLOR output with no backslash leakage.
  - F2 fixed: _status_badge_for_pane deleted; _subentity_pane_title_raw now delegates to discussion._status_badge (same impl, one source). _SUMMARY_COLS_BY_KIND deleted; _print_subentity_summary now reads from discussion._SUMMARY_COLS directly. Both private usages carry a pyright: ignore comment — the established pattern already used in tests/test_rendering.py for the same names. STATUS_EMOJI (previously imported for the deleted helper) removed from the import list.
  - F3 fixed: three new tests added to tests/test_show_render.py — test_plain_pane_title_literal_brackets_no_backslashes (plain path: bracket title appears verbatim, no backslash), test_plain_pane_title_literal_brackets_styled_path (styled path: Rich renders literal brackets correctly), and test_plain_comment_header_literal_brackets_no_backslashes (comment header plain path: no backslash leakage). These are the gap tests that would have caught F1 before it shipped.
  - Gates: 336 passed (333 original + 3 new), 1 skipped; pyright 0 errors; ruff clean. @reviewer all three findings Fixed, ready for re-review.
- [2026-06-12T09:43:19Z] Paul Reviewer:
  - Re-review APPROVED. All three findings verified fixed in the working tree; all gates green (336 passed, 1 skipped; pyright 0 errors; ruff clean).
  - F1 (the blocker) — fixed correctly. The escaping boundary was restructured: _subentity_pane_title_raw builds the title from raw fields with no escaping; e() is applied only at the styled Panel title boundary; the plain branch prints the raw title with markup=False. _render_comments_plain now uses raw timestamp/author. Re-ran my original repro in a throwaway squad with a subtask titled with bracket tokens and a checkbox idiom: piped --full prints the title verbatim with zero backslashes (previously leaked escapes); forced-TTY styled path renders the literal brackets inside the Panel border with no leak and no markup consumption. Both paths now correct.
  - F2 — fixed. _status_badge_for_pane and the duplicated summary-columns map are deleted; _common.py reuses discussion._status_badge and discussion._SUMMARY_COLS with a pyright-ignore for private usage — confirmed this is the established pattern (same one in tests/test_rendering.py). STATUS_EMOJI dropped from the import list; SEVERITY_EMOJI rightly retained. Badge vocabulary and column order now have a single source.
  - F3 — fixed. Three new tests in tests/test_show_render.py cover plain pane-title bracket fidelity (asserts no backslash), the styled-path title, and the plain comment-header path. These are exactly the gap tests that would have caught F1.
  - Regression spot-check on the four-cell matrix: none = summary only; --comments = main comments only; --full = sub prose only; --full --comments = sub prose + sub comments + main last. Ordering and scope correct. --json byte-identical across all four flag combos. No regression.
<!-- sq:discussion:end -->
