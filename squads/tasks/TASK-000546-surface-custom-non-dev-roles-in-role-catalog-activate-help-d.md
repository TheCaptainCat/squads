---
id: TASK-546
sequence_id: 546
type: task
title: Surface custom non-dev roles in role catalog/activate help + docs
status: Done
parent: FEAT-543
author: tech-lead
assignee: python-dev
created_at: '2026-07-21T20:57:09Z'
updated_at: '2026-07-21T21:30:12Z'
---
<!-- sq:body -->
Maps to FEAT-543 US3 (Surface custom-role discoverability in catalog/help/docs).

## Scope

Make the custom non-dev role path discoverable without reading resolver source.
Today `sq role catalog` and `sq role activate --help` only surface the bundled
roles; nothing tells an adopter a wholly custom role is possible or how to start
one. Add pointers in three places.

1. **`sq role catalog`** (`src/squads/_cli/_role.py::role_catalog`, non-JSON
   path): after the table, print a short hint line that custom non-dev roles are
   supported and point at `sq override scaffold --new <slug>` then `sq role
   activate <slug>`. Leave the `--json` output shape unchanged (it's a machine
   contract — bundled roles only).

2. **`sq role activate --help`** (the `activate_role` docstring/help): mention
   that `<slug>` may be a custom non-dev role defined under
   `.overrides/roles/<slug>.toml`, scaffolded with `sq override scaffold --new
   <slug>`.

3. **Docs.** Update the override/customization docs to reference the new scaffold
   command as the starting point for a brand-new role:
   - `docs/overrides.md` — the "brand-new role slug" section (currently shows a
     hand-authored `.overrides/roles/<slug>.toml`) should lead with `sq override
     scaffold --new <slug>` as the way to generate that starter file.
   - `docs/roles.md` — the activation section should note that a custom non-dev
     role follows the same `sq role activate <slug>` flow after scaffolding.
   Keep docs adopter-facing (no sq item IDs / dev-process refs).

Escape any dynamic strings printed to the console with `_cli._common.e()` per
the Rich-markup convention.

## Acceptance

- `sq role catalog` output contains a pointer to `sq override scaffold --new`
  (and activate) for custom roles; `--json` output is unchanged.
- `sq role activate --help` text mentions the custom non-dev role / scaffold
  path.
- `docs/overrides.md` and `docs/roles.md` point at `sq override scaffold --new
  <slug>` for creating a brand-new role.
- `pyright` + `ruff` clean; `sq check` clean.

## Tests (CLI smoke)

- `tests/cli/test_role_commands_cli.py` (or the role CLI test module): assert
  `sq role catalog` stdout contains the custom-role/scaffold pointer text, and
  that `--json` still emits only the bundled roles (shape unchanged).
- Assert `sq role activate --help` contains the custom-role mention.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 546 add-subtask "<title>"`; track with `sq task 546 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T21:09:56Z] Elias Python:
  - Added discoverability: sq role catalog (non-JSON) now prints a hint pointing at 'sq override scaffold --new <slug>' + 'sq role activate <slug>'; --json shape unchanged. sq role activate --help now mentions the custom non-dev role / .overrides/roles/<slug>.toml path.
  - Docs: docs/overrides.md (scaffold section + 'brand-new role slug' + 'Define a custom role' example) and docs/roles.md (new 'Custom non-dev roles' subsection) now lead with sq override scaffold --new; adopter-facing only, no internal refs.
  - Files: src/squads/_cli/_role.py, docs/overrides.md, docs/roles.md; new tests/cli/test_role_commands_cli.py.
  - Gates: pyright clean (whole src/squads), ruff check + format clean (whole repo), targeted pytest across all FEAT-543 touched files (127 tests) passed, sq check clean.
<!-- sq:discussion:end -->
