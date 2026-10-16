---
id: REV-1068
sequence_id: 1068
type: review
title: TASK-990 checkpoint review, ST1 to ST4
status: ChangesRequested
author: reviewer
refs:
- TASK-990
description: Capabilities declared and resolved, required documents, role --json additions
subentities:
- local_id: F1
  title: Lane exemption falls back to the bundled catalog's default role, not the
    squad's
  status: Open
  severity: medium
- local_id: F2
  title: Handback says sq check has no may-be-stale line for role documents; it has
    one, and no test pins it
  status: Open
  severity: medium
- local_id: F3
  title: Catalog error names the override file but indexes roles[N] into the merged
    catalog
  status: Open
  severity: low
- local_id: F4
  title: Text-output capability assertions are vacuous for three of five shapes
  status: Open
  severity: low
- local_id: F5
  title: Scaffold and comments describe *<name> playbook addressing the loader still
    refuses
  status: Open
  severity: low
- local_id: F6
  title: role catalog --json capabilities ignore per-slug files; [dev] capabilities
    on no catalog surface
  status: Open
  severity: low
- local_id: F7
  title: Explicit None in _role_override_shadows_bundled contradicts its docstring
  status: Open
  severity: low
- local_id: F8
  title: No row pins an existing developer's capabilities after [dev] changes
  status: Open
  severity: low
created_at: '2026-10-16T19:03:52Z'
updated_at: '2026-10-16T19:05:05Z'
---
<!-- sq:body -->
Review of the uncommitted ST1 to ST4 checkpoint on TASK-990: required documents on the derivation path, `capabilities` declared and resolved onto `RoleDef` and `RoleView`, the developer template read from the resolved catalog, and `capabilities` on the role `--json` and text surfaces.

## What was checked

- The source diff to HEAD and the five new test files. The new test files pass (123 tests, run in isolation).
- Probes ran in scratch squads with the dev build. Declaration shapes covered: a `[[roles]]` entry, a per-slug file over a bundled role and over a templated developer, and the `[dev]` table, both well-formed and malformed (a string, an integer element, uppercase, a leading hyphen, the empty string). Also driven: an existing developer after `[dev].capabilities` changes (to `[]` and to a repeated name), and the splat-append form.
- Every caller of the now-required playbook, spec and default-slug parameters was grepped and read.
- The four `--json` payloads were diffed against the HEAD build on the same squad: `role catalog`, `role list`, `role <slug> show` and the playbook view `roster[]` (`item_skill` and `squads_skill`). In each, the only change is the additive `capabilities` key. Every old key keeps its value and position.
- Exit codes: a malformed `capabilities` value makes `sq check` exit 3 and `sq sync` exit 1. A malformed `[dev].model` gives the same codes, so the new error follows the existing config-error contract.
- No ticket ids or history prose were found in the added lines.

## Verdict

Changes requested. The two medium findings are a bundled-document fallback that ST1 should have removed, and a false statement in the handback, which is the input the tech writer works from.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1068 add-finding "…" --severity medium`; track with `sq review 1068 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Lane exemption falls back to the bundled catalog's default role, not the squad's

<!-- sq:finding:F1:body -->
**Where:** `_services/_base.py`, in the out-of-lane check of create: `is_lane_exempt(author, self._default_role_slug(db) or catalog_default_slug(get_catalog()))`.

`get_catalog()` is the bundled catalog. When no live role holds the default designation, the lane exemption goes to the bundled `is_default` role, even when the squad's own `.overrides/roles.toml` has taken the designation away from that role. ST1 made `catalog_default_slug` take "the catalog it reads", but the only production caller hands it the bundled one. The resolved catalog is `load_role_catalog(self.paths.squad_dir)`.

**Driven** in a scratch squad:
1. An override sets `manager` to `is_default = false` and `tech-lead` to `is_default = true`.
2. `sq role tech-lead status Archived`.
3. `sq create task probe --author manager` gives no advisory. The exemption came from the bundled catalog.
4. Control: `--author architect` prints the out-of-lane advisory.

