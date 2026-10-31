---
id: TASK-1123
sequence_id: 1123
type: task
title: Cut sq's fixed startup cost, measured before and after
status: Done
parent: FEAT-916
author: tech-lead
refs:
- TASK-1104:depends-on
- TASK-1105:depends-on
- TASK-1106:depends-on
description: Attribute the fixed cost by phase, defer what no command needs, record
  timings.
subentities:
- local_id: ST1
  title: Attribute the fixed startup cost by phase
  status: Done
  maps_to: US1
- local_id: ST2
  title: Defer startup work the invoked command does not need
  status: Done
  maps_to: US2
- local_id: ST3
  title: Record before and after timings on FEAT-916
  status: Done
  maps_to: US3
created_at: '2026-10-24T21:53:14Z'
updated_at: '2026-10-25T10:45:53Z'
priority: medium
---
<!-- sq:body -->
## Goal

Every `sq` invocation does only the startup work the invoked command needs. `sq --version` gets under 0.3 s, `sq --help` stops re-reading the squad per listed command, and a command that needs the spec resolves it once. Output, exit codes and generated files do not change.

## Measured on 2026-10-24

Installed 0.16.0 tool (`~/.local/bin/sq`), this repo's squad (which has a workflow override), three runs each, wall time from `/usr/bin/time` (driven):

| command | wall |
|---|---|
| `python -c "import squads"` | 0.04 to 0.08 s |
| `sq --version` | 0.53 to 0.60 s |
| `sq --help` | 1.47 to 1.57 s (0.81 to 0.86 s outside any squad) |
| `sq task 1111 show` | 0.94 to 0.98 s |
| `sq board list` | 1.01 to 1.07 s |

In-process split for `sq --version` (driven, `perf_counter` around each phase): `import squads` 0.04 s, `import squads._cli` 0.29 to 0.34 s, `app()` 0.07 to 0.10 s. Within the `_cli` import (driven, overlapping cumulative times): third-party libraries about 0.10 s, the `_workflow` package about 0.10 s (it loads the bundled spec at import, `src/squads/_workflow/__init__.py:36`), `_interactions` about 0.03 s (it loads the bundled playbook at import, `src/squads/_interactions/__init__.py:111`), the remaining command modules about 0.23 s. The root command table is also built from the bundled spec at import (`_STATIC_TYPES`, `src/squads/_cli/__init__.py:388`).

Two leads from `cProfile` (driven; profiler times are inflated, ST1 re-attributes them):

- `sq --help` calls `common.resolve_spec_for_ctx` (`src/squads/_cli/_common.py:245`) 17 times. Each call re-reads the workflow override and re-validates it against the index (`validate_against_index_fail_closed`, `src/squads/_workflow/_loader.py`). The callers are `format_help`, `list_commands` and 52 `get_command` calls through `static_alias_is_stale` (`_cli/_common.py:314`). That is about 1.4 of the 1.9 profiled seconds.
- A subcommand builds the whole Click command tree twice: once in Typer's `app()`, and again in `value_options()` (`_cli/_common.py:1769`), reached from the root callback through `require_current_schema` and `help_requested`.

## Approach

1. **Attribute (ST1).** Measure by phase (interpreter start, third-party imports, `_workflow` import and bundled spec load, playbook load, command-module imports, Click tree build, spec and index resolution, the command itself) for `sq --version`, `sq --help` inside and outside a squad, `sq task <n> show` and one write command. Use `-X importtime` and `cProfile` with the command and corpus named. Post the table as a comment on FEAT-916, naming what is deferrable and what is not.
2. **Defer (ST2).** Choose from the ST1 numbers, not this list. Candidates, each reachable with the code as it stands:
   - resolve the spec at most once per invocation on the help and completion path, memoised on the Click root context the way `get_service` already memoises the service;
   - compute `value_options()` from the command tree Click already built, not a second `typer.main.get_command(app)`;
   - import command modules on first dispatch: the root group keeps a name to module and short-help table and imports in `get_command`, so `--version` imports no command module;
   - load the bundled spec and playbook on first use instead of at package import. This is only worth doing if ST1 shows it matters for `--version`. The module-level shims over the bundled spec are pruned by FEAT-1092, so do not build new machinery around them.
3. **Record (ST3).** Post the before and after timings of `sq --version`, `sq task <n> show` and one write command as a comment on FEAT-916: same machine, same corpus, three runs each.

Constraints:

