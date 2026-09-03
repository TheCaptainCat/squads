---
id: TASK-720
sequence_id: 720
type: task
title: Playbook override loader resolved on the request context
status: Done
parent: FEAT-714
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-696:implements
- EPIC-538
- TASK-716:depends-on
- FEAT-533
description: Fourth override kind plus the per-request merged playbook seam; bundled
  stays immutable
subentities:
- local_id: ST1
  title: Playbook loader over the shared merge engine
  status: Done
  story: US1
- local_id: ST2
  title: Merged playbook resolved on the request context
  status: Done
  story: US2
- local_id: ST3
  title: Thread every playbook consumer onto the merged spec
  status: Done
  story: US2
- local_id: ST4
  title: sq override gains the playbook as a fourth kind
  status: Done
  story: US3
created_at: '2026-07-31T13:37:37Z'
updated_at: '2026-08-03T15:47:55Z'
---
<!-- sq:body -->
## What to build

Give the playbook — `playbook.toml`, the spec saying which role guidance attaches to which
item type — a project override (`.overrides/playbook.toml`), the one bundled spec still left
out of the `.overrides/` subsystem, and resolve the **merged** playbook per request so that
override composes and coverage-validates against the project's own active type set rather than
the bundled one.

Two halves, and the second is not optional. A merged playbook that still lives in an
import-time singleton would be composed against, and coverage-checked against, the bundled
type set — which makes the override wrong in exactly the case it exists for.

The merge itself is not written here: the shared engine (`src/squads/_specmerge.py` — splat
resolution, deep recursive merge, `selected` apply/strip plus its provenance record, fail-fast
and collect-all modes, all over raw `dict[str, Any]` mappings) is a dependency. This task
builds the playbook loader on it and threads the result.

## The seam: bundled stays module-level, merged lives in the request context

This is settled and confirmed; build it, do not re-derive it.

- **The bundled playbook stays a module-level immutable.** `_interactions/__init__.py`'s
  `_PLAYBOOK_SPEC` remains the code default, loaded once at import, exactly as it is today. It
  is CODE by the project's own triage rule: an immutable spec loaded once and safe to share
  across every request. Do not remove it, do not make it lazy, do not make it rebindable.
- **The merged (override-applied) playbook becomes a per-request value**, resolved onto the
  same request-scoped container the active `WorkflowSpec` already uses:
  `_context.RequestContext` (a frozen dataclass behind one `ContextVar`, seeded at the CLI edge,
  read only through accessor functions). Add a field with a default, the way that container is
  designed to be extended — adding one must not touch existing fields or call sites. **No new
  module-level mutable singleton, and no second ambient mechanism.**
- The accessor pattern to follow is the existing one: nothing below the service layer reads the
  `ContextVar` directly; call sites go through a function that returns the merged playbook when
  one is bound and the bundled immutable otherwise. That fallback is what keeps every existing
  caller — including the ones with no spec handle — working unchanged.

## The loader

A playbook loader built on the shared engine: bundled base mapping + `.overrides/playbook.toml`
→ merged mapping → the existing `_interactions/_loader.py` model build and validation. Points
that are fixed by the governing decision:

- **Single file with keyed tables**, like the workflow override — not a per-slug file like
  roles. The playbook is one referentially coupled document: an entry references role slugs and
  a type name, and a single `override_base` stamp over a scattered graph would be meaningless.
- **Splat-refs are the entry point for adding a custom role's guidance** to a type's entry:
  `roles = ["$(*self)", { slug = "my-role", … }]` inherits every bundled guide for that type
  and adds one. This must use TOML's **inline-array** form — the `[[types.<t>.roles]]` header
  form has no slot for a token. Heterogeneous string-and-table arrays are valid TOML 1.0 and
  `tomllib` accepts them, so drive at least one test off a real parsed override string rather
  than a hand-built dict.
