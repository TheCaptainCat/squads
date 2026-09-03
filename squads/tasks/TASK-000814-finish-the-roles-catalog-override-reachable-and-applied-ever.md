---
id: TASK-814
sequence_id: 814
type: task
title: 'Finish the roles catalog override: reachable and applied everywhere'
status: Done
parent: FEAT-791
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-777:implements
- TASK-800
- TASK-799
description: Wire the roles catalog document into the override CLI verbs and make
  it apply to an already-activated role, so the kind is reachable by a human and behaves
  the same before and after activation
subentities:
- local_id: ST1
  title: Wire the roles kind into the override CLI verbs
  status: Done
  story: US3
- local_id: ST2
  title: Apply the catalog document to an activated role
  status: Done
  story: US3
- local_id: ST3
  title: sq role catalog lists project-declared roles
  status: Done
  story: US3
created_at: '2026-08-25T21:05:19Z'
updated_at: '2026-08-25T23:40:02Z'
---
<!-- sq:body -->
## Scope

ADR-777 §3 — FEAT-791 US3. The roles catalog document (`.overrides/roles.toml`) resolves through
the shared merge engine and carries a scaffold, a state classifier and both diff deltas at the
service layer. It is still not reachable from the CLI, and it still does not apply to a role that
has been activated. Both are finished here.

**FEAT-791's own acceptance is not met until both land.** The feature promises one override
contract for every bundled spec document; a kind a human cannot invoke and that silently stops
applying after activation is not that contract, it is a half-wired kind that happens to pass
every gate. Nobody should read the catalog document's service-layer delivery as the capability
being shipped.

## Why one task and not two

They are one surface — making the kind real for the person using it — and neither half is worth
shipping alone. CLI verbs that scaffold a document which then does nothing for any activated role
is worse than no verbs, because it invites an adopter to write an override and trust it. A
resolver fix for a document a human has no command to create is unreachable. Same owner, same
review, same increment.

The reason they were split during the original delivery no longer holds: the developer stayed out
of `_cli/` because another dev owned that directory concurrently, and out of the resolver because
the threading touches `_cli/_role.py` and `_services/_maintenance.py`. Both constraints are gone.
File collision is a scheduling fact, not a scoping principle.

## Gap 1 — the CLI cannot reach the kind

Driven on a scratch squad:

    sq override scaffold roles  -> error: no bundled template 'roles' — use a path like 'items/task.md.j2'
    sq override diff roles      -> error: no template override for 'roles' (run `sq override scaffold roles` first)
    sq override update roles    -> error: no override found for 'roles' (kind='template'). ...

Every one of them falls through to the template branch, so the errors are not merely unhelpful,
they name the wrong kind and recommend a command that does not work either. `sq override list`
**does** already show the kind, because it goes through the service scan — but the only way to
reach that state is to write the file by hand, which is how it had to be driven.

The three verbs each have a workflow branch and a playbook branch and no roles branch:
`_cli/_override.py:130-149` (`scaffold`), `:281-287` (`diff`), `:385-391` (`update`). The
diff label helper `_diff_label` (`:322-330`) has arms for template, role and playbook and none for
this kind. Three help strings still enumerate the reachable kinds as "Template name, role slug,
'workflow', or 'playbook'" (`:53`, `:244`, `:359`).

**The flag name is a trap worth deciding deliberately.** `--role <slug>` already means the
per-slug override. A `--roles` flag for the catalog document differs from it by one character and
selects a different kind. Either give the document a positional name only, or pick a flag that
cannot be misread as a typo for the other — and whichever is chosen, the help text has to make the
two kinds distinguishable at a glance, because they will sit in the same `--help` output.

## Gap 2 — the document does not apply to an activated role

`role_base_from_item` (`_roles/_resolver.py:364-410`) resolves a bundled role's base through
`_PREDEFINED_BY_SLUG.get(slug)` (`:394`) — the bundled catalog alone. `resolve_role_with_base`
resolves it through `_predefined_for_slug(slug, squad_dir)` (`:317`), which merges the catalog
document. And a supplied base **wins**: `effective_base = base if base is not None else predefined`
(`:318`). So on every path that has a live item in hand, the merged value is computed and then
discarded.

Driven in-process on a squad carrying a catalog document that renames the reviewer's title and
declares a new `security-analyst` slug:

