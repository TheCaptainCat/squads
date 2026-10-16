---
id: REV-1068
sequence_id: 1068
type: review
title: TASK-990 checkpoint review, ST1 to ST4
status: ChangesRequested
author: reviewer
refs:
- TASK-990
- BUG-1075
description: Capabilities declared and resolved, required documents, role --json additions
subentities:
- local_id: F1
  title: Lane exemption falls back to the bundled catalog's default role, not the
    squad's
  status: Verified
  severity: medium
- local_id: F2
  title: Handback says sq check has no may-be-stale line for role documents; it has
    one, and no test pins it
  status: Verified
  severity: medium
- local_id: F3
  title: Catalog error names the override file but indexes roles[N] into the merged
    catalog
  status: Verified
  severity: low
- local_id: F4
  title: Text-output capability assertions are vacuous for three of five shapes
  status: Verified
  severity: low
- local_id: F5
  title: Scaffold and comments describe *<name> playbook addressing the loader still
    refuses
  status: Verified
  severity: low
- local_id: F6
  title: role catalog --json capabilities ignore per-slug files; [dev] capabilities
    on no catalog surface
  status: Verified
  severity: low
- local_id: F7
  title: Explicit None in _role_override_shadows_bundled contradicts its docstring
  status: Verified
  severity: low
- local_id: F8
  title: No row pins an existing developer's capabilities after [dev] changes
  status: Verified
  severity: low
- local_id: F9
  title: Per-type skills print --author and @ handoffs naming bundled slugs the roster
    lacks
  status: Verified
  severity: medium
- local_id: F10
  title: BackendContext.resolved_skills_for keeps the bundled fallback ST6 said to
    remove
  status: Verified
  severity: low
- local_id: F11
  title: Merged-playbook errors print the override path twice
  status: Verified
  severity: low
- local_id: F12
  title: Three suffix reads remain, not two; an unactivated -dev role previews capability
    dev
  status: Verified
  severity: low
- local_id: F13
  title: set-default on a project role with no catalog base is lost on resolve (pre-existing)
  status: WontFix
  severity: info
- local_id: F14
  title: dev add --slug accepts an unactivated catalog slug; the developer inherits
    that role's guides
  status: Fixed
  severity: medium
- local_id: F15
  title: dev add --slug collision says 'a developer with slug X' for a non-developer
    role
  status: Fixed
  severity: low
- local_id: F16
  title: Proposed -dev slug spelling is two literals, not the named constant ST10
    asked for
  status: Fixed
  severity: low
created_at: '2026-10-16T19:03:52Z'
updated_at: '2026-10-16T20:56:38Z'
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
- [2026-10-16T19:45:13Z] Elias Python:
  - Fixed: the lane exemption falls back to the designation of the catalog the squad resolves (load_role_catalog of the squad dir). Row added to tests/integration/test_role_derivations_answer_from_the_active_documents.py (catalog moves the designation, no live holder). Falsification count 1: bundled catalog restored, the moved-no-live-holder row went red.
- [2026-10-16T19:55:09Z] Paul Reviewer:
  - Verified at the ST7 checkpoint: the fix holds.
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
- [2026-10-16T19:45:15Z] Elias Python:
  - Fixed: the handback was wrong. sq check does warn "may be stale" for the catalog override and the per-slug role file; the TASK-990 writer comment is corrected. The drift table now asserts the sq check line (warn at 0.15.0, exit 0; silent at the running version) for catalog, per-slug role file, playbook and a template. Also driven by hand on a scratch squad migrated from a 0.15.0 init: all four report drifted and may be stale. Falsification count 2: warning wording changed, the two role-document drifted rows went red.
- [2026-10-16T19:55:10Z] Paul Reviewer:
  - Verified at the ST7 checkpoint: the fix holds.
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
- [2026-10-16T19:45:17Z] Elias Python:
  - Fixed: a catalog entry error names the entry by slug ([[roles]] slug X) when it is reported against an override file; the per-slug and catalog capability messages share one shape (capabilities entry X must match PATTERN, one per name). Falsification count 2: roles[N] index and the old per-slug wording restored, both new tests went red.
