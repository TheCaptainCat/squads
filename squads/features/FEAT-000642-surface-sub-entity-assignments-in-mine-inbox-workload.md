---
id: FEAT-642
sequence_id: 642
type: feature
title: Surface sub-entity assignments in mine/inbox/workload
status: Draft
author: product-owner
description: Route work by per-subtask assignee, not just item-level
created_at: '2026-07-24T07:28:33Z'
updated_at: '2026-07-24T07:28:35Z'
---
<!-- sq:body -->
A sub-entity (story/subtask/finding) already carries its own `assignee`, but the work-queue surfaces are item-level only: `sq mine` filters on `item.assignee`, and `inbox`/`workload` likewise never scan sub-entity assignees. So an actor assigned only a subtask (not the parent) is never routed that work.

Make mine/inbox/workload sub-entity-aware so a larger task can be broken into subtasks owned by different actors and each actor sees their subtask in their own queue. Deferred backlog capture; not scheduled.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 642 add-story "As a <role>, I want … so that …"`; track with `sq feature 642 story <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