- **No independent deselect for the playbook.** Its active type set is *derived*, not
  declarable: the coverage rule already requires exactly one entry per active non-roster type,
  so dropping a type from the workflow spec drops its playbook entry as a consequence. Do not
  add a `selected.playbook_types` key or any equivalent.
- **Coverage validates against the active workflow spec**, not the bundled one:
  `_check_coverage` already takes a `WorkflowSpec` and reads `non_roster_types()` — it must
  receive the merged spec on the request path. A type dropped by a workflow override must not
  produce a coverage false positive, and a project-declared type must be satisfiable by a
  project playbook entry.
- **Splat resolution and `[selected]` stripping complete before model validation** —
  `ItemPlaybookSpec`/`RoleGuideSpec` set `extra="forbid"` and are strictly typed, so a token or
  a stray table sitting where a typed value is due would be rejected as a type error before it
  could be resolved.
- Role-slug referential integrity keeps its current shape: every guide slug must be in the role
  catalog, with the `*dev` sentinel exempt.

## The consumers to thread

Every site that reads playbook coverage or role/skill guidance for a type must read the
per-request merged playbook, so a project with an override sees its own guidance and a project
without one sees exactly today's bundled behaviour. The full set, all currently reading the
module-level `PLAYBOOK` dict or a constant derived from it:

- `_interactions/__init__.py` — `PLAYBOOK` itself and everything derived from it:
  `managed_item_types`, `item_types_for_role`, `skills_for_role`, `bundled_skill_slugs`,
  `custom_skill_slugs`, `is_system_skill`, `SKILL_DESCRIPTIONS` / `skill_description`,
  and the `authoring_owner` / cheatsheet helpers.
- `_backends/_claude_code/_backend.py` — the rich per-type skill writer and the thin
  custom-type skill path; `_backends/_agents_md/`; `_backends/_base.py::resolved_skills_for`.
- `_services/_base.py` and `_services/_maintenance.py` — skill seeding, the system-skill
  membership union, and custom-type skill creation.
- `_services/_config_integrity.py` — the implied-skill floor per live role. Note the standing
  comment there that `item_types_for_role` reads the bundled singleton and never the active
  spec: that observation becomes stale with this change, so re-read the surrounding logic and
  update or delete the note rather than leaving it to mislead.
- `_services/_roster.py` — the skills stamped onto a generated roster entry.
- The `sq workflow` cheatsheet rendering (`_rendering/templates/workflow.md.j2` and its CLI
  caller).
- **Migration runners are exempt and must stay exempt.** A runner transforms a corpus written
  at a pinned schema version, so it reads the vocabulary that version used, never the live
  spec. `_migrations/_v0_4_to_v0_5.py` and `_v0_8_to_v0_10.py` call `bundled_skill_slugs()` /
  `skill_description()` deliberately — leave them on the bundled path.

## `sq override` as a fourth kind

The playbook joins workflow, roles, and templates in `_overrides/_service.py` and
`_cli/_override.py`: scaffold, list, diff, and update, with the same `override_base` drift stamp
and the same verb shape an adopter already knows for the workflow override. Mirror the workflow
kind rather than inventing a shape — including its `OverrideEntry` kind string, its scan entry,
its `diff` delta pair, and its `update` re-stamp path — and give the scaffold a commented worked
example that actually parses, the way the workflow scaffold does.

## Acceptance

- Appending one role guide to one type takes **one line** (`$(*self)` plus the addition), not a
  restated list — and a later change to that type's other bundled guides flows through on the
  next load with the override untouched.
- `sq override scaffold` / `diff` / `update` handle the playbook end to end, including the
  `override_base` drift warning and `sq override list` reporting its state.
- Two concurrent requests against two differently-customized squads each see their own merged
  playbook and neither observes the other's — proven the same way the active workflow spec's
  per-request isolation is proven today (concurrent tasks, distinct bound contexts, assert
  both directions).
- With no `.overrides/playbook.toml` present, behaviour is **byte-identical to today**: the
  bundled playbook, the same generated skill bodies, the same pointer files. The existing
  playbook golden and the generated-skill goldens are the instrument — assert, do not assume.
