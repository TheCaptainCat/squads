---
id: FEAT-977
sequence_id: 977
type: feature
title: Verb parity for skills, roles and operators
status: Draft
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
updated_at: '2026-09-29T14:59:28Z'
---
<!-- sq:body -->
Roster entities lack most of the verbs an item has, and use different names for some. Compared with a task, read from `--help`:

- Skills: `show regen rm status view` plus `add`; no `update` (a skill cannot be retitled at all), no `comment`, no `comments`; `rm` where items use `remove`.
- Roles: `show regen rm set-default status view` plus `catalog list activate`.
- Operators: group-level `add` and `list`; addressed as `sq operator <slug|id|n> show|rm|status`.

## Spec

- Skills gain `update` (title, `--desc`, `--when-to-use`), `comment`, `comments` and `remove`. `rm` stays as an alias.
- Roles gain `update`, `comment`, `comments` and `remove`; `rm` stays as an alias.
- Operators gain `show`, `update` (display name only, never the slug), `comment`, `comments`, `remove` and `status`.
- A slug is permanent: no `update` ever changes one.
- `comment` and `comments` are allowed on system skills and roles, since a comment never touches generated content. Only content-changing verbs refuse.
- Any verb that would edit a spec-generated item (a system skill or role, per the stored origin) refuses with an error that names the real authoring surface. It reuses the same classification as the existing body refusal (`_reject_unwritable_body`); no hand-rolled membership test.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 977 add-story "As a <role>, I want … so that …"`; track with `sq feature 977 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator, I want to retitle and describe a skill

<!-- sq:story:US1:body -->
Acceptance: sq skill <x> update sets title, --desc and --when-to-use on a project skill; the pointer file regenerates; refused with the named-surface error on a system skill; sq check clean.
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
Acceptance: roles gain update, comment, comments and remove; operators gain show, update (display name only, never the slug), comment, comments, remove and status; no update changes a slug; rm remains as an alias of remove.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an operator, I want a clear error on spec-generated items

<!-- sq:story:US4:body -->
Acceptance: any verb that would edit a spec-generated skill or role exits 1 with a message naming the real authoring surface (playbook for skills, role override for roles), driven by the single existing classification used by the body refusal; a test proves each new verb hits it.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T14:30:15Z] Pierre Chat:
  - Comments are allowed on system skills and roles: a comment never touches generated content. Only content-changing verbs refuse.
  - Operators get show, update (display name only, never the slug), comment/comments, and remove/status.
<!-- sq:discussion:end -->
