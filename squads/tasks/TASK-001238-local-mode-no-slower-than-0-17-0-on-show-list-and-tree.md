---
id: TASK-1238
sequence_id: 1238
type: task
title: Local mode no slower than 0.17.0 on show, list and tree
status: Done
parent: FEAT-1226
author: tech-lead
priority: high
refs:
- ADR-1224:implements
- ADR-1225
description: Measure where the 20-30 % run-time regression goes, apply the local-mode
  levers, prove show/list/tree no slower than 0.17.0
subentities:
- local_id: ST1
  title: Benchmark script and span breakdown
  status: Done
  story: US6
- local_id: ST2
  title: Local-mode levers from ADR-1225
  status: Done
  story: US6
- local_id: ST3
  title: Fix the run-time costs until the criterion holds
  status: Done
  story: US6
created_at: '2026-10-29T07:11:29Z'
updated_at: '2026-10-29T12:42:24Z'
---
<!-- sq:body -->
## Goal

Local mode in 0.18 is not slower than 0.17.0 on `sq <type> <n> show`, `sq list` and `sq tree` (op-pierre, FEAT-1226 comment 739a3b6, 2026-10-29).

## Problem

Measured on 2026-10-29, local mode is 20-30 % slower than 0.17.0: `task show` 1088 → 1304 ms median, `list` 908 → 1100 ms, `tree` 840 → 1110 ms. Import time has not moved (`import squads._cli` about 0.5-0.65 s), so the added cost is spent at run time.

## Criterion

For each of `show`, `list` and `tree`, the median of 31 interleaved runs of 0.18 in local mode (`SQUADS_DAEMON=off`) on the reference host is at most the median of the released 0.17.0 on the same squad. Measured by a script checked in under `scripts/`, which runs both versions interleaved against one copy of a squad and prints the medians and p25-p75 per command. The numbers are recorded as a comment on this task and with the release.

## Approach

