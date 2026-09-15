---
id: TASK-918
sequence_id: 918
type: task
title: 'View source layer: role, playbook, and self resolvers'
status: Done
parent: FEAT-903
author: tech-lead
assignee: python-dev
refs:
- ADR-880:implements
subentities:
- local_id: ST1
  title: 'resolve_records -> resolve_source: widen the dispatch and spec grammar'
  status: Done
  story: US1
- local_id: ST2
  title: 'role source: resolve the merged RoleDef + applicability'
  status: Done
  story: US2
- local_id: ST3
  title: 'playbook source: lane/roster/spec + applicability + agreement pinning'
  status: Done
  story: US3
- local_id: ST4
  title: 'self source: host item, spec, squad dir + applicability'
  status: Done
  story: US4
- local_id: ST5
  title: 'Template context: unflattened shapes, badges filter, settled/delivered'
  status: Done
  story: US5
- local_id: ST6
  title: 'Gates: falsification, narration sweep, agreement pinning, sq check'
  status: Done
  story: US1
created_at: '2026-09-03T15:05:50Z'
updated_at: '2026-09-04T07:36:10Z'
---
<!-- sq:body -->
## Scope

The engine layer FEAT-903 exists to build: three new `source.kind` resolvers (`role`,
`playbook`, `self`), the applicability predicate each declares beside its resolver, the
`resolve_records` -> `resolve_source` rename that makes the dispatch generic over six kinds
instead of three, and the plumbing that lets a template receive each new kind's own resolved
shape rather than a `Projection`.

ADR-880 (ruled) plus its two amendments are binding. The second amendment's classification
test is what every new predicate is judged by:

> Is this condition decidable from the declared spec plus the host item's **type** alone,
> before any record is read and before any template is rendered?

Decidable -> the kind's applicability predicate, registered in `_SOURCE_APPLICABILITY`
(`_views.py`) beside `_ref_source_applies`/`_subtree_source_applies`/`_subentity_source_applies`,
which this task's three new predicates join. Not decidable -> the resolver raises
`SquadsError`. A resolver may not raise for anything its own predicate could have decided; a
predicate may read the host item's **type** only, never its content; emptiness (zero rows, no
lane, no override field) is never a failure -- only "cannot produce a well-formed result at
all" is.

**Additive to what shipped (FEAT-905's tasks).** The placement verb, the read-time expansion
boundary, `resolve_view_target`, and `sq check`'s file-level scan are untouched by this task --
they already dispatch through `_SOURCE_APPLICABILITY` and `view_tag_name`, and a kind
registered here is picked up by all three for free, with no new call site in any of them.
`ref`/`subtree`/`subentity` themselves -- resolvers, applicability, output shape -- stay
byte-identical (US1). FEAT-904 deletes the projection middle layer
(`Cell`/`ViewRecord`/`ViewGroup`/`project`/`_BASE_RESOLVERS`/`VIEW_BASE_FIELDS_BY_SOURCE`/the
`fields`/`group_by`/`order_by` grammar); none of that layer's code is touched or removed here --
only exempted, at the two points below, from questions it cannot answer for the three new
kinds.

## What lands

**1. `resolve_records` becomes `resolve_source` (US1).** Same dispatch, six kinds instead of
three. `ViewSource.kind` widens from `Literal["ref", "subentity", "subtree"]` to include
`"role"`, `"playbook"`, `"self"`. `ViewSource.name` widens from `str` to `str | None` -- `role`
and `self` take no name; `playbook`'s name is optional (absent = the host's own type). At spec
load, `_check_views`/`_resolve_view_source` (`_workflow/_models.py`) gain one branch per new
kind, validating `name` against the kind's vocabulary exactly as `ref`/`subtree`/`subentity`
are validated today (`playbook`'s name, when given, must resolve against `[items]`; `role` and
`self` must not carry a name at all -- refuse one if given, the same shape of refusal
`_resolve_view_source` already gives an undeclared `ref_kinds`/`items` entry).

Field-list validation (`_check_view_fields`, `VIEW_BASE_FIELDS_BY_SOURCE[kind]`) does not apply
to the three new kinds -- their resolved value is never a list of projectable records (a single
`RoleDef`, a playbook lane, a bare item), so there is nothing for `fields`/`group_by`/`order_by`
to project over. `_check_views` must skip that branch entirely for `role`/`playbook`/`self`
rather than requiring a `fields` list that means nothing for them, or KeyError-ing on
`VIEW_BASE_FIELDS_BY_SOURCE`. This is not a new grammar concept to invent -- it is the minimal
exemption that keeps spec loading correct until FEAT-904 deletes the grammar these three kinds
never participated in.

