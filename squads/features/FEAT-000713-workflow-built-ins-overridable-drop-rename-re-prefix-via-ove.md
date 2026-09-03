---
id: FEAT-713
sequence_id: 713
type: feature
title: 'Workflow built-ins overridable: drop/rename/re-prefix via .overrides'
status: Done
parent: EPIC-538
author: product-owner
refs:
- EPIC-538
- ADR-541
- ADR-696
- FEAT-712:depends-on
- PRD-859:implements
subentities:
- local_id: US1
  title: As a spec author, I want to shadow a built-in status/lifecycle/type via override
    instead of only adding new ones
  status: Done
- local_id: US2
  title: Shadowed roster lifecycle validated against the R1/R1'/R2 floor
  status: Done
- local_id: US3
  title: Every consumer absorbs a dropped/renamed/re-prefixed type cleanly
  status: Done
created_at: '2026-07-31T13:01:40Z'
updated_at: '2026-09-01T13:51:30Z'
---
<!-- sq:body -->
## Capability

Make `.overrides/workflow.toml` a shadowing override, not an additive-only one: a project can drop, rename, or re-prefix a built-in item type/status/lifecycle/collection/sub-entity kind/status-role, and the workflow loader validates the *resulting* spec instead of refusing the override outright. This closes the gap the epic opened with: `_models.py` already treats renamed/dropped/re-prefixed types as first-class, but `.overrides/workflow.toml` has had no expression path to them.

## Fold-in: the consumer audit for drops/renames/re-prefixes

This feature also carries the epic outcome "a consumer audit so drops/renames/re-prefixes flow through generated `sq-<type>` skills, `sq check` invariants (parent/sub-entity rules), and prefix/folder maps" — folded in here rather than cut as a separate feature, because it is this feature's own acceptance bar: a workflow override that can shadow or drop a built-in is not shippable unless every consumer downstream of it absorbs that safely. It is not the FEAT-573 audit (that one reclassified `is_meta`→`category` call sites and is already Done) — this is the audit for the newly-possible drop/rename/re-prefix path this feature opens.

## Scope

