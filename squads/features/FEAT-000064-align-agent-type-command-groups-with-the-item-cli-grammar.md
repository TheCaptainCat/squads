---
id: FEAT-64
sequence_id: 64
type: feature
title: Align agent-type command groups with the item CLI grammar
status: Done
parent: EPIC-12
author: product-owner
priority: high
refs:
- FEAT-19
- FEAT-26
- FEAT-13
description: 'Bring role/skill/operator command groups in line with the item grammar:
  item-first addressing, styled body rendering, and a single list surface'
subentities:
- local_id: US1
  title: Item-first grammar for roles, skills, and operators
  status: Done
- local_id: US2
  title: Role and skill bodies rendered as styled markdown like any item show
  status: Done
- local_id: US3
  title: Single list surface for tracked agents; sq role catalog for bundled ones
  status: Done
- local_id: US4
  title: Grammar decisions recorded as deferral obligation on FEAT-000013
  status: Done
created_at: '2026-06-12T11:56:22Z'
updated_at: '2026-06-23T10:01:25Z'
---
<!-- sq:body -->
## Problem

Three command groups — `sq role`, `sq skill`, `sq operator` — predate the uniform item CLI grammar
and have never been brought into line with it.

**Grammar inversion.** Every other item type is addressed as `sq <type> <n> <verb>` (e.g.
`sq feature 26 show`). Roles, skills, and operators invert this: verb comes first, identifier
second (`sq role show manager`, `sq skill show squads`). FEAT-19 established uniform addressing
(full ID or bare number accepted everywhere) for all commands — the agent-type groups escaped it
entirely, not because there is a principled reason, but because they predate the decision.
Roles/skills/operators are tracked items with sequence IDs (ROLE-1..., SKIL-000001...,
OPER-000001...); the inversion is a historical accident, not a design choice.

**Plain body rendering.** `sq role show` prints the item body plain:
`src/squads/_cli/_role.py:76` — `console.print(e(body))` — raw markdown characters, no color, no
panels. FEAT-26 introduced styled markdown rendering for all item types (`sq <type> <n> show`
renders headings, bullets, code, panes, `--raw` for opt-out, plain when piped). Role (and skill)
show commands were written before FEAT-26 landed and were never updated to use the renderer
it built.

**Redundant list commands.** `sq role list`, `sq skill list`, and `sq operator list` duplicate
`sq list -t role`, `sq list -t skill`, `sq list -t operator`. The only view these commands carry
that `sq list` cannot replicate is `sq role list --available`, which shows the bundled role catalog
(agents that exist in code but have no tracked item yet) — a distinct surface that has nothing to
do with listing tracked items.

## Value

One grammar, no exceptions. The stability contract (FEAT-13) documents the CLI grammar as
SemVer-stable from 1.0; that means every command surface must be deliberately chosen before the
freeze. Fixing these three groups now costs one feature's work; fixing them post-1.0 would be a
breaking change. Alignment means operators and agents can apply the same habit (`sq <type> <n>
<verb>`) to roles, skills, and operators as to every other item type, and styled rendering makes
role/skill bodies as readable as any other item. The redundant list commands are clutter against a
surface that must be stable — removing them pre-1.0 is free; removing them post-1.0 is a break.

## Scope

### 1. Item-first grammar for `show`, `regen`, and `rm`

The subcommands that address an *existing* item flip to item-first:

```
sq role <slug|id|n> show     (was: sq role show <slug>)
sq role <slug|id|n> regen    (was: sq role regen <id>)
sq role <slug|id|n> rm       (was: sq role rm <id>)

sq skill <slug|id|n> show    (was: sq skill show <id>)
sq skill <slug|id|n> regen   (was: sq skill regen <id>)
sq skill <slug|id|n> rm      (was: sq skill rm <id>)

sq operator <slug|id|n> show (new — operator had no show command)
sq operator <slug|id|n> rm   (was: sq operator rm <id>)
```

The primary address form: for roles, the slug is the natural identifier (analogous to using a title
slug); full ID (`ROLE-000001`) and bare sequence number (`1`) must also be accepted per
FEAT-19's spirit. The shared resolver from FEAT-19 already handles ID and number; the
implementation must extend or wrap it to also resolve by slug where the type carries one.

