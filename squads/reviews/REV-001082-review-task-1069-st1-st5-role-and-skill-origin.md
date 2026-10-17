---
id: REV-1082
sequence_id: 1082
type: review
title: 'Review TASK-1069 ST1-ST5: role and skill origin'
status: Approved
author: reviewer
refs:
- TASK-1069
subentities:
- local_id: F1
  title: Role catalog lists per-slug declared roles only when they are developers
  status: Verified
  severity: medium
- local_id: F2
  title: Role catalog keeps a row for an archived developer that sq dev list drops
  status: WontFix
  severity: low
- local_id: F3
  title: New test comments name release versions
  status: Verified
  severity: low
- local_id: F4
  title: view add places foreign view tags in a generated body that no verb can remove
  status: Verified
  severity: medium
- local_id: F5
  title: Update gate locks labels, assignee, parent and priority on roles and generated
    skills
  status: Verified
  severity: medium
- local_id: F6
  title: Check and view remedies still offer view disable on classified hosts
  status: Verified
  severity: low
- local_id: F7
  title: Changed tests dropped coverage of still-reachable skew and hint branches
  status: Verified
  severity: low
created_at: '2026-10-16T21:54:03Z'
updated_at: '2026-10-16T22:48:03Z'
---
<!-- sq:body -->
## Scope

The uncommitted TASK-1069 checkpoint, ST1 to ST5, against 0eaadbc5: the origin rule, the pinned `origin` attribute and its check, creation stamps, the surfaces, and the origin contribution to the 0.15 to 0.16 step. ST6 (the refusal) is not built and is out of scope.

## What was driven

Probes ran in a scratch squad with the dev build, and on the same squad with a HEAD build.

- Origin by shape: bundled role; bundled role with a per-slug override (`qa`); a role declared by the catalog; templated developer; declared developer; project role; bundled skills (`squads`, `greeting`, `sq-memory`, `sq-<type>`); a project-type `sq-incident`, then its type dropped; `sq skill add`; `sq import` of a role and a skill. The stored value matched the rule on every shape, and the dropped-type skill kept `system`.
- Creation paths: init, sync seeding after a type is added, sync re-seeding a purged or deleted skill, role activate, dev add, skill add, import create. All of them stamp. `--set origin` and an import `fields` update are refused.
- `sq check` reports a missing value, a list and `System`. Deleting the index and running `sq repair` rebuilds every value verbatim, invalid ones included. `sq sync` is a fixed point and does not backfill.
- JSON compared against HEAD on the same squad. `role list`, `role show` (activated, unactivated bundled, declared, developer), `list -t role|skill` and `skill show` are identical except for the added `origin` and the removed `system`. In `role catalog`, `bundled` became `system`, plus two rows for developers.
- Migration on a copy of the real squad (dev build, `-C`): 10 roles system, 12 skills system, 2 skills project (`releasing-squads`, `launch-dev-host`). `sync` succeeded and `check` was clean. CRLF role and skill files keep CRLF, origin line included. A planning failure writes nothing. A stored value, valid or invalid, is never touched. On the developer fixture: templated developers are system; `legacy-dev`, `old-dev` and `builder` are project.
- ruff and format are clean. The five new test modules plus `tests/meta` pass (524). pyright was not run.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1082 add-finding "…" --severity medium`; track with `sq review 1082 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Role catalog lists per-slug declared roles only when they are developers

<!-- sq:finding:F1:body -->
`sq role catalog` now adds a row for an activated role the catalog document does not declare only when that role is a developer. A project role declared through a per-slug file (`.overrides/roles/<slug>.toml`) gets a row if it holds the `dev` capability and no row if it does not.

Driven in a scratch squad: `builder` (per-slug file, `capabilities = ["dev"]`, activated) is listed with `project`; `analyst` (per-slug file, no capability, activated) is not listed. Both have the same origin and come from the same kind of file. Reading the catalog, an adopter cannot tell why one appears and the other does not. `test_the_catalog_names_no_bundled_origin` pins the gap (`assert not slugs & {"security-analyst", "sandbox-dev"}`).

