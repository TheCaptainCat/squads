---
id: TASK-497
sequence_id: 497
type: task
title: 'Dogfood: author the release-process skill scoped to manager/devops/tech-writer'
status: Done
parent: FEAT-491
author: tech-lead
refs:
- ADR-492:implements
- BUG-490:fixes
- TASK-493:depends-on
- TASK-495:depends-on
description: End-to-end validation of the capability; runbook content supplied by
  manager
created_at: '2026-07-20T08:59:21Z'
updated_at: '2026-07-20T12:32:53Z'
---
<!-- sq:body -->
## Scope

Exercise the whole capability end-to-end by authoring the motivating skill (BUG-490): a
release-process skill — the gates, the prep steps, how to **draft** (not publish) a release —
preloaded for the `manager`, `devops`, and `tech-writer` roles. This is the acceptance-in-anger
proof that authored bodies + role scoping actually deliver the use case; it uses only the new
supported surface, no new code.

### Steps

- `sq skill add <name> --desc "…" [--when-to-use "…"]` to create the skill.
- `sq skill <n> body --file …` (or `-m`) to author the runbook body — real, multi-paragraph
  content, not the stub.
- `sq skill <n> link-role manager`, `… link-role devops`, `… link-role tech-writer` to scope it.

### Content ownership

The **runbook content itself is supplied by the manager** — this task validates the mechanism,
not the release process wording. Do not invent release steps here; the manager provides the body
text (and it must respect the "prep, never publish" boundary — agents never tag/publish).

## Acceptance

- The release-process skill exists as a custom (authored) skill with a real body, and
  `sq skill show` labels it custom.
- Its pointer body and the `manager`, `devops`, and `tech-writer` role pointers + `## Skills`
  sections all reflect the scoping; no other role preloads it.
- The skill is discoverable by the main agent by name regardless of scoping (scoping only drives
  which role pointers auto-preload it).
- A subsequent `sq sync` leaves the authored body and the three scope edges intact (no drift).
- `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 497 add-subtask "<title>"`; track with `sq task 497 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
