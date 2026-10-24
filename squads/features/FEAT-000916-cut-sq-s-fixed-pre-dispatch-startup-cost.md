---
id: FEAT-916
sequence_id: 916
type: feature
title: Cut sq's fixed pre-dispatch startup cost
status: Ready
parent: EPIC-31
author: product-owner
priority: medium
refs:
- EPIC-29
- MILE-1051:targets
subentities:
- local_id: US1
  title: Attribute the fixed startup cost by phase
  status: Todo
- local_id: US2
  title: Defer work no command needs at startup
  status: Todo
- local_id: US3
  title: Record the before and after timings
  status: Todo
created_at: '2026-09-03T13:06:26Z'
updated_at: '2026-10-24T19:42:49Z'
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
- `sq --version` and `sq --help` load no spec and build no sub-app they do not
list, and `sq --version` is under 0.3 s on the machine of the baseline
measurement; the bar is revisited if the attribution shows it unreachable.
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
As an agent making hundreds of calls, I want sq to do only the work the invoked command needs, so that each call is cheap. Acceptance: --version and --help build no unlisted sub-app and load no spec; a command that needs the spec loads it once; output and exit codes are unchanged and the suite passes with no assertion edited.
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
<!-- sq:discussion:end -->
