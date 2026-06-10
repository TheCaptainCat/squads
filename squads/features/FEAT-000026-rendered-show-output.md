---
id: FEAT-000026
sequence_id: 26
type: feature
title: Rendered show output
status: Draft
parent: EPIC-000038
author: product-owner
priority: low
refs:
- FEAT-000019:depends-on
- BUG-000025:depends-on
description: sq show renders body and discussion as styled markdown on a TTY (headings,
  bullets, code), with --raw opt-out, NO_COLOR respected, and plain output when piped
subentities:
- local_id: US1
  title: As an operator reading the backlog in my terminal, I want show to render
    the markdown, so that sq tree + sq show covers browsing and reading without external
    viewers
  status: Todo
- local_id: US2
  title: As an agent or script consuming show output, I want piped/--raw/NO_COLOR
    output plain and stable, so that rendering never breaks my parsing
  status: Todo
- local_id: US3
  title: As a user with an ID or number in hand, I want a root sq show command that
    displays any item regardless of type, so that I can read anything in one step
    without naming its type
  status: Todo
- local_id: US4
  title: As a reader of a feature, task or review, I want show to include the sub-entity
    summary table and the discussion, so that one command gives me the whole item,
    not just its body
  status: Todo
- local_id: US5
  title: As a reader wanting the whole story, I want --full to render each sub-entity
    and its comments in tidy panes along with the main discussion, so that one command
    reads as the item's dossier
  status: Todo
created_at: '2026-06-10T14:57:23Z'
updated_at: '2026-06-11T08:56:44Z'
---
<!-- sq:body -->
## Problem

`sq <type> <n> show` is the team's reading surface, but it's both **plain and incomplete**: it
prints the metadata panel and the raw body — `##` and `**` verbatim, no color beyond the panel —
and then stops. The sub-entity summary table (user stories, subtasks, findings) and the discussion
never appear at all (verified 2026-06-11): reading a whole item takes `show` plus `stories` plus
opening the file. Operators fall back to external viewers (VSCode preview, glow), which lose the
live sq state and the tree context. Reading is also one step harder than it should be: you must
name the type to show an item, even though the ID (or the globally-unique number) already
identifies it.

## Value

`sq tree` already navigates the hierarchy; a complete, rendered `show` finishes the loop — one
tool to browse *and* read, from a quick brief to the item's full dossier, chosen by two composable
flags. A root `sq show <id|number>` makes the loop frictionless: copy anything from the tree, show
it, no type required. The renderer is already in the dependency tree (rich powers the panels), so
this is wiring, not a new stack.

## Scope

- **Two composable axes** (decided with op-pierre, 2026-06-11): **`--full` widens the scope**
  (item alone → item + its sub-entities); **`--comments` adds the discussion facet to whatever is
  in scope**. The matrix:

  | flags | output |
  |---|---|
  | *(none)* | panel + rendered body + compact sub-entity summary table |
  | `--comments` | … + the item's discussion (main comments only — subs aren't in scope) |
  | `--full` | … + one pane per sub-entity (badge line + rendered body, no comments) |
  | `--full --comments` | … + sub-entity panes each embedding their own comments, then the main discussion |

- **Pretty panes**: comments and sub-entities render as rich Panels — a comment pane titled with
  author + timestamp, a sub-entity pane titled with its local id + title + badges; rendered
  markdown inside. Easy to read at a glance, never a wall of text.
- `--raw` to opt out (exact file text, today's behaviour); **auto-plain when piped** and full
  respect for `NO_COLOR` — panes degrade to plain delimited text; `--json` always carries the
  complete item (sub-entities, discussions) regardless of flags — flags are presentation-only,
  the machine surface stays FEAT-000015's domain.
- A root **`sq show <id|number>`** displaying any work item regardless of type — same output and
  flags as `sq <type> <n> show`, resolution per FEAT-000019's shared resolver (bare numbers are
  unambiguous thanks to the global counter, and with no type named there is no mismatch to
  police).