The docstring also undersells what is listed: it says "plus the squad's templated developers", but declared developers are listed as well.

The implementation adds a second catalog walk: `developer_roles(...)` over `resolve_role_for_item` for every role item, plus a second `load_role_catalog`.

Suggested simplest rule: after the catalog entries, add one row for every activated role item the document does not declare. That covers templated developers, declared developers and per-slug project roles in a single line, with no developer test. If listing only developers is intended, the docstring and the FEAT-976 wording should say so explicitly.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T21:57:05Z] `python-dev` Elias Python:
  - Fixed: sq role catalog lists one row per role item the document does not declare, developer or not; docstring rewritten, the unreachable footer removed, surface and designation tests updated. Falsification: restoring the developers-only condition turns 5 tests red.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Role catalog keeps a row for an archived developer that sq dev list drops

<!-- sq:finding:F2:body -->
The catalog's developer rows come from `list_roles()` without a live-status filter, so a developer the operator archived (`sq role go-dev status Archived`) keeps a catalog row with origin `system`. `sq dev list` drops it in the same squad (driven: after archiving, `dev list` shows only `builder` while `role catalog --json` still lists `go-dev`).

Bundled rows were already listed whatever their status, so this may be intended. If it is, say so in the docstring. If not, filter with `svc.spec.live_statuses(ROSTER_ROLE)`, as `role list`'s Live column does. Finding 1's simpler rule would raise the same question once for every non-declared row.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T22:28:36Z] `reviewer` Paul Reviewer:
  - WontFix per the manager ruling of 2026-10-16: a catalog row exists while the item does, live or retired; sq dev list stays live-only.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — New test comments name release versions

<!-- sq:finding:F3:body -->
New code comments name release versions, which the comment rule forbids (no versions or history in comments):

- `tests/integration/test_skill_migration.py`: "Only the 0.4 to 0.5 runner ran, so the 0.16 origin stamp is still to come."
- `tests/integration/test_memory_skill_migration.py`: "Only the 0.8 to 0.10 runner ran, so the 0.16 origin stamp is still to come."
- `tests/integration/test_migration_corpus.py` `_lift_extra`: "# the stamp the 0.16 step writes"

Describe what the comment means instead, e.g. "only one runner ran, so roles and skills carry no origin yet". Versions used as test data (fixture names, chlog ranges) are fine.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T21:57:07Z] `python-dev` Elias Python:
  - Fixed: the three comments no longer name release versions. Falsification: 0 tests, since no test reads comments; checked with rg for the old text.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — view add places foreign view tags in a generated body that no verb can remove

<!-- sq:finding:F4:body -->
`view add` is not gated, so it can put a *foreign* view tag into a generated role or skill body. Since `view disable` and `body` are now refused, no verb can take that tag out again.

Driven in a scratch squad: `sq role tech-lead view add milestone_rollup` and `sq role tech-lead view add squads_skill` both exit 0 and place the tags in ROLE-3's body. `sq role tech-lead show` then renders the whole squads skill inside the tech lead's definition. `sq check` is silent. `sq role tech-lead view disable milestone_rollup` is refused by the new gate. The only way back is to drop `role_definition` from `[selected]` and hand-edit or clear the body. At HEAD, `view disable` (or a body write) undid it.

I agree that `view add` of the host's **own** classified view must stay open, because every check remedy ends in it. The gap is any other view name. Suggested fix: in `add_view`, refuse when the host is classified and `name != roster_body_view_name(...)`; let `view add <own view>` through. Alternatively, let `view disable` through for names other than the host's classified view. Either keeps one classifier call. Add a row for a foreign name on a role and on a generated skill to the refusal table.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T22:43:52Z] `python-dev` Elias Python:
  - Fixed: view add on a gated role or skill is refused unless the name is the host's own view (gate takes allow_view). Rows added to the refusal table. Falsification: removing the gate call from add_view turns 5 tests red.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Update gate locks labels, assignee, parent and priority on roles and generated skills

