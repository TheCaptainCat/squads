---
id: REV-238
sequence_id: 238
type: review
title: 'FEAT-208 review: de-type to str + capability flags + reserved-vocab'
status: Approved
author: reviewer
refs:
- FEAT-208
- TASK-233
- TASK-234
- TASK-235
subentities:
- local_id: F1
  title: 'Load-boundary vocab validation (ADR-232 §1) not implemented: unknown type/status
    in frontmatter is silently indexed, then crashes check/list with raw KeyError'
  status: Fixed
  severity: high
- local_id: F2
  title: Reserved-status set is ALL of Status, not the accepted structural floor —
    over-restrictive vs ADR-accept pin; will block F5 custom statuses
  status: Fixed
  severity: medium
- local_id: F3
  title: parse_type/parse_status still iterate ItemType/Status enums, not spec.managed_types()/spec
    status set as ADR scope states (behaviour-identical for default vocab)
  status: Fixed
  severity: low
- local_id: F4
  title: Item._coerce_str_fields/_coerce_status do str(v) with no type guard — a non-str
    non-enum (e.g. int) silently stringifies instead of raising
  status: Fixed
  severity: low
- local_id: F5
  title: 'Residual: sub-entity status is still an unguarded ingestion path — bad sub-entity
    status survives load/repair and crashes sq show --full with a raw ValueError (check
    reports it cleanly)'
  status: Open
  severity: medium
created_at: '2026-06-26T14:32:39Z'
updated_at: '2026-06-26T15:12:51Z'
---
<!-- sq:body -->
Independent review of FEAT-208 (de-typing Item.type/status + SubEntity.status to str; reify ~22 is-ItemType/is-Status checks onto TypeSpec/StatusSpec capability flags; reserved-vocab subset check; extra=forbid hardening). Implemented across TASK-233/234/235 (uncommitted). Reviewed the full HEAD diff, the TOML flag values vs git show HEAD, the characterization gate (REV-236), and ran a live corrupt-frontmatter repro against both HEAD and the change.

## Reification equivalence (the core risk) — PASS. Every one of the ~22 identity checks reifies to behaviour IDENTICAL to the original for the default vocabulary, and each is pinned by a characterization test. Verified individually: _template_for (is_meta -> agents/<type>.md.j2, equiv since meta values == role/skill/operator); _is_participant (is_meta && !=SKILL == {role,operator}); _check_author (is_meta == the 3-tuple); _AGENT_TYPES regen/body/remove (is_meta && !=OPERATOR == {role,skill}); _validate_subtask_story + _check_subtask_stories (parent_required='feature' + subentity_kind=='subtask', uniqueness holds); _check_orphaned registered (is_meta); _check_decisions (supersedes ref_rule + status_role=='superseded', decision is the only type with the rule and Superseded the only status with the role); parent_hint (fixes/addresses ref_rules -> only task gets the suffix); roster _NON_WORK_TYPES (is_meta); work_types() == old WORK_TYPES; severity_field (bug only); backend SKILL removal + role/skill/operator lookups (legit is->== on the widened field, kept type-specific).

## TOML flag values — PASS. All 10 types verified against git show HEAD: is_meta true exactly for role/skill/operator; subentity_kind feature->story/task->subtask/review->finding else None; severity_field true only for bug; parent_required 'feature' only on task; ref_rules task->fixes+addresses, decision->supersedes; status role 'superseded' only on Superseded. Golden shape locks + 76 targeted tests pass.

## extra=forbid / model_validate — PASS. Lifecycle/ItemSpec/StatusSpec/RefRule/WorkflowSpec all carry extra='forbid'; the loader routes each through model_validate with payloads that preserve pre-coerced fields and pass through extras so unknown keys fire. Negative tests cover all five (test_workflow_capability_flags.py).

## Invariants — clean: acyclic imports preserved, no from __future__, clock untouched, the f-string !r/'{x}' changes are output-identical, the id computed_field uses PREFIX_BY_TYPE.get(type, type.upper()) == old .prefix for reserved types.

## Issues — see findings. F1 (HIGH): the ADR §1 load-boundary vocab validation was NOT implemented — unknown type/status in frontmatter is silently indexed by repair (HEAD rejected it) and then crashes check/list with a raw KeyError instead of a clean SquadsError; the ADR §7 hazard-(b) path it was told to characterize is uncovered. F2 (MEDIUM): reserved-status set = all of Status, not the accepted structural floor — fail-closed/neutral today but contradicts the ADR-accept pin and will block F5. F3 (LOW) parse_* still iterate enums vs ADR scope wording (behaviour-identical). F4 (LOW) str(v) coercion accepts non-str input silently.

