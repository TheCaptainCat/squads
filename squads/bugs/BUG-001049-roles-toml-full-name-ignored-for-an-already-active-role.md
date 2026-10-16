---
id: BUG-1049
sequence_id: 1049
type: bug
title: roles.toml full_name ignored for an already-active role
status: Open
author: qa
priority: medium
refs:
- REV-1047
description: Catalog-document full_name renames only the catalog and new activations,
  not a live role; per-slug file does.
created_at: '2026-10-16T11:19:07Z'
updated_at: '2026-10-16T11:25:53Z'
---
<!-- sq:body -->
## Repro (dev build, scratch squad)

```
git init a && sq -C a init --roles architect,qa --default-names --backend claude_code
sq -C a override scaffold roles
# append to a/squads/.overrides/roles.toml:
#   [[roles]] slug="architect" full_name="Rita Catalog" title="Chief Architect" mission="CATALOG MISSION"
#   [[roles]] slug="reviewer"  full_name="Newt Reviewer" title="Chief Reviewer" mission="REV MISSION"
sq -C a sync
sq -C a role catalog        # architect: Rita Catalog / Chief Architect   (renamed)
sq -C a role architect show # header "Robert Architect"; title "Chief Architect"; body "CATALOG MISSION"
sq -C a check               # no issues
sq -C a role activate reviewer ; sq -C a role reviewer show   # "Newt Reviewer" (renamed)
```

Putting `full_name = "Pat Perslug"` in `.overrides/roles/architect.toml` and running `sq sync` renames the active architect; `sq check` stays clean.

## Findings (driven)

- Already-active role: `full_name` from roles.toml is ignored. `title`, `mission` from the same roles.toml entry do reach the active role.
- Newly activated role: roles.toml `full_name` is honoured (activate reads the merged catalog).
- Per-slug `full_name` wins and renames an active role.
- Nothing warns: `sq check` is clean and `sq sync` prints no notice.
- `is_default`: same carry-over in code, not driven (roles.toml `is_default` on a non-default role fails validation with two defaults, since the bundled default cannot be unset there).

## Cause (read)

`role_base_from_item` (`src/squads/_roles/_resolver.py`) builds the merge base from the catalog but swaps in the item's stored `title` as `full_name` (and `extra.is_default`), as the operator's lasting answer for `sq role activate --name`. The per-slug file merges over that base so it wins; the roles.toml layer is below the stored name. But `sq init --default-names` stores the bundled name, so an unchosen default is indistinguishable from an operator's choice and is frozen too.

## Intent

ADR-777 section 3 sets precedence "bundled base, then the catalog document, then the per-slug file" and says `[[roles]]` is for a project that states its catalog in one document. It does not carve out `full_name`. The `role_base_from_item` docstring does carve it out, for `--name`. So the code contradicts the stated precedence for an unchosen name; only a name chosen with `--name` is plausibly meant to be sticky.

## Expected

Either roles.toml `full_name` renames an active role whose stored name was never explicitly chosen (for example, the stored title equals the previous catalog name), or overrides.md, stability.md and the roles.toml scaffold comment state that an active role keeps its stored name unless a per-slug file sets it, and `sq check`/`sq sync` should say so when roles.toml `full_name` differs from an active role's name. The decision between the two belongs to the architect.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T11:25:53Z] Catherine Manager:
  - When fixed, re-check docs/overrides.md (roles.toml precedence paragraph ~257-259, 'Which name wins' ~2092-2110) and docs/stability.md:158 (REV-1047 F5).
<!-- sq:discussion:end -->
