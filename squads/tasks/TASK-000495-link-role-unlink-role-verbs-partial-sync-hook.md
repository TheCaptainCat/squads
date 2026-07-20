---
id: TASK-495
sequence_id: 495
type: task
title: link-role / unlink-role verbs + partial-sync hook
status: Done
parent: FEAT-491
author: tech-lead
refs:
- ADR-492:implements
- BUG-490:fixes
- TASK-494:depends-on
description: Dedicated scope verbs that write/remove the edge and re-sync only the
  affected role pointer(s)+body
subentities:
- local_id: ST1
  title: link-role / unlink-role verbs scope a skill to roles
  status: Done
  story: US3
- local_id: ST2
  title: Partial-sync hook keeps affected role pointers current
  status: Done
  story: US4
created_at: '2026-07-20T08:59:19Z'
updated_at: '2026-07-20T10:23:48Z'
---
<!-- sq:body -->
## Scope

Add the sanctioned CLI surface for role scoping and keep role pointers current without a manual
full resync — ADR-492 Pillar 3's verbs + partial-sync hook. Builds on the `scopes` kind and
resolver from the sibling foundation task.

### 1. `link-role` / `unlink-role` verbs (`_cli/_skill.py` + service)

Add to the addressed skill subgroup:

- `sq skill <n> link-role <role-slug-or-id>` — writes the `ROLE-n:scopes` edge on the skill.
- `sq skill <n> unlink-role <role-slug-or-id>` — removes that edge.

Both resolve the role argument and error clearly if the role does not exist (no silently
accepted broken link). These are the supported surface: raw `sq skill <n> ref add ROLE-n
--kind scopes` would write the same edge but skip the hook below, so the dedicated verb is the
sanctioned path (note this in the verb help).

### 2. Partial-sync hook

After writing/removing the edge, recompute the resolver for **only the affected role(s)** and
rewrite that role's pointer `skills:` and body `## Skills` (and its `extra[skills]` cache).
Other roles' pointers/bodies are left byte-untouched. A full `sq sync` already re-renders every
role pointer and body, so with the resolver as their skills source it recomputes for all roles —
the hook is an optimisation, never the only path.

## Acceptance

- Linking a skill to one or more roles makes exactly those roles preload it (pointer + body),
  as part of the link command — no separate resync needed.
- A skill can be scoped to several roles at once (the release-runbook case: manager, devops,
  tech-writer).
- Unlinking removes the skill from that one role's preload set; removing the last role link
  leaves no orphaned reference anywhere.
- Linking to a non-existent role gives a clear error.
- Only the affected role(s) are touched by a link/unlink; other roles are unchanged.
- The end state reached via link/unlink is identical to the state after a full `sq sync` — no
  drift between the two paths.
- Deleting a scoped role leaves the skill's edge dangling and `sq check` flags it.
- Tests: link/unlink (single + multi-role), non-existent-role error, only-affected-role touched,
  link/unlink-vs-full-sync parity, dangling-edge-after-role-delete. Name tests by behaviour,
  not by ticket id.

## Code sites

- `src/squads/_cli/_skill.py` — addressed subgroup (`link-role`/`unlink-role`).
- `src/squads/_services/` — link/unlink service methods + the partial-sync hook (reuse the
  resolver + the existing per-role pointer/body regen).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 495 add-subtask "<title>"`; track with `sq task 495 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | link-role / unlink-role verbs scope a skill to roles | US3 |
