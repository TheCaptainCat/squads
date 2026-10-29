---
id: TASK-1238
sequence_id: 1238
type: task
title: Local mode no slower than 0.17.0 on show, list and tree
status: Ready
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
  status: Todo
  story: US6
- local_id: ST2
  title: Local-mode levers from ADR-1225
  status: Todo
  story: US6
- local_id: ST3
  title: Fix the run-time costs until the criterion holds
  status: Todo
  story: US6
created_at: '2026-10-29T07:11:29Z'
updated_at: '2026-10-29T07:12:49Z'
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
3. **Levers from ADR-1225 section 5 that serve local mode,** applied here: lazy command modules (a literal command-name table at the root that imports only the invoked group's module, root `--help` still loading all, with a `tests/meta` guard comparing the table to the registered tree); `gc.freeze()` once output is flushed and `gc.disable()` for start-up, in `main`; `__version__` without `importlib.metadata`; `defer_build` on the DTO modules and `rich.markdown` imported only when a body is rendered (check each is in place and effective). These move here from TASK-1219.
4. Fix what the spans show, re-measure, repeat until the criterion holds.

The remote-client budget (275/235 ms), its import guard and its benchmark stay in TASK-1219; that task now builds on the levers landed here.

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
<!-- sq:discussion:end -->
