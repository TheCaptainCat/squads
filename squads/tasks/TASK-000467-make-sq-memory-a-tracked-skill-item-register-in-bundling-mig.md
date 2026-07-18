---
id: TASK-467
sequence_id: 467
type: task
title: Make sq-memory a tracked SKILL item (register in bundling + migrate)
status: Done
author: manager
created_at: '2026-07-17T15:47:40Z'
updated_at: '2026-07-18T21:59:20Z'
---
<!-- sq:body -->
sq-memory is the only bundled skill NOT tracked as a SKILL item: plain squads/agents/skills/sq-memory.md, absent from .squads.json, while the other 9 (including the transversal 'greeting') are SKILL-NNN items. Transversal/cross-role is not the reason (greeting is transversal AND tracked). Fix: (1) register sq-memory as a tracked bundled SKILL in the skill-creation/bundling flow so fresh init/sync allocates it an id and indexes it like the others; (2) a migration for existing squads — rename to SKILL-000NNN-sq-memory.md, allocate the next global-counter id, add the index entry, repoint the .claude pointer. Architect to confirm the migration approach and whether it warrants an ADR before implementation.

## Additional scope — sq-memory add doc-clarity fix (folded in)

Since this task already restructures the sq-memory skill, fold in a small
documentation-clarity fix here rather than touching the same skill twice.

Defect: agents repeatedly cram the whole fact into the positional `sq memory
<role> add` argument, which becomes the memory's one-line `summary:` (the index
entry) plus a truncated auto-slug — producing a bloated summary + ugly handle
instead of a snappy summary + a detailed `--file` body. Root cause is doc text
that never explains the summary-vs-body split.

Additional acceptance criteria (keep the register-as-tracked-SKILL + migrate
scope above intact):

- Wherever the sq-memory skill body ends up living once it's a tracked SKILL
  item, it must explain the summary-vs-body split: the positional `sq memory
  <role> add` argument is the snappy one-line SUMMARY (the index entry /
  `summary:` field); the detailed body goes in `--file`; name the handle with
  `--slug` for a clean, stable slug. Document `--slug` in the command-surface
  block (currently omitted).
- Reword the CLI `fact` arg help in `src/squads/_cli/_memory.py` (currently "The
  fact to remember (also the default slug source)") to say it's the memory's
  summary/headline, kept snappy — not the whole fact.
- Canonical skill source is `src/squads/_rendering/templates/agents/memory_skill.md.j2`
  today; note that this task's tracked-item conversion may change where the body
  lives, so apply the rewording at whatever the post-conversion source of truth
  is.
- Keep `sq check` + the doc/meta gates clean; regenerate the templates manifest /
  skill golden as needed.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 467 add-subtask "<title>"`; track with `sq task 467 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T15:47:42Z] Pierre Chat:
  - Transversal skills must be tracked items too — greeting is transversal and tracked, so cross-role is no excuse. Make sq-memory an item.
- [2026-07-18T20:43:18Z] Robert Architect:
  - ARCHITECT RULING — no ADR. This applies ADR-181 (SKILL as first-class Item, role/operator pattern) to the last straggler; it introduces no new architectural decision. Recording the approach here instead of an ADR to avoid ceremony.
  - Correction to the task premise: the BUNDLING half is already done. MEMORY_SKILL is in bundled_skill_slugs() and seed_bundled_skills() stamps it — verified by a fresh 'sq init' (sq-memory lands as a tracked SKILL, e.g. SKILL-000015). No code change needed for fresh-init/adopter-init tracking. The only real gap is existing squads (incl. this dogfood repo) carrying a legacy untracked squads/agents/skills/sq-memory.md written by write_managed after TASK-381, which never re-ran seeding (seed runs at init only, not sync).
  - Migration approach (four points resolved):
  - 1) Stable id — per-repo counter allocation at migration time is CORRECT and acceptable, not a defect. Invariant #2 (one global monotonic counter) makes a fixed cross-repo id impossible AND ADR-181 already accepts per-repo SKILL ids (this repo has SKILL-192..200; a fresh init has SKILL-9..18). Allocate the next counter value inside IndexStore.transaction(); the SKILL-000NNN-sq-memory.md filename follows from it. Do NOT hardcode an id.
  - 2) Migration vs repair — a dedicated registry entry is REQUIRED; repair cannot do it. _rebuild_index_from_disk skips id-less files (if not data.get('id'): continue) and legacy slug-named files are silently skipped, so repair/sync will never pick up an unstamped sq-memory.md — allocating an id is a mutation, not a pure rebuild. Ship a frozen runner modeled on _v0_4_to_v0_5 (the existing SKILL-id migration), scoped to the 'sq-memory' slug, with frozen skill vocab literals (never the live spec/enum). Three-branch idempotency, identical to _v0_4_to_v0_5: (a) SKILL-*-sq-memory.md convention file already exists -> no-op; (b) legacy sq-memory.md with no frontmatter id -> allocate + stamp + rename + repoint; (c) id present but still slug-named -> rename + repoint, no allocation. run_pending_migrations then calls repair(), recovering the counter high-water from max(sequence_id).
  - 3) Backend pointer — the live seed/sync path already repoints via backend.generate_skill_entry (the ABC), satisfying invariant #6. In the MIGRATION runner, follow the established _v0_4_to_v0_5 precedent: a frozen point-in-time pointer render (claude/pointer_skill.md.j2), NOT a call into the live backend registry — a migration must stay immune to future ABC/spec drift and only receives SquadPaths. That is the accepted deviation for migration runners; do not reach into .claude anywhere else.
  - 4) Schema version — CORRECTION: a bump IS needed (0.8 -> 0.9), contrary to the task's 'likely no bump'. The frontmatter SHAPE is unchanged (a SKILL item's frontmatter already exists), so this is a data backfill — but sq's migration registry is version-keyed and 'sq migrate up' only triggers on a schema transition. The bump is the trigger/apply-once marker, not a claim of structural change (same shape as the additive v0_3_to_v0_4 lineage backfill, which also rode a bump). It also correctly forces existing squads to run the backfill via the root-callback hard-stop. NOTE: we are on release/0.10 with the registry still ending at 0.8 — if the 0.10 cut introduces any OTHER schema transition, fold the sq-memory stamp into that runner rather than minting a separate step, to avoid gratuitous schema churn. Absent that, ship a standalone 0.8 -> 0.9 backfill.
  - Folded doc-clarity fix (summary-vs-body split, --slug, _cli/_memory.py 'fact' help reword) is unaffected by this ruling — apply it at the post-conversion source of truth (the tracked SKILL body / memory_skill.md.j2). Proceed to implementation.
