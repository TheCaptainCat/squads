---
id: TASK-919
sequence_id: 919
type: task
title: Per-source --json for the widened view source grammar
status: Done
parent: FEAT-903
author: tech-lead
assignee: python-dev
refs:
- ADR-880:implements
- TASK-918:depends-on
subentities:
- local_id: ST1
  title: 'ref/subtree/subentity/role --json: dispatch to each kind''s existing serializer'
  status: Done
  story: US6
- local_id: ST2
  title: self/playbook --json + envelope-removal grep + emptiness cases
  status: Done
  story: US6
- local_id: ST3
  title: 'Gates: falsification, narration sweep, agreement pinning, sq check'
  status: Done
  story: US6
created_at: '2026-09-03T15:07:18Z'
updated_at: '2026-09-04T07:36:08Z'
---
<!-- sq:body -->
## Scope

Rewire `sq workflow view <name> <id> --json` off the retired `{fields, group_by, groups}`
projection envelope, onto the per-source shape each kind already has a serializer for --
completing FEAT-903's `--json` half now that TASK-918 (the role/playbook/self resolvers) exists
for it to dispatch to. ADR-880's `--json` ruling: "each source kind serializes in the shape it
already has a serializer for ... no bespoke envelope. `--json` answers about the data, `--raw`
about the text." US6 is the acceptance surface; this task is where it lands.

**Depends on TASK-918.** `role`/`playbook`/`self` must already resolve through `resolve_source`
before their `--json` shape can be wired -- do not start this task until TASK-918 is Done.

## What lands

`sq workflow view <name> <id> --json` (`_cli/_workflow_cmd.py::workflow_view`) stops calling
`projection_json` unconditionally and dispatches on the view's declared `source.kind`:

- **`ref`/`subtree`** -- the resolved items serialize in the same shape `sq tree --json`/`sq
  list --json` already emit for an item row (reuse that shape's builder rather than
  re-deriving field-by-field; the service-layer machinery those two commands already share is
  the reuse target).
- **`subentity`** -- the resolved sub-entities serialize in the same shape `sq <type> <n>
  <kind>s --json` (the per-kind list command, e.g. `sq task <n> subtasks --json`) already
  emits.
- **`role`** -- the resolved `RoleDef` serializes as the full resolved definition, the same
  shape `sq role <slug> show --json` already emits (`_cli/_role.py::_role_json_payload`).
  Extract the reusable half of that payload builder rather than writing role-JSON shape a
  second time; `_role_json_payload` itself stays CLI-layer, so this reuse happens within
  `_cli`, never by `_views.py`/`_services` reaching up into it.
- **`self`** -- the host item serializes in the same shape an item's own `show --json` already
  emits for that item, plus enough of the active spec's identity (never the whole spec object
  -- that is not item-shaped JSON) that a client can tell which spec resolved it.
