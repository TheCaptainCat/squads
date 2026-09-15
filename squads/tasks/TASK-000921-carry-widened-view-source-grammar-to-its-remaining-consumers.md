---
id: TASK-921
sequence_id: 921
type: task
title: Carry widened view-source grammar to its remaining consumers
status: Done
parent: FEAT-903
author: tech-lead
assignee: python-dev
priority: urgent
refs:
- ADR-880:implements
- REV-920:addresses
subentities:
- local_id: ST1
  title: 'F1: playbook applicability lets empty-lane through'
  status: Done
- local_id: ST2
  title: 'F2+F3: refuse type-attaching a non-relation view at spec load'
  status: Done
- local_id: ST3
  title: 'F4: role source resolver bypasses the documented degrade seam'
  status: Done
- local_id: ST4
  title: 'F5: populate real children on ref/subtree --json rows'
  status: Done
- local_id: ST5
  title: 'F6+F7: prose defects — false delegation claim and stale --json contract
    description'
  status: Done
- local_id: ST6
  title: 'F8: stop resolving the roster eagerly on every tagged body read'
  status: Done
- local_id: ST7
  title: 'Gates: falsification both directions, narration sweep, sq check'
  status: Done
created_at: '2026-09-04T08:05:11Z'
updated_at: '2026-09-04T08:59:02Z'
---
<!-- sq:body -->
## Scope

REV-920's fix task. The three new `source.kind`s (`role`, `playbook`, `self`) reached
`_SOURCE_APPLICABILITY` correctly and the tag path — placement, read-time expansion, `sq
check`'s file scan — works end to end (verified in the review). What was missed is three
other consumers of the same source grammar, plus one predicate that violates ADR-880's own
emptiness corollary. One coherent surface, one task:

- **F1** — `_playbook_source_applies` (`_views.py`) refuses a declared-but-unlaned type,
  against ADR-880's second amendment ("emptiness is never a failure") and against
  `_resolve_playbook_source`'s own docstring, which already claims the predicate lets the
  empty case through. Two branches (the resolver's `lane=None`, `_playbook_json_payload`'s
  `lane: None` arm) are dead as a result.
- **F2 + F3** — one root, both at the type-attached `items.<type>.views` surface.
  `_check_item_views` (`_workflow/_models.py`) only checks host-applicability for `subentity`,
  so a `role`/`playbook`-sourced view attaches to an incompatible type with a clean spec load
  (F3) and then breaks `show`/`--raw`/`--json` at read time. Separately, `build_item_json`
  calls `resolve_view` unconditionally for every attached view, and `resolve_view` refuses any
  non-relation kind outright regardless of applicability — so even attaching `self` (which is
  applicable to every type) breaks `show --json` for every item of the attaching type (F2).
  Both collapse to the same fix: the type-attachment mechanism only ever had a serializer for
  the three relation kinds (`resolve_view` → `projection_json`), so `_check_item_views` must
  refuse attaching a non-relation-kind view at spec load, unconditionally — a load-time check
  that agrees with what `resolve_view` already does at read time, rather than a load check
  that passes where a read fails. `_check_item_views`'s existing `subentity` axis also
  hand-rolls the same host-constraint question `_subentity_source_applies` (`_views.py`)
  already answers, independently — the REV-912 F2 shape, "two functions answering one
  question." Fix both in the one call site.
- **F4** — `_resolve_role_source` calls `resolve_role_with_base` directly instead of the
  documented seam `resolve_role_for_item` (`_roles/_resolver.py`), so an orphaned role item
  (its backing override deleted) raises `RoleNotFoundError` out of `read_body` — every read
  surface — where `resolve_role_for_item` degrades gracefully to `RoleDef.from_extra_or_item`.
  `sq check` stays silent: the predicate is type-scoped and correctly passes.