`activate` (role-only) and `add` (skill, operator) are **group-level creation commands** — they
receive a catalog slug or a new name, not an existing item ID. These stay verb-first at the group
level: `sq role activate <slug>`, `sq skill add <name>`, `sq operator add <name>`. No change there.

### 2. Styled body rendering in `show`

`sq role <n> show` and `sq skill <n> show` must render the item body with the same styled markdown
renderer introduced in FEAT-26 — headed panes, inline markdown (headings, bullets, code),
`--raw` to opt out, and plain/unstyled output when stdout is piped or `NO_COLOR` is set. Behavior
must match what `sq feature <n> show` produces for the body facet.

### 3. Catalog home: `sq role catalog`

The `--available` flag on `sq role list` is the only non-redundant view in the three list commands.
It shows the bundled catalog (slugs, full names, titles, defaults) — a list of code-defined roles
that have not been activated as tracked items. This view does not belong on a `list` subcommand
because it does not list tracked items.

New home: a dedicated `sq role catalog` subcommand. `sq role catalog` replaces `sq role list
--available`; it is a group-level command (no item address), consistent with `activate` staying
group-level.

### 4. Removal of the standalone list commands

`sq role list`, `sq skill list`, and `sq operator list` are removed. Their tracked-item listing is
already available via `sq list -t role`, `sq list -t skill`, `sq list -t operator`.

**Backward-compat stance:** this feature lands before 1.0. Pre-1.0 removal without a deprecation
shim is explicitly allowed — the stability contract has not been promised yet, and the whole point
of the contract is that post-1.0 surfaces stay fixed. No alias or deprecation shim is required.
Agents and operators who relied on the list subcommands should use `sq list -t <type>` instead.

### 5. `sq operator show`

The `operator` group currently has no `show` command at all. As part of grammar alignment, add
`sq operator <slug|id|n> show` — same styled panel + body rendering as role and skill.

### Out of scope

- `--full` / `--comments` flags on role/skill/operator show: bring the body into the FEAT-26
  renderer; the full flag matrix (sub-entities, discussion panes) is a follow-on if there is demand.
- Themes, palette configuration.
- Any change to `activate`, `add`, or the catalog data itself.

## Acceptance

- `sq role <slug|id|n> show` works with slug, full ID, and bare number; `sq role show <slug>`
  fails or is removed.
- `sq skill <slug|id|n> show` and `sq operator <slug|id|n> show` work with ID and bare number.
- `sq role <n> show` and `sq skill <n> show` render the body as styled markdown on a TTY;
  `--raw` prints the raw text; piped output is plain.
- `sq role catalog` lists the bundled catalog (the view formerly at `sq role list --available`).
- `sq role list`, `sq skill list`, and `sq operator list` are removed; `sq list -t role` (etc.)
  continues to work.
- `sq role <n> regen` and `sq role <n> rm` work with ID and bare number (was: verb-first only).
- Existing tests pass or are updated to use the new grammar; new tests cover the item-first
  invocations and the styled-vs-raw rendering toggle.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 64 add-story "As a <role>, I want … so that …"`; track with `sq feature 64 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Item-first grammar for roles, skills, and operators |
| US2 | Done |  | Role and skill bodies rendered as styled markdown like any item show |
| US3 | Done |  | Single list surface for tracked agents; sq role catalog for bundled ones |
| US4 | Done |  | Grammar decisions recorded as deferral obligation on FEAT-13 |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Item-first grammar for roles, skills, and operators

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a CLI user, I want to address roles, skills, and operators with the same item-first grammar I use for every other type (sq role N show, sq skill N show, sq operator N show), so that one habit works everywhere without exceptions.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
- [2026-06-12T12:07:19Z] Olivia Lead:
  - Carried by TASK-65 (ST1, ST2, ST5). Exact slug match only — no fuzzy (op-pierre confirmed). Resolution order: full-ID shape, then bare number, then exact slug against extra[X.SLUG] (fallback it.slug). Reuse _role_item/_skill_item/_operator_item in _services/_base.py for the slug lookup.