| Path | Result |
| --- | --- |
| `resolve_role("reviewer", squad_dir)` — no live item | the document's title |
| `role_base_from_item(item)` for the same slug | the bundled title |
| `resolve_role_with_base("reviewer", squad_dir, base=…)` | the bundled title |
| `sq role security-analyst show` — declared, never activated | the document's title |
| `sq role reviewer show` — activated | the bundled title |

**In a real squad this makes the capability inert for its main case.** `sq init` activates the
bundled roles, so every role a team actually uses is on the activated path — and the document
reaches none of them. It applies only to slugs nobody has activated yet. The same override
applying before activation and silently not after is exactly the shape that reads as a bug.

The three surfaces that build their base this way, all with `squad_dir` obtainable at the site:
`_cli/_role.py:219` (`sq role <slug> show`), `_services/_maintenance.py:744`
(`_refresh_catalog_extra`, behind `sq sync`), and `_overrides/_service.py:1283`
(`_check_role_override_resolves`, behind `sq check` — which already takes `squad_dir` as a
parameter).

Note what must **not** change: `role_base_from_item`'s contract is that the item is authoritative
for exactly the operator-settable fields (`full_name` for a bundled role) and everything else
comes from the current catalog, fresh, every call. Widening the catalog it reads from bundled to
bundled-plus-document is that contract working as documented, not a relaxation of it.

## Gap 3 — `sq role catalog` lists the bundled tuple directly

Found while verifying the other two, and the same defect one layer over: `sq role catalog`
iterates the module-level `PREDEFINED` tuple (`_cli/_role.py:82` and `:90`, built at import in
`_roles/_catalog.py:202`), so it never consults the document at all — no item, no base, no
`squad_dir`.

Driven, on the same squad: the declared `security-analyst` slug does not appear in
`sq role catalog --json`, and the reviewer keeps its bundled title there — while
`sq role security-analyst show` resolves the new role and `project_role_slugs` already counts it.
So a project can declare a role the tool will resolve and activate, and the command whose job is
to list what can be activated does not mention it.

This is in scope because it is the same question — does a project's declared catalog reach the
surfaces that read the catalog — and because leaving it makes the other two fixes look arbitrary.

## Is this general or roles-specific?

**Roles-specific, and structurally so.** Templates, the workflow spec and the playbook are
resolved fresh through their loaders on every read; none of them has a supplied-base concept and
none materialises a per-instance copy that can go stale. Roles are the only kind whose subject is
*activated* — written out as a live roster item that then carries catalog-merged fields — so they
are the only kind with a before-activation and an after-activation path to disagree.

Narrower still: it is not the roles override kind in general. The per-slug
`.overrides/roles/<slug>.toml` layer is applied at `_roles/_resolver.py:319-324`, **outside** the
`base is None` branch, so it reaches both paths correctly. Only the catalog-document layer is
bypassed, because it was placed inside `_predefined_for_slug`, which is consulted only when no
base is supplied.

(A template override also has a "materialised once" flavour — an item file rendered from it is
never re-rendered — but that is the standing contract that an authored body is never rewritten,
and the override still applies to every subsequent render. The catalog document applies to no
activated role at all. Different things.)

## Traps

- **Do not fix Gap 2 by making the item authoritative.** The item supplies operator-settable
  fields only; the fix is which catalog the rest is read from, not how much of the item is
  trusted.
- **The per-slug layer must keep winning.** Precedence is bundled → catalog document → per-slug
  file, and the per-slug file is applied by the caller of `_predefined_for_slug`, not inside it.
  A fix that merges the document into the base must not disturb that order.
- **The resolver stays stateless.** It reads from disk on every call by its own stated stance; do
  not add a cache to avoid re-reading the document.
- **A squad with no `.overrides/roles.toml` must behave exactly as it does today**, on every one
  of these paths — that is the regression surface for the whole task.
- **`sq check`'s role-override resolve already receives `squad_dir`** and needs no new threading;
  only the other two call sites do.
- **No bundled template is touched**, so no manifest regeneration, and `scripts/bump_version.py`
  must not be run.

## Acceptance

- `sq override scaffold`, `sq override diff` and `sq override update` each reach the roles catalog
  document, and `sq override list` still shows it with a state.
- A scaffolded catalog document carries a stamp, diffs with both deltas, and re-stamps — driven
  through the CLI end to end, without writing the file by hand.