- Sensible width handling (don't hard-wrap inside code blocks).
- Out of scope: themes/configurable palettes — rich's defaults first; a `.squads.toml` knob only
  if someone actually asks.

## Acceptance

- The four-cell matrix above behaves exactly as specified; the axes stay composable if scope ever
  grows further (the rule is "comments follow scope", not a hard-coded flag pairing).
- On a TTY it's styled markdown and panels; piped/`--raw`/`NO_COLOR` output is plain and
  byte-stable.
- `sq show FEAT-000013` and `sq show 13` work for every work-item type; unknown ids error cleanly.
- `--json` includes the full item (sub-entities, discussions) independent of flags, and is stable.
- BUG-000025's redundant `Body` label is gone (folded in or fixed first — linked).
- Existing CLI tests pass unmodified except those asserting raw body output, which switch to
  `--raw` or piped mode.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 26 add-story "As a <role>, I want … so that …"`; track with `sq feature 26 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As an operator reading the backlog in my terminal, I want show to render the markdown, so that sq tree + sq show covers browsing and reading without external viewers |
| US2 | Todo |  | As an agent or script consuming show output, I want piped/--raw/NO_COLOR output plain and stable, so that rendering never breaks my parsing |
| US3 | Todo |  | As a user with an ID or number in hand, I want a root sq show command that displays any item regardless of type, so that I can read anything in one step without naming its type |
| US4 | Todo |  | As a reader of a feature, task or review, I want show to include the sub-entity summary table and the discussion, so that one command gives me the whole item, not just its body |
| US5 | Todo |  | As a reader wanting the whole story, I want --full to render each sub-entity and its comments in tidy panes along with the main discussion, so that one command reads as the item's dossier |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator reading the backlog in my terminal, I want show to render the markdown, so that sq tree + sq show covers browsing and reading without external viewers

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** headings, bold, bullets and code blocks display styled on a TTY for body, sub-entity prose and discussion; no redundant viewer-injected labels.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an agent or script consuming show output, I want piped/--raw/NO_COLOR output plain and stable, so that rendering never breaks my parsing

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** when piped, with --raw, or with NO_COLOR set, output is unstyled and byte-stable; --json byte-identical to pre-change.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a user with an ID or number in hand, I want a root sq show command that displays any item regardless of type, so that I can read anything in one step without naming its type

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** `sq show FEAT-000013` and `sq show 13` both work for every work-item type, with the same rendered output as `sq <type> <n> show`; unknown id/number errors cleanly. Resolution follows FEAT-000019's shared-resolver rules (bare numbers are unambiguous via the global counter; no type to mismatch since none is named).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As a reader of a feature, task or review, I want show to include the sub-entity summary table and the discussion, so that one command gives me the whole item, not just its body

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
**Acceptance:** default `show` = panel + rendered body + compact summary table; `--comments` alone adds the item's main discussion only (one pretty pane per comment, author + timestamp as title) — sub-entity comments stay out because subs aren't in scope. Today show stops at the body (verified 2026-06-11).
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As a reader wanting the whole story, I want --full to render each sub-entity and its comments in tidy panes along with the main discussion, so that one command reads as the item's dossier

<!-- sq:story:US5:head -->
**Status:** ⚪ Todo
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
**Acceptance:** `--full` alone adds one pane per sub-entity (local id + title + badges as pane title, rendered body, no comments); `--full --comments` embeds each sub-entity's comments in its pane and closes with the main discussion. Rule: comments follow scope. Panes degrade to plain text when piped/NO_COLOR; --json unaffected by flags.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T07:34:02Z] Pierre Chat:
  - show must display the sub-entity summary table (stories/subtasks/findings) and not stop at the body — requested while reviewing the backlog.
- [2026-06-11T08:51:17Z] Pierre Chat:
  - Spec refinement: tiered show — default stays lean (panel + body + summary table); --comments adds the discussion in per-comment panes; --full is the dossier (each sub-entity pane with its own comments, plus main discussion). Panes must be pretty and easy to read.
- [2026-06-11T08:54:53Z] Pierre Chat:
  - Correction: --full does NOT imply --comments. The flags are orthogonal — --full adds only the sub-entity prose panes; --comments adds all comments (main + sub-entity, wherever they belong); combined they make the dossier.
- [2026-06-11T08:56:44Z] Pierre Chat:
  - Final flag semantics: --full widens scope (item → item + sub-entities); --comments adds the discussion facet to whatever is in scope. Hence: --comments = main comments only; --full = sub prose only; together = subs with their comments + main comments. Comments follow scope.
<!-- sq:discussion:end -->
