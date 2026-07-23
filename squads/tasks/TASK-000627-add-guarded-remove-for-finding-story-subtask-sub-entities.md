---
id: TASK-627
sequence_id: 627
type: task
title: Add guarded remove for finding/story/subtask sub-entities
status: Done
parent: FEAT-575
author: tech-lead
description: 'US3: guarded sub-entity remove — hard-delete + --yes, marker-safe, reflog'
created_at: '2026-07-23T08:03:36Z'
updated_at: '2026-07-23T08:40:48Z'
---
<!-- sq:body -->
Implements FEAT-575 **US3**. Add a guarded `remove` for the finding/story/subtask
sub-entities, mirroring the parent-item `remove` contract (hard-delete + `--yes`
confirmation). A mis-created sub-entity is currently permanent — there is no delete
path.

This is destructive-verb territory; scope it as carefully as item-level
`remove_work_item` (see `_services/_items.py`) does.

## Service — new `remove_block(parent_id, kind, local_id)` in `_services/_subentities.py`

- Runs inside a single `store.transaction()` (atomic RMW), same as the other
  sub-entity mutators. Steps:
  1. Resolve the parent + require the sub-entity exists (`_require_parent` +
     `_find`), raising `SquadsError` if not.
  2. Drop the `SubEntity` from `item.subentities` (frontmatter is the source of truth
     for sub-entity state).
  3. **Marker-safe body removal** — `_sections.py` currently has NO region-delete
     helper (only get/replace/append/region_lines). Add one (e.g. `remove_section(text,
     tag)` that excises the whole span from a tag's open marker through its matching
     `:end` marker inclusive, and is a no-op / raises cleanly if absent). Use it to remove the
     block's regions from the container section: the block itself (`<kind>:<local_id>`,
     heading + `:head`), its `:body`, and its discussion (`discussion_tag`). Never
     hand-rewrite the agent-authored body — go through `_sections` only.
  4. Re-render the parent's roll-up summary table (`discussion.ensure_summary`) so it
     reflects the removed row.
  5. Reflog: append an `op=remove` (or `op=subentity` with a remove delta) stub with a
     gone-sub-entity snapshot (kind, local_id, title, status), via `store._log(...)`,
     matching how `remove_work_item` records its snapshot.
- **local_id policy:** confirm `discussion.next_local_id` derives the next id from the
  live sub-entities such that a removed id is not silently reissued to a different
  future sub-entity (a freed number should stay freed, like the item counter's
  sanctioned gap). If it currently recomputes from max/count, note the behaviour in
  the body and add a test pinning it.
- **Dangling story map:** removing a `story` can leave subtasks (in a child task)
  whose `story` field points at the gone `USn`. Decide + document the behaviour —
  either refuse with a `SquadsError` listing the dependent subtasks, or allow and
  clear/orphan the mapping — and cover it with a test. Findings/subtasks have no such
  inbound mapping.

## CLI — `remove` verb under the sub-entity subgroup

- Register `remove` in `_register_sub_verbs` (`src/squads/_cli/_items.py`), so it
  reaches all three built-in kinds (and any custom kind) generically. Guard with a
  `--yes` flag that skips an interactive `typer.confirm(..., abort=True)`, mirroring
  `_cmd_remove`'s wording ("This cannot be undone."). Consider a `--json` result
  (`{"removed": "<kind> <local_id>"}`) for scriptability, but keep the shape minimal.

## Tests

- Service + CLI: happy-path remove for each of finding/story/subtask (index +
  frontmatter both drop the entry, markers intact, sibling blocks + summary
  preserved); `--yes` bypasses the prompt and the prompt aborts without it;
  remove of a nonexistent local id raises `SquadsError`; the dangling-story-map
  behaviour above. Assert the reflog entry is written.

## Conventions (apply to every deliverable)

- No status/lifecycle prose in any body/doc (frontmatter `status:` is the single
  source of truth). The category term is **roster**, never "meta".
- No ticket IDs in source or test names — name by behaviour; keep the pointer in the
  sq ref/comment. Use PEP-695 `type X = …` for any alias. User-facing errors are the
  `SquadsError` family. Escape console output via `_cli._common.e()`.
- If you add any module-level constant, run `tests/meta` in your gate (the
  mutable-state guard has tripped repeatedly). Run all gates with `uv run --all-extras`
  (pyright/ruff/pytest) — a bare `uv run` prunes the `tui` extra and floods false
  errors.
- Set sq bodies via the CLI only; if you use `--file`, verify `grep -c '</\?content>'`
  == 0 on the written body. Run `uv run sq check` clean before handing off.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 627 add-subtask "<title>"`; track with `sq task 627 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T08:27:36Z] Elias Python:
  - Added guarded sub-entity remove (finding/story/subtask): new _sections.remove_section() (marker-safe whole-span excise, absorbs the block's own leading blank line so siblings/summary stay clean) + Service.remove_block() (atomic transaction, reflog op=remove with kind/local_id/title/status snapshot, roll-up summary re-rendered) + CLI 'remove' verb under each sub-entity subgroup (--yes guard mirroring item remove, optional --json {removed: '<kind> <local_id>'}). Policy decisions: (1) freed local-id — next_local_id recomputes from live max (documented on the function + pinned by two tests): a non-highest removed id is never reissued (genuine gap), but removing the highest-numbered one does free it for reissue — accepted as-is since a sub-entity local id is a within-parent label, not a durable cross-repo identity; (2) dangling story map — removing a story with subtasks still mapped to it is refused with a SquadsError listing the dependent task/subtask pairs (remap or remove them first), scoped to kind=='story' since subtask/finding have no inbound mapping. Gates green, sq check clean.
<!-- sq:discussion:end -->
