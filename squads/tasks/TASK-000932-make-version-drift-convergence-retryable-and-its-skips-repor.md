---
id: TASK-932
sequence_id: 932
type: task
title: Make version-drift convergence retryable and its skips reported
status: Done
parent: FEAT-906
author: tech-lead
assignee: python-dev
refs:
- ADR-880:implements
- REV-926:addresses
subentities:
- local_id: ST1
  title: Retry a skipped body-tag convergence instead of stamping past it (F13)
  status: Done
  story: US5
- local_id: ST2
  title: Stop schema_tuple crashing sync() on a prerelease squads_version (F14)
  status: Done
  story: US5
- local_id: ST3
  title: Report repair skips from sq migrate up (F15)
  status: Done
  story: US5
created_at: '2026-09-08T13:52:19Z'
updated_at: '2026-09-10T09:40:31Z'
---
<!-- sq:body -->
## Scope

Fixes REV-926 F13, F14, and F15 — three low-severity gaps in the same corridor: the
version-drift convergence `sync()` runs and the `skipped` channel it and `sq repair` share.
Grouped in one task because all three touch the same reporting/retry surface
(`_services/_maintenance.py::sync`/`_converge_body_tag` and their two CLI consumers,
`_cli/_migrate.py` and `_cli/_maintenance.py`/`_cli` `repair`), same owner, same increment.

### F13 — a skipped convergence is never retried, and `sq check` stays clean

