---
id: TASK-1293
sequence_id: 1293
type: task
title: Run the Jira connectors against a live Jira
status: Draft
author: tech-lead
refs:
- TASK-1278
- ADR-1274
description: Live run of jira@cloud-v3 and jira@dc-v2 to confirm the API shapes and
  scoped-sources behaviour
created_at: '2026-11-04T18:38:36Z'
updated_at: '2026-11-04T18:39:02Z'
priority: low
---
<!-- sq:body -->
## Goal

Run the Jira connectors against a live Jira instance. Their fixtures under `tests/fixtures/sources/jira-cloud` and `jira-dc` were written from the API documentation, so the API shapes they assume and the scoped-sources behaviour on Jira have only run on the loopback harness (TASK-1278, ADR-1274 §14). GitLab and GitHub have had their live run; Jira has not, for want of an instance.

## What to run

- A throwaway squad outside the repository (`sq init` in a fresh directory, never under the repo or directly in `/tmp`), driven by the dev build: `uv run --project <repo> sq -C <scratch> …`.
- One source per available connector version: `jira@cloud-v3` (credential `user` = email, `token` = API token) and `jira@dc-v2` (personal access token). Run both if both instances are available; otherwise the one at hand, and say which was not run.
- Scope: a `jql` naming a small project with issues of several types and priorities, a closed issue, an issue link, a comment, and if possible a comment restricted by visibility and an issue carrying a security level.
- In order: `sq source check`; `sq source pull --dry-run`; `sq source pull`; a second `sq source pull` (everything unchanged); `sq <type> <n> show --refresh` on a pulled item; `sq <type> <n> source unlink` then `sq <type> <n> source relink <source> <issue>` on a pulled item, once by key and once by immutable ID; then `sq check` and `sq repair` (index unchanged).

## What to confirm

API shapes, Jira Cloud (`cloud-v3`):

- `/search/jql` paging with `nextPageToken` and `isLast`.
- `fields` selecting what comes back.
- `/label` paging.
- `/user/search` and `/user?accountId`; the handle shown is the accountId.
- Comment `visibility` and `jsdPublic`: a restricted or customer-hidden comment is not pulled.

API shapes, Jira Data Center (`dc-v2`):

- `/search` capping `maxResults`, and paging still covering the whole scope.
- `/user?key=` and `/user?username=`; the handle shown is the username.
- `key` present on the issue records.
- With no label listing endpoint, a mapped label that no in-scope issue carries is reported missing by `sq source check`.

Both versions:

- Type from the issue type name, priority from the priority name, labels, issue links keyed by the directional phrase (`blocks`, `is blocked by`), open or closed from the status category.
- Author fields from `creator`.
- The issue ID as the immutable ID; if the instance allows it, a move to another project keeps the item while the key changes.

Scoped-sources behaviour:

- The JQL is the scope: the pull lists every issue it returns, in every state, and the optional filter applies to what it returns; the report line counts issues rejected by the filter.
- A `jql` holding `ORDER BY` is refused at load, saying the clause is to be removed; the words inside a quoted JQL string are not refused.
- An issue carrying a security level is not pulled, by the listing, by ID or as a link's other end; an item whose issue becomes restricted reads as `gone` and stays.
- `show --refresh` and `relink` decide whether the issue is in scope with one search, `id = <id> AND (<jql>)`, without listing the scope; an issue outside the JQL reads as outside the scope.

## How to record the result

One comment on this task per connector version: the date, the Jira product and version, the commands run, what each shape and behaviour above did (confirmed, differed, not exercised), and any gap found, filed as a bug referencing this task. Never name the instance's hostname, project key, users or issue content, and never paste a credential or a raw response.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1293 add-subtask "<title>"`; track with `sq task 1293 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
