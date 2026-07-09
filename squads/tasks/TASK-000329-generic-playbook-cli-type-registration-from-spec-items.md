---
id: TASK-329
sequence_id: 329
type: task
title: Generic playbook + CLI type registration from spec.items
status: Done
parent: FEAT-326
author: tech-lead
subentities:
- local_id: ST1
  title: Playbook keyed by str; coverage over work_types(); thin auto-skill fallback
  status: Done
  story: US3
- local_id: ST2
  title: CLI registers all spec.items types dynamically in deterministic order
  status: Done
  story: US3
- local_id: ST3
  title: SUBENTITY_* + sq check subtask literal rederive from spec
  status: Done
  story: US3
created_at: '2026-07-07T14:50:23Z'
updated_at: '2026-07-08T11:36:12Z'
---
<!-- sq:body -->
## Scope

Route every type — built-in and custom — through **one** generic registration
path keyed off `spec.items`, with a **deterministic** iteration order, and
remove today's static-vs-dynamic built-in/custom split. This is ADR-322's "hard
blocker" (the playbook loader) plus the CLI app-build (US3).

## Areas / files

- `_interactions.py` (+ `_interactions/_loader.py`, `_interactions/_models.py`) —
  key the playbook by `str`; delete `_coerce_item_type` / `ItemType(name)`
  coercion; `_check_coverage` requires a playbook entry only for each
  `spec.work_types()` entry. A work type with no bundled playbook entry falls
  back to a thin auto-generated `sq-<type>` skill instead of failing coverage
  (F4).
- `_cli/__init__.py` — register per-type command groups for **all** `spec.items`
  entries dynamically; remove the `_builtin_work_type_names` / `_ORDERED_WORK_TYPES`
  static branch. Ordering must derive from a **deterministic spec order** (define
  and document the order key — not implicit TOML insertion order).
- `_cli/_create.py` — remove the hardcoded work-type tuple; `_make` keyed by
  `str`; register from `spec.items`.
- `_cli/_common.py`, `_cli/_items.py` — drop `ItemType` annotations/parsers →
  `str`.
- `_services/_base.py` — the `SUBENTITY_*` maps derive kind↔type from the spec's
  per-type `subentity_kind`; `sq check`'s residual `"subtask"` literal routes
  through the spec so a dropped/renamed type cleanly loses (not silently keeps)
  its sub-entity checks.

## Done criteria

- The playbook and CLI register every `spec.items` type through one code path, in
  deterministic order; adding a type requires no static-table edit.
- A type absent from the playbook still gets a working thin auto-generated
  `sq-<type>` skill.
- No-override default squad (roster held constant) exposes an identical CLI
  surface and identical generated skills.
- `pyright` + `ruff check` + `ruff format --check` clean.

## Sequencing note

