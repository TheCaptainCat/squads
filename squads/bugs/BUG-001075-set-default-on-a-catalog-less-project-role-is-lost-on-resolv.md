---
id: BUG-1075
sequence_id: 1075
type: bug
title: set-default on a catalog-less project role is lost on resolve
status: Open
parent: MILE-1051
author: qa
priority: low
refs:
- REV-1068
created_at: '2026-10-16T20:02:07Z'
updated_at: '2026-10-16T20:02:07Z'
---
<!-- sq:body -->
`sq role <slug> set-default` on a project role (a role defined under `.overrides/roles/<slug>.toml`, with no bundled-catalog entry) stores `is_default: true` in the role item, but resolving the role reads it back as `is_default: false`. The designation is lost: `sq role list` shows no default and the generated CLAUDE.md omits the default-role line. Found by REV-1068 F13; pre-existing, not a regression of the current work.

**Reproduced** on the released sq 0.15.0 and on the dev build (`uv run sq`), in scratch squads.

**Steps**
1. `sq init --roles manager,qa --backend none --default-names`
2. Create `squads/.overrides/roles/lead.toml` and `builder.toml`, each with `full_name`, `title`, `description`, `mission` (no catalog entry).
3. `sq role activate lead` then `sq role activate builder`
4. `sq role lead set-default`
5. `sq role manager status Archived`
6. `sq role list`, `sq role lead show --json`

**Expected:** `lead` is the default role: `Default` column ticked in `sq role list`, `"is_default": true` in `show --json`.

**Actual (0.15.0):**
```
$ sq role lead set-default
  cleared ROLE-1
$ sq role list
Slug     Name               Title        Default  Live
manager  Catherine Manager  manager                   
qa       Mara Tester        QA engineer           ✓   
lead     lead Person        lead                  ✓   
builder  builder Person     builder               ✓   
$ sq role lead show --json   ->  "is_default": false
```
The Default column holds no tick at all after the archive. `ROLE-000003-lead.md` frontmatter holds `is_default: true`, so the stored value is right and the loss happens on resolve.

**Actual (dev build):** `set-default` prints `ROLE-3 is now the default` / `cleared ROLE-1`, then `role list` has no default and `show --json` gives `"is_default": false`.

**Suspected cause (from REV-1068, not verified in code):** the resolution of a role with no catalog base (`role_spec_to_def` over the per-slug file, whose `is_default` defaults to `False`) overrides the stored designation.

**Scope:** frontmatter is the source of truth, so the resolved value should follow the stored `is_default` for catalog-less roles. Needs a regression test that sets the default on a project role and asserts `role list`, `show --json` and the rendered CLAUDE.md default line.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