- [2026-07-18T20:48:42Z] Pierre Chat:
  - Decision: ship the tracked-item migration in the 0.10 cut (accepted it's 0.10's only schema transition + a forced sq migrate up for existing squads; safe idempotent backfill, precedented). Schema goes 0.8 → 0.10 (tracks the release), runner _v0_8_to_v0_10.py. No ADR (applies ADR-181, per architect).
- [2026-07-18T21:54:31Z] Elias Python:
  - Shipped: migration _v0_8_to_v0_10.py (schema 0.8->0.10, version=0.10.0 in the registry), scoped to sq-memory, 3-branch idempotent, modeled on _v0_4_to_v0_5.
  - Applied to this dogfood repo: sq-memory is now SKILL-486, .claude pointer repointed, sq check clean; verified idempotency (2nd run no-op) and the SKILL-000486 filename via the corpus unit tests.
  - Caught + fixed a real bug in my own runner: the .claude pointer path was squad_dir-relative instead of root-relative (dropped the 'squads/' segment) — affects every real repo since squad_dir='squads' is the init default, not just this one. Tightened the pointer test to assert the exact @-path so it doesn't regress.
  - Folded-in doc fix: memory_skill.md.j2 now explains the summary-vs-body split and documents --slug in the command block; reworded the CLI 'fact' arg help in _cli/_memory.py to say summary/headline, not 'the fact'.
  - New corpus fixture tests/fixtures/corpus/v0_10 added per the standing rule (copy of v0_8, migrated forward, schema-stamped); templates_manifest.json regenerated (only the memory_skill.md.j2 hash under the existing unreleased 0.9.0 key changed, no prior release entries touched).
  - Gates: pyright/ruff/ruff-format clean; targeted pytest (migration + corpus + memory/skill + override-manifest suites) all green. Flag: found substantial unrelated uncommitted changes already in this working tree (clients/vscode/*, _badges.py, _workflow_cmd.py, new badge/collections-catalog work) that weren't part of my scope or present in the session's initial git status — looks like other work landed in this tree concurrently; didn't touch any of it, but the 'only agent touching the repo' assumption may not hold.
- [2026-07-18T21:58:07Z] Elias Python:
  - Fixed 2 full-suite failures flagged by the coordinator: (1) stray FEAT-315/TASK-381 reference in _v0_8_to_v0_10.py's docstring, removed (kept the rationale, dropped the IDs) — grep confirmed clean across the new migration+test files. (2) tests/goldens/reflog_shape.json's pinned schema_version 0.8 -> 0.10 (only field that changed; fields/example_ops untouched).
  - Confirmed green: tests/cli/test_reflog_cli.py + tests/meta/test_source_and_new_test_tree_have_no_stray_ticket_references.py (-n0). Re-ran ruff check/format, pyright, sq check — all clean.
- [2026-07-18T21:59:20Z] Catherine Manager:
  - Done: _v0_8_to_v0_10 migration (sq-memory → tracked SKILL-486), schema 0.8→0.10, summary/body + --slug rewording. Dogfood migrated + idempotent; .claude pointer @-path bug caught & fixed via real migrate-up run. Full suite green. Not committed (Pierre owns).
<!-- sq:discussion:end -->
