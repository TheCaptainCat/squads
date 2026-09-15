---
id: FEAT-916
sequence_id: 916
type: feature
title: Cut sq's fixed pre-dispatch startup cost
status: Draft
parent: EPIC-31
author: product-owner
priority: medium
refs:
- EPIC-29
created_at: '2026-09-03T13:06:26Z'
updated_at: '2026-09-03T13:32:06Z'
---
<!-- sq:body -->
## Capability

Reduce the fixed pre-dispatch cost every `sq` invocation pays, by deferring
work — spec load, sub-app construction, whatever attribution finds — until
the command that actually needs it runs, instead of doing it unconditionally
on every call. Agents make hundreds of `sq` calls a session (briefs, board
reads, status transitions); each one currently pays the full fixed cost even
when the command itself does almost nothing.

**Measurement-first.** Which parts of that fixed cost are deferrable is an
implementation question this feature does not answer. The first step is a
measurement pass that attributes the fixed cost across Typer app
construction, spec loading, and sub-app construction — we should know where
the time goes before choosing what to defer, not guess at it and defer the
first plausible suspect.

## Evidence (driven, op-pierre, 2026-09-03, `release/0.15`, this machine, this repo's corpus)

| what | time |
|---|---|
| `uv run` overhead alone (`uv run python -c "pass"`) | 0.049s |
| `import squads` | 0.072s |
| `.venv/bin/sq --version` (no uv in the loop) | 0.740s |
| `.venv/bin/sq task 909 show` | 0.668s |
| `uv run sq check` (whole corpus) | 3.203s |

Neither `uv` nor importing the package is the cost — both are noise (0.049s
and 0.072s). There is roughly **0.7s of fixed work between "package
imported" and "simplest possible command answered"**: `sq --version` pays
essentially all of it (0.740s) while doing nothing beyond printing a string,
and `sq task 909 show` (0.668s) — real work — costs almost the same,
confirming the 0.7s sits before dispatch, not inside the command. That is
Typer app construction plus spec loading happening unconditionally on every
invocation, whether the command needs them or not.

## Context: relationship to daemon mode (not scope)

op-pierre's web-line sequence (EPIC-29) includes daemon logic, noted as
valuable for a *local* git-backed squad precisely because of this same
startup cost, not only for remote mode. These are complementary, not
alternatives: lazy-loading this fixed cost is a fraction of daemon-scale
work, and it lands the win for everyone, including anyone who never runs a
daemon. The daemon would then buy back the *remaining* per-call cost on top
of that, not the whole 0.7s — the cheap win does not depend on the daemon,
and the daemon does not make the cheap win unnecessary. See the measurement
comment on EPIC-29 for the number attached to that line.

## Context: `sq check`'s 3.2s is a separate problem (not scope)

`uv run sq check` over the whole corpus costs 3.203s — that is real
per-corpus work (every item, every rule), not startup: it is roughly 2.5s on
top of the ~0.7s fixed cost this feature targets. It deserves its own
attribution pass and is out of scope here.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 916 add-story "As a <role>, I want … so that …"`; track with `sq feature 916 story <n> update --status <Status>`._

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T13:32:06Z] Pierre Chat:
  - Held, not in 0.15. Neither is gated on the web API or the daemon -- both are local CLI work that lands independently -- but 0.15 already carries two full lines and nothing forces these early. Picked up in a later release, or alongside the daemon work when the startup cost starts hurting enough to act on. The measurements are on the record; that was the point of writing them down.
<!-- sq:discussion:end -->
