---
id: REV-000094
sequence_id: 94
type: review
title: 'Review TASK-000084: golden-file harness freezing every --json shape'
status: Approved
author: reviewer
subentities:
- local_id: F1
  title: print_block (add-story/add-subtask/add-finding --json) emits the .md file
    location under key 'file', while read-side show --json emits the same path concept
    under 'path'. Both are the item's markdown file path; a JSON consumer must special-case
    the key per command. Documented in the module docstring per Catherine's REV-86
    carry-over (rename-or-document was sanctioned), and print_block is outside this
    task's frozen read surface — non-blocking. Recorded so a future consumer/contributor
    sees the asymmetry is deliberate, not accidental. Recommend revisiting file->path
    alignment when the write surface gets its own goldens.
  status: Open
  severity: low
created_at: '2026-06-12T21:23:52Z'
updated_at: '2026-06-12T21:24:17Z'
---
<!-- sq:body -->
Scope: golden-file test harness for TASK-000084 (US3 of FEAT-000015) — tests/test_golden_json.py + tests/goldens/ (24 snapshots, 25 tests). Read surface only; write-side print_block out of scope by design.

Verdict: Approved. Coverage complete, determinism proven byte-stable, drift-catching verified (hand-edit + source-shape mutation both fail the build), UPDATE_GOLDENS gated on explicit env var (never auto-heals).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 94 add-finding "…" --severity high`; track with `sq review 94 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | print_block (add-story/add-subtask/add-finding --json) emits the .md file location under key 'file', while read-side show --json emits the same path concept under 'path'. Both are the item's markdown file path; a JSON consumer must special-case the key per command. Documented in the module docstring per Catherine's REV-86 carry-over (rename-or-document was sanctioned), and print_block is outside this task's frozen read surface — non-blocking. Recorded so a future consumer/contributor sees the asymmetry is deliberate, not accidental. Recommend revisiting file->path alignment when the write surface gets its own goldens. |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — print_block (add-story/add-subtask/add-finding --json) emits the .md file location under key 'file', while read-side show --json emits the same path concept under 'path'. Both are the item's markdown file path; a JSON consumer must special-case the key per command. Documented in the module docstring per Catherine's REV-86 carry-over (rename-or-document was sanctioned), and print_block is outside this task's frozen read surface — non-blocking. Recorded so a future consumer/contributor sees the asymmetry is deliberate, not accidental. Recommend revisiting file->path alignment when the write surface gets its own goldens.

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
_Describe the finding, its impact, and a recommendation — free-form._
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T21:24:17Z] Paul Reviewer:
  - Approved. Coverage: all 16 read-side --json emitters pinned (9 in _main: list/tree/inbox/search/blocked/workload/mine/show/check; item show+refs+sub-entity list covering stories/subtasks/findings; role catalog+show; skill show; operator show). The only unpinned --json flags are write/mutation commands (create, create guide, add-story/subtask/finding via print_block) — correctly out of scope for a read-shape freeze.
  - Determinism: byte-stable — two independent UPDATE_GOLDENS regenerations are identical and match the committed goldens exactly. Time frozen (2026-06-07T10:00:00Z), id counter pinned (ROLE-000001..OP-000009), no *-dev role activated so the random name pool is never exercised. Paths in goldens are squad-relative (tasks/TASK-...md), not absolute /tmp — no path flake.
  - Drift-catching verified two ways: a hand-edited golden and a source-side shape mutation both fail with a clear UPDATE_GOLDENS regeneration message; default mode compares, never auto-heals. F1 (low, non-blocking): documented file/path key asymmetry on the write side. pyright/ruff errors in the tree are all in the unrelated override-loader files (_resolver.py/_base.py/_roster.py) — TASK-84 files are clean.
<!-- sq:discussion:end -->
