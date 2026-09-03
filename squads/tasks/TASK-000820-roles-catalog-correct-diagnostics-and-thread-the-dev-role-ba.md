---
id: TASK-820
sequence_id: 820
type: task
title: 'Roles catalog: correct diagnostics and thread the dev-role base'
status: Done
parent: FEAT-791
author: tech-lead
assignee: python-dev
priority: medium
refs:
- REV-817:addresses
- ADR-775:implements
- TASK-800
- TASK-814
- MILE-836:targets
description: Catalog refusals name the merged document rather than the bundled one,
  the stamp finding names its own object, and the dev-role preview base honours the
  project catalog
subentities:
- local_id: ST1
  title: Carry the origin into roles catalog validation refusals
  status: Done
  assignee: python-dev
  story: US3
- local_id: ST2
  title: Name roles in the stamp finding and retire the stale docstring
  status: Done
  assignee: python-dev
  story: US3
- local_id: ST3
  title: Thread squad_dir into the dev-role preview merge base
  status: Done
  assignee: python-dev
  story: US3
created_at: '2026-08-25T22:59:31Z'
updated_at: '2026-08-26T16:01:02Z'
---
<!-- sq:body -->
## Scope

FEAT-791 US3 — three residual defects in the whole-document roles catalog override. The capability
itself works: an override document is picked up on both the activated and not-yet-activated paths,
per-slug files win field-by-field over it, and the scaffold/list/diff/update verbs behave. What is
left is one wrong diagnosis, one remediation hint pointing at the wrong object, and one resolver
that never received the project's catalog.

They are grouped because they land in the same four files and two of them touch the same function
neighbourhoods; splitting them would put two developers in `_overrides/_service.py` at once.

## 1. Refusals name the bundled catalog for the adopter's own override

`_roles/_loader.py:212`, `:220` and `:309` all raise `Invalid bundled role catalog...`, but
`_validate` and `_build_catalog` run on the result of merging `.overrides/roles.toml` over the
bundled base (`load_role_catalog`, `:160-194`). The wording predates the override path and was not
moved with it.

The observable: a `.overrides/roles.toml` carrying only a `[selected]` deselect of one bundled role
— the sanctioned way to hide a role — produces

    error: Invalid bundled role catalog:
      - bundle 'all' references unknown slug 'tech-writer'
      - 'all' bundle has unknown slugs: ['tech-writer']

The adopter can open the bundled `roles.toml`, see `tech-writer` declared and named by `all`, and
conclude the guard is wrong. That is precisely what ADR-775 A4's standing rule forbids: **a refusal
may not assert a cause the reader can disprove.** The rule was written for the skew refusal in this
same release; this is the same defect one axis over.

Two further gaps in the same message: it names no file at all, so there is no path to the document
actually at fault; and it never mentions `[selected]`, the mechanism that caused it. Nothing tells
the reader that deselecting a role also requires deselecting or rewriting every bundle naming it.

The floor doing the work with no deselect-specific guard is the right design and stays. What has to
change is that the floor's message reaches the adopter as guidance instead of as an accusation
against a file they did not write.

## 2. The stamp finding names the bulk remediation form

`_overrides/_service.py:1237` states as current fact that `_cli/_override.py` "has no dedicated
`roles` positional match yet ... so a named invocation would silently mis-route to the `template`
kind". That was true when it landed and stopped being true one commit later: `_cli/_override.py`
now matches `roles` at `:172`, `:326-327` and `:444-445`, and both `sq override update roles` and
`sq override diff roles` resolve to the `roles` kind.

Two consequences, in the order they matter:

- The emitted messages (`:1245-1256`) name `sq override update` and `sq override diff` with no
  object, where every sibling kind names its own (`sq override update workflow`,
  `sq override diff --role <slug>`). A squad carrying several overrides is told to re-stamp all of
  them to clear a finding about one.
- A docstring asserting the reverse of what ships is the defect class ADR-777 §4 spends a section
  retiring. Reintroducing an instance in the feature that retires three is not acceptable.

## 3. The dev-role preview base is not threaded with the squad

