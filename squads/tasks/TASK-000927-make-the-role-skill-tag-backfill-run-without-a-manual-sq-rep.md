---
id: TASK-927
sequence_id: 927
type: task
title: Make the role/skill tag backfill run without a manual sq repair
status: Done
parent: FEAT-906
author: tech-lead
assignee: python-dev
refs:
- ADR-880:implements
- REV-926:addresses
subentities:
- local_id: ST1
  title: Wire an automatic backfill trigger into the upgrade path
  status: Done
  assignee: python-dev
  story: US5
- local_id: ST2
  title: Convert the sweep's bare AssertionError to SquadsError, skip-and-report per
    file
  status: Done
  assignee: python-dev
  story: US5
- local_id: ST3
  title: Gate role/system-skill re-seeding on the view still being declared
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST4
  title: Add ROLE_DEFINITION_VIEW_NAME and fix the adjacent false docstring
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST5
  title: Restore sq role show's unresolvable-role advisory
  status: Done
  assignee: python-dev
  story: US1
created_at: '2026-09-04T14:39:46Z'
updated_at: '2026-09-10T09:40:24Z'
---
<!-- sq:body -->
## Scope

Fixes REV-926 F1, F4, F5, F7, F8 (the `example_assignee_slug` instance), and F9 — the tag-
convergence surface TASK-922/923 built (`_maintenance.py::_repair_body_tag` /
`_converge_body_tag`), plus its two CLI callers (`_cli/_role.py`, `_cli/_skill.py`) and
`_interactions/__init__.py`.

### F1 — the upgrade path must not depend on a manually-run `sq repair`

The convergence mechanism TASK-922/923 built is sound (REV-926 confirms it, driven). The gap is
purely reachability: `run_pending_migrations` only calls `repair()` when a schema migration
actually applies (`applied` non-empty). 0.15 did not bump `SCHEMA_VERSION`, so a 0.14.x adopter's
`sq migrate up` says "nothing to migrate" and never sweeps. `sync()` stamps `squads_version` to
the running package version (`_stamp_version`, called at the end of `sync()`) without ever
touching a role/skill body — so the one command the version-drift notice itself tells the operator
to run ("squads X detected... Run `sq sync` to refresh them") does not fix the emptied definitions
either.

Wire the existing body-tag convergence step (the part of `repair()`/`_repair_body_tag` that
converges role/system-skill/per-item-type-skill bodies onto their tag) into the ordinary upgrade
path, keyed on `squads_version` drift rather than `schema_version` drift — `sync()` is the natural
hook, since its own job is "regenerate all tool-owned managed files to the current version" and a
role/skill body's tag is exactly that. Do **not** fold in the rest of `repair()` (index rebuild,
renumbering, retired-region stripping) — scope precisely to the convergence step, reused, not
`repair()` wholesale, so this doesn't also turn every `sq sync` into an F10-shaped index-diff
event.

Two secondary defects in the same failure, fix alongside:
- The role's empty-body hint text is `(empty — set it with `body`)`. There is no `body` verb in
  the `sq role` addressing group and `set_body` refuses a role body unconditionally — the hint
  names an action that cannot be taken. Once the automatic path lands this hint should rarely
  fire, but it must not lie when it does.
- The skill's empty-body hint blames "the item type this skill described is no longer declared."
  For `squads`/`sq-task` on a squad where both are perfectly declared, that diagnosis is false —
  `_cli/_skill.py`'s hint branches on `system` alone and cannot distinguish "no tag seeded" from
  "type dropped." Both hints must name what is actually true of the item in front of them.

If full automation genuinely cannot be made safe within this task's scope, the fallback is: name
the remedy somewhere an upgrading adopter will actually see it (the version-drift notice text, or
a new `sq check` advisory) rather than the current clean "no issues" / "synced" reports. Report
which of the two you landed and why in the handoff — this is the call REV-926 asked the tech lead
to make about *scope*, and it left the *mechanism* choice to you as the implementer closest to the
code.

### F4 — the sweep must not abort on one bad file

