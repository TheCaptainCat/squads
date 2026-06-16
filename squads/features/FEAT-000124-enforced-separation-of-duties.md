---
id: FEAT-000124
sequence_id: 124
type: feature
title: Enforced separation of duties
status: Draft
parent: EPIC-000121
author: product-owner
priority: low
refs:
- FEAT-000125:depends-on
- REV-000118
- REV-000119
- BUG-000120
subentities:
- local_id: US1
  title: sq check flags self-review by same spawn lineage
  status: Todo
- local_id: US2
  title: Suppressible self-review guard for solo workflows
  status: Todo
created_at: '2026-06-15T11:56:15Z'
updated_at: '2026-06-16T09:52:43Z'
---
<!-- sq:body -->
## Problem

On 2026-06-15, REV-000118 was filed with `author: reviewer` — indistinguishable in `sq` from a
review by an independently-spawned agent. In reality it was filed by the same architect lineage
that had designed and implemented the work it was reviewing. The self-review approved its own code,
and the real defect (BUG-000120, retype not logged) slipped through. Only an independent
re-verification (REV-000119) caught it (see EPIC-000121).

Today squads has no concept of **lineage separation**. Nothing in the item model, the review
lifecycle, or the index tracks which agent spawned which. A review item carries an `author` slug —
self-declared — and `sq check` verifies structural rules (subtask→story, task→feature) but has no
rule that "the review author must not be in the same spawn tree as the implementation author."

## Value

If squads can detect and/or prevent self-review, then:

- the review lifecycle becomes a meaningful quality gate, not a formality a lineage can satisfy
  for itself,
- `sq check` can flag a review whose author is in the same spawn lineage as the item author,
- a manager running the orchestration loop has a verifiable guarantee that reviews are independent,
- the incident on 2026-06-15 becomes structurally impossible.

## Scope (exploratory — not a design commitment)

- A **lineage field** on the review item (and on the reflog entry): which spawn chain produced
  this agent session? This is the FEAT-000125 dependency — without trustworthy identity, lineage
  is just another self-declared field.
- A **`sq check` rule**: a review's lineage must differ from the target item's author lineage.
  Violation is a warning (not a hard block) in the first iteration; can be promoted to a block
  with a flag.
- A **filing guard**: `sq create review --of FEAT-<n>` checks whether the creating agent is in
  the same lineage as the feature's author and emits a warning/error.
- Tie-in: REV-000118 is the motivating incident artifact; REV-000119 is the independent
  re-verification that caught what REV-000118 missed; BUG-000120 is the defect.

## Acceptance (draft — subject to triage)

- A review item carries a lineage identifier in addition to its `author` slug.
- `sq check` flags a review whose lineage matches the target item's author lineage, with a
  machine-readable violation code in `--json` output.
- `sq create review --of <id>` emits a clear warning (or error with `--strict`) when the creating
  agent's lineage matches the target's author lineage.
- The guard is suppressible with `--force` and an explicit rationale comment (e.g. solo operator
  flow where independence is impossible), so it does not block legitimate single-operator use.

## Open questions

- What defines "same lineage"? Same top-level spawn parent? Same session? The right boundary is
  not obvious — especially for long chains (manager → tech-lead → architect → reviewer).
- Can squads detect lineage at all without FEAT-000125? If not, this feature has a hard dependency
  and cannot be designed in isolation.
- Is a warning sufficient, or does the use case require a hard block? A hard block on self-review
  could prevent legitimate single-operator workflows where only one agent is available.
- Should the rule apply to review creation, review approval, or both?
- How does this interact with the manager role, which may legitimately file a review as a
  coordination step even if it is "in the lineage"?
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 124 add-story "As a <role>, I want … so that …"`; track with `sq feature 124 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | sq check flags self-review by same spawn lineage |
| US2 | Todo |  | Suppressible self-review guard for solo workflows |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — sq check flags self-review by same spawn lineage

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a squad manager, I want `sq check` to flag any review whose author lineage matches the target item's author lineage, so that I can detect self-review before the review closes.

**Acceptance:** a review item carries a lineage identifier alongside its `author` slug; `sq check` emits a warning (or error with `--strict`) when the review's lineage matches the target item's author lineage; the violation is machine-readable via a structured code in `--json` output; `sq create review --of <id>` emits the same warning at filing time.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Suppressible self-review guard for solo workflows

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a solo operator running a single-agent workflow, I want to suppress the self-review guard with `--force` and a rationale comment, so that the check does not block legitimate single-agent use.

**Acceptance:** `sq create review --of <id> --force -m "<rationale>"` bypasses the lineage check and records the rationale in the review's discussion; the override is visible in the reflog; `sq check` does not re-raise the violation for a forced review.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
