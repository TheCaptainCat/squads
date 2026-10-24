---
id: FEAT-1101
sequence_id: 1101
type: feature
title: 'Adopter field-report fixes: errors, round-trips, checks, guidance'
status: Draft
author: product-owner
refs:
- MILE-1051:targets
- REV-1099:addresses
description: 'Fixes for the triaged findings of REV-1099: defects, new checks, docs
  and bundled guidance.'
subentities:
- local_id: US1
  title: Writes fail cleanly under index-lock contention
  status: Todo
- local_id: US2
  title: Milestone bodies round-trip and create sets every declared field
  status: Todo
- local_id: US3
  title: Generated files report the truth after a team or version change
  status: Todo
- local_id: US4
  title: Operator subtasks close without --force
  status: Todo
- local_id: US5
  title: sq check flags Approved reviews with Open findings and unowned types
  status: Todo
- local_id: US6
  title: Findings can be Deferred or Noted
  status: Todo
- local_id: US7
  title: Adopters can find how to import, override and change roles
  status: Todo
- local_id: US8
  title: Bundled guidance names the right owners and asks the right questions
  status: Todo
- local_id: US9
  title: sq list has a compact one-line form
  status: Todo
created_at: '2026-10-24T09:39:06Z'
updated_at: '2026-10-24T09:40:05Z'
---
<!-- sq:body -->
## Problem

An adopter project upgraded to 0.15.0 and ran eight agents for a day, up to four writing to `sq` at once. Its field report (REV-1099) was net positive: no work data lost, concurrent writers never corrupted the index. It also surfaced real defects, missing checks and guidance gaps. The review triaged them and the operator ruled to fix every finding as recommended.

## Scope

### Defects
- **F4** Index-lock contention is silent, then ends in a raw traceback. A wait on the lock must say so, and a timeout must be a clean error that states the write did not happen and can be retried.
- **F5** A milestone body does not round-trip: the refusal does not name the fix for a placed view tag, and feeding back the rendered roll-up duplicates it.
- **F9** `sq create bug` cannot set severity; create should expose every field the type declares, and a declared default should be honoured.
- **F16** A second author on a type silently drops its Team workflow line from CLAUDE.md; the line must render for any number of authors.
- **F6** Closing an operator-assigned subtask (Todo to Done) must not need `--force`.
- **F2** `sync` calls an older release's generated pointer "had drifted"; it should say it is outdated, and the post-migrate instruction should say what is left for sync to do.

### New sq check rules
- **F10** Warn on an Approved review that holds an Open finding.
- **F3** Warn when a type holds items but no active role authors it, naming the catalog role to activate.

### Docs, bundled guidance and ergonomics
- **F1** Document the `sq import` event schema: every op with its required and optional fields and an example.
- **F12** Role-override docs show splat-refs on list fields.
- **F13** `sq role show` says how to change a role's definition.
- **F15** `override scaffold --role` writes every overridable field commented out with its bundled value, plus the append idiom.
- **F17** Bundled handoffs address the review's author, not a hardcoded `@reviewer` or `@qa` (wording change only).
- **F8** `sq list` gains a compact one-line form.
- **F11** No bundled convention on when to open a review. The init interview checklist gains a question about it; each adopter decides.
- **F14** The bundled tech-writer owns the narration sweep (orchestration loop step 5 names it), and its default model moves to sonnet.

### Finding lifecycle
- **F7** Findings gain Deferred (with a ref to the item that carries the work) and Noted (for an info finding). The design is governed by the finding-lifecycle decision record; this feature delivers it.

## Out of scope
- Findings already fixed or by design in REV-1099 (11.1, 11.2, 11.6, 14.5, 14.6, 14.7 arrow, 14.8).
- Preferred IDs on import and a bundled designer role (closed WontFix in REV-565).
- Enforced separation of duties (FEAT-124) and the daemon work (ADR-1052), beyond keeping the F4 guarantees in view for it.
- Replacing a single playbook guide by slug (part of F17, set aside as heavier).
- A bundled rule for when a review is warranted (F11 is a question, not a rule).

