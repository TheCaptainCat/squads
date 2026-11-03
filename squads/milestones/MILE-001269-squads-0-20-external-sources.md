---
id: MILE-1269
sequence_id: 1269
type: milestone
title: squads 0.20 - external sources
status: Draft
author: product-owner
refs:
- MILE-1241:depends-on
- EPIC-1268
description: Pull issues from GitLab, GitHub and Jira into the squad, with a schema
  migration
created_at: '2026-11-03T15:57:06Z'
updated_at: '2026-11-03T15:57:06Z'
---
<!-- sq:body -->
The external sources release: a squad pulls the issues humans file on GitLab, GitHub and Jira and agents work them through `sq`. The linked epic carries the outcome and the framing. A new core `source` key on items and a `map` attribute kind make this a schema release, with a migration for existing squads.

Scope is carried by the features that target this milestone:

- stored view bodies, the generic views capability the source description is built on;
- the sources spec document and the pull engine, with the source-owned fields, the check rules and the link verbs;
- `sq source check`, the per-source readiness checklist, and the converter registry;
- the GitLab, GitHub and Jira connectors, registered by name and version.

The release is ready when a squad declaring one source of each connector can run `sq source check` clean against a sandbox instance, pull twice with the second pull changing nothing, and have every source-owned field refused for local writes, with `sq migrate up` carrying an existing squad to the new schema and `sq repair` rebuilding the index from the item files.

Writing back to a tracker, daemon-triggered pulls and automatic resolution of duplicate imports are out of scope.

Membership works through incoming `targets` refs; the roll-up below inverts them.

<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
