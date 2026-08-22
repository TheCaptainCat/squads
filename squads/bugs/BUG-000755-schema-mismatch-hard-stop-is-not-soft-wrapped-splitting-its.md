---
id: BUG-755
sequence_id: 755
type: bug
title: Schema-mismatch hard-stop is not soft-wrapped, splitting its own remedy when
  piped
status: Verified
author: qa
refs:
- BUG-745
created_at: '2026-08-21T16:57:42Z'
updated_at: '2026-08-21T20:50:50Z'
---
<!-- sq:body -->
Residual of BUG-745, driven end-to-end (a real schema mismatch, not a Rich render).

BUG-745's fix (ca7cee3) soft-wrapped the three single-line CLI error render sites in
`command`'s `SquadsError` handler, but `require_current_schema` (`src/squads/_cli/_common.py`,
the hard-stop around line 1061) renders its own error separately, via a bare
`err_console.print(...)` with no `soft_wrap=True`. Its remedy is a command an adopter is meant
to copy and run — exactly the shape BUG-745 targeted — and it still hard-wraps at 80 columns
when piped.

Reproduction, driven in a throwaway squad on this branch:

1. `sq init --name architect=Rob` in an empty dir.
2. Edit the generated `.squads.toml`, set `schema_version` one release behind
   `squads._models._schema.SCHEMA_VERSION` (e.g. "0.9" against current "0.11").
3. `COLUMNS=80 sq list 2>&1 | cat -A`

Output (verbatim, `$` = real newline inserted by Rich):

```
error: this squad is at schema v0.9; squads 0.13.0 expects v0.11. Run sq migrate$
up to upgrade it (see `sq migrate help`).$
```

`grep -c "sq migrate up"` on that piped output returns 0 — the copyable remedy is split in
two, the exact failure mode BUG-745 was filed against. This is the message every adopter with
a stale squad hits (the hard-stop fires on nearly every command once schema drifts), and it is
the newer sibling branch too: the schema-ahead message a few lines below the reproduced one
(`"Upgrade the squads package."`) goes through the same unwrapped `err_console.print` call and
shares the defect, even though its current wording happens to fit under 80 columns.

Two related sites share the same shape (missing `soft_wrap=True` on an `err_console.print`/
`console.print` that can carry a long copyable token) but are not this bug's reproduction and
are noted only so they are not lost:

- `version_notice()` (`_common.py`, prints "squads X detected ... Run `sq sync` to refresh
  them."): today's version strings keep the line at 79 chars on an 80-column pipe, just under
  the wrap, so it does not currently manifest — but it is the identical defect, latent on a
  longer version string.
- The per-file degrade loops in `_report_unreadable` (`_cli/_main.py`, feeding `sq inbox`/
  `sq search`), and the equivalent per-file error loops in `sq board list` and
  `sq memory <role> list/search` — these print an unwrapped `[red]error[/red]: {msg}` per
  unreadable file, where `msg` includes a file path that can exceed 80 columns and split.

Scope for the fix: audit every `err_console.print`/`console.print` call site that renders a
single logical line containing a copy-pasteable command or path, outside the three the
BUG-745 fix already covers, and add `soft_wrap=True` (matching the pattern already used at
`_common.py` lines 375/951/1011). The two schema-mismatch branches in `require_current_schema`
are the must-fix; the version notice and per-file degrade loops are worth sweeping in the same
pass since they are the same one-line fix, but are not required to close this ticket if scoped
tighter.

Follow-up on scope: `sq override scaffold`'s success-guidance messages (`_cli/_override.py`,
`console.print` calls that say "Edit <path> to ... then verify with ...") are the same
mechanism — an unwrapped Rich print carrying a long copyable path/command — and were seen to
wrap mid-path when piped during this verification pass. They differ from everything above in
two ways: they are `console.print` (stdout, informational success output), not
`err_console.print` (stderr, an error/hard-stop path), and they live in a different module
(`_override.py`) entirely unconnected to schema checking or CLI error rendering.

Recommendation: keep them in this bug's scope rather than opening a third item. The fix at
every site discussed here is the identical one-liner (add `soft_wrap=True`), so splitting the
`_override.py` sites into their own ticket would fragment one mechanical sweep across two
tickets for no benefit — there is no separate design question, owner, or shipping increment
that would justify a second item. Whoever picks up this bug should include the
`sq override scaffold` message sites in the same audit/sweep.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T20:48:44Z] Mara Tester:
  - Drove the bug's own reproduction end to end on 9ebcf6d: fresh throwaway squad, schema_version set one release behind SCHEMA_VERSION, COLUMNS=80 sq list piped through cat -A. The remedy is now one unbroken line and grep -c "sq migrate up" on the piped output returns 1.
  - Spot-checked several of the other sites, especially the per-file degrade loops I originally reported. Real corruption + a long path in each case: sq board list (malformed-YAML notice file, ~130-char filename) prints the whole path on one line, greps whole. sq memory qa list AND search (malformed-YAML memory file, ~130-char filename) same result, both commands. sq search and sq inbox qa (a broken-symlink item file, both an out-of-squad-escape shape and an in-squad broken-symlink shape) each print their error as one unbroken line with the full path intact and grep whole. All hold.
  - Status note for the record: this bug is still InProgress on disk, not Fixed -- no discussion comment on the item itself names the landing commit, even though the fix genuinely shipped in 9ebcf6d (confirmed by driving it, and corroborated by TASK-762's handoff comment, which references this bug's board-list/memory finding by content). InProgress -> Verified is not a legal transition in the bug lifecycle (only Fixed -> Verified is), so I have not transitioned this item -- flagging for whoever should move it InProgress -> Fixed first.
- [2026-08-21T20:50:45Z] Catherine Manager:
  - Fix landed in 9ebcf6d on release/0.14 (TASK-762): 33 advisory print sites soft-wrapped across nine _cli modules, found by an AST scan rather than the briefed list of eight, plus a class-level guard in tests/meta. My own bookkeeping error left this item in InProgress after I verified the fix - recording the landing commit now, which is what QA correctly refused to transition around.
- [2026-08-21T20:50:48Z] Catherine Manager:
  - Verified. QA drove the schema-mismatch reproduction end to end (real mismatch, COLUMNS=80, piped, remedy greps whole) and spot-checked the per-file degrade loops on real corruption in board list, memory list and search, sq search and sq inbox. I independently confirmed the remedy survives piping and that reverting one real site makes the class guard fail naming _board.py:89.
<!-- sq:discussion:end -->
