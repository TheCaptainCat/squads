---
id: FEAT-792
sequence_id: 792
type: feature
title: Pointers name commands, never a local path
status: Draft
author: product-owner
refs:
- ADR-781:implements
- BUG-784
subentities:
- local_id: US1
  title: Drop squad_path from all four pointer/entry templates
  status: Todo
- local_id: US2
  title: Slug-bound startup commands and the definition-fetch command
  status: Todo
- local_id: US3
  title: Five per-host questions on the AgentBackend ABC
  status: Todo
- local_id: US4
  title: Currency detection for per-entry pointers
  status: Todo
- local_id: US5
  title: Reword invariant 5 to state the containment rule
  status: Todo
created_at: '2026-08-24T18:28:02Z'
updated_at: '2026-08-24T18:29:12Z'
---
<!-- sq:body -->
## The problem

Both `.claude/` pointer templates instruct the agent host with a local file path
(`@{{ squad_path }}`), and the `agents_md` backend displays the same local path in a different
spelling. That instruction is unsatisfiable when the CLI is a client to a squads server — there is
no local squad directory for the path to name. And the path is only the visible half: a pointer's
contents materialize seven values of role state (slug, description, model, colour, spawn
authority, the resolved skills list, and the full name in its body) into a file that is committed
by default, so under remote mode a pointer is a tracked snapshot of state the repository does not
hold, wrong from the moment the server moves with nothing reporting it.

ADR-781 rules on both the path and the contents: no materialized pointer may carry a local path;
a pointer carries only what a host must consume at or before spawn plus commands that fetch the
rest; and detection of a wrong or missing pointer must reach the operator unprompted, because an
adopter has no baseline for what a correct pointer looks like.

**Scope note.** BUG-784 already shipped the presence half of detection — `managed_entry_paths`
landed in commit `383d5e8` (Verified), so `sq check`/`sq sync` already report a missing per-entry
pointer at warn, scoped to the roster's live entries, and `sq sync` already names what it
regenerated for that case. This feature is scoped to everything ADR-781 decides beyond that: the
template rewrite itself, the containment rule's other consequences, the currency half of
detection, and the invariant wording. It does not re-do presence.

## Shape

- **All four pointer/entry templates lose `squad_path`.** `pointer_agent.md.j2` and
  `pointer_skill.md.j2` drop `@{{ squad_path }}`; `agents_md/role_entry.md.j2` and
  `skill_entry.md.j2` drop the `**Squad file:**` line. The `squad_path` context value stops being
  computed for any of the seven producer sites that fed them (five backend render sites, two
  frozen migration runners — which drop the now-dead kwarg, emitting today's pointer shape rather
  than a historical one, per the rule that a migration renders regenerable artifacts fresh).
- **A pointer instead names the command that renders the full definition**
  (`sq role <slug> show` / `sq skill <slug> show`), and gains the slug-bound startup command set
  moved from the role body template (`sq memory <slug> list`, `sq memory <slug> show <slug>`,
  `sq board list`, `sq mine <slug>`, `sq inbox <slug>`) — removing the duplicate copy from
  `agents/role.md.j2` rather than leaving two hand-maintained copies. Both render from one declared
  list in code.
- **The containment rule governs what stays in a pointer's frontmatter**: materialize a value only
  when the host consumes it at or before spawn *and* a runtime fetch cannot substitute for its
  effect (true when the value restricts or configures the session; false when it merely supplies
  content). Applied: `name`/`description`/`model`/`color`/`disallowedTools`/the resolved `skills`
  list all stay (each restricts or configures); `full_name` and the full definition move to the
  fetch command.
- **`AgentBackend`'s ABC gains the five per-host questions** ADR-781 §2d states, each answerable
  from the host's own documentation alone: can an agent under this host execute a command; which
  projected values does this host's configuration have a place for (undeclared ones are reported
  once at write time and dropped, on `model_drop_warning`'s precedent); which of those are the
  irreducible discovery set; which constrain the session rather than configure it; and what would
  a pure render of this entry look like. `_claude_code` answers question 1 "yes" and is rebuilt on
  it; `_agents_md` answers "not knowably" and keeps its compiled roster prose for that stated
  reason rather than as an unexplained asymmetry.
