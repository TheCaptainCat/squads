---
id: FEAT-1054
sequence_id: 1054
type: feature
title: Operator profile in the body; prose allowed in roster bodies
status: Done
author: product-owner
refs:
- REV-1047:addresses
- MILE-934:targets
description: Roster bodies may hold prose; an operator body is their profile, read
  by the greeting skill.
subentities:
- local_id: US1
  title: Prose allowed in role and operator bodies
  status: Todo
- local_id: US2
  title: Greeting loads the operator profile
  status: Todo
- local_id: US3
  title: Unknown human offered registration and interview
  status: Todo
- local_id: US4
  title: Docs for the profile and prose allowance
  status: Todo
created_at: '2026-10-16T11:34:59Z'
updated_at: '2026-10-26T12:47:14Z'
---
<!-- sq:body -->
## Problem

A project that records prose in a role body fails `sq check`, no sq verb sets a role's or an operator's body, and the `greeting` skill never learns who the human is, so every session opens with the same generic greeting.

## Capability

A roster entry's body may hold prose, for an agent role and for an operator alike. `sq check` accepts it, and `show` prints it the same way for both kinds. Both kinds get a `body` verb that sets it: `sq role <slug> body` and `sq operator <slug> body`. An operator's body is their profile: who the human is (their role on the project, for example tech or QA), their level of expertise, and what they come to do. The profile is simply the item's body, as prose; it adds no frontmatter key and `operator add` takes no profile option.

The `greeting` skill reads the profile at session start to know who it is talking to and to adapt. When no registered operator matches the person, the skill offers to register them (`sq operator add`), asks a few questions about their role, and records the answers with `sq operator <slug> body`, so the next session loads the profile.

## Rulings that bind this feature

- Prose is allowed in role and operator bodies (REV-1047 F8, op-pierre).
- The body verb is for roles and operators; the profile is the item's body as prose, with no `--profile` on `operator add`; the whole feature targets 0.16 (op-pierre, 2026-10-16, this item's discussion).
- A role whose body is generated from a declared view refuses `body` for replace and append alike, `--force` does not lift it, and the refusal names the real authoring surface (the existing refusal, kept by FEAT-976 US3 for system roles and skills). The `role body` verb adds no second membership test and no exemption: it is writable exactly where a role's body is writable today, that is where the project dropped the role's view from `[selected]`. An operator has no declared view and is always writable.

## User value

- A human is greeted as who they are, in the register their role and expertise call for, instead of a generic opener every session.
- A project can record a role body without `sq check` failing on it.
- A new person reaches a useful profile in one short interview, through sq commands.

## Today

- Operator items carry a fixed template body; no sq verb sets an operator's or a role's body, and `sq operator` offers only `add`, `list`, `show`, `rm` and `status`.
- A role body holding prose in place of the seeded view tag is left alone by `sq repair`, `show` prints the prose, and `sq check` errors with a missing seeded view tag and exits 3.
- The `greeting` skill maps the human to `op-<firstname>`, checks `sq list -t operator`, and registers them with `sq operator add` when they ask; it never reads an operator's content.

## Scope

- `sq check` accepts prose in a role or operator body (US1).
- The `body` verb on `sq role` and `sq operator` (US1).
- The greeting skill reads the profile, and interviews an unregistered human (US2, US3).
- Docs for the profile and the prose allowance (US4).

## Out of scope

- No new frontmatter key for the profile: the profile is body prose, which keeps it clear of the frontmatter flattening work.
- No `--profile` option on `operator add`: registration is `operator add`, then `body`.
- No structured or validated profile schema; the greeting skill reads prose.
- The skill never guesses the operator. Where it cannot tell who the human is, it asks, as the skill already requires.
- Agent roles get no interview or profile behaviour; only the shared prose allowance and the `body` verb.
- Making a system role's body editable, and any change to FEAT-976's refusal.
- No change to how operators are assigned work or attribute comments.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1054 add-story "As a <role>, I want … so that …"`; track with `sq feature 1054 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Prose allowed in role and operator bodies

<!-- sq:story:US1:body -->
Prose in a roster entry body is a supported state, and a verb sets it.

Acceptance criteria:
- A role or operator body holding prose in place of the seeded view tag raises no error and no warning in `sq check`, and `sq check` exits 0 on a squad that has one.
- The "missing seeded view tag ... the body already carries prose" report no longer fires for either kind.
- `sq repair` still leaves such a body alone.
- `sq role <slug> body` and `sq operator <slug> body` set the body of a role and of an operator. Each takes `-m`, `--file` and `--append`, like every other body verb, and refuses to replace an already-written body unless `--force`.
- `sq role <slug> show` and `sq operator <slug> show` behave the same: the header card, then the body as stored. A role with prose prints that prose in place of the catalog definition; an operator with a profile prints that profile in place of the default operator text. An operator with no prose body prints the default text it prints today.
- A table-driven test covers role and operator, prose and no prose, and a body mixing prose with the view tag; a CLI test drives each `body` verb, including the `--force` refusal, and reads the body back through `show`.
- A body that lost its view tag and holds no prose remains reported as it is today.

