---
id: TASK-924
sequence_id: 924
type: task
title: Declared level, floor, and threshold for validator selections
status: Done
parent: FEAT-898
author: tech-lead
assignee: python-dev
refs:
- ADR-864:implements
subentities:
- local_id: ST1
  title: Declare a validator's level in its selection
  status: Done
  story: US1
- local_id: ST2
  title: 'Declared floor: selections may raise, never lower, level'
  status: Done
  story: US2
- local_id: ST3
  title: Move validator thresholds from constants into the spec
  status: Done
  story: US3
- local_id: ST4
  title: Extend the required-context correspondence to level/floor
  status: Done
  story: US4
- local_id: ST5
  title: Make parent_present selectable at warn
  status: Done
  story: US5
created_at: '2026-09-04T12:54:01Z'
updated_at: '2026-09-08T14:55:40Z'
---
<!-- sq:body -->
## Scope

Builds ADR-864 step 1: the validator assignment grammar gains three declarable dimensions —
level, threshold/parameter, and required context — over the existing per-item catalog
(`VALIDATOR_NAMES` in `_workflow/_models.py`, `CATALOG` in `_services/_validators.py`). Squad-
global validators (`SQUAD_GLOBAL_VALIDATOR_NAMES`) are out of scope: they are never selected
through a type's `validators` list, so no assignment grammar applies to them.

**Ground truth check before starting**: the required-context dimension is already built.
`ContextRequirement`, `ValidatorContext.held_context()`, `VALIDATOR_CONTEXT`, and
`ValidatorEngine._run_per_item`'s filter (`_services/_validators.py`) already declare which
members need `raw_text`/`type_present`, skip members the gate can't supply, and an
import-time assert plus `tests/meta/test_validator_context_requirements_match_what_each_member_reads.py`
(a static AST scanner) close the correspondence between declared and actually-read context.
This landed in commit 0901816c, ahead of this feature being scoped, as the code-side discharge
of ADR-864's gate-clause correction. Confirm this by running that test file before touching
anything — it must be green on a clean checkout. Subtask 4 below is about *extending* this
mechanism to the new level/floor table, not building it from nothing.

## What must be preserved (verify before and after, on every subtask)

1. **The spec/service catalog split.** The validator NAME catalog (`VALIDATOR_NAMES`) and any
   new name-keyed declaration table this task adds (default level, floor, threshold) live in
   the spec layer (`_workflow/_models.py`), not `_services/`. Behaviour stays in
   `_services/_validators.py::CATALOG`. `assert set(CATALOG) == VALIDATOR_NAMES` must keep
   holding, and no new import edge from `_workflow` up into `_services` may appear (this is
   what lets Plane-1 spec-load validation — e.g. rejecting a level below a member's floor —
   run without `_workflow` importing `_services`; see how `PARAMETERIZED_VALIDATOR_NAMES`
   already does this for the existing `:<param>` suffix, as precedent for where a new floor
   table belongs).
2. **The consistency-clause closure.** `CONSISTENCY_CLAUSES` + `UNGUARDED_VALIDATOR_NAMES` +
   the assert closing their union against `VALIDATOR_NAMES` (`_services/_validators.py`, near
   line 1440) must keep holding unchanged — this task adds no new catalog *member*, only new
   declarable properties on existing members, so no new clause/unguarded-name decision should
   be needed. If a subtask's design somehow requires one, that is a signal to stop and reopen
   scope with the tech lead, not to route around the assert.
3. **The two gate-correction rulings carried in from ADR-864, unchanged**: the create/update
   gate is not widened to the item's on-disk text; `subentity_container_marker` keeps `error`
   (it is the canonical example of a load-bearing floor, not a candidate for demotion).
4. **`sq check`'s two-tier structure.** `_marker_issues`/`_view_target_issues`
   (`_services/_maintenance.py::_scan_for_check`) are file-level, always-on, and outside
   `CATALOG` by design. Nothing in this task pulls them into the declaration surface, and no
   docstring/comment written by this task should describe `CATALOG` as `sq check`'s complete
   finding surface.

## Subtasks

Five subtasks, mapped to FEAT-898's five stories (US1–US5). Do them in order — each after
depends on the assignment-parsing groundwork the first one lays.

1. Declare a validator's level in its selection (US1)
2. Declared floor: a selection may raise level, never lower it (US2)
3. Move validator thresholds from module constants into the spec (US3)
4. Extend the required-context correspondence assertion to the new level/floor table (US4)
5. `parent_present` becomes selectable at warn (US5)

## Acceptance criteria — apply to every subtask, not just the one it reads most naturally on

1. **The catalog-wide assertion over declared-context correspondence** must still hold after
   this task lands, and subtask 4 must extend the *same class* of assertion (a static,
   AST-or-equivalent check that the declared table cannot drift from what the code actually
   does) to the new level/floor declaration — not merely trust a hand-maintained table. No
   docstring or comment may assert a catalog-wide property that nothing verifies.
2. **Falsify every new and changed test, both directions, and report both.** Break the
   invariant under test (e.g. hand-edit the floor table to let a load-bearing member drop to
   warn, or desync a declared level from what a validator emits) and confirm the test goes
   red; restore and confirm green. This applies to the correspondence assertion in subtask 4
   as much as to any behavioural test — a mutation test proves the assertion, not just the
   happy path.
