---
id: TASK-683
sequence_id: 683
type: task
title: Set VS Code Marketplace categories, keywords & description
status: Draft
author: product-owner
created_at: '2026-07-28T12:43:01Z'
updated_at: '2026-07-28T13:28:28Z'
---
<!-- sq:body -->
The extension currently ships `categories: ["Other"]`, no `keywords`, no `galleryBanner`, no
`qna`, and a description that only mentions work items. Apply the following to
`clients/vscode/package.json` (values chosen against VS Code's current fixed category enum —
`AI, Azure, Chat, Data Science, Debuggers, Education, Extension Packs, Formatters, Keymaps,
Language Packs, Linters, Machine Learning, Notebooks, Programming Languages, SCM Providers,
Snippets, Testing, Themes, Visualization, Other` — confirmed from
`microsoft/vscode:src/vs/platform/extensions/common/extensions.ts`, not the older docs page,
which is missing `AI`/`Azure`/`Chat`):

## categories

```json
"categories": ["AI", "Visualization"]
```

- **AI** — squads is a coordination layer for a team of AI coding agents; this extension is the
  in-editor window onto that team's work. That's the shelf a user browsing for AI-agent tooling
  will check, and precedent exists for browse/companion extensions claiming it (e.g. GitHub's own
  Pull Requests extension lists `AI`/`Chat` without shipping a chat participant on every surface).
- **Visualization** — the extension's actual mechanism is visualizing structured project data:
  hierarchical work-item trees, a roster view, rendered item dossiers, and two collapsible mermaid
  graphs (refs + subtree). Genuinely descriptive, not a reach.
- Near-misses that lost: **Chat** (no chat participant or chat-view contribution — would overclaim
  a capability this extension doesn't have); **Extension Packs** / **SCM Providers** / **Testing**
  / **Data Science** / **Machine Learning** / **Notebooks** / **Language Packs** / **Azure** (none
  describe what this does); **Other** (dropped — it's the "nobody chose" default we're fixing).
- On the read-only tension: none of the 20 valid categories say "task management" or "project
  management" at all, so there's no category here that over-promises write capability. That risk
  lives in keywords/copy, not this field.

## keywords

```json
"keywords": [
  "ai agents",
  "multi-agent systems",
  "agent orchestration",
  "claude code",
  "agentic development",
  "work item tracking",
  "issue tracking",
  "project tracking",
  "team roster",
  "markdown"
]
```

Two different searches are possible here — "I want in-editor issue/project tracking" vs. "I want
tooling for coordinating AI coding agents" — and they're not symmetric: squads' actual identity is
the latter (a coordination layer for named AI agents; work-item tracking is the mechanism, not the
pitch). Keywords are ordered AI-agent-first for that reason, with the tracking-domain terms kept
(accurate — it does browse work items, issues, and tracking status) so the other audience still
lands on it. `claude code` is included because it's the one backend that exists today (accurate,
not aspirational) and a high-intent search term. Deliberately excluded: `kanban`/`board` (the
extension has no swimlane/board UI, only trees — would overclaim the UI paradigm); `task manager`
(implies mutation this read-only extension can't do).

## galleryBanner — skip

Not setting this now. It requires picking a background color (and light/dark theme) that
complements the actual icon asset's palette — a visual design call belonging to whoever owns the
icon/packaging work, not a metadata call to invent blind. Leave unset; revisit alongside any icon
rework.

## qna

```json
"qna": false
```

Explicitly disable the Marketplace's built-in Q&A widget. The `repository` field already points
at GitHub, which is where the team actually watches for issues; a second, unmonitored comment
channel on the Marketplace page is worse than none. Don't set `qna` to a custom URL string either
— GitHub Issues is the one channel, and `repository`/`bugs` already say so.

## description

Current: `"Browse a squads-managed project's work items from VS Code."` — undersells: it drops
the AI-agent framing (squads' actual differentiator), never mentions the roster view or dossier
preview, and reads as a generic PM-extension blurb with an unfamiliar product name attached.
Replace with:

```json
"description": "Browse your AI-agent team's work items, roster, and workflow in VS Code — read-only companion for squads-managed projects."
```

Leads with the AI-agent hook, names the three real surfaces (work items / roster / workflow),
and states the read-only limitation inline rather than leaving it for a user to discover after
install — under-promise here, not over-promise.

## displayName — no change

Keep `"Squads"`. It's the established brand across the activity bar, icon, and views; changing it
is a bigger branding call than this metadata pass and shouldn't ride along with it. If a
keyword-bearing subtitle (e.g. "Squads — AI Agent Work Tracker") is wanted later for search-title
weight, that's a separate, deliberate call — not scoped here.

## Note on MARKETPLACE.md

Read for this decision, not changed by it: its "Currently Read-Only" section already states the
limitation plainly, and its feature list already covers roster/preview/graphs — it doesn't need
the same undersell fix the one-line `description` does. Leave as is.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 683 add-subtask "<title>"`; track with `sq task 683 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-28T13:28:28Z] Theo Writer:
  - Rewrote clients/vscode/MARKETPLACE.md as positioning copy: it now opens by saying what squads is (a CLI coordination layer for a team of AI coding agents, state as committed markdown) and why the extension earns screen space, before any feature list.
  - Structure: lede + plain read-only statement -> Three views in the sidebar (Work Items / Records / Roster — Records was missing entirely before) -> The item dossier -> It updates while you work -> Finding things (adds the palette search, which was undocumented) -> What it doesn't do -> Getting started / Requirements / Troubleshooting kept and tightened. Dropped the 'Polish' heading; auto-refresh is now its own named section instead of a parenthetical.
  - Read-only is stated twice by design: one bold line in the lede (the install decision happens at the top of the page, and the manifest description already says read-only, so the two must agree) and a 'What it doesn't do' section placed before Getting Started rather than after Troubleshooting, so nobody installs first and finds the boundary later. Also states there that the extension does not bundle the CLI and makes no network calls.
  - Copy verified against the shipped client, not the old page: three view ids, spec-driven type categories (review is work, decision/guide are records), spec-driven status colours (not a hardcoded green), search narrowing axes, preview back/forward, clickable graph nodes, bundled mermaid. Closing line replaced — 'Made by the squads team' was circular. Consistent with the description chosen here for the manifest.
  - Flag for @tech-lead: README.md never mentions the VS Code client at all, and calls decision/guide 'work-item types' plus uses 'meta-types' for role/skill/operator — a reader arriving from the Marketplace page's Work/Records/Roster framing will hit that mismatch. Not touched, out of scope for this pass.
<!-- sq:discussion:end -->
