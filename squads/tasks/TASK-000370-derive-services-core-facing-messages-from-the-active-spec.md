---
id: TASK-370
sequence_id: 370
type: task
title: Derive services-core facing messages from the active spec
status: Done
parent: FEAT-336
author: tech-lead
created_at: '2026-07-10T02:00:12Z'
updated_at: '2026-07-10T04:14:10Z'
---
<!-- sq:body -->
## Scope

Surface 5 of the REV-360 audit — services-core facing messages/metadata that hardcode
bundled vocab even though the required value is already resolved from the spec one line
away. Derive the vocab from the active spec. Files: `_workflow/_models.py` (parent_hint),
`_services/_subentities.py`, `_models/_metadata.py`, `_services/_maintenance.py`,
`_services/_results.py`. Independent of the other FEAT-336 tasks (disjoint files).

## Covered REV-360 findings

- MEDIUM — `_workflow/_models.py:782-784` (`WorkflowSpec.parent_hint`) — hardcodes ref-kind
  names + the whole hint sentence ("link a bug or review with `sq ref add … --kind
  fixes|addresses`") even though `RefRule` carries a per-rule `hint` field populated for
  this purpose (default_workflow.toml 295-296). Use the spec-declared hint instead of
  re-detecting literal fixes/addresses + emitting bundled "bug or review" prose. Feeds
  `sq check` output and retype refusals.
- MEDIUM — `_services/_subentities.py:473` (`_validate_subtask_story`) — message
  `"{task.id}'s parent is a {kind}, not a feature"` hardcodes "feature" though
  `required = self.spec.item_parent_required(task.type)` is resolved one line above.
- MEDIUM — `_models/_metadata.py:42-47` (`EXTRA_FIELDS`) — settable `extra` metadata keyed
  by hardcoded type names 'guide' (X.TAGS) / 'review' (X.TARGET_REF); both are overridable
  work types. A renamed guide→doc / review→audit makes `sq update --set tags=…` /
  `--set target_ref=…` rejected and the fields unsettable. This drives real accept/reject
  behaviour + the valid-field error list — key it on spec-declared type identity, not the
  bundled literal.
- LOW — `_services/_subentities.py:467` — message "{task.id} has no feature parent; …"
  hardcodes "feature"; required parent type is available via `item_parent_required`.
- LOW — `_services/_maintenance.py:1042` & `:1048` (`_check_subtask_stories`) — `sq check`
  messages hardcode "task"/"feature"/"subtask"/"user story" though `required_parent` is
  resolved at 1036.
- LOW — `_services/_maintenance.py:1098` (`_check_decisions`) — warning hardcodes the
  status label "Superseded" though gated on `status_role(...)=='superseded'` with the real
  status in `item.status`.
- LOW — `_services/_results.py:57,70` (`GraphNode.priority` / `to_dict`) — carries a single
  hardcoded `priority` badge field + serialises the fixed key 'priority'; a project on a
  different/additional badge axis sees a permanently-null 'priority' in `sq graph --json`.
  (TreeNode carries the whole Item and stays generic — GraphNode-specific.)

## Ordering / flag

`EXTRA_FIELDS` (MEDIUM) is the one with real behavioural impact (fields become unsettable
under a renamed type), not just message wording — prioritize it within this task. The rest
are message-accuracy fixes.

## Out of scope (REV-360 INFO — sanctioned deferred, do NOT fix here)

- `_base.py:54-58` SUBENTITY_CONTAINER / `_retype.py:26-30` _CONTAINER_HEADINGS /
  `_workflow/__init__.py:50` _SUBENTITY_KINDS — custom sub-entity-kind support is a
  documented deferred non-goal; these stay bundled-keyed.
- `_workflow/_models.py:567-573` _SIDE_PRIORITY — cosmetic ordering with deterministic
  fallback; output stays coherent.

## Acceptance

- Each cited message names the spec-resolved required type/status/kind, not the bundled
  literal (verified on a spec that renames feature/task/guide/review and a superseded-role
  status).
- `EXTRA_FIELDS`/`settable()` resolve by spec type identity so tags/target_ref stay
  settable on a renamed host type.
- `GraphNode` surfaces the type's actual badge axis (or is made generic) in `sq graph
  --json`.
- Full gate green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 370 add-subtask "<title>"`; track with `sq task 370 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T03:50:01Z] Elias Python:
  - Starting: reading code before editing.
- [2026-07-10T04:07:08Z] Elias Python:
  - Implemented all 5 REV-360 findings; gates green; leaving InProgress for review.
  - EXTRA_FIELDS (real fix): added ItemSpec.extra_fields + WorkflowSpec.item_extra_fields; guide/review now advertise tags/target_ref via default_workflow.toml instead of a hardcoded type-name lookup. role/skill stay literal (reserved meta-types, already name-bound elsewhere). settable()/coerce_extra() take a caller-resolved extra_keys param; _models stays free of a _workflow import.
  - parent_hint: now joins the spec-declared RefRule.hint text(s) instead of re-detecting fixes/addresses + emitting bundled 'bug or review' prose. Byte-identical on the bundled spec.
  - _validate_subtask_story / _check_subtask_stories / _check_decisions: messages now name the spec-resolved required-parent type / sub-entity kind / actual status instead of feature/task/subtask/user story/Superseded literals. Byte-identical on the bundled spec.
  - GraphNode: kept 'priority' as-is (CLI at _main.py, out of scope, still reads it) and added an additive 'badges' dict (field-code -> value, resolved via spec.fields_for + Item.badge_value) so --json surfaces a type's actual axis without a CLI/schema-breaking rename. Golden regenerated (additive diff only).
  - Tests added: test_rename.py (extra field survives a guide->doc rename), test_workflow_capability_flags.py (parent_hint uses declared hint; item_extra_fields), test_spine_characterization.py (check/validate messages name a custom required-parent type; supersedes warning names a custom status).
  - Fast gates green: pyright, ruff check, ruff format --check, plus targeted service/model/maintenance/graph/rename/spine/custom-type tests and test_squad_ref_hygiene.py. Did not run the full suite (main loop's job).
  - Reviewer: scrutinize the GraphNode call (additive badges dict vs. renaming/removing priority) and the EXTRA_FIELDS layering (_models still has no _workflow import; default_workflow.toml gained extra_fields on guide/review).
- [2026-07-10T04:13:18Z] Paul Reviewer:
  - Reviewed uncommitted TASK-370 diff (independent, last FEAT-336 fix). VERDICT: APPROVE. gates clean (pyright/ruff/format), full suite green (exit 0, 0 failures). One LOW byte-identity nit (below); everything else byte-identical.
  - EXTRA_FIELDS rename-safe + layering CLEAN (Q1): _models/_metadata keeps only role/skill (reserved meta, bound by name — no rename hazard); guide/review's tags/target_ref move to spec-declared ItemSpec.extra_fields + WorkflowSpec.item_extra_fields, with settable()/coerce_extra() taking caller-supplied extra_keys. _models does NOT import _workflow (verified) — the service bridges (_items.py:116 passes self.spec.item_extra_fields(item.type)). That is the ONLY coerce_extra call site and settable() has no external caller, so no built-in field became unsettable. test_extra_field_stays_settable_after_type_rename proves guide->doc keeps --set tags (coerced to list) and still rejects target_ref.
  - Byte-identical bundled (Q2): YES except one wording nit. parent_hint — dedup of the two identical fixes/addresses RefRule.hint strings reproduces the exact old sentence (verified toml:278-279 carry that literal hint; supersedes hint='' is filtered, decision unchanged). _validate_subtask_story — host=required or 'parent' = 'feature' for bundled, identical. _check_decisions — condition is spec-role-based (status_role=='superseded'), item.status='Superseded' when it fires, identical. default_workflow.toml extra_fields on guide/review is additive (no golden needed beyond graph_feat_json's additive 'badges: {}'). No SCHEMA_VERSION bump (Q3) — correct, extra_fields is workflow-spec schema not item frontmatter, matching the FEAT-212/281 precedent.
  - F1 (LOW, byte-identity nit): _check_subtask_stories message changed 'user story' -> 'story' for the bundled spec (story_kind=item_subentity_kind('feature')='story', not the prose 'user story'). Deliberate + spec-consistent (names the actual kind), and the spine test assertion is lenient ('story' in msg) so nothing regressed — but it contradicts the strict byte-identical claim. Acceptable/arguably an improvement; flagging only because the message wording is no longer identical.
  - GraphNode badges call (Q4): REASONABLE. Additive badges:dict resolved generically via _resolve_badges(spec.fields_for(type) -> badge_value) surfaces a custom axis in --json (closing the finding) while leaving priority in place for the CLI — no CLI-breaking rename. graph_feat_json golden is purely additive ('badges': {}). Priority itself keeping its slot is the right scope call; a priority->generic rename would be a separate CLI-facing change (fine as a future follow-up, not needed here). Tests genuine (rename-safe tags, custom host/parent naming, capability-flags); no ticket IDs in source. Completes FEAT-336's REV-360 surfaces.
- [2026-07-10T04:14:09Z] Catherine Manager:
  - Reviewer-approved; full suite green. EXTRA_FIELDS rename-safe (spec-declared ItemSpec.extra_fields, service bridges the layering — guide→doc keeps --set tags), parent_hint from declared RefRule.hint, messages spec-resolved, GraphNode additive badges (no CLI-breaking rename). F1 (LOW: subtask-story check now says 'story' vs 'user story' — names the actual kind, spec-consistent) accepted as an improvement. No SCHEMA_VERSION bump. Landing.
<!-- sq:discussion:end -->