`dev_base_for_slug` (`_roles/_resolver.py:419-426`) takes no `squad_dir` and calls the bundled
`dev_role(...)`, while its sibling `resolve_dev_role` (`:429-460`) threads `squad_dir` through
`load_role_catalog(squad_dir).dev`. So a `[dev]` override is honoured where a dev role is created
and ignored where one is previewed: with `[dev] model = "haiku"` in the catalog document,
`sq role python-dev show` on an un-added slug reports `model: sonnet`, and `sq dev add --tech rust`
then `sq role rust-dev show` reports `model: haiku`. The preview tells the adopter one thing and the
command does another.

ADR-777 §3's stated defect is that `[bundles]` and `[dev]` cannot be overridden at all. Half of
`[dev]` is still unreachable.

Three call sites, and the plumbing is not uniform — check each rather than assuming:

- `_cli/_role.py:265` — has `squad_dir` in the enclosing signature and does not pass it. The line
  directly above, `role_base_from_item(it, squad_dir)`, does. This is the observable case.
- `_overrides/_service.py:882` — inside `_shadowed_bundled_role_toml(slug)`, which takes **no**
  `squad_dir`. Its two callers are `_diff_role(squad_dir, slug)` (`:901`, has one) and
  `_role_override_shadows_bundled(slug, role_items_by_slug)` (`:1170`, has none). Threading here
  means changing signatures, not just adding an argument. Note the same function's bundled branch
  calls `role_by_slug(slug)`, equally un-threaded — decide deliberately whether that one is in
  scope and say so on the subtask.
- `_overrides/_service.py:1450` — the base a per-slug dev override is diffed and shadow-classified
  against. Latent today; `squad_dir` is in hand.

## Acceptance

1. A catalog-document override that fails validation is refused with a message that names
   `.overrides/roles.toml` (by path), does not describe the bundled catalog as invalid, and — when
   the unknown slug is one `[selected]` removed — carries a hint saying so and naming the remedy.
2. A genuinely invalid **bundled** catalog still refuses, and its message still says so. Do not
   trade one wrong document name for the other; the origin has to be carried, not assumed.
3. The roles-catalog stamp finding's two messages name `roles` as the object, matching every sibling
   kind's form, and `sq override update roles` / `sq override diff roles` are driven to prove the
   named form works.
4. No docstring in `_overrides/_service.py` asserts the CLI lacks `roles` verbs.
5. With `[dev]` set in `.overrides/roles.toml`, `sq role <tech>-dev show` on a slug with no roster
   entry reports the project's values, and reports the same values `sq dev add` would then produce.
6. The two latent call sites resolve against the project's dev defaults too, with a test each — a
   scaffold base and a per-slug dev override's diff base.
7. `sq check` clean; `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` clean.

## Out of scope

The `[bundles]` half of ADR-777 §3, and any change to which layer wins during the merge. This task
changes what the adopter is told and which catalog a preview reads — not precedence.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 820 add-subtask "<title>"`; track with `sq task 820 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Carry the origin into roles catalog validation refusals

<!-- sq:subtask:ST1:body -->
`load_role_catalog` already knows whether it merged an override and, when it did, the override
path — it builds `origin` at `:174`. Carry that through to `_validate` and `_build_catalog` so the
three raise sites report the document that is actually at fault.

Shape to aim for, from the review: `.overrides/roles.toml: role catalog invalid after merge: ...`
for the merged path, with the bundled-only path keeping a message that says bundled.

Then give `_check_bundles` a hint for the specific case an adopter will hit first: the unknown slug
is a slug `[selected]` removed. The hint has to say that deselecting a role obliges deselecting or
rewriting every bundle that names it, and name the bundle and slug involved. Without it the
sanctioned capability is discoverable only by trial and error — one deselect produces two errors,
several produce eight.

Two tests, both driven through the CLI: a `[selected]` deselect of one bundled role, and a
deliberately invalid bundled catalog (patch the bundled raw mapping) to prove the bundled wording
survives for the case it is true of.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Name roles in the stamp finding and retire the stale docstring

<!-- sq:subtask:ST2:body -->
In `_roles_catalog_stamp_finding_gated`:

- Change both emitted messages to name the object: `sq override update roles` for the unstamped
  arm, and `sq override diff roles` / `sq override update roles` for the drifted arm. The sibling
  forms to match are in `_workflow/_loader.py:1069,1076` and `_overrides/_service.py:1397-1398`.
