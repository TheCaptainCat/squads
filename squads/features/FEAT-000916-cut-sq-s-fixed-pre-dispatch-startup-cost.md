---
id: FEAT-916
sequence_id: 916
type: feature
title: Cut sq's fixed pre-dispatch startup cost
status: Done
parent: EPIC-31
author: product-owner
priority: medium
refs:
- EPIC-29
- MILE-1051:targets
subentities:
- local_id: US1
  title: Attribute the fixed startup cost by phase
  status: Done
- local_id: US2
  title: Defer work no command needs at startup
  status: Done
- local_id: US3
  title: Record the before and after timings
  status: Done
created_at: '2026-09-03T13:06:26Z'
updated_at: '2026-10-25T02:17:36Z'
---
<!-- sq:body -->
## Capability

Reduce the fixed pre-dispatch cost every `sq` invocation pays, by deferring
work (spec load, sub-app construction, whatever attribution finds) until the
command that actually needs it runs, instead of doing it unconditionally on
every call. Agents make hundreds of `sq` calls a session (briefs, board reads,
status transitions); each one pays the full fixed cost even when the command
itself does almost nothing.

It is built before the daemon work (EPIC-29, ADR-1052), so the daemon is
measured against the lean startup baseline.

**Measurement-first.** Which parts of the fixed cost are deferrable is an
implementation question this feature does not answer up front. The first step is
a measurement pass that attributes the fixed cost across Typer app construction,
spec loading and sub-app construction, so that what is deferred is chosen from
the numbers, not from the first plausible suspect.

## Evidence

Driven by op-pierre on 2026-09-03 (`release/0.15`, this machine, this repo's
corpus):

| what | time |
|---|---|
| `uv run` overhead alone (`uv run python -c "pass"`) | 0.049s |
| `import squads` | 0.072s |
| `.venv/bin/sq --version` (no uv in the loop) | 0.740s |
| `.venv/bin/sq task 909 show` | 0.668s |
| `uv run sq check` (whole corpus) | 3.203s |

Re-driven on 2026-10-24 on the installed 0.16.0 tool: `sq --version` takes
0.62 to 0.65 s over three runs. The cost is unchanged.

Neither `uv` nor importing the package is the cost. About 0.6 to 0.7 s of fixed
work sits between "package imported" and "simplest possible command answered":
`sq --version` pays essentially all of it while only printing a string, and a
real `show` costs almost the same. That is Typer app construction plus spec
loading happening unconditionally on every invocation.

## Context: relationship to daemon mode (not scope)

The daemon work (EPIC-29) is valuable for a local git-backed squad because of
this same startup cost, not only for remote mode. The two are complementary:
lazy-loading is a fraction of daemon-scale work and lands the win for everyone,
including anyone who never runs a daemon. The daemon then buys back the
remaining per-call cost, not the whole of it.

## Context: `sq check`'s 3.2s is a separate problem (not scope)

`sq check` over the whole corpus is real per-corpus work (every item, every
rule), roughly 2.5 s on top of the fixed cost this feature targets. It deserves
its own attribution pass.

## Out of scope

- Per-corpus cost of `sq check`, `sq repair` or any whole-corpus command.
- The daemon itself.
- Any change to what a command prints or does.

## Acceptance criteria

- A recorded attribution of the fixed cost, by phase (import, app construction,
spec load, sub-app construction), measured with the command and corpus named.
- `sq --version` loads no spec and builds no sub-app, and is under 0.3 s on the
machine of the baseline measurement; the bar is revisited if the attribution
shows it unreachable. `sq --help` resolves the spec at most once per invocation
and builds no sub-app it does not list: a customised squad's help shows its
workflow override, so help cannot skip the spec.
- A command that needs the spec (`sq task <n> show`) loads it once and is no
slower than before.
- Output, exit codes and generated files of every command are unchanged: the
full test suite passes with no assertion edited to fit.
- Before and after timings are recorded in a comment on this feature.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 916 add-story "As a <role>, I want … so that …"`; track with `sq feature 916 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Attribute the fixed startup cost by phase

<!-- sq:story:US1:body -->
As a maintainer, I want the 0.6 to 0.7 s fixed cost attributed across import, Typer app construction, spec load and sub-app construction, so that what is deferred is chosen from numbers. Acceptance: a table of time per phase on a named corpus, recorded as a comment on this feature, and the deferrable parts named.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Defer work no command needs at startup

<!-- sq:story:US2:body -->
As an agent making hundreds of calls, I want sq to do only the work the invoked command needs, so that each call is cheap. Acceptance: --version loads no spec and --help resolves it at most once per invocation, and neither builds an unlisted sub-app; a command that needs the spec loads it once; output and exit codes are unchanged and the suite passes with no assertion edited.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Record the before and after timings

<!-- sq:story:US3:body -->
As the operator, I want measured results, so that the daemon is judged against a known baseline. Acceptance: before and after timings of sq --version, sq task <n> show and one write command are recorded in a comment, same machine and corpus as the attribution, three runs each.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T13:32:06Z] `op-pierre` Pierre Chat:
  - Held, not in 0.15. Neither is gated on the web API or the daemon -- both are local CLI work that lands independently -- but 0.15 already carries two full lines and nothing forces these early. Picked up in a later release, or alongside the daemon work when the startup cost starts hurting enough to act on. The measurements are on the record; that was the point of writing them down.
- [2026-10-16T11:28:12Z] `op-pierre` Pierre Chat:
  - 2026-10-16: targets 0.17 (MILE-1051), built first so the daemon is measured against the lean startup baseline.
