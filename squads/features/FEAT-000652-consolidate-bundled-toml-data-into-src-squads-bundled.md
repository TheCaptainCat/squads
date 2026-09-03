---
id: FEAT-652
sequence_id: 652
type: feature
title: Consolidate bundled TOML data into src/squads/_bundled
status: Done
author: tech-lead
created_at: '2026-07-24T13:02:45Z'
updated_at: '2026-07-24T13:29:30Z'
---
<!-- sq:body -->
Consolidate the three scattered bundled TOML data files into a single package folder and drop the `default_` filename prefix.

Today the bundled data lives in three different source packages:

- `src/squads/_workflow/default_workflow.toml`
- `src/squads/_interactions/playbook.toml`
- `src/squads/_roles/roles.toml`

They move to one home:

- `src/squads/_bundled/workflow.toml`
- `src/squads/_bundled/playbook.toml`
- `src/squads/_bundled/roles.toml`

Pure engineering hygiene: the loaded data is byte-identical, only its on-disk home and filenames change. No schema bump, no user-facing behavior change.

## Acceptance
- All three loaders resolve their TOML from `squads._bundled` via `importlib.resources.files`.
- The `default_` prefix is gone (`default_workflow.toml` → `workflow.toml`).
- The built wheel still ships all three TOMLs (`uv build`, confirm the files are present in the wheel; build/skew-canary test stays green).
- Full suite green; strict pyright/ruff clean; import graph stays acyclic.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 652 add-story "As a <role>, I want … so that …"`; track with `sq feature 652 story <n> update --status <Status>`._

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T13:03:13Z] Pierre Chat:
  - Folder name: I picked `_bundled` (over `_data`/`_spec`). Requested for the 0.12.1 release.
<!-- sq:discussion:end -->
