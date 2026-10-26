---
id: REV-1170
sequence_id: 1170
type: review
title: 'Review: role bodies take prose beside the definition'
status: Approved
author: reviewer
refs:
- TASK-1165
description: Commit 633c735a, TASK-1165 ST1 and ST2
subentities:
- local_id: F1
  title: Body verb help still says a role body is refused, and a test pins it
  status: Verified
  severity: medium
- local_id: F2
  title: Role refusal tail still says drop the view from [selected] to author the
    body
  status: Verified
  severity: medium
- local_id: F3
  title: migration.md and overrides.md still say a role body refuses writes
  status: Verified
  severity: low
- local_id: F4
  title: set_body docstring lists a role as both refused and admitted
  status: Verified
  severity: low
- local_id: F5
  title: CHANGELOG and a test name claim an empty-mission state no input can produce
  status: Verified
  severity: info
- local_id: F6
  title: Foreign view tag in a role body write names view verbs the role refuses
  status: Verified
  severity: low
created_at: '2026-10-26T15:40:59Z'
updated_at: '2026-10-26T16:12:46Z'
---
<!-- sq:body -->
Review of commit 633c735a: TASK-1165 ST1 (every role body takes prose beside its role_definition tag, skills still refused) and ST2 (no Mission/Responsibilities section and no placeholder when empty; the --file help names the list keys). Rules: ADR-880 sections 6, 8, 9 and ADR-1151 section 11 with the op-pierre rulings of 2026-10-26.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1170 add-finding "…" --severity medium`; track with `sq review 1170 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Body verb help still says a role body is refused, and a test pins it

<!-- sq:finding:F1:body -->
The `body` verb's help, shared by `sq role|skill|operator <x> body --help` (`src/squads/_cli/_common.py:2136-2139`), still says: "A body generated from a declared view (a role, a system or per-type skill) is refused even with `--force`". After this commit a role body write is admitted, so the help on `sq role <slug> body --help` contradicts the command it documents.

Failure scenario: an adopter reads `sq role qa body --help`, concludes the role takes no prose, and moves the text into an override or drops the view instead.

The stale phrase is pinned by `tests/cli/test_greeting_skill_reads_and_records_the_profile_cli.py:89` (`assert "a role, a system or per-type skill" in text`), so the suite stays green while the help is wrong. Fix: name only the system and per-type skills as refused, say a role takes prose beside its tag, and update the pinning test.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T15:55:51Z] `python-dev` Elias Python:
  - Rewrote the body --help: a role takes prose beside its generated definition; only system and per-type skills refuse. Pinning test updated.
- [2026-10-26T16:07:57Z] `reviewer` Paul Reviewer:
  - Verified at c466f309: role and skill body --help now say a role takes prose beside its definition and name only system and per-type skills as refused; reverting the help turns 3 tests red.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Role refusal tail still says drop the view from [selected] to author the body

<!-- sq:finding:F2:body -->
The role refusal built in `_refuse_classified_roster_write` (`src/squads/_services/_base.py:660-666`) ends with "Drop the view from `[selected]` to author this directly instead, then clear its leftover tag with `sq role <slug> view disable role_definition`". On a role it is raised by `view disable`, `view add <other view>` and the metadata update.

Driven on a scratch squad: `sq role tech-lead view disable role_definition` prints that tail. For a role it now misleads: authoring prose needs no view drop any more (ADR-880 section 8), and dropping `role_definition` from `[selected]` removes the generated definition from every role at once. An adopter who only wanted to add a note beside the definition follows the remedy and loses every role's definition.

For a role the tail should point at `sq role <slug> body` (prose beside the definition) and keep the view drop only as the way to replace the generated definition. The same text is quoted in `docs/roles.md:704` (ST3 scope).
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T15:55:54Z] `python-dev` Elias Python:
  - Role refusal now points at 'sq role <slug> body' for prose and keeps the view drop only for replacing the generated definition; skill wording unchanged. Pinned in the service test.
- [2026-10-26T16:07:59Z] `reviewer` Paul Reviewer:
  - Verified at c466f309: view disable role_definition and view add milestone_rollup on catalog and template roles now point at sq role <slug> body for prose and keep the view drop for replacing the definition; skills keep the old tail. The catalog metadata update has its own message (override file), unaffected. Reverting the role branch turns 3 tests red.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — migration.md and overrides.md still say a role body refuses writes

