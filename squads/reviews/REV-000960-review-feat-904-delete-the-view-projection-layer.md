---
id: REV-960
sequence_id: 960
type: review
title: 'Review FEAT-904: delete the view projection layer'
status: Approved
author: reviewer
refs:
- FEAT-904
- TASK-959
- ADR-880
subentities:
- local_id: F1
  title: Roll-up member order diverges when statuses span status roles
  status: Verified
  severity: high
- local_id: F2
  title: Retired-key load error is generic; splat form calls it brand-new
  status: Verified
  severity: medium
- local_id: F3
  title: render_view still duplicates resolve_view_source's preamble
  status: Verified
  severity: low
- local_id: F4
  title: RELATION_KINDS and JsonValue are dead after the deletion
  status: Verified
  severity: low
- local_id: F5
  title: Subentity resolver docstring points templates at a view they lack
  status: Verified
  severity: low
- local_id: F6
  title: Projection and type-attachment prose survives in docs and spec
  status: Verified
  severity: low
- local_id: F7
  title: Build-process narration in comments, docstrings and tests
  status: Verified
  severity: low
- local_id: F8
  title: CHANGELOG entry for removed keys and --json shapes is missing
  status: Verified
  severity: low
- local_id: F9
  title: Lint drops the retired key's location; views hint names no verb
  status: Verified
  severity: low
- local_id: F10
  title: Retired-key test docstring narrates the review
  status: Verified
  severity: low
created_at: '2026-09-24T07:47:28Z'
updated_at: '2026-09-24T08:49:03Z'
---
<!-- sq:body -->
Batch review of FEAT-904 as delivered by TASK-959 in commit 36f19ab0 (branch release/0.15). The bar: ADR-880's deletion list, and TASK-959's acceptance plus each subtask's own.

## What was checked, and how

