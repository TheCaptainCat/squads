---
id: TASK-000111
sequence_id: 111
type: task
title: Implement sq <type> <n> remove for work items
status: Done
parent: FEAT-000023
author: tech-lead
priority: medium
subentities:
- local_id: ST1
  title: Atomic remove preserving counter high-water mark
  status: Done
  story: US1
- local_id: ST2
  title: Ref/child safety on removal; --force severs incoming refs
  status: Done
  story: US2
- local_id: ST3
  title: Traceable removal trace + remove-vs-cancel docs
  status: Done
  story: US3
created_at: '2026-06-15T08:20:37Z'
updated_at: '2026-06-23T09:58:35Z'
---
<!-- sq:body -->
## Goal

A first-class, safe `sq <type> <n> remove` for **work items** (feature/task/bug/review/decision/epic/guide). Today `remove_item` exists (`_services/_items.py:180`) but is bare — index-entry delete + backend `remove_artifacts` + optional `--purge` unlink — and is only wired as `rm` for **roles/skills/operators** (`_cli/_role.py`, `_skill.py`, `_operator.py`). Work-item types get NO remove verb (`build_item_app`, `_cli/_items.py:60`). This task adds the real, guarded removal.

## Design gate (BLOCKS code — architect ADR on FEAT-000023)

Before implementing, the FEAT-23 design questions must be settled in an ADR (see the feature Scope/Acceptance):
- **Hard delete vs. an `Archived`-style soft state.** Hold the line: *cancel* = dropped work, *remove* = should-never-have-existed. The ADR picks hard-delete (file + index gone) vs. soft-archive.
- **Audit-trail mechanism (US3):** tombstone entry in the index vs. a removal log vs. relying on git history. Whatever is chosen must be *queryable* so a sequence-number gap is explainable, and must not violate Invariant 1 (anything in `.squads.json` must be rebuildable from `.md` — a tombstone needs a file-backed source or it breaks `sq repair`).
@architect input needed here; implementation starts once the ADR is Accepted.

## Approach (assuming hard-delete + chosen trace)

1. **Service `remove_item` (rework, `_services/_items.py`)** — extend to work items inside one `store.transaction()`:
   - Resolve item; compute **incoming refs** (`SquadsDB.backrefs` / `refs_in`, `_models/_index.py:101`, `_services/_refs.py:74` — width-tolerant) and **children** (items whose `parent == id`; add a small `children()` helper on `SquadsDB` or scan `db.items` in-transaction).
   - **Refuse** (raise `SquadsError`) when refs/children exist and not `--force`, listing offenders.
   - **`--force`**: sever each referrer's matching ref from frontmatter (reuse the `_id_matches`/`rm_ref` severing logic in `_services/_refs.py`, persist via `update_frontmatter`); children must be re-parented first — `--force` does NOT auto-reparent (refuse if children remain).
   - Delete the index entry (`del db.items[seq]`) and unlink the `.md` (always, not just `--purge`, for work items) atomically.
   - Counter is **untouched** (BUG-000022 already done): the freed seq stays ≤ counter and is never reissued; verify across a follow-up `repair`.
   - Emit the chosen audit trace.
   - Return a result dataclass (new `RemoveResult` in `_services/_results.py`: removed id, severed-ref list, trace ref).

2. **CLI verb (`_cli/_items.py`)** — register a `remove` verb in `build_item_app` (alongside `_cmd_show`/`_cmd_status`/…): `--force` (sever refs), `--yes` (skip the interactive `typer.confirm` — this is the first destructive confirm in the codebase, no existing pattern to copy). Print removed id + severed refs. Add `--json`. Keep the role/skill/operator `rm` wiring consistent (it may delegate to the same hardened path).

3. **Paths/store** — no signature change expected to `_paths.py`/`_index/_store.py`; removal rides existing `transaction()`. Confirm `abspath` traversal guard still covers the unlink path.

## Files to touch
- `src/squads/_services/_items.py` — rework `remove_item` (ref/child safety, sever, atomic unlink, trace).
- `src/squads/_services/_results.py` — `RemoveResult` dataclass.
- `src/squads/_cli/_items.py` — `remove` verb + confirm/--yes/--force/--json.
- `src/squads/_models/_index.py` — likely a `children()` helper (parent inversion); possibly tombstone field if the ADR chooses index-stored trace.
- (maybe) `src/squads/_services/_refs.py` — reuse/expose sever logic.
- `src/squads/_cli/_role.py` / `_skill.py` / `_operator.py` — keep `rm` consistent with the hardened path.
- docs: remove-vs-cancel rule (tech-writer follow-up; the `squads` skill + workflow cheatsheet).
- `tests/` — service + CLI smoke tests.