- **`playbook`** -- no pre-existing serializer covers a playbook lane; ADR-880's text does not
  enumerate one either (only `ref`/`subtree`/`subentity`/`role` are named in both the ADR and
  this feature's own US6 acceptance). Build the smallest natural shape -- the lane's own
  declared fields (overview, commands, per-role sections) plus the resolved type and roster --
  and treat it explicitly as **not** a reintroduction of the retired `{fields, group_by,
  groups}` envelope: no `fields`/`group_by`/`order_by` keys, no generic projection wrapper,
  just the lane's own shape. Name this decision in the handoff comment so it is on the record
  rather than silently invented.

No source kind's `--json` output may contain `fields`, `group_by`, or `groups` keys -- grep
the new code for those three literal strings after writing it.

`sq workflow views --json` (the view *catalog*, not a resolved view) is **out of scope** -- it
lists declarations, still validly emits `fields: []`/`group_by: null` for a
`role`/`playbook`/`self`-sourced view under today's grammar, and reshaping its output is
FEAT-904's job when the grammar it describes is deleted, not this task's.

## Acceptance

**US6 -- per-source `--json` matches each kind's own existing serializer.**
- `ref`/`subtree` `--json` on a view resolving to N items matches `sq tree --json`'s per-node
  shape for those same N items, field for field.
- `subentity` `--json` matches the per-kind list command's shape.
- `role` `--json` matches `sq role <slug> show --json`'s resolved-definition shape.
- `self` `--json` matches the host item's own `show --json` shape.
- `playbook` `--json` is documented in the task's handoff comment as this task's own reasoned
  shape (no pre-existing serializer to match), and is internally consistent (every declared
  lane on the bundled spec round-trips through it without a crash).
- No `{fields, group_by, groups}` envelope remains in any of the six kinds' `--json` output.
- `--raw` is unaffected -- it still returns the rendered text; this task touches `--json` only.

**Emptiness, tested as success per kind:**
- `ref`/`subtree` `--json` on zero matching records emits an empty list in that kind's shape,
  not an error.
- `subentity` `--json` on a host with zero sub-entities of the projected kind emits an empty
  list.
- `playbook` `--json` on a declared-but-unlaned type emits the shape's own "no lane" case, not
  a raise.

## Project constraints

- Layering: `_cli` may call into `_services`/`_views.py`; neither of those may call up into
  `_cli` -- the role-payload reuse above stays inside `_cli`.
- `SquadsError` for any user-facing refusal; never a bare exception.
- Escape console output with `_cli._common.e()` on any human-readable path this task touches --
  the JSON path itself is machine output, not escaping-exempt from correctness but not a Rich
  markup concern.
- No `from __future__ import annotations`; PEP-695 `type X = ...` for any new alias.
- No sq/ticket IDs in source or test filenames.
- A new module-level dict/list stays allowlisted in `tests/meta` as a CODE constant.
- Multi-exception handlers parenthesized with `# fmt: skip`.

## Acceptance -- gates

1. **Narration sweep is part of this task's acceptance, not a later pass.** The stranger test,
   sentence by sentence, on every new docstring/comment/error string this task adds; then a
   post-rewrite grep across this feature's whole added-prose surface for any old wording
   removed -- not a phrase-list grep run before the rewrite. A line-oriented grep misses a
   phrase split by a wrap; use a throwaway ast+tokenize block scan in the scratchpad if needed,
   never committed.
2. **Falsify every new test.** Break the dispatch (route a kind to the wrong serializer, or
   drop a branch entirely), watch it go red, restore it, watch it go green, report both
   directions in the handoff comment.
3. **Pin agreement between functions answering the same question.** The `ref`/`subtree`
   `--json` output and `sq tree --json`'s own output must be asserted *equal* (not merely
   "similarly shaped") for the same query -- a test that runs both against the same fixture and
   diffs the JSON is this task's required instance.
4. **`uv run sq check` clean**, plus `uv run --all-extras pyright && uv run --all-extras ruff
   check . && uv run --all-extras ruff format --check .` clean -- `--all-extras` on every one
   of the three.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 919 add-subtask "<title>"`; track with `sq task 919 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — ref/subtree/subentity/role --json: dispatch to each kind's existing serializer

<!-- sq:subtask:ST1:body -->
workflow_view --json dispatches on source.kind instead of calling projection_json unconditionally: ref/subtree match sq tree --json/sq list --json's item-row shape; subentity matches the per-kind list command's shape (e.g. sq task <n> subtasks --json); role matches sq role <slug> show --json's resolved-definition shape (extract the reusable half of _role_json_payload rather than re-deriving it -- stays inside _cli, never _views.py/_services reaching up). See task body 'What lands' and US6 acceptance.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — self/playbook --json + envelope-removal grep + emptiness cases

<!-- sq:subtask:ST2:body -->
self --json matches the host item's own show --json shape plus enough spec identity to say which spec resolved it (never the whole spec object). playbook --json has no pre-existing serializer to match -- build the smallest natural shape (lane fields + resolved type + roster), explicitly not the retired {fields, group_by, groups} envelope, and name that decision in the handoff comment. Grep all six kinds' --json output for fields/group_by/groups keys: zero hits. Cover emptiness per kind (zero records, zero sub-entities, unlaned type) as success, not a raise. See task body 'What lands' and US6 acceptance.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Gates: falsification, narration sweep, agreement pinning, sq check