- Dropping a type via a workflow override removes its playbook coverage requirement as a
  consequence, with no separate declaration and no coverage false positive.
- Nothing new is a module-level mutable singleton; the bundled playbook is still the
  module-level immutable it is today.

## Testing

Service-level and unit tests plus a CLI smoke test for each new `sq override` verb.

Cover: the one-line append via a real parsed inline-array override; a shadowed guide field
leaving that guide's other fields intact; an override for a project-declared type; coverage
satisfied and coverage violated; the concurrency isolation case; the no-override byte-identity
case; each `sq override` verb on the playbook kind; the fallback path where no context is bound
(the bundled playbook is returned, not an error).

**Falsify each test before handing back.** Break the implementation it covers, watch it go red,
restore it, and report both directions in this task's discussion. The concurrency test in
particular is worthless unless you have seen it fail against a singleton — force the merged
playbook into a module global, watch it go red, then restore.

`tests/meta`'s module-level mutable-state guard fires on any new module-level dict or list — if
one is genuinely a constant, allowlist it as a CODE constant with a one-line reason rather than
restructuring around the guard. Run `tests/meta` before handing back.

## Conventions

- No `from __future__ import annotations` (Python 3.14 / PEP 649); keep the import graph
  acyclic. `_context` sits below `_clock`/`_actor` and must not gain a runtime import of a
  module above it — use `if TYPE_CHECKING:` plus a string annotation, as its existing
  `WorkflowSpec` annotation does.
- Type aliases use PEP-695 `type X = …`, never bare assignment.
- No `eval` and no user-supplied code path — splat-refs are a closed-grammar path splice.
- Every user-facing failure subclasses `SquadsError` and fails closed; never a traceback.
- Name tests by behaviour. No ticket or item IDs in `src/` or `tests/`, including filenames.
- Strict gate, with the extras on every command:
  `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .`
  A bare `uv run` prunes the optional `tui` extra and floods pyright with false import errors.
- `sq check` clean before handing back.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 720 add-subtask "<title>"`; track with `sq task 720 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Playbook loader over the shared merge engine

<!-- sq:subtask:ST1:body -->
Built: `_interactions/_loader.py` extends `load_playbook(catalog, spec=None, squad_dir=None)` — merges `.overrides/playbook.toml` over bundled raw via the shared engine (single top-level section `types`, empty selected-sections set so any `[selected]` table is refused, no independent deselect). Coverage validates against the passed-in `spec` (the active/merged workflow spec on the request path); a new `_base_raw_for(spec)` filters the bundled base's `types` table to `spec.non_roster_types()` BEFORE merging, so a type dropped via a workflow override never surfaces as a coverage false positive. Also fixed a scope bug found while falsifying: the 'missing entry' coverage direction is now scoped to bundled type names only — a project-declared type with no playbook entry is the existing thin-skill fallback, not a violation.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-08-03T10:07:54Z] Elias Python:
  - Falsified: broke the append-idiom test by removing $(*self) handling — red, then restored; broke coverage scoping — the pre-existing custom-type-via-workflow-override test went red (missing required work-type entry), confirming the scope fix was needed and correct.
  - sq check clean; pyright/ruff clean; tests/unit/test_playbook_override_merge.py (17 tests) all pass.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Merged playbook resolved on the request context

