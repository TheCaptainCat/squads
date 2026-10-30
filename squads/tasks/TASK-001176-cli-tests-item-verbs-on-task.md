---
id: TASK-1176
sequence_id: 1176
type: task
title: 'CLI tests: item verbs on task'
status: Done
parent: FEAT-1173
author: tech-lead
assignee: python-dev
refs:
- TASK-1174:depends-on
subentities:
- local_id: ST1
  title: update and its interactions
  status: Done
  maps_to: US3
- local_id: ST2
  title: show, status, body, retype, remove
  status: Done
  maps_to: US3
- local_id: ST3
  title: ref, refs, comments and view verbs
  status: Done
  maps_to: US3
created_at: '2026-10-27T21:35:09Z'
updated_at: '2026-10-28T01:02:40Z'
---
<!-- sq:body -->
## Scope

FEAT-1173 US3: the work-item verbs `build_item_app` mounts, tested on the reference type `task` in `tests/cli/test_item_verbs.py`, keyed `<type> …` (ADR-1172 rules 2-3): the group's `N` argument, `show`, `update`, `status`, `body`, `retype`, `remove`, `comments`, `ref add`/`ref rm`, `refs`, `view add`/`view disable`, with every option of each. Sub-entity and comment verbs are a separate task.

Rules that bite:
- Rule 1 interactions, each its own test named for the interaction: `--parent` with `--no-parent`, `--assignee` with `--clear-assignee`, `--add-label` with `--rm-label` on the same label, `--set` with `--unset` on the same attribute, `--priority` with `--no-priority`.
- Rule 2: `status` is tested on `task`'s lifecycle only, one allowed and one refused transition; per-type lifecycles are not surface.
- Modifiers (`--as`, `--json`, `--force`, `--yes`, `--append`) run the smallest write the verb accepts and assert their own effect.
- Other item types are held by the parity guard, never by repeated tests.

## Acceptance

- Every (verb, parameter) pair of the item group is declared once under the `<type>` key.
- Each interacting pair has a test named for the interaction.
- `--as` and `--json` are covered on every verb that declares them.

## Ground rules (every CLI surface task)

- Rulebook: ADR-1172. Read it before starting; the rules are cited here, not restated.
- In-process only: Typer `CliRunner` through the `runner`/`invoke` fixtures, on a squad copied per test (`copy_squad` and the builders in `tests/_squads.py`), under the frozen clock. No subprocess (ADR-1172 rule 4).
- One case per (command, parameter) pair where the value takes effect, plus its boundary refusals; combinations only for a genuine interaction, named for the interaction (rule 1). No cross-product or per-type parametrised tables (rules 1-2).
- Assert the exit code and the whole message line or JSON object, never a substring. Read state back through the CLI (`sq <type> <n> show --json` or the command's `--json` form); never open an item file or `.squads.json` (rule 5).
- Declare coverage with `@pytest.mark.covers("<key>", "<param>", ...)`, literal strings, keyed as ADR-1172 rule 3 says; an option is named by its first long flag, so `-m` is declared as `--message`. Hidden parameters are pairs too, each with a refusal test; `--as` is covered on every write command and `--json` on every command that declares it (op-pierre ruling on ADR-1172).
- Mutation-check each test when written: break the parameter's effect, see the test red, restore it. Record in the handback which effect you broke for each test.
- Names state the behaviour; no ticket IDs or process vocabulary in module, function or fixture names (the naming guards in `tests/meta` apply). Docstrings 1-2 sentences, present tense, no versions or history.

## Gate

`uv run --all-extras pyright`, `uv run --all-extras ruff check .` and `uv run --all-extras ruff format --check .` clean; `uv run --all-extras pytest tests/meta tests/cli -n 4` green; `~/.local/bin/sq check` clean for this task. The full suite is run by the main loop.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1176 add-subtask "<title>"`; track with `sq task 1176 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — update and its interactions

<!-- sq:subtask:ST1:body -->
Every update option on task, plus the named interaction tests: parent with no-parent, assignee with clear-assignee, priority with no-priority, add-label with rm-label on one label, set with unset on one attribute.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — show, status, body, retype, remove

<!-- sq:subtask:ST2:body -->
The group N argument and these verbs with every option; status with one allowed and one refused task transition; modifiers (--as, --json, --force, --yes, --append) on the smallest write each verb accepts.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — ref, refs, comments and view verbs

<!-- sq:subtask:ST3:body -->
ref add (with and without --kind) and ref rm, refs with --out/--in/--all/--json, comments --json, view add and view disable, each with its refusals.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-27T22:12:17Z] `python-dev` Elias Python:
  - - Handback: ST1-ST3 Done; gate green. `pytest tests/meta tests/cli -n 3`: `707 passed in 20.28s`; pyright 0 errors; ruff check and format clean; sq check clean. `git diff src/` empty; nothing committed.
    - Files: tests/cli/test_item_verbs.py (92 tests); tests/meta/test_every_cli_parameter_is_declared_by_a_covering_test.py (only the "<type>" line removed from PENDING). No shared fixture added.
    - Pairs: all 55 `<type> ...` (verb, parameter) pairs declared (N, update x17, show x4, status x3, body x6, retype x2, remove x4, ref add x3, ref rm x2, refs x4, comments --json, view add x2, view disable x2). Interactions each named: parent/no-parent, assignee/clear-assignee, priority/no-priority, add-label/rm-label (same label, rm wins), set/unset (same attribute: priority); also refs --out with --in, body -m with --file. `--as` covered on every verb declaring it with the reflog actor read back through `reflog --json`, plus an unknown-slug refusal each; `--json` on show, remove, refs, comments.
    - Mutation proofs (each run red, then restored; all 60 mutations RED): one effect broken per option at the CLI call site, e.g. update title/desc/author/status/force/parent/clear_parent/assignee/clear_assignee/priority/clear_priority/add_labels/rm_labels/set/unset set to None/False; apply_edit_actor skipped for each verb's --as; label add/rm order swapped in the service; the three update mutual-exclusion raises removed; show json/raw/comments/full flags forced off; status target replaced and force=False; body message/file/append/force dropped; retype target replaced; remove --yes prompt forced, force=False, json off; refs out/in/all/json altered; ref add target/kind replaced; ref rm target replaced; view add/disable name replaced; group N hardcoded. src restored after each (git diff src empty).
    - Notes: `--set`/`--unset` on task only reach the badge field `priority` (task declares no attributes), so the effects are tested through it. `task N refs --out` alone equals the default; its effect shows only next to `--in`, hence the separate interaction test.
    - Bugs/oddities (no tests, not fixed): (1) `sq task N ref rm TARGET` prints `removed TASK-N → TARGET` and exits 0 even when no such ref exists (`rm_ref` filters silently); expected an error or a "no such ref" message. (2) `body` refusal prints "(1 line)" but the code path uses plural-aware text only for the count, fine; no bug. (3) `ref add REV-4 --kind related` stores the bare ID (default kind elided), tests assert that.
    - @manager ready for review.
<!-- sq:discussion:end -->
