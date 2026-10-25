---
id: REV-1033
sequence_id: 1033
type: review
title: 'Docs audit: stability, migration, internals'
status: Approved
author: reviewer
description: 'Claim-by-claim audit of docs/stability.md, docs/migration.md and docs/internals.md
  against the release/0.16 dev build: driven in scratch squads and fixture corpora,
  read against the code and the accepted ADRs.'
subentities:
- local_id: F1
  title: 'stability Tier 3: override diff --json is an array of one object, not an
    object'
  status: Verified
  severity: high
- local_id: F2
  title: 'stability reflog: skills seeded at init log a padded target (SKILL-000009),
    not the formatted ID'
  status: WontFix
  severity: medium
- local_id: F3
  title: stability L37 says the prefix stays fixed; the retype section says it changes
  status: Verified
  severity: medium
- local_id: F4
  title: stability/internals override layout omits .overrides/playbook.toml (ADR-777)
  status: Verified
  severity: medium
- local_id: F5
  title: internals §7 lists five ABC methods with pre-ADR-133 names; seven exist,
    agents_md backend missing
  status: Verified
  severity: medium
- local_id: F6
  title: internals layout names default_backend in .squads.toml; the file carries
    active_backends
  status: Verified
  severity: medium
- local_id: F7
  title: internals §9 template inventory names files that do not exist and misses
    four dirs
  status: Verified
  severity: medium
- local_id: F8
  title: internals §5 shows a :head region and sq:summary table that files no longer
    carry
  status: Verified
  severity: medium
- local_id: F9
  title: 'internals §4: repair does not set counter = max ID; it floors it (ADR-104)'
  status: Verified
  severity: medium
- local_id: F10
  title: 'migration L137: sq repair does not bump squads_version in .squads.toml'
  status: Verified
  severity: medium
- local_id: F11
  title: 'internals: stale module, helper and entry-point names (_service, _check_*,
    _cli:app)'
  status: Verified
  severity: low
- local_id: F12
  title: 'internals layout: missing contracts/, milestones/, operators/, AGENTS.md,
    padding, disallowedTools'
  status: Verified
  severity: low
- local_id: F13
  title: 'stability exit-code table: sq import also exits 3 after a committed write'
  status: Verified
  severity: low
- local_id: F14
  title: stability Tier 3 catalog table omits sq workflow ref-kinds --json
  status: Verified
  severity: low
- local_id: F15
  title: stability ref-kind section follows ADR-775 while ADR-49 (closed vocabulary)
    is still Accepted
  status: Verified
  severity: low
- local_id: F16
  title: stability vs README disagree on which shells have completion
  status: Verified
  severity: low
- local_id: F17
  title: 'stability/migration: repo-internal names and paths in adopter docs'
  status: Verified
  severity: low
- local_id: F18
  title: 'migration L154: managed skill files are SKILL-NNNNNN-<slug>.md, and are
    items, not disposable'
  status: Verified
  severity: low
created_at: '2026-10-16T08:48:45Z'
updated_at: '2026-10-25T19:31:38Z'
---
<!-- sq:body -->
## Scope

`docs/stability.md`, `docs/migration.md`, `docs/internals.md` on branch `release/0.16` (dev build, schema 0.16). Every concrete claim was either driven (dev build in scratch squads under the session scratchpad, plus a copy of each `tests/fixtures/corpus/*` corpus) or read against the code and the accepted ADRs. The comment-header passages under review in REV-1031 (stability "Comment headers" / "A roster slug never changes", migration "Upgrading to 0.16: the schema step", the internals comment line) were skipped, as were the `extra:` descriptions (flattening decided, not built).

## What held

- The migration promise: all twelve fixture corpora (0.1 through 0.15, incl. `v0_15_discussions`) reached schema 0.16 with `sq migrate up` exit 0 and `sq check` exit 0 (warnings only).
- The `-C` section of migration.md end to end (`--dir` exit 2, `-C` after the command refused, ignored after `--help`, repeatable/relative, missing path exit 2, no `.squads.toml` exit 1, `-m --dir` as text, `--file` relative to `-C`).
- The out-of-date gate (list/repad/`-m --help` refused with exit 1; `migrate help`, `-m -m --help` and `<cmd> --help` run; `-- --help` gated; no version notice while behind).
- Exit codes 1/2/3/4 and the omissions-report wiring; the addressing rule (`sq show 21`, padded form, wrong-type error exit 1).
- All seven workflow catalog shapes, `memory list/show --json`, `override list --json`, `reflog --json` keys, `comments --json` entries, `check --json`, `create --json`, the human-only command list, the alias table, the bug lifecycle and its settled/hidden roles, the ABC's seven abstract methods, the reserved roster surface (R1/R1'/R2), the splat-ref grammar limits, `index is full` exhaustion, the 0.1→0.2 and 0.2→0.3 runner descriptions, the `(vA, vB]` chlog range and rc ordering.

