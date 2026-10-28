---
id: TASK-1199
sequence_id: 1199
type: task
title: Fix the CLI surface test review findings
status: Done
parent: FEAT-1173
author: tech-lead
assignee: python-dev
refs:
- REV-1198:addresses
description: Harness, guard, roster-fold, marker and portability fixes for the REV-1198
  findings
subentities:
- local_id: ST1
  title: 'Harness and guards: F1-F5, F15'
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST2
  title: 'Roster folding: F6'
  status: Done
  assignee: python-dev
  story: US6
- local_id: ST3
  title: 'Markers and assertions: F12, F16, F13 docstrings'
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST4
  title: 'Pinned bugs and portability: F7-F11'
  status: Done
  assignee: python-dev
  story: US7
- local_id: ST5
  title: Fix review findings F18 and F19
  status: Done
  story: US1
- local_id: ST6
  title: Fix Windows CI failures in init, memory, role, repair tests
  status: Done
  story: US7
created_at: '2026-10-27T23:53:34Z'
updated_at: '2026-10-28T01:02:47Z'
---
<!-- sq:body -->
## Goal

Fix the REV-1198 findings the manager triaged as Fix: F1 to F12, F15 and F16, plus the F13 docstrings. Test and harness changes only: no production code changes. F14 is an ADR-1172 rule 5 amendment owned by the architect and is not in this task; F17 is Noted.

## Ground rules

- Every harness or guard fix is shown red on the reviewer's seeded defect before it is called done: reapply the seed the finding body describes, see the guard or test fail, revert the seed. Report each seed and its red output in the handback.
- Every new or changed test is mutation-checked: break the effect it asserts, see it red, restore. `git diff src` is empty at handback.
- No test pins buggy behaviour. Where today's output is a known bug, assert only what is correct, or leave the shape to the bug's own regression test.
- Test names describe behaviour; no ticket IDs in code, names or docstrings. Docstrings one or two sentences, no build-process words.

## Harness and guards (F1, F2, F3, F4, F5, F15)

