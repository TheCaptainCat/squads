---
id: REV-52
sequence_id: 52
type: review
title: FEAT-000035 — typed ref vocabulary
status: Approved
author: reviewer
refs:
- FEAT-35:addresses
subentities:
- local_id: F1
  title: Function-local Status import in _check_decisions; hoist to module top
  status: Open
  severity: low
created_at: '2026-06-11T20:41:00Z'
updated_at: '2026-06-23T09:59:39Z'
---
<!-- sq:body -->
Formal review of FEAT-35 (typed ref vocabulary) — TASK-50 (VALID_REF_KINDS constant + validation at add_ref and ServiceCore.create) and TASK-51 (depends-on≡blocks in sq blocked, sq check unknown-kind + Superseded-without-supersedes warnings, eight-row kinds table in workflow.md.j2, refreshed --kind help). Reviewed the full working-tree diff against acceptance criteria, ADR-49 conformance, CLAUDE.md invariants, and quality. Gates green; live spot-checks pass.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 52 add-finding "…" --severity high`; track with `sq review 52 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Function-local Status import in _check_decisions; hoist to module top |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Function-local Status import in _check_decisions; hoist to module top

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Style: _check_decisions() in _maintenance.py uses a function-local 'from squads._models._enums import Status' (line ~332) when ItemType is already imported from that same module at the top. Hoist Status to the module-level import for consistency. Non-blocking — no cycle, gates clean.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T20:43:10Z] Paul Reviewer:
  - VERDICT: Approved. Both tasks meet acceptance, conform to ADR-49, and respect every CLAUDE.md invariant. No blocking findings.
  - Acceptance verified live: unknown --kind (banana, typo fixe, embedded ID:banana) rejected exit 1 listing all eight kinds; create --ref ID:banana rejected; all eight accepted; bare ref add stays related (frictionless). depends-on shows in sq blocked with correct direction (dependent blocked by blocker); mixed blocks+depends-on dedups (item once, union of blockers); same-pair via both spellings appears once. sq workflow shows the single eight-row kinds table (meaning/direction/consumer) matching the ADR's direction conventions verbatim; --kind help points at it. check warns (exit 0) on unknown kinds naming item+edge and on Superseded decisions lacking an incoming supersedes edge.
  - ADR-49: vocabulary lives in ONE place (VALID_REF_KINDS in _models/_item.py). The only kind literals left in src/ are legitimate consumer dispatch points — blocked() matching blocks/depends-on, _check_decisions matching supersedes — which must name the kind they consume. No config lookup on the validation path; flat set-membership throughout.
  - Invariants: SquadsError raised at both authoring surfaces (caught by @handle_errors); pyright strict + ruff clean; frontmatter untouched (kinds additive, schema 0.3, no migration); depends-on and supersedes inversions are computed in-memory per call, never persisted (backref invariant held); refs via split_ref/make_ref only; workflow table is static markdown (StrictUndefined-safe); no datetime.now().
  - Gates: pytest all pass (1 skip, pre-existing); pyright 0 errors; ruff check passes; ruff format clean. sq check clean on this squad.
  - One non-blocking low finding (F1): _check_decisions uses a function-local Status import where the module already imports ItemType from _enums — hoist for consistency. Not a release blocker.
<!-- sq:discussion:end -->