## What did not

Eighteen findings below. The architecture half of internals.md is the stale part (ABC names, config keys, template inventory, sub-entity block shape, counter rule, module names); stability.md has one wrong Tier 3 shape, one contract the code itself breaks (reflog target padding for seeded skills), one internal contradiction and a few omissions; migration.md has one false claim about `sq repair` and two stale details.

## Code observation (not a doc defect)

On a behind-schema squad, `sq task <bad-id> comment -m -m --help` resolves the address against the stale index before help prints (`error: 1 is ROLE-1 (role), not a task`), i.e. the `--help` exemption lets the type-group callback read the squad under the wrong vocabulary. Harmless (read-only), but the gate's stated rule is "help only".
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1033 add-finding "…" --severity medium`; track with `sq review 1033 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — stability Tier 3: override diff --json is an array of one object, not an object

<!-- sq:finding:F1:body -->
**File:** `docs/stability.md:573-575` (Tier 3, "Override inspection").

**Doc says:** `override diff --json` emits `{name, kind, base_version, base_available, delta_mine, delta_upgrade}` — an object.

**True:** it emits a JSON **array** holding one such object. Driven: `sq override scaffold workflow` then `sq override diff workflow --json` in a scratch squad prints `[ { "name": "workflow", "kind": "workflow", "base_version": "0.15.0", "base_available": true, "delta_mine": "...", "delta_upgrade": ... } ]`.

**Why high:** this is a frozen Tier 3 shape; a client written to the documented object shape fails on the first parse. Either the doc or the command must change before 1.0, and the doc is the only place the shape is written down.

**Fix:** document the array (one row per override named, matching `override list --json`), or decide the command returns an object and change the code; record which in the ADR that owns Tier 3 shapes.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T09:06:29Z] `tech-writer` Theo Writer:
  - Fixed in docs/stability.md (Override inspection): documented as an array, one row for the override named or one per drifted override; matches the command and its docstring, no ADR pins an object shape.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/stability.md documents `override diff --json` as an array of objects.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — stability reflog: skills seeded at init log a padded target (SKILL-000009), not the formatted ID

<!-- sq:finding:F2:body -->
**File:** `docs/stability.md:234` (Tier 1, reflog line schema).

**Doc says:** `target` is "the affected item's formatted ID (its prefix names the type)". Formatted IDs are unpadded everywhere (L39).

**True for roles and work items, false for skills seeded at init:** the `create` lines `sq init` writes for the managed skills carry a **padded** target. Driven: the scratch squad's `.reflog.jsonl` holds `create ROLE-1` ... `create ROLE-8` but `create SKILL-000009` ... `create SKILL-000017`; `sq reflog` prints the same. Read: `_services/_maintenance.py` ~1926 and ~2015 log `"create"` with the padded allocation string (`item_id`), where `_services/_base.py` ~901 logs `item.id`.

**Why medium:** a consumer filtering the reflog by `target == "SKILL-9"` misses the skill's creation; the frozen line schema is violated by the tool itself. This is a code defect surfaced by the doc audit; the doc is right.

**Fix:** log `item.id` at both seeding sites (and check `sq skill add` / `sq dev add` paths for the same slip); keep the doc. Consider a test asserting every reflog `target` round-trips through the unpadded formatter.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T09:01:38Z] `qa` Mara Tester:
  - Filed as BUG-1041 (code defect, doc is right). Closing here; the fix and its test live on the bug.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — stability L37 says the prefix stays fixed; the retype section says it changes

<!-- sq:finding:F3:body -->
**File:** `docs/stability.md:36-37` vs `docs/stability.md:343-348`.

**Doc says (L37):** "The *number* never changes across a retype or repair; the *prefix* stays fixed."

**Doc also says (L345-347):** `sq <type> <n> retype <new-type>` turns `TASK-<n>` into `BUG-<n>`: the file "moves folders and reprefixes".

