---
id: TASK-1174
sequence_id: 1174
type: task
title: 'CLI tests: covers marker, parity and coverage guards'
status: Done
parent: FEAT-1173
author: tech-lead
assignee: python-dev
subentities:
- local_id: ST1
  title: covers marker and invoke cross-check
  status: Done
  maps_to: US1
- local_id: ST2
  title: Verb-set parity guard
  status: Done
  maps_to: US1
- local_id: ST3
  title: Coverage guard
  status: Done
  maps_to: US1
- local_id: ST4
  title: tests/cli scaffold and fixtures
  status: Done
  maps_to: US1
created_at: '2026-10-27T21:35:07Z'
updated_at: '2026-10-28T01:02:38Z'
---
<!-- sq:body -->
## Scope

The foundation every other CLI surface task builds on (FEAT-1173 US1), as ADR-1172 rule 3 and its Consequences section name it:

1. **`covers` marker and the invoke cross-check.** Register `covers` under `[tool.pytest.ini_options] markers`. Extend the `invoke` fixture in `tests/conftest.py` (or a `tests/cli/conftest.py` override of it) so each call resolves its argument list against the live tree and records the (key, parameter) pairs it reached; at teardown, fail the test when a pair its `covers` markers declare was not reached. The check is local to the test, so `-k`, `--lf` and xdist stay valid.
2. **Verb-set parity guard** in `tests/meta` (ADR-1172 rule 2): every declared work-item type's verb set and per-verb parameter names equal the reference type `task`'s, minus what the spec decides (the `add-<kind>`/`<kind>`/plural verbs exactly when the type hosts a kind, `retype`/`remove` exactly when it is not roster, create-time attributes and kind-specific sub-entity options); every comment host exposes the same comment verbs with the same parameters. Expectations derive from the bundled spec; the guard stores no list of types.
3. **Coverage guard** in `tests/meta` (ADR-1172 rule 3): enumerate the tree with `_help_tree.command_nodes()` in an empty directory, hidden parameters included, fold each node onto its key; read every `covers` marker under `tests/cli/` with `ast`, without importing; fail on an undeclared pair and on a stale marker. Excluded: `--install-completion` and `--show-completion` only, as a named constant with one reason per entry.
4. **`tests/cli/` scaffold** and its shared fixtures, built on the module-scoped squad copied per test.

## Key folding details to settle in the guard

- `_help_tree` keeps the hidden `_addr` dispatcher node (e.g. `task comment _addr edit`, `role _addr update`). ADR-1172's own example key is `<host> comment edit`, so drop the `_addr` segment from keys; the dispatcher's argument (`HASH`, `<slug|id|n>`) belongs to the parent key (`<host> comment`, `role`).
- Item type names fold to `<type>`, sub-entity kinds to `<kind>` / `add-<kind>` / `<kinds>`, the segments up to a mounted comment group to `<host>`. The root callback is the empty key `""`. Roster groups (`role`, `skill`, `operator`) are not folded except for their comment group.
- A leaf with no parameters (`sync`, `ui`, `migrate up`, `workflow lint`, `role <slug> regen`, ...) has no pair, so the guard also requires every leaf key to be declared, written `covers("sync")` with no parameter (ADR-1172 rule 3).

## Acceptance

- Both guards pass on the tree, and fail on a seeded verb or parameter that is missing, stale or undeclared (shown red once each, recorded in the handback).
- A `covers` marker naming a pair its test does not reach fails that test at teardown; shown with a seeded test that is then removed.
- The guards and the cross-check stay valid under `-k`, `--lf` and xdist.
- `tests/meta` keeps passing, including `test_shared_flags_are_declared_once`, `test_squad_copies_are_isolated_in_any_order` and the naming guards.

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