<!-- sq:subtask:ST2:body -->
Built: `_context.RequestContext` gains `active_playbook: PlaybookSpec | None = None` (TYPE_CHECKING import, mirrors `active_spec`). `_interactions/__init__.py::get_active_playbook_spec()` is the one accessor — reads the context, falls back to the bundled `_PLAYBOOK_SPEC` singleton when unbound. `Service.playbook: PlaybookSpec` (ServiceCore.__init__) is the threaded-below-the-edge carrier (ADR-249's shape, same split as Service.spec), resolved by a new `_services/_service.py::resolve_playbook(spec, squad_dir)` — a zero-reparse fast path when spec is the untouched bundled singleton AND no override file exists, else `load_playbook(...)`. Wired into `init`/`adopt`/`open_service`. CLI edge: `_cli/__init__.py::_bind_active_playbook` binds it into the RequestContext alongside active_spec in `main_callback`, mirroring `_bind_active_spec` exactly. The bundled `_PLAYBOOK_SPEC`/`PLAYBOOK` stayed completely untouched (no removal, no laziness, no rebinding).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-08-03T10:08:10Z] Elias Python:
  - Falsified per the task's explicit instruction: forced get_active_playbook_spec() to ignore the context and always return the bundled singleton (a stand-in module global) — both the direct-binding test and the concurrent-tasks test went red (asserting True got False), then restored and re-confirmed green. tests/service/test_context_playbook_isolation.py (5 tests, incl. concurrent asyncio-task isolation and a bundled-immutability check) all pass; tests/meta's mutable-state guard stays clean (no new module-level dict/list — only frozensets, already an allowlisted pattern elsewhere).
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Thread every playbook consumer onto the merged spec

<!-- sq:subtask:ST3:body -->
Threaded the active/merged playbook (default-arg, bundled-blind unless a caller passes it — same contract as WorkflowSpec) through every named consumer: _interactions/__init__.py (managed_item_types, item_types_for_role, skills_for_role, bundled_skill_slugs, custom_skill_slugs, is_system_skill, orphaned_skill_item_type all gained an optional playbook param); _backends/_base.py::BackendContext gained a playbook field, resolved_skills_for threads it; _backends/_claude_code/_backend.py's rich-vs-thin skill-writer split now reads ctx.playbook instead of the bundled PLAYBOOK global; _services/_base.py (ServiceCore.playbook + every BackendContext construction + skills_for_role call), _services/_maintenance.py (seed_bundled_skills/seed_custom_skills/orphan detection/ValidatorEngine construction), _services/_roster.py, _services/_config_integrity.py (check_all/check_preloaded_skill/_always_on_floor gained the param), _services/_validators.py (SquadGlobalContext + ValidatorEngine gained it), _services/_retirement.py::enforce, _services/_items.py, _services/_import.py, _cli/_skill.py all thread it. Simplified skill_description() to compute the generic per-type description on the fly (same template custom_item_skill_description already used) instead of a PLAYBOOK-keyed lookup table, so a type gaining coverage via override needs no dict entry added. Audited (no change needed, confirmed via read + tests): authoring_owner/cheatsheet_anchor_* and the sq workflow cheatsheet (workflow.md.j2 + _cli/_workflow_cmd.py) never read PLAYBOOK content at all — only CREATE_LANES/spec — so they're playbook-content-invariant by construction. Migration runners (_v0_4_to_v0_5.py, _v0_8_to_v0_10.py) untouched: they call the same functions with no playbook arg, which is the bundled default — the exemption falls out of the default-arg design, not a special case.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-08-03T10:08:36Z] Elias Python:
  - Falsified: reverted item_types_for_role's playbook arg in check_preloaded_skill's implicating_types computation to None — the new type_implied consumer test went red (expected True, got False), then restored.
  - Byte-identity established two ways: (1) fresh-init'd throwaway squad (roles=all + one dev, frozen clock/session), full artifact set hashed (44 files incl. .claude/, CLAUDE.md, every role/skill body) at HEAD vs with every change applied — diff exit 0, zero bytes differ. (2) A second regeneration after a later coverage-scoping fix, re-diffed against the same HEAD snapshot — still exit 0. (3) Positive-effect check: same fresh-init flow WITH a pre-placed .overrides/playbook.toml appending an architect guide to task — sq-task's generated body carries the new lines + the role's full name once reopened through open_service; the same body is unchanged with no override present (tests/integration/test_playbook_override_consumers.py, 4 tests).