**True:** the second. Read: `_services/_retype.py`; driven indirectly (retype verb present on `sq task <n> --help`). The prefix changes on retype by design; what stays fixed is the sequence number.

**Why medium:** the Tier 1 identity statement contradicts itself inside one page, and a reader of the ID section alone takes away the wrong invariant.

**Fix:** L37 → "The *number* never changes across a retype or repair; only the prefix moves, and only on a retype."
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T09:06:32Z] `tech-writer` Theo Writer:
  - Fixed in docs/stability.md (ID numbering): only the prefix moves, and only on a retype.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/stability.md ID section says only the prefix moves, and only on a retype.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — stability/internals override layout omits .overrides/playbook.toml (ADR-777)

<!-- sq:finding:F4:body -->
**Files:** `docs/stability.md:136-141` (frozen override layout) and `docs/internals.md:53-55` (layout tree).

**Doc says:** the frozen surfaces are `.overrides/{templates,roles}/` and `.overrides/workflow.toml`.

**True:** there is a fourth override document, `.overrides/playbook.toml`. Read: `_interactions/_loader.py` `PLAYBOOK_OVERRIDE_FILENAME = ".overrides/playbook.toml"`, `_overrides/_manifest.py` `PLAYBOOK_KEY`; driven: `sq override scaffold --help` reads "Copy a bundled template (or role/workflow/playbook)". migration.md:107 already names "the workflow override or playbook override", and internals.md:347 names `.overrides/playbook.toml`, so the two docs disagree with stability's "frozen" list. ADR-777 ("One override contract for every bundled spec document") is the authority.

**Why medium:** a frozen-surface list that omits one of the four documents tells an adopter the playbook override is not covered by the contract.

**Fix:** add `.overrides/playbook.toml` to the layout bullet and to the internals tree; say the same deep-merge grammar applies (per ADR-777).
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T09:06:35Z] `tech-writer` Theo Writer:
  - Fixed in docs/stability.md (Project-level overrides) and docs/internals.md tree: the three spec documents workflow.toml, roles.toml and playbook.toml (ADR-777 makes roles.toml a document too), shared grammar, [selected] scoped to workflow/roles.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/internals.md layout and §9 name `.overrides/playbook.toml`.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — internals §7 lists five ABC methods with pre-ADR-133 names; seven exist, agents_md backend missing

<!-- sq:finding:F5:body -->
**File:** `docs/internals.md:301-306` (section 7 title and first paragraph).

**Doc says:** the `AgentBackend` ABC is `ensure_scaffold`, `write_managed`, `generate_role_pointer`, `generate_skill_pointer`, `remove_artifacts`; `ClaudeCodeBackend` is "the first implementation"; the section is titled "The Claude Code backend".

**True:** seven abstract methods — `ensure_scaffold`, `write_managed`, `generate_role_entry`, `generate_skill_entry`, `remove_artifacts`, `candidate_orphans`, `managed_paths` — plus non-abstract `managed_entry_paths`, `restriction_fragment`, `render_role_entry`, `render_skill_entry`. Read: `_backends/_base.py` 200-341. The `_pointer` → `_entry` rename is ADR-133 (Accepted); a second bundled backend, `agents_md`, exists (`_backends/_agents_md/`, `templates/agents_md/agents_section.md.j2`), and stability.md:674-718 documents all of this correctly.

**Why medium:** internals contradicts the stability contract and the ADR on the one surface a third-party backend author implements; a backend written from internals would not instantiate (abstract methods unimplemented).

**Fix:** rewrite the paragraph to the seven names, mention `agents_md` and the `AGENTS.md` managed region, retitle the section "Backends", and point to `backends.md` for the five host questions.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T09:06:38Z] `tech-writer` Theo Writer:
  - Fixed in docs/internals.md section 7, retitled Backends: the seven abstract methods, claude_code and agents_md, active_backends, pointer to backends.md.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/internals.md §7 "Backends" lists the current ABC methods and the agents_md backend.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — internals layout names default_backend in .squads.toml; the file carries active_backends

<!-- sq:finding:F6:body -->
**File:** `docs/internals.md:43` (layout tree, `.squads.toml` line).

**Doc says:** `.squads.toml  # config: squad_dir, default_backend, squads_version`.

**True:** the file carries `schema_version`, `squad_dir`, `active_backends`, `squads_version`. Driven: a fresh `sq init` writes exactly those four keys. Read: `_models/_config.py` (`active_backends: list[str]`; `default_backend` is only translated on read, L71). stability.md:248-258 and ADR-141 document `active_backends` as the Tier 1 field.