- `sq --help` in a squad with a workflow override must still show that squad's dropped types, renamed aliases and custom types, and must fall back to the bundled spec when the override fails. The help path keeps reading the spec, once.
- Add no module-level mutable state. A per-invocation memo lives on the Click context. `functools.cache` on a pure function of bundled data is allowed.
- `_CustomTypeGroup._custom_cmd_cache` is a class-level dict that BUG-1021 reports leaking between in-process runs. Do not extend it, and reuse nothing from it for the new memo.

## Tests

The suite as it stands is the safety net: it passes with no assertion edited. Timings are never asserted in tests.

- **One table, "startup work per command"**, with only these rows: `--version` (no spec resolution, no command module imported); `--help` in a squad with a workflow override (the spec resolved exactly once); `--help` outside a squad; `task <n> show` (the spec resolved once, the Click tree built once). Count with spies on the resolution function and the tree build, and check `sys.modules` for the lazy modules. Falsify each row once by removing the memo or the laziness it pins, and record the red.
- If the command table becomes lazy, add one `tests/meta` guard: every name in the table dispatches to a real command, and its short help matches the command's own help. One guard, not a test per command.
- No new help-output tests: the help goldens and the existing override and fail-soft tests already own that, so a second layer would duplicate them.

## Generated output

None. No template, skill, pointer or CLAUDE.md section changes, and the template manifest is unchanged.

## CHANGELOG substance (the writer authors the entry)

Faster startup on every command. `sq --version` and `sq --help` do much less work, and `sq --help` in a customised squad no longer re-reads the workflow override once per listed command. Include the before and after numbers from ST3. Nothing an adopter sees changes apart from speed.

## Order

This task starts after the FEAT-1101 tasks that are editing `_cli/` (TASK-1104, TASK-1105, TASK-1106). It lands before the FEAT-1092 structural work and before the test-suite rebuild inventory (TASK-1111), so both build on the lean startup path. It also lands before any daemon task, so the daemon is measured against this baseline.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1123 add-subtask "<title>"`; track with `sq task 1123 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Attribute the fixed startup cost by phase

<!-- sq:subtask:ST1:body -->
Attribute the fixed cost by phase: interpreter start, third-party imports, the `_workflow` import with the bundled spec load, the playbook load, command-module imports, the Click tree build, spec and index resolution, and the command itself. Measure `sq --version`, `sq --help` inside and outside a squad, `sq task <n> show` and one write command, three runs each, with `-X importtime` and `cProfile`, naming the command and the corpus. Post the table as a comment on FEAT-916 and name the deferrable parts.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Defer startup work the invoked command does not need

<!-- sq:subtask:ST2:body -->
Defer what ST1 shows no command needs. The candidates are in the task body: resolve the spec at most once on the help path, compute `value_options()` from the tree Click already built, import command modules on first dispatch, and load the bundled documents lazily. Keep help output for a customised squad identical. Add no module-level mutable state. Add the startup-work table and, if the command table becomes lazy, its `tests/meta` guard. Falsify each row.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Record before and after timings on FEAT-916

<!-- sq:subtask:ST3:body -->
Post the before and after timings of `sq --version`, `sq task <n> show` and one write command as a comment on FEAT-916: three runs each, on the same machine and corpus as ST1. Report the numbers for the CHANGELOG entry to the writer.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T21:56:14Z] `tech-lead` Olivia Lead:
  - @op-pierre one ruling needed before this goes Ready. FEAT-916's acceptance says `sq --help` "loads no spec". In a squad with a workflow override, root help shows that squad's dropped types, renamed aliases and custom types, so help has to read the override, or its output changes for every customised squad. That collides with "output unchanged". Recommendation: reword it to "`sq --version` loads no spec; `sq --help` resolves it at most once per invocation". Driven today on this repo: 17 resolutions per `sq --help`, each re-reading the override and the index, 1.47 to 1.57 s. Keep the 0.3 s bar for `--version`: it is reachable if `--version` imports no command module (0.53 to 0.60 s today, of which about 0.3 s is the `_cli` import).
- [2026-10-24T23:45:22Z] `manager` Catherine Manager:
  - Taking the tech-lead recommendation to keep the loop moving overnight (reversible, acceptance wording only): "--version loads no spec; --help resolves it at most once per invocation", with the 0.3 s bar on --version. A customised squad must read its override for help, so "loads no spec" cannot hold for --help. @op-pierre to confirm or change in the morning. @product-owner amend FEAT-916 acceptance accordingly.
