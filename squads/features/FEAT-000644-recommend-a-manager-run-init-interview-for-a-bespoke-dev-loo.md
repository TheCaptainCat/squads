---
id: FEAT-644
sequence_id: 644
type: feature
title: Recommend a manager-run init interview for a bespoke dev-loop skill
status: Draft
author: product-owner
refs:
- FEAT-642
description: Init docs recommend the manager interview the operator and author a self-assigned
  squad-running skill
created_at: '2026-07-24T07:41:51Z'
updated_at: '2026-07-24T07:42:22Z'
---
<!-- sq:body -->
**Capability.** `sq init`'s documentation recommends — but never scaffolds, generates, or enforces — that the manager agent open a squad by interviewing the operator about how they want the squad run, then author and self-assign a bespoke skill (e.g. a "run the dev loop" skill) that encodes the operator's answers.

**Why.** sq deliberately enforces only a hard floor: stable IDs, the status lifecycle, and item structure. Everything about *how* a squad is managed day to day is a per-operator, per-squad style choice, and sq should stay out of the way of that choice rather than impose one. Recommending an init-time interview front-loads those working preferences in one sitting, instead of letting them accrue slowly, one piece of corrective feedback at a time, across many sessions.

**Scope.**

- Add a recommendation to the init documentation: early in a new squad's life, the manager role interviews the operator about how they want work run, then closes the interview by authoring a bespoke skill for itself and self-assigning it, so the operator's answers become durable, discoverable guidance rather than a one-off conversation.

- Ship a suggested interview checklist as documentation content — seven areas the manager can raise, offered as prompts and illustrative questions, not a rigid script: (1) autonomy & escalation — unattended loop vs. pausing at gates, and what must interrupt the operator (schema/migration changes, architectural decisions, design forks, spend, anything user-facing/visual); (2) delegation & roles — who authors what, which specialists are live, custom roles, whether review must be an independent agent from the builder; (3) quality bar — the must-pass gate before a handoff or commit, review rigor for integrity-critical work, and whether to independently verify completion claims; (4) git & releases — commit-message style and trailers, who commits vs. pushes vs. publishes; (5) communication — update verbosity, handoff conventions, and putting the operator's own words on the record; (6) structure & records lifecycle — feature and task grouping style, and whether records like decisions/requirements documents are amended in place or superseded by a new item as they evolve; (7) safety — confirmation before destructive operations, and comfort with parallel agents.

- Explicitly out of scope: sq itself generates nothing from this. No new command, no scaffolded file, no init-time prompt, no validation that the skill exists or matches the checklist. The interview and the resulting skill are ordinary operator/manager-authored content, exactly like any other custom skill — the recommendation lives in documentation only.

- One grouping style raised under structure & records lifecycle — a single larger task broken into subtasks owned by different actors — depends on the work queues (the assignment-routing surfaces an actor checks for their own work) becoming aware of per-subtask assignments; until then, that style routes correctly for the parent item's assignee but not for a different actor assigned only a subtask.

**Acceptance.**

- Init documentation recommends the manager-interview → self-authored-skill flow, clearly framed as optional guidance an operator can decline entirely.

- The seven-area checklist ships as documentation content, usable as-is or adapted.

- No new command, generator, template, or validation step ships — sq's runtime behavior is unchanged; this is a documentation-only change.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 644 add-story "As a <role>, I want … so that …"`; track with `sq feature 644 story <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
