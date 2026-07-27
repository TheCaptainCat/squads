---
id: TASK-677
sequence_id: 677
type: task
title: Undecodable files and stale item paths fail cleanly
status: InProgress
author: tech-lead
refs:
- BUG-675:fixes
- BUG-676:fixes
description: Guard the UTF-8 decode in the shared read helper and the config reader,
  and convert the interrupted-rename FileNotFoundError at the item-read seam — without
  breaking the two callers that use it as control flow.
subentities:
- local_id: ST1
  title: Decode guard in the read helper and the config reader
  status: Todo
- local_id: ST2
  title: Stale-path guard at the item-read seam
  status: Todo
- local_id: ST3
  title: CLI-layer tests and the two control-flow regressions
  status: Todo
created_at: '2026-07-27T22:44:54Z'
updated_at: '2026-07-27T22:46:29Z'
---
<!-- sq:body -->
Two read-path defects that still produce raw tracebacks after the parse guards landed. Same family,
one pass: a file `sq` cannot decode, and an item file that is not where the index says it is.

Fixes BUG-675 and BUG-676. Read both first — each has a reproduction.

## The two defects

**Undecodable bytes (BUG-675).** The parse guards wrap YAML and TOML *parsing*; decoding happens one
layer below. `_aio.read_text` calls `Path.read_text(encoding="utf-8")` unguarded, and
`_paths.load_config` hits the same failure inside `tomllib.load`'s own `b.decode()` — before the TOML
grammar is reached, so the existing `except tomllib.TOMLDecodeError` never sees it. One stray `0x80`
byte produces a raw `UnicodeDecodeError` traceback out of `check`, `repair`, `board list`, and — when
the byte is in `.squads.toml` — out of *every* command, since config resolution runs before dispatch.

**Stale item path (BUG-676).** An interrupted title-changing update leaves the file at its new path
while the index still names the old one. Anything resolving through `item_file` and then reading —
`show --full`, `comment`, body reads — raises a raw `FileNotFoundError` until `sq repair` runs.

**The skew itself is sanctioned**, documented in `_services/_retype.py::_apply_type_change` and in
ADR-663 §1's retype/rename row. The defect is the raw traceback as the user-facing result, not the
state that produces it. Nothing here changes the write path or the skew direction.

## Fail clean, do not fall back

For BUG-676 the tempting fix is to re-resolve on miss — find the item by sequence number in its type
folder. Rejected:

- `check` can afford a fallback because it already holds a full disk scan. Every other caller
  (`_base.py`'s section-mutate and role-body reads, `_collab.py`, `_subentities.py`, `_items.py`'s
  show and body paths) would need a bespoke directory scan bolted onto a single-item read, for a
  state whose resolution is already one command away.
- Re-resolving papers over the one signal that tells an agent a mutation was interrupted at all. That
  is the same tension ADR-663 cites when it refuses to disguise a real inconsistency: a loud,
  repairable state beats a quiet self-correction.

So both defects get the shape BUG-669 established: a `SquadsError` naming the file or item and
pointing at the fix.

## Where the guards go — and the one place they must not

Derive the call-site list from a fresh grep (`grep -rn "read_text(" src/` and
`grep -rn "item_file(" src/`), not from the bug bodies. What that showed when this was written:
46 `_aio.read_text` call sites and 37 `item_file` call sites across `_services/`, `_index/`,
`_memory/`, `_board/`, `_overrides/` and the migration runners.

**The decode guard belongs in `_aio.read_text`** — one guard, every reader covered, and nothing in
the codebase catches `UnicodeDecodeError`, so converting it breaks no caller. `_paths.load_config`
needs its own, since it reads binary and never goes through the helper.

**The not-found guard must NOT go in `_aio.read_text`.** Three existing callers depend on
`FileNotFoundError` as control flow, and converting it in the shared helper breaks all three:

- `_services/_maintenance.py`, the confirm round — catches `FileNotFoundError` at the fresh index's
  path and *falls back to the path the scan found*, then catches it again to skip a genuinely gone
  candidate. That fallback exists for precisely BUG-676's state. Convert the exception in the helper
  and `sq check` starts crashing on the interrupted-rename board this task is meant to make friendly.
- `_services/_import.py`, the pre-pass skew guard — catches it to defer the claim to `sq check`
  rather than fail the import.

Those two are the reason this is not a one-line change in the obvious place. The not-found guard goes
at the **item-read seam in the service layer** — the paths BUG-676 names, where the exception escapes
to the user today — leaving `_aio.read_text` to propagate `FileNotFoundError` unchanged for callers
that read it as a signal. Any new guard must keep both call sites working exactly as they do now.

**One caller needs its own message, not the generic one.** `IndexStore.load` wraps a corrupt index
with "corrupt index …; run `sq repair` to rebuild it from the markdown files" — but it catches only
`ValidationError`, so an undecodable `.squads.json` would bypass it and surface the generic decode
message instead, losing the actionable remedy. Preserve the index's own wording for that case.

**And the repair pointer is not universally right.** "Run `sq repair`" is correct for an item file;
it is wrong advice for a missing `.squads.toml`, an override template, or a backend artifact. Do not
attach it to a blanket handler — the hint belongs where the read is known to be an item read.

## Out of scope

- **Recovery or re-resolution.** No fallback scan, no lenient decode, no `errors="replace"`. The user
  fixes the file or runs `sq repair`; `sq` says which and why.
- **The write path and the skew direction.** Both unchanged.
- **Per-file degradation on listing reads.** See the note below — it is a real follow-up, not this.

## Sequencing

Lands after the in-flight visibility refactor, which touches the mixins, `_index/_store.py`, `_cli/`
and `_retype.py` — the same functions this edits. Nothing here depends on that work logically; it is
collision avoidance.

## Acceptance

Pinned at the **CLI layer**, as the earlier read-path work established. A test asserting only
`pytest.raises(SquadsError)` would pass while the CLI still printed a traceback.

- An item `.md`, a board notice and a memory entry each containing an invalid byte produce a clean
  `error: …` line naming the file and the documented exit code from the commands that read them.
- **`.squads.toml` with an invalid byte** produces the same clean shape from an ordinary command —
  this is the case that otherwise breaks every command, including the diagnostic ones.
- An interrupted rename leaves `show --full`, `comment` and the body-read paths failing with a clean
  error naming the **item** and pointing at `sq repair`; after `sq repair`, all of them work again.
- Output contains no `Traceback`, no `site-packages`, no `UnicodeDecodeError`, no
  `FileNotFoundError`. Assert the absence explicitly — that is the regression, and only an explicit
  assertion catches it if someone later re-raises the underlying error.
- An undecodable `.squads.json` still reports the corrupt-index message with its `sq repair` remedy,
  not a generic decode error.
- The confirm round's stale-path fallback and the import pre-pass's missing-file skip both still
  behave exactly as they do today — pinned by test, because they are what a blanket guard would
  silently break.
- Exit codes asserted on a bare invocation (`cmd >/dev/null 2>&1; echo $?`); a pipeline masks them.
- A clean board is byte-identical in output and exit code to before.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 677 add-subtask "<title>"`; track with `sq task 677 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Decode guard in the read helper and the config reader |  |
| ST2 | Todo |  | Stale-path guard at the item-read seam |  |
| ST3 | Todo |  | CLI-layer tests and the two control-flow regressions |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Decode guard in the read helper and the config reader

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
The decode guard: one place for every reader, plus the two that bypass it.

**`_aio.read_text`.** Catch `UnicodeDecodeError` and raise a `SquadsError` naming the file. This is
the shared helper every read in the product goes through, so one guard covers item files, board
notices, memory entries, override templates, the reflog and the migration runners at once. Safe to
convert here: a fresh `grep -rn "except UnicodeDecodeError" src/ tests/` returns nothing, so no
caller reads that exception as a signal.

