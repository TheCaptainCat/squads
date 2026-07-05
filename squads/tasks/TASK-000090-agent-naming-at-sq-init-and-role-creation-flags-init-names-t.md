---
id: TASK-90
sequence_id: 90
type: task
title: Agent naming at sq init and role creation (flags, [init.names], TTY prompt)
status: Done
parent: FEAT-14
author: tech-lead
priority: high
refs:
- TASK-91:blocks
description: Repeatable --name slug=Full Name + [init.names] + TTY prompting/--default-names;
  flow to extra.full_name → roster/pointers/CLAUDE.md
subentities:
- local_id: ST1
  title: 'sq init: --name flags + [init.names] + TTY prompt/--default-names'
  status: Done
  story: US4
- local_id: ST2
  title: sq role activate/dev add --name; flow to extra.full_name → roster/pointers/CLAUDE.md
  status: Done
  story: US4
created_at: '2026-06-12T20:57:27Z'
updated_at: '2026-06-12T21:55:47Z'
---
<!-- sq:body -->
Naming-surface task for FEAT-14 (ADR-85 §4, Consequences 'sq init gains interactive prompting' + 'new .squads.toml keys').

**Goal.** Make a role's name a first-class input at both creation surfaces, with the bundled pool as fallback — names ride the existing `extra.full_name` channel, so no new downstream plumbing.

**Scope — sq init (three composing layers).** (1) Repeatable `--name <slug>=<Full Name>` flags. (2) Optional `[init.names]` table in `.squads.toml` (the declarative, checked-in path; round-trips through `to_toml()`). (3) **Interactive prompt, TTY only**: when stdin/stdout is a TTY, prompt for each role still un-named after flags+`[init.names]`, UNLESS `--default-names` is passed; when NOT a TTY (CI/pipes), behave exactly as `--default-names` (never block). Flags and `[init.names]` **pre-answer** prompts — a fully declarative invocation is never interactive even at a TTY.

**Scope — role creation later.** `sq role activate <slug> --name '…'` and the existing `sq dev add --name '…'` accept a name; absent it, the same fallback applies. A `roles/<slug>.toml` override carrying `full_name` seeds the name at activation (coordinate with T2).

**Fallback (never blank).** Any role still un-named after flags/config/prompting falls through to bundled `RoleDef.full_name` (bundled roles) or `DEV_NAME_POOL` (developers). `--default-names` and the non-TTY path take this fallback for every otherwise-unnamed role.

**Flow + frozen rule.** The chosen name is written to the ROLE item's frontmatter `extra.full_name` (single source of truth); `roster()` → `RoleView.full_name` → CLAUDE.md Agent-roster section, agent pointer files, and the rendered role body already read it. **Slugs stay canonical and non-renamable** — names are free, the slug is the addressing key.

**Acceptance (covered by tests).** Names supplied via flag, via `[init.names]`, via interactive prompt at a **faked TTY**, suppressed by `--default-names`, and the **non-TTY-implies-default** path; plus `sq role activate --name` flowing through to roster + pointer + CLAUDE.md. Unnamed roles still get a pool/bundled name. Contracted: names live in `extra.full_name`, prompt PRESENCE + the `--default-names`/TTY rule (the prompt copy is NOT frozen).

**Dependencies.** Mostly independent — can run in parallel with T1/T3. One coordination point with T2: the `roles/<slug>.toml` `full_name` seed at activation.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 90 add-subtask "<title>"`; track with `sq task 90 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | sq init: --name flags + [init.names] + TTY prompt/--default-names | US4 |
| ST2 | Done |  | sq role activate/dev add --name; flow to extra.full_name → roster/pointers/CLAUDE.md | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq init: --name flags + [init.names] + TTY prompt/--default-names

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US4 — As a project lead, I want to supply each agent's name at init and at role creation, so that my squad's roster is named the way my team wants
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — sq role activate/dev add --name; flow to extra.full_name → roster/pointers/CLAUDE.md

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US4 — As a project lead, I want to supply each agent's name at init and at role creation, so that my squad's roster is named the way my team wants
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T21:40:21Z] Elias Python:
  - Implementation complete. Three-layer naming surface as specified in ADR-85 §4.
  - **sq init**: Added repeatable --name slug=Full Name flags and --default-names flag. TTY detection is injectable (module-level _is_tty callable; tests monkeypatch it). Names from [init.names] in a pre-existing .squads.toml are read and merged (flags win on conflict). At a TTY without --default-names, sq init prompts for each role not already named; blank answer keeps the bundled default. Non-TTY and --default-names skip all prompting.
  - **sq role activate**: Added --name option; passed through as name kwarg to service.activate_role().
  - **Service layer**: activate_role(slug, *, name=None) accepts an explicit name; uses dataclasses.replace to swap the full_name on the RoleDef before storing it. init() accepts names dict and passes per-slug names down.
  - **SquadsConfig**: Added init_names: dict[str, str] field. to_toml() writes an [init.names] section when non-empty. from_toml_dict() hoists the nested [init] table into init_names.
  - **End-to-end**: Names ride extra.full_name. Verified: CLAUDE.md Agent roster section picks up the custom name; pointer files render the custom name; the role item frontmatter stores it. Pool fallback for devs and bundled fallback for predefined roles are unchanged.
  - **Tests**: 31 new tests in tests/test_agent_naming.py covering: service activate_role with name kwarg; init names kwarg; config round-trip; CLAUDE.md flow; CLI --name single/multiple; --default-names; TTY prompt path (mocked); blank answer keeps default; flag wins over config; [init.names] pre-answers prompts; malformed --name (missing =, empty slug, empty name). Suite: 477 passed, 1 skipped. pyright + ruff clean.
  - @reviewer ready for review.
- [2026-06-12T21:43:44Z] Paul Reviewer:
  - APPROVED (REV-96). Reviewed the naming surface against ADR-85 §4. @tech-lead @python-dev
  - Correctness confirmed: --name flags and [init.names] both work and flags win over config; TTY prompts cover only the gaps; --default-names and non-TTY both skip prompting; blank prompt answer falls back to pool/bundled; unnamed roles never blank.
  - End-to-end verified by running the CLI (not just the extra field): a custom name flows to the ROLE item frontmatter, the agent pointer file (.claude/agents/<slug>.md), AND the CLAUDE.md Agent roster section.
  - The prior mid-flight _config.py pyright errors are RESOLVED — from_toml_dict hoists the nested [init] table with proper narrowing and init_names is soundly typed; whole-tree pyright is 0/0/0.
  - Green confirmed: pytest 477 passed / 1 skipped; pyright clean; ruff check + format clean. The _is_tty seam is cleanly injectable and tests drive both branches; malformed/unknown --name inputs raise SquadsError → clean message + exit 1 (no traceback).
  - One non-blocking nit: test_activate_name_flows_to_pointer_file guards its assert with 'if pointer.exists()'; I verified the pointer is written today so it fires, but an unconditional assert would catch a future regression. Not a blocker.
<!-- sq:discussion:end -->