- [2026-10-24T19:42:47Z] `product-owner` Nina Product:
  - @tech-lead needs a breakdown into tasks (no tasks yet). Premises re-checked on 2026-10-24: startup cost unchanged on 0.16.0 (0.62 to 0.65 s). Body now has acceptance criteria and three stories.
- [2026-10-24T21:56:17Z] `tech-lead` Olivia Lead:
  - Broken down into TASK-1123, one task with three subtasks mapped to US1-US3. It stays Draft on one acceptance question for @op-pierre: `--help` has to read a workflow override to keep its output, see the task.
    Order: after the FEAT-1101 tasks editing `_cli/` (TASK-1104, TASK-1105, TASK-1106). Then before FEAT-1092's structural task (TASK-1124 depends on it) and before the test-rebuild inventory (TASK-1111 depends on it). Why: the startup work and the structural moves both edit `_cli/_common.py` and the import-time loads in `_workflow`/`_interactions`, so this small one goes first, and the rebuild then ports the startup path as it will stay. There are no daemon tasks yet (FEAT-33 is Draft). When it is broken down, its first task should depend on TASK-1123, so the daemon is measured against this baseline.
    Re-measured 2026-10-24 on 0.16.0: `--version` 0.53 to 0.60 s, `--help` 1.47 to 1.57 s, `task <n> show` 0.94 to 0.98 s. The figures and the two profiler leads are in the task body.
- [2026-10-24T23:45:54Z] `product-owner` Nina Product:
  - 2026-10-25: acceptance amended per the manager ruling on TASK-1123: --version loads no spec (0.3 s bar kept); --help resolves the spec at most once per invocation, since a customised squad needs its override for help. US2 reworded to match. @op-pierre confirms or changes this in the morning.
- [2026-10-25T01:16:55Z] `python-dev` Elias Python:
  - ST1 attribution, driven on 2026-10-25 with the dev build, three runs each, wall time. The machine is shared (load average 6 to 11 during these runs), so every figure carries noise of about 0.1 s.
    
    Phases of `sq --version` before the change (perf_counter and `-X importtime`, this repo's squad):
    
    | phase | time |
    |---|---|
    | interpreter start and `import squads` | 0.04 to 0.06 s |
    | third-party (typer, rich, pydantic) | 0.06 to 0.09 s |
    | `_workflow` package import plus bundled spec load | 0.06 to 0.10 s |
    | `_interactions` plus bundled playbook load | 0.02 to 0.04 s |
    | rest of the `squads._cli` import (`_common` pulls in `_services`, `_index`, `_models`, `_rendering`, `_discussion`) | 0.15 to 0.20 s |
    | the eleven command modules themselves | under 0.01 s in total |
    | Click tree build (`typer.main.get_command(app)`, 33 registered groups, 538 commands) | 0.065 s |
    | second Click tree build in `value_options()` | 0.062 s |
    
    - `sq --help`, 17 `resolve_spec_for_ctx` calls (52 `get_command` calls through `static_alias_is_stale`, three more from `format_help` and `list_commands`), each re-reading the override and validating it against the index: 1.5 s on this repo, 0.8 s in a small squad.
    - Not deferrable: the `_common` import chain (every command except `--version` uses services and models), the bundled spec (the item apps are built from it) and one Click tree build.
    - Deferrable: the second tree build, the 16 repeat spec resolutions, and for a bare `sq --version` the whole `squads._cli` import.
    - Measured and not worth doing: lazy command modules (the eleven modules cost under 0.01 s; their import cost is `_common`); registering the nine hidden aliases once rather than as 14 extra groups (the tree build would drop from 0.069 to 0.039 s, but Typer's did-you-mean reads the raw registered table, so the change risks output for about 0.03 s).
- [2026-10-25T01:16:57Z] `python-dev` Elias Python:
  - ST3 before and after, same machine, same corpus (this repo's squad, a scratch squad copying its workflow override, and an empty directory), interleaved before/after runs, three runs each, wall seconds including interpreter start. The machine is shared (load average 6 to 11), so the numbers carry noise of about 0.1 s.
    
    | command | before | after |
    |---|---|---|
    | `sq --version` (scratch squad) | 0.68 0.69 0.70 | 0.12 0.09 0.09 |
    | `sq --version` (outside a squad) | 0.67 0.72 0.73 | 0.08 0.11 0.09 |
    | `sq --help` (this repo) | 1.53 1.48 1.57 | 0.69 0.71 0.70 |
    | `sq --help` (scratch squad with override) | 0.84 0.79 1.03 | 0.75 0.81 0.71 |
    | `sq --help` (outside a squad) | 0.72 0.70 0.69 | 0.71 0.70 0.63 |
    | `sq task <n> show` (scratch squad) | 0.74 0.81 0.71 | 0.69 0.73 0.65 |
    | `sq task 1111 show` (this repo) | 0.86 0.87 0.82 | 0.94 0.82 0.87 |
    | `sq task <n> comment` write (scratch squad) | 0.78 0.78 0.78 | 0.74 0.77 0.68 |
    
    - `sq --version` is under the 0.3 s bar by a wide margin when it is the whole command line. With a `-C` before it, it still goes through the full CLI at about 0.6 s.
    - `sq task <n> show` and the write command are within noise of before, a few hundredths of a second faster in the scratch squad; the second tree build removed there is about 0.06 s. Their floor is the `_common` import chain.
    - Help output (`--help`, `task --help`, `create --help`) is byte-identical before and after in all three corpora.
- [2026-10-25T02:17:36Z] `manager` Catherine Manager:
  - Done: TASK-1123 delivered all three stories; review REV-1132 Approved. The --help acceptance wording awaits op-pierre confirmation (see TASK-1123).
<!-- sq:discussion:end -->
