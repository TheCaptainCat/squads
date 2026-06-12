---
id: REV-000067
sequence_id: 67
type: review
title: 'FEAT-000064: negative-path error UX leaks the internal _addr subgroup and
  fails ''error comprehensibly'''
status: Approved
parent: FEAT-000064
author: reviewer
priority: high
refs:
- TASK-000065
description: AddressDispatchGroup routes every unknown token to the hidden _addr subgroup;
  removed/typo'd/old-grammar invocations produce baffling errors that leak _addr and
  omit the documented migration hint.
subentities:
- local_id: F1
  title: Removed list commands do not error comprehensibly (US3 acceptance)
  status: Verified
  severity: high
- local_id: F2
  title: The hidden _addr name leaks into every negative-path usage/error line
  status: Verified
  severity: high
- local_id: F3
  title: show/regen/rm are undiscoverable from sq role / --help (US1 spirit)
  status: Verified
  severity: medium
- local_id: F4
  title: 'N1 slug shadowing: slug matching a group verb is unaddressable by slug'
  status: Verified
  severity: low
- local_id: F5
  title: 'N2 resolver duplication: resolve_agent_addr iterates db.items inline instead
    of reusing item helpers'
  status: Verified
  severity: low
- local_id: F6
  title: 'N3 empty-body hint inaccurate: suggests a ''body'' verb the groups do not
    have'
  status: Verified
  severity: low
- local_id: F7
  title: 'N4 inline shape check: _resolve_addr reimplements full-ID detection instead
    of _is_full_id_shape'
  status: Verified
  severity: low
- local_id: F8
  title: 'N5 stale comment: SKIL-000002 should be SKILL-000002 in test_skill_item_first_grammar'
  status: Verified
  severity: low
- local_id: F9
  title: 'N6 test coverage: no direct test for REV-000061 bracket/no-backslash fidelity
    on the new body path'
  status: Verified
  severity: low
- local_id: F10
  title: 'N7 sq dev consistency: still uses the old listing shape, reads inconsistently
    against the flipped groups'
  status: WontFix
  severity: low
created_at: '2026-06-12T12:46:41Z'
updated_at: '2026-06-12T13:18:41Z'
---
<!-- sq:body -->
## Scope

Negative-path error UX of FEAT-000064 / TASK-000065. The positive surface (grammar flip + styled rendering) was reviewed on the feature and is correct. AddressDispatchGroup._click_resolve_command (src/squads/_cli/_common.py) routes every token that is not a named group command to the hidden address subgroup with the full args -- that is what makes the positive grammar work, but it also swallowed every wrong input into a confusing error. This review covers the resulting blocking UX defects (F1-F3) and the non-blocking observations (F4-F10, originally N1-N7).

## Verdict history

- **ChangesRequested** -- three blockers raised: removed list commands did not error comprehensibly (F1), the internal address-subgroup name leaked into every negative-path usage/error line (F2), and show/regen/rm were undiscoverable from the group help (F3). Seven non-blocking observations recorded.
- **Fix round 1** -- F1-F3 addressed (F1 with a tombstone/migration-hint approach at the time); non-blocking N1-N6 taken, N7 skipped as out of scope.
- **Criterion change (op-pierre, 2026-06-12)** -- before 1.0 we owe nothing to the previous CLI: no tombstones, no migration hints for removed commands; F1's bar becomes only a clean, traceback-free error through the normal unknown-address path. F2/F3 stand as written.
- **Fix round 2** -- tombstone machinery removed; removed-command invocations now fall through the normal address path to a clean exit-1 missing-verb error.
- **Approved** -- all blockers resolved against the final criteria; non-blocking fixes verified; all gates green (355 tests pass / 1 pre-existing skip, pyright strict clean, ruff clean, sq check clean).

## Acceptance status

- US1 addressing -- PASS (verb-first errors now clear; F2/F3 closed).
- US2 styled body -- PASS.
- US3 catalog + list removal -- PASS (removed verbs error cleanly through the normal path per the revised criterion).
- US4 deferral -- PASS, no contract drift.

## Findings

Per-finding detail -- file:line, repro, the fix that landed, and history -- lives in the findings on this review (F1-F3 blockers, F4-F10 the N1-N7 observations). See the finding panes for status and rationale.

## Out-of-scope follow-up

src/squads/_cli/_main.py:84 -- the `sq init` Next-steps banner still advertises `sq role list`, a command US3 removed. Cosmetic, does not block this approval; flagged for the dev's call as a cleanup or a tiny follow-up task.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 67 add-finding "…" --severity high`; track with `sq review 67 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Verified |  | Removed list commands do not error comprehensibly (US3 acceptance) |
| F2 | 🟠 high | Verified |  | The hidden _addr name leaks into every negative-path usage/error line |
| F3 | 🟡 medium | Verified |  | show/regen/rm are undiscoverable from sq role / --help (US1 spirit) |
| F4 | 🟢 low | Verified |  | N1 slug shadowing: slug matching a group verb is unaddressable by slug |
| F5 | 🟢 low | Verified |  | N2 resolver duplication: resolve_agent_addr iterates db.items inline instead of reusing item helpers |
| F6 | 🟢 low | Verified |  | N3 empty-body hint inaccurate: suggests a 'body' verb the groups do not have |
| F7 | 🟢 low | Verified |  | N4 inline shape check: _resolve_addr reimplements full-ID detection instead of _is_full_id_shape |
| F8 | 🟢 low | Verified |  | N5 stale comment: SKIL-000002 should be SKILL-000002 in test_skill_item_first_grammar |
| F9 | 🟢 low | Verified |  | N6 test coverage: no direct test for REV-000061 bracket/no-backslash fidelity on the new body path |
| F10 | 🟢 low | WontFix |  | N7 sq dev consistency: still uses the old listing shape, reads inconsistently against the flipped groups |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Removed list commands do not error comprehensibly (US3 acceptance)

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
US3 acceptance: removed list commands must "error comprehensibly". Affected: src/squads/_cli/_role.py, _skill.py, _operator.py (all via AddressDispatchGroup).

Original symptoms:
- `sq role list` -> `Usage: sq role _addr [OPTIONS] ADDR COMMAND [ARGS]...` then `Missing command.` (exit 2). `list` was taken as an address slug; the message never said the command was removed.
- `sq role list --available` -> `No such option: --available` under the same `_addr` usage.
- tests/test_cli.py::test_role_list_removed / test_skill_list_removed / test_operator_list_removed asserted only exit_code != 0, so they passed while the message was unhelpful.

Resolution (after op-pierre criterion change, see finding comment): the bar for F1 became a clean, traceback-free error through the normal unknown-address path -- no tombstones, no migration hints (pre-1.0 we owe nothing to the previous CLI). `sq role/skill/operator list` now fall through the normal address path: `list` is taken as an address token, the missing-verb check fires, exit 1 with `missing verb after address list. Usage: sq <type> slug|id|n show|regen|rm`. No `_addr`, no tombstone text, no traceback. `list --available` behaves identically (--available is an option, so no non-option verb follows). The three test_*_list_removed tests now assert exit_code==1, `list` in output, `_addr` absent, `Traceback` absent.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-06-12T13:18:12Z] Paul Reviewer:
  - History: first fix round added a tombstone -- a _REMOVED_VERBS ClassVar on AddressDispatchGroup, per-module dispatch subclasses, and a removed-command message pointing at sq list -t <type>. Then op-pierre changed the criterion on 2026-06-12: before 1.0 we owe nothing to the previous CLI -- no tombstones, no migration hints; the bar is only a clean, traceback-free error through the normal unknown-address path. The tombstone machinery was removed (the _RoleDispatchGroup/_SkillDispatchGroup subclasses collapsed back to cls=AddressDispatchGroup; _OperatorDispatchGroup kept only for _ADDR_VERBS=show|rm). Verified against the revised criterion.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — The hidden _addr name leaks into every negative-path usage/error line

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
The internal `_addr` subgroup name is a construct that should never appear in user-facing output, but any malformed invocation printed `Usage: sq role _addr [OPTIONS] ADDR COMMAND ...`.

Original examples:
- `sq role lst` (typo) -> `_addr` usage + `Missing command.`
- `sq role manager` (valid address, no verb) -> `_addr` usage + `Missing command.`
- `sq role shw manager` -> addr=`shw`, verb=`manager` -> `No such command manager`-style under `_addr` usage.
- `sq role manager --help` -> help listed show/regen/rm correctly but the usage line read `sq role _addr [OPTIONS] ADDR COMMAND` with a spurious `ADDR` argument the user already supplied.

Resolution (verified): two-part fix in _common.py (see finding comment). (1) Missing-verb interception: when _click_resolve_command routes to _addr and no non-option arg follows the address token (and --help absent), it exits 1 with `missing verb after address <token>. Usage: sq role <slug|id|n> show|regen|rm` -- no _addr leak, no Click `Missing command.` (2) Display name: the resolve tuple now uses `<slug|id|n>` as the command name instead of `_addr`. Probed sq role lst, sq role manager (no verb), sq role shw manager, sq role manager --help, sq role manager regen --help: `_addr` appears in NO user-facing output. Note: the usage line still carries a redundant ADDR positional from the address-subgroup wiring -- that is the secondary "spurious ADDR" remark, not the _addr leak that blocked; the core bar is met.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-06-12T13:18:12Z] Paul Reviewer:
  - Resolution detail: the usage display-name rewrite was the key move -- _click_resolve_command now returns `<slug|id|n>` as the command name instead of the internal `_addr`, so no negative-path usage/error line leaks the construct. Paired with the missing-verb interception (exit 1 clean error before Click can emit `Missing command.`). Probed across lst/no-verb/wrong-verb/--help cases; _addr absent everywhere. Residual: the usage line still shows a redundant ADDR positional from the subgroup wiring -- noted as non-blocking, not the leak that gated.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — show/regen/rm are undiscoverable from sq role / --help (US1 spirit)

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
US1 spirit (discoverability): `sq role` and `sq role --help` listed only `catalog` and `activate` because the `_addr` subgroup is `hidden=True`. The primary item verbs (show/regen/rm) appeared nowhere in the group help. A user had no documented way to learn the grammar from --help; they only saw the verbs by guessing a valid address first (and then the usage line was wrong per F2).

Resolution (verified): added `epilog=` to role_app, skill_app, and operator_app. `sq role --help` now shows `Address a role: sq role <slug|id|n> show|regen|rm` with slug/number/ID examples (sq role manager show / sq role 1 regen / sq role ROLE-000001 rm). Same pattern for skill (show|regen|rm) and operator (show|rm). The N1 slug-shadowing note is folded into each epilog. A fresh user can discover show/regen/rm from --help alone.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-06-12T13:18:13Z] Paul Reviewer:
  - Resolution detail: fixed via epilog= on role_app/skill_app/operator_app rather than unhiding the _addr subgroup -- keeps the internal name hidden while still teaching the full address grammar in --help. The N1 slug-shadowing caveat was folded into the same epilog, so one change closed both F3 and the N1 doc-note ask.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — N1 slug shadowing: slug matching a group verb is unaddressable by slug

<!-- sq:finding:F4:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
N1 (non-blocking). A role/skill/operator slugged exactly as a group verb (add/catalog/activate) is unaddressable by slug -- the named verb wins in get_command before _addr is tried. Number/full-ID still addresses it (verified), so there is an escape hatch, but the shadowing is silent. Acceptable given the escape hatch; worth a one-line doc note.

Resolution: folded into the F3 epilog on all three groups -- one line each noting the slug-shadowing caveat and pointing at full ID / bare number.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — N2 resolver duplication: resolve_agent_addr iterates db.items inline instead of reusing item helpers

<!-- sq:finding:F5:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
N2 (non-blocking). resolve_agent_addr (src/squads/_cli/_common.py:546-561) iterated db.items.values() inline with it.extra.get(X.SLUG, it.slug) for all three types instead of reusing _role_item/_skill_item/_operator_item (_services/_base.py:251-282) as the tech lead directed. Behavioral superset (roles/operators always carry a SLUG extra), but slug-matching semantics lived in two places that could drift.

Resolution (verified): resolve_agent_addr now delegates slug lookup to svc._role_item / svc._skill_item / svc._operator_item via a per-type dispatch table, eliminating the inline loop.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — N3 empty-body hint inaccurate: suggests a 'body' verb the groups do not have

<!-- sq:finding:F6:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
N3 (non-blocking). render_body_text -> _render_body printed `(empty -- set it with body)` when a body is empty, but there is no `body` verb on the role/skill/operator groups -- an inaccurate hint. Bodies are template-managed so it is rarely reached.

Resolution (verified): render_body_text gained an empty_hint param; role/skill/operator show pass `empty -- run sq sync to regenerate the definition` instead of the inaccurate hint.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — N4 inline shape check: _resolve_addr reimplements full-ID detection instead of _is_full_id_shape

<!-- sq:finding:F7:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
N4 (non-blocking). _role.py::_resolve_addr re-implemented full-ID-shape detection (t.rpartition("-")) inline instead of calling the new _is_full_id_shape helper in _common.py. Minor DRY.

Resolution (verified): _resolve_addr now calls _is_full_id_shape(t).
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — N5 stale comment: SKIL-000002 should be SKILL-000002 in test_skill_item_first_grammar

<!-- sq:finding:F8:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
N5 (non-blocking). tests/test_cli.py::test_skill_item_first_grammar had a `# SKIL-000002` comment; the prefix is SKILL.

Resolution (verified): SKIL-000002 -> SKILL-000002.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — N6 test coverage: no direct test for REV-000061 bracket/no-backslash fidelity on the new body path

<!-- sq:finding:F9:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
N6 (non-blocking). No test asserted REV-000061 bracket / no-backslash fidelity on the new role/skill/operator body path (structurally inherited from the shared _render_body markup=False, so low risk, but the regression net did not cover it directly).

Resolution (verified): test_role_skill_body_bracket_fidelity added -- asserts --raw output contains no backslash-escaped brackets on the role and skill body paths.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — N7 sq dev consistency: still uses the old listing shape, reads inconsistently against the flipped groups

<!-- sq:finding:F10:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F10:head:end -->

<!-- sq:finding:F10:body -->
N7 (non-blocking). sq dev still uses the old listing shape and now reads inconsistently against the three flipped groups. Flagged per the lead request; out of scope for TASK-000065.

Resolution: WontFix for this review -- explicitly out of scope as specified. Left for a follow-up if the inconsistency is worth closing.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T12:47:21Z] Paul Reviewer:
  - @python-dev — opened against FEAT-000064 / TASK-000065. The grammar flip and styled rendering are solid; this is purely the negative-path UX. Three blocking items (F1-F3): removed-list commands must point at 'sq list -t <type>' instead of leaking '_addr / Missing command'; the internal '_addr' name must not appear in any user-facing usage/error line; and 'sq role --help' must teach show/regen/rm (currently only catalog/activate show). N1-N7 are non-blocking — judgment calls and small cleanups, your call. Re-request review once F1-F3 are addressed and the three test_*_list_removed tests assert message content.
- [2026-06-12T12:59:30Z] Elias Python:
  - F1 fixed. AddressDispatchGroup now has a _REMOVED_VERBS ClassVar that each app subclass populates. _click_resolve_command checks the token against _REMOVED_VERBS before attempting named-command lookup or _addr routing. Role: 'sq role list' exits 1 with 'has been removed. Use sq list -t role to list tracked roles, or sq role catalog for the bundled catalog.' Skill: points at sq list -t skill. Operator: points at sq list -t operator. sq role list --available also hits the tombstone cleanly (the token 'list' is intercepted before args are parsed). The three test_list_removed tests now assert exit_code==1, 'has been removed' in output, and the correct replacement hint.
- [2026-06-12T12:59:38Z] Elias Python:
  - F2 fixed. Two-part fix. (1) Missing-verb interception: when _click_resolve_command routes to _addr and no non-option arg follows the address token (and --help is not present), it now exits 1 immediately with 'missing verb after address <token>. Usage: sq role <slug|id|n> show|regen|rm' — no _addr leakage, no Click 'Missing command.' (2) Display name: the return tuple from _click_resolve_command now uses '<slug|id|n>' as the command name instead of '_addr'. This means sq role manager --help shows 'Usage: sq role <slug|id|n> [OPTIONS] ADDR COMMAND' and sq role shw manager shows 'No such command manager' under 'sq role <slug|id|n>' usage — _addr never appears in user-facing text. Probed: sq role lst (exit 1 clean error), sq role manager (exit 1 clean error), sq role manager --help (no _addr in output), sq role shw manager (no _addr in output).
- [2026-06-12T12:59:46Z] Elias Python:
  - F3 fixed. Added epilog= to role_app, skill_app, and operator_app. sq role --help now shows: 'Address a role: sq role <slug|id|n> show|regen|rm. Examples: sq role manager show  sq role 1 regen  sq role ROLE-000001 rm. Note: a slug matching a group verb (catalog, activate) is unaddressable by slug; use the full ID or bare number instead.' Same pattern for skill (show|regen|rm, examples with slug/number/ID) and operator (show|rm). The N1 slug-shadowing note is also embedded in each epilog, folding N1 in naturally.
- [2026-06-12T12:59:55Z] Elias Python:
  - Non-blocking fixes taken: N1 (slug-shadowing note) folded into the F3 epilog on all three groups — one line each. N2 (resolver duplication) fixed: resolve_agent_addr now delegates slug lookup to svc._role_item / svc._skill_item / svc._operator_item via a per-type dispatch table, eliminating the inline db.items.values() loop. N3 (empty-body hint) fixed: render_body_text gained an empty_hint param; role/skill/operator show pass 'empty — run sq sync to regenerate the definition' instead of the inaccurate 'set it with body'. N4 (inline shape check) fixed: _role.py _resolve_addr now calls _is_full_id_shape(t) instead of reimplementing the rpartition check inline. N5 (stale comment) fixed: SKIL-000002 -> SKILL-000002 in test_skill_item_first_grammar. N6 (bracket fidelity) added: test_role_skill_body_bracket_fidelity checks that --raw output contains no backslash-escaped brackets on the role and skill body paths. N7 (sq dev consistency) skipped — out of scope as specified. All 355 tests pass, pyright strict clean, ruff check + format clean.
- [2026-06-12T13:00:00Z] Elias Python:
  - @reviewer — F1, F2, F3 all addressed; non-blocking N1-N6 done (N7 skipped per scope). Gates: 355 tests pass (+1 new), pyright strict clean, ruff clean. Please re-review.
- [2026-06-12T13:01:46Z] Pierre Chat:
  - Criterion change on F1: before 1.0 we owe nothing to the previous CLI interface. No tombstones, no migration hints for removed commands — the bar is only a clean, traceback-free error through the normal unknown-address path. The tombstone machinery added for F1 must come out; F2/F3 stand as written (they concern the new surface).
- [2026-06-12T13:06:48Z] Elias Python:
  - Tombstone machinery removed per op-pierre's criterion change on 2026-06-12. Removed: _REMOVED_VERBS ClassVar and the tombstone check block from AddressDispatchGroup in _common.py; _RoleDispatchGroup and _SkillDispatchGroup subclasses (collapsed back to cls=AddressDispatchGroup); _REMOVED_VERBS from _OperatorDispatchGroup (subclass kept for _ADDR_VERBS='show|rm'). All three modules (_role.py, _skill.py, _operator.py) cleaned of the from typing import ClassVar that was only needed for _REMOVED_VERBS.
  - sq role list / sq skill list / sq operator list now fall through the normal address path: 'list' is treated as an address token, the missing-verb check fires (no verb follows), exit 1 with 'missing verb after address list. Usage: sq role/skill/operator slug|id|n show|regen|rm'. No _addr leak. Same for sq role list --available (--available is an option, so no non-option verb is present). sq role lst (typo) and sq role manager show behave identically to before.
  - Three test_list_removed tests retargeted: assert exit_code==1, 'list' in output, '_addr' not in output, 'Traceback' not in output. Migration-hint assertions dropped.
  - Gates: 355 tests pass (1 skipped, pre-existing), pyright strict 0 errors, ruff check+format clean. F2/F3/N1-N6 fixes from the previous round are unchanged. @reviewer — ready for re-verdict on F1.
- [2026-06-12T13:10:37Z] Paul Reviewer:
  - APPROVED. Re-reviewed after the two fix rounds and op-pierre's 2026-06-12 criterion change (pre-1.0 nothing owed to the previous CLI; F1's bar is now only a clean traceback-free error through the normal unknown-address path). All three blocking findings resolved; all gates green.
  - F1 (revised criterion): PASS. The tombstone machinery is gone from source — no _REMOVED_VERBS ClassVar, no per-module dispatch subclasses for role/skill (both collapsed back to cls=AddressDispatchGroup); only _OperatorDispatchGroup survives, and solely to carry _ADDR_VERBS=show|rm. sq role/skill/operator list now fall through the normal address path: 'list' is taken as an address token, the missing-verb check fires, exit 1 with 'missing verb after address list. Usage: sq <type> slug|id|n show|regen|rm'. No _addr, no tombstone text, no migration hint, no traceback. 'list --available' behaves identically (--available is an option, so no non-option verb follows). The three test_*_list_removed tests now assert exit_code==1, 'list' in output, '_addr' absent, 'Traceback' absent — migration-hint assertions dropped.
  - F2 (no _addr leak): PASS. Probed sq role lst (exit 1 clean), sq role manager / no verb (exit 1 clean), sq role shw manager (exit 2, 'No such command manager' under 'sq role slug|id|n' usage), sq role manager --help, sq role manager regen --help. The internal _addr name appears in NO user-facing output — the display name slug|id|n is shown instead. (The usage line still carries a redundant ADDR positional from the address-subgroup wiring — that is the secondary 'spurious ADDR' remark from the original F2, not the _addr leak that blocked; the core bar is met.)
  - F3 (discoverability): PASS. sq role/skill/operator --help each carry an epilog teaching the full address grammar (slug|id|n show|regen|rm; operator show|rm), with slug/number/ID examples and the N1 slug-shadowing note folded in. A fresh user can discover show/regen/rm from --help alone.
  - Non-blocking fixes from round 1 verified intact: N2 resolve_agent_addr delegates slug lookup to svc._role_item/_skill_item/_operator_item via a per-type dispatch table (no inline db.items.values() loop); N3 empty_hint param wired on all three show commands ('run sq sync to regenerate ...'); N4 _resolve_addr in _role.py reuses _is_full_id_shape; N5 SKIL->SKILL comment fixed; N6 test_role_skill_body_bracket_fidelity asserts no backslash-escaped brackets on the role/skill body path.
  - Gates (clean checkout): uv run pytest 355 passed / 1 skipped (pre-existing); uv run pyright 0 errors; uv run ruff check . + format --check clean; uv run sq check no issues. Positive surface re-confirmed live: catalog, slug/number/ID resolution for show/regen/rm, sq list -t role|skill|operator, wrong-type tokens give clean exit-1 errors with no traceback.
  - One non-blocking loose end found, OUT OF SCOPE for this REV but worth a follow-up: src/squads/_cli/_main.py:84 — the 'sq init' Next-steps banner still advertises 'sq role list', a command US3 removed. Cosmetic, not negative-path UX, does not block this approval. @python-dev your call whether to fold it into a cleanup or a tiny follow-up task.
- [2026-06-12T13:18:41Z] Paul Reviewer:
  - Retrofit (structure only, no verdict change) -- requested by op-pierre. The F1-F3 blockers and N1-N7 observations that previously lived as prose in the item body are now tracked as finding sub-entities: F1-F3 (severity high/high/medium) Verified; F4-F10 carry N1-N7 (severity low) -- F4-F9 Verified, F10 (N7, sq dev consistency) WontFix as out of scope. F1/F2/F3 carry finding-scoped comments for their notable history (F1 tombstone added then removed per op-pierres pre-1.0 criterion; F2 usage display-name rewrite; F3 epilog approach folding in N1). The item body is now the review summary only -- scope, verdict history, acceptance status, and a pointer to the findings. Overall verdict unchanged: Approved.
<!-- sq:discussion:end -->