**2. `role` resolves the merged `RoleDef` (US2).** The resolver is `resolve_role_with_base`
(`_roles/_resolver.py`) with a base built by `role_base_from_item` off the host item -- the same
resolution `role_definition_text` (`_services/_base.py`) already calls for the hardcoded
role-show path. Applicability: the host's type must be the declared role type (`ROSTER_ROLE`,
`_workflow/_models.py`) -- type-decidable, no name to check.

**3. `playbook` resolves a type's lane, the live roster, and the active spec (US3).** Resolves
against the named type (validated at load against `[items]`) or, when `name` is absent, the
host's own type. Applicability: the resolved type must be declared **and carry a lane** --
type-decidable. **Reuse, do not re-derive, the existing "does this type carry a lane"
question**: `laned_types(playbook)` (`_interactions/__init__.py`) already answers it for the
create-lane guard, and `_item_skill_definition_text`'s rich/thin split
(`_services/_base.py:1349`, `pb = self.playbook.types.get(item_type)`) already asks the
identical question to decide whether a per-type skill gets full role sections or the thin
fallback. The new predicate must ask through the same mechanism (`playbook.types.get(type) is
not None`, or `laned_types` -- pick one, but the same one both existing call sites already
use), not a third implementation that can silently disagree with either. Pin this: a test
sweeps every declared type on both the bundled spec and a synthetic override adding/dropping a
lane, and asserts the new predicate and `_item_skill_definition_text`'s own rich/thin branch
agree on every one -- this is this task's instance of "two functions answering the same
question," the exact shape FEAT-905 shipped without (two tag recognisers, no test holding them
in agreement -- REV-912 F2).

**4. `self` resolves the host item, the active spec, and the squad dir (US4).** No resolution
beyond what the caller already has in hand -- the "resolver" is closer to a pass-through than a
lookup. Applicability: constantly true, declared explicitly (mirrors
`_ref_source_applies`/`_subtree_source_applies` -- every parameter present and unused, not
dropped, so the call shape stays uniform across `_SOURCE_APPLICABILITY` and `item_type` stays
structurally checkable on every entry, per the existing test
`tests/unit/test_view_source_applicability_predicate.py`, which this task extends to the three
new entries rather than replaces).

**5. Templates receive each new kind's native shape (US5).** `resolve_source`'s return type is
no longer uniformly `list[_RawRecord]` -- `role` returns one `RoleDef`, `playbook` returns the
lane plus the live roster plus the spec, `self` returns the host item plus the spec plus the
squad dir. `project()`/`Projection` (`_views.py`) apply only to `ref`/`subtree`/`subentity`,
exactly as before -- **do not force the three new kinds through it**, and do not invent a
`Cell`/`ViewRecord` wrapper for them; that is the exact flattening ADR-880 rules against. The
render path (`ViewsMixin.resolve_view`/`render_view` in `_services/_views.py`, `render_view` in
`_views.py`, `templates/views/<name>.md.j2`'s Jinja context) branches on `source.kind`: the
three relation kinds keep today's `project()` -> `Projection` -> template path unchanged (US1's
byte-identical promise); the three new kinds skip `project()` entirely and the template
receives the resolved object directly, plus `item=` (the host item) and `spec=` (the active
spec) always available -- `self` additionally gets `squad_dir=`. No test may assert that a
`Cell`, `_RawRecord`, or `ViewRecord` is constructed anywhere on the new-kind path.

`_badges.py` becomes reachable from a template: register one of its existing functions
(`_badges.py` already has `status_badge`/`badge_render`/`resolve_collection`/`field_label` --
reuse, do not reimplement badge resolution in Jinja) as a filter in `_rendering/_engine.py`
beside `slugify`/`open_marker`/`close_marker`/`idnum`, so a template can write `{{ r.status |
badge }}` instead of hand-writing emoji.