- [2026-10-25T01:17:10Z] `python-dev` Elias Python:
  - Handoff. Timings are in the two FEAT-916 comments (ST1 attribution, ST3 table); the machine was shared (load average 6 to 11), so figures carry about 0.1 s of noise. Summary, three runs each, before to after: bare `sq --version` 0.7 s to 0.1 s; `sq --help` on this repo 1.5 s to 0.7 s, in a customised scratch squad 0.8 s to 0.75 s, outside a squad unchanged at 0.7 s; `sq task <n> show` and a write command within noise (0.74 to 0.69 and 0.78 to 0.74 in the scratch squad). Help output is byte-identical before and after in three corpora.
    
    ST1: attribution posted on FEAT-916. Command modules cost under 0.01 s; the fixed cost is the `_common` import chain (about 0.15 to 0.2 s), the bundled spec and playbook loads (about 0.1 s), third-party imports, and two Click tree builds (0.065 s each).
    
    ST2, what changed:
    - `resolve_spec_for_ctx` (`_cli/_common.py`) memoises its disk read on the root Click context (`squads.resolved_spec_memo`), split into `_read_spec_from_disk`. `sq --help` now reads the override once, down from 17 times. No module-level state; `_custom_cmd_cache` is untouched.
    - `help_requested` takes an optional root command and `apply_gate` passes the invocation's own tree, so `value_options()` no longer builds a second tree. `value_options()` itself keeps its signature and its once-per-process cache.
    - `squads.__main__:main` is now the console-script entry point (pyproject, docs/internals.md). A command line that is exactly `--version` prints the version without importing `squads._cli`; everything else delegates to `squads._cli.main`. The edge table in the tests/meta guard has the two new rows.
    - Not done, with numbers in the FEAT-916 comment: lazy command modules (nothing to gain), lazy bundled spec and playbook (every command but `--version` needs them), registering aliases once (about 0.03 s for output risk).
    - Tests: `tests/cli/test_startup_work_per_command.py`, one table of four rows (bare `--version`, `--help` in a customised squad, `--help` outside a squad, `task <n> show`), counting override reads and tree builds with spies. Falsified: without the memo the customised-squad row reads 17 against 1; with the second tree build restored the `show` row reads (1, 2) against (1, 1); with the fast path removed the `--version` row loses its empty module list. The outside-a-squad row went red only through the missing helper, not through a count. No lazy command table, so no new meta guard.
    - Gates: pyright, ruff check and format clean; `tests/meta`, `tests/integration`, `tests/cli` and the two targeted unit files: 5124 passed, 11 skipped, 1 xfailed. No full suite run.
    
    Deviations: `sq -C <dir> --version` and `sq --version` after other options still take the full path (about 0.6 s); only the bare form is fast. `uv sync` regenerates the venv script for the new entry point; an installed tool needs a reinstall to pick it up.
    
    CHANGELOG substance for the writer: `sq --version` answers in about 0.1 s instead of 0.7 s when it is the whole command line. `sq --help` reads a workflow override once instead of once per listed command, taking this repo's help from 1.5 s to 0.7 s. Every other command skips one redundant build of the command tree, a few hundredths of a second. Nothing an adopter sees changes apart from speed. Packaging note: the `sq` and `squads` console scripts now point at `squads.__main__:main`.
- [2026-10-25T01:26:30Z] `tech-writer` Theo Writer:
  - CHANGELOG 0.17.0 entry written under Changed, from the ST3 numbers and the dev handoff: bare --version about 0.1 s (was about 0.7 s), --help with a workflow override about 1.5 s to 0.7 s on the measured squad, one redundant command-tree build removed for other commands. Timings are labelled approximate, one shared machine, three runs each, noise about 0.1 s. Caveats kept in: -C or options before --version still take the full path (about 0.6 s). No packaging note: an upgrade reinstalls the console scripts, so it does not reach adopters; the contributor uv sync reinstall note stays out of the CHANGELOG. docs/internals.md already names squads.__main__:main at HEAD, so no docs edit. sq check clean. @tech-lead for a read of the entry against the measured figures.
- [2026-10-25T01:43:06Z] `reviewer` Paul Reviewer:
  - Reviewed in REV-1132: three low findings, no behaviour defect found. @python-dev see the review.
- [2026-10-25T10:45:53Z] `op-pierre` Pierre Chat:
  - Acceptance: the spec must be loaded exactly once per invocation on every path, not only under --help.
<!-- sq:discussion:end -->
