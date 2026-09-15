---
id: REV-925
sequence_id: 925
type: review
title: 'Validator selection grammar: declared level, floor and threshold'
status: Approved
author: reviewer
refs:
- FEAT-898:addresses
- ADR-864
subentities:
- local_id: F1
  title: ref_rule_target_present duplicate-entry check rejects legitimate multi-target
    selections
  status: Verified
  severity: high
- local_id: F2
  title: 'Narration: two build-history claims fail the stranger test'
  status: Verified
  severity: low
- local_id: F3
  title: Commit bundles unrelated FEAT-906 surface into TASK-924's delivery
  status: WontFix
  severity: medium
- local_id: F4
  title: '@ separator''s no-collision claim is unverified for item-type names containing
    @'
  status: Verified
  severity: low
- local_id: F5
  title: 'Duplicate-selection fix over-generalized: subentity_title_max silently accepts
    an ambiguous second threshold'
  status: Verified
  severity: high
- local_id: F6
  title: Repeat-selection message calls two visibly different entries 'the same selection'
  status: Verified
  severity: low
created_at: '2026-09-04T14:23:05Z'
updated_at: '2026-09-08T14:55:01Z'
---
<!-- sq:body -->
## Scope

One batch review over TASK-924's single commit — `git diff 110b845d^..110b845d -- src/ tests/`
(11 files, ~980 added lines). TASK-924 builds ADR-864's step-1 assignment grammar: a `name`,
`name:param`, `name@level`, or `name:param@level` selection, a declared floor
(`VALIDATOR_LEVEL_FLOOR`) a selection may raise but not lower, a spec-resolved
`subentity_title_max` threshold, and `parent_present` selectable at warn.

Read: TASK-924's handback (subtasks ST1-ST5, all Done), ADR-864 in full including the
gate-clause correction and the ruling/accepted build order. Driven: targeted pytest against
every touched/added test file, ruff, pyright, plus my own falsification of three claims (see
below). Not driven: the full suite (pre-verified green, 4889 passed/12 skipped, not re-run here).

## Falsification spot-checks (both green)

1. **Floor enforcement.** Neutered `_check_validator_level`'s floor lookup (`floor = None`) —
   both `test_a_floor_member_refuses_a_level_below_its_floor` cases (parent_acyclic,
   subentity_container_marker) went red (`DID NOT RAISE`). Restored, green.
2. **Spec-resolved threshold, create-time call site.** Hardcoded `_services/_subentities.py`'s
   check back to `> 120` — `test_a_declared_threshold_moves_where_the_create_time_advisory_fires`
   went red. Restored, green. (The `sq check` call site — `ctx.spec.item_subentity_title_max`
   in `_services/_validators.py` — is the same one accessor; not separately mutated.)
3. **Level-not-hardcoded meta gate.** Hardcoded `_dangling_ref`'s level back to a literal
   `"warn"` — `test_no_catalog_member_passes_a_literal_level_string_to_checkissue` went red.
   Restored, green.

## Floor table — per-member verdict

Current floor: `parent_acyclic`, `subentity_container_marker` (both `error`), matching
ADR-864's own two named cases. Applying the ADR's tiering test (*can a competent squad be in
this state on purpose, indefinitely, with nothing else in the engine misbehaving because of
it?*) to each of the eight error-level members:

- **`parent_acyclic`** — floor, agree (read: BUG-865, a proven hang; not a policy question).
- **`subentity_container_marker`** — floor, agree (ADR-864 ruled this explicitly; the only
  plane that can see the desync, per its own docstring — read).
- **`parent_present`** — no floor, agree; the ADR names this by name as the deliberate
  exception, and the code carries an assert pinning it (see finding below on that assert).
- **`item_status_valid`** — not floor, agree. Driven: `_apply_status` (`_services/_items.py`)
  checks target-vocabulary membership unconditionally and only skips the *transition* lookup
  under `--force`, so a stuck item is one `--force` away from a valid state regardless of how
  it got stuck. Read: `status_badge` (`_badges.py`) falls back to a neutral badge on an
  unrecognized status rather than crashing, so rendering is unaffected either way.
- **`subentity_status_valid`** — not floor, agree, identical shape one level down
  (`_apply_subentity_status`/`_require_declared_status` in `_services/_subentities.py`,
  read — same unconditional-vocabulary-then-waivable-transition split).
- **`subtask_story_mapping`** — not floor, agree. Read: `sub.story` is consumed only by
  `_discussion.py`'s rollup-table row and `_views.py`'s field projection — display only,
  nothing gates or walks on it resolving.
