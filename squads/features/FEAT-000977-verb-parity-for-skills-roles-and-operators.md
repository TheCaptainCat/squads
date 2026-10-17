---
id: FEAT-977
sequence_id: 977
type: feature
title: Verb parity for skills, roles and operators
status: Done
author: product-owner
refs:
- FEAT-976:depends-on
- MILE-934:targets
- ADR-979
subentities:
- local_id: US1
  title: As an operator, I want to retitle and describe a skill
  status: Todo
- local_id: US2
  title: As an operator, I want to comment on skills and roles
  status: Todo
- local_id: US3
  title: As an operator, I want the item verbs on roles and operators
  status: Todo
- local_id: US4
  title: As an operator, I want a clear error on spec-generated items
  status: Todo
created_at: '2026-09-29T14:19:16Z'
updated_at: '2026-10-17T00:17:39Z'
---
<!-- sq:body -->
Roster entities lack most of the verbs an item has, and use different names for some. Compared with a task, read from `--help`:

- Skills: `show regen rm status view` plus `add`; no `update` (a skill cannot be retitled at all), no `comment`, no `comments`; `rm` where items use `remove`.
- Roles: `show regen rm set-default status view` plus `catalog list activate`; no `update`, `comment` or `comments`.
- Operators: group-level `add` and `list`; addressed as `sq operator <slug|id|n> show|rm|status` (driven: `show` and `status` already work); no `update`, `comment` or `comments`; `rm` where items use `remove`.

## Spec

- Skills gain `update` (title, `--desc`, `--when-to-use`), `comment`, `comments` and `remove`. `rm` stays as an alias.
- Roles gain `update`, `comment`, `comments` and `remove`; `rm` stays as an alias.
- Operators end with `show`, `update` (display name only, never the slug), `comment`, `comments`, `remove` and `status`. Of these `show` and `status` exist today; `update`, `comment`, `comments` and `remove` are new, and `rm` stays as an alias.
- A slug is permanent: no `update` ever changes one, and none takes a slug option.
- `comment` and `comments` are allowed on system skills and roles, since a comment never touches generated content. Only content-changing verbs refuse.
- Any verb that would edit a spec-generated item (a system skill or role) refuses with an error that names the real authoring surface. It reuses the same classification as the existing body refusal (`_reject_unwritable_body`), the one the origin feature's refusal also reads; no hand-rolled membership test. Origin is the label operators see; the refusal follows the classification.
- Comments written on roster entities use the permanent-slug header grammar of the comment-header feature, and `update` on a roster entity edits display fields only.

- Pronouns are exempt from that refusal. A pronouns value is identity the operator sets, like the name and the default-role designation, not generated content, so `update` may set, change or clear pronouns on a system role (and on an operator or project role) while every other content-changing edit on a system role is still refused. The pronouns value itself, its checks and where it is stored are the business of the pronouns feature.

- The skill invocability option is exempt from that refusal too. `--operator-invocable <yes|no|default>` is how a squad chooses whether a skill is offered to the person at the keyboard; it is an operator's choice about exposure, not generated content, so `sq skill <addr> update --operator-invocable` works on a system skill, and it is the only `update` option a system skill accepts. The option, its values and its storage belong to the skill invocability feature.

- Lifecycle verbs are not content-changing either: `remove` (the same command as `rm`) and `status` stay allowed on system skills and roles, like `comment`.

- A role's name is exempt from that refusal too. A role's stored name is its name and is renamed only through `update`, so `update` may rename any role, bundled ones included, while every other content-changing edit on a system role is still refused.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 977 add-story "As a <role>, I want … so that …"`; track with `sq feature 977 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator, I want to retitle and describe a skill

<!-- sq:story:US1:body -->
Acceptance:
- sq skill <x> update sets the title, --desc and --when-to-use on a project skill; the skill's pointer file regenerates with the new description; the slug, file name and pointer directory do not change.
- On a system skill it exits 1 with the named-surface error (the playbook); sq check clean afterwards.
- sq skill <x> remove works and sq skill <x> rm still works as an alias with the same effect.

- On a system skill, update --operator-invocable yes|no|default succeeds (exit 0) and is the only update option accepted there: update --desc, --when-to-use and a title change on the same skill still exit 1 with the named-surface error, and so does a call that combines the option with any of them (nothing is written).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an operator, I want to comment on skills and roles

<!-- sq:story:US2:body -->
Acceptance: comment and comments work on skills and roles with the same semantics as items (attribution, @mentions, inbox), including on system skills and roles, where they are allowed.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an operator, I want the item verbs on roles and operators

<!-- sq:story:US3:body -->
Acceptance:
- Roles gain update, comment, comments and remove; operators gain update, comment, comments and remove, and keep show and status as they work today; rm remains as an alias of remove on skills, roles and operators.
- Operator update changes the display name only: it takes no slug option, and the operator's slug, file name and id are identical before and after; a role or skill update likewise never changes a slug.
- On a system role, remove (the same command as rm) stays allowed, like rm and status; update is refused with the named-surface error (the role override) except for the role's name, which any role, bundled ones included, may be renamed through update. On a project role all of them work. A project role's body stays refused by the existing body refusal, unchanged.
- sq check clean after each verb.
- Setting pronouns on a system role through `update` succeeds (exit 0, the value is then visible on the role), and a content-changing edit on that same role is still refused with the named-surface error. Pronouns on a project role and on an operator work the same way.
- Renaming a bundled role through `update` succeeds (exit 0, the new name is then visible on the role), and any other content-changing option on that role is still refused.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an operator, I want a clear error on spec-generated items