- **Currency detection is added** (the half BUG-784 did not cover): `sq check` renders a fresh copy
  of each declared per-entry artifact and compares it against what's on disk, reporting drift —
  error for a drifted/missing capability-restricting field (a stale `disallowedTools` is a live
  regression against the squad's own revocation), warn for everything else — by comparison, never
  by a stamp (a pointer is tool-owned and re-renderable, unlike a user-owned override). This does
  not read output back as a declaration source; the render is the expectation the check tests
  against, preserving the never-read-back rule.
- **`sq sync` reports what it regenerated** for a currency fix, the same shape BUG-784 already
  established for a presence fix, so an operator learns both that there was a fault and that a
  commit is now owed.
- **Invariant 5 is reworded** to state the containment rule directly rather than locating
  definitions by directory (a claim remote mode breaks): "A pointer carries only what the host
  must read before an agent can run — its identity, the text the host selects it by, and the
  constraints squads imposes on the session — plus the commands that fetch the rest."
- **Release ordering**: this is a bundled-template edit (all four pointer/entry templates plus the
  managed-section golden and the generated-agent-text guards move together), so it queues behind
  the version bump before the manifest regeneration, per ADR-781 §6 — the single statement of that
  ordering for every template-touching change landing this release.

## Acceptance

- No template squads writes into an agent host's configuration contains `squad_path` or any local
  file path; the context value is no longer computed at any of its seven former producer sites.
- A generated Claude Code pointer contains: identity fields, the slug-bound startup command set
  (memory/board/mine/inbox with the slug substituted), and `sq role <slug> show` (or `sq skill
  <slug> show`) as the definition-fetch command — and nothing that duplicates a value `sq` can
  answer. The role body template no longer carries its own copy of the startup command set.
- The `agents_md` backend's compiled roster entries drop the `**Squad file:**` line and carry no
  replacement path; its roster prose stays for the stated reason (its backend answers "no" to the
  can-execute-a-command question), not by default.
- `AgentBackend`'s ABC declares the five per-host questions; both bundled backends answer all
  five explicitly, and a future backend is not required to reopen the rule to answer them for
  itself.
- Currency checking exists in `sq check`: editing a live role's `disallowedTools` or resolved
  skills without running `sq sync` is caught (error for the capability field, warn otherwise);
  running `sq sync` after fixes it and `sq sync` states what it regenerated. A correct,
  already-current pointer produces no finding.
- The frozen migration runners that render pointer templates (`_v0_4_to_v0_5.py`,
  `_v0_8_to_v0_10.py`) no longer pass `squad_path`, and emit the current pointer shape.
- Invariant 5 in CLAUDE.md's managed region reads the reworded containment statement, edited at
  its template source (`claude_section.md.j2`), not the rendered file.
- `sq check`/`sq sync` output, once this lands, is unchanged for the presence findings BUG-784
  already shipped — this feature adds currency findings alongside them, not a second presence
  mechanism.

## Out of scope

- Presence detection for missing per-entry pointers — already shipped (BUG-784, commit
  `383d5e8`, Verified).
- Building a Codex, Copilot or Cursor backend — this feature only adds the ABC questions those
  future backends will answer; it builds no third backend.
- Remote-mode connectivity design for the currency check (whether it runs against a cache,
  requires connectivity, or degrades to "cannot verify") — ADR-781 §2c names this as the one
  deferral that remains, narrower than before; the offline currency check this feature builds
  gives every mode a floor regardless.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 792 add-story "As a <role>, I want … so that …"`; track with `sq feature 792 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Drop squad_path from all four pointer/entry templates |
| US2 | Todo |  | Slug-bound startup commands and the definition-fetch command |
| US3 | Todo |  | Five per-host questions on the AgentBackend ABC |
| US4 | Todo |  | Currency detection for per-entry pointers |
| US5 | Todo |  | Reword invariant 5 to state the containment rule |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Drop squad_path from all four pointer/entry templates

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
All four pointer/entry templates lose `squad_path`: `pointer_agent.md.j2` and
`pointer_skill.md.j2` drop the `@{{ squad_path }}` load-bearing line, `agents_md/role_entry.md.j2`
and `skill_entry.md.j2` drop the `**Squad file:**` display line. The `squad_path` context value
stops being computed at any of its seven former producer sites (five backend render sites, two
frozen migration runners), and the two migration runners drop the now-dead kwarg rather than
keeping it — a migration renders today's pointer shape, never a historical one pinned inside the
runner.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Slug-bound startup commands and the definition-fetch command

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
The Claude Code agent and skill pointers gain, in place of the dropped path: the slug-bound
startup command set (`sq memory <slug> list`, `sq memory <slug> show <slug>`, `sq board list`,
`sq mine <slug>`, `sq inbox <slug>`) moved out of the role body template, and one command that
renders the full definition (`sq role <slug> show` / `sq skill <slug> show`). The role body
template's own copy of the startup command set is removed rather than left duplicated beside the
pointer's. Both surfaces render from one declared list in code, so a command added to the startup
set appears in both or in neither. The containment rule (materialize a value only when the host
consumes it at or before spawn and a runtime fetch cannot substitute for its effect) is what
decides frontmatter contents: `name`/`description`/`model`/`color`/`disallowedTools`/the resolved
`skills` list stay; `full_name` and the mission/responsibilities move to the fetch command.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Five per-host questions on the AgentBackend ABC

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
`AgentBackend`'s ABC declares the five per-host questions ADR-781 §2d states, each phrased so a
future backend's author can answer it from their host's own documentation alone: whether an agent
under the host can execute a command; which projected values the host's configuration has a
place for (an undeclared one is reported once at write time and dropped, on `model_drop_warning`'s
precedent — never silently, and never validated a second time at storage time); which of those
are the irreducible discovery set; which constrain the session rather than merely configure it;
and what a pure render of an entry looks like. `_claude_code` answers question 1 "yes" and its
templates are rebuilt on that answer (this story's sibling stories); `_agents_md` answers "not
knowably" and keeps its compiled roster prose (full name, slug, title, mission, responsibilities)
for that stated, declared reason — a host that cannot run a command has no fetch to substitute
with — rather than as an unexplained asymmetry with the Claude Code backend.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Currency detection for per-entry pointers

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
Currency joins presence (already shipped by BUG-784) as the second half of pointer detection:
`sq check` renders a fresh copy of each declared live per-entry artifact and compares it byte-for-
byte against what's on disk, reporting drift by comparison rather than by a stamp — a pointer is
tool-owned and re-renderable, unlike a user-owned override, so comparison answers "is this wrong"
directly. Severity follows the containment rule's own distinction: a drifted or missing value that
restricts the session (`disallowedTools`) is an error, because a stale grant is a live regression
against the squad's own revocation and is not repairable from inside the session it governs;
everything else is a warn. The comparison never reads a backend's own output back as a declaration
source — every declared value still comes from the role/skill item, and the render is the
expectation under test, preserving the existing never-read-back guard. `sq sync` reports what it
regenerated for a currency fix, the same shape BUG-784 already established for a presence fix.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Reword invariant 5 to state the containment rule

<!-- sq:story:US5:head -->
**Status:** ⚪ Todo
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
CLAUDE.md's invariant 5 is reworded at its template source (`claude/claude_section.md.j2`, not the
rendered file) to state the containment rule directly instead of locating definitions by
directory — a locality claim remote mode breaks: "A pointer carries only what the host must read
before an agent can run — its identity, the text the host selects it by, and the constraints
squads imposes on the session — plus the commands that fetch the rest. Anything `sq` can answer, a
pointer does not hold." This is a bundled-template edit alongside the pointer/entry templates
themselves, so the managed-section golden and the generated-agent-text guards move together with
them, and the whole set queues behind the version bump before the manifest regeneration, per the
release ordering ADR-781 §6 states once for every template-touching change landing this release.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