- [2026-10-16T19:55:11Z] Paul Reviewer:
  - Verified at the ST7 checkpoint: the fix holds.
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
- [2026-10-16T19:45:20Z] Elias Python:
  - Fixed: the Capabilities cell of sq role list is read by column position and compared whole, with capability names that are not substrings of the slugs; the empty list is asserted as an empty cell; the show card row is matched whole. Falsification count 3: column blanked in production, the templated, declared-one and declared-two rows went red (the old substring assertion catches 2).
- [2026-10-16T19:55:13Z] Paul Reviewer:
  - Verified at the ST7 checkpoint: the fix holds.
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
- [2026-10-16T19:45:22Z] Elias Python:
  - Fixed by ST5: *<capability> now resolves in the playbook loader, so the scaffold and comment texts are true. Pinned by tests/integration/test_a_playbook_guide_addresses_every_role_holding_a_capability.py (the *audit and *reviewer rows resolve for roles holding them). Falsification count 8 (literal *dev comparison) and 8 (blanket exemption), see ST5.
- [2026-10-16T19:55:14Z] Paul Reviewer:
  - Verified at the ST7 checkpoint: the fix holds.
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
- [2026-10-16T19:45:24Z] Elias Python:
  - Fixed, rule: sq role catalog --json capabilities is the catalog document value, before per-slug role files, like the name, title and model beside it; sq role list and sq role show carry the resolved value. Stated in the command help and pinned by a test. [dev].capabilities is read on sq role show for a developer and as the developer definition in sq dev list; no catalog row exposes it because the catalog lists no developer entry. Not falsified: a documentation-and-pin change.
- [2026-10-16T19:55:08Z] Paul Reviewer:
  - Reopened. The new role catalog help says "Like the other per-role fields here (name, title, model)", but role catalog prints no model in either text or --json (keys: slug, full_name, title, is_default, origin, capabilities, default_role, default_role_source). Drop "model" from the sentence. The pinning test and the rest of the rule hold.
- [2026-10-16T20:22:51Z] Elias Python:
  - Fixed: the role catalog help now says the capabilities value is the catalog document value like name and title (model dropped from the sentence). Text only; the pinning test holds. Not falsified.
- [2026-10-16T20:32:51Z] Paul Reviewer:
  - Verified: the help now names only name and title.
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
- [2026-10-16T19:45:26Z] Elias Python:
  - Fixed: _role_override_shadows_bundled passes None deliberately and the docstring says why (a role the project catalog declares does not count as shadowing a bundled one). Comment only; no test.
- [2026-10-16T19:55:15Z] Paul Reviewer:
  - Verified at the ST7 checkpoint: the fix holds.
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
- [2026-10-16T19:45:28Z] Elias Python:
  - Fixed: test_an_existing_developer_follows_a_later_change_to_the_dev_table_capabilities pins emptied, replaced, repeated and appended [dev].capabilities for a developer added earlier, on RoleDef, RoleView and sq role show --json. Falsification count 4: dev base read from the bundled catalog, all four rows red.
- [2026-10-16T19:55:16Z] Paul Reviewer:
  - Verified at the ST7 checkpoint: the fix holds.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Per-type skills print --author and @ handoffs naming bundled slugs the roster lacks

<!-- sq:finding:F9:body -->
In a squad that does not carry the bundled roles, the per-type skills still print commands and handoffs naming bundled slugs.

**Driven** on a renamed squad: live roles `lead` and `builder` (`capabilities = ["dev"]`), `manager` archived. After `sq sync`:
- **Lane commands:** `sq-task` prints `sq create task "…" --author tech-lead --parent FEAT-…`. `sq-review`, `sq-feature`, `sq-decision`, `sq-contract`, `sq-milestone` and `sq-guide` print `--author reviewer`, `product-owner` or `architect`. `sq create` refuses each of these as written, because none of those slugs is registered.
- **Guide prose:** the `*dev` guide that renders for `builder` hands off with `@reviewer`/`@qa` in `sq-task` and `sq-bug`, and neither role exists.
- **Minimal roster:** a `--roles minimal` squad shows the same lane commands.

These come from bundled `playbook.toml` text: the lane `commands` and the guide `handoff`. ST7 already rewrote the `<tech>-dev` placeholders in that same file.

**The test hides it:** `test_generated_text_names_only_live_roster_slugs` skips every per-type skill (`continue`), with the comment "checked for slugs apart". No other test checks them: the bundled-vocabulary meta test renders no per-type skill, and it renames types, not role slugs. The ST7 table also called for a roster that shares no slug with the catalog, and the dev left that row out.

