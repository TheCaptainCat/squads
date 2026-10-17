---
id: REV-1087
sequence_id: 1087
type: review
title: 'Review of TASK-1078 ST1-ST4: roster prose, body verb, greeting profile'
status: Requested
author: reviewer
refs:
- TASK-1078
subentities:
- local_id: F1
  title: Empty-body hints name remedies that fail and omit the new body verb
  status: Open
  severity: low
- local_id: F2
  title: Shared body help says only roles are refused, shown on skills and operators
  status: Open
  severity: low
- local_id: F3
  title: 'Stale no-role-body-verb claims: dead role branch in clear_roster_body_cmd,
    0.15 manual'
  status: Open
  severity: low
- local_id: F4
  title: Body-verb table has a vacuous inactive-role row; meta guard narrower than
    ST2 asks
  status: Open
  severity: low
- local_id: F5
  title: Greeting treats a retired operator as unknown, then operator add fails
  status: Open
  severity: low
- local_id: F6
  title: 'Dropping the role view leaves a stranded live tag: body writes but check
    exits 3'
  status: Open
  severity: medium
- local_id: F7
  title: A damaged role_definition tag now passes sq check as prose
  status: Open
  severity: low
created_at: '2026-10-17T00:37:35Z'
updated_at: '2026-10-17T00:38:56Z'
---
<!-- sq:body -->
Scope: the uncommitted TASK-1078 ST1 to ST4 diff against 17de25d5 (`git diff HEAD -- src tests` plus the four untracked test modules): prose accepted in role and operator bodies by `sq check`, the shared `body` verb on roles, operators and skills, and the greeting skill reading and recording the operator profile.

Method: every shape driven in scratch squads with the dev tree; the touched test modules run (130 passed); ruff and pyright clean on the touched files.

Held up under probing:
- Role with its view selected (system, developer): `body` refused for `-m`, `--file`, `--append`, with and without `--force`, naming `.overrides/roles.toml`, file unchanged. Inactive or unknown role: "activate it first".
- Operator: first write over the template needs no `--force`, also after `update --title`; a second replace exits 1 with the file unchanged; `--append` and `--file -` work. Project and generated skills behave as before.
- One classifier: no `roster_body_view_name` or view-membership test under `_cli/`; all three verbs go through `set_body`.
- A retired operator accepts `body`, `update` and comments on it, while acting as it is refused: consistent across verbs.
- `sq repair` re-seeds an empty tagless role and leaves prose alone; `sq sync` is a fixed point after body writes.
- The greeting skill reads the profile with `sq operator <slug> show`, asks first, records with `operator <slug> body --file`, and its `.claude/` pointer is unchanged. A 0.15 squad after `migrate up` and `sync` renders the same greeting `show` output and identical `.claude/` files as a fresh init (the item file differs only in timestamps).
- No ticket ids or history in the new comments and docstrings.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1087 add-finding "…" --severity medium`; track with `sq review 1087 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Empty-body hints name remedies that fail and omit the new body verb

<!-- sq:finding:F1:body -->
Driven in a scratch squad:

- **Operator, empty region:** `sq operator op-dan show` prints `(empty — run sq sync to regenerate the operator definition)` (`_cli/_operator.py:161`). Neither `sq sync` nor `sq repair` changes the file; the hint stays. The remedy that works is now `sq operator <slug> body`.
- **Role, view dropped and tag disabled:** `sq role manager show` prints `(disabled — sq role manager view add role_definition re-enables it)`; running it exits 1 with `no declared view 'role_definition'`. The body verb works in that state and is not named. `_role_empty_body_hint` checks `disabled` before `view_undeclared`, so the undeclared case never reaches its own text.

**Fix:** the operator hint names `sq operator <slug> body`; the role hint, when the view is undeclared, names `sq role <slug> body` (and checks undeclared before disabled). Add both to the shape tests.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Shared body help says only roles are refused, shown on skills and operators

<!-- sq:finding:F2:body -->
`register_body_verb` gives one help text to all three groups: "A role whose body is generated from a view is refused outright; --force does not lift that." Driven: `sq skill greeting body --help` shows it, although generated and system skills are refused the same way (`sq skill greeting body -m x --force` exits 1 naming the view template override), and `sq operator <slug> body --help` shows it although an operator is never refused. The removed `skill_body` help said system skills were rejected.

**Fix:** word it by kind-neutral cause, e.g. "A body generated from a declared view (a role, a system or per-type skill) is refused outright; --force does not lift that."
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Stale no-role-body-verb claims: dead role branch in clear_roster_body_cmd, 0.15 manual

<!-- sq:finding:F3:body -->
Two passages still say a role has no `body` verb, and one also says `sq check` reports a prose role:

- `src/squads/_views.py:734-748`, `clear_roster_body_cmd`: the docstring says "a role has none, so it's a single-event sq import - instead". With roles skipped in `_seeded_view_issues`, both callers (`_maintenance.py:562`, `_validators.py:951`) now reach it only for skills, so the role branch (the `sq import -` event) is dead. Drop the branch and the claim, or give it the role body verb if a caller still needs it.
- `src/squads/_migrations/_v0_14_to_v0_15.py:212-228`, the `manual` text `sq migrate chlog` prints: it says a role "has no body verb at all" and that `sq check` "then names the same four-step remedy" for a prose role. An adopter upgrading from 0.14 through 0.16 reads both and neither is true. Migration steps may record history, but this one instructs the reader, so its role half should say what 0.16 does (prose is accepted; `sq role <slug> body` once the view is dropped).
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Body-verb table has a vacuous inactive-role row; meta guard narrower than ST2 asks

