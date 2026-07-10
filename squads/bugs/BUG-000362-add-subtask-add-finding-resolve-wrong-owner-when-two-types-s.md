---
id: BUG-362
sequence_id: 362
type: bug
title: add_subtask/add_finding resolve wrong owner when two types share a subentity_kind
status: Verified
author: qa
created_at: '2026-07-10T01:35:51Z'
updated_at: '2026-07-10T01:55:38Z'
---
<!-- sq:body -->
`ServiceCore.subentity_parent` (`_base.py::subentity_parent_map`) inverts `{type: subentity_kind}` into `{subentity_kind: type}` via a plain dict comprehension — when two live item types declare the *same* `subentity_kind` (e.g. `task` and a project-declared `ticket`, both `subentity_kind="subtask"`), the inversion silently keeps only the last one iterated, and `_require_parent`/`_check_type` then reject the other type's items outright.

Repro:
1. `sq create task t --parent <feat>` (plain squad, no override yet) — a real TASK item.
2. Declare `.overrides/workflow.toml` with a project type `ticket` whose `subentity_kind = "subtask"` (mirrors task, as FEAT-281's own rename-type worked example requires — the target type must be declared additively before `rename-type` runs).
3. `sq task <n> add-subtask "..."` on the pre-existing TASK item now fails:
   `SquadsError: TASK-3 is a task; subtasks live on a ticket`

This blocks FEAT-281's own documented workflow: declare the rename target additively, then continue ordinary work on the old-type items (including adding subtasks) before running `rename-type`. Any generic sub-entity verb that resolves owner via `subentity_parent[kind]` (add_subtask/add_finding/add_story, set_block_status, set_block_assignee, update_block, etc.) is affected the same way, not just add_subtask.

Also has a **permanent** post-rename echo: the built-in `task` entry is unremovable (additive-only), so after renaming task->ticket the merged spec still declares two types sharing subentity_kind="subtask" forever — harmless while task has zero live items, but latent for any future type that reintroduces a task-kind item.

Found during TASK-359 (FEAT-281 acceptance sweep) while seeding a realistic pre-rename scenario; worked around in the acceptance test by seeding sub-entities before writing the override file, but a real project following the feature's own worked example would hit this.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T01:36:10Z] Mara Tester:
  - @tech-lead found via TASK-359 (FEAT-281 acceptance sweep); FEAT-281's own rename-type worked example (declare target type additively, then keep working on old-type items) hits this. Not part of _rename.py itself — the ambiguous kind->owner inversion lives in _base.py::subentity_parent_map, pre-existing (FEAT-210/211/326 spec-vocab engine).
- [2026-07-10T01:47:51Z] Elias Python:
  - Root-caused: subentity_parent_map inverted the 1:many type->kind relation into a lossy kind->type map; _check_type/_require_parent used that inversion for ownership.
  - Fix: ownership now resolves forward+1:1 via spec.item_subentity_kind(item.type)==kind (src/squads/_services/_subentities.py: _check_type, _require_parent no longer takes an 'expect' param; call sites in add_block/set_block_status/_set_block_assignee/update_block simplified).
  - subentity_kind_map now built directly off the spec (t: ts.subentity_kind), not by inverting subentity_parent_map, so no type is dropped when kinds collide.
  - subentity_parent_map kept but re-scoped/documented as a naming HINT only (kind -> one representative hosting type) -- no remaining ownership/validation caller.
  - Reworked error message: '{id} is a {type}, which does not host {kind}s (…s host …s)' replacing the misleading single-expected-type wording; updated the two spine-characterization tests asserting the old text.
  - De-workarounded tests/test_rename_acceptance.py: the ticket override is now written and loaded FIRST, then add_subtask runs on pre-existing task items while task/ticket share subentity_kind=subtask -- the real repro, no longer sidestepped.
  - Added a focused regression test (tests/test_subentity_kind_spec_driven.py): add-subtask on both a task item and a ticket item (sharing subentity_kind) resolves to the correct owner.
  - Bundled-spec behaviour unchanged (unique kinds, no collapse) -- confirmed via full spine-characterization + spec-driven + rename-acceptance + rename + workflow-override + custom-subentity-kind-CLI + ref-hygiene runs, all green. pyright/ruff check/ruff format clean.
  - Leaving InProgress for verification.
- [2026-07-10T01:52:45Z] Paul Reviewer:
  - Reviewed the BUG-362 fix (independent). VERDICT: APPROVE. Root cause correctly addressed: ownership now resolves FORWARD via spec.item_subentity_kind(item.type)==kind (1:1), never by inverting the lossy kind->type map. gates clean (pyright/ruff/format), full suite green (exit 0, 0 failures). One LOW hygiene finding (ticket IDs in test comments).
  - Forward-check complete (Q1): YES. _check_type (_subentities.py:464) uses spec.item_subentity_kind(item.type)==kind; _require_parent dropped its expect param and delegates to it; all six ownership sites (add_block:112, set_block_status:280, _set_block_assignee:318, update_block:347, list_blocks:183/get_block:399, _require_parent:461) route through _check_type. Grepped every subentity_parent use in src: only the definition + the now-caller-less naming-hint property remain — NO ownership/validation path depends on the reverse map's 1:1-ness anymore.
  - subentity_kind_map drop-safe (Q2): YES. Rebuilt directly as {t: ts.subentity_kind for t,ts in spec.items} (_base.py:65), so subentity_kind[task] survives when ticket shares the kind (previously it inverted the lossy parent map and dropped one). Its two forward uses (_retype.py:237 container-on-retype, _subentities.py:412 _write_block_file) are type->kind, correct. Regression test test_two_types_sharing_a_kind_both_resolve_their_own_items adds a subtask to BOTH a task and a ticket item and asserts each gets its own — proves no cross-routing.
  - Bundled byte-identical (Q3): YES. Built-in kinds are unique (task/feature/review -> subtask/story/finding), so the old inversion never actually collapsed for built-ins; forward-check yields identical decisions. Only user-visible change is the error wording ('{id} is a {type}, which does not host {kind}s'), updated in test_spine_characterization. Full suite + goldens green confirm.
  - LOW (hygiene, non-blocking): three new BUG-362 references in test comments — test_rename_acceptance.py:54,77 and test_subentity_kind_spec_driven.py:62. The behavioral description ('two types sharing a kind', 'override-first repro') is already spelled out, so the 'BUG-362' token can be dropped per the no-ticket-IDs-in-source rule; the ticket pointer belongs in the sq/commit. Matches an existing (non-compliant) pattern in neighboring test docstrings, so not introduced-in-isolation — flagging for a cleanup pass, not blocking. Error messages otherwise read well and the '(… host …s)' hint is helpful.
- [2026-07-10T01:55:26Z] Catherine Manager:
  - Fixed: ownership now resolves forward via spec.item_subentity_kind(item.type)==kind (1:1), subentity_kind_map rebuilt directly from spec (drop-safe), subentity_parent_map re-scoped to a naming-hint with no ownership caller. Error messages reworked. Bundled byte-identical; regression test + de-worked-around acceptance test prove the two-types-share-a-kind case. Reviewer-approved; full suite green. Verified via the FEAT-281 acceptance sweep (TASK-359).
<!-- sq:discussion:end -->
