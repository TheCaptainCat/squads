---
id: TASK-638
sequence_id: 638
type: task
title: 'Import apply: single transaction, per-event clock/actor, reflog'
status: Done
parent: FEAT-576
author: tech-lead
refs:
- ADR-622:implements
description: 'The single IndexStore.transaction apply: per-event at/as rebind via
  the RequestContext seam, fresh IDs from the counter, files-then-index safe order,
  per-event reflog, gate, board-debt as warnings. Reuse existing service paths via
  db-taking apply-helpers.'
created_at: '2026-07-23T13:29:37Z'
updated_at: '2026-07-23T14:51:02Z'
---
<!-- sq:body -->
Implements the apply half of the bulk-import mechanism defined in ADR-622 ("Apply is one index transaction"). Depends on the event model + validate-first pre-pass task — apply only runs once that pre-pass is fully clean.

## Scope

**One transaction (ADR-622 "Apply is one index transaction").** After a fully clean pre-pass, apply inside a single `IndexStore.transaction()`: mutate the loaded `db` in memory, allocate fresh IDs from the single global counter (`db.allocate_id` — never from IDs written in the file), write each item's `.md` through the marker-safe section/frontmatter helpers, and commit the index once at the end. The store's transaction already preserves the files-then-index safe-failure order (`os.replace` last, reflog appended after) — do not re-implement it; ride it. Because the pre-pass caught every logical/authoring error, an apply-time failure can only be I/O, in which case the index simply isn't committed and `sq repair` reconciles.

**Per-event clock/actor via the RequestContext seam.** Each event rebinds the ambient clock/actor for its own effective `at`/`as` (resolved by the pre-pass task's inheritance rule) via `_context.rebind` (the small `clock`/`actor` setters), then restores — so `created_at`/`updated_at`, comment authorship, the `updated_at` session lineage, and `create`'s default author all reflect that one event. Every applied event still emits its own reflog op with the event's own actor/session, so imported history lands in the reflog exactly as interactive work does.

**Reuse the interactive mutation cores — one code path per mutation (ADR-622 implementation note).** The interactive service methods each open their OWN `transaction()`, so they CANNOT be called inside the import's single open transaction (the file lock is not reentrant). Factor each op's mutation core into a `db`-taking apply-helper that BOTH the existing single-op service method and the import loop call. Do NOT write a parallel importer that duplicates mutation logic — that would drift from interactive behaviour. Map the v1 ops onto the existing paths: `create` -> `create`; `status` -> `set_status`; `body` -> `set_body`; `comment` -> `comment`; `ref` -> the ref-add path; `add-story`/`add-subtask`/`add-finding`/`add-sub` -> `add_block`; `sub-status` -> `set_block_status`; `sub-body` -> `set_block_body`; `assign` -> the assignee setters; `update` -> `update`/`update_block`. Resolve handles to the ids allocated earlier in the same run.

**Gate + board-debt (ADR-622 "Interaction with sq check").** Every created/updated item passes the same `ValidatorEngine.gate()` the interactive commands run — import does not bypass the catalog gate, so a clean import leaves `sq check` clean. Board-debt conditions `sq check` reports (unwritten sub-entity bodies, over-long finding/story titles) surface as **import warnings**, not silent debt.

## Where it plugs in
- `_index/_store.py::IndexStore.transaction`/`allocate_id`; `_context.py` (`rebind`/`get_context`) via the `clock`/`actor` setters; `ValidatorEngine.gate` in `_services/_validators.py`.
- The refactor touches `_services/_items.py`, `_collab.py`, `_subentities.py`, `_refs.py`, and `_base.create` — extract each mutation core to a `db`-taking helper and have the existing method wrap it in its own `transaction()`. Keep behaviour identical (existing tests must stay green).
- Return a structured apply result (per-op counts, `handle -> id` map, warnings) for the CLI/`--json` task to render.

## Conventions (must hold)
- No status/lifecycle prose in bodies/docstrings. Category is "roster". No ticket/sq IDs in source or test names. PEP-695 `type` aliases. `SquadsError` family. Escape console output via `_cli._common.e()`. Marker-safe edits only — import bodies go through `_sections`. Time via `clock`/the context seam only.
- Invariants: frontmatter is source of truth (index is the derived commit, `repair`-rebuildable); one global counter (allocate only inside the one transaction — never from the file); forward edges only.

## Testing / gates
- Gates: `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .`.
- If you add ANY module-level constant, run `tests/meta` (mutable-state guard).
- Service-level tests: apply a multi-event file and assert item `.md` files (valid frontmatter, intact markers, preserved body), per-event `created_at`/author/session, the reflog entries, board-debt warnings, and that the counter advanced monotonically. Prove the extracted apply-helpers keep the single-op methods behaviour-identical. Verify `sq repair` reconciles after a simulated mid-apply failure (index uncommitted). A CLI smoke test belongs to the CLI task.
- `uv run sq check` clean before finishing.

## Sizing
The second of the two sizable core tasks (with the event-model/pre-pass task). The helper-extraction refactor across five service modules is the bulk of the risk — keep it behaviour-preserving.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 638 add-subtask "<title>"`; track with `sq task 638 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T14:30:45Z] Elias Python:
  - Apply pass done, one transaction, real IDs from the real counter. The refactor: extracted a _X_model (pure, no I/O) / _X_core (I/O: render/write/reflog) split for every op-bearing interactive method — create, set_status, update, add_ref, add_block, set_block_status, set_block_assignee — plus a shared _section_edit_core (body/comment/sub-body's common core, since those three already funneled through one _locked_section_edit helper). Each interactive method is now a 2-line wrapper: open its own transaction, call its own core. Behavior-preservation proof: the full existing service+cli+unit+integration suite (every one of these methods' own tests) stayed green through every step of the refactor, run repeatedly as I went.
  - Apply (_services/_import.py ImportMixin._apply_import): ONE self.store.transaction(), per-event clock.set_now(ev.at)/actor.set_actor(ev.actor) via the RequestContext seam (bind/restore around each event), dispatch to the real _X_core methods with handles resolved against the real db, per-event reflog (now correctly per-event actor/clock — see the store fix noted on TASK-636). Every create/update runs the same ValidatorEngine.gate() the interactive path runs (fail-closed, same as always). Board-debt: post-commit re-reads only the items THIS run touched and runs ValidatorEngine(...).report() over them (squad_global disabled), folding warn-level issues (unwritten body, over-long title, etc.) into ImportApplyResult.warnings — never silent.
  - Entry point for the CLI task: Service.import_events(text, *, default_at=None, default_as=None, dry_run=False) -> ImportResult(plan, applied). plan is always populated; applied is None whenever dry_run or the pre-pass found any issue — apply only ever runs after a fully clean pre-pass.
  - Tests: multi-op end-to-end scenario (handles cross-referencing an epic/feature/story/task/subtask, per-event at/as, body/comment/ref/sub-status/sub-body/assign/update) asserting final frontmatter+markers+reflog actor-per-event; counter-monotonic; dry-run-writes-nothing; apply-only-after-clean-prepass; board-debt warning; sq repair reconciles after a simulated mid-apply I/O crash. Gates green: pyright/ruff (repo-wide) + targeted suite + tests/meta.
<!-- sq:discussion:end -->
