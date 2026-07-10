---
id: TASK-368
sequence_id: 368
type: task
title: Fix generated sq-<type> skill lifecycle and sub-entity trailers
status: Done
parent: FEAT-336
author: tech-lead
created_at: '2026-07-10T02:00:11Z'
updated_at: '2026-07-10T02:30:58Z'
---
<!-- sq:body -->
## Scope

Surface 4a of the REV-360 audit — the generated per-type `sq-<type>` skill correctness.
These are the HIGH current-behaviour bugs: the built-in-type skill render path produces
wrong text even on the bundled spec. Make the built-in branch derive lifecycle + trailer
from the active spec, matching what the custom-type branch already does. Files:
`_rendering/templates/agents/item_skill.md.j2`, `_backends/_claude_code/_backend.py`
(built-in render call ~226-234, custom at ~251), `_interactions/playbook.toml`; regenerate
the skill snapshots under `squads/agents/skills/`.

## Covered REV-360 findings

- HIGH (wrong on bundled spec — FIX FIRST) — `item_skill.md.j2:53` (built-in branch at
  `_backend.py:226-234` omits `subentity_kind`) — trailer hardcodes the literal triple
  "user stories / subtasks / findings" for EVERY type: prints for epic/decision/guide/bug
  (no matching sub-entity) and over-lists feature (story only) / task (subtask only) /
  review (finding only). The custom branch correctly passes `subentity_kind`. Pass the
  spec-resolved kind (or None) so each skill names only its actual sub-entity kind.
- HIGH — `_backend.py:232` renders `item_skill.md.j2:5` `**Lifecycle:**` from
  `lifecycle=pb.lifecycle` (FROZEN playbook prose) instead of the spec machine; the
  custom branch at `:251` correctly uses `linearize_lifecycle(ctx.spec.machine_for(...))`.
  Make the built-in branch symmetric so a status override on a kept built-in type yields
  a correct lifecycle line.
- MEDIUM — `_interactions/playbook.toml` (pervasive: `lifecycle=` lines
  12,56,115,191,242,275,320; cross-type ID prefixes 15,35,87,120,194,281; sub-entity
  verbs 59,88,278,291; axes 205,278,291) — root source feeding the two HIGHs above:
  frozen status/prefix/kind/axis strings duplicating the workflow machines + cross-type
  sibling references by name. Reduce/derive where the skill render should come from the
  spec; where playbook prose must stay hand-authored (enter/do/handoff/watch guidance),
  the fix is to stop rendering the frozen lifecycle string and derive it instead (above).
  Scope the playbook edits to what the skill-generation fix requires — a full playbook
  rewrite is not in scope.

## Ordering / flag

Contains the top current-behaviour bug (trailer over-listing). Recommend dispatching
this task first among FEAT-336.

## Dependency note

Regenerates `squads/agents/skills/SKILL-*` snapshots — shares that generated-snapshot
surface with the squads-skill/roles task; sequence the two (or have one own the regen)
to avoid snapshot merge conflicts.

## Acceptance

- Each `sq-<type>` skill trailer names only that type's actual sub-entity kind (none for
  epic/decision/guide/bug on the bundled spec); verified on bundled + a custom
  sub-entity-kind spec.
- Built-in-type Lifecycle line reflects the active status machine (verified by overriding
  a kept built-in type's statuses).
- Regenerated snapshots committed; `sq sync` re-render is stable; full gate green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 368 add-subtask "<title>"`; track with `sq task 368 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T02:17:03Z] Elias Python:
  - Fixed both HIGH bugs: built-in branch now derives Lifecycle from spec.machine_for(item_type) (falls back to the frozen playbook string only if the type was dropped from the active spec, guarding sq sync against a KeyError on a renamed-away built-in type) and passes the real spec.item_subentity_kind(item_type)/subentity_plural through, same as the custom branch.
  - Trailer now names only the type's actual kind: feature->stories, task->subtasks, review->findings; epic/decision/guide/bug (no sub-entity) drop the clause entirely. Regenerated all 7 sq-<type> snapshots + the matching golden .txt fixtures against this repo's real roster; spot-checked diffs are exactly the trailer/kind fix, no roster noise.
  - playbook.toml lifecycle= strings kept (not dropped) -- still load-bearing as the graceful-degradation fallback for a built-in type dropped/renamed out of the active spec.
  - Added 2 tests in test_skills.py: trailer names only the real kind (bundled spec), and Lifecycle line reflects an overridden status machine on a kept built-in type. Fast gates green: pyright, ruff check, ruff format --check, plus targeted skill/backend/rendering/playbook/golden/conformance/ref-hygiene tests (169 passed). Did not touch playbook.toml prose, squads_skill.md.j2, or roles.toml (TASK-369 territory). Full suite left for the main loop.