## Verdict: CHANGES-REQUESTED. The reification and flag encoding are faithful and well-tested — that core is sound. But F1 is a real correctness gap: an explicit, mandatory ADR §1 requirement is missing, it regresses corrupt-frontmatter handling (silent admit + raw KeyError crash on check/list, violating the SquadsError invariant), and the characterization safety net does not cover it. F2 should be corrected in the same pass to honour the accepted scope and not booby-trap F5.



---

## Re-review (round 2) — fixes verified

All four original findings independently re-verified against the new HEAD diff and live repros. F1 (HIGH) RESOLVED: _index/_store.py::_validate_item_vocab(db) runs at the end of IndexStore.load() (deferred _workflow import, no cycle) and _services/_maintenance.py::repair() guards inline after from_frontmatter — BOTH paths check type AND status and raise a clean SquadsError with the item id. Confirmed: index-injected type:gizmo -> sq check/list now raise 'item GIZMO-000018 has unknown type gizmo …' (exit 1, no traceback); a file with bad type/status -> repair rejects cleanly. tests/test_load_boundary_vocab.py adds the 4 cases (load/repair × type/status). F2 (MEDIUM) RESOLVED: _RESERVED_FLOOR is now the 12 structural statuses (agent Draft/Active/Archived + sub-entity Todo/InProgress/Blocked/Done/Cancelled + finding Open/Fixed/Verified/WontFix); work-item-only statuses are no longer reserved, and §5-1/§5-2 still enforce referenced statuses indirectly — matches the ADR-accept pin exactly. test_non_reserved_status_omission_is_allowed proves a custom spec dropping 'Ready' is accepted. (Note: Draft is correctly in the floor as the agent lifecycle's initial, beyond the manager's illustrative 'Active/Archived' shorthand — the whole agent machine is reserved.) F3 (LOW) RESOLVED: parse_type/parse_status now consult _DEFAULT_SPEC.items/.statuses; loose-match preserved, behaviour-identical for default vocab. F4 (LOW) RESOLVED: both coerce validators now raise ValueError on a non-str input (StrEnum still accepted as a str subclass).

## Completeness — one residual path (F5, MEDIUM nit, non-blocking). The item-level guard is complete: all service reads go through store.load() (guarded) or repair (guarded); load_item() in _itemfile is dead code; migrations are ADR-exempt. The ONE remaining unguarded ingestion path is SUB-ENTITY status — a corrupt subentities[].status survives load/repair and crashes sq show --full with a raw ValueError (check reports it cleanly). Same defect class as F1 on the sub-entity axis; filed as F5 with a repro. Lower severity (check catches it; crash confined to show --full on a hand-corrupted file), so not a blocker — recommend folding the sub-entity-status check into _validate_item_vocab + the repair guard in a quick follow-up.

## Updated verdict: APPROVE-WITH-NITS. The four findings are genuinely resolved, each independently re-verified; the core de-typing + reification remains faithful and is now well-guarded at the load boundary with direct tests. Approving with the single non-blocking nit F5 (sub-entity-status load-boundary check) to be addressed as a follow-up.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 238 add-finding "…" --severity high`; track with `sq review 238 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | Load-boundary vocab validation (ADR-232 §1) not implemented: unknown type/status in frontmatter is silently indexed, then crashes check/list with raw KeyError |
| F2 | 🟡 medium | Fixed |  | Reserved-status set is ALL of Status, not the accepted structural floor — over-restrictive vs ADR-accept pin; will block F5 custom statuses |
| F3 | 🟢 low | Fixed |  | parse_type/parse_status still iterate ItemType/Status enums, not spec.managed_types()/spec status set as ADR scope states (behaviour-identical for default vocab) |
| F4 | 🟢 low | Fixed |  | Item._coerce_str_fields/_coerce_status do str(v) with no type guard — a non-str non-enum (e.g. int) silently stringifies instead of raising |
| F5 | 🟡 medium | Open |  | Residual: sub-entity status is still an unguarded ingestion path — bad sub-entity status survives load/repair and crashes sq show --full with a raw ValueError (check reports it cleanly) |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Load-boundary vocab validation (ADR-232 §1) not implemented: unknown type/status in frontmatter is silently indexed, then crashes check/list with raw KeyError

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
ADR-232 §1 mandates that ItemStore.load / open_service validate each item's type/status against the loaded WorkflowSpec (spec.is_known_type / spec.is_valid_status), raising SquadsError with the offending item id on an unknown value. This was NOT implemented — _index/_store.py has zero diff, open_service does no validation, and there are no is_known_type/is_valid_status methods.

