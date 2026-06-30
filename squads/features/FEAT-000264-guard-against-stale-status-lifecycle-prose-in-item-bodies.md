---
id: FEAT-000264
sequence_id: 264
type: feature
title: Guard against stale status/lifecycle prose in item bodies
status: Draft
author: tech-lead
refs:
- FEAT-000237
subentities:
- local_id: US1
  title: The tracker's status is never contradicted by body prose
  status: Todo
created_at: '2026-06-30T12:20:12Z'
updated_at: '2026-06-30T12:21:21Z'
---
<!-- sq:body -->
## What this delivers

A hardening of the invariant **"status/lifecycle state lives in the frontmatter, never in prose"**
across sq-managed bodies — a documented CLAUDE.md convention every spawned agent reads, plus an
enforcement guard that detects status/lifecycle banners in item/ADR/review/doc bodies and fails with
an actionable message. The frontmatter `status:` field (shown by `sq … show` and tracked in the
index) is the single source of truth for where an item sits in its lifecycle; a body must describe
the *substance* (problem, design, decision, acceptance), never restate or pre-declare its own
workflow state.

## The problem (concrete)

Agents keep restating lifecycle state as prose banners in bodies and `description:` summaries, where
it goes stale the moment the real `status:` changes. The frontmatter then disagrees with the body and
the body lies. A live example: **ADR-000264**'s body once opened with a `**STATUS: Proposed /
assessment** … drafting is not a greenlight … TASK-… stays blocked until Accepted` banner. The ADR
is now `Accepted` — the banner is a falsehood the reader has to second-guess. The same class of drift
covers: a hand-written `## Status` section, "this is a draft", "blocked until accepted", "if
accepted, then…", "go / no-go", "pending approval" — anything that encodes the item's *own* position
in its lifecycle in free text instead of reading it from the tracker.

Crucially, this is about **state-as-prose**, not about discussing lifecycle as a *topic*. A feature
body may legitimately describe "the Draft→Ready transition" as the thing it is building; an ADR may
cite another item's status as context ("blocks TASK-257 until that lands"). Those stay. The rule
targets a body declaring *its own* current state.

## Scope (axes to harden)

1. **Document the convention in CLAUDE.md.** Add a crisp project instruction under the working norms:
   *never write status / lifecycle / workflow-state into an item, ADR, review, or doc body or its
   `description:` summary — status is the frontmatter field, shown by `sq … show`.* State explicitly
   that **timestamped discussion comments** recording state-at-a-point-in-time are fine and
   encouraged (the discussion is an append-only record; a dated "moved to Accepted because…" comment
   does not go stale — it is history). The body is the part that must stay state-free. This is the
   "harden the lifecycle in CLAUDE.md" piece.

2. **An enforcement guard.** A detector that flags lifecycle-state prose in bodies and `description:`
   summaries. Two candidate homes, to be decided at design time:
   - a **`sq check` rule** (preferred primary home — `sq check` already lints markers, dangling
     links, invalid status, index drift; a body-prose rule sits naturally beside the others and runs
     against the live tracker); and/or
   - a **CI lint** for the repo's own `squads/` tree, mirroring the FEAT-000237 guard's mechanism.

   **Detection heuristic (precise, false-positive-averse):**
   - Flag a **leading banner**: a body or section that *opens* with `STATUS:` / `**STATUS …**`, or a
     hand-written `## Status` / `### Status` heading. A leading banner is almost always a
     self-declaration and the highest-signal pattern.
   - Flag lifecycle words used as a **first-person state declaration** — `proposed`, `accepted`,
     `draft`, `pending`, `blocked`, `superseded`, `rejected`, plus phrases `go / no-go`,
     `if accepted`, `until accepted`, `not (yet) a greenlight`, `pending approval` — when they assert
     *this* item's state (typically near the top, in a banner/heading, or in a `description:`).
   - **Avoid false positives** by NOT flagging: lifecycle words in mid-body prose that reference
     another item or discuss a transition as a topic; the words appearing inside fenced code / CLI
     examples; the discussion section (comments are exempt by design). Anchor the match to
     banner/heading position and `description:` rather than a bare keyword grep over the whole body,
     and lint only the `sq:body` / `description` regions, never `sq:discussion`.
   - **Rollout: warn-then-error**, like the FEAT-000237 guard — ship as a warning first so the
     existing corpus can be cleaned without a hard build break, then promote to error once the tree
     is clean and a negative test proves the gate fires on a newly-introduced banner.

