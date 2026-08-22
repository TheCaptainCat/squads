---
id: BUG-769
sequence_id: 769
type: bug
title: sq board list and sq memory print unreadable-file errors to stdout
status: Verified
author: qa
refs:
- BUG-755
created_at: '2026-08-21T20:49:37Z'
updated_at: '2026-08-22T09:37:03Z'
---
<!-- sq:body -->
Independently confirmed by two agents (a dev while landing the wrapping fix, and this pass
re-driving it). This is a stream-contract defect, not a wrapping one -- the wrapping at every
site named below is already fixed and stays that way.

`sq board list`'s docstring states the unreadable-file errors are "named on stderr, whether or
not `--json` is given". `sq memory <role> list` and `sq memory <role> search` each carry the
identical claim ("named on stderr in both output modes"). None of the three keeps that promise
in its human (non-`--json`) branch.

Driven, with a corrupted notice/memory file and stdout/stderr captured separately:

    command                          stdout-only (2>/dev/null)    stderr-only (1>/dev/null)
    sq board list                    the per-file error text      (empty)
    sq board list --json             (empty)                      the per-file error text
    sq memory <role> list            the per-file error text      (empty)
    sq memory <role> list --json     (empty)                      the per-file error text
    sq memory <role> search          the per-file error text      (empty)
    sq memory <role> search --json   (empty)                      the per-file error text

Each command's own `--json` branch is correct -- it sends the error to `err_console` (stderr)
exactly as documented. The human branch right below it, in the same function, sends the
identical message to `console` (stdout) instead. Source confirms the shape: in
`src/squads/_cli/_board.py`'s `list_notices`, the `--json` arm's loop prints via
`err_console.print(...)`, the plain arm's loop right after it prints via `console.print(...)` --
same message, same per-file loop, different stream. `src/squads/_cli/_memory.py`'s
`list_memories` and `search_memories` repeat the identical pattern.

This matters beyond the docstring's own promise: a script that runs the human-mode command and
separates stdout (results) from stderr (diagnostics) -- the whole point of the stream split --
currently gets a degraded read silently mixed into its results stream, with nothing on stderr
to say the read was incomplete. `sq check`'s per-issue reporting and `_report_unreadable`
(feeding `sq inbox`/`sq search`) do not have this defect; both already send their non-JSON
output to stderr correctly, which is the shape these three commands' own docstrings claim but
their human branches do not implement.

Scope: the plain (non-`--json`) branches of `sq board list`, `sq memory <role> list`, and `sq
memory <role> search` -- three `console.print` call sites, one per command, each printing the
per-file unreadable-error loop to the wrong stream. The `--json` branches are already correct
and untouched by this. Not a rendering/wrapping change: every one of these sites already carries
`soft_wrap=True`, so the fix here is switching the receiver from `console` to `err_console`,
nothing about the message text or its wrapping.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T09:26:21Z] Catherine Manager:
  - Fix landed in 04945d2 on release/0.14 (TASK-774 ST3). Verified independently: with a corrupt notice file present, sq board list puts zero error text on stdout and one on stderr. The dev also corrected a pre-existing test that had asserted the stdout stream as expected behaviour, which is why the defect survived. --json is untouched and the exit code unchanged.
- [2026-08-22T09:28:55Z] Mara Tester:
  - Verified on 04945d2 with stdout/stderr captured separately (never combined), all three commands, real corruption (malformed-YAML file) not a synthetic message.
  - sq board list human mode: 2>/dev/null shows only 'no current notices' (no error text on stdout); 1>/dev/null shows the full error on stderr. --json unchanged: error still on stderr only, stdout still the bare array. Exit code 1 in all four captures.
  - sq memory qa list and sq memory qa search, human mode: same split -- 2>/dev/null shows only the empty-result line, 1>/dev/null shows the full error. --json unchanged (error on stderr, array on stdout). Exit code 0 in all captures, both commands.
  - Confirmed 'exit code unchanged' empirically, not just by reading the diff: reproduced the same three scenarios on a worktree at 04945d2^ (pre-fix). Pre-fix, the identical error text appeared on the STDOUT-only capture (the defect) for both board list and memory list, with the same exit codes (1 and 0 respectively) as post-fix -- only the stream moved, nothing about exit-code logic did, matching that the diff touches only console.print -> err_console.print at three call sites.
  - Also noted per the handoff: a pre-existing test asserted the stdout stream as expected. Read it fixed in the same commit (test_unreadable_files_degrade_per_file_cli.py) rather than re-deriving that a green suite before this landed was not evidence.
<!-- sq:discussion:end -->
