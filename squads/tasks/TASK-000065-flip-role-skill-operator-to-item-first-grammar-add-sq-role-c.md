---
id: TASK-65
sequence_id: 65
type: task
title: Flip role/skill/operator to item-first grammar; add sq role catalog; remove
  the list subcommands
status: Done
parent: FEAT-64
author: tech-lead
assignee: python-dev
priority: high
subentities:
- local_id: ST1
  title: Item-first grammar for role/skill/operator show/regen/rm (slug|id|n, exact
    match)
  status: Done
  story: US1
- local_id: ST2
  title: Extend the resolver with exact slug lookup (full-id, then number, then slug)
  status: Done
  story: US1
- local_id: ST3
  title: Add sq role catalog; remove role/skill/operator list and --available (no
    shim)
  status: Done
  story: US3
- local_id: ST4
  title: Update grammar in claude_section / greeting / squads templates; regen artifacts
  status: Done
  story: US3
- local_id: ST5
  title: Rewrite CLI tests to item-first; add slug/id/n + catalog + removed-list coverage
  status: Done
  story: US1
- local_id: ST6
  title: Top up the FEAT-000013 deferral comment if the shipped grammar deviated from
    the PO note
  status: Done
  story: US3
created_at: '2026-06-12T12:05:15Z'
updated_at: '2026-07-06T15:19:00Z'
---
<!-- sq:body -->
Bring `sq role`, `sq skill`, and `sq operator` into the uniform item CLI grammar (FEAT-19 / the FEAT-13 contract). This task covers everything EXCEPT styled body rendering, which is TASK-66 — but both touch the same three CLI modules, so coordinate (one PR or stacked).

## What changes

### 1. Item-first addressing for the existing-item verbs

Flip from verb-first to item-first. Target grammar:

- `sq role <slug|id|n> show | regen | rm`
- `sq skill <slug|id|n> show | regen | rm`
- `sq operator <slug|id|n> show | rm`  (NEW `show`; `rm` flips)

Address forms accepted, EXACT match (no fuzzy):
- role: slug (primary), full ID (ROLE-1), bare number (1)
- skill: slug, full ID, bare number
- operator: slug (op-pierre), full ID, bare number

Creation verbs stay verb-first at the group level, UNCHANGED: `sq role activate <slug>`, `sq skill add <name>`, `sq operator add <name>`.

### 2. `sq role catalog`

New group-level subcommand showing the bundled catalog (slug, full name, title, default indicator) — exactly the table currently behind `sq role list --available` (rows from `PREDEFINED` in `_roles/_catalog.py`). Replaces `sq role list --available`.

### 3. Remove the list subcommands

Delete `sq role list`, `sq skill list`, `sq operator list` (and the `--available` flag). NO deprecation shim — pre-1.0 removal is explicitly allowed. Tracked-item listing remains via `sq list -t role|skill|operator`, which already works.

## Slug resolution — extend the resolver

The shared resolver `resolve_item_id_typed(token, item_type, svc)` in `_cli/_common.py` already handles bare number and full ID via `_parse_item_token`. It does NOT resolve slugs. Add a slug-aware wrapper (suggest `resolve_agent_addr(token, item_type, svc)` or extend the typed resolver with an optional slug lookup) that: tries the slug path first when the token is non-numeric and not a full ID, else falls through to `resolve_item_id_typed`. Slug lookup must be EXACT against the item's `extra[X.SLUG]` (fall back to `it.slug`), reusing the service helpers `_role_item` / `_skill_item` / `_operator_item` in `_services/_base.py` (they already match on `extra[X.SLUG]`). Surface a clear error naming the type when nothing matches. Keep it one DB read per call, mirroring the existing resolvers.

Note: a slug like `manager` is non-numeric so it can't collide with a bare number; a full ID is detected by the `TYPE-NNNNNN` shape in `_parse_item_token`. Resolution order: full-ID shape -> bare number -> slug.

## Typer wiring — the load-bearing decision

The item groups (`_cli/_items.py::build_item_app`) use a group `@callback` with a required `Argument N` that resolves into `ctx.obj`, and every subcommand is item-addressed. That trick does NOT transplant directly here, because role/skill/operator must ALSO expose group-level commands that take no address (`activate`, `add`, `catalog`). A callback with a required positional argument would swallow `catalog`/`add` as if they were an address.