- [2026-06-12T12:46:35Z] Paul Reviewer:
  - US1 (item-first addressing): PASS on the positive surface. Verified slug/bare-number/full-ID for show/regen/rm on role and skill, and show/rm on operator (incl. operator slug op-<first>); exact match only, no fuzzy. Wrong-type tokens error cleanly. The acceptance line 'verb-first invocations no longer exist or error clearly' is only half-met: they no longer exist (good) but do NOT error clearly — 'sq role show manager' becomes addr='show' verb='manager' -> 'No such command manager' under a leaked 'sq role _addr' usage. Tracked in the REV as part of the negative-path UX fix.
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Role and skill bodies rendered as styled markdown like any item show

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a CLI user reading a role or skill definition, I want the body rendered as styled markdown (headings, bullets, code blocks, panes) just like any other item show, so that role bodies are as readable as feature bodies.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
- [2026-06-12T12:07:20Z] Olivia Lead:
  - Carried by TASK-66. Match sq feature <n> show's body facet exactly: styled Markdown on TTY, --raw opt-out, plain/byte-stable when piped or NO_COLOR. Panel/card unchanged. Preserve role's catalog card and the activate-hint fallback for bundled-only roles.
- [2026-06-12T12:46:35Z] Paul Reviewer:
  - US2 (styled body): PASS. role/skill/operator show render styled Markdown on a TTY, --raw prints plain, piped/NO_COLOR is plain and byte-stable (verified byte-identical to --raw). Panel/card unchanged; role catalog card + bundled-only activation hint preserved. print_item guard removal is sound — ROLE/SKILL/OPERATOR flow through _print_item_content with the sub-entity branch a clean no-op, and sq show ROLE-N now renders the body consistently. 10 new rendering tests are well-structured. Minor: no test asserts the REV-61 bracket/no-backslash fidelity on the new role/skill body path, though it's structurally inherited from the shared _render_body (markup=False) so the risk is low.
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Single list surface for tracked agents; sq role catalog for bundled ones

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a CLI user, I want a single list surface for tracked items (sq list -t role|skill|operator) and a dedicated catalog command for the bundled role catalog (sq role catalog), so that the command surface is clean and unambiguous.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
- [2026-06-12T12:07:20Z] Olivia Lead:
  - Carried by TASK-65 (ST3, ST4). sq role catalog replaces sq role list --available (rows from PREDEFINED). Remove all three list subcommands with no shim. sq dev group is out of scope — leave its list alone, just flag in review if it now looks inconsistent.
- [2026-06-12T12:46:35Z] Paul Reviewer:
  - US3 (single list surface + catalog): catalog and removal are functionally done — 'sq role catalog' shows the bundled catalog, 'sq list -t role|skill|operator' works, the three list subcommands and --available are gone. BUT acceptance says they should error 'comprehensibly' and they don't: 'sq role list' -> 'sq role _addr / Missing command', 'sq role list --available' -> 'No such option: --available', neither pointing at 'sq list -t role' as the feature body promises. This is the core of the REV. (sq dev group left untouched per scope; its list now reads inconsistently against the three flipped groups — flagging as the lead asked, not changing it here.)
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Grammar decisions recorded as deferral obligation on FEAT-13

<!-- sq:story:US4:head -->
**Status:** 🟢 Done
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As the stability contract author, I want this feature's grammar decisions recorded as a deferral obligation on FEAT-13 before it closes, so that the contract document reflects the final CLI surface accurately.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
- [2026-06-12T12:07:21Z] Olivia Lead:
  - Already satisfied by Nina's deferral comment on FEAT-13 (2026-06-12) — it records all five grammar decisions. Tracked as ST6 on TASK-65: only top it up if the shipped grammar deviates from that note. No new comment needed if implementation matches.