<!-- sq:finding:F3:body -->
Two adopter docs still describe a role body as refusing writes, and ST3's brief names only one of them.

- `docs/migration.md:891-915` ("A role or skill that still holds old generated text"): says a role body refuses writes while its view is declared and prescribes the four-step drop/clear/restore/view add remedy for roles. On a role, `sq role <slug> body -m "" --force` alone now clears the old text and re-inserts the tag enabled at the top (driven: a role body holding hand-placed old text and no tag became the tag alone, and sq check stayed clean). ST3 does not list migration.md.
- `docs/overrides.md:2066-2083`: "With `role_definition` dropped, a role takes `body`..." and "Putting the view back in `[selected]` makes the bodies refuse writes again", plus the `sq role qa body` / `view disable` example. ST3 lists this one.

Home: TASK-1165 ST3; flagging so the writer picks up migration.md too.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-26T15:56:13Z] `python-dev` Elias Python:
  - Left Open for the writer (ST3): docs/migration.md and docs/overrides.md, listed on ST3.
- [2026-10-26T16:11:04Z] `tech-writer` Theo Writer:
  - Fixed in docs: migration.md "A role or skill that still holds old generated text" now gives one command for a role (`sq role <slug> body -m "" --force` clears the old text and puts the tag back at the top) and keeps the four-step remedy for skills only, with a greeting_skill example.
  - overrides.md "Authoring a role or skill body by hand" is rewritten around skills; the role case points to roles.md, and dropping role_definition is described only as the way to replace the generated definition. The qa body/view disable example is gone. Also fixed the same stale claim in workflow.md "Which bodies take prose". All commands driven on a scratch squad with the dev build.
- [2026-10-26T16:12:43Z] `reviewer` Paul Reviewer:
  - Verified at c3231f49: migration.md, overrides.md, roles.md, workflow.md, agents.md and internals.md now describe prose beside the role definition; the role old-text remedy is the one body -m '' --force command, and the view drop is kept only for replacing the definition. Driven: the roles.md sq import refusal text matches the CLI byte for byte, the reviewer body example ends at the tag alone, agreements append and clear as documented.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — set_body docstring lists a role as both refused and admitted

<!-- sq:finding:F4:body -->
`ItemsMixin.set_body`'s docstring (`src/squads/_services/_items.py:688-692`) now reads "A role's, system skill's and per-item-type skill's body is refused (...), while a role's, a custom skill's and an ordinary item's is admitted." A role is listed as both refused and admitted; the first "A role's" was not removed.

Failure scenario: a developer reading the service API cannot tell the rule without reading `_reject_unwritable_body`. Fix: drop "A role's" from the refused list.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-26T15:55:57Z] `python-dev` Elias Python:
  - set_body docstring no longer lists a role as refused.
- [2026-10-26T16:08:02Z] `reviewer` Paul Reviewer:
  - Verified at c466f309: the set_body docstring lists only system and per-type skills as refused.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — CHANGELOG and a test name claim an empty-mission state no input can produce

<!-- sq:finding:F5:body -->
The CHANGELOG entry ("A role with no responsibilities or mission shows no section for it"), the CLI test file name `test_a_role_with_no_responsibilities_or_mission_renders_no_section_cli.py` and its module docstring ("or an empty mission leaves no heading") describe an empty-mission role. No input produces one: mission is a required non-blank field for catalog roles (`_roles/_loader.py:353-362`), templates (`_TEMPLATE_REQUIRED_KEYS`) and item-defined roles (`_resolver.py` `_REQUIRED_FOR_NEW`, `_REQUIRED_NON_BLANK_FIELDS`). Driven: `role add` without `--mission`, `update --mission ""`, `update --file` with `mission = ""` and a catalog override with `mission = ""` are all refused.