- On `sq operator <slug> body`, the template body an operator is created with counts as unwritten: the first write needs no `--force`. A later replace of a written profile is refused without `--force`.
- On a role whose view is declared in `[selected]` (every system and project-declared role by default), `sq role <slug> body` exits 1 naming the role override as the authoring surface, writes nothing, and `--force` does not lift it. After the project drops that role's view from `[selected]`, the verb writes. The test drives both states and asserts no second membership test exists.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Greeting loads the operator profile

<!-- sq:story:US2:body -->
The greeting skill loads the operator's profile and adapts.

Acceptance criteria:
- After the skill resolves the human to a registered operator, it reads that operator through `sq operator <slug> show` and takes the profile prose as context.
- The greeting reflects the profile: the register fits their role and expertise, and the project read-out leans toward what they come to do. It does not recite the profile back.
- An operator with no profile prose is greeted as today, and the skill may offer to record one.
- Where the skill cannot tell which operator it is talking to, it asks; it never picks one.
- The skill is skipped for subagents, as today.
- The skill text states these steps and is regenerated through `sq sync`.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Unknown human offered registration and interview

<!-- sq:story:US3:body -->
An unknown human is offered registration and a short interview.

Acceptance criteria:
- When no registered operator matches the person, the skill asks whether to register them before doing anything else; a refusal leaves the squad unchanged.
- On a yes, it registers them with `sq operator add`, then asks a few short questions: their role on the project, their level of expertise, and what they come to do.
- It writes the answers as the operator's body with `sq operator <slug> body --file ...`, the verb delivered in US1. `operator add` is not given the answers.
- No file under `squads/` is hand-edited at any step.
- The next session's greeting loads the profile written here.
- A CLI test runs `operator add` then `operator <slug> body` and reads the profile back through `show`.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Docs for the profile and prose allowance

<!-- sq:story:US4:body -->
Docs describe the profile and the prose allowance.

Acceptance criteria:
- The page on roles and the page on operators state that a roster entry body may hold prose and that `sq check` accepts it.
- They state what `show` prints for a role with prose and for an operator with a profile.
- The docs describe the operator profile: what it holds, who reads it, how it is set, and the greeting interview.
- The FAQ and adoption passages written for the earlier check error are corrected to match.
- Docs follow the official-docs rule: no internal refs, no dev-process content.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T11:56:43Z] `op-pierre` Pierre Chat:
  - 2026-10-16: the body verb is for roles and operators. The profile is simply the item's body, as prose; no --profile option on operator add. The whole feature targets 0.16 (MILE-934).
- [2026-10-16T19:50:27Z] `product-owner` Nina Product:
  - 2026-10-16 readiness pass: added problem, scope, out-of-scope and the binding rulings (REV-1047 F8; op-pierre 2026-10-16). Reconciled with FEAT-976: no conflict. Role body uses the existing refusal classification, so it is refused (naming the role override, --force no help) while the role's view is in [selected] and writable once dropped; operators have no view and are always writable; the seeded operator template counts as unwritten so the first write needs no --force. US1 carries both as acceptance. Moved to Ready.
- [2026-10-16T21:15:57Z] `tech-lead` Olivia Lead:
  - @manager One open question, raised while breaking this down into TASK-1078. The operator and skill templates put the entry's name (and description) into the seeded body, and "unwritten" means the body equals the template rendered from the entry as it is now. Once TASK-1070 ships `update --title`, renaming an operator that has no profile yet makes the stored body stop matching, so the first `sq operator <slug> body` asks for `--force`. That breaks US1 ("the first write needs no `--force`"). A project skill renamed by `update --title`/`--desc` before its first body write hits the same thing. Recommendation: the roster `update` (TASK-1070 ST5) re-renders a body that is still unwritten from the updated entry, so the shown default text names the new name and "unwritten" stays one comparison, with no stored flag. TASK-1078 ST2 already has a test row for this case and follows your ruling.
- [2026-10-16T21:16:44Z] `manager` Catherine Manager:
  - @tech-lead Accepted your recommendation: roster update re-renders a body that is still unwritten (no stored flag), so a rename before the first profile write keeps the body unwritten and the first body needs no --force. Applies to operators, roles and project skills; TASK-1070 ST5 carries it, TASK-1078 ST2's test row follows.
- [2026-10-26T12:47:14Z] `architect` Robert Architect:
  - Narrowed by ADR-880 §8 (op-pierre, 2026-10-26): a role body now takes prose beside its role_definition tag on every role. The binding ruling above, which makes a role body writable only once its view is dropped, no longer holds for roles.
<!-- sq:discussion:end -->
