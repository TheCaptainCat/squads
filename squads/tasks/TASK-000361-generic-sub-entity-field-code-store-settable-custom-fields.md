---
id: TASK-361
sequence_id: 361
type: task
title: 'Generic sub-entity field-code store: settable custom fields'
status: Done
parent: FEAT-212
author: tech-lead
refs:
- ADR-348
- REV-337
created_at: '2026-07-09T23:51:27Z'
updated_at: '2026-07-10T00:09:31Z'
---
<!-- sq:body -->
Realizes ADR-348 §4 — the generic per-field storage for sub-entity kinds. Missed by the FEAT-212 breakdown (349..354) and surfaced by the TASK-353 review (F1/F2): a custom sub-entity kind can *declare* a non-severity field (it renders as a column) but cannot *set* it — `add-<kind>`/`update` currently fail loud with "no CLI storage yet" (gated by `_STORED_FIELD_CODES`). This closes that half-capability so custom sub-entity fields are settable and round-trip, mirroring the already-shipped item axis.

## Scope

- Add a generic field-code -> badge-code store on `SubEntity` (`_models/_subentity.py`), the direct analog of the item axis `Item.badge_value`/`set_badge_value` (attribute for `severity`, `extra[code]` for any other declared field). The badge code is the authoritative stored value (ADR-348 §4 / ADR-323 §4 discipline): `--json` and no-spec reads work, label/emoji resolve at render time.
- Keep `SubEntity.severity`'s typed slot for byte-identical finding round-trip; other field codes store in the generic map.
- Wire the CLI `add-<kind>`/`update` (`_cli/_items.py`) to store via this surface instead of raising; remove the `_STORED_FIELD_CODES` fail-loud gate.
- Ensure `_discussion.summary_row` field-value retrieval reads the generic store (it currently `getattr(sub, field.code, None)` — extend to the badge-code store for non-attribute fields).

## Acceptance

1. A custom kind declaring a non-severity field (e.g. `urgency`) can set it via `add-<kind> --urgency X` and `update --urgency Y`; the value round-trips in frontmatter and renders in the summary column.
2. Finding `severity` behaviour is byte-identical (typed slot preserved).
3. `_STORED_FIELD_CODES` and the "no CLI storage yet" error are gone.
4. `--json` and no-spec reads surface the stored badge code; full suite green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 361 add-subtask "<title>"`; track with `sq task 361 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T23:51:28Z] Catherine Manager:
  - Filed to close the ADR-348 §4 gap the FEAT-212 breakdown missed (TASK-353 review F1/F2). Sequenced before the TASK-354 closeout so vulture/golden/lint verification runs over the complete feature.
- [2026-07-10T00:03:10Z] Elias Python:
  - Implemented ADR-348 §4: SubEntity gains extra: dict[str, Any] + badge_value/set_badge_value, mirroring Item's pattern exactly (severity keeps its typed slot; any other declared field code stores in extra).
  - CLI: _STORED_FIELD_CODES gate + 'no CLI storage yet' error removed from _cli/_items.py; add-<kind>/update now resolve every declared field via _resolve_add_fields/the update loop and pass fields={...} through to svc.add_block/update_block.
  - Service: add_block/update_block's severity kwarg replaced by a generic fields: dict[str,str] | None, applied via sub.set_badge_value(code, value); add_finding/update_finding (kept for existing call sites) now route severity through fields={'severity': ...}.
  - Rendering: _discussion.summary_row's _field_value + _cli/_common.py's _subentity_pane_title_raw both switched from getattr(sub, code) to sub.badge_value(code) — same one-line gap, fixed in both places for consistency (byte-identical for severity since getattr==badge_value there).
  - Test: test_custom_subentity_kind_cli.py::test_custom_kind_declared_field_is_settable_and_round_trips — a custom 'action' kind's urgency field set via add-action --urgency high, remapped via update --urgency low, verified in the derived summary column, on-disk frontmatter (extra: {urgency: low}), and show --json (subentities[0].extra.urgency).
  - Golden diff: feature_show/task_show/show_feat/show_task/list/list_feature all gained a purely additive subentities[].extra: {} key (SubEntity's new field appearing in model_dump_json, exactly mirroring Item.extra's existing presence) — regenerated with UPDATE_GOLDENS=1, no other change.
  - Gates green: pyright/ruff/ruff format clean; targeted suite (custom-kind/badge-axis/collab/cli/discussion/models/golden-json/golden-rendered/migrations/bug-severity/reflog/load-boundary/workflow-spec/ref-hygiene) all pass, no full-suite run per scope.
  - Reviewer should scrutinize: the severity kwarg removal from add_block/update_block's public signature (no test called them directly, only via CLI/wrappers, but double-check no external caller relies on it) and whether print_subentity's hardcoded 'severity:' line (sq <kind> show, unextended) should also generalize in a follow-up — left untouched, out of this task's stated scope.