<!-- sq:story:US4:body -->
Acceptance:
- Any content-changing verb that would edit a spec-generated skill or role exits 1 with a message naming the real authoring surface (playbook for skills, role override for roles). Content-changing means update (except the exempt fields below), body and view edits; remove (the same command as rm) and status are lifecycle verbs and stay allowed, like comment.
- The decision comes from the single existing classification used by the body refusal; a test proves the new content-changing verb (update) hits it, a test asserts no second membership test exists, and --force does not lift it.
- comment and comments are not content-changing: a test proves they succeed on a system skill and a system role.
- remove and rm are not content-changing: a test proves each succeeds on a system role and a system skill.
- A role's name is not content-changing: a test proves a name-only `update` succeeds on a system role, and that any other content-changing `update` on the same role is still refused, so the exemption is exactly the name.
- Pronouns are not content-changing: a test proves a pronouns-only `update` succeeds on a system role, and that a content-changing `update` on the same role is still refused, so the exemption is exactly the pronouns value and nothing broader.
- The skill invocability option is not content-changing: a test proves update --operator-invocable succeeds on a system skill, and that every other update option on that skill, alone or combined with it, is still refused, so the exemption is exactly that one option.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T14:30:15Z] `op-pierre` Pierre Chat:
  - Comments are allowed on system skills and roles: a comment never touches generated content. Only content-changing verbs refuse.
  - Operators get show, update (display name only, never the slug), comment/comments, and remove/status.
- [2026-10-09T15:35:27Z] `product-owner` Nina Product:
  - 2026-10-09 readiness pass: folded in the comments-allowed and operator-verb rulings; corrected the baseline (operator show and status already exist, driven), so the real operator gains are update, comment, comments, remove. Refusal wording aligned with FEAT-976 (classification, not a second test) and with ADR-979 decision 6 (update edits display fields only). Moved to Ready; still depends on FEAT-976.
- [2026-10-09T18:16:47Z] `product-owner` Nina Product:
  - 2026-10-09: added the pronouns exemption to the spec and to US3/US4 acceptance (ADR-981 consequence); still Ready, still depends on FEAT-976.
- [2026-10-09T19:18:32Z] `product-owner` Nina Product:
  - 2026-10-09 per ADR-983 clause 3: added the --operator-invocable exemption (the only update option a system skill accepts) to the body and to US1 and US4 acceptance. Still Ready.
- [2026-10-16T17:07:18Z] `manager` Catherine Manager:
  - When the roster update verb lands, rewrite the passages that say roles, skills and operators have no update verb and that point to sq import for renames: docs/overrides.md (~449, ~2226, ~2471) and CHANGELOG.md (~39). From REV-1064 F10.
- [2026-10-16T19:53:48Z] `tech-lead` Olivia Lead:
  - Broken down into TASK-1070 (ST1-ST6; depends on TASK-990 and TASK-1069). Two points:
    
    1. @manager design question: may `sq role <slug> update --title` rename a system (bundled) role? Two rulings collide. op-pierre (2026-10-16, BUG-1049/TASK-1059): a role is renamed only through its update verb, and the CHANGELOG already tells adopters to rename a bundled role with an `sq import` update event. But US3 and TASK-1069 ST6 refuse update on system roles, with only pronouns exempt. If both hold, a bundled role can never be renamed. Recommendation: the name is identity, like pronouns and the default-role designation. The gate refuses update field by field against one declared exemption set: role `{title}` (+ `pronouns` with the pronouns feature), skill `{}` (+ `operator_invocable` with the invocability feature). Role update gets no other option, because a role's definition is resolved from the catalog and its overrides. TASK-1070 ST4 is written this way. TASK-1069 ST6 needs the same exemption, or its import refusal breaks the documented rename.
    2. @product-owner: US3 and US4 still list `remove` as refused on system roles. Per op-pierre 2026-10-16 (FEAT-976), rm stays allowed and `remove` is the same command, so please amend. TASK-1070 follows the ruling.
- [2026-10-16T19:54:18Z] `manager` Catherine Manager:
  - @tech-lead @product-owner Settled by the 2026-10-16 op-pierre ruling (a role's stored name is its name; renamed only through update): update may rename any role, bundled ones included. The role name is an exempt field of the system-entry refusal; TASK-1070 ST4 as written. remove is rm, so it stays allowed like rm (2026-10-16 FEAT-976 ruling); US3/US4 to be amended.
- [2026-10-16T19:54:47Z] `product-owner` Nina Product:
  - 2026-10-16: US3, US4 and the body amended per the manager's ruling: remove is rm and stays allowed on system roles and skills; update may rename any role, the name being an exempt field.
<!-- sq:discussion:end -->