- No verb for this kind falls through to the template branch, and no error message for it names
  `kind='template'`.
- The help text distinguishes the per-slug role override from the catalog document so the two
  cannot be confused in one `--help` output.
- A catalog document that changes a bundled role's field reaches that role **after activation**:
  `sq role <slug> show`, `sq sync`'s catalog refresh and `sq check`'s role-override resolve all
  report the document's value.
- The same document reaching a not-yet-activated slug is unchanged from today.
- Precedence still runs bundled → catalog document → per-slug file, proven with all three layers
  naming the same field.
- `sq role catalog` lists a role the document declares, and shows the document's values for a
  bundled role it overrides.
- A squad with no `.overrides/roles.toml` behaves identically to today on every path above.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 814 add-subtask "<title>"`; track with `sq task 814 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Wire the roles kind into the override CLI verbs

<!-- sq:subtask:ST1:body -->
Wire the roles catalog document into `sq override scaffold`, `sq override diff` and
`sq override update`, so the service-layer capability is reachable by a human.

Driven today, on a scratch squad:

    sq override scaffold roles  -> error: no bundled template 'roles' — use a path like 'items/task.md.j2'
    sq override diff roles      -> error: no template override for 'roles' (run `sq override scaffold roles` first)
    sq override update roles    -> error: no override found for 'roles' (kind='template'). ...

All three fall through to the template branch, so each names the wrong kind and points at a
command that does not work either. `sq override list` already shows the kind — it goes through
the service scan and is kind-agnostic — but reaching that state requires writing the file by hand.

The sites, each of which already has a workflow arm and a playbook arm to mirror:

- `_cli/_override.py:130-149` — `scaffold`, which calls the existing `scaffold_roles_catalog`.
- `:281-287` — `diff`, dispatching `diff_override(..., kind="roles")`.
- `:385-391` — `update`, dispatching `update_stamp(..., kind="roles")`.
- `:322-330` — `_diff_label`, which has arms for template, role and playbook and none for this
  kind, so a roles result prints the fallback label.
- `:53`, `:244`, `:359` — three help strings still enumerating the reachable kinds as "Template
  name, role slug, 'workflow', or 'playbook'".

**Decide the flag name deliberately.** `--role <slug>` already selects the per-slug override. A
`--roles` flag differs from it by one character and means a different kind, and the two will sit
in the same `--help` output. Either give the document a positional name only, or choose a flag
that cannot be misread as a typo for the other — and make the help text distinguish the two kinds
at a glance either way.

Cover it by **driving the verbs**, not by calling the service functions: an integration test that
scaffolds through the CLI, diffs, edits, diffs again and updates. The service layer already has
its own lifecycle test; what was missing is exactly the layer that turned out to be unwired.

Done when each verb reaches the kind, a scaffolded document diffs with both deltas and re-stamps
through the CLI alone, no verb for it falls through to the template branch, no message for it
names `kind='template'`, and the help text tells the two roles kinds apart.

Wired: scaffold_roles_catalog/diff_override(kind=roles)/update_stamp(kind=roles) reached from _cli/_override.py — 'roles' positional plus a --roles-catalog flag (see the task comment for the naming decision), mirroring the workflow/playbook branches exactly. _print_diff_result gained a roles label branch. All three help strings (scaffold/diff/update) now list 'roles' and distinguish it from --role <slug>.

Driven end to end (scaffold roles / diff roles / update roles) on a scratch squad with no hand-written file; sq override list already showed the kind and is unchanged. Tests: tests/cli/test_override_commands_cli.py new roles-kind cases mirroring the workflow/playbook ones, plus an updated test_roles_catalog_override_lifecycle.py docstring (the CLI wiring it flagged as out of scope now exists).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Apply the catalog document to an activated role

<!-- sq:subtask:ST2:body -->
Make the roles catalog document apply to a role that has already been activated.

`role_base_from_item` (`_roles/_resolver.py:364-410`) reads `_PREDEFINED_BY_SLUG.get(slug)`
(`:394`) — the bundled catalog alone — while `resolve_role_with_base` reads
`_predefined_for_slug(slug, squad_dir)` (`:317`), which merges the document. And a supplied base
wins: `effective_base = base if base is not None else predefined` (`:318`). So wherever a live
item exists, the merged value is computed and then thrown away.

Driven in-process, on a squad whose document renames the reviewer's title:

