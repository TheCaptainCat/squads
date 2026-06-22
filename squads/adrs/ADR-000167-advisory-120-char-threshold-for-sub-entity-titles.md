---
id: ADR-000167
sequence_id: 167
type: decision
title: Advisory 120-char threshold for sub-entity titles
status: Proposed
author: architect
refs:
- FEAT-000166
description: Warn-and-proceed above 120 chars on finding/subtask/story titles; no
  body gating
created_at: '2026-06-23T08:26:01Z'
updated_at: '2026-06-23T08:26:01Z'
---
<!-- sq:body -->
## Context

Sub-entity authors (review findings, task subtasks, feature stories) routinely
cram the full description into the **title** and leave the **body** as the
rendered placeholder. A corpus sweep found 107 empty/placeholder sub-entity
bodies (zero at the top-item level); 44 of those carry titles over 120 chars,
the worst being a 781-char finding title. See FEAT-000166 for the full data.

The title is meant to be a one-line **handle**, not the specification. We want
to insist on that without **gating body presence** — a short-title sub-entity
with no body is legitimately complete, so an empty body is not the signal to act
on. A long title is.

## Decision

Add a **single advisory threshold of 120 characters** on sub-entity titles.
Titles at or below 120 are silent; titles above 120 trigger an
**advisory, warn-and-proceed** message. This is not an error, not a gate, and
never blocks: the command creates the sub-entity and exits 0, mirroring the
`CreateResult.lane_warning` pattern from FEAT-000122 / ADR-000163.

- **Threshold value: 120 chars**, held as one module-level constant in
  `_interactions.py` (the home of the comparable `CREATE_LANES`). Not
  `.squads.toml`-configurable — tuning one number is cheaper than carrying the
  config surface; revisit only on demand.
- **Where it fires:** at authoring time on `add-finding` / `add-subtask` /
  `add-story`, and as an advisory `sq check` rule that audits the existing
  corpus (no migration, no auto-fix).
- **Body presence is never gated.** Empty bodies are not warned on or rejected.

## Rationale

120 is deliberately above the ambiguous 70–120 band. It fires only on the 44
unambiguous-prose titles and stays silent through every borderline case. This
protects the advisory's credibility: an alarm that goes off on legitimate
handles gets trained away and then fails to catch the 781-char offenders it
exists for. We accept letting the borderline middle through in exchange for a
warning people will actually heed.

## Warning copy

Advisory register — names the fix with real IDs, does not scold:

    Title is 213 chars — a sub-entity title is a one-line handle, not the
    description. Put the detail in the body:
      sq review 165 finding F1 body -m "…"

## Scope / consequences

- New constant + advisory check at the three `add-*` entry points.
- New advisory `sq check` rule (reported as advisory finding, not error; a
  previously-clean `sq check` still exits 0).
- Skill reinforcement in `sq-review` / `sq-task` / `sq-feature`: titles are
  handles, prose goes in the body.
- No breaking change: no new mandatory arguments, no exit-code change for
  previously-clean runs.

## References

- FEAT-000166 — the feature this decision governs.
- FEAT-000122 / REV-000165 / ADR-000163 — the advisory lane-warning pattern
  this mirrors.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
