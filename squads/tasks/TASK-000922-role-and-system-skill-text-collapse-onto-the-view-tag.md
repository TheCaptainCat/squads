---
id: TASK-922
sequence_id: 922
type: task
title: Role and system-skill text collapse onto the view tag
status: Done
parent: FEAT-906
author: tech-lead
assignee: python-dev
refs:
- ADR-880:implements
subentities:
- local_id: ST1
  title: 'Role view: source, template, tag-seeded scaffold'
  status: Done
  story: US1
- local_id: ST2
  title: Delete role_definition_text and the CLI's hardcoded branch
  status: Done
  story: US1
- local_id: ST3
  title: Backfill the tag into every existing role body
  status: Done
  story: US1
- local_id: ST4
  title: 'System-skill views: squads, greeting, sq-memory'
  status: Done
  story: US2
- local_id: ST5
  title: Seed the tag at skill-file creation; prove the three named branches equivalent
  status: Done
  story: US2
- local_id: ST6
  title: Backfill the tag into the three existing system-skill bodies
  status: Done
  story: US2
- local_id: ST7
  title: Consumer enumeration and generated-artefact diff
  status: Done
  story: US5
created_at: '2026-09-04T09:11:13Z'
updated_at: '2026-09-04T13:01:26Z'
---
<!-- sq:body -->
## Scope

Collapses US1 (role) and US2 (system skill) of FEAT-906 onto the source+template+tag mechanism
FEAT-903/905 shipped. Both share one shape: a hardcoded CLI branch calls a `ServiceCore` method
that renders a bespoke template at read time from a body region the service/backend deliberately
keeps empty. Both delete that branch and seed a `sq:view:<name>` tag into the body instead.

**Sequencing constraint, load-bearing — do not delete more than named below.**
`_cli/_skill.py`'s `if system:` branch and `ServiceCore.skill_definition_text`/
`_item_skill_definition_text` are the SAME seam a per-item-type skill uses
(`is_system_skill` covers both families with one discriminator). This task only replaces the
THREE named system-skill branches inside `skill_definition_text` (`SQUADS_SKILL`/
`GREETING_SKILL`/`MEMORY_SKILL`) with tag-based equivalents and proves them byte-equivalent — it
does NOT delete `skill_definition_text`, `_item_skill_definition_text`, or the CLI's `if system:`
branch. The per-item-type-skill task (depends-on this one) deletes all three wholesale once its
own mechanism lands, and collapses `skill_show` to one unconditional `read_body` call. Deleting
more than the three named branches here breaks every per-item-type skill until that task lands.

### Role (US1)

- New view `[views.role_definition] source = { kind = "role" }` +
  `templates/views/role_definition.md.j2`, carrying the prose `agents/role.md.j2`'s `sq:body`
  region holds today — rewritten to read `source.*`/`item`/`spec` instead of the bare `role`
  context var `role_definition_text` supplies today. `agents/role.md.j2` keeps only the file's
  frame (the panel-adjacent markers, the `## Discussion` heading); its `sq:body` region seeds the
  tag `sq:view:role_definition` instead of empty text.
- `ServiceCore._create_core`'s role branch (`_services/_base.py`, the
  `sections.replace_section(rendered, markers.BODY, "")` line) seeds the tag instead of blanking
  to `""`.