3. **The project's own CLAUDE.md "Status" section is in scope as a risk to assess.** This repo's
   hand-written CLAUDE.md carries a `## Status` prose section ("All three planned phases are built and
   green…"). That is exactly the stale-prose shape the feature warns against, though it describes the
   *product's* maturity rather than a single item's lifecycle. The design should decide whether to (a)
   leave it (product-level prose, not item-lifecycle), (b) reword it to a durable statement, or (c)
   exempt it explicitly so the guard does not false-positive on it. Likewise confirm no
   managed/generated section (rendered partials) emits lifecycle prose into a body.

## Relationship to FEAT-000237 (verdict: STANDALONE)

FEAT-000237 is a close sibling but a **different axis**, so this is a standalone feature, not a fold:

| | FEAT-000237 | FEAT-000264 (this) |
|---|---|---|
| Target surface | source **code** comments/docstrings under `src/squads/` (someday tests/docs) | sq-managed **markdown bodies** (items/ADRs/reviews/docs) + CLAUDE.md prose |
| What it strips | squad-item references + history/archaeology narration | lifecycle/status **state-as-prose** (banners, self-declarations) |
| Detection | `(FEAT|TASK|ADR|REV|BUG|EPIC)-\d`, `§N`, "previously/now" | leading `STATUS:` banners, `## Status` sections, lifecycle-word state declarations |
| Guard home | grep/ruff gate over `src/` | `sq check` rule and/or CI lint over `squads/` |

FEAT-000237 **explicitly declares CLAUDE.md and item/ADR bodies out of scope** ("Does NOT rewrite
CLAUDE.md, nor the bundled role / skill / playbook PROSE"). The two guards do not overlap and must
not double-touch the same surface: 237 owns `src/` comments, 264 owns tracker bodies + CLAUDE.md. The
design must keep the two detection patterns separated by surface so neither false-positives on the
other's domain. Linked `related`.

## Acceptance criteria

1. CLAUDE.md carries a crisp, agent-readable convention: status/lifecycle/workflow-state never goes
   in an item/ADR/review/doc body or `description:`; status is the frontmatter field; timestamped
   discussion comments recording state-at-a-point-in-time are explicitly permitted.
2. A guard (a `sq check` rule and/or a CI lint) detects lifecycle-state prose in bodies/`description:`
   and reports it with a clear, actionable message naming the offending item and the fix ("move state
   to frontmatter / a dated comment").
3. The detector matches the high-signal patterns (leading `STATUS:` banner, `## Status` section,
   first-person lifecycle-word declaration) and does **not** false-positive on: lifecycle words used
   as a topic, references to another item's status, code-fenced examples, or the discussion section.
4. Rollout is warn-then-error; a negative test proves the gate fires on a newly-introduced banner and
   stays green once the corpus is clean.
5. The existing corpus is cleaned to pass (at minimum the known offenders, e.g. an ADR opening with a
   `STATUS:` banner that contradicts its frontmatter), and the project's own CLAUDE.md `## Status`
   section is resolved (kept / reworded / explicitly exempted) with the choice recorded.
6. Guard scope is disjoint from FEAT-000237's: no shared file is double-touched; the two detection
   patterns do not cross-fire.

## Non-goals

- Not a change to how `status:` itself works, nor to the workflow state machines.
- Does not touch source-code comments/docstrings — that is FEAT-000237's domain.
- Does not forbid discussing lifecycle as a *subject* in a body, nor recording state in dated
  discussion comments (those are the sanctioned channel).

## Sequencing

Drafted for the record (Draft) — not scheduled. Like its sibling FEAT-000237, it is cleanest to
schedule after the EPIC-000206 churn settles, since the de-typing work is still producing new bodies.
Pierre decides if/when to schedule.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 264 add-story "As a <role>, I want … so that …"`; track with `sq feature 264 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | The tracker's status is never contradicted by body prose |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — The tracker's status is never contradicted by body prose

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a maintainer, I want every item's lifecycle position to come solely from its frontmatter `status:` field (shown by `sq … show`), so the body, ADR text, review notes, and `description:` summaries are never contradicted by stale status-as-prose. State-at-a-point-in-time belongs in dated discussion comments (append-only record), not in the body.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T12:21:21Z] Olivia Lead:
  - Drafted at @manager's request — hardens 'status lives in frontmatter, never in prose' (the ADR-264 STATUS-banner-vs-Accepted drift class Pierre flagged). Left Draft, no tasks, no implementation — Pierre decides scheduling.
  - Verdict: STANDALONE, not a fold into FEAT-000237. Different axis — 237 strips squad-item refs + history from src/ code comments and explicitly declares CLAUDE.md / item bodies OUT of scope; this guards lifecycle-state PROSE in sq-managed markdown bodies + CLAUDE.md. Linked related; guard scopes are disjoint (237 owns src/ comments, 264 owns tracker bodies) so they don't cross-fire.
  - Enforcement heuristic: flag high-signal self-declarations — a leading 'STATUS:' banner, a hand-written '## Status' section, and lifecycle words (proposed/accepted/draft/pending/blocked/superseded, 'go/no-go', 'if/until accepted') asserting THIS item's state — anchored to banner/heading position + description:, linting only sq:body/description and never sq:discussion (comments are the sanctioned channel). Home: a sq check rule and/or CI lint, warn-then-error like the 237 guard.
  - Open design call for whoever picks this up: this repo's own CLAUDE.md '## Status' section is the same shape — decide keep / reword / explicitly-exempt. @manager
<!-- sq:discussion:end -->