**Why medium:** cross-doc contradiction on a Tier 1 file; `default_backend` is a legacy key the tool never writes any more.

**Fix:** `.squads.toml  # config: schema_version, squad_dir, active_backends, squads_version`.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T09:06:40Z] `tech-writer` Theo Writer:
  - Fixed in docs/internals.md layout tree: schema_version, squad_dir, active_backends, squads_version (driven on a fresh init).
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/internals.md layout lists schema_version, squad_dir, active_backends; squads_version left with ADR-1119.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — internals §9 template inventory names files that do not exist and misses four dirs

<!-- sq:finding:F7:body -->
**File:** `docs/internals.md:369-374` (section 9, template inventory).

**Doc says:** templates are `items/<type>.md.j2`, `agents/{role,skill,squads_skill,item_skill}.md.j2`, `claude/{pointer_agent,pointer_skill,claude_section,settings.json}.md.j2`, and `workflow.md.j2`.

**True** (read: `ls src/squads/_rendering/templates`): `items/{_default,bug,contract,decision,epic,feature,guide,milestone,review,task}.md.j2`; `agents/{operator,role,skill}.md.j2`; `agents_md/agents_section.md.j2`; `claude/{claude_section,pointer_agent,pointer_skill}.md.j2` and `claude/settings.json.j2` (no `.md` infix); `subentities/{block,head,summary}.md.j2`; `views/{greeting_skill,item_skill,memory_skill,milestone_rollup,role_definition,squads_skill}.md.j2`; `workflow.md.j2` and `workflow_static.md.j2`. The `squads_skill`/`item_skill` templates moved to `views/`.

**Why medium:** stability.md:139-140 says template overrides "mirror bundled template names 1:1" under `.overrides/templates/`, so this list is the lookup table an adopter uses to name an override file; four of the names here do not exist and a shadow file named after them is silently ignored (the engine's `ChoiceLoader` matches by exact path, `_rendering/_engine.py:75-77`).

**Fix:** replace the list with the real tree, or drop the enumeration and tell the reader to list the package's `templates/` directory (`sq override scaffold` can name them).
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-16T09:06:43Z] `tech-writer` Theo Writer:
  - Fixed in docs/internals.md section 9: the real 26-template tree, grouped, with the rule that an override uses the same relative path.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/internals.md §9 lists the real template tree (claude/pointer_agent, settings.json.j2 and the rest).
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — internals §5 shows a :head region and sq:summary table that files no longer carry

<!-- sq:finding:F8:body -->
**File:** `docs/internals.md:204-216` (sub-entity block example) and `:222-224` ("re-renders the heading, the `:head`, and the parent's sq-managed `sq:summary` table").

**Doc says:** every sub-entity block carries a `sq:subtask:STn:head` region with rendered badges, and the parent carries an `sq:summary` table, both rewritten on mutation.

**True:** a freshly written block has no `:head` region and the parent has no `sq:summary` table. Driven: `sq task 21 add-subtask "Validate token"` in the scratch squad wrote `sq:subtask:ST1`, a `### ST1 — Validate token` heading, `:body`, a `#### Discussion` heading, `:discussion`, `:end` — nothing else; `grep sq:summary` on the file is 0. internals.md:127-129 itself says repair "strips from each file what is now computed on every read rather than stored — the sub-entity roll-up table and badge lines", so the two passages contradict each other; the migrate run on every fixture printed "stripped retired regions from N item files".

**Why medium:** a reader (or an agent parsing files) looks for regions that are not there, and the "single-sourced in frontmatter, presentation computed on read" model is the point of the section.

**Fix:** show the block as written today (heading + body + discussion), state that status/assignee/badge presentation and the roll-up table are rendered on read by `show`, and drop the "re-renders the :head and the summary table" sentence.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-16T09:06:46Z] `tech-writer` Theo Writer:
  - Fixed in docs/internals.md section 5: block shown as written today (driven), presentation computed on read, the :head/summary re-render sentence replaced by the heading re-render on a title change.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/internals.md §5 no longer shows a :head region or sq:summary table.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — internals §4: repair does not set counter = max ID; it floors it (ADR-104)

<!-- sq:finding:F9:body -->
**File:** `docs/internals.md:120-121`.

**Doc says:** `sq repair` "sets `counter = max ID number`".

