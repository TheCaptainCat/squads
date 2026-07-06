---
id: TASK-59
sequence_id: 59
type: task
title: 'Rendered show dossier: --full sub-entity panes with embedded comments'
status: Done
parent: FEAT-26
author: tech-lead
assignee: python-dev
priority: high
subentities:
- local_id: ST1
  title: Sub-entity panes and the --full --comments dossier
  status: Done
  story: US5
created_at: '2026-06-12T08:58:27Z'
updated_at: '2026-07-06T15:18:22Z'
---
<!-- sq:body -->
## Goal

The dossier layer: `--full` widens scope to the sub-entities, rendered as tidy panes, and composes with `--comments` per the "comments follow scope" rule. Implements US5. Builds on TASK-58's pane/markdown/degradation primitives.

## Decided semantics (FEAT-26 discussion, 2026-06-11; US5 acceptance)

| flags | output |
|---|---|
| --full | + one pane per sub-entity: local id + title + badges as pane title, rendered body, NO comments |
| --full --comments | + each sub-entity pane embeds its own comments, then the main discussion closes the output |

Rule: comments follow scope. --full alone = sub prose panes only; with --comments the subs carry their comments and the main discussion still renders (after the sub panes).

## In scope

- For each sub-entity (stories/subtasks/findings): a rich Panel titled with local id + title + badges (status, and severity/assignee/story where present — mirror the head badge vocabulary), rendered-markdown body inside. No comments unless --comments.
- --full --comments: embed each sub-entity's own comments (per-comment panes, reuse TASK-58's comment-pane + splitter) inside that sub-entity's pane, then render the main discussion last.
- Order: panel + body + summary table, then sub-entity panes, then (with --comments) the main discussion last. Keep the default and --comments-only paths from TASK-58 untouched.
- Degrade to plain delimited text when piped / NO_COLOR (same mechanism as TASK-58); --json unaffected by flags.

## Anchors

- TASK-58's render entry point in src/squads/_cli/_common.py — extend, do not fork it; --full adds the sub-entity section.
- Sub-entity prose + per-sub discussion: src/squads/_services/_subentities.py :: _get_block / get_story / get_subtask / get_finding return SubentityDetail(info, body, discussion) — body and discussion already extracted per sub. SubentityDetail in src/squads/_services/_results.py.
- Badge vocabulary: src/squads/_discussion.py :: _status_badge / _severity_badge and squads._models._enums STATUS_EMOJI / SEVERITY_EMOJI. Item.subentities (typed SubEntity) for the per-sub state.
- Comment splitter from TASK-58 (in _discussion.py) — reuse for per-sub discussion panes.

## Sequencing

Depends on TASK-58 (shared render path, comment splitter, degradation). Same file (_common.py) — sequence after 58 to avoid churn conflict.

## Tests

Service + CLI smoke: --full sub panes (badge title, body, no comments), --full --comments (sub panes WITH their comments + main discussion last), piped/NO_COLOR plain for both, --json unaffected. Verify the four-cell matrix end-to-end.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 59 add-subtask "<title>"`; track with `sq task 59 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Sub-entity panes and the --full --comments dossier | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Sub-entity panes and the --full --comments dossier

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US5 — As a reader wanting the whole story, I want --full to render each sub-entity and its comments in tidy panes along with the main discussion, so that one command reads as the item's dossier
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Extend TASK-58's render entry point (not fork it) with the --full dossier layer: one rich Panel per sub-entity titled with local id + title + status/severity/assignee/story badges and rendered-markdown body. With --full --comments each pane embeds its own comments (reusing the TASK-58 comment splitter/pane) and the main discussion renders last, honouring the comments-follow-scope rule and the same piped/NO_COLOR degradation (US5).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
