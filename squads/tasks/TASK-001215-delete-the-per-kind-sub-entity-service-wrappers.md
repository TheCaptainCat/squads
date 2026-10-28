---
id: TASK-1215
sequence_id: 1215
type: task
title: Delete the per-kind sub-entity service wrappers
status: Done
parent: FEAT-1092
author: tech-lead
assignee: python-dev
priority: low
refs:
- REV-956:addresses
description: Remove the 16 test-only per-kind sub-entity wrappers and comment selectors;
  port two fixtures to the generic API.
subentities:
- local_id: ST1
  title: Port the two CLI fixture builders to the generic API
  status: Done
  story: US3
- local_id: ST2
  title: Delete the 16 wrappers and their exemptions
  status: Done
  story: US3
- local_id: ST3
  title: Route comment selectors through the generic sub pair
  status: Done
  story: US3
created_at: '2026-10-28T12:22:42Z'
updated_at: '2026-10-28T12:48:07Z'
---
<!-- sq:body -->
Remove the bundled per-kind sub-entity surface that only tests use, so every sub-entity goes through the generic kind-taking API. The remainder of REV-956 F7. No behaviour change.

## Facts (checked in the code on 2026-10-28)

- `SubentitiesMixin` (`src/squads/_services/_subentities.py`) carries 16 per-kind wrappers over the generic `add_block`/`list_blocks`/`get_block`/`update_block`/`set_block_body`/`set_block_status`: `add_story`, `add_subtask`, `add_finding`, `list_stories`, `list_subtasks`, `list_findings`, `get_story`, `get_subtask`, `set_story_body`, `set_subtask_body`, `set_story_status`, `set_subtask_status`, `set_subtask_done`, `set_subtask_assignee`, `update_subtask`, `update_finding`. No code in `src/` calls them. The only callers are `tests/cli/_populated.py` and `tests/cli/_readable.py` (13 calls).
- `add_finding` does more than delegate: with no `severity` it fills the `finding` kind's declared default (`field_default("finding", "severity")`). `add_block` does not. A ported call that omits the severity must pass that default explicitly, or the fixture squads change.
- `pyproject.toml` `[tool.vulture] ignore_names` lists the 16 names as test-only service API.
- `tests/meta/test_no_bundled_subentity_kind_literal_outside_the_spec_layer.py` allows `story`/`subtask`/`finding` in `_services/_subentities.py` for the wrappers. Every such literal in that file sits inside a wrapper, so the entry goes with them.
- `CollabMixin.comment` (`_services/_collab.py`) takes `story`/`subtask`/`finding` keywords. No caller passes them: the CLI passes `sub=(kind, local_id)` and the tests pass neither. `_comment_core` and `_discussion_tag` are not dead, though: the bulk importer (`_services/_import.py`, `_apply_comment` and `_sim_comment`) feeds them the import format's per-kind comment selectors. The `_collab.py` allowlist entry covers the three literals in `_discussion_tag`'s legacy branch.
- Stale prose naming the wrappers: the comment above `add_block` ("the per-kind wrappers above delegate to them"), the `_resolve_add_fields` docstring in `_cli/_items.py` (cites `add_finding`), and the vulture paragraph in `CLAUDE.md` (outside the managed region), which says sub-entity `Service` methods are dispatched from `_cli/_items.py` at runtime. Nothing is dispatched that way.

## Scope

1. Port the two fixture builders to `add_block`/`update_block`. The squads they build stay identical.
2. Delete the 16 wrappers, their `ignore_names` entries, the `_subentities.py` allowlist entry and the stale prose above.
3. Drop the per-kind keywords from `CollabMixin.comment`. Have the importer turn its per-kind comment selector into the generic `sub` pair before calling the core. `_comment_core` and `_discussion_tag` then take only `sub`, and the `_collab.py` allowlist entry goes. The import format does not change: same fields, same refusal and message when an event names more than one selector. The per-kind literals stay in `_import.py`, which is already allowed for the import format's events.

