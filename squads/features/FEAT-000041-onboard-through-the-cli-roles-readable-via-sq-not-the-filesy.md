---
id: FEAT-000041
sequence_id: 41
type: feature
title: 'Onboard through the CLI: roles readable via sq, not the filesystem'
status: Done
parent: EPIC-000012
author: product-owner
priority: high
refs:
- FEAT-000040
- FEAT-000033
description: sq role show displays the complete definition (working agreements included)
  and every onboarding text (CLAUDE.md section, skills) directs agents to sq commands
  instead of reading files under squads/
subentities:
- local_id: US1
  title: As an agent adopting my persona, I want sq role show to give me the complete
    definition including working agreements, so that I never open the file to learn
    my job
  status: Done
- local_id: US2
  title: As an agent following the onboarding texts, I want every read they prescribe
    to be an sq command, so that one interface covers work and identity — locally
    and, someday, remotely
  status: Done
created_at: '2026-06-11T09:02:40Z'
updated_at: '2026-06-12T08:05:41Z'
---
<!-- sq:body -->
## Problem

Every ticket manipulation goes through `sq` — but to learn *who they are*, agents are told to read
files: the generated CLAUDE.md section says "load their role definition from
`squads/agents/roles/`", and `sq role show <slug>` is not a substitute because it prints only the
catalog card (mission, responsibilities) — the **working agreements**, the part an agent actually
needs to behave correctly, live only in the item body. Observed live (2026-06-11): the product
owner re-read her role by opening the `.md` directly, in a session where everything else went
through the CLI. One interface for work, a filesystem detour for identity.

## Value

The CLI becomes the *single* interface agents are taught: read your role, your skills, your
items — all through `sq`. That consistency matters beyond elegance: remote mode (FEAT-000033)
has no filesystem to detour to, so any onboarding text that says "read this path" breaks the day
the squad is remote; text that says "run `sq role show`" doesn't.

## Scope

- **`sq role show <slug>` shows the complete definition**: the catalog card *plus* the tracked
  item's body (working agreements, skills list) — everything the file would give, rendered. Honors
  FEAT-000026's conventions when both land (panes, --raw, piped behaviour).
- **Onboarding texts direct to the CLI**: the generated CLAUDE.md section's impersonation
  paragraph says `sq role show <slug>` (not "load from `squads/agents/roles/`"); the `squads` and
  `greeting` skills and the role files' own self-references get the same sweep.
- **Pointer files are exempt**: `.claude/agents/*.md` `@`-including the role path is backend
  plumbing (how Claude Code boots a subagent), not agent guidance — paths stay. The rule:
  *machinery may use paths; instructions teach commands.*
- Sweep for siblings: any other "read the file at …" guidance in generated content (skills,
  workflow cheatsheet, docs) gets the same treatment where an sq command exists; gaps where no
  command exists get noted (candidate: `sq skill show`?).
- Regenerated via `sq sync`; no migration (managed files are regenerable).

## Acceptance

- `sq role show <slug>` output contains the working agreements and skills, matching the item body;
  covered by a test.
- The generated CLAUDE.md section and bundled skills contain no agent-facing instruction to read
  files under `squads/` for content an sq command provides; pointer files unchanged.
- An agent following only onboarding texts can fully brief on their role without a single file
  read (the live scenario above, replayed through the CLI).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 41 add-story "As a <role>, I want … so that …"`; track with `sq feature 41 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | As an agent adopting my persona, I want sq role show to give me the complete definition including working agreements, so that I never open the file to learn my job |
| US2 | Done |  | As an agent following the onboarding texts, I want every read they prescribe to be an sq command, so that one interface covers work and identity — locally and, someday, remotely |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an agent adopting my persona, I want sq role show to give me the complete definition including working agreements, so that I never open the file to learn my job

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** sq role show <slug> renders catalog card + item body (mission, responsibilities, working agreements, skills); content matches the .md; test asserts the agreements are present.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an agent following the onboarding texts, I want every read they prescribe to be an sq command, so that one interface covers work and identity — locally and, someday, remotely

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** the CLAUDE.md impersonation paragraph and the bundled skills reference sq role show / sq docs / sq <type> show only; grep for 'squads/agents/roles' in agent-facing generated text comes back empty (pointer files exempt); sq sync propagates.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T07:53:48Z] Olivia Lead:
  - Broke FEAT-000041 into two Ready tasks, both assigned @python-dev.
  - TASK-000054 (US1): sq role show <slug> must render the active role item body (working agreements + skills) below the catalog card. Today show_role uses role_by_slug only and never reads the tracked item — the agreements are invisible from the CLI. Reuse the existing slug→role-item resolver in _services/_base.py (~L232); pull the body region with _sections.get_section(text, markers.BODY). Builds on FEAT-000040's complete role body. Acceptance: output contains the agreements, covered by a test.
  - TASK-000055 (US2): sweep onboarding texts to teach sq commands, not paths. I already did the sweep — the ONLY offender is claude_section.md.j2 L43-44 (impersonation paragraph: 'load their role definition from squads/agents/roles/' → 'run sq role show <slug>'). The squads/greeting/skill/operator/workflow templates and role catalog bodies are already path-free. pointer_agent.md.j2's @-include is exempt machinery. sq sync regenerates CLAUDE.md afterward. Soft-depends on TASK-000054 for the replay-the-live-scenario acceptance.
  - Gap noted, not invented (per scope): sq skill show exists but prints only metadata, not the skill body. No current instruction sends agents to a skill *file* (skills are named by handle), so no command is needed now — recorded as a candidate follow-up if a 'read your skill' instruction ever appears.
  - Suggested order: TASK-000054 first (the CLI surface US2 points agents to), then TASK-000055. @python-dev — start with 54.
