---
id: TASK-1181
sequence_id: 1181
type: task
title: 'CLI tests: read commands'
status: Done
parent: FEAT-1173
author: tech-lead
assignee: python-dev
refs:
- TASK-1174:depends-on
subentities:
- local_id: ST1
  title: list and tree
  status: Done
  maps_to: US8
- local_id: ST2
  title: show, search, inbox, mine, blocked
  status: Done
  maps_to: US8
- local_id: ST3
  title: graph, workload, reflog
  status: Done
  maps_to: US8
- local_id: ST4
  title: docs, workflow and ui
  status: Done
  maps_to: US8
created_at: '2026-10-27T21:35:14Z'
updated_at: '2026-10-28T01:02:45Z'
---
<!-- sq:body -->
## Scope

FEAT-1173 US8: the read commands, one module per command or closely related pair in `tests/cli/`: `list`, `tree`, `show`, `search`, `inbox`, `mine`, `blocked`, `graph`, `workload`, `reflog`, `docs`, the `workflow` group (`show`, `types`, `statuses`, `lifecycles`, `collections`, `ref-kinds`, `roles`, `subentity-kinds`, `views`, `view`, `lint`) and `ui`'s non-interactive surface. Each runs on a seeded copied squad built once per module with enough items to make each filter observable.

Rules that bite:
- Rule 1: each filter alone; filters that narrow one listing independently are never crossed. Genuine interactions get their own named tests: `--priority` with `--min-priority` and `--badge` with `--min-badge` on one listing, `--sort` with `--json` (the order the array prints in).
- Rule 5: the whole output line or JSON object, not a substring.

## Acceptance

- Every pair is declared; filters are not crossed.
- Each case asserts a whole line or JSON object.

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

_Add with `sq task 1181 add-subtask "<title>"`; track with `sq task 1181 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — list and tree

<!-- sq:subtask:ST1:body -->
Every list and tree filter alone; named interaction tests for priority with min-priority, badge with min-badge and sort with json; whole lines and JSON objects asserted.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — show, search, inbox, mine, blocked

<!-- sq:subtask:ST2:body -->
Every parameter of these read commands on a seeded copied squad, whole line or JSON object asserted.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — graph, workload, reflog

<!-- sq:subtask:ST3:body -->
Every graph, workload and reflog parameter, each filter alone, with refusals for malformed values such as a bad --since or --direction.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — docs, workflow and ui

<!-- sq:subtask:ST4:body -->
docs with NAME and --rich, every workflow subcommand and its --json or --raw, workflow view with NAME and ID, and the ui command non-interactive surface.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-27T23:25:57Z] `python-dev` Elias Python:
  - - Handback: ST1-ST4 Done, task left InProgress. Gate green: pytest tests/meta tests/cli -n 3 `1366 passed in 31.53s`, pyright 0 errors, ruff check and format clean, sq check clean. `git diff src/` empty; nothing committed.
    - Files (new, tests/cli/): _readable.py (shared squad builders and `lines()`), test_list.py, test_tree.py, test_show.py, test_search.py, test_inbox_mine.py, test_blocked_workload.py, test_graph.py, test_reflog.py, test_docs_ui.py, test_workflow.py. PENDING: removed blocked, docs, graph, inbox, list, mine, reflog, search, show, tree, ui, workflow, workload; only `override` remains.
    - Pairs: every pair of the 13 owners is declared and honoured (guard + invoke cross-check pass); `ui` and `workflow lint` key-only. `ui`: stubbed `SquadsApp.run` proves wiring; refusal outside a squad.
    - Rule 1: each filter alone. Named interactions: priority with min-priority, badge with min-badge (list and tree), sort with --json order (list, tree), compact refusing json.
    - Mutation proof: 98 mutations applied one at a time and reverted by a harness; all 134 tests went red at least once. Examples: ItemFilter type/status/parent/label/assignee/category/badge/badge-min and its rank comparison; priority/min-priority/badge/min-badge builders; list/tree sort, --all, closed-hidden gate, --json, --compact, --depth, root id, blocked flag; parse_type/status/category/badge-code/CODE=VALUE/slug/item-id refusals; inbox/mine role, --all, matched sub-entities; search text/case/type/status/hit cap; blocked, workload counts and sort; show id/prefix/json/raw/comments/full; graph id/depth/kind/kind set/direction/--all/formats/refusals/seen mark/edge label; reflog item/actor/op/since (and inclusive bound)/tail/oldest-first/tree/json/line format; docs name/rich/listing/case/suffix/refusal; ui run and squad requirement; workflow raw/show/each --json/each table/view name/id/json/render/unknown name/lint text.
    - One equivalent mutant: `reflog --tail 0` (`tail=tail` instead of `tail if tail > 0 else None`) behaves identically because `out[-0:]` returns everything, so the `> 0` guard is redundant and `--tail 0` has no distinguishing test.
    - Product observations, not fixed and not pinned: (1) `sq list --sort ghost` / `sq tree --sort ghost` (unknown field) exits 0 with unsorted output; expected a refusal like `--priority ghost`. (2) `sq list --badge priority=ghost`, `--badge ghost=x` and `--min-badge priority=ghost` exit 0 with `no items`, where `--priority ghost` is refused with the valid set. (3) `sq reflog --op ghost` exits 0 with `no reflog entries` although the help lists the valid ops. (4) `sq reflog --item 4` (bare number) matches nothing; help says full ID so arguably fine. (5) `sq tree --depth -1` and `sq graph --depth -1` accept a negative depth silently.
    - Note: the `--at` clock and `task comment --as` are used only to build the reflog fixture. @manager ready for review.
<!-- sq:discussion:end -->