<!-- sq:subtask:ST3:body -->
Apply the stranger test to every docstring/comment/error string this task adds, then grep any old wording removed across the feature's added-prose surface post-rewrite. Falsify every new test (break the dispatch, red, restore, green, report both directions). Required agreement-pinning test: assert ref/subtree --json output equals sq tree --json's own output for the same query, not merely similarly-shaped. uv run sq check clean, plus pyright/ruff check/ruff format --all-extras clean, before handoff.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-04T07:32:43Z] Elias Python:
  - Per-source --json landed. All three subtasks Done.
    
    **ST1/ST2 — dispatch + shapes**
    `workflow_view --json` (_cli/_workflow_cmd.py) now dispatches on view.source.kind through a new
    `_view_json_payload`, reusing svc.resolve_view_source (new ViewsMixin method, mirrors
    render_view's resolution but returns the native SourceResult instead of forcing render/project):
    - ref/subtree -> build_item_row_json (new shared _cli/_common.py builder + ItemRowFields
      dataclass) — the exact function sq tree --json's node() now calls too (refactored tree() to
      share it, kept behaviourally identical, proven — see falsification below).
    - subentity -> build_subentity_row_json (new shared builder), also now used by
      `sq <type> <n> <kind>s --json`'s list_sub in _items.py.
    - role -> build_role_json_payload/role_base_for_show/dev_preview_full_name. These three were
      private to _cli/_role.py (_role_json_payload etc.) — pyright's reportPrivateUsage (strict in
      src/, only relaxed for tests/) refused a cross-module import, so per the task's own
      instruction ("extract the reusable half") I moved all three into _cli/_common.py as public
      functions and updated _role.py's show_role to call them via `common.`. Two existing test
      files imported the old private names directly (test_dev_base_gating_reads_the_stored_fact_
      first.py, a docstring line in test_roles_catalog_dev_override_reaches_the_unadded_preview.py)
      — updated both to the new location/names; both still pass.
    - self -> build_item_json (existing) + new _spec_identity_json: {"schema_version", "override"}
      where override is whether .overrides/workflow.toml exists — my own reasoned choice for
      "enough spec identity to say which spec resolved it, never the whole object." Named here per
      the task's instruction to record playbook's shape decision — same treatment for this one.
    - playbook -> new _playbook_json_payload (no pre-existing serializer): {type, lane, roster};
      lane is {overview, lifecycle, commands, roles:[{slug,enter,do,handoff,watch,authors}]} or
      None for the unlaned case. No fields/group_by/order_by anywhere — grepped the new dispatch
      code and _common.py's new builders for those three literal strings: zero hits.
    
    **Coexistence, manually verified** (not just asserted): `sq workflow view milestone_rollup
    <id> --json` now emits the new tree-node-shaped array; `sq milestone <id> show --json`'s
    "views" key (the type-attached items.<type>.views feature, via build_item_json ->
    svc.resolve_view -> projection_json, all untouched) still emits the old {fields, group_by,
    groups} envelope for that same view. Ran both by hand against a live squad — old path and new
    path coexist exactly as instructed, resolve_view/projection_json genuinely still needed and
    still correct for their one remaining caller.
    
    **Agreement-pinning (ST3's named requirement)**: two CLI tests in test_workflow_views_cli.py
    run the real `sq tree --json` (or, for subtree, `sq tree <host> --json` navigated to the real
    `children` key of the real root node) and assert byte-equal against the view's own --json
    output for an equivalent query — never a hand-written expected dict. Same discipline for
    subentity: asserts equal against the real `sq review <n> findings --json` output.
    
    **Emptiness, tested as success per kind** (all in test_workflow_views_cli.py):
    ref (no matching refs), subentity (no sub-entities) -> `[]`, not an error.
    playbook's unlaned case is tested at the resolver/builder level directly (new unit file
    test_playbook_view_json_payload_shape.py) rather than through the gated CLI path — the
    playbook applicability predicate already refuses an unlaned type before resolve_source ever
    returns one (same shape as TASK-918's own playbook resolver test), so the CLI path can't reach
    PlaybookSource(lane=None); the builder's handling of it is real and tested, just not reachable
    end-to-end today.
    
    **Falsification, both directions, every new test** (restored to green after each; no
    FALSIFICATION-PROBE markers remain in the tree, grepped clean):
    - ItemRowFields.title swapped for status in the ref/subtree branch -> red in both equality
      tests. Restored, green.
    - subentity branch's severity field swapped to the wrong badge code -> red in the subentity
      equality test only (group_count/emptiness tests correctly stayed green, since they don't
      check field values). Restored, green.
    - subentity branch disabled entirely (falls through to self) -> red in both the subentity
      equality test AND its emptiness test (proves the emptiness case isn't accidentally passing
      for the wrong reason). Restored, green.
    - ref/subtree branch made to raise on an empty result -> red in exactly the ref emptiness test,
      the two non-empty equality tests stayed green (confirms the raise, not the mechanism, was the
      point of failure). Restored, green.
    - role branch rerouted through build_item_json (self's shape) -> red in the role equality test.
      Restored, green.
    - self branch's `payload["spec"] = ...` line dropped -> red (KeyError on the test's own
      `payload.pop("spec")`). Restored, green.
    - playbook branch shorted to `return {}` -> red. Restored, green.
    - resolve_view_source made to always return `result=[]` without calling resolve_source -> red
      in ref/subtree/subentity/playbook (the four kinds that actually consume `result`); role and
      self stayed green, which is correct and worth noting — both ignore `result` entirely (role
      re-resolves by slug, self only needs `item`), so this probe precisely separates which kinds
      depend on the new seam. Restored, green.
    - _playbook_json_payload: forced the None-lane branch unreachable -> red only in the
      "no lane" unit test (AttributeError on None.overview); the round-trip test stayed green (real
      lanes are never None). Restored, green.
    - _playbook_json_payload: dropped the "watch" key from a role row -> red only in the
      round-trip test (key-set assertion). Restored, green.
    - _playbook_json_payload: added a stray "fields" key -> red only in the envelope test.
      Restored, green.
    - Refactor-safety probes against PRE-EXISTING tests (not new, but these two functions moved/
      changed and needed proof nothing regressed): forced tree()'s node() to always emit
      anchor=False -> red in test_bare_tree_covers_list_on_a_cyclic_corpus_cli.py's
      test_the_invented_root_carries_a_field_on_the_wire. Forced list_sub's severity to always be
      None -> red in the review_findings golden (test_json_output_shape.py) and both
      test_add_subentity_status_flag_cli.py tests. Both restored, both green.
    
    **Narration sweep**: reused the ast+tokenize scanner already in the scratchpad (validated
    against its own known-positive fixtures first — both a plain and a line-wrapped narration
    phrase caught). Ran restricted to this task's added lines across all 10 touched/new files:
    found and fixed four real hits on first pass (all diff-relative framing a stranger can't check)
    — "this task reasons out" -> "reasoned out directly here"; "no longer the retired {...}
    envelope" / "no longer carries a group" -> present-tense-only restatements; a docstring
    literally saying "see the handoff comment on the task that added per-source --json" -> replaced
    with a checkable claim (no pre-existing serializer elsewhere in the codebase). Re-scanned:
    zero. Manual sentence-by-sentence read then caught three more the phrase list doesn't cover
    ("retired"/"retiring" used three more times without matching a listed phrase, "The required
    agreement-pinning instance" echoing the task's own acceptance wording) — fixed all three,
    grepped every removed fragment's exact old wording across src+tests afterward: zero remaining
    copies in every case.
    
    **Gates**: `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run
    --all-extras ruff format --check .` — all clean, full repo. Targeted selection (32 view/role/
    playbook-related files, all touched-or-adjacent) + `tests/meta` in full: 569 passed, 0 failed.
    `uv run sq check`: clean. Did not run the full suite (per instructions).
    
    **Unresolved / worth a look**
    - self's spec-identity shape ({schema_version, override}) and playbook's whole shape are both
      this task's own invented design, per the task body's instruction to name that decision here
      rather than silently invent it — flag if you want either shaped differently before it's
      load-bearing for a real client.
    - Nothing else outstanding that I'm aware of. FEAT-903's US6 acceptance surface should be fully
      landed now (TASK-918 + this task); FEAT-904 (deleting the projection layer, resolve_view/
      projection_json/Cell/ViewRecord/etc.) is still open and untouched, as scoped.
- [2026-09-04T07:36:05Z] Catherine Manager:
  - Full suite green as the authoritative gate: 4828 passed, 12 skipped, exit 0. This task refactored two client-facing JSON contracts onto shared builders -- wider than per-source --json -- so I verified them directly rather than trusting the tests: captured sq tree --json and sq feature <n> stories --json, stashed the change, captured both again, and diffed. Both byte-identical, with each payload confirmed non-empty on both sides. Sharing a builder is a stronger guarantee than an equality assertion: the two paths are now equal by construction rather than by a test that could rot.
  - Method note for the record: my first attempt at the sub-entity comparison was worthless -- I used the wrong verb and both sides returned the same usage error, which diffs as identical. Two matching errors look exactly like a match. Confirm a payload is real before trusting a diff, the same way a zero-hit grep needs a known positive.
<!-- sq:discussion:end -->
