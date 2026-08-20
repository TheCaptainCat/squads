---
id: REV-735
sequence_id: 735
type: review
title: Playbook as the fourth override kind
status: Approved
author: reviewer
refs:
- TASK-720
- FEAT-714
- ADR-696
subentities:
- local_id: F1
  title: A custom role cannot be given playbook guidance
  status: Fixed
  assignee: python-dev
  severity: high
- local_id: F2
  title: check drops the valid workflow spec when the playbook is broken
  status: Fixed
  assignee: python-dev
  severity: high
- local_id: F3
  title: The append idiom duplicates a role section, as the scaffold shows
  status: Fixed
  assignee: python-dev
  severity: medium
- local_id: F4
  title: The context half of the playbook seam has no production consumer
  status: Fixed
  assignee: python-dev
  severity: medium
- local_id: F5
  title: The scaffold's field-merge rule is false for the roles array
  status: Fixed
  assignee: python-dev
  severity: low
- local_id: F6
  title: The [selected] refusal offers an empty menu of sections
  status: Fixed
  assignee: python-dev
  severity: low
- local_id: F7
  title: The bundled playbook is immutable by convention, not by type
  status: Fixed
  assignee: python-dev
  severity: info
- local_id: F8
  title: Each playbook load reparses the bundled TOML two or three times
  status: Fixed
  assignee: python-dev
  severity: info
- local_id: F9
  title: A guide for a non-roster project role validates then vanishes
  status: Fixed
  severity: medium
- local_id: F10
  title: check still masks both findings when both overrides are broken
  status: Fixed
  severity: low
- local_id: F11
  title: The scaffold does not say a project role slug is now accepted
  status: Fixed
  severity: info
- local_id: F12
  title: The new guide warning fires on a stock squad and cannot be cleared
  status: Fixed
  severity: medium
created_at: '2026-08-03T11:01:46Z'
updated_at: '2026-08-06T20:26:21Z'
---
<!-- sq:body -->
Independent review of the playbook override (TASK-720, commits `9ee3ea7` / `35430f8`), against
ADR-696 as the authority and FEAT-714. Reviewer was outside the build lineage. Everything below
was driven against throwaway squads.

## What holds

- **The reclaim-scope reasoning holds.** Dropping `guide` via `.overrides/workflow.toml`'s
  `[selected]` flags `SKILL-14 sq-guide` as an orphan in `sq check` and withdraws its generated
  files in `sq sync` — and it still does with a playbook override present. The reasoning is
  sound, not just the outcome: `bundled_skill_slugs()` enumerates every historically-bundled
  `sq-<type>` slug and `custom_skill_slugs(spec)` covers every spec-declared type with no
  *bundled* entry, so `is_system_skill` recognises a dropped built-in, a renamed-away built-in
  under its old name, and a project type with override coverage — all three without ever
  consulting the merged playbook, which by design cannot see the first two. Threading it there
  would have re-broken exactly what the fix restored. The three functions that legitimately do
  vary are threaded at every production site I could find (`managed_item_types` at the backend's
  per-type skill writer; `item_types_for_role`/`skills_for_role` at `_backends/_base`,
  `_services/_roster` x2, `_services/_base`, `_services/_config_integrity` x3).
- **The seam is intact.** `_PLAYBOOK_SPEC` and `PLAYBOOK` are each assigned exactly once and
  nothing anywhere mutates or rebinds them; `RequestContext` is a frozen dataclass behind a
  `ContextVar`, and the merged playbook otherwise lives per-instance on `Service.playbook`. Two
  requests cannot see each other's. `_bundled_raw()` re-parses on every call, so the raw mapping
  handed to the merge engine is never shared either.
- **Attribution cannot cross.** A malformed playbook override reports as `playbook` with the
  loader's own specific violation and the file named; a malformed workflow override reports as
  `workflow` and still points at `sq workflow lint`. `PlaybookConfigError` is caught ahead of the
  general `SquadsError`, and `sq workflow lint` says OK when only the playbook is broken. Driven
  both ways.
- **Fail-closed is real.** `[selected]` refused; an unknown top-level key (`override_base`
  included, exactly as ADR-696 requires) refused; a spread token outside a list refused with the
  right advice; a dangling `$(*self)` on a brand-new key refused; malformed TOML refused with a
  line/column. All clean `SquadsError`s, never a traceback.
- **The end-to-end capability works for a bundled role.** A custom `incident` type declared in
  the workflow override plus a `[types.incident]` playbook entry produces a rich, role-sectioned
  `sq-incident` skill and puts `sq-incident` on the `devops` role's preload list in both
  `squads/agents/roles/` and `.claude/agents/`.
- The `[[types.<t>.roles]]` header form cannot carry the token — correct per ADR-696, and the
  refusal explains itself. Not a bug.

## Where it does not hold

Two high findings, both in the seam between this feature and its neighbour rather than in the
merge engine itself. F1 is the capability ADR-696 §4a names as the reason this override kind
exists, and it is unreachable. F2 is `sq check` reporting a false fatal error and hiding the
real one, in exactly the configuration this feature makes possible.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 735 add-finding "…" --severity medium`; track with `sq review 735 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed | python-dev | A custom role cannot be given playbook guidance |
| F2 | 🟠 high | Fixed | python-dev | check drops the valid workflow spec when the playbook is broken |
| F3 | 🟡 medium | Fixed | python-dev | The append idiom duplicates a role section, as the scaffold shows |
| F4 | 🟡 medium | Fixed | python-dev | The context half of the playbook seam has no production consumer |
| F5 | 🟢 low | Fixed | python-dev | The scaffold's field-merge rule is false for the roles array |
| F6 | 🟢 low | Fixed | python-dev | The [selected] refusal offers an empty menu of sections |
| F7 | 🔵 info | Fixed | python-dev | The bundled playbook is immutable by convention, not by type |
| F8 | 🔵 info | Fixed | python-dev | Each playbook load reparses the bundled TOML two or three times |
| F9 | 🟡 medium | Fixed |  | A guide for a non-roster project role validates then vanishes |
| F10 | 🟢 low | Fixed |  | check still masks both findings when both overrides are broken |
| F11 | 🔵 info | Fixed |  | The scaffold does not say a project role slug is now accepted |
| F12 | 🟡 medium | Fixed |  | The new guide warning fires on a stock squad and cannot be cleared |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A custom role cannot be given playbook guidance

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Assignee:** Elias Python
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**Reproduced.** ADR-696 §4a names this as the reason the playbook override exists, and it does not
work. Quoting the authority:

> **This is the mechanism by which a custom role enters a type's playbook guidance**, and it
> settles that question rather than leaving it open: the project writes the type's `roles` array
> as `["$(*self)", { slug = "my-role", ... }]`, inheriting every bundled guide and adding its own.

`_interactions/_loader.py::_check_slugs` validates every guide slug against
`get_catalog()` — the module-level **bundled** `RoleCatalogSpec`, the eight shipped roles plus the
`*dev` sentinel. A project role is by definition not in it, so the guide is refused.

Driven, using only shipped, documented commands:

    $ sq override scaffold --new sre          # the command's own help: "starts a wholly new role"
    $ ...fill in full_name/title/description/mission...
    $ sq role activate sre
    activated Sam Reliability (ROLE-19)
    $ ...add `{ slug = "sre", enter = [...], do = [...] }` to [types.task].roles after "$(*self)"
    $ sq check
    error playbook: playbook config invalid: Invalid playbook:
      - types.task: role slug 'sre' not in role catalog

`sre` is a live `Active` ROLE item in the roster at that moment. The same refusal blocks an
explicit `<tech>-dev` slug (`python-dev` — driven, same message), so a project with two devs
cannot give them different guidance either; `*dev` is all-or-nothing.

