---
id: FEAT-1024
sequence_id: 1024
type: feature
title: The --help surface follows one rule
status: Draft
author: product-owner
priority: medium
refs:
- REV-958:addresses
- MILE-934:targets
description: Every command's help answers what it does, what to type and what comes
  back, in one dialect with every flag described.
subentities:
- local_id: US1
  title: As a contributor, I want the help rule written where I read it
  status: Todo
- local_id: US2
  title: As an adopter, I want help free of maintainer reasoning and private names
  status: Todo
- local_id: US3
  title: As a script author, I want the JSON field reference in the docs, not in help
  status: Todo
- local_id: US4
  title: As a user, I want every option and argument described
  status: Todo
- local_id: US5
  title: As a user, I want the same flag to read the same everywhere
  status: Todo
- local_id: US6
  title: As a user, I want one exit-code form in help
  status: Todo
- local_id: US7
  title: As a user, I want one markup dialect that survives an 80-column terminal
  status: Todo
- local_id: US8
  title: As a reader, I want summaries that state the outcome and flags described
    once
  status: Todo
- local_id: US9
  title: As a maintainer, I want a guard that holds help to the rule
  status: Todo
- local_id: US10
  title: As an adopter, I want the docs and changelog to match the new help
  status: Todo
created_at: '2026-10-15T21:43:01Z'
updated_at: '2026-10-15T21:43:41Z'
---
<!-- sq:body -->
Brings the rendered `--help` surface into line with the rule on what a command's help holds, so that a person with the tool and no repository finds what they typed `--help` to learn. The rule, the eleven findings and their measurements are the review's; the stories below cite the rule (R1 to R9) and the findings (F1 to F11) and add acceptance only.

## Scope

- The rule for a command's help body, summary, option and argument text, `--json` line and exit-code line, written where a contributor reads it (R1 to R9, F11).
- Moving maintainer reasoning and private names out of help, to the code they explain (F1).
- Trimming the `--json` field reference from 13 help bodies, with the field-level reference landing in the docs in the same change where help is its only home today (F3).
- A description on every option and argument, one shared definition per flag, one wording per meaning (F2, F8).
- One exit-code form (F5).
- One markup dialect, and a layout that survives an 80-column terminal (F4, F7).
- Summaries, and flags described twice (F9, F10).
- A guard in `tests/meta` that walks the live command tree and holds the surface to the mechanical half of the rule (F11).
- Documentation and changelog.

## Out of scope

- A per-item verb's help needing a real item to open (F6). It is a behaviour change to how the item and skill groups resolve their address, and gets its own item.
- Any command, flag, default or output change other than the help text itself. Where help is accurate about behaviour that is wrong, that is a bug to file.
- Changing the help renderer. It stays on Rich console markup (op-pierre, 2026-10-09).
- A verdict on the designs whose rationale leaves the help body (`check`'s degradation, `role catalog`'s default column). Only where the prose lives is in scope.
- The structural refactors and the comment pass of the structural review. Text moved out of help into comments and helper docstrings follows the project comment rule: one or two sentences, no release versions, no ticket ids, no history.

## Sequencing

Help text touches `_cli/` broadly, so this is built after FEAT-980, after the 0.16.0 bump and after TASK-989, so it does not collide with the CLI changes in flight. The milestone's build order places it as step 7: the writer's strings first, then one developer task that places them and adds the guard. The review sizes the writer's pass at about a day and a half on the stronger model and the placement at about two days. A docs change precedes or accompanies the trim wherever a help body is the only home of a contract (US3, US6).

## Open questions for the architect

Stated in the stories that raise them (US3, US6, US9). None is answered here.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1024 add-story "As a <role>, I want … so that …"`; track with `sq feature 1024 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a contributor, I want the help rule written where I read it

<!-- sq:story:US1:body -->
Acceptance (R1 to R9, F11):
- CONTRIBUTING.md has its own short section stating the three questions a help screen answers, the content-to-home table (help, code comment, docs), the 10-source-line tripwire for a body, and the review test: render the command at 80 columns and read the screen.
- The section states R1 to R9 in applicable form, not as a list of commands currently wrong.
- A reviewer can hold a help change to the section without reading REV-958.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an adopter, I want help free of maintainer reasoning and private names

<!-- sq:story:US2:body -->
Acceptance (F1, R3):
- The rendered help of every command listed in F1 contains no function, class, module or package path, no internal type, no history word (legacy, old, today) and no shouted caveat.
- sq check keeps exactly: the summary, the exit-code line, one sentence that output order is stable, one sentence that a broken workflow or playbook override is reported as an issue while the other checks still run.
- Moved reasoning lives at the code it explains, in the helper or module docstring, or after a form feed; each moved text obeys the project comment rule.
- sq reflog --tree carries its warning in one plain sentence.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a script author, I want the JSON field reference in the docs, not in help

<!-- sq:story:US3:body -->
Acceptance (F3, R5, R6):
- The 13 listed bodies keep the one-line --json description naming the top-level shape, any don't-misuse sentence (graph: branch on edge_semantic, never edge_kind; tree: anchor true is an invented root for a parent cycle; search: region says where the hit was found) and the pointer 'Fields: sq docs stability'.
- Nine bodies shrink with no docs change, the docs already carrying their fields.
- For search, tree, graph and workflow ref-kinds, the field reference lands in docs/stability.md in the same change that removes it from help, and the stability sentence naming help as their authority is corrected.
- graph is about 8 body lines and search about 6.
Open question for the architect: writing these fields into the stability document may extend the frozen --json contract from the named commands to every field. The review does not settle which fields are frozen; that ruling is needed before the docs are written.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As a user, I want every option and argument described

