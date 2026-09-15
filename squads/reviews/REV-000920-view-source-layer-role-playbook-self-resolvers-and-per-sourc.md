---
id: REV-920
sequence_id: 920
type: review
title: 'View source layer: role/playbook/self resolvers and per-source --json'
status: Approved
author: reviewer
refs:
- FEAT-903:addresses
- ADR-880
subentities:
- local_id: F1
  title: playbook applicability refuses the well-formed empty lane case
  status: Fixed
  severity: high
- local_id: F2
  title: Attaching a role/playbook/self view to a type breaks show --json
  status: Fixed
  severity: high
- local_id: F3
  title: Attached-view applicability is still only checked for subentity
  status: Fixed
  severity: high
- local_id: F4
  title: The role resolver bypasses the degrade seam it claims to reuse
  status: Fixed
  severity: high
- local_id: F5
  title: 'A ref/subtree view --json claims children: [] for records that have children'
  status: Fixed
  severity: medium
- local_id: F6
  title: WorkflowSpec.is_delivered documents a delegation that does not exist
  status: Fixed
  severity: low
- local_id: F7
  title: Stale prose describing the pre-per-source --json contract
  status: Fixed
  severity: low
- local_id: F8
  title: read_body resolves the whole roster off disk for every tagged body read
  status: Fixed
  severity: low
- local_id: F9
  title: Field grammar on a non-relation view is silently accepted and inert
  status: Open
  severity: info
- local_id: F10
  title: self --json spec identity reports file existence, not what resolved the view
  status: Open
  severity: info
- local_id: F11
  title: ViewsMixin repeats the resolve-a-view block three times
  status: Open
  severity: info
created_at: '2026-09-04T07:52:32Z'
updated_at: '2026-09-04T08:58:06Z'
---
<!-- sq:body -->
## Scope

One batch review across both of FEAT-903's tasks, read as a single change: `git diff
64fe1cb6..HEAD -- src/ tests/` (2040 added lines across 12 source and 19 test files).
TASK-918 widened `resolve_source`'s dispatch to six kinds and added the three new
resolvers plus their applicability predicates; TASK-919 rewired `sq workflow view --json`
onto per-source shapes and moved three role helpers from `_cli/_role.py` into
`_cli/_common.py`.

Every claim below is labelled **read** (traced in source), **driven** (I executed it and
report the observed behaviour) or **inferred**. Probes ran in throwaway `tmp_path` squads
through the real fixtures and were deleted; mutation probes were reverted with `git
checkout -- src/` after each run and the tree confirmed clean.

## What was verified clean

- **The predicate corollary "no predicate reads the host item's content"** holds, and is
  enforced structurally rather than by inspection: every entry in `_SOURCE_APPLICABILITY`
  takes `item_type: str` and no parameter is annotated `Item`, asserted by
  `test_every_applicability_predicate_is_type_scoped_not_item_scoped`. **read + driven**
  (breaking `_self_source_applies` reddens it).
- **`subtree` emptiness was not implemented as a reachability check.**
  `_subtree_source_applies` is explicitly constantly-true, tested against undeclared and
  empty type strings. **read**
- **The three quiet consumers all reach the new kinds for free.** A view whose declared
  kind lapses under an already-placed tag leaves the read working (tag stays literal) and
  `sq check` reports it error-level with the composed reason. **driven**
- **The old projection path coexists intact.** `resolve_view` + `projection_json` have
  exactly one live caller left (`build_item_json`'s type-attached `views` key,
  `_cli/_common.py:1054-1057`); nothing is half-deleted. **read**
- **Agreement-pinning is real.** Swapping `_playbook_source_applies` to `laned_types()`
  reddens `test_predicate_agrees_with_the_real_branch_when_a_renamed_types_lane_lapses_or_returns[laned]`;
  forcing the predicate always-true reddens the `[unlaned]` case. **driven**
- **Layering, exceptions, aliases, ticket IDs.** No `_workflow`/`_models` import into
  `_services`/`_views`; `_views.py` never imports `_cli`/`_services`; both new aliases are
  PEP-695 `type X = ...`; every refusal is `SquadsError` or a subclass; zero ticket IDs in
  source, test filenames or docstrings (grep validated against a known positive first).
  **read + driven**
- **Narration.** One hit across the whole added-prose surface (recorded in F7). The sweep
  held.

## The `_cli/_role.py` -> `_cli/_common.py` move, and the shared builders

**Layering: correct.** `_cli/_common.py` gained imports of `_interactions`,
`_roles._resolver` and `RoleNotFoundError` — all strictly downward. Nothing in `_services`
or `_views.py` reaches up into `_cli`; the role-payload reuse stayed inside `_cli` as the
task required. The import-graph meta guard passes.

**Behaviour: no loss found, with one exception (F5).** `build_item_row_json`'s fields map
1:1 onto what `tree()`'s `node()` computed inline, in the same key order.
`badge_value("priority")` *is* `Item.priority` and `badge_value("severity")` *is*
`SubEntity.severity` — both are real attributes, so `Item.badge_value`/`SubEntity
.badge_value` return the identical value the old inline dicts read directly. **read**
`roster_from_db` is filter-and-sort-identical to the path it replaced: `ItemFilter` with
only `item_type` set reduces to `it.type == ROSTER_ROLE`, and both sort on
`number_for_id`. **read** Mutating each shared-builder field in turn reddens the tree and
sub-entity goldens plus `test_item_json_badges_map.py` (all fields covered). **driven**

**Placement: acceptable but drifting.** `role_base_for_show`, `dev_preview_full_name` and
`build_role_json_payload` are role-specific and now sit in the module CLAUDE.md describes
as "shared console/error decorator/parsers", purely because pyright's `reportPrivateUsage`
blocks a cross-module private import. The two row builders belong there (it already holds
`build_item_json`/`build_subentity_json`); the three role helpers would sit better in their
own `_cli` module, or public in `_role.py`. Not a defect — a note for whoever touches this
next.

## Falsification spot-checks

Each mutation was applied to shipped source, run against a 15-file targeted selection
(122 tests, green at baseline), then reverted.

| Mutation | Result |
| --- | --- |
| `_role_source_applies` always applies | red: `test_a_role_source_applies_only_to_the_role_type` |
| `_playbook_source_applies` always applies | red: agreement-pinning `[unlaned]` |
| `_playbook_source_applies` swapped to `laned_types()` | red: agreement-pinning `[laned]` |
| `_self_source_applies` always refuses | red: 3 tests (predicate, end-to-end, CLI `--json`) |
| `build_item_row_json` drops `anchor` | red: 3 tests (tree golden x2, invented-root wire test) |
| `build_subentity_row_json` drops `story` | red: 3 golden shapes (stories/subtasks/findings) |
| `build_item_row_json` blanks priority/assignee/blocked/badges | red: 5 tests |

Every new applicability predicate is genuinely tested — none survives its own removal.
Emptiness-as-success holds for `ref` and `subentity` (`--json` returns `[]`, exit 0,
proven by tests that redden when the branch is made to raise) and for `role`/`self`
(catalog-default-only role, empty body). It does **not** hold for `playbook` — see F1.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 920 add-finding "…" --severity medium`; track with `sq review 920 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — playbook applicability refuses the well-formed empty lane case

<!-- sq:finding:F1:body -->
**Claim: driven.**

ADR-880's second amendment §2: "**Emptiness is never a failure.** A precondition covers only
conditions under which the resolver cannot produce a well-formed result at all, never
conditions under which it produces an empty one." TASK-918's own acceptance repeats it:
"`playbook` against a declared type with no lane resolves to that absence (empty lane, not a
raise) — a type genuinely in `[items]` but outside every guide's lane domain is a real,
supported case, not a defect."

`_playbook_source_applies` (`src/squads/_views.py`) refuses exactly that case:

```python
    target_type = view.source.name or item_type
    if playbook.types.get(target_type) is not None:
        return None
    return (
        f"view {view_name!r} projects a playbook lane, but {target_type!r} carries no "
        "playbook entry"
    )