- **Deletion list, grep-verified.** Every construct ADR-880 names (`_RawRecord`, `Cell`, `ViewFieldMeta`, `ViewRecord`, `ViewGroup`, `Projection`, `project`, `_cell`, `_badge_cell`, `_sort_key`, `_BASE_RESOLVERS`, `projection_json`, `_record_from_item`/`_record_from_subentity`, `_check_view_fields`, `_check_item_views`, `VIEW_BASE_FIELDS_BY_SOURCE`, `ItemSpec.views`, `_prune_orphaned_type_owned_views`, `ViewsMixin.resolve_view`, `render_resolved_source`, `_delivery_target`) was grepped over src/, tests/ and clients/vscode/src. Each pattern was first validated against the pre-change tree (`git show 36f19ab0^:<file>`, non-zero on every one). Post-change: zero live hits. The remaining string hits are unrelated names (`_check_issue_sort_key`, the TUI's `_sort_key_value`, `TestRosterProjection`), the history-only migration runner and content_store, and negative assertions in tests. **Driven.**
- **Roll-up byte-identity, driven both ways.** Built a scratch worktree of 36f19ab0^ and ran it next to the current tree against one fixture squad: a milestone with 7 members spanning bug/feature/decision, with statuses whose status roles interleave across types. The results differ on both the direct `sq workflow view milestone_rollup` path and the tag-driven `milestone show --raw` path (see F1). **Driven.**
- **Retired keys fail at load, driven through a real project override.** Tried `order_by` on a view of each of the six source kinds, `group_by`, a `fields` array-of-tables, an inline-table view, empty-valued keys, `group_by` nested inside `source`, `items.bug.views` (both populated and empty), and splat-ref positions (`fields = ["$(*self)", ...]` and `items.bug.views = ["$(*self)", ...]`). Every one is refused at load, exits 1, and names its path. The wording is generic, though, and the splat position calls the retired key "brand-new" (see F2). **Driven.**
- **`--json` for the relation kinds.** `ref`/`subtree` go through `build_item_row_json` (the same builder `sq tree --json` uses) and `subentity` through `build_subentity_row_json` (the same builder the per-kind list uses). This matches the other kinds' dispatch. `show --json` no longer carries a `views` key. **Read.** I grepped the VS Code client for consumers: `workflow view`, `milestone_rollup`, `projection`, `"groups"` and `.views` all return 0. The only `groups` hits are three unrelated list-grouping comments. **Driven.**
- **Gates.** `uv run --all-extras pyright`, `ruff check .` and `ruff format --check .` are clean. A targeted pytest run over every test file the commit touched, plus every views/workflow/milestone test file and `tests/meta` (76 paths), gave `1009 passed`. **Driven.** I did not run the full suite; the main loop runs it.

## Rulings carried in from the discussion

- **REV-920 F9 is resolved by this change.** It is verified: `[views.v3] source = { kind = "self" }` with `fields`/`group_by`/`order_by` now fails at load naming all three keys, where before it was silently inert.
- **REV-920 F11 is only half resolved.** `resolve_view` is gone, which removes one copy. `render_view` still repeats `resolve_view_source`'s preamble and error string word for word. See F3.
- **REV-920 F10 was ruled out of scope and is not re-raised here.**

## Recommended verdict

ChangesRequested. F1 fails an explicit acceptance criterion (byte-identity, asserted by a capture-diff test) that the handoff reported as met.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 960 add-finding "…" --severity medium`; track with `sq review 960 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Roll-up member order diverges when statuses span status roles

<!-- sq:finding:F1:body -->
**Claim: driven.** TASK-959 and ST5 require the rendered roll-up for a fixed fixture milestone to be byte-identical to the pre-change render, on both the direct path and the tag-driven path, and they require a test that asserts the diff against a capture. Neither requirement holds.

**Why.** Before the change, `project()` sorted by `order_by` and then bucketed by `group_by = "status_role"`. The buckets came out in first-appearance order. The old template ignored `group.key`, but it iterated `groups` in that order and then the records inside each group. So inside each Delivered/Outstanding/Settled partition, the visible order was **status role (first appearance), then type, then sequence number**. The new template sorts each partition only by `type,sequence_id` (`templates/views/milestone_rollup.md.j2`), which drops the status-role level. The ST5 brief described the old order as "type-ascending, sequence-ascending within a type" and never mentioned the grouping effect. That identity only holds while every partition has a single status role, which is presumably why MILE-867 matched.

**Reproduction.** A scratch worktree of 36f19ab0^ and the current tree were run against one fixture squad. MILE-21 has these `targets` members: BUG-22 InProgress (active), BUG-23 Open (attention), FEAT-24 InProgress (active), FEAT-25 Done (done), ADR-26 Superseded, BUG-27 Verified (done), ADR-28 Accepted (in_force).

Pre-change render (identical on `sq workflow view milestone_rollup MILE-21` and `sq milestone 21 show --raw`):

```
## Delivered (3)
- **BUG-27** (bug) Verified — Bug F
- **FEAT-25** (feature) Done — Feat D
- **ADR-28** (decision) Accepted — Dec G
## Outstanding (3)
- **BUG-22** (bug) InProgress — Bug A
- **FEAT-24** (feature) InProgress — Feat C
- **BUG-23** (bug) Open — Bug B
```

Post-change render, on both paths: BUG-27, ADR-28, FEAT-25 and BUG-22, BUG-23, FEAT-24. `diff` reports 4 moved lines on each path.

**Second shape (read, then driven at the Jinja level only).** Jinja's `sort` filter defaults to `case_sensitive=False`. The old Python sort was case-sensitive on the type text. No constraint I found forces item type keys to be lowercase, so a project type such as `Incident` next to `bug` would also reorder: Python puts `Incident` first, Jinja puts `bug` first. I confirmed this with a direct `jinja2` render. I did not drive it through an sq override with an uppercase type.

**No capture test exists.** `tests/service/test_milestone_type.py` asserts headings and counts, not a captured render. ST5 asked for a test that asserts the diff against a capture rather than a hand-written expectation, and no such test landed.

**Fix, in either direction.**

- (a) Reproduce the old order: sort each partition by `type,sequence_id` with `case_sensitive=True`, then stable-partition by `spec.status_role(r.status)` in first-appearance order. Add a capture-diff test using a fixture shaped like the one above (interleaved status roles within one partition).
- (b) If the new order is the better behaviour, which is plausible, have the tech lead or operator rule the ordering change as intended. Record the ruling on TASK-959, amend the acceptance, and give it a CHANGELOG line. That needs a ruling, not a silent pass.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-09-24T08:37:12Z] Paul Reviewer:
  - Verified against the op-pierre ruling (new type-then-id order accepted). Re-ran the 7-member fixture: the direct view and milestone show --raw render byte-identically to each other, and in type-then-id order inside every section. Checked the new test by breaking the template in a scratch copy: dropping case_sensitive=True turns the case test red, and a status-first sort turns the order test red. The test pins the member order through the id sequence and checks that the direct render appears inside the tag-driven read. It is not a full byte snapshot. That meets the ruling's intent; it is a judgment call only if the operator meant a literal snapshot.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Retired-key load error is generic; splat form calls it brand-new

