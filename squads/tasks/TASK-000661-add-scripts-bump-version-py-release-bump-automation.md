---
id: TASK-661
sequence_id: 661
type: task
title: Add scripts/bump_version.py release bump automation
status: Done
parent: FEAT-660
author: tech-lead
subentities:
- local_id: ST1
  title: Implement scripts/bump_version.py (pure helpers + orchestration + --dry-run)
  status: Done
- local_id: ST2
  title: Unit-test version-rewrite helpers + --dry-run smoke test
  status: Done
- local_id: ST3
  title: Update releasing-squads (SKILL-508) Prep to call the script
  status: Done
created_at: '2026-07-27T09:43:45Z'
updated_at: '2026-07-27T10:00:29Z'
---
<!-- sq:body -->
Automate the mechanical release version-bump documented in the `releasing-squads`
skill Prep section, as a single command, plus its tests and the runbook update.

## Script: `scripts/bump_version.py`
Invoked `uv run python scripts/bump_version.py X.Y.Z`. Each step prints as it runs and
fails loudly on any error. Steps, in order:

1. Determine the CURRENT version from `pyproject.toml` `[project].version` — this is the
   "prior" version needed for the template-manifest gotcha.
2. Rewrite `pyproject.toml` `version` -> the new version.
3. Rewrite `clients/vscode/package.json` `version` -> the new version (lockstep; the
   Marketplace VSIX publishes off this).
4. `uv sync --all-extras` so `squads.__version__` reflects the new version.
5. Template-manifest gotcha: `git checkout v<prior> -- src/squads/_rendering/templates_manifest.json`
   (restore the prior release's entry byte-identical to its tag), then run
   `scripts/gen_template_manifest.py` in write mode so a clean new-version entry appends.
   If the `v<prior>` tag does not exist yet (e.g. first run), skip the checkout with a
   clear message.
6. Regenerate the version-embedding goldens:
   `UPDATE_GOLDENS=1 <pytest> tests/cli/test_json_output_shape.py -q -n0`
   (re-stamps `override_list` / `override_diff`).
7. `sq sync` to re-stamp this repo's managed files (`.squads.toml` `squads_version`).
8. Print a summary table (each file/step: old -> new).

Constraints:
- MUST NOT edit the CHANGELOG, `git commit`, `git tag`, or push — those stay human.
- Support `--dry-run` that prints the plan without writing anything.
- Keep testable pure helpers (e.g. the version-string rewrite for pyproject/package.json)
  separate from the side-effecting orchestration (git/uv/sq), so helpers unit-test in
  isolation.

Style: match `scripts/gen_template_manifest.py` — `from __future__ import annotations`
is used there and is fine here; `scripts/` is not under the strict `src` gate (confirm).
Keep pyright/ruff clean for whatever the gate covers.

## Tests
- Unit-test the pure version-rewrite helpers: correct field replaced, idempotent, and
  rejects a malformed / version-mismatched file.
- A `--dry-run` smoke test asserting no files change.
- Do NOT attempt to integration-test the full git/uv/sq side effects.

## Runbook (SKILL-508 `releasing-squads`)
Update the Prep section so the manual bump / manifest / goldens / `sq sync` bullets are
replaced by "run `uv run python scripts/bump_version.py X.Y.Z`". Keep the
CHANGELOG-authoring step, the `git fetch --tags` step, and the build steps. Edit the
skill body via `sq skill releasing-squads body --file` or a marker-safe edit; leave
`sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 661 add-subtask "<title>"`; track with `sq task 661 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Implement scripts/bump_version.py (pure helpers + orchestration + --dry-run) |  |
| ST2 | Done |  | Unit-test version-rewrite helpers + --dry-run smoke test |  |
| ST3 | Done |  | Update releasing-squads (SKILL-508) Prep to call the script |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Implement scripts/bump_version.py (pure helpers + orchestration + --dry-run)

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Implemented scripts/bump_version.py: pure rewrite helpers (read_pyproject_version/set_pyproject_version, read_package_json_version/set_package_json_version) plus orchestration steps 1-8, --dry-run (no writes/subprocess), fail-loud via BumpError.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Unit-test version-rewrite helpers + --dry-run smoke test

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Added tests/meta/test_release_version_bump_script.py: rewrite-helper correctness/idempotency/malformed-input tests plus a --dry-run smoke test (subprocess.run and Path.write_text patched to raise, asserts no file changed).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Update releasing-squads (SKILL-508) Prep to call the script

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Replaced the individual bump/manifest/goldens/sq-sync bullets in SKILL-508 Prep with one 'run scripts/bump_version.py X.Y.Z' bullet; kept git fetch --tags, CHANGELOG-authoring, schema/migration note, uv build. Marker-safe body edit; sq check clean.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T09:55:23Z] Hugo Ops:
  - TASK-661 done: scripts/bump_version.py implements the 8-step bump (pure rewrite helpers + orchestration), --dry-run verified side-effect-free, tests added, SKILL-508 Prep updated to call the script.
  - Fast gates clean: pyright, ruff check, ruff format --check, and the new tests/meta suite (11 tests). sq check clean.
- [2026-07-27T09:56:49Z] Hugo Ops:
  - Coordinator correction applied: removed 'from __future__ import annotations' from both scripts/bump_version.py and scripts/gen_template_manifest.py (pre-existing violation of the project's no-future-annotations convention, PEP 649 makes it unneeded on 3.14). Gates re-run clean (pyright/ruff check/ruff format --check + the 11 tests).
<!-- sq:discussion:end -->