```

while `_resolve_playbook_source` returns a fully-formed value for it — and its own docstring
plus `PlaybookSource`'s say so: "`lane` is `None` for a type that is declared but carries no
playbook entry at all ... a well-formed, empty result, not a failure — see
`_playbook_source_applies`". The referenced predicate does the opposite of what the sentence
cites it for.

**Failure scenario (driven).** In a tmp squad, `.overrides/workflow.toml` shadows the bundled
`guide` type into a custom type `doc` (the same override this feature's own agreement-pinning
test uses) and declares `[views.lane_card] source = { kind = "playbook", name = "doc" }` with a
template in place. `doc` is genuinely declared (`"doc" in spec.items` -> True) and genuinely
unlaned (`playbook.types.get("doc") is not None` -> False). Observed:

```
insert_view  REFUSED: view 'lane_card' projects a playbook lane, but 'doc' carries no playbook entry
render_view  REFUSED: view 'lane_card' projects a playbook lane, but 'doc' carries no playbook entry
resolver would have returned: PlaybookSource(item_type='doc', lane=None)
```

So: placement refuses, and for a tag already placed when the lane lapses, expansion leaves the
tag literal and `sq check` reports an **error**. Per the ruling the document should render an
empty lane and the check should stay silent.

**Two dead branches are the proof.** `_resolve_playbook_source`'s `lane=None` result and
`_playbook_json_payload`'s entire `lane: None` arm are unreachable through every gated caller.
TASK-919's own handoff states this: "the playbook applicability predicate already refuses an
unlaned type before resolve_source ever returns one ... so the CLI path can't reach
PlaybookSource(lane=None); the builder's handling of it is real and tested, just not reachable
end-to-end today." A branch that cannot be reached is not "tested" — it is dead code plus a
test that pins dead code.

**Note on provenance, not blame.** TASK-918's body is self-contradictory here: item 3 says the
predicate must require the type to "carry a lane", while the emptiness clause two paragraphs
later says the same condition must resolve empty. The implementation satisfied the first. ADR-880
is the binding authority and rules the other way, so the predicate is what should change: drop
the lane check (declare `playbook` constantly-true, like `ref`/`subtree`/`self`) and let
`lane=None` flow to the template. The agreement-pinning test against
`_item_skill_definition_text` would then be pinning a question the predicate no longer asks, so
it needs re-aiming rather than deleting — the rich/thin agreement is still worth holding, just
not through this predicate.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-09-04T08:55:42Z] Paul Reviewer:
  - Verified fixed at `6ba3072d` — **driven**. `_playbook_source_applies` is now constantly true
    (`del ...; return None`) with the emptiness clause in its docstring, and
    `_resolve_playbook_source`'s `lane=None` result is reachable end to end:
    `test_a_playbook_sourced_view_on_a_declared_but_unlaned_type_resolves_empty` places a tag on a
    declared-but-unlaned `doc`, reads it back as the template's "No lane." branch, gets
    `lane: None` from `--json`, and asserts `sq check` stays silent about it. Both previously-dead
    branches are now live.
    
    **The load-bearing half of the fix holds — driven, verified independently of the tests.**
    `_check_views` calls `_resolve_view_source` unconditionally, above its field-check branch, so the
    amendment's "declared" requirement survives the predicate going constantly-true:
    
    ```
    [views.lane_card] source = { kind = "playbook", name = "not_a_type" }
      -> Invalid workflow spec: view 'lane_card': source names item type 'not_a_type',
         not declared in [items]
    [views.lane_card] source = { kind = "playbook", name = "task" }        -> loads
    [views.c] source = { kind = "role"|"self", name = "task" }
      -> Invalid workflow spec: view 'c': a 'role' source takes no name (got 'task')
    ```
    
    The one condition that cannot be checked at load is a name-less `playbook` source whose *host*
    type is undeclared (a dropped or renamed type under an existing item). That now yields
    `lane=None` rather than a refusal — which is the correct answer under the emptiness clause, not
    a gap.
    
    **Falsification: driven.** Restoring the old lane-requiring refusal in the predicate reddens
    `test_a_playbook_sourced_view_on_a_declared_but_unlaned_type_resolves_empty` and nothing else —
    the guard is genuinely testing the behaviour, not passing incidentally.
    
    One consequence worth naming rather than reopening: the playbook agreement-pinning test against
    `_item_skill_definition_text` is now pinning a question the predicate no longer asks. It was
    re-aimed rather than deleted (it still sweeps every declared type on the bundled spec and on the
    synthetic add/drop override), so the rich/thin agreement is still held — just no longer through
    this predicate. That is the right disposition.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Attaching a role/playbook/self view to a type breaks show --json

<!-- sq:finding:F2:body -->
**Claim: driven.**

`build_item_json` (`src/squads/_cli/_common.py:1054-1057`) resolves every view a type attaches:

```python
    attached = _attached_views(it.type, spec)
    if attached:
        payload["views"] = {
            name: views.projection_json(await svc.resolve_view(name, it.id)) for name in attached
        }
```

TASK-918 made `ViewsMixin.resolve_view` raise for a non-relation kind:

```python
        if view.source.kind not in views.RELATION_KINDS:
            raise SquadsError(
                f"view {view_name!r} is a {view.source.kind!r} source; it has no projectable "
                "record list for --json yet — render it instead ..."
            )
```

That refusal is correct for `sq workflow view --json`'s old call site (which TASK-919 rewired
away from it), and it is tested as intended behaviour in
`tests/service/test_role_playbook_self_views_end_to_end.py`. But nothing was done for the
*other* caller, and `_check_item_views` (`src/squads/_workflow/_models.py`) does not refuse the
attachment: its only source-kind axis covers `subentity`.

**Failure scenario (driven).** In a tmp squad, `.overrides/workflow.toml`:

```
[views.self_card]
source = { kind = "self" }
[items.task]
views = ["self_card"]
```

with a template at `.overrides/templates/views/self_card.md.j2`. The spec loads clean
(`spec.items["task"].views == ["self_card"]`), `sq check` reports nothing, and `sq task 2 show`
renders the view correctly. Then:

```
$ sq task 2 show --json
error: view 'self_card' is a 'self' source; it has no projectable record list for --json yet
       — render it instead (`sq workflow view self_card TASK-2`, no --json)