| Path | Result |
| --- | --- |
| `resolve_role("reviewer", squad_dir)` | the document's title |
| `role_base_from_item(item)` | the bundled title |
| `resolve_role_with_base("reviewer", squad_dir, base=…)` | the bundled title |

`sq init` activates the bundled roles, so every role a team actually uses is on the losing side of
this. The document reaches only slugs nobody has activated yet.

The three call sites, all able to obtain `squad_dir`:

- `_cli/_role.py:219` — `_role_base_for_show`, behind `sq role <slug> show`.
- `_services/_maintenance.py:744` — `_refresh_catalog_extra`, behind `sq sync`; `self.paths.squad_dir`
  is already in hand and already passed to the very next line's `resolve_role_with_base`.
- `_overrides/_service.py:1283` — `_check_role_override_resolves`, behind `sq check`; it already
  takes `squad_dir` as a parameter and needs no new threading.

Constraints:

- **The item stays authoritative for operator-settable fields only** — `full_name` for a bundled
  role, `full_name`/`model`/`tech` for a developer role. What changes is which catalog the
  remaining fields are read from, not how much of the item is trusted. The function's docstring
  already promises the catalog's *current* value for everything else; this makes that true of a
  project's catalog too.
- **Precedence stays bundled → catalog document → per-slug file.** The per-slug layer is applied
  at `:319-324`, outside the `base is None` branch, and must keep being applied by the caller of
  `_predefined_for_slug` rather than folded into the base.
- **The resolver stays stateless** — it reads from disk on every call by its own stated stance.
  Do not add a cache to avoid re-reading the document.
- **The developer-role branch is unaffected**: `dev_base_from_item` regenerates from the tech
  template and has no catalog-document layer to gain here.

Done when a document that changes a bundled role's field reaches that role through
`sq role <slug> show`, `sq sync` and `sq check` after activation; a not-yet-activated slug is
unchanged; all three layers naming the same field resolve in the stated order; and a squad with no
`.overrides/roles.toml` behaves exactly as it does today on every one of these paths.

role_base_from_item(item, squad_dir=None) now takes squad_dir and reads _predefined_for_slug(slug, squad_dir) instead of _PREDEFINED_BY_SLUG.get(slug) — squad_dir defaults to None so an unmodified caller keeps today's bundled-only answer. Wired at the two in-territory call sites: _cli/_role.py's _role_base_for_show (sq role <slug> show) and _services/_maintenance.py's _refresh_catalog_extra (sq sync).