<!-- sq:finding:F5:body -->
The update gate refuses every metadata field on a role (except `title`) and on a generated skill, including fields that no role document or playbook can hold: `labels` (add and rm), `assignee`, `parent`/`clear_parent`, `priority`/`clear_priority`, and `author`. For those fields there is no remaining supported path. The error still names `.overrides/roles.toml` as the authoring surface, but that file has no labels or assignee.

Driven against HEAD, the same squad shape: `{"op":"update","target":"ROLE-1","add_labels":["oncall"],"assignee":"manager"}` imports, and `sq list -t role --label oncall` finds the role. With this checkpoint, the same event is refused with the authoring-surface message, and so is an assignee-only update on a project role (ROLE-18).

The ruling refuses *content-changing* writes (definition: description, `--set` definition attributes, body, view edits). Labels and assignee are tracking metadata, like `title`, which is already exempt. Suggested fix: gate only `description` and `set_attributes`/`unset_attributes` (plus `title` for skills), and leave labels, assignee, parent and priority open. If locking them is intended, record that on FEAT-976 and make the message say there is no surface for them.

Checked and fine: every role definition field still has a path. A developer's model, mission and colour work through `.overrides/roles/<slug>.toml` plus `sync`; so do a project role's mission (which becomes its description) and model, and a bundled role's model and mission through a per-slug file. On a generated skill, `model`, `when_to_use` and `allowed_tools` are now unchangeable. No pointer reads them and FEAT-976 keeps system skills non-editable, so this is noted, not counted.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T22:43:54Z] `python-dev` Elias Python:
  - Fixed: the update gate covers description, set/unset attributes, and a skill's title only; labels, assignee, parent, priority and author stay writable. Rows added. Falsification: gating assignee and labels again turns 10 tests red.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Check and view remedies still offer view disable on classified hosts

<!-- sq:finding:F6:body -->
Several `sq check` and view remedies still offer `view disable` on a classified role or generated skill, and that verb is now refused. Each is reachable:

- `_services/_maintenance.py`, `_absent_body_region_issues`: "restore it with `sq role reviewer view add role_definition`, or disable the view with `sq role reviewer view disable role_definition`". Driven by deleting both `sq:body` markers from ROLE-4.
- `_services/_maintenance.py`, the missing-seeded-tag remedy: "restore it with `… view add …`, or disable it with `… view disable …`". Driven by deleting the tag from ROLE-3.
- The duplicate-tag remedy ("collapse to one with `… view add …` or `… view disable …`") and `ConflictingViewStateError` in `_views.py` (settle its state with add or disable) offer the same alternative.

In each case `view add` works, so nobody is stranded, but half of the advice ends in a refusal. Suggested fix: when `roster_body_view_name` names the view, offer only the `add` command. This uses the same classifier, so no second membership test.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T22:43:56Z] `python-dev` Elias Python:
  - Fixed: the missing-region, missing-tag, duplicate-tag and conflicting-state remedies name only view add for a role or skill. New test table over those shapes. Falsification: restoring view disable in the missing-tag remedy turns 1 test red.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Changed tests dropped coverage of still-reachable skew and hint branches

<!-- sq:finding:F7:body -->
Two test edits dropped coverage of branches that are still reachable:

- `test_interrupting_a_dev_roles_set_model_then_editing_elsewhere_refuses_not_reverts` was removed because `--set model` on a developer is now refused. What it guarded is still live. The skew guard treats a developer's `model` as non-exempt, and a real skew on it can still arise from an interrupted `sync` refresh (which writes a developer's model from its per-slug file) or from a hand edit. Re-express it: put the developer's file ahead of the index on `model` (crash the refresh's index commit, or edit the file), then assert that a title update refuses and leaves the file untouched.
- `test_a_roles_name_is_refused_with_the_verb_that_actually_sets_it` now asserts the gate message, so nothing covers the `full_name` clause of `_refusal_hint` any more. That clause is not dead code. With `role_definition` dropped from `[selected]` the gate lets the update through, and `{"op":"update","target":"ROLE-1","fields":{"full_name":"X"}}` prints the `title` / `--name` hint (driven). The `mission` override hint is reachable the same way. Keep a row for each with the view dropped.

