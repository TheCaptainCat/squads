---
id: MILE-1241
sequence_id: 1241
type: milestone
title: squads 0.19 - the daemon and the overridable vocabulary
status: InProgress
author: product-owner
refs:
- MILE-1152:depends-on
- EPIC-29
description: The daemon serving the command layer's operations as resource routes,
  the bundled vocabulary fully overridable on generic storage, a bug batch, and dependencies
  upgraded and tested
created_at: '2026-10-29T12:59:12Z'
updated_at: '2026-10-31T15:55:20Z'
---
<!-- sq:body -->
The 0.19 release: the daemon that serves the command layer's operations as 
resource routes on the adopter's own machine, a CLI and terminal UI that call 
those routes or read the squad directly with the same output either way, the 
bundled vocabulary made fully overridable on generic storage, and the fixes and 
dependency upgrades that ride with them. It builds on the command layer of 
0.18.0, whose operations the routes serve. It makes that line usable on one 
machine, for one person; the browser frontend (MILE-868) builds on the same 
routes. The generic-storage schema migration is what makes this 0.19.0 rather 
than a patch release.

Scope is carried by these items:

- **FEAT-1140**, the daemon: the resource routes and their errors, the OpenAPI 
document, the CLI's remote and local modes, item versions on writes, the schema 
and vocabulary checks, the terminal UI as a daemon client, the client budget, 
the daemon's lifecycle and settings, and native Windows. Decided in ADR-1052 and
ADR-1225.
- **FEAT-1249**, the bundled vocabulary fully overridable: no bundled type, 
status, priority surface, alias or generated text is special-cased outside the 
spec, stored generically, with a schema migration for existing squads. Decided 
in ADR-1250.
- **FEAT-1242**, dependencies current and tested: the versions an adopter 
installs are the versions the suite runs, with the daemon's new server 
dependencies among them.
- **The bug batch** (BUG-1183 to BUG-1200, BUG-1240, BUG-1248), delivered 
through TASK-1244, TASK-1245 and TASK-1246 and reviewed in REV-1247.

The release is ready when the terminal UI works through the API in both modes,
the client budget is met and recorded (the CLI is a stdlib shim, and its
overhead, the wall time minus the daemon's handler time, is at most 100 ms as
the median of 31 interleaved `sq task <n> show` runs on the GitHub-hosted Linux
runner of the client-budget CI job, one figure for human output, `--json` and
completion), the CLI's tests pass in all three modes (local, remote through the
command endpoint, and routes through `HttpApi`) on Linux, macOS and native
Windows, and the declared lower bounds of every dependency are the versions the
suite ran. It also needs the bundled vocabulary to resolve only through the
spec, with `sq migrate up` carrying an existing squad to the new storage and
`sq repair` rebuilding the index from the item files, and every bug in the batch
Fixed or settled with a reason.

Authentication, a squad hosted on another machine (FEAT-33), pagination and the 
frontend itself are out of scope.

Membership works through incoming `targets` refs; the roll-up below inverts 
them.

<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T12:59:50Z] `product-owner` Nina Product:
  - Created 2026-10-29 per op-pierre e9859e1 on MILE-1152: the daemon (FEAT-1140, its tasks TASK-1218 to 1222 following through the feature) and the dependency upgrade (FEAT-1242). Depends on MILE-1152 for the command layer.
- [2026-10-29T16:20:00Z] `op-pierre` Pierre Chat:
  - 2026-10-29: FEAT-1242 (dependency upgrade) goes first, so the daemon (FEAT-1140, TASK-1218 onward) is built on typer 0.27 and filelock 4. The wrong-prefix id resolution in sq workflow view (raised in REV-1235) is filed as a bug and targets this milestone.
- [2026-10-29T16:24:27Z] `op-pierre` Pierre Chat:
  - 2026-10-29: every open bug (BUG-1183 to BUG-1197, BUG-1200, BUG-1240) is fixed in one batch in this milestone, before any feature work (FEAT-1242, then FEAT-1140). At most 3 developers, working in parallel.
- [2026-10-29T16:32:00Z] `tech-lead` Olivia Lead:
  - Bug batch planned as three parallel tasks, disjoint by module: TASK-1244 (init/adopt/migrate/repair: BUG-1187..1191), TASK-1245 (list/tree/reflog/graph options, memory search, import message, typer suggestion: BUG-1192..1197, 1200), TASK-1246 (create guide, ref rm, sub-entity verbs, workflow view: BUG-1183..1186, 1240). All Draft.
  - Open points: BUG-1185 needs a product ruling (sub-entity titles are optional by documented design); BUG-1192 is fixed by typer 0.27.3, which TASK-1243 brings, so TASK-1245 ST1 lands after it. CHANGELOG.md is the one shared file; devs report, @tech-writer writes the 0.18.1 lines. @manager
- [2026-10-29T19:02:52Z] `op-pierre` Pierre Chat:
  - 2026-10-29: the 12 gaps of the bundled-vocabulary audit (architect comment on REV-1247) are fixed in this milestone, before feature work, after the bug batch: ADRs first (ADR-323 section 5, ADR-348 section 7, ADR-622), then tasks, at most 3 developers in parallel. The frozen keys stay; their labels come from the spec.
- [2026-10-29T19:18:38Z] `op-pierre` Pierre Chat:
  - 2026-10-29: the schema migration makes this release 0.19.0, not 0.18.1. The following milestones shift: more backends (MILE-1061) becomes 0.20, the web frontend (MILE-868) becomes 0.21.
- [2026-10-31T15:54:37Z] `manager` Catherine Manager:
  - Release benchmarks, 0.19.0 tree (HEAD b18668d4), 2026-10-31, copy of this repo's squad, load average about 2 on 14 cores.
    
    Local-mode run time: the released 0.18.0 build refuses this squad's 0.19 schema, so as the runbook says these are the new build's --spans medians (SQUADS_DAEMON=off, 31 runs):
    
    ```
    
    show: median wall 757 ms
      startup             364.8 ms
      root_callback       213.5 ms
      resolve_squad         9.3 ms
      compose               2.9 ms
      dto                   3.5 ms
      operation           121.7 ms
      api_call            135.4 ms
      call_done           717.6 ms
      end                 725.0 ms
      exit (after end)     32.1 ms
    
    list: median wall 712 ms
      startup             250.5 ms
      root_callback       224.5 ms
      resolve_squad         9.9 ms
      compose               3.0 ms
      dto                   5.4 ms
      operation            97.5 ms
      api_call            113.8 ms
      call_done           603.6 ms
      end                 688.2 ms
      exit (after end)     23.8 ms
    
    tree: median wall 673 ms
      startup             250.6 ms
      root_callback       237.3 ms
      resolve_squad        10.5 ms
      compose               2.6 ms
      dto                   4.4 ms
      operation           106.7 ms
      api_call            126.1 ms
      call_done           622.5 ms
      end                 651.1 ms
      exit (after end)     21.6 ms
    ```
    
    CLI shim overhead (wall time minus the daemon's handler time, 31 interleaved runs), against the 100 ms budget:
    
    ```
    form                 median      p25      p75   budget   (ms, 31 runs)
    show                     51       49       61      100   ok
    list --json              63       54       73      100   ok
    bash completion          57       47       69      100   ok
    load average  before: (1.828125, 2.81494140625, 2.08544921875)  after: (1.7119140625, 2.7412109375, 2.0732421875)
    ```
    
    On the GitHub runner the client-budget job reported 35-36 ms (run 41141368085) and 53-55 ms (run 41145415746).
<!-- sq:discussion:end -->