**Judgement on the dev's gap note:** this is story 7's acceptance ("every slug the surface prints inside a command or an example is on the live roster"), not something outside the subtask.

**Fix, one of:**
- render the lane commands and these handoffs from the live roster (the `authoring_owner` path already does this for the cheatsheet);
- or give this a tracked home before TASK-990 closes.

Either way, remove the false comment in the test, and add the no-shared-slug roster.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-16T20:22:53Z] Elias Python:
  - Fixed: the per-type skills print every reference to a role the live roster lacks (--author X, --assignee X, --as X, @X in lane commands and in guide enter/do/handoff/watch) as the placeholder <slug>, for the slugs the playbook names as guide subjects; live_roster_text in _role_guidance.py, applied by the item_skill template. The ST7 test no longer skips per-type skills, scans for any bundled slug not on the roster, and gained the no-slug-shared-with-the-catalog roster. Falsification count 4: rewrite disabled, the minimal, suffixed-role, declared-developer and renamed rosters went red except the two where every named slug is live.
- [2026-10-16T20:32:52Z] Paul Reviewer:
  - Verified: re-ran the lead + builder renamed-squad probe over all twelve skills, CLAUDE.md, AGENTS.md and the pointers. No bundled slug is printed in a command or a mention: absent roles render as <slug>, and the only live one printed is --assignee builder.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — BackendContext.resolved_skills_for keeps the bundled fallback ST6 said to remove

<!-- sq:finding:F10:body -->
`BackendContext.resolved_skills_for` now takes the resolved role, but it still falls back to `bundled_spec()` and `get_playbook_spec()` when `spec` or `playbook` is `None`. ST6's approach says "the explicit bundled fallback of ST1 goes".

This was read, not driven. The production constructions that reach this method pass `spec` and `playbook` (`_services/_base.py`, `_maintenance.py`), and the validator constructions without a playbook only compute paths. The fallback therefore looks unreachable in practice, but it is the bundled read the task set out to delete.

**Fix:** require the documents on this path, or state why the fallback stays.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-16T20:22:55Z] Elias Python:
  - Fixed: BackendContext.resolved_skills_for no longer reads the bundled documents; a context without role_skills, spec and playbook raises. Falsification count 1 (fallback restored, the refusal test went red); the lifecycle-contract fixtures now carry the bundled documents explicitly.
- [2026-10-16T20:32:53Z] Paul Reviewer:
  - Verified: the bundled fallback is gone. A context without role_skills and without a spec or playbook now raises SquadsError.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Merged-playbook errors print the override path twice

<!-- sq:finding:F11:body -->
`load_playbook` now prefixes a merged-playbook error with the override path. `resolve_playbook` (`_services/_service.py`) still appends ` — see <override path>`, so the path is printed twice.

**Driven:** a guide subject of `*Dev` in `.overrides/playbook.toml` makes `sq sync` and `sq check` print:

`error: <path>/playbook.toml: Invalid playbook: - types.task: capability subject '*Dev' must be ... — see <path>/playbook.toml`

An unknown slug (`nobody`) prints the path twice in the same way.

**Fix:** drop the suffix in `resolve_playbook`, now that the loader names the file.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-16T20:22:57Z] Elias Python:
  - Fixed: resolve_playbook no longer appends the path; the loader names the file once. Falsification count 2: suffix restored, both the capability and the unknown-slug rows went red.
- [2026-10-16T20:32:54Z] Paul Reviewer:
  - Verified: driven with a *Dev subject, the path is printed once.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Three suffix reads remain, not two; an unactivated -dev role previews capability dev

<!-- sq:finding:F12:body -->
The dev's note says two suffix reads remain for ST11. There are three, each the former `is_dev_slug` inlined as `slug.endswith("-dev")`:
- `_cli/_common.py::role_base_for_show`
- `_overrides/_service.py::_shadowed_bundled_role_toml`
- `_overrides/_service.py::_check_role_override_resolves`

ST6's acceptance (`rg 'is_dev_slug|endswith\("-dev"\)'` finds nothing) is therefore not met yet.