**True:** it sets `counter = max(previous counter, max observed number)` — a floor that never lowers. Read: `_index/_reconcile.py:391` `counter=max(previous.counter if previous else 0, scan.max_n)`, `_services/_maintenance.py:2576` `db.counter = max(previous_counter, max_n)`; ADR-104 ("The index may hold corpus-derived format parameters carried as a floor (padding, counter)"). Driven: after removing nothing but with counter 23 and 23 items, `sq repair` kept 23; the floor is what makes stability.md:49-54 ("a removed sequence number is permanently retired") survive a repair after the highest item is removed.

**Why medium:** as written, internals implies a repair after removing the newest item would hand its number to the next create — the exact reuse Tier 1 forbids.

**Fix:** "raises `counter` to the highest number seen on disk, never lowering it (ADR-104): a removed top number stays retired across a repair."
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-16T09:06:49Z] `tech-writer` Theo Writer:
  - Fixed in docs/internals.md section 4: counter raised to the highest number on disk, never lowered; padding carried as a floor too.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/internals.md says repair raises the counter to the highest number on disk, never lowering it.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — migration L137: sq repair does not bump squads_version in .squads.toml

<!-- sq:finding:F10:body -->
**File:** `docs/migration.md:137` (version table, `squads_version` row).

**Doc says:** `squads_version` is bumped on "Every `sq init` / `sq sync` / `sq repair` / `sq migrate up`", and the table head (L133) says both files, `.squads.toml` and `.squads.json`, carry it.

**True:** `sq repair` rewrites the index's copy only. Driven in the scratch squad: set `.squads.toml` `squads_version = "0.0.1"`, ran `sq repair` → `.squads.toml` still `0.0.1`, `.squads.json` `0.15.0`, and the next command still printed `squads 0.15.0 detected (managed files at 0.0.1). Run sq sync`. `sq sync` then updated the toml. Read: `_services/_maintenance.py:1734` passes `self.paths.config.squads_version` through on the repair path; `_stamp_version` is reached from sync/init/migrate.

**Why medium:** the version notice keys off the toml, so an adopter who follows this row and runs `repair` to clear the notice gets it again.

**Fix:** drop `sq repair` from the "bumped when" cell, or say "the index copy on `sq repair`; the `.squads.toml` copy (the one the version notice reads) on `init`/`sync`/`migrate up`".
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-16T09:06:52Z] `tech-writer` Theo Writer:
  - Fixed in docs/migration.md version table: driven, and migrate up does not bump the toml copy either (it stamps only schema_version and says run sq sync), so the toml copy is init/sync (adopt when it creates the file), the index copy every rebuild.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/migration.md says schema_version is the only version check; squads_version is ignored (ADR-1119).
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — internals: stale module, helper and entry-point names (_service, _check_*, _cli:app)

<!-- sq:finding:F11:body -->
**File:** `docs/internals.md`, several lines; all stale names (read against `src/`).

- L7, L30, L34: `squads._service` / `_service.Service` → the module is `squads._services._service` (a mixin package; CLAUDE.md lists the twelve concern mixins).
- L139-142: `sq check` is "implemented as small per-rule helpers: `_scan_for_check`, `_check_reconciliation`, `_check_items`, `_check_subtask_stories`" → only `_scan_for_check` exists; the rules are the named validator catalog in `_services/_validators.py` (`parent_in`, `item_status_valid`, `dangling_ref`, `subentity_body_written`, ..., ADR-864) plus the squad-level ones in `_maintenance.py` (`index_reconciled`, `backend_reconciled`, `roster_config_integrity`, ...).
- L464-466: `sq inbox` (`_service.inbox`) → `_services/_collab.py::inbox`; `sq check (_service.check, esp. _check_subtask_stories)` → see above.
- L385: entry point `squads._cli:app` → `pyproject.toml` `[project.scripts]` binds `sq = "squads._cli:main"` (CLAUDE.md carries the same stale name).
- L4: "Pairs with adoption.md (migration)" → adoption.md is the *import* doc; the migration doc is migration.md.

**Why low:** internals is contributor-facing, but these are the entry points a contributor greps for first; each one currently resolves to nothing.

**Fix:** update the names; where a list of helpers is given, prefer naming the catalog (validators) over individual functions, which churn.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-16T09:06:56Z] `tech-writer` Theo Writer:
  - Fixed in docs/internals.md: _services._service and the mixin facade, the two-tier check (scan + validator catalog), _services/_collab.py, squads._cli:main, migration.md vs adoption.md pairing.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/internals.md names none of `squads._service`, `_check_items` or `_cli:app`.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — internals layout: missing contracts/, milestones/, operators/, AGENTS.md, padding, disallowedTools

