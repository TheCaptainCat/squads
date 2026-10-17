---
id: TASK-1048
sequence_id: 1048
type: task
title: Enforce operator slug grammar and one author namespace
status: Done
parent: FEAT-980
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-979:implements
- REV-1026:addresses
description: Operator slugs op-…, skills out of the author namespace, roster_slug_valid,
  the 0.16 migration refusal, and --as squads refused (ADR-979 A1–A5)
subentities:
- local_id: ST1
  title: Operator slug grammar at creation; skills out of the author namespace
  status: Done
  assignee: python-dev
  story: US2
- local_id: ST2
  title: Default roster_slug_valid check
  status: Done
  assignee: python-dev
  story: US2
- local_id: ST3
  title: 0.16 migration refuses a role or operator in breach
  status: Done
  assignee: python-dev
  story: US3
- local_id: ST4
  title: Refuse --as squads in every comment writer
  status: Done
  assignee: python-dev
  story: US2
- local_id: ST5
  title: Docs and CHANGELOG for the operator slug rule
  status: Done
  assignee: tech-writer
  story: US5
created_at: '2026-10-16T11:18:03Z'
updated_at: '2026-10-16T12:35:07Z'
---
<!-- sq:body -->
Builds ADR-979 amendments A1 to A5, confirmed by op-pierre on 2026-10-16. The amendment text in ADR-979 ("Amendments — 2026-10-16") is the spec; the subtasks add acceptance only. A6 (the slug fallback in the 0.16 migration) is already built and is out of scope here.

## Scope

- Operator slug grammar `op-[a-z0-9][a-z0-9-]*` at the roster creation seam, and one author namespace of roles plus operators plus the reserved `operator`/`squads`; skills fall outside it (A1, A2).
- A new default `sq check` rule, `roster_slug_valid` (A3).
- The 0.16 migration refuses a role or operator in breach, replacing today's report line (A4).
- `--as squads` refused by every comment writer, the importer included (A5).
- The MANUAL text and the adopter docs that state the old behaviour.

## Out of scope

The rest of REV-1026 F5 (an importer actor not in the roster). Any stronger author match than slug equality (A5). Rewriting a header already written.

## Testing

One table-driven test per behaviour, over slug shapes rather than one case per branch: grammar position and character class (prefix, case, spaces, empty tail, double hyphen, digits, reserved words, a live role's slug), and the same table run through every entry path the subtask names. Each refusal asserts exit 1 and an unchanged squad (no file written, index unchanged).

## Verification

A migration dry run on a copy of this repository's squad, made under the scratchpad (never under the live tree or a bare /tmp), with the dev tree: it must report how many operators and roles break the rule. Expected here: zero, since the only operator is `op-pierre`. Paste the count in the handoff comment.

## Gates

`uv run --all-extras pyright`, `ruff check`, `ruff format --check`, the touched tests, and `sq check` clean. No ticket IDs in code or test names; docstrings one or two sentences.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1048 add-subtask "<title>"`; track with `sq task 1048 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Operator slug grammar at creation; skills out of the author namespace

<!-- sq:subtask:ST1:body -->
ADR-979 A1 and A2. The rule sits at the roster creation seam that already holds the role rule (`_check_roster_slug`, `_services/_base.py`), so every operator creation path inherits it.

## Acceptance

- Operator creation refuses any slug outside `op-[a-z0-9][a-z0-9-]*`, explicit or derived, with exit 1 and nothing written, on `sq operator add --slug` and the importer's operator `create`.
- The message names the rule and, when one exists, the compliant form: `operator slug 'Anna' must start with 'op-' and be lowercase letters, digits and hyphens (e.g. 'op-anna')`.
- A typed slug is never lowercased or prefixed: the stored slug is the one typed and accepted.
- The derived default (`operator_slug`, `_util.py`) is accepted for an ASCII, an accented, a non-Latin and a punctuation-only name (the last two give `op-untitled` or a compliant form).
- `agent_registered` builds its set from roles and operators only (`registered_slugs`, `_services/_validators.py`): an item whose author or assignee names a skill slug is now reported.
- Skill slugs stay unique among skills and in the grammar, and are otherwise unconstrained: the bundled `squads` skill still loads and `sq skill squads show` works.

## Tests (one table per behaviour)

- Creation table, run through both `operator add --slug` and the importer: `squads`, `operator`, `qa` with role `qa` live, `Bad Slug`, `OP-UP`, `op-`, `op--x`, `Op-anna`, `op-anna ` (trailing space), `op_anna` refused; `op-anna`, `op-a1`, `op-1`, `op-ann-lee` and the derived default accepted. Each refusal asserts an unchanged squad.
- `agent_registered` table: author or assignee naming a role, a developer role, an operator, a retired role, a retired operator (pass); a skill slug, an unknown slug (reported).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-16T11:25:07Z] `python-dev` Elias Python:
  - Done. Falsified with 5 mutants, all red: operator rule off (24 red), importer derived slug back to slugify (1), registered set back to every roster type (2), skill author exemption off (1), suggestion removed (25). Importer-created operators now derive op-<first name> like operator add (they derived slugify(title) before, which the rule would refuse).
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Default roster_slug_valid check

