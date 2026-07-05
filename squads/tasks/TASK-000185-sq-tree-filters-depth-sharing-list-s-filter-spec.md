---
id: TASK-185
sequence_id: 185
type: task
title: sq tree filters + --depth, sharing list's filter spec
status: Done
parent: FEAT-39
author: tech-lead
subentities:
- local_id: ST1
  title: Shared ItemFilter predicate + tree filter flags
  status: Done
  story: US1
- local_id: ST2
  title: Ancestor-preserving prune, --depth, path-only render + JSON
  status: Done
  story: US2
created_at: '2026-06-24T13:13:35Z'
updated_at: '2026-06-24T14:14:32Z'
---
<!-- sq:body -->
Give `sq tree` the same filters as `sq list` (`--type/-t`, `--status/-s`, `--assignee`, `--priority`) plus a new `--depth N`, while keeping the tree a tree: a filter matches **nodes**, but every match keeps its **ancestor chain** so it always shows in context. Acceptance criteria are on FEAT-39.

The whole point of the feature: **one filter implementation shared by `list` and `tree`, so they can never drift.** Get that shared piece right first; the rest is pruning + rendering on top.

## The core design decision — where the shared filter lives

Today `list` filtering is a per-field loop inside `ServiceCore.list_items` (`_services/_base.py:222`); `tree` calls `svc.list_items()` with **no** filters and builds its own parent→children map (`_cli/_main.py:335`, helper `_build_children` at line 311). If we add a second filter loop to `tree` they will drift the moment a flag changes. So:

**Extract the per-item match into one predicate, in the service layer, and have both `list_items` and the new tree pruner call it.** Add to `_services/_base.py` (next to `list_items`):

```python
@dataclass(frozen=True)
class ItemFilter:
    """The shared list/tree filter spec. One match predicate, used by both."""
    item_type: ItemType | None = None
    status: Status | None = None
    parent: str | None = None
    label: str | None = None
    assignee: str | None = None
    priority: Priority | None = None

    def matches(self, it: Item) -> bool:
        if self.item_type and it.type is not self.item_type: return False
        if self.status and it.status is not self.status: return False
        if self.parent and it.parent != self.parent: return False
        if self.label and self.label not in it.labels: return False
        if self.assignee and it.assignee != self.assignee: return False
        if self.priority and it.priority is not self.priority: return False
        return True

    def is_empty(self) -> bool:
        return not any((self.item_type, self.status, self.parent, self.label,
                        self.assignee, self.priority))
```

Then **`list_items` is reimplemented in terms of it** — keep its existing keyword signature (callers and the `list` CLI are unchanged), build an `ItemFilter` internally, and replace the inline `continue` chain with `if not f.matches(it): continue`. This is a pure refactor of `_base.py:232-247` with identical behaviour — assert that via the existing list tests.