- **F5** — a `ref`/`subtree` view's `--json` reports `children: []` for records that
  demonstrably have children, contradicting the shipped, tested, and documented claim (CLI
  help, `build_item_row_json`'s docstring, TASK-919's own acceptance) that the shape matches
  `sq tree --json`'s per-node shape field for field. **Ruled: populate `children`**, not drop
  the fields. `_children_by_parent` (`_views.py`) already does the walk `_resolve_subtree_source`
  uses; reuse it (or the service-layer tree machinery, whichever avoids a second
  implementation) to build each matched record's real subtree recursively, the same shape `sq
  tree --json` returns for that same item. This keeps the contract three places already assert
  rather than retreating from it, and costs the existing two byte-equality tests nothing but a
  grandchild in their fixtures (the review's own cheapest-guard suggestion) — no test redesign.
- **F6 + F7** — prose defects, not code changes. `WorkflowSpec.is_delivered`'s docstring
  claims `_views._is_delivered` delegates to it; `_views._is_delivered`'s own docstring says
  the opposite and explains why (a private module function pyright would flag as dead the
  moment nothing called it). Both halves of `is_delivered`'s claim are false. Fix the one
  sentence: both make the same comparison independently, held together by
  `tests/unit/test_settled_versus_delivered_status.py`. F7 is `_views.py`'s module docstring
  and `projection_json`'s docstring still describing the pre-TASK-919 `--json` contract
  (`--json` callers no longer call `projection_json` for the relation kinds — `_view_json_payload`
  does), `_is_delivered`'s "this task" diff-relative phrase, and
  `tests/service/test_render_resolved_source_or_raise_lets_a_missing_template_error_through_unwrapped.py`'s
  inner test function still named after the pre-rename function. Full list is in REV-920 F7;
  fix each once.
- **F8** — `ItemsMixin.read_body` (`_services/_items.py`) resolves the full roster off disk
  on every tagged body read, for every tag kind, even though only `playbook` ever looks at it.
  Fix: thread a zero-argument `Callable[[], list[RoleView]]` through `expand_view_tags` →
  `resolve_source` → `_resolve_playbook_source` instead of a materialised `list[RoleView]`, so
  only the `playbook` arm forces it. Memoize the callable at the `read_body` call site (a
  `functools.cache`-wrapped closure or an equivalent single-cell cache) so a body carrying more
  than one `playbook` tag pays the roster cost once, not once per tag.

F9, F10, F11 (info) are **not** in this task. F9 (inert field grammar on a non-relation view)
and F11 (`ViewsMixin` repeating the resolve-a-view preamble three times, one of the three
copies being `resolve_view` itself) are resolved by FEAT-904's own scope (deletes the
`fields`/`group_by`/`order_by` grammar and `resolve_view`/`ItemSpec.views` outright) — a
separate fix now would be thrown away within the same release. F10 (`self --json`'s spec
identity reporting file existence rather than merge outcome) is not resolved by FEAT-904's
stated scope but is not load-bearing for any client today (the implementer's own handoff
flagged it as a reasoned-under-pressure shape); noted on FEAT-904 as a design question to
settle whenever `self`'s JSON shape is next touched, rather than a fix here.

## What lands

**F1 — playbook emptiness.** `_playbook_source_applies` becomes constantly-true, the same
shape as `_ref_source_applies`/`_subtree_source_applies`/`_self_source_applies` (full unused
signature, explicit `None`, not a dropped parameter) — drop the `playbook.types.get(...) is
not None` refusal entirely; `lane=None` is a well-formed empty result, not a precondition
failure. The predicate still takes `item_type: str` only, never `item`, so it stays callable
from `sq check`'s pre-frontmatter file scan.

The existing agreement-pinning test
(`tests/unit/test_playbook_source_applicability_agrees_with_item_skill_branch.py`) currently
pins the predicate against `_item_skill_definition_text`'s rich/thin branch on the "does this
type carry a lane" question — that question no longer decides applicability, so the test needs
re-aiming, not deleting: the rich/thin agreement between `_item_skill_definition_text` and
whatever now decides a skill's own lane-presence question is still worth holding: re-point the
test at `laned_types()`/`playbook.types.get()` agreement directly (the two are proven to
disagree on an authors=False lane by TASK-918's own falsification, restated in that test file's
history) rather than the now-constantly-true predicate.

**Success case, not prose:** a declared-but-unlaned type (the existing synthetic-override
fixture: shadow `guide` into a custom type with no `playbook.toml` entry) resolves through
`resolve_view_target` cleanly, `resolve_source` returns `PlaybookSource(lane=None)`, and
`render_source_view` renders the "no lane" template arm — end to end, through the real
`Service` seam (placement, read, `--json`), not asserted only at the predicate/resolver unit
level.

**F2 + F3 — type-attached view consumers.** `_check_item_views` (`_workflow/_models.py`)
gains, at the top of its loop body, a refusal for any `v.source.kind not in
VIEW_BASE_FIELDS_BY_SOURCE` (the same membership test `RELATION_KINDS` in `_views.py` already
is — `_workflow/_models.py` defines `VIEW_BASE_FIELDS_BY_SOURCE` itself, so no import needed):
`items.<type>.views` may only attach a relation-sourced view, for any type, because
`resolve_view`/`build_item_json` has no serializer for anything else and TASK-918 deliberately
made `resolve_view` refuse them. This alone makes both F2's and F3's failure scenarios
unreachable — role/playbook/self can never be type-attached, so `resolve_view` is never called
against one through this path, and the specific "role attached to task" case F3 drove can no
longer load clean.

The existing `subentity` axis stays (relation kinds remain attachable and still need their
host-constraint check), but stop hand-rolling it: extract the "does `item_type`'s own
`subentity_kind` match the projected kind" question onto a `WorkflowSpec`/`ItemSpec` method (or
call `item_subentity_kind` directly, whichever needs the smaller diff) so `_check_item_views`
and `_subentity_source_applies` ask it through the same code, not two independently-worded
implementations that could silently disagree — the same move already made for
settled/delivered in TASK-918.

**Two driven repros to turn green**, both from REV-920's bodies, run against the fix:
`.overrides/workflow.toml` attaching `self_card` (a `self`-sourced view) to `task` now refuses
at spec load (F2's scenario); attaching `role_card` (a `role`-sourced view) to `task` now
refuses at spec load (F3's scenario) — both with a `SquadsError` naming the source kind and the
type, not a bare validation failure.

**F4 — role resolver seam.** `_resolve_role_source` (`_views.py`) becomes a one-line call to
`resolve_role_for_item(item, squad_dir)` (`_roles/_resolver.py`), dropping the direct
`resolve_role_with_base`/`role_base_from_item` call it currently makes. Correct the docstring's
claim accordingly — it currently says this *is* the seam `role_definition_text` calls, which
was true of the happy path and false of the failure path; say plainly that this now calls the
documented seam and inherits its graceful degrade.

`test_a_bundled_role_resolves_to_the_same_definition...` (or whichever pins
`_resolve_role_source(item, dir) == resolve_role_for_item(item, dir)`) now pins two expressions
that are, after this fix, the same call — re-aim it to something that still tests a real
property (e.g. that `_resolve_role_source` genuinely delegates rather than reimplementing, or
fold it into the driven repro below) rather than leaving a tautology in the suite.

**Driven repro to turn green:** an activated project-declared role whose `.overrides/roles/`
file is then deleted, with a placed `role` tag, still reads (`sq role N show`, and the tagged
item's `show`/`--raw`) — degraded to `RoleDef.from_extra_or_item`, not `RoleNotFoundError` —
from REV-920's F4 body.

**F5 — ref/subtree `--json` children.** `_view_json_payload`'s `ref`/`subtree` arm
(`_cli/_workflow_cmd.py`) populates `children` for each matched record by walking its real
descendants — reuse `_children_by_parent`/the existing tree-children resolution rather than a
third implementation of "who are this item's children." No CLI flag exists on `sq workflow
view --json` for closed-item visibility, so the walk includes every descendant unconditionally
(document that choice in the function's docstring rather than leaving it implicit). Deepen
`test_a_ref_sourced_views_json_equals_sq_tree_jsons_own_output` and
`test_a_subtree_sourced_views_json_equals_the_hosts_own_tree_children`'s fixtures with a
grandchild each (the review's own cheapest guard) rather than redesigning either test — the
byte-equality assertion against real `sq tree --json` output stays as-is and now actually holds
at depth.

**F6 + F7 — prose.** One sentence in `WorkflowSpec.is_delivered`'s docstring
(`_workflow/_models.py`): state that `_views._is_delivered` makes the same comparison
independently, name the pinning test. In `_views.py`: rewrite the module docstring's
`--json`/`projection_json` sentence to name `_view_json_payload`
(`_cli/_workflow_cmd.py`) as the actual per-source `--json` dispatch point and `projection_json`
as the one remaining type-attached-views caller's contract, not "the `--json` contract";
rewrite `projection_json`'s own docstring to the same narrower claim; restate `_is_delivered`'s
"this task adds" sentence in the present tense. Rename
`test_render_view_or_raise_lets_a_missing_template_error_through_unwrapped` (the function) to
match its already-renamed module. Apply the stranger test to each rewrite — present-tense fact
only, no diff-relative framing — and grep the exact old wording removed across the touched
files afterward to confirm no sibling copy survives.

**F8 — read_body roster laziness.** `expand_view_tags`'s `roster: list[RoleView]` parameter
becomes `roster: Callable[[], list[RoleView]]`; `resolve_source`'s and
`_resolve_playbook_source`'s `roster` parameters follow the same change. `read_body`
(`_services/_items.py`) passes a memoized zero-arg callable instead of calling
`self.roster_from_db(db)` eagerly; `ViewsMixin.resolve_view`/`resolve_view_source`/`render_view`
(`_services/_views.py`), which also currently call `self.roster_from_db(db)` eagerly before
dispatch, get the same treatment for consistency, even though a single explicit `sq workflow
view` call pays the cost regardless of kind today — do not leave one call site lazy and its
two siblings eager for the same parameter. `ref`/`subtree`/`subentity`/`role`/`self` bodies
read with **zero** `.overrides/roles/*.toml` stat-or-read calls; a `playbook`-tagged body reads
with the same roster cost as today, once per body even with multiple `playbook` tags.

## Project constraints

- Layering unchanged by this task: `_workflow` never imports `_services` or `_views`; `_views.py`
  sits above `_workflow`/`_models`/`_roles`/`_interactions`, below `_services`. The F2/F3 fix
  lives entirely inside `_workflow/_models.py` (no new import) precisely because `_check_item_views`
  already has `VIEW_BASE_FIELDS_BY_SOURCE` in scope; do not import `_views.RELATION_KINDS` from
  `_workflow/_models.py` — that would be the cycle the review's F3 body already named as blocking
  a naive fix.
- `SquadsError` for every user-facing refusal; never a bare exception.
- Time via `clock.now()`/`clock.iso()` if any new code touches a timestamp.
- Escape console/CLI output with `_cli._common.e()`.
- No `from __future__ import annotations`; PEP-695 `type X = ...` for any new alias.
- No sq/ticket IDs in source or test filenames or docstrings — name by behaviour.
- A new or restructured module-level dict/list stays allowlisted in `tests/meta`'s
  mutable-state guard — check the existing `_SOURCE_APPLICABILITY` allowlist entry before
  adding a new one.
- Any multi-exception handler stays parenthesized (`except (A, B):`) with `# fmt: skip`.

## Acceptance — gates (apply to every fix above, not a separate pass)

1. **Emptiness-as-success is a driven test, not prose.** F1's declared-but-unlaned case is
   proven end to end (placement, read, `--json`) through the real `Service` seam, and asserted
   as a passing render/resolve — never merely stated in a docstring or commit message.
2. **F2 and F3's driven repros land as tests and go green.** Both scenarios above (attaching
   `self`, attaching `role`, to `task`) are reproduced as tests against the fixed code and pass
   by refusing at spec load with a named reason — not by a bare validation failure, and not by
   asserting only that `show` no longer crashes without also asserting the load-time refusal
   fired for the right reason.
3. **F4's driven repro lands as a test and goes green.** The orphaned-role-under-a-placed-tag
   scenario reads successfully (degraded `RoleDef`), reproduced against the real `Service`
   seam, not only at the module-function level.
4. **Falsify every new and changed test, both directions reported.** For each predicate/
   resolver/check pair touched by F1–F5 and F8 — restore the refusal or the eager call this
   task removes, watch the newly-relevant test go red, revert, watch it go green, report both
   in the handoff comment. Falsify the mechanism: for F2/F3, remove the load-time refusal *and*
   confirm the read-time refusal alone does not catch it (the state F3 exists to close); for F1,
   remove the constantly-true predicate's replacement and confirm the emptiness test alone
   catches the regression, not merely a crash.
5. **Narration sweep is per-task acceptance, not a later pass — F6/F7 are what this task is
   fixing, not merely running a sweep over.** Apply the stranger test to every docstring/
   comment/error string this task adds or rewrites; then grep the exact old wording removed
   across the whole touched surface, confirming zero remaining copies. Use the validated
   ast+tokenize block scanner already built in the scratchpad during TASK-918/919 (whitespace-
   collapsed, validated against a line-wrapped known positive) if a phrase might wrap across
   lines — build it fresh in this session's own scratchpad if the prior one is gone, and never
   commit it.
6. **Do not write a docstring or comment citing coverage that does not exist.** Verify every
   test-name citation resolves to a real, passing test before writing the sentence that names
   it — this happened twice on TASK-918 and the finishing pass had to catch it both times.
7. **`uv run sq check` clean**, plus `uv run --all-extras pyright && uv run --all-extras ruff
   check . && uv run --all-extras ruff format --check .` clean — `--all-extras` on every one of
   the three, not a bare `uv run`.
8. Do not run the full test suite from a subagent seat; a targeted selection covering every
   touched/new file plus `tests/meta` in full is the dev's own gate. The full suite is the
   tech lead's/manager's authoritative gate at handback.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 921 add-subtask "<title>"`; track with `sq task 921 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — F1: playbook applicability lets empty-lane through

<!-- sq:subtask:ST1:body -->
Drop the lane-presence refusal in _playbook_source_applies (_views.py); declare it constantly-true like ref/subtree/self. Re-aim the existing agreement-pinning test off the now-removed applicability question onto laned_types()/playbook.types.get() agreement directly. Prove the declared-but-unlaned case end to end (placement, read, --json) through the real Service seam as a passing test, not prose. Falsify: restore the refusal, confirm the emptiness test reddens for the right reason.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — F2+F3: refuse type-attaching a non-relation view at spec load

<!-- sq:subtask:ST2:body -->
Widen _check_item_views (_workflow/_models.py): refuse any items.<type>.views entry whose source.kind is not in VIEW_BASE_FIELDS_BY_SOURCE, for any type — resolve_view/build_item_json has no serializer for role/playbook/self and never will until FEAT-904. Collapses both F2 (self/role/playbook attachment breaks show --json for every item of the type) and F3 (role view attached to an incompatible type loads clean, breaks show at read time) at one call site. Also fold the existing subentity host-constraint branch onto the same question _subentity_source_applies (_views.py) already answers, rather than a second hand-rolled implementation. Land both REV-920 driven repros (self_card on task, role_card on task) as tests that assert the load-time refusal fires with a named reason. Falsify: remove the refusal, confirm read-time alone does not catch either scenario.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — F4: role source resolver bypasses the documented degrade seam

<!-- sq:subtask:ST3:body -->
Change _resolve_role_source (_views.py) to call resolve_role_for_item(item, squad_dir) (_roles/_resolver.py) instead of resolve_role_with_base/role_base_from_item directly. Correct the docstrings false happy-path-only claim. Re-aim the existing pin that now compares two calls to the same function into something that still tests a real property. Land REV-920s driven repro (an activated role whose override file is deleted, under a placed role tag, still reads via the real Service seam) as a passing test. Falsify: revert to the direct call, confirm the repro reddens with RoleNotFoundError.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — F5: populate real children on ref/subtree --json rows

<!-- sq:subtask:ST4:body -->
_view_json_payload (_cli/_workflow_cmd.py) currently defaults children to [] for every ref/subtree --json row, contradicting the shipped sq-tree--json-shape claim. Populate each matched records real descendant subtree by reusing _children_by_parent (_views.py) or the existing tree-children resolution -- no third implementation, no CLI filter for closed items (document that as unconditional). Deepen the two existing byte-equality tests with a grandchild fixture each rather than redesigning them. Falsify: force children back to [], confirm the deepened tests redden.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — F6+F7: prose defects — false delegation claim and stale --json contract description

<!-- sq:subtask:ST5:body -->
WorkflowSpec.is_delivered (_workflow/_models.py): fix the one sentence claiming _views._is_delivered delegates to it -- state both compare independently, name the pinning test. _views.py module docstring + projection_json docstring: stop describing projection_json as "the --json contract" -- name _view_json_payload as the real per-source dispatch point, projection_json as the one remaining type-attached-views callers contract. _is_delivered docstring: present-tense, drop "this task adds". Rename the inner test function in tests/service/test_render_resolved_source_or_raise_lets_a_missing_template_error_through_unwrapped.py to match its already-renamed module. Stranger-test each rewrite; grep the exact old wording removed across the touched files afterward, zero remaining copies.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — F8: stop resolving the roster eagerly on every tagged body read

<!-- sq:subtask:ST6:body -->
Change expand_view_tags/resolve_source/_resolve_playbook_source roster parameter from list[RoleView] to Callable[[], list[RoleView]] (_views.py). read_body (_services/_items.py) passes a memoized zero-arg callable instead of calling self.roster_from_db(db) eagerly; apply the same to ViewsMixin.resolve_view/resolve_view_source/render_view (_services/_views.py) for consistency. A body read with a ref/subtree/subentity/role/self tag makes zero .overrides/roles/*.toml reads; a playbook-tagged body with multiple playbook tags pays the roster cost once, not per tag. Falsify: revert to eager, confirm a new test asserting zero role-file reads on a non-playbook tagged body reddens.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Gates: falsification both directions, narration sweep, sq check

<!-- sq:subtask:ST7:body -->
Apply the stranger test to every docstring/comment/error string this task adds or rewrites, then grep the exact old wording removed across the whole touched surface post-rewrite -- use the ast+tokenize block scanner from TASK-918/919 (rebuilt fresh in this sessions scratchpad if the old one is gone), never committed. Falsify every new and changed test, both directions, reported in the handoff comment -- for F2/F3 confirm read-time refusal alone does not catch what the load-time refusal now does. Verify every test-name citation in a docstring/comment resolves to a real passing test before writing it. uv run sq check clean, plus pyright/ruff check/ruff format --all-extras clean, before handoff. Do not run the full suite.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-04T08:47:07Z] Elias Python:
  - Implementation complete, all seven subtasks Done. Gates clean:
    `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .`
    (whole repo, not just touched files) all exit 0; `uv run --all-extras pytest tests/meta` — 279 passed;
    `uv run sq check` — no issues. Did not run the full suite.
    
    Touched: src/squads/_views.py, src/squads/_workflow/_models.py, src/squads/_cli/_workflow_cmd.py,
    src/squads/_services/_items.py, src/squads/_services/_views.py, plus 13 test files (12 modified,
    tests/unit/test_role_source_resolver.py rewritten from an untracked prior-session draft that carried
    tautological pins — reused its scaffolding, replaced the assertions).
    
    **ST1 (F1)** — `_playbook_source_applies` is now constantly-true (dropped the lane-presence refusal),
    matching ref/subtree/self. Re-aimed `test_playbook_source_applicability_agrees_with_item_skill_branch.py`
    off the predicate (now trivially true, nothing to pin) onto `_item_skill_definition_text`'s real branch
    vs the raw `playbook.types.get(type) is not None` expression directly — the existing `give_it_back_a_lane`
    fixture (an authors=False lane) already proves that expression disagrees with `laned_types()`, so I added
    an explicit assertion of that disagreement rather than just relying on it implicitly.
    Driven end-to-end test added in `tests/service/test_role_playbook_self_views_end_to_end.py`
    (`test_a_playbook_sourced_view_on_a_declared_but_unlaned_type_resolves_empty`): shadows `guide`→`doc`
    (no playbook entry), places the tag via `insert_view`, reads via `read_body`, checks `--json` via the
    real `_view_json_payload`, and asserts `sq check` stays silent. Falsified: restored the old refusal,
    the new test reddened with `SquadsError: view 'lane_card' projects a playbook lane, but 'doc' carries
    no playbook entry` out of `insert_view` — confirmed it fails for the right reason, not a fixture bug.
    Restored, green.
    
    **ST2 (F2+F3)** — `_check_item_views` (`_workflow/_models.py`) gained an unconditional refusal for any
    `v.source.kind not in VIEW_BASE_FIELDS_BY_SOURCE` before the existing subentity axis, so `role`/
    `playbook`/`self` can never type-attach. Extracted the subentity host-constraint question into a shared
    `subentity_source_reason(view_name, item_type, kind, items)` function in `_workflow/_models.py` (the
    predicate's own module, since `_workflow` cannot import `_views`) — `_views._subentity_source_applies`
    now imports and calls it instead of hand-rolling its own copy of the same comparison, closing the
    REV-912-shaped "two functions answering one question" duplication the review flagged as a second defect
    at the same call site. Two driven repros landed in `tests/unit/test_view_declaration_referential_checks.py`
    (`test_a_self_sourced_view_attached_to_a_type_is_refused_at_load`,
    `test_a_role_sourced_view_attached_to_a_type_is_refused_at_load`) — both assert `SquadsError` at
    `load_workflow_spec` naming the type, the view, and the source kind. Falsified: removed the new axis,
    both reddened with "DID NOT RAISE" (spec loaded clean, confirming read-time refusal alone — or rather
    its *absence* at load time — does not catch either scenario the way F3 exists to close). Restored, green.
    
    **ST3 (F4)** — `_resolve_role_source` is now a one-line call to `resolve_role_for_item`, dropping the
    direct `resolve_role_with_base`/`role_base_from_item` call. This has a wider ripple than the task body's
    one-line description suggested: the module docstring and two existing tests in
    `test_view_source_applicability_predicate.py` asserted the OLD (correct-at-the-time) claim that
    role's resolver is "the one kind whose resolver may raise." That's no longer true post-fix — the
    resolver never raises now, `resolve_role_for_item` degrades every case. I updated the module docstring,
    moved `_resolve_role_source` into the "no per-kind resolver raises" list in
    `test_no_per_kind_resolver_function_raises`, and rewrote
    `test_the_role_resolver_may_raise_for_an_identity_its_predicate_could_not_decide` into
    `test_an_unresolvable_role_identity_degrades_rather_than_raising` (same fixture, asserts a degraded
    `RoleDef` instead of `pytest.raises`). Re-aimed the tautological pin in `test_role_source_resolver.py`
    onto a delegation spy (`patch.object(views, "resolve_role_for_item", wraps=...)` +
    `spy.assert_called_once_with(item, squad_dir)`) rather than an equality check that would hold for any
    reimplementation returning the same happy-path value. Driven repro in
    `test_role_playbook_self_views_end_to_end.py`
    (`test_an_orphaned_project_role_under_a_placed_tag_still_reads`): a project-declared custom role
    (`.overrides/roles/sre.toml`, no bundled catalog entry), activated, tag placed, reads correctly; delete
    the override file; still reads (degraded), asserted via `read_body` directly. Falsified: reverted to the
    direct `resolve_role_with_base` call, the repro reddened with `RoleNotFoundError: no predefined role
    'sre' and no project override found` raised out of `read_body`. Restored, green.
    
    **ST4 (F5)** — Added `_view_json_child_rows` (`_cli/_workflow_cmd.py`), a recursive builder reusing
    `squads._views.children_by_parent` (renamed from `_children_by_parent` — had to make it public since
    pyright's strict `reportPrivateUsage` is *not* relaxed for `src/`, only for `tests/`; cross-module
    private imports in `src/` are real errors here, not a style nit). Unconditional (no closed-item
    filter, matching "no CLI flag exists" from the ruling) and cycle-guarded the same way
    `_resolve_subtree_source` already is. Deepened both byte-equality tests in
    `tests/cli/test_workflow_views_cli.py` with a real grandchild each, but the naive "just add a task
    under a task" approach doesn't work: `task`'s own `parents = ["feature"]` forbids it, and more
    fundamentally `sq tree --type task` prunes a matched node's own non-matching descendants (keep-set is
    match∪ancestors-of-matches, never descendants), which fights the now-unconditional children population
    regardless of the grandchild's type. Fixed by giving each matched task a `bug` child (parent-unconstrained)
    and dropping the `--type task` CLI filter — for the `ref` test, filtering `tree --json`'s output to
    `type == "task"` in Python instead (since without an explicit root the bare forest also includes every
    other root, e.g. roster items); for the `subtree` test, just dropping `--type` since an explicit root
    already scopes the comparison. Falsified: forced `children` back to `[]` in `_view_json_payload`, both
    deepened tests reddened on `assert any(row["children"] for row in view_payload)` (the vacuousness guard
    fired, not just the final equality). Restored, green.
    
    **ST5 (F6+F7)** — `WorkflowSpec.is_delivered`'s docstring no longer claims `_views._is_delivered`
    delegates to it; states both compare independently, names the pinning test
    (`tests/unit/test_settled_versus_delivered_status.py`, verified it actually holds both functions in
    agreement across every status of every kind before citing it). `_views.py` module docstring and
    `projection_json`'s own docstring now name `_view_json_payload` as the real per-source `--json`
    dispatch point and `projection_json` as the one remaining type-attached-views caller's contract.
    `_is_delivered`'s "this task adds" phrase is now present-tense. Renamed the inner test function in
    `test_render_resolved_source_or_raise_lets_a_missing_template_error_through_unwrapped.py` to match its
    module. Grepped the four exact removed phrases across the whole repo post-rewrite — zero remaining
    copies.
    
    **ST6 (F8)** — Added `type RosterProvider = Callable[[], list[RoleView]]` in `_views.py`;
    `_resolve_playbook_source`/`resolve_source`/`expand_view_tags` all take it instead of a materialised
    list, with `_resolve_playbook_source` the one call site that ever invokes it. `ItemsMixin.read_body`
    passes `functools.cache(lambda: self.roster_from_db(db))`; `ViewsMixin`'s three methods
    (`resolve_view`/`resolve_view_source`/`render_view`) pass a plain `lambda: self.roster_from_db(db)`
    each (no memoization needed there — each calls `resolve_source` at most once per invocation, but they
    get the same laziness treatment for consistency, per the ruling). Two new driven tests in
    `test_role_playbook_self_views_end_to_end.py`: a `self`-tagged body read spied via
    `patch.object(reopened, "roster_from_db", wraps=...)` asserts `spy.assert_not_called()`; a body with
    two `playbook` tags (different types) asserts `spy.assert_called_once()`. Also had to update five other
    existing test files whose direct `resolve_source(...)`/`expand_view_tags(...)`/`_resolve_playbook_source(...)`
    calls passed a bare list — three of those five weren't even caught by pyright (Unknown-type propagation
    from an unannotated test fixture parameter suppressed `reportArgumentType`), so I fixed them by reading
    the call sites, not by trusting the type checker's silence. Falsified: reverted `read_body` to the eager
    non-memoized call, `test_read_body_computes_the_roster_once_for_two_playbook_tags` reddened
    (`spy` called twice, not once). Restored, green.
    
    **ST7 (gates)** — Narration sweep: rebuilt the ast+tokenize block scanner fresh in this session's own
    scratchpad (a prior partial attempt at this same task had already left one there, from before this
    conversation's context — validated it still catches a known positive: a bare and a line-wrapped
    instance of "this task"/"this pass"/"just added", both caught). Ran it against every touched file
    (whole-file scan, so it also surfaced pre-existing, unrelated hits) then cross-referenced against
    `git diff`'s added lines only. Two genuine hits survived the phrase-filter and a full manual read of
    every added docstring/comment as a stranger: `projection_json`'s docstring said "no longer calls this"
    (diff-relative — rewrote to state the current dispatch positively) and the re-aimed
    `test_playbook_source_applicability_...` module docstring narrated the test's own edit history ("used
    to be... used to pin... no longer asks... used to wrap" — rewrote to describe the current predicate's
    design in present tense only). Also caught one non-phrase-list hit on a closer read:
    `_check_item_views`'s new axis said a door "the source-widening grammar reopened" — diff-relative
    (the reader cannot observe a "before" anywhere but git history) — rewrote to state the current
    mechanism. And one in the new roster-laziness test module docstring ("rather than resolving the roster
    eagerly" — the eager path no longer exists to observe) — rewrote to state only the current behaviour.
    Grepped all four exact removed fragments across the whole repo afterward: zero remaining copies. Also
    caught and fixed a genuine coverage-citation error while re-reading `test_role_source_resolver.py`'s own
    docstring: it cited `test_view_source_applicability_predicate.py` "for the one case that genuinely
    can't" resolve, directly contradicting the same sentence's own claim two clauses later that the case
    degrades rather than failing — a leftover from the pre-F4 wording that I hadn't fully re-derived: fixed
    to describe the degrade case consistently at both citation sites, and re-verified both cited tests
    actually pass before leaving the sentence in.
    
    **No ticket IDs anywhere in the added-lines diff** (checked via the same phrase-list pass, extended
    with `f1`..`f8`/`rev-`/`task-`/`adr-880` as literal terms — zero hits in added lines; source. only
    false-positive was "this pr[edicate]" matching the "this pr" phrase substring).
    
    Targeted selection (all green): `test_playbook_source_applicability_agrees_with_item_skill_branch.py`,
    `test_role_playbook_self_views_end_to_end.py`, `test_view_declaration_referential_checks.py`,
    `test_view_source_applicability_predicate.py`, `test_role_source_resolver.py`,
    `test_workflow_views_cli.py`, `test_view_expresses_the_subentity_summary_shape.py`,
    `test_view_projection_engine.py`, `test_has_view_tag_and_expand_view_tags_agree.py`,
    `test_playbook_source_resolver.py`, `test_playbook_view_json_payload_shape.py`,
    `test_render_source_view_template_context.py`, `test_settled_versus_delivered_status.py`,
    `test_render_resolved_source_or_raise_lets_a_missing_template_error_through_unwrapped.py`, plus
    `tests/meta` in full — **404 passed**. Also separately swept six more files that call the touched
    functions but weren't in the primary set (`test_role_body_content_generation.py`,
    `test_milestone_type.py`, `test_role_projects_resolved_name_and_mission_onto_item_fields.py`,
    `test_role_skill_scope_resolution.py`, `test_view_resolve_and_render.py`,
    `test_view_tag_expansion_at_read_time.py`) — **79 passed**.
    
    One thing I'd flag rather than silently work around: F4's fix has a real ripple the task body didn't
    mention — it inverts what `test_view_source_applicability_predicate.py` and its own module docstring
    claimed was true ("role is the one kind whose resolver may raise"). That's now false, and I updated it,
    but it's worth the reviewer double-checking I didn't lose any real coverage in that rewrite — the old
    test asserted a raise fires for a condition the predicate can't decide; the new one asserts the same
    condition degrades instead, which is the correct behaviour per the ruling, but it's a meaningfully
    different assertion than "re-aim the tautological pin" (ST3's own framing) suggested — this one wasn't
    tautological, it was actively asserting the pre-fix behaviour.
    
    Nothing else struck me as wrong in the rulings or acceptance criteria — F1's emptiness fix, F2/F3's one
    load-time axis, F4's degrade-not-raise, F5's real children, and F8's laziness all landed cleanly against
    the existing architecture with no design friction beyond what's noted above (the `children_by_parent`
    privacy fix and the F4 ripple).
    
    @tech-lead for review; full-suite run is yours per the standing instruction.
- [2026-09-04T08:50:06Z] Catherine Manager:
  - Full suite green as the authoritative gate: 4834 passed, 12 skipped, exit 0. Verified the two ruled fixes from source rather than the handback: _playbook_source_applies returns None with the emptiness clause documented (lane=None is the well-formed empty result, not a failure), and _resolve_role_source returns resolve_role_for_item(item, squad_dir). Scanner stayed out of the repo. F1-F8 marked Fixed on REV-920; F9-F11 stay Open and deferred to FEAT-904, which deletes the field grammar and resolve_view outright.
<!-- sq:discussion:end -->
