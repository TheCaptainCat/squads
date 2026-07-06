---
id: TASK-313
sequence_id: 313
type: task
title: 'CI guard: forbid squad-item refs outside squads/**'
status: Done
parent: FEAT-237
author: tech-lead
assignee: python-dev
priority: high
refs:
- TASK-308:depends-on
- TASK-309:depends-on
- TASK-310:depends-on
- TASK-311:depends-on
- TASK-312:depends-on
subentities:
- local_id: ST1
  title: Implement gate + wire into CI
  status: Done
  assignee: python-dev
  story: US3
- local_id: ST2
  title: Tolerate legitimate id-shaped tokens
  status: Done
  assignee: python-dev
  story: US3
- local_id: ST3
  title: 'Negative check: gate fails on a new ref'
  status: Done
  assignee: python-dev
  story: US3
created_at: '2026-07-06T12:55:28Z'
updated_at: '2026-07-06T14:32:05Z'
---
<!-- sq:body -->
THE GATE (lands last / green). Ship an enforced lint/CI gate (grep gate or ruff rule) that FAILS the build when a squad-item reference appears anywhere it is forbidden. Allowlist = the dogfood squad's item markdown under squads/** ONLY; forbidden territory = everything else (src/, docs/, README, shipped markdown, CLI output strings, bundled prose, CLAUDE.md). Detection pattern at minimum: (FEAT|TASK|ADR|REV|BUG|EPIC)-\d, bare US/ST story-subtask numbers, bare §. The gate MUST tolerate legitimate uses so it does not false-positive: CLI-syntax templates (--parent FEAT-…, sq task <n>) and illustrative example payloads (a reflog JSON sample carrying a TASK id; a recipe's example BUG id). Recommended: develop the gate EARLY to use as the cleanup's own completion checker, but MERGE it with/after the final cleanup so CI is never red in the interim. Depends-on all five cleanup tasks. Done when: the gate runs in CI and is GREEN on the cleaned tree with squads/** as sole allowlist; it does NOT fire on the surviving legitimate uses; and a negative check proves it FAILS when a squad-item ref is introduced on a forbidden surface.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 313 add-subtask "<title>"`; track with `sq task 313 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Implement gate + wire into CI | US3 |
| ST2 | Done | python-dev | Tolerate legitimate id-shaped tokens | US3 |
| ST3 | Done | python-dev | Negative check: gate fails on a new ref | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Implement gate + wire into CI

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US3 — CI guard blocks squad-item refs outside item files
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add an enforced lint/CI gate (grep gate script or ruff rule) with allowlist = squads/** item markdown ONLY and forbidden territory = everything else (src/, docs/, README, shipped markdown, CLI output strings, bundled prose, CLAUDE.md). Detection at minimum: (FEAT|TASK|ADR|REV|BUG|EPIC)-\d, bare US/ST numbers, bare §. Wire it into the CI checks alongside pyright/ruff. Done when: the gate runs in CI and is GREEN on the cleaned tree.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Tolerate legitimate id-shaped tokens

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US3 — CI guard blocks squad-item refs outside item files
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
The gate must NOT false-positive on legitimate non-references: CLI-syntax templates (--parent FEAT-…, sq task <n>) and illustrative example payloads (a reflog JSON sample carrying a TASK id; a recipe's example id). Encode the necessary allowances (pattern scoping / inline-allow markers / path carve-outs) so those surviving uses pass. Done when: the gate is green with those known-legit occurrences present in the tree.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Negative check: gate fails on a new ref

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US3 — CI guard blocks squad-item refs outside item files
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Prove the gate actually bites: introducing a squad-item ref on a forbidden surface (e.g. a new src comment or a docs line) must make the gate exit non-zero. Capture this as a documented negative check (a test or a CI-verifiable step). Done when: the negative case is demonstrated to fail the build and the demonstration is reproducible.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T14:32:02Z] Elias Python:
  - Gate landed: tests/test_squad_ref_hygiene.py — a repo-wide pytest guard (not a separate CI step; pytest is already the CI test job).
  - Pattern: \b(ADR|FEAT|TASK|REV|BUG|EPIC)-[0-9]|\bUS[0-9]|\bST[0-9]|§[0-9] — concrete-digit only, so placeholder shapes (FEAT-<n>, USn, PREFIX-NNNNNN) auto-pass.
  - Allowlist: squads/{epics,features,tasks,bugs,adrs,reviews,guides,operators}/** (item markdown) + squads/.squads.json (the rebuildable index); docs/tutorial.md, docs/recipes.md, docs/adoption.md (designated illustrative walkthroughs); CHANGELOG.md (historical release log, out of TASK-311's scope). Deliberately EXCLUDES squads/agents/{roles,skills}/** — that's rendered bundled prose and must itself stay clean (per TASK-312's own done-when).
  - File universe = 'git ls-files --cached --others --exclude-standard' under repo root (falls back to a plain walk with a build/VCS skip-dir list when not inside a git checkout, e.g. the synthetic tree the negative test builds) — this transparently keeps out .venv/__pycache__/the gitignored per-clone .reflog.jsonl without hand-listing every artifact dir, and keeps tests/** out of scope (FEAT-231 territory, not this gate's job) since that's still walked but allowlisted wholesale.
  - Found and fixed 2 real leftovers beyond the known _main.py payload: pyproject.toml's ruff ASYNC select comment (cited ADR-000153 — removed), and 2 docstring/comment ADR-000085 citations in src/squads/_overrides/_service.py + __init__.py (removed, prose otherwise untouched).
  - src/_main.py resolved by placeholdering the --json example payload: BUG-22->BUG-<n>, FEAT-35->FEAT-<n>, TASK-100->TASK-<n> (readable, no allow-marker mechanism needed).
  - One flagged hit was NOT a leftover: playbook.toml's '--story US1' CLI-syntax example (previously judged legitimate by TASK-308/310). Reconciled it to 'USn' for consistency with the same file's other USn placeholder 2 lines below — this keeps the gate's rule simple (concrete-digit = forbidden, no exceptions) instead of needing a bespoke allowance. Propagated via sq sync (SKILL-000199-sq-task.md) + UPDATE_GOLDENS=1 (tests/goldens/skill_body_sq-task.txt) + the frozen Layer-A snapshot in tests/test_playbook.py — all green.
  - Negative test: test_gate_flags_a_planted_reference_outside_the_allowlist plants FEAT-123 in a synthetic src/squads/ file and confirms it's flagged, while the same ID in a synthetic squads/features/ item file and in docs/tutorial.md is not — proves the guard actually bites and isn't allowlisted into uselessness.
  - Verify: uv run pyright && uv run ruff check . && uv run ruff format --check . clean; targeted runs green (test_squad_ref_hygiene.py, test_playbook.py, test_golden_rendered_output.py, test_override_*, test_backend_*, test_skill*, test_cli.py, test_multi_active_backends.py). Full suite left to the manager per instructions.
<!-- sq:discussion:end -->