`_converge_body_tag` raises a bare `AssertionError` when a role's or permanently-system skill's
`sq:body` holds marker-shaped content it refuses to guess at. The guard itself is correct and
load-bearing (keep it, and keep its falsifying test) — the defect is the exception class and the
blast radius. Per `CLAUDE.md`: "User-facing errors subclass `SquadsError`... Raise those, not bare
exceptions." Wrap it as a `SquadsError` with the same message text, and make the sweep loop that
calls it skip-and-report one bad file (`skipped ROLE-000001: ...`) rather than aborting the whole
corpus-wide pass mid-transaction. This matters more once F1 lands, because the sweep then runs on
every upgrade rather than only when an operator remembers to type `sq repair` — one damaged file
should not be able to re-empty every other role and skill in the squad by blocking the pass that
would have fixed them.

### F5 — re-seeding must respect a dropped view declaration

`_repair_body_tag`'s per-item-type branch already gates on the type still being declared
(`item_type_for_skill_slug` resolving) before naming a tag. Its role and system-skill branches do
not consult `self.spec.views` at all — they return a bare literal / a fixed dict unconditionally.
So dropping `role_definition` via a `.overrides/workflow.toml` `[selected]` block (a documented,
supported way to drop declared vocabulary) makes every role file fail `sq check` with a dangling-
tag error, and running `sq repair` — the tool's own recovery command — re-converges the tag right
back in, because the classifier doesn't know the view is gone. Nine unfixable errors on files the
adopter never authored, with no supported way to remove the tag (no `view` verb on `sq role`,
`set_body` refuses a role body). Gate the role and system-skill branches on the view being present
in `self.spec.views`, exactly the way the per-type branch already gates on the type — one
condition, and all three branches then agree about what "the view still exists" means.

### F7 / F8 — the role view name should be a shared constant, and the docstring beside its family should tell the truth

Two small, adjacent fixes in `_interactions/__init__.py`:

- **F7.** `interactions.SYSTEM_SKILL_VIEW_NAMES` and `interactions.ITEM_SKILL_VIEW_NAME` are each
  declared once and documented as "the two writers this table is shared between." The role's view
  name is not: `"role_definition"` is a bare literal independently in `agents/role.md.j2`'s seeded
  tag, `ServiceCore._create_core`'s reseed, and `_repair_body_tag`'s classification — three places
  that must agree, with nothing pinning them to `[views.role_definition]` in `_specs/workflow.toml`,
  the declaration all three are supposed to match. Add a `ROLE_DEFINITION_VIEW_NAME` constant
  beside the other two; use it everywhere the literal appears today; add (or extend) a test that
  pins the template's seeded tag, the reseed, and the classifier's returned name to the constant,
  so a rename can't silently produce a dangling tag in every newly-activated role.
- **F8 (one of two narration instances; the other is TASK-Y's).** `example_assignee_slug`'s
  docstring (`_interactions/__init__.py`) says it accepts a plain dict mapping "every caller
  **before this collapse**" — a build-process reference a reader with no diff cannot resolve — and
  the parenthetical is false in the present: `templates/agents_md/agents_section.md.j2:44` still
  calls it with the backend's dict-shaped `roles_data`. Rewrite to name the two live callers (the
  dict-shaped `agents_md` caller and the `RoleView`-shaped view caller) in the present tense, no
  history.

### F9 — `sq role show` lost its unresolvable-role advisory

Before TASK-922, an activated role whose catalog resolution raised `RoleNotFoundError` printed
`(the definition for <slug> could not be resolved — run `sq check` to see why)`. Now the same role
renders a plausible-looking definition, because the tag's `role` source degrades through
`RoleDef.from_extra_or_item` instead of raising. That degrading behaviour is fine and is not to be
undone — but it removed the only place the CLI pointed a user at the diagnosis for a broken
`.overrides/roles.toml`, and a nearby comment in the same function still asserts the opposite
intent ("an invalid override must be reported, never quietly replaced"). Restore a one-line
advisory in `show_role` when the role fails to resolve (the branch that computes `r is None` is
still there) — the panel above still degrades to item fields correctly; only the definition pane's
silence needs fixing.

## Acceptance

