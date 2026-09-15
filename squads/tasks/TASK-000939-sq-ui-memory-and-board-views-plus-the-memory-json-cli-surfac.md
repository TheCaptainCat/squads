---
id: TASK-939
sequence_id: 939
type: task
title: sq ui memory and board views, plus the memory --json CLI surface
status: Done
parent: FEAT-690
author: tech-lead
assignee: python-dev
subentities:
- local_id: ST1
  title: Carry created_at into sq memory list --json
  status: Done
  story: US1
- local_id: ST2
  title: Add sq memory show --json
  status: Done
  story: US1
- local_id: ST3
  title: Nest memory under Roster identities in the sq ui tree
  status: Done
  story: US1
- local_id: ST4
  title: A memory-shaped reader for the sq ui drill-in step
  status: Done
  story: US1
- local_id: ST5
  title: Board screen in sq ui
  status: Done
  story: US2
created_at: '2026-09-14T12:14:24Z'
updated_at: '2026-09-15T07:44:23Z'
---
<!-- sq:body -->
The Python half of the two knowledge surfaces: per-role memory and the team board, read-only,
in `sq ui` — plus the two `sq memory` JSON additions the VS Code client needs. One dev pass:
the CLI additions and the TUI work touch adjacent code and share the same `Service` calls, so
they are not worth splitting across devs who would collide.

`sq ui` needs no CLI change of its own — it runs in-process against `Service`, which already
returns a full `MemoryEntry` (summary, `created_at`, tags, body) from `memory_list()` and
`memory_show()`, and a full `BoardNotice` from `board_list()`. The CLI additions here exist
only so the extension can reach the same data.

## Files

- `src/squads/_cli/_memory.py` — `list_memories` (the `--json` branch), plus a new `--json`
  path on `show_memory`.
- `src/squads/_tui/_tree.py` — roster identities gain children for the first time.
- `src/squads/_tui/_browse.py` — the tree's node payload type, highlight dispatch, the board
  keybinding.
- `src/squads/_tui/_reader.py` (or a new sibling module) — memory has no sub-entities and no
  discussion, so the three-tab `ReaderPanel` is the wrong shape for it.
- a new `src/squads/_tui/` screen module for the board, peer to `_filter.py` / `_search.py`.
- `tests/cli/`, `tests/tui/`.

## Design constraints

**Tree payload.** `BrowseScreen` holds a `Tree[str]` whose node data is an item id, and
`on_tree_node_highlighted` feeds that straight to `ReaderPanel.load`. A memory child is not an
item and has no item id, so the payload has to become a small typed value that says which of
the two it is (group nodes already carry `None`). Everything that reads `node.data` must go
through that discriminator rather than assuming a string is an item id.

**Which identities carry a notebook.** The pool folder is keyed on the role slug
(`squads/agents/memory/<slug>/`), and the roster item's own `slug` field is that slug — checked
against `sq list --type role --json`, which returns `manager` / `tech-lead`, not the filename
stem. Roles and operators have notebooks; skills do not. Reuse the existing reserved-type
handling rather than introducing a fresh literal list.

**Eager, not lazy.** The whole point of the view is comparing hygiene across the roster at a
glance, so the fetch happens as part of `refresh_tree()` — one `memory_list()` per identity —
not on node expansion. The roster is small (10 roles + 1 operator here) and these are
in-process directory reads.

**Degraded reads stay visible.** `memory_list()` returns `(entries, unreadable)`. A shortened
list with nothing said about it is the failure mode to avoid; follow `_search.py`'s
`_skipped_note` precedent and say the listing is partial.

**Sort and filter.** `sort_siblings` reorders `TreeNode`s; memory children are not `TreeNode`s
and must be left alone by it rather than crashing it. The status filter has no meaning for a
memory entry.

**Bracket safety.** Memory bodies, summaries and notice text are free-form and may contain
`[...]`. Build labels from `Text.assemble` spans or `Content.from_markup` template variables,
never by concatenating content into a markup string — `tests/tui/test_bracket_content_renders_safely.py`
is the existing precedent.

**Read-only.** No `memory add` / `memory forget` / `board post` / `board clear` path from the
TUI. Acting on what the view surfaces stays a terminal job.

## Acceptance criteria

- `sq memory <role> list --json` emits `created_at` on every entry; `slug`, `filename` and
  `description` keep their current names and values, so a client reading only the old keys is
  unaffected. Non-JSON output is unchanged.
- `sq memory <role> show <slug> --json` exists and prints one object carrying at least `slug`,
  `summary`, `created_at`, `tags` and `body`. Non-JSON output is unchanged. An unknown slug
  keeps failing the way it does today.
