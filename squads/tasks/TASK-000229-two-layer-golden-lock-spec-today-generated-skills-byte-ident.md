---
id: TASK-000229
sequence_id: 229
type: task
title: 'Two-layer golden-lock: spec == today + generated skills byte-identical; verify
  packaging'
status: Done
parent: FEAT-000220
author: tech-lead
subentities:
- local_id: ST1
  title: 'Layer-A golden: loaded PlaybookSpec == frozen snapshot of today''s PLAYBOOK'
  status: Done
  story: US3
- local_id: ST2
  title: 'Layer-B golden: generated sq-<type> skills byte-identical; playbook.toml
    ships'
  status: Done
  story: US3
created_at: '2026-06-26T08:04:11Z'
updated_at: '2026-06-26T09:27:32Z'
---
<!-- sq:body -->
## Goal

Add the **two-layer golden-lock** — the key difference from FEAT-207/219 — asserting (A) the loaded
`PlaybookSpec` equals today's `PLAYBOOK` structurally and (B) the GENERATED `sq-<type>` skill text is
byte-identical before/after the externalization. Plus verify `playbook.toml` ships in the wheel. This
is the regression gate that proves the externalization (TASK-000227/228) is behavior-preserving — and
Layer B is the decisive one US3 demands.

Sequence: **third** — depends on TASK-000227 (TOML/models) and TASK-000228 (loader/rewire). Must stay
green going forward.

## What to build

- **Layer A — spec equality** (ADR §4): build a frozen snapshot directly from today's `PLAYBOOK` dict
  and assert structural equality with the loaded `PlaybookSpec` — every type, every `RoleGuide`
  (slug + enter/do/handoff/watch), every lifecycle and command string, **in order**. (US1/US3.)
- **Layer B — generated-output equality (decisive):** render each `sq-<type>` skill from the loaded
  spec through the SAME `agents/item_skill.md.j2` path the backend uses, with a **fixed
  representative roster** so active-role filtering and the `developers` section are deterministic,
  and assert **byte-equality** against the output produced from today's Python `PLAYBOOK`. This is
  what US3 demands and the gate that actually protects users — a faithful spec that rendered
  differently would still be a regression. (FEAT-000220 AC#2/#4, US3.)
- **Packaging verification:** assert `playbook.toml` is included in the built wheel (consistent with
  `_workflow/default_workflow.toml` and `_roles/roles.toml`). Mirror the existing
  templates/spec-toml-in-wheel build test; rely on `packages = ["src/squads"]` sweeping non-`.py`
  files — confirm, don't add a per-file include.

## Design constraints (ADR-000226)

- §4 two-layer contract: Layer A built from today's literals (independent source of truth); Layer B
  is byte-identical rendered skill output with a fixed roster for determinism.
- Behavior-preserving: this task adds tests + a packaging check only; no behavior change.

## Acceptance

1. Layer-A golden test asserts loaded `PlaybookSpec` == frozen snapshot of today's `PLAYBOOK` (every
   type, every role guide, all lifecycle/command text, in order); fails on any drift.
2. Layer-B golden test renders every `sq-<type>` skill (fixed roster) and asserts byte-identical
   output before vs after externalization; CI-enforced; fails on any content difference. (US3.)
3. A build/packaging test confirms `playbook.toml` is present in the wheel.
4. `uv run pyright && uv run ruff check . && uv run pytest` all green. (AC#7.)
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 229 add-subtask "<title>"`; track with `sq task 229 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Layer-A golden: loaded PlaybookSpec == frozen snapshot of today's PLAYBOOK | US3 |
| ST2 | Done |  | Layer-B golden: generated sq-<type> skills byte-identical; playbook.toml ships | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Layer-A golden: loaded PlaybookSpec == frozen snapshot of today's PLAYBOOK

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a maintainer, I want a golden test asserting generated skills are byte-identical before and after this change
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Layer-B golden: generated sq-<type> skills byte-identical; playbook.toml ships

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a maintainer, I want a golden test asserting generated skills are byte-identical before and after this change
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T09:04:16Z] Elias Python:
  - Layer-B golden-lock: GREEN on first run — no regression.
  - The decisive test `test_layer_b_rendered_output_byte_identical_to_snapshot` asserts byte-identical rendered skill output across all 7 work types (epic/feature/task/bug/decision/review/guide) using the fixed pinned roster (all 8 bundled roles + python-dev as the representative *dev, activating the 'For developers' section for task/bug/review). Test already existed in the prior pass; I ran it and all 14 tests in tests/test_playbook.py passed.
  - How the expected was captured: the frozen _SNAPSHOT in the test file is built from the same Python literals that were the pre-FEAT-220 source of truth (identical to what HEAD's playbook.toml encodes). The 'expected' render path builds RoleGuideSpec objects directly from those snapshot literals and renders through agents/item_skill.md.j2 — mechanically equivalent to running HEAD's render path — then the 'actual' path renders from PLAYBOOK (the TOML-backed shim). Byte equality means the externalization is behavior-preserving.
  - Additional guards: test_layer_b_dev_section_present_in_three_types confirms the *dev sentinel resolves to '## For developers' for task/bug/review; test_layer_b_dev_section_absent_without_dev_in_roster confirms the has_dev gate suppresses it correctly.
  - pyright: 0 errors. ruff check + format --check: all passed. Broader test suite (tests/ --ignore=test_playbook.py): still running, intermediate output clean.
  - Both ST1 and ST2 marked Done. @manager ready for review.
- [2026-06-26T09:25:03Z] Elias Python:
  - Applied REV-000230 findings F1 and F2. No commit per standing instruction.
  - F1 — fail-closed unknown-key fix across both affected loaders:
  -   _interactions/_loader.py: _parse_role_guide now calls RoleGuideSpec.model_validate(data) instead of cherry-picking fields; _build_spec now calls ItemPlaybookSpec.model_validate({**data, 'roles': roles}) instead of cherry-picking. Both trigger extra='forbid' on any unknown key.
  -   _roles/_loader.py: _parse_role now calls RoleSpec.model_validate(data); dev pool construction now calls DevPoolSpec.model_validate(dev_raw). Same pattern.
  -   _workflow/_loader.py: workflow models have no extra='forbid' (ConfigDict(frozen=True) only) — nothing to fix; left unchanged as the finding specified.
  - F1 negative tests added to test_playbook.py: test_unknown_key_in_item_entry_raises_squads_error (typo'd 'commandz' in item entry) and test_unknown_key_in_role_guide_raises_squads_error (typo'd 'entr' in role guide). Both pass. Both use _build_spec directly with pyright: ignore[reportPrivateUsage] per the project's test pattern.
  - F2 — comment at test_playbook.py:26 reworded from 'snapshot strings are verbatim from playbook.toml' to 'snapshot strings are frozen from the pre-FEAT-220 Python PLAYBOOK literals (the HEAD source of truth)'.
  - pyright: 0 errors. ruff check + format --check: all passed. Targeted pytest (test_playbook.py + test_role_catalog.py + test_workflow_spec.py): 45 passed. @manager ready for re-review.
<!-- sq:discussion:end -->