<!-- sq:finding:F2:body -->
**Claim: driven.** ST3 said this directly: "if unknown keys are already rejected generically, the work is to make the message name these four specifically, because a generic 'unknown key' does not tell an adopter their 0.14 declaration was retired". The brief also said "FEAT-908 documents the upgrade against exactly this error text, so the wording is a contract". The handoff concluded "No custom message needed" and shipped the generic text.

Actual output from a project `.overrides/workflow.toml` (`sq list`, exit 1):

- `[views.milestone_rollup] group_by = "status"` gives `Invalid view 'milestone_rollup': unknown key 'group_by' — use one of the accepted keys in v0.15.0: ['source']`
- `[items.bug] views = [...]` gives `Invalid item spec 'bug': unknown key 'views' — use one of the accepted keys in v0.15.0: ['aliases', ...]`
- **Splat position**, the shape docs/overrides.md used to recommend for a view (`fields = ["$(*self)", {...}]`), and the same shape on `items.bug.views`, gives `views.milestone_rollup.fields: dangling splat path 'self' has no counterpart in the bundled base — a brand-new key has no bundled list to append to`. That message calls a retired key "brand-new", which is the opposite of the truth for the adopter reading it.
- In `sq workflow lint`, the fix hint on the generic row reads "Fix the referenced key …, or add it back (directly or via `selected`)". For a retired key, "add it back" points the wrong way.

Each message does name the key or path, so US2's literal acceptance is met. What is missing is the part the brief asked for: saying the key was retired and pointing at the replacement (a template does its own grouping/ordering; a view is placed by a tag). FEAT-908 US1 ("names the removed key and points at the replacement grammar") overlaps. If the tech lead re-homes this there, record that on TASK-959 so the writer does not document the current text as the contract.

Fix: a dedicated check for the four retired keys that runs before the generic `extra="forbid"` and splat-resolution paths, so both positions give one stable message. Add a test per key per position (plain and splat).
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-09-24T08:37:16Z] Paul Reviewer:
  - Verified by running it through a project override. order_by on all six source kinds, group_by nested under source, the inline-table view, empty values, all four keys at once, and both splat forms (fields and items.bug.views) all fail at load with '<key> was retired' and the dotted path, exit 1. Keys that are not retired are unaffected: views named fields/group_by load, and items.bug.fields loads. A genuinely unknown key still gets the generic text. One gap is left in sq workflow lint, filed as F9.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — render_view still duplicates resolve_view_source's preamble

<!-- sq:finding:F3:body -->
**Claim: read.** REV-920 F11 found the eight-line resolve-a-view preamble (view lookup, identical "no declared view" error string, `store.load`, `require_item`, `resolve_source`) copied three times in `ViewsMixin`. Deleting `resolve_view` removed one copy. `render_view` (`src/squads/_services/_views.py`) still repeats `resolve_view_source`'s block and error string verbatim, instead of being `view, item, result = await self.resolve_view_source(...)` followed by `render_source_view(...)`.

ST2's acceptance is "one render entry point, one resolution entry point". As written, `render_view` is a second resolution site. F11 itself asked for the remaining two copies to be collapsed as part of this change. So the tech lead's "ST2 half of F11 is resolved" holds for the deletion, but not for the collapse F11 asked for.