Before de-typing, Item.from_frontmatter called ItemType(...)/Status(...) which raised at construction on a bad value, so sq repair REJECTED corrupt frontmatter. Now from_frontmatter stores the raw string with no check.

Repro (fresh squad, hand-edit a task's frontmatter to type: gizmo / status: Frobnicated): sq repair silently accepts it into the index (exit 0); then sq check crashes with KeyError: 'gizmo' at _models.py:269 (item_is_meta -> self.items[item_type]) and sq list crashes with KeyError: 'Frobnicated' at _models.py:245 (is_open -> self.statuses[status]). Raw tracebacks, not the clean @handle_errors one-liner.

Violates: (a) ADR §1 explicit requirement; (b) CLAUDE.md invariant 'user-facing errors subclass SquadsError' — these leak KeyError; (c) ADR §7 hazard (b), which the characterization suite was explicitly told to cover but does not (no bad-value load/repair test in test_spine_characterization.py). check is the very tool meant to REPORT this corruption and it crashes on it.

Also crash surfaces on the same gap: _paths.folder_for / squad_relative do FOLDER_BY_TYPE[item_type] (KeyError on unknown). Fix: add the spec vocab check at the load boundary raising SquadsError with the item id, and add a characterization test pinning the bad-value path.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Reserved-status set is ALL of Status, not the accepted structural floor — over-restrictive vs ADR-accept pin; will block F5 custom statuses

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
_workflow/_models.py:331 sets reserved_statuses = {s.value for s in Status} — i.e. ALL 22 statuses are reserved. But the ADR-accept comment (Catherine Manager, 2026-06-26) pinned the reserved-status floor as the STRUCTURAL minimum only: agent meta-type statuses (Active/Archived) + sub-entity statuses (subtask/story Todo/InProgress/Blocked/Done/Cancelled + finding Open/Fixed/Verified/WontFix). It states explicitly: 'work-item statuses are NOT reserved (customizable when F5/custom-statuses lands).'

The implementation over-reserves ~11 work/ADR/review/guide-only statuses (Ready, InReview, Proposed, Accepted, Rejected, Deprecated, Requested, ChangesRequested, Approved, Published, ...) beyond the accepted decision.

Impact: fail-closed and behaviour-neutral TODAY (F2 has no way to define a custom spec, full suite green), so not a current regression — but it contradicts the accepted ADR and will BOOBY-TRAP F5: a custom spec that legitimately replaces a work-item status would be wrongly rejected. The negative test test_reserved_vocab_omit_status_fails_closed happens to drop 'Done' (which is reserved under BOTH readings, as a sub-entity status), so it does not expose the over-broad set. RESERVED_TYPES = all ItemType is correct per ADR; only RESERVED_STATUSES is wrong. Fix: pin reserved_statuses to the structural floor (extract a named RESERVED_STATUSES constant) and add a test that a work-only status (e.g. 'Ready') may be omitted.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — parse_type/parse_status still iterate ItemType/Status enums, not spec.managed_types()/spec status set as ADR scope states (behaviour-identical for default vocab)

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
_cli/_common.py parse_type/parse_status iterate ItemType / Status enum members. ADR-232 scope says they should iterate spec.managed_types() / the spec status set. Behaviour-identical for the default vocab (reserved == default), so no regression; arguably safer (validates against reserved vocab). Informational — flagging only because it deviates from the ADR's stated approach. Fine to leave within the F2 scope boundary (no custom types end-to-end yet).
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Item._coerce_str_fields/_coerce_status do str(v) with no type guard — a non-str non-enum (e.g. int) silently stringifies instead of raising

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Item._coerce_str_fields (type/status) and SubEntity._coerce_status (mode=before) do return str(v). For StrEnum members str() yields the value (correct). But str() never fails, so a non-str/non-enum value (e.g. an int 123, or None) is silently coerced to '123'/'None' instead of raising a validation error. Pre-de-typing, Pydantic's enum field would have rejected it. Minor — all real callers pass str/StrEnum — but it widens the accepted input set. Consider isinstance(v, str | StrEnum) guard, or rely on F1's load-boundary check.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Residual: sub-entity status is still an unguarded ingestion path — bad sub-entity status survives load/repair and crashes sq show --full with a raw ValueError (check reports it cleanly)

<!-- sq:finding:F5:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
The F1 fix guards ITEM type/status on both ingestion paths (IndexStore.load -> _validate_item_vocab; repair -> inline after from_frontmatter) and is verified clean. But neither guard validates SUB-ENTITY status (Item.subentities[].status), which is the same de-typed field (SubEntity.status: str). SubEntity.from_frontmatter no longer calls Status(...), so a corrupt sub-entity status flows into the index unvalidated — HEAD rejected it at construction.

Repro (fresh squad, feature + add-story US1, hand-edit the subentities entry to status: Frobnicated): sq repair exit 0 (silently accepted); sq feature 18 show --full CRASHES with a raw 'ValueError: Frobnicated is not a valid Status' (via _discussion._status_badge -> Status(...)), not a clean SquadsError. sq check DOES report it cleanly (exit 3, 'story US1 has invalid status Frobnicated') because _check_subentity_status uses a safe membership test.

So the primary corruption-reporting tool (check) works, and the crash is confined to show --full on a hand-corrupted file — lower severity than the item-level F1. But it is the same defect class on the sub-entity axis (silent admit + raw ValueError traceback on a read path, violating the SquadsError invariant), and it is exactly the completeness axis flagged in the re-review request. Fix: extend _validate_item_vocab and the repair guard to also check each item.subentities[].status against the loaded spec's statuses, and add a load/repair test for a bad sub-entity status. Not blocking — filing as a follow-up nit.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T14:34:00Z] Paul Reviewer:
  - Independent review complete — verdict CHANGES-REQUESTED. Reification equivalence is faithful (all ~22 checks behaviour-identical, every flag value correct, each pinned by a characterization test) and the extra=forbid hardening is clean.
  - Blocking: F1 (HIGH) — ADR-232 §1 load-boundary vocab validation was never implemented; corrupt frontmatter (unknown type/status) is silently indexed by repair and crashes sq check/sq list with a raw KeyError (verified via live repro vs HEAD, which rejected it). The ADR §7 hazard-(b) path is uncharacterized. @tech-lead please scope a fix: validate type/status against the loaded WorkflowSpec at the load boundary, raise SquadsError with the item id, and add a characterization test for the bad-value path.
  - Should-fix in same pass: F2 (MEDIUM) — reserved_statuses uses all of Status, not the structural floor the ADR-accept comment pinned; fail-closed today but will wrongly reject custom work-item statuses in F5.
- [2026-06-26T14:35:48Z] Catherine Manager:
  - Confirmed F1 independently: corrupted a task to 'type: gizmo' — sq repair silently re-indexed it (19 items, no rejection) and sq check crashed with a raw Traceback. HEAD rejected it at enum construction; the de-typing dropped that guard and the ADR-mandated load-boundary validation was never added. Real regression + SquadsError-invariant violation. Reopening TASK-235; fixes dispatched (F1+F2 blocking, F3/F4 cheap). The bad-value path also needs a characterization test — it's the §7 hazard-b gap that let this through the green suite.
- [2026-06-26T15:02:53Z] Paul Reviewer:
  - Re-review complete — verdict APPROVE-WITH-NITS. All four original findings independently re-verified as resolved (F1/F2/F3/F4 -> Fixed), with live repros + the new tests/test_load_boundary_vocab.py (load/repair × type/status) and test_non_reserved_status_omission_is_allowed.
  - F1 item-level guard confirmed clean on both paths (index-load + repair): corrupt type/status now raises a one-line SquadsError with the item id, no raw KeyError. F2 reserved floor is the 12 structural statuses, matching the accepted decision. F3 spec-driven. F4 raises on non-str.
  - One residual nit on the record — F5 (MEDIUM, NON-BLOCKING): sub-entity status (SubEntity.status, also de-typed to str) is still an unguarded ingestion path. A corrupt subentities[].status survives load/repair and crashes sq show --full with a raw ValueError; sq check reports it cleanly. Same defect class as F1 on the sub-entity axis. @tech-lead recommend a quick follow-up: extend _validate_item_vocab + the repair guard to also validate each item.subentities[].status, with a matching test. Approving now; this can land as a fast-follow.
- [2026-06-26T15:12:51Z] Catherine Manager:
  - F5 verified fixed — the load-boundary guard now also validates sub-entity status on both paths (_validate_item_vocab at index-load + the repair inline guard). Confirmed: a bad subentities[].status injected into the index → sq feature show --full / sq list now raise a clean SquadsError (item id + sub-entity key), no raw ValueError; 2 new tests added. The guard is complete across item AND sub-entity vocabulary. All of F1-F5 resolved; running a final full-suite confirmation before marking Done.
<!-- sq:discussion:end -->