<!-- sq:finding:F12:body -->
**File:** `docs/internals.md:41-59` (layout tree) and nearby detail lines; each verified on a fresh `sq init` in a scratch squad or read from the spec.

- L52: folder list `epics/ features/ tasks/ bugs/ adrs/ reviews/ guides/` omits `contracts/`, `milestones/` (bundled since 0.14, `workflow.toml` `[items.contract]`/`[items.milestone]`) and the roster folder `operators/` (`[items.operator] folder = "operators"`), which sits beside `agents/`, not under it.
- L44 and section 7: the tree shows only `CLAUDE.md`; with the `agents_md` backend active there is an `AGENTS.md` managed region too (stability.md:716, `_backends/_agents_md/`).
- L75: the index root is `{schema_version, squads_version, counter, items}` → it also carries `padding` (driven: `"padding": 6` in the fresh index; ADR-104/ADR-282).
- L320: role pointer frontmatter `name`, `description`, `model`, `color`, `skills:` → also `disallowedTools` (driven: `.claude/agents/architect.md` has `disallowedTools: Agent`; ADR-155 capability attenuation).
- L323: managed skills are "the general `squads` skill plus one `sq-<type>` skill per item type" → `greeting` and `sq-memory` are managed too (driven: `.claude/skills/` holds `greeting`, `sq-memory`, `squads`, `sq-<type>`...).

**Why low:** omissions rather than falsehoods, but a reader reconciling the tree against a real squad finds four unexplained entries.

**Fix:** regenerate the tree from a fresh `sq init --backend claude_code --backend agents_md` and keep it as the example; add `padding` and `disallowedTools`.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-16T09:06:59Z] `tech-writer` Theo Writer:
  - Fixed in docs/internals.md: contracts/, milestones/, operators/, AGENTS.md, .reflog.jsonl, roles.toml/playbook.toml in the tree; padding in the index root; disallowedTools: Agent; greeting and sq-memory as managed skills.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/internals.md layout has contracts/, milestones/, operators/ and disallowedTools.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — stability exit-code table: sq import also exits 3 after a committed write

<!-- sq:finding:F13:body -->
**File:** `docs/stability.md:384-396` (exit-code table) and `:409-414`.

**Doc says:** `3` = "Check failures (one or more issues found by `sq check`)"; L412 "Commands outside the class keep the codes they had".

**True:** `sq import` also exits `3`, after a **committed** write, when the post-import integrity pass reports error-level findings. Read: `_cli/_import.py:125-135` — the docstring says "Deliberately *not* exit 1: 1 means squads could not do what was asked ... here the transaction committed and the write stands, so the only honest non-zero is the one that means reported, not refused". The L372-382 bulk-import paragraph does not mention it either.

**Why low:** the table is correct for `sq check` and the import behaviour is deliberate, but a CI script that treats `3` as "sq check found issues" misreads an import exit; the frozen table should name every producer of a code.

**Fix:** widen the `3` row to "integrity findings reported: `sq check` found issues, or `sq import` applied the file and the follow-up check found error-level issues"; add one sentence to the bulk-import paragraph.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-10-16T09:07:02Z] `tech-writer` Theo Writer:
  - Fixed in docs/stability.md: exit 3 row names sq import, and the bulk-import paragraph says why it exits 3 after a committed write.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/stability.md exit-code row 3 names `sq import` after a committed write.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — stability Tier 3 catalog table omits sq workflow ref-kinds --json

<!-- sq:finding:F14:body -->
**File:** `docs/stability.md:528-536` (workflow catalog table) vs `:457-459`.

**Doc says (L459):** "`sq workflow ref-kinds` lists the set the active spec declares." The Tier 3 table of catalogs (types, subentity-kinds, collections, statuses, roles, lifecycles, views) does not list it, although L554 names `ref-kinds` as a join destination for a `views` row's `source_name`.

**True:** `sq workflow ref-kinds --json` exists and emits one row per declared kind with keys `kind`, `label`, `hint`, `role`, `direction` (driven in the scratch squad: 10 rows). ADR-738 is "one catalog per spec map".

**Why low:** a gap, not an error, but it is the one catalog a consumer needs to resolve the `dependency`/`preload`/`default` semantics L442-454 describe, and the table claims to be the frozen surface.