- **`parent_in`** — not floor, agree. Read: the ancestor walk (`_services/_base.py`, the
  `parent_acyclic`-guarded one) and the subtree/tree builders (`_views.py::children_by_parent`)
  key off `item.parent` alone, never `parent_allowed`; a wrong-type parent doesn't affect
  termination or grouping.
- **`no_parent`** — not floor, agree, same reasoning; nothing downstream assumes a
  `records`/`roster` item is parentless in order to function.

No member is missing from the floor by my own pass — I re-ran the same test against all eight
and land on the same two the table names. I looked specifically for a downstream consumer that
would silently misbehave on a `parent_in`/`no_parent` violation (badge resolution, view
grouping, role/authoring-owner resolution keyed off parent type) and found none.

## What else I checked and found clean

- **`@` separator.** Confirmed no collision with `@mention` extraction (`_discussion.py`'s
  `_MENTION_RE` is scoped to comment-text parsing, an unrelated namespace) or with item ids/ref
  syntax. One narrow gap noted as a finding below (item-type names have no character
  restriction, unlike `[ref_kinds]` keys).
- **Layering.** No new `_workflow` → `_services` import edge; `DEFAULT_VALIDATOR_LEVEL`/
  `VALIDATOR_LEVEL_FLOOR` live beside `VALIDATOR_NAMES`/`PARAMETERIZED_VALIDATOR_NAMES` in
  `_workflow/_models.py`, same placement rationale.
- **`CONSISTENCY_CLAUSES`/`UNGUARDED_VALIDATOR_NAMES` closure** — untouched by this diff, no
  new member added, no new bucket decision needed. Confirmed by reading the region; not touched
  by `git diff`.
- **Level-resolution completeness.** All 16 `VALIDATOR_NAMES` catalog members call
  `_resolved_level` and pass its result into `CheckIssue(...)` — none left on a literal.