HEAD behaves the same way, because the fallback used to sit inside `is_lane_exempt`. The checkpoint's purpose is to make bundled reads explicit choices, though, and this one is the wrong choice.

**Fix:**
- Pass the squad's resolved catalog.
- Add a row to the active-documents table: a catalog override that moves the designation, with no live holder.
- Bring the `_default_role_slug` docstring ("falls back to the role catalog's own designation") in line with the code.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Handback says sq check has no may-be-stale line for role documents; it has one, and no test pins it

<!-- sq:finding:F2:body -->
The handback says that `sq check` prints "may be stale" for workflow and playbook overrides only, and has no such line for role documents ("read in the code, driven in the suite"). That is false.

**Driven** with the dev build, overrides stamped `0.15.0`:
- `sq check` warns `.overrides/roles.toml: role catalog override may be stale: bundled roles.toml changed since v0.15.0; run sq override diff roles ...`.
- It also warns `.overrides/roles/architect.toml: role override may be stale ... sq override diff --role architect ...`.
- `sq override list` shows both as `drifted`.

**Suite gap:**
- `tests/integration/test_a_changed_bundled_document_marks_its_stamped_overrides_drifted.py` asserts only `scan_overrides` and `sq override list`. No test pins the `sq check` line.
- ST2's approach asked for the check to report "may be stale" for the catalog and the per-slug file. The task body's drift section asks the same for the catalog, the playbook, a per-slug role file and a template.

**Fix:**
- Correct the statement for the writer (TASK-991) in a comment.
- Add the `sq check` "may be stale" assertion to the drift table: warn at the previous release, silent at the running version, exit 0.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Catalog error names the override file but indexes roles[N] into the merged catalog

<!-- sq:finding:F3:body -->
`_parse_role` now prefixes its error with the override file's path. The `roles[N]` index it prints, however, counts the merged catalog (the bundled roles plus the override's entries), not the entries in that file.

**Driven:**
- An override whose only entry is `[[roles]] slug = "reviewer"` with `capabilities = "dev"` reports `.../.overrides/roles.toml: Invalid role entry roles[3]: ...`.
- A new-slug entry, again the file's only entry, reports `roles[8]`.

The new prefix tells the reader to look in that file, and no `roles[3]` exists there. Name the entry by its slug (for example `[[roles]] slug "reviewer"`), or by its index in the override file.

**Secondary point (low):** the two new capability messages differ in shape.
- The catalog site prints one line per name: `capability 'Dev' must match ...`.
- The per-slug site prints a Python list repr: `capabilities ['Rev', '-x', ''] must each match ...`.

One wording would read better.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Text-output capability assertions are vacuous for three of five shapes

<!-- sq:finding:F4:body -->
**Where:** `tests/cli/test_capabilities_are_readable_on_every_role_surface.py::test_the_text_outputs_show_capabilities` checks the `sq role list` row with `assert all(name in row for name in expected)`. The row starts with the slug, so the assertion cannot fail for three of the five shapes:
- **templated-developer:** `dev` is a substring of `rust-dev`.
- **declared-one:** `audit` is a substring of `auditor`.
- **bundled:** `expected` is `[]`, so `all()` is vacuously true. Nothing checks that the cell is empty.

Only `declared-two` and `definition-gone` exercise the Capabilities column. This was read, not driven: the substring relation is plain from the fixture.

**Fix:** assert the cell itself, either by splitting the row on the column boundaries or by checking `", ".join(expected)` in the column's own position. Use capability names that are not substrings of the slugs.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Scaffold and comments describe *<name> playbook addressing the loader still refuses