<!-- sq:subtask:ST2:body -->
ADR-979 A3. A new squad-global `sq check` rule, `roster_slug_valid`, on by default at `error`.

## Acceptance

- Reports each role and operator, live or retired, whose slug is outside its A1 grammar (role: not `operator`/`squads`, not starting with `op-`; operator: `op-[a-z0-9][a-z0-9-]*`), or that shares its slug with another entry of the author namespace (roles and operators; skills do not count).
- One issue per entry, naming the item, the slug, the rule broken and, for a shared slug, the other holders: `OP-12: operator slug 'qa' does not start with 'op-'; it is also held by ROLE-5`.
- The message carries the remedy, addressing by id: `sq operator <id> rm --purge`, then `sq operator add` under the same name.
- Report-only: it gates no write, like `default_designation_duplicated`. A test proves an unrelated write still succeeds on a squad holding a breaching entry.
- Squad-global like `default_designation_duplicated`: always on at a fixed `error` level, not selectable or severity-overridable, and absent from the bundled spec (ADR-979 A3 note).
- `sq check` on this repository's squad stays clean.

## Tests (one table per behaviour)

- Breach table, entries written by hand into a scratch squad's files (creation can no longer produce them): operator `squads`, `operator`, `qa` beside live role `qa`, `Bad Slug`, `OP-UP`, `op-`; two operators sharing `op-ann` (both reported, each naming the other); a retired breaching operator; a role holding `op-dev`; a skill holding `squads` (not reported); a compliant roster (no issue).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-16T11:27:56Z] `python-dev` Elias Python:
  - Done. roster_slug_valid is a squad-global rule in the same registry as default_designation_duplicated, reports at error, never gates. Falsified with 6 mutants, all red: shared holders dropped (2 red), role grammar off (3), operator grammar off (7), retired entries skipped (1), skills counted (2), remedy dropped (11). The squad-global rules are not selectable or severity-overridable in this codebase (fixed at error, absent from the bundled workflow spec), so I matched default_designation_duplicated rather than inventing a selection path.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — 0.16 migration refuses a role or operator in breach

<!-- sq:subtask:ST3:body -->
ADR-979 A4. The 0.16 planning pass (`_migrations/_v0_15_to_v0_16.py`) checks the roster before any header resolves, and a breach refuses the run. This replaces today's report line, "An operator whose slug does not start with `op-` is listed in the run's report; nothing is refused".

## Acceptance