Left undone: the third call site, _overrides/_service.py:1283 _check_role_override_resolves (sq check's role-override resolve), still calls role_base_from_item(item) with no squad_dir and so still builds a bundled-only base there. That file is out of my territory this run (a concurrent dev owns _overrides/ and _workflow/) — it is a one-line addition (role_base_from_item(item, squad_dir)) once that lock lifts, no other change needed. Not a regression: sq check stays clean either way, it just doesn't yet exercise the document layer on that one internal resolve-check.

Driven and proven for the two fixed sites (see the task comment): sq role reviewer show and sq sync both now report a catalog-document title change on an already-activated role, with precedence bundled -> document -> per-slug file holding across all three layers.

Closed: _overrides/_service.py:1283 (_check_role_override_resolves) now calls role_base_from_item(item, squad_dir) — the same one-line fix as the other two sites. File was free once TASK-805 landed (it deleted _workflow_stamp_finding_gated and rerouted _check_workflow_override_issues elsewhere in the same file; read the file fresh before editing, unaffected by that change).

Driven on a scratch squad (not inferred): an activated architect + a stamped catalog document setting color="" (a value load_role_catalog's own validation doesn't check, so the document alone loads fine) + a stamped per-slug architect.toml — before this fix sq check was silent; now it reports 'role override does not load: ... blank or whitespace-only ... color', matching sq role architect show's own refusal. Removing the document (same per-slug file) returns sq check to clean, isolating the document as the cause. A valid document field change (mission) alongside a per-slug field change (title) resolves cleanly and both land on sync. A squad with no document, and a document-only squad with no per-slug file, are both unchanged (still clean).

Permanent coverage: tests/service/test_roles_catalog_document_reaches_an_activated_role.py gained 3 tests using the same blank-color technique tests/integration/test_blank_role_override_field_breaks_no_generated_surface.py already established for the per-slug-only case.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — sq role catalog lists project-declared roles

<!-- sq:subtask:ST3:body -->
Make `sq role catalog` show the roles a project actually declares.

It iterates the module-level `PREDEFINED` tuple directly (`_cli/_role.py:82` and `:90`, built at
import in `_roles/_catalog.py:202`), so it consults no document at all — there is no item, no
base and no `squad_dir` involved. This is the same defect as the activated-path one, a layer over:
a bundled-only read of the catalog.

Driven on a squad whose document declares a `security-analyst` slug and renames the reviewer's
title: the new slug is absent from `sq role catalog --json` and the reviewer shows its bundled
title there — while `sq role security-analyst show` resolves the new role and `project_role_slugs`
already counts it. So a project can declare a role the tool will resolve and activate, and the
command whose whole job is to list what can be activated does not mention it.

Read the merged catalog for the active squad instead, so a declared role appears and an overridden
bundled role shows the project's values.

Two things to settle rather than assume:

- **What the command means when there is no squad.** It resolves the squad directory like any
  other command; if that can legitimately be absent, the bundled catalog remains the honest answer
  for that case and the code should say so.
- **Whether the listing distinguishes bundled from project-declared.** A reader choosing what to
  activate benefits from knowing which is which, and the command already carries an `is_default`
  column, so the shape exists. Decide it; do not leave the two indistinguishable by accident.

Done when a document-declared role appears in `sq role catalog` and in its `--json`, an overridden
bundled role shows the document's values there, and a squad with no document lists exactly what it
lists today.

sq role catalog (plain and --json) now reads load_role_catalog(squad_dir) instead of the module-level PREDEFINED tuple, resolved via a new _catalog_squad_dir() helper mirroring version_notice()'s not-a-squad handling. Added an Origin/origin column (bundled vs project) since a document-overridden bundled role and a wholly project-declared slug both needed to read as distinguishable, not just present.

Driven: a document renaming reviewer's title and declaring security-analyst both appear in sq role catalog and its --json, with origin bundled/project respectively; a squad with no document is unchanged except for the new origin key (updated the pinned golden + JSON-shape tests deliberately, noted in the handoff).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T21:06:34Z] Olivia Lead:
  - Authored from what TASK-800 left open. Chose ONE task over two: they are one surface - making the kind real for the person using it - and neither half ships alone. CLI verbs that scaffold a document which then does nothing for any activated role is worse than no verbs, because it invites an adopter to write an override and trust it; a resolver fix for a document a human has no command to create is unreachable. Same owner, same review, same increment. The original split reason was a concurrent dev owning _cli/, which is a scheduling fact, not a scoping principle, and it is gone.
  - Both gaps driven, not read off the handoff. CLI: scaffold roles, diff roles and update roles all fall through to the template branch on a scratch squad - the update error literally says kind=template - while sq override list already shows the kind because it is kind-agnostic, so the only way to reach that state is to write the file by hand. Resolver: with a document renaming the reviewer title, resolve_role gives the document value and role_base_from_item plus resolve_role_with_base give the bundled one, because a supplied base wins at _resolver.py:318 and the base was built bundled-only at :394.
  - Sharper than the handoff states it: sq init activates the bundled roles, so every role a team actually uses is on the activated path and the document reaches NONE of them. It applies only to slugs nobody has activated yet. That makes the capability inert for its main case rather than merely asymmetric.
  - Third gap found while verifying, now ST3: sq role catalog iterates the module-level PREDEFINED tuple directly (_cli/_role.py:82 and :90), so a document-declared role never appears in the list of roles available to activate - driven, security-analyst resolves through sq role show and is counted by project_role_slugs but is absent from sq role catalog. Same defect one layer over, and leaving it would make the other two fixes look arbitrary. @python-dev
- [2026-08-25T21:56:00Z] Elias Python:
  - ST1 (CLI verbs) and ST3 (sq role catalog) are Done; ST2 (activated-role resolve) is InProgress — 2 of 3 call sites fixed, one blocked by the concurrent-dev file lock (details below).
  - Naming decision: --role <slug> (per-role) vs the catalog document collide at one character with --roles. Chose a positional 'roles' name plus a --roles-catalog flag — never a bare --roles — matching the existing workflow/playbook shape (positional name OR boolean flag) and making the two kinds unmistakable in one --help listing (verified: sq override scaffold --help shows --role and --roles-catalog side by side with 'distinct from --role <slug>' in both help strings).
  - Gap 1 (CLI): scaffold_roles_catalog/diff_override(kind=roles)/update_stamp(kind=roles) reached from _cli/_override.py — scaffold/diff/update all take 'roles' positionally or --roles-catalog, _print_diff_result got a roles label branch, all three help strings list 'roles' distinctly. Driven end to end on a scratch squad with no hand-written file. Fixed a Rich-markup bug I introduced along the way (unescaped [[roles]]/[bundles]/[dev] in the scaffold hint and docstring were being swallowed as markup tags).
  - Gap 2 (resolver): role_base_from_item(item, squad_dir=None) now reads _predefined_for_slug(slug, squad_dir) instead of the bundled-only _PREDEFINED_BY_SLUG.get(slug); squad_dir defaults to None so an unmodified caller is unaffected. Wired at _cli/_role.py (sq role show) and _services/_maintenance.py (sq sync) — both in my territory. NOT wired at _overrides/_service.py:1283 (_check_role_override_resolves, sq check's role-override resolve): that file is owned by the concurrent TASK-805 dev this run, so I left its role_base_from_item(item) call untouched rather than risk a collision. It's a one-line follow-up (add squad_dir) once that lock lifts — no other change needed, and sq check stays clean either way in the meantime, it just doesn't yet exercise the document layer on that one internal check.
  - Gap 3 (sq role catalog): now reads load_role_catalog(squad_dir) instead of PREDEFINED, via a new _catalog_squad_dir() helper (mirrors version_notice()'s not-a-squad handling). Added an Origin/origin column (bundled vs project) to keep a document-overridden bundled role and a wholly new project slug distinguishable, not just present.
  - Driven proof (real scratch squad, sq init --roles all, reviewer already activated): sq override scaffold roles / diff roles / update roles work through the CLI alone; a document renaming reviewer's title + declaring security-analyst reaches sq role reviewer show (activated), sq sync (item + CLAUDE.md), and sq role catalog (both plain and --json) — none of which worked before this task; a squad with no document is unchanged on every path; precedence bundled -> document -> per-slug file holds with all three layers naming the same role (title from the document, model from a per-slug file).
  - Gates: pyright/ruff check/ruff format clean repo-wide. tests/meta: 227 passed. Targeted (role/override/catalog across unit/cli/integration/service): 1014 passed, 1 skipped. sq check clean on this repo. Did not run the full pytest suite per the brief — updated 2 pinned golden/JSON-shape tests deliberately (role_catalog.json + test_json_output_shape.py's set-equality assertion) to add the new origin field; new coverage added in tests/cli/test_override_commands_cli.py, tests/cli/test_roles_catalog_document_cli_surfaces.py, tests/unit/test_role_base_from_item_dispatches_by_role_kind.py, tests/service/test_roles_catalog_document_reaches_an_activated_role.py.
- [2026-08-25T22:03:41Z] Elias Python:
  - ST2 closed — Done. The one remaining piece (_overrides/_service.py:1283, _check_role_override_resolves) is now the same one-line fix as the other two sites: role_base_from_item(item, squad_dir). File was free once TASK-805 finished; read it fresh (it had deleted _workflow_stamp_finding_gated and rerouted _check_workflow_override_issues in the same file) before editing — my earlier reasoning still held on the current code.
  - Driven, not inferred: on a scratch squad with an activated architect, a stamped catalog document setting a blank color (a value load_role_catalog's own validation doesn't check, so the document alone still loads) plus a stamped per-slug architect.toml — before this fix sq check was silent about it; now it reports the blank-color refusal, exactly matching sq role architect show's own error. Removing the document alone (same per-slug file) returns sq check to clean, isolating the document as the cause. A valid document field change (mission) plus a different per-slug field (title) resolves cleanly and both land after sync. A squad with no document, and a document-only squad with no per-slug file, are both unchanged.
  - All three of ST1/ST2/ST3 are now Done. Added permanent coverage in tests/service/test_roles_catalog_document_reaches_an_activated_role.py (3 new tests) using the same blank-field technique the pre-existing per-slug-only test already established.
  - Gates: pyright/ruff check/ruff format clean repo-wide. tests/meta: 227 passed. Targeted role/override/catalog/check sweep: 1273 passed, 1 skipped. sq check clean. Full suite not run per the brief. Leaving TASK-814 in InReview.
<!-- sq:discussion:end -->