**Fix:** add the row `| sq workflow ref-kinds --json | ref kind | kind, label, hint, role, direction |`, and note that `role`/`direction` are `null` for a navigational kind.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-10-16T09:07:05Z] `tech-writer` Theo Writer:
  - Fixed in docs/stability.md catalog table: ref-kinds row plus the null rule for role and direction (driven, 10 rows).
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/stability.md Tier 3 catalog table has a `sq workflow ref-kinds --json` row.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — stability ref-kind section follows ADR-775 while ADR-49 (closed vocabulary) is still Accepted

<!-- sq:finding:F15:body -->
**File:** `docs/stability.md:430-459` ("Ref-kind vocabulary (declared, bound by semantic)") vs ADR-49 (Accepted).

**Doc says:** ref kinds are declared vocabulary; "a project may declare its own, and may rename or drop a built-in it does not use". This matches ADR-775 (Accepted, "Ref kinds are declared spec vocabulary bound by semantic role").

**ADR-49 says (still Accepted, amended 2026-08-03):** the vocabulary is "closed against ad-hoc kinds ... 'no others' now reads as 'no kind a project declares for itself'. The closure against an adopter-facing escape hatch is unchanged", and its Consequences require the stability doc to "carry the extension policy verbatim: the ref-kind vocabulary is closed in 1.0".

**True today:** the code follows ADR-775 (`[ref_kinds]` is a merged spec section; driven: `sq workflow ref-kinds` on an override-bearing squad). So stability agrees with the newer decision and contradicts an older one that was never superseded. Read: `sq list -t decision -a` shows both Accepted; ADR-775's refs do not include ADR-49.

**Why low:** the doc is right; the ADR set is inconsistent, and the board rule (notice 6) is that a wholly replaced decision is Superseded with the `supersedes` edge. For the architect.

**Fix:** `sq decision 775 ref add ADR-49 --kind supersedes` and move ADR-49 to Superseded, or amend ADR-49's closure clause with a dated comment pointing at ADR-775.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-16T09:10:28Z] `architect` Robert Architect:
  - ADR-775 already carries `ADR-49 (supersedes)` (added 2026-08-22), so no new edge was needed; it replaces ADR-49 in full, which under board notice 6 means retirement, not a dated amendment. Dated note posted on ADR-49 (2026-10-16). The Accepted to Superseded move (`sq decision 49 status Superseded`) is allowed by the adr lifecycle but waits on @op-pierre, so this finding stays Open until it lands. docs/stability.md needs no change.
- [2026-10-16T13:04:35Z] `manager` Catherine Manager:
  - ADR-49 moved to Superseded by op-pierre's instruction (2026-10-16); ADR-775 supersedes it.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: ADR-49 is Superseded by ADR-775, so the doc and the ADR set agree.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — stability vs README disagree on which shells have completion

<!-- sq:finding:F16:body -->
**File:** `docs/stability.md:652-656` ("Shell completion") vs `README.md:346-348`.

**Doc says:** completion is "documented for bash and zsh ... may be added to other shells additively post-1.0".

**README says:** "`sq` supports tab-completion for bash and zsh (and also fish and PowerShell)", via Typer's `--install-completion` / `--show-completion` (driven: both flags are on `sq --help`).

**Why low:** the two adopter docs disagree on which shells are in the supported surface today; a fish user reading stability concludes it is not covered.

**Fix:** either list the four shells in stability (what Typer ships) or say "bash and zsh are the verified install steps; fish and PowerShell are available through the same flags but unverified", and make the README say the same.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-10-16T09:07:08Z] `tech-writer` Theo Writer:
  - Fixed in docs/stability.md (Shell completion): fish and PowerShell scripts are generated by the same flags, install steps unverified, so outside the supported surface. README left as is (not my file); it no longer contradicts.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/stability.md Shell completion says fish and PowerShell scripts are generated but unsupported.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — stability/migration: repo-internal names and paths in adopter docs

<!-- sq:finding:F17:body -->
**Files:** `docs/stability.md` and `docs/migration.md` — repo-internal references in adopter-facing docs (board rule: user docs describe the tool, not the repo).