- F1: `create guide` is a hand-written command, so it must not fold onto `create <type>`. Give it its own key (or fold only commands the builder mounts, telling them apart by command class as `create_problems` already does), then cover its pairs in their own right: `--desc`, `--parent`, `--assignee`, `--json` and the rest. Acceptance: the reviewer's seed in `create_guide` (description emptied, parent and assignee dropped, `--json` branch disabled) turns tests red.
- F2: the coverage and parity guards walk hidden commands too; aliases still fold onto their keys; any deliberate exclusion is named in `EXCLUDED_PARAMS` with its reason. Test the hidden `role|skill|operator <slug> rm` (`--purge`, `--as`). Acceptance: a seeded hidden `wipe --everything` command fails the coverage guard.
- F3: a `covers` marker counts only on a collected `test_*` function (or a module `pytestmark`) that carries no skip, skipif, xfail or slow marker; either in the guard or refused at collection by the conftest hook. Acceptance: `@pytest.mark.skip` under the `covers("sync")` markers in `test_sync.py` fails the guard.
- F4: `reached_pairs` counts an argument only when it has a value (not `None` or `()`), and stops at an eager `--help`. Add both shapes (a missing argument, options after `--help`) to the cross-check meta cases. Acceptance: the new meta cases are red against the old `reached_pairs`.
- F5: the parity guard compares a parameter signature (kind, `required`, `is_flag`, `multiple`, `nargs`, `hidden`, default), not the name only; exclude only what the spec legitimately varies (such as a field option's choices). Acceptance: the reviewer's seeds on `bug show --json` (required, non-flag, multiple, hidden) and on `bug status --force` (default `True`) each fail the guard.
- F15: delete the dead `owner()` in `tests/_cli_surface.py`; `KIND_SEGMENTS` stays.

## Roster folding (F6)

- Fold the roster verbs shared by one registrar (`status`, `body`, `remove`, and the `comments` listing) onto one key, keep one host's tests, delete the duplicated tests on the other hosts.
- Extend the parity guard over the roster hosts, so a drift on `skill` or `operator` fails it.
- Where a host really differs (`refresh_managed=True` on role and operator `remove`), test that difference by name.
- Acceptance: the duplicate tests are gone; a seeded parameter drift on one roster host's shared verb fails the parity guard; the coverage guard still passes.

## Markers and assertions (F12, F16, F13 docstrings)

- F12: replace the prefix-only asserts with whole-output asserts (test_skill.py :381 and :899, reusing the role module's refusal text; test_import.py:161; test_init.py :241 and :255, using `flat()` for the panel).
- F16: one `covers` marker per asserted parameter; multi-parameter markers stay only on named interaction tests (parent/no-parent, add-label/rm-label, onto/by, ...).
- F13: keep the seven refusal-only cases; each test gets a one-line docstring stating that no effect is reachable under the bundled spec and the refusal is the case. No guard change.
- Acceptance: no `startswith` assert on CLI output remains in `tests/cli`; every multi-parameter marker sits on a test named for an interaction.

## Pinned bugs and portability (F7, F8, F9, F10, F11)

- F7: in `test_repair.py`, drop the repair-output assertion that pins the silent drop (4 items rebuilt from 5 files); keep the `sq check` `numbers_unique` half.
- F8: in `test_memory.py`, give the memory a body distinct from its summary, so the search case asserts the intended single hit.
- F9: build the expected `init` and `adopt` panel paths with `str(root / folder)` and `str(root / folder / ".squads.json")`, not `/` joins.
- F10: pass `encoding="utf-8"` to every `read_text()` of a generated file in `tests/cli` (the helpers and call sites listed in the finding); optionally run tests with `-W error::EncodingWarning`.
- F11: `test_docs_ui.py` must collect without the `tui` extra: import the app inside the `ui` tests after `pytest.importorskip("textual")`, or patch by dotted string.
- Acceptance: `rg 'read_text\(\)' tests/cli` returns nothing for generated files; `test_docs_ui.py` collects in an environment without `textual` (show it, e.g. by blocking the import); the F7/F8 tests stay green and no longer encode the bug output.

## Gates

```bash
uv run --all-extras pyright
uv run --all-extras ruff check src tests
uv run --all-extras ruff format --check src tests
uv run --all-extras pytest tests/meta tests/cli -n 3
~/.local/bin/sq check
```

The main loop runs the full suite.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1199 add-subtask "<title>"`; track with `sq task 1199 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Harness and guards: F1-F5, F15

<!-- sq:subtask:ST1:body -->
F1, F2, F3, F4, F5 and F15 from REV-1198: `create guide` gets its own key and tests, the guards walk hidden commands (roster `rm` tested), covers markers count only on runnable tests, `reached_pairs` counts supplied arguments only and stops at `--help`, parity compares parameter signatures, and the dead `owner()` goes. Done when each fix is red on the reviewer's seed and green after; see the task body for each seed.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Roster folding: F6

<!-- sq:subtask:ST2:body -->
F6 from REV-1198: fold the shared roster verbs (`status`, `body`, `remove`, `comments`) onto one key, keep one host's tests, delete the duplicates, and extend the parity guard over `role`, `skill` and `operator`. Test the `refresh_managed` difference on role and operator `remove` by name. Done when a seeded drift on one roster host fails the parity guard.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Markers and assertions: F12, F16, F13 docstrings

<!-- sq:subtask:ST3:body -->
F12, F16 and the F13 docstrings from REV-1198: whole-output asserts instead of prefixes, one covers marker per parameter outside named interaction tests, and a one-line docstring on each refusal-only test stating the bundled spec cannot reach the effect. Done when no `startswith` assert on CLI output remains in `tests/cli`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Pinned bugs and portability: F7-F11

<!-- sq:subtask:ST4:body -->
F7, F8, F9, F10 and F11 from REV-1198: drop the repair assertion that pins the silent drop, give the memory search case a distinct body, build expected init/adopt paths with `pathlib`, read generated files with `encoding="utf-8"`, and make `test_docs_ui.py` collect without the `tui` extra. Done when no test encodes known bug output and the module collects without `textual`.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Fix review findings F18 and F19

<!-- sq:subtask:ST5:body -->
F18: the import refusal test no longer pins line 2. F19: one addressing case each on operator and skill for the shared body, status and remove verbs.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Fix Windows CI failures in init, memory, role, repair tests

<!-- sq:subtask:ST6:body -->
Expected paths in the init, memory and role tests are built as the product prints them (str of a Path, repr of the path string for the OSError tail). The repair duplicate is a byte copy, so it stays an identical copy on every OS.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T00:18:41Z] `python-dev` Elias Python:
  - @manager ST1 to ST4 are Done and F1 to F12, F15, F16 are Fixed on REV-1198; F13 is Noted. Test and harness changes only: `git diff src` is empty.
  - Gates: pyright 0 errors, ruff check and format clean, `pytest tests/meta tests/cli -n 3` gives 1382 passed (was 1363), `sq check` clean.
  - Roster fold: role is the reference host (its remove also re-renders the managed roster section). body, remove, rm and status fold onto `role X`, comments onto `<host> comments`.
  - Not committed. The full suite is left to the main loop.
- [2026-10-28T00:30:08Z] `python-dev` Elias Python:
  - @manager ST5 Done: F18 and F19 Fixed. Gates: pyright 0 errors, ruff clean, tests/meta + tests/cli 1384 passed, sq check clean, git diff src empty.
- [2026-10-28T00:53:24Z] `python-dev` Elias Python:
  - @manager ST6 Done. Init path uses str(Path); memory and role errno tails use repr(str(path)). Repair: the test setup was the cause. It copied the task file with read_text/write_text, which turns LF into CRLF on Windows, so the copy was no longer byte-identical and the product (which refuses only identical copies or shared slugs) renumbered it. It now copies bytes; no product difference, no bug to file. Gates: pyright 0 errors, ruff clean, tests/meta + tests/cli 1384 passed, sq check clean, git diff src empty.
<!-- sq:discussion:end -->
