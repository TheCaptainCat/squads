---
id: TASK-874
sequence_id: 874
type: task
title: Refuse an empty --parent on the create path as update does
status: Done
author: tech-lead
assignee: python-dev
priority: low
refs:
- BUG-871:fixes
description: Three sites in the create path discard an empty --parent and report success;
  the update door refuses it. Collapse them onto one shared resolution helper.
created_at: '2026-09-02T09:58:45Z'
updated_at: '2026-09-02T14:01:28Z'
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
- [2026-09-02T13:20:33Z] Elias Python:
  - Fixed in `_cli/_create.py`. All three sites now call one shared helper, `_resolve_parent_option(parent, svc)` — the built-in `_make` command, the lazily-built `_build_create_cmd` command for override-declared types, and `create_guide`. It returns `None` only for `parent is None`, refuses empty/whitespace-only, and otherwise delegates to `resolve_item_id_any`. No `if parent else None` remains in the file.
    
    Message, and why it is not the update door's: `--parent needs an item ID; omit --parent to create without a parent`. The leading sentence is byte-identical to update's, so the two doors agree on what is wrong; the remedy after the semicolon is per-door. Copying update's `use --no-parent` would name a flag `sq create` does not accept — on this door omitting `--parent` *is* how a parentless item is made, so that is what it says. It fits one line at the pinned 80-column width, and the tests normalise whitespace anyway so a narrower console cannot break them.
    
    Red first, on the pre-fix source (my change stashed, the test file present): **10 failed, 5 passed**. Every door was observed accepting the empty value and creating the item — `assert 'omit --parent' in 'created GUIDE-2 → …/GUIDE-000002-guide-door.md'`, and on the shared-refusal test `AssertionError: created FEAT-4 → … assert 0 != 0 where 0 = <Result okay>.exit_code`. The 5 that passed pre-fix are the regression guards (omitting `--parent` still creates a parentless item; a real parent still resolves), which is the right shape.
    
    Test: `tests/cli/test_an_empty_parent_value_is_refused_on_every_create_door.py`, 15 cases, all through the CLI. Parametrised over the three doors × `""` and `"   "`; asserts exit non-zero, no `created` line, an unchanged corpus read back through `sq list -a --json`, that the id parser did *not* answer (`no item with number` absent), that `--no-parent` is absent from the create message and `--parent` named, that omitting the flag still creates parentless on all three doors, that full-ID and bare-number parents still resolve, and that create and update lead with the same sentence while keeping different remedies. The corpus is read through `invoke`, not the `svc` fixture: `svc` is built before the override declares the custom type, so its spec no longer describes what it would read. No existing test was touched.
    
    Suite, both numbers, run once each and read off the summary line. Baseline with my change stashed and the test file moved aside: **1 failed, 4536 passed, 12 skipped**, the failure being `test_every_tree_form_returns_on_a_cyclic_corpus_cli`. With my change: **5 failed, 4547 passed, 12 skipped** — the delta of 15 is exactly my new cases. None of the 5 are mine, and I attributed them rather than asserting it: the two `test_json_output_shape` tree goldens reproduce with my change removed on the same tree, and the three `test_status_role_colour` TUI cases pass in isolation alongside my file. All five sit on the tree/TUI surfaces another agent was editing live during the runs; the baseline's own failure was fixed under me in the same window.
    
    Gates: `pyright` 0 errors on both my files, `ruff check` and `ruff format --check` clean on them, `sq check` clean. Repo-wide `ruff check` reports one E501 in `_specmerge.py`, which is another agent's in-flight edit, not mine.
    
    Out-of-scope shape noticed while in the file, recorded not widened, per the task: `--assignee` carries the identical truthiness test on all three create commands (`resolve_slug_or_raise(assignee, svc) if assignee else None`), and `sq … update` has the same one. `sq create feature "…" --author manager --assignee ""` exits 0 and creates the item unassigned. Milder than the parent case — there is no second door disagreeing, since update behaves the same way — but it is the same class. `--author ""` is already safe: it reaches the slug resolver and is refused at exit 1. The guide-only `--tech ""` also drops silently.
    
    One thing to correct in the brief, from me not from the tech lead: while probing option shapes I ran two `sq create` calls against the repo squad instead of my scratch squad and created four throwaway items (FEAT-886/887, GUIDE-888/889). I removed the four files and ran `sq repair` — 857 items, counter held at 889, so no number was reused and nothing else moved. `sq check` is clean and the other agents' in-flight items are untouched. Flagging it rather than leaving it to be found.
<!-- sq:discussion:end -->