Out of scope: the import format itself, the remaining allowlist entries, any other test module.

## Acceptance

- No name from the 16 is defined or called anywhere in `src/` or `tests/`, and `rg` finds none.
- `uv run vulture` reports none of the 16 names, nor anything new compared with before the change.
- The kind-literal guard passes with the `_subentities.py` and `_collab.py` entries removed. Its dead-entry test proves no allowed pair is left over.
- Gates clean: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`.
- Affected tests pass: `tests/meta`, `tests/cli`, and the import and comment tests (`-n 4`). The main loop runs the full suite.
- No ticket IDs in code, comments or test names. Comments state present truth, in one or two sentences.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1215 add-subtask "<title>"`; track with `sq task 1215 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Port the two CLI fixture builders to the generic API

<!-- sq:subtask:ST1:body -->
Rewrite `tests/cli/_populated.py` and `tests/cli/_readable.py` to call `add_block` and `update_block` with the kind in place of `add_story`, `add_subtask`, `add_finding`, `update_subtask` and `update_finding`. A finding added without a severity gets `fields={"severity": svc.field_default("finding", "severity")}`, as `add_finding` did, so the fixture squads stay the same. Check that the `tests/cli` modules using `init_populated` and `init_readable` still pass.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Delete the 16 wrappers and their exemptions

<!-- sq:subtask:ST2:body -->
Remove the 16 per-kind wrappers from `SubentitiesMixin`. Remove their entries and comment from `[tool.vulture] ignore_names` in `pyproject.toml`, and the `_services/_subentities.py` entry from the kind-literal guard's `_ALLOWED`. Fix the prose that names them: the comment above `add_block`, the `_resolve_add_fields` docstring in `_cli/_items.py`, and the vulture paragraph in `CLAUDE.md`. Its runtime-dispatch clause is false and goes. Run vulture and check it reports none of the 16 names.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Route comment selectors through the generic sub pair

<!-- sq:subtask:ST3:body -->
Drop the `story`/`subtask`/`finding` keywords from `CollabMixin.comment`. Fold the importer's per-kind comment selector into the generic `sub` pair in `_apply_comment` and `_sim_comment` before the core is called. Keep the existing refusal and its message when an event names more than one selector. `_comment_core` and `_discussion_tag` then take only `sub`, so the `_services/_collab.py` entry leaves the guard's `_ALLOWED`. The import format is unchanged, and the import comment tests prove it.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T12:27:53Z] `python-dev` Elias Python:
  - @manager handoff: ST1-ST3 done, no behaviour change.
    - 16 wrappers deleted; fixtures ported to add_block/update_block (default severity passed explicitly); vulture ignore_names entries, CLAUDE.md clause, stale docstrings and both guard allowlist entries removed.
    - CollabMixin.comment/_comment_core/_discussion_tag take only sub; importer folds story/subtask/finding into sub via a new _comment_selector helper (same refusal message).
    - Deviation: deleting the wrappers left set_block_status, _set_block_assignee and WorkflowSpec.subentity_completion with no caller (vulture would flag them as new), so I deleted them too.
    - Gates: pyright 0 errors; ruff check clean; format clean; vulture identical to baseline except line numbers; pytest tests/meta tests/cli tests/check: 1536 passed; sq check clean.
- [2026-10-28T12:38:38Z] `python-dev` Elias Python:
  - @reviewer @manager REV-1216 F1-F3 fixed and marked Fixed; import comment tests added and falsified, prose fixed, refusal reworded in import-field terms. Gates: pyright 0 errors, ruff check/format clean, vulture unchanged, tests/meta+cli+check 1548 passed, sq check clean.
- [2026-10-28T12:48:06Z] `manager` Catherine Manager:
  - Accepted: REV-1216 F1-F4 Verified, review Approved; full suite 1554 passed, pyright/ruff clean. Note: the import multi-selector refusal wording changed (REV-1216 F3), so Scope 3 "same refusal and message" is superseded; CHANGELOG 0.17 records it.
<!-- sq:discussion:end -->
