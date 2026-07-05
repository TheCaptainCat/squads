---
id: TASK-44
sequence_id: 44
type: task
title: 'Cosmetic cleanup: drop redundant show ''Body'' label and add tree separator
  (BUG-000025, BUG-000030)'
status: Done
author: tech-lead
assignee: python-dev
priority: low
refs:
- BUG-25:fixes
- BUG-30:fixes
created_at: '2026-06-11T12:14:53Z'
updated_at: '2026-06-11T12:50:23Z'
---
<!-- sq:body -->
## Goal

Two cosmetic fixes to the human-readable CLI surface, plus a consistency sweep. Machine surfaces (`--json`) are untouched.

## What to change

1. **Drop the redundant 'Body' label (BUG-25)** — `sq <type> <n> show` prints a bare `Body` literal between the metadata panel and the body. Remove it; the body is self-evident after the panel and opens with its own markdown headings. This is the only viewer-injected literal — real markdown headings in the file (e.g. the discussion) stay as-is. In `_cli/` (the show command). NOTE: rendering the body as markdown via rich is explicitly OUT of scope (separate, see BUG-25 notes / FEAT-26).
2. **Tree priority/title separator (BUG-30)** — in `sq tree`'s human rendering, the priority label and title run together (`🟠 high Stability contract documentation`). Put a middle dot between them: `🟠 high · Stability contract documentation`. `sq tree --json` is untouched (FEAT-15's machine surface).
3. **Consistency sweep** — apply the same `·` separator to other composed lines that share the pattern: `sq blocked`, `sq mine` output. `sq list` is columnar and unaffected. Keep the separator consistent everywhere.

## Notes / invariants

- Escape dynamic output with `_cli._common.e()` when printing user/content strings (Rich treats `[...]` as markup).
- Only human-readable rendering changes; no JSON surface, no model/frontmatter changes.

## Acceptance

- Service-level / rendering tests: show output has no `Body` literal; composed lines carry the `·` separator between priority and title.
- CLI smoke tests: `sq <type> <n> show` (no `Body` label), `sq tree` (dot present), `sq blocked` / `sq mine` (consistent separator), `sq tree --json` unchanged.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 44 add-subtask "<title>"`; track with `sq task 44 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T12:45:46Z] Elias Python:
  - Implemented BUG-25 and BUG-30 fixes.
  - BUG-25: removed the viewer-injected 'Body' literal in print_item() (_cli/_common.py line 120); replaced console.print('\n[bold]Body[/bold]') with console.print() so a blank line still separates the panel from the body — no markdown rendering change.
  - BUG-30: added '·' separator between priority badge and title in tree's label() function (_cli/_main.py line 202); prio format changed from '{badge} ' to '{badge} · '.
  - Consistency sweep: blocked and mine outputs don't compose priority+title (blocked shows title only, mine uses columnar _item_table), so no other sites needed updating.
  - Tests: test_show_has_no_body_label in test_cli.py; test_tree_priority_dot_separator in test_priority_views.py. Full suite: 247 passed, 1 skipped. pyright: 12 errors (all pre-existing baseline). ruff check: 12 errors (pre-existing). ruff format: only _discussion.py (pre-existing). @tech-lead ready for review.
- [2026-06-11T12:50:23Z] Olivia Lead:
  - Review PASS — Done. 'Body' literal removed from print_item (replaced with a blank line); verified 'sq <type> <n> show' no longer prints a standalone 'Body' header, body content intact. tree human rendering now uses '🟠 high · beta' (middle dot); tree --json untouched.
  - Consistency-sweep claim verified: blocked renders 'id title (status)' with no priority badge, and mine uses the columnar _item_table — neither composes priority+title inline, so tree was correctly the only site to change. Dynamic output still escaped via e(). 2 new tests; JSON surface asserted unchanged. Clean gates.
<!-- sq:discussion:end -->