- **Threshold single-source-of-truth.** Both call sites (`_services/_validators.py`'s
  `_subentity_title_max`, `_services/_subentities.py`'s create-time advisory) read
  `WorkflowSpec.item_subentity_title_max`; `_interactions.TITLE_ADVISORY_MAX` is a genuine
  re-export (`= DEFAULT_SUBENTITY_TITLE_MAX`) read only by tests, not a second live threshold.
- **`parent_present` at warn.** `test_selecting_it_at_warn_loads_clean_over_an_existing_parentless_item`
  covers exactly the on-disk-parentless-item scenario the ADR flags; read + it's in my green
  targeted run.
- **Two-tier `sq check` structure.** `_marker_issues`/`_view_target_issues`
  (`_services/_maintenance.py`) untouched by this diff; no comment in the diff claims `CATALOG`
  is the complete finding surface.
- **No ticket IDs** in any new source/test file name or body.
- **ruff/pyright clean** on every touched file; targeted pytest
  (`tests/meta tests/unit/test_validators_assignment_surface.py
  tests/unit/test_validator_engine_scaffold.py` + the 3 new service test files +
  `test_validator_catalog_lift.py`/`test_subentity_title_length_advisory.py`/
  `test_subentity_title_advisory_cli.py`) — 386 passed.

Findings below. One narration finding bundles two instances per the "report once" convention.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 925 add-finding "…" --severity medium`; track with `sq review 925 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — ref_rule_target_present duplicate-entry check rejects legitimate multi-target selections

<!-- sq:finding:F1:body -->
**driven.** `_check_validators_assignment`'s new duplicate-bare-name check
(`_workflow/_models.py`, the `if bare in seen: errors.append(...)` block) refuses ANY type
whose own `validators` list names the same bare validator twice — but `ref_rule_target_present`
is explicitly designed to be named more than once per type, each entry selecting a *different*
target type. Its runtime (`_ref_rule_target_present`, `_services/_validators.py`) builds its
`targets` set from a comprehension over every matching entry in `item_spec.validators`, and its
own Plane-1 companion check (`_check_ref_rule_targets`) validates each entry independently —
both pre-existing, both unmodified by this task apart from switching `.partition(":")` to
`parse_validator_entry`. The new duplicate check sits in front of both and blocks the pattern
they were built to support.

Reproduced directly against the current tree (feature type, one `ref_rules` entry each for
`contract` and `milestone`, selecting both via two `ref_rule_target_present:<T>` entries):

```
FAILED TO LOAD: Invalid workflow spec:
  - item 'feature': validator 'ref_rule_target_present' is named more than once in its own
    validators list ('ref_rule_target_present:contract' and 'ref_rule_target_present:milestone')
```

Checked out `_workflow/_models.py` at the parent commit (110b845d^, before this task) with the
same spec — it loads clean. So this is a regression this commit introduces, not a pre-existing
limitation.

The check's own docstring reasons "two entries for one member is an ambiguous declaration
(which suffix wins is not this loader's call to make)" — that premise is false for this member:
nothing "wins," the runtime unions every entry. The check needs to distinguish "same bare name,
same param" (genuinely redundant/ambiguous — worth refusing) from "same bare name, different
param on a member whose runtime unions multiple entries" (legitimate).

Impact: blocks the exact multi-target-type pattern ADR-864 and this task's own grammar are
building toward for the FEAT-899/900/901/902 follow-on catalog members that will want to select
several types at once. Fails closed (a spec-load error, not silent misbehavior), which limits
the blast radius, but it's a real capability regression with no test coverage catching it — the
green 4889-test suite has no test exercising two `ref_rule_target_present:<T>` entries on one
type.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-09-08T13:27:07Z] Paul Reviewer:
  - Verified against the current tree (tip c804c64c): re-drove the repro end-to-end in a throwaway squad — a feature type with implements/contract + addresses/milestone rules and both ref_rule_target_present selections loads clean, and sq check emits one combined warning naming both targets; dropping one selection narrows the message, so both entries are honoured at the point of use. Closing.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Narration: two build-history claims fail the stranger test

<!-- sq:finding:F2:body -->
**read.** Full list, per the "report once" convention — swept every added comment/docstring in
the diff by hand (not just grep) and applied the stranger test (could someone who never saw the
diff, and is writing this code from scratch today, have written this sentence?).

1. `tests/service/test_parent_present_selectable_at_warn.py`,
   `test_selecting_it_at_error_still_refuses_a_parentless_create`'s docstring: *"Regression: bare
   (today's implicit meaning) and an explicit `@error` behave alike, and both still refuse
   exactly as before this dimension existed."* — "before this dimension existed" has no referent
   a reader of the shipped code can check; the level dimension has always existed for them.
2. `tests/service/test_subentity_title_max_threshold_is_spec_resolved.py`,
   `test_the_bundled_default_message_text_is_unchanged`'s docstring: *"...the threshold value
   moved from a module constant to a spec-resolved accessor..."* — same shape: a "moved from"
   claim whose "from" state exists only in git history, not in anything the reader can observe.

Both pass the carve-out test's opposite: the "before" exists nowhere but the diff (not a corpus
state or spec drift a reader can reproduce), so both fail per the standing narration rule.

Not flagged (checked against the same test, kept as fine): `test_the_bundled_spec_selects_
parent_present_nowhere`'s neighboring reference to "today's implicit meaning" and the two
"reproduces today's ... default" phrasings in the same threshold test file use "today" as
"currently," a checkable present-tense fact, not a build-history delta. The
`test_selecting_it_at_warn_loads_clean_over_an_existing_parentless_item` docstring's "created
before the override existed" describes the TEST'S OWN setup ordering (create item, then add the
override) — a corpus state an adopter can reproduce, so it's exempt under the carve-out.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-09-08T13:27:09Z] Paul Reviewer:
  - Verified against the current tree: both phrases still grep to zero across src/ and tests/ (known positive: 2 hits at 110b845d, so the pattern works). Closing.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Commit bundles unrelated FEAT-906 surface into TASK-924's delivery

<!-- sq:finding:F3:body -->
**read.** The commit under review (110b845d, `src/squads/_interactions/__init__.py`) adds
`ITEM_SKILL_VIEW_NAME`, `item_type_for_skill_slug`, `_RoleGuideBearing`, and
`item_skill_role_sections` — none of which exist at the parent commit (110b845d^), and none of
which the validator-grammar work reads or is read by. These are the per-item-type-skill/view
collapse pieces the *other* concurrently-running review (FEAT-906, explicitly out of my scope
per this run's brief) is reviewing; `_services/_maintenance.py` and `_views.py` on the current
tip already consume them, confirming they belong to that surface, not this one.

This doesn't make the validator-grammar code wrong, but it means the diff I was handed to
review isn't actually scoped to TASK-924 — a future `git bisect`/`git blame` against this
commit for a validator-grammar question will also surface unrelated skill/view code, and vice
versa. Worth a note for whoever manages commit hygiene across the two concurrent task branches;
not something I evaluated for correctness (that's the other reviewer's surface by design).
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — @ separator's no-collision claim is unverified for item-type names containing @

<!-- sq:finding:F4:body -->
**read + inferred.** `_LEVEL_SEP`'s docstring claims `@` "never appears anywhere else in this
grammar: not in a validator name..., not in a `:<param>` value (an item-type name or a small
integer)". Verified true for the `subentity_title_max` param (digit-only, enforced by
`_check_validator_param`). Not actually guaranteed for `ref_rule_target_present`'s param, which
is an item-type name: unlike `[ref_kinds]` keys (constrained to `_BARE_TOML_KEY_RE`,
`[A-Za-z0-9_-]+`, deliberately excluding `@` and `:` — read, `_workflow/_models.py`), nothing in
the spec loader restricts an `[items.<type>]` TOML key's character set; the project's own
"fully overridable" design (memory: only the 3 roster types are reserved) suggests this is
intentional elsewhere.

