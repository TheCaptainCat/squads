---
id: ADR-000077
sequence_id: 77
type: decision
title: Time is injectable through a single clock module
status: Accepted
author: architect
refs:
- GUIDE-000079
description: All timestamps route through _clock.now()/iso(); freezable in tests and
  forgeable via --at for history-preserving adoption
created_at: '2026-06-12T14:23:17Z'
updated_at: '2026-06-12T14:29:32Z'
---
<!-- sq:body -->
## Context

squads stamps timestamps everywhere — `created_at`, `updated_at`, comment headers, status changes —
and two needs pulled against a naive `datetime.now()`. First, the test suite has to assert exact
generated content (frontmatter, comment lines), which is impossible if every run embeds the wall
clock. Second, adopting an existing project means re-creating its history with the *original* dates,
not today's. Both needs require time to be something the system can be told, not something it reads
directly.

The call was to route every timestamp through one injectable clock, so a test can freeze it and a
migration or adoption can forge it for a single invocation.

## Decision

**Time is injectable through `_clock`.** All timestamps come from `clock.now()` / `clock.iso()`;
nothing in the codebase calls `datetime.now()` directly. `set_now(dt)` overrides `now()` for one CLI
invocation, which is how the global `--at WHEN` option forges historical dates across
`create`/`status`/`comment` during adoption, and how the `frozen_time` test fixture pins the clock so
generated files are deterministic.

## Consequences

What this binds today:

- **No direct `datetime.now()` anywhere.** Every timestamping path goes through `_clock`; a new
  feature that records a time uses `clock.now()`/`clock.iso()` or it is wrong by construction.
- **`--at` and adoption depend on this.** History-preserving adoption (re-creating items with their
  original dates) works only because the single invocation can set the clock; this is the mechanism,
  not a convenience.
- **Tests stay deterministic.** Frozen time is what lets the suite assert exact frontmatter and
  comment content; breaking the single-clock rule would make those assertions flaky.

## Status note

Recorded retroactively. This decision predates squads tracking itself and lived only in `CLAUDE.md`
(the "time is injectable" gotcha) and `docs/internals.md` (§10). It is documented here as a decision
already **in force**, not newly debated in-tool. Included as an optional standing call of the same
rank as the core six. Left **Proposed** for the manager to accept with the set.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