exit 1
```

Not just the `views` key — the whole payload is gone. Every consumer of `build_item_json`
(`sq <type> <n> show --json`, and anything downstream that parses it) fails for *every item of
that type*, on a spec every gate calls clean.

`_check_item_views`' own docstring names this exact failure class as the reason its first axis
exists: "Left unchecked, this turns `show`/`show --json`/`show --raw` into a hard failure for
every item of the attaching type, on a spec `sq workflow lint` calls clean." The grammar
widening reintroduced the class through a door that axis does not cover.

**Two ways out, both cheap.** Either refuse the attachment at load for a kind whose resolved
value has no projection (one line beside the existing `subentity` axis — see F3, which wants the
same call site widened anyway), or give the attached-views `--json` path the per-source dispatch
TASK-919 already wrote for `sq workflow view --json`. The second is the better shape and is
arguably what US6's "no `{fields, group_by, groups}` envelope remains" asked for; the first is
the safe stopgap if this is meant to wait for FEAT-904.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-09-04T08:56:01Z] Paul Reviewer:
  - Verified fixed at `6ba3072d` — **driven**. Both of my original repros are now unreachable; I
    re-ran the exact overrides from the finding bodies against the fixed tree:
    
    ```
    [views.self_card] source = { kind = "self" }
    [items.task] views = ["self_card"]
      -> Invalid workflow spec: item 'task': views entry 'self_card' is a 'self' source;
         items.<type>.views may only attach a relation-sourced view
         (['ref', 'subentity', 'subtree']) — show --json has no serializer for the
         resolved value otherwise
    
    [views.role_card] source = { kind = "role" }
    [items.task] views = ["role_card"]
      -> same refusal, naming 'role'
    ```
    
    The refusal names the attaching type, the view, and the kind, and it fires at spec load — before
    any item is read — so `show`/`--raw`/`--json` can no longer be reached in the broken state at
    all. Using `VIEW_BASE_FIELDS_BY_SOURCE` membership as the family test rather than a literal kind
    list is the right call: it is the same dict `_views.RELATION_KINDS` is built from, so a future
    relation kind is attachable for free and a future non-relation kind is refused for free, with no
    second list to keep in step.
    
    **Control, driven — the new axis did not shadow the existing one.** The new `continue` sits above
    the `subentity` arm, so I checked that the pre-existing hosting check still fires:
    
    ```
    [views.f_card] source = { kind = "subentity", name = "finding" }
    [items.task] views = ["f_card"]
      -> Invalid workflow spec: item 'task': view 'f_card' projects 'finding' sub-entities,
         but a 'task' item hosts 'subtask'
    ```
    
    **Falsification: driven.** Deleting the new refusal block reddens exactly
    `test_a_self_sourced_view_attached_to_a_type_is_refused_at_load` and
    `test_a_role_sourced_view_attached_to_a_type_is_refused_at_load`, and nothing else.
    
    **The duplicated-question half of F3 is also resolved.** `subentity_source_reason`
    (`_workflow/_models.py`) is now the single composition point, called by both `_check_item_views`
    and `_views._subentity_source_applies` — one wording, one comparison, and the layering edge still
    runs one way (`_views` imports it, never the reverse). Its two-line `items.get(item_type)` lookup
    re-inlines `WorkflowSpec.item_subentity_kind`'s body byte-for-byte rather than calling the method,
    because `_check_item_views` runs mid-build with no `WorkflowSpec` in hand — **read**, correct, and
    not worth chasing: the *reason string* was what could drift, and that is now single-sourced.
    
    Closing on the understanding that the legacy type-attached projection path stays alive
    deliberately until FEAT-904 deletes it. The refusal above is what makes that safe in the interim.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Attached-view applicability is still only checked for subentity

<!-- sq:finding:F3:body -->
**Claim: driven.**

`_check_item_views` (`src/squads/_workflow/_models.py`) validates the reverse binding an
`items.<type>.views` list creates. Its second axis asks whether the view's source can apply to
the attaching type — but only for one of six kinds:

```python
            if v.source.kind == "subentity":
                kind = v.source.name
                hosted = ts.subentity_kind
                if hosted != kind:
                    ...errors.append(...)
```

`role` and `playbook` both carry host constraints of exactly the same shape, and both are
type-decidable, so both could be refused here. Neither is.

**Failure scenario (driven).** `.overrides/workflow.toml`:

```
[views.role_card]
source = { kind = "role" }
[items.task]
views = ["role_card"]
```

The spec loads clean and `sq check` reports nothing. Then:

```
$ sq task 2 show
╭──────────────────────────────╮
│ TASK-2  (task)               │
│ ...                          │
╰──────────────────────────────╯
## Description
_TODO: describe this task._
error: view 'role_card' projects a role definition, but 'task' is not the role type ('role')
exit 1

$ sq task 2 show --raw
error: view 'role_card' projects a role definition, but 'task' is not the role type ('role')
exit 1
```

The human path emits a partial render and then fails; `--raw` fails outright; `--json` fails via
F2's route. This is precisely the state ADR-880's second amendment was written to eliminate —
"a correct-looking corpus becomes unreadable with every gate clean" — except that the amendment
fixed it for the *tag* path (which now leaves the tag literal and reports it in the file scan,
verified working, see the review body) and nobody carried the same treatment to the
type-attached path.

**Second, related defect at the same call site: the applicability question is implemented
twice.** `_check_item_views`' `subentity` arm hand-rolls the question and its message:

```python
f"item {t!r}: view {name!r} projects {kind!r} sub-entities, but {t!r} hosts {hosted_desc}"
```

while `_views._subentity_source_applies` composes its own:

```python
f"view {view_name!r} projects {kind!r} sub-entities, but a {item_type!r} item hosts {hosted_desc}"
```

Two functions answering one question, with no test holding them in agreement — the REV-912 F2
shape, and against the amendment's explicit "One predicate, asked once, three consumers ...
never a second implementation of it." **read**

**Inferred** as to *why* it is duplicated: `_views.py` imports `_workflow._models`, so
`_workflow._models` cannot call `_source_incompatibility` without a cycle. That is a real
constraint, and it means the fix is a design call rather than a one-liner: either the predicate
registry moves below `_workflow._models`, or the attached-view applicability check moves up to
where `_views` is importable (a `sq check`/`sq workflow lint` validator rather than a spec-build
error). Worth deciding deliberately — one attachment axis covering one of six kinds is not a
resting state.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-09-04T08:56:04Z] Paul Reviewer:
  - Verified fixed at `6ba3072d` — one fix with F2; the driven repros, the control proving the new axis did not shadow the pre-existing `subentity` arm, and the falsification are all recorded on F2. The duplicated-wording half is resolved by `subentity_source_reason` as the single composition point.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — The role resolver bypasses the degrade seam it claims to reuse

<!-- sq:finding:F4:body -->
**Claim: driven.**

`_resolve_role_source` (`src/squads/_views.py`):

```python
    slug = item.extra.get(X.SLUG, item.slug)
    return resolve_role_with_base(slug, squad_dir, base=role_base_from_item(item, squad_dir))
```

Its docstring says this is "The exact resolution `ServiceCore.role_definition_text` already
calls for the hardcoded role-show path". That is true of the happy path and **false of the
failure path**, which is the one that matters here. The actual seam every other consumer uses is
`resolve_role_for_item` (`src/squads/_roles/_resolver.py:478`) — documented as "The one seam
every consumer that needs a live role item's full `RoleDef` goes through" — and it wraps the
same two calls in a fallback:

```python
    try:
        return resolve_role_with_base(slug, squad_dir, base=base)
    except RoleNotFoundError:
        return RoleDef.from_extra_or_item(
            item.extra, title=item.title, slug=slug, description=item.description
        )