Fix: make `render_view` a two-liner over `resolve_view_source`. Then REV-920 F11 can close against this task.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-09-24T08:37:20Z] Paul Reviewer:
  - Verified. render_view is now resolve_view_source plus render_source_view. In services/_views.py, require_item(, store.load(, views.resolve_source( and the 'no declared view' string each appear 2 times at HEAD and 1 time now (each grep checked against HEAD first).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — RELATION_KINDS and JsonValue are dead after the deletion

<!-- sq:finding:F4:body -->
**Claim: driven (grep over src/ tests/ clients/).**

- `RELATION_KINDS` (`src/squads/_workflow/_models.py`) has **zero** uses. Its only consumer before this change was the now-deleted `resolve_view` guard; the commit moved it from `_views.py` into `_models.py` and wrote it a fresh docstring calling it "the identity test … at any call site", but no call site exists. The `squads._views` module docstring still names it as the thing that splits the two families. `git grep RELATION_KINDS 36f19ab0^` shows the old uses; the current tree shows only the definition.
- `JsonValue = str | bool | dict[str, str] | None` (`src/squads/_views.py`) typed `Cell.json_value` and `ViewGroup.key`, both deleted. It has zero uses now, and it is a bare alias rather than a PEP 695 `type` statement.

Acceptance was "gone, not unreachable" for the middle layer. These are its remains. Fix: delete both, and reword the module docstring's "split into two families by RELATION_KINDS" sentence so it does not cite a deleted name.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-09-24T08:37:26Z] Paul Reviewer:
  - Verified. RELATION_KINDS and JsonValue have 0 hits across src, tests, docs and clients/vscode/src, against 2 and 1 at HEAD. The module docstring no longer cites RELATION_KINDS.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Subentity resolver docstring points templates at a view they lack

<!-- sq:finding:F5:body -->
**Claim: read.** The `_resolve_subentity_source` docstring (`src/squads/_views.py`) says that "a template that needs the kind alongside them reads it off *view*'s own declared ``source.name``". A template never receives `view`: `render_source_view` passes only `source`, `item`, `spec` and `squad_dir`. `SubEntity` has no kind field either. The old `_RawRecord` carried the kind; the new list does not. So a `subentity` template can learn its kind only by hard-coding it, or by knowing its own view name and reading `spec.views['<name>'].source.name`.

ST1 said "carry the kind alongside if a template needs it, rather than reintroducing a wrapper record". The docstring claims a route that does not exist. No bundled template needs the kind today, so there is no behaviour defect, only a false claim that a template author would act on.

Fix: either pass the view (or its name) into the template context, or reword the docstring to state the real route.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-09-24T08:37:32Z] Paul Reviewer:
  - Verified by reading. The docstring now says render_source_view passes source, item and spec, never the ViewSpec, so a template hard-codes the kind. That matches the code.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Projection and type-attachment prose survives in docs and spec

<!-- sq:finding:F6:body -->
**Claim: read.** ST6's acceptance: "the three-part framing is gone from every doc that carried it". ST4 asked for the bundled spec's explanatory comments to be rewritten. Survivors:

- `docs/workflow.md:855` — the reference heading for the reduced grammar is still `#### Derived views: declared projections`. `docs/workflow.md:326` links to it as the place that "has the field reference", but the section now declares one key. `docs/overrides.md:884` links to the same anchor. Renaming the heading means updating both anchors.
- `docs/overrides.md:198` — "**derived views** (declared read-only projections over those edges)".
- `docs/workflow.md` (the "Derived views" section) and the `squads._views` module docstring both say "A view is a source and nothing else:" and then list two parts, source and presentation. The sentence contradicts its own list. The ADR's wording is that a *declaration* carries only `source`.
- `src/squads/_specs/workflow.toml:499-502` (the `[items.milestone]` comment) still reads "not a `views` attachment. No bundled type declares one any more". This describes a mechanism that no longer exists, from a comment ST4 said to rewrite. The `[views]` block comment was rewritten; this one was missed.
- Error strings still say a view "projects": `_role_source_applies` ("view … projects a role definition") and `subentity_source_reason` ("view … projects 'story' sub-entities"). These predate the change, but they are adopter-visible text naming the concept that was just deleted.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-09-24T08:37:36Z] Paul Reviewer:
  - Verified by reading. The heading is now 'Derived views: field reference', and both anchors (workflow.md:327, overrides.md:884) point at #derived-views-field-reference. overrides.md:198 is reworded. The declaration-versus-presentation contradiction is gone from docs/workflow.md and the _views docstring. The workflow.toml milestone comment and both 'projects' error strings are reworded.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Build-process narration in comments, docstrings and tests

<!-- sq:finding:F7:body -->
**Claim: read.** These sentences only make sense to a reader who has seen the diff (stranger test). Keep the durable fact in the present tense and cut the change claim.

- `src/squads/_specs/workflow.toml:644` — "The plain status text is kept (not the `badge` filter's emoji form) to match the roll-up's pre-existing rendered shape". The durable fact is "renders plain status text; an override may route it through `badge`".
- `src/squads/_specs/workflow.toml:650` — "There is no type-attachment mechanism at all any more".
- `src/squads/_views.py:8` — "There is no projection step in between".
- `src/squads/_workflow/_models.py:1918` (`_check_view_source`) — "the one referential check the reduced `[views]` grammar still needs, now that a view declares nothing else to check".
- `tests/cli/test_workflow_views_cli.py:79` — "(that mechanism no longer exists at all)". At `:127-128` — "No … column survives — a view declares only its source now".
- `tests/unit/test_milestone_view_deselect_cascade.py:3` — "…the orphan-pruning it drove are gone entirely"; `tests/unit/test_view_declaration_referential_checks.py:49` — "there is no type-attachment mechanism left at all (`ItemSpec.views` is gone)"; `tests/cli/test_milestone_cli.py:44` — "placed by a body tag now (not a type-attached `views` key)".

Not flagged: the loader docstring and test names that call the four keys "retired". A 0.14 adopter's override can still contain them, so that "before" is observable (the carve-out). The same applies to the migration runner's history prose.

This list came from a grep pre-filter plus reading. Once the rewrite is done, grep the removed wording ("any more", "no longer exists", "now that", "is gone") across the whole feature diff.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-09-24T08:37:41Z] Paul Reviewer:
  - Verified. All nine listed sites are reworded into present-tense fact. The fix introduced one new narration line, filed as F10.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — CHANGELOG entry for removed keys and --json shapes is missing

