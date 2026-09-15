---
id: FEAT-903
sequence_id: 903
type: feature
title: 'View source layer: widen to role, playbook, and self kinds'
status: Done
parent: EPIC-897
author: product-owner
priority: urgent
refs:
- MILE-867:targets
- ADR-880:implements
description: resolve_source dispatches on ref/subtree/subentity/role/playbook/self;
  per-source --json in each source's own shape
subentities:
- local_id: US1
  title: ref/subtree/subentity sources survive unchanged under resolve_source
  status: Done
- local_id: US2
  title: role source resolves the merged RoleDef
  status: Done
- local_id: US3
  title: playbook source resolves the type's lane, roster, and spec
  status: Done
- local_id: US4
  title: self source resolves the host item, spec, and squad dir
  status: Done
- local_id: US5
  title: Templates receive each source's native shape, unflattened
  status: Done
- local_id: US6
  title: Per-source --json matches each kind's own existing serializer
  status: Done
created_at: '2026-09-03T09:10:55Z'
updated_at: '2026-09-04T08:59:07Z'
---
<!-- sq:body -->
## Why

The ruled model widens "where a render's data comes from" past item relations. Three sources
that are not relations — `role`, `playbook`, `self` — join `ref`/`subtree`/`subentity`, which
is what lets the bespoke read-time render paths (FEAT-906) collapse onto one mechanism.

## Scope

- `resolve_records` becomes `resolve_source`: a dispatch on `source.kind` over resolvers.
  `ref`, `subtree`, `subentity` survive verbatim — same behaviour, same output shape.
- `role` resolves the merged `RoleDef` (catalog + `.overrides/roles.toml` + item fields).
- `playbook` resolves a type's playbook lane + the live roster + the active spec.
- `self` resolves the host item + the active spec + the squad dir.
- Each new kind's `name` (where it takes one) is validated at spec load against its kind's
  vocabulary, the same way `_check_view_source` validates `ref`/`subtree`/`subentity` today.
- The settled-versus-delivered distinction moves onto `WorkflowSpec` beside
  `first_settled_status`, callable from a template — it is real logic, not a column that dies
  with the grammar it was expressed through (FEAT-904).
- `_badges.py` is reachable as a registered Jinja filter beside `slugify`/`open_marker`/`idnum`.
- Per-source `--json`: each source kind serializes in the shape it already has a serializer
  for — `ref`/`subtree` match `sq tree --json`/`sq list --json`; `subentity` matches the
  per-kind list; `role` emits the resolved definition. No `{fields, group_by, groups}` envelope.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 903 add-story "As a <role>, I want … so that …"`; track with `sq feature 903 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — ref/subtree/subentity sources survive unchanged under resolve_source

<!-- sq:story:US1:body -->
As a maintainer, I want the rename from resolve_records to resolve_source to change nothing about ref/subtree/subentity behaviour, so the existing milestone roll-up and any other today-working source keeps working through the rename.

Acceptance: ref inversion, the subtree walk, and the sub-entity collection read are byte-identical in output to today; only the dispatch's name and the set of kinds it recognizes change.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — role source resolves the merged RoleDef

<!-- sq:story:US2:body -->
As a template author, I want a role source that resolves the same merged RoleDef role_definition_text already computes (catalog + .overrides/roles.toml + item fields), so a role's view can render exactly what today's hardcoded path renders.

Acceptance: source.kind = role resolves to the same object role_definition_text passes into agents/role.md.j2 today; no name is required (role sources read the host item).
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — playbook source resolves the type's lane, roster, and spec

<!-- sq:story:US3:body -->
As a template author, I want a playbook source that resolves a type's playbook lane plus the live roster and active spec, so a per-item-type skill's view can derive what _item_skill_definition_text's eight kwargs derive today.

Acceptance: source.kind = playbook resolves against [items] or the host's own type; the template receives the playbook lane, the live roster, and the spec object, not pre-computed strings.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — self source resolves the host item, spec, and squad dir

<!-- sq:story:US4:body -->
As a template author, I want a self source that resolves the host item plus the active spec and squad dir, so a view can render facts about the document it lives in without a relation to another item.

Acceptance: source.kind = self requires no name; resolves to the host item, active spec, and squad dir.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Templates receive each source's native shape, unflattened

<!-- sq:story:US5:body -->
As a template author, I want the source's real objects (Item/SubEntity/RoleDef/etc.), not flattened cells, so I can write {{ r.id }}, {{ r.status | badge }}, and use Jinja's groupby/sort/selectattr directly against real fields.

Acceptance: no Cell/_RawRecord/ViewRecord passes through resolve_source; badges.py is registered as a Jinja filter beside slugify/open_marker/idnum; the settled-vs-delivered distinction is callable from a template via WorkflowSpec, beside first_settled_status.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Per-source --json matches each kind's own existing serializer

<!-- sq:story:US6:body -->
As a client or scripting consumer, I want sq workflow view <name> <id> --json to emit each source's data in the shape that source already has a serializer for, so I parse one already-known shape instead of a bespoke projection envelope.