1. **Measure first, without a profiler.** Wall-clock spans around the root callback, `LocalApi` composition, the operation, the DTO build and validation, and rendering, taken in the script's runs, not under cProfile, whose overhead distorts pydantic and import-heavy paths. Post the span breakdown per command before changing anything.
2. **Candidates to check:** `LocalApi` composition (a service composed per mode, the binding table walk); pydantic DTO build and validation on objects built in-process (`model_construct` where the service already holds valid data, validation kept at the HTTP boundary); building the full `display` object when the command shows only part of it; Typer converting the whole command tree on every invocation.
3. **Levers from ADR-1225 section 5 that serve local mode,** applied here: lazy command modules (a literal command-name table at the root that imports only the invoked group's module, root `--help` still loading all, with a `tests/meta` guard comparing the table to the registered tree); `gc.freeze()` once output is flushed and `gc.disable()` for start-up, in `main`; `__version__` without `importlib.metadata`; `defer_build` on the DTO modules and `rich.markdown` imported only when a body is rendered (check each is in place and effective). TASK-1219 does not apply them.
4. Fix what the spans show, re-measure, repeat until the criterion holds.

The remote-client budget (275/235 ms), its import guard and its benchmark stay in TASK-1219, which builds on the levers this task lands.

## Modules touched

Depends on the spans; expected: `src/squads/_cli/__init__.py` (root callback, command-name table, `gc` in `main`), `src/squads/__init__.py` (`__version__`), `src/squads/_services/_local_api.py`, the DTO projections in `_services`, `_api/_dto/` modules, `_cli/_render/`, `tests/meta/` (the command-name table guard), `scripts/` (the benchmark). Output stays byte-identical: the surface suite passes unchanged.

## Acceptance

- The criterion above, measured and recorded for `show`, `list` and `tree`.
- FEAT-1226 US1: human output, `--json`, exit codes and error text unchanged.
- Gates green: pyright, ruff, `sq check`, `tests/meta`, the surface suite.

## Test approach

- No benchmark in the suite (ADR-1172): the script is a release-time check, like TASK-1219's budget script, and the releasing runbook runs it.
- New guard: 1 (the command-name table matches the registered tree). Falsify once by adding a command without a table entry. New surface cases: 0.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1238 add-subtask "<title>"`; track with `sq task 1238 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Benchmark script and span breakdown

<!-- sq:subtask:ST1:body -->
Benchmark script under `scripts/`: runs the released 0.17.0 (installed as a separate uv tool or venv) and the dev tree interleaved, 31 runs each, of `sq <type> <n> show`, `sq list` and `sq tree` against one copy of a squad with `SQUADS_DAEMON=off`, and prints median and p25-p75 per command and version. Add wall-clock spans (root callback, composition, operation, DTO build and validation, render) reported by the dev tree when an environment variable asks for them, without a profiler. Post the baseline and the span breakdown per command as a comment before any fix.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Local-mode levers from ADR-1225

<!-- sq:subtask:ST2:body -->
Apply the ADR-1225 section 5 levers that serve local mode: the literal command-name table with lazy command modules (root `--help` loads all) and its `tests/meta` guard against the registered tree; `gc.freeze()` after output is flushed and `gc.disable()` for start-up in `main`; `__version__` without `importlib.metadata`; confirm `defer_build` on every DTO module and `rich.markdown` imported only when a body renders. Re-measure with the script after each lever and record its effect. 1 guard.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Fix the run-time costs until the criterion holds

<!-- sq:subtask:ST3:body -->
Fix the run-time costs the spans show among the candidates: `LocalApi` composition, pydantic validation of DTOs built in-process (`model_construct` where the data is already valid, validation kept at the HTTP boundary), building the full `display` object when the command shows part of it, Typer's full-tree conversion. Re-measure until 0.18 is not slower than 0.17.0 on `show`, `list` and `tree`, and record the final numbers as a comment. Output stays byte-identical (surface suite unchanged).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T07:11:56Z] `tech-lead` Olivia Lead:
  - Created per op-pierre 739a3b6 on FEAT-1226. Subtasks mapped to US1 for lack of a performance story. @product-owner a local-mode performance story on FEAT-1226 would fit better; remap when it exists.
- [2026-10-29T07:12:30Z] `product-owner` Nina Product:
  - @tech-lead the story now exists: FEAT-1226 US6 (local commands no slower than 0.17.0). Please remap the subtasks to US6.
- [2026-10-29T07:12:49Z] `manager` Catherine Manager:
  - Subtasks remapped to FEAT-1226 US6 (the product owner's new performance story).
- [2026-10-29T10:27:16Z] `python-dev` Elias Python:
  - Baseline and span breakdown, measured before any lever (scratch copy of this repo's squads/ corpus, SQUADS_DAEMON=off, 31 interleaved runs, medians in ms; script: scripts/bench_local_mode.py):
    
    | command | 0.17.0 median (p25-p75) | 0.18 median (p25-p75) | new/old |
    |---|---|---|---|
    | task show | 1019 (944-1052) | 1222 (1141-1274) | 1.20 |
    | list | 1106 (1052-1167) | 1341 (1286-1384) | 1.21 |
    | tree | 1028 (1002-1073) | 1241 (1208-1301) | 1.21 |
    
    Wall-clock spans of the 0.18 run (median of 31, SQUADS_SPANS on; times are since the launcher started the process unless noted):
    
    | span | show | list | tree |
    |---|---|---|---|
    | start-up to root callback (interpreter + imports + command tree build) | 546 | 571 | 547 |
    | root callback | 139 | 142 | 138 |
    | LocalApi squad resolve + schema gate | 10 | 10 | 10 |
    | LocalApi composition | 2.7 | 2.3 | 2.3 |
    | operation (handler, includes the DTO span) | 98 | 86 | 95 |
    | DTO build + validation (inside operation) | 3.4 | 7.2 | 5.6 |
    | api_call total (asyncio.run) | 113 | 103 | 108 |
    | render, up to the end of main | 12 | 111 | 39 |
    | exit, after main returns (interpreter teardown) | 370 | 389 | 373 |
    
    Reading: composition and DTO validation are noise (under 10 ms). The costs are the root callback (about 140 ms), the operation (about 90 ms), and interpreter teardown after output (about 370 ms, a full object-graph walk by the collector at exit). Neither version has the gc lever, so the 0.17.0 run pays the teardown too; the regression sits in the root callback and the operation, and the teardown is the largest single cost to take back.
- [2026-10-29T10:49:55Z] `python-dev` Elias Python:
  - Final medians, same scratch squad copy, SQUADS_DAEMON=off, 31 interleaved runs, ms (script: scripts/bench_local_mode.py, commits f70d4bbb and b058ee3d on the worktree branch):
    
    | command | 0.17.0 median (p25-p75) | 0.18 median (p25-p75) | new/old |
    |---|---|---|---|
    | task show | 1015 (955-1039) | 704 (661-732) | 0.69 |
    | list | 1084 (1043-1125) | 785 (751-807) | 0.72 |
    | tree | 985 (921-1052) | 688 (649-723) | 0.70 |
    
    The criterion holds on all three, with 28-31 % to spare. Before any lever (earlier comment): 1222 / 1341 / 1241.
    
    Levers applied:
    - gc.disable() from the launcher through the imports, gc.freeze() + gc.enable() before the command runs, output flushed and gc.freeze() before exit: show 1222 to 762, list 1341 to 933, tree 1241 to 832 (11-run medians, this lever alone). This is most of the gain: interpreter teardown after output fell from about 370 ms to about 25-30 ms.
    - Lazy command groups: the root maps each group name (and each type and alias) to its module, imports and converts it on first lookup; root --help still builds every one. With the next three levers it took show to 660-685, list to 704-725, tree to 654-748 (11-15-run medians). Typer's conversion of the whole tree was about 70-110 ms.
    - __version__ read from the installed metadata on first use instead of at import; rich.markdown imported when a comment pane renders; help_requested returns early when no --help token is present (it walked the whole command tree on every addressed command). These three were not measured one by one; the importtime figures were 23 ms (importlib.metadata chain) and 32 ms (rich.markdown), and the help_requested walk would have forced every lazy group to build.
    - defer_build: already on the DTO base model and Response; no change.
    
    Span medians after the levers (ms, since process launch unless noted): start-up to root callback 334-341, root callback 204-219 (it now carries imports that used to sit before it), resolve + schema gate 8-9, composition 2.3-2.6, operation 89-107, DTO build and validation 4-6, api_call total 107-120, exit after output 25-32.
    
    Not applied, noted for the record: the root callback and the operation each parse the 2 MB index (about 25-30 ms apiece). Sharing one parse would save about 25 ms; not needed for the criterion. CLI output is byte-identical to the pre-change 0.18 tree on 48 sampled invocations (list/tree/show text and --json, root and every group and alias --help, errors), and tests/meta plus tests/cli pass.
- [2026-10-29T11:11:19Z] `reviewer` Paul Reviewer:
  - Reviewed on REV-1235 (F54-F59). Output, exit codes, help, aliases, completion and override types all match 0aec4439 on 225 sampled invocations. gc is back on during the command, and piped and redirected output is complete. @tech-lead one medium blocker: F54, where the type-app cache is built from an override spec and leaks across run() calls. The fix is one line: spec=bundled_spec() in _type_app. The rest are low or info.
- [2026-10-29T11:28:04Z] `python-dev` Elias Python:
  - Round 2 (6e65283e), 31 interleaved runs, medians ms: show 988 to 657, list 1119 to 795, tree 1031 to 717 (0.17.0 to 0.18); new/old 0.67, 0.71, 0.70. Review findings F54, F55, F56, F57, F59 fixed; F58 left for the writer.
- [2026-10-29T11:33:11Z] `reviewer` Paul Reviewer:
  - @tech-lead REV-1235: F55, F56, F57, F59 Verified. F54 reopened: the fix holds (repro clean), but its test is vacuous whenever an earlier test on the worker built bug, because the root conftest caches the root command per process. Evidence and a whole-output test shape are in the F54 discussion.
- [2026-10-29T11:41:57Z] `reviewer` Paul Reviewer:
  - @tech-lead REV-1235 F54 Verified: the reworked test fails with the fix reverted, both alone and after a bug --help test. New low F60: drop_type_apps is a src-only test hook (vulture flags it); a per-root type-app cache removes it and the module-level cache. Details are on F60.
- [2026-10-29T11:48:02Z] `python-dev` Elias Python:
  - Round 4 (d9d97731), 31 interleaved runs, medians ms 0.17.0 to 0.18: show 1025 to 723, list 1094 to 788, tree 1037 to 713 (0.71, 0.72, 0.69); no regression.
- [2026-10-29T11:49:38Z] `manager` Catherine Manager:
  - Done: criterion met (31 interleaved runs, 0.18/0.17.0 medians show 0.71, list 0.72, tree 0.69); REV-1235 F54-F57, F59, F60 verified; F58 (releasing runbook) is with the writer on TASK-1234.
<!-- sq:discussion:end -->
