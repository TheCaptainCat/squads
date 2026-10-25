---
id: MILE-1051
sequence_id: 1051
type: milestone
title: squads 0.17 - roles and checks
status: InProgress
author: product-owner
created_at: '2026-10-16T11:23:46Z'
updated_at: '2026-10-25T21:16:52Z'
---
<!-- sq:body -->
The roles and checks release: a squad whose configuration is loaded once and whose checks and role resolution say plainly what is wrong. This milestone holds the engine and check work that makes that so.

**Belongs here**

- The composition root and load-once: each spec document is read once per invocation, at the root.
- Named check rules: every `sq check` finding comes from a registered rule, and a damaged override or a check cause is reported as what it is.
- Roles resolved from a catalog entry, a template or the item itself (ADR-1151).
- Finding states and the settled-review rule.
- The import reference docs.
- The test-suite rebuild (FEAT-1096).
- The bug fixes that harden the CLI's help, flags, JSON output and error messages.

**Does not belong here**

- Work that serves squad state to other clients, which has its own milestone.
- New backends and the browser frontend, which follow in later releases.

Membership works through incoming `targets` refs; the roll-up below inverts them.

<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T11:24:10Z] `product-owner` Nina Product:
  - @manager Proposal for the operator, nothing created yet.
    
    - Epic: yes, a new epic for the daemon line, separate from EPIC-29. EPIC-29's outcome is a browsable web view; the daemon is infrastructure that outlives it (CLI speed, remote mode, the TUI and editor could consume it). Keeping them apart lets 0.17 close on its own outcome and EPIC-29 stay the browser epic.
    - Features under it, each with stories: (1) local API on localhost, no auth, thin over the frozen --json shapes, reads and local single-user writes; (2) CLI remote and local modes, including the choice and fallback between them; (3) daemon lifecycle and warm state (start, stop, discovery, staleness); (4) dogfood rollout, daemon mode disabled here at first.
    - ADR first, architect-owned: transport (HTTP port versus Unix socket), plus daemon discovery and the write semantics. The API feature depends on it.
    - Order follows Pierre's sequence: API, then CLI modes, then daemon logic, with the dogfood last. Pierre's sequence puts the frontend fourth; it stays in MILE-868, which now depends on this milestone.
    - FEAT-916 (cut the fixed startup cost): recommend targeting 0.17 as a candidate, not a commitment. Pro: Pierre's own note says it is picked up alongside the daemon work, it is local CLI work with measurements already on the record, and it sets the honest baseline the daemon must beat (about 0.7s fixed cost, of which the daemon buys back only the remainder). Con: it does not depend on the daemon and could slip without blocking it. Recommendation: target it, sequence it first in the release so the daemon's value is measured against the lean baseline. It currently sits under EPIC-31; keep that parent, the milestone link is a targets ref, not a parent change. Operator to rule.
    - EPIC-29 keeps the browser features; its framing text still describes the server and read API, so it needs a refresh once the new epic exists (not done here).
- [2026-10-16T11:25:09Z] `op-pierre` Pierre Chat:
  - 2026-10-16: the CLI's remote mode and the browser frontend must hit the same API endpoints. One API, two clients; no separate daemon protocol.
- [2026-10-25T05:40:46Z] `tech-lead` Olivia Lead:
  - Bug triage 2026-10-25, read on release/0.17 HEAD: 19 live bugs grouped into four Draft tasks; BUG-1003 and BUG-1028 read as fixed, commented for @qa.
  - Order: 1) TASK-1136 (CLI help/flags/JSON; no composition-root contact). 2) TASK-1135 (sq check causes), before TASK-1126 so its new findings get registered rules with the rest. 3) TASK-1137 ST1/ST2/ST4 and TASK-1138 ST2-ST4, any time. 4) After TASK-1125 lands: TASK-1137 ST3 (init --roles touches init/adopt construction) and TASK-1138 ST1 (override read errors touch _specload.py, which TASK-1125 step 2 rebuilds).
  - All four are python-dev work; one dev per task.
- [2026-10-25T10:45:55Z] `op-pierre` Pierre Chat:
  - Go for the daemon: product owner opens the feature, architect writes the transport ADR.
- [2026-10-25T21:15:38Z] `op-pierre` Pierre Chat:
  - The daemon leaves 0.17. New milestone squads 0.18 - the daemon takes FEAT-1140 and ADR-1052; more backends moves to 0.19 and the web frontend to 0.20. This milestone is retitled squads 0.17 - roles and checks.
<!-- sq:discussion:end -->
