---
id: TASK-244
sequence_id: 244
type: task
title: Add workflow as the third sq override artifact (scaffold/diff/drift)
status: Done
parent: FEAT-209
author: tech-lead
subentities:
- local_id: ST1
  title: workflow as third sq override artifact (scaffold/diff/drift)
  status: Done
  story: US1
created_at: '2026-06-30T07:49:54Z'
updated_at: '2026-07-06T15:21:08Z'
---
<!-- sq:body -->
## Goal
Make the workflow spec the **third overridable artifact** in the existing `_overrides/` + `sq
override` machinery, alongside templates and roles: `sq override scaffold workflow`,
`sq override diff workflow`, `sq override drift/list workflow`. (AC #6; supports US1.)

## Current state — the pattern to follow
`src/squads/_overrides/_service.py` dispatches on a `kind` string ("template" | "role") across
`scan_overrides`, `scaffold_*`, `diff_override`, `update_stamp`, and `check_override_issues`.
- Templates: stored under `.overrides/templates/`, diffed against bundled template content, drift via
  a per-release content-hash manifest (`_manifest.py` reads `templates_manifest.json`).
- Roles: stored as `.overrides/roles/<slug>.toml`, stamped with `# squads:override-base:<version>`,
  drift keyed on the `agents/role.md.j2` body template hash.
The CLI is `src/squads/_cli/_override.py` (scaffold / list / diff / update).

## What to build — add kind "workflow"
- **Canonical location**: `.overrides/workflow.toml` (single file, not a directory — there's one
  workflow spec). This is also the file TASK-239's loader reads. **Pin this as the single source
  of truth** and make sure TASK-239 reads the same path (cross-reference in both bodies). If the
  team also wants a `[workflow]` block in `.squads.toml`, treat `.overrides/workflow.toml` as primary
  and error on both-present (decided in TASK-239).
- **scaffold workflow**: write a STARTER override file (NOT a full copy of the bundled default —
  additive-only means the override should contain only the team's additions). Seed it with the
  `# squads:override-base:<version>` stamp + a commented worked example (e.g. a `[items.incident]` +
  `[lifecycles.incident]` block) so an admin can uncomment and edit. Reuse `scaffold_role`'s
  stamp-comment approach.
- **diff workflow**: Δ-mine = the override file vs an empty/starter reference (like roles, which diff
  against empty — the override is purely additive so there's no bundled counterpart to diff against);
  optionally a Δ-upgrade based on whether the bundled `default_workflow.toml` changed since the stamp.
  To support drift detection you'll need the bundled `default_workflow.toml` hashed in the manifest
  (`_manifest.py` currently only hashes templates under `_rendering/templates/`). Either extend the
  manifest generator (`scripts/gen_template_manifest.py` — see the @devops note in `_manifest.py`) to
  include the workflow TOML, OR drift for workflow simply compares the stamp to the running version
  (simpler, acceptable for v1). Pick the simpler path that satisfies AC #6 and note it.
- **list / scan_overrides**: include the workflow override entry with its kind, stamp, state.
- **update**: re-stamp the workflow override (TOML stamp, same as roles).
- **check_override_issues**: add workflow drift/unstamped warnings consistent with roles.
- **CLI** (`_cli/_override.py`): accept `workflow` as a scaffold/diff/update target. Since
  `scaffold` currently takes a template name positional + `--role` option, add a parallel
  `--workflow` flag OR recognise the literal `workflow` — match whatever reads cleanest against the
  existing `--role` design; keep it consistent.

## Acceptance (AC #6)
- `sq override scaffold workflow` creates `.overrides/workflow.toml` with a stamp + commented example.
- `sq override diff workflow` shows the team's additions (Δ-mine).
- `sq override list` shows the workflow override with a state; `sq override drift`/check flags
  staleness consistent with roles.
- A no-override squad shows no workflow override (no false entry).

## Ordering
After TASK-239 (which defines the canonical override path/format). Can run in parallel with the
lint/check tasks. The `_overrides` work is independent of the validation core.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 244 add-subtask "<title>"`; track with `sq task 244 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | workflow as third sq override artifact (scaffold/diff/drift) | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — workflow as third sq override artifact (scaffold/diff/drift)

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Project admin can add custom types and statuses via .squads.toml
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers making the workflow spec the third overridable artifact in the `_overrides/` + `sq override` machinery, alongside templates and roles (kind "workflow"). `sq override scaffold workflow` writes a stamped starter `.overrides/workflow.toml` (the canonical path TASK-239's loader reads) with a `# squads:override-base:<version>` stamp + a commented worked example — not a full copy, since additive-only means the override holds only the team's additions. `diff workflow` shows the team's additions (Δ-mine vs an empty reference), `list`/`scan_overrides` reports its kind/stamp/state, `update` re-stamps, and `check_override_issues` flags drift/unstamped consistent with roles. CLI accepts `workflow` as a scaffold/diff/update target. (US1)
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T09:01:16Z] Elias Python:
  - TASK-244 implementation done — workflow as third sq override artifact (AC #6).
  - Files changed: src/squads/_overrides/_service.py (scaffold_workflow, _workflow_state, _diff_workflow, _check_workflow_override_issues added; scan_overrides/diff_override/update_stamp/_update_one/_update_all extended; check_override_issues extracted workflow block to helper to stay under complexity limit); src/squads/_cli/_override.py (scaffold/diff/update now accept 'workflow' positional OR --workflow flag; scaffold_workflow imported).
  - Tests added to tests/test_workflow_override.py: 26 new tests covering scaffold (creates stamped file, commented example loads clean, refuses clobber, force overwrite), scan_overrides (entry present/absent, drifted when old stamp), diff_override (delta_mine non-empty, absent raises, stamp messages), update_stamp (re-stamps, absent raises, bulk includes), check_override_issues (no stamp warns, old stamp warns stale, current clean, absent clean), and CLI smoke (scaffold positional+flag, refuses clobber, force, list, diff positional+flag, update positional+flag, JSON list no-entry).
  - Gate results: pyright 0 errors/0 warnings, ruff check clean, ruff format clean. pytest tests/test_workflow_override.py tests/test_override_commands.py: 135 passed.
  - F2 flag (REV-246): the override canonical location is .overrides/workflow.toml but FEAT-209 AC#1 and US1 wording still say '.squads.toml'. This wording mismatch is intentional divergence per TASK-239 design, but the feature body and US1 text need updating to say .overrides/workflow.toml for consistency. Flagged for TASK-245 (docs) to reconcile — do NOT edit the feature text now.
  - Design note: drift detection for workflow uses version-stamp-only comparison (stamp != running_version → drifted), not a per-release content hash. Consistent with the task body guidance ('simpler, acceptable for v1'). No manifest extension needed. update_stamp bulk path now also re-stamps workflow.toml. The _check_workflow_override_issues helper was extracted from check_override_issues to stay under the 12-branch complexity limit (ruff C901/PLR0912).
  - @manager: ready for review.
- [2026-06-30T09:19:44Z] Mara Tester:
  - AC#6 verification: scaffold (no-clobber guard works, --force overwrites), diff (shows correct delta-mine), update (re-stamps). sq override list shows workflow with correct state. All three commands pass. NOTICE: AC#6 text says 'drift workflow' but the command is 'sq override update workflow' — drift is not a subcommand. The docs correctly say 'update'; AC wording is a stale planning-era artefact.
<!-- sq:discussion:end -->