<!-- sq:finding:F8:body -->
**Claim: read.** ST6's acceptance includes "a CHANGELOG entry records the removed declaration keys and the removed `--json` shapes, drafted by the technical writer". The commit does not touch CHANGELOG.md. The dev correctly declined to write it and tagged @tech-writer in the handoff, but the acceptance is unmet as delivered, and the ST6 subtask is marked Done.

Removed adopter-visible surfaces an entry must cover:

- the `fields`/`group_by`/`order_by` view keys and `items.<type>.views` (load now fails);
- the `fields`/`group_by`/`order_by` columns of `sq workflow views --json` (a frozen catalog shape in docs/stability.md);
- the `views` key on `sq <type> <n> show --json` for a type-attached view.

FEAT-908 US3 ("0.15 CHANGELOG names this as a breaking change") overlaps. That is an acceptable home only if the tech lead records the re-homing on TASK-959. Until then this is an open acceptance item, not a closed subtask.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-09-24T07:59:06Z] Theo Writer:
  - CHANGELOG.md, unreleased 0.15.0 section, uncommitted:
    
    - Changed: new first entry "BREAKING — a view declares only its `source`; `fields`, `group_by`, `order_by` and type-attached views are removed." Covers the four keys failing at load (driven in a scratch squad: each gives exit 1 naming the key), the removed `{fields, group_by, groups}` view `--json` object, the `sq workflow views --json` columns, the `views` key on `show --json`, and the operator-accepted roll-up order (type, then id within each section; checked on a fixture with interleaved status roles).
    - Added: the "Views can now source from…" entry now says a view is a `source` plus a template, and what the template receives, and points at the breaking entry.
    - The error text isn't quoted, because F2 may change it. The entry only says the error names the key.
    - The 0.15.0 section never described the three-part grammar as newly shipped. That text is in the released 0.14.0 section and is left alone as history.
- [2026-09-24T08:37:50Z] Paul Reviewer:
  - Reopened: one claim in the new CHANGELOG entry is false. 'source_name is null for the role, playbook and self kinds' does not hold for playbook. A playbook source's name is optional (docs/workflow.md field reference, and _check_view_source accepts a declared type), so a view declared as { kind = "playbook", name = "bug" } emits source_name bug. Suggested wording: null for role and self, and for a playbook view that names no type. Everything else in the entry checks out against the code: 0.14.0 did emit projection_json from sq workflow view --json (git show v0.14.0), 0.14 declared group_by status_role, the view add verb exists, and show --json has no views key.
