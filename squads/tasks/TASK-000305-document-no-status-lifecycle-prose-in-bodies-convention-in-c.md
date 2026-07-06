---
id: TASK-305
sequence_id: 305
type: task
title: Document 'no status/lifecycle prose in bodies' convention in CLAUDE.md
status: Done
parent: FEAT-264
author: tech-lead
assignee: python-dev
subentities:
- local_id: ST1
  title: Write the convention paragraph in CLAUDE.md
  status: Done
  story: US1
- local_id: ST2
  title: 'Resolve the repo CLAUDE.md ## Status section + record decision'
  status: Done
  story: US1
created_at: '2026-07-06T12:13:32Z'
updated_at: '2026-07-06T12:31:43Z'
---
<!-- sq:body -->
**Axis 1 — the working-norm convention.** Add a crisp, agent-readable instruction to CLAUDE.md: never write status / lifecycle / workflow-state into an item, ADR, review, or doc **body** or its `description:` summary — status is the frontmatter field, shown by `sq … show`. The body describes the *substance* (problem, design, decision, acceptance); it must never restate or pre-declare its own workflow position.

Explicitly permit the sanctioned channel: **timestamped discussion comments** recording state-at-a-point-in-time are fine and encouraged — the discussion is an append-only record, so a dated 'moved to Accepted because…' comment does not go stale. The distinction to spell out: recording state in a dated comment = good; a standing state banner in the body = banned. Also distinguish state-**as-prose** (banned) from discussing lifecycle **as a topic** (allowed — e.g. a feature body describing 'the Draft→Ready transition' it is building, or citing another item's status as context).

**Done when:** CLAUDE.md carries the convention in the working-norms area (Conventions/gotchas or Working with squads); it names both surfaces (body + `description:`), permits dated comments explicitly, and draws the topic-vs-state-declaration line. Wording is terse and durable.

**Also resolve the repo's own CLAUDE.md `## Status` section** (the 'All three planned phases are built and green…' prose — the same stale shape this feature warns against, though it describes *product* maturity not one item's lifecycle). Note that the sq check guard (TASK-306) scans **index items only** and never scans the repo-root CLAUDE.md, so no code exemption is needed — the decision is purely editorial: keep as product-maturity prose vs reword to a durable, state-free statement. Recommendation: reword. Record the choice + rationale in a comment on this task.

Note: this task edits CLAUDE.md prose only — no shipped source file is touched, and the convention text is generic (no sq/item IDs).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 305 add-subtask "<title>"`; track with `sq task 305 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Write the convention paragraph in CLAUDE.md | US1 |
| ST2 | Done |  | Resolve the repo CLAUDE.md ## Status section + record decision | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Write the convention paragraph in CLAUDE.md

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — The tracker's status is never contradicted by body prose
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add the working-norm instruction to CLAUDE.md: status/lifecycle/workflow-state never goes in an item/ADR/review/doc body or its `description:` summary — status is the frontmatter field (shown by `sq … show`). State explicitly that timestamped discussion comments recording state-at-a-point-in-time are permitted/encouraged (append-only history, never stale), and that the ban targets a body declaring its OWN state, not discussing lifecycle as a topic or citing another item's status. Done when the paragraph is present, terse, and unambiguous on both surfaces (body + description).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-07-06T12:31:29Z] Operator:
  - Done: added the 'No status/lifecycle prose in bodies' bullet to CLAUDE.md's Conventions/gotchas section. Names both surfaces (body + description:), explicitly permits dated discussion comments, and draws the topic-vs-declaration line.
- [2026-07-06T12:31:42Z] Elias Python:
  - (re-attributing) Done: added the 'No status/lifecycle prose in bodies' bullet to CLAUDE.md's Conventions/gotchas section. Names both surfaces (body + description:), explicitly permits dated discussion comments, and draws the topic-vs-declaration line.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Resolve the repo CLAUDE.md ## Status section + record decision

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — The tracker's status is never contradicted by body prose
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Decide the fate of the repo's own CLAUDE.md `## Status` section (product-maturity prose, same stale shape). The sq check guard never scans CLAUDE.md, so this is editorial only: keep vs reword to a durable, state-free statement (recommendation: reword). Apply the choice and record the rationale in a comment on TASK-305. Done when the section is resolved and the decision is on the record.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-07-06T12:31:30Z] Operator:
  - Done: reworded CLAUDE.md's '## Status' section to '## Build scope', dropping the phase-completion framing for a durable scope statement. Decision + rationale recorded on the parent task.
- [2026-07-06T12:31:43Z] Elias Python:
  - (re-attributing) Done: reworded CLAUDE.md's '## Status' section to '## Build scope', dropping the phase-completion framing for a durable scope statement. Decision + rationale recorded on the parent task.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T12:24:02Z] Elias Python:
  - ST2 decision: reworded the repo CLAUDE.md section rather than keeping it as-is. Renamed the heading from '## Status' to '## Build scope' and dropped the phase-completion framing ('All three planned phases are built and green') in favor of a durable statement of what's implemented and what's deferred. Rationale: even though sq check's new banner guard only scans index items (never CLAUDE.md), a '## Status' heading is exactly the shape the new convention paragraph just told every agent to avoid — leaving it would read as 'do as I say, not as I do'. The reworded section states scope, not a lifecycle claim, so it won't go stale as the roadmap moves.
- [2026-07-06T12:31:32Z] Elias Python:
  - Both subtasks done. CLAUDE.md now carries the working-norm convention (Conventions/gotchas) and the repo's own '## Status' section is reworded to '## Build scope' — no self-declared lifecycle banner left in our own file. Full suite green (1641 passed, 1 skipped, 0 failed) after this + TASK-306's changes; gates (pyright/ruff/ruff format) clean.
<!-- sq:discussion:end -->
