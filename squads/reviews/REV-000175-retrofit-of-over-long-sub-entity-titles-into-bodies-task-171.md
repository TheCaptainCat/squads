---
id: REV-175
sequence_id: 175
type: review
title: Retrofit of over-long sub-entity titles into bodies (TASK-171)
status: Approved
author: reviewer
refs:
- TASK-171:addresses
created_at: '2026-06-23T10:05:27Z'
updated_at: '2026-06-23T10:06:05Z'
---
<!-- sq:body -->
Independent sampling review of TASK-171 (corpus retrofit: over-long sub-entity titles moved into bodies, titles shortened to handles).

## Verdict: Approved

## Objective gate — PASS
- `uv run sq check` exits 0; `sq check --json` returns []. Zero over-long-title advisories, zero errors.

## Integrity — PASS
- Rebuilt the index from frontmatter in a temp copy and diffed against the live .squads.json: zero diffs in any sub-entity title or body (only unrelated can_spawn role fields and a 0.4.0->0.4.1 version stamp). Frontmatter<->index stayed consistent across all 107 edits.

## Sample (12 sub-entities, all three types) — CLEAN
- REV-048 F1-F4, REV-097 F5 (781c worst-case offender), FEAT-62 US1/US2, FEAT-26 US4/US5, TASK-63 ST1-ST3.
- No information loss: original long-title prose recovered verbatim (or faithfully) into the sub-entity body in every sampled case; REV-097 F5's full 781 chars preserved.
- Titles are now real handles: short (all <=70 chars), meaningful, not truncated mid-word.

## Collateral-mutation gate (whole corpus, not just sample) — CLEAN
- git diff scan across all touched feature/task/review .md files: zero sub-entity status/severity changes, zero parent item status changes, zero sq marker lines added/removed. Pre-existing bodies appended-to, not clobbered (41 placeholder->prose clean fills).

No findings.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 175 add-finding "…" --severity high`; track with `sq review 175 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
