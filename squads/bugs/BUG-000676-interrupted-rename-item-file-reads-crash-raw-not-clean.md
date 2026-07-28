---
id: BUG-676
sequence_id: 676
type: bug
title: 'Interrupted rename: item-file reads crash raw, not clean'
status: Fixed
author: qa
severity: medium
refs:
- BUG-675
created_at: '2026-07-27T22:40:47Z'
updated_at: '2026-07-27T23:07:49Z'
---
<!-- sq:body -->
## Symptom

`sq bug/task/… show --full`, `comment`, `body`, and other verbs that need an item's file
content raise a raw, uncaught `FileNotFoundError` (full Python traceback) instead of a clean
error, when the item's most recent title-changing update or retype was interrupted before the
index committed. Plain `show` (no `--full`) and `sq list -a` are unaffected — they resolve
entirely from the index and never re-read the file.

## Scope note — the state is sanctioned, the crash is not

This is not a challenge to the durability model. `_services/_retype.py::apply_type_change`'s
own docstring and ADR-663's retype/rename row both name this exact state as the expected,
permitted outcome of the skew-direction rule: rename-then-write means a crash between the
move and the frontmatter rewrite leaves the item at its new path with the index still naming
the old one, and `apply_type_change`'s docstring says so explicitly, down to naming
`show`/`get` and `FileNotFoundError` by name. `sq repair` re-indexes from the file's new
location and fully recovers every time; nothing here disagrees with that. What's in scope is
narrower: the *result* of hitting that sanctioned state through the CLI today is a raw
traceback, not a clean, actionable error — the same user-facing symptom the read-path work
this release (BUG-669, BUG-675) exists to eliminate elsewhere.

## Root cause

Any caller that resolves `item_file(self.paths, item)` from an index-loaded `Item` and then
reads that path assumes the path is current. It usually is — but not in the window between an
interrupted title-changing update (`_services/_items.py::_update_core`) or retype
(`_services/_retype.py::apply_type_change`) physically moving the file and the transaction's
index commit, which never ran. `item_file` has no fallback and no existence check; the read
that follows it (a bare `_aio.read_text`) then hits a path that no longer exists.

`_services/_maintenance.py`'s `check()` confirm round (F10, REV-671) already had this exact
failure mode and was fixed: on a `FileNotFoundError` at the index's path, it falls back to the
path the file scan actually found the sequence number at (`on_disk[seq][1]`) before giving up.
That fix is local to the confirm round's own comparison loop — it did not touch `item_file` or
any of its other callers, so the same failure mode is still open everywhere else `item_file`
feeds a read: `_base.py` (comment/discussion appends, role-body reads, the shared
marker/section-mutate helper), `_collab.py`, `_subentities.py`, and `_items.py`'s own
`show`/body paths.

## Repro

Real fork+SIGKILL (not fault injection) against a throwaway squad on `release/0.12.2`,
monkeypatching only in the disposable script, calling the real `Service.update()`:

- Killed a title-changing `update(title=…, status=…)` right after the physical rename but
  before the frontmatter rewrite at the new path, and again after the frontmatter rewrite
  completed (both landed the file, non-truncated, at its new path with the index still
  pointing at the old one). In both cases:
  - `sq check` correctly reports the drift as a warn (F10 holds for detection) or, when only
    the path changed and status didn't, correctly reports nothing (nothing to detect — status
    drift is the only signal `check` compares, and it wasn't stale in that narrower case).
  - `sq <type> <n> show --full` and `sq <type> <n> comment --as … -m …` both raise
    `FileNotFoundError: [Errno 2] No such file or directory: …` (the item's *old* path) as an
    unhandled traceback, exit 1.
  - Plain `sq <type> <n> show` and `sq list -a` stay correct throughout (index-only).
  - `sq repair` re-indexes from the new path and fully recovers every time; every verb works
    cleanly again immediately after.

## Severity

Medium. Not data loss and not a detection gap (both already covered): `sq repair` always
recovers, and `check` already reports what it claims to. The severity is the raw-traceback UX
regression itself — reachable by the same ordinary interruption (background-stop, timeout,
OOM) as everything else in this release, on any command that touches the item's file rather
than just its index-derived metadata, until the next `sq repair`.

## Proposed fix

Two honest shapes, not a design decision made here:

- **Re-resolve on miss.** Mirror F10's own fix at the `item_file` boundary itself: on
  `FileNotFoundError` at the index's path, look the item up by its sequence number in the type
  folder it currently belongs to (a targeted directory scan, not the full board walk `check`
  already has in hand from its own pass) before giving up.
- **Fail clean instead.** Catch the `FileNotFoundError` at (or below) `item_file` and raise a
  `SquadsError` naming the item and pointing at `sq repair`, the same shape BUG-669/675 use for
  a malformed read. No re-resolution — the read seam converts an exception it already
  understands into a message instead of a traceback.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T23:07:26Z] Catherine Manager:
  - Correction to this bug's own scope, verified against HEAD before the fix: plain 'sq show' was NOT unaffected. _print_item_content in _cli/_common.py calls read_body unconditionally, so plain show read the file and crashed raw in this scenario too — the fix covers it. Only 'sq list -a' is genuinely index-only here.
<!-- sq:discussion:end -->
