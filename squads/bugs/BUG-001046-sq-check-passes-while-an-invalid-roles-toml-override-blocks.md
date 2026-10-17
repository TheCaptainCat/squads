---
id: BUG-1046
sequence_id: 1046
type: bug
title: sq check passes while an invalid roles.toml override blocks commands
status: Fixed
author: qa
priority: high
refs:
- REV-1035
created_at: '2026-10-16T09:14:42Z'
updated_at: '2026-10-16T11:23:10Z'
---
<!-- sq:body -->
`sq check` never loads `.overrides/roles.toml`, so an invalid role catalog override can read "no issues" while every command that needs the catalog refuses.

Reproduction (dev build, fresh scratch squad with the claude backend, `sq init --default-names`):

1. `sq override scaffold roles`, then append a new role (`[[roles]]` slug `sre` with full_name, title, description, mission) and `[bundles]` with `ops = ["manager","sre"]`. The bundled `all` bundle is left alone, so it omits `sre`.
2. `sq check` prints `no issues` (exit 0).
3. `sq role list`, `sq create bug x --author qa -m b` and `sq override diff roles` all fail: `role catalog invalid after merge: 'all' bundle missing roles: ['sre']`.

Condition that makes check report it: add any per-slug override, e.g. `.overrides/roles/qa.toml` containing `model = "opus"`. `sq check` then prints `error corpus: could not scan the corpus: ...roles.toml: role catalog invalid after merge: 'all' bundle missing roles: ['sre']`. That works only by accident: `_check_role_override_resolves` (`src/squads/_overrides/_service.py`) resolves each per-slug file through `resolve_role_with_base`, which loads the catalog. Without such a file nothing loads it. Two issues:

- `_check_roles_catalog_override_issues` checks only the override-base stamp (missing or stale). It never validates the merged catalog, unlike the workflow and playbook overrides, whose loaders run on `open_service` and are reported by check.
- When it is caught, the message is attributed to `corpus` ("could not scan the corpus") rather than to `.overrides/roles.toml`.

Expected: `sq check` reports an invalid merged role catalog as an error on `.overrides/roles.toml` whenever that file exists, with or without per-slug overrides, and the exit code is non-zero.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T11:13:02Z] `python-dev` Elias Python:
  - Fixed on branch worktree-agent-adb998e0d11286bfb, commit 8797c128. check now loads the merged role catalog and reports a refusal as an error on .overrides/roles.toml, with or without per-slug files (per-slug checks are skipped while the catalog is invalid so they do not repeat it as a corpus error).
  - Add-only fixtures in two existing tests used a new role outside the all bundle, which is itself invalid; changed them to a new bundle.
  - Workflow and playbook overrides load on open_service, so they have no such gap.
- [2026-10-16T11:23:10Z] `reviewer` Paul Reviewer:
  - Reviewed in REV-1050: ChangesRequested (F1, F2 medium). @python-dev
<!-- sq:discussion:end -->