- In `sq ui`, every role and operator node under Roster shows its memory count and how long
  ago its most recent entry was written, before anything is expanded. A roster identity with
  an empty pool reads as zero rather than as a missing signal.
- Expanding such a node lists its entries as children, each showing slug + summary + age,
  ordered oldest-touched first (ties broken stably by slug).
- Skill nodes gain no children.
- Selecting a memory child opens its full body in a reader suited to a memory (header with
  slug, timestamp and tags; body rendered as markdown), not the three-tab item reader, and
  never attempts to resolve it as an item id.
- A role whose pool contains an unreadable file still lists its readable entries, and the
  screen says the listing is partial.
- A keybinding on the browse screen opens a board screen listing current notices newest-first
  with author, posted-at, expiry where set, and the notice body; escape closes it. Unreadable
  notices are reported the same way.
- A memory summary, memory body or notice body containing square brackets renders literally in
  every one of those surfaces.
- `uv run --all-extras pyright`, `uv run --all-extras ruff check .` and
  `uv run --all-extras ruff format --check .` are clean.
- New tests cover both JSON shapes, the parent-node signal, the child ordering, the memory
  reader and the board screen. Name tests by behaviour; no ticket ids in source or filenames.

## Scope boundary

Run the targeted suites you touch (`tests/cli`, `tests/tui`) rather than the full sweep — the
main loop owns the authoritative full run. Note that the Textual tests are intermittently
flaky under `-n auto`; re-run a single failing test alone before calling it a regression.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 939 add-subtask "<title>"`; track with `sq task 939 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Carry created_at into sq memory list --json

<!-- sq:subtask:ST1:body -->
Add `created_at` to each entry object in the `--json` branch of `list_memories` (`src/squads/_cli/_memory.py`). The value is already on every `MemoryEntry` the service returns; this exposes it. Keep `slug`, `filename` and `description` byte-identical so a client reading only the old keys is unaffected, and leave the non-JSON listing alone. This is the one change that unlocks the extension staleness signal.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add sq memory show --json

<!-- sq:subtask:ST2:body -->
New `--json` option on `show_memory` (`src/squads/_cli/_memory.py`), which today has no machine-readable path at all — the extension drill-to-body has nothing to call. Emit one object carrying at least `slug`, `summary`, `created_at`, `tags` and `body`. Non-JSON output unchanged; an unknown slug keeps failing the way it does today. Route through `print_json_clean` like every other JSON branch.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Nest memory under Roster identities in the sq ui tree

<!-- sq:subtask:ST3:body -->
Roster leaves in `src/squads/_tui/_tree.py` have never had children. Give each role and operator node an eager `svc.memory_list(slug)` fetch during `BrowseScreen.refresh_tree`, a glance-level count plus most-recent-entry age on the parent label, and its entries as children sorted oldest-touched first (ties stable by slug). Skills gain nothing.

Two structural consequences to handle rather than work around: the tree payload is `Tree[str]` holding an item id that `on_tree_node_highlighted` feeds straight to `ReaderPanel.load`, so it needs a typed discriminator; and `sort_siblings` reorders `TreeNode`s, which memory children are not — it must leave them alone, not crash on them. Labels go through `Text.assemble` spans, never string concatenation, since summaries are free-form. A pool with an unreadable file still lists its readable entries and says the listing is partial, following the `_skipped_note` precedent in `_search.py`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — A memory-shaped reader for the sq ui drill-in step

<!-- sq:subtask:ST4:body -->
A memory has no sub-entities and no discussion, so the three-tab `ReaderPanel` in `src/squads/_tui/_reader.py` is the wrong shape for it. Add a small reader of its own: header with slug, created-at and tags, body rendered as markdown via `svc.memory_show(role_slug, slug)`. Selecting a memory child routes here through the tree payload discriminator and never tries to resolve the entry as an item id. Bodies are free-form, so bracket-bearing text must render literally.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Board screen in sq ui

