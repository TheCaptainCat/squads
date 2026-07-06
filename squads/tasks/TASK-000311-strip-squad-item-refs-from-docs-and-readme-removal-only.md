---
id: TASK-311
sequence_id: 311
type: task
title: Strip squad-item refs from docs/ and README (removal only)
status: Done
parent: FEAT-237
author: tech-lead
assignee: python-dev
priority: medium
subentities:
- local_id: ST1
  title: Remove refs from docs/README (no rewording)
  status: Done
  assignee: python-dev
  story: US4
- local_id: ST2
  title: Preserve legit CLI-syntax / example payloads
  status: Done
  assignee: python-dev
  story: US4
created_at: '2026-07-06T12:55:26Z'
updated_at: '2026-07-06T14:06:17Z'
---
<!-- sq:body -->
USER-FACING WAVE. Scope: docs/*.md + README.md (ref-bearing: adoption, agents, internals, recipes, stability, tutorial, workflow, docs/README, README.md). Blast radius: ~116 ref-hits across 9 files. REMOVAL ONLY — strip the reference and let the guarantee stand on its own terms; do NOT reword or restyle the surrounding prose (product content). Disjoint from src/ and bundled-prose tasks — parallel-safe. Done when: zero real-citation squad-item refs remain; the diff is reference removals only (no sentence rewrites); legitimate CLI-syntax templates (--parent FEAT-…, sq task <n>) and illustrative example payloads (e.g. a recipe's example BUG id) are preserved and confirmed as non-violations for the guard.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 311 add-subtask "<title>"`; track with `sq task 311 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Remove refs from docs/README (no rewording) | US4 |
| ST2 | Done | python-dev | Preserve legit CLI-syntax / example payloads | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Remove refs from docs/README (no rewording)

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US4 — User-facing content carries no squad-item references
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Strip every real-citation squad-item ref from docs/*.md and README.md; state the guarantee on its own terms. REMOVAL ONLY — do not reword, shorten, or restyle the surrounding prose; the diff must be reference removals only. Covers the 'shipped docs must not cite internal items' principle. Done when: grep of the ref pattern over docs/ + README.md returns zero real citations, and a diff review confirms no sentence-level rewrites.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Preserve legit CLI-syntax / example payloads

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US4 — User-facing content carries no squad-item references
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Do NOT strip legitimate non-references: CLI-syntax templates (--parent FEAT-…, sq task <n>) and illustrative example payloads (e.g. a recipe's sample id, a reflog JSON sample). Confirm each surviving id-shaped token is a shape/example, not a citation of a real tracked item, so it is a valid non-violation for the guard. Done when: recipes/tutorial examples still render as valid illustrative shapes and each surviving token is confirmed non-citing.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T14:06:17Z] Elias Python:
  - Stripped squad-item refs from docs/*.md + README.md (removal only, no rewording): converted standalone/reference-doc examples (agents.md, workflow.md, README.md, stability.md, internals.md, docs/README.md) to non-digit placeholder tokens (FEAT-<n>, TASK-<n>, BUG-<n>, USn, STn, TASK-NNNNNN for the zero-padded filename shape) so no digit-bearing squad-item token remains.
  - Deliberately kept as illustrative (non-citing) CLI-output examples, per the task's own carve-out: docs/tutorial.md, docs/recipes.md, docs/adoption.md — each is a coherent, self-consistent worked walkthrough (fictional 'auth' feature) using concrete EPIC/FEAT/TASK/BUG/REV/ADR numbers exactly as sq would print them; recipes.md already discloses 'IDs are illustrative — use the ones sq prints'. None cites a real tracked item in this repo's own history.
  - Verification: git diff added-line grep for the ref pattern over docs/+README.md is empty (only untouched files still contain matches, all confirmed illustrative above); pyright/ruff check/ruff format all clean; no external/GitHub URLs introduced.
  - ST1 and ST2 done; task Done.
<!-- sq:discussion:end -->