The `{% if source.mission %}` guard is harmless as defence, and only the unit test with a hand-built source reaches it. But the adopter-facing CHANGELOG claims behaviour no adopter can reach. Drop "or mission" from the CHANGELOG (ST3 is rewriting the entry anyway) and from the CLI test's name and docstring, which exercises no empty mission.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-26T15:55:59Z] `python-dev` Elias Python:
  - Mission renders unconditionally; CHANGELOG, CLI test name/docstring and the unit test no longer claim an empty mission. Manifest and store regenerated.
- [2026-10-26T16:08:04Z] `reviewer` Paul Reviewer:
  - Verified at c466f309: CHANGELOG and the renamed CLI test speak of responsibilities only; the Mission guard is gone and Mission renders on catalog, template and item-defined roles (driven). No test can go red for the guard itself, since no input yields an empty mission; the CLI test now asserts Mission is always present.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Foreign view tag in a role body write names view verbs the role refuses

<!-- sq:finding:F6:body -->
Now that a role body write is admitted, the view-tag check in the body write is reachable on a role host, and its remedy names verbs the role refuses.

Driven: `sq role tech-lead body --append -m 'x <tag> y' (with <tag> the HTML-comment form of sq:view:milestone_rollup)` errors with "...to show or hide the view use `sq role tech-lead view add milestone_rollup` or `sq role tech-lead view disable milestone_rollup`". Both named commands are refused on a role (view add admits only `role_definition`, view disable is refused), each with the roster refusal quoted in F2.

Failure scenario: the operator follows either remedy and hits a second, unrelated refusal. The first sentence ("Leave it out of the body") is the only remedy that works; on a role host the message should drop the view-verb clause, or name only what the host admits (as the conflicting-state message already does: it names `view add role_definition` only).
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-26T15:56:02Z] `python-dev` Elias Python:
  - A foreign view tag in a role body now gets the plain 'leave it out of the body' message, no view verbs. Pinned for all three role kinds.
- [2026-10-26T16:08:06Z] `reviewer` Paul Reviewer:
  - Verified at c466f309: a foreign or differently-stated view tag in a role body write now says only to leave it out, on all three role kinds; custom skills and ordinary items keep the view-verb remedy. Restoring the role branch turns 3 tests red.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T15:42:32Z] `reviewer` Paul Reviewer:
  - - Verdict: changes requested. The behaviour is right and matches ADR-880 sections 6, 8, 9 and ADR-1151 section 11; the six findings are stale operator-facing text (F1, F2, F6 in code, F3 in docs, F4 a docstring, F5 a CHANGELOG overclaim). F1 and F2 are the two to fix before ST3 documents the shipped text.
    - Driven on a scratch squad with the dev build, all as specified: replace, append, refused replace without force, `-m ""` with and without force, `--file` and stdin on catalog, template, item-defined and archived roles; an unknown role is refused with "activate it first". Tag hand-moved, removed, duplicated, disabled, conflicting (refused, names `view add` only) and CRLF all re-place correctly; marker-shaped prose is refused by reject_markers. `position = "bottom"` in an override puts prose above the definition. `sq import` replace/append/refusal match the verb; skills squads, greeting, sq-memory and sq-task still refuse replace, append and force through the verb and the importer.
    - Read surfaces: prose shows after the definition in `sq role <slug> show` and in `sq show ROLE-n --json` body; absent from `.claude/agents/*.md` (after sync and regen), CLAUDE.md, AGENTS.md and `sq role <slug> show --json` (grep validated against the role files). `sync` and `repair` leave role files byte-identical; a 0.16 squad (uvx squads==0.16.0) with hand-placed role prose migrated with the prose kept.
    - Mutation on a scratch copy of the commit, targeted set of 311 tests: guard reverted 69 red, `position` set to bottom 33 red, responsibilities guard removed 7 red, either `--file` help sentence removed 2 red each. tests/meta 518 passed on HEAD.
- [2026-10-26T16:08:12Z] `reviewer` Paul Reviewer:
  - Re-review of c466f309: F1, F2, F4, F5 and F6 verified on a scratch squad with the dev build, each code fix going red under mutation (3 tests each for F1, F2, F6). No new findings. F3 stays Open for TASK-1165 ST3; the review is ready to approve once ST3 lands. @manager
- [2026-10-26T16:12:46Z] `reviewer` Paul Reviewer:
  - All six findings verified; REV-1170 approved. @manager
<!-- sq:discussion:end -->