Inferred consequence, not driven: a project naming a custom type with `@` in it (e.g.
`[items."x@y"]`) and then selecting `ref_rule_target_present:x@y` would have the entry
mis-split (`@` partitions first, so `y` becomes the "level" and fails Plane-1 as an unknown
level) — it fails closed with a confusing message rather than silently misbehaving, so this is
low severity, not a correctness bug. Worth either a defensive check at spec-load time (an
item-type key must itself be `@`/`:`-free, mirroring `_BARE_TOML_KEY_RE`) or narrowing the
docstring's claim to what's actually enforced.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-09-08T13:27:11Z] Paul Reviewer:
  - Verified against the current tree: the reasoning now lives on _LEVEL_SEP (_workflow/_models.py:261-275), scopes the guarantee to validator names and subentity_title_max's integer param, states plainly that ref_rule_target_present's item-type param is not covered and fails closed naming the wrong half, and test_an_at_sign_in_a_ref_rule_target_present_param_mis_splits pins the split. Documentation-only ruling stands. Closing.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Duplicate-selection fix over-generalized: subentity_title_max silently accepts an ambiguous second threshold

<!-- sq:finding:F5:body -->
**driven.** This is the exact failure mode flagged for scrutiny: `validator_selection_key`
generalizes "keyed on (bare, param) rather than bare alone" to *every* member in
`PARAMETERIZED_VALIDATOR_NAMES` — but the premise that justifies it ("its runtime unions every
matching entry") only holds for `ref_rule_target_present`. `subentity_title_max`'s own resolver
(`WorkflowSpec.item_subentity_title_max`) returns on the *first* matching entry it finds in
`ts.validators` — it does not union. So two different-param `subentity_title_max` entries are
no longer flagged as a duplicate (different keys ⇒ "independent selections"), both load clean,
and the second is silently inert: not an error, not a warning, nowhere reported.

Reproduced (direct model validation, `subentity_title_max:80` + `subentity_title_max:100` on
`task`):

```
LOADED OK (ambiguous double-threshold accepted!): ['subentity_title_max:80', 'subentity_title_max:100']
resolved threshold -> 80
```

And end-to-end through the real service (override file, `feature` type,
`["subentity_title_max:50", "subentity_title_max:80"]`, a 65-char title — over 50, under 80):

```
RESOLVED THRESHOLD: 50
CREATE-TIME ADVISORY (65-char title): Title is 65 chars ...
SQ CHECK MATCHING ISSUES COUNT: 1
  -> advisory: story US1 title is 65 chars (threshold: 50) ...
```

Both call sites agree with each other (both read the one accessor, so no cross-call-site
disagreement — that part of the original task's guarantee holds), but the `:80` entry the
adopter wrote has zero effect, silently, forever. No error, no warning, nothing distinguishes
this from the entry having never been written.

This directly contradicts the design principle the codebase already applies to the sibling
case: `_check_ref_rule_targets`'s own reasoning for refusing a paramless
`ref_rule_target_present` entry is "refused here rather than silently doing nothing forever" —
exactly the property this new gap violates for `subentity_title_max`.

The dev's own new test (`test_two_entries_of_the_other_parameterized_member_with_different_
params_also_load_clean`, `tests/unit/test_validators_assignment_surface.py`) asserts this loads
clean and stops there — it doesn't assert on the *resolved* value or exercise `sq check`, so it
never surfaces that the second entry is inert. Its own docstring flags the generalization
("`PARAMETERIZED_VALIDATOR_NAMES` membership decides this, not a hand-picked member ... even
though nothing bundled selects it more than once") without checking whether the premise the
generalization rests on actually holds for the member it names.

Note on scope, since this wasn't asked about directly: the **dispatch-loop** dedup
(`ValidatorEngine._run_per_item`'s `run: set[str]`) itself is *not* the bug — driven above, it
produces exactly one `sq check` finding either way, because `_subentity_title_max` ignores
`name` and re-derives the threshold from `ctx.spec` regardless of dispatch count. The gap is
one layer up, in `validator_selection_key`'s Plane-1 identity, not in the dispatch count.

Fix shape: `validator_selection_key` needs to know not just "is this member parameterized" but
"does this member's own resolver union multiple entries, or read only one" — the same
distinction the dispatch-loop comment already draws in prose but doesn't encode. Concretely,
either scope the (bare, param) keying to `ref_rule_target_present` specifically (a second,
narrower set, or a per-member flag) rather than all of `PARAMETERIZED_VALIDATOR_NAMES`, or make
`item_subentity_title_max` itself refuse (at Plane-1, via a new check alongside
`_check_validator_param`) more than one param-bearing entry for the same type.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-09-08T13:26:57Z] Paul Reviewer:
  - Re-verified against the current tree (tip c804c64c, fix commit c04da804). Three of four criteria hold; the fourth does not, so this stays Open.
    
    **Holds — the behavioural core (driven).**
    - The repro is dead: `["subentity_title_max:50", "subentity_title_max:80"]` on one type now raises at spec load ("selected more than once"). Same refusal for same-param repeats, for `:50@warn` + `:80@error`, and for bare + param'd. A single entry still resolves (50).
    - `ref_rule_target_present` with two different targets still loads and still honours both at the point of use. Driven end-to-end in a throwaway squad (`.overrides/workflow.toml`, `feature` with `implements→contract` + `addresses→milestone` rules and both selections): one combined `sq check` warning naming `addresses/implements` and `contract/milestone`; dropping the `:contract` entry narrows the message to `addresses` / `milestone`, so each entry demonstrably contributes. Satisfying either clears it.
    - The closure asserts bite, all four ways: emptying MULTI, emptying SINGLE, adding a third parameterised member (`parent_in`) without classifying it, and putting one member in both — every one fails at import with the intended message. This was the thing whose absence caused F5, and it does bite.
    - The replacement tests redden on a revert. Reverting `validator_selection_key`'s guard to `PARAMETERIZED_VALIDATOR_NAMES` (the exact bug) reddens 3, including the new duplicate-refusal test. Swapping the two classifications (asserts still satisfied) reddens 11, four of them service-level. Also probed the resolver-vs-classification direction the asserts cannot see: making `_ref_rule_target_present` first-match reddens 2 pre-existing service tests, so the dangerous direction is covered.
    
    **Does not hold — criterion 4, a docstring still claiming unioning for a member that does not union.**
    
    `effective_validator_names`, `src/squads/_workflow/_models.py:493-499`:
    
    > A type's own *extra* naming a ``PARAMETERIZED_VALIDATOR_ NAMES`` member with two *different* params (``ref_rule_target_present:contract`` and ``ref_rule_target_present:milestone``) keys differently for each and both survive as independent selections; the dispatch engine ... still calls the member's catalog function only once per bare name regardless, since a parameterized member reads every one of its own entries back off the spec itself rather than off what survived here.
    
    Both halves are false for the other member of the set it names. Driven:
    
    ```
    ref_rule_target_present (MULTI): ('ref_rule_target_present:contract', 'ref_rule_target_present:milestone')
    subentity_title_max  (SINGLE):  ('subentity_title_max:80',)
    ```
    
    Two different params of `subentity_title_max` do not "both survive" — they collapse — and `item_subentity_title_max` does not read "every one of its own entries", it returns on the first. This is verbatim the conflation F5 named, still stated as a rule over `PARAMETERIZED_VALIDATOR_NAMES`, in the third of the three functions that share `validator_selection_key`'s identity (and the one this docstring's own second paragraph cross-references). ADR-864's step 1 is explicit that no docstring should assert a catalog-wide property nothing verifies; this one asserts a property the code now contradicts.
    
    Why the sweep missed it: the identifier is line-wrapped mid-token (`PARAMETERIZED_VALIDATOR_` / newline / `NAMES``), so `grep PARAMETERIZED_VALIDATOR_NAMES` returns four hits in `src/` and this is not one of them. Any grep-driven check of this criterion produces a false zero. It is the only such wrap on these identifiers in `src/` — checked.
    
    **Scope of what is left:** the one paragraph above, corrected to say the same thing `validator_selection_key` and `_check_validators_assignment` now say (MULTI keys on param and both survive; SINGLE and every non-parameterized name key on the bare name alone and collapse). Nothing behavioural. No test change required, though a line in `test_effective_validator_names_collapses_a_single_selection_members_override` already proves the corrected wording.
- [2026-09-08T14:54:12Z] Paul Reviewer:
  - Verified against tip c15336d9 (docstring rewrite in 6103ed99). effective_validator_names' paragraph (_workflow/_models.py:490-502) no longer states a property over PARAMETERIZED_VALIDATOR_NAMES as a whole -- it now attributes the surviving-both-entries/unioning behaviour to MULTI_SELECTION_VALIDATOR_NAMES only, and states plainly that a SINGLE_SELECTION_VALIDATOR_NAMES member keys on its bare name alone and never reaches this function with two surviving entries because _check_validators_assignment refuses the second. Matches what validator_selection_key/_check_validators_assignment actually do, driven.
- [2026-09-08T14:54:18Z] Paul Reviewer:
  - Re-derived the wrap-scan completeness claim independently, not trusting the dev's tool: wrote my own whitespace-collapsed scanner (own script, not the dev's), validated it against a known positive first -- git show 6103ed99^:src/squads/_workflow/_models.py, PARAMETERIZED_VALIDATOR_NAMES: plain grep 8, collapsed-whitespace count 9, reproducing the exact wrap the dev's tool found. Then ran my scanner over the current tree (src/squads + tests) for the same six identifiers (PARAMETERIZED_VALIDATOR_NAMES, MULTI_SELECTION_VALIDATOR_NAMES, SINGLE_SELECTION_VALIDATOR_NAMES, validator_selection_key, item_subentity_title_max, effective_validator_names): zero wrap-only hits in every case, plain-grep count equals whitespace-collapsed count for all six. Completeness claim independently confirmed.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Repeat-selection message calls two visibly different entries 'the same selection'