- [2026-06-12T08:02:11Z] Elias Python:
  - TASK-000054 and TASK-000055 are done. Here is what changed:
  - **TASK-000054** — sq role show now renders the complete role definition. Added `role_body(slug)` to `ServiceCore` in `src/squads/_services/_base.py`: reads the active role item's body section via `_sections.get_section`. Updated `show_role` in `src/squads/_cli/_role.py` to call this after the card panel; it escapes all dynamic content with `e()`. Fallback for bundled-only roles (no tracked item) or uninitialized squads: card is printed plus a dim hint to run `sq role activate <slug>` then `sq sync`. FEAT-000026 (panes/--raw) has not landed; current Rich rendering style is kept. Tests added: `test_role_body_active_contains_working_agreements`, `test_role_body_bundled_only_returns_none` in test_service.py; `test_role_show_includes_body_and_degrades_for_bundled` in test_cli.py.
  - **TASK-000055** — Rewrote the impersonation paragraph in `src/squads/_rendering/templates/claude/claude_section.md.j2` (lines 43-44): replaces 'load their role definition from `{{ squad_dir }}/agents/roles/`' with 'run `sq role show <slug>` to read the full role definition'. Ran `sq sync` — the repo CLAUDE.md section was regenerated; grep for `agents/roles/` in agent-facing generated text comes back empty. Pointer files (`.claude/agents/*.md`) are unchanged (exempt backend machinery). Confirmed `sq skill show` prints metadata only — no path-read instruction found requiring it, so it is NOT expanded here; recorded as follow-up candidate. Test added: `test_claude_md_impersonation_uses_sq_command_not_path` in test_backend_claude.py.
  - Gates all clean: 280 passed, 1 skipped; pyright 0 errors; ruff all checks passed. @reviewer — ready for review.
- [2026-06-12T08:05:17Z] Paul Reviewer:
  - Review of TASK-000054 + TASK-000055 (impl in working tree): **APPROVED**, no findings. Gates all green: pytest (all pass, 1 skipped), pyright (0 errors), ruff check + format clean.
  - Correctness — layering: CLI → service only. show_role calls svc.role_body(slug); the new ServiceCore.role_body resolves the active role item, reads its file, and extracts the sq:body region via sections.get_section — marker-safe (read-only, no body rewrite), returns None when there's no active item. Clean.
  - try/except SquadsError in show_role (src/squads/_cli/_role.py:68-72): sound. It wraps get_service()+role_body so an *uninitialized squad* degrades to the same activation hint as a bundled-only role — verified manually in an empty dir (exit 0, hint printed). It does NOT mask a corrupt index in a harmful way: a corrupt index would surface elsewhere on any real mutation, and for a read-only 'show your role card' the graceful card+hint is the right UX. Acceptable; the catalog card still always prints.
  - Rich escaping: the body is printed as console.print(e(body)) at _role.py:76 — exactly the established convention used by print_item at _cli/_common.py:121 for item bodies. The working agreements contain literal [bold]/[/bold] and backtick-wrapped <!-- sq:* --> markers; e() escapes them so they render literally rather than as Rich markup. The card rows and the dim hint also wrap all dynamic values (full_name/slug/title/model/mission/responsibilities) in e(). Consistent and correct.
  - Onboarding sweep (acceptance): claude_section.md.j2 impersonation paragraph now teaches 'run sq role show <slug>' instead of 'load their role definition from <squad>/agents/roles/'. Grepped generated content: no agent-facing 'agents/roles/' instruction in the managed CLAUDE.md section (lines 137-237; the only repo hit is project-doc prose at line 59, outside the section), none in bundled skills, greeting, role files, or role.md.j2. Pointer files (.claude/) unchanged — matches the 'machinery may use paths; instructions teach commands' rule.
  - Output quality: ran sq role show manager / qa — card + full body (Mission, Responsibilities, Skills, Working agreements, spawned-vs-live regimes) render cleanly; bundled-only / uninitialized path degrades to the activation hint at exit 0.
  - Acceptance criteria met: (1) output contains working agreements + skills matching the item body, covered by test_role_body_active_contains_working_agreements + test_role_show_includes_body_and_degrades_for_bundled; (2) no agent-facing path instruction in generated CLAUDE.md/skills, pointer files unchanged, covered by test_claude_md_impersonation_uses_sq_command_not_path (incl. stability across sync); (3) an agent can fully self-brief via the CLI. Tests well-placed per CLAUDE.md (service-level + CLI smoke + backend). Docstrings present; strict typing clean. No changes required.
<!-- sq:discussion:end -->
