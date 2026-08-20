---
id: FEAT-715
sequence_id: 715
type: feature
title: Consolidate bundled specs under squads/_specs/, drop default_ prefix
status: Done
parent: EPIC-538
author: product-owner
refs:
- EPIC-538
subentities:
- local_id: US1
  title: As a maintainer, I want the three bundled specs relocated to squads/_specs/
    mirroring .overrides/'s layout
  status: Done
- local_id: US2
  title: As a maintainer, I want every loader/migration/guard reference updated to
    the new path with zero behaviour change
  status: Done
created_at: '2026-07-31T13:04:01Z'
updated_at: '2026-07-31T16:22:56Z'
---
<!-- sq:body -->
## Capability

Relocate the three bundled spec TOMLs (workflow, roles, playbook — currently `src/squads/_bundled/workflow.toml`, `roles.toml`, `playbook.toml`) into `squads/_specs/`, mirroring the `.overrides/` directory's own layout, so the bundled-vs-override pairing reads symmetrically: `squads/_specs/workflow.toml` next to `.overrides/workflow.toml`, and likewise for `roles.toml`/`playbook.toml`.

## Current state — most of this outcome is already done

The three files are already named without a `default_` prefix (`workflow.toml`, `roles.toml`, `playbook.toml`) and already live together in one directory. What remains is narrower than the epic bullet's original framing suggested: **only the directory itself moves**, from `src/squads/_bundled/` to `squads/_specs/` (the package-relative path the three loaders resolve against — confirm the exact final path with whoever picks this up; the point is mirroring `.overrides/`'s own layout, not a specific literal).

## Scope

- Move the three files; update every loader that resolves them by path: `_workflow/_loader.py`, `_roles/_loader.py`, `_interactions/_loader.py` (a 4th consumer once the playbook loader from the playbook-override feature lands — coordinate so this move doesn't collide with that feature's new loader).
- Update every other reference to the old path: `_migrations/_v0_4_to_v0_5.py` and `_v0_8_to_v0_10.py` (these must keep reading the file that existed *at their pinned schema version* — confirm the migration runners' carve-out for frozen literals, per ADR-696 §2, is not disturbed by a path move that happens after the version they migrate from), `_services/_maintenance.py`, `_services/_service.py`, `_backends/_claude_code/_backend.py`, `_overrides/_service.py`.
- Update the `tests/meta` guard ADR-696 introduces (no bundled roster status name as a literal in `src/squads/` outside the bundled workflow file and `_migrations/`) to point at the new path.
- Update the package-data manifest (`pyproject.toml` / build config) so the relocated directory still ships in the wheel — verified in the build, per this repo's existing package-data test coverage.
- Update any doc/comment that names the old path.

## Acceptance

- `squads/_specs/workflow.toml`, `roles.toml`, `playbook.toml` exist; `src/squads/_bundled/` is gone, not left as a stale duplicate.
- All three loaders resolve the new location; `uv run pytest` is green with no path-not-found regressions.
- `uv build` still ships the three files as package data (verified the same way the existing package-data build check verifies it).
- With no override present, behaviour is byte-identical to today — this is a pure relocation, no spec content changes.
- `sq check` clean.

## Constraints

- Pure relocation/rename — no change to the *content* of any of the three bundled specs, and no change to override-resolution semantics (that is FEAT-712/713/714's scope, not this one's).
- Byte-identical default behaviour with no override present.
- Coordinate sequencing with the playbook-override feature (FEAT-714) if both are in flight at once — that feature introduces the fourth loader this one's path move must also cover.

## Dependencies

None blocking — this is an independent relocation and can land in any order relative to FEAT-712/713/714, though it touches the same loader modules those features touch, so avoid landing it concurrently with any of them against the same files.

## References

EPIC-538 outcome list ("The three bundled TOMLs consolidated under squads/_specs/ and name-normalized … mirroring the .overrides/ layout"). The name-normalization half of this outcome (dropping `default_`) is already in place on disk; only the directory relocation remains.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 715 add-story "As a <role>, I want … so that …"`; track with `sq feature 715 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | As a maintainer, I want the three bundled specs relocated to squads/_specs/ mirroring .overrides/'s layout |
| US2 | Done |  | As a maintainer, I want every loader/migration/guard reference updated to the new path with zero behaviour change |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a maintainer, I want the three bundled specs relocated to squads/_specs/ mirroring .overrides/'s layout

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Move workflow.toml/roles.toml/playbook.toml from src/squads/_bundled/ to squads/_specs/ (final path confirmed by whoever picks this up). No content change to any of the three files.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a maintainer, I want every loader/migration/guard reference updated to the new path with zero behaviour change

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Update the three loaders (_workflow/_loader.py, _roles/_loader.py, _interactions/_loader.py), the migration runners' frozen-literal carve-out, the tests/meta guard's path exemption, package-data manifest, and any doc/comment naming the old path. uv run pytest and uv build both green; sq check clean.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T13:42:47Z] Olivia Lead:
  - Broken down as one task: TASK-721 (medium, python-dev). Three subtasks: ST1 git-mv the three TOMLs to src/squads/_specs/ and repoint the three loaders (US1); ST2 repoint both tests/meta guards and prove uv build still ships the files, with each guard falsified after the exemption path is edited (US2); ST3 sweep stale mentions of the old path (US2).
  - One task: pure relocation, one owner, one increment. Pinned the target as the package src/squads/_specs/ (importlib package squads._specs) since the body left the literal open — squads/ at the repo root is the squad data dir, so the mirror of .overrides/ has to be inside the package the loaders resolve against.
  - Scope correction the dev is briefed to confirm by grep rather than trust: the only path references in src/ are the three loaders' importlib.resources.files("squads._bundled") calls. The migration runners, _services/_maintenance.py, _services/_service.py, _backends/_claude_code/_backend.py and _overrides/_service.py match only on function names (seed_bundled_skills, bundled_template_content, _required_markers_from_bundled), not the package path — so the migrations' frozen-literal carve-out is not disturbed by this move at all. The real extra sites are the two tests/meta guards, which the body's scope list has.
  - @manager sequencing: this shares files with the engine and both loader features. Cleanest slot is straight after the engine task lands and before TASK-718 starts — then 718 and 720 are written against the final path and nobody sweeps twice. The engine task's own tests read the bundled TOMLs by path, so this must not land while that is in flight.
- [2026-07-31T15:31:12Z] Pierre Chat:
  - Low value — the move buys directory symmetry and nothing functional. Kept because it's a declared epic outcome, not because it earns priority.
<!-- sq:discussion:end -->