This can land **before** the `ItemType` deletion — `str` keys interoperate with
the surviving `StrEnum`, so the conversion is behavior-preserving on its own. It
leaves the enum-deletion task inheriting `str`-keyed consumers.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 329 add-subtask "<title>"`; track with `sq task 329 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Playbook keyed by str; coverage over work_types(); thin auto-skill fallback | US3 |
| ST2 | Done |  | CLI registers all spec.items types dynamically in deterministic order | US3 |
| ST3 | Done |  | SUBENTITY_* + sq check subtask literal rederive from spec | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Playbook keyed by str; coverage over work_types(); thin auto-skill fallback

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — Playbook + CLI register types generically
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Key the playbook by str and delete the ItemType(name) coercion in _interactions/_loader.py. _check_coverage requires a playbook entry only for each spec.work_types() entry; a work type with no bundled entry falls back to a thin auto-generated sq-<type> skill rather than failing coverage.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — CLI registers all spec.items types dynamically in deterministic order

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — Playbook + CLI register types generically
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Register per-type command groups for all spec.items entries dynamically in _cli/__init__.py and _cli/_create.py; remove the _builtin_work_type_names/_ORDERED_WORK_TYPES static branch and the hardcoded work-type tuple. Derive registration order from a documented deterministic spec order, not implicit TOML insertion order.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — SUBENTITY_* + sq check subtask literal rederive from spec

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US3 — Playbook + CLI register types generically
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Rederive the SUBENTITY_* kind-to-type maps in _services/_base.py from the spec's per-type subentity_kind, and route sq check's residual 'subtask' literal through the spec so a dropped or renamed type cleanly loses its sub-entity checks instead of silently keeping them.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-08T08:57:02Z] Elias Python:
  - ST1 (playbook keyed by str): _interactions/_models.py's PlaybookSpec.types and _interactions/_loader.py rewritten — load_playbook(catalog, spec=bundled_spec()) drops _coerce_item_type/ItemType(name); _check_coverage now requires an entry only for each spec.work_types() name and rejects any entry outside that set (replaces the hardcoded _WORK_TYPES/_META_TYPES frozensets). _interactions/__init__.py's PLAYBOOK/CREATE_LANES/LANED_TYPES/managed_item_types/item_types_for_role/item_skill_name/allowed_create_types are all str-keyed now; custom_skill_slugs(spec) and the backend's _write_item_skills fallback loop now key the F4 thin-auto-skill boundary off 'not in PLAYBOOK' instead of 'not an ItemType member' — verified live end-to-end with a custom 'incident' type (sq create incident, sq sync -> thin sq-incident skill body + .claude pointer, sq check clean).
  - ST2 (CLI generic registration): _cli/__init__.py's _CustomTypeGroup and _cli/_create.py's _CustomCreateGroup both register from spec.work_types() directly (removed _builtin_work_type_names/_ORDERED_WORK_TYPES and the hardcoded _CREATABLE ItemType tuple, now derived from _bundled_spec().work_types()). Deterministic order = explicit lexical (alphabetical) sort over the type-name string, documented inline in both files as independent of default_workflow.toml's own [items.*] table order. Verified sq --help / sq create --help register the same 7 built-in types, byte-identical set, in the new lexical order (no golden pins the old order).
  - ST3 (SUBENTITY_* + sq check from spec): _services/_base.py's SUBENTITY_PARENT (and derived SUBENTITY_KIND) now build from bundled_spec().items[...].subentity_kind instead of a hand-typed literal dict (SUBENTITY_CONTAINER's kind->marker-tag map is unchanged, out of this ADR's scope). _services/_maintenance.py's three sq-check helpers that used the static SUBENTITY_KIND.get(item.type) now call self.spec.item_subentity_kind(item.type) instead (the ACTIVE resolved per-service spec, not the frozen bundled-only global) — _check_subentity_title_lengths lost its @staticmethod to read self.spec. This means a project override renaming/dropping a type's subentity_kind is reflected in sq check immediately rather than silently tracking the stale bundled vocabulary; not independently exercisable yet since workflow overrides are additive-only (no rename support until FEAT-281), but the plumbing is correct and behavior-preserving for the default squad.
  - Also touched (consequential, not in the dossier's file list, required by the str-keying): _backends/_claude_code/_backend.py (_write_item_skills' item_type.value -> item_type, custom-type loop keyed off 'ctype in interactions.PLAYBOOK'); _cli/_common.py (resolve_agent_addr(item_type: ItemType -> str), _SLUG_LOOKUP keyed by literal 'role'/'skill'/'operator'); _cli/_role.py, _cli/_skill.py, _cli/_operator.py (pass literal strings to resolve_agent_addr, dropped the now-unused ItemType import); _cli/_role.py's three 'sorted(t.value for t in allowed_create_types(...))' -> 'sorted(allowed_create_types(...))' (allowed_create_types now returns set[str]). Left ItemType imports/usages alone everywhere they reference the three meta-types by literal name (_backend.py:'item.type == ItemType.SKILL', _cli/_dev.py, _maintenance.py's ItemType.SKILL.folder/.prefix and _scan_for_check's built-in/custom folder-scan split) — those are meta-name-constant and type-axis-deletion territory (TASK-328/330), not this task's playbook/CLI-registration scope.
  - Tests: fixed breakage from PLAYBOOK/CREATE_LANES/etc. becoming str-keyed (item_type.value on what is now a plain str) in tests/test_skills.py, tests/test_playbook.py (incl. the two direct _build_spec(raw, catalog) calls, which now need a third bundled_spec() arg), tests/test_lane_derivation.py. No new test files added — ST1's F4 fallback and ST2's generic registration are already covered by the existing test_custom_type_cli.py/test_custom_type_create.py/test_custom_type_skill.py/test_reserved_types_invariants.py suites (which pass unmodified), plus the live end-to-end smoke above.
  - Gates: uv run pyright (0 errors) + uv run ruff check . (all checks passed) + uv run ruff format --check . (161 files already formatted) all green. Targeted tests run (not the full suite, per instructions): test_playbook, test_lane_derivation, test_reserved_types_invariants, test_custom_type_cli, test_custom_type_create, test_custom_type_skill, test_skills, test_spine_characterization, test_golden_rendered_output, test_title_advisory, test_aliases, test_backend_agents_md, test_backend_claude, test_backend_conformance, test_cli, test_multi_active_backends, test_role_catalog, test_role_resolver, test_skill_migration, test_skill_seeding, test_status_banner_check, test_unwritten_subentity_body_check, test_workflow_lint, test_workflow_override, test_override_commands, test_bug_workflow, test_collab, test_migration_corpus, test_remove, test_retype, test_service, test_session_lineage, test_golden_json, test_reflog_read, test_workflow_authoring_prose, test_operators — all green (exit 0 on every batch). Did NOT run the full suite (~4 min, main loop's job per CLAUDE.md) — @tech-lead please run it as the closing gate before merging release/0.8.
  - No source/test edits touched .squads.json or squads/*.md by hand; nothing committed (operator reviews first, per working rules).
- [2026-07-08T09:06:49Z] Elias Python:
  - Ref-hygiene fix per @manager: reworded the two flagged comments in src/squads/_services/_base.py (lines documenting SUBENTITY_PARENT/SUBENTITY_KIND) to drop the 'ADR-322 §4' and 'FEAT-212' squad-item references while keeping the explanation — now reads '...instead of a hand-maintained literal dict...' / '...are a deferred non-goal, so this stays keyed off the bundled spec...' with no ticket IDs.
  - Swept the rest of the diff: git diff --unified=0 -- src/ tests/ | grep -nE '(ADR|FEAT|TASK|BUG|EPIC|REV|DOC|SKILL)-[0-9]' is clean — no other leaks in src/ or tests/ (the only hits in the full untargeted diff are inside squads/**.md and .squads.json, which is the allowlisted location).
  - Gates: uv run pytest tests/test_squad_ref_hygiene.py -q passes (5 passed); uv run pyright (0 errors) + uv run ruff check . (all checks passed) + uv run ruff format --check . (161 files already formatted) all green. Did not run the full suite (main loop's job) and nothing committed.
  - TASK-329 left in InReview.
- [2026-07-08T09:10:02Z] Catherine Manager:
  - CLI type-listing order decided by op-pierre: an explicit integer 'order' field on each [items.*] in the spec, with alphabetical (by type name) as the tiebreaker on an order collision.
  - Rationale: the bundled default preserves today's logical sequence (epic->feature->task->bug->decision->review->guide) rather than switching to bare alpha; custom/project types slot in by their declared order; ties fall back to name. This is faithful to the 'identical CLI surface' criterion and realizes the ADR-322 'deterministic spec order, not TOML insertion order' mandate concretely. Supersedes the interim bare-alphabetical choice in the first pass of this task.
- [2026-07-08T09:20:14Z] Elias Python:
  - Explicit CLI order field (operator decision, superseding the interim alphabetical order): added ItemSpec.order (src/squads/_workflow/_models.py) as a float, default math.inf — an omitted order sorts a type after every explicitly-ordered one, then alphabetically among themselves (final design after two refinements: started as int/1000 sentinel, then float for fractional insertion, then +inf to drop the arbitrary sentinel entirely).
  - src/squads/_workflow/default_workflow.toml: every [items.*] now declares order, gapped by 10 so future insertion is easy (including fractional): epic=10, feature=20, task=30, bug=40, decision=50, review=60, guide=70, then the meta types role=80, skill=90, operator=100 (registered via their own subcommands, not this loop, but given values for completeness). Values parse as floats via pydantic coercion (verified: spec.items['epic'].order == 10.0, type float).
  - src/squads/_cli/__init__.py and src/squads/_cli/_create.py: the registration sort key is now sorted(work_types(), key=lambda t: (spec.items[t].order, t)) in both the resource-group loop and the _CREATABLE tuple derivation; inline docs updated to describe explicit-order-then-alpha instead of bare alphabetical. Live-verified: sq --help and sq create --help now list epic, feature, task, bug, decision, review, guide in that logical order (not alphabetical).
  - Confirmed no JSON-serialization hazard: grepped for model_dump_json/--json paths touching WorkflowSpec/ItemSpec — none exist (sq workflow has no --json; sq override list/diff --json emit override-file metadata and text diffs only, never a structured ItemSpec dump), so the float('inf') default can never hit a JSON encoder today.
  - Test added: tests/test_workflow_capability_flags.py — test_order_is_float_with_gapped_values_and_logical_sequence (bundled sequence + gaps), test_order_omitted_defaults_to_positive_infinity, and test_fractional_custom_order_sorts_between_two_bundled_types (a synthetic 'incident' type with order=35.5 sorts strictly between task(30) and bug(40) under the same (order, name) key the CLI uses — also documents that the CLI's lazy dynamic-dispatch path for project-declared custom types is unaffected by order and still appends them alphabetically after the static set, since that path wasn't in scope of this change).
  - Watch-outs checked: no golden/spec test pins ItemSpec's field set or default_workflow.toml's raw byte content (only import-time-loadable + a few spot-checked flags), so adding  didn't break anything there; scripts/gen_template_manifest.py only hashes *.md.j2 under _rendering/templates/ — default_workflow.toml is untouched by that mechanism. No squad-item IDs in the new source/test comments (checked via the same grep gate as before).
  - Gates: uv run pyright (0 errors) + uv run ruff check . (all checks passed) + uv run ruff format --check . (161 files already formatted) all green. Targeted: test_workflow_capability_flags, test_workflow_spec, test_workflow_lint, test_workflow_override, test_workflow_renderer_261, test_workflow_authoring_prose, test_cli, test_custom_type_cli, test_custom_type_create, test_custom_type_skill, test_custom_type_paths, test_aliases, test_lane_derivation, test_reserved_types_invariants, test_playbook, test_prefix_resolver, test_override_commands, test_squad_ref_hygiene — all pass (exit 0). Did not run the full suite; nothing committed. TASK-329 left in InReview.
- [2026-07-08T09:20:38Z] Elias Python:
  - Correction to the previous comment's watch-outs bullet (a backtick around the word order got eaten by the shell as command substitution, leaving a gap in the text): it should read '...so adding the order field didn't break anything there...'. No content change, just a transcription artifact.
- [2026-07-08T09:28:43Z] Catherine Manager:
  - Correction to the earlier order-field note: the field landed as FLOAT (not int), default +inf for an omitted order (no sentinel). Final shape: ItemSpec.order: float = math.inf; bundled default_workflow.toml orders work types 10-70 (epic->guide) + meta 80-100; CLI sort key (order, type_name). Full suite green on the final combined diff (exit 0, clean progress).
- [2026-07-08T09:32:09Z] Paul Reviewer:
  - APPROVE — independent review of the working-tree diff (src/ + tests/). Reran gates myself: pyright 0 errors, ruff check clean, ruff format clean (161 files); targeted suites green (test_workflow_capability_flags, test_playbook, test_lane_derivation, test_squad_ref_hygiene, test_skills, test_custom_type_{cli,create,skill}, test_reserved_types_invariants). Live: sq --help / sq create --help list epic,feature,task,bug,decision,review,guide in that exact (pre-change) order; role/skill/operator correctly absent from sq create; sq check clean.
  - Verified against scope: (1) Single-path registration confirmed — _STATIC_TYPES/_CREATABLE both derive from _bundled_spec().work_types(), the _builtin_work_type_names/_ORDERED_WORK_TYPES/hardcoded ItemType tuple are gone, PLAYBOOK is str-keyed, F4 fallback boundary is uniformly 'ctype not in interactions.PLAYBOOK'. (2) Deterministic order = (spec.items[t].order, t) in BOTH _cli/__init__.py and _cli/_create.py; bundled 10-70 preserves the logical sequence, +inf default sorts omitted last, fractional insert proven by test; meta types (order 80-100) excluded via work_types() is_meta filter — not pulled into the work-type CLI. (3) SUBENTITY_PARENT/KIND rederive from bundled spec; check helpers route through self.spec (active) — behavior-identical for the default squad. (4) Scope discipline OK — ItemType/Status enums untouched, meta refs left as literals, change is behavior-preserving. (5) No new mutable global state (compute-once constants), no import cycle (_models/_workflow clean; _loader→_workflow edge pre-existed), zero squad-id leaks in added lines, e()-escaping unaffected. (6) CLI surface + skills identical apart from the intended ordering.
  - One LOW / forward-looking note (non-blocking): WorkflowSpec.item_subentity_kind does 'self.items[item_type].subentity_kind' — a raw index that KeyErrors on a type absent from the active spec, whereas the old SUBENTITY_KIND.get(item.type) returned None. Behavior-preserving today (every index item type, incl. meta, is in spec.items → None), but once FEAT-281 adds type rename/drop, an item whose type was dropped from the active spec would make 'sq check' crash rather than 'cleanly lose the check' as ST3 intends. Suggest a guarded lookup (self.items.get(item_type) → None) so the de-typing work inherits graceful degradation. Not required for this task's merge.
- [2026-07-08T09:56:21Z] Elias Python:
  - Reviewer finding addressed: WorkflowSpec.item_subentity_kind (src/squads/_workflow/_models.py) no longer does a raw self.items[item_type] index — now ts = self.items.get(item_type); return ts.subentity_kind if ts else None. Return type unchanged (str | None); docstring updated to say it degrades gracefully for a type not declared in the spec instead of raising KeyError.
  - Verified all three sq-check callers in src/squads/_services/_maintenance.py already handle a None result correctly, no papering over needed: line 1033 (_check_subtask_stories) compares != 'subtask' so None just continues; lines 1064/1125/1199 (_check_subentity_status, _check_unwritten_subentity_bodies, _check_subentity_title_lengths) each assign kind = self.spec.item_subentity_kind(...) immediately followed by an explicit 'if kind is None: continue' guard. No misbehavior found.
  - Test added: tests/test_workflow_capability_flags.py::test_item_subentity_kind_returns_none_for_unknown_type — asserts item_subentity_kind('not-a-real-type') is None, next to the existing subentity_kind tests.
  - Gates: uv run pyright (0 errors) + uv run ruff check . (all checks passed) + uv run ruff format --check . (161 files already formatted) all green. Targeted: test_workflow_capability_flags, test_workflow_spec, test_status_banner_check, test_unwritten_subentity_body_check, test_title_advisory, test_spine_characterization, test_custom_type_cli, test_custom_type_create, test_squad_ref_hygiene — all pass. Squad-item-ID hygiene grep on the diff also clean. Did not run the full suite; nothing committed. TASK-329 left in InReview.
<!-- sq:discussion:end -->