- [2026-08-03T10:27:58Z] Elias Python:
  - Follow-up from @manager's full-suite run: tests/service/test_dropped_type_skill_orphan_is_withdrawn_and_flagged.py (3 tests) was red at e2e3640+changes. Root cause: is_system_skill/orphaned_skill_item_type got a playbook default that, once threaded with the caller's MERGED (spec-filtered) playbook, defeated bundled_skill_slugs()'s deliberate bundled-blindness — the exact property orphan-reclaim depends on (a renamed/dropped built-in's OLD name is filtered OUT of the merged playbook by design, so a caller-supplied merged value there makes the stale slug invisible to reclaim, letting it silently outlive the type it described).
  - Fix: removed the playbook parameter entirely from bundled_skill_slugs/custom_skill_slugs/is_system_skill/orphaned_skill_item_type (4 functions) — not a defaulting fix, a scope fix: these four must never vary with a caller-supplied playbook, required or optional, because the seeding-order/reclaim question they answer is orthogonal to override content (that axis is served entirely by managed_item_types(playbook), used directly at the one call site that needs it: the backend's rich-vs-thin writer). Updated the 6 call sites that had threaded self.playbook/svc.playbook into these four.
  - Audited every remaining playbook-defaulted call site (grep across src/squads for every consumer of managed_item_types/item_types_for_role/skills_for_role) — all thread self.playbook/ctx.playbook correctly; none rely on the default in production. Re-verified: the 3 originally-failing tests pass; byte-identity re-established (diff exit 0 against the same HEAD snapshot); the positive-effect consumer tests (override actually reaching generated content) still pass.
  - Falsified via an env-var-gated probe reproducing the exact reported defect (thread the merged/filtered playbook into is_system_skill's bundled leg) — all 3 tests went red with the identical assertions the manager reported, then the probe was fully removed and reconfirmed green; grepped the tree for probe residue after, zero hits.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — sq override gains the playbook as a fourth kind

<!-- sq:subtask:ST4:body -->
Mirrored the workflow kind exactly, in _overrides/_service.py + _cli/_override.py: OverrideEntry kind 'playbook'; scan_overrides gains a single-file entry (mirrors the workflow entry, same STATE_CURRENT/DRIFTED contract, TOML has no markers so never BROKEN); scaffold_playbook writes the stamp + a commented worked example that IS the append idiom ('roles = ["$(*self)", {...}]'); _diff_playbook gives the same Delta-mine (vs bundled_playbook_toml_text())/Delta-upgrade (stamp-vs-running-version) pair, degrading the same way on no/stale stamp; update_stamp's _update_one/_update_all gained the playbook branch; check_override_issues gained _check_playbook_override_issues, sharing playbook_stamp_finding's decision shape with workflow_stamp_finding via the same three-state contract (shadow+unstamped=error, stale stamp=warn, add-only+unstamped=nothing). CLI: --playbook flag alongside --workflow on scaffold/diff/update, plus the bare positional 'playbook' name form; list already generic. Unknown-kind error message now names playbook among the accepted kinds.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-08-03T10:08:55Z] Elias Python:
  - Falsified: point-removed the playbook branch from diff_override's dispatch — the CLI smoke test (scaffold/diff/update reaching the playbook kind) went red with 'unknown override kind', then restored.
  - TestPlaybookOverride (9 tests, tests/integration/test_override_scaffold_scan_diff_update_and_check.py) covers scaffold+refuse-clobber, scan state transitions, diff (present/absent/stale/unstamped), update (single+bulk), check (clean/stale-warn/shadowing-no-stamp-error/add-only-no-stamp-clean). CLI smoke (tests/cli/test_override_commands_cli.py) covers scaffold/list/diff/update end to end plus the plain-output label branch. Unknown-kind test extended to assert 'playbook' is named in the message.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T10:09:14Z] Elias Python:
  - All four subtasks Done. Seam: bundled _PLAYBOOK_SPEC/PLAYBOOK stay the module-level immutable, byte-untouched; the merged playbook lives on RequestContext.active_playbook (per-request) and Service.playbook (threaded-below-the-edge), resolved via _services/_service.py::resolve_playbook. No independent [selected] for the playbook (refused, not silently accepted) — coverage is derived from the active workflow spec.
  - Design correction found while falsifying (not in the original brief): coverage's 'missing entry' check must be scoped to BUNDLED type names only, never to a project-declared one — else 'add a custom type via a workflow override with no matching playbook entry' (a pre-existing, sanctioned thin-skill-fallback pattern) would become a hard open_service failure the moment this feature landed. Fixed in _interactions/_loader.py::_check_coverage; covered by tests/unit/test_playbook_override_merge.py.
  - Byte-identity with no override present: established by a whole-artifact SHA-256 diff (44 files: CLAUDE.md, .claude/, every role/skill body) between a fresh-init'd throwaway squad at HEAD vs with every change applied, frozen clock/session for determinism — zero bytes differ, re-verified after the coverage fix above.
  - For @tech-writer (docs/overrides.md): add the fourth override kind (playbook) alongside workflow/roles/templates — same scaffold/diff/update/list verbs, same override_base stamp. State the limitation plainly: the bundled playbook carries ~50 cross-type command references (e.g. the feature skill telling a product-owner to `sq create task`); renaming or dropping a type leaves those references stale inside a SURVIVING type's skill until the adopter also overrides the playbook (the append idiom — one line — is the fix, not a restated list). This is a documented limitation, not something engineered around: no templating, no placeholder DSL. Making the playbook overridable IS the remedy — say that, and point at `sq override scaffold playbook`.
