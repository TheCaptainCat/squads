---
id: FEAT-1054
sequence_id: 1054
type: feature
title: Operator profile in the body; prose allowed in roster bodies
status: Draft
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
updated_at: '2026-10-16T11:57:31Z'
---
<!-- sq:body -->
## Capability

A roster entry's body may hold prose, for an agent role and for an operator alike. `sq check` accepts it, and `show` prints it the same way for both kinds. Both kinds get a `body` verb that sets it: `sq role <slug> body` and `sq operator <slug> body`. An operator's body becomes their profile: who the human is (their role on the project, for example tech or QA), their level of expertise, and what they come to do. The profile is simply the item's body, as prose; it adds no frontmatter key and `operator add` takes no profile option.

The `greeting` skill reads the profile at session start to know who it is talking to and to adapt. When no registered operator matches the person, the skill offers to register them (`sq operator add`), asks a few questions about their role, and records the answers with `sq operator <slug> body`, so the next session loads the profile.

## User value

- A human is greeted as who they are, in the register their role and expertise call for, instead of a generic opener every session.
- A project can record a role body without `sq check` failing on it.
- A new person reaches a useful profile in one short interview, through sq commands.

## Today

- Operator items carry a fixed template body; no sq verb sets an operator's or a role's body, and `sq operator` offers only `add`, `list`, `show`, `rm` and `status`.
- A role body holding prose in place of the seeded view tag is left alone by `sq repair`, `show` prints the prose, and `sq check` errors with a missing seeded view tag and exits 3.
- The `greeting` skill maps the human to `op-<firstname>`, checks `sq list -t operator`, and registers them with `sq operator add` when they ask; it never reads an operator's content.

## Non-goals

- No new frontmatter key for the profile: the profile is body prose, which keeps it clear of the frontmatter flattening work.
- No `--profile` option on `operator add`: registration is `operator add`, then `body`.
- No structured or validated profile schema; the greeting skill reads prose.
- The skill never guesses the operator. Where it cannot tell who the human is, it asks, as the skill already requires.
- Agent roles get no interview or profile behaviour; only the shared prose allowance and the `body` verb.
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
- [2026-10-16T11:56:43Z] Pierre Chat:
  - 2026-10-16: the body verb is for roles and operators. The profile is simply the item's body, as prose; no --profile option on operator add. The whole feature targets 0.16 (MILE-934).
<!-- sq:discussion:end -->