`sync()` stamps `squads_version` unconditionally at the end of the run, whether or not
`_backfill_roster_body_tags` actually converged everything. A body the marker-shaped-content
guard refused is therefore never retried on a later `sync` — after the first run the config
reads the new version, so the drift comparison that triggers the backfill is false forever.
This is F1's own failure signature (a definition that does not render, `sq check` clean, `sq
sync` reporting success) reappearing through the one channel this feature added to close it.

Two closures named in review, pick one: don't stamp `squads_version` when the run reported
skips (so the next `sync` retries); or add the advisory F1 itself proposed — `sq check` flags a
role/permanently-system-skill body carrying neither its tag nor content. The retry approach is
simpler and directly closes the reachability gap without adding a new validator; prefer it
unless it conflicts with something in `_backfill_roster_body_tags`'s own contract (read it
first — this task doesn't mandate re-deriving that decision from scratch, just requires the
chosen fix to make a second `sync` actually retry a previously-skipped body).

**Acceptance, driven:** a body with marker-shaped content in `sq:body`; `sq sync` reports the
skip and stamps whatever it stamps; a second `sq sync` (nothing else changed) either retries and
reports the same skip again (if the guard still refuses it), or `sq check` now surfaces the
stuck state — either way, the operator is not left with a silent "success" that never revisits
the file.

### F14 — a non-numeric `squads_version` makes `sq sync` raise a bare `ValueError`

The version-drift trigger (`_services/_maintenance.py`, the `schema_tuple(__version__) >
schema_tuple(recorded_version)` comparison `sync()` added) uses `schema_tuple`
(`_models/_schema.py`), which raises `ValueError` on any non-integer segment. The CLI's own
drift notice (`_cli/_common.py::version_notice`) compares the same field with the tolerant
`version_tuple` (strips non-digits) and is what tells the operator to run the command that then
crashes. `_stamp_version` writes `__version__` verbatim, so any prerelease/dev/local package
version reaching this comparison reproduces it — not only a hand-edited config.

**This is the same exception class F4 was raised about, reintroduced at this new call site by
the commit that fixed F4** — note that in the fix's own commit message or PR description as a
pattern, not a coincidence, per standing instruction.

Two closures named in review: compare with `version_tuple` instead of `schema_tuple` (move
`version_tuple` down out of `_cli` so `_services` can import it without inverting the
`_cli → _services` layering — e.g. into `_models/_schema.py` beside `schema_tuple`, or another
dependency-free home); or guard the comparison and treat an unparseable stamp as drift with a
named `SquadsError` message. Prefer the tolerant-comparator move — it also fixes the *silent*
half of the bug (a prerelease version currently compares as "no drift" incorrectly in some cases
depending on which raises first; check this against the CLI's own tolerant behavior so `sq
sync`'s drift detection agrees with `sq check`'s notice about the same field).

**Acceptance, driven with a prerelease version string** (the shape that broke it, per REV-926):
a squad whose `.squads.toml` reads `squads_version = "0.14.0rc1"` — `sq sync` completes cleanly
(no traceback, no bare `ValueError`) or fails with a clean `SquadsError`, never the former.

### F15 — `sq migrate up` does not report the repair skips it collects

F4's fix threads a `skipped` channel from `_converge_body_tag` through `RepairResult`, and wires
it into `sq repair`'s own CLI output. `_cli/_migrate.py`'s `up` command reads
`run.repair.strip_notice()` and nothing else from the same `RepairResult` — a refused body-tag
convergence during a migration's trailing repair is printed nowhere, and `sq migrate up` exits 0
saying "migrated ... index rebuilt" even though a file was skipped. (`unreadable` has the same
gap on this path; it predates this change and is not this task's job to fix, but don't make it
worse.)

Fix: one loop over `run.repair.skipped` beside the existing `strip_notice()` printing, in
`_cli/_migrate.py`, using the same wording `sq repair` already prints for the same list. Whether
`sq migrate up` should also exit non-zero on a skip is a separate call (changes that verb's exit
contract) — out of scope here; reporting it is what's missing.

**Acceptance, driven:** a migration corpus (below the current schema stamp) with one file
carrying marker-shaped `sq:body` content; `sq migrate up` prints the skip (same message `sq
repair` prints for the identical input) instead of silence.

## Testing

Falsify every new/changed test both directions (revert, confirm red; restore, confirm green);
report both.

Test selection: grep `_backfill_roster_body_tags`, `schema_tuple`, `version_tuple`,
`RepairResult`, `strip_notice`, and `skipped` across `tests/`, plus the unconditional floor —
`tests/meta`, `tests/integration`, `tests/cli` — since this touches `_cli/_migrate.py`. Validate
any zero-hit grep against a known positive first (whitespace-collapsed scan, per the board's
line-wrap warning) before treating it as proof nothing else needs updating.

No docstring or message claiming a retry/report happens where the code doesn't actually make it
happen — this finding family exists because a prior release's own claims about this exact
mechanism didn't match what ran.

## Refs

Implements ADR-880. Addresses REV-926 F13, F14, F15.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 932 add-subtask "<title>"`; track with `sq task 932 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Retry a skipped body-tag convergence instead of stamping past it (F13)

<!-- sq:subtask:ST1:body -->
Don't let sync() stamp squads_version when _backfill_roster_body_tags reported skips, or add sq check's own advisory for the untagged/uncontent case F1 proposed — read _backfill_roster_body_tags's contract first and pick whichever keeps a second sync() actually revisiting a previously-skipped body.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-09-08T14:28:35Z] Elias Python:
  - Withheld the squads_version stamp when _backfill_roster_body_tags reports a skip (sync(), backfill_skipped guard) instead of adding a check finding — chose retry per the task's own preference; a second sync retries and re-reports the same skip until fixed. Driven + falsified (both directions).
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Stop schema_tuple crashing sync() on a prerelease squads_version (F14)

<!-- sq:subtask:ST2:body -->
Move the tolerant version_tuple down out of _cli/_common.py (e.g. beside schema_tuple in _models/_schema.py) so _services can use it in place of schema_tuple for the drift comparison, or guard the comparison with a named SquadsError. Drive with squads_version = "0.14.0rc1" — the exact shape that crashes today. Same exception class as F4, reintroduced by F4's own fix; note that in the commit.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-09-08T14:28:36Z] Elias Python:
  - Swapped schema_tuple for the tolerant version_tuple (reused from squads._util, already the dependency-free home _overrides uses — no move needed) on the squads_version/__version__ drift comparison. Audited the rest of the sync/migrate path for the same bare-exception shape: nothing else found (all other raises in _maintenance.py/_migrate.py are SquadsError; the other schema_tuple calls compare schema_version, which is hand-authored dotted-int and never carries a prerelease suffix). Driven with squads_version = '0.14.0rc1' + falsified.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Report repair skips from sq migrate up (F15)

<!-- sq:subtask:ST3:body -->
_cli/_migrate.py's up command reads only run.repair.strip_notice(); add a loop over run.repair.skipped beside it, same wording sq repair already prints for the same list.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-09-08T14:28:41Z] Elias Python:
  - sq migrate up now loops over run.repair.skipped with the identical wording sq repair prints, right after the existing strip_notice() print. Exit code unchanged (0) — the task scoped that decision out. Driven through the real CLI on a copy of the v0_11 corpus fixture with a marker-shaped skill body; bare exit code confirmed via uv run sq migrate up (no pipe). Falsified.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-08T14:29:02Z] Elias Python:
  - Handoff — F13/F14/F15, all in `_services/_maintenance.py` and `_cli/_migrate.py`.
    
    **F13 (visibility + retry).** `sync()` now withholds `_stamp_version` when its own
    `_backfill_roster_body_tags` call reported a skip; the drift comparison stays true, so a later
    `sync` retries the backfill and re-reports the same skip until the body is fixed. Chose the
    retry path over a new `sq check` finding: it's what the task's own text preferred, it's simpler,
    and it doesn't conflict with `_backfill_roster_body_tags`'s contract (its skip messages already
    feed `sync`'s own printed output via `_print_scaffold_warnings` — the CLI reproduction in the
    review already shows this). No new check finding, so no tier decision was needed. Visibility
    lives entirely in `sync`'s own repeating output, not `sq check`.
    
    **F14 (prerelease crash + same-shape audit).** Swapped `schema_tuple` for `version_tuple` on
    the `squads_version`/`__version__` drift comparison — the same tolerant comparator
    `version_notice()` already uses for this exact field. No move was needed: `squads._util`
    already carries a dependency-free `version_tuple` (the one `_overrides/_service.py` and
    `_overrides/_manifest.py` import), so `_services` now reuses that rather than duplicating it a
    third time. Audited every other raise this task's diff touches or sits beside on the same path
    for the bare-exception shape F4 was about: every raise in `_maintenance.py`/`_migrate.py` is
    already `SquadsError`; the two other `schema_tuple` call sites compare `schema_version`, a
    hand-authored dotted-int the package version never feeds, so they're a different field and not
    this bug. Nothing else on this path carried the shape.
    
    **F15 (reporting).** `sq migrate up` now loops over `run.repair.skipped` right after the
    existing `strip_notice()` print, with the identical wording `sq repair` uses for the same
    input (verified byte-for-byte against a live `sq repair` run on the same seeded fixture). Exit
    code is unchanged (0) — the task scoped that decision out explicitly; confirmed bare
    (`uv run sq migrate up; echo $?`, no pipe) against a real reproduction, not just the pytest
    `CliRunner` result.
    
    **Falsification.** All three: reverted the guard/comparator/loop, confirmed the exact tests
    that exercise it redden (F14's revert reproduces the review's own bare `ValueError` traceback
    verbatim), restored, confirmed green. The two pre-existing test modules for the F1/F4 work
    (version-drift backfill, marker-shaped-skip reporting) still pass unchanged — no regression.
    
    **Selection.** Grepped `_backfill_roster_body_tags`, `schema_tuple`, `version_tuple`,
    `RepairResult`, `strip_notice`, `skipped` across `tests/` (union of hits), plus the
    unconditional floor (`tests/meta`, `tests/integration`, `tests/cli`) and the extra service/
    unit/tui files the grep surfaced outside the floor — 2194 passed, 7 skipped, 0 failed. One
    failure surfaced and was fixed along the way: a finding-ID reference ("F4") in a new test
    docstring tripped `tests/meta`'s ticket-reference gate — reworded, reran clean. Validated the
    whitespace-collapsed scanner against a synthetic wrapped identifier (plain grep 0 hits, scanner
    1 hit) before trusting its own zero result over the new/changed files.
    
    `pyright`/`ruff check`/`ruff format --check` clean; `sq check` clean.
    
    Files: `src/squads/_services/_maintenance.py`, `src/squads/_cli/_migrate.py`,
    `tests/service/test_sync_withholds_the_stamp_after_a_body_tag_skip.py`,
    `tests/service/test_sync_tolerates_a_prerelease_squads_version.py`,
    `tests/cli/test_migrate_up_reports_repair_skips.py`.
    
    @tech-lead ready for review.
- [2026-09-08T14:35:41Z] Elias Python:
  - F15 follow-up, per coordinator: `sq migrate up` now exits 1 on the same condition `sq repair`
    does (`_cli/_main.py`: `if result.unreadable or result.skipped`), mirrored as
    `if run.repair and (run.repair.unreadable or run.repair.skipped): raise typer.Exit(1)` at the
    end of `migrate_up`. Included `unreadable` in the condition even though this command still
    prints only `skipped` (unchanged, out of scope) — the exit code answers "did the repair come
    back clean," not "did this command already explain every reason it didn't," and `unreadable`
    does reach this caller (the trailing repair walks the same corpus a bare `sq repair` would).
    Docstring now states the exit-code contract explicitly, same wording as `repair`'s.
    
    Guarded: only fires past the early `nothing to migrate` return, so `run.repair` is never `None`
    there — an already-current squad stays exit 0 unconditionally, never touches this branch.
    
    Verified bare, no pipe: `uv run sq migrate up >/dev/null 2>&1; echo $?` — 1 on a seeded
    marker-shaped skill body, 0 on a clean migration, 0 on the already-current "nothing to migrate"
    case. Added a subprocess-based test (against the installed `sq` script next to
    `sys.executable`, not `CliRunner`) for the same three cases, alongside the existing
    `CliRunner` ones. Falsified: reverted the `raise typer.Exit(1)`, both the `CliRunner` and the
    bare-subprocess skip-case tests reddened (returncode 0 instead of 1); restored, green.
    
    Re-ran the full migration-corpus suite (every historical schema fixture through
    `sq migrate up`) plus the `unreadable`-grep union outside the floor dirs — no regressions.
    `pyright`/`ruff check`/`ruff format --check` clean; `sq check` clean.
<!-- sq:discussion:end -->