1. **F1's driven upgrade path.** Build a real 0.14.x-shaped corpus (role and system-skill `sq:body`
   regions present and empty — the exact shape TASK-922's own manual repro used: `sq init --roles
   all`, `sq dev add --tech python`, `sq sync`, at the pre-collapse commit or with the tags
   manually stripped to reproduce the pre-collapse shape), then run only the ordinary upgrade
   action(s) your fix wires to (never `sq repair` directly) against the current build. Assert every
   role and system-skill definition renders. If a manual step is genuinely unavoidable, assert
   instead that the remedy is named somewhere the operator sees it (the version notice or `sq
   check`), not that the run reports clean success.
2. **Falsify every new and changed test, both directions reported** — break each predicate/guard/
   wiring this task adds or changes, confirm red, restore, confirm green. This includes: the
   automatic-trigger wiring itself, the `AssertionError`→`SquadsError` conversion and the sweep's
   skip-and-continue behaviour (one corrupted file among several — confirm the others still
   converge and the corrupted one is reported, not silently dropped), the `self.spec.views` gate
   on the role/system-skill branches (drop `role_definition` via `[selected]`, confirm `sq repair`
   stops re-seeding it and `sq check` no longer produces the nine-error stuck state), and the
   `ROLE_DEFINITION_VIEW_NAME` pinning test.
3. **Test-selection rule from the board notice.** Derive selection from your diff: grep each
   changed name across `tests/` and run the union, plus the unconditional floor — `tests/meta`,
   `tests/integration`, and `tests/cli` — since this task touches `_cli/`.
4. **Narration sweep**, validated ast+tokenize scanner (scratchpad only, validated against a known
   positive first, never committed), applied to every line this task adds or changes.
5. **No docstring or comment citing coverage, a test file, or a delegation that does not exist** —
   verify every citation this task's new/changed prose makes resolves to something real.
6. `uv run sq check` clean on this repo's own squad.

## Dependency

None inbound. Can run in parallel with the sibling fix task (different files) — the only shared
file between the two is `_interactions/__init__.py`, and this task owns both edits to it (the new
constant and the adjacent docstring fix), so the sibling task never opens that file. Sequence F4
(ST2) and F5 (ST3) before or alongside F1's wiring (ST1) rather than after — F1 is what makes the
sweep run automatically on every upgrade, which is exactly what makes an un-hardened, ungated sweep
dangerous; do not land the automatic trigger ahead of the guard it depends on.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 927 add-subtask "<title>"`; track with `sq task 927 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Wire an automatic backfill trigger into the upgrade path

<!-- sq:subtask:ST1:body -->
Wire the existing role/system-skill/per-item-type-skill body-tag convergence step into the ordinary upgrade path (sync(), keyed on squads_version drift, not schema_version) so a 0.14 corpus upgraded to 0.15 renders every definition with no manual sq repair. Scope precisely to the convergence step — do not fold in repair()'s index rebuild or renumbering. If full automation proves unsafe, name the remedy in the version-drift notice or an sq check advisory instead of reporting clean success. Also fix the role's dead '(empty — set it with body)' hint and the skill's false 'type no longer declared' hint (F1's two secondary defects) so neither names a diagnosis that isn't true of the item in front of it.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-09-04T15:22:33Z] Elias Python:
  - Wired into sync(): squads_version vs __version__ (schema_tuple comparator), calls new _backfill_roster_body_tags(). Driven: pre-tag corpus (empty role/skill bodies + squads_version=0.14.0), one sync() call converges every body and no repair() call anywhere in the test. Falsified (disabled the trigger -> reddened, restored -> green).
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Convert the sweep's bare AssertionError to SquadsError, skip-and-report per file

<!-- sq:subtask:ST2:body -->
Convert _converge_body_tag's bare AssertionError (raised on marker-shaped body content it refuses to guess at) into a SquadsError with the same message text — the guard itself is correct and stays. Make the corpus-wide sweep loop that calls it skip-and-report one bad file rather than aborting mid-transaction, so the other 21 files still converge. This matters more once ST1 lands, since the sweep then runs on every upgrade rather than only when an operator remembers sq repair.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-09-04T15:22:36Z] Elias Python:
  - _converge_body_tag raises SquadsError (same message). _strip_retired_regions now catches it per file, returns (text, skip_message); _record_pending_rewrite/_PendingRewrites/_rebuild_index_from_disk/RepairResult all thread a skipped list through. sq repair CLI prints skipped entries and exits 1 on any. Falsified: one marker-shaped role body no longer blocks a second, healthy role's convergence in the same repair() call (reverting the fix aborts the whole sweep with a raw AssertionError, confirmed red then green).
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Gate role/system-skill re-seeding on the view still being declared

<!-- sq:subtask:ST3:body -->
_repair_body_tag's role and system-skill branches must check self.spec.views the same way the per-type branch already gates on the declared type, before naming a tag to seed/reconverge. Today they return a bare literal / fixed dict unconditionally, so dropping role_definition via a [selected] block makes every role file fail sq check with a dangling-tag error that sq repair itself keeps re-creating, with no supported way to remove the tag (no view verb on sq role, set_body refuses a role body). One condition, matching the per-type branch's existing shape.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-09-04T15:22:39Z] Elias Python:
  - _repair_body_tag's role and both skill branches now gate on the tag name being in self.spec.views, same shape as the existing per-type gate. Verified both directions: an already-tagged body under a dropped view is untouched either way (ADR doctrine: visible, never undone); an empty body under a dropped view stays empty only with the gate -- reverting it lets the sweep seed a fresh dangling tag into the empty body (driven, red then green).
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Add ROLE_DEFINITION_VIEW_NAME and fix the adjacent false docstring

<!-- sq:subtask:ST4:body -->
Add ROLE_DEFINITION_VIEW_NAME to _interactions/__init__.py beside SYSTEM_SKILL_VIEW_NAMES/ITEM_SKILL_VIEW_NAME; replace the bare 'role_definition' literal in agents/role.md.j2's seeded tag, _create_core's reseed, and _repair_body_tag's classification with it, and add/extend a test pinning all three (plus [views.role_definition] in _specs/workflow.toml) to the constant. In the same file, rewrite example_assignee_slug's docstring: drop the 'this collapse'/'every caller before' build-process reference (false in the present — agents_section.md.j2:44 still calls it dict-shaped) and name the two live callers instead, present tense.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-09-04T15:22:43Z] Elias Python:
  - Added ROLE_DEFINITION_VIEW_NAME beside SYSTEM_SKILL_VIEW_NAMES/ITEM_SKILL_VIEW_NAME; used in _create_core's reseed and _repair_body_tag's classification (role.md.j2 stays a static scaffold -- pinned by a template-read test instead). Fixed example_assignee_slug's docstring to name its two live callers in present tense. Pinning test falsifies each writer independently (renamed the constant: 3 of 4 assertions reddened as expected; the 4th -- create_core's reseed -- stays green under a rename because it imports the same symbol, and reddens instead when that writer is reverted to a bare literal, confirmed separately).
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Restore sq role show's unresolvable-role advisory

<!-- sq:subtask:ST5:body -->
show_role (_cli/_role.py) must print '(the definition for <slug> could not be resolved — run sq check to see why)' again when the role fails to resolve (the r is None branch that used to raise). resolve_role_for_item's degrade-rather-than-raise behaviour stays as is; only the definition pane's silence is the defect — the panel above already degrades to item fields correctly, and a nearby comment in the same function still asserts the opposite intent ('an invalid override must be reported, never quietly replaced').
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-09-04T15:22:47Z] Elias Python:
  - Restored the '(the definition for <slug> could not be resolved -- run sq check to see why)' advisory in show_role's r is None branch, printed alongside (not instead of) the degraded body render. Driven via a custom role whose .overrides/roles/<slug>.toml was deleted after activation; falsified (reverted -> 2 of 3 tests red, restored -> green).
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-04T15:23:32Z] Elias Python:
  - Implemented, all five subtasks Done (per-subtask detail also on each ST's own comment).
    
    **F1 — driven upgrade path.** Wired the existing body-tag convergence into `sync()`, keyed on
    `squads_version` drift (`schema_tuple(__version__) > schema_tuple(recorded_version)`, captured
    before anything in `sync()` can change it), calling a new narrow method
    `_backfill_roster_body_tags(roster_roles, roster_skills)` that reuses `_repair_body_tag` +
    `_converge_body_tag` directly -- no index rebuild, no retired-region strip, no ref-encoding
    canonicalisation, so this does not create an F10-shaped index-diff event on every sync.
    
    Driven, exactly as the acceptance asks -- built the real shape, ran only the ordinary action:
    1. `service.init(root=tmp_path, roles_spec="all")` + `svc.add_dev("python", ...)` +
       `svc.seed_bundled_skills()` -- a full roster (9 roles) + a developer + the 3 system skills.
    2. Every role's and every system skill's `sq:body` region stripped back to empty (the pre-tag
       shape; verified as a precondition in its own test).
    3. `.squads.toml` rewritten with `squads_version = "0.14.0"` (this build's SCHEMA_VERSION is
       unchanged at "0.14", so this is exactly the "squads_version moved, schema_version didn't"
       case F1 diagnosed).
    4. A fresh `SquadPaths`/`Service` (a real re-resolve from disk, not a cached object) then
       `await svc.sync()` -- `repair()` is never called anywhere in this test.
    5. Every role and skill body now carries its placement tag and `read_body()` renders real,
       non-empty text; the config is re-stamped to the current version. Also proved through the CLI
       (`invoke(["sync"])` against the same corpus) and proved the trigger is genuinely drift-gated
       (a second sync at the current version leaves an already-converged file byte-identical).
    
    Also fixed the two secondary hints: a role's empty body no longer says "set it with `body`"
    (there is no such verb); a system skill's empty body now distinguishes "type genuinely dropped"
    (`orphaned_skill_item_type`, unchanged wording) from "type live, backfill hasn't run yet" (new:
    points at `sq sync`) -- previously both cases said "no longer declared", which was false for the
    second one.
    
    **F4 -- guard stays loud, blast radius shrinks.** `_converge_body_tag` now raises `SquadsError`
    (same message) instead of a bare `AssertionError`. `_strip_retired_regions` catches it per file
    and returns `(text, skip_message)` instead of raising through; `_record_pending_rewrite` records
    the message onto a new `pending.skipped` list regardless of whether the file needed any other
    rewrite. `_rebuild_index_from_disk` now returns a 5-tuple (added `skipped`); `repair()` and
    `renumber()` updated at both call sites. `RepairResult.skipped` is new; `sq repair` prints each
    as `error: skipped <item id>: <reason>` and now also exits 1 on a non-empty `skipped` (same
    "reported degradation is not success" contract as `unreadable`). The guard itself is untouched --
    still refuses to overwrite marker-shaped content it has no model for; only what happens after the
    refusal changed (report + skip one region, not abort the whole corpus-wide pass).
    
    **F5 -- declared-view gate.** `_repair_body_tag`'s role and both system-skill branches now check
    `tag_name in self.spec.views` before naming it, the same shape the per-type branch already used
    for its own declared-type check. Important nuance I want on record: the gate protects against
    *seeding a new* dangling tag into an empty/untagged body under a dropped view -- it does **not**
    retroactively clear an already-tagged body under a dropped view (confirmed empirically: an
    already-tagged file is byte-identical after `repair()` whether or not the gate exists, since
    `_converge_body_tag`'s own idempotent early-return fires before the gate would ever matter). That
    matches ADR-880's own binding constraint ("a tag valid when placed and no longer valid is ...
    visible, never undone"), so it isn't a gap -- but I think this narrows what TASK-927's own
    acceptance text technically promised ("drop `role_definition`, confirm `sq repair` stops
    re-seeding it and `sq check` no longer produces the nine-error stuck state"). On an *already
    fully-synced* corpus (which is the realistic steady state -- every role's body already carries
    its tag from `_create_core`'s unconditional, ungated reseed at creation), dropping the view still
    leaves all nine `sq check` errors standing after `sq repair`, because there was never anything to
    seed. I verified this directly against the real reproduction sequence before writing the test,
    and I believe the review's "sq repair keeps re-seeding it" framing describes the mechanism (an
    ungated classifier naming a tag it shouldn't) rather than a literal always-reproducible symptom on
    an already-tagged corpus -- the fix is still correct and is exactly what's asked (the classifier
    gate), I just want the empty-body scoping on record rather than implied.
    
    **F7 / F8a.** Added `ROLE_DEFINITION_VIEW_NAME` beside `SYSTEM_SKILL_VIEW_NAMES`/
    `ITEM_SKILL_VIEW_NAME`; used in `_create_core`'s reseed and `_repair_body_tag`'s classification.
    `agents/role.md.j2` stays a static scaffold file (can't read a Python constant) -- pinned by a
    test that reads the template's raw text and asserts it equals `markers.view_tag(constant)`
    instead. Rewrote `example_assignee_slug`'s docstring to name its two live callers
    (`agents_section.md.j2`'s dict-shaped `roles`, `squads_skill.md.j2`'s `RoleView`-shaped
    `source.roster`) in present tense, no history.
    
    **F9.** Restored `show_role`'s advisory in the `r is None` branch (the definition-pane silence
    REV-926 flagged) -- printed *alongside*, not instead of, the degraded body render, since the
    degrade-rather-than-raise behaviour itself stays exactly as it is per the review's own
    instruction.
    
    **Falsification, both directions, every new/changed test:** for each of F1's trigger, F4's
    exception-class + skip-and-report, F5's gate (role branch AND a system-skill branch), F7's
    pinning (constant renamed -- 3 assertions correctly reddened; the reseed-writer assertion stays
    green under a pure rename since it imports the same symbol, and reddens instead when I reverted
    that writer to a bare literal separately), and F9's advisory: broke it, confirmed the specific
    new/changed test(s) went red with the expected failure shape, restored, confirmed green. None of
    this is asserted from memory -- every revert/restore pair is in this session's tool history.
    
    **Test selection**, per the board's grep-your-diff rule. Changed/added names grepped across
    `tests/`: `ROLE_DEFINITION_VIEW_NAME`, `_repair_body_tag`, `_converge_body_tag`,
    `_strip_retired_regions`, `_record_pending_rewrite`, `_rebuild_index_from_disk`, `RepairResult`,
    `orphaned_skill_item_type`, `role_definition` -- union resolved to specific files under
    `tests/service/` and `tests/unit/`. Floor applied because `_cli/` changed
    (`_cli/_role.py`/`_cli/_skill.py`/`_cli/_main.py`): full `tests/meta`, `tests/integration`,
    `tests/cli`. Combined run: 2105 passed, 7 skipped, 0 failed (log kept locally, not committed).
    Also ran the repo-wide gates: `pyright` 0 errors, `ruff check .` clean, `ruff format --check .`
    clean (647 files). Did **not** run the full suite -- per instruction, that's yours to run as the
    authoritative gate.
    
    **Narration sweep:** ran the validated ast+tokenize scanner (scratchpad only, never committed;
    validated against a known-positive fixture first) over every touched file, cross-referenced hits
    against the actual added/changed lines (not the whole file) via a diff-line filter, then read
    every new/changed docstring and comment by hand as the stranger test. Found and fixed three real
    instances beyond the scanner's own phrase list: a "before this behaviour ... that raise
    propagated" passage in `_strip_retired_regions`'s docstring, an "F1's fix ... Before this, ...
    F10/TASK-929" block in `sync()`'s new comment (also a bare ticket-ID reference, removed), and a
    "were each a bare literal ... kept re-seeding" passage in `_repair_body_tag`'s docstring -- all
    three described the pre-fix bug in the past tense rather than stating the current invariant, so
    none of them were reproducible by a reader with no diff. Rewrote each to state the durable
    mechanism/invariant instead. Also caught (via the repo's own ticket-reference gate, which I ran
    as part of the floor) an "ADR-880" citation in one of my new test docstrings and removed it.
    
    `uv run sq check` clean. Nothing above TASK-927 transitioned; TASK-928/929 untouched.
    
    @tech-lead @manager for review/dispatch of the next step.
<!-- sq:discussion:end -->