<!-- sq:finding:F6:body -->
**driven.** `_check_validators_assignment`'s repeat-selection message names the two entries verbatim and then calls them "the same selection", which reads as self-contradictory whenever they are not textually identical:

```
item 'feature': validator 'subentity_title_max' is selected more than once with the same selection ('subentity_title_max:50' and 'subentity_title_max:80')
item 'decision': validator 'no_parent' is selected more than once with the same selection ('no_parent@warn' and 'no_parent@error')
```

An adopter reads two visibly different strings and a sentence insisting they are the same, with nothing saying *why* the loader considers them one selection — that the level suffix never distinguishes an entry, and that a param distinguishes one only for a member whose resolver unions its entries. The information that would let them fix it (write one entry; the threshold/level is a property of the single selection, not a second one) is in the docstring, not in the message.

Not introduced by the multi-selection fix: the level-suffix case has produced this wording since `validator_selection_key` started ignoring `@level` (4fdf57db). The fix broadens it to the param case, which is where it reads worst, because a differing param looks far more like a deliberate second selection than a differing level does.

Shape of a fix: distinguish the identical-entry case from the same-key-different-text case in the message, e.g. "…is selected more than once ('subentity_title_max:50' and 'subentity_title_max:80' are the same selection — the param does not make them independent for this validator; keep one)". Message-only; no behaviour change and no new refusal.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-09-08T14:54:33Z] Paul Reviewer:
  - Verified against tip. _repeat_selection_message (_workflow/_models.py) names the actual reason per case, driven end-to-end: param case on subentity_title_max -> "...resolves only its first matching entry, so the second would be silently ignored rather than take effect -- refused here instead; keep one entry"; level-only case on no_parent -> "...an '@<level>' suffix alone does not make two entries independent selections; keep one entry"; literal repeat -> "...('no_parent' repeated) -- keep one entry". Two new pinning tests (test_the_refusal_names_the_reason_for_a_differing_param_on_a_single_selection_member, test_the_refusal_names_the_reason_for_a_differing_level_with_no_param_involved) both green.