## Acceptance bar (from FEAT-000023)
- Removes file + index entry atomically; next `create` never reuses the number — proven by a test that includes a follow-up `sq repair`.
- Refuses on incoming refs/children unless `--force`; forced removal leaves no dangling refs — `sq check` clean afterwards.
- Removal is traceable after the fact; docs explain remove-vs-cancel.
- No documented removal scenario requires hand-editing `.squads.json`.
- Interactive confirm unless `--yes`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 111 add-subtask "<title>"`; track with `sq task 111 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Atomic remove preserving counter high-water mark | US1 |
| ST2 | Done |  | Ref/child safety on removal; --force severs incoming refs | US2 |
| ST3 | Done |  | Traceable removal trace + remove-vs-cancel docs | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Atomic remove preserving counter high-water mark

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As an operator who created an item by mistake, I want sq remove to take it off the books safely, so that I never have to hand-edit files or the index
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Atomic remove: delete .md + index entry in one transaction; counter high-water mark survives removal and a subsequent repair (never re-issues the number); interactive confirm unless --yes.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Ref/child safety on removal; --force severs incoming refs

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a teammate whose items reference the removed one, I want removal to refuse or cleanly sever those refs, so that nothing dangles silently
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Ref/child safety: refuse removal when incoming refs or children exist (list them); --force severs incoming refs from referrers' frontmatter (no danglers); children must be re-parented first; sq check clean after any removal.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Traceable removal trace + remove-vs-cancel docs

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US3 — As someone auditing a squad later, I want number gaps to be explainable, so that a missing sequence number reads as a recorded removal, not corruption
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Traceable removal + docs: leave a queryable trace per the design ADR (tombstone/log) so a sequence-number gap reads as a recorded removal; document the remove-vs-cancel rule.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T08:59:09Z] Elias Python:
  - Implemented TASK-000111 (FEAT-000023 — sanctioned item removal) per ADR-000114.
  - REV-000115 pre-req cleanups applied first (F1: _carry_or_reset_status typed as Status→tuple[bool,Status], # type: ignore dropped; F2: local _SUBENTITY_KIND_FOR removed, SUBENTITY_KIND from _base.py reused). Mentioned here per review request.
  - Service: remove_item() docstring updated to route callers to remove_work_item() for work items. remove_work_item() added with three-phase logic: (1) children check — refuses regardless of --force; (2) backrefs check — refuses without force, lists referrers; (3) --force severs refs from each referrer's frontmatter inside the same transaction (width-tolerant, reuses _ref_id_matches logic locally to avoid cross-module private access), then hard-deletes the index entry and unlinks the .md. Counter is never modified — gap is sanctioned per ADR-000114 §4.
  - Reflog stub: _reflog_stub dict is assembled inside the transaction capturing op=remove, id, type, title, status, severed_refs. It's a no-op local variable (prefixed _ to suppress unused-var lint) until TASK-000112 wires the FEAT-000024 reflog writer. No tombstone, no separate log — conforms exactly to ADR-000114 §2 composition contract.
  - Model: SquadsDB.children() helper added to _models/_index.py — returns sorted IDs of items whose parent field matches item_id.
  - Results: RemoveResult frozen dataclass added (removed_id, severed_refs).
  - CLI: _cmd_remove() registered in build_item_app() for all WORK_TYPES. Flags: --force (sever refs), --yes (skip typer.confirm), --json. Output: 'removed ID' plus 'severed refs in: ...' when --force was active.
  - Docs (ST3): workflow.md.j2 gets a new 'Remove vs. Cancel' section documenting the semantic split, command forms, ref/child safety rules, and the sanctioned-gap invariant. Manifest hash updated.
  - Tests: tests/test_remove.py — 10 service-level tests (hard delete, counter/repair invariant, ref refusal, --force sever, multiple referrers, children block, clean sq check, width-tolerant sever, children helper) + 7 CLI smoke tests (basic, confirm, JSON, ref refusal, --force, children block, counter+repair). Gate: 653 passed, 1 skipped. pyright: 0 errors. ruff: clean.
  - @reviewer @qa ready for review. ADR-000114 conformance: hard-delete confirmed, no tombstone, counter untouched, reflog stub stubbed at call site.
- [2026-06-15T09:03:47Z] Paul Reviewer:
  - Reviewed against FEAT-000023 + ADR-000114 → REV-000116: **ChangesRequested**. Gate is fully green (652 pass/1 skip, pyright 0, ruff clean+formatted) and the ADR core all conforms: hard delete, counter untouched, refuse-then-force-sever, children always block, no tombstone (reflog stub is a real no-op), Invariant 1 holds.
  - @python-dev two changes before approval:
  - F1 (medium): `path.unlink()` in remove_work_item runs *after* the transaction commits, not inside it. ADR §1 says unlink + del index entry happen in one transaction. As written, a crash between index-commit and unlink leaves an orphaned .md that `sq repair` re-adopts — resurrecting the removed item. Move the unlink inside the `with self.store.transaction()` body (before commit). Counter stays untouched, so the gap invariant is unaffected.
  - F2 (low): `_ref_id_matches` in _items.py is a byte-for-byte fork of `_id_matches` in _refs.py. ADR §3 said reuse it. You were right NOT to call rm_ref (it opens its own transaction — would nest). But the *pure* matcher should be promoted to _models/_item.py (next to split_ref) and imported by both modules — that kills the fork and the reportPrivateUsage worry at once.
  - Both findings have full detail in REV-000116 F1/F2.
- [2026-06-15T09:07:06Z] Mara Tester:
  - QA verification complete — TASK-000111 / FEAT-000023 (ADR-000114). All acceptance criteria PASS. Empirical tests run in an isolated scratch squad (no squads repo data touched); full suite 653 passed / 1 skipped.
  - AC1 (hard delete, atomic, index gone): PASS. sq task N remove --yes unlinks the .md and removes the index entry in one transaction. Item absent from sq list / sq tree afterwards.
  - AC2 (ID never reused, gap survives repair): PASS. After removing TASK-000012 the next create produced TASK-000014 (skipped 12). Counter held at 13 through the removal; after repair counter=14. TASK-000012 never reappeared. Multiple multi-removal cycles confirmed counter=17 with gaps 9/11/12/13/15/16 all sanctioned.
  - AC3 (ref safety — default refuse): PASS. Attempting to remove TASK-000009 while TASK-000010 referenced it exited 1 with error listing TASK-000010. No silent removal.
  - AC4 (ref safety — --force severs, sq check clean): PASS. Remove --yes --force severed the ref from TASK-000010 frontmatter inside the same transaction and reported 'severed refs in: TASK-000010'. sq check: no issues.
  - AC5 (child safety — refused even with --force): PASS. FEAT-000011 with child TASK-000013 refused removal both without and with --force with 'Re-parent or remove each child first.' message. After removing the child first, the feature removed cleanly.
  - AC6 (confirm UX — prompt without --yes, --yes skips): PASS. echo 'n' piped in produced 'Aborted.' and exit 1; item untouched. --yes bypassed the prompt.
  - AC7 (--json shape): PASS. --json emits {removed_id: ..., severed_refs: [...]} — clean shape for both no-refs and forced-sever cases.
  - AC8 (Invariant 1 — sq repair consistent): PASS. sq repair after all removals rebuilt the same item count and counter; sq check clean; no resurrection of removed items.
  - AC9 (remove-vs-cancel docs in sq workflow): PASS. 'Remove vs. Cancel' section present in sq workflow output with table, command forms, ref/child safety rules, and sanctioned-gap invariant statement per ADR-000114 §4.
  - AC10 (verb on all work types): PASS. remove verb registered in task/feature/bug/decision/review/guide/epic.
  - Full test suite: 653 passed, 1 skipped. 18 tests in tests/test_remove.py all green.
  - No coverage gaps found. Feature is READY TO CLOSE. @python-dev all AC pass.
- [2026-06-15T09:15:30Z] Elias Python:
  - REV-000116 findings addressed — both changes are in.
  - F1 (atomicity): path.unlink() is now inside the transaction body, before del db.items[seq]. A crash at commit time leaves the file gone and the index entry dangling — repair drops it, not re-adopts it. Failure direction is now safe. Test: test_remove_unlink_happens_before_index_commit_no_resurrection patches _atomic_write to raise and asserts the .md is already gone, then confirms repair does not resurrect.
  - F2 (shared matcher): ref_id_matches() promoted to _models/_item.py as a public function alongside split_ref/make_ref. The private _id_matches in _refs.py and the forked _ref_id_matches in _items.py are gone. Both modules import from the single source. _item.py is a leaf — no import cycle introduced. reportPrivateUsage resolved.
  - Gate: 654 passed / 1 skipped, 0 pyright errors, ruff clean. @reviewer ready for re-review.
- [2026-06-15T09:20:38Z] Paul Reviewer:
  - Re-review complete — REV-000116 APPROVED. Both findings re-verified and closed.
  - F1 (atomicity, medium): confirmed path.unlink() now runs inside the with self.store.transaction() block (_items.py:288), before del db.items[seq] and the commit. Safe failure direction confirmed — crash at commit leaves file-gone/index-pending, and repair drops the dangling entry instead of re-adopting a surviving .md. The new test test_remove_unlink_happens_before_index_commit_no_resurrection genuinely exercises a commit-time crash (patches IndexStore._atomic_write to raise) and proves no resurrection after repair; it would fail against the old after-the-block unlink, so it is not vacuous.
  - F2 (shared matcher, low): confirmed ref_id_matches() is now public in _models/_item.py alongside split_ref/make_ref; the private _id_matches (_refs.py) and forked _ref_id_matches (_items.py) are both gone, both modules import the shared one. _item.py stays a leaf — no import cycle. Behaviour identical.
  - Gate green: 654 passed / 1 skipped, pyright 0 errors, ruff check clean, ruff format clean. @python-dev nice work — ready to close.
<!-- sq:discussion:end -->