- [2026-07-10T02:22:51Z] Paul Reviewer:
  - Reviewed uncommitted TASK-368 diff (independent). VERDICT: CHANGES-REQUESTED — the fix itself is correct and high-quality, but the FULL SUITE IS RED: this change edits a bundled template without regenerating the template manifest.
  - F1 (BLOCKER): test_override_commands.py::test_manifest_freshness_all_bundled_templates FAILS — 'manifest v0.7.0 has stale hashes for: agents/item_skill.md.j2 (manifest=ee63225db6c9 actual=219ca41406e5)'. The template edit (item_skill.md.j2) changed its bytes but scripts/gen_template_manifest.py wasn't re-run, so the packaged-template manifest is stale. Fix: run wrote manifest for v0.7.0: 25 template hashes → src/squads/_rendering/templates_manifest.json, commit the refreshed manifest, re-verify the full suite green. (This is the only failure — 1 FAILED, everything else green.)
  - The FIX is otherwise correct — all three focus questions are YES. Snapshots CORRECT: epic/decision/guide/bug dropped the bogus 'user stories/subtasks/findings' clause entirely; feature names only stories (sq feature <n> story <k> ...), task only subtasks, review only findings, each with the real verb (goldens + SKILL-*.md match). Lifecycle BYTE-IDENTICAL on bundled: no **Lifecycle:** line changed in any snapshot; linearize_lifecycle(spec.machine_for(type)) reproduces the frozen pb.lifecycle for built-ins. The backend built-in branch is now symmetric with the custom branch.
  - Dropped-type fallback SOUND: the loop iterates managed_item_types()=list(PLAYBOOK) (frozen), so a dropped/renamed type is still rendered; item_subentity_kind returns None for it (no crash) and the  guard avoids machine_for KeyError, degrading to the frozen prose. Correct by construction. Roster NOT drifted (SKILL-feature.md diff is trailer-only, role sections untouched). No ticket IDs in source. The override-lifecycle test is genuine (points task at the guide machine, asserts the derived Lifecycle line).
  - LOW (dev's own flag, non-blocking): the dropped-type else-branch is reachable+correct but untested end-to-end (only the kept-type override case is). A thin test — drop a built-in type from the spec, refresh managed, assert sq-<type> still renders with the frozen pb.lifecycle and no sub-entity clause (no crash) — would cover it. Add alongside the manifest regen if convenient.
- [2026-07-10T02:23:02Z] Paul Reviewer:
  - Correction (backticks dropped a phrase from the dropped-type bullet): the fallback is SOUND. The loop iterates managed_item_types() = list(PLAYBOOK), which is frozen, so a dropped or renamed built-in type is still rendered. item_subentity_kind returns None for a type absent from the spec (no crash, trailer clause omitted), and the guard reading 'linearize when item_type is in spec.items, else the frozen pb.lifecycle' avoids a machine_for KeyError, degrading to the frozen prose. Correct by construction; roster not drifted (SKILL-feature.md diff is trailer-only); the override-lifecycle test is genuine.
- [2026-07-10T02:27:57Z] Elias Python:
  - Manifest: regenerated (python scripts/gen_template_manifest.py); templates_manifest.json 0.7.0 entry for agents/item_skill.md.j2 updated to the current hash, verified by independent recompute; test_manifest_freshness_all_bundled_templates now passes.
  - F2 closed: added test_item_skill_falls_back_to_frozen_lifecycle_when_type_dropped_from_spec (tests/test_skills.py) -- drops 'bug' from bundled spec.items, refresh_managed, asserts the sq-bug skill renders the frozen playbook Lifecycle line + no sub-entity clause, no crash. Used 'bug' not 'task'/'feature'/'epic': those three sit on workflow.md.j2's/claude_section.md.j2's hardcoded task->feature->epic parent-chain calls (unconditional spec.item_parent_required('task') / parent_chain(spec,'task')), which KeyError on drop for an unrelated pre-existing reason (FEAT-334 scope) -- not something to fix here.
  - Gates: pyright clean, ruff check clean, ruff format --check clean. tests/test_override_commands.py + test_skills.py + test_playbook.py + test_golden_rendered_output.py + test_backend_conformance.py + test_backend_agents_md.py + test_custom_type_skill.py + test_squad_ref_hygiene.py all green (no full-suite run, per instruction).
- [2026-07-10T02:30:57Z] Catherine Manager:
  - Reviewer-approved (fix confirmed correct — snapshots right, lifecycle byte-identical on bundled, dropped-type fallback sound). Blocker F1 (stale template manifest for item_skill.md.j2) fixed via gen_template_manifest.py; F2 dropped-type fallback test added. Full suite green. Note: dev found dropping task/feature crashes via hardcoded literals in workflow.md.j2/claude_section.md.j2 — FEAT-334/TASK-363 territory, folding claude_section.md.j2 into that scope. Landing.
<!-- sq:discussion:end -->
