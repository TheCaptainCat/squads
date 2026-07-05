---
id: TASK-275
sequence_id: 275
type: task
title: 'F1 characterization golden: pin sq workflow + badges + blocked/list at HEAD'
status: Done
parent: FEAT-211
author: tech-lead
priority: high
refs:
- REV-284:addresses
created_at: '2026-07-02T09:20:17Z'
updated_at: '2026-07-02T10:22:07Z'
---
<!-- sq:body -->
## Goal (GATING — must land FIRST, against HEAD)

Author the characterization golden that pins every generated/computed surface FEAT-211
touches, **before any rewire**, so the whole feature runs under a passing guard. This is the
FEAT-220/REV-230 process rule: the proof is the first task, not a trailing one an agent can
abandon. Covers **AC#6** (F1 golden stays green — built-in statuses/badges unchanged).

## What to pin (all inputs frozen — roster, flags, clock)

Follow [[pin-roster-when-diffing-generated-skills]]: generated text is roster-dependent (the
`has_dev` gate), so hold the roster constant across before/after. Freeze `--at` / the
`frozen_time` fixture, and pass explicit flags — never rely on ambient state.

1. **`sq workflow` cheatsheet** — full rendered `workflow.md.j2` output for the **bundled**
   spec (byte-for-byte). This captures the current role→type authoring prose and the current
   hardcoded `workflow_static.md.j2` retype-target list, so TASK-279's spec-derivation of
   those must reproduce the same text for the bundled team. If we already have a HEAD golden in
   `tests/test_workflow_renderer_261.py`, extend/confirm it covers the exact regions 279 will
   touch; otherwise add one.
2. **Status badges** — for every built-in item status AND every sub-entity status, pin the
   badge the current code produces (`STATUS_EMOJI` for the 9 sub-entity statuses via
   `_discussion._status_badge`; note that top-level item statuses render with NO badge today).
   Assert the exact `sq <type> show` panel line (`status: <value>`) and the `sq list` Status
   column for a built-in item, plus a sub-entity head badge, so TASK-276 cannot silently
   change built-in output.
3. **`sq list` default filter + `sq blocked`** — pin, for the bundled spec, that a `Done`/
   `Cancelled` item is hidden by default and that `sq blocked` classifies open/closed as it
   does today (a small fixture squad with a blocks/depends-on edge).

## Acceptance

- New/extended tests live under `tests/` and are GREEN against **current HEAD** (no product
  code changed). They must FAIL if built-in cheatsheet text, a built-in badge, or the
  default-filter/blocked classification drifts.
- All inputs are pinned (roster fixed, clock frozen, flags explicit) — document this in the
  test module docstring so later tasks don't accidentally unpin them.
- This task's tests are the guard TASK-276/277/278/279 run under; they must stay green
  through the whole feature.

## Notes for implementer
- Existing golden scaffolding: `tests/test_workflow_renderer_261.py`, `tests/test_golden_json.py`.
- Do NOT pin the FEAT-013 static prose as "spec-derived" — it stays literal (see TASK-279).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 275 add-subtask "<title>"`; track with `sq task 275 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-02T09:36:46Z] Elias Python:
  - Golden characterization tests authored against HEAD (no product code touched): tests/test_task275_characterization.py — 39 tests, all green.
  - Pinned: (1) sq workflow cheatsheet — cross-checked the existing TASK-261 byte-identical golden (tests/goldens/workflow_cheatsheet.txt via render('workflow.md.j2', spec=bundled_spec())), which already gates this and has no roster/clock dependency; (2) status badges — all 9 sub-entity statuses' exact _discussion._status_badge text, plus the same text verbatim in a rendered sub-entity :head region on disk (subtask + finding, driven via --force to reach every value), and the STATUS_EMOJI domain-equality check; (3) top-level 'no badge today' invariant — sq show panel line and sq list (table + --json) render the plain status string with zero STATUS_EMOJI bytes present, per AC#3 ruling (b); (4) sq list default closed-item filter for every built-in top-level status (Draft/Ready/InProgress/InReview/Blocked open, Done/Cancelled hidden) plus --all always showing; (5) sq blocked — open dependent+blocker reported, cleared once either side reaches a terminal status, plus --json shape.
  - All fixtures init with --roles minimal (same roster as the shared project/svc fixtures) and use the frozen_time fixture — pinned per [[pin-roster-when-diffing-generated-skills]] even though none of these three surfaces are actually roster-sensitive (workflow.md.j2 is spec-only; badges/list/blocked are pure status-machine surfaces) — documented in the module docstring so later tasks don't unpin it.
  - Verified: uv run pytest tests/test_task275_characterization.py -q -> 39 passed. Also re-ran alongside test_workflow_renderer_261.py + test_workflow_spec.py -> all green together. uv run pyright tests/test_task275_characterization.py -> 0 errors. uv run ruff check + ruff format --check -> clean.
  - Everything requested was deterministically pinnable — nothing skipped. Moving to InReview for @reviewer; TASK-276/277/278/279 must keep this file green throughout the FEAT-211 rewire.
- [2026-07-02T09:40:27Z] Elias Python:
  - Naming fix per op-pierre: sq item IDs must not appear in code/filenames. Renamed tests/test_task275_characterization.py -> tests/test_status_display_characterization.py, and rewrote the module/class docstrings and comments to describe the pinned BEHAVIOR (status badge display, top-level no-badge invariant, sq list default filter, sq blocked classification, the sq workflow cheatsheet byte-identical golden) rather than citing TASK-275/FEAT-211/AC numbers — the tracking pointer lives only in this comment now.
  - Also fixed the unused frozen_time fixture arg: the pinned_squad fixture now asserts ROLE-1's created_at against the frozen timestamp right after init, so the clock freeze is exercised (load-bearing) rather than merely declared.
  - Re-verified after the rename: uv run pytest tests/test_status_display_characterization.py -q -> 39 passed; re-ran together with test_workflow_renderer_261.py + test_workflow_spec.py -> all green. uv run pyright tests/test_status_display_characterization.py -> 0 errors. uv run ruff check + ruff format --check -> clean.
  - @reviewer ready for review — file is tests/test_status_display_characterization.py.
- [2026-07-02T09:53:58Z] Paul Reviewer:
  - Reviewed the F1 gating golden — see REV-284 (ChangesRequested, 4 findings).
  - The COMMITTED golden (this task's deliverable at HEAD) is a VALID GATE and I recommend accepting it as the guard for the FEAT-211 rewire: 37 tests, green against HEAD, pyright/ruff clean, inputs pinned (minimal roster + frozen clock), and confirmed by mutation to catch a built-in badge-glyph change and an open/terminal misclassification. AC#3 reading-(b) no-top-level-badge invariant is pinned across sq show / sq list / --json.
  - The ChangesRequested is NOT about the golden's design — it's the WORKING-TREE state: the TASK-276 rewire (src/squads/_discussion.py, _cli/_common.py, _services/_subentities.py) is applied UNCOMMITTED, and this test file has 5 post-rewire custom-status tests added in-tree that FAIL against HEAD. That entangles the proof with the change (the FEAT-220/REV-230 anti-pattern the process rule forbids). Manager to sequence: keep the gate committed green-against-HEAD by itself; land the rewire + its 5 acceptance tests as a separate TASK-276 commit.
<!-- sq:discussion:end -->