Recommended approach: keep `activate`/`add`/`catalog` as ordinary named subcommands on the group, and put the item-addressed verbs under a nested address subgroup — i.e. the group callback inspects, but does not consume, the address; the cleanest Typer-clean form is a small address subgroup whose own callback takes the `<slug|id|n>` Argument and resolves into `ctx.obj`, with `show`/`regen`/`rm` as its subcommands. Validate the chosen shape produces the exact surface in Scope (`sq role manager show`, `sq role catalog`, `sq role activate qa` all parse unambiguously) before building it out. If the implementer finds a materially simpler Typer construction that yields the same surface and exact-match semantics, that is fine — record it in a comment. Do NOT open an ADR (Nina explicitly ruled it out unless we deviate from the target grammar).

## Generated docs / templates that teach the old grammar (MUST update)

These templates emit the old grammar into generated CLAUDE.md / skill bodies — update them as part of this task so generated artifacts match the new surface:
- `_rendering/templates/claude/claude_section.md.j2`: line ~29 `sq operator list` -> `sq list -t operator`; line ~43 `sq role show <slug>` -> `sq role <slug> show`.
- `_rendering/templates/agents/greeting_skill.md.j2`: `sq operator list` -> `sq list -t operator`.
- `_rendering/templates/agents/squads_skill.md.j2`: `sq operator list` -> `sq list -t operator`.
After editing templates, regenerate the managed artifacts the normal way (via the service refresh / `sq sync`); do NOT hand-edit the generated `.md` under `squads/`.

## Out of scope (this task)
- Styled body rendering in `show` — that is TASK-66.
- The `sq dev` group (developer roles) — separate creation surface, not named by the feature; leave it untouched. Call out in review if its `list` now looks inconsistent, but do not change it here.
- `--full`/`--comments` panes for show — follow-on, not in this feature.

## Tests (expect churn — call out in the PR)
Existing CLI tests use the old grammar and WILL break; update them:
- `tests/test_cli.py`: ~lines 795-866 — `role regen 1`, `role activate`, `role rm 3`, `role show manager/qa`, `skill show 2`, `skill regen 2`, `skill rm 2`, `operator rm 2`. Rewrite to item-first.
- `tests/test_operators.py`: ~line 113 `operator list` — replace with `sq list -t operator` (or drop, since coverage moves there).
- Add NEW coverage: slug / full-ID / bare-number resolution for show and rm on role and skill (US1 acceptance); `sq operator <addr> show` (new command); `sq role catalog` output; assert the removed `list` subcommands error.
- Generated-doc assertions: `tests/test_backend_claude.py` (~line 93/100 asserts `sq role show`) and `tests/test_skills.py` (~line 130 asserts `sq operator list`) check template OUTPUT — update the expected strings to the new grammar once templates change.