- [2026-07-10T00:08:29Z] Paul Reviewer:
  - Reviewed uncommitted TASK-361 diff (independent, on committed TASK-353). VERDICT: APPROVE. Clean §4 implementation closing the TASK-353 F1/F2 gap. Gates clean (pyright/ruff/format), full suite green (exit 0, 0 failures), AC1-4 met. Only one LOW deferral note (correctly routed to REV-360).
  - Mirrors the item axis correctly: SubEntity.badge_value/set_badge_value (_subentity.py:47-64) are byte-for-byte the same dispatch as Item.badge_value/set_badge_value (_item.py:247-263) — attribute when hasattr(severity), extra[code] otherwise; badge code is the authoritative stored value (no-spec/--json reads work). extra:dict={} field + to/from_frontmatter wiring (omit-if-empty on write, dict(...or{}) on read) mirror Item.extra exactly; pydantic v2 deep-copies the mutable default per instance, so no shared-state bug.
  - Byte-identical for severity/findings: YES. severity keeps its typed slot; badge_value('severity')->getattr, set_badge_value('severity')->setattr, so finding round-trip and frontmatter key are unchanged. Golden diff is ONLY additive 'extra: {}' (the story:null lines just gain a trailing comma before it) across the 6 JSON goldens — nothing behavioural. Frontmatter stays clean (empty extra not written). .squads.json churn is benign bookkeeping (item 359->360 is this task's own item + additive extra + counter bump; no data loss).
  - Signature-change safety: YES, safe. add_block/update_block swapped severity= for fields:dict|None; grep confirms NO caller anywhere passes severity= to either (all 8 block-op call sites checked) — add_finding/update_finding route fields={'severity':...} (update only when severity is not None, preserving the old 'don't touch' semantics), and add_story/add_subtask/update_story/update_subtask never touched severity. AC3: _STORED_FIELD_CODES + the 'no CLI storage yet' error fully deleted (grep-clean).
- [2026-07-10T00:08:42Z] Paul Reviewer:
  - End-to-end proof: GENUINE, not a stub. test_custom_kind_declared_field_is_settable_and_round_trips declares a non-severity 'urgency' field (bound to a custom 'level' collection) on the action kind and asserts: add-action --urgency high (AC1), the derived Urgency summary column renders 'high', update --urgency low remaps (low present/high gone), 'urgency: low' persists in on-disk frontmatter (round-trip), and show --json exposes subentities[0].extra.urgency=='low' (no-spec badge-code read). Exercises both add AND update across frontmatter + column + JSON.
  - print_subentity flag (flag 6): acceptable to defer, and REV-360/FEAT-336 IS the right home. _cli/_common.py:392 hardcodes a 'severity:' meta line in the 'sq <kind> show' pane and won't display other declared fields (a custom kind's urgency is invisible there) — but the data round-trips and IS visible on every other surface (list table, pane title, --json), so this is display-incompleteness, not data loss. It's squarely REV-360's definition (a facing surface assuming bundled vocab). LOW. Recommend the coordinator ensure it's captured as an explicit REV-360 finding so it's tracked, not only verbally deferred.
  - Scope-disciplined; no ticket IDs in source (the one ADR-323 ref is a test comment citing the field mechanism, matching repo provenance convention). _discussion._field_value and _common._subentity_pane_title_raw correctly switched to sub.badge_value (the 'if value:' truthiness is equivalent to the old isinstance+truthy). FEAT-212 is now materially complete on the field axis — the F1 half-capability I flagged on TASK-353 is closed.
- [2026-07-10T00:09:30Z] Catherine Manager:
  - Reviewer-approved; full suite green; AC1-4 met — FEAT-212 is materially complete on the field axis. F1 (LOW: print_subentity severity-only meta line) captured as an explicit finding on REV-360 for the FEAT-336 pass. Landing.
<!-- sq:discussion:end -->
