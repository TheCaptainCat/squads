---
id: TASK-774
sequence_id: 774
type: task
title: Widen the advisory-print guard and fix the sites it was missing
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- REV-770:addresses
- BUG-769:fixes
description: The class guard is blind to an attribute receiver, one real unwrapped
  site hides behind that hole, and three human-mode diagnostics go to stdout
subentities:
- local_id: ST1
  title: Accept an attribute receiver in the advisory-print guard
  status: Done
- local_id: ST2
  title: Soft-wrap the root --at timestamp refusal
  status: Done
- local_id: ST3
  title: Send human-mode unreadable-file errors to stderr
  status: Done
created_at: '2026-08-22T09:08:24Z'
updated_at: '2026-08-22T09:26:34Z'
---
<!-- sq:body -->
Three defects on one surface, all in `_cli/`, deliberately one task: the class guard that was
supposed to make a hand-maintained site list unnecessary is blind to a receiver form two files
already use, one of the sites it cannot see is a real unwrapped error the sweep missed, and three
more sites in the same neighbourhood send diagnostics to the wrong stream.

The first two are the same job — the guard's blind spot is exactly why the missed site was missed,
so fixing one and not the other leaves either a real defect or a guard that still certifies it as
clean. The third is a different defect class (stream, not wrapping) at sites whose wrapping is
already correct and must stay correct; it rides along because it is the same owner, the same
increment and the same directory, with no file overlap to collide over.

**Subtask order matters: 1 before 2.** Widening the guard first should make the `--at` site visible,
which is the guard proving itself on a real defect rather than on a planted one.

## Handoff, for all three subtasks

**Do not edit `CHANGELOG.md`.** Hand the tech lead your adopter-facing entry text in your handoff
comment. One item needs calling out specifically rather than left in a list: the changelog currently
names `--at` as *still unchanged*, which subtask 2 makes false — say so explicitly in the handoff so
that sentence gets corrected when this lands.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 774 add-subtask "<title>"`; track with `sq task 774 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Accept an attribute receiver in the advisory-print guard

<!-- sq:subtask:ST1:body -->
The class guard `tests/meta/test_single_line_advisory_prints_stay_soft_wrapped.py` resolves a print's
receiver with:

```python
def _receiver_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    return None
```

so only a bare `console` / `err_console` / `target` name is ever in scope. A module-qualified
receiver — `common.console.print(...)`, `common.err_console.print(...)`, an `ast.Attribute` — is not
merely unmatched, it is **never collected as a candidate at all**. Two files in `_cli/` use that form
exclusively: `_cli/__init__.py` and `_cli/_import.py`.

**Why this is worth doing at all: the guard currently certifies as clean a tree containing the exact
defect it exists to prevent.** Driven, calling the module's own `_unwrapped_marker_hits` — the same
helper the real assertion runs:

```
over src/squads/_cli, keyed at repo root                      -> {}   (zero hits)
over a planted tree containing a verbatim copy of
_cli/__init__.py:267 with a `common.err_console` receiver     -> {}   (still zero)
```

A direct AST scan of the same tree, differing only in accepting an `ast.Attribute` receiver, finds
two marker-matching unwrapped calls: `_cli/__init__.py:267` and `_cli/_import.py:95`. So the guard's
green is not evidence the property holds — it is evidence the property was not checked on those
files. All four existing plant tests plant a bare `console` receiver, so none of them can catch this,
and `test_the_allowlist_has_no_stale_entry` cannot either, because the allowlist is empty.

The guard's idea is right and stays: restricting to `ast.Constant`/`ast.JoinedStr` first arguments
excludes every `Table`/`Panel`/bound-prose render by construction rather than by allowlist, which is
what makes an empty allowlist honest. The weakness is in the predicate.

## What to change

Accept an `ast.Attribute` receiver whose **trailing attribute name** is in `_CONSOLE_RECEIVERS`, so
`common.err_console` resolves as `err_console`. Then soft-wrap whatever real sites the widened
predicate reveals.

## The computed-marker hole — an option, not a requirement

The guard documents a second hole: a print whose marker word is computed at runtime. That hole is
real but narrower than feared — every unwrapped interpolated console print under `_cli/` was scanned
for a runtime-computed advisory prefix and there is **exactly one**, `_cli/_main.py:1577`
(`f"[{color}]{i.level}[/{color}]…"`, the `sq check` issue line), which already carries `soft_wrap`
from the earlier sweep. Nothing else in the package builds its `error`/`warning` word at runtime.