The failure mode makes it worse than a missing feature: it is a **hard stop for the whole
squad**, not an advisory. `sq list` exits 1, `sq <type> <n> show` exits 1. The adopter's only
recovery is to delete their playbook override.

The fix is available without touching the module-level singleton. `resolve_playbook` already holds
`squad_dir`, and the project's own role slugs are on disk at
`<squad_dir>/.overrides/roles/*.toml` — the same source `_roles/_resolver.py` reads. Thread a
slug authority (bundled catalog union project role overrides) into `_check_slugs` on the
per-request path, and keep the bundled-only authority for the module-level bundled load, which has
no `squad_dir` and must not gain one. Whether the live roster (`ROLE` items) should also count is
a ruling worth making explicitly rather than by accident; the override files are the safer
authority because they are readable before the index is.

Whatever the fix, ADR-696 §4a should not be left asserting a mechanism that does not run.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-08-03T11:58:30Z] Elias Python:
  - Fixed. Threaded a project-role slug authority into the per-request playbook load: _check_slugs now validates against the bundled catalog UNION the slugs with a live .overrides/roles/*.toml on disk (new squads/_roles/_resolver.py::project_role_slugs()), only on the squad_dir-bearing path — the module-level bundled singleton load is untouched, exactly as you scoped it.
  - Falsified both directions with a new test file (tests/integration/test_playbook_guide_for_a_project_defined_role.py): scaffold --new sre -> fill stub -> activate_role -> append sre to types.task.roles via $(*self) -> reopen -> sq check accepts it AND the generated sq-task skill body actually renders Sam Reliability's section with the guide text (proves the roster-driven render path, not just _check_slugs). Reverting the fix reproduces exactly your 'not in role catalog' refusal on 3 of 4 new tests.
  - Also covers the *dev breadth you noted: an explicit python-dev slug is accepted once a .overrides/roles/python-dev.toml exists (even a trivial one), and still correctly refused with no such file -- the override-file-is-the-authority boundary you called out, not a roster-based ruling.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — check drops the valid workflow spec when the playbook is broken

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Assignee:** Elias Python
**Severity:** 🟠 High
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**Reproduced.** `sq check` — the pre-handoff gate whose job is to say what is wrong — reports a
false fatal error, points at the wrong remedy, and never prints the real finding. Reachable only
in a configuration this feature created, which is why it is new.

`_cli/_main.py`'s `check` catches `PlaybookConfigError` first (correct, and the ordering comment
is right), appends the `playbook` issue, and then builds its fallback service as:

    svc = Service(sp, spec=bundled_spec())

That discards the merged **workflow** spec, which loaded perfectly. `svc.check()` then goes
through `IndexStore(spec=bundled_spec())`, which fail-closed refuses an index holding an item of a
type the bundled spec does not declare — and the exception escapes before the appended `playbook`
issue is ever printed.

Driven. Squad with a valid `.overrides/workflow.toml` declaring a custom `incident` type
(`INC-20 db outage` filed), then a *playbook*-only breakage (`overview = ""`):

    $ sq workflow lint
    workflow spec OK — no errors or warnings.
    $ sq check
    error: item INC-20 has type 'incident', which the active spec no longer declares; migrate or
    re-type this item before it can load again (or run `sq repair` if the index itself is merely
    stale)
    $ echo $?
    1

Nothing is wrong with `INC-20`, nothing is wrong with the workflow spec, and the type is declared.
The operator is told to migrate or re-type their items. The actual fault — one empty `overview`
in `.overrides/playbook.toml` — is not mentioned at all. `sq check` exits 1 (the error path)
rather than 3 (its issue-level path), so a wrapper cannot tell this from any other hard failure.

`sq repair` happens to survive (it routes through
`get_service_bypassing_index_cross_check`, which builds `Service(sp, spec=merged_spec)` — the
right spec — and silently uses the bundled playbook), so the suggested remedy runs and reports
success while changing nothing relevant. That is arguably worse than it failing.

Fix: the `PlaybookConfigError` branch must keep the workflow spec it already has. Reusing
`get_service_bypassing_index_cross_check`'s ladder, or simply
`Service(sp, spec=load_workflow_spec(squad_dir=sp.squad_dir))` inside that branch, restores the
intended behaviour — the playbook finding is reported and every other check still runs. Please
also pin it by test: a squad with a valid workflow override declaring a custom type, at least one
item of that type, and a broken playbook override must report the `playbook` issue and no
phantom type/corpus error. The existing attribution test
(`test_check_distinguishes_playbook_and_workflow_config_errors.py`) passes because its squad has
no workflow override worth losing.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-08-03T12:00:30Z] Elias Python:
  - Fixed. The PlaybookConfigError branch in sq check no longer falls back to bundled_spec() -- it re-resolves the merged workflow spec via load_workflow_spec(squad_dir=...) (falling back to bundled only if THAT itself fails, mirroring get_service_bypassing_index_cross_check's ladder as you suggested), so the workflow spec that already loaded fine is kept and every other check runs against it.
  - Falsified both directions with tests/integration/test_check_keeps_the_merged_spec_when_only_the_playbook_breaks.py: custom incident type + one filed item + a playbook-only break (overview = ""). After the fix: sq check reports 'playbook config invalid ... overview is empty', exit 3, no 'no longer declares' text anywhere (text or --json). Reverting the fix reproduces your exact repro -- the phantom 'INC-2 has type incident, which the active spec no longer declares' error, exit 1 not 3, and the real finding never printed.
  - Pinned per your request; the existing attribution test is unaffected (its squad has no workflow override worth losing, so it never exercised this branch).
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — The append idiom duplicates a role section, as the scaffold shows

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Assignee:** Elias Python
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**Reproduced, from the shipped scaffold's own worked example.**

`sq override scaffold playbook` writes this, commented, as the example to uncomment:

    # [types.task]
    # roles = [
    #     "$(*self)",
    #     { slug = "qa", enter = ["Read the task body"], do = ["Verify the fix"] },
    # ]

The bundled `task` entry's roles are `['tech-lead', '*dev', 'reviewer', 'qa']` — `qa` is already
there. `$(*self)` spreads the bundled list and the merge appends; nothing merges guides by slug,
because `roles` is a plain array and arrays are leaves. So uncommenting the example exactly as
shipped produces a generated skill with **two** `## For Mara Tester (`qa`)` sections:

    $ sq sync
    synced managed files to this squads version
    $ grep -c '^## For Mara Tester' squads/agents/skills/SKILL-000199-sq-task.md
    2

The first is the full bundled guide (Enter/Do/Hand off/Watch for); the second carries only the two
lines from the override, so it reads as a truncated contradiction of the section immediately above
it. `sq check` is clean. This is agent-facing generated content, and it is the *default* outcome of
following the scaffold.

ADR-696 permits the duplication at the token layer — "Compose-only also permits the same base list
to be spread twice, duplicating it; nothing needs it to behave as a set" — and that ruling is about
the splat operator, correctly. It says nothing about a `roles` array carrying two guides for one
slug, which is a property of the *document*, not the operator, and is what the models and the
renderer own. Nothing checks it.

Two things to fix, and they are separable:

1. **Change the scaffold's example slug** to one the bundled `task` entry does not already carry
   (`architect` and `devops` are both free), so the shipped example demonstrates the idiom without
   demonstrating the defect. Cheap, and it is the half that bites an adopter on day one.
2. **Decide whether a duplicate slug in one type's `roles` is legal.** If it is not, that is a
   one-line addition to `_check_slugs`' sibling checks — refuse a repeated slug per type, naming
   both positions. If it is legal, the renderer should merge or the guidance should say what the
   adopter gets, because two sections for one role in a file an agent loads is not a usable
   outcome. My read is that it should be refused: `roles` is semantically keyed by slug, the
   generated skill treats it as keyed by slug (one H2 per slug), and there is no use for two.

Worth noting for whoever fixes it: shadowing a single bundled guide is *not* currently expressible
at all — `roles` being a leaf means the only way to change one guide is to restate the whole array,
which freezes it against bundled improvements. That is the gap the duplicate is a symptom of. It
may be out of scope for this task, but it should be named rather than left for an adopter to find.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-03T12:05:20Z] Elias Python:
  - Fixed, both halves. (1) Scaffold's worked example now spreads a role the bundled task entry does not already carry (architect, not qa). (2) Added a duplicate-slug refusal to the loader's fail-closed validation: a slug appearing twice in one type's roles array (spread-and-re-add, or two hand-written guides for the same slug) is now rejected at load time, naming both positions -- your read that this should be refused, not silently rendered twice, matches the renderer's own one-section-per-slug behavior.
  - Falsified: tests/integration/test_playbook_roles_array_rejects_duplicate_slugs.py -- spreading qa onto task raises 'appears twice'; two hand-written architect guides in one array also raise; and uncommenting the shipped scaffold example verbatim now merges clean with no duplicate slug. Reverting the guard makes the two refusal tests fail with DID NOT RAISE, confirming they test the new check and not something else. Also caught and fixed a second, adjacent bug while editing the scaffold text: the original example's inline table spanned two physical lines, which is invalid TOML (tomllib rejects newlines inside {}) -- would have made the example itself unparseable even without the duplicate slug.
  - Existing tests test_appending_to_one_type_leaves_every_other_types_entry_untouched and test_the_dev_sentinel_role_slug_is_exempt_from_catalog_validation were exercising this exact defect shape (spreading qa/*dev back onto a type that already has it) as their fixture; retargeted both to a slug/type without the collision so they test what they say they test.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — The context half of the playbook seam has no production consumer

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Assignee:** Elias Python
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
**Reproduced by exhaustive grep over `src/`, `tests/` and `clients/`.**

The brief for this work describes the seam as "the bundled playbook stays a module-level immutable
while the merged one lives per-request on the context". The context half exists, is tested, and has
**no production consumer**:

- `RequestContext.active_playbook` — read in exactly one place, `get_active_playbook_spec()`.
- `get_active_playbook_spec()` — referenced only from
  `tests/service/test_context_playbook_isolation.py`. Zero call sites in `src/` outside its own
  definition, and none in `clients/`.
- `_cli/__init__.py::_bind_active_playbook()` — called once, to populate the field nobody reads.

Every real consumer threads `Service.playbook` instead (the backend context, the roster mixin, the
config-integrity validators, `_services/_base`). That is the right carrier and it works. The
context path is a parallel one that was built, proven by test, and never wired up.

Two costs, both real:

**A second resolution path with different failure semantics.** `_bind_active_playbook` wraps
everything in `except Exception: return None`, so a broken playbook override resolves *soft* to the
bundled playbook there, while `resolve_playbook` inside `open_service` raises `PlaybookConfigError`
and hard-stops. Two carriers for one fact that disagree under failure is precisely what ADR-696
argues against when it rejects a second provenance carrier ("Two carriers for one fact would
disagree, with no rule for which wins"). Nothing reads the soft one today, so nothing is wrong
*now* — but the next reader who reaches for the ambient accessor, because it is the one that looks
official, gets the bundled playbook silently where the Service would have refused.

**Work on every invocation for a value nobody reads.** `main_callback` calls
`_bind_active_playbook` unconditionally. Its `resolve_playbook` fast path only applies when the
spec **is** the bundled singleton and no override file exists — so for any squad with a
`.overrides/workflow.toml`, every single `sq` command now runs a full `load_playbook`: reparse the
bundled TOML, merge, build the models, revalidate coverage. `open_service` then does the same work
again a moment later.

Recommendation: either wire a real consumer (if the ambient accessor is meant to be how
`_interactions` reads the active playbook without a `Service` in hand, convert those call sites
and drop the parameter threading), or delete the context field, the accessor and
`_bind_active_playbook`, and keep `Service.playbook` as the single carrier. Shipping both, with
only one live, is the state that goes wrong later. Note that `vulture` will not flag
`get_active_playbook_spec` because the tests reference it — the dead-code scan cannot see this
class of thing, which is why it is worth deciding now.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-08-03T12:14:17Z] Elias Python:
  - Dropped the dead half, per your own recommendation. Deleted RequestContext.active_playbook, _interactions.get_active_playbook_spec(), and _cli._bind_active_playbook() + its call site; Service.playbook stays the single carrier (every real consumer already threaded that). This routes through @tech-lead in the normal author-by-role sense (an architectural removal), but the operator's directive on this review was to disposition all eight myself -- I made the call because the evidence left no real ambiguity: zero production call sites, a documented failure-semantics disagreement with the hard-stop path (soft-fail-to-bundled vs PlaybookConfigError), and a real per-invocation cost for a value nobody read. Flagging the call here for visibility rather than silently taking it.
  - Removed tests/service/test_context_playbook_isolation.py (tested the deleted field/accessor directly; the general RequestContext-isolation pattern stays covered by test_context_spec_and_dir_isolation.py, which was never about this field). Added tests/service/test_service_playbook_is_the_only_active_playbook_carrier.py as a pin: asserts RequestContext carries no active_playbook field and _interactions exposes no ambient accessor, so a re-introduction of the parallel carrier fails a test immediately instead of silently drifting again.
  - F8's second, cheaper half (caching the coverage key set) still stands on its own regardless of this call -- see that finding.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — The scaffold's field-merge rule is false for the roles array

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Assignee:** Elias Python
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
**Reproduced by reading the file the command writes.** The scaffolded
`.overrides/playbook.toml` states, in its own rules list:

    #   - A hand-written field replaces its bundled counterpart; every other field of that guide
    #     (or that type's entry) is inherited unchanged.

The parenthetical is true of a type's entry: write only `overview` under `[types.task]` and
`lifecycle`, `commands` and `roles` are inherited. It is **false of a guide**. `roles` is a plain
array, arrays are leaves and are replaced wholesale, and the merge engine never descends into a
list to match guides by slug. There is no per-guide field merge, so "every other field of that
guide is inherited unchanged" describes behaviour that does not exist.

The practical consequences an adopter hits:

- Writing `roles = [{ slug = "qa", do = ["..."] }]` without `$(*self)` silently deletes the other
  three bundled guides for that type — the array replaced the bundled one.
- Writing `roles = ["$(*self)", { slug = "qa", ... }]` does not *modify* the bundled `qa` guide;
  it adds a second one (see F3).
- Changing one field of one bundled guide is not expressible at all without restating the whole
  array, which freezes it against bundled improvements — the exact thing the splat idiom exists to
  avoid.

This is the sentence that leads an adopter into F3, so it is worth fixing in the same pass. Say
plainly: a type entry's scalar fields merge; `roles` is a list and is replaced wholesale unless you
spread the bundled one with `$(*self)`, in which case you are appending, not editing.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-08-03T12:05:30Z] Elias Python:
  - Fixed, in the same edit as F3 (same file, same rules block). Replaced the false parenthetical with the actual rule: a type entry's SCALAR fields (overview/lifecycle/commands) merge field-by-field; 'roles' is a LIST and is replaced wholesale -- spreading $(*self) appends, it does not edit an existing guide's fields -- and shadowing/editing one bundled guide's field is not expressible without restating the whole array by hand. Added a fourth bullet stating the new duplicate-slug refusal (F3) so the two land together as one coherent, honest rule set instead of the prior single false sentence.
  - No separate test needed beyond F3's: the corrected prose is asserted indirectly by test_the_shipped_scaffold_example_no_longer_duplicates_a_bundled_guide, which parses the file's own worked example and proves it behaves the way the rules now describe.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — The [selected] refusal offers an empty menu of sections

<!-- sq:finding:F6:head -->
**Status:** 🟡 Fixed
**Assignee:** Elias Python
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
**Reproduced.** The refusal is correct — ADR-696 requires that a `[selected]` table in a playbook
override be rejected rather than silently ignored, and `PLAYBOOK_SELECTED_SECTIONS = frozenset()`
achieves that. The *message* is what the empty set produces:

    $ sq check
    error playbook: playbook config invalid: .../.overrides/playbook.toml: selected.types:
    unknown [selected] section 'types' — use one of the accepted [selected] sections: [] —
    see .../.overrides/playbook.toml

"use one of the accepted sections: `[]`" offers the adopter an empty menu. It is the shared
`_specmerge` message template meeting a document that has no deselectable sections, so the
generic wording is right for the workflow override and wrong here.

The adopter needs the reason, which the loader already knows and documents in its own module
docstring: the playbook's active type set is *derived* from the workflow spec's coverage rule, so
dropping a type from `.overrides/workflow.toml`'s `[selected]` drops its playbook entry as a
consequence and there is nothing to deselect here.

Suggested: have the engine special-case an empty accepted set into "this document has no
`[selected]` sections" plus a one-line why, or let the caller supply the sentence. Small, but this
is a fail-closed hard stop on every command, so the message is the entire user experience of it.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-08-03T12:09:10Z] Elias Python:
  - Fixed, at the shared engine (squads/_specmerge.py), not with a playbook-special-case hack: merge_override/apply_selected/_validate_selected_shape/_unknown_key_violations now take an optional empty_selected_hint -- used only when the accepted set is empty, ignored otherwise, so the workflow loader's populated section_names is unaffected. The playbook loader supplies its own reason (coverage is derived from the workflow spec, not declared here) via PLAYBOOK_NO_SELECTED_HINT.
  - Falsified: extended the existing test_a_selected_table_on_the_playbook_override_is_refused + added test_the_selected_refusal_names_the_real_reason_not_an_empty_menu -- asserts the empty-menu string is gone and the real reason ('no [selected] sections to deselect ... coverage') is present. Temporarily un-wired the hint at the call site: the new test failed on the exact old empty-menu string, the plain refusal test still passed (still refused, just the worse message) -- confirms the test targets the message, not the refusal.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — The bundled playbook is immutable by convention, not by type

<!-- sq:finding:F7:head -->
**Status:** 🟡 Fixed
**Assignee:** Elias Python
**Severity:** 🔵 Info
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
**Verified by inspection; no defect today.** Recorded because the seam's safety rests on it.

The bundled playbook is described throughout as a module-level immutable. Structurally it is not:

- `PLAYBOOK: dict[str, ItemPlaybook]` (`_interactions/__init__.py:120`) is a plain module-level
  mutable dict.
- `PlaybookSpec` is `frozen=True`, but pydantic's `frozen` blocks attribute *assignment* only —
  `types: dict[str, ItemPlaybookSpec]` is a mutable dict, so
  `get_playbook_spec().types["x"] = ...` succeeds and would corrupt the singleton process-wide.

I checked and nothing mutates either: `_PLAYBOOK_SPEC` and `PLAYBOOK` are each assigned exactly
once, at lines 88 and 120, and there is no subscript assignment, `.update()`, `.pop()` or
`setdefault` against either anywhere in `src/`. The per-request merge path never touches them —
`_bundled_raw()` reparses on each call, so even the raw mapping handed to `merge_override` is a
fresh object rather than a shared one. The isolation tests assert `before is after` and a full
`model_dump` equality, which is the right proof shape.

So the property holds by discipline, not by type. Given this release's history of a fix breaking
its neighbour, it is worth making the type system carry it: `Mapping[...]` on the model field (or a
`MappingProxyType`) and the same on `PLAYBOOK` would make an accidental mutation a pyright error
rather than a process-wide corruption discovered later. Note that this project already runs a
`tests/meta` guard over module-level mutable state, so `PLAYBOOK` is presumably allowlisted there
as a CODE constant — which is exactly the allowlist entry that stops being true if someone ever
writes to it.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-08-03T12:19:49Z] Elias Python:
  - Assessed properly per the standing rule, not dismissed on the summary line -- and fixed. Made the property real where it can be made real: PLAYBOOK (a plain module dict, never validated through pydantic) is now wrapped in a real MappingProxyType -- a mutation attempt raises TypeError at the call site, at RUNTIME, not just by convention. PlaybookSpec.types is now typed Mapping[str, ItemPlaybookSpec] instead of dict[...]; pydantic keeps the actual runtime value a plain dict regardless (confirmed empirically, not assumed), so that half of the fix is a STATIC guarantee only -- pyright rejects spec.types['x'] = ... because Mapping has no __setitem__. Both are strictly better than the prior all-convention state, and I said which is which rather than overclaiming.
  - On the tests/meta guard question: didn't add a new guard -- the MappingProxyType wrap makes PLAYBOOK invisible to the existing module-level-mutable-state AST guard (MappingProxyType isn't in its mutable-factory list), which is correct, not a gap: that guard exists to catch a bare dict/list/set global; this dict is now genuinely immutable, a stronger property than anything a static grep-shaped guard could assert. Verified tests/meta stays green (the PLAYBOOK allowlist entry is now unnecessary-but-harmless, not stale -- it's still a real module-scope binding, just no longer flagged).
  - Falsified in both directions with tests/unit/test_playbook_singleton_mutation_is_refused_at_runtime.py: reverting PLAYBOOK to a plain dict comprehension makes the isinstance/TypeError assertions fail exactly as expected (DID NOT RAISE); reverting the types field to dict[...] makes the annotation assertion fail, confirming it pins something real, not decorative.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Each playbook load reparses the bundled TOML two or three times

<!-- sq:finding:F8:head -->
**Status:** 🟡 Fixed
**Assignee:** Elias Python
**Severity:** 🔵 Info
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
**Verified by inspection.** Not a defect; a cost worth knowing, and it compounds with F4.

`_interactions/_loader.py` reads and parses the bundled `playbook.toml` more than once per
`load_playbook()` call:

- `_base_raw_for(spec)` calls `_bundled_raw()` -> `_read_bundled_bytes()` + `tomllib.loads`.
- `_check_coverage(...)` calls `_bundled_raw()` again, purely to recover
  `bundled_type_names = set(_bundled_raw().get("types", {}))`.

So a merged load parses the document twice, plus a third read if the override path is taken and
anything else in the chain re-enters. The re-parse is also what keeps the mapping unshared and
therefore safe (see F7), so it is load-bearing at `_base_raw_for` — but the `_check_coverage` call
needs only the *key set* of the bundled `[types]` table, which is a constant of the release and
could be derived once from `_PLAYBOOK_SPEC.types` (or cached module-level) with no aliasing risk.

With F4 unfixed this is paid twice per CLI invocation for any squad that has a
`.overrides/workflow.toml` — once in `_bind_active_playbook` for a value nobody reads, once in
`open_service`. Fixing F4 removes most of it; caching the coverage key set removes the rest.

Flagging it only because `docs/internals.md` already tracks per-command cost, and a fixed
per-invocation TOML parse-and-validate on the override path is the kind of thing that is invisible
until a squad is large.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-08-03T12:23:31Z] Elias Python:
  - Fixed the cheap half, judged the other half correctly fine. _check_coverage's bundled_type_names = set(_bundled_raw().get('types', {})) -- a second full reparse purely to recover a release-constant key set -- is now a functools.cache-wrapped _bundled_type_names(), read from disk at most once per process. Left _base_raw_for's own reparse alone: that one is load-bearing for the isolation guarantee (a fresh, unshared mapping per call), so caching it would trade a real safety property for a cost that's invisible below thousands of items -- not worth it, and I said why rather than just leaving it.
  - Falsified with tests/unit/test_playbook_bundled_coverage_key_set_is_cached.py: monkeypatches the actual byte-read, clears the cache, calls load_playbook three times, asserts exactly 4 reads (3 from the still-uncached _base_raw_for + 1 for the now-cached key set). Reverting the fix reproduces exactly the old cost: 6 reads (2 per call).
  - With F4 dropped, the compounding per-invocation cost this finding flagged (paid twice per CLI command for an override-using squad) is already gone at the source -- this fix is the remainder that stands on its own regardless.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — A guide for a non-roster project role validates then vanishes

<!-- sq:finding:F9:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
**Fixed** on the surfaces you recommended, and the loader is untouched — it stays permissive,
filename-globbing, and readable before the index, for exactly the reason you gave.

New pure predicate `orphaned_playbook_guides(playbook, spec, live_role_slugs=, known_role_slugs=)`
in `_interactions`, returning every `(item_type, role_slug)` pair whose guidance the renderer will
drop. Two consumers, one shared wording (`orphaned_playbook_guide_message`) so they cannot drift:

- **`sq check`** — a new squad-global validator `playbook_guide_role_live`, warn-level, alongside the
  orphaned-skill rule it mirrors. Names the type, the slug and both ways out.
- **`sq sync`** — the same message on the `skipped` channel that already carries the orphaned-skill
  notice, emitted after `write_managed` and computed from the very `roster` that gating used, so the
  report cannot disagree with the file it just wrote.

On being consistent with the skill side: I went **report, not refuse**, deliberately. The skill side
can refuse because `--unlink` is a step the operator can actually perform inside that transition.
Here neither remedy is — activating a role is a different command, and sq never rewrites an adopter's
`.overrides/playbook.toml`. A refusal would be the lock-out the withdrawn default-role clause was
withdrawn for. It is also report-only because refusal only covers retirement, while the
scaffold-then-forget order is the *other* trigger and has no transition to hang a refusal on; one
warning covers both.

Two things beyond your write-up:

- **A retired *bundled* role is included.** Not exempt — that is the same retirement event. The
  exemption is narrower and exactly the one you drew: a bundled slug this squad has *no roster entry
  for at all* (the `--roles minimal` precedent). "Never installed" and "retired" are distinguishable
  from `roster_all`, so the rule uses that rather than the coarser bundled/project split. Pinned in
  both directions, because a rule that fired on a clean minimal squad's seven bundled guides would be
  noise an adopter learns to ignore.
- **The malformed-`.toml` and `NOTES.toml` stems need no separate handling** — their stems resolve to
  no live role, so the one rule already reports them. Both driven.

Verified the drop itself rather than assuming it: the guide text is absent from the generated
`sq-task` skill while the role is unactivated and present after `sq role activate`, asserted in the
same test as the warning.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — check still masks both findings when both overrides are broken

<!-- sq:finding:F10:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F10:head:end -->

<!-- sq:finding:F10:body -->
**Reproduced. Pre-existing, and out of TASK-720's scope** — recorded because it is now the only
remaining path by which F2's exact symptom returns, and because the fix's own reasoning names it.

F2's fix re-resolves the merged workflow spec in the `PlaybookConfigError` branch. Verified
holding: with a valid workflow override declaring a custom `incident` type, an `INC-19` item on
the board, and a playbook-only breakage, `sq check` now reports

    error playbook: playbook config invalid: Invalid playbook:
      - types.incident: overview is empty — see .../.overrides/playbook.toml

and exits 3. No phantom type error. That is exactly right.

The shape survives in two configurations, because two other lines still fall back to
`bundled_spec()` while an item of a project-declared type is on the board:

**(b) both overrides broken** — `load_workflow_spec` fails, so the branch's own inner
`except SquadsError: fallback_spec = bundled_spec()` fires:

    $ sq check
    error: item INC-19 has type 'incident', which the active spec no longer declares; migrate or
    re-type this item before it can load again (or run `sq repair` if the index itself is merely
    stale)
    $ echo $?
    1

Neither the workflow finding nor the playbook finding is printed.

**(b2) workflow-only breakage** — same output, via the sibling `except SquadsError:` branch's
`Service(sp, spec=bundled_spec())`, which predates this work and was untouched.

**(c) a workflow override that drops a type with live items** — `load_workflow_spec` *succeeds*
here (the live-corpus cross-check that would refuse it lives in
`validate_against_index_fail_closed`, which this path deliberately skips), so `fallback_spec` is
the merged spec, which does not declare `incident` — same crash. Driven with the playbook
override removed entirely, so this one is independent of the playbook feature.

The general rule underneath all three: **`sq check` can report nothing at all whenever its chosen
fallback spec cannot load the index.** The fix reasoned this out precisely ("any item of a
project-declared type then looks undeclared to `svc.check()` and drowns out the real finding") and
then left two copies of the same fallback in place.

Not a blocker on this review — (b2) and (c) are reachable without the playbook and belong to
`check`'s own resilience rather than to this feature. Worth its own ticket: `check` should be able
to report its collected config findings even when no spec can load the index (report and stop,
rather than raise), which is the same "a reporter that stops at the first problem fails when it is
most needed" argument TASK-674 already won for the per-file case.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-08-03T15:21:47Z] Elias Python:
  - Fixed on the general rule you named, not per-configuration: `sq check` no longer lets the corpus scan discard the config findings it already collected. The scan is wrapped, and its own failure becomes an error-level `corpus` finding alongside them — report and stop, never report nothing. Exit code moves from a generic 1 to the ordinary errors-found 3.
  - All three of your configurations driven, before and after. Before: one unrelated `item INC-19 has type 'incident'...` line and exit 1, with neither config finding printed. After: `error corpus: could not scan the corpus: <the real reason>` plus `error workflow: workflow config invalid` and exit 3. One correction to your (b): with both overrides broken it takes the general `SquadsError` branch, not the PlaybookConfigError one — the workflow is what `get_service` fails on first, so the playbook finding is not separately printed. The masking is gone either way; I did not want to claim "both findings print" when I only drove one surviving.
  - Deliberately not done, because it is the pre-existing wording and outside this finding: the two `bundled_spec()` fallbacks are still two, and in configuration (c) the surviving finding is `workflow config invalid — run `sq workflow lint`` while lint reports clean (the spec loads; it is the live-corpus cross-check that refuses). That pointer is a false remedy of the same family as REV-733 F13 — @manager, worth its own ticket.
  - Pinned in the new `tests/integration/test_check_reports_its_config_findings_when_the_corpus_cannot_load.py`: both halves parametrized over the three configurations, plus a clean-squad negative (no new error on a healthy board) and a broken-config-but-readable-board case so the fix cannot read as "any config error means the corpus failed". Falsified: reverting reddens 6 of 8.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — The scaffold does not say a project role slug is now accepted

<!-- sq:finding:F11:head -->
**Status:** 🟡 Fixed
**Severity:** 🔵 Info
<!-- sq:finding:F11:head:end -->

<!-- sq:finding:F11:body -->
**Fixed**, with your suggested wording and the ordering constraint carried, as you asked.

The scaffold's slug rule now reads:

    Every role slug must be one of: a bundled catalog role, the "*dev" sentinel (matching any
    <tech>-dev role), or a project role you have defined under .overrides/roles/<slug>.toml.
    A project role must also be ACTIVATED (`sq role activate <slug>`) for its guidance to
    reach the generated skill — a guide whose slug names no live role loads fine but is
    dropped from the skill, and `sq check` warns about it until you activate the role or
    remove the guide.

So the two halves land together: the adopter learns the capability *and* the sequence it has to be
done in, and the sentence points at the same warning the check rule now emits.

Pinned claim-by-claim rather than as a golden blob — each of the three legal slug sources, the
activation step, and the check warning is its own assertion, plus a negative one for the removed
absolute ("must be in the role catalog"), since adding the new sentence while leaving the old one
would satisfy every positive assertion and still tell the adopter their project role is invalid. A
fourth test guards the blast radius: the scalar-vs-list split, the append idiom and the
duplicate-slug refusal are all still stated. Falsified by reverting the line — five of seven go red.

`docs/overrides.md` needs the same correction and is **not** mine to make; flagged to the
coordinator for the tech-writer.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — The new guide warning fires on a stock squad and cannot be cleared

<!-- sq:finding:F12:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F12:head:end -->

<!-- sq:finding:F12:body -->
**Reproduced. A new defect created by F9's fix** — the release-risk you flagged, and it is real,
though narrower than "noisy on a stock squad".

Your two checks hold. A stock `sq init --default-names` squad: `sq check` clean, exit 0; `sq sync`
exit 0. A `--roles minimal` squad: clean, exit 0 — the bundled-slug-with-no-roster-entry exemption
does its job. And every project-role case works exactly as designed: scaffolded-but-not-activated
warns, `sq role activate` clears it, retiring it warns again.

The gap is the third combination, which neither check covers: **a bundled role that this squad
did install and has now retired, on a squad with no playbook override at all.**

    $ sq init --default-names          # all roles, no overrides anywhere
    $ sq check                         -> ✓ no issues     (exit 0)
    $ sq role tech-writer status Archived
    ROLE-8 → Archived
    $ sq check
    warn: playbook guide for role 'tech-writer' on type 'guide' names no live role, so its
    guidance is dropped from the generated `sq-guide` skill — activate the role
    (`sq role activate tech-writer`), or remove the guide from `.overrides/playbook.toml`
    under `[types.guide]`
    $ test -f squads/.overrides/playbook.toml && echo yes || echo NO
    NO

`sq sync` prints the same line. Three problems, in order of weight:

**The named remedy does not exist.** There is no `.overrides/playbook.toml`, and the guide is not
in one — it is in the bundled document, which sq never writes. This is the third message in this
batch to send an operator to a file they do not have (REV-733 F2's `.overrides/workflow.toml`, now
this).

**The warning is unclearable.** Driven: scaffolding an empty `.overrides/playbook.toml` does not
clear it (the guide still comes from the bundled base). Only `sq role tech-writer status Active`
clears it. So the only way out of the warning is to undo the retirement — and retiring a role is a
first-class, documented, reversible operation this very release added. Five bundled roles are named
in the bundled playbook (`product-owner`, `architect`, `tech-lead`, `qa`, `reviewer`, plus
`tech-writer`), so any adopter who retires one acquires a permanent warning.

**The exemption keys on the wrong thing.** It asks "does this squad have a roster entry for the
slug", which distinguishes never-installed from retired. But from the adopter's side those two
states are the same event with the same non-remedy: the bundled document names a role they do not
have, and they cannot edit the bundled document. What actually separates an actionable guide from an
unactionable one is **who wrote it** — a guide present in `.overrides/playbook.toml` is theirs and
they can remove it; a guide that exists only in the bundled base is squads' own graceful
degradation, exactly as it is for a never-installed role.

Suggested: exempt a guide whose `(item_type, slug)` pair is not present in the project's override
document, rather than exempting by roster-entry presence. The loader already reads the raw override
mapping, so the pair is available; `_raw_shadows_bundled` in `_interactions/_loader.py` is the
nearest existing precedent for asking "did the adopter write this". Then the retired-project-role
case (which is the one you actually want reported, and which works today) keeps warning, and the
retired-bundled-role case goes back to being silent degradation with no remedy to name.

If that is too much for this release, the minimum is to stop naming a file that may not exist:
branch the remedy sentence on whether `.overrides/playbook.toml` is present, and for the bundled
case say plainly that the guidance is squads' own and the only way back is to reactivate the role.

Not a gate failure — it is a `warn`, `sq check` still exits 0, and this repo's own board is clean
at `e59c10b`. But this project's standing rule is that a warning is a defect to fix rather than an
advisory to explain away, and an unclearable warning produced by a documented operation is the
worst kind: the adopter's only options are to live with it or undo their change.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-08-03T15:21:34Z] Elias Python:
  - Fixed with your diagnosis, not the fallback: the exemption now keys on **who wrote the guide**. `playbook_override_guide_pairs(squad_dir)` in `_interactions/_loader.py` reads the raw override document (before any merge, so provenance survives) and returns the `(item_type, slug)` pairs it declares literally; `orphaned_playbook_guides` takes that as `override_guides` and the roster-entry `known_role_slugs` parameter is gone.
  - Driven, seven shapes: stock squad + `sq role tech-writer status Archived`, no override -> check and sync both silent, exit 0 (your headline shape). `--roles minimal` -> silent. Scaffolded-not-activated project role -> warns; activate -> clears; retire -> warns again. Adopter restates a bundled guide then retires the role -> warns, and the file the remedy names genuinely exists. Splat-only override (`roles = ["$(*self)"]`) -> silent, because a splat names no slug of its own and the guides it spreads are still ours. Malformed override TOML -> no traceback.
  - One thing your finding named that I found also broken, and fixed here rather than leaving it: the message's `sq role activate <slug>` remedy is a no-op for a retired role. Driven — `activate_role` returns an existing roster entry untouched, so it prints "activated Theo Writer (ROLE-8)" and leaves the status `Archived`. You had noted only `status Active` clears it; that is now what the message says. `orphaned_playbook_guide_message` takes `retired`/`live_status` and prints `sq role <slug> status <live-initial>` for a slug with an entry, `sq role activate <slug>` for one without — reusing the spelling `_retired_participant_hint` already uses, and reading `spec.live_initial(ROSTER_ROLE)` rather than hard-coding Active.
  - Pinned in `tests/integration/test_playbook_guide_dropped_for_a_non_live_role_is_reported.py`: the retired-bundled case asserts silence AND that no override file exists (so the test cannot stop covering the case it exists for); the restated case asserts it warns; the splat case asserts the override is in force and still silent; a remedy test drives `activate_role` being a no-op on a retired role and then drives the named transition clearing the report. Plus a CLI smoke, since the report came in at the CLI. Falsified: removing the exemption reddens 7.
  - Two existing tests encoded the old keying and were rewritten, flagging for @reviewer: `test_a_guide_for_a_retired_bundled_role_is_warned_about_too` asserted the defect, and `test_a_guide_on_a_type_the_spec_has_dropped_is_not_reported_per_role` relied on a retired bundled role producing warnings with no override. On the second — an override declaring a guide on a dropped type is now refused at load (driven: the splat has no bundled counterpart, or coverage rejects the type), so the per-role pile is unreachable by two independent mechanisms and the test drives both.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T11:10:06Z] Paul Reviewer:
  - Verdict: ChangesRequested. The merge engine, the fail-closed set, the attribution split and the reclaim-scope fix all hold — I drove each. Both blockers are in the seam between this feature and its neighbour, which is where this release has put every defect.
  - Blocking F1: a custom role created by the shipped path (sq override scaffold --new sre, sq role activate sre, live ROLE-19) cannot be given playbook guidance — _check_slugs validates against the bundled get_catalog() singleton. That is ADR-696 4a stated headline mechanism, it is unreachable, and the refusal is a hard stop for every command. Same root cause blocks a per-dev slug.
  - Blocking F2: sq check catches PlaybookConfigError and then rebuilds its fallback Service on the BUNDLED workflow spec, discarding a merged one that loaded fine. With a custom type declared and a playbook-only breakage, sq check dies with "item INC-20 has type incident, which the active spec no longer declares" and never prints the playbook finding. get_service_bypassing_index_cross_check already does this correctly; check should use the same ladder. The existing attribution test passes only because its squad has no workflow override worth losing.
  - F3 (medium) is reachable from the shipped scaffold example as written: appending a qa guide to task duplicates the bundled one, giving the generated skill two "For Mara Tester (qa)" sections with sq check clean. F4 (medium): the RequestContext.active_playbook half of the seam has no production consumer at all — only tests — while costing a full playbook resolve on every invocation for override-using squads.
  - Reclaim-scope reasoning verified and correct: bundled-blindness is load-bearing and the three varying functions are threaded at every production site. Two requests cannot see each other. Attribution cannot cross. @architect for F1 (the slug authority ruling, and ADR-696 4a should not be left asserting a mechanism that does not run), @python-dev for F2/F3/F5/F6, @tech-lead for the F4 wire-it-or-drop-it call.
- [2026-08-03T13:18:49Z] Paul Reviewer:
  - Delta pass at 12540ce. Verdict: still ChangesRequested, on one new medium finding created by the F1 fix.
  - Dispositions that hold, driven end to end. F1: sq override scaffold --new sre, activate, then a guide via the append idiom — check clean at exit 0, sync clean, one For Sam Reliability section in the generated skill, sre preloading sq-task in .claude/agents. F2: with a valid workflow override declaring a custom incident type, an INC-19 item on the board and a playbook-only breakage, check now reports the playbook finding and exits 3, no phantom type error. F3: the duplicate slug is refused with a message that names both positions and the way out, and the shipped scaffold example moved off qa onto architect, so the defect is no longer reachable from the shipped text. F5: the scaffold merge rules are now accurate on the scalar-vs-list split. F6: the empty-menu hint is replaced by the real reason. F4: RequestContext.active_playbook, get_active_playbook_spec and _bind_active_playbook are gone with a pin test, and the only get_playbook_spec uses left in src are the three documented bundled fallbacks. F7: PLAYBOOK is a MappingProxyType and PlaybookSpec.types is a Mapping. F8: the cache is zero-argument over the bundled document only and never reads the spec, so it cannot leak across a spec change — safe by construction, not by discipline.
  - Blocking F9 (medium): project_role_slugs globs filenames and never parses or consults the roster, while the renderer gates on live roster membership — so a guide for a scaffolded-but-not-yet-activated role, or one retired later, validates clean and its guidance silently vanishes from the generated skill. Driven both triggers plus resync in each direction; check stays clean throughout. A malformed .toml and a stray NOTES.toml likewise contribute their stems as valid slugs. Keep the loader permissive (it must be readable before the index) and add the gap to check next to the orphaned-skill rule it mirrors — compare how loudly this release treats the skill side of the same retirement.
  - F10 low: the masking shape survives when both overrides are broken, and independently when a workflow override drops a type with live items — both via a fallback to bundled_spec that predates this work. Reachable without the playbook, so out of scope here, but worth its own ticket: check should report its collected config findings even when no spec can load the index. F11 info: the scaffold still says a slug must be in the role catalog, which is the opposite of what F1 just built.
  - @python-dev for F9 and F11. @architect — F1 works now, so ADR-696 4a describes something real; worth confirming the slug-authority ruling (override file versus live roster) is recorded where the next implementer will find it, since F9 is a disagreement between two answers to that question.
- [2026-08-03T14:10:23Z] Elias Python:
  - F9 and F11 both fixed. The loader stays permissive exactly as you argued — the gap moved to `check` (a new warn-level squad-global validator `playbook_guide_role_live`) and to `sq sync` (the same `skipped` channel the orphaned-skill notice uses), off one shared predicate `orphaned_playbook_guides` and one shared message so the two surfaces cannot drift.
  - Report, not refuse, and here is the reasoning against your consistency point: the skill side can refuse because `--unlink` is performable inside that transition. Neither remedy here is — activation is a different command and sq never rewrites an adopter override file — so a refusal would be a lock-out. Refusal also only covers retirement, while scaffold-then-forget has no transition to hang one on; the one warning covers both triggers.
  - Went slightly wider than the finding on one axis: a retired *bundled* role is included, since that is the same event. The exemption is exactly the one you drew — a bundled slug with no roster entry at all (the `--roles minimal` precedent). `roster_all` distinguishes "never installed" from "retired", so the rule uses that rather than a coarse bundled/project split. Pinned in both directions; a rule firing on a clean minimal squad would be noise.
  - The malformed-`.toml` and `NOTES.toml` stems need no extra handling: their stems resolve to no live role, so the same rule reports them. Both driven, plus the `*dev` exemption and a dropped type (which I found is already filtered out of the merged playbook, so my own type guard is defensive — the test says so rather than claiming the guard earns it).
  - Verified the drop itself, not just the warning: the guide text is absent from the generated sq-task skill while unactivated and present after `sq role activate`. 12 integration tests + 7 on the scaffold prose; both falsified.
  - F11 done with your wording plus the ordering constraint. `docs/overrides.md` needs the same correction and is not mine — flagged for the writer. @reviewer
- [2026-08-03T14:17:47Z] Elias Python:
  - Writer-facing, not mine to write: `docs/overrides.md` states the playbook role-slug rule alongside the scaffold and needs the same correction — the three legal slug sources plus the activation requirement and the new `sq check` warning. Adopter-visible surfaces this landed: a new warn-level `sq check` class and a new `sq sync` skip message (both exit 0, driven).
- [2026-08-03T14:34:29Z] Theo Writer:
  - F11 writer half done: `docs/overrides.md` now carries the corrected slug rule, matching the scaffold prose. The old absolute ("every slug must be a real role, apart from `*dev`") is replaced by the three legal sources — bundled catalog role, `*dev` sentinel, or a project role under `.overrides/roles/<slug>.toml` — as its own bullet, plus a second bullet for the activation requirement, the ordering, and the new `sq check`/`sq sync` warning with both remedies and the exit-0 fact.
  - Went one step past the bullet because the ordering constraint is a sequence, not a fact: the "Guidance for a role you invented" section now has the scaffold → activate → sync → check run of commands, states that writing the guide before activating is fine (that IS the order the scaffold suggests), and covers the reverse direction — retiring a role leaves its guides behind and can produce several warning lines at once, one per type. Drove the documented sequence verbatim in a sandbox: warning present before activation with exit 0, `✓ no issues` and the guidance in the generated sq-task skill after.
  - Verified the rule itself both ways rather than translating: guidance absent from the generated skill while the role is inactive, present after `sq role activate`, absent again after `sq role <slug> status Archived`, with the warning tracking each transition. Also confirmed the two exemptions hold — a `--roles minimal` squad is clean, and a retired *bundled* role IS reported (one line per type), which means the warning fires with no override file at all.
- [2026-08-03T14:34:37Z] Paul Reviewer:
  - Third pass at e59c10b. F9 holds for the cases it was written for and I re-drove all three: a project role scaffolded but not activated warns, sq role activate clears it, retiring it warns again. The widening you mention (_scan_records on a non-str id) is covered under REV-733.
  - Blocking F12 (medium, new): your two checks hold — stock squad clean at exit 0, --roles minimal clean — but they do not cover the third combination. A bundled role this squad DID install and has now retired, on a squad with NO playbook override, warns: sq init --default-names then sq role tech-writer status Archived produces the warning, and .overrides/playbook.toml does not exist. Three problems: the named remedy points at a file the adopter does not have; the warning is unclearable (I drove it — scaffolding an empty override does not clear it, only reactivating the role does); and retiring a role is a first-class documented reversible operation this release added, with six bundled roles named in the bundled playbook. The exemption keys on "does this squad have a roster entry" when what actually separates an actionable guide from an unactionable one is who wrote it — a guide only in the bundled base is squads own degradation, exactly as for a never-installed role. Body has the suggested predicate and a minimum fallback.
  - On your judgement question about the unreachable item_type not in spec.items guard: keep the guard, keep the honest note, and I would not have accepted a test that claimed coverage instead. The docstring says removing the guard does not redden the test and asserts at the behaviour rather than the mechanism, which is the right layer — a merged playbook being spec-filtered is a property of the loader, not of this predicate, so pinning it here would pin it in the wrong place and break when the loader changes. The guard is not dead code: orphaned_playbook_guides takes a playbook and a spec as independent arguments, so pairing the BUNDLED playbook with an overridden spec is a legal call today, and _write_item_skills keeps the identical defence for the identical reason. A defence that is currently unreached because every caller happens to pass a pre-filtered value is a precondition made explicit, not dead code — the alternative is a function whose correctness depends on a caller invariant nobody wrote down. What I would not accept is the guard without the note.
  - F10 is still Open from the last round (its own ticket, reachable without the playbook). @python-dev for F12.
- [2026-08-03T15:22:07Z] Elias Python:
  - F10 and F12 both Fixed — see each finding. Same gate results as REV-733 (pyright/ruff clean, 3019 tests pass, each fix falsified).
  - Adopter-visible, for @tech-writer to route: (1) retiring a bundled role no longer produces an unclearable playbook-guide warning — the report is now scoped to guides the adopter declared in `.overrides/playbook.toml`; (2) when the report does fire, it names the command that actually revives the role (a status transition for a retired one, `sq role activate` for one never activated); (3) `sq check` now reports its config findings even when the corpus cannot be scanned, and exits 3 rather than 1 in that case.
  - @manager one follow-up ticket needed, recorded on F10: `check` still points a configuration-(c) failure at `sq workflow lint`, which reports clean for it — the spec loads and it is the live-corpus cross-check that refuses. Same false-remedy family as REV-733 F13, but it is pre-existing wording outside F10s scope.
- [2026-08-03T15:32:15Z] Paul Reviewer:
  - Targeted delta at 8473abf. Both widenings on this review hold; nothing new found here.
  - Correction to my own read on F10, and you were right to make me settle it rather than concede: HE is right and I was wrong. open_service loads the workflow spec first (_services/_service.py line 310) and only reaches resolve_playbook at line 320, so when BOTH overrides are broken the workflow load raises a plain SquadsError and PlaybookConfigError is never constructed. Driven, all three combinations: playbook-only reports level error item playbook; both-broken reports item workflow; workflow-only reports item workflow. So case (b) takes the general SquadsError branch, not the PlaybookConfigError branch as my F10 body said. The consequence, which I will not file: that branch inner except SquadsError -> bundled_spec is therefore defensive-only, same class as the item_type not in spec.items guard I endorsed on this review, so it is consistent rather than dead.
  - F10 fix verified working: in all three combinations the config finding now prints instead of being discarded, and where the corpus scan itself fails it becomes its own finding — a corrupt .squads.json behind a VALID workflow override reports exactly one thing, error corpus could not scan the corpus ... run sq repair, with no false workflow pointer.
  - F12 re-key verified on the case it was re-keyed for: a guide the adopter wrote in .overrides/playbook.toml with no roster entry yet reports "activate the role (sq role activate sre)", and after activate-then-retire it reports "reactivate the role (sq role sre status Active)". Both name the command that actually works — I ran the second and it cleared the warning. The provenance read via playbook_override_guide_pairs is the right discriminator and it skips splat-refs, so a bundled guide pulled in by $(*self) stays silent.
  - The behaviour claim outside the finding is real and I drove it: on a role at Archived, sq role activate <slug> prints "activated Theo Writer (ROLE-8)" and the status stays Archived (measured through sq list -t role -a --json, not the rendered body). So the old message named a command that reports success and does nothing. Disposition below in my report to @manager — it is a bug in sq role activate, outside both reviews and untracked; I searched and found nothing.
- [2026-08-03T15:47:25Z] Catherine Manager:
  - Approved as second party. Twelve findings, zero Open. The reviewer re-drove every disposition across three passes and both of the last rounds widenings verified: the retired-role exemption re-keyed on authorship, and the sq role activate no-op it exposed is now tracked as BUG-739 rather than absorbed silently.
  - One disposition reversal worth the record: the reviewer stated in F10 that the both-overrides-broken case takes the PlaybookConfigError branch, and the dev reported it takes the general SquadsError branch. The reviewer traced open_service, found the workflow spec loads before resolve_playbook is reached, and corrected his own finding against himself. The consequence he chose not to file -- that the inner fallback is therefore defensive-only -- is consistent with the unreachable-guard call he endorsed earlier in the same review.
- [2026-08-06T20:26:21Z] Theo Writer:
  - Withdrew the false paragraph from the 0.13.0 playbook-guidance entry and re-checked the whole entry against shipped behaviour, not against the brief I wrote it from. Reproduced QA exactly: on a pristine synced squad `sq role reviewer status Archived` prints only `ROLE-4 → Archived`, the guidance IS dropped (no `## For` section survives in the generated sq-review skill), and `sq check` then says `✓ no issues` at exit 0.
  - The F12 fix narrowed more than the one paragraph, so two further sentences were wrong or unsupported and are now corrected. (1) The whole entry has to be scoped: the rule reports only guides present in the adopter's own `.overrides/playbook.toml`, read from the raw override for provenance. The headline now says "playbook guidance YOU wrote". (2) The old closing sentence exempted "a bundled role your squad never installed" and credited a `--roles minimal` squad's quiet to that exemption — the exemption it named no longer exists, replaced by the authorship test, so the sentence was right by accident. Dropped; it is implied by the scope now.
  - Drove the boundary rather than assuming it, and it is not bundled-vs-project as the old prose implied: retiring a BUNDLED role you wrote a guide for IS reported (devops + an adopter-written task guide -> warned). What is exempt is squads own bundled guidance for a non-live role. Also drove the two remedy spellings, which the entry previously flattened into "activate the role": a slug with no roster entry gets `sq role activate <slug>`, a retired one gets `sq role <slug> status Active` — and per the code the wrong one of those prints success while changing nothing, so the entry now says the message picks. All four reachable shapes driven: not-yet-activated, retired project role, retired bundled role with an adopter guide, stray `.overrides/roles/` file.
  - One probe error worth recording: my first attempt at the retired-bundled-role case used `reviewer`, which already has a bundled task guide, so `"$(*self)"` plus re-adding it hit the duplicate-slug refusal and looked like the rule failing. The refusal was correct and my probe was wrong — re-ran with `devops`, which has no bundled task guide.
<!-- sq:discussion:end -->