The settled-versus-delivered distinction moves onto `WorkflowSpec`, beside
`first_settled_status` (`_workflow/_models.py`) -- a method taking a kind and a status,
answering whether that status is the kind's own delivery target, generalizing `_is_delivered`
(`_views.py`)'s existing `rec.status == _delivery_target(rec.kind, spec)` logic off a resolved
record to a bare (kind, status) pair a template can call without a `_RawRecord` to hand it.
`_views.py`'s own `_delivery_target`/`_is_delivered` may delegate to the new method rather than
duplicate it -- they still back the untouched `ref`/`subtree`/`subentity` projection path, so
they are not deleted here.

## Acceptance

**US1 -- ref/subtree/subentity survive unchanged under `resolve_source`.**
- The rename touches the dispatch's name and the set of kinds it recognizes only; ref
  inversion, the subtree walk, and the sub-entity collection read are byte-identical in output
  to today (same test corpus, same assertions, only the call renamed).
- Every existing caller of `resolve_records` (the service mixin, the CLI `--json` path, any
  test) is updated to call `resolve_source`; nothing still calls the old name.

**US2 -- `role` resolves the merged `RoleDef`.**
- `source.kind = "role"` resolves to the same object `role_definition_text` already passes
  into `agents/role.md.j2` today, for a bundled role, a developer role, and a role with an
  `.overrides/roles/<slug>.toml` override -- three cases, three tests.
- No name is required; a declared `name` on a `role` source is refused at spec load.
- Applicability: a `role`-sourced view resolved against a non-`role`-typed host is refused by
  the predicate; against a `role`-typed host it is not.

**US3 -- `playbook` resolves the type's lane, roster, and spec.**
- `source.kind = "playbook"` with no name resolves against the host's own type; with a name,
  against `[items]`'s declared entry (refused at load if undeclared).
- The resolved value carries the type's playbook lane (or its absence, for a declared type
  with no lane -- see the emptiness clause below), the live roster, and the active spec -- not
  pre-computed strings.
- Applicability predicate agreement test (above) passes: the new predicate and
  `_item_skill_definition_text`'s rich/thin branch never disagree, over the bundled spec and at
  least one synthetic override that adds a lane to an unlaned type and drops one from a laned
  type.

**US4 -- `self` resolves the host item, spec, and squad dir.**
- `source.kind = "self"` requires no name (refused at load if one is given).
- Resolves to the host item, the active spec, and the squad dir -- verified by identity/equality
  against what the caller already holds, not a re-fetch.

**US5 -- templates receive each source's native shape, unflattened.**
- No `Cell`/`_RawRecord`/`ViewRecord` is constructed on the `role`/`playbook`/`self` path,
  anywhere -- grep the new code for those three names after writing it; zero hits outside the
  untouched `ref`/`subtree`/`subentity` path.
- `_badges.py` is registered as a Jinja filter reachable from a template as `| badge` (or the
  chosen name), proven by a throwaway test template that calls it.
- `WorkflowSpec` gains the settled/delivered method beside `first_settled_status`, callable with
  a bare (kind, status) pair, with a test proving it agrees with `_views.py`'s existing
  `_is_delivered` for every status of every declared kind on the bundled spec (another instance
  of the agreement-pinning requirement below).

**Emptiness, tested as success per new kind, not asserted in prose:**
- `role` on a `role`-typed host whose only identity is the catalog default (no override, no
  item-set fields) still resolves -- "nothing customised" is not "cannot resolve."
- `playbook` against a declared type with no lane resolves to that absence (empty lane, not a
  raise) -- a type genuinely in `[items]` but outside every guide's lane domain is a real,
  supported case, not a defect.
- `self` on a freshly-created item with an empty body resolves -- an empty body is not an
  absent item.

## Project constraints

- Layering: `_workflow` never imports up into `_services`; `_models` has no internal deps;
  `_views.py` sits above `_workflow`/`_models`/`_roles`/`_interactions` and below `_services`
  (a service may call into it, never the reverse -- see `_children_by_parent`'s docstring for
  the existing statement of this edge).
- The applicability predicate stays callable from `sq check`'s file-level scan
  (`_services/_maintenance.py`), which runs *before* `read_frontmatter` and binds the host type
  from the file path alone -- do not give any new predicate a signature that needs a resolved
  `Item`.
- `SquadsError` for every user-facing refusal (a bad name at spec load, an inapplicable
  source at the direct `sq workflow view` path); never a bare exception.