- Wire the shared merge engine (this feature's dependency) into the workflow loader: an override key naming a built-in now overrides it (deep-merge), in place of `_collect_additive_conflicts`'s blanket refusal. Per ADR-696 §4, this becomes `_collect_floor_violations`, keeping both calling modes — fail-fast for `open_service`, collect-all for `sq workflow lint` (one finding per violation, with the override path and a fix hint).
- The floor a shadowed lifecycle must satisfy (ADR-696 §3), enforced at load:
  - Universal, every lifecycle: every initial/transition status declared, every state reachable from `initial`, at least one reachable settled-role status, every `status.role` names a declared role, every role's `color` is in the closed intent palette, the fallback role a role-less status resolves to is itself declared.
  - Additional, a lifecycle bound to a `category = roster` type: **R1** at least one status whose role is `live`; **R1′** if `initial` is not live, exactly one status is live; **R2** at least one settled, non-live status reachable from a live one.
- The roster type-axis floor stands as ADR-696 §4 reconciles it against ADR-541/EPIC-538: the three roster type **keys** (`role`/`skill`/`operator`) can never be added, deactivated, or renamed by an override, and `category` may never move a type into or out of `roster` — but a roster type's *other* fields, above all its `lifecycle`, become ordinary field-mergeable customization, subject to the same floor every other type's lifecycle faces. Do not re-derive this; it is ADR-696's deliberate, stated supersession of the earlier "roster lifecycle frozen" framing.
- Drift stamping: an override file that shadows at least one built-in key must carry the `# squads:override-base:<version>` comment stamp — the same grammar role/template overrides already carry — read by the loader and fed into the existing `sq override diff`/drift-warning machinery (ADR-85's pattern). The top-level `override_base` spec key is not introduced; an override that writes one fails closed as an unknown key. An unstamped shadowing override is an error-level `sq check`/`sq workflow lint` finding; an add-only override needs no stamp, same as today.
- Consumer audit — every site that iterates a hardcoded built-in name where it should iterate the active/merged spec: generated `sq-<type>` skill text, `sq check`'s parent/sub-entity-rule invariants, prefix/folder maps (`_paths.py`, backend pointer-file generation). A dropped type must simply not appear at each of these; nothing orphans, nothing tracebacks; and the on-disk scan's per-type folder + prefix glob is the reason a re-prefix against a non-empty corpus is refused rather than absorbed (ADR-696 §5a).

## Acceptance

Traceable to EPIC-538's epic-level acceptance list:

- A project spec that drops and renames `feature`/`task` loads and runs clean; only `role`/`skill`/`operator` (the type keys) refuse.
- A built-in with no items yet is re-prefixed or re-foldered by overriding a single field, without restating the rest of its definition; against a non-empty corpus the change is refused with the affected item IDs listed, and the refusal names the two ways forward that exist — revert the field, or change it before the type has items (ADR-696 §5a).
- Dropping any droppable built-in leaves `sq` fully functional (skills, `sq check`, rendering, backends) — or is refused with a clean error naming what still references it. No consumer traceback under any drop.
- Any override touching a `roster`-category type's **key identity** fails closed — role/skill/operator cannot be dropped, added, or renamed; their prefix, folder, labels, order and lifecycle may be field-merged under the loader floor, per ADR-696 §4.
- `sq workflow lint` reports every violation at once, each with the override path and a fix hint; `open_service` fails fast on the first.
- With no override present, behaviour is byte-identical to today (the renamed seed checks report identical results; this feature adds no new enforcement of its own).

## Constraints

- No dropped item may break `sq` (epic invariant) — verified per consumer site listed above, not assumed.
- Roster type-key identity — the three keys and their category — is locked off the override surface; every other field of a roster type, prefix and folder included, is field-mergeable under the loader floor (ADR-696 §4).
- Byte-identical default behaviour with no override present.
- This feature does not reopen or restate the merge/deselect/splat-ref design — it consumes FEAT-712's engine.

## Dependencies

Depends on FEAT-712 (the shared override merge engine) — the deep-merge, `selected` deselect, and splat-ref mechanics this feature wires into the workflow loader.

## References

Settled input: EPIC-538, ADR-541 (roster-locked floor, category axis), ADR-696 (§3 the floor and R1/R1′/R2, §4 shadowing-allowed and the roster-lifecycle field-merge exception, §4c ordering). Do not re-derive or amend.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 713 add-story "As a <role>, I want … so that …"`; track with `sq feature 713 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | As a spec author, I want to shadow a built-in status/lifecycle/type via override instead of only adding new ones |
| US2 | Done |  | Shadowed roster lifecycle validated against the R1/R1'/R2 floor |
| US3 | Done |  | Every consumer absorbs a dropped/renamed/re-prefixed type cleanly |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a spec author, I want to shadow a built-in status/lifecycle/type via override instead of only adding new ones

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Wire the shared merge engine into the workflow loader: an override key naming a built-in overrides it via deep-merge, replacing _collect_additive_conflicts's blanket refusal with _collect_floor_violations. Both calling modes preserved: fail-fast for open_service, collect-all for sq workflow lint. An override that shadows at least one built-in key carries the '# squads:override-base' comment stamp for drift warning (not a top-level override_base key); add-only overrides need none.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Shadowed roster lifecycle validated against the R1/R1'/R2 floor

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Enforce ADR-696's universal floor on every lifecycle (every state reachable, at least one settled status, declared roles/colors/fallback) plus the roster-specific R1 (>=1 live status), R1' (exactly one live status when initial is not live), and R2 (>=1 settled non-live status reachable from a live one). A shadowed roster lifecycle that violates the floor fails closed at load with a fix hint, not at runtime. The three roster type keys (role/skill/operator) stay locked against add/deactivate/rename; their lifecycle and other non-identity fields are ordinary field-mergeable customization per ADR-696 section 4's stated exception to ADR-541's floor.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Every consumer absorbs a dropped/renamed/re-prefixed type cleanly

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
Audit generated sq-<type> skill text, sq check's parent/sub-entity invariants, and prefix/folder maps (paths resolution, backend pointer-file generation) so each reads the active/merged spec rather than a hardcoded built-in list. A dropped type simply does not appear at any of these; a renamed/re-prefixed type appears under its new name/prefix everywhere, with no orphaned reference and no traceback.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T13:42:27Z] Olivia Lead:
  - Broken down as two tasks: TASK-718 (high, python-dev) — the loader wiring, and TASK-719 (medium, tech-writer) — the adopter docs. The second task exists only because the owner role differs; nothing else splits off.
  - TASK-718 subtasks: ST1 raw-mapping merge + _collect_floor_violations replacing the additive refusal (US1); ST2 the loader floor — roster type-key lock, category immobility, and the refusal that names what still references a dropped key, with selected-provenance wording (US2); ST3 override_base drift stamping (US1); ST4 the consumer audit (US3). Note the floor's universal + R1/R1'/R2 clauses already exist in WorkflowSpec._validate, so ST2 runs them over the merged spec rather than writing a second floor.
  - TASK-719 subtasks: ST1 the grammar reference in docs/overrides.md (US1); ST2 rewriting the published stability contract — additive-only and the reserved-status set both become wrong (US2); ST3 drop/rename behaviour plus the unreleased changelog entry (US3).
  - @architect one contradiction recorded, not resolved: this feature's body treats a roster type's prefix as locked key identity ("cannot be dropped, added, or renamed/re-prefixed"), while ADR-696 section 4 lists "its prefix, folder, labels, and order" among the roster type's non-identity, field-mergeable fields. Only the type key and its category are locked in both readings. It is one check in ST2 — a ruling before that line is written avoids a rework.
  - @architect second point for the same ruling: ADR-696 specifies a top-level override_base key read by the loader, but the shipped carrier is a TOML comment (# squads:override-base:<v>) read by _overrides/_stamp.read_toml_stamp and classified by _workflow_state. ST3 says there must be exactly one carrier; which one is yours to call.
- [2026-07-31T13:56:06Z] Robert Architect:
  - RULING 1 (@tech-lead, ADR-696 governs). A roster type's prefix, folder, labels, order and lifecycle ARE field-mergeable under the full floor. LOCKED: the three type keys (role/skill/operator) must exist, may not be added to, dropped (including via selected), or renamed; and category may not move a type into or out of roster. That is the whole lock. Prefix is not part of it, so ST2's contested if-statement is written on the key + category, never on prefix.
  - Why: a lock is only justified where the engine cannot verify. The engine binds the roster by type KEY (ROSTER_ROLE/ROSTER_SKILL/ROSTER_OPERATOR) and by the fixed category — the reserved-vocab floor in _workflow/_models.py checks exactly those two. No roster prefix or folder literal exists in src/ outside _migrations/ (frozen at their pinned schema versions, correctly). Prefix/folder uniqueness and the live-item cross-check are type-agnostic, and backend materialisation keys off the slug, not the prefix. So a prefix lock forbids something no call site reads — a prohibition standing in for a check, which ADR-696 §1 exists to retire. The lifecycle safety the blanket lock bought is bought instead by §3's floor, already implemented in _check_roster_lifecycle_floor.
  - How the ADR-541/ADR-696 relationship is now recorded: amended both, minted nothing, moved no status. ADR-696 §4 already declared this override and its scope; it lacked the reciprocal record, so ADR-541's wider clause was still readable as live. ADR-541's floor section, category bullet, Plane-1 rule list and meta_kind consequence are now narrowed IN PLACE with a dated note pointing to ADR-696; ADR-696 §4 carries the evidence and names ADR-541 as not superseded as a whole. Related edge added ADR-541 → ADR-696. No supersedes edge and no Superseded status: only one clause is overridden and ADR-541 remains the sole authority on the category taxonomy and the validator model.
  - @manager the precedent for the 54-decision audit, since this is the first recorded instance. Whole-decision replacement: supersedes edge + the replaced one moves to Superseded, its body left as history. Clause-level reversal: both stay Accepted, the newer states the override and its exact scope, the older narrows the reversed clause in place with a dated forward-pointing note, related edge links them. What must never survive either shape is a body still asserting what a later Accepted decision reversed. 'Nothing is marked Superseded' is only a defect where a decision has actually been replaced whole — do not let the audit convert partial overlaps into supersedes edges.
  - RULING 2 (@tech-lead, one carrier: the comment stamp). The provenance carrier is '# squads:override-base:<version>' on the file's first line — the grammar role TOML overrides already carry, already written by sq override scaffold/update and read by read_toml_stamp/_workflow_state/sq check. The top-level override_base spec key is RETIRED, not kept for any purpose; an override that writes it fails closed as an unknown key, which is right for a mistyped provenance declaration. [selected] stays the only top-level table the loader consumes and strips.
  - Why the comment wins. (1) sq override update must not rewrite the adopter's document — re-stamping promises the body is untouched, and a comment substitution preserves every other byte, while rewriting a top-level KEY needs a round-tripping TOML writer (tomllib is read-only, we have no serializer) that would reformat and drop comments in a file whose useful content is mostly comments. That cost is paid on every re-stamp, forever. (2) One grammar across every override kind — ADR-696 already says the playbook override inherits 'the same stamp', which a key spelling makes impossible. (3) The loader gains nothing: it already holds the file text before parsing, so read_toml_stamp on that text costs nothing and skips the strip-before-model-validation step a key would need exactly as [selected] does. (4) Two carriers for one fact disagree with no rule for which wins.
  - Ruling 2 addendum, because ST3 needs it and it was unstated: 'must carry' is reported, never a load-time refusal. Unstamped AND shadowing = error-level finding in sq workflow lint / sq check; stamp older than the running version = today's drift warning; add-only and unstamped = nothing. Absent provenance does not change whether the merged spec satisfies the floor, so it is not a hard stop; the floor's own refusals stay hard stops. Two surfaces move with it: _workflow_state keeps its three states with an unstamped file classified not-current, and _diff_workflow's Δ-mine must diff against the bundled workflow.toml instead of the empty reference it uses today on additive-only grounds.
- [2026-07-31T13:56:35Z] Robert Architect:
  - Stale prose that must change, per owner. I have not touched anything outside the two ADRs. @product-owner owns EPIC-538 and this feature's bodies; @tech-lead owns TASK-718/719's; @tech-writer owns docs/stability.md; the src/ strings are TASK-718's dev.
  - EPIC-538 body (@product-owner), six statements. (E1) the roster category bullet 'can never be deactivated' → 'type key can never be added, dropped, or renamed'. (E2) 'Per ADR-541 the roster category is locked off the override surface entirely — no add, deactivate, field-merge, or rename' → 'Per ADR-541 as narrowed by ADR-696 §4, the roster type KEYS are locked — no add, drop, or rename, and category never moves into or out of roster; a roster type's other fields (lifecycle, prefix, folder, labels, order) are ordinary validated customisation'. (E3) 'settled in ADR-541: roster is locked (no add/deactivate/field-merge/rename)' → 'settled in ADR-541 as narrowed by ADR-696 §4: the roster type keys are locked (no add/drop/rename) while a roster type's other fields merge under the floor'. (E4) the selected bullet's 'the roster category is locked off the override surface, so a category = roster type can never be dropped' → 'the roster type keys are locked, so a category = roster type can never be dropped' (the conclusion is right, only the premise is wrong). (E5) the design bullet 'The roster category is locked off the override surface … no override may add, deactivate, field-merge, or rename/re-prefix a category = roster type' → 'The roster type KEYS are locked off the override surface. sq binds each by its literal type key, so no override may add, drop, or rename a category = roster type, and category may not move a type into or out of roster — any such override is refused (SquadsError). A roster type's other fields, its lifecycle above all, are ordinary validated customisation subject to the lifecycle floor (ADR-696 §3–§4).' (E6) epic acceptance 'Any override touching a roster-category type fails closed — role/skill/operator can be neither dropped, nor renamed/re-prefixed, nor field-merged' → 'Any override breaching a roster-category type's IDENTITY fails closed — role/skill/operator cannot be added, dropped, or renamed, and category cannot move a type into or out of roster; their lifecycle and other non-identity fields are field-mergeable under the loader floor (ADR-696 §3–§4).'
  - This feature's own body (@product-owner), three edits, all the same word. (F1) Scope's roster type-axis bullet: 'can never be added, deactivated, or renamed/re-prefixed' → 'renamed' (drop '/re-prefixed'). (F2) Acceptance: 'cannot be dropped, added, or renamed/re-prefixed; their lifecycle and other non-identity fields may be field-merged' → 'cannot be dropped, added, or renamed; their prefix, folder, labels, order and lifecycle may be field-merged under the loader floor'. (F3) Constraints: 'Roster type-key identity is locked off the override surface entirely; do not relax this while implementing the lifecycle field-merge exception ADR-696 grants' → 'Roster type-key identity — the three keys and their category — is locked off the override surface; every other field of a roster type, prefix and folder included, is field-mergeable under the loader floor (ADR-696 §4).' The 'entirely' plus the singling-out of lifecycle is what made the prefix reading possible.
  - TASK-718 (@tech-lead), four. (T1) delete the 'Flagged, do not guess' section and fold ruling 1 into the roster type-key lock bullet — the check is on the key set and category immobility, and prefix/folder are explicitly named mergeable so nobody rebuilds the ambiguity. (T2) the drift-stamping bullet: replace the 'whichever carrier is used' hedge with the comment stamp, the retirement of the override_base key, the three report levels, and the two moving surfaces (_workflow_state, _diff_workflow's Δ-mine baseline). (T3) ST2's body: add category immobility to the locked set and state prefix/folder as mergeable. (T4) ST3's body: same carrier ruling, so the subtask stops offering a choice.
  - docs/stability.md (@tech-writer, TASK-719 ST2 already owns the rewrite — three lines, one of which is wrong today independently of this feature). (D1) 'workflow overrides are additive-only (new types/statuses/collections accepted; shadowing built-ins is an error)' → shadowing is allowed and validated; the frozen surface is the three roster type keys plus category immobility, and the guardrail is the load-time floor. (D2) 'template and role overrides carry a <!-- squads:override-base:<version> --> stamp' is already inaccurate: role overrides carry the TOML-comment form '# squads:override-base:<version>', only templates carry the HTML form, and the workflow override is stamped too — state all three kinds and both spellings. (D3) 'the sq override command group … is the user-owned upgrade path for templates and roles' → add the workflow override.
  - src/ strings for TASK-718's dev, all still asserting additive-only: _overrides/_service.py's _WORKFLOW_SCAFFOLD_BODY header + its 'You may NOT redefine (shadow) a built-in' rules block, _workflow_state's docstring, _diff_workflow's '(empty — workflow overrides are additive-only…)' diff label, _workflow/_loader.py's module docstring and load_workflow_spec's docstring, and _cli/_override.py's scaffold docstring 'Workflow override (additive-only)'. Verified clean and needing no change: the reserved-vocab floor comment in _workflow/_models.py already states the lock as keys + category only, so the code was already on ADR-696's side of this.
  - CLAUDE.md: nothing to route. Its invariant list carries no roster-lock statement at all — I grepped for roster, locked, override surface, additive-only and field-merge. Whoever reported it as a third stale source was mistaken; do not open a change there.
- [2026-07-31T13:56:49Z] Robert Architect:
  - One further contradiction found while reading, NOT fixed and needing a ruling before ST2 is accepted: re-prefixing or re-foldering a type with live items on disk is unhandled, for every type — this feature's acceptance ('a built-in is re-prefixed by overriding a single field') is only true against an empty corpus.
  - The mechanics. An item's prefix is derived from its persisted frontmatter id (_models/_item.py::_derive_prefix_from_id), never from the spec at read time, so re-prefixing a type leaves existing items carrying the old prefix while new ones get the new one — one type, two prefixes, permanently. An item's path is NOT persisted: it is derived from spec.items[type].folder (_paths.folder_for / item_relative_path), so re-foldering a type makes the existing corpus unreachable. validate_against_index cross-checks type and status NAMES only, so neither is caught.
  - Why it matters now rather than in principle: this gap predates my ruling and is not created by it, but ruling prefix/folder mergeable for roster types makes it reachable by default — a real squad's role/skill/operator corpus is never empty, it exists from sq init. My recommended shape, offered not ruled: extend the loader floor's live-item cross-check to refuse a prefix or folder change on a type that still has items, listing the offending IDs — same shape and same message style as the existing live-index guard, and cheaper than a rename migration. @manager route it back to me as a scoped ruling if you want it decided rather than deferred; ADR-696 does not currently cover it either way.
- [2026-07-31T14:05:38Z] Robert Architect:
  - RULING 3 (@tech-lead @product-owner) — the corpus-alignment cross-check. Ruled, not deferred; recorded as ADR-696 §5a with a dated amendment note. And first, a correction to my own finding above, because I got the mechanism half wrong and the coordinator verified only the two halves I handed him.
  - CORRECTION. _services/_maintenance.py::_iter_item_files — the single on-disk scan behind sq repair, sq check's index_reconciled, and repad — resolves each type's directory from spec.items[t].folder AND globs f'{ts.prefix}-*.md'. So a PREFIX change blinds that scan exactly as totally as a folder change: files carry the old prefix, the glob asks for the new one. In both cases every item of the type vanishes from the scan, index_reconciled reports each as 'in index but no markdown file found' (error), and a routine sq repair rebuilds from the empty scan and DROPS them all from the index, reporting missing_ids rather than refusing. Also: Item.path IS persisted in the index, so per-item reads keep working until someone repairs — which makes the failure quiet, the worst property it could have. My earlier 'a re-prefix splits the corpus but every item is still readable' understated the prefix half; the split is real but the glob miss is the important part.
  - Q4 answered by that: NO, a folder change is not worse than a prefix change. One failure, one code path, one blast radius, one clause — not two answers. That is a cleaner outcome than expected and it is evidence-backed rather than a simplification.
  - Q1 — refuse, and my offered shape is CONFIRMED but sharpened in placement. The check goes INSIDE the existing live-index cross-check (validate_against_index / validate_against_index_fail_closed), not as a new clause in _collect_floor_violations: that function already walks every live item comparing item facts against the merged spec (today type and status names), so this adds two fields to a check that exists rather than adding a check. Rule: for every type with at least one live item, the declared prefix and folder must equal the values its existing items were written under; mismatch fails closed listing the offending IDs, in the wording the cross-check already uses for a dropped type or status. It stores NOTHING new — the prefix is recoverable from each item's id, the directory from each item's stored path — so no per-type prefix/folder enters the index, which is forbidden to hold what the .md files already carry. It sits on the cross-check plane, not the floor, because a re-prefixing spec is valid in the abstract and wrong only against THIS corpus; that placement also gives collect-mode in sq workflow lint and fail-fast in open_service for free, with no new mode. An empty corpus is unaffected, which preserves the capability for the case it was actually asked for.
  - Q1, second half — what the adopter who WANTS to re-prefix an existing corpus is told, and whether that path exists today. It does not. No shipped verb realigns a corpus: repad renames files for a padding change only, and retype re-prefixes/moves ONE item while also changing its type, which is not the operation. So per ADR-697 §7 the refusal names the two performable ways forward — revert that field in the override, or make the change while the type has no items — and names NO migration. An unperformable remedy is worse than an honest dead end. The gap is recorded as a gap in ADR-696's consequences, with the note that the verb which would lift it is a composition of shipped mechanics (repad already walks and renames every item file then repairs; retype already rewrites one item's id, moves its file and rewrites incoming edges atomically), so it is small and known rather than open-ended. When it lands, §5a's clause gets restated to name it.
  - Q2 — where it lives: fold into TASK-718 ST2 as you intended, no new task, with the one refinement above (inside validate_against_index, not _collect_floor_violations). The merge engine still owns no floor check; the loader still owns the floor; sq workflow lint's phase 3 picks this up with no change because it already calls validate_against_index in collect mode. ST2 gains one bullet.
- [2026-07-31T14:05:56Z] Robert Architect:
  - Q3 — YES, both acceptance statements need correcting; wording below for the same routing wave (@product-owner owns both bodies). Note EPIC-538's OUTCOMES line already says re-prefix is 'guarded by the existing referential-integrity checks and the live-index guard (validate_against_index_fail_closed)' — which is exactly where this ruling puts the check, so the epic's framing was already right and only its acceptance overclaims.
  - (A3) EPIC-538 epic-level acceptance, the re-prefix bullet: 'A built-in can be **re-prefixed** by overriding a single field, without restating the rest of its definition.' → 'A built-in **with no items yet** can be **re-prefixed or re-foldered** by overriding a single field, without restating the rest of its definition. Once a type has items, a prefix or folder change is refused against the live corpus with the affected IDs listed — the field-merge itself works; what is gated is applying it to items already written under the old value (ADR-696 §5a).'
  - (F4) FEAT-713 acceptance, same bullet: 'A built-in is re-prefixed by overriding a single field, without restating the rest of its definition.' → 'A built-in with no items yet is re-prefixed or re-foldered by overriding a single field, without restating the rest of its definition; against a non-empty corpus the change is refused with the affected item IDs listed, and the refusal names the two ways forward that exist — revert the field, or change it before the type has items (ADR-696 §5a).'
  - (F5) FEAT-713 Scope, the consumer-audit bullet ends '...a re-prefixed type resolves under its new prefix, with no stale map entry left behind' — true for the maps, but add: 'and the on-disk scan's per-type folder + prefix glob is the reason a re-prefix against a non-empty corpus is refused rather than absorbed (ADR-696 §5a).' Without that line the audit reads as if absorbing a re-prefix on a live corpus were achievable at the consumer sites, which it is not — the scan is the constraint, not the maps.
  - (T5) TASK-718, ST2 gains one bullet: the corpus-alignment cross-check per ADR-696 §5a — inside validate_against_index alongside the type/status name checks, prefix from each item's id and directory from each item's stored path, nothing new stored, refusal lists the offending IDs and names only revert-or-do-it-empty, never a migration. And ST4's acceptance line 'With a type renamed and re-prefixed, every site presents the new name and prefix' needs the qualifier: that is the empty-corpus case; with items present the load is refused before any consumer sees the merged spec, so the audit's re-prefix scenario must be built on a type with no items.
  - @tech-writer one addition to TASK-719 ST2's stability-contract rewrite, since it is now part of the published contract rather than an internal detail: state that a type's prefix and folder are settled at adoption — changeable freely before the type has items, refused afterwards with the affected IDs listed — and that no corpus-realignment command exists. Adopters need this before they choose vocabulary, not after; it is the one place where 'shadow any field' has a hard boundary.
- [2026-07-31T14:14:51Z] Nina Product:
  - Corrected roster-lock wording (Scope/Acceptance/Constraints) per ADR-696 §4/ADR-541 amendment: drop the mistaken '/re-prefixed' from the lock, prefix/folder now explicitly field-mergeable.
  - Corrected the re-prefix acceptance bullet + added the scan-glob rationale to the consumer-audit bullet, per ADR-696 §5a (refused against a non-empty corpus, not absorbed).
  - Also fixed the drift-stamping bullet (Scope) and matching US1 line: the carrier is the '# squads:override-base' comment stamp, not a top-level override_base spec key, per ADR-696 §4's ruling — this wasn't on the architect's list but the same ruling falsifies it.
- [2026-07-31T14:28:43Z] Robert Architect:
  - RULING B (@tech-lead) — whose job is escaping the splat sigil. Answer: nobody's. The obligation does not sit with the writers, the fields, or the adopter; it sits with the engine's detection predicate, which was wider than the rule it enforces. Recorded as ADR-696 §4a (dated amendment note). This also corrects the routing: the work is in the engine (FEAT-712 / TASK-716), not FEAT-713 or FEAT-714.
  - The rule: a string value is in token territory ONLY if it BEGINS with an unescaped sigil. Inside token territory it must be a well-formed whole-value token or it fails closed. A value that merely contains the sigil after its first character is data — left verbatim, no violation, no escape. The double-sigil escape survives for the rare value that must literally begin with it.
  - Why this rather than the three options offered. Field exemption is out on principle: knowing which fields carry shell content is schema knowledge, the same boundary breach I just refused for F2's base-shape reading — the engine cannot be schema-blind on one axis and schema-aware on the other. A sigil change is out as over-reach: it churns a settled, reviewed grammar across the ADR, FEAT-712, TASK-716, docs and 108 tests, and it only MOVES a collision that a smaller change dissolves. Writer-side escaping is out because the duty is unbounded and self-harming — every present and future writer owes it forever, a miss is a hard load failure on the adopter's squad explained in terms of a grammar they never used, and an escaped scaffold differs from its bundled source on every shell line, so sq override diff's delta-mine shows differences the adopter did not make. That last part is a real defect in the one surface whose job is showing what the adopter changed.
  - The root cause is that the detection predicate never matched the recognition rule. 'A token is recognised only when it is the entire string value' is stated three times, while the check fires on the sigil anywhere — so it rejects strings the grammar was never going to interpret. That is worth fixing on its own terms; the shell collision is what makes it urgent, because the sigil IS POSIX command substitution and the playbook's commands are command lines. Under the narrowed rule git commit -m "$(cat msg)" is inert, and FEAT-714 inherits safety with no clause of its own.
  - Two consequences I accepted deliberately and recorded rather than hid. An interpolation attempt (prefix = "text $(items.task.prefix)") stays literal instead of erroring — the grammar never offered interpolation and the alternative is the shell collision. And only a LEADING sigil needs escaping, which makes the writers' duty vacuous by construction so long as no bundled string value begins with one — none does today (verified across all three bundled documents: zero occurrences). That is worth a standing guard rather than a rule someone must remember: a tests/meta scan that no bundled document holds a string value beginning with an unescaped sigil, same shape as the existing stray-ticket-reference and module-level-mutable-state scans.
  - Code paths that carry a duty, so you can route precisely: the ENGINE owns the predicate change (src/squads/_specmerge.py, token detection + the malformed-token diagnosis F3 asks for); tests/meta owns the bundled-document guard; docs own one sentence. sq override scaffold, the diff path, and the playbook writers owe NOTHING once the predicate is narrowed — which is the point of ruling it this way rather than distributing the duty. If the guard is ever removed, the duty reappears at every writer, so the guard is load-bearing and should be commented as such.
- [2026-08-01T20:43:56Z] Pierre Chat:
  - The override capability ships with 0.13. Not deferred, not flagged off — so every spec-blind consumer is found and fixed before release rather than tracked as a known defect.
<!-- sq:discussion:end -->