- [2026-09-08T14:54:37Z] Paul Reviewer:
  - Adopter's read: each message now tells someone what they did wrong AND what to do -- names the two literal entries, states the specific reason they collide (first-match-only resolver, or a level suffix not being independence), and ends 'keep one entry' every time. Closes the self-contradiction F6 raised. No behaviour change, message-only, as intended.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-04T14:24:56Z] Paul Reviewer:
  - Verdict: ChangesRequested. F1 (high) is a real regression — the new duplicate-bare-name check silently forecloses ref_rule_target_present's multi-target-type pattern, which is load-bearing for FEAT-899/900/901/902; needs a fix distinguishing same-param duplicates (redundant, reject) from different-param duplicates on a member whose runtime unions entries (legitimate, allow). F2/F4 are low-severity cleanups. F3 is informational (commit hygiene, not this task's own defect).
- [2026-09-04T14:25:02Z] Paul Reviewer:
  - @python-dev four findings, F1 (high) blocking — see review body for the full falsification/floor-verdict record.
- [2026-09-04T14:26:22Z] Catherine Manager:
  - F3 accepted as accurate and closed WontFix: the commit-hygiene mixing is mine, not the devs. Two devs edited _interactions/__init__.py concurrently -- TASK-924 added the TITLE_ADVISORY_MAX re-export, TASK-923 added ITEM_SKILL_VIEW_NAME and the slug inversion -- and I staged by path, which cannot separate two authors edits to one file. Both halves are committed, green and reviewed by their own reviewers; unmixing them means rewriting two commits for no functional gain. The lesson is that per-path staging is not per-task staging when devs share a file.
  - F1 verified independently at _workflow/_models.py:1393 -- the check errors on any repeated bare name within a types own list, which refuses the legitimate one-entry-per-target-type pattern. Real capability regression and it would have propagated into FEAT-899 through 902. Floor verdict accepted: all eight classifications agreed, no member missing, and re-derived from the downstream consumers rather than the comments own reasoning.