- Delete `_cli/_role.py`'s `if it is not None and r is not None:
  render_body_text(svc.role_definition_text(r), raw=raw)` branch and `ServiceCore
  .role_definition_text` outright; `show_role` reads the body generically
  (`await svc.read_body(it.id)`, tag-expanded) the same way a non-role item already does.
- **Backfill, licensed on ADR-880 problem 1's model even though a role body is never authored.**
  `set_body` refuses a role body unconditionally today, so there is no "an author's deliberate
  removal" to protect against — unlike milestone's body, the tag can safely converge on every
  repair without reopening problem 2. Generalize `_sweep_empties_body`'s repair behaviour: for a
  role item, `sq repair` normalizes `sq:body` to carry exactly `sq:view:role_definition`
  (idempotent — an already-tagged body is untouched) instead of emptying it to `""`. This
  retrofits every already-activated role in an existing squad, this repo's own roster included,
  in one `sq repair` run. Report the count changed, the way the sweep already reports other
  repairs.

### System skills — squads, greeting, sq-memory (US2)

- New views: `[views.squads_skill] source = { kind = "playbook" }` — `name` deliberately unset,
  so it resolves against the host's own type, which for a skill item is the roster type `skill`;
  `playbook.types.get("skill")` is correctly `None` and unused, and `PlaybookSource.roster` is
  populated unconditionally regardless — that is what gives `squads_skill.md.j2`'s
  `example_assignee_slug(source.roster)` call live roster data with no widening of `self`.
  `[views.greeting_skill] source = { kind = "self" }`, `[views.memory_skill] source = { kind =
  "self" }` — neither needs the roster, only `squad_dir`.
- Widen `render_source_view` (`_views.py`) to pass `squad_dir` in context for every source kind,
  not `self` alone — already in hand at the one call site, costs nothing, and removes a special
  case rather than adding one. This is what lets a `playbook`-sourced template
  (`squads_skill.md.j2`) reach `{{ squad_dir }}` the same way a `self`-sourced one does.
- Move `agents/squads_skill.md.j2`/`greeting_skill.md.j2`/`memory_skill.md.j2`'s content into
  `templates/views/squads_skill.md.j2`/`greeting_skill.md.j2`/`memory_skill.md.j2`, rewritten
  against `source`/`item`/`spec`/`squad_dir` (`source.roster` replaces the bare `roles` context
  var for squads_skill; `source.lane` is unused by any of the three).
- `_backends/_claude_code/_backend.py::_write_managed_skill`'s `empty_body` constant becomes
  tag-seeding, keyed by which of the three system slugs is being written. The existing "first
  write only, an existing region is left byte-untouched" discipline stays — this only seeds NEW
  files.
- In `ServiceCore.skill_definition_text`, replace the three named branches
  (`if slug == GREETING_SKILL: ...` / `MEMORY_SKILL` / `SQUADS_SKILL`) with a proof that
  `read_body` on that slug's item, tag seeded, renders byte-identical output to what the branch
  renders today. Do not delete the method itself or the branches that still route to it for
  per-item-type skills.
- **Backfill.** Extend the repair sweep (or a sibling corpus walk run from the same `sq repair`
  pass) to insert each system skill's tag into its existing body file when
  `is_system_skill(slug, spec)` names one of the three system slugs and the on-disk body is
  empty (assert that invariant rather than assume it — never touch a non-empty body). Covers
  this repo's own three system-skill files. Idempotent, reports the count.

## Acceptance

1. **Enumerate the consumers, each proven still working, before either branch deletes.**
   `sq role show` / `--raw` / `--json`; `sq skill show squads|greeting|sq-memory` / `--raw` /
   `--json`; the TUI reader (`_tui/_reader.py`); `.claude/agents/<slug>.md` role pointers
   (confirm — driven, not asserted — they read `RoleDef` fields directly and never called
   `role_definition_text`, so they're unaffected); `.claude/skills/<slug>/SKILL.md` pointers for
   the three system skills (confirm they render from slug + description alone); the AGENTS.md
   backend's role/skill sections (confirm they read `RoleView`/static prose, never the deleted
   methods); every docstring in `_services/_maintenance.py`, `_services/_items.py`,
   `_services/_base.py` citing `role_definition_text`/`skill_definition_text` by name — updated
   to describe the new mechanism, never left pointing at a name that no longer exists there.
2. **Generated-artefact before/after diff, roster held constant.** `sq sync` output
   (`.claude/` pointers, managed skill files, the `sq:body` regions the backfill touches) for
   every bundled role and the three system skills, diffed before/after on the SAME roster (a
   dev-less fresh init vs. this repo's dev-bearing roster gives a false "regression" — hold the
   roster fixed). Every rendered TEXT byte-identical; the only intended diff is a `sq:body`
   region now carrying a tag instead of being empty.
3. **Falsify every new and changed test, both directions reported.** Break each
   predicate/resolver/branch this task touches (the two new views' applicability, the backfill
   sweep's idempotence — force it to run twice and assert no duplicate tag — the
   `render_source_view` squad_dir widening), confirm red, restore, confirm green. Falsify the
   mechanism, not merely that a raise fires.
4. **The narration sweep is acceptance, not advice.** Run the validated ast+tokenize block
   scanner (scratchpad only, never committed, validated first against a known positive) against
   this task's added prose. Apply the stranger test per sentence — it passes only if it names
   something a stranger can actually check, with no diff in hand.
5. **No docstring or comment citing coverage, a test file, or a delegation that does not exist.**
   Verify every citation this task's new/changed prose makes (a test file, a seam, a delegated
   call) resolves to something real before handoff — this is the exact class that bit TASK-918
   twice and was FEAT-903's F6/F7.

## Dependency

None inbound. The per-item-type-skill task depends on this one landing first — see the
sequencing constraint above (shared `_cli/_skill.py`/`skill_definition_text` seam).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 922 add-subtask "<title>"`; track with `sq task 922 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Role view: source, template, tag-seeded scaffold

<!-- sq:subtask:ST1:body -->
New [views.role_definition] (role source) + templates/views/role_definition.md.j2 carrying agents/role.md.j2's current prose, rewritten against source/item/spec. agents/role.md.j2 keeps only the file frame; its sq:body seeds sq:view:role_definition.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-09-04T10:06:49Z] Elias Python:
  - templates/views/role_definition.md.j2 carries the prose; [views.role_definition] (kind=role, no fields since role/playbook/self skip the field grammar) declared in workflow.toml; agents/role.md.j2 trimmed to frame + seeded tag.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Delete role_definition_text and the CLI's hardcoded branch

<!-- sq:subtask:ST2:body -->
_create_core seeds the tag instead of blanking to empty. Delete _cli/_role.py's 'it is not None and r is not None' branch and ServiceCore.role_definition_text; show_role reads the body generically.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-09-04T10:07:42Z] Elias Python:
  - Deleted ServiceCore.role_definition_text and _cli/_role.py's it-is-not-None branch; show_role now does render_body_text(await svc.read_body(it.id), raw=raw). A defensible behavior improvement noted in the comment: since resolve_role_for_item degrades a broken override rather than raising, the definition now renders even on the one path (broken project override) where the old code showed nothing.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Backfill the tag into every existing role body

<!-- sq:subtask:ST3:body -->
Generalize _sweep_empties_body so sq repair normalizes a role's sq:body to carry the tag (idempotent) instead of emptying it. Retrofits this repo's own already-activated roster. Report the count changed.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-09-04T10:07:44Z] Elias Python:
  - Generalised _sweep_empties_body -> _repair_body_tag (returns (view_name, unconditional)) + _converge_body_tag (the mutation). Role: unconditional convergence (matches old unconditional-blank semantics). Proven driven: manually blanked a role body on a live squad, sq repair converged it back to the tag, sq role show rendered correctly again; automated in tests/service/test_repair_strips_only_retired_regions.py (renamed test + the frozen-list guard) and tests/unit/test_repair_body_tag_convergence_pure_function.py.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — System-skill views: squads, greeting, sq-memory

<!-- sq:subtask:ST4:body -->
[views.squads_skill] (playbook, name unset -> host's own 'skill' type, roster still populated) + [views.greeting_skill]/[views.memory_skill] (self). Widen render_source_view to pass squad_dir for every kind, not self alone. Move the three agents/*_skill.md.j2 templates' content into templates/views/*.md.j2 against source/item/spec/squad_dir.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-09-04T10:07:54Z] Elias Python:
  - [views.squads_skill] (playbook, name unset), [views.greeting_skill]/[views.memory_skill] (self) declared. Widened render_source_view to pass squad_dir for all 6 kinds (removed the now-unused kind param). Added PlaybookSource.playbook (the whole active/merged PlaybookSpec, not just the type's own lane) -- needed because squads_skill's embedded workflow cheatsheet loops every type's authoring lane, which one lane can't answer; this is a finding beyond the task body's own framing, documented on the dataclass.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Seed the tag at skill-file creation; prove the three named branches equivalent

<!-- sq:subtask:ST5:body -->
_write_managed_skill's empty_body seeds the right tag per system slug on first write only. skill_definition_text's three named branches (SQUADS_SKILL/GREETING_SKILL/MEMORY_SKILL) are replaced with a proof that tag-expanded read_body renders byte-identical output -- do not delete the method or its per-type-skill branches; that is the next task's job (see this task's sequencing constraint).
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-09-04T10:07:55Z] Elias Python:
  - _write_managed_skill gained body_tag: str | None=None (per-type skills keep None/empty; the 3 system skills pass their view name). skill_definition_text's 3 named branches replaced with a call into views.resolve_source/render_resolved_source directly (NOT via self.read_body -- ServiceCore can't see ItemsMixin's methods, sibling mixin, confirmed by pyright). Falls back to a throwaway unpersisted Item when no real item is indexed yet, preserving the method's long-standing item-independent purity many existing tests rely on (a real regression I hit and fixed -- see handoff). Proven byte-equivalent to read_body in test_a_system_skills_definition_is_never_stored_in_its_file.py.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Backfill the tag into the three existing system-skill bodies

<!-- sq:subtask:ST6:body -->
Extend the repair sweep (or a sibling corpus walk in the same sq repair pass) to insert each system skill's tag into its existing, empty body file. Never touches a non-empty body -- assert that invariant. Covers this repo's own three system-skill files. Idempotent, reports the count.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-09-04T10:08:01Z] Elias Python:
  - Same _repair_body_tag/_converge_body_tag mechanism (SYSTEM_SKILL_VIEW_NAMES, shared with _write_managed_skill, declared once in _interactions). Skill license is narrower: insert-only when the region is genuinely empty; anything else raises AssertionError (falsified directly in test_repair_body_tag_convergence_pure_function.py). Driven end-to-end on a live squad alongside ST3's role case.
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Consumer enumeration and generated-artefact diff

<!-- sq:subtask:ST7:body -->
Prove every consumer named in this task's Acceptance #1 unaffected or correctly updated, driven not asserted. Before/after diff of sq sync output (roster held constant) for every bundled role and the three system skills -- byte-identical text, only the sq:body region's content changes. Falsify every new/changed test both directions. Run the validated ast+tokenize narration scanner.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
- [2026-09-04T10:08:03Z] Elias Python:
  - Consumer enumeration, generated-artefact diff and falsification evidence are in the handoff comment on TASK-922 itself (too long for a subtask comment).
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-04T10:09:22Z] Elias Python:
  - Handoff — TASK-922 implemented, all 7 subtasks Done. Detail per-subtask is on each ST's own comment; this is the cross-cutting record.
    
    **What landed (US1/US2).** `[views.role_definition]` (role, no name), `[views.squads_skill]` (playbook, name unset), `[views.greeting_skill]`/`[views.memory_skill]` (self) declared in workflow.toml. `templates/views/role_definition.md.j2`/`squads_skill.md.j2`/`greeting_skill.md.j2`/`memory_skill.md.j2` carry the moved prose against `source`/`item`/`spec`/`squad_dir`. `agents/role.md.j2` trimmed to frame + seeded tag; the three `agents/*_skill.md.j2` templates deleted. `_create_core`'s role branch and `_write_managed_skill` (new `body_tag` param, per-type skills untouched) both seed the tag instead of blanking. `ServiceCore.role_definition_text` deleted outright; `_cli/_role.py`'s hardcoded branch replaced with `await svc.read_body(it.id)`. `skill_definition_text`'s three named branches (GREETING/MEMORY/SQUADS) replaced with a call into `views.resolve_source`/`render_resolved_source` directly — **not** through `self.read_body`, because `ServiceCore` cannot see `ItemsMixin`'s methods (sibling mixin; pyright caught this immediately, `reportAttributeAccessIssue`). `skill_definition_text`/`_item_skill_definition_text`/`_cli/_skill.py`'s `if system:` branch left standing per the sequencing constraint, for TASK-923.
    
    **Backfill (ST3/ST6).** `_sweep_empties_body` → `_repair_body_tag` (returns `(view_name, unconditional)` or `None`) + `_converge_body_tag` (the mutation). Two licenses, not one: a role converges **unconditionally** (any stray content → the tag — the direct generalisation of the old unconditional blank-to-`""`, since `set_body` refuses a role body outright so there's nothing authored to protect either way); a permanently-system skill converges **only when genuinely empty** — anything else raises `AssertionError` rather than silently overwriting, since (unlike the role case) this hasn't held under every past release. `SYSTEM_SKILL_VIEW_NAMES` (slug→view name) declared once in `_interactions`, shared by `_write_managed_skill` (seed) and `_repair_body_tag` (backfill) — allowlisted in `tests/meta/test_no_unallowlisted_module_level_mutable_state.py`.
    
    **Repair-survives-the-tag proof — both a test and a manual driven run.**
    - `tests/service/test_repair_strips_only_retired_regions.py::test_a_role_body_converges_onto_the_placement_tag_and_keeps_its_markers` (renamed from `..._is_emptied_...`) and `test_the_live_write_path_produces_none_of_the_stripped_names` (extended to assert the write path's own role/skill bodies carry exactly their tag, not empty).
    - `tests/unit/test_repair_body_tag_convergence_pure_function.py` — new, falsifies `_converge_body_tag`'s guard directly: calling it on stray content with `unconditional=False` raises `AssertionError`; the same input with `unconditional=True` (simulating the guard's absence) silently converges instead — proving the guard is load-bearing, not decoration.
    - Manual, on a real `sq init --roles all` + `sq dev add python` + `sq sync` squad: blanked the manager role's and the squads skill's `sq:body` by hand (simulating a pre-collapse squad); `sq role manager show --raw` showed `(empty — set it with body)`; ran `sq repair` → `"stripped retired regions from 2 item files"`; on-disk bodies now carry exactly their own placement tag (role_definition / squads_skill); `sq role manager show --raw` rendered the full definition again. A second `sq repair` produced no strip notice (idempotent) and the tag count stayed at 1. `sq check` clean throughout.
    
    **Consumer enumeration — driven, not assumed.**
    - `sq role show` / `--raw`: goes through `read_body`, verified above and by `tests/integration/test_role_body_content_generation.py` (rewritten — `_definition()` helper now calls `read_body`).
    - `sq role show --json`: read `build_role_json_payload` — never touches body/definition text (only structured `RoleDef` fields). Unaffected, confirmed by reading, not run against a golden that would mask it (`role_manager_show.json`/`role_qa_show.json` untouched, still pass).
    - `sq skill show` / `--raw` for the 3 system skills: still routes through `skill_definition_text` (the `if system:` branch stands per scope) — now internally resolves via the tag mechanism. `tests/cli/test_skill_show_renders_a_system_definition_on_read.py` passes unchanged.
    - `sq skill show --json`: read `_cli/_skill.py` — payload never includes body. Unaffected.
    - TUI reader (`_tui/_reader.py:51`): already calls `svc.read_body(item_id)` for every item — the shared boundary, automatically inherits the tag mechanism, no code change needed.
    - `.claude/agents/<slug>.md` role pointers: `_render_role_pointer`/`generate_role_entry` take a `RoleDef` directly, no reference to either deleted/changed method — confirmed by reading the signatures, and by the byte-identical diff below.
    - `.claude/skills/<slug>/SKILL.md` pointers: `render("claude/pointer_skill.md.j2", slug=name, description=oneline(description))` — slug+description only. Confirmed by reading + the diff.
    - AGENTS.md backend: `write_managed` builds `roles_data`/`roles=` from `RoleView` fields directly; grepped the whole `_backends/_agents_md/` tree for either method name — zero hits.
    - Docstrings citing `role_definition_text`/`skill_definition_text` by name in `_maintenance.py`, `_items.py`, `_base.py`, and the claude_code backend: all updated to describe the tag mechanism (grepped clean afterward — only the still-standing `_item_skill_definition_text`/`skill_definition_text` citations remain, correctly).
    
    **Generated-artefact before/after diff (roster held constant).** Used a `git worktree` at the pre-task commit (not a stash — a stash earlier this session got popped back cleanly but was too risky to repeat) to build a "before" squad (`sq init --roles all` + `sq dev add python` + `sq sync`) and an identical "after" squad on the current tree.
    - `.claude/` (every agent pointer, every skill pointer, settings.json): **byte-identical**, `diff -rq` reports nothing.
    - `CLAUDE.md`: **byte-identical**.
    - `squads/agents/`: of 21 files, exactly 12 differ after normalising `created_at`/`updated_at` (the two runs happened at different wall-clock seconds, unfrozen) — the 9 role files and the 3 system-skill files (greeting/sq-memory/squads). Every one of the 12 diffs is *only* the timestamp pair plus one added line: the seeded `sq:view:<name>` tag. The other 9 per-type skill files (sq-bug, sq-contract, sq-decision, sq-epic, sq-feature, sq-guide, sq-milestone, sq-review, sq-task) are content-identical. This is the complete, accounted-for diff — no other difference of any kind.
    
    **Falsification — both directions, several mechanisms.**
    1. `render_source_view`'s squad_dir widening: reverted to the old self-only special case → 3 tests in `test_render_source_view_template_context.py` went red (undefined `squad_dir` in the role/playbook probe templates); restored → green.
    2. `example_assignee_slug`'s Protocol widening: reverted to `.get("slug")`-only → 22 tests across `test_generated_agent_text_names_no_bundled_vocabulary.py`, `test_every_cli_command_is_named_in_agent_guidance.py` and `test_squads_skill_content_generation.py` went red (`AttributeError: 'RoleView' object has no attribute 'get'`, right at the `source.roster` call site); restored → green.
    3. `PlaybookSource.playbook`: removed the field from the constructor call → `TypeError: missing 1 required positional argument` at the exact call site, 2 tests red; restored → green.
    4. `_converge_body_tag`'s skill-side guard: see the pure-function test above (both directions live in the permanent suite, not just a manual toggle).
    
    **Narration sweep — the ast+tokenize scanner (scratchpad, never committed), validated against the pre-existing known-positive fixture first (2/2 hits found).** Ran it over every file this task touched, then cross-referenced hits against the exact added lines from `git diff` (not the whole file — several early hits turned out to be pre-existing prose the coarse span-based first pass miscaptured because it touched the same docstring). Applying the stranger test to the genuine hits found and fixed 4 real narration instances: a "used to / now" comparison in `_cli/_role.py`'s show_role comment; two "the direct generalisation of this sweep's old/previous unconditional blank-to-''" clauses in `_maintenance.py` (both rewritten to state the invariant directly, no history); a "used to render... now the region is what a read expands" framing in `test_role_body_content_generation.py`; and a vague "this change produces" in `test_a_system_skills_definition_is_never_stored_in_its_file.py`'s module docstring. Left two flagged-but-pre-existing sentences alone (not mine, present before this task, out of scope to relitigate): `test_role_body_content_generation.py`'s "It no longer lists the role's own skills" and `test_the_role_write_path_stores_no_definition.py`'s "activation used to render the whole definition" (this second one literally describes an *earlier release's* collapse, not this task's).
    
    **Coverage-citation check.** Caught and fixed one dead citation myself mid-task: an early draft of `test_role_body_content_generation.py`'s corrupted-body test cited a test file (`test_repair_generalises_body_convergence_to_the_view_tag.py`) I ended up never creating — the real coverage lives in `test_repair_strips_only_retired_regions.py` and `test_repair_body_tag_convergence_pure_function.py`. Fixed before handoff; grepped for any other TASK-923/FEAT-etc reference across every touched file (also required by `tests/meta/test_source_and_new_test_tree_have_no_stray_ticket_references.py`, which caught one — see below) and re-verified every `tests/...` citation in my own new/changed docstrings resolves to a real file.
    
    **Gates.**
    - `uv run --all-extras pyright` — 0 errors.
    - `uv run --all-extras ruff check .` — all checks passed.
    - `uv run --all-extras ruff format --check .` — all files already formatted.
    - `uv run --all-extras pytest tests/meta` — 270 passed, 9 failed, all in `tests/meta/test_override_manifest_and_stamp_freshness.py` / `test_override_kind_uniformity.py::test_every_registered_kind_wires_all_five_parts` — see the finding below, this is a known structural blocker, not a defect in this task's work.
    - Targeted (135 files matching `*view*`/`*role*`/`*skill*`/`*repair*`/`*check*`/`*retype*` under tests/, minus tui): 134 passed, 1 failed — `tests/integration/test_override_scaffold_scan_diff_update_and_check.py::TestWorkflowOverride::test_diff_raises_when_absent_and_reflects_the_stamp_state_once_present` — same root cause as the 9 above (the 10th occurrence).
    - All individually-touched test files re-run green after every edit; the full list is in this task's git diff.
    - `sq check` on this repo's own squad: clean.
    
    **Finding — not worked around, reported.** Adding/removing/changing bundled templates and `workflow.toml` (this task's whole job) requires regenerating `templates_manifest.json`/`content_store.json` (`scripts/gen_template_manifest.py`). `pyproject.toml`'s version is still `0.14.0`, and `v0.14.0` is an **already-tagged, shipped release** — per ADR-781 §6 and the "Template manifest release gotcha" memory, regenerating now would overwrite that shipped entry. I verified this is a genuine pre-existing gap, not something I broke: `git worktree` at the pre-task commit shows the exact same 9 `tests/meta` failures are **absent** on the base tree and appear **only** after these template/spec changes land. This is the first piece of 0.15 work to touch the bundled template *set* (FEAT-905/903 only touched Python). The fix is a version bump (0.14.0 → some 0.15.0-dev value) followed by `python scripts/gen_template_manifest.py` — squarely release-management territory, not something I did unilaterally. Recommend the tech lead/manager decide whether to bump now (so this and every later 0.15 template-touching task lands clean) or batch the regen at release-cut. All 10 failing tests are enumerated above; nothing else is affected.
    
    **Finding — beyond the task body's own framing, resolved rather than left as a gap.** `squads_skill.md.j2`'s embedded workflow cheatsheet (`{% include "workflow.md.j2" %}`) needs the *whole* active/merged `PlaybookSpec` to loop every declared type's own authoring lane — `PlaybookSource.lane` (one type's own entry) can't answer that. Added a `playbook: PlaybookSpec` field to `PlaybookSource`, populated in `_resolve_playbook_source` (already had `playbook` in hand). Falsified directly (see above) and covered by `test_a_playbook_source_carries_the_whole_active_playbook_not_only_its_own_lane`. `_playbook_json_payload` (FEAT-903/TASK-919, already shipped) is untouched — it builds its dict by hand and never reads the new field, so nothing leaks into `--json`.
    
    `sq check` clean. Nothing outside TASK-922 transitioned. @tech-lead this is ready for review; TASK-923 stays blocked on it per the sequencing constraint until you say otherwise.
- [2026-09-04T10:32:22Z] Elias Python:
  - Root cause fixed: `_converge_body_tag` (`_services/_maintenance.py`) asserted "empty or already-tagged" as the only reachable shapes for a role/system-skill `sq:body`, true only for current write paths. Migrating corpora (0.1-0.11 fixtures) carry a third shape: plain-prose rendered by a pre-tag-mechanism release, before `set_body` refused these bodies at all. Licence stated in `_converge_body_tag`'s docstring: `set_body` refuses both bodies unconditionally today, so nothing there is authored — a stored region is either empty, the tag, or a superseded rendering of the same class 0.14's retired-region sweep already established may be stripped (narrower than the milestone precedent, which protects still-authorable prose).
    
    Unified the role/system-skill licence into one function (dropped the `unconditional` bool split — both now get the same treatment). Stays loud: content is admitted only if it's empty or contains no marker-shaped bytes of its own (`sections.find_markers`); anything marker-shaped still raises `AssertionError` rather than being guessed at — falsified via `test_marker_shaped_content_is_not_silently_overwritten` (both directions: red without the check, green with it).
    
    Reporting: no new plumbing needed — conversion already flows through the existing `pending.stripped`/reflog `stripped` delta, so `test_a_sweep_route_states_the_content_diff_it_produced[migrate-up]` passes as-is with an honest count.
    
    `test_self_source_resolver.py`'s failure is a **separate** root: same task's `_create_core` change (role bodies now seed the tag at creation) made its "genuinely empty body" fixture (a fresh role) false — no item type has a truly blank body at creation anymore. Fixed by explicitly clearing a plain task's body instead of relying on a role's create-time scaffold.
    
    Also updated three pre-existing `tests/integration/test_migration_corpus.py` assertions that predated the role tag-seeding and expected an empty post-migration role body; they now assert the `sq:view:role_definition` tag. `test_a_system_skill_body_survives_the_migration_unchanged` renamed/split: the three fixed system skills now converge onto their tag, any other template-owned (per-type) skill still survives byte-identical (untouched, as before).
    
    ADR-880's unpaired-tag invariant untouched; `test_a_role_body_converges_onto_the_placement_tag_and_keeps_its_markers` still green.
    
    Gates: `pyright` / `ruff check` / `ruff format --check` all clean. `uv run --all-extras pytest tests/integration` → 704 passed, 6 skipped. `uv run --all-extras pytest tests/meta` → 279 passed. Targeted: `tests/unit/test_self_source_resolver.py tests/unit/test_repair_body_tag_convergence_pure_function.py tests/service/test_repair_strips_only_retired_regions.py` → all green (combined run: 1009 passed, 6 skipped). `sq check` clean. Did not run the full suite.
- [2026-09-04T10:32:25Z] Elias Python:
  - Files touched: src/squads/_services/_maintenance.py, tests/integration/test_migration_corpus.py, tests/unit/test_repair_body_tag_convergence_pure_function.py, tests/unit/test_self_source_resolver.py. Task status/parent untouched, per brief.
- [2026-09-04T10:34:48Z] Catherine Manager:
  - Full suite green as the authoritative gate: 4842 passed, 12 skipped, exit 0. Two rounds were needed: the first handback passed pyright, ruff, targeted tests and tests/meta while the full suite failed 34 times, all from the migration corpora -- the targeted selection did not include tests/integration. That is a brief defect, not a dev one; tests/integration is now mandatory in the brief alongside tests/meta.
  - Verified the changed migration assertions rather than accepting them: they are stronger, not bent to pass. The old test asserted a post-migration role body was empty; the new one asserts it equals the tag exactly. The renamed test now covers both convergence and byte-identical survival, and carries a non-vacuity guard so the loop cannot pass by finding nothing to check. The convergence admits legacy content by shape -- no marker-shaped bytes -- and still raises on anything outside that set, so the caught failure was not traded for an uncaught one.
<!-- sq:discussion:end -->
