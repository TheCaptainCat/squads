---
id: TASK-69
sequence_id: 69
type: task
title: Backfill retroactive ADRs for squads' standing design decisions
status: Done
parent: FEAT-18
author: tech-lead
assignee: architect
priority: medium
subentities:
- local_id: ST1
  title: Author the six (plus up to two optional) retroactive ADRs as decisions in
    force, each Proposed
  status: Done
  story: US2
created_at: '2026-06-12T14:18:09Z'
updated_at: '2026-06-12T14:24:04Z'
---
<!-- sq:body -->
Content-only documentation work: zero code changes. Deliverables are sq decision items (retroactive ADRs) authored through the CLI, one per standing call.

## What to produce

One `sq create decision` per standing call. The six required, framed honestly as decisions already in force:

1. **Frontmatter is the source of truth; the index is rebuildable.** State/refs/sub-entity state live in the `.md` frontmatter; `.squads.json` is a derived index that `sq repair` reconstructs.
2. **Single global ID counter.** One monotonic counter across all item types; an ID's number is globally unique; allocation only inside the index transaction.
3. **Forward-only refs with computed backrefs.** Items store outgoing refs; backrefs are computed by inversion, never persisted.
4. **Marker-safe editing.** File content is touched only through the section machinery; agent-authored bodies are never rewritten; anchor tags delimit managed regions.
5. **Pluggable backends with the dot-claude folder as pointers.** An `AgentBackend` ABC + registry; real definitions live under the squad folder, the dot-claude tree holds only pointers; nothing reaches into it outside a backend.
6. **The dotted 0.x schema-version scheme plus the migrate runner.** Schema version is a single source of truth tracked as a dotted string for the release that introduced it, compared as a tuple; the migrate app runs ordered migrations then repairs and stamps.

You may add up to ~2 more if they are clearly standing calls — candidates: injectable clock, module-privacy convention. Judgment, not obligation; skip if marginal.

## Shape

ADR-49 is the model: Context / Decision / Consequences, plus a Status note framing it as a decision already in force. Create each **Proposed** (the manager accepts the set at the end). Write the context honestly — these were made off the record before squads tracked itself; the ADR puts them on the record, it does not pretend they were debated in-tool.

## Source material

- `CLAUDE.md` (Invariants + Conventions sections are the spine of these calls).
- `docs/internals.md` and `docs/README.md` for depth and exact mechanism wording.

## Watch for

If writing an ADR exposes a decision genuinely worth REVISITING (not just documenting), that is a NEW item — flag it in a comment on this task, do not expand scope here.

No literal sq anchor tags in any ADR text.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 69 add-subtask "<title>"`; track with `sq task 69 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Author the six (plus up to two optional) retroactive ADRs as decisions in force, each Proposed | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Author the six (plus up to two optional) retroactive ADRs as decisions in force, each Proposed

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — As an architect, I want the standing design decisions on record as ADRs, so that future work can cite, build on, or formally revisit them
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T14:19:03Z] Olivia Lead:
  - @architect this is the retroactive-ADR half of FEAT-18 (US2). One ADR per standing call — the six in the body are required; the two candidates (injectable clock, module privacy) are your call. Model on ADR-49: Context / Decision / Consequences + a Status note that frames each as a decision already in force. Create them Proposed; the manager accepts the set at the end. Source: CLAUDE.md invariants + conventions, docs/internals.md, docs/README.md.
  - If drafting one surfaces a decision genuinely worth REVISITING (not just recording), that's a new item — drop a comment here flagging it, don't grow this task. And no literal sq anchor tags anywhere in the ADR prose.
- [2026-06-12T14:24:01Z] Robert Architect:
  - Done. Authored eight retroactive ADRs (US2), all Proposed for the manager to accept with the set: ADR-71 Frontmatter is the source of truth / index is rebuildable; ADR-72 One global monotonic ID counter; ADR-73 Forward-only refs with computed backrefs; ADR-74 Marker-safe editing (sq owns anchors, agents own prose); ADR-75 Pluggable backends behind the AgentBackend ABC, .claude/ as pointers; ADR-76 Dotted 0.x schema-version scheme + sq migrate runner; ADR-77 Time is injectable via _clock; ADR-78 Module-privacy convention. The last two are the optional candidates — both are clearly standing calls of the same rank, so I included them; the set is eight.
  - Each follows ADR-49's shape: Context (why it was decided then, honestly — these were made off the record before squads tracked itself) / Decision (the call as it stands) / Consequences (what it binds today, including the costs) / Status note (retroactive, recorded in force, left Proposed). No literal sq anchor tags in any ADR prose — verified each file carries only the template's own 4 markers; sq check is clean.
  - Refs added: ADR-76 → FEAT-27 and FEAT-13 (related, both build on the migrate runner); ADR-74 → BUG-56 (related, the literal-marker-in-comment bug) and → ADR-71 (related, the frontmatter/body state split); ADR-72 → ADR-71 (related, repair reconstructs the counter from frontmatter).
  - For TASK-70 (the architecture guide + cross-linking, US1/US3): the eight ADR IDs to cite and cross-link both directions are ADR-71 through ADR-78. US3's ST2 cross-link step depends on exactly these.
  - No revisit-worthy decisions surfaced — every ADR documents what IS and holds up as written; nothing exposed a call worth reopening, so no new items flagged.
<!-- sq:discussion:end -->