- [2026-09-04T15:33:23Z] Paul Reviewer:
  - Re-review of 4fdf57db: F1 confirmed fixed (repro dead; mutation-tested — reverting validator_selection_key to bare-only reddens 6 tests, including the two new ones asserting the multi-target pattern loads clean). F2 confirmed (old phrasing greps to zero, was 1/1 at 110b845d — known positive validated). F4: ruling below.
- [2026-09-04T15:33:25Z] Paul Reviewer:
  - F4 ruling: accurate documentation satisfies this finding without enforcement. The docstring no longer claims a universal no-collision guarantee — it now precisely scopes where @ is excluded (validator names, subentity_title_max's param) and where it isn't (ref_rule_target_present's param), states the actual fail-closed consequence, and a new test pins the exact mis-split. Restricting item-type name characters is a broader, separate design question (it would touch every [items.<type>] consumer, not just this grammar) and the failure mode is safe (fails closed with a message that, per the docstring's own admission, names the wrong half — a known, written-down rough edge, not a silent one). Agree with not building the constraint for this.
- [2026-09-04T15:33:27Z] Paul Reviewer:
  - NEW finding, F5 (high), not yet addressed — do not approve as-is. The fix over-generalizes: validator_selection_key keys every PARAMETERIZED_VALIDATOR_NAMES member on (bare, param), but only ref_rule_target_present's resolver unions multiple entries. subentity_title_max's resolver (item_subentity_title_max) returns on the FIRST match — so two different-threshold entries now load clean (previously correctly refused) and the second is silently, permanently inert: no error, no warning, contradicts the project's own stated principle (_check_ref_rule_targets: 'refused here rather than silently doing nothing forever'). Driven end-to-end (service + sq check) — see finding body. This is the same failure class the dispatch-loop check was meant to rule out, just one layer up (Plane-1 identity, not dispatch count) — the dispatch loop itself is fine, verified separately.
- [2026-09-04T15:33:29Z] Paul Reviewer:
  - @python-dev @tech-lead F5 blocks approval. Holding REV-925 at ChangesRequested.
- [2026-09-04T15:34:28Z] Catherine Manager:
  - F5 verified independently: PARAMETERIZED_VALIDATOR_NAMES holds exactly two members and only ref_rule_target_present unions -- item_subentity_title_maxs own docstring says "its own selection when its validators list carries one", singular, first match. So the fix keyed off the wrong property: is-parameterized is not accepts-multiple-selections. The regression is real and it converts a correct refusal into silent permanent inertness, which is the exact thing _check_ref_rule_targets in the same file refuses on principle.
  - Reviewer was right to check the layer I pointed him at and tell me it was clean: the dispatch-loop dedup is not the bug. Also noting the shape of the dev test that missed it -- it asserted the spec loads and never checked the resolved value, so it confirmed the change rather than disproving it. That is the pattern the 0.14 audit named and it recurred inside a fix for a review finding.
- [2026-09-08T13:27:55Z] Paul Reviewer:
  - Re-review of c04da804 against the current tree. F1/F2/F4 re-verified and closed (Verified) — they had been sitting at Fixed. F3 stays WontFix. F5's behavioural core holds: repro dead, multi-target still unions at the point of use (driven end-to-end), all four closure-assert mutations bite at import, and the replacement tests redden on both a guard revert (3 tests) and a swapped classification (11, four service-level). I also probed the direction the asserts cannot see — making the unioning resolver first-match reddens 2 pre-existing service tests, so the dangerous side is covered; the benign side (a SINGLE member's resolver becoming unioning) reddens nothing, which is fail-closed and not worth building for.
  - F5 back to Open on criterion 4 only: effective_validator_names' docstring (_workflow/_models.py:493-499) still states, over PARAMETERIZED_VALIDATOR_NAMES, that two different params 'both survive as independent selections' and that 'a parameterized member reads every one of its own entries' — both false for subentity_title_max, driven. That is verbatim the conflation F5 named, left in the third function sharing validator_selection_key's identity. A grep cannot find it: the identifier is line-wrapped mid-token, so the obvious sweep returns a false zero. One paragraph, no behaviour, no test change.
  - New F6 (low): the repeat-selection error message names two visibly different entries and calls them 'the same selection', with no hint why. Pre-existing wording for the level case, broadened by this fix to the param case where it reads worst. Message-only.
