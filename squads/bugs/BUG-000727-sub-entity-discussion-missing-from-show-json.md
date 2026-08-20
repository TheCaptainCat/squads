---
id: BUG-727
sequence_id: 727
type: bug
title: sub-entity discussion missing from show --json
status: Verified
author: qa
priority: high
refs:
- REV-726:addresses
created_at: '2026-08-03T07:45:41Z'
updated_at: '2026-08-06T19:24:16Z'
---
<!-- sq:body -->
`sq show <id> --json` and `sq <type> <n> show --json` include a top-level `discussion` array, but each entry in `subentities` carries only local_id/title/status/assignee/severity/story/extra/body/badges — no discussion, even though the data exists and renders correctly on the human-readable surfaces.

Repro: `uv run sq review 726 finding 17 show` renders both comments on F17 (stored under `sq:finding:F17:discussion` in the .md file, and surfaced by `sq search --json` as region `finding:F17:discussion#1`). `uv run sq review 726 show --json` returns that same finding with no discussion field at all — actual vs expected: expected an additive `discussion` array on the sub-entity object mirroring the item-level shape; actual is silently absent.

Root cause: `build_item_json` (src/squads/_cli/_common.py) fetches a full `SubentityDetail` per sub-entity (`svc.get_block`), which carries both `.body` and `.discussion`, but only copies `.body` onto the JSON payload — `.discussion` is dropped on the floor.

Affected surfaces: (1) `sq show <id> --json` / `sq <type> <n> show --json` — confirmed missing, every sub-entity kind (story/subtask/finding), since sub-entity discussion is generic, not per-kind. (2) `sq <type> <n> <kind> <k> show` (the dedicated sub-entity show verb) has no `--json` option at all — never implemented, so there is currently no machine-readable single-sub-entity surface at any level. (3) `sq search --json` is NOT affected — it already surfaces sub-entity comment text via region `<kind>:<local_id>:discussion#<n>` with a snippet, confirmed against this exact finding.

Never-implemented, not a regression: per-subentity `body` and top-level `discussion` were both added together in the commit that introduced the JSON body/discussion keys (TASK-434, VS Code client foundation) — per-subentity discussion was never added at the same time, and no later commit has touched it since.

Impact: this project's convention is that decisions live in discussions, not bodies (CLAUDE.md). An orchestrating agent that briefs itself from `sq show --json` is blind to every finding-level and story-level comment — including the exact case here, a manager's re-scoping note on a finding, invisible to any JSON-driven consumer (also the VS Code preview's data source; see the companion client-side bug).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T07:50:44Z] Catherine Manager:
  - Folded into the FEAT-642 pass rather than fixed standalone: same theme, same read surfaces, and the discussion payload is a one-field omission in the same builder that FEAT-642 extends.
- [2026-08-03T07:59:57Z] Olivia Lead:
  - Fixed by TASK-729 ST4 — the discussion field on each sub-entity entry, alongside the sub-entity-aware work-queue surfaces.
- [2026-08-03T09:05:42Z] Elias Python:
  - Fixed by TASK-729 ST4: build_subentity_json (src/squads/_cli/_common.py) adds the missing discussion array to every subentities entry in show --json, sourced from the SubentityDetail.discussion already fetched — no new plumbing. Covered for story/subtask/finding in tests/cli/test_subentity_discussion_and_standalone_json.py; feature_show/task_show goldens updated additively.
- [2026-08-06T19:24:16Z] Elias Python:
  - Body edited for marker hygiene only: the repro line quoted a well-formed sq marker tag inside backticks, which the write guard has always forbidden and only accepted because find_markers was blind to mixed-case sub-entity tags (REV-736 F2). De-wrapped to the bare tag; no other prose changed, no status change.
<!-- sq:discussion:end -->