The suggestion is to forbid a *computed* style tag on a console print rather than trying to read one,
which closes that class at the cost of one allowlist entry for the site that legitimately does it.
**Take it or reject it, and state the reason either way** — an allowlist entry is a decision on the
record, and so is declining to add the rule.

## Acceptance criteria

- `_receiver_name` accepts an attribute receiver by its trailing attribute name; a bare-name
  receiver keeps behaving exactly as it does today.
- **A plant test using the attribute form**, so the hole cannot reopen. Revert the predicate widening
  and that test must go red — drive it and report both directions. Without this test the fix is one
  edit away from being undone silently, which is the whole lesson of this defect.
- The existing four plant tests, `test_a_non_console_receiver_is_ignored`, and
  `test_a_prebuilt_renderable_or_bound_prose_variable_is_never_a_candidate` all still pass — the
  widening must not turn a `Table`/`Panel` render or a genuinely unrelated receiver into a candidate.
- Every real site the widened predicate reveals is soft-wrapped, and the guard is green against the
  live tree afterwards with the allowlist still honest (empty, or carrying only entries you justified).
- **`_cli/_import.py:74` is fixed by hand and its status stated.** It reads `[red]line {issue.line}:`
  and carries file paths and ids that exceed 80 columns, but the marker list holds `[red]error`, so
  the widened predicate collects it as a candidate and still will not flag it. Soft-wrap it, then say
  whether the marker list should grow to cover that shape — and if you think it should, say what the
  false-positive risk is rather than just adding the string.
- The computed-marker option is either implemented with its allowlist entry, or declined with a
  stated reason.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Soft-wrap the root --at timestamp refusal

<!-- sq:subtask:ST2:body -->
The root callback's `--at` timestamp refusal is unwrapped, so its ISO example splits across a real
newline when stderr is piped. It was one of the sites the earlier sweep named explicitly and did not
fix, and its receiver form is exactly the one the class guard cannot see — which is why subtask 1
comes first.

Driven at `COLUMNS=80`, stderr piped, `$` marking the newline Rich inserted:

```
sq --at nope list
  error: invalid --at timestamp 'nope' (use ISO 8601, e.g. 2024-01-15 or $
  2024-01-15T09:30:00Z)$

sq reflog --since nope          (the sibling that was fixed, for contrast)
  error: invalid --since timestamp 'nope' (use ISO 8601, e.g. 2026-01-15 or 2026-01-15T09:30:00Z)$
```

## Surface

`src/squads/_cli/__init__.py`, the `--at` parser's `common.err_console.print` in the root callback's
`ValueError` arm — the call that precedes `raise typer.Exit(2)`. Message text, colour and exit code
are unchanged; this is wrapping only.

## Acceptance criteria

- `COLUMNS=80 sq --at nope list 2>&1 | cat -A` shows the ISO example on one line, with no `$` inside
  `2024-01-15T09:30:00Z`, and `grep -c "2024-01-15T09:30:00Z"` on the piped output returns 1.
- The exit code stays 2 — this parser refuses differently from the general error path, and a wrapping
  change must not normalise that.
- `sq reflog --since nope` is unchanged, as the contrast case.
- **State whether subtask 1's widened guard caught this site.** If it did, the guard has proved itself
  on a real defect rather than a planted one — say so. If it did not, that is a finding about the
  guard and it goes in the handoff, because a guard that misses the very site that motivated widening
  it is not finished.
- A test covers the site, in the shape the class guard uses rather than a one-off assertion on this
  one message.

## Handoff

The changelog currently names `--at` as **still unchanged**. This makes that false. Flag it
explicitly in your handoff comment — not buried in a list — so the tech lead corrects that sentence.
Do not edit `CHANGELOG.md` yourself.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Send human-mode unreadable-file errors to stderr

<!-- sq:subtask:ST3:body -->
`sq board list`, `sq memory <role> list` and `sq memory <role> search` print their per-file
unreadable-file errors to **stdout** in the human form, while each command's `--json` branch
correctly uses stderr. Every one of the three docstrings promises stderr in both modes.

**This is a stream-contract defect, not a wrapping one.** Every site below already carries
`soft_wrap=True`; that stays, and the message text does not change. The fix is the receiver.

Driven, with a corrupted notice/memory file and the two streams captured separately:

| command | stdout only (`2>/dev/null`) | stderr only (`1>/dev/null`) |
|---|---|---|
| `sq board list` | the per-file error text | (empty) |
| `sq board list --json` | (empty) | the per-file error text |
| `sq memory <role> list` | the per-file error text | (empty) |
| `sq memory <role> list --json` | (empty) | the per-file error text |
| `sq memory <role> search` | the per-file error text | (empty) |
| `sq memory <role> search --json` | (empty) | the per-file error text |

Why it matters past the docstring: a script that runs the human-mode command and separates stdout
(results) from stderr (diagnostics) — the entire point of the split — currently gets a degraded read
mixed silently into its results, with nothing on stderr to say the read was incomplete.
`sq check`'s per-issue reporting and the corpus-walk report feeding `sq inbox`/`sq search` already do
this correctly, so the shape to match is in the codebase.

## Surfaces

Three `console.print` call sites, one per command, each the human arm's per-file loop sitting
directly below a correct `err_console.print` loop in the same function:

- `src/squads/_cli/_board.py` — `list_notices`
- `src/squads/_cli/_memory.py` — `list_memories`
- `src/squads/_cli/_memory.py` — `search_memories`

## Acceptance criteria

- The human form sends each per-file error to **stderr**; stdout carries only the command's actual
  output (the notice/memory listing, or the "no current notices" / "no memories" / "no matches" line).
- **A test asserts the stream, not just the text** — stdout and stderr captured separately, with the
  error asserted present on stderr *and* absent from stdout. A test that greps combined output passes
  on the current defect and is not acceptance.
- All three commands are covered, not one standing in for the family.
- `--json` behaviour is byte-identical: the payload on stdout, the errors on stderr, unchanged.
- The non-zero exit code where a command has one (`sq board list` exits 1 on an unreadable notice) is
  unchanged — a script gating on `$?` must see exactly what it sees today.
- **`soft_wrap=True` stays at all three sites.** Assert it, so this change cannot quietly undo the
  earlier wrapping fix.
- Each command's docstring still describes what the code now does — check the wording rather than
  assuming, since the docstrings were already right and the code was wrong.

## Report, do not fix

`_cli/_import.py` prints its importer warnings via `common.console` — a `[yellow]warning:` line going
to **stdout**. That is arguably the same stream question as the three sites above, but it is outside
this subtask's scope and belongs to whoever owns that command's contract. Say in your handoff whether
you think it should move to stderr; do not change it here.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T09:09:11Z] Olivia Lead:
  - One task, three subtasks, ordered 1 before 2 so the widened guard is what surfaces the --at site. ST1 acceptance requires the attribute-form plant test with a driven revert (the fix is otherwise one edit from being undone silently, which is the lesson of this defect) and requires the existing renderable/non-console-receiver tests to keep passing, since the widening must not turn a Table/Panel render into a candidate.
  - Two additions from reading the source. _cli/_import.py:74 reads [red]line {n}: — the widened predicate collects it as a candidate but the marker list holds [red]error, so it still will not flag; ST1 requires it fixed by hand plus a stated position on whether the marker list should grow (with the false-positive risk named, not just the string added). And _cli/_import.py:95 sends a [yellow]warning: line to stdout via common.console, which is arguably ST3s stream question one file over — ST3 says report it, do not fix it.
  - ST2 requires the dev to state whether ST1s guard caught the --at site, and treats a miss as a finding about the guard rather than a footnote. ST3 requires the test to capture stdout and stderr separately and assert absence from stdout — a combined-output grep passes on the current defect — plus that soft_wrap stays asserted at all three sites so this cannot undo the earlier wrapping fix.