- [2026-09-08T13:27:56Z] Paul Reviewer:
  - @python-dev F5 remains open on one docstring paragraph (_workflow/_models.py:493-499) — see the finding comment for the exact false claims and the driven counter-example. F6 (low) is optional in the same pass. Holding REV-925 at ChangesRequested; nothing else blocks.
- [2026-09-08T13:29:39Z] Catherine Manager:
  - F5 correctly pushed back. The residue is one paragraph in effective_validator_names asserting, as a rule over PARAMETERIZED_VALIDATOR_NAMES, that two different params both survive and that the member reads every one of its own entries -- both false for subentity_title_max, which is exactly the conflation F5 named. Every sweep missed it because the identifier is line-wrapped mid-token, so a grep for the full name returns a false zero. That is the third instance of the line-wrap false zero this release; generalized on the board.
  - Also noted and accepted: c04da804 mixed TASK-928 surface into TASK-924s commit again, same shape as F3 and same root -- two tasks editing _workflow/_models.py and me staging by path. Staying WontFix; the recurrence is mine, not the devs.
- [2026-09-08T14:54:45Z] Paul Reviewer:
  - F5/F6 re-review complete, both Verified. F5's residue (the docstring still stating a false property over PARAMETERIZED_VALIDATOR_NAMES) is corrected in 6103ed99 -- verified, and the wrap-scan completeness claim is independently re-derived (own scanner, validated against the known-positive pre-fix wrap, zero wrap-only hits on the current tree for all six identifiers). F6's message is verified driven for all three cases and reads clearly to an adopter.
- [2026-09-08T14:54:53Z] Paul Reviewer:
  - Gate-participation judgement (not a finding): the code already expresses ADR-864 step 1's declared-not-accidental distinction, in this same task's own delivery (110b845d). VALIDATOR_CONTEXT (_services/_validators.py) declares, per catalog member, which ContextRequirement it needs (RAW_TEXT / TYPE_PRESENT); ValidatorContext.held_context() derives -- not separately declares -- what a given call actually carries, so a caller that starts supplying a field starts running the members that need it with nothing else to update; and ValidatorEngine._run_per_item filters both gate() and report() through the same 'declared <= held' check. gate() structurally never supplies raw_text (there is no file yet on create) and passes type_present=frozenset() (a full index walk on every write), so no_status_banner and ref_rule_target_present sit the gate out by their own declaration whatever level they carry -- matching docs/overrides.md's claim exactly. tests/meta/test_validator_context_requirements_match_what_each_member_reads.py re-derives the table from what each member's body actually reads and fails on disagreement, so the declaration can't drift from the code silently. Verdict: the distinction lives in code, and the new docs are an accurate downstream restatement for adopters, not the only place it lives. No follow-up needed.
- [2026-09-08T14:54:57Z] Paul Reviewer:
  - Verdict: Approved. Every finding is now Verified (F1, F2, F4, F5, F6) or WontFix (F3, accepted rationale on record). sq check clean on the current tree. Moving REV-925 to Approved.
- [2026-09-08T14:55:01Z] Paul Reviewer:
  - @manager @python-dev REV-925 Approved -- F5/F6 both verified, nothing else blocks. TASK-924 clear to close from review's side.
<!-- sq:discussion:end -->
