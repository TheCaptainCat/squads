---
id: TASK-928
sequence_id: 928
type: task
title: Fix squad_dir path leak, filter compat, and skill-shadow advisory
status: Done
parent: FEAT-906
author: tech-lead
assignee: python-dev
refs:
- ADR-880:implements
- REV-926:addresses
subentities:
- local_id: ST1
  title: Fix the squad_dir absolute-path leak in squads_skill and memory_skill
  status: Done
  story: US2
- local_id: ST2
  title: Keep linearize_lifecycle as a one-release compatibility global alongside
    the filter
  status: Done
  story: US4
- local_id: ST3
  title: 'sq check advisory: a declared type''s generated skill guidance is shadowed
    by authored content'
  status: Done
  story: US3
- local_id: ST4
  title: Fix the second narration instance in the repair convergence test docstring
  status: Done
  story: US3
created_at: '2026-09-04T14:39:48Z'
updated_at: '2026-09-10T09:40:25Z'
---
<!-- sq:body -->
## Scope

Fixes REV-926 F2, F3, F6, and the second F8 narration instance — three independent surfaces
(`_views.py`/`_services/_items.py`, `_rendering/_engine.py` + `workflow.md.j2`, and
`_services/_validators.py`) plus one test-file docstring. No file this task touches overlaps the
sibling fix task.

### F2 — `squad_dir` now means two different things under one name

Two different values share one context-key name. The deleted `ServiceCore.skill_definition_text`
passed the squad **folder name** (`self.paths.config.squad_dir`, e.g. `"squads"`) as `squad_dir`.
The view-rendering path that replaced it (`ItemsMixin.read_body` → `expand_view_tags` →
`render_source_view`) passes `self.paths.squad_dir`, an **absolute resolved `Path`**. Both
`templates/views/squads_skill.md.j2` and `templates/views/memory_skill.md.j2` moved across that
boundary unchanged, so `{{ squad_dir }}` silently changed meaning: on this repo, `sq skill squads
show` now reads `` `/home/.../squads/squads/` `` where it read `` `squads/` `` before, and `sq
skill sq-memory show` leaks the same absolute path. `claude/claude_section.md.j2` and
`agents_md/agents_section.md.j2`, rendered from the backend directly (not through this path), still
correctly mean the folder name — so the same key name now has two live, incompatible meanings in
one template corpus.