- [2026-06-12T12:46:36Z] Paul Reviewer:
  - US4 (FEAT-13 deferral): PASS, no drift. Shipped positive surface (item-first slug|id|n, verb-first creation, sq role catalog, list removal without shim, slug resolution) matches Nina's 2026-06-12 deferral note verbatim, so ST6's top-up correctly did not fire. The AddressDispatchGroup-vs-nested-subgroup choice is internal wiring, not contracted surface — no contract drift on what FEAT-13 records. Caveat: the negative-path error UX (separate REV) is arguably part of the 'final CLI surface' an operator experiences; if the team wants the migration hint in the contract, note it there — but it does not invalidate US4 as written.
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T11:57:56Z] Pierre Chat:
  - Three things I noticed in today's session that bother me before we freeze the grammar.
  - First, role commands don't follow the pattern. Every other type is 'sq feature 26 show' — you name the item first and the verb second. With roles it's backwards: 'sq role show manager'. Roles and skills and operators are tracked items with IDs, so there's no reason they should be different.
  - Second, when I run 'sq role show' the body prints completely plain — raw markdown characters. Feature bodies render nicely now (thanks to the work in FEAT-26). Role bodies look like they didn't get the update.
  - Third, 'sq role list' is pointless next to 'sq list -t role'. Same for skill and operator. The only thing list gives me that the other surface doesn't is 'sq role list --available', which shows the bundled catalog — and that view should have a better home anyway.
