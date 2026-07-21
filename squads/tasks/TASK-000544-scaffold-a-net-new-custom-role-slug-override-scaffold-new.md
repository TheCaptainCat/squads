---
id: TASK-544
sequence_id: 544
type: task
title: Scaffold a net-new custom role slug (override scaffold --new)
status: Done
parent: FEAT-543
author: tech-lead
assignee: python-dev
created_at: '2026-07-21T20:57:07Z'
updated_at: '2026-07-21T21:30:11Z'
---
<!-- sq:body -->
Maps to FEAT-543 US1 (Scaffold a net-new custom role slug).

## Scope

Give `sq override scaffold` a net-new-slug path so an adopter can start a wholly
custom non-dev role (e.g. `security-analyst`, `incident-commander`) without
hand-authoring the TOML from resolver source. The engine already supports the
new-slug role end-to-end (`_roles/_resolver.py` new-slug path + `sq role
activate`); this task only adds the scaffold ergonomics.

Add a `--new <slug>` option to `sq override scaffold` (`src/squads/_cli/_override.py`)
that writes `.overrides/roles/<slug>.toml` for a slug **absent from the bundled
catalog**. The existing `--role <slug>` path (copies a bundled role's empty stub)
is unchanged; `--new` is the create-a-brand-new-role path.

Back it with a new service function in `src/squads/_overrides/_service.py`
(e.g. `scaffold_new_role(squad_dir, slug, *, force=False)`) — keep `scaffold_role`
as-is for the bundled path. The scaffolded file must:

- Carry the `# squads:override-base:<version>` stamp as the first line (same
  convention as `scaffold_role`/`scaffold_workflow`, from `squads.__version__`),
  so `sq override list`/`diff`/`update` and `sq check` treat it like any other
  role override.
- Pre-stub the **essential** new-slug fields the resolver requires
  (`_REQUIRED_FOR_NEW` = `full_name`, `title`, `description`, `mission`) as
  active TOML keys with fill-in placeholder values (e.g. `full_name = "TODO: …"`).
  These are the fields `_apply_override` errors on if missing.
- Include the **advanced** fields (`responsibilities`, `agreements`, `model`,
  `color`, `can_spawn`) as **commented-out** lines with a short hint each, so the
  adopter uncomments and fills them by hand. No flag per field — the command
  stays simple (see the separate `can_spawn` scaffold flag decision in TASK-545).
- Refuse to clobber an existing `.overrides/roles/<slug>.toml` without `--force`
  (raise `SquadsError`, matching the other scaffolders).

Print a next-steps hint on success: edit the file, then `sq role activate <slug>`.

Guard rails:
- The `--new` slug must NOT be a bundled catalog slug (that's what `--role` is
  for) — if it collides with `PREDEFINED`, error and point at `--role <slug>`.
- Keep the CLI option surface coherent: `--new` and `--role` are mutually
  exclusive; positional template name / `--workflow` paths are untouched.

## Acceptance

- `sq override scaffold --new <slug>` writes `.overrides/roles/<slug>.toml` with
  the override-base stamp, the four essential fields stubbed as active keys, and
  the advanced fields present as commented lines.
- Running `sq role activate <slug>` on the scaffolded file (after filling the
  stubs) succeeds via the existing resolver path — verified in TASK-545.
- Re-running `sq override scaffold --new <slug>` without `--force` errors and
  does not overwrite; with `--force` it overwrites.
- `--new` on a bundled slug errors and points the user at `--role`.
- `pyright` + `ruff` clean; `sq check` clean.

## Tests (CLAUDE.md conventions — service + CLI smoke)

- Service test (`tests/integration/…` alongside the existing override scaffold
  tests): `scaffold_new_role` writes the file, stamp is the running version,
  essentials are uncommented and advanced fields are commented; clobber refused
  without force, overwritten with force; bundled-slug rejection.
- Parse-back check: the scaffolded TOML (with placeholders filled) parses and
  `resolve_role` builds a valid `RoleDef`.
- CLI smoke (`tests/cli/test_override_commands_cli.py`): `sq override scaffold
  --new <slug>` exits 0 and reports the path; clobber-without-force exits 1.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 544 add-subtask "<title>"`; track with `sq task 544 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T21:05:36Z] Elias Python:
  - Added --new <slug> to sq override scaffold (mutually exclusive w/ --role), backed by scaffold_new_role() in _overrides/_service.py: stamps the override-base line, stubs full_name/title/description/mission as active keys, comments out responsibilities/agreements/model/color/can_spawn, refuses to clobber w/o --force, rejects bundled slugs pointing at --role. Also added --can-spawn (used by TASK-545).
  - Files: src/squads/_overrides/_service.py, src/squads/_cli/_override.py; tests: tests/integration/test_override_scaffold_scan_diff_update_and_check.py (TestScaffoldNewRole), tests/cli/test_override_commands_cli.py.
  - Gates: pyright clean, ruff check + format clean, targeted pytest (override scaffold/CLI + role-merge unit tests) 61 passed, sq check clean.
<!-- sq:discussion:end -->