```

`sq role <slug> show` has the same fallback inline (`_cli/_role.py`, both the `--json` and the
human branch). The `role` view source is a new consumer of that seam and bypasses it.

**Failure scenario (driven).** In a tmp squad: a project-declared custom role
`.overrides/roles/sre.toml`, activated (`ROLE-2`), a `role`-sourced view declared and its tag
placed. The tag expands correctly (`'Role: sre / site reliability engineer'`). Then the override
file is deleted — an ordinary edit, and a corpus state the codebase explicitly tolerates
elsewhere (`role_base_from_item`'s "anything else" case, and
`MaintenanceMixin._refresh_catalog_extra`'s own `RoleNotFoundError` catch). Observed:

```
resolve_role_for_item (the seam):  sre          <- still resolves, degraded
read_body                          RAISED: RoleNotFoundError: no predefined role 'sre' and no project override found
render_view                        RAISED: RoleNotFoundError: ...
_resolve_role_source               RAISED: RoleNotFoundError: ...
```

`read_body` is the one shared body-read boundary, so the blast radius is every read surface:
`sq <type> <n> show` / `--raw` / `--json`'s body field (`_cli/_common.py:694`, `:795`, `:1040`),
the TUI reader (`_tui/_reader.py:51`), `sq skill show` (`_cli/_skill.py:157`), `sq operator show`
(`_cli/_operator.py:155`). `sq check` reports nothing: the applicability predicate is type-scoped
and passes. Clean gates, unreadable item.

**On the design argument.** The code and
`test_the_role_resolver_may_raise_for_an_identity_its_predicate_could_not_decide` both argue
this raise is correct because an unresolvable slug is not decidable from the host's *type*, so
the classification test routes it to a defect. The classification is right; the disposition is
not. The amendment's stated reason for the split is that treating a corpus/spec mismatch as a
crash "put the louder half on the side where a correct-looking corpus becomes unreadable with
every gate clean" — and this case lands exactly there. It is a defect *and* the codebase already
ships the graceful degrade for it. §5 of the amendment reserves the loud half for "a render-time
failure with the precondition satisfied", meaning a template or engine fault; an orphaned role
definition is neither.

**Suggested shape:** call `resolve_role_for_item` rather than `resolve_role_with_base` directly.
That makes the resolver's own docstring true, removes the divergence from the documented seam,
and the item keeps reading. If a raise is genuinely wanted, the `role` source has to be
excluded from the read-time expansion path, which is not something a source kind can express
today.

**One more, at the same spot.** `test_a_bundled_role_resolves_to_the_same_definition...`
asserts `views._resolve_role_source(item, dir) == resolve_role_for_item(item, dir)` — it pins
the two together on the happy path while the code diverges on the failure path. That is why the
divergence shipped with an agreement test in place.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-09-04T08:56:36Z] Paul Reviewer:
  - Verified fixed at `6ba3072d` — **driven**. `_resolve_role_source` is now
    `return resolve_role_for_item(item, squad_dir)`. I re-ran my original repro (project-declared
    custom role `sre`, activated, `role` tag placed, then `.overrides/roles/sre.toml` deleted):
    
    ```
    before deletion   read_body -> 'Role: sre / site reliability engineer\n'
    after deletion    seam (resolve_role_for_item) -> sre
                      read_body   -> 'Role: sre / Sam SRE\n'      (was: RoleNotFoundError)
                      render_view -> 'Role: sre / Sam SRE\n'      (was: RoleNotFoundError)
    sq role sre show --raw -> exit 0, "(the definition for sre could not be resolved — run
                              `sq check` to see why)"
    ```
    
    The item reads. The blast radius named in the finding — `show`, `--raw`, `--json`'s body field,
    the TUI reader, `sq skill show`, `sq operator show` — is closed at the one shared boundary.
    
    **Falsification: driven.** Restoring the old `resolve_role_with_base` + `role_base_from_item`
    resolution reddens three tests, in three different registers:
    `test_an_unresolvable_role_identity_degrades_rather_than_raising` (unit predicate module),
    `test_an_orphaned_project_role_under_a_placed_tag_still_reads` (service, end to end through the
    real seams), and `test_resolve_role_source_delegates_to_the_documented_seam` (the delegation
    itself). Triple-covered.
    
    The resolver's docstring now claims what the code does ("Calls the documented seam every other
    consumer of a live role item's full `RoleDef` goes through ... so this inherits that seam's
    graceful degrade along with its happy path") — the false claim the finding flagged is gone.
    
    **One inherited behaviour, named rather than reopened.** In the degraded state a template reading
    `source.title` gets the *item's* title ("Sam SRE") where before deletion it got the definition's
    ("site reliability engineer") — `RoleDef.from_extra_or_item`'s documented mapping. So the render
    changes value rather than reporting absence. That is identical to what every other role reader
    does with an orphan, `sq role show --raw` says so in plain words on the same corpus, and
    `sq check` flags the underlying state. Inheriting the seam's behaviour wholesale is exactly what
    this finding asked for; if that mapping is ever wrong it is wrong for all of its readers, not for
    this one.
    
    See the corollary ruling on the review's own discussion for the classification question this fix
    raised.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — A ref/subtree view --json claims children: [] for records that have children

<!-- sq:finding:F5:body -->
**Claim: driven.**

`_view_json_payload`'s `ref`/`subtree` arm (`src/squads/_cli/_workflow_cmd.py`) builds each row
through `build_item_row_json` and takes the builder's defaults for the last two fields:

```python
def build_item_row_json(
    fields: ItemRowFields, *, spec, blocked_ids, anchor: bool = False,
    children: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ...
        "anchor": anchor,
        "children": children if children is not None else [],
```

`anchor: False` is an honest statement (the record is not a fabricated root). `children: []` is
not — it is a positive claim that the record has no children, and the resolver simply never
looked.

**Failure scenario (driven).** One tmp squad, one corpus: `EPIC-3` refs `MILE-2` with kind
`targets`, and `FEAT-4` has `EPIC-3` as its parent. Both commands run against that same state:

```
$ sq workflow view milestone_rollup MILE-2 --json
[ { "id": "EPIC-3", ..., "anchor": false, "children": [] } ]

$ sq tree EPIC-3 --json
[ { "id": "EPIC-3", ..., "anchor": false,
    "children": [ { "id": "FEAT-4", ..., "children": [] } ] } ]
```

Same node, same run, two different answers about whether `EPIC-3` has children.

Why that matters here rather than being a harmless default: the shape is *declared* to be
`sq tree --json`'s shape, in three places — the CLI help ("`ref`/`subtree` match `sq tree
--json`'s per-node shape"), `build_item_row_json`'s docstring ("the one definition `sq tree`'s
own node builder and a `ref`/`subtree` view's `--json` dispatch both build from"), and TASK-919's
acceptance ("matches `sq tree --json`'s per-node shape for those same N items, field for
field"). Field for field it does match; value for value it contradicts. A client written against
the documented equivalence reads a false fact.

**Why the pinning tests do not catch it.** Both required agreement tests compare only childless
records:

- `test_a_ref_sourced_views_json_equals_sq_tree_jsons_own_output` — two freshly created `task`s,
  no children, so `children: []` is correct on both sides.
- `test_a_subtree_sourced_views_json_equals_the_hosts_own_tree_children` — two `task`s under one
  `feature`; the compared slice is the feature's children, each of which is childless.

The equality discipline is the right discipline; the fixtures just have no depth. Adding one
grandchild to either fixture turns both tests red and is the cheapest guard.

**Two defensible fixes:** populate `children` from the same `_children_by_parent` walk `_views.py`
already has, or omit `anchor`/`children` from the flat-record shape and stop claiming the shapes
are the same. The second is smaller and arguably more honest — a flat resolved set is not a tree
— but it does break the byte-equality the tests assert, so it is a call for the tech lead rather
than a mechanical edit.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-09-04T08:56:38Z] Paul Reviewer:
  - Verified fixed at `6ba3072d` — **driven**. `_view_json_child_rows` now populates the real
    recursive descendant subtree via the newly-public `children_by_parent`. I re-ran my original
    repro, extended one level deeper (`MILE -> EPIC` by `targets` ref; `EPIC -> FEAT -> TASK` by
    parent), and diffed the two payloads on the same corpus in the same run:
    
    ```
    sq workflow view milestone_rollup MILE-2 --json
    sq tree EPIC-3 --json
    EQUAL: True     (EPIC-3 -> children[FEAT-4] -> children[TASK-5] -> children[])
    ```
    
    Byte-equal at two levels of depth — the exact case my repro disproved before.
    
    **The fixture weakness I flagged is closed.** Both agreement-pinning tests now redden when
    `children` is reverted to the flat default: `test_a_ref_sourced_views_json_equals_sq_tree_jsons_own_output`
    and `test_a_subtree_sourced_views_json_equals_the_hosts_own_tree_children`. **driven** — that is
    the depth the fixtures previously lacked.
    
    **Ordering agrees by construction, not by coincidence — read.** `_view_json_child_rows` sorts
    `sorted(children_by_parent.get(parent_id, []), key=lambda i: number_for_id(i.id))`, which is
    character-for-character `_walk_tree`'s own child ordering (`_services/_base.py`); `sq tree`'s
    `_sort_children` is identity when no `--sort` is passed, so the two walks emit the same order.
    The cycle guard (`seen`, seeded with the matched record's id) mirrors `_resolve_subtree_source`'s
    and is equivalent to `_walk_tree`'s ancestor set given that `parent` is single-valued.
    
    **The rename did not widen anything it shouldn't — read.** `_children_by_parent` ->
    `children_by_parent` is the only visibility change in the commit; it has exactly two callers
    (`_resolve_subtree_source` in-module, and `_view_json_payload` in `_cli`), the new edge runs
    `_cli` -> `_views` which is downward, and no other private name was touched.
    
    Two notes, neither reopening this:
    
    - **A documented divergence replaces the false claim.** `sq tree --json` hides settled items by
      default; this walk includes every descendant unconditionally, which the docstring states
      outright ("`sq workflow view --json` carries no flag equivalent to `sq tree --all`"). For a
      data endpoint that is the better default, and the byte-equality above holds because the fixture
      is all-open. The original defect was a false *negative* (`children: []` for an item that had
      children); a documented superset is not that.
    - **Three index loads per call.** `resolve_view_source` loads, `svc.blocked()` loads, and the new
      `child_map` loads a third time. Free under the CLI by the project's own stated pricing, and
      `sq tree --json` already pays two; worth knowing if `sq ui` ever routes through this.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — WorkflowSpec.is_delivered documents a delegation that does not exist

<!-- sq:finding:F6:body -->
**Claim: read.**

`WorkflowSpec.is_delivered` (`src/squads/_workflow/_models.py`) states:

> "The one place this comparison is made; `squads._views._is_delivered` delegates here rather
> than repeating `status == first_settled_status(...)` against a `_RawRecord`, so the
> record-shaped and bare-pair callers can never quietly diverge."

`_views._is_delivered`, added in the same commit, says the opposite and explains why:

> "Kept as its own comparison against `_delivery_target` rather than delegating to
> `WorkflowSpec.is_delivered` ... this function's own caller ... is real, ongoing use of
> `_delivery_target`, and a private module function pyright's strict mode would flag as dead the
> moment nothing calls it — delegating here would have deleted its only caller. The two are
> pinned to always agree by `tests/unit/test_settled_versus_delivered_status.py` instead."

and returns `rec.status == _delivery_target(rec.kind, spec)`.

So both halves of `is_delivered`'s sentence are false: nothing delegates to it, and it is not
"the one place this comparison is made" — there are two, held together by a test.

This is the same class of defect the finishing pass on TASK-918 already caught twice (docstrings
citing test files that were never written): prose asserting a property of the code that the code
does not have. It is worth naming rather than shrugging at, because the false claim is exactly
the one a future reader would rely on when deciding whether it is safe to change one of the two.

The pinning test is real and does its job — mutating `is_delivered` from "delivered" to "settled"
reddens all three of its cases (**driven**, reported by the implementer and re-confirmed by the
targeted run). The fix is one sentence of prose in `is_delivered`, not a code change: say that
`_views._is_delivered` makes the same comparison independently and name the test that holds them
together.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-09-04T08:57:03Z] Paul Reviewer:
  - Verified fixed at `6ba3072d` — **read**. `WorkflowSpec.is_delivered` now says `squads._views._is_delivered` "makes the identical comparison independently ... not a delegation (a private module function with no caller of its own would be dead code under pyright strict mode)" and names the pinning test. Both halves of the false sentence are gone, and the two docstrings now agree with each other and with the code. Grepped `delegates here` across `src/`: zero hits (pattern validated against a known positive).
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Stale prose describing the pre-per-source --json contract

<!-- sq:finding:F7:body -->
**Claim: read. One finding, full list attached — not iterated.**

The narration sweep was in both tasks' acceptance and it held: a phrase scan over the added
lines of all 31 changed files produced exactly one narration hit (item 3 below). What it did not
cover is *staleness introduced by the second commit into prose the first commit wrote* — the two
commits were reviewed as one change, and read that way the module docstring now describes a
contract the same feature replaced.

1. **`src/squads/_views.py` module docstring, last sentence of the source-family paragraph:**

   > "`--json` callers use `projection_json` directly and skip `render_view` entirely for the
   > relation kinds — the projection is the contract, presentation is one consumer of it;
   > per-source `--json` for the other three is a separate, later piece of work."

   False as of the second commit under review. `sq workflow view --json` no longer calls
   `projection_json` for any kind; per-source `--json` for the other three landed in
   `_cli/_workflow_cmd._view_json_payload`. The only surviving `projection_json` caller is
   `build_item_json`'s type-attached `views` key.

2. **`projection_json`'s own docstring** — "The `--json` contract: field metadata + grouping +
   records, no presentation output." It is now one specific caller's contract (the type-attached
   `views` key), not "the `--json` contract".

3. **`src/squads/_views.py`, `_is_delivered`'s docstring** — "`WorkflowSpec.is_delivered` (the
   bare-`(kind, status)` generalisation **this task** adds beside `first_settled_status` ...)".
   "this task" is diff-relative framing a stranger cannot resolve — the one hit the sweep's
   phrase list missed. Restate as the present-tense fact.

4. **Test module/function name mismatch.** `tests/service/
   test_render_resolved_source_or_raise_lets_a_missing_template_error_through_unwrapped.py`
   was renamed with the function it covers, but the test inside it is still
   `test_render_view_or_raise_lets_a_missing_template_error_through_unwrapped` — naming a
   function that no longer exists.

None of these change behaviour. They are on the record because the module docstring is the first
thing a reader of `_views.py` sees, and it currently sends them to the wrong function for the
`--json` contract.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-09-04T08:57:05Z] Paul Reviewer:
  - Verified fixed at `6ba3072d` — **read**. All four items closed:
    
    1. **Module docstring's `--json` contract** — rewritten to name the real dispatch point
       (`_cli._workflow_cmd._view_json_payload`) and to state what `projection_json` now is: "one
       remaining caller's contract, not that dispatch point", with the type-attached surface named
       and the reason it cannot serialize anything else. Accurate as of this commit.
    2. **`projection_json`'s own docstring** — now "A `Projection`'s own JSON shape ... The
       type-attached `items.<type>.views` surface's contract ... not `sq workflow view --json`'s, for
       any source kind."
    3. **`_is_delivered`'s "this task adds"** — removed; the sentence is present-tense only.
    4. **Test module/function name mismatch** — the function is now
       `test_render_resolved_source_or_raise_lets_a_missing_template_error_through_unwrapped`,
       matching its module.
    
    Grepped each removed fragment across `src/` and `tests/` (`per-source --json for the other
    three`, `The --json contract`, `this task adds`, `delegates here`): zero remaining copies, with
    the pattern validated against a known positive first.
    
    **Residual narration in the fix commit itself: none.** A phrase scan over the commit's added
    lines across all 18 changed files returned one hit, a false positive ("this pr" matching inside
    "this predicate"). Pattern validated against a known positive. Reporting this once, as asked —
    not iterating.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — read_body resolves the whole roster off disk for every tagged body read

<!-- sq:finding:F8:body -->
**Claim: read, with the cost traced rather than measured.**

`ItemsMixin.read_body` now resolves the full roster on every body read that carries any view
tag, whatever kind that tag names:

```python
        if not views.has_view_tag(body):
            return body
        db = await self.store.load()
        return views.expand_view_tags(
            body, item, db, self.spec, self.playbook, self.roster_from_db(db), self.paths.squad_dir
        )
```

`roster_from_db` calls `self._role_view(it)` per live role, which calls `resolve_role_for_item`,
which calls `role_base_from_item` + `resolve_role_with_base`. `_roles/_resolver.py`'s own module
docstring: "The resolver is *stateless*: it reads from disk on every call. The service layer is
already the cached / transactional boundary; there is no need to cache here." So a body read
with a single `ref`-sourced tag pays N `.overrides/roles/<slug>.toml` stat-and-read cycles
(N = live roles; 10 in this repo) for a value only the `playbook` kind ever looks at.

`_views.py`'s own cost statement is now understated as a result:

> "Cost is one already-loaded index plus an inversion/walk over it — the same shape `sq tree`
> and `sq blocked` have always had"

The eager argument was a deliberate call, and its stated reason is sound as far as it goes:
`expand_view_tags`' docstring says "a body can carry tags of more than one kind and the caller
already has all three in hand at its one call site". But the caller does *not* already have the
roster in hand — this change is what makes it compute one. `spec`, `playbook` and `squad_dir` are
genuinely free; `roster` is not.

**Cheapest fix that keeps the uniform call shape:** pass a zero-argument callable
(`Callable[[], list[RoleView]]`) instead of a materialised list, so the `playbook` arm forces it
and the other five never do. `roster_from_db` is already the right seam for that — it takes the
`db` the caller holds and does no I/O of its own beyond the per-role resolution.

Filed as low rather than ignored because the surfaces that call `read_body` are the interactive
ones (`show`, `--raw`, `--json`, the TUI reader), and because a recent release cycle added
explicit startup-cost and check-cost capabilities — this is the kind of per-read cost those
exist to keep visible.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-09-04T08:57:08Z] Paul Reviewer:
  - Verified fixed at `6ba3072d` — **read**, with the behaviour pinned behaviourally rather than by
    inspection. `resolve_source`/`expand_view_tags` now take a `RosterProvider`
    (`type RosterProvider = Callable[[], list[RoleView]]`, PEP-695), `_resolve_playbook_source` is
    the one call site anywhere in the dispatch that forces it, and `ItemsMixin.read_body` passes
    `cache(lambda: self.roster_from_db(db))` — a fresh memoized closure per read, so no `db` outlives
    its call.
    
    Two new tests hold both halves, and they are behavioural, not structural:
    
    - `test_read_body_never_computes_the_roster_for_a_self_sourced_tag` — spies
      `roster_from_db`, asserts `assert_not_called()`.
    - `test_read_body_computes_the_roster_once_for_two_playbook_tags` — two `playbook` tags in one
      body, `assert_called_once()`, which is the memoization half the finding's suggested fix would
      not have covered on its own.
    
    `ViewsMixin`'s three call sites pass a bare `lambda: self.roster_from_db(db)` rather than a
    memoized one — correct, and **read** rather than assumed: each calls `resolve_source` exactly
    once, which forces the provider at most once. The `RosterProvider` docstring states that
    contract explicitly ("A caller invoked more than once per roster ... is expected to memoize its
    own callable"), so the asymmetry is declared rather than accidental.
    
    The overstated cost claim in `_views.py`'s module docstring is unchanged and is now true again:
    with the provider lazy, a `ref`/`subtree`/`subentity`/`role`/`self` tag really does cost "one
    already-loaded index plus an inversion/walk over it".
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Field grammar on a non-relation view is silently accepted and inert

<!-- sq:finding:F9:body -->
**Claim: read.**

`_check_views` (`src/squads/_workflow/_models.py`) skips the whole field/`group_by`/`order_by`
branch for the three non-relation kinds:

```python
        if v.source.kind not in VIEW_BASE_FIELDS_BY_SOURCE:
            continue
```

`ViewSpec` still accepts `fields`, `group_by` and `order_by`, so an adopter can write

```
[views.self_card]
source = { kind = "self" }
fields = [ { code = "not_a_field", label = "Nonsense" } ]
group_by = "not_a_field"
```

and the spec loads clean. Nothing reads any of it: `render_source_view` hands the template
`source`/`item`/`spec` (+`squad_dir`), and `_view_json_payload` never touches the field list.

This is against that same function's own stated purpose one paragraph earlier — "a source that
can never resolve is refused here rather than carried as an inert declaration" — and against the
project's general "customisation must not be able to break squads, and a declaration that means
nothing is refused, not ignored" posture.

TASK-918 asked for exactly this ("`_check_views` must skip that branch entirely for
`role`/`playbook`/`self` rather than requiring a `fields` list that means nothing for them"), so
the implementation followed the brief. The brief's alternative was "require a fields list", and
"skip" was the right call between those two. The third option — *refuse* a field grammar on a
kind that has none — was not on the table and is the one that matches the module's own rules.

Filed as info because FEAT-904 deletes the `fields`/`group_by`/`order_by` grammar outright,
which resolves it for free. Recording it so that deletion is a deliberate resolution rather than
an accident, and so that a reader in the interim knows a silently-inert declaration is possible.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — self --json spec identity reports file existence, not what resolved the view

<!-- sq:finding:F10:body -->
**Claim: read.**

`_spec_identity_json` (`src/squads/_cli/_workflow_cmd.py`) is this task's own invented shape —
the implementer flagged it for review, which is the right call, so here is the read on it.

```python
    override = (svc.paths.squad_dir / WORKFLOW_OVERRIDE_FILENAME).is_file()
    return {"schema_version": SCHEMA_VERSION, "override": override}
```

Two gaps between the docstring and the code:

1. The docstring says `override` "says whether a project `.overrides/workflow.toml` is **in
   force**". The code says whether the file **exists**. Those differ whenever the override is
   present but not fully applied — an unstamped or partially-rejected document — and a client
   told "in force" would draw the wrong conclusion. Either weaken the sentence to "a workflow
   override document is present", or report the loader's actual merge outcome.

2. The stated purpose is "enough of the active spec's identity for a `self`-view client to tell
   **which spec resolved the payload**". A boolean plus a schema version cannot distinguish two
   different override documents, and it says nothing about `.overrides/playbook.toml` or
   `.overrides/roles/*.toml`, which also shape what a view resolves against (the `playbook`
   source reads the first directly). A client comparing two payloads from two squads, or from
   the same squad before and after an override edit, gets the same answer both times.

Not a correctness bug in what ships — `{schema_version, override}` is internally consistent and
tested. It is a client-facing contract invented under time pressure, and the moment a real
client depends on it, changing it is a breaking change. Worth settling now: either narrow the
promise to what the two fields actually support, or carry something that identifies the merged
spec (a content hash of the override set would do it, and would cover all three documents).
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — ViewsMixin repeats the resolve-a-view block three times

<!-- sq:finding:F11:body -->
**Claim: read.**

`ViewsMixin` (`src/squads/_services/_views.py`) now carries the same eight-line preamble three
times — in `resolve_view`, `resolve_view_source` and `render_view`:

```python
        view = self.spec.views.get(view_name)
        if view is None:
            raise SquadsError(
                f"no declared view {view_name!r}; see `sq workflow views` for the declared set"
            )
        db = await self.store.load()
        item = require_item(db, item_id)
        result = views.resolve_source(
            view, view_name, item, db, self.spec, self.playbook,
            self.roster_from_db(db), self.paths.squad_dir,
        )
```

including the identical error string in all three. The three methods differ only in what they do
with `result`: project it, return it, or render it. `resolve_view_source` already returns
`(view, item, result)` — exactly what the other two need — so `render_view` could be two lines
over it, and `resolve_view` three.

Filed as info, not as a change request for this feature: FEAT-904 deletes `resolve_view`, which
takes one of the three copies with it, and collapsing the remaining two is a natural part of
that pass rather than a separate edit now. Recording it so the collapse is on someone's list —
three copies of one error string is how a message drifts.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-04T07:57:49Z] Paul Reviewer:
  - Review complete on the combined diff (64fe1cb6..HEAD, both commits read as one change).
    Recommended verdict: **ChangesRequested** on F1-F4; F5-F11 do not need to block a merge.
    
    Eleven findings: four high, one medium, three low, three info. The four high ones share one
    root — the widening added three source kinds to `_SOURCE_APPLICABILITY` and the tag path picked
    them up correctly (verified working end to end), but three other consumers were not carried
    along: the type-attached `views` list at spec load (F3), that same list's `--json` render (F2),
    and the role resolver's failure path (F4). F1 is a straight conflict between the ADR's emptiness
    clause and the playbook predicate, which TASK-918's own body asked for both ways.
    
    - **F1** high — the `playbook` predicate refuses a declared-but-unlaned type, so the resolver's
      documented `lane=None` result and `_playbook_json_payload`'s whole `lane: None` arm are
      unreachable. Driven against a real unlaned declared type.
    - **F2** high — attaching a `role`/`playbook`/`self` view to a type makes `sq <type> <n> show
      --json` exit 1 for every item of that type; `build_item_json` calls `resolve_view`
      unconditionally and TASK-918 taught it to refuse those kinds. Spec loads clean. Driven.
    - **F3** high — `_check_item_views`' applicability axis still covers only `subentity`, so a
      `role` view attached to `task` loads clean and then breaks `show`/`--raw` at read time.
      Driven. Same call site also implements the subentity applicability question a second time,
      unpinned.
    - **F4** high — `_resolve_role_source` calls `resolve_role_with_base` directly instead of the
      documented `resolve_role_for_item` seam, so an orphaned role item with a `role` view tag
      raises `RoleNotFoundError` out of `read_body` — every read surface, `sq check` silent. Driven
      by deleting a project role override under a placed tag.
    - **F5** medium — a `ref`/`subtree` view's `--json` emits `children: []` for records that
      demonstrably have children; both agreement-pinning tests compare only childless fixtures.
    - **F6/F7** low — `WorkflowSpec.is_delivered` documents a delegation that does not exist, and
      `_views.py`'s module docstring still describes the pre-TASK-919 `--json` contract. F7 carries
      the full stale-prose list in one place; the narration sweep itself held (one hit).
    - **F8** low — `read_body` resolves the whole roster off disk for every tagged body read,
      including for kinds that never read it.
    - **F9/F10/F11** info — inert field grammar accepted on non-relation views; `self`'s
      spec-identity shape promises more than it delivers; `ViewsMixin` repeats the resolve preamble
      three times.
    
    Verified clean and not padded with findings: no predicate reads the host item's content (enforced
    structurally); `subtree` emptiness is not a reachability check; the old projection path coexists
    with exactly one live caller and nothing half-deleted; layering, `SquadsError` discipline,
    PEP-695 aliases and the no-ticket-IDs rule all hold. The `_cli/_role.py` -> `_cli/_common.py`
    move is layering-correct and I found no behaviour lost in the shared builders beyond F5
    (`badge_value("priority")`/`("severity")` are the same real attributes the old inline dicts read;
    `roster_from_db` is filter-and-sort-identical to the path it replaced). Placement of the three
    role helpers in `_common.py` is a cohesion note in the review body, not a finding.
    
    Falsification spot-checks are tabulated in the review body: seven mutations, each reddening the
    tests that should catch it. Every new applicability predicate is genuinely covered.
    
    Not approving my own review. @manager F1-F4 need a ruling before FEAT-903 closes — F1 is an
    ADR-vs-task-body conflict that wants @architect, F2/F3 want @tech-lead on where the
    attached-view check belongs given the `_workflow` -> `_views` import direction.
- [2026-09-04T07:59:17Z] Catherine Manager:
  - ChangesRequested on F1-F4. One root, four faces: the three new kinds reached _SOURCE_APPLICABILITY and the tag path is correct end to end, but three other consumers were never carried along -- show --json, _check_item_views, and the resolve_role_for_item seam. F1 is a direct violation of the second amendments emptiness corollary, which is the one I flagged to the reviewer as most likely to be implemented as a reachability check by accident.
- [2026-09-04T08:08:08Z] Olivia Lead:
  - Fix task authored: TASK-921 (Draft, parent FEAT-903, refs ADR-880 implements + this review addresses), 7 subtasks, one per F1-F8 plus a gates subtask.
  - Triage: F1-F8 all in scope (non-info, per standing rule). F1 fixed by dropping the lane refusal (predicate goes constantly-true, matches ref/subtree/self). F2+F3 collapse to one fix -- _check_item_views refuses type-attaching any non-relation-kind view at spec load, which makes both failure scenarios unreachable (resolve_view already had no serializer for them); the subentity host-constraint duplication folds onto the shared predicate too. F4 fixed by routing _resolve_role_source through resolve_role_for_item, the documented degrade seam. F5 ruled to populate real children via the existing _children_by_parent walk, not drop the fields -- keeps the shipped sq-tree--json-shape contract intact rather than retreating from it. F6+F7 are prose-only. F8 threads a lazy roster callable through resolve_source so only playbook forces the roster load.
  - F9 and F11 are homed to FEAT-904 (deletes the field grammar and resolve_view outright this release) -- a separate fix now would be thrown away. F10 (self --json spec-identity shape) is not resolved by FEAT-904s stated scope; noted there as a design question for whenever self/playbook JSON is next touched, not load-bearing for any client today. Comment left on FEAT-904.
  - Left every status untouched -- FEAT-903, this review, and all eleven findings are unchanged by me; that disposition is for @manager/@architect to rule on once TASK-921 lands.
- [2026-09-04T08:57:39Z] Paul Reviewer:
  - ## Ruling: `role`'s resolver no longer raising is correct, and the corollary is unharmed
    
    The dev flagged that F4's fix inverts this module's prior claim — "`role` is the one kind whose
    resolver *can* still raise" became "`role`'s resolver degrades rather than raising" — and said
    plainly that this is a materially different claim rather than a tautological re-pin. He is right
    that it is materially different, and the new assertion is the correct one.
    
    **Why the old assertion was a misreading, not a fact that changed.** The amendment's first
    corollary reads:
    
    > A resolver may not raise for a condition its kind's predicate could have decided. Every raise
    > left inside a resolver is, after this ruling, a defect signal.
    
    That is a prohibition plus a reading rule. The prohibition constrains *which* conditions may
    raise: decidable ones may not. The reading rule tells you how to interpret a raise you find: it
    can only be about a not-decidable condition. Neither sentence says a not-decidable condition
    *must* be signalled by a raise. The old assertion read the reading rule as a licence — "not
    decidable, therefore raises" — and then hardened that inference into a test.
    
    An unresolvable role identity was never decidable from the host's type, so a raise there was
    never *forbidden*. It was also never *required*. What changed at `6ba3072d` is the disposition of
    a permitted-but-not-mandated raise, and it moved toward the amendment's own stated purpose: the
    whole reason the applicability split exists is that treating a corpus/spec mismatch as a crash
    "put the louder half on the side where a correct-looking corpus becomes unreadable with every
    gate clean." An orphaned role definition is a corpus/spec mismatch. §5 names what the loud half
    is actually reserved for — "a render-time failure with the precondition satisfied": a template
    raising under `StrictUndefined`, or an engine fault. An orphan is neither.
    
    So the corollary is satisfied both before and after. The fix did not weaken it; it stopped the
    test from asserting something the corollary never claimed.
    
    **What that means for the corollary's reachability.** No per-kind resolver now contains a raise,
    and `test_no_per_kind_resolver_function_raises` sweeps all six rather than five. The reading rule
    is therefore currently vacuous *at the resolver level* — there are no remaining raises to read as
    defect signals. That is the corollary working, not eroding. It stays binding as a rule for the
    next source kind: a kind arriving with a raise in its resolver now owes two justifications, not
    one — that the condition is not decidable from the host's type, *and* that degrading to a
    well-formed value is genuinely impossible. A kind that cannot make the first argument has a
    precondition it failed to declare; one that cannot make the second is choosing an unreadable
    corpus over a degraded render, which this ruling says it may not do silently.
    
    **What is left inside the loud half.** Two things, both above the resolvers, and nothing else:
    
    1. `resolve_source`'s own applicability raise, for the direct-question caller
       (`sq workflow view <name> <id>`) — an inapplicable pair is a bad argument, not a broken read.
       Pinned by `test_the_dispatcher_is_where_the_direct_question_caller_raises_instead`.
    2. `render_view`/`render_source_view`'s `ViewTemplateMissingError`, and the engine-translated
       `TemplateError` that `_render_resolved_source_or_raise` re-raises with the item named —
       exactly §5's "render-time failure with the precondition satisfied".
    
    **One caveat on how the new assertion is held.** `_contains_raise` parses a function's own body.
    For the five self-contained resolvers that is a real guard. For `role`, now a one-line delegation
    to `resolve_role_for_item`, it is not: the structural test would pass unchanged if that seam were
    made to re-raise. The docstring is honest about this, and the behavioural guards are what
    actually hold it — `test_an_unresolvable_role_identity_degrades_rather_than_raising` and the
    end-to-end orphan repro, both of which redden when the old resolution is restored (**driven**).
    Adequate as a pair. Worth knowing that for this one kind the structural half carries less weight
    than its siblings, so a future change to `resolve_role_for_item` needs to be read against the
    behavioural tests rather than trusted to trip the structural one.
- [2026-09-04T08:58:03Z] Paul Reviewer:
  - ## Close-out: F1-F8 verified fixed at `6ba3072d`, F9-F11 deferral sound
    
    All eight verified in one pass, each closed with its own driven evidence on the finding's own
    discussion. Summary:
    
    - **F1** — predicate constantly true, `lane=None` reachable end to end; and the amendment's
      "declared" half genuinely survives it (I drove `_check_views`' unconditional
      `_resolve_view_source` call independently of the tests: an undeclared `playbook` name is still
      refused at load, a declared one loads, and `role`/`self` still refuse a name).
    - **F2+F3** — both repros now refused at spec load, naming type/view/kind; the pre-existing
      `subentity` axis still fires (controlled for, since the new `continue` sits above it); the
      duplicated wording is single-sourced through `subentity_source_reason`.
    - **F4** — `read_body` and `render_view` both succeed on the orphaned-role corpus that
      previously raised out of the shared body-read boundary.
    - **F5** — view `--json` now byte-equal to `sq tree --json` two levels deep on the same corpus,
      and the pinning fixtures now have the depth they lacked.
    - **F6/F7** — the false delegation claim and all four stale-prose items gone; zero residual
      narration in the fix commit's own added lines (one false positive, "this predicate").
    - **F8** — lazy memoized `RosterProvider`, pinned behaviourally in both directions
      (`assert_not_called` for a non-playbook tag, `assert_called_once` for two playbook tags).
    
    **Falsification, driven, four mutations against a 10-file targeted selection (131 tests, green
    at baseline), each reverted:**
    
    | Mutation | Result |
    | --- | --- |
    | restore the lane-requiring `playbook` refusal | red: the unlaned end-to-end case, and only it |
    | delete the non-relation attachment refusal | red: both new load-refusal tests |
    | revert view `--json` `children` to the flat default | red: both agreement-pinning tests |
    | restore `role`'s raising resolution | red: 3 tests (unit predicate, service end-to-end, delegation) |
    
    Every guard genuinely tests its behaviour; none passes incidentally.
    
    **F9-F11 deferral: sound, and for the stated reasons.** F9 (inert field grammar accepted on a
    non-relation view) and F11 (`ViewsMixin`'s repeated resolve preamble) are both artefacts of the
    grammar and the method FEAT-904 deletes outright — resolved for free there, and neither is
    reachable as a failure in the interim. F9's blast radius is narrower still now that F2/F3 refuse
    attaching a non-relation view at all: the inert declaration can only sit on a freestanding view
    reached via `sq workflow view`. F10 (`self --json`'s spec identity promising more than
    `{schema_version, override}` delivers) is a design question about an invented client-facing
    contract, not a defect in what ships, and it wants settling before a client depends on it —
    FEAT-904 is the right place for that, since the same pass decides what the `--json` surface
    looks like overall.
    
    **Scope note:** I confirmed the eight and ruled the one classification question, and stopped
    there — no re-review of the feature, and the residual-prose result is reported once above rather
    than iterated.
    
    Verdict: **Approved**, on the coordinator's delegation (they verified the F1 and F2+F3 rulings
    themselves before dispatch, and hold the authoritative full-suite result at 4834 passed / 12
    skipped). @manager FEAT-903 is clear from my side; F9-F11 stay Open against FEAT-904.
<!-- sq:discussion:end -->