<!-- sq:subtask:ST5:body -->
A modal `Screen` peer to `FilterScreen` and `SearchScreen`, in its own module under `src/squads/_tui/`, opened by a keybinding on `BrowseScreen` (`f` and `/` are taken, `q` quits). Lists `svc.board_list()` newest-first with author, posted-at, expiry where set, and the body rendered as markdown; escape closes. Notices that could not be read are reported rather than silently dropped. No CLI change needed — `Service.board_list` already returns the full `BoardNotice`. Read-only: no post or clear path.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-14T12:44:01Z] Elias Python:
  - All five subtasks landed and marked Done; `sq check` clean.
    
    **ST1/ST2** — `src/squads/_cli/_memory.py`: `list_memories --json` now carries `created_at` alongside the unchanged `slug`/`filename`/`description`; `show_memory` gained `--json` (slug/summary/created_at/tags/body). Non-JSON paths and the unknown-slug error shape are unchanged.
    
    **ST3** — `src/squads/_tui/_tree.py`: Role/Operator leaves under Roster now carry an eager `memory_list()`-derived count+recency suffix on their own label ("memory: 0" / "memory: N · Xd ago"), and their pool as UI-only children (oldest-touched first, ties by slug), gated on `ROSTER_ROLE`/`ROSTER_OPERATOR` (skills untouched). New `NodeData = str | MemoryNodeData` discriminator; the fetch is eager in `BrowseScreen.refresh_tree()` (one `memory_list()` per visible identity, via new `roster_identity_slugs()`), never in `populate_tree`/`sort_siblings` — the latter still only ever sees real `TreeNode`s, so it needed no defensive code, just the type-level separation. An unreadable pool file still lists its readable entries plus a "listing partial" leaf.
    
    **ST4** — new `src/squads/_tui/_memory_reader.py` (`MemoryReaderPanel`): header (slug/created-at/tags) + markdown body. `BrowseScreen` now holds a `ContentSwitcher` between it and the item `ReaderPanel`, switching on the tree payload's type in `on_tree_node_highlighted` — a memory child never reaches `ReaderPanel.load`.
    
    **ST5** — new `src/squads/_tui/_board.py` (`BoardScreen`): modal, `b` keybinding, notices newest-first with author/posted-at/expiry/body, degraded-partial reporting on an unreadable notice, escape closes. No CLI change needed (`board_list()` already full).
    
    Bracket safety followed existing precedent throughout (`Text.assemble` spans for tree labels, `Content.from_markup` template vars for the memory-reader header, plain Markdown for body/notice text) — covered by a new bracket-content test in `test_board_screen.py` plus the existing suite's own coverage.
    
    Also updated `_find()`'s type in `tests/tui/test_bracket_content_renders_safely.py` / `test_search_screen.py` from `TreeNode[str]` to `TreeNode[NodeData]` — the tree's generic changed, invariantly, so those local helpers needed the same type.
    
    New tests: `tests/cli/test_memory_cli.py` (+5), `tests/tui/test_memory_view.py` (8, new file), `tests/tui/test_board_screen.py` (5, new file). Falsified each new mechanism by hand (broke it, watched red, restored, watched green): CLI `created_at`/`show --json` (4 tests reddened when reverted — `show --json` not existing yet showed as exit 2), the parent-node count+age suffix, oldest-first sort, the memory-pool degraded-partial leaf, the reader-switcher dispatch (2 tests), board newest-first ordering, board degraded-partial reporting. All restored clean afterward (diffed byte-identical against the pre-falsification files).
    
    Gates, `--all-extras` throughout: `pyright` 0 errors, `ruff check` all passed, `ruff format --check` all formatted. Targeted suites: `pytest tests/tui/ tests/cli/test_memory_cli.py` → 82 passed; `pytest tests/meta` → 303 passed (ran it since `_tree.py` gained a new module-level constant, `_AGE_UNITS`, though it's an immutable tuple rather than dict/list). Did not run the full suite per the standing rule — that's yours.
    
    Files touched: `src/squads/_cli/_memory.py`, `src/squads/_tui/_tree.py`, `src/squads/_tui/_browse.py`, `src/squads/_tui/_board.py` (new), `src/squads/_tui/_memory_reader.py` (new), `tests/cli/test_memory_cli.py`, `tests/tui/test_memory_view.py` (new), `tests/tui/test_board_screen.py` (new), `tests/tui/test_bracket_content_renders_safely.py`, `tests/tui/test_search_screen.py`.
    
    Nothing left unfinished on this task. Left the task itself and FEAT-690 untouched, per scope. @manager over to you for verification and status.
- [2026-09-14T12:46:26Z] Catherine Manager:
  - Verified as authoritative gate: full suite 5036 passed / 12 skipped / 0 failed; pyright 0 errors; ruff check + format clean. Traced the TUI seam myself — sort_siblings runs on the service-level forest before populate_tree attaches memory as UI-only children, so the by-construction claim holds; highlight dispatch is a real typed discriminator. Hygiene greps clean (no ticket ids, no direct datetime.now, no stray wrapper tags). Held at InReview rather than Done: this is a visual surface, so op-pierre eyeballs sq ui before it closes.
- [2026-09-15T07:44:20Z] Pierre Chat:
  - Looked at the dev host: the memory and board surfaces look good. Visual sign-off given.
<!-- sq:discussion:end -->