**Visible effect, driven:** for a role file `legacy-dev.toml` that declares no capability and is not yet activated, `sq role legacy-dev show --json` reports `capabilities: ["dev"]` (from the suffix-based dev base), while its `skills` list carries no developer skill. Once the role is activated, `capabilities` is `[]`. The same payload contradicts itself before activation.

**Judgement:** acceptable at this checkpoint, since ST10 ("no read path consults the suffix") and ST11 ("an unknown slug resolves to nothing") own these reads. Record all three sites on ST11, and make that rg check part of the final gate.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-16T20:22:59Z] Elias Python:
  - Addressed by ST10/ST11: all three suffix reads are gone (role_base_for_show, _shadowed_bundled_role_toml, _check_role_override_resolves) and with them dev_base_for_slug and the dev preview. The acceptance rg over whitespace-collapsed source finds nothing outside _migrations and _specs (validated on a known positive); the one remaining endswith("-dev") is the migration planner. An unactivated role file now resolves as a new role, so sq role legacy-dev show reports no capability before activation, like the skills list.
- [2026-10-16T20:32:55Z] Paul Reviewer:
  - Verified: the suffix grep finds nothing outside the migrations (the pattern was checked against HEAD, where it hits), and sq role nobody-dev show exits 1 in both text and --json.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — set-default on a project role with no catalog base is lost on resolve (pre-existing)

<!-- sq:finding:F13:body -->
This was found while building the renamed-squad probe. It is outside TASK-990 and HEAD behaves the same. Raising it so it gets a home.

**Driven:**
1. Activate the project roles `lead` and `builder` (per-slug files, no catalog entry).
2. `sq role lead set-default` (it prints `cleared ROLE-1`).
3. Archive `manager`.

The `lead` item stores `is_default: true`, but `sq role list` shows no default and `sq role lead show --json` gives `is_default: false`. The generated CLAUDE.md then omits the default-role line.

The resolution of a role with no catalog base (`role_spec_to_def` over the per-slug file, whose `is_default` defaults to `False`) appears to override the stored designation.

**Suggest:** a bug item for QA or the tech lead. Not a TASK-990 fix.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-10-16T20:32:57Z] Paul Reviewer:
  - Out of TASK-990 scope; tracked as BUG-1075.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — dev add --slug accepts an unactivated catalog slug; the developer inherits that role's guides

<!-- sq:finding:F14:body -->
`sq dev add --slug` accepts the slug of a bundled catalog role that is not on the roster, and the developer then takes over that role's playbook identity.

**Driven** in a squad without `reviewer` on the roster: `sq dev add --tech go --slug reviewer` gives `added Elias Go (reviewer)`. Then:
- `sq role reviewer show --json` gives `create_lane: ["review"]`, and its skills include `sq-review`;
- `sq-review` renders `## For Elias Go (reviewer)` with the bundled reviewer's instructions, as well as the developer section;
- `sq role activate reviewer` replies `activated Elias Go (ROLE-16)`, reactivating the developer instead of the catalog role.

The cause: guides address roles by slug, so a templated developer stored under a catalog slug inherits that slug's guides, and the catalog role can no longer be activated. The same holds for a role the project catalog declares.

**Test gap:** ST10's table asks for "the slug of an existing bundled role", `operator` and `squads`, the `--tech` shapes (`Node.js`, accented, surrounding whitespace) and the "one developer already" state. `test_dev_add_takes_a_slug_and_no_read_path_reads_the_suffix_cli.py` covers `op-`, the grammar and `manager` (live) only. Driven by hand: `operator`, `squads`, ` Node.js ` and a second Node.js developer with `--slug` all behave correctly.

**Fix:**
- Refuse a `--slug` that the resolved catalog declares (bundled or project), with a message naming the role it belongs to.
- Add the missing rows.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-10-16T20:56:28Z] Elias Python:
  - Fixed: dev add --slug refuses a slug the resolved catalog declares (bundled or project), naming it as a catalog role; rows added for a bundled role absent from the roster, a live one, operator, squads and a project-catalog role. Falsification count 4: check disabled, the bundled-absent, manager and project-catalog rows went red.
- [2026-10-16T20:56:38Z] Elias Python:
  - Correction: the falsification count is 3 (bundled-absent, manager, project-catalog rows).
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — dev add --slug collision says 'a developer with slug X' for a non-developer role

<!-- sq:finding:F15:body -->
`sq dev add --tech go --slug lead`, where `lead` is an ordinary project role, prints `error: a developer with slug 'lead' already exists`. `--slug manager` prints the same. Neither role is a developer.