Fix by making the two call sites agree, not by picking whichever is more convenient at the one
call site that broke: either pass the folder name into the view-rendering path under the
`squad_dir` key (matching the backend templates and the two moved templates' original meaning), or
give the two meanings distinct key names throughout (e.g. `squad_dir` stays the folder name
everywhere, a new key carries the absolute path for whichever future template genuinely needs it).
Restore `squads_skill.md.j2`/`memory_skill.md.j2`'s output to the relative folder-name form.

**Prove it the way REV-926 proved the regression — by comparing rendered TEXT, not file bytes or
existence.** TASK-922's own diff treated the `squads`/`sq-memory` divergence as a fixture artifact
because it compared file trees between two different temp roots; the reviewer caught it only by
diffing the *rendered strings* for the same slug. Add a real assertion (a golden, or an explicit
string-equality test) for the skill text's `squad_dir` rendering — today there is none anywhere in
`tests/` (`grep -rn squad_dir tests/integration/test_squads_skill_content_generation.py
tests/integration/test_memory_skill_generation.py` is empty) — so this specific regression cannot
recur silently a second time.

### F3 — `linearize_lifecycle` becoming a filter breaks an existing adopter override, hard

Converting `linearize_lifecycle` from `env.globals` to `env.filters` is correct per ADR-880's
ruling (the sanctioned extension point for this class of helper is a registered filter) and is not
to be reverted. The defect is that it is a breaking change to a documented adopter extension point
— an adopter who ran `sq override scaffold workflow.md.j2` on 0.14.x and changed nothing gets `error:
template 'workflow.md.j2' failed to render: 'linearize_lifecycle' is undefined` from both `sq
workflow` and `sq skill squads show` (which includes `workflow.md.j2`) on 0.15.0, with `sq check`
reporting only the generic "override may be stale" drift advisory and `sq sync` reporting success.

Keep `env.globals["linearize_lifecycle"]` registered as a one-release compatibility alias for the
exact same callable, alongside the new filter registration — this is not the query-logic-in-
templates failure ADR-880's guard exists to prevent (registering one callable under two Jinja
entry points is not a second implementation of anything), it is a deprecation shim. Flag the
CHANGELOG's 0.15.0 section as needing an entry naming the breaking change and the fix (`{{
linearize_lifecycle(x) }}` → `{{ x | linearize_lifecycle }}`) for anyone with an un-scaffolded
custom override — do not write the CHANGELOG prose yourself; report the fact you found to the tech
writer.

### F6 — a declared type whose skill slug is already authored loses its guidance with nothing saying so

`strict_empty` (TASK-923) correctly refuses to overwrite an authored `sq-<slug>` skill body once
that slug's type is later declared — not destroying real content is the right call. The
undeclared, unreported side effect: the declared type's *generated* guidance (lifecycle, verbs,
sub-entity footer) then has nowhere to live, and nothing on the `sq check` surface says so —
`_write_managed_skill` leaves the existing region untouched, `_repair_body_tag` correctly declines
to converge it, and `sq check` reports clean.

Add an `sq check` advisory (`_services/_validators.py`) that fires when a live `sq-<slug>` skill
item's body is authored (non-empty, not the tag) *and* the type it would otherwise document is
currently declared — naming both facts (which skill, which type) and the resolution (rename the
skill, or drop the type), so the collision is visible instead of only discoverable by reading the
file.

**Sequencing note — read before starting.** `_services/_validators.py` is under active,
uncommitted edit in this tree for REV-925's fix (the validator-catalog surface). Confirm that work
has landed (or coordinate directly) before opening this file; do not start this subtask against a
moving target.

### F8 — the second surviving narration instance

`tests/unit/test_repair_body_tag_convergence_pure_function.py`'s module docstring says it guards
against what "an earlier version of this backfill" did — no release ever shipped that version, it
existed for part of one work session, so "the before" exists nowhere a reader can check it. Rewrite
to state the invariant and why it can be violated ("a `sq-` slug can be authored before its type is
declared, so converging on non-empty content would destroy real work"), with no history. (The
sibling instance, in `_interactions/__init__.py`, is fixed on the other REV-926 fix task, which
owns that file for this round.)

## Acceptance

1. **F2 proven by comparing rendered text, not file bytes.** Diff the actual rendered strings for
   `squads` and `sq-memory` (and confirm `greeting` is unaffected, since it reads no `squad_dir`)
   before/after your fix, and add the missing pinning assertion described above.
2. **Falsify every new and changed test, both directions reported** — the `squad_dir` fix, the
   compatibility alias (an override calling the global form renders correctly both with and
   without the alias present — confirm it breaks without, passes with), and the new `sq check`
   advisory (an authored skill on a declared type triggers it; an authored skill on an undeclared
   type, or a template-owned skill on a declared type, does not).
3. **Test-selection rule from the board notice.** Derive selection from your diff: grep each
   changed name across `tests/` and run the union, plus the unconditional floor — `tests/meta`,
   `tests/integration`, and `tests/cli` — since this task touches `_rendering/templates/` and
   `_specs/`-adjacent validator wiring.
4. **Narration sweep**, validated ast+tokenize scanner (scratchpad only, validated against a known
   positive first, never committed), applied to every line this task adds or changes.
5. **No docstring or comment citing coverage, a test file, or a property nothing enforces** — this
   is the exact class F8 already is; verify every citation this task's new/changed prose makes
   resolves to something real, and that no new prose asserts an invariant (e.g. "byte-identical for
   every system skill") that this task's own fix doesn't actually make true.
6. `uv run sq check` clean on this repo's own squad.

## Dependency

None inbound. Can run in parallel with the sibling fix task (disjoint files). F6's subtask alone
has a real-world sequencing constraint against the concurrent REV-925 fix in this tree — see the
note under F6 above; the other three subtasks (F2, F3, F8) have no such constraint and can start
immediately.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 928 add-subtask "<title>"`; track with `sq task 928 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Fix the squad_dir absolute-path leak in squads_skill and memory_skill

<!-- sq:subtask:ST1:body -->
squad_dir now means two different things under one context-key name: the deleted skill_definition_text passed the folder name (self.paths.config.squad_dir); render_source_view (via read_body/expand_view_tags) passes the absolute resolved Path (self.paths.squad_dir). squads_skill.md.j2/memory_skill.md.j2 moved across that boundary unchanged, so their rendered text now embeds an absolute filesystem path where it embedded 'squads/'. claude_section.md.j2/agents_section.md.j2 still correctly mean the folder name. Make the two call sites agree — pass the folder name into the view path under the squad_dir key, or split the key into two distinct names — and restore the two templates' relative-folder output. Prove it by diffing RENDERED TEXT for squads/sq-memory before/after (not file existence), and add a real assertion pinning the squad_dir value these two templates render, since none exists anywhere in tests/ today.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Keep linearize_lifecycle as a one-release compatibility global alongside the filter

<!-- sq:subtask:ST2:body -->
Register env.globals['linearize_lifecycle'] as a compatibility alias for the same callable alongside the new filter registration, for one release. The filter conversion itself stays (ADR-880's ruling is literal on this); the alias is a deprecation shim, not a second implementation, so it does not reopen the query-logic-in-templates guard. This is what stops an un-scaffolded adopter override (sq override scaffold workflow.md.j2 on 0.14.x, changed nothing) from hard-failing sq workflow / sq skill squads show on 0.15.0. Report the breaking change and its fix (linearize_lifecycle(x) -> x | linearize_lifecycle) to the tech writer for the 0.15.0 CHANGELOG entry — do not author that entry yourself.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — sq check advisory: a declared type's generated skill guidance is shadowed by authored content

<!-- sq:subtask:ST3:body -->
Add an sq check advisory (_services/_validators.py) firing when a live sq-<slug> skill item's body is authored (non-empty, not the tag) and the type it would otherwise document is currently declared — strict_empty (TASK-923) correctly refuses to overwrite that authored content, but nothing currently reports that the declared type's generated guidance then has nowhere to live. Name both facts (the skill, the type) and the resolution (rename the skill, or drop the type). Sequencing: _services/_validators.py is under active, uncommitted edit in this tree for REV-925's fix — confirm that work has landed, or coordinate directly, before opening this file; do not start against a moving target.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Fix the second narration instance in the repair convergence test docstring

<!-- sq:subtask:ST4:body -->
tests/unit/test_repair_body_tag_convergence_pure_function.py's module docstring cites 'an earlier version of this backfill' that destroyed authored content — no release ever shipped that version, so the before exists nowhere a reader can check it. Rewrite to state the invariant and why it can be violated (a sq- slug can be authored before its type is declared, so converging on non-empty content would destroy real work), with no history. The sibling instance (_interactions/__init__.py's example_assignee_slug) is fixed on the other REV-926 task, which owns that file this round.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-04T15:55:23Z] Elias Python:
  - ## ST1 — F2, squad_dir absolute-path leak
    
    Root cause confirmed: `SquadsConfig.squad_dir` (the config folder-name string, "squads") vs
    `SquadPaths.squad_dir` (`root / config.squad_dir`, an absolute `Path`) collide under one
    parameter name threaded through `resolve_source`/`render_resolved_source`/`render_source_view`.
    The absolute Path is genuinely needed upstream (`_resolve_role_source` -> `resolve_role_for_item`
    opens `.overrides/roles/<slug>.toml` on disk), so it stays threaded as-is everywhere except the
    one boundary that matters: `render_source_view`'s call into `render()`. Added
    `_squad_dir_display(squad_dir) -> str | None` there (`.name` on the resolved Path — always
    recovers the configured folder name, since `SquadPaths.squad_dir` is always built as
    `root / config.squad_dir` in both `_paths.py::resolve()` branches) and feed that string under
    the `squad_dir` Jinja key instead of the Path object. No template changed — `squads_skill.md.j2`/
    `memory_skill.md.j2` keep meaning the same thing they meant before the collapse; the fix is
    entirely on the Python side of the one call site that broke.
    
    **Proven by rendered text, not bytes**, per the instruction:
    - Before (mutated back to the buggy call to falsify): `uv run sq skill squads show --raw` line
      read `` `/home/pchat/projects/squads/squads/`, indexed in `/home/pchat/projects/squads/squads/.squads.json` ``.
    - After (fix restored): same line reads `` `squads/`, indexed in `squads/.squads.json` `` —
      identical to pre-regression text.
    - Same pair for `sq skill sq-memory show --raw`: `` (`/home/.../squads/agents/memory/<role>/`) ``
      -> `` (`squads/agents/memory/<role>/`) ``.
    - `greeting` confirmed unaffected: `grep squad_dir templates/views/greeting_skill.md.j2` — no
      hits, so nothing in that template reads the key either way.
    
    **New pinning assertions** (none existed anywhere in `tests/` before, confirmed by the same grep
    the review ran): `tests/integration/test_squads_skill_content_generation.py::
    test_squad_dir_renders_the_configured_folder_name_not_an_absolute_path` and the sibling in
    `test_memory_skill_generation.py`. Each asserts the exact relative-folder substring AND that
    `str(svc.paths.squad_dir)` (the absolute form) is absent from the rendered body.
    
    **Falsified both directions**: reverted `render_source_view`'s call to pass the raw `squad_dir`
    Path — both new tests went red with the absolute-path string in the failure diff, confirming
    they catch the regression; restored, both green.
    
    **Selection floor surfaced two more sites pinning the old (buggy) behaviour directly** —
    `tests/unit/test_render_source_view_template_context.py` (3 tests) and
    `tests/service/test_role_playbook_self_views_end_to_end.py::
    test_a_self_sourced_view_renders_the_host_and_carries_squad_dir` all asserted
    `sd == str(squad_dir)`. Updated all four to assert the configured folder name
    (`svc.paths.config.squad_dir` / `project.config.squad_dir`) instead — these were pinning the
    defect, not a property; fixing F2 without touching them would have left them red.
    
    ## ST2 — F3, linearize_lifecycle compat alias
    
    Registered `env.globals["linearize_lifecycle"]` alongside the existing `env.filters[...]`
    entry in `_rendering/_engine.py` — same callable under both Jinja entry points, not a second
    implementation (ADR-880's guard is about query logic re-implemented in a template, not a
    calling-convention alias for one already-registered pure function). Comment states it's a
    one-release deprecation shim and names the removal criterion.
    
    New test `tests/unit/test_linearize_lifecycle_global_compat_alias.py` (pattern copied from
    `test_badge_filter_reachable_from_templates.py` — a throwaway probe template placed as a real
    project override, rendered through the actual engine):
    1. the old global-call syntax (`{{ linearize_lifecycle(machine) }}`) still renders,
    2. the global and filter forms agree on the same machine (proves "one callable, two doors" —
       not two implementations that could drift),
    3. the bundled `workflow.md.j2` itself (filter-only) still renders clean with the alias present.
    
    **Falsified**: removed the `env.globals[...]` line — tests 1 and 2 went red
    (`'linearize_lifecycle' is undefined`), test 3 stayed green (bundled template never calls the
    global form, so the alias's absence cannot break it) — the expected asymmetric result, not a
    uniform failure, confirming the test actually isolates the alias rather than the filter.
    Restored, all three green.
    
    **CHANGELOG**: not authored by me per role boundary — reporting the fact for the tech writer.
    Breaking change: `linearize_lifecycle` moved from a Jinja global to a filter in 0.15.0. An
    adopter who ran `sq override scaffold workflow.md.j2` before 0.15.0 and calls
    `{{ linearize_lifecycle(x) }}` in their own copy keeps working through 0.15.x (the
    compatibility alias covers it), but should migrate to `{{ x | linearize_lifecycle }}` before
    the alias is dropped in a future release. @tech-writer for the actual 0.15.0 entry — please
    also flag this needs surfacing since the current unreleased-section text mentions two additive
    features and no breakage.
    
    ## ST3 — F6, item_skill_shadowed sq check advisory
    
    New per-item CATALOG validator `item_skill_shadowed` in `_services/_validators.py`: fires warn
    when a live `sq-<slug>` skill item's `sq:body` is authored (non-empty, not the `item_skill`
    placement tag) while `item_type_for_skill_slug(slug, spec)` resolves a currently-declared type.
    Names both facts and the resolution (rename the skill, or drop the type) in the message.
    
    **Tier**: per-item CATALOG (not the file-level scan). The file-level scan
    (`_maintenance._scan_for_check`, Tier 1) is unconditional-across-every-type and runs on raw
    text before frontmatter parses — this check is neither: it applies to exactly one type (skill),
    needs the resolved `Item` (to read `extra[X.SLUG]` and cross it against the live spec via
    `item_type_for_skill_slug`), and is naturally selectable the way every other per-type addition
    is. It's declared directly in `[items.skill].validators` in `_specs/workflow.toml` — the same
    shape as `epic`'s own `no_parent` — rather than a `CATEGORY_BUNDLES["roster"]` entry, since
    `role`/`operator` items have no matching collision to report and the bundle is empty by design.
    
    **Closure**: added to `VALIDATOR_NAMES`/`DEFAULT_VALIDATOR_LEVEL` (warn) in `_workflow/_models.py`,
    implemented in `CATALOG`, needs-raw-text declared in `VALIDATOR_CONTEXT` (so it sits `gate()`
    out the same way `no_status_banner` does — it's a corpus-state advisory, not a create/update
    blocker). Placed in `UNGUARDED_VALIDATOR_NAMES`, deliberately: it sits in no category bundle at
    all (the `parent_present`/`ref_rule_target_present` shape — a name you wrote yourself in a
    type's own list cannot be silently lost to a category reassignment), *and* `skill` is one of
    the three roster keys `_workflow/_loader.py` locks to `category = "roster"` permanently, so
    there is no reassignment path for it to survive in the first place — documented as a stronger
    guarantee than the other two `UNGUARDED` entries. The import-time asserts
    (`CATALOG == VALIDATOR_NAMES`, `_CLAUSE_GUARDED | COMMON_CORE | UNGUARDED == VALIDATOR_NAMES`,
    `VALIDATOR_CONTEXT <= CATALOG`) all still pass.
    
    New tests, `tests/service/test_item_skill_shadowed_validator.py` (5 cases): fires on authored+
    declared; silent on authored+undeclared; silent on template-owned (tag-converged) body on a
    declared type; silent on genuinely-empty body on a declared type; silent for a permanently-
    system skill (squads/greeting/sq-memory) even with authored content, since
    `item_type_for_skill_slug` returns `None` for all three regardless of body.
    
    **Falsified two ways**: (1) short-circuited the function to always return `[]` — the positive
    test went red, all four silent-case tests stayed green (correct — a validator that never fires
    can't wrongly fire). (2) forced `doc_type` non-`None` even when undeclared — the two negative-
    direction tests (undeclared type, permanently-system skill) both went red, proving they're
    actually exercising the guard rather than passing vacuously. Both mutations reverted, all 5
    green again.
    
    Also fixed `tests/unit/test_validators_assignment_surface.py::
    test_bundled_spec_declares_epics_validators_addition_only` — its premise ("epic is the only
    built-in type with a validators addition") is now false; renamed and widened to assert both
    `epic` and `skill`'s additions plus the negative over every other type.
    
    ## ST4 — F8b narration
    
    Rewrote `tests/unit/test_repair_body_tag_convergence_pure_function.py`'s module docstring: cut
    "an earlier version of this backfill" (no release ever shipped it — nowhere a reader can check
    it), replaced with the invariant and why it can be violated (a `sq-` slug can be authored
    before its type is declared; converging unconditionally over non-empty content the moment it
    turns template-owned would destroy that work) plus a pointer to the end-to-end proof in
    `test_repair_strips_only_retired_regions.py`.
    
    ## Narration sweep
    
    Ran the validated ast+tokenize scanner (scratchpad-only, validated against
    `known_positive.py` first — 4/4 known hits caught) over every file I touched. Two real
    false-positive substrings ("has nowhere" containing "has now") in my own new docstrings, no
    action. One legitimate hit: `test_the_bundled_workflow_template_itself_still_renders`'s
    docstring said "...that no longer calls the global form at all" — read as a stranger this is a
    before/after comparison with no diff-checkable "before", so reworded to state the template's
    current behaviour plainly ("only ever calls the filter form"). Re-ran after the fix: clean.
    `_rendering/_engine.py`'s "once 0.15.x is no longer a supported upgrade source" comment matched
    the phrase list too but is forward-looking maintenance guidance (a removal criterion), not
    narration — kept as-is.
    
    **Ticket-ID sweep** (separate from narration, `CLAUDE.md`'s no-ticket-IDs-in-source rule):
    found and removed three "TASK-923"/"F6" citations I'd written into
    `_services/_validators.py`'s docstring, `_specs/workflow.toml`'s comment, and my own new test
    file's module docstring — replaced each with a description of the mechanism instead of the
    ticket. Re-grepped clean afterward.
    
    ## Gates
    
    `pyright`/`ruff check`/`ruff format --check` all clean (`--all-extras` throughout).
    
    ## Test selection
    
    Derived from the diff, not recalled: grepped every changed name (`squad_dir`'s actual call
    sites — `render_source_view`/`resolve_source`/`render_resolved_source`, since bare `squad_dir`
    as an identifier is shared by dozens of unrelated `SquadPaths`/`load_workflow_spec` call sites
    across the whole suite and grepping it verbatim would have pulled in most of `tests/`;
    `linearize_lifecycle`; `item_skill_shadowed`; `ITEM_SKILL_VIEW_NAME`; `UNGUARDED_VALIDATOR_NAMES`;
    `DEFAULT_VALIDATOR_LEVEL`; `VALIDATOR_CONTEXT`) plus a handful of directly-adjacent view/skill
    tests. **Plus the unconditional floor** — `tests/meta`, `tests/integration`, `tests/cli` in
    full, since this task touches `_specs/workflow.toml` (spec-adjacent) even though it turns out
    not to touch any `.j2` template file or `_cli/` directly.
    
    The floor caught two things the name-grep alone would have missed: (1) four tests pinning the
    pre-fix `squad_dir` behaviour (listed under ST1), and (2) a stale manifest hash —
    `_specs/workflow.toml` is one of the 31 manifest-tracked bundled artifacts
    (`_rendering/templates_manifest.json`/`content_store.json`), so editing it without regenerating
    the manifest failed `tests/meta/test_override_manifest_and_stamp_freshness.py` +
    `test_override_kind_uniformity.py` + an integration override-diff test. Ran
    `scripts/gen_template_manifest.py` (safe — 0.15.0 is the untagged working version, confirmed
    via `git tag` before running) then `scripts/seed_content_store.py --rebuild` (also safe:
    `--check` first showed all 16 tagged releases already current, so nothing but the fresh
    working-tree orphan was touched) to clean up the one orphaned blob the regen left behind. Both
    committed doc files (`templates_manifest.json`, `content_store.json`) are part of this
    handback.
    
    Final run: `pytest tests/meta tests/integration tests/cli` + 27 targeted files, once,
    redirected to a log — **2186 passed, 7 skipped, 1 failed**. The one failure
    (`test_the_new_test_tree_has_no_ticket_reference_in_a_filename_or_docstring`, flagging `'F5'`
    in `tests/unit/test_validator_engine_scaffold.py`) is **not mine** — that file is under active
    concurrent edit in this same tree by another session (visible throughout as interleaved,
    non-conflicting hunks in `_workflow/_models.py`/`_services/_validators.py` — the
    `PARAMETERIZED_VALIDATOR_NAMES` -> `MULTI_SELECTION_VALIDATOR_NAMES`/
    `SINGLE_SELECTION_VALIDATOR_NAMES` split, presumably REV-925 follow-on work). I did not touch
    that file and left it alone rather than editing another agent's in-flight work; flagging so it
    doesn't get missed before that other line of work hands back.
    
    ## sq check
    
    Clean (`✓ no issues`) on this repo's own squad after all edits.
    
    ## What I think the review/breakdown may have underweighted
    
    The breakdown's F2 fix suggestion ("pass the folder name into the view-rendering path under
    the squad_dir key... or split into two distinct key names") reads as two mutually exclusive
    options at the *Python parameter* level. What I actually did is closer to a hybrid: the
    parameter stays a `Path` everywhere it's threaded (needed for `_resolve_role_source`'s real
    disk access), and only the *template-context* value at the one render boundary converts to the
    display string. I think this is what "make the two call sites agree" meant in practice, since
    neither literal option cleanly handles that the same value is genuinely dual-purpose
    upstream — but flagging in case the intent was a more literal two-key split (e.g. a
    `squad_dir`/`squad_dir_path` pair threaded end to end) for extra clarity to a future reader who
    doesn't trace into `_squad_dir_display`'s docstring.
<!-- sq:discussion:end -->