<!-- sq:story:US4:body -->
Acceptance (F2, R4, R5):
- Walking the live command tree, no option or argument other than --help renders a blank description (741 rendered, 186 blank today).
- Each is one line: what the value is and what it does here, with where legal values come from (STATUS names its source).
- --json is described on every command that takes it, in one line naming the top-level shape.
- The panel's default and required markers are never restated in the text.
- Each shared flag is declared once and reused by the per-type, per-kind and roster registrations.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As a user, I want the same flag to read the same everywhere

<!-- sq:story:US5:body -->
Acceptance (F8):
- --file, -m/--message, --force on a status change, --raw, --desc, --author, --all, --depth and --tech each have one wording per meaning, from one definition in _cli/_common.py.
- --all reads 'Include closed items.'; --author names operators; -m states that it repeats.
- No hand-written '(default ...)' or '(required)' remains where the panel prints it; required flags validated by hand say so in the same words.
- The --priority difference between item verbs and list/tree is kept; a test or comment records why.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — As a user, I want one exit-code form in help

<!-- sq:story:US6:body -->
Acceptance (F5, R7):
- A command with no code of its own says nothing about exit codes.
- Each of the 11 commands with a code of its own carries one line in the form 'Exit codes: <code> <meaning>. See sq docs faq.'
- sq import keeps, in two lines, that exit 3 means the work is applied: do not retry, read applied from --json.
- docs/faq.md's row for code 3 names sq import before import's paragraph shrinks.
Open question for the architect: whether the exit-4 partial-result contract (stderr line per skipped file, one JSON line, unchanged payload) is stated in help at all on inbox, search, board list and memory list/search, given docs/faq.md and docs/stability.md state it once for all five. The review's standard implies a one-line code and meaning only; the architect confirms.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — As a user, I want one markup dialect that survives an 80-column terminal

<!-- sq:story:US7:body -->
Acceptance (F7, F4, R8, R9):
- No rendered help contains doubled backticks, asterisks, a '::' line ending or a cross-reference role; literals use single backticks, including in option descriptions.
- No help text holds a square-bracketed lowercase word, #, / or @ span that Rich reads as a tag.
- Body paragraphs wrap at 78 columns after dedent; line-structured text sits in a no-rewrap block under 78 columns.
- No enumeration is cut by an ellipsis at 80 columns: retype's NEW-TYPE and reflog --op show every value or point at the command that lists them; the tests that pin the truncated string move with the fix.
- Example blocks in the role, operator and skill epilogs render as separate lines.
- The addressed roster verbs and the sub-entity verbs print one placeholder each, distinctly named.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — As a reader, I want summaries that state the outcome and flags described once

<!-- sq:story:US8:body -->
Acceptance (F9, F10, R1, R4):
- Every summary is one sentence on one source line of 72 characters or fewer, verb first, naming the outcome; none names a mechanism or carries a parenthesis.
- Sub-entity verbs use the kind's own labels (stories, add-story), as update already does; status on role, operator and skill no longer points at a work-item verb.
- No type group or create summary has a wrong article ('a epic') for any declared type name.
- Each flag is described once, in its help=; bodies keep only how flags combine (override scaffold about five lines on the four override kinds; tree keeps that ancestors of a match are kept and dimmed).
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — As a maintainer, I want a guard that holds help to the rule

<!-- sq:story:US9:body -->
Acceptance (F11):
- A tests/meta module walks the live Click tree in-process, covering per-type and per-kind commands, and asserts for every canonical command: non-empty option and argument descriptions; one-line summary of 72 characters or fewer; no doubled backtick, role or '::' line ending; no bracket tag; no body line over 78 columns; no truncation ellipsis at 80 columns.
- Each assertion is enabled with the story that fixes its finding, not before.
- The guard runs in the default suite in a few seconds and adds no module-level mutable state.
Open question for the architect: how the guard encodes an accepted exception to the 10-source-line tripwire (an allowlist or reviewer judgment only), and how it treats project-declared types whose commands exist only under an override.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->

<!-- sq:story:US10 -->
### US10 — As an adopter, I want the docs and changelog to match the new help

<!-- sq:story:US10:body -->
Acceptance:
- docs/stability.md and docs/faq.md carry the changes stories 3 and 6 require, with no internal references.
- The CHANGELOG unreleased 0.16 section has an entry written by the tech writer describing the help changes for adopters, with no item ids.
- Documentation that quotes a help screen or flag description matches the shipped text.
<!-- sq:story:US10:body:end -->

#### Discussion

<!-- sq:story:US10:discussion -->
<!-- sq:story:US10:discussion:end -->
<!-- sq:story:US10:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T21:43:41Z] Nina Product:
  - @manager FEAT-1024 drafted for REV-958 (F1 to F5, F7 to F11; F6 excluded, needs its own item). 10 stories; open questions for @architect in US3 (fields frozen), US6 (exit-4 in help) and US9 (guard exceptions). Build after FEAT-980, the bump and TASK-989.
<!-- sq:discussion:end -->
