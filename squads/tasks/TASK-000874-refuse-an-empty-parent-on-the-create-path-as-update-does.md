---
id: TASK-874
sequence_id: 874
type: task
title: Refuse an empty --parent on the create path as update does
status: Ready
author: tech-lead
assignee: python-dev
priority: low
refs:
- BUG-871:fixes
description: Three sites in the create path discard an empty --parent and report success;
  the update door refuses it. Collapse them onto one shared resolution helper.
created_at: '2026-09-02T09:58:45Z'
updated_at: '2026-09-02T10:02:45Z'
---
<!-- sq:body -->
## What is wrong

`sq create <type> "…" --parent ""` exits 0 and creates the item with no parent. The
empty value is neither honoured nor refused — it is discarded, and a plain success is
reported. A caller who supplied a parent gets an item without one and is told the
command worked; the only way to notice is to read the item back.

The two write doors disagree on the same argument. `update --parent ""` refuses at
exit 1. `create --parent ""` accepts at exit 0.

## Mechanism

`src/squads/_cli/_create.py` tests the option for truthiness before resolving it, so an
empty string takes the no-parent branch instead of reaching the id parser. Three sites
carry the identical expression — the expression is the stable identifier, the line
numbers move:

    resolved_parent = await resolve_item_id_any(parent, svc) if parent else None

## The reference shape, and why a one-token change is not the fix

`src/squads/_cli/_items.py`'s `update` was fixed and is the shape to match. It is three
cooperating pieces, not one:

- the mutual-exclusion guard tests `parent is not None`, so `--parent "" --no-parent` is
  still caught as a conflict rather than silently collapsing to one branch;
- an explicit refusal of an empty or whitespace-only value, with its own message;
- the resolution itself, testing `parent is not None`.

Flipping the ternary to `parent is not None` on its own is **not** the fix: it sends `""`
into the id parser and surfaces whatever that parser says about an empty string, which is
not the message the update door gives. The doors must agree on the message and the exit
code, not just on the refusal.

One wording caveat to settle rather than copy blindly: `create` has no `--no-parent` —
omitting `--parent` is how a parentless item is made. The update door's sentence points at
a flag that does not exist here. Render the create-side message and read it before
committing to it.

## What to do

Collapse the three sites onto a single shared resolution helper rather than making the
same edit three times. Three parallel edits leave the class exactly where it is — the
next create-shaped command copies whichever site it sits nearest. One helper that takes
the raw option and returns a resolved parent or refuses gives all three commands one
behaviour, one message, and the test one seam.

## Out of scope

- `_cli/_items.py`. The update path is correct. Do not harmonise it toward create.
- Any other truthiness-shaped option you notice on the create path while you are in the
  file. Record it in a comment on this task; do not widen the change.

## Acceptance

- `--parent ""` exits 1, writes nothing, and prints a message naming `--parent`. Driven
  on **each** of the three commands the expression appears on, not on one of them.
- `--parent "   "` (whitespace only) behaves identically to empty.
- Omitting `--parent` still creates a parentless item at exit 0. This is the regression
  the fix can plausibly cause; assert it.
- A valid `--parent` still resolves, including through a short/alias form of the id.
- Exit codes are read from bare invocations (`cmd >/dev/null 2>&1; echo $?`), never
  through a pipe — a pipeline reports the last element's status, not the command's.
- **The test fails before the fix.** On the pre-fix tree it must observe exit 0 and a
  created parentless item. Run it red first and say so in the handoff comment, with what
  it printed.
- Name the test by behaviour. No ticket identifier in a test name, a file name, or a
  source comment.
- `uv run --all-extras pytest`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .` and `sq check` all clean. `--all-extras` is
  required on each; a bare `uv run` prunes the optional tui extra and pyright then reports
  hundreds of false import errors.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 874 add-subtask "<title>"`; track with `sq task 874 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T10:02:45Z] Olivia Lead:
  - Scoped from BUG-871 and dispatchable. Small and standalone: it shares no file, layer or test with the other two 0.14 bugs. The one thing not to skim is that the reference fix on the update door is three pieces, not one — flipping the ternary alone gives a different message than the door it is meant to match.
  - @python-dev ready for dispatch.
<!-- sq:discussion:end -->