<!-- sq:finding:F4:body -->
- **Vacuous row:** `bundled-role-not-activated` in `tests/cli/test_roster_body_verb_by_shape_cli.py` addresses slug `tester`, which is not in the catalog (manager, architect, tech-lead, reviewer, qa, devops, product-owner, tech-writer), and the squad is built with `roles_spec="all"`, so no bundled role is inactive. The row proves only the unknown-slug message (`sq role nope body` prints the same "activate it first"). Build that row with a narrower bundle and a real slug such as `qa`.
- **Meta guard narrower than specified:** ST2 asks that no `roster_body_view_name` call is added under `_cli/`; `test_the_shared_helper_writes_through_set_body_only` checks only the helper's own body. A grep shows zero calls under `_cli/` today; widen the assertion to every `_cli` module so it guards what it says.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Greeting treats a retired operator as unknown, then operator add fails

<!-- sq:finding:F5:body -->
The skill's first step is `sq list -t operator`, which hides an Archived operator (driven: after `sq operator op-alice status Archived`, the list omits OP-17). A returning person whose operator was retired therefore lands in the **Not registered** branch: the skill asks to register them, then `sq operator add "Alice Smith"` exits 1 with `an operator with slug 'op-alice' already exists`, and the interview has nowhere to go. The skill names no reactivation.

**Fix:** list with `--all`, and for a retired match say to ask, then `sq operator <slug> status Active`, then read the profile as for a registered operator. One more golden phrase covers it.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Dropping the role view leaves a stranded live tag: body writes but check exits 3

<!-- sq:finding:F6:body -->
**Shape** (driven, scratch squad, dev tree): drop `role_definition` from `[selected]` (the escape the refusal names), run `sq sync`, then `sq role reviewer body -m "R prose"`.

**Result:** the write succeeds (exit 0), but `place_view_tags` keeps the now-undeclared live tag, so the region is `R prose` + `the live sq:view:role_definition tag`. `sq role reviewer show` prints the raw tag under the prose, and `sq check` exits 3 with one error per role: `no declared view 'role_definition' with a resolvable presentation template; see sq workflow views for the declared set`. Neither that error nor the refusal ("Drop the view from `[selected]` to author this directly instead") names the step that clears it, `sq role <slug> view disable role_definition`; after it, check is clean and show prints only the prose.

**Test gap:** the `role-view-dropped` and `declared-role-view-dropped` rows in `tests/cli/test_roster_body_verb_by_shape_cli.py` assert only that the prose is read back; neither runs `sq check` nor asserts the raw tag is absent, so the US1 path "after the project drops the view, the verb writes" ends in a check-failing squad under green tests.

**Fix:** make the documented path converge: name `view disable` in the refusal's drop sentence (or the check error), and add `sq check` exit 0 plus "no raw tag in show" to the dropped-view rows. The gate text itself is TASK-1069's; route the message change there if it is out of this task's scope.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — A damaged role_definition tag now passes sq check as prose

<!-- sq:finding:F7:body -->
**Question asked:** with `_seeded_view_issues` skipping a role whose region holds prose beside a missing tag, can a broken role file pass `sq check`?

**Yes, for a damaged tag** (driven, view selected, region replaced by the shape, then `sq check` and `sq role reviewer show`):

| region | check | show |
|---|---|---|
| `Some prose` | clean | prose (intended) |
| a truncated tag (the comment opener, then sq:view:role_definition, no closer) | clean | raw broken comment, no definition |
| `&nbsp;` | clean | `&nbsp;`, no definition |
| empty | error, restore with view add | hint |
| a well-formed tag with a typo (role_defintion) | two errors | raw tag |

A truncated tag is not a marker, so it counts as prose and the role's generated definition silently stops rendering; the agent pointer loads `sq role <slug> show` and gets nothing useful. Before this change the same file reported the missing tag (inferred from the diff: the removed branch fired on any prose). The same applies to legacy text a 0.15 reclaim skipped: the migration names it once in `skipped`, and `sq check` no longer does.

**Fix (simplest rule that keeps the ruling):** keep skipping prose, but still report when the stripped prose contains a `sq:view:` fragment, i.e. a damaged tag; add the truncated row to the check-by-shape table. Or accept the gap explicitly with a comment on FEAT-1054.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-17T00:38:56Z] Paul Reviewer:
  - Seven findings: F6 medium (dropping the role view, the escape the refusal names, leaves a stranded live tag so check exits 3); F1-F5 and F7 low (hints, help text, stale role-has-no-body-verb claims, a vacuous test row, retired operator in the greeting, damaged tag passing check). Recommend ChangesRequested on F6; the lows are cheap to fold in. @manager @python-dev
<!-- sq:discussion:end -->