Acceptance: ref/subtree --json matches sq tree --json / sq list --json's own shape; subentity --json matches the per-kind list's shape; role --json emits the resolved definition; no {fields, group_by, groups} envelope remains; --raw stays the way to get rendered text, --json answers about data only.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T14:50:56Z] Catherine Manager:
  - Breakdown parked: three consecutive server-side API overload failures killed the tech-lead agent before it wrote anything. No partial state -- no tasks exist. Moved back to Ready rather than left InProgress, since nothing is in flight and an InProgress feature with no tasks misreports the board. Re-dispatch when capacity returns.
- [2026-09-03T15:08:13Z] Olivia Lead:
  - Broke this into two tasks, one per coherent surface: TASK-918 the three new resolvers (role/playbook/self) plus their applicability entries, WorkflowSpec settled/delivered, badges-as-filter, and the render-context plumbing (US1-US5); TASK-919 per-source --json (US6). Both Draft — promotion at dispatch is mine. TASK-919 refs TASK-918 depends-on: it needs the new resolvers to exist before it can dispatch --json to them.
  - One cut I made rather than the briefed default: resolve_records->resolve_source (the rename itself, plus the two spec-load exemptions it forces on _check_views/VIEW_BASE_FIELDS_BY_SOURCE for the fields-less new kinds) sits in TASK-918, not split out — it's mechanically inseparable from the applicability registry it feeds. --json stays its own task because it is a CLI-layer concern with its own reuse targets (sq tree --json, sq role show --json, the per-kind list command) that don't touch the resolver code at all.
  - Both task bodies carry FEAT-905's four lessons as acceptance, not boilerplate: the stranger-test narration sweep (sentence by sentence, plus a post-rewrite grep of removed wording) is acceptance criteria on each task, not an end-of-feature pass; every new test must be falsified (broken, red, restored, green, both directions reported); each task names a concrete agreement-pinning instance (TASK-918: the new playbook applicability predicate vs. _item_skill_definition_text's existing rich/thin lane check must never disagree; TASK-919: ref/subtree --json output must equal sq tree --json's own output for the same query, not merely resemble it); emptiness is tested as a success case per kind in both tasks, not asserted in prose.
  - sq check clean. @manager both ready for dispatch, TASK-918 then TASK-919.
- [2026-09-04T07:58:07Z] Paul Reviewer:
  - Batch review of both tasks landed as REV-920 (addresses FEAT-903). Eleven findings: four high,
    one medium, three low, three info. Recommended verdict on the review: ChangesRequested — F1-F4
    want a ruling before this feature closes; F5-F11 do not need to block.
    
    The four high findings share one root: the three new kinds were registered in
    `_SOURCE_APPLICABILITY` and the tag path picks them up correctly (I verified placement,
    read-time expansion and the `sq check` file scan all work end to end for a new kind), but three
    other consumers were not carried along —
    
    - `_check_item_views`' applicability axis at spec load still covers only `subentity`, so a
      `role`-sourced view attached to `items.task.views` loads clean and then breaks `sq task N
      show` / `--raw` at read time (F3);
    - `build_item_json` calls `resolve_view` unconditionally for attached views, and TASK-918
      taught `resolve_view` to refuse the three new kinds, so attaching any of them makes `sq
      <type> <n> show --json` exit 1 for every item of that type (F2);
    - `_resolve_role_source` bypasses the documented `resolve_role_for_item` seam, so an orphaned
      role item with a `role` view tag raises out of `read_body` — every read surface, with `sq
      check` silent (F4).
    
    F1 is separate: the `playbook` predicate refuses a declared-but-unlaned type, which ADR-880's
    second amendment rules must resolve empty. TASK-918's body asked for both behaviours in the same
    document, so the implementation is not at fault — the specification is, and it wants @architect
    to say which half survives. Two branches are dead as a result (the resolver's `lane=None` and
    `_playbook_json_payload`'s `lane: None` arm).
    
    All four are driven, not inferred — probe transcripts are in each finding body.
    
    @tech-lead F2/F3 are both at the type-attached-views surface and the obvious fix (call
    `_source_incompatibility` from `_check_item_views`) is blocked by the `_views` -> `_workflow`
    import direction, so where that check lives is your call rather than a mechanical edit.
    @architect F1 needs the ADR-vs-task-body conflict ruled.
- [2026-09-04T08:59:05Z] Catherine Manager:
  - Closed. The source grammar now spans role, playbook and self alongside ref, subtree and subentity, each with a type-decidable applicability predicate; --json serves each source in the shape it already had a serialiser for, with ref/subtree byte-equal to sq tree --json; and the three consumers the first pass missed are carried. REV-920 Approved with F1-F8 verified driven; F9-F11 are info and deferred to FEAT-904, which deletes the field grammar and resolve_view outright.
  - Two things worth carrying to FEAT-904 and FEAT-906. The loud half of ADR-880s failure model now contains exactly two things, both above the resolvers: resolve_sources applicability raise for the direct-question caller, and render_views ViewTemplateMissingError plus the engine-translated TemplateError. And _contains_raise parses a functions own body, so for role -- now a one-line delegation -- the structural test would pass unchanged if resolve_role_for_item were made to re-raise; the behavioural guards are what hold it. A future change to that seam gets read against the behavioural tests, not trusted to the structural one.
<!-- sq:discussion:end -->