- [2026-08-03T10:28:13Z] Elias Python:
  - Design question answered: required-vs-optional is the wrong axis for is_system_skill/orphaned_skill_item_type specifically — required would not have caught this, since every real call site already passed a value (self.playbook); the defect was passing the WRONG value at a site that must never accept a caller override at all. Fixed by removing the parameter (stronger than making it required).
  - For the three functions where the merged playbook is genuinely wanted (managed_item_types, item_types_for_role, skills_for_role): audited every production call site (grep, not spot-check) — all already thread self.playbook/ctx.playbook explicitly; zero rely on the optional default. ~25 pre-existing unit tests deliberately call them bundled-only (playbook=None) for standalone testability, mirroring the spec: WorkflowSpec | None = None convention that predates this feature. Given no production site relies on the default and the test churn would be pure ceremony with no safety gain, I kept these three optional-defaulting-to-bundled rather than making playbook required-keyword-only — happy to make the change project-wide if you want the stricter contract regardless, but this incident doesn't provide evidence for it.
  - Separately, not fixed per instruction — the sq check / sq workflow lint mismatch: src/squads/_cli/_main.py's check() command (~line 1436) catches SquadsError from get_service() and unconditionally reports it as "workflow config invalid — run sq workflow lint". open_service() now also raises SquadsError from resolve_playbook() for a bad .overrides/playbook.toml (my change), and check() has no way to tell the two apart, so a broken playbook override gets the workflow's error label and points at a lint command that only ever inspects workflow.toml. Reproduced live: a malformed playbook.toml gives 'error workflow: workflow config invalid' from sq check, and sq workflow lint answers 'workflow spec OK — no override file found'.
  - Full targeted re-run: 512 passed (tests/meta + every new/affected file), pyright/ruff/format clean, sq check clean, byte-identity re-confirmed. TASK-720 left InProgress.