The other changed tests look legitimate: description edits became title edits on the skew seams, the roster update seam moved to a project skill, view disable now asserts refusal, and the re-enable setup now writes the file directly.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-16T22:43:58Z] `python-dev` Elias Python:
  - Fixed: the developer-model skew test is rewritten through a hand edit of the file, and the full_name hint is covered with role_definition dropped from [selected]. Falsification: disabling the skew refusal turns 3 tests red; renaming the hint key turns 1 red.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T21:54:57Z] `reviewer` Paul Reviewer:
  - ST1-ST5 reviewed: no correctness defect found. The origin rule, stamps, check, repair round-trip, surfaces and migration contribution behave as specified on every shape driven. F1 (medium) is about catalog scope and simplicity: per-slug declared roles are listed only when they are developers. F2 and F3 are low.
  - @python-dev F1-F3 are for you; @manager recommended verdict: approve once F1 is settled (fix, or record that developers-only is intended).
- [2026-10-16T21:55:28Z] `manager` Catherine Manager:
  - F1: take the simpler rule, one catalog row for every role item the catalog document does not declare, developer or not. F2: follows from that rule (the row exists while the item does, live or retired); sq dev list stays live-only; not a defect. F3: fix.
- [2026-10-16T22:28:37Z] `reviewer` Paul Reviewer:
  - Re-review: F1 and F3 verified (catalog lists analyst as project; no versions left in the comments). F2 WontFix per the manager ruling.
  - ST6: the gate itself holds on every shape driven (system/project roles, generated/project skills, dropped view, dropped type, --force, body/append/update/view disable refused; status, rm, role title open). Every role definition field, a developer model included, still changes through the per-slug file plus sync. Agree view add of the host own view stays open.
  - New: F4 (medium) view add of a foreign view is unremovable; F5 (medium) the gate locks labels/assignee/parent/priority with no surface; F6 (low) remedies still offer view disable; F7 (low) two test edits dropped coverage of reachable branches.
  - @python-dev F4-F7 are yours. @manager recommended verdict: request changes on F4 and F5 (or a recorded ruling that F5 is intended); review stays Requested.
- [2026-10-16T22:29:53Z] `manager` Catherine Manager:
  - F4: refuse view add on a gated role or skill unless the name is the host's own view. F5: gate only what config supplies (description and attributes); labels, assignee, parent and priority stay writable on every role and skill. F6: drop view disable from those remedies. F7: rewrite the removed skew test and restore coverage of the full_name hint.
- [2026-10-16T22:47:43Z] `reviewer` Paul Reviewer:
  - F4-F7 verified on the dev build. F4: view add of a foreign view is refused on a role and a generated skill, the host own view is accepted, and a project skill takes any view. F5: labels (add and rm) and assignee import on a role and a system skill; description, attributes (with --force too) and a skill title are refused; a role title is open. F6: the duplicate, missing-tag and absent-region remedies on a role offer only view add. F7: the rewritten developer-model skew test and the full_name hint test (role_definition dropped) are present and pass.
  - Migration: HEAD and dev migrated output is byte-identical (diff -r) on a fresh copy of the real squad, on v0_15 and on v0_15_developers, and the stamp counts match. Only the changed-file count drops (981 to 957 on the real squad), because a file is no longer counted twice. The real copy syncs, and sq check is clean.
  - Targeted tests (changed files, refusal table, migration and meta): 701 passed. ruff clean. @manager recommend Approved.
<!-- sq:discussion:end -->