## Acceptance
- All three groups address existing items item-first with slug/id/number, exact match.
- `sq operator <addr> show` exists.
- `sq role catalog` shows the bundled catalog; `sq role list --available` is gone.
- `sq role list` / `sq skill list` / `sq operator list` are removed; `sq list -t <type>` still works.
- Creation verbs (`activate`/`add`) unchanged.
- pyright strict + ruff clean; full suite green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 65 add-subtask "<title>"`; track with `sq task 65 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Item-first grammar for role/skill/operator show/regen/rm (slug|id|n, exact match) | US1 |
| ST2 | Done |  | Extend the resolver with exact slug lookup (full-id, then number, then slug) | US1 |
| ST3 | Done |  | Add sq role catalog; remove role/skill/operator list and --available (no shim) | US3 |
| ST4 | Done |  | Update grammar in claude_section / greeting / squads templates; regen artifacts | US3 |
| ST5 | Done |  | Rewrite CLI tests to item-first; add slug/id/n + catalog + removed-list coverage | US1 |
| ST6 | Done |  | Top up the FEAT-13 deferral comment if the shipped grammar deviated from the PO note | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Item-first grammar for role/skill/operator show/regen/rm (slug|id|n, exact match)

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a CLI user, I want to address roles, skills, and operators with the same item-first grammar I use for every other type (sq role N show, sq skill N show, sq operator N show), so that one habit works everywhere without exceptions
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Flip sq role/skill/operator existing-item verbs (show/regen/rm, plus a new operator show) from verb-first to item-first grammar: sq role <slug|id|n> show|regen|rm etc., accepting slug / full ID / bare number with exact (non-fuzzy) match. Creation verbs (activate/add) stay verb-first at the group level (US1).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-06-12T12:14:14Z] Elias Python:
  - Probe confirms: the wiring shape that works is cls=AddressDispatchGroup on the Typer() call, where AddressDispatchGroup subclasses TyperGroup and overrides _click_resolve_command. Named commands (catalog/activate) dispatch normally; unknown tokens are routed to a hidden _addr subgroup with the original args list (address token + verb) passed intact. The _addr subgroup's callback consumes the address as ADDR and puts it in ctx.obj, then the named sub-verb (show/regen/rm) reads ctx.obj.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Extend the resolver with exact slug lookup (full-id, then number, then slug)

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a CLI user, I want to address roles, skills, and operators with the same item-first grammar I use for every other type (sq role N show, sq skill N show, sq operator N show), so that one habit works everywhere without exceptions
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Extend the shared resolver with an exact slug lookup: resolution order full-ID shape, then bare number, then slug, matching exactly against extra[X.SLUG] (fallback it.slug) via the _role_item/_skill_item/_operator_item service helpers in one DB read. Non-matching tokens raise a clear error naming the type (US1).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Add sq role catalog; remove role/skill/operator list and --available (no shim)

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a CLI user, I want a single list surface for tracked items (sq list -t role|skill|operator) and a dedicated catalog command for the bundled role catalog (sq role catalog), so that the command surface is clean and unambiguous
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Add the group-level sq role catalog subcommand (the bundled PREDEFINED table: slug/full name/title/default indicator) replacing sq role list --available, and remove sq role/skill/operator list plus the --available flag with no deprecation shim (pre-1.0 removal allowed). Tracked-item listing stays via sq list -t role|skill|operator (US3).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Update grammar in claude_section / greeting / squads templates; regen artifacts

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a CLI user, I want a single list surface for tracked items (sq list -t role|skill|operator) and a dedicated catalog command for the bundled role catalog (sq role catalog), so that the command surface is clean and unambiguous
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Update the templates that emit the old grammar into generated artifacts — claude_section.md.j2 (sq operator list -> sq list -t operator, sq role show <slug> -> sq role <slug> show), greeting_skill.md.j2 and squads_skill.md.j2 (sq operator list -> sq list -t operator) — then regenerate the managed .md via the service refresh / sq sync rather than hand-editing (US3).
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-06-12T12:25:57Z] Elias Python:
  - Templates updated: claude_section.md.j2 (sq operator list -> sq list -t operator; sq role show <slug> -> sq role <slug> show), greeting_skill.md.j2 (sq operator list -> sq list -t operator), squads_skill.md.j2 (sq operator list -> sq list -t operator). sq sync run — CLAUDE.md, greeting.md, squads.md all regenerated with new grammar.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Rewrite CLI tests to item-first; add slug/id/n + catalog + removed-list coverage

<!-- sq:subtask:ST5:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a CLI user, I want to address roles, skills, and operators with the same item-first grammar I use for every other type (sq role N show, sq skill N show, sq operator N show), so that one habit works everywhere without exceptions
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
Rewrite the existing CLI tests that used the old verb-first grammar (test_cli.py role/skill/operator cases, test_operators.py operator list) to item-first, and add new coverage: slug/full-ID/bare-number resolution for role and skill show/rm, the new sq operator <addr> show, sq role catalog output, generated-doc assertions to the new grammar, and asserting the removed list subcommands error (US1).
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-06-12T12:26:06Z] Elias Python:
  - Tests rewritten to item-first grammar. test_role_regen_rm_bare_number -> test_role_item_first_grammar (covers slug/id/number for show/regen/rm). test_role_show_includes_body_and_degrades_for_bundled updated to use item-first grammar. Added test_role_catalog, test_role_list_removed. test_skill_show_regen_rm_bare_number -> test_skill_item_first_grammar (slug/id/number). Added test_skill_list_removed. test_operator_rm_bare_number -> test_operator_item_first_grammar (show/rm with slug/id). Added test_operator_list_removed. test_operators.py: sq operator list -> sq list -t operator + operator show verification. test_backend_claude.py: sq role show -> sq role <slug> show assertion. test_skills.py: sq operator list -> sq list -t operator assertion.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Top up the FEAT-13 deferral comment if the shipped grammar deviated from the PO note

<!-- sq:subtask:ST6:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a CLI user, I want a single list surface for tracked items (sq list -t role|skill|operator) and a dedicated catalog command for the bundled role catalog (sq role catalog), so that the command surface is clean and unambiguous
<!-- sq:subtask:ST6:head:end -->

<!-- sq:subtask:ST6:body -->
Reconcile the FEAT-000013 deferral comment: if the shipped Typer construction / grammar deviated from the PO note, top up that deferral record so the contract reflects what actually shipped (US3).
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-06-12T12:26:22Z] Elias Python:
  - Shipped grammar matches Nina's deferral note on FEAT-13 (2026-06-12) verbatim. All five decisions (item-first, verb-first creation, sq role catalog, list removal without shim, slug resolution) are satisfied by this implementation. No top-up needed.
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