- Time via `clock.now()`/`clock.iso()` if any new code touches a timestamp.
- Escape console/CLI output with `_cli._common.e()`.
- No `from __future__ import annotations`; PEP-695 `type X = ...` for any new type alias (see
  `_SourceApplicability`'s existing `type` alias in `_views.py` for the pattern to match).
- No sq/ticket IDs in source or test filenames -- name tests by behaviour.
- A new module-level dict/list (e.g. an extended `_SOURCE_APPLICABILITY`, if restructured)
  stays allowlisted in `tests/meta`'s mutable-state guard as a CODE constant -- check whether
  the existing allowlist entry already covers it before adding a new one.
- Any multi-exception handler stays parenthesized (`except (A, B):`) with `# fmt: skip`.

## Acceptance -- gates (apply to every story above, not a separate pass)

1. **Narration sweep is part of this task's acceptance, not a later pass.** Apply the stranger
   test -- read as someone who never saw the diff and cannot see repo history; if a sentence is
   false, stale, or meaningless for that reader, or names nothing checkable, it is narration --
   sentence by sentence to every docstring/comment/error string this task adds. Then, after any
   rewrite, grep a distinctive fragment of the OLD wording across this feature's whole added-
   prose surface -- not before the rewrite over a guessed vocabulary. A line-oriented grep
   misses a phrase split by a wrap; build a throwaway ast+tokenize block scan with whitespace
   collapsed in the scratchpad if a fragment might wrap, and never commit that script.
2. **Falsify every new test.** For each test this task adds -- the three resolvers, the three
   applicability predicates, the agreement-pinning tests, the emptiness cases -- break the
   behaviour it covers, watch the test go red, restore it, watch it go green, and report both
   directions in the handoff comment. Falsify the mechanism: for a predicate/resolver pair,
   remove the predicate's refusal *and* the resolver's own defensive check together, so the
   test is proven to catch wrong output, not merely a missing raise.
3. **Pin agreement between functions answering the same question.** The playbook-lane
   agreement test above is this task's required instance; if writing the other two resolvers
   surfaces a second pair of functions answering the same question, pin that one too rather
   than leaving it implicit.
4. **`uv run sq check` clean** before handoff, and `uv run --all-extras pyright && uv run
   --all-extras ruff check . && uv run --all-extras ruff format --check .` clean --
   `--all-extras` on every one of the three, not a bare `uv run`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 918 add-subtask "<title>"`; track with `sq task 918 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — resolve_records -> resolve_source: widen the dispatch and spec grammar

<!-- sq:subtask:ST1:body -->
Rename resolve_records to resolve_source; widen ViewSource.kind to include role/playbook/self and ViewSource.name to str | None; add per-kind name validation in _check_views/_resolve_view_source; exempt the three new kinds from _check_view_fields/VIEW_BASE_FIELDS_BY_SOURCE (they have no field grammar to project over). See the task body's 'What lands' item 1 and US1 acceptance.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — role source: resolve the merged RoleDef + applicability

<!-- sq:subtask:ST2:body -->
role resolver: dispatch to resolve_role_with_base + role_base_from_item (reuse role_definition_text's own resolution, do not re-derive). Applicability: item_type == ROSTER_ROLE, type-decidable, no name accepted. Cover a bundled role, a developer role, and an overridden role. See 'What lands' item 2 and US2 acceptance.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — playbook source: lane/roster/spec + applicability + agreement pinning

<!-- sq:subtask:ST3:body -->
playbook resolver: resolve the named type (validated against [items] at load) or the host's own type when name is absent, to its playbook lane + live roster + active spec. Applicability must reuse the SAME 'does this type carry a lane' question as laned_types()/_item_skill_definition_text's rich-thin branch (self.playbook.types.get(item_type) is not None) -- not a third implementation. Required agreement-pinning test: the new predicate and _item_skill_definition_text's rich/thin branch must agree over every declared type, bundled spec plus a synthetic override adding/dropping a lane. See 'What lands' item 3 and US3 acceptance.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — self source: host item, spec, squad dir + applicability

<!-- sq:subtask:ST4:body -->
self resolver: pass-through to the host item + active spec + squad dir already in hand. Applicability constantly true, declared explicitly (same shape as _ref_source_applies/_subtree_source_applies -- full unused signature, not a shortcut). Extend tests/unit/test_view_source_applicability_predicate.py's structural check to the three new entries. See 'What lands' item 4 and US4 acceptance.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Template context: unflattened shapes, badges filter, settled/delivered

<!-- sq:subtask:ST5:body -->
resolve_view/render_view (_services/_views.py, _views.py) branch on source.kind: ref/subtree/subentity keep today's project()->Projection path unchanged; role/playbook/self skip project() and hand the template their resolved object directly plus item= and spec= (self also squad_dir=). No Cell/_RawRecord/ViewRecord on the new-kind path -- grep for zero hits outside the untouched path. Register a _badges.py function as a Jinja filter beside slugify/open_marker/idnum. Add WorkflowSpec's settled/delivered method beside first_settled_status, taking a bare (kind, status) pair; pin its agreement against _views.py's existing _is_delivered over every status of every declared kind. See 'What lands' item 5 and US5 acceptance.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Gates: falsification, narration sweep, agreement pinning, sq check

<!-- sq:subtask:ST6:body -->
Apply the stranger test to every docstring/comment/error string this task adds, then grep any old wording removed across the feature's added-prose surface post-rewrite. Falsify every new test (break, red, restore, green, report both directions in the handoff comment) -- falsify the mechanism, not just the exception, for each predicate/resolver pair. Confirm the playbook agreement-pinning test (ST3) landed. uv run sq check clean, plus pyright/ruff check/ruff format --all-extras clean, before handoff.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-04T06:49:13Z] Elias Python:
  - Reconstructed and finished this task; the previous session's implementation (resolve_source rename, three new resolvers, six-entry _SOURCE_APPLICABILITY) was sound and is preserved unchanged in its logic.
    
    **Two gate fixes**
    1. tests/meta ticket-ID gate: two "US2" references in tests/unit/test_role_source_resolver.py's docstrings (module + one test), rewritten to describe behaviour instead of citing the story.
    2. ruff format: tests/unit/test_view_declaration_referential_checks.py had one over-long line from a previous edit; reformatted.
    
    **Subtasks ST2-ST5 (were InProgress) — verified against their own acceptance, gaps closed, now Done**
    Each had its own resolver + applicability predicate landed, but several concrete acceptance items were missing test coverage (only asserted in docstrings, not proven):
    - US2 (role): coverage was actually complete (bundled/dev/overridden role, emptiness case) — marked Done as-is.
    - US3 (playbook): the required agreement-pinning test against `_item_skill_definition_text`'s rich/thin branch (_services/_base.py:1349) did not exist — the predicate's own docstring cited a test file (`test_playbook_source_applicability_agrees_with_item_skill_branch.py`) that was never written. Added it: sweeps every declared type on the bundled spec, plus a synthetic override (shadow `guide`->custom type `doc`, with/without a playbook.toml entry) covering both "gains a lane" and "loses a lane". Also added a dedicated resolver test (named type, absent-name-resolves-host's-own-type, emptiness/no-raise).
    - US4 (self): no resolver test existed at all (only the applicability predicate was covered). Added identity + empty-body-still-resolves tests.
    - US5 (template context / badges / settled-delivered): `WorkflowSpec.is_delivered`'s own docstring also cited a nonexistent test (`test_settled_versus_delivered_status.py`) — added it, sweeping every status of every declared kind (item types + sub-entity kinds) against `_views._is_delivered`. Added: a real-template proof the `badge` Jinja filter is registered and reachable; a structural test that no Cell/_RawRecord/ViewRecord is ever constructed on the role/playbook/self path (ast-parsed function bodies, with a control proving the scan isn't vacuous); a template-context test proving `render_source_view` hands a template `source=`/`item=`/`spec=` always and `squad_dir=` only for `self`; and a service-level end-to-end suite (placement, read-time tag expansion, render_view, and resolve_view's clean --json refusal) for all three new kinds through the real Service seams, not just the module-level functions.
    
    **Falsification — every new test, both directions (break/red/restore/green)**
    Mechanism-level (predicate/resolver), not just presence-of-a-raise:
    - `_role_source_applies` forced to always apply -> red in test_a_role_source_applies_only_to_the_role_type; restored, green.
    - `_playbook_source_applies` forced to always apply -> red in the new agreement-pinning test's "unlaned" case (bundled sweep alone did NOT catch it, since every bundled type is laned — only the synthetic-override sweep did). Restored, green.
    - `_playbook_source_applies` swapped to the narrower `laned_types()` question (the exact "second implementation that could silently disagree" the docstring warns about) -> red in the "laned" case (doc's playbook entry has authors=False, so laned_types() excludes it while playbook.types.get() includes it). Restored, green. This is the concrete instance of REV-912 F2's failure shape the task asked to guard against.
    - `_self_source_applies` forced to always refuse -> red in both the dedicated predicate test and the new end-to-end self-view test. Restored, green.
    - `_resolve_role_source` broken to drop squad_dir at the resolve_role_with_base call -> red in the overridden-role test. Restored, green.
    - `_resolve_playbook_source` broken to ignore an explicit name -> red; separately, made it raise on an unlaned type instead of returning lane=None -> red in both the new resolver test AND the existing structural "no per-kind resolver raises" test. Restored, green both times.
    - `_resolve_self_source` broken to return a copy instead of the same object -> red in both self-resolver tests (identity check). Restored, green.
    - `render_source_view`'s squad_dir gating flipped to the wrong kind -> red in both new context tests (role wrongly got it, self wrongly didn't). Restored, green.
    - `render_resolved_source`'s branch dispatch broken to route "self" through project()/render_view -> red in the end-to-end self-view test (KeyError from VIEW_BASE_FIELDS_BY_SOURCE); the structural "no middle layer name" test did NOT catch this (it checks identifiers, not routing), which is exactly why the end-to-end test earns its place. Restored, green.
    - `env.filters["badge"]` registration commented out -> red in both badge-filter tests. Restored, green.
    - `WorkflowSpec.is_delivered` swapped to "settled" instead of "delivered" -> red in all three settled/delivered tests. Restored, green.
    - `_check_views`' field-grammar exemption for role/playbook/self removed -> red in 5 of the referential-check tests (KeyError->validation error). Restored, green.
    No FALSIFICATION-PROBE markers remain in the tree (grepped clean).
    
    **Narration sweep**
    Built a throwaway ast+tokenize scanner in the scratchpad (never committed) that pulls every docstring and `#` comment via ast/tokenize, collapses whitespace, and greps a phrase list — validated against a deliberately line-wrapped known positive first (a plain line grep missed it, the scanner caught it), and against a second known positive to validate the git-diff added-line filter (confirmed it both catches a newly-inserted narration line and excludes pre-existing file content the whole-file scan would have false-positived on). Ran it restricted to this task's added lines across all touched/new files. Found and fixed two real hits, both temporal diff-relative framing invisible to a stranger:
    - _views.py: "unchanged from before this task" -> restated as the present-tense fact only.
    - _views.py: "exactly as before this widening" -> same fix.
    - tests/unit/test_playbook_source_applicability_agrees_with_item_skill_branch.py (my own new file): "the task's acceptance names" -> dropped, kept the checkable claim.
    Grepped each old fragment across the whole src+tests tree after rewriting; zero remaining copies in every case. Remaining scanner hits (2x "this pr" matching inside "this predicate") are confirmed false positives on inspection.
    
    **Gates**
    `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .` — all clean.
    Targeted selection (22 view/playbook-related unit+service files, 21 of them touched/new, plus the two pre-existing files whose behaviour these changes flow through) + `tests/meta` in full: 526 passed, 0 failed.
    `uv run sq check`: clean.
    Did not run the full suite (per instructions) — that's the authoritative gate on your end.
    
    **Unresolved / worth a look**
    - `--json` for role/playbook/self sources is deliberately out of scope (per-source --json is named as separate later work in the ADR and the task body); `resolve_view` refuses cleanly for those three kinds today, proven by test.
    - Nothing else outstanding that I'm aware of; TASK-919 (per-source --json) is next and was left untouched.
- [2026-09-04T06:51:13Z] Catherine Manager:
  - Full suite green as the authoritative gate: 4818 passed, 12 skipped, exit 0. Two gate failures I found before dispatching the finishing pass are fixed and verified: the US2 story references in test_role_source_resolver.py (grep validated against a known positive) and the ruff format failure. Verified independently that the scanner stayed out of the repo and that all four test files the docstrings cited now actually exist.
  - Worth recording as the reusable lesson: the interrupted session left two docstrings citing test files that were never written. Same class as a false (read) label -- prose asserting verification that was never performed. The finishing pass found them by checking the citations rather than the prose. Also note the previous session passed pyright, ruff check and 4794 tests while carrying a real tests/meta violation, because its targeted selection did not include tests/meta. The main loop owning the full suite is what caught it.
<!-- sq:discussion:end -->
