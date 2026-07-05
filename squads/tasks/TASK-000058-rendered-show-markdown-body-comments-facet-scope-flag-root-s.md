---
id: TASK-58
sequence_id: 58
type: task
title: 'Rendered show: markdown body, comments facet, scope flag, root sq show'
status: Done
parent: FEAT-26
author: tech-lead
assignee: python-dev
priority: high
subentities:
- local_id: ST1
  title: Render body as styled markdown on a TTY
  status: Done
  story: US1
- local_id: ST2
  title: Plain/byte-stable output when piped, --raw, or NO_COLOR; --json unchanged
  status: Done
  story: US2
- local_id: ST3
  title: Root sq show <id|number> for any work-item type
  status: Done
  story: US3
- local_id: ST4
  title: Default summary table + --comments main discussion panes
  status: Done
  story: US4
created_at: '2026-06-12T08:58:26Z'
updated_at: '2026-06-12T09:15:16Z'
---
<!-- sq:body -->
## Goal

Build the rendering core for `show`: styled markdown on a TTY, the **two composable axes**, and the root `sq show`. Implements US1, US2, US3, US4. Default scope only here (no sub-entity panes — that is TASK-59).

## Decided flag semantics (from FEAT-26 discussion, 2026-06-11)

Orthogonal axes — `--full` widens SCOPE, `--comments` adds the DISCUSSION facet to whatever is in scope. Comments follow scope.

| flags | output |
|---|---|
| none | panel + rendered body + compact sub-entity summary table |
| --comments | + the item's main discussion only (subs not in scope) |

The `--full` cells are TASK-59's job; design the render path so it slots the sub-entity panes in cleanly.

## In scope

- Render the item body as styled markdown on a TTY using rich's Markdown (rich already in the dep tree). Headings, bold, bullets, fenced code; sensible width, do not hard-wrap inside code blocks.
- Render the sub-entity summary table in the default output (today show stops at the body — verified 2026-06-11). Drive it from the item's subentities; reuse the roll-up data, not a re-parse of the markdown table.
- `--comments` facet: render the main discussion as one rich Panel per comment, titled author + timestamp, rendered-markdown inside. Add a helper that splits the main discussion region into individual comments (the region is a flat list of `- [ts] author:` bullets — see _discussion.format_comment for the exact shape; parse the inverse). Put the parser in _discussion.py next to format_comment.
- `--raw` opts out: exact file text, today's behaviour (panel + plain body). 
- Degradation: auto-plain when piped (stdout not a TTY) and when NO_COLOR is set — panes become plain delimited text, byte-stable. rich Console already detects TTY; make the panel/markdown path collapse to plain delimited text in that case so output is parseable and stable.
- `--json` is unchanged by any flag — it already dumps the full model; keep it presentation-independent (the machine surface is FEAT-15's domain).
- Root `sq show <id|number>`: a top-level command in _cli/_main.py that resolves any work-item type via resolve_item_id_any (FEAT-19's shared resolver) and renders with the same output + flags as the per-type show. Unknown id/number errors cleanly. Bare numbers are unambiguous via the global counter.
- Wire the same flags (--full, --comments, --raw, --json) onto the per-type `sq <type> <n> show` in _cli/_items.py _cmd_show.

## Anchors

- src/squads/_cli/_common.py :: print_item (current panel + body render), e() escaping helper — every dynamic string into rich must go through e().
- src/squads/_cli/_items.py :: _cmd_show / show (line ~84) — per-type wiring.
- src/squads/_cli/_main.py — add the root `sq show` command (model it on tree/blocked/inbox @app.command()).
- src/squads/_discussion.py :: format_comment — the comment line format to parse back; add the splitter here.
- src/squads/_sections.py :: get_section + squads._models._markers.DISCUSSION — read the main discussion region.
- src/squads/_services/_items.py :: read_body — body text source.
- rich.console.Console (is terminal detection), rich.markdown.Markdown, rich.panel.Panel.

## Out of scope

- Sub-entity panes and the dossier (--full cells): TASK-59.
- Skills/onboarding guidance: TASK-60.
- BUG-25 (redundant Body label) is already Done — no action.

## Tests

Service + CLI smoke per CLAUDE.md. Cover: default (panel+body+summary), --comments panes, --raw byte-stable, piped/NO_COLOR plain, --json byte-identical to pre-change, root `sq show` for several types + unknown id error. Existing tests asserting raw body switch to --raw or piped mode.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 58 add-subtask "<title>"`; track with `sq task 58 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Render body as styled markdown on a TTY | US1 |
| ST2 | Done |  | Plain/byte-stable output when piped, --raw, or NO_COLOR; --json unchanged | US2 |
| ST3 | Done |  | Root sq show <id|number> for any work-item type | US3 |
| ST4 | Done |  | Default summary table + --comments main discussion panes | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Render body as styled markdown on a TTY

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As an operator reading the backlog in my terminal, I want show to render the markdown, so that sq tree + sq show covers browsing and reading without external viewers
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Plain/byte-stable output when piped, --raw, or NO_COLOR; --json unchanged

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As an agent or script consuming show output, I want piped/--raw/NO_COLOR output plain and stable, so that rendering never breaks my parsing
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Root sq show <id|number> for any work-item type

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a user with an ID or number in hand, I want a root sq show command that displays any item regardless of type, so that I can read anything in one step without naming its type
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Default summary table + --comments main discussion panes

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US4 — As a reader of a feature, task or review, I want show to include the sub-entity summary table and the discussion, so that one command gives me the whole item, not just its body
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