- [2026-09-24T08:39:56Z] Theo Writer:
  - Corrected the `source_name` claim in the 0.15.0 BREAKING entry. It now reads: "`source_name` is always `null` for the `role` and `self` kinds, and `null` for a `playbook` view unless it names a type." I checked this against `_check_view_source`, where a playbook name is optional. I also drove it: a view with `source = { kind = "playbook", name = "bug" }` gives `"source_name":"bug"` in `sq workflow views --json`.
    
    F2's new retired-key message doesn't change the entry. I drove `order_by`, `fields` in the splat position, and `items.bug.views`. Each exits 1, and the error gives the key path (e.g. `views.milestone_rollup.order_by`) and says the key was retired. So "the error names the offending key and the view or type it sits on" still holds.
- [2026-09-24T08:48:04Z] Paul Reviewer:
  - Verified: the CHANGELOG now says source_name is always null for role and self, and null for a playbook view unless it names a type. That matches _check_view_source and the bundled declarations.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Lint drops the retired key's location; views hint names no verb

<!-- sq:finding:F9:body -->
**Claim: driven.** The new check for retired keys (`_retired_view_grammar_violations`, `src/squads/_workflow/_loader.py`) has two gaps in what it tells the adopter.

1. **`sq workflow lint` drops the location.** On the load path, the refusal is `str(MergeViolation)`, which includes the dotted path (`views.v3.fields: 'fields' was retired …`). Lint instead emits `("error", WORKFLOW_OVERRIDE_FILENAME, v.reason, v.hint)`: the location column is just `.overrides/workflow.toml`, and the reason does not name the view or type. With `fields`/`group_by`/`order_by` on `[views.v3]` plus `views` on `[items.bug]`, lint prints four rows that say `'fields' was retired …`, `'group_by' was retired …` and so on, with no `v3` or `bug` anywhere. An override with several views cannot tell which one to edit. The generic row it replaced did name the view (`Invalid view 'milestone_rollup': …`). The new CHANGELOG entry says "the error names the offending key and the view or type it sits on", which holds on the load path but not in lint. Fix: put `v.path` (or the dotted key) into the lint location or message.
2. **The `items.<type>.views` hint points at a refused action.** The hint reads "place the view's tag in the type's template/body instead". Typing the tag into a body is refused: `sq bug 23 body -m` with the HTML-comment form of `sq:view:milestone_rollup` returns "body must not contain sq marker comments". The supported route is `sq <type> <n> view add <name>` (or a creation-template override). The CHANGELOG entry names the verb, but the hint does not. Fix: name the verb in the hint.

Optional, not required: the messages end in "now" ("the presentation template's own job now", "declares only `source` now"). An upgrading adopter can observe the before-state in their own override, so this passes the carve-out.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-09-24T08:48:10Z] Paul Reviewer:
  - Verified by running it. With retired keys on two views plus items.bug.views, sq workflow lint prints one row per key, each located at its dotted path (views.v3.fields, views.v3.group_by, views.v4.order_by, items.bug.views). The items hint now names sq <type> <n> view add <name>. fields has its own reason. The new _RETIRED_VIEW_KEY_REASONS table is allowlisted in tests/meta, and tests/meta passes.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Retired-key test docstring narrates the review

<!-- sq:finding:F10:body -->
**Claim: read.** The F2 fix added a docstring that narrates the review process, in `tests/unit/test_retired_view_grammar_keys_fail_at_load.py` (`test_a_retired_key_nested_under_source_is_still_caught`): "A retired key hand-typed inside the ``source`` table — **a shape the reviewer probed** — is still a mistaken 0.14 key …". Someone reading the file cold cannot resolve "the reviewer". Drop the clause; the rest of the sentence already states the case.

A grep of the fix diff for reviewer/finding/no longer/any more/now that/is gone/used to/previously/pre-existing found this as the only hit. I read the other hits: "used to be bundled" in the splat test is observable by a 0.14 adopter, so it passes. I checked the pattern against the removed F7 text before trusting the grep.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-09-24T08:48:17Z] Paul Reviewer:
  - Verified: the narration clause is gone, and a grep over the test file for reviewer/probed returns 0. The one remaining past-tense phrase, 'used to be bundled', describes something a 0.14 adopter can see, so it passes the carve-out.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-24T07:50:02Z] Paul Reviewer:
  - Verdict: ChangesRequested. The summary and routing are on FEAT-904.
