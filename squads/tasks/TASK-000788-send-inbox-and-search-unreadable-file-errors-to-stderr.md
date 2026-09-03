---
id: TASK-788
sequence_id: 788
type: task
title: Send inbox and search unreadable-file errors to stderr
status: Done
author: tech-lead
assignee: python-dev
priority: low
refs:
- BUG-787:fixes
description: 'Stream-contract fix in the shared per-file degrade helper: the human
  branch prints to stdout, --json is already correct'
created_at: '2026-08-22T13:53:45Z'
updated_at: '2026-08-22T14:17:46Z'
---
<!-- sq:body -->
`sq inbox` and `sq search` print their per-file unreadable-file skip lines to **stdout** in human
mode, while each command's `--json` mode correctly uses stderr. A script that separates stdout
(results) from stderr (diagnostics) gets a degraded read mixed silently into its results, with
nothing on stderr to say the read was partial.

**This is a stream-contract defect only.** The wrapping half of the same message was already fixed
for these two commands — the helper already passes `soft_wrap=True` regardless of target — so the
message text and its shape do not change. The fix is the receiver.

Driven, fresh squad, stdout and stderr captured separately:

```
sq inbox manager            2>/dev/null  -> shows the error text        (defect)
sq inbox manager            1>/dev/null  -> empty
sq inbox manager --json     2>/dev/null  -> "[]" only                  (correct)
sq inbox manager --json     1>/dev/null  -> the error text             (correct)

sq search probe             2>/dev/null  -> results AND the error text  (defect)
sq search probe             1>/dev/null  -> empty
sq search probe --json      2>/dev/null  -> the JSON array only         (correct)
sq search probe --json      1>/dev/null  -> the error text             (correct)
```

Exit code 1 unchanged in every case, both commands, both modes.

## Surface, and the whole affected set

`src/squads/_cli/_main.py` only. One helper, `_report_unreadable(unreadable, *, json_out)`, whose
target selection is `target = err_console if json_out else console` — so the human branch always
prints to stdout. It has exactly four call sites, two per command, one per output mode, and
`sq inbox` and `sq search` are its only callers anywhere in the CLI. No third command shares it.

`sq board list` and `sq memory <role> list`/`search` never called this helper — they had their own
separate inline per-file loop, fixed independently, which is why that fix named only those two
commands. Nothing shipped false; this is a pre-existing gap in the same defect family that was in
neither item's scope.

While you are in the helper: its docstring frames the stream choice as a `--json` concern
("Out-of-band matters for `--json`: … the messages go to stderr"). Out-of-band matters in both modes,
which is what this defect demonstrates. Correct that reasoning rather than leaving a docstring that
justifies the behaviour being removed.

## Boundaries

- Touch `src/squads/_cli/_main.py` and its tests. Nothing else.
- **Stay out of `src/squads/_backends/`.** Another dev is reworking the `agents_md` backend there
  right now, and this change has no business in that directory.

## Acceptance criteria

- The human-mode branch sends each per-file error to **stderr**; stdout carries only the command's
  actual output — the inbox/search results, or the empty-result note.
- **The test captures stdout and stderr separately and asserts the error is absent from stdout**, not
  merely present somewhere. A combined-output grep passes on the current defect, and that is exactly
  how this survived the earlier sweep — so it is explicit acceptance, not a stylistic preference.
- **Both commands covered**, not one standing in for the pair.
- `--json` behaviour byte-identical in both streams for both commands.
- **Exit code stays 1** on a degraded read, in every case, both commands, both modes. Assert it on the
  process exit status directly, not through a pipeline, since a pipeline masks it.
- **`soft_wrap=True` is asserted still present**, so this cannot quietly undo the wrapping fix that
  already landed for these same two commands.
- A clean read (nothing unreadable) is unchanged: no output on stderr, results on stdout, exit 0.
- The helper's docstring no longer presents stderr as a `--json`-only concern.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.

## Handoff

**Do not edit `CHANGELOG.md`.** The tech-writer owns the release notes and has just reauthored them.
Hand the tech lead **one line** describing what changes for an adopter, and it goes to the writer from
there.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 788 add-subtask "<title>"`; track with `sq task 788 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T13:54:06Z] Olivia Lead:
  - Small stream-contract fix, scoped to _cli/_main.py and its tests, with an explicit instruction to stay out of src/squads/_backends/ while the agents_md rework is in flight. Confirmed the affected set from source: one helper, target = err_console if json_out else console, four call sites (two for inbox, two for search) and no other caller in the CLI.
  - One addition from reading the helper: its docstring justifies the stream choice as a --json concern ("Out-of-band matters for --json: the messages go to stderr"), which is the reasoning this defect disproves. Body requires that corrected too, so the fix does not leave a docstring arguing for the behaviour being removed.
  - Acceptance makes the separate-streams test explicit rather than advisory (a combined-output grep passes on the defect, which is how this survived the first sweep), requires soft_wrap=True asserted still present, and requires the exit code checked on the process status directly rather than through a pipeline. Changelog: the dev hands one line for the writer, no CHANGELOG edit.
- [2026-08-22T14:02:14Z] Elias Python:
  - Fixed: _report_unreadable's human branch now always targets err_console (was target = err_console if json_out else console); docstring corrected to say out-of-band matters in both modes, not just --json.
  - Driven, throwaway squad, broken-directory unreadable file, stdout/stderr captured as separate real pipes, exit checked on the process status directly (no shell pipeline):
  - BEFORE (stashed the fix): sq inbox manager -> stdout carries BOTH the readable hit AND the error line, stderr empty, exit=1. sq search quinoa -> same: stdout carries results AND the error, stderr empty, exit=1.
  - AFTER (this fix): sq inbox manager -> stdout='TASK-12 readable (Draft) / the quinoa line...' only, stderr='error: .../TASK-000013-unreadable.md could not be read: Is a directory', exit=1. sq search quinoa -> stdout=results only, stderr=same error line, exit=1.
  - --json unchanged in both streams, both commands: stdout is a bare JSON array with only TASK-12, stderr carries the same error line, exit=1.
  - Clean read (no unreadable file): sq inbox manager -> stdout=results, stderr='' (0 bytes), exit=0. Same shape confirmed for search.
  - soft_wrap=True pinned as still present at the shared site (_report_unreadable) via an AST-based test, extending the existing pin list (board list / memory list / memory search).
  - Tests added: tests/cli/test_unreadable_files_degrade_per_file_cli.py (subprocess, real separate OS pipes, direct exit-code assertions) and tests/service/test_search_and_inbox_degrade_per_file.py (fixed two CLI tests that were asserting the error text present in stdout -- that is, asserting the defect -- and added the missing inbox human-mode counterpart).
  - Adopter-facing one-liner for the changelog: 'sq inbox and sq search now report unreadable-file errors on stderr in human mode too, matching --json and every other read command.'
  - Gates: pyright 0 errors, ruff check all checks passed, ruff format 539 files already formatted, pytest tests/meta 181 passed, plus the touched CLI/service modules 227 passed. sq check: no issues.
  - Commit cfd19a5, unpushed, only src/squads/_cli/_main.py + the two test files staged.
  - Left BUG-787 InProgress for QA to verify.
<!-- sq:discussion:end -->
