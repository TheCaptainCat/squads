---
id: BUG-698
sequence_id: 698
type: bug
title: A foundation skill can be archived, with nothing refusing or reporting it
status: Verified
author: architect
priority: high
refs:
- ADR-697:addresses
description: The roster status verb shipped before its config-integrity guards; sq
  check stays silent
created_at: '2026-07-29T16:20:12Z'
updated_at: '2026-07-31T12:41:40Z'
---
<!-- sq:body -->
The roster status verb accepts any lifecycle-valid transition on a roster entry, including retiring a skill that every role preloads. In a fresh squad, `sq skill squads status Archived` succeeds and `sq check` then reports no issues, leaving a squad whose generated role entries all preload a skill whose own status says it is retired.

The transition-time clauses that would refuse this are decided but not implemented. Two distinct gaps: the gate (refuse the transition) and the reporter (notice a squad already in that state, since the clauses gate transitions and cannot see existing state). The reporter is needed regardless of when the gate lands, because any squad transitioned before the gate exists keeps the invalid state and the convergence sweep faithfully projects it.

Verified on the current build in a throwaway squad: transition accepted (SKILL-18 to Archived), check clean afterwards.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T16:20:15Z] Pierre Chat:
  - Scheduled for 0.13 — the verb shipped in this release, so the guard and the validator belong in it too.
- [2026-07-29T16:20:34Z] Catherine Manager:
  - Correction: the preceding 0.13 scheduling comment was recorded under the operator's name in error — he has not ruled on this bug's milestone. It is my recommendation only: the verb shipped in 0.13, so the guard and the validator arguably belong in the same release. Awaiting his call.
- [2026-07-29T16:28:46Z] Pierre Chat:
  - 0.13. The verb shipped in this release, so the guard and the validator ship with it.
- [2026-07-30T07:53:11Z] Olivia Lead:
  - Both halves are cut and linked as fixes: TASK-700 is the reporter (urgent, and per ADR-697 it can land independently of the gate), TASK-701 is the gate. Left in Draft for the dispatch gate.
  - The repro recorded here is a named acceptance criterion on TASK-700/ST4 — the fresh squad whose always-on skill was archived before the guard existed must be caught by the validator afterwards.
<!-- sq:discussion:end -->
