---
id: ADR-77
sequence_id: 77
type: decision
title: Time is injectable through a single clock module
status: Accepted
author: architect
refs:
- GUIDE-79
description: All timestamps route through _clock.now()/iso(); freezable in tests and
  forgeable via --at for history-preserving adoption
created_at: '2026-06-12T14:23:17Z'
updated_at: '2026-08-03T08:41:18Z'
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

## Provenance

Recorded retroactively. This decision predates squads tracking itself and lived only in `CLAUDE.md`
(the "time is injectable" gotcha) and `docs/internals.md` (§10). It is documented here as a decision
already **in force**, not newly debated in-tool. Included as an optional standing call of the same
rank as the core six.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:41:18Z] Robert Architect:
  - Dropped the "Left **Proposed** for the manager to accept with the set" closer and retitled the section from "Status note" to "Provenance". Status prose in a body is forbidden here and this one had been false since the day the set was accepted. The provenance itself is kept and is worth keeping — this decision predates squads tracking itself and lived only in CLAUDE.md and docs/internals.md, which is why the body reads retroactively. Part of one sweep across the ten retroactive decisions (49, 71-78, 85), not ten tickets.
  - Verified in force, nothing else owed: `clock.now`/`clock.iso`, `set_now`, the global `--at` at `_cli/__init__.py:308`, and zero `datetime.now()` calls anywhere in `src/squads/`. ADR-534 moved the override out of a module global into the request context and explicitly preserves this decision; this body never named the module global, so nothing in it is falsified — which is why it needs no narrowing where ADR-117 did.
<!-- sq:discussion:end -->
