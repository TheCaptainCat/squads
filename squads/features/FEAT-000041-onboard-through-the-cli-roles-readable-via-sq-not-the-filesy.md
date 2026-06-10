---
id: FEAT-000041
sequence_id: 41
type: feature
title: 'Onboard through the CLI: roles readable via sq, not the filesystem'
status: Ready
parent: EPIC-000012
author: product-owner
priority: high
refs:
- FEAT-000040
- FEAT-000033
description: sq role show displays the complete definition (working agreements included)
  and every onboarding text (CLAUDE.md section, skills) directs agents to sq commands
  instead of reading files under squads/
subentities:
- local_id: US1
  title: As an agent adopting my persona, I want sq role show to give me the complete
    definition including working agreements, so that I never open the file to learn
    my job
  status: Todo
- local_id: US2
  title: As an agent following the onboarding texts, I want every read they prescribe
    to be an sq command, so that one interface covers work and identity — locally
    and, someday, remotely
  status: Todo
created_at: '2026-06-11T09:02:40Z'
updated_at: '2026-06-11T09:17:28Z'
---
<!-- sq:body -->
## Problem

Every ticket manipulation goes through `sq` — but to learn *who they are*, agents are told to read
files: the generated CLAUDE.md section says "load their role definition from
`squads/agents/roles/`", and `sq role show <slug>` is not a substitute because it prints only the
catalog card (mission, responsibilities) — the **working agreements**, the part an agent actually
needs to behave correctly, live only in the item body. Observed live (2026-06-11): the product
owner re-read her role by opening the `.md` directly, in a session where everything else went
through the CLI. One interface for work, a filesystem detour for identity.

## Value

The CLI becomes the *single* interface agents are taught: read your role, your skills, your
items — all through `sq`. That consistency matters beyond elegance: remote mode (FEAT-000033)
has no filesystem to detour to, so any onboarding text that says "read this path" breaks the day
the squad is remote; text that says "run `sq role show`" doesn't.

## Scope

- **`sq role show <slug>` shows the complete definition**: the catalog card *plus* the tracked
  item's body (working agreements, skills list) — everything the file would give, rendered. Honors
  FEAT-000026's conventions when both land (panes, --raw, piped behaviour).
- **Onboarding texts direct to the CLI**: the generated CLAUDE.md section's impersonation
  paragraph says `sq role show <slug>` (not "load from `squads/agents/roles/`"); the `squads` and
  `greeting` skills and the role files' own self-references get the same sweep.
- **Pointer files are exempt**: `.claude/agents/*.md` `@`-including the role path is backend
  plumbing (how Claude Code boots a subagent), not agent guidance — paths stay. The rule:
  *machinery may use paths; instructions teach commands.*
- Sweep for siblings: any other "read the file at …" guidance in generated content (skills,
  workflow cheatsheet, docs) gets the same treatment where an sq command exists; gaps where no
  command exists get noted (candidate: `sq skill show`?).
- Regenerated via `sq sync`; no migration (managed files are regenerable).

## Acceptance

- `sq role show <slug>` output contains the working agreements and skills, matching the item body;
  covered by a test.
- The generated CLAUDE.md section and bundled skills contain no agent-facing instruction to read
  files under `squads/` for content an sq command provides; pointer files unchanged.
- An agent following only onboarding texts can fully brief on their role without a single file
  read (the live scenario above, replayed through the CLI).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 41 add-story "As a <role>, I want … so that …"`; track with `sq feature 41 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As an agent adopting my persona, I want sq role show to give me the complete definition including working agreements, so that I never open the file to learn my job |
| US2 | Todo |  | As an agent following the onboarding texts, I want every read they prescribe to be an sq command, so that one interface covers work and identity — locally and, someday, remotely |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an agent adopting my persona, I want sq role show to give me the complete definition including working agreements, so that I never open the file to learn my job

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** sq role show <slug> renders catalog card + item body (mission, responsibilities, working agreements, skills); content matches the .md; test asserts the agreements are present.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an agent following the onboarding texts, I want every read they prescribe to be an sq command, so that one interface covers work and identity — locally and, someday, remotely

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** the CLAUDE.md impersonation paragraph and the bundled skills reference sq role show / sq docs / sq <type> show only; grep for 'squads/agents/roles' in agent-facing generated text comes back empty (pointer files exempt); sq sync propagates.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
