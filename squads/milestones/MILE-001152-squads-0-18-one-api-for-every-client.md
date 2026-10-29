---
id: MILE-1152
sequence_id: 1152
type: milestone
title: squads 0.18 - one API for every client
status: Done
author: product-owner
description: 'The command layer: every command calls one operation and renders its
  result, with JSON output on every command'
created_at: '2026-10-25T21:16:14Z'
updated_at: '2026-10-29T13:58:48Z'
---
<!-- sq:body -->
The command-layer release: every command calls one operation and renders the result it gets back, so the JSON a command prints is the same shape an API answers with, and every command that prints a result can print it as JSON. Output adopters rely on today does not change, and local commands are no slower than in 0.17.0. The daemon that serves these operations over HTTP follows in 0.18.1 (MILE-1241).

Scope is carried by **FEAT-1226**, the command layer: one operation per command, `--json` on every command that prints a result, one result shape for the CLI and the API, results that carry their own display, the terminal UI reading through the same API, and local performance held at 0.17.0's level. Decided in ADR-1224.

The release is ready when every command runs on its operation, human and `--json` output and exit codes are unchanged apart from added JSON keys, the terminal UI shows the same screens through the API, and `sq <type> <n> show`, `sq list` and `sq tree` are no slower than in 0.17.0 on the reference host.

The daemon, remote mode, authentication, a squad hosted on another machine (FEAT-33), pagination and the frontend are out of scope.

Membership works through incoming `targets` refs; the roll-up below inverts them.

<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T13:48:28Z] `manager` Catherine Manager:
  - 0.18 opened 2026-10-28 by op-pierre; FEAT-1140 is the scope, its dependencies (ADR-1052, TASK-1125) are settled.
- [2026-10-28T20:45:29Z] `op-pierre` Pierre Chat:
  - Scope (2026-10-28): 0.18 carries both the DTO refactor (one service call per command where possible, renderer fed DTOs and never calling the service) and the daemon's resource endpoints with the CLI's HTTP-or-local layer. See the op-pierre direction on FEAT-1140.
- [2026-10-28T21:58:00Z] `op-pierre` Pierre Chat:
  - 2026-10-28: the manager drives 0.18 overnight. Order: product owner scope, then tech lead breakdown; move to Ready if coherent; then the dev/review loop, the DTO refactor first and the daemon after.
- [2026-10-28T22:06:05Z] `product-owner` Nina Product:
  - Body and summary aligned 2026-10-28 with the new scope: FEAT-1226 (command layer, first) and FEAT-1140 (daemon), the release gate from ADR-1225 (every command on its operation, TUI in both modes, the 275/235 ms client budget, tests in both modes on three OSes), FEAT-33 and pagination out of scope. Title question raised on FEAT-1140.
- [2026-10-28T22:07:56Z] `product-owner` Nina Product:
  - Retitled 2026-10-28 to "squads 0.18 - the daemon and one API for every client" per board notice 11, decided by the manager (FEAT-1140, 027ea69).
- [2026-10-29T12:57:48Z] `op-pierre` Pierre Chat:
  - 2026-10-29: 0.18.0 is released now without the daemon. The daemon (FEAT-1140, TASK-1218 to 1222) moves to 0.18.1, together with the dependency upgrade (typer 0.27, filelock 4, pydantic 2.14, anyio, dev tools ruff/pyright/pytest) and raised lower bounds.
  - 2026-10-29: the TUI eye-check (TASK-1233 ST2) is done before the cut; the 125 release-branch commits are squashed into themed commits and force-pushed before the PR.
- [2026-10-29T12:59:51Z] `product-owner` Nina Product:
  - Retitled 2026-10-29 to "squads 0.18 - one API for every client" and body rewritten per op-pierre e9859e1: 0.18.0 carries FEAT-1226 only; FEAT-1140 now targets MILE-1241 (0.18.1), and MILE-868 depends on MILE-1241 instead.
- [2026-10-29T13:12:52Z] `manager` Catherine Manager:
  - Release benchmark, 2026-10-29: `scripts/bench_local_mode.py`, 31 interleaved runs, released 0.17.0 (old) against the 0.18.0 release tree (new), on a copy of this repository's squad.
    
    ```
    command build    median      p25      p75   (ms, 31 runs)
    show    old        1052      919     1215
    show    new         702      646      843
    show    new/old median = 0.667
    list    old        1063     1022     1134
    list    new         778      746      807
    list    new/old median = 0.731
    tree    old        1053      981     1105
    tree    new         724      695      764
    tree    new/old median = 0.688
    ```
- [2026-10-29T13:58:48Z] `manager` Catherine Manager:
  - Released 2026-10-29 as v0.18.0 (https://github.com/TheCaptainCat/squads/releases/tag/v0.18.0): PyPI publish and VSIX asset succeeded.
<!-- sq:discussion:end -->