`ItemFilter` lives in `_base.py` (or a tiny `_services/_filter.py` if `_base` gets crowded — dev's call, but it must be importable by both the base mixin and wherever the tree prune lands). It is the single source of truth for "what a filter means". When a future flag is added, it is added **here once** and both views get it. This directly satisfies the acceptance "filter flags, names and parsing are shared with `list` (one implementation), so the two never drift" — the *parsing* stays at the CLI edge (the same `parse_type`/`parse_status`/`parse_priority`/`resolve_slug_or_raise` helpers `list` already uses, see `_cli/_common.py:693+`), and the *semantics* are this one predicate.

## Where the prune/depth logic lives — service layer, not the CLI

Follow the FEAT-37 precedent exactly: TASK-182 put the graph **traversal** in the service (`_refs.py::graph`) returning a `GraphNode` dataclass, and left the CLI as a thin Rich/JSON renderer. Do the same here so the match+prune+depth logic is reusable by a future TUI/web and is unit-testable without the CLI.

Add to the service (the tree/hierarchy concern — put it where `list_items` lives, `_services/_base.py`, or a small focused method; keep it on the `Service` façade):

```python
async def tree_view(
    self,
    root_id: str | None = None,
    *,
    filter: ItemFilter | None = None,
    depth: int | None = None,
    include_closed: bool = False,
) -> list[TreeNode]:
    ...
```

returning a list of root `TreeNode`s. Add a frozen dataclass to `_services/_results.py`:

```python
@dataclass(frozen=True)
class TreeNode:
    item: Item
    path_only: bool        # True = ancestor kept only to anchor a descendant match
    children: list["TreeNode"]
```

`path_only` is **derived state for the renderer**, NOT persisted and NOT a JSON field (see JSON section). It is the marker the CLI uses to dim ancestors without changing the `--json` shape.

### Algorithm (service)

1. **Load the candidate set.** `items = all items`; if `not include_closed`, drop closed (`is_open`) — same gate `tree` uses today. This is the universe the tree is built from. (Note: unlike `list`, `tree` has no implicit "show closed when a status filter is given" rule — `tree` only widens on `--all`. Keep that; a `--status Done` tree with `--all` shows the Done nodes, without `--all` the closed gate removes them. Confirm with PO — see open questions.)
2. **Build the parent→children map and the id→item map** from that candidate set, reusing `_build_children` (it is width-tolerant across a repad; do not reinvent it).
3. **Determine roots** exactly as `tree` does today: explicit `root_id` → `[that item]` (error if absent from candidate set, same message as now); else the `children[None]` forest. `--depth` is measured **from each root** (root = level 0).
4. **Compute the match set** = `{it for it in candidate set if filter.matches(it)}`. If `filter` is None / `is_empty()`, every candidate matches (tree behaves like today, just with depth).
5. **Compute keep set = matches ∪ all-ancestors-of-each-match**, walking parent links up to a root via the children/parent map. An ancestor in the keep set but NOT in the match set is `path_only=True`.
6. **Prune + apply depth in one downward walk** from each root: include a node iff it is in the keep set; recurse into children; stop descending when the next level would exceed `depth` (when `depth is not None`). A node cut purely by depth disappears with its subtree (acceptance: "--depth truncates correctly"). Order children by `number_for_id` (stable, matches today).
7. A root that ends up with no kept descendants and is not itself a match is dropped — no orphaned/empty roots.

This guarantees the acceptance "never show an orphaned match: ancestor paths always intact" — because step 5 pulls in the full chain — and "path-only nodes visually distinct" via the `path_only` flag.

**Depth + prune composition:** apply both in the single walk of step 6 so they compose cleanly. Depth bounds *how deep we render*; prune bounds *which nodes survive*. A match deeper than `--depth` is **not** shown (depth wins on its own axis) — note this in tests and confirm it reads right to PO. Its kept ancestors above the cut still render (they are within depth).

## The CLI edge (`_cli/_main.py::tree`)

- Add the four filter options to the `tree` signature, **copied verbatim** from `list_items` (`_main.py:278-298`) — same names, same short flags, same help, same parsing/resolution (`parse_type`, `parse_status`, `parse_priority`, `resolve_slug_or_raise`, `resolve_item_id_any` for `--parent`). Add `--depth: int | None`.
- Build an `ItemFilter` from the parsed values and call `svc.tree_view(resolved_root, filter=..., depth=..., include_closed=all_)`.
- **Rendering** stays in the CLI, mirroring today's `label`/`attach` (lines 387-398). For a `path_only` node, render dimmed / marked so it is visually distinct from a real match — e.g. wrap the whole label in `[dim]…[/dim]` and/or append a faint ` ·` / `(path)` marker. Keep using `e()` on every dynamic string and `priority_badge` for priority. Decide the exact dim treatment with the renderer; the contract is only "visually distinct from a match".
- Reuse the existing not-found error for an explicit root that isn't in the candidate set (keep the current message, including the `--all` hint).

## `--json` shape — pruned, NOT reshaped

This is load-bearing and must be confirmed: the acceptance says "`--json` output is the **same shape**, pruned consistently with the rendered tree." Read that as: **do not add new fields to the JSON node.** The existing `node()` builder (`_main.py:373-382`) emits exactly `id/type/status/priority/assignee/blocked/children`. Keep those keys and nothing else. The filtering/depth simply means **fewer nodes appear** (the tree is pruned), but each surviving node has the identical key set it has today. In particular **do not** add a `path_only` (or `match`) key to JSON — `path_only` is a render-only concern; a JSON consumer sees a path-only ancestor as an ordinary node that happens to have a matching descendant, which is exactly the pruned-not-reshaped contract.

Implementation: the CLI's `node()` walks the `list[TreeNode]` returned by `tree_view` (instead of the old `children`/`kids` closures), reads `.item` for the fields, recurses over `.children`, and **ignores** `.path_only`. `blocked` is still computed from `svc.blocked()` as today. Golden-test the pruned JSON for a fixed fixture (per FEAT-15 / the graph precedent), asserting the key set is unchanged.

## Module-by-module summary

- `_services/_base.py` (or new `_services/_filter.py`): add `ItemFilter` (frozen dataclass + `matches` + `is_empty`); reimplement `list_items` in terms of it (pure refactor, behaviour identical).
- `_services/_base.py`: add `tree_view(...)` returning `list[TreeNode]` — match set, ancestor keep set, depth-bounded prune. Reuse `_build_children` (move it from `_cli/_main.py` to the service if cleaner, or keep a shared copy — but do NOT duplicate parent-resolution logic; one implementation).
- `_services/_results.py`: add `TreeNode` frozen dataclass (`item`, `path_only`, `children`).
- `_services/_service.py`: ensure `tree_view` is exposed on the façade (mixin composition).
- `_cli/_main.py::tree`: add filter options + `--depth`, build `ItemFilter`, call `tree_view`, render path-only nodes dimmed, walk `TreeNode` for both Rich and `--json` (same JSON keys).
- Tests: service-level (match-set, ancestor preservation, depth truncation, depth-vs-match interaction, empty-filter = today's tree) + CLI smoke (each flag alone and combined, with/without explicit root, with/without `--all`) + a `--json` golden proving same-shape pruning + a regression asserting `list` output is unchanged by the refactor.

## Acceptance mapping (from FEAT-39)

- "Each filter works alone and combined, with/without explicit root; `--depth` truncates" → US1 (filters) + US2 (depth).
- "Never an orphaned match; ancestor paths intact; path-only nodes visually distinct" → US2 (keep set + `path_only` rendering).
- "`--json` same shape, pruned consistently" → US2 (JSON walks the pruned `TreeNode` list, same keys).
- "Filter flags, names, parsing shared with `list` (one implementation)" → US1 (`ItemFilter` predicate + reused CLI parsers).

## Out of scope (per feature)

Filtering by ref kinds / graph relations — that is FEAT-37 (`sq graph`).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 185 add-subtask "<title>"`; track with `sq task 185 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Shared ItemFilter predicate + tree filter flags | US1 |
| ST2 | Done |  | Ancestor-preserving prune, --depth, path-only render + JSON | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Shared ItemFilter predicate + tree filter flags

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Filter tree by status/priority/assignee/type for focused reviews
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
US1 — filter the tree by status/priority/assignee/type, sharing list's filter spec.

Extract the per-item match from ServiceCore.list_items (_base.py:222) into a frozen ItemFilter (item_type/status/parent/label/assignee/priority) with .matches(it)->bool and .is_empty(). Reimplement list_items in terms of it — pure refactor, identical behaviour; prove with existing list tests.

CLI: add the four filter options to tree (_main.py:335) copied VERBATIM from list_items (_main.py:278-298) — same names, short flags, help, and the same parsers (parse_type/parse_status/parse_priority/resolve_slug_or_raise, resolve_item_id_any for --parent). Parsing stays at the CLI edge; semantics live in the one ItemFilter. This is the 'one implementation, never drift' acceptance.

Tests: service test that ItemFilter.matches matches list_items behaviour field-by-field; CLI smoke that each tree filter works alone and combined; a regression asserting list output is unchanged by the refactor.

Done = each filter flag exists on tree with list-identical names/parsing, backed by the shared predicate.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Ancestor-preserving prune, --depth, path-only render + JSON

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — --depth and context-preserving pruning keep filtered trees readable
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
US2 — --depth + context-preserving pruning keep filtered trees readable.

Service: add tree_view(root_id=None, *, filter: ItemFilter|None, depth: int|None, include_closed=False) -> list[TreeNode] in _base.py (on the Service facade), mirroring how FEAT-37 put graph traversal in _refs.py. Add TreeNode(item, path_only: bool, children) to _results.py — path_only is render-only derived state, never persisted.

Algorithm: load candidate set (drop closed unless include_closed); build parent->children via the existing _build_children (width-tolerant — reuse, don't reinvent); determine roots like tree does today; match set = {filter.matches(it)}; keep set = matches UNION all-ancestors-of-matches (walk parents to a root); ancestors not themselves matches => path_only=True; then a single downward walk prunes to the keep set and cuts below --depth (depth measured from each root, root=level 0); drop empty/orphan roots.

Depth vs match: a match deeper than --depth is NOT shown (depth wins on its own axis); its in-depth ancestors still render. Note in tests; confirm reading with PO.

CLI render: path_only nodes shown dimmed/marked, visually distinct from a real match (e.g. wrap label in [dim]); keep e() on dynamic strings + priority_badge.

--json: SAME shape, pruned not reshaped. The node() builder keeps EXACTLY id/type/status/priority/assignee/blocked/children — do NOT add a path_only/match key. Walk the pruned TreeNode list; fewer nodes appear but each surviving node's key set is unchanged. Golden-test the pruned JSON.

Tests: ancestor preservation (no orphaned match), depth truncation, depth-vs-deep-match, empty filter == today's tree, with/without explicit root, with/without --all; --json same-shape golden.

Done = a filtered tree always shows full ancestor paths, path-only nodes are distinct, --depth truncates, and --json is pruned with an unchanged shape.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-24T13:15:47Z] Olivia Lead:
  - @python-dev TASK-185 is Ready — sq tree gains list's filters (--type/-t, --status/-s, --assignee, --priority) + a new --depth N, with ancestor-preserving pruning. Full plan + module-by-module in the body; read it with: sq task 185 show --full.
  - Build order: ST1 first (US1) — extract a frozen ItemFilter predicate from list_items (_base.py:222) and reimplement list_items on top of it (pure refactor, prove behaviour unchanged), then copy the four filter flags onto tree VERBATIM from list_items (_main.py:278-298), reusing the same CLI parsers. Then ST2 (US2) — add tree_view(...) -> list[TreeNode] in the SERVICE (mirror FEAT-37's service-layer traversal), computing match set UNION ancestors and a --depth cut; CLI dims path_only ancestors.
  - Two hard constraints: (1) ONE filter implementation shared by list+tree — the ItemFilter predicate is the single source of truth, parsing stays at the CLI edge. (2) --json is pruned, NOT reshaped — keep EXACTLY id/type/status/priority/assignee/blocked/children; do not add a path_only/match key. Golden-test the pruned JSON. Reuse _build_children (width-tolerant), don't reinvent parent resolution.
  - Two reads I want PO to confirm before they bite you (see my note to @manager): tree's closed-item gate vs --status, and depth-wins-over-deep-match. I flagged both to the manager; proceed on my documented reading unless you hear otherwise.
  - @manager Broke FEAT-39 into TASK-185 (Ready, not started): ST1->US1 (shared ItemFilter + tree filter flags), ST2->US2 (ancestor-preserving prune + --depth + path-only render + pruned-not-reshaped JSON). Shared-filter decision: a frozen ItemFilter in _services/_base.py is the single match predicate; list_items refactored onto it, tree's CLI flags copied verbatim from list with the same parsers. Two open questions for you/PO in my report.
- [2026-06-24T13:17:01Z] Catherine Manager:
  - Decisions on Olivia's two open questions (proceed on these): (1) tree MIRRORS list's closed-item gate exactly — a --status filter (or --all) reveals matching closed items; priority/assignee/type filters alone do NOT widen to closed. This is the 'one implementation, never drift' requirement applied to behaviour, not just flags. (2) --depth wins over a deeper match: --depth N shows the first N levels; a match below the cut is simply out of scope (not an 'orphaned match' — that rule is about ancestors of SHOWN matches). Both confirmed with @op-pierre in-session.
  - @python-dev proceed with implementation on Olivia's documented plan + these two confirmations. Keep the match/prune/depth logic in the service (tree_view -> TreeNode) and rendering at the CLI edge; --json stays the exact same shape, pruned not reshaped (no path_only field in JSON). @manager
- [2026-06-24T14:05:16Z] Elias Python:
  - ST1 complete: extracted frozen ItemFilter(item_type/status/parent/label/assignee/priority) with matches()->bool and is_empty() into _services/_base.py. Reimplemented list_items in terms of ItemFilter.matches — pure refactor, identical behaviour confirmed by all existing list/service tests staying green.
  - ST2 complete: added TreeNode(item, path_only, children) to _services/_results.py; added tree_view(root_id, *, filter, depth, include_closed) -> list[TreeNode] to ServiceCore in _base.py; extracted _compute_keep_set and _walk_tree module helpers to satisfy the max-complexity 12 constraint. Algorithm: load candidates, build maps, determine roots, match set, keep set=matches UNION ancestors, single downward walk with depth cut + path_only flag for non-matching ancestors. Removed _build_children from CLI (replaced by service-layer _build_tree_children).
  - CLI tree command (_cli/_main.py): added --type/-t, --status/-s, --assignee, --priority flags COPIED VERBATIM from list_items (same names/parsers); added --depth int|None. Mirrors list's closed-item gate: include_closed = bool(all_ or status) so --priority/--assignee/--type alone do NOT widen to closed. path_only ancestors rendered dimmed via [dim]...[/dim]. --json walks TreeNode list, ignores path_only, emits same id/type/status/priority/assignee/blocked/children keys unchanged.
  - Tests: 45 new tests in tests/test_tree.py — ItemFilter unit (each field, combined AND, is_empty), shared-filter regression asserting ItemFilter.matches == list_items behaviour (no drift), tree_view service tests (empty filter=all-items, type/priority/assignee/combined filters, explicit root, ancestor preservation no-orphan, path_only flag correct, matching ancestor not path_only, depth 0/1/N, depth-wins-over-deep-match, include_closed gate, status filter reveals closed), CLI smoke (each flag alone and combined, explicit root+filter, --all, --depth 0/1, dim rendering, --status reveals closed, non-status does not widen, --json no path_only key, same shape filtered vs unfiltered, ANSI-free, pruned consistently, --json golden, --depth JSON). Golden: tests/goldens/tree_task_json.json.
  - Gate result: pyright 0 errors, ruff clean, ruff format clean. Full suite: 1104 passed, 1 skipped (pre-existing skip). @reviewer @manager
- [2026-06-24T14:13:13Z] Elias Python:
  - F1 fix: replaced the hollow test_cli_tree_path_only_ancestors_dimmed (which only re-checked node presence, not dimming) with async test_path_only_ancestors_flagged_and_match_not — a service-layer test that directly asserts root.id and mid.id carry path_only=True and leaf.id carries path_only=False. This is the genuine boundary: the CLI emits [dim] based on the path_only flag, CliRunner strips Rich markup, so the service layer is the right place to assert the distinction.
  - F2 fix: rewrote _build_tree_children docstring to remove the stale reference to _build_children (which was deleted in this change). New text: 'Used by tree_view and shared by any future caller that needs the same parent-resolution logic; keeps parent resolution in one place.'
  - Gate: 45 passed in tests/test_tree.py, pyright 0 errors, ruff clean, ruff format clean. @reviewer @manager
- [2026-06-24T14:14:31Z] Catherine Manager:
  - Loop closed. Independent review (REV-186) → Approved; all 4 acceptance criteria + both behaviour decisions (mirror list's closed gate; --depth wins over a deeper match) verified — by the reviewer live end-to-end and by me via live CLI checks (ancestor-preserving prune with dimmed path-only ancestors, depth truncation, --status revealing closed matches, non-status filters not widening). Shared ItemFilter predicate keeps list + tree from drifting.
  - F1 (hollow path-only dim test) rewritten to assert path_only at the service layer; F2 (stale _build_children docstring) reworded — both Verified. Tree suite 45 green, pyright/ruff clean; full suite was green at 1104 before the test-only cleanup. ST1/ST2 Done. @reviewer @python-dev thanks.
<!-- sq:discussion:end -->