- Every role and operator item, live and retired, is checked against A1 and A2 (the same predicate as `roster_slug_valid`, shared, not duplicated) before any header is resolved.
- A breach is one file-level line per entry, in the same report as the header failures, counted toward the same exit 1 with nothing written: `operators/OP-000012-qa.md: operator slug 'qa' does not start with 'op-'; also held by ROLE-5`.
- Each entry is reported once; the headers that name it are not also listed.
- A role in breach of decision 2 or the grammar is reported the same way.
- `_HEADER_MANUAL` drops the "nothing is refused" paragraph and gives the remedy, run with the release the squad is stamped for: `sq operator <id> rm --purge`, then `sq operator add "<the same full name>"`, then `sq migrate up` again; why the purge is required (a plain `rm` keeps the file and the reconcile re-indexes it); `update --assignee` for open items assigned to the old slug; an item's `author` keeps the old slug, which `agent_registered` names. For a role: rename the project role file to a compliant slug, activate it again, purge the old one.
- A6's title-then-operator-slug resolution keeps working beside the new check.

## Tests (one table per behaviour)

- Refusal table: each breach kind (reserved slug, live role's slug, out of grammar, shared operator slug, retired breaching entry, role holding `op-`), alone and beside a header failure. Every file in the squad hashes identically before and after, and the error lists each breach once.
- A compliant squad migrates as today.

## Dry run

On a copy of this repository's squad under the scratchpad, run the dev tree's `sq migrate up`: report the number of breaching operators and roles (expected 0; `op-pierre` conforms) in the handoff comment. Never run it on the live squad.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-16T11:36:37Z] `python-dev` Elias Python:
  - Done. The 0.16 planning pass now checks every role and operator (live and retired) with the shared predicate (roster_slug_breaches in _models/_participants.py, also behind roster_slug_valid) before headers resolve. Breach lines join the header failures in the same report and count; the old report-only line is gone. Falsified with 7 mutants, all red: breach lines dropped (23 red), header failures hidden when a breach exists (11), breaches listed twice (23), retired entries skipped (4), shared holders off (6), role grammar off (9), MANUAL remedy wording changed (1).
    Dry run on a copy of this repo's squad (squads/, .squads.toml, .claude/, CLAUDE.md, git-inited, dev tree, exit 0): 0 breaching operators and 0 breaching roles. 4067 comment headers rewritten in 897 files. git diff on the copy: 897 .md files changed, 4067 lines removed and 4067 added, every one of them a comment header line (old grammar out, slug grammar in), plus the expected .squads.toml stamp, .squads.json and .reflog.jsonl. The dev-tree sq check on the migrated copy reports no issues, roster_slug_valid included.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Refuse --as squads in every comment writer

<!-- sq:subtask:ST4:body -->
ADR-979 A5. `squads` resolves for no actor, whatever the roster holds, so system entries stay immutable by rule.

## Acceptance

- `--as squads` is refused with exit 1 and nothing written by every comment writer: item `comment`, sub-entity `comment`, `sq board post`, any roster-entity comment verb, and the importer's `as` (event-level and the `--as` default). The refusal holds even when a roster entry holds `squads` (a hand-edited file).
- Rename and retype still write `squads` system entries internally.
- `--as operator` keeps resolving to the anonymous author before the roster is read, even when an entry holds `operator`.
- The author match stays slug equality (ADR-1013 §9); no stronger match is added.

## Tests (one table per behaviour)

- Writer table: each writer above × (`squads` with no entry holding it, `squads` held by a hand-written operator) refused; × a live role and an `op-` operator accepted. Each refusal asserts the item file unchanged.
- `operator` table: with and without an entry holding `operator`, the header names the anonymous author.
- A retype still writes a `squads` header.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-16T11:30:52Z] `python-dev` Elias Python:
  - Done. --as squads is refused by item comment, sub-entity comment and board post at the CLI (resolve_actor_or_raise, before the roster is read) and in the service (comment core, board_post), and by the importer for both an event-level as and the --as default, with or without a hand-written operator holding the slug. There is no roster-entity comment verb in this build (role/operator/skill have show, rm, status and the like only), so that row of the table does not exist. Falsified with 5 mutants, all red: CLI refusal off (9 red), service comment off (2), board off (2), CLI and service together (15), case/@ normalisation off (6). The importer's own simulate-time refusal is backed by the comment core, so removing only it stays green by design. operator still resolves anonymously with or without an entry holding it; retype still writes a squads header.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Docs and CHANGELOG for the operator slug rule