_Add with `sq task 1174 add-subtask "<title>"`; track with `sq task 1174 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — covers marker and invoke cross-check

<!-- sq:subtask:ST1:body -->
Register the covers marker in pyproject.toml and extend the invoke fixture to record the (key, parameter) pairs each call reaches, failing the test at teardown when a declared pair was not reached. Show it red once on a seeded mismatched marker.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Verb-set parity guard

<!-- sq:subtask:ST2:body -->
New tests/meta guard: every work-item type matches the task verb set and parameter names minus what the spec decides; every comment host exposes the same comment verbs. Expectations derive from the bundled spec, no stored type list. Show it red on a seeded missing verb and parameter.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Coverage guard

<!-- sq:subtask:ST3:body -->
New tests/meta guard: fold the tree onto keys (dropping the _addr segment), read covers markers by ast, fail on undeclared and stale pairs; named exclusion constant for the two completion options.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — tests/cli scaffold and fixtures

<!-- sq:subtask:ST4:body -->
Create tests/cli with its conftest: the module-scoped squads the surface modules share (minimal, seeded, and a populated one with a feature, stories, a task with subtasks and a review with findings), copied per test.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-27T21:50:55Z] `python-dev` Elias Python:
  - - Handback: all four subtasks Done; gate green. pytest tests/meta tests/cli -n 4: `583 passed in 18.56s`; pyright 0 errors; ruff check and format clean; sq check clean. No production code changed; nothing committed.
    - Files: tests/_cli_surface.py (fold, pairs, reached_pairs, marker reading); tests/conftest.py (invoke cross-check, autouse guard that `covers` needs `invoke`); pyproject.toml (`covers` marker); tests/meta/test_every_cli_parameter_is_declared_by_a_covering_test.py (coverage guard + PENDING + EXCLUDED_PARAMS in _cli_surface); tests/meta/test_every_work_item_type_and_comment_host_exposes_the_reference_verbs.py (parity); tests/meta/test_a_covers_marker_is_checked_against_the_pairs_a_call_reaches.py; tests/cli/{__init__,conftest,_populated,test_squad_fixtures}.py (populated squad fixture: FEAT-2 with 2 stories, TASK-3 with 2 subtasks, REV-4 with 2 findings).
    - Pending list (33 owners, the exact set of undeclared owners): "", <type>, <kind>, <host>, adopt, blocked, board, check, create, dev, docs, graph, import, inbox, init, list, memory, migrate, mine, operator, override, reflog, renumber, repair, role, search, show, skill, sync, tree, ui, workflow, workload. `<kind>` is the sub-entity keys (`<type> <kind>`, `add-<kind>`, `<kinds>`) apart from `<type>`, and `<host>` the comment keys, so US3 and US4 can each remove their own entry. Surface today: 371 pairs + 8 parameterless leaves (dev list, migrate help, migrate up, role regen, skill regen, sync, ui, workflow lint).
    - Seeded-red proofs (all removed): invoke cross-check: a test marked covers("show","--json") that calls `list --json` errors at teardown "covers declares pairs no call reached: sq show --json"; a marker without `invoke` errors at setup. Coverage guard: dropping "sync" from PENDING gave "undeclared: sq sync (the command itself)"; a marker ("<type> show","--nope") gave "stale marker"; a test declaring sync with "sync" still pending gave "pending entry 'sync' has no undeclared pair left; remove it"; a temporary `--seeded-opt` on `sync` gave the undeclared pair plus the now-stale key-only marker. Parity: skipping retype/remove on `bug` in build_item_app gave "bug: missing verb retype/remove"; renaming `--json` to `--jsonx` on one host's `comments` gave "skill: comments lacks --json / has extra --jsonx". Src restored; git shows no src diff.
    - Rules I settled: a key-only marker is valid only for a parameterless leaf (on a command with parameters it is stale); a level that does not parse ends the cross-check walk, so a parse-time refusal of an option does not count that option as reached (declare it on the effect case); `comments` is held on item and roster hosts, the `comment` group on every host; parity of `create <type>` compares built commands exactly (plus field options like bug's --severity) and the hand-written `create guide` only on a core set (CREATE_CORE: TITLE, --author, --parent, --desc, --assignee, --message, --file, --json), since its --tag/--tech and missing --label/--priority/--ref are not spec-derived.
    - Not settled: nothing blocking. Note `create guide` lacks --priority although guide declares a priority field; I left it alone.
    - @manager ready for review.
<!-- sq:discussion:end -->