- Delete the docstring paragraph claiming `_cli/_override.py` has no `roles` positional match. It
  is contradicted by `_cli/_override.py:172`, `:326-327` and `:444-445`. Replace it with what is
  true, or with nothing — do not soften it into a hedge.

Update the tests asserting the old message text, and add one that drives `sq override update roles`
and `sq override diff roles` and asserts each resolves to the `roles` kind rather than falling
through to `template`.

While in the file, sweep for any other docstring claim about CLI wiring that the same commit
falsified. One instance was found; a grep for claims of the form "not yet" or "left to the task
that" costs nothing.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Thread squad_dir into the dev-role preview merge base

<!-- sq:subtask:ST3:body -->
Give `dev_base_for_slug` an optional `squad_dir` and have it resolve the dev pool the way
`resolve_dev_role` does — `load_role_catalog(squad_dir).dev` via `dev_role_from_pool` when a squad
is given, the bundled `dev_role` when it is not. Keep the no-squad behaviour byte-identical; the
module-level bundled singleton path must not change.

Then pass a squad at each call site. They are not uniform:

- `_cli/_role.py:265` — `squad_dir` is already in the enclosing signature. One argument.
- `_overrides/_service.py:882` — inside `_shadowed_bundled_role_toml(slug)`, which has no
  `squad_dir`. Its callers are `_diff_role` (has one) and `_role_override_shadows_bundled` (does
  not). Thread the signatures rather than reaching for a module-level handle. If the second caller
  genuinely cannot supply one, say so on this subtask and leave that path bundled deliberately —
  a stated exclusion, not a silent one.
- `_overrides/_service.py:1450` — `squad_dir` is in hand.

Decide explicitly whether the bundled branch of `_shadowed_bundled_role_toml` (`role_by_slug(slug)`,
equally un-threaded) belongs in this change, and record the call either way.

Cover it with the observable from the finding: a scratch squad with `[dev] model` and `color` set,
`sq role <tech>-dev show` on an un-added slug, then `sq dev add` and `sq role <tech>-dev show`
again — both must report the project's values, and the test should assert they agree with each other,
not just that each matches a literal.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T08:36:02Z] Elias Python:
  - ST1 (F3): threaded origin through _build_catalog/_validate/_check_bundles in _roles/_loader.py. A [selected] deselect now refuses naming .overrides/roles.toml by path ("role catalog invalid after merge"), never the bundled document, plus a hint naming [selected].roles and the remedy. The bundled-only path is unchanged ("Invalid bundled role catalog"). Driven both legs on a scratch squad.
  - ST2 (F7): _roles_catalog_stamp_finding_gated now emits `sq override update roles` / `sq override diff roles`, matching sibling kinds. Deleted the stale docstring paragraph; grepped _roles/ and _overrides/_service.py for the same claim shape ("no dedicated", "mis-route", "left to the task") — no other instance. The :1290-1293 citation the reviewer couldn't confirm is unrelated (check_override_issues docstring, accurate).
  - ST3 (F6): dev_base_for_slug(slug, squad_dir=None) now resolves load_role_catalog(squad_dir).dev via dev_role_from_pool when given a squad, matching resolve_dev_role. Threaded to all three call sites (_cli/_role.py:265, _overrides/_service.py's _shadowed_bundled_role_toml + _check_role_override_resolves, and _role_override_shadows_bundled's new squad_dir param). Driven: preview and sq dev add now agree on [dev].model for an un-added slug.
  - Decision on the un-added part of F6: left _shadowed_bundled_role_toml's bundled branch (role_by_slug(slug)) unthreaded — deliberate exclusion, not silent. It's the [roles] catalog-document layer reaching a per-slug bundled-role Δ-mine/shadow baseline, a different consumer than either finding named; threading it also changes what the baseline means (bundled-as-shipped vs bundled-after-catalog-merge), not just where it reads from. No finding or acceptance clause here calls for it. Left as a stated exclusion in the function's docstring.
  - Tests: 4 new (dev-pool preview/scaffold-base/diff-base wiring) + 5 new (F3 origin-carrying, both legs) + strengthened 2 existing (F7 message wording) — 194/194 targeted pass, tests/meta 238/238 pass. Full gates clean: ruff check/format, pyright --all-extras (0 errors). sq check clean.
<!-- sq:discussion:end -->
