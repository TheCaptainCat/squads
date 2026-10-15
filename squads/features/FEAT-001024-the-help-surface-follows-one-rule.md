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
updated_at: '2026-10-15T21:52:05Z'
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

Raised in US3, US6 and US9, and answered there by the architect (ruled in ADR-1025 for US3); each story records the question and its answer.
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
- For search, tree, graph and workflow ref-kinds, the field reference lands in docs/stability.md in the same change that removes it from help. The stability sentence naming help as their authority is withdrawn, not reworded to another authority.
- The docs list each key and mark its value as vocabulary, open set or display, per ADR-1025. Listing a field records the existing freeze and widens nothing; no new tier. edge_semantic, search region and ref-kind role are open sets. The graph --json field list includes badges, which its help omits.
- The ref-kinds catalog row in docs/stability.md is added.
- graph is about 8 body lines and search about 6.

Question for the architect: writing these fields into the stability document may extend the frozen --json contract from the named commands to every field. Answered in ADR-1025 (awaiting the operator's acceptance, which the docs pass waits for).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
- [2026-10-15T21:51:04Z] Robert Architect:
  - Ruled in ADR-1025 (a contract question, so an ADR). Listing a field in `docs/stability.md` does not freeze it: Tier 3 freezes a shape by command, and the document already says the promise covers every key a shape emits whether enumerated or not (read). So the move changes no promise. `workflow ref-kinds` is a Tier 3 catalog under ADR-738 §8, whose table row was owed and missing; this change discharges it.
    
    No new tier. Each key stays frozen in name, type, presence and meaning, and the field reference marks keys whose value is not a fixed squads format as one of: vocabulary (a name the squad declares; read the catalog), open set (squads values that may grow; tolerate unknown), display (human text; never parse). ADR-1025 §3 has the per-shape table for search, tree, graph and ref-kinds.
    
    For the writer: the help-as-authority sentence goes; enumerate from the live payload, key for key, not from help. `sq graph --json` emits `badges`, which its help omits (read: golden `graph_feat_json.json`; driven: `sq graph --help`). Add the open-set mark to ref-kind `role` in `docs/workflow.md` too.
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
- inbox, search, board list and memory list/search each carry exactly: 'Exit codes: 4 partial result; what could be read is printed. See sq docs faq.' The mechanics (stderr line per skipped file, JSON line, unchanged payload) live in the docs only. No contract change.
- sq import keeps, in two lines, that exit 3 means the work is applied: do not retry, read applied from --json.
- docs/faq.md's row for code 3 names sq import before import's paragraph shrinks.

Question for the architect: whether the exit-4 partial-result contract is stated in help at all, given docs/faq.md and docs/stability.md state it once for all five. Answered: one line, text above.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
- [2026-10-15T21:51:05Z] Robert Architect:
  - Yes, one line, on each of the five, and nothing more. Membership in the partial-result class is per command (ADR-947 §1), and a script author reading one command's help must learn that it can exit non-zero with output worth keeping; that is the one fact a caller misreads. The mechanics (one stderr line per skipped file, the JSON line, the unchanged payload, precedence) live once with the table in the faq and stability docs.
    
    Suggested line, 77 characters: `Exit codes: 4 partial result; what could be read is printed. See sq docs faq.` It replaces the paragraph on `inbox`, `search`, `board list`, `memory list` and `memory search` (the last loses its "degrade-signal rule" back-reference). R7's import-style exception does not apply: code 4 is not a mutation that must not be retried.
    
    No contract change, so no ADR: help is not contract, and ADR-947 stays as written.
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
- A tests/meta module walks the live Click tree in-process, covering per-type and per-kind commands, and makes seven assertions for every canonical command:
  1. non-empty option and argument descriptions;
  2. one-line summary of 72 characters or fewer;
  3. no doubled backtick, role or '::' line ending;
  4. no bracket tag;
  5. no body line over 78 columns;
  6. no truncation ellipsis at 80 columns;
  7. a body over 10 source lines appears in an immutable allowlist of (command path, reason) pairs; an allowlist entry that no longer matches a body over 10 lines fails the test as stale.
- The line-count rule in assertion 7 is the one stated in the CONTRIBUTING section of US1, and the two agree on what counts as a source line.
- A second walk runs over a test-local override declaring an awkward custom type, sub-entity kind and ref kind, never the repo's own override, and makes the same assertions.
- Each assertion is enabled with the story that fixes its finding, not before.
- The guard runs in the default suite in a few seconds and adds no module-level mutable state.

Question for the architect: how the guard encodes an accepted exception to the 10-source-line tripwire, and how it treats project-declared types. Answered: the immutable allowlist and the second walk above.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
- [2026-10-15T21:51:06Z] Robert Architect:
  - **Over-10-line bodies: an allowlist with reasons, checked both ways.** A tripwire nothing trips is not one, and review alone is how the long bodies REV-958 measured shipped. The guard counts a body's source lines after the summary paragraph and before any form feed, blank lines not counted (my reading of R2; US1's section must state the same count). A body over 10 fails unless its canonical command path is in an immutable module constant, a tuple of (path, reason) pairs, so no mutable-state guard trips. The reason is one line naming what a reader would type or read differently (R2's admission test); "the contract has nowhere else to live" is not one. The guard also fails on a stale entry, whose command is now 10 lines or fewer or no longer exists, so the list cannot outlive its exceptions. The list does not replace the reviewer: adding an entry is a diff the reviewer approves. Enable it after the trims (US2, US3, US8), seeded with what remains. It is a seventh assertion beyond US9's six; @product-owner to add it to the acceptance if accepted.
    
    **Project-declared types and kinds: a fixture spec, not the repo's own.** The main walk runs under the bundled spec in a tmp squad, never this repo's `squads/.overrides`, which would tie the guard to the dogfood squad. A second, smaller walk uses a test-local override that declares one custom type with a custom sub-entity kind and ref kind, picked to stress the generators: a vowel-initial name (the article), an irregular plural, a label of realistic length. It walks only what the spec changes (that type's group and kind verbs, its create command, the root listing). Custom types appear only when the resolved spec declares them (read: ADR-263), and tests already drive spec-derived help (read: REV-958 F11). What it holds is every string squads writes, templates around a declared name included. It does not hold the adopter's own declared strings (label, hint, heading): those are their content, and a bound on them would be a workflow-lint question, out of scope here (inferred).
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
- [2026-10-15T21:51:07Z] Robert Architect:
  - @manager Architect answers to the three open questions, each also on its story:
    - US3: ruled in ADR-1025, created in its initial status for acceptance. Listing a field in `docs/stability.md` records the existing Tier 3 freeze and does not widen it. No new tier; each key's value is marked vocabulary, open set or display. The `ref-kinds` catalog row was owed under ADR-738 §8 and missing. Help as authority is withdrawn; `sq graph --json` already emits `badges`, which its help omits.
    - US6: one line on each of the five commands, the mechanics in the docs only: `Exit codes: 4 partial result; what could be read is printed. See sq docs faq.` No contract change.
    - US9: the over-10-line body is checked against an immutable allowlist of (command path, reason) pairs that also fails on stale entries; custom types and kinds are covered by a second walk over a test-local override, never the repo's own. This adds a seventh guard assertion to US9; @product-owner to fold it in.
    - Needs the operator: accept ADR-1025 before the US3 docs pass. It marks edge_semantic, search region and ref-kind role as open sets, which docs/workflow.md's four-value role list comes closest to reading as closed.
<!-- sq:discussion:end -->
