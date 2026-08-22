---
id: BUG-787
sequence_id: 787
type: bug
title: sq inbox and sq search still print unreadable-file errors to stdout
status: Verified
author: qa
severity: low
refs:
- BUG-769
created_at: '2026-08-22T13:51:47Z'
updated_at: '2026-08-22T14:17:40Z'
---
<!-- sq:body -->
Same defect class as BUG-769, on the two commands that share `_report_unreadable`
(`_cli/_main.py`) instead of printing their own per-file skip loop inline. Found by the
tech-writer auditing the release notes (read from source, not driven); re-driven here with
stdout and stderr captured separately, since a combined-output grep is exactly how the
original slipped through and would pass on this one too.

Fresh throwaway squad, one task with a broken-symlink file to trigger the per-file degrade
path:

    sq inbox manager                    2>/dev/null  -> shows the error text (defect)
    sq inbox manager                    1>/dev/null  -> empty
    sq inbox manager --json             2>/dev/null  -> "[]" only (correct)
    sq inbox manager --json             1>/dev/null  -> the error text (correct)

    sq search probe                     2>/dev/null  -> results AND the error text (defect)
    sq search probe                     1>/dev/null  -> empty
    sq search probe --json              2>/dev/null  -> the JSON array only (correct)
    sq search probe --json              1>/dev/null  -> the error text (correct)

Exit code 1 unchanged in every case, both commands, both modes. `--json` is correct for both
— the defect is confined to the human-mode branch, exactly as it was for `sq board list`/
`sq memory list`/`sq memory search` before BUG-769.

Mechanism, read directly: `_report_unreadable(unreadable, *, json_out)` picks its target with
`target = err_console if json_out else console` — the human branch (`json_out=False`) always
prints to stdout. `sq inbox` and `sq search` are the only two callers of this helper in the
whole CLI (`grep -n "_report_unreadable(" src/squads/_cli/_main.py` — four call sites, two
per command, one per mode); no third command shares it. `sq board list` and `sq memory
<role> list`/`search` never called this helper at all — they had their own separate inline
per-file loop, fixed independently by BUG-769/`04945d2`, which is why that fix's changelog
entry correctly names only those two commands and did not claim to cover these. Nothing
shipped false; this is a real, pre-existing gap in the same defect family that simply wasn't
in either bug's scope, not a regression introduced by that fix or by anything else in this
release.

**Severity: low.** Reasoning, not a default: the wrapping half of this same message (a long
skip line splitting mid-token when piped) was already fixed for `inbox`/`search` alongside
everything else in the earlier soft-wrap sweep — `_report_unreadable` already calls
`target.print(..., soft_wrap=True)` regardless of target, so what is missing here is only the
stream, not the content or its shape. The practical exposure is a script that separates
stdout (results) from stderr (diagnostics) for `sq inbox`/`sq search` specifically and expects
a clean stdout stream on a degraded read — narrower than `sq board list`, which every agent in
this project runs at the start of every session per this project's own working agreements,
and narrower than `sq check`, the actual health gate. `sq inbox`/`sq search` are read/filter
commands an operator or script runs opportunistically, not a startup ritual or a gate, so a
polluted stdout on the (uncommon) degraded-read path is a real but low-traffic inconsistency
rather than something actively breaking a documented workflow today.

Not proposing this as a release blocker: it predates this release's own changes to this area
and op-pierre is best placed to decide whether the one-line fix (route `_report_unreadable`'s
human branch to `err_console`, matching BUG-769's fix exactly) rides along in 0.13.1 or waits.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T14:17:37Z] Catherine Manager:
  - Fix landed in cfd19a5 on release/0.14 (TASK-788), shipping in 0.13.1. Verified independently with stdout and stderr captured separately on both commands: the per-file error is on stderr only, stdout carries results alone, --json still puts the array on stdout with the error on stderr, and the exit code stays 1. A clean read leaves stderr empty at exit 0. The dev also found a pre-existing test asserting the defect itself - it checked the error text was present in stdout - which is the second such test this release.
<!-- sq:discussion:end -->
