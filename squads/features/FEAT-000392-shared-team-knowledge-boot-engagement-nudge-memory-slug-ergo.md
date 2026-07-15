---
id: FEAT-392
sequence_id: 392
type: feature
title: Shared team knowledge — boot engagement nudge + memory slug ergonomics
status: Done
parent: EPIC-316
author: product-owner
subentities:
- local_id: US1
  title: 'Boot directive: review memory + board before starting'
  status: Todo
- local_id: US2
  title: Short, human-friendly memory slugs
  status: Todo
created_at: '2026-07-15T11:43:20Z'
updated_at: '2026-07-15T12:02:56Z'
---
<!-- sq:body -->
Two small refinements to the shared-team-knowledge surfaces shipped in FEAT-315
(agent memory) and FEAT-317 (bulletin board), both requested by op-pierre after
a live demo of the two features:

1. Boot context passively surfaces an agent's memory index and the board, but
   nothing in the always-seen boot definition tells a spawning agent to
   actually look at them and act — the only such nudge lives in the
   `sq-memory` skill, which is skill-gated and may not get read on every
   spawn.
2. `sq memory <role> add "<fact>"` slugifies the entire fact text, producing
   slugs long enough to be awkward to type back into `show <slug>` (e.g.
   `except-a-b-without-parens-is-valid-python-3-14-pep-758-it-is`).

Neither changes the storage model (ADR-314) or the board mechanics
(FEAT-317) — this is boot-prompt wording plus a slug-derivation tweak on
`add`.

## User Stories

See below.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 392 add-story "As a <role>, I want … so that …"`; track with `sq feature 392 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Boot directive: review memory + board before starting |
| US2 | Todo |  | Short, human-friendly memory slugs |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Boot directive: review memory + board before starting

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a spawning agent, I want an always-seen boot directive to review my memory
and the team board so that I apply anything relevant before I start work.

Today the per-role memory index (`## Your memory`) and the team board
(`## Board`) are *passively surfaced* into an agent's boot context, but the
only instruction to actually engage with them — read, then apply — lives in
the `sq-memory` skill. Skills are on-demand: an agent may not load it on every
spawn, so the nudge can be missed entirely on a given run.

This story adds an **always-seen directive** to the role boot definition
(`role.md.j2`, which every role's generated boot content renders from and
which already carries both the memory index and the board) telling a
spawning agent, in substance: before you start, skim `## Your memory` and
`## Board` and apply anything relevant.

## Acceptance criteria

- The generated role boot content (role pointer / role body) contains an
  explicit "before you start, review your memory + the board and apply
  what's relevant" directive, for every role.
- The directive is part of the always-seen boot definition, not only the
  on-demand `sq-memory` skill.
- It renders cleanly whether or not the pool/board is empty — either the
  directive stands unconditionally even over empty sections, or it's phrased
  to no-op gracefully when there's nothing there. Implementer's call.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Short, human-friendly memory slugs

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a role authoring a memory entry, I want a short, human-friendly slug so
that I can type it back into `show <slug>` / `prune <slug>` without wrestling
a full-sentence handle.

Today `sq memory <role> add "<fact>"` derives the slug from the *entire*
fact, giving unwieldy slugs like
`except-a-b-without-parens-is-valid-python-3-14-pep-758-it-is`. The full fact
text already lives in the entry's summary/description and body — the slug
only needs to be a short handle for addressing the entry, not a restatement
of its content.

## Acceptance criteria

- `add` derives a **short** slug (e.g. first few words / capped length,
  truncated at a word boundary — not mid-word), not the whole fact.
- An optional explicit override, e.g. `--slug <handle>`, lets the author name
  the slug directly instead of deriving it.
- Existing long-slug memories continue to resolve unchanged (no breakage to
  already-committed entries).
- Collision disambiguation (`-2`, `-3`, ...) still applies to the new
  short-slug derivation.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