<!-- sq:finding:F5:body -->
The checkpoint ships three texts that describe the playbook addressing a capability as `*<name>`, a feature that does not exist until ST5:
- The new-role scaffold in `_overrides/_service.py`: `# capabilities = ["reviewer"]  # names a playbook guide can address as *reviewer`.
- The `RoleSpec.capabilities` comment in `_roles/_models.py`: "names a playbook guide addresses as `*<name>`".
- The `CAPABILITY_NAME_PATTERN` comment: "A playbook subject `*<name>` uses the same pattern".

**Driven:** a playbook override with a guide subject of `*reviewer` makes `sq sync` fail with `role slug '*reviewer' not in role catalog`. An adopter who follows the scaffold comment today gets a refused playbook.

This is harmless only if ST5 lands in the same release. If the checkpoint is committed alone, either word these as present truth (a capability is a name a role holds) or make sure ST5 lands before any release cut.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — role catalog --json capabilities ignore per-slug files; [dev] capabilities on no catalog surface

<!-- sq:finding:F6:body -->
`sq role catalog --json` takes `capabilities` from the catalog document (`load_role_catalog(...).roles`). `sq role list` and `sq role <slug> show` take it from the resolved role.

**Driven:**
- With `.overrides/roles/reviewer.toml` declaring `capabilities = ["rev"]`: `role catalog` gives `[]`, while `role list` and `role reviewer show` give `["rev"]`.
- The `[dev].capabilities` value, the one capability the bundled documents declare, appears on no catalog surface, because the catalog lists no developer entry.

The catalog's `full_name`, `title` and other fields already behave this way with per-slug files, so this follows an existing semantic. The new key, however, is the one a tool will read to learn "who holds capability X", so the gap matters more here.

**Decide one of:**
- state in the `role catalog` help and the writer's notes that its values are the catalog document's, before per-slug files;
- or resolve the row.

Either way, consider exposing `[dev].capabilities` somewhere a tool can read it.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Explicit None in _role_override_shadows_bundled contradicts its docstring

<!-- sq:finding:F7:body -->
**Where:** `_overrides/_service.py::_role_override_shadows_bundled` now calls `role_base_from_item(item, None)`. Its docstring says it resolves "the exact way `_check_role_override_resolves` resolves a base", and that function passes `squad_dir`.

The `None` keeps HEAD's behaviour, and it is probably intended: "shadows a bundled role" should not count a role from the project catalog. As written, though, the explicit `None` contradicts its own docstring, and a reader on ST6 may "fix" it.

This was read, not driven.

**Fix:** a short comment on why the bundled catalog is meant here, and a docstring that matches the code.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — No row pins an existing developer's capabilities after [dev] changes

<!-- sq:finding:F8:body -->
In the declaration-site table, the `catalog-dev-table` site writes `.overrides/roles.toml` before `sq dev add` (`after=False`). The ST3 table pins colour and model for an existing developer, but not capabilities. No row pins that an existing developer's capabilities follow a later change to `[dev].capabilities`.

**Driven** in a scratch squad: with `rust-dev` already added, setting `[dev] capabilities = []` makes `role rust-dev show --json` give `[]`. Setting `["builder", "builder"]` makes it give `["builder"]`. The behaviour is right. It is just not pinned, and ST6 starts deciding from this value.

**Fix:** add an `after=True` variant of the `[dev]` site, or a capabilities column in the ST3 existing-developer table.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T19:04:22Z] Paul Reviewer:
  - Checkpoint ST1-ST4 reviewed: 8 findings (2 medium, 6 low). Recommended verdict: changes requested. Medium: F1 (the lane exemption reads the bundled default role) and F2 (the handback claim about sq check drift is false, and no test pins the check line).
  - Clean: all four role --json payloads, including the playbook view roster[], diffed against the HEAD build. capabilities is the only new key. Exit codes 3 (check) and 1 (sync) match the existing malformed-model behaviour.
  - @python-dev please address the findings. @manager the verdict transition is yours.
<!-- sq:discussion:end -->