3. **The narration sweep is per-subtask acceptance.** Before closing each subtask, sweep the
   new/changed prose (docstrings, comments, assert messages, error strings — not fixture data)
   with the validated ast+tokenize block scanner in the scratchpad (never committed to the
   repo), validated first against a known positive so a clean sweep is trustworthy. Apply the
   stranger test per sentence: does it name something a stranger who never saw the diff can
   still check? Past-tense delta claims about *this build* ("this replaces the old X", "the
   docstring used to say Y") fail it; durable present-tense facts pass.
4. **No docstring or comment citing coverage that does not exist.** In particular: don't claim
   `CATALOG`/the assignment grammar covers squad-global validators, and don't claim the
   required-context mechanism was built by this task when subtask 4 only extends it.
5. **Gates before handoff**: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
   `uv run --all-extras ruff format --check .`, and a targeted `pytest` selection that
   explicitly names `tests/meta` AND `tests/integration` alongside whatever unit/service paths
   changed — e.g. `uv run --all-extras pytest tests/meta tests/integration tests/unit/... tests/service/...`.
   Neither directory may be dropped from the selection to save time; this release already had a
   targeted run pass while `tests/meta` held a real violation, and separately while
   `tests/integration` held 34. `uv run sq check` clean before handoff.

## Non-goals

- No new catalog member (that's FEAT-899 through FEAT-902).
- No change to squad-global validator selection or levels.
- No widening of what context the gate holds (raw_text/type_present stay report()-only).
- No demotion of `subentity_container_marker`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 924 add-subtask "<title>"`; track with `sq task 924 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare a validator's level in its selection

<!-- sq:subtask:ST1:body -->
Extend the assignment string grammar so a type's `validators` entry can declare a level
override, alongside the existing bare-name / `:<param>` shapes. Today every entry is
`name` or `name:param` (`_workflow/_models.py::ItemSpec.validators`,
`_check_validators_assignment`); every catalog member hardcodes exactly one level inline
in its own `CheckIssue(...)` calls (confirmed: every per-item member in
`_services/_validators.py` emits a single fixed level today, none mix error/warn).

Design the suffix so it composes with the existing param syntax without ambiguity (e.g.
`name@level` and `name:param@level` — the exact separator is your call, but it must not
collide with a valid item id, ref kind, or the existing `:` param separator, and must be
validated at spec load the same way the param suffix already is: an unknown level value is
a Plane-1 error naming the entry and the type).

Only `error`/`warn` are valid levels (matches `CheckIssue.level`'s existing two-value
contract — don't invent a third).

Acceptance:
- A selection with no level suffix keeps today's bundled default level for that member,
  unchanged.
- An entry naming a level not in `{error, warn}` is a Plane-1 spec-load error.
- Parsing lives where the existing `:<param>` parsing lives (spec layer,
  `_workflow/_models.py`) — no new import edge into `_services`.
- The dispatch engine (`ValidatorEngine._run_per_item`) strips the level suffix before the
  `CATALOG` lookup, the same way it already strips the param suffix.
- New tests cover: no suffix, level only, param only, both, in each valid order if the
  grammar allows more than one, and at least one malformed shape per rejected case.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Declared floor: selections may raise, never lower, level

<!-- sq:subtask:ST2:body -->
Declare, per catalog member, a floor level a selection may raise but never lower — for the
members whose level is load-bearing. `subentity_container_marker` is the one the ADR names
explicitly: it keeps `error` unchanged (carried in from the gate-clause correction; not a
demotion candidate, not open to re-litigation here).

Enumerate the rest yourself, applying the same reasoning ADR-864's tiering test uses for
category membership, one level down: would letting this member's level drop to `warn` let
the engine's own correctness — not just a policy preference — break silently past the
create/update gate? Today's error-level members are `parent_in`, `no_parent`,
`parent_present`, `parent_acyclic`, `item_status_valid`, `subtask_story_mapping`,
`subentity_status_valid`, `subentity_container_marker`. `parent_present` is the deliberate
exception (US5, subtask 5): the ADR names its cliff as the reason it stayed unbundled, not
as a reason it needs a floor, so it must NOT default to a floor here even though it is
error today. Every other error-level member is a candidate; write down your yes/no per
member and why, in the code comment next to the floor table — not just in this subtask's
discussion.

Floor data is a name-keyed table. Same placement question as `PARAMETERIZED_VALIDATOR_NAMES`:
it lives in the spec layer (`_workflow/_models.py`) so Plane-1 spec-load validation
(rejecting a declared level below a member's floor) can consult it without `_workflow`
importing `_services`. Assert it validates as a subset of `VALIDATOR_NAMES`, the same shape
as the existing `VALIDATOR_CONTEXT ⊆ CATALOG` assert in `_services/_validators.py`.

Acceptance:
- Declaring a level below a member's floor is a spec-load error naming the member and its
  floor value.
- Declaring a level at or above the floor succeeds.
- A member with no floor accepts either level, including lower than its own default (this
  is what makes `parent_present` selectable at warn in subtask 5).
- The floor table is enumerated and each entry's inclusion is tested individually, not just
  the two examples above — a test per floor member asserting the refusal, and a test per
  non-floor member (at least `parent_present` and one other) asserting a lower level is
  accepted.
- `subentity_container_marker`'s floor is `error`; a test asserts declaring it at `warn` is
  refused.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Move validator thresholds from constants into the spec

<!-- sq:subtask:ST3:body -->
`subentity_title_max`'s `:<param>` suffix is documentary today and never read back
(`_workflow/_models.py`'s own comment says so; `_services/_validators.py::_subentity_title_max`
reads the module constant `TITLE_ADVISORY_MAX` — `_interactions/__init__.py`, value 120 —
never `ctx`). Make the suffix real: the threshold moves into the spec as a declared,
overridable field, and the validator reads it from `ctx` instead of the constant.

`ref_rule_target_present`'s `:<T>` param is the existing precedent for a genuinely-read
parameter (it reads its own target type off the entry, stripped by the dispatch engine the
same way — `_services/_validators.py`, near the `and sep` guard for that member). Follow the
same shape: the type's own `validators` entry carries the threshold
(`subentity_title_max:150`), Plane-1 already accepts a `:<param>` suffix on this name
(`PARAMETERIZED_VALIDATOR_NAMES`) — extend its validation to require the param parse as a
positive integer, the same class of check `_check_ref_rule_targets` runs for its own param.

The bundled default must reproduce today's behaviour exactly: same 120 threshold, same
message text (including the literal "(threshold: 120)" segment) for a type that declares no
override. Don't leave `TITLE_ADVISORY_MAX` as a second source of truth once the spec field
exists — either it becomes the bundled default value referenced from one place, or it is
retired in favour of the spec's own default; pick one and don't let the two drift.

**A second, independent call site reads the same constant and is easy to miss**:
`_services/_subentities.py`'s `add-<kind>` path reads `TITLE_ADVISORY_MAX` directly to build
its own create-time advisory (the message returned to the CLI at sub-entity creation, distinct
from the `sq check` validator). It is not a `CATALOG` member and this task does not bring it
into the catalog — but it must read the same resolved, type-aware threshold this subtask
declares, or a type that overrides the threshold gets a `sq check` warning at one number and a
create-time advisory at another. Route both reads through the one spec-resolved value.

Acceptance:
- A type with no `subentity_title_max` override behaves identically to today — same
  threshold, same message, verified by a test that would fail if the module constant or the
  spec default diverged.
- A type declaring `subentity_title_max:80` warns above 80 chars, not 120, and the message's
  own threshold text reflects 80.
- A non-integer or non-positive param is a Plane-1 spec-load error.
- No runtime code still reads `TITLE_ADVISORY_MAX` as the effective threshold once this
  lands (grep it — a stray read that only serves as the bundled default's value is fine, a
  read used as a check's or advisory's live threshold is not). This includes
  `_services/_subentities.py`'s create-time advisory, not only the `sq check` validator.
- A type declaring `subentity_title_max:80` produces the same 80-char threshold at both
  `add-<kind>` create time and `sq check` — a test creating a sub-entity with a title between
  the old and new threshold on such a type, asserting the create-time advisory fires (or
  doesn't) consistently with what `sq check` would report.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Extend the required-context correspondence to level/floor

<!-- sq:subtask:ST4:body -->
Ground truth: the required-context dimension US4 asks for is already built. `ContextRequirement`,
`ValidatorContext.held_context()`, `VALIDATOR_CONTEXT`, and the filter in
`ValidatorEngine._run_per_item` (`_services/_validators.py`) already declare which members need
`raw_text`/`type_present`, skip a member on a call path that can't supply what it declared, and
`tests/meta/test_validator_context_requirements_match_what_each_member_reads.py` is a static AST
scanner that fails if a member's declaration and what its body actually reads disagree. This
landed in commit 0901816c, ahead of this feature being scoped, as the code-side discharge of
ADR-864's gate-clause correction. Run that test file first — it must already be green — and do
not re-implement any part of this mechanism from scratch.

This subtask has two jobs, both smaller than "build it":

1. **Verify it survived subtasks 1–3 unchanged in meaning.** Nothing about declaring a level or
   a threshold reads a new `ValidatorContext` field, so `VALIDATOR_CONTEXT` and the AST scanner
   should need zero edits. Confirm this by running the meta test after subtasks 1–3 land, not
   just before this subtask starts — if it needed a change, that is a signal something in
   subtasks 1–3 leaked a context read somewhere it shouldn't be, not a reason to loosen the
   scanner.

2. **Close the same class of correspondence for the new level/floor table subtasks 1–2 added.**
   That table is a second place a name-keyed declaration about a catalog member could drift from
   what the member's code actually does — the identical failure shape the context mechanism was
   built to catch (a declaration nobody re-derives from the code it describes). Add an
   analogous static check: either (a) refactor each validator body to read its resolved level
   from `ctx`/a passed-in value rather than hardcoding it in `CheckIssue(...)`, which removes the
   duplication outright and needs no scanner, or (b) if a hardcoded fallback level remains in
   each function for any reason, add a scanner in the shape of
   `test_validator_context_requirements_match_what_each_member_reads.py` that fails when the
   declared default/floor disagrees with what the function actually emits. Prefer (a); only fall
   back to (b) with a stated reason why threading the level through wasn't viable.

Acceptance:
- `tests/meta/test_validator_context_requirements_match_what_each_member_reads.py` passes
  unmodified (or, if genuinely touched, the diff is reviewed against why — not a routine edit).
- A new static test closes the level/floor correspondence the same way — falsify it: desync a
  declared level or floor from what the code does, confirm it fails, restore, confirm it passes.
- No docstring or comment in this subtask's diff claims to have built the required-context
  mechanism; it must say what it actually did — extended the existing one to a new declaration
  table, or nothing if job 1 found no drift.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Make parent_present selectable at warn

<!-- sq:subtask:ST5:body -->
With level declarable (subtasks 1–2), `parent_present` — Part 1's requires-a-parent check,
deliberately in no `CATEGORY_BUNDLES` entry — becomes selectable at `warn` in a project's own
spec. The cliff that kept it unbundled was its level (selecting it at `error` fails every
parentless item already on disk at its first ordinary update), not its rule; as a warning a
project can adopt the convention without that cliff.

This is mostly acceptance work once subtasks 1–2 land: `parent_present` must carry no floor
(subtask 2 already excludes it deliberately — confirm that exclusion rather than re-deciding
it here), so `parent_present@warn` in a type's own `validators` list is accepted at spec load
and produces a `warn`-level `CheckIssue` at runtime instead of `error`, without touching the
bundled spec's own defaults (selecting it is a project choice, not a new bundled default —
this project's own spec is unchanged by this subtask on its own).

Acceptance:
- A project spec selecting `parent_present@warn` on a type loads clean even when the corpus
  already holds parentless items of that type — `sq check` reports the warning, `sq check`'s
  exit code stays 0 on warn-only findings (matches today's error-only exit contract), and
  ordinary `sq <type> <n> update` on an existing parentless item is not refused.
- Selecting `parent_present` at `error` (bare, or `parent_present@error`) still refuses an
  update creating/leaving a parentless item, exactly as today — a regression test proving
  the default behaviour is unchanged.
- This project's bundled `.squads` spec gains no new selection from this subtask — verify with
  `sq check`/`sq workflow lint` clean and no diff to the bundled spec's own type declarations
  beyond what subtasks 1–3 required for the grammar itself.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-04T13:39:40Z] Elias Python:
  - Implemented all five subtasks. Summary per subtask, floor proposal, both directions of falsification, and gate results below.
    
    ## ST1 — assignment grammar
    
    Separator: `@` for level (never a second `:`). Grammar: `name`, `name:param`, `name@level`, `name:param@level` — param always precedes level. `@` cannot collide: it never appears in a validator name, a `:<param>` value, an item id, or a ref kind; the codebase's only other `@` usage (`@mention` in discussion prose) is a different namespace entirely (comment text, never spec vocabulary). One parser, `parse_validator_entry` (`_workflow/_models.py`), used by every consumer: Plane-1 validation, `effective_validator_names`'s composition, the dispatch engine's catalog lookup, and `ref_rule_target_present`'s own param read-back.
    
    `DEFAULT_VALIDATOR_LEVEL` (spec layer) replaces every hardcoded level literal inline in a `CheckIssue(...)` call — each catalog member now calls `_resolved_level(ctx, name)` (services layer), which reads a type's own `@<level>` override or falls back to the table. No second number left to drift.
    
    One thing this needed beyond the ADR's own speculative spelling: `effective_validator_names` now de-dupes by bare name (last occurrence wins, first-seen position kept) — without it, a type naming an already-bundled member with a suffix (e.g. `subentity_title_max:80` on a `work`-category type, which already gets bare `subentity_title_max` from the category bundle) would run the member twice under two spellings of the same name. Also added: a type may not name the same bare validator twice in its own `validators` list (ambiguous — refused at load).
    
    ## ST2 — declared floor (my judgement call, presented as a proposal)
    
    Floor table, `VALIDATOR_LEVEL_FLOOR` (`_workflow/_models.py`, next to `DEFAULT_VALIDATOR_LEVEL`), enumerates **two** members: `parent_acyclic` and `subentity_container_marker`. Full per-member reasoning is written in the code comment above the table (per-member, not just here) — summary:
    
    **Floor:**
    - `parent_acyclic` — a parent cycle makes every ancestor/descendant walk in the engine non-terminating (the live hang BUG-865 tracked and fixed). Demoted to warn, a project's own choice reintroduces a whole-squad hang `sq check` no longer fails on.
    - `subentity_container_marker` — carried in from the ADR unchanged, as instructed.
    
    **Not floor** (candidates weighed and rejected, each with its own reason, not a blanket call):
    - `parent_in` / `no_parent` — nothing downstream assumes the constraint already holds to function; no walk or transition depends on parent-type eligibility, only on the parent existing and the chain terminating (`parent_acyclic`'s job). A team mid-reorganisation could hold this state on purpose.
    - `item_status_valid` — flags a status outside the *type's own* lifecycle graph (not an undeclared status globally); badge/role resolution reads the global status catalog, unaffected. The engine already ships a designed recovery: `--force` on an ordinary status update short-circuits the transition-table lookup and only re-checks target-vocabulary membership — an item outside its lifecycle graph is one documented escape away, unlike a parent cycle (no equivalent recovery short of clearing the parent).
    - `subtask_story_mapping` — affects grouping/rollup display only; nothing gates or walks on it resolving, and it's visible wherever rendered (unlike the container-marker desync, which is invisible everywhere but `sq check`).
    - `subentity_status_valid` — same shape/reasoning as `item_status_valid`; `_apply_subentity_status`'s own docstring documents the identical designed-recovery property (vocabulary gate first, unconditional).
    
    **Expect this to be challenged.** The dividing line I used, beyond "can a squad sit here on purpose": does anything *outside* `sq check`'s own report ever detect or is broken by the state (a hang, an invisible desync), or does the engine already ship a designed, documented recovery (`--force`)? That's a narrower bar than the Part-1 tiering test's "is it a defect at all" — I read the ADR's "engine's own correctness, not just policy preference" framing as asking specifically about mechanism breaks (hangs, invisible desyncs), not about "is this ever undesirable" (everything on the list is undesirable). Reasonable people could put `item_status_valid`/`subentity_status_valid` on the floor side instead — the `--force` counterargument is the one to attack if so.
    
    `parent_present` carries no floor (asserted at import time — verified this actually catches a regression, see falsification below).
    
    ## ST3 — threshold in the spec, both call sites
    
    `WorkflowSpec.item_subentity_title_max(item_type)` is the one resolver: a type's own `subentity_title_max:<n>` entry, else `DEFAULT_SUBENTITY_TITLE_MAX` (120, moved from `_interactions.TITLE_ADVISORY_MAX`, which now re-exports the spec constant rather than being a second source of truth). Both call sites fixed:
    - `_services/_validators.py::_subentity_title_max` (the `sq check` advisory)
    - `_services/_subentities.py::_add_block_core` (the create-time advisory) — this was the second, easy-to-miss read the tech lead flagged; confirmed it was reading the raw constant before my fix and would have diverged from an overridden threshold.
    
    Grepped `TITLE_ADVISORY_MAX` post-fix: the only two remaining reads are the re-export definition itself and its own docstring — no live-threshold read anywhere.
    
    ## ST4 — required-context correspondence
    
    Job 1 (verify unchanged): `tests/meta/test_validator_context_requirements_match_what_each_member_reads.py` has **zero diff** and passes unmodified — confirmed subtasks 1-3 leaked no new context read.
    
    Job 2 (extend the same class): chose option (a) — refactored every catalog member to read its level from `_resolved_level` instead of hardcoding, which removes the duplication outright (no second number exists to check against the table). Added a new static scanner, `tests/meta/test_validator_level_is_resolved_not_hardcoded_per_member.py`, same shape as the existing one (ast for docstrings not needed here, walks `CheckIssue(...)` call sites inside each catalog member's own function body via ast, fails if any argument is a literal `"error"`/`"warn"` string instead of a resolved value) — this is what closes the correspondence for option (a): nothing left to drift, and a regression (someone re-hardcoding a literal) is caught structurally.
    
    ## ST5 — parent_present@warn
    
    Mostly fell out of ST1/ST2 as expected. New test file `tests/service/test_parent_present_selectable_at_warn.py`: loads clean over an existing parentless item, ordinary update on it not refused, `sq check` reports warn with exit 0, `parent_present`/`parent_present@error` still refuse a parentless create/update (regression), bundled spec selects it nowhere.
    
    ## Structural properties preserved
    
    1. **Spec/service split.** `DEFAULT_VALIDATOR_LEVEL`/`VALIDATOR_LEVEL_FLOOR`/`parse_validator_entry` all live in `_workflow/_models.py` (spec layer), same placement as `PARAMETERIZED_VALIDATOR_NAMES`. `_resolved_level` (the behaviour) lives in `_services/_validators.py`. `assert set(CATALOG) == VALIDATOR_NAMES` untouched — verified by running the import (it's an import-time assert, so any drift would fail collection). No new `_workflow` → `_services` import edge (checked the diff: `_workflow/_models.py` gained zero new imports).
    2. **Consistency-clause closure.** `git diff` on `CONSISTENCY_CLAUSES`/`UNGUARDED_VALIDATOR_NAMES`/the assert closing their union is **empty** — this task added properties to existing members, no new catalog member, so no new clause was needed, matching the prediction.
    3. **Two-tier `sq check` structure.** Did not touch `_marker_issues`/`_view_target_issues`/`_scan_for_check`; no new/changed docstring in my diff claims `CATALOG` is `sq check`'s complete finding surface.
    
    ## Falsification, both directions, per mechanism (all confirmed then reverted)
    
    - Level-literal scanner: hand-reintroduced a hardcoded `"error"` in `_no_parent` → scanner reddened naming the exact function; reverted → green.
    - Floor rejection: removed `parent_acyclic` from `VALIDATOR_LEVEL_FLOOR` → the floor-refusal unit test reddened (`DID NOT RAISE`); reverted → green.
    - Dedup/override: reverted `effective_validator_names` to the old concatenate-only shape → both new dedup unit tests reddened with the exact duplicate-entry diff shown; reverted → green.
    - Threshold resolution: hardcoded `_subentity_title_max`'s threshold back to `120` → the check-side threshold test reddened; separately hardcoded the create-time advisory back to `120` → the create-time test reddened (proving each call site is independently covered); reverted both → green.
    - `parent_present` floor exclusion: added it to `VALIDATOR_LEVEL_FLOOR` → the import-time assert itself failed immediately (module wouldn't even import) — the strongest possible catch; reverted → green.
    - Level governs gate/report (both directions): patched `_resolved_level` to ignore overrides entirely → 4 tests across two files reddened (the warn-down case, the raise-to-error case, and both `parent_present@warn` behavioural tests); reverted → all green.
    
    ## Gates run
    
    `uv run --all-extras pyright` / `ruff check` / `ruff format --check` on every file I touched: clean. (Whole-repo `ruff check .`/`ruff format --check .` currently carries one pre-existing violation in `_interactions/__init__.py:346` from concurrent work on this branch — not in my diff, confirmed by `git diff` attribution repeatedly through the session; it resolved itself as that work continued, worth a final check on your end.)
    
    Targeted selection, run together:
    ```
    uv run --all-extras pytest tests/unit/test_validators_assignment_surface.py tests/unit/test_validator_engine_scaffold.py \
      tests/service/test_validator_catalog_lift.py tests/service/test_subentity_title_length_advisory.py \
      tests/cli/test_subentity_title_advisory_cli.py tests/service/test_declared_validator_level_governs_report_and_gate.py \
      tests/service/test_parent_present_selectable_at_warn.py tests/service/test_subentity_title_max_threshold_is_spec_resolved.py \
      tests/service/test_ref_rule_target_present_validator.py tests/service/test_records_epic_no_parent_enforcement.py \
      tests/service/test_parent_rule_and_subtask_story_enforcement.py tests/meta tests/integration
    ```
    Final run: **1119 passed, 6 skipped, 0 failed** (this branch's concurrent work — TASK-922 — was mid-refactor for most of my session and briefly held real, unrelated `tests/meta`/`tests/integration` failures of its own; both are fully clean as of the last run). `uv run sq check`: clean. Did not run the full suite (backgrounds/stalls per standing guidance) — this selection plus `tests/meta`/`tests/integration` is what I ran.
    
    ## Where ADR-864 step 1 as specified didn't quite work
    
    The speculative spelling (`name:param@warn`) composes fine, but the ADR doesn't mention the duplicate-entry/override problem that appears the moment a type wants to override an already-bundled member's level or param — `effective_validator_names`'s old concatenate-only behaviour would have silently run the member twice. Not a contradiction, just underspecified; the de-dup-by-bare-name-last-wins design is mine, flagged here as a design decision worth a second look rather than something the record already settled.
    
    Files touched: `src/squads/_workflow/_models.py`, `src/squads/_services/_validators.py`, `src/squads/_services/_subentities.py`, `src/squads/_interactions/__init__.py`; new tests `tests/service/test_declared_validator_level_governs_report_and_gate.py`, `tests/service/test_parent_present_selectable_at_warn.py`, `tests/service/test_subentity_title_max_threshold_is_spec_resolved.py`, `tests/meta/test_validator_level_is_resolved_not_hardcoded_per_member.py`; extended `tests/unit/test_validators_assignment_surface.py`, `tests/unit/test_validator_engine_scaffold.py`; allowlisted the three new module-level dicts in `tests/meta/test_no_unallowlisted_module_level_mutable_state.py`.
- [2026-09-04T14:47:14Z] Elias Python:
  - REV-925 fixes landed (not committed — awaiting review/handoff per the operator's workflow).
  - F1 (high, fixed). Root cause: the F1 dedup keyed on bare validator name only. Fix: a new validator_selection_key(entry) -> (bare, param) in _workflow/_models.py — for a member in PARAMETERIZED_VALIDATOR_NAMES with a param present, the key includes the param (so two different-param entries are independent selections); every other case (non-parameterized member, or a parameterized one named with no param) keys on bare name alone, same as before. Used identically by _check_validators_assignment's duplicate refusal and effective_validator_names' de-dup, so both agree on what counts as a duplicate.
  - Second half of the fix (not asked for by name, but load-bearing): effective_validator_names now lets a bundled bare entry and a type's param'd override of the same member survive as two distinct tuple entries (they used to collapse to one). Left alone, that would make ValidatorEngine._run_per_item's dispatch loop call the member's CATALOG function twice for one item -- a real double-report regression I caught while testing (broke test_a_declared_threshold_moves_where_sq_check_fires_with_the_same_number: 2 matching issues instead of 1). Fixed by making _run_per_item dedupe by bare name before calling self.catalog[bare](ctx) -- each catalog member reads all its own type's matching entries back off ctx.spec/item_spec.validators itself (both _ref_rule_target_present and _resolved_level already do this), so calling it more than once per bare name only repeats the same issue(s).
  - Falsified both directions, twice over (once per half of the fix): (1) reverted validator_selection_key to bare-only -- the exact review repro (two ref_rule_target_present entries) reddened 9 new tests with the exact 'selected more than once' spec-load error; restored, all green. (2) reverted the _run_per_item dedup -- 3 tests reddened with 2-issues-instead-of-1 (including the pre-existing subentity_title_max threshold test, proving this half guards something real, not just my own new test); restored, all green.
  - New tests: tests/unit/test_validators_assignment_surface.py (Plane-1 load-time: different-param pair loads clean, same-param pair refused, same treatment for subentity_title_max via PARAMETERIZED_VALIDATOR_NAMES not a hand-picked member, non-parameterized repeat still refused regardless of level); tests/unit/test_validator_engine_scaffold.py (effective_validator_names key behavior + a dispatch-level test proving the catalog function is called once, not twice, across two param selections); tests/service/test_ref_rule_target_present_validator.py (end-to-end: load-clean two-target selection, one combined warning not two when neither target is satisfied, either target's own edge clears it, same-param-twice refused at load).
  - F2 (low, fixed). Rewrote both flagged docstrings to present-tense fact, no build-history claim: test_parent_present_selectable_at_warn.py's 'Regression: ... exactly as before this dimension existed' -> 'Bare (no suffix) resolves to the same bundled default level as an explicit @error, so both refuse a parentless create.' test_subentity_title_max_threshold_is_spec_resolved.py's 'the threshold value moved from a module constant to a spec-resolved accessor' -> 'the threshold is resolved through WorkflowSpec.item_subentity_title_max, and its number and wording must match TITLE_ADVISORY_MAX exactly.' Grepped both removed phrasings across src/tests post-rewrite: no other copies.
  - F4 (low, resolved by documenting, not constraining). Verified the claim first (parse_validator_entry('ref_rule_target_present:x@y') == ('ref_rule_target_present','x','y') -- confirmed the mis-split). Chose to correct _LEVEL_SEP's docstring rather than add a new item-type-name character restriction: constraining item-type names is a broader change (affects every type, not just this one validator's grammar) than a low-severity finding whose actual failure mode is fail-closed-with-a-confusing-message warrants, and the project's own 'fully overridable item types' stance argues against tightening that surface without a dedicated design call. Rewrote the docstring to state plainly what's enforced (validator names, subentity_title_max's integer param) versus what isn't (ref_rule_target_present's item-type param), and how the mis-split actually surfaces (read as an unknown level, Plane-1-refused, naming the wrong half). Added a pinning test (test_an_at_sign_in_a_ref_rule_target_present_param_mis_splits) so the documented behavior stays true if parsing ever changes. Flagging for the record in case the operator wants the constraining option instead -- it's a small addition (mirror _BARE_TOML_KEY_RE onto item-type keys in _check_item_refs) if so.
  - Narration sweep: ran the validated (against known_positive.py) ast+tokenize scanner over every touched file's added lines -- one hit on first pass (a 'used to refuse... before this test existed' phrasing in my own new test docstring), rewrote to present tense, re-swept clean, grepped the removed wording across src/tests to confirm no copies. Also did a full manual read of every added docstring/comment as a stranger, not just the grep pass.
  - Gates: uv run --all-extras pyright / ruff check . / ruff format --check . all clean, whole repo. Targeted: tests/unit/test_validators_assignment_surface.py tests/unit/test_validator_engine_scaffold.py tests/service/test_ref_rule_target_present_validator.py tests/service/test_parent_present_selectable_at_warn.py tests/service/test_subentity_title_max_threshold_is_spec_resolved.py tests/service/test_validator_catalog_lift.py tests/service/test_declared_validator_level_governs_report_and_gate.py tests/service/test_records_epic_no_parent_enforcement.py tests/service/test_parent_rule_and_subtask_story_enforcement.py plus tests/meta tests/integration -- 1156 passed, 6 skipped, 0 failed. Searched for goldens/canaries that could pin this surface (grepped for the old error-message wording and for validator-catalog references in golden/canary test files and docs/) -- found none pinning validators-surface text or shape, so also ran the two obvious candidates (tests/cli/test_json_output_shape.py, tests/cli/test_workflow_raw_markdown_golden.py) as a sanity check; both green, both in the count above. uv run sq check: clean.
  - Did not run the full suite (per standing guidance) -- this selection plus tests/meta/tests/integration is what I ran. My diff stays scoped to the 5 files above; squads/.squads.json and the concurrent FEAT-906/TASK-923 churn under squads/ this session is the other reviewer's, not mine.
  - Where I think the review's framing could be sharpened, not where I think it's wrong: F1's own text frames the fix as specific to the multi-target pattern, but the actual bug surface is two-sided -- the load-time refusal AND effective_validator_names' dedup both needed the same key change, and that change alone would have introduced a NEW double-report bug for subentity_title_max's bundle-override case if I hadn't also made the dispatch loop idempotent per bare name. That second half isn't mentioned in the finding at all; I'm fairly confident it's load-bearing (falsification #2 above breaks a pre-existing test, not just a new one) rather than me over-engineering, but it's worth a second pair of eyes since it's the one piece I derived rather than was told.
  - @reviewer ready for re-review.
- [2026-09-04T15:44:45Z] Elias Python:
  - REV-925 F5 (high) fixed. Root cause confirmed as the reviewer described: validator_selection_key keyed every PARAMETERIZED_VALIDATOR_NAMES member on (bare, param), but only ref_rule_target_present's own resolver unions multiple entries — item_subentity_title_max returns on the first match. "Is parameterized" and "accepts multiple selections" are different properties; the fix declares the second one explicitly instead of inferring it from the first.
    
    Fix, in _workflow/_models.py:
    - New MULTI_SELECTION_VALIDATOR_NAMES = {"ref_rule_target_present"} — members whose runtime unions every matching entry.
    - New SINGLE_SELECTION_VALIDATOR_NAMES = {"subentity_title_max"} — members whose resolver returns on the first match; a second, differently-parameterised entry is refused as a duplicate, same as a same-param repeat.
    - assert (MULTI | SINGLE) == PARAMETERIZED_VALIDATOR_NAMES, plus a disjointness assert — the closure discipline CONSISTENCY_CLAUSES/UNGUARDED_VALIDATOR_NAMES already apply, extended here: a future parameterised member added without a place in one of these two sets fails import instead of silently inheriting either behaviour.
    - validator_selection_key now branches on MULTI_SELECTION_VALIDATOR_NAMES (not PARAMETERIZED_VALIDATOR_NAMES). Docstrings on validator_selection_key, _check_validators_assignment, and the ItemSpec.validators-adjacent comment in _services/_validators.py updated to name the correct set — no docstring claims unioning for a member that doesn't.
    - No new _workflow -> _services import edge (both new sets are plain frozensets in the spec layer, same placement as PARAMETERIZED_VALIDATOR_NAMES).
    
    subentity_title_max now refuses a repeat again: two differently-thresholded entries on one type ("subentity_title_max:50", "subentity_title_max:80") raise "selected more than once" at spec load, verified directly (WorkflowSpec.model_validate raises SquadsError) — the exact repro from the finding no longer loads clean.
    
    Replacement tests, resolved behaviour not load success:
    - tests/unit/test_validators_assignment_surface.py: replaced test_two_entries_of_the_other_parameterized_member_with_different_params_also_load_clean (asserted load-clean only, the exact miss F5 named) with test_two_differently_thresholded_subentity_title_max_entries_fail_closed_at_load (asserts the SquadsError, "more than once").
    - tests/unit/test_validator_engine_scaffold.py: added test_validator_selection_key_ignores_param_too_for_a_single_selection_member (key-identity level) and test_effective_validator_names_collapses_a_single_selection_members_override (a bundled bare entry + a type's own param'd override collapse to one authoritative entry, not two — the composition-level consequence of the same property). Fixed test_effective_validator_names_keeps_a_bundled_bare_entry_and_a_typed_override_both, which had used subentity_title_max as its "both survive" example — switched it to ref_rule_target_present, a genuine multi-selection member, since with subentity_title_max correctly reclassified the "both survive" premise no longer holds for it.
    - Multi-selection member honoured at the point of use (not just load) was already covered by the pre-existing tests/service/test_ref_rule_target_present_validator.py (test_neither_target_satisfied_produces_one_combined_warning_not_two, test_satisfying_either_selected_target_clears_the_finding) — driven through the real service, unmodified, still green; included in my run for confirmation.
    
    Falsification, both directions:
    1. Reverted validator_selection_key's guard from MULTI_SELECTION_VALIDATOR_NAMES back to PARAMETERIZED_VALIDATOR_NAMES (the exact bug) — 3 tests reddened: the new duplicate-refusal test (DID NOT RAISE), the new key-identity test, and the new collapse test. Restored — all green.
    2. Emptied MULTI_SELECTION_VALIDATOR_NAMES (leaving ref_rule_target_present unclassified) — the import-time union assert failed immediately, module wouldn't import. Restored — imports clean.
    
    Narration sweep: ran the ast+tokenize scanner from the scratchpad (validated against known_positive.py first — 4/4 expected hits) over every line I actually added (git diff, restricted to added lines) across all 4 touched files. Zero hits in my own additions — the only phrase-list matches in the whole-file scan were pre-existing text and, separately, prose in TASK-928's concurrent _item_skill_shadowed addition (not mine, not in scope).
    
    Gates: uv run --all-extras pyright / ruff check . / ruff format --check . all clean on every file I touched (one unrelated file, tests/service/test_item_skill_shadowed_validator.py, needs formatting — that's TASK-928's WIP, not mine).
    
    Selection: grep -rl for validator_selection_key, MULTI_SELECTION_VALIDATOR_NAMES, SINGLE_SELECTION_VALIDATOR_NAMES, PARAMETERIZED_VALIDATOR_NAMES, item_subentity_title_max, effective_validator_names across tests/ -> tests/unit/test_validator_engine_scaffold.py, tests/unit/test_validators_assignment_surface.py, tests/service/test_subentity_title_max_threshold_is_spec_resolved.py. Added tests/service/test_ref_rule_target_present_validator.py for the resolved-behaviour coverage noted above. Plus tests/meta and tests/integration per standing instruction. Run: 1053 passed, 6 skipped, 11 failed (75/75 in my own target files pass; the 1 failure inside my selection and the 10 in tests/meta/tests/integration are unrelated — traced to TASK-928's concurrent, uncommitted src/squads/_specs/workflow.toml change, which adds validators = ["item_skill_shadowed"] to the skill type and a bare "TASK-923" ref in a docstring; that breaks test_bundled_spec_declares_epics_validators_addition_only's "only epic has validators" assumption, the stray-ticket-reference gate, and the override-manifest/kind-uniformity tests whose content hashes now disagree with the stale manifest. Confirmed via git diff on workflow.toml and by running my 4 target files alone: 75 passed, 1 pre-existing failure, same one). Did not run the full suite. uv run sq check: clean.
    
    Where I think the review's framing could be sharpened: none — F5 as written matches what I found exactly, root cause and all. One thing worth flagging for the record since it's not in the finding: the same conflated-property mistake could recur for CONSISTENCY_CLAUSES/UNGUARDED_VALIDATOR_NAMES if a future catalog member needs a similarly two-part classification — the assert-over-a-union pattern this fix adds is now the second instance of that discipline in this module, which is the shape the task asked for.
    
    @reviewer ready for re-review.
- [2026-09-08T13:38:47Z] Elias Python:
  - F5 residue + F6, both addressed. No behaviour change for F5; F6 is message-only with a new pinning test.
    
    **F5 — docstring rewrite.** `effective_validator_names`'s paragraph (`_workflow/_models.py`) no longer states a property over `PARAMETERIZED_VALIDATOR_NAMES` as a whole. It now says: a `MULTI_SELECTION_VALIDATOR_NAMES` member (`ref_rule_target_present`) with two different params keys differently for each and both survive, because its own resolver unions every entry; a `SINGLE_SELECTION_VALIDATOR_NAMES` member (`subentity_title_max`) keys on its bare name alone regardless of param, so it never reaches this function with two surviving entries — `_check_validators_assignment` refuses the second outright, because that member's resolver reads only its first matching entry rather than unioning. No test change (none needed — an existing assertion already proves the corrected wording).
    
    **Whitespace-collapsed identifier scan, run before handing back.** Built `identifier_wrap_scan.py` in the scratchpad (ast for docstrings, tokenize for comment runs, per-unit whitespace-stripped substring match, `--wrap-only` reports only hits a plain grep on that same unit would miss). Validated against a known positive first: a saved pre-fix copy of `_models.py` — the tool found the exact wrapped occurrence (`PARAMETERIZED_VALIDATOR_/\nNAMES` at the `effective_validator_names` docstring) that `grep -c` misses (grep: 8 hits, scanner: +1 wrap-only hit there). With the tool proven against that positive, ran it `--wrap-only` over `src/squads` and `tests/` for `PARAMETERIZED_VALIDATOR_NAMES`, `MULTI_SELECTION_VALIDATOR_NAMES`, `SINGLE_SELECTION_VALIDATOR_NAMES`, `validator_selection_key`, `item_subentity_title_max`, `effective_validator_names` — 0 hits in both trees. No other wrapped occurrence of these names remains anywhere in the corpus.
    
    **F6 — message rewrite.** Replaced the "is selected more than once with the same selection (A and B)" wording (self-contradictory when A and B are visibly different) with `_repeat_selection_message`, a small helper called from `_check_validators_assignment`. It names the actual reason: for a differing-param case (only reachable via a `SINGLE_SELECTION_VALIDATOR_NAMES` member) — "`subentity_title_max` resolves only its first matching entry, so the second would be silently ignored rather than take effect — refused here instead; keep one entry"; for a differing-level-only case (any member, since `@<level>` never distinguishes a selection) — "...an `@<level>` suffix alone does not make two entries independent selections; keep one entry"; for a literal repeat — "...keep one entry". Pinned with two new tests in `tests/unit/test_validators_assignment_surface.py` (`test_the_refusal_names_the_reason_for_a_differing_param_on_a_single_selection_member`, `test_the_refusal_names_the_reason_for_a_differing_level_with_no_param_involved`), each matching a distinctive substring of its own branch. Falsified both directions: reverted the call site to the old inline message — both new tests reddened (regex did not match, old wording shown in the failure); restored — both green, full file green (36/36).
    
    **Gates.** pyright/ruff check/ruff format clean project-wide. Selection: grepped `_repeat_selection_message`, `MULTI_SELECTION_VALIDATOR_NAMES`, `SINGLE_SELECTION_VALIDATOR_NAMES`, `validator_selection_key`, `effective_validator_names`, `_check_validators_assignment` across `tests/` → `tests/unit/test_validator_engine_scaffold.py` + `tests/unit/test_validators_assignment_surface.py`, plus `tests/meta` and `tests/integration` per standing instruction. Ran the union: 1046 passed, 6 skipped, 0 failed. Did not run the full suite. `sq check`: clean.
    
    @reviewer ready for re-review on F5/F6.
<!-- sq:discussion:end -->