<!-- sq:subtask:ST5:body -->
The adopter-facing text that states the old behaviour, rewritten to the A1–A5 rules once the code lands (REV-1031 F8 lists the migration passages). Describe the tool, not how it was built.

## Acceptance

- `docs/stability.md` Tier 1, beside the header grammar: drop "Operator slugs are not checked against these rules" and the paragraph after it; state that an operator slug is `op-[a-z0-9][a-z0-9-]*`, refused otherwise by `sq operator add --slug` and the importer, that `--as squads` is refused, and that a role or operator in breach does not migrate. Correct "the 0.16 migration neither reports nor refuses it" for a role in breach.
- `docs/migration.md`, "Upgrading to 0.16": replace "The report also names any operator whose slug does not start with `op-`; nothing is refused for it" with the refusal and the purge-and-add remedy; re-check the operator matching rule against A6 (title first, then an operator's slug) and the other two REV-1031 F8 passages.
- The 0.16 CHANGELOG entry: the reserved-slug bullet no longer says operator slugs are unchecked or that the migration ignores a role in breach; a bullet covers the operator slug rule, `roster_slug_valid`, `--as squads`, and the migration refusal.
- The `sq operator add --help` text names the slug rule if the help does not already.
- Text matches the built messages and the final `_HEADER_MANUAL` word for word where it quotes them; every example run against the dev tree.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-10-16T12:34:05Z] `tech-writer` Theo Writer:
  - Done, uncommitted. stability.md Tier 1 (Comment headers): one author namespace with the operator and role grammars, the operator refusal, the role refusal, --as squads refused, roster_slug_valid (squad-global, fixed error, not selectable), and the migration refusal. The old "operator slugs are not checked" and "migration neither reports nor refuses" text is gone. Tier 2: role/skill verb slugs refused.
  - migration.md 0.16: the "nothing is refused" line is replaced; new sections "A role or operator whose slug breaks the rules" and "Every operator carries a stored slug and full name"; run report example updated. roles.md and README carry the operator grammar, the role verb slugs, skill slugs (never add, cannot author), and a skill-slug note in overrides.md Validators. CHANGELOG [0.16.0]: the reserved-slug bullet is rewritten, and there are new bullets for verb slugs, roster_slug_valid, --as squads, the migration refusal and fill-in, and importer-derived op- slugs.
  - REV-1031 F8 re-check: the duplicate-name remedy (full_name under extra) still holds, because the 0.16 fill-in keeps extra.full_name. The operator matching rule ("full name, or slug when it has none") matches the built _read_roster and the MANUAL. It does not match A6 as worded (title first, then any operator slug when no title matches). @architect that is a code/ADR gap, not a docs one. The third passage is replaced.
  - Every quoted message was driven with the dev build in scratch squads, including a 0.15 squad from the released sq: operator/role/verb refusals, --as squads on comment, board and import, roster_slug_valid output, the migration refusal and the fill-in report. sq operator add --help still does not state the slug grammar (src, not touched).
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T11:36:38Z] `python-dev` Elias Python:
  - Handoff to @tech-writer for ST5. Code for ST1 to ST4 is in the working tree, uncommitted. Nothing under docs/ or README was touched.
    
    Final MANUAL text (the new section is appended to the header section; the "nothing is refused" paragraph is deleted):
    
    
    User-visible messages that changed or are new:
    - Operator creation refusal (sq operator add --slug, importer operator create): operator slug 'Anna' must start with 'op-' and be lowercase letters, digits and hyphens (e.g. 'op-anna'). The "(e.g. ...)" part is omitted when nothing of the slug survives (for example 'op-'). It replaces "cannot create this operator as 'Bad Slug': a slug is lowercase letters, digits and hyphens".
    - Role creation refusals are unchanged.
    - An imported operator with no slug now derives op-<first name> (file OP-n-op-anna.md), like sq operator add. It used to derive the slugified full name, which the rule refuses. The importer still stores no extra.slug for it.
    - New sq check error, roster_slug_valid, one per entry (item column is the entry id): operator slug 'qa' does not start with 'op-'; it is also held by ROLE-5 - remedy: sq operator OP-000012 rm --purge, then sq operator add "Quentin Adams". Other forms: operator slug 'op-' is not 'op-' followed by lowercase letters, digits and hyphens; role slug 'op-dev' is reserved for operators (the 'op-' prefix); role slug 'squads' is reserved for system entries; role slug 'x' is not lowercase letters, digits and hyphens; role/operator slug 'x' is not unique; it is also held by OP-3. A role's remedy reads: rename the project role file to a compliant slug, run sq role activate <slug>, then sq role <id> rm --purge.
    - sq check agent_registered (warn): a skill slug as author or assignee is now reported ("author 'pairing' is not a registered agent or operator"). A skill item's own author is exempt.
    - Migration refusal line (one per entry, same report and count as header failures): operators/OP-000012-qa.md: operator slug 'qa' does not start with 'op-'; also held by ROLE-5. Other fragments: is not 'op-' followed by lowercase letters, digits and hyphens; is reserved for operators (the 'op-' prefix); is reserved for system entries; is not lowercase letters, digits and hyphens; is not unique.
    - --as squads (item comment, sub-entity comment, board post, importer event-level as and --as default): cannot comment as 'squads': that slug is reserved for system entries. The importer refuses Squads or @squads on the slug grammar instead ("cannot write a comment as ..."). The CLI lowercases and strips a leading @ before comparing.
    - sq operator add --help for --slug still reads "Override the derived `op-<first>` slug." and does not state the grammar; that string is in src/squads/_cli/_operator.py if you want it changed.
    
    Things to know for the docs:
    - roster_slug_valid is a squad-global rule like default_designation_duplicated: always on, fixed at error, report-only. It is not selectable or severity-overridable and the bundled workflow spec does not list the squad-global rules, so the AC line "selectable and severity-overridable" does not apply in this build.
    - There is no comment verb on role, operator or skill entries, so "--as squads in every roster-entity comment verb" has no surface.
    - sq operator add --slug list (a slug equal to a group verb) is now refused, so operators are always addressable by slug.