- [2026-08-03T10:38:47Z] Elias Python:
  - Fixed the sq check misrouting per @manager's correction: FEAT-714's own scope, not a separately-filed bug. Root cause was exactly what I'd flagged — open_service() raises a plain SquadsError from resolve_playbook() on a bad .overrides/playbook.toml, and _cli/_main.py's check() catches SquadsError generically and hardcodes the workflow message/pointer.
  - Shape: added PlaybookConfigError(SquadsError) (src/squads/_errors.py). resolve_playbook() (src/squads/_services/_service.py) now wraps the loader's failure in that subclass, naming the underlying violation plus the override file path (no invented command — nothing lints a playbook override today, so the message states what/where rather than pointing at one); both open_service call sites (the no-workflow-override fast path, which previously wasn't even wrapped, and the merged path) get this for free from one place. check() (src/squads/_cli/_main.py) now catches PlaybookConfigError before the generic SquadsError catch, emitting a separate 'playbook' CheckIssue; the workflow branch is untouched.
  - A dedicated playbook-lint surface (a lint_playbook mirroring lint_workflow_spec's collect-all/phased design) would be the honest longer-term answer for adopters who want more than a fail-fast message, but is a real feature addition (a new collect-all path through the loader + a CLI surface), not a small one — flagging as follow-up, not building it.
  - Falsified both fix points independently: reverted check()'s PlaybookConfigError branch alone -> 2 of 9 new tests red (message/JSON label wrong); separately reverted resolve_playbook()'s wrapping alone -> 5 of 9 red (exception type + open_service fast-path + check() together); restored both, reconfirmed 9/9 green. Verified both directions live via the CLI: a malformed .overrides/playbook.toml now gives 'error playbook: playbook config invalid: ... — see <path>' with sq workflow lint correctly reporting the workflow spec clean; a malformed .overrides/workflow.toml is unchanged — 'error workflow: workflow config invalid — run sq workflow lint', and lint shows the real error. New tests: tests/integration/test_check_distinguishes_playbook_and_workflow_config_errors.py (9 tests).
  - Full re-run: 554 passed / 0 failed (tests/meta + every new/affected file), pyright/ruff/format clean, sq check clean, byte-identity re-confirmed (diff exit 0 against the same HEAD snapshot). TASK-720 left InProgress.
- [2026-08-03T10:40:57Z] Catherine Manager:
  - Landed and verified by driving it. The acceptance criterion holds: an inline-array append adds one bullet in one line, bundled bullets go 20 to 21, sq check clean. Orphan sweep confirmed still firing after the reclaim-scope fix. Both error routes verified: a malformed playbook override reports error playbook with the real validation violation and no false pointer, and a malformed workflow override is unchanged. Full suite 2495 passed / 6 skipped, all gates clean.
- [2026-08-03T12:27:03Z] Elias Python:
  - Addressed all 8 findings from REV-735 (all Fixed, verdict was ChangesRequested). F1: threaded a project-role-override slug authority into the playbook loader's per-request path (bundled catalog union .overrides/roles/*.toml), so a custom activated role can now be given playbook guidance end to end. F2: sq check's PlaybookConfigError branch keeps the merged workflow spec (re-resolved via load_workflow_spec) instead of falling back to bundled, so a playbook-only break no longer masks itself as a phantom type/corpus error. F3/F5: fixed the scaffold's duplicating worked example + its false field-merge rule, and added a fail-closed duplicate-role-slug check to the loader. F6: the [selected] refusal on the playbook now states the real reason (derived coverage) instead of an empty accepted-sections menu. F4: dropped the dead RequestContext.active_playbook carrier (no production consumer, divergent failure semantics) -- Service.playbook is now the sole carrier. F7: made bundled-immutability real where it can be (MappingProxyType on PLAYBOOK; Mapping-typed PlaybookSpec.types for the pyright-level guarantee). F8: cached the bundled [types] key set so sq check-adjacent loads stop re-parsing the bundled TOML for it.
  - Every fix has a falsifying test that fails against the pre-fix code and passes against the fix (verified both directions by hand for each). Ran the whole targeted area (tests/unit + integration + service + meta + cli): 2484 passed, 1 skipped. sq check is clean. Gates (pyright, ruff check, ruff format) clean --all-extras. Did not run the full suite; leaving that to the main loop. Task stays InReview.
- [2026-08-03T15:47:54Z] Catherine Manager:
  - Review REV-735 Approved, all four subtasks Done, full suite 3076 passed. Closing on delegation: non-visual work, reviewed across three passes and independently verified.
<!-- sq:discussion:end -->