| ST2 | Done |  | Partial-sync hook keeps affected role pointers current | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — link-role / unlink-role verbs scope a skill to roles

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a squad author, I want to scope a custom skill to one or more roles so exactly those agents preload it
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Dedicated verbs write/remove the SKILL->ROLE:scopes edge; multi-role scoping; unlink drops one role; removing the last link leaves no orphan; linking a non-existent role errors clearly.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Partial-sync hook keeps affected role pointers current

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US4 — As a squad author, I want role pointers to stay current when I link or unlink a skill without a manual full resync
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
link/unlink recompute the resolver and rewrite only the affected role(s)' pointer + body + extra[skills]; other roles untouched; end state identical to a full sq sync (no drift).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T10:10:38Z] Elias Python:
  - @manager Implemented: sq skill <n> link-role/unlink-role (src/squads/_cli/_skill.py), Service.link_role/unlink_role (src/squads/_services/_refs.py, reusing add_ref for link + kind-scoped edge removal for unlink), and the partial-sync hook _resync_role_skills (src/squads/_services/_base.py, alongside the moved _refresh_role_skills_extra/_regen_role_body helpers).
  - Behavior: both verbs resolve the role by slug/id/number (resolve_agent_addr), write/remove the ROLE-n:scopes edge, then rewrite only that role's pointer + body ## Skills + extra.skills cache — other roles untouched. Idempotent: re-linking/-unlinking is a clean no-op. Linking/unlinking a non-role or non-existent role errors clearly.
  - Fixed a latent bug found along the way: _refresh_role_skills_extra's early-return compared against the index-cached extra.skills (which this call never updates, only the .md frontmatter does) — a second resync that reverted to the original skill set (e.g. link then unlink) would wrongly no-op and leave the .md file stale. Removed the stale comparison; now always writes when a resolved list exists.
  - Gates: pyright + ruff clean; tests/meta guard clean; targeted tests (skill/scope/role/link/sync/backend) 259 passed; sq check clean. New tests: tests/cli/test_skill_role_scoping_verbs.py, tests/service/test_skill_role_scope_link_unlink_hook.py (incl. dedicated-verb-vs-raw-ref-add parity, only-affected-role isolation, idempotency, non-role rejection).
  - ST1 + ST2 -> Done.
- [2026-07-20T10:17:14Z] Mara Tester:
  - @manager QA verified end-to-end role-scoping in a throwaway squad (not this repo's board). All PASS:
  - US3 (scope to role): link-role manager on a fresh custom skill immediately added it to manager's pointer skills: + body ## Skills; tech-lead untouched. Multi-role (manager+devops+tech-writer) worked simultaneously; other roles stayed clean.
  - US4 (partial resync, no manual sync needed): effect visible immediately after link-role/unlink-role, before any sq sync. Only the affected role's pointer+body+extra[skills] cache changed — byte-diffed tech-lead pointer/body as IDENTICAL before vs after.
  - Isolation: unlink-role brought manager's pointer/body back byte-identical to pre-link baseline; unrelated roles never touched across the whole run.
  - Dedicated verb vs raw ref add: raw 'sq skill <n> ref add ROLE-1 --kind scopes' wrote the edge but left manager's pointer/body stale (0 occurrences); a follow-up sq sync then reconciled it, and the resulting files were byte-identical to what link-role produces directly (no drift).
  - Full-sync consistency + system skills: after sq sync every role still carries its always-on system skills (squads/greeting/sq-memory + its sq-<type> set) untouched, plus the scoped custom skill only on the linked role(s). sq check clean. Cross-backend: also verified with agents_md active — .agents_md/roles/manager.md picked up the scoped skill immediately, other roles' agents_md files untouched.
  - Guards: link-role to a nonexistent slug/ROLE-id/non-role target -> clear error, exit 1 in all three cases. Re-link/re-unlink are idempotent no-ops (exit 0, no duplication, no error on unlinking an already-unlinked role). Deleting a scoped role (--purge) leaves a dangling ref that sq check flags ('warn SKILL-19: dangling ref ROLE-8'), matching acceptance.
  - No defects found — no bug filed.
- [2026-07-20T10:22:19Z] Elias Python:
  - @manager F1 (REV-501) addressed with regression tests; see REV-501 comment for details. TASK-495 stays InReview.
<!-- sq:discussion:end -->
