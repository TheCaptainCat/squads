---
id: EPIC-99
sequence_id: 99
type: epic
title: VS Code extension — browse the squad in the editor
status: Done
author: product-owner
priority: low
refs:
- FEAT-15:depends-on
- EPIC-12
- EPIC-28
- EPIC-29
- EPIC-38
description: 'A VS Code extension: a sidebar tree of the squad + items opened in the
  markdown preview; consumes the frozen --json surface; browse-first, mutations a
  later increment'
created_at: '2026-06-14T20:45:06Z'
updated_at: '2026-07-19T19:33:00Z'
---
<!-- sq:body -->
## Outcome

Operators who live in VS Code get the squad without leaving the editor: an activity-bar **sidebar
tree** of the hierarchy (status / assignee / blocked at a glance), and clicking an item opens its
**`sq show --raw` clean-markdown output in the markdown preview**. The CLI stays the tool for *doing*; the extension
becomes the editor-native tool for *seeing* — a fourth frontend next to `sq ui` (EPIC-28),
`sq web` (EPIC-29) and the plain-CLI reading experience (EPIC-38).

## Framing

- **Browse-first, not read-only-by-design**: the first increment ships navigation and reading — the
  cheap, high-value 80% — but mutations (transition, comment, assign) via `sq` from context menus are
  an explicit later increment, not a non-goal.
- **A pure consumer of the machine surface.** The extension shells out to `sq … --json` and parses
  the frozen 1.0 shapes (EPIC-12's FEAT-15): `sq tree --json` drives the tree (blocked-state
  included), `sq list --json` feeds flat/filtered views. Item display runs **`sq show <id> --raw`**
  (FEAT-26) into VS Code's markdown preview via a read-only virtual document — clean markdown, no
  frontmatter or `<!-- sq:* -->` marker noise. It never reads `.claude/` or parses `.squads.json`
  directly (the index is not a frozen surface).
- **Placement**: in-repo at `clients/vscode/` — a TypeScript/Node package with its own toolchain,
  isolated from the Python uv/pyright/ruff core and CI.

Features (the product owner will author them when this epic activates): read-only browse (tree +
rendered preview) first, then the first mutation increment.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-16T13:37:42Z] Pierre Chat:
  - Greenlit for 0.10: ship FEAT-100 (read-only browse) only; mutations deferred. New typescript-dev role (Ada) will build it. Architect to record a cross-language client ADR before tasks are cut.
- [2026-07-19T19:33:00Z] Catherine Manager:
  - Closed: both features (FEAT-449, FEAT-471) and all child tasks Done; the VS Code extension alignment work is complete. Tidying the board ahead of the 0.10 cut.
<!-- sq:discussion:end -->