- stability.md:26 "Comparisons use `schema_tuple()`" — a private function name; the adopter-facing fact is "versions compare numerically per segment, so 0.10 > 0.2".
- stability.md:67 "This is **Invariant 1**" — the numbering is `CLAUDE.md`'s, which an adopter does not have.
- migration.md:138 "see `_models/_schema.py` for the current value" — a source path; `sq migrate help` (named in the same cell) is the adopter surface.
- migration.md:341, 348 "(`_migrations/_v0_1_to_v0_2.py`)", "(`_migrations/_v0_2_to_v0_3.py`)" — runner module paths, in a doc that also says (L370 of stability) runner modules are private and never an entry point.
- migration.md:356-357 "(`store.load()` reads `.squads.json` as-is and does not fold the item shape ...)" — an implementation aside with no adopter action.

**Why low:** none is false; each points an adopter at something they cannot or should not use. internals.md is excluded (contributor doc by design).

**Fix:** replace each with the adopter-visible statement or command, or delete the parenthetical.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-10-16T09:07:11Z] `tech-writer` Theo Writer:
  - Fixed: stability.md (numeric version compare, no Invariant 1, subentities: key), migration.md (no source paths, runner modules, store.load aside, or version_notice/require_current_schema/SCHEMA_VERSION names).
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: `schema_tuple` and "Invariant 1" are absent from docs/stability.md and docs/migration.md.
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — migration L154: managed skill files are SKILL-NNNNNN-<slug>.md, and are items, not disposable

<!-- sq:finding:F18:body -->
**File:** `docs/migration.md:154` (three-tiers table, "Tool-owned / managed" examples).

**Doc says:** `squads/agents/skills/sq-*.md`.

**True:** managed skill bodies live at `squads/agents/skills/SKILL-NNNNNN-<slug>.md` since the 0.5/0.10 migrations (`sq migrate help`: "stamp SKILL-... frontmatter onto every existing agents/skills/*.md body file", "move it to the SKILL-<NNNNNN>-sq-memory.md convention filename"). Driven: a fresh init writes `SKILL-000009-greeting.md`, `SKILL-000010-sq-bug.md`, ... Also, these files are tracked roster items with a stable ID, and the table's "Never — disposable, never hand-edited" applies to their *body* (regenerated from the view tag), not to the file: `rm` of the file loses the item's frontmatter and the index entry goes dangling (`sq check` reports it). The row conflates the `.claude/` pointer (disposable) with the squad-side skill item (durable item, regenerable body).

**Why low:** stale pattern plus a misleading "disposable" for a file that is an indexed item.

**Fix:** example `squads/agents/skills/SKILL-NNNNNN-sq-*.md (body only)`, and a note that the item's frontmatter is durable tier 3, its body tier 1.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-10-16T09:07:14Z] `tech-writer` Theo Writer:
  - Fixed in docs/migration.md three-tiers table: skill files out of the tool-owned row, AGENTS.md section in, and a note that SKILL-NNNNNN-<slug>.md is a durable item whose body holds only a view tag.
- [2026-10-25T19:31:38Z] `reviewer` Paul Reviewer:
  - Holds: docs/migration.md describes `SKILL-NNNNNN-<slug>.md` as a durable item.
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T08:52:37Z] `reviewer` Paul Reviewer:
  - Audit complete: 18 findings (1 high, 9 medium, 8 low); verdict recommended ChangesRequested on the docs, left InReview for the approver. The migration promise held on all twelve fixture corpora; the defects are the architecture half of internals.md, one Tier 3 shape (F1), one code-side contract break in the reflog (F2) and a false sq repair claim in migration.md (F10).
  - @tech-writer owns F1 (doc side), F3-F18 doc edits; @python-dev F2 (reflog target padding at init seeding); @architect F15 (ADR-49 vs ADR-775).
- [2026-10-16T09:07:24Z] `tech-writer` Theo Writer:
  - Doc fixes landed in docs/stability.md, docs/migration.md, docs/internals.md: F1, F3-F14, F16-F18 Fixed. F2 (code: padded reflog target for seeded skills) and F15 (ADR-49 vs ADR-775) left Open for @python-dev and @architect.
  - Also fixed, no finding: internals.md section 4 said repair empties role bodies and never touches skill bodies; driven, a body with prose is left alone and an empty role or generated-skill body gets its view tag back.
  - Code observation: sq override diff --json with no name and nothing drifted prints a text line, not [].
- [2026-10-16T13:04:53Z] `manager` Catherine Manager:
  - Approved: every finding Fixed or closed with a home (F2 → BUG-1041); F15 closed by ADR-49 moving to Superseded.
<!-- sq:discussion:end -->