- [2026-10-16T11:36:49Z] `python-dev` Elias Python:
  - Final MANUAL text for ST5 (the section appended to the header section in src/squads/_migrations/_v0_15_to_v0_16.py; this is the last part of the step's MANUAL, read it with sq migrate chlog v0.15.0..v0.16.0). The earlier line "An operator whose slug does not start with op- is listed in the run's report; nothing is refused for it." is deleted.
    
    ### A role or operator whose slug breaks the rules refuses the run
    
    Before it resolves any header, the step checks every role and operator, retired ones included.
    An operator's slug is `op-` followed by lowercase letters, digits and hyphens. A role's slug is
    lowercase letters, digits and hyphens, and is neither `operator` nor `squads` nor anything that
    starts with `op-`. No slug is held by two entries. An entry that breaks a rule refuses the run
    like an unresolvable header: nothing is written, the schema stamp is unchanged and the command
    exits 1, with one line for the entry, naming its file, its slug, the rule and the other holders:
    
        operators/OP-000012-qa.md: operator slug 'qa' does not start with 'op-'; also held by ROLE-5
    
    It is refused, and not only reported, because this is the last point where the slug can change.
    Once the headers carry it no later step rewrites them, so a reserved slug would turn comments
    into system entries, `operator` would make them anonymous, and a slug shared with a role would
    make them editable by whoever holds it.
    
    What to do for each, with the release the squad is stamped for, before running `sq migrate up`
    again:
    
    - **An operator.** Run `sq operator <id> rm --purge`, using the ID in the line, then
      `sq operator add "<the same full name>"`, which takes `op-` and the first name unless you pass
      a compliant `--slug`. The purge is required: a plain `rm` drops the entry from the index but
      keeps its file, and the next run reads that file again. The comments that named the operator
      then resolve to the new slug. Reassign the open items assigned to the old slug with
      `sq <type> <n> update --assignee <new slug>`. An item's `author` keeps the old slug, and
      `sq check` reports it as not registered.
    - **A role.** Give the role's project definition a compliant slug (the file under
      `<squad folder>/.overrides/roles/`, renamed, and its `slug` line with it), run
      `sq role activate <new slug>`, then `sq role <id> rm --purge` for the old entry.
    - **A slug held by two entries.** Both entries are listed, each naming the other. Replace the one
      that breaks a rule above, or the one you can spare, the same way.