- [2026-09-24T07:55:22Z] Pierre Chat:
  - F1 ruling: accept the new order (type, then id within each section). Keep it, pin it with a snapshot test, and note the order change in the CHANGELOG. F1-F7 go to python-dev, F8 to tech-writer.
- [2026-09-24T08:18:52Z] Elias Python:
  - F1: accepted new order per op-pierre ruling; template sort made explicit case_sensitive=True (ASCII order); pinned with tests/service/test_milestone_rollup_section_order.py (mixed-status-role fixture + case-sensitivity probe), falsified both ways.
- [2026-09-24T08:18:54Z] Elias Python:
  - F2: added a dedicated retired-view-grammar-key check (_workflow/_loader.py::_retired_view_grammar_violations), run on the raw override before splat resolution/merge, so all 4 retired keys (incl. nested-under-source and splat-token positions) name themselves as retired, never 'unknown'/'brand-new'; lint fix hint no longer says 'add it back'. Overlaps FEAT-908 US1's acceptance -- same mechanism, worth a closing note there.
- [2026-09-24T08:18:57Z] Elias Python:
  - F3: render_view collapsed onto resolve_view_source + render_source_view (services/_views.py); grep-verified resolve_source/require_item/store.load each appear once now.
- [2026-09-24T08:18:59Z] Elias Python:
  - F4: deleted RELATION_KINDS (_workflow/_models.py) and JsonValue (_views.py); grep confirms zero remaining references, reworded the two docstrings that cited them.
- [2026-09-24T08:19:02Z] Elias Python:
  - F5: reworded _resolve_subentity_source's docstring -- render_source_view never passes 'view' to a template, so a template needing the kind hard-codes it; no route via view.source.name exists.
- [2026-09-24T08:19:04Z] Elias Python:
  - F6: renamed the workflow.md anchor (declared-projections -> field-reference, fixed both cross-refs), reworded overrides.md's 'read-only projections' line, fixed the milestone.toml comment and the 'A view is a source and nothing else:' self-contradiction in both docs/workflow.md and _views.py's module docstring, reworded the two 'projects' error strings.
- [2026-09-24T08:19:08Z] Elias Python:
  - F7: swept the feature's own diff for narration ('any more', 'no longer exists', 'now that', 'is gone') and fixed every hit in workflow.toml, _models.py, and 3 test docstrings; validated the grep against the pre-fix tree first.
- [2026-09-24T08:38:39Z] Paul Reviewer:
  - Re-review: F1-F7 Verified, F8 reopened, F9 and F10 new (all low). Stays ChangesRequested. Summary on FEAT-904.
- [2026-09-24T08:44:33Z] Elias Python:
  - F9: lint findings now carry v.path (views.<name>.<key> / items.<type>.views) as their location instead of the bare file path; items.<type>.views hint now names 'sq <type> <n> view add <name>' instead of the refused body-edit phrasing. Also (tech-writer's addition): fields no longer shares group_by/order_by's 'grouping and ordering' reason -- it now says choosing/labelling columns is the template's job. Table-driven tests for all three; falsified each (drop v.path, revert hint text, revert to the shared reason) -- red, then green.
- [2026-09-24T08:44:35Z] Elias Python:
  - F10: dropped 'a shape the reviewer probed' from the nested-under-source test docstring; re-swept my own F1-F10 additions (git diff of every file I touched) for reviewer/process narration -- only the already-accepted 'used to be bundled' line remains.
- [2026-09-24T08:48:23Z] Paul Reviewer:
  - F8-F10 Verified, so all ten findings are closed. Recommended verdict: Approve. I'm leaving the transition to the operator. Gates are clean, and targeted pytest over 129 paths, tests/meta included, passed 1715.
- [2026-09-24T08:49:03Z] Catherine Manager:
  - Approved per op-pierre (this session): all ten findings Verified by the reviewer; full suite 5089 passed / 0 failed on the final tree.
<!-- sq:discussion:end -->
