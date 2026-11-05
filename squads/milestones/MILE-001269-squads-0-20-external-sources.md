---
id: MILE-1269
sequence_id: 1269
type: milestone
title: squads 0.20 - external sources
status: InProgress
author: product-owner
refs:
- MILE-1241:depends-on
- EPIC-1268
description: Pull issues from GitLab, GitHub and Jira into the squad, with a schema
  migration
created_at: '2026-11-03T15:57:06Z'
updated_at: '2026-11-05T09:56:11Z'
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
- [2026-11-04T19:08:42Z] `manager` Catherine Manager:
  - InProgress since the external sources work started on 2026-11-03; the status trailed the work. Remaining for 0.20: FEAT-1290 (injected skills), TASK-1293 (live Jira check) when an instance is available, and the release itself.
- [2026-11-05T09:38:29Z] `manager` Catherine Manager:
  - - Release benchmarks, 0.20.0 tree (HEAD 9a5ea0eb), 2026-11-05, copy of this squad. The schema moved to 0.20, so the released 0.19 build refuses the copy; as the runbook says these are the new build's --spans medians.
    
    ```
    
    show: median wall 131 ms
      startup              14.8 ms
      root_callback         0.1 ms
      resolve_squad         0.4 ms
      dto                   0.2 ms
      operation            66.3 ms
      api_call             67.6 ms
      call_done            83.0 ms
      shim_start           30.6 ms
      shim_resolve          1.1 ms
      shim_roundtrip       94.1 ms
      handler              77.8 ms
      shim_end            125.7 ms
    
    list: median wall 203 ms
      startup              13.0 ms
      root_callback         0.1 ms
      resolve_squad         0.3 ms
      dto                   4.3 ms
      operation            51.3 ms
      api_call             54.7 ms
      call_done            67.7 ms
      shim_start           29.2 ms
      shim_resolve          1.0 ms
      shim_roundtrip      161.4 ms
      handler             143.3 ms
      shim_end            198.5 ms
    
    tree: median wall 126 ms
      startup              12.6 ms
      root_callback         0.1 ms
      resolve_squad         0.3 ms
      dto                   2.8 ms
      operation            51.6 ms
      api_call             53.4 ms
      call_done            66.5 ms
      shim_start           30.2 ms
      shim_resolve          1.1 ms
      shim_roundtrip       90.7 ms
      handler              75.7 ms
      shim_end            122.0 ms
    
    CLI shim overhead (wall time minus the daemon handler time, 31 interleaved runs):
    form                 median      p25      p75   budget   (ms, 31 runs)
    show                     60       52       67      100   ok
    list --json              58       50       80      100   ok
    bash completion          52       48       64      100   ok
    load average  before: (3.451171875, 2.82421875, 2.49951171875)  after: (3.14794921875, 2.77978515625, 2.48828125)
    ```
    
      Against 0.19.0's medians (show 757, list 712, tree 673 ms) every command is faster; the shim overhead medians stay within the 100 ms budget.
- [2026-11-05T09:56:11Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-05): the Jira connectors (jira@cloud-v3, jira@dc-v2) ship as experimental in 0.20: they are tested against recorded fixtures only, never against a live Jira.
<!-- sq:discussion:end -->
