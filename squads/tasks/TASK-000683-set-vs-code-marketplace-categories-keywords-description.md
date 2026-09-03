---
id: TASK-683
sequence_id: 683
type: task
title: Set VS Code Marketplace categories, keywords & description
status: Done
author: product-owner
created_at: '2026-07-28T12:43:01Z'
updated_at: '2026-07-29T08:26:11Z'
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
- [2026-07-28T13:40:29Z] Theo Writer:
  - Fixed the README's stale/false claims (README.md only; the Marketplace page is untouched).
  - The four flagged: (1) dropped the 'from PyPI, once published' hedge so the install command reads as the real instruction, and added the tui-extra line for sq ui; (2) 'Reserved meta-types' -> the roster category, with role/skill/operator named as the three reserved types; (3) new 'Browsing the squad' section covering both read-only clients — sq ui and the VS Code extension — placed right after Quickstart; (4) resolved the category conflict in the spec's favour: sq workflow types --json reports epic/feature/task/bug/review as category=work and decision/guide as category=records, so Concepts now describes ten bundled types across work / records / roster instead of 'seven work-item types'.
  - Six more stale claims found in the same file. Two were actively harmful: the bug lifecycle row was wrong (bundled machine is Open -> InProgress -> Fixed -> Verified (+ WontFix, Blocked, Cancelled), not the epic/feature/task Draft->Done chain), and two passages told readers that agents 'write the body directly' in the .md file — the opposite of the current rule that bodies go in through sq body and files are never hand-edited. Also: 'default_backend' in .squads.toml is legacy (the key is active_backends, a list, and --backend is repeatable); the roster lifecycle row omitted operator; 'sq story add' and 'sq skill list' / 'sq guide list' are not commands (the real grammar is address-first, sq feature <n> add-story / sq role <slug> show); and the OP prefix was missing from the built-in prefix list.
  - Also brought the reference in line with the shipped CLI where it was merely silent: sq show / graph / ui / docs / memory / board / override / migrate / renumber / reflog, the retype and remove verbs, show --full/--comments, the type-command aliases, and the extra list/search filters. Layout block and docs index updated too (operators/, board/, agents/memory, overrides.md, migration.md). Every claim was checked against --help output or the bundled workflow spec, not against the old text.
  - @op-pierre one claim I could not verify locally: 'Install it from the VS Code Marketplace (search Squads)'. The publish step is gated on a secret, so if the listing is not live yet, say so and I will invert that sentence to lead with the .vsix attached to each release.
- [2026-07-28T14:14:03Z] Theo Writer:
  - Second pass on clients/vscode/MARKETPLACE.md: the page now introduces squads as a product before it introduces the extension. Added 'The problem it solves' (agents lose context between sessions and between each other; state moves out of the chat and into the repo), 'The model' (named roles + skills, typed items with one global counter, per-type lifecycles, epic/feature/task breakdown with stories mapped to subtasks, handoff by comment + @mention + inbox, records, human operators on the roster), a worked 'What using it looks like' example, and a short backend-pluggability section (claude_code + agents_md behind one interface). A rule and one line — 'That's squads. The rest of this page is the extension.' — marks the hand-off; the extension sections follow unchanged in substance.
  - The example is one piece of work from proposal to closed: feature + story, task + subtask mapped to the story, developer moves it InProgress and hands off with an @mention, reviewer picks it up from their inbox and files a finding, finding closed, review approved, task Done. Every command was executed in a throwaway squad outside the repo, not just checked against --help. One line changed as a result: a review cannot go Requested to Approved directly, so the sequence goes through InReview — kept in the example with an inline comment, since it demonstrates that transitions are validated rather than free text. The ID numbers (FEAT-20, TASK-21, REV-22) are the ones a real 'sq init --roles all' actually produces, because the roster and skills consume the counter first.
  - Cuts that paid for it: the 'Display Controls' bullets collapsed into one 'View controls' line; the dossier's separate 'Navigation' bullet folded into the discussion bullet; the numbered sq-discovery list became a single prose sentence; troubleshooting's three numbered procedures became three short paragraphs. Two additions replaced weaker material: the CLI install step now gives the real command (uv tool install squads) instead of sending readers to the repo, and 'Type icons' moved into Finding things. Read-only stays where it was — bold in the lede, plus 'What it doesn't do' before Getting started.
  - @op-pierre length tension, flagged rather than decided: the page is 216 lines, at the top of what a skimmed listing carries. If it needs to come down, the ~35 lines I would drop are Troubleshooting and the sq-discovery order — reference material a reader deciding whether to care never reads, and both live in the repository docs. I would not cut the model or the example to get there: those are what the pass was for.
- [2026-07-28T14:43:00Z] Theo Writer:
  - Trimmed the Marketplace listing to 206 lines (was 216). Removed the discovery-order prose from Getting started, the non-local-filesystem refresh caveat, and the sq repair note, keeping the override settings block and the sq-not-found guidance.
  - Two things needed reshaping rather than deleting. (1) Dropping the discovery prose left the sq-not-found paragraph and the settings block saying the same thing in two places separated only by Requirements, so they are now one step — 'If the views can't find sq' as Getting started §4, carrying the sq --version check, the settings JSON, and the window reload. The scannable phrase survives as a heading, and it now sits in the install flow where a first-run reader already is instead of after Requirements.
  - (2) The refresh caveat was the honesty hedge on the auto-refresh claim, so rather than lose it I folded it into one clause of 'It updates while you work': a workspace not backed by a local filesystem falls back to each view's refresh button. The claim stays qualified at the cost of half a line instead of a four-line troubleshooting entry.
  - The model section and the worked example are untouched.
<!-- sq:discussion:end -->
