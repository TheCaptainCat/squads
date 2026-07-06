---
id: TASK-187
sequence_id: 187
type: task
title: Make skill-body regen path frontmatter-preserving and marker-safe
status: Done
parent: FEAT-178
author: tech-lead
subentities:
- local_id: ST1
  title: Body-region-only marker-safe regen preserves stamped frontmatter
  status: Done
  story: US1
- local_id: ST2
  title: 'Idempotence test: sq sync twice leaves id/sequence_id unchanged'
  status: Done
  story: US1
created_at: '2026-06-24T18:46:55Z'
updated_at: '2026-07-06T15:19:50Z'
---
<!-- sq:body -->
## Goal

Convert the managed skill-body regeneration from a **full-file overwrite** to a **body-region-only,
marker-safe** replacement that preserves stamped sq frontmatter. This is the riskiest change in
FEAT-178 (per ADR-181 decision #3 / consequences) and a **prerequisite** for the other tasks:
without it, the very next `sq sync` after a skill is stamped would wipe its `id`/`sequence_id`/
`status`/`schema_version` and destroy the stable identity the feature exists to provide.

Implement this **first**, before the allocation/migration work.

## What to change

- `_write_managed_skill` in `_backends/_claude_code/_backend.py:107` currently does a blunt
  full-file overwrite of pure template output carrying no frontmatter (`_aio.write_text(body_path, body)`).
  Convert it to replace **only** the `sq:body` region of the existing skill file, mirroring
  `_regen_role_body` in `_services/_maintenance.py:125`, which reads the existing role item file and
  replaces only the `sq:body` region via a marker-safe section edit (invariant 3), never the
  frontmatter.
- Equivalently per ADR #3: load the skill `Item` and re-emit preserved frontmatter + freshly
  rendered body (round-trip through the index), rather than re-render a bare template over the file.
- The managed skill body already uses sq markers, so it is region-compatible — this task pins the
  regen path to **use** that structure instead of overwriting the whole file. Must remain marker-safe
  (invariant 3) and stay within the FEAT-177 codec contract.
- Where a skill file has not yet been stamped (no frontmatter), the path must still behave correctly
  (it should not invent ids — allocation is TASK-188's job — but it must not corrupt the file).

## Design constraints (ADR-181)

- Decision #3: regen touches only the rendered body region, frontmatter intact.
- Decision #4 (idempotence): re-running `sq sync` on an already-stamped skill must NOT change its
  `id`/`sequence_id`. This task makes that property true.

## Acceptance

1. The skill-body regen path replaces only the `sq:body` region; frontmatter and markers are
   preserved on re-sync.
2. **Dedicated idempotence test**: stamp a skill (or use a stamped fixture), run `sq sync` twice,
   assert the skill's `id` and `sequence_id` are unchanged after both runs. (FEAT-178 AC#4.)
3. Service-level test + CLI smoke test per project testing convention.
4. `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; suite green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 187 add-subtask "<title>"`; track with `sq task 187 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Body-region-only marker-safe regen preserves stamped frontmatter | US1 |
| ST2 | Done |  | Idempotence test: sq sync twice leaves id/sequence_id unchanged | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Body-region-only marker-safe regen preserves stamped frontmatter

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Stable SKILL-… ID per skill for cross-entity referencing
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers converting _write_managed_skill in the claude_code backend from a blunt full-file overwrite to a body-region-only, marker-safe replacement that preserves stamped sq frontmatter (id/sequence_id/status/schema_version) — mirroring _regen_role_body's read-existing-then-replace-only-the-sq:body-region approach (invariant 3). Handles the not-yet-stamped skill file case without corrupting it (no id invention — that is TASK-188).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Idempotence test: sq sync twice leaves id/sequence_id unchanged

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — Stable SKILL-… ID per skill for cross-entity referencing
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Covers the dedicated idempotence test (FEAT-178 AC#4, ADR-181 #4): stamp a skill (or use a stamped fixture), run sq sync twice, and assert the skill's id and sequence_id are unchanged after both runs — proving re-sync never churns skill identity. Plus service-level and CLI smoke tests per convention.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-24T19:39:08Z] Elias Python:
  - Implementation complete. _write_managed_skill in _backends/_claude_code/_backend.py now reads the existing skill file before writing: if the file has frontmatter and a sq:body region, only the body region is replaced (via sections.replace_section); otherwise the body-with-markers is written as before. Mirrors the _regen_role_body pattern exactly.
  - Two subtasks done: (1) body-region-only marker-safe regen preserving stamped frontmatter, (2) mandatory idempotence test test_sync_twice_leaves_skill_ids_unchanged confirming sq sync twice never changes id/sequence_id. Full suite green (exit 0).
- [2026-06-24T19:53:47Z] Elias Python:
  - F1 nit from REV-191 addressed. The else-branch in _write_managed_skill (_backends/_claude_code/_backend.py) was split into two cases: (1) frontmatter present but sq:body region absent/partial — now re-emits the existing frontmatter via sections.join_frontmatter(fm, body_with_markers) so stamped id/sequence_id are never lost (ADR-181 #3 fail-safe); (2) genuinely no frontmatter — unchanged, writes bare body_with_markers. The happy-path branch (frontmatter + body region present) is untouched.
<!-- sq:discussion:end -->