## Acceptance criteria
- Holding the index lock from another process produces a waiting notice on stderr and, past the timeout, a one-line error naming the lock file, stating nothing was written and the command can be retried; no traceback.
- Writing back a milestone body obtained from the read surface never duplicates the roll-up; refusing a placed view tag tells the user to leave the tag out.
- `sq create bug --severity high` sets severity; any declared field of any type is settable at create; an omitted field with a declared default stores that default.
- With two or more authors of a type, CLAUDE.md lists all of them in that type's Team workflow line.
- A subtask assigned to an operator goes Todo to Done without `--force`.
- After an upgrade, sync labels a pointer from an older release as outdated, not drifted, and the post-migrate message says what sync still does.
- `sq check` warns on an Approved review with an Open finding and on a type with items but no active authoring role (naming the role to activate), and stays clean otherwise.
- `sq docs adoption` (or `sq import --help`) lists every import op with its fields and an example.
- Override docs show a splat-ref on a role list field; `sq role show` ends with how to change the role; `override scaffold --role` output lists every overridable field with its bundled value.
- Bundled review and bug handoffs address the item's author instead of a hardcoded role.
- `sq list` has a compact one-line-per-item form.
- The init interview asks how the repository decides when to open a review.
- The tech-writer role lists the narration sweep, loop step 5 names it, and its default model is sonnet.
- A finding can be marked Deferred (requiring a ref to the carrying item) or Noted, per the finding-lifecycle decision record.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1101 add-story "As a <role>, I want … so that …"`; track with `sq feature 1101 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Writes fail cleanly under index-lock contention

<!-- sq:story:US1:body -->
Covers F4. A write that waits on the index lock says so on stderr; past the timeout it ends in a one-line error naming the lock file, stating nothing was written and the command can be retried, with no traceback. The same guarantees hold for the daemon path.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Milestone bodies round-trip and create sets every declared field

<!-- sq:story:US2:body -->
Covers F5 and F9. Writing back a milestone body never duplicates the rendered roll-up, and the refusal for a placed view tag names the fix. Create accepts every field the type declares (severity on bugs), and a declared default is stored when the field is omitted.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Generated files report the truth after a team or version change

<!-- sq:story:US3:body -->
Covers F16 and F2. CLAUDE.md lists every author of a type in its Team workflow line instead of dropping it when there are two or more. Sync labels a pointer from an older release as outdated rather than drifted, and the post-migrate message says what sync still has to do.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Operator subtasks close without --force

<!-- sq:story:US4:body -->
Covers F6. A subtask assigned to an operator for a manual step goes from Todo to Done on the normal path, so agents are not trained to reach for --force.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — sq check flags Approved reviews with Open findings and unowned types

<!-- sq:story:US5:body -->
Covers F10 and F3. check warns on an Approved review that still holds an Open finding, and on a type that holds items while no active role authors it, naming the catalog role to activate. Both stay silent when the squad is sound.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Findings can be Deferred or Noted

<!-- sq:story:US6:body -->
Covers F7. A finding can be marked Deferred, pointing by ref to the item that carries the work, or Noted when it is an info finding with nothing to fix. The design is set by the finding-lifecycle decision record; check verifies the Deferred pointer.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — Adopters can find how to import, override and change roles

<!-- sq:story:US7:body -->
Covers F1, F12, F13 and F15. The import event schema is documented op by op with fields and examples; role-override docs show splat-refs on list fields; role show ends with how to change the role; override scaffold for a role lists every overridable field with its bundled value and the append idiom.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — Bundled guidance names the right owners and asks the right questions

<!-- sq:story:US8:body -->
Covers F17, F14 and F11. Bundled handoffs address the item author instead of a hardcoded role; the tech-writer owns the narration sweep named in loop step 5 and defaults to sonnet; the init interview asks how the repository decides when to open a review, with no bundled rule.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — sq list has a compact one-line form

<!-- sq:story:US9:body -->
Covers F8. A compact option prints one line per item with a truncated title so long lists stay readable in a narrow terminal.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