- [2026-10-16T11:50:21Z] `reviewer` Paul Reviewer:
  - Reviewed in REV-1055: ChangesRequested. One high (importer operators escape the duplicate guard and roster_slug_valid: three live op-ann, sq check clean), one medium (shared-slug remedy fails as printed), five low. @python-dev
- [2026-10-16T11:53:32Z] `architect` Robert Architect:
  - - @tech-lead please correct ST2's acceptance: `roster_slug_valid` is not "selectable and severity-overridable like the other default rules". It is a squad-global rule, always on at a fixed `error`, as built and now recorded in ADR-979's dated note under A3 (REV-1055 F5). ST5 must not document a switch that does not exist.
- [2026-10-16T12:03:13Z] `python-dev` Elias Python:
  - REV-1055 F1, F2, F3, F4, F6 and ADR-979 A7 (F7) are fixed; F5 and F7 dispositions stay with the architect as noted. Changed user-visible messages for ST5: operator refusal now reads 'operator slug 'op-' must be 'op-' followed by lowercase letters, digits and hyphens (e.g. ...)' when the prefix is present; system-slug refusal is 'cannot act as 'squads': that slug is reserved for system entries'; new creation refusal 'role slug 'list' is a verb of `sq role` and cannot be addressed by slug; pick another slug' (and the skill form); the roster_slug_valid remedies now carry --slug, a replace-the-other-holder form and a retire-again step, and it reports group-verb slugs. Imported operators now store slug and full_name and a duplicate slug is refused.
- [2026-10-16T12:12:17Z] `architect` Robert Architect:
  - Reminder @tech-lead: ST2 acceptance still says "Selectable and severity-overridable like the other default rules; the bundled spec lists it." That is false as built: roster_slug_valid is squad-global, fixed at error, not in the bundled spec (ADR-979 A3 note, REV-1055 F5). Please correct it before ST5 documents from it.
- [2026-10-16T12:13:21Z] `tech-lead` Olivia Lead:
  - @architect ST2 acceptance corrected: roster_slug_valid is squad-global, always on at a fixed error level, not selectable and not in the bundled spec (ADR-979 A3 note).
- [2026-10-16T12:16:13Z] `python-dev` Elias Python:
  - Exact new text for the writer (step 0.16 now has two contributions).
    
    Step summary clause, appended after the header clause: Every operator carries a stored slug and full name.
    
    Run report line (always printed, after the header line): N operator(s) given a stored slug or full name
    
    MANUAL section, appended after the roster-slug section:
    
    ### Every operator carries a stored slug and full name
    
    An operator that an earlier release's importer created has neither a `slug` nor a `full_name`
    under `extra:` in its file, so the rest of sq could not tell it was an operator. `sq migrate up`
    writes both: the slug is the one the operator already answers to, and the full name is its title.
    Only the frontmatter of those operators changes. The run reports how many it filled in; an
    operator that already had both is not touched.
    
    
    Also changed: sq check remedy for a slug held by one entry that breaks a rule reads 'replace OP-98, which breaks a rule of its own' (several: 'which break a rule of their own').
- [2026-10-16T12:35:06Z] `manager` Catherine Manager:
  - Moved to Done under the manager's delegation: ST1–ST5 Done, REV-1055 Approved, full suite 10,643 passed, docs committed.
<!-- sq:discussion:end -->