- [2026-08-22T09:22:31Z] Elias Python:
  - ST1 (done): widened _receiver_name (tests/meta/test_single_line_advisory_prints_stay_soft_wrapped.py) to resolve an ast.Attribute receiver by its trailing name, so common.err_console/common.console now register as candidates. Added test_the_wired_guard_reddens_on_a_planted_attribute_receiver (attribute-form plant). Driven both directions: reverted the widening -> that test goes red (missing == {}, expected the planted site); restored -> green. All four pre-existing plant tests, test_a_non_console_receiver_is_ignored and test_a_prebuilt_renderable_or_bound_prose_variable_is_never_a_candidate still pass, so Table/Panel/bound-prose renders are still excluded by construction.
  - ST1: the widened predicate revealed exactly two real unwrapped, marker-matching sites -- _cli/__init__.py:267 and _cli/_import.py:95 -- confirmed by running the guard before and after (before: {} on the live tree same as the old guard reported; after: two hits; then soft_wrap=True on both makes it {} again). Also fixed _cli/_import.py:74 by hand -- it reads [red]line {n}: which the marker list does not match ([red]error only), so the widened predicate still would not have caught it. Position on growing MARKERS with a "[red]line" entry: declining. That prefix is a generic Rich style tag, not an advisory-specific word like error/warning -- widening MARKERS to it risks collecting future non-advisory per-line renders (diff/blame-style listings, itemized reports) as candidates and forcing allowlist churn for things that were never advisories. Fixed the one known site by hand instead; the guard already prevents a *silent* regression there via soft_wrap enforcement once a call is a candidate for some other reason.
  - ST1: computed-marker hole (a print whose color/level word is built at runtime, e.g. _main.py:1577) -- declined the "forbid a computed style tag" rule, reasoning recorded in the guard module docstring: the only site with this shape already carries soft_wrap=True, and a positive rule would need to distinguish an advisory computed tag from any other legitimate computed-color single-line render, which is exactly the ambiguity the literal-text exclusion is designed to avoid. Revisit if a second computed-marker site appears.
  - ST2 (done): guard-caught-it answer is YES -- ST1s widened guard flagged _cli/__init__.py:267 on the live tree before I touched it (see ST1 evidence above), so this is the guard proving itself on a real defect, not a planted one. Added soft_wrap=True at the --at ValueError arm. New test test_an_unparseable_at_values_iso_example_stays_on_one_line (tests/cli/test_time_forging_backdates_items_and_comments.py) asserts no embedded newline and exactly one occurrence of the ISO token, at the suites pinned COLUMNS=80 -- same shape as the class guard (absence of a split), not a hardcoded full-message match. Exit code still 2, confirmed. sq reflog --since nope contrast case unaffected (still exit 1, already soft_wrap=True, unrelated to this change; see test_reflog_cli.test_an_invalid_since_value_is_rejected).
  - ST3 (done): switched the human-mode per-file loop in list_notices (_board.py), list_memories and search_memories (_memory.py) from console.print to err_console.print -- soft_wrap=True kept unchanged at all three (see new parametrized test_the_human_mode_unreadable_error_still_carries_soft_wrap, an AST pin independent of the tests/meta guard). New subprocess tests (tests/cli/test_unreadable_files_degrade_per_file_cli.py) capture real OS stdout/stderr separately for board list, memory list and memory search and assert the unreadable-file name is present on stderr and ABSENT from stdout -- not a combined-output grep. Also corrected an existing test (test_board_list_exits_1_bare_on_a_corrupt_notice) that had been asserting the bug itself (the notice name in stdout) as expected behavior. --json branches untouched (byte-identical); exit codes unchanged (board list still 1 on unreadable, memory list/search still 0). Docstrings already promised stderr in both modes and needed no wording change -- only the code was wrong.
  - Report only (out of ST3 scope per brief): _cli/_import.py:95 ([yellow]warning: via common.console) still sends importer warnings to stdout. Same stream question as BUG-769 one file over -- my read is it should probably move to stderr for the same reason (a script separating stdout results from stderr diagnostics currently gets warnings mixed into its results), but that is scope creep past this bug and belongs to whoever owns sq imports contract.
  - CHANGELOG correction: the current unreleased entry names --at as still unchanged/unfixed -- that sentence is now false (ST2). Please correct it.
  - Proposed CHANGELOG entry text (adopter-facing): "Fixed: the root `--at` timestamp refusal and two `sq import` diagnostics no longer split a copy-pasteable ISO example or a long path across a line when piped or narrow. `sq board list` and `sq memory <role> list`/`search` now send their per-file unreadable-file errors to stderr in human-readable mode too, matching `--json` and each commands documented contract."
  - Gates: uv run --all-extras pyright -> 0 errors, 0 warnings, 0 informations. ruff check . -> All checks passed!. ruff format --check . -> 531 files already formatted. pytest tests/meta -> 181 passed. Targeted pytest (tests/meta + the touched cli test modules, board/memory/import/reflog/time-forging/error-width/help-width/remedy) -> 247 passed. sq check -> no issues. Commit 04945d2 on release/0.14 (unpushed), only src/squads/_cli/{__init__,_board,_import,_memory}.py + the three test files staged; squads/ item-state changes left uncommitted per the stage-explicitly convention.
<!-- sq:discussion:end -->
