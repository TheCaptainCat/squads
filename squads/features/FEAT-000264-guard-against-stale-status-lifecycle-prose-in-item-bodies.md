---
id: FEAT-264
sequence_id: 264
type: feature
title: Guard against stale status/lifecycle prose in item bodies
status: Done
author: tech-lead
refs:
- FEAT-237
subentities:
- local_id: US1
  title: The tracker's status is never contradicted by body prose
  status: Todo
created_at: '2026-06-30T12:20:12Z'
updated_at: '2026-07-06T12:50:04Z'
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
   - a **CI lint** for the repo's own `squads/` tree, mirroring the FEAT-237 guard's mechanism.

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
   - **Rollout: warn-then-error**, like the FEAT-237 guard — ship as a warning first so the
     existing corpus can be cleaned without a hard build break, then promote to error once the tree
     is clean and a negative test proves the gate fires on a newly-introduced banner.

3. **The project's own CLAUDE.md "Status" section is in scope as a risk to assess.** This repo's
   hand-written CLAUDE.md carries a `## Status` prose section ("All three planned phases are built and
   green…"). That is exactly the stale-prose shape the feature warns against, though it describes the
   *product's* maturity rather than a single item's lifecycle. The design should decide whether to (a)
   leave it (product-level prose, not item-lifecycle), (b) reword it to a durable statement, or (c)
   exempt it explicitly so the guard does not false-positive on it. Likewise confirm no
   managed/generated section (rendered partials) emits lifecycle prose into a body.

## Relationship to FEAT-237 (verdict: STANDALONE)

FEAT-237 is a close sibling but a **different axis**, so this is a standalone feature, not a fold:

| | FEAT-237 | FEAT-264 (this) |
|---|---|---|
| Target surface | source **code** comments/docstrings under `src/squads/` (someday tests/docs) | sq-managed **markdown bodies** (items/ADRs/reviews/docs) + CLAUDE.md prose |
| What it strips | squad-item references + history/archaeology narration | lifecycle/status **state-as-prose** (banners, self-declarations) |
| Detection | `(FEAT|TASK|ADR|REV|BUG|EPIC)-\d`, `§N`, "previously/now" | leading `STATUS:` banners, `## Status` sections, lifecycle-word state declarations |
| Guard home | grep/ruff gate over `src/` | `sq check` rule and/or CI lint over `squads/` |

FEAT-237 **explicitly declares CLAUDE.md and item/ADR bodies out of scope** ("Does NOT rewrite
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
6. Guard scope is disjoint from FEAT-237's: no shared file is double-touched; the two detection
   patterns do not cross-fire.

## Non-goals

- Not a change to how `status:` itself works, nor to the workflow state machines.
- Does not touch source-code comments/docstrings — that is FEAT-237's domain.
- Does not forbid discussing lifecycle as a *subject* in a body, nor recording state in dated
  discussion comments (those are the sanctioned channel).

## Sequencing

Drafted for the record (Draft) — not scheduled. Like its sibling FEAT-237, it is cleanest to
schedule after the EPIC-206 churn settles, since the de-typing work is still producing new bodies.
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
  - Verdict: STANDALONE, not a fold into FEAT-237. Different axis — 237 strips squad-item refs + history from src/ code comments and explicitly declares CLAUDE.md / item bodies OUT of scope; this guards lifecycle-state PROSE in sq-managed markdown bodies + CLAUDE.md. Linked related; guard scopes are disjoint (237 owns src/ comments, 264 owns tracker bodies) so they don't cross-fire.
  - Enforcement heuristic: flag high-signal self-declarations — a leading 'STATUS:' banner, a hand-written '## Status' section, and lifecycle words (proposed/accepted/draft/pending/blocked/superseded, 'go/no-go', 'if/until accepted') asserting THIS item's state — anchored to banner/heading position + description:, linting only sq:body/description and never sq:discussion (comments are the sanctioned channel). Home: a sq check rule and/or CI lint, warn-then-error like the 237 guard.
  - Open design call for whoever picks this up: this repo's own CLAUDE.md '## Status' section is the same shape — decide keep / reword / explicitly-exempt. @manager
- [2026-06-30T13:20:56Z] Catherine Manager:
  - Live corpus offender found 2026-06-30 (stronger than the ADR-264 example already in the body): TASK-257's body carried a standing '### The startup-ordering problem — THIS TASK IS BLOCKED ON THE ADR' banner plus 'Dependencies: BLOCKED ON: the startup-ordering ADR'. ADR-263 was accepted afterward and nobody cleared the banner — so the body asserted a blocker that no longer existed. This actively misled a manager triage into reporting the ADR didn't exist and the critical path was blocked. Exactly this feature's thesis: a stale 'status:' field is caught by the tracker, but stale lifecycle PROSE in a body has nothing watching it. Detection-wise it's the high-signal case the heuristic targets — a leading 'BLOCKED ON …' self-declaration in a body/heading, distinct from citing another item's status as context. (Banner since cleared on TASK-257 and moved to a dated comment.)
- [2026-07-06T12:15:31Z] Olivia Lead:
  - Broke this down into 3 tasks (all Draft), subtasks mapped to US1.
  - TASK-305 — Document the 'no status/lifecycle prose in bodies' convention in CLAUDE.md (Axis 1). ST1 write the convention paragraph (bans body + description: state-as-prose, explicitly permits dated discussion comments as the sanctioned append-only channel, distinguishes state-declaration from lifecycle-as-topic); ST2 resolve the repo's own CLAUDE.md ## Status section (editorial only — the sq check rule never scans CLAUDE.md; keep vs reword, recommend reword, record the choice). No source touched.
  - TASK-306 — Add the sq check rule flagging leading status/lifecycle banners in bodies (Axis 2, the code). New _check_* helper in _services/_maintenance.py mirroring FEAT-289's _check_unwritten_subentity_bodies: reads the :body marker region + item.description, flags ONLY a leading STATUS:/**STATUS…** banner or a hand-written ##/### Status heading, warn severity, lints sq:body+description and never sq:discussion, false-positive-averse (no topical mentions, cross-refs, code-fences). ST1 helper+wiring, ST2 positive+negative tests, ST3 reconcile fixtures/goldens WITHOUT weakening the detector. related→FEAT-237 (disjoint surface, no cross-fire). warn-then-error promotion to a blocking error is a deferred fast-follow, out of scope.
  - TASK-307 — Sweep the dogfood tree of existing status/lifecycle body banners (corpus cleanup). depends-on TASK-306 (the detector defines the worklist). ST1 enumerate + clean flagged bodies (move durable state to dated comments, edit only via sq), ST2 verify markers/frontmatter intact. Known offenders: the once-'STATUS: Proposed' ADR now Accepted, and any leading 'BLOCKED ON …'/## Status self-declarations.
  - Build order: WAVE 1 (parallel) TASK-305 (docs) + TASK-306 (guard); WAVE 2 TASK-307 (sweep) after 306 is green. TASK-305 and TASK-306 are independent.
  - Scope call on cleaning existing violations: IN-SCOPE (AC5 requires the corpus pass), delivered as the bounded TASK-307 sweep scheduled after the guard lands so the detector — not eyeballing — sets the worklist. TASK-306 owns test-fixture/golden reconciliation (may break like FEAT-289) and must NOT weaken the detector to pass; TASK-307 owns the live-tree data cleanup. Shipped source in TASK-306 carries no sq IDs; task/subtask bodies may.
- [2026-07-06T12:50:04Z] Catherine Manager:
  - FEAT-264 complete. TASK-305: CLAUDE.md convention added (no status/lifecycle self-declaration in bodies or description: summaries; timestamped discussion comments are the sanctioned place for state-at-a-point-in-time), and the repo's own '## Status' section reworded to '## Build scope'. TASK-306: new advisory sq check rule _check_status_banners — flags only a LEADING banner (body/section opening with STATUS:/**STATUS**/## Status heading) or a description opening with one, skips sq:discussion, warn severity; shipped with positive AND negative tests (topical lifecycle mentions, cross-refs, fenced-code examples, and discussion comments all correctly NOT flagged). TASK-307: swept the four ADRs the detector flagged (ADR-129/155/158/163) — deleted the leading status banners (not reworded). Manager note: the sweep also removed ADR-158's 'Revised (Pierre's correction)' meta-blockquote; its substance survives in the restructured body (the 'squads is never in the spawn path' section), but flagging for the operator's awareness. Verified: sq check banner-clean, full suite green, gates clean, no sq IDs in source.
<!-- sq:discussion:end -->
