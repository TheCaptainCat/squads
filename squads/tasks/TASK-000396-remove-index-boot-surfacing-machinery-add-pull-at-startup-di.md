---
id: TASK-396
sequence_id: 396
type: task
title: Remove index/boot-surfacing machinery; add pull-at-startup directive
status: Draft
parent: FEAT-315
author: tech-lead
refs:
- REV-395:addresses
- FEAT-317:addresses
- FEAT-392:addresses
created_at: '2026-07-15T12:42:17Z'
updated_at: '2026-07-15T12:42:28Z'
---
<!-- sq:body -->
# Scope

Coordinated **source** rip-out of push-into-managed-files boot-surfacing and the per-folder
`.index.jsonl` roll-up, plus the small pull-at-startup addition. The pieces are interdependent
(deleting the generator breaks its importers), so **all source edits land in this single pass, one
dev** — do not fragment. The test/golden churn is the sibling task; the pytest suite is expected to
be RED after this task and turns green in the sibling. Do NOT touch test files here.

## Delete outright

- `src/squads/_content_index.py` — the whole generator (`IndexEntry`, `render_index`,
  `parse_index`, `regenerate`, `regenerate_from_content_files`, and its `INDEX_FILENAME =
  ".index.jsonl"`).
  - **Trap:** a *different* `INDEX_FILENAME = ".squads.json"` lives in `_models/_config.py` and is
    re-exported through `_paths.py` — that one **stays**. Only the `_content_index` one goes.
- `src/squads/_backends/_memory_surface.py`
- `src/squads/_backends/_board_surface.py`

## Memory store — `src/squads/_memory/_store.py`

- Delete `read_index` (its only caller was `_memory_surface`).
- Drop the `regenerate_from_content_files(...)` call in `add` and in `forget` (they no longer write
  an index).
- Remove the `_content_index` import block (`INDEX_FILENAME`, `IndexEntry`, `parse_index`,
  `regenerate_from_content_files`) and refresh the module docstring: storage is plain slug-named
  `.md` files only, no roll-up. `list_entries`/`search`/`read` already read the `.md` files directly
  and stay as-is.

## Board store — `src/squads/_board/_store.py`

- Delete `regenerate_index` and its calls in `post` and `clear`.
- Remove the `_content_index` imports (`IndexEntry`, `regenerate as regenerate_index_file`) and
  refresh the module docstring. `list_notices`/`clear` resolve the positional ordinal against the
  live sorted-unexpired listing computed from the `.md` files — that logic stays; only the derived
  index write goes.

## Maintenance — `src/squads/_services/_maintenance.py`

- Delete `_regenerate_content_indexes` and its `_memory_role_folders` helper (the helper has no
  other caller), and remove both call sites — one in `sync()`, one in `repair()`.
- Drop now-unused imports (`regenerate_from_content_files`; and check whether `board_store` is still
  referenced elsewhere in the module — if not, drop that import too).

## Templates

- `_rendering/templates/claude/pointer_agent.md.j2` — remove the `{% if memory_lines %}`
  `## Your memory` block.
- `_rendering/templates/claude/claude_section.md.j2` — remove the `{% if board_lines %}` `## Board`
  block.
- `_rendering/templates/agents_md/agents_section.md.j2` — remove the `{% if board_lines %}`
  `## Board` block **and** the per-role `{% if r.memory_lines %}` **Memory** block in the role
  definitions section.
- `_rendering/templates/agents/role.md.j2` — rewrite the current directive:

  > Before you start, review your `## Your memory` index and the team `## Board` — both surfaced
  > earlier in your boot context — and apply anything relevant.

  to the **pull** form: at the start of a run, run `sq memory <its-slug> list` and `sq board list`
  and apply anything relevant. Use the role's slug variable (the template already uses
  `extra.get('slug', item.slug)`). It must be unconditional and valid on an empty pool/board (an
  empty list simply lists nothing), and must not reference the removed rendered sections.

## Backend wiring

- `_backends/_claude_code/_backend.py` — remove the `board_notice_lines` / `memory_index_lines`
  imports and the `board_lines=` (claude_section render) and `memory_lines=` (pointer_agent render)
  context args.
- `_backends/_agents_md/_backend.py` — remove the imports, the `board_lines=` render context, and
  the per-role `"memory_lines": ...` entry built into `roles_data`.

## Gates (fast, this pass)

- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean.
- `uv run sq check` clean.
- Leave the pytest suite to the sibling test task; the manifest regeneration and all golden/test
  updates live there.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 396 add-subtask "<title>"`; track with `sq task 396 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