- [2026-06-12T11:58:11Z] Nina Product:
  - Authoring rationale.
  - Priority set to high (not medium) because this is a grammar question, and FEAT-13 documents the CLI grammar as SemVer-stable from 1.0. Every surface that isn't deliberately settled before tagging becomes an accidental promise we can never fix cheaply. That's the same reasoning that made FEAT-19 high — addressing rules are a grammar question, and so is command ordering.
  - Target grammar: 'sq role <slug|id|n> show' — item-first, consistent with every other type. Slug is the natural primary address for roles (analogous to how numbers are for tasks), but full ID and bare number must also work per FEAT-19's spirit. The shared resolver from FEAT-19 will need extending or wrapping to cover slug resolution.
  - Creation commands stay verb-first: 'sq role activate <slug>', 'sq skill add <name>', 'sq operator add <name>'. These don't address an existing item — they receive a catalog slug or a new name. Flipping them would be odd and serves no user.
  - Catalog home: 'sq role catalog' as a group-level subcommand. The '--available' view is conceptually distinct from listing tracked items; giving it its own command name makes that distinction legible.
  - ADR call: I am not calling for an ADR here. The grammar change is a straightforward alignment with a rule that already exists (FEAT-19, now FEAT-13's contract). An ADR is warranted when there is genuine design ambiguity or a novel tradeoff to record. Flipping verb order to match the established pattern is a correction, not a new decision — the tech lead can implement it directly. If during implementation the team finds a reason to deviate from the target grammar specified in this feature's body, that is the moment to raise it.
  - Backward-compat stance: removal without a deprecation shim is explicitly allowed pre-1.0. The body says so. If the tech lead wants to add a short deprecation message as a courtesy (pointing to 'sq list -t role'), that is fine but not required.
- [2026-06-12T12:07:09Z] Olivia Lead:
  - Broke this down into two stacked tasks. @python-dev — start with TASK-65 (grammar + catalog + list removal), then TASK-66 (styled body rendering); both touch the same three CLI modules (_role.py / _skill.py / _operator.py) plus _common.py, so do them as one PR or a clean stack, 65 first.
  - TASK-65 covers US1 (item-first slug|id|n addressing, exact match) and US3 (sq role catalog, removal of the three list subcommands + --available, no shim). Includes the resolver extension (exact slug lookup layered on the FEAT-19 number/id resolver) and the template updates that teach the old grammar (claude_section / greeting / squads skill).
  - TASK-66 covers US2: route role/skill/operator show bodies through the FEAT-26 styled path. The seam is print_item in _common.py — it currently guards out ROLE/SKILL bodies (line ~278); relaxing that guard is the preferred fix. Watch for regressions across feature/task/review show.
  - Typer wiring is the load-bearing call: the item-group callback trick (required Argument N) does NOT transplant cleanly because these groups need group-level verbs (activate/add/catalog) alongside item-addressed verbs. Recommended shape: keep activate/add/catalog as named subcommands and put show/regen/rm under a nested address subgroup whose callback consumes the <slug|id|n> argument. Details and fallbacks are in the task body. No ADR (Nina ruled it out unless we deviate from the target grammar — if you do, raise it).
  - Test churn: ~6 CLI tests in test_cli.py (lines ~795-866) and 1 in test_operators.py use the old grammar and must be rewritten; test_backend_claude.py and test_skills.py assert generated-doc strings that change with the templates. Add new coverage for slug/id/number resolution, operator show, role catalog, and the removed list commands erroring.
  - US4 (FEAT-13 deferral) is already satisfied — Nina's 2026-06-12 deferral comment on FEAT-13 records all five decisions verbatim. ST6 on TASK-65 only fires if the shipped grammar deviates from that note; if it matches, leave it untouched.
- [2026-06-12T12:26:56Z] Elias Python:
  - TASK-65 delivered. Item-first grammar for sq role/skill/operator is now live with all six subtasks green, full suite (344 tests) passing, pyright strict and ruff clean.
  - Wiring shape: AddressDispatchGroup (TyperGroup subclass, cls= parameter) overrides _click_resolve_command — named subcommands dispatch normally; unknown tokens route to a hidden _addr subgroup that receives the full args list so its callback can consume the address token. The nested address subgroup carries show/regen/rm. This is the probe-confirmed shape; it handles sq role catalog, sq role activate qa, sq role manager show, sq role 1 show, sq role ROLE-1 show cleanly.
  - What's in this task: AddressDispatchGroup + resolve_agent_addr in _common.py; _role.py, _skill.py, _operator.py fully rewritten to item-first grammar; sq role catalog added; sq role/skill/operator list removed (no shim); template updates (claude_section, greeting_skill, squads_skill) + sq sync run; tests updated and new coverage added.
  - Special case for bundled-only roles: sq role qa show works even if qa is not activated — the _addr callback uses soft resolution for slug tokens (stores None on failure) so show() can render the bundled catalog card with an activation hint. Numeric/ID-shaped tokens remain strict (type mismatch errors bubble up).
  - For TASK-66 dev: the seam for styled body rendering is print_item in _common.py (line ~278 guards out ROLE and SKILL types). The role show command currently calls svc.role_body(slug) and prints plain; TASK-66 should route through print_item instead. Also note operator show currently has no body rendering (empty no-op as agreed). The _addr subgroup pattern in each CLI module is the hook point for adding --raw/--comments flags to show.
- [2026-06-12T12:38:31Z] Elias Python:
  - TASK-65 and TASK-66 are both done. FEAT-64 is ready for review.
  - TASK-65 (grammar flip): AddressDispatchGroup dispatches role/skill/operator show/regen/rm through the item-first address subgroup. sq role catalog added; sq role/skill/operator list removed. Templates updated and sq sync run. 344 tests green at handoff.
  - TASK-66 (styled body rendering): render_body_text() helper added to _common.py. Relaxed print_item guard (ROLE/SKILL/OPERATOR now flow through _print_item_content — sub-entity branches no-op cleanly). show_role, skill_show, operator_show each call render_body_text(body, raw=raw) after their custom panel. --raw flag added to all three show commands. 354 tests green, pyright strict clean, ruff clean.
  - Design decision: factored _render_body (pre-computed styled flag) and render_body_text (computes styled = _is_styled() and not raw) rather than reusing print_item. This keeps role catalog card and operator panel independent from the generic item panel that print_item builds. The guard in print_item is now gone (ROLE/SKILL/OPERATOR go through _print_item_content) so sq show ROLE-N also renders the body styled — consistent with the three show commands.
  - --comments not wired on role/skill/operator show. The feature scope was styled body + --raw; role items DO have discussions but wiring --comments would require a fuller print_item adoption (with its generic panel replacing the catalog card). Left as a follow-on. All four US stories are Done. @reviewer — please review.
- [2026-06-12T12:46:16Z] Paul Reviewer:
  - Review verdict: CHANGES REQUESTED. Core grammar flip, slug/id/number resolution, styled body rendering, catalog command, and list removal are all correctly implemented and the contracted positive surface matches Nina's deferral note exactly (US1/US2/US3 functionally delivered). All gates green on my machine: pytest (354), pyright strict, ruff check+format, sq check (no issues), sq sync idempotent. But the error/negative-path UX fails the 'error comprehensibly' acceptance bar and leaks the internal _addr subgroup — see REV (opened, @python-dev) for the blocking item.
  - What I verified live in a throwaway squad: slug/number/full-ID resolution for show/regen/rm on role/skill/operator; wrong-type number and wrong-type full-ID give clean 'N is X (type), not a role/skill' errors (exit 1, no traceback); piped output is plain and byte-identical to --raw; sq show ROLE-N now renders the body via the generic item panel with the sub-entity branch a clean no-op (consistent, no regression on feature/task show); regenerated CLAUDE.md + greeting/squads skills are swept clean of old grammar and teach the new forms.
  - Blocking concern (negative-path UX): AddressDispatchGroup routes EVERY unknown token to the hidden _addr subgroup, so removed/typo'd/old-grammar invocations surface a baffling error. 'sq role list' -> 'Usage: sq role _addr [OPTIONS] ADDR COMMAND...' / 'Missing command.' — it neither says 'list' was removed nor points at 'sq list -t role' (the feature body promises that migration hint). 'sq role lst' (typo) and 'sq role manager' (valid addr, no verb) -> same '_addr / Missing command'. 'sq role shw manager' -> 'No such command manager'. The internal _addr name leaks into the usage line everywhere, and 'sq role'/'sq role --help' never lists show/regen/rm at all (discoverability gap — the primary verbs are invisible; they only appear if you happen to pass a valid address before --help, and even then the usage line wrongly reads 'sq role _addr ... ADDR COMMAND'). The test_*_list_removed tests only assert exit_code != 0, so they pass without catching any of this.
  - Non-blocking observations recorded for the team: (1) slug-shadowing — a skill/role/operator slugged exactly like a group verb ('add'/'catalog'/'activate') is unaddressable by slug (named verb always wins in _click_resolve_command); number/full-ID still works as the escape hatch (verified), but the shadowing is silent and undocumented. (2) resolve_agent_addr re-implements the slug loop inline with extra.get(X.SLUG, it.slug) for all three types rather than reusing _role_item/_skill_item/_operator_item as the lead directed — it's a superset (roles/operators always carry a SLUG extra so no behavior change today) but slug-matching semantics now live in two places that can drift. (3) the empty-body path prints '(empty — set it with body)' but there is no 'body' verb on role/skill/operator groups — latent inaccurate hint (bodies are template-managed, so rarely hit). (4) _addr callback re-implements full-ID-shape detection inline instead of calling the new _is_full_id_shape helper; test_cli.py has a stale '# SKIL-000002' comment (prefix is SKILL).
- [2026-06-12T13:01:14Z] Pierre Chat:
  - Scope correction on the removal stance: before 1.0 we owe nothing to the previous CLI interface. No tombstones, no migration hints for removed commands — 'sq role list' should fail like any unknown token, with the normal clean unknown-address error. The feature body's promised removal hint is withdrawn; the contract is only the NEW surface.
- [2026-06-12T13:10:46Z] Paul Reviewer:
  - REV-67 APPROVED. The negative-path error UX is resolved across all three blocking findings, re-reviewed after the two fix rounds and op-pierre's 2026-06-12 criterion change. F1: removed-list invocations now produce a clean traceback-free exit-1 error through the normal unknown-address path (tombstone/migration-hint machinery added then removed per that decision); no _addr leak, no tombstone text. F2: the internal _addr name no longer appears in any user-facing usage/error line. F3: sq role/skill/operator --help epilogs teach the full address grammar so show/regen/rm are discoverable. Non-blocking N2-N6 fixes are intact.
  - All gates green on a clean checkout: pytest 355 passed/1 skipped, pyright strict 0 errors, ruff check+format clean, sq check no issues. With US1-US4 Done and this review approved, the feature is functionally complete from a review standpoint. One non-blocking loose end recorded on the REV: _main.py:84 'sq init' banner still advertises the removed 'sq role list' — cosmetic, out of REV scope. Feature close is the manager's call.
- [2026-06-12T13:12:14Z] Catherine Manager:
  - Closing the loop: TASK-65/066 Done, REV-67 Approved after two fix rounds (negative-path UX, then the op-pierre pre-1.0 criterion change removing the tombstone). Also swept the stale 'sq role list' from the init banner (_main.py, now 'sq role catalog') flagged in the re-review. Feature complete, uncommitted pending op-pierre's commit call.
<!-- sq:discussion:end -->