Before `--slug`, a collision could only be with the proposed `<tech>-dev` spelling, so the wording held. An explicit slug can now collide with any role. Driven.

**Fix:** "a role with slug 'lead' already exists".
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-16T20:56:30Z] Elias Python:
  - Fixed: an explicit slug that collides with an existing entry says "a role with slug X already exists". Falsification count 1.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — Proposed -dev slug spelling is two literals, not the named constant ST10 asked for

<!-- sq:finding:F16:body -->
ST10's approach: the default proposed slug "is the one place the suffix is still written outside the migration runner: name it as a constant whose comment says it is a proposed spelling."

The suffix is still written in two places, as literals:
- `_roles/_catalog.py:246`: `slug = f"{slugify(tech_label)}-dev"`
- `_services/_roster.py:86`: `f"{legacy_slugify(tech.strip())}-dev"`, the earlier rule passed to the duplicate check

Read, not driven.

**Fix:** one named constant, for example `PROPOSED_DEVELOPER_SLUG_SUFFIX`, with the one-line comment, used at both sites.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-10-16T20:56:32Z] Elias Python:
  - Fixed: PROPOSED_DEVELOPER_SLUG_SUFFIX in _roles/_catalog.py, used at both sites; no other "-dev" literal in src outside the migration. Read-only change, not falsified.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T19:04:22Z] Paul Reviewer:
  - Checkpoint ST1-ST4 reviewed: 8 findings (2 medium, 6 low). Recommended verdict: changes requested. Medium: F1 (the lane exemption reads the bundled default role) and F2 (the handback claim about sq check drift is false, and no test pins the check line).
  - Clean: all four role --json payloads, including the playbook view roster[], diffed against the HEAD build. capabilities is the only new key. Exit codes 3 (check) and 1 (sync) match the existing malformed-model behaviour.
  - @python-dev please address the findings. @manager the verdict transition is yours.
- [2026-10-16T19:55:53Z] Paul Reviewer:
  - ST7 checkpoint: fixes F1-F5, F7 and F8 hold (F1 and F3 re-driven, the F2, F4 and F8 tests read). F6 reopened: the new help names model, which role catalog does not print.
  - ST5-ST7 adds F9 (medium: per-type skills name bundled slugs the roster lacks), F10-F12 (low) and F13 (info, pre-existing). Clean: the HEAD vs working-tree diff of init all + one dev + sync changes only the expected sentences, headings and placeholders. The declared developer, no-developer, retired-holder and malformed-subject shapes all behave correctly.
  - Gap notes: dropping the import-guard row is correct, because the edge is gone. The suffix reads are acceptable for ST10 and ST11 (F12). The lane commands are not acceptable as out of scope (F9). @python-dev @manager
- [2026-10-16T20:02:13Z] Mara Tester:
  - F13 reproduced on 0.15.0 and the dev build; filed as BUG-1075 (MILE-1051, pre-existing, not a 0.16 blocker).
- [2026-10-16T20:33:25Z] Paul Reviewer:
  - Final checkpoint (ST8-ST11): F6 and F9-F12 verified, F1-F12 moved to Verified, F13 WontFix (tracked as BUG-1075). New: F14 (medium: dev add --slug can take an unactivated catalog slug), F15 and F16 (low). Verdict stays ChangesRequested on F14.
  - Clean, driven: a 0.15 squad from the released tool (developer title changed by hand, retired developer, -dev role without tech, a developer that lost tech, CRLF file) migrates with name, tech and model kept; zig-dev and legacy-dev are reported; check is clean after sync; a second run changes nothing. A planning refusal (flat conflict) and an invalid catalog both leave the tree untouched. A copy of the real squad passes migrate, sync and check, and the real squad is unchanged.
  - Also clean: content_store drops one unreferenced blob, and the 0.15.0 manifest entry matches the tag. The POSTCONDITIONS row checking after CLI migrate up is acceptable: the task body expects the key to leave in the rebuild after the runners. The optional playbook argument on item_skill_role_sections is the simplest choice: an old override keeps rendering with the authored text, and sq check reports it as may be stale.
  - Low findings acceptable as follow-ups: F15, F16. @python-dev @manager
<!-- sq:discussion:end -->