Include enough of the decoder's own detail to be actionable — the byte and its offset are what let
someone find it in an otherwise-normal-looking file.

**`_paths.load_config`.** Reads binary and hands the bytes to `tomllib.load`, which decodes
internally, so it never touches `_aio.read_text` and its existing `except tomllib.TOMLDecodeError`
never fires — decoding fails before the grammar is reached. Add `UnicodeDecodeError` to what it
handles, with the same message shape the other TOML loaders use. This is the highest-value single
line in the task: config resolution runs before command dispatch, so without it every command fails
with a traceback, including the ones an operator would run to diagnose it.

**`IndexStore.load` keeps its own message.** It wraps a corrupt index with "corrupt index …; run
`sq repair` to rebuild it from the markdown files", but catches only `ValidationError`. An
undecodable `.squads.json` would now surface the generic decode message and lose that remedy —
which is the one piece of advice that actually resolves it. Make the decode case reach the same
wording.

Acceptance:
- An invalid byte in an item file, a board notice or a memory entry raises a `SquadsError` naming
  the file, from a single guard rather than per-call-site handling.
- An invalid byte in `.squads.toml` raises a `SquadsError` matching the other TOML loaders' shape.
- An invalid byte in `.squads.json` reports the corrupt-index message and its `sq repair` remedy.
- The message carries the decoder's byte/offset detail.
- A valid file reads exactly as before; no signature change visible to existing callers.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Stale-path guard at the item-read seam

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
The stale-path guard — at the item-read seam, deliberately not in the shared helper.

An interrupted title-changing update leaves the file at its new path with the index still naming the
old one. `item_file` is a pure path builder (`sp.abspath(item.path)`) and never touches the
filesystem, so it cannot be the place that raises; the `FileNotFoundError` comes from the read that
follows it.

**Do not put this guard in `_aio.read_text`.** Three call sites depend on `FileNotFoundError` as
control flow and a blanket conversion breaks them:

- `_services/_maintenance.py`, the confirm round: it catches `FileNotFoundError` at the fresh index's
  path, falls back to the path the scan actually found the item at, and catches it a second time to
  skip a genuinely gone candidate. That fallback exists for exactly this bug's state — convert the
  exception underneath it and `sq check` starts crashing on an interrupted-rename board.
- `_services/_import.py`, the pre-pass skew guard: catches it to defer the claim to `sq check`
  instead of failing the whole import.

Both must keep behaving exactly as they do today. Verify with a fresh
`grep -rn "except FileNotFoundError" src/` before starting — if the refactor in flight has added
more, they are all in the same category.

**Where it goes instead:** the item-read paths where the exception escapes to the user — `_items.py`
(show/body/discussion reads), `_base.py` (the section-mutate core and the role-body read),
`_collab.py`, `_subentities.py`. Derive the list from `grep -rn "item_file(" src/` and cover the
ones that read; the ones that only build a path to write are not in scope.

Prefer a single small read-an-item-file helper those seams share over a `try`/`except` repeated at
each — one message shape, and a new read path cannot forget it.

**The message names the item, not just the path**, and points at `sq repair`. That pointer is
correct here because the read is known to be an item read; it would be wrong advice for a missing
override template or backend artifact, which is the other reason this does not belong in the shared
helper.

Acceptance:
- After an interrupted rename, `show --full`, `comment` and the body-read paths fail with a clean
  error naming the item and pointing at `sq repair`; after `sq repair` all of them work again.
- `_aio.read_text` still propagates `FileNotFoundError` unchanged.
- The confirm round's two-step fallback and the import pre-pass's skip are unchanged in behaviour.
- Index-only verbs (`sq list`, plain `show`) keep working throughout, as they do today.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — CLI-layer tests and the two control-flow regressions

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
CLI-layer tests, plus the two regression guards a blanket fix would trip.

**Fixtures.** Corruption by insertion, not truncation — these are intact files with bad content:

- an item `.md`, a board notice and a memory entry, each with a single invalid byte (`0x80`) in
  otherwise-normal prose;
- a `.squads.toml` with the same;
- a `.squads.json` with the same;
- an interrupted-rename board: the item file at its new path, the index still naming the old one.

**Per command, through the CLI.** For each corrupt input, drive the commands that read it and assert
a single clean `error: …` line naming the file or item, and the documented exit code. For
`.squads.toml`, any ordinary command will do — the failure happens in resolution, before dispatch,
which is exactly what makes it the worst case.

**Assert the absence, not just the presence.** Check the output contains no `Traceback`, no
`site-packages`, no `UnicodeDecodeError` and no `FileNotFoundError`. The message being right does not
prove the traceback is gone, and a later change that re-raises the underlying error would pass a
presence-only test.

**The two regressions a blanket guard would cause** — these matter more than the happy path, because
they are silent:

- the confirm round's stale-path fallback: on an interrupted-rename board that *also* carries a real
  status drift, `sq check` must still confirm and report that drift, having found the file at the
  scan's path rather than the index's. If this test fails, the not-found guard was placed in the
  shared helper.
- the import pre-pass's missing-file skip: an import targeting an item whose file is absent must
  still plan, deferring the claim, rather than failing.

Both existed before this task and neither is obviously connected to it, so state in a comment on each
what it is protecting — otherwise the next person to touch the read helper will delete the coupling
without knowing it was load-bearing.

**Exit codes and the clean board.** Exit codes asserted bare (`cmd >/dev/null 2>&1; echo $?`) — a
pipeline masks the status. A clean board produces byte-identical output and exit codes to before,
across the same commands.

Name tests by the behaviour they pin, never by a ticket id.

**Changelog.** One adopter-facing line under the unreleased section: a file `sq` cannot read, and an
item whose file has moved out from under the index, now report a clear error naming what is wrong
instead of failing with a stack trace. Adopter wording only — no ticket ids, no repo-process detail,
nothing about the internal helpers.

Acceptance:
- Every corrupt input above produces a clean, named error through the CLI with the right exit code.
- No output contains a traceback, a venv path, or either exception name.
- Both regression tests pass and carry a comment explaining what they protect.
- Exit codes asserted bare; clean board unchanged.
- Full suite green under `uv run --all-extras`; run it once, redirect to a file, and read the file
  rather than re-running to reslice output.
- CHANGELOG updated in the unreleased section.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T22:45:41Z] Olivia Lead:
  - Cut for BUG-675 + BUG-676 as one pass — same read-path family, same functions. Fail-clean is carried with QA's reasoning against the re-resolve fallback (only check can afford it; every other caller would need a bespoke directory scan for a state one command away; and re-resolving hides the only signal that a mutation was interrupted).
  - IMPORTANT design correction, found by grep rather than from the bug bodies: the not-found guard must NOT go in _aio.read_text. Three call sites already depend on FileNotFoundError as control flow — _services/_maintenance.py's confirm round catches it twice (falling back to the path the scan found, which exists for exactly BUG-676's state), and _services/_import.py's pre-pass catches it to defer the claim to sq check. A blanket conversion in the shared helper makes sq check crash on the very interrupted-rename board this task is meant to make friendly. The decode guard IS safe there (nothing catches UnicodeDecodeError); the not-found guard goes at the item-read seam in the service layer. Also note item_file is a pure path builder and never raises — 'at or below item_file' is not a place that exists.
  - Two more: an undecodable .squads.json would bypass IndexStore.load's ValidationError-only catch and lose the 'corrupt index — run sq repair' remedy, so that wording must be preserved for the decode case; and a blanket 'run sq repair' hint is wrong advice for a missing .squads.toml, override template or backend artifact, so the pointer belongs only where the read is known to be an item read. Both are in the body, and the two control-flow callers are pinned by regression tests in ST3.
<!-- sq:discussion:end -->
