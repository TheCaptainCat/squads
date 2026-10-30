---
id: BUG-1045
sequence_id: 1045
type: bug
title: sq init --roles ignores bundles and roles in .overrides/roles.toml
status: Verified
author: qa
refs:
- REV-1035
- MILE-1051:targets
created_at: '2026-10-16T09:14:41Z'
updated_at: '2026-10-26T06:46:26Z'
priority: low
---
<!-- sq:body -->
`sq init --roles <name>` resolves its bundle and slugs against the bundled role catalog only, so a bundle or role declared in the project's `.overrides/roles.toml` is refused.

Reachability: a plain `sq init` runs before any override exists, so the normal path cannot hit it. It is reachable when `.overrides/roles.toml` is already present and init runs again: `sq init --force` on that project, or a checkout where the override is committed and `.squads.toml` is not.

Reproduction (dev build, scratch squad):

1. `sq init --default-names`, then `sq override scaffold roles`.
2. Append to `squads/.overrides/roles.toml` a `[[roles]]` entry (slug `sre`, full_name, title, description, mission) and `[bundles]` with `all` extended by `sre` plus `ops = ["manager","sre"]`. `sq override diff roles` and `sq check` accept it.
3. `sq init --force --default-names --no-claude --roles ops` prints `error: no predefined role 'ops' (known: manager, architect, ... tech-writer)`.
4. `sq init --force --default-names --no-claude --roles manager,sre` prints `error: no predefined role 'sre' (known: ...)`.

Cause: `resolve_roles` / `role_by_slug` in `src/squads/_roles/_catalog.py` read the module-level `BUNDLES` / `_BY_SLUG` built from the bundled catalog; the squad-aware resolver in `_roles/_resolver.py` is not used.

Expected: with `.overrides/roles.toml` present, `--roles` accepts its bundles and role slugs, as `sq role` and `sq sync` already do. Otherwise the error should say that project overrides are not consulted by init.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T06:45:42Z] `qa` Mara Tester:
  - Verified on the dev build (release/0.17, uv run sq), scratch squads under /tmp.
    - Repro: init --roles minimal, `override scaffold roles`, append `[[roles]] sre` + `[bundles] all=[$(*self),"sre"]`, `ops=[manager,sre]`; `override diff roles` and `sq check` accept it.
    - `init --force --default-names --no-claude --roles ops` -> roles: manager, sre. `--roles manager,sre` -> same. `--roles all` -> all eight plus sre. rc 0.
    - Neighbours: `--roles sre,nonexist` -> `error: no bundle or role 'nonexist' (bundles: all, core, minimal, ops; roles: ... sre)`, rc 1. No override: `--roles sre` -> `no bundle or role 'sre' (bundles: all, core, minimal; ...)`, rc 1. Malformed override (`[[roles`) -> `error: malformed role catalog override .../roles.toml: Expected ']]' ...`, rc 1. Fresh checkout (override committed, no .squads.toml): `init --roles ops` -> roles: manager, sre.
    Fix held (TASK-1137 ST3). Moving to Verified.
<!-- sq:discussion:end -->
