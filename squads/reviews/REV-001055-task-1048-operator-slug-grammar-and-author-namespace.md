---
id: REV-1055
sequence_id: 1055
type: review
title: 'TASK-1048: operator slug grammar and author namespace'
status: Approved
author: reviewer
assignee: reviewer
refs:
- TASK-1048
description: 'Review of ADR-979 A1-A5 as built: slug grammar, roster_slug_valid, migration
  refusal, --as squads'
subentities:
- local_id: F1
  title: Importer operators escape the duplicate guard and roster_slug_valid
  status: Verified
  severity: high
- local_id: F2
  title: Shared-slug remedy fails as printed
  status: Verified
  severity: medium
- local_id: F3
  title: Skill author exemption hides any unregistered skill author
  status: Verified
  severity: low
- local_id: F4
  title: Operator refusal message false for op- shapes
  status: Verified
  severity: low
- local_id: F5
  title: roster_slug_valid is not selectable as A3 and ST2 state
  status: Verified
  severity: low
- local_id: F6
  title: Migration refusal test hashes only md and toml
  status: Verified
  severity: low
- local_id: F7
  title: Role slug equal to a sq role verb is unaddressable
  status: Verified
  severity: low
- local_id: F8
  title: A7 says verbs are read from the CLI; they are pinned constants
  status: Fixed
  severity: low
- local_id: F9
  title: Shared-slug remedy says 'which break' for a single culprit
  status: Fixed
  severity: low
- local_id: F10
  title: Operator with no stored slug is not a participant
  status: Fixed
  severity: low
created_at: '2026-10-16T11:49:46Z'
updated_at: '2026-10-16T12:19:56Z'
---
<!-- sq:body -->
Scope: TASK-1048 ST1 to ST4, uncommitted in the working tree (`git diff -- src tests` plus six untracked test files), against ADR-979 amendments A1 to A5.

What was driven (dev build, `uv run --all-extras sq -C <scratch>`, one git-inited scratch squad per scenario under the session scratchpad; the released 0.15.0 tool built the pre-migration squad):

- `sq operator add --slug` over 20 shapes: case (`Op-anna`, `OP-UP`), unicode (`op-é`, full-width `op-ａ`, roman numeral `op-ⅰ`), `op-`, `op--x`, leading and trailing spaces, an embedded newline, `op_anna`, `op-anna.x`, `squads`, `operator`, `qa`, `list`. Every refusal exits 1 and writes nothing. Accepted: `op-1`, `op-a1`, `op-list`, and `op-anna-` (a trailing hyphen is inside the A1 grammar).
- Importer operator `create` with an explicit slug (same refusals, nothing written) and with derived slugs (`!!!` and `Ζωή Ελ` both give `op-untitled`, `Élodie Roux` gives `op-elodie`).
- `sq dev add --tech op`, `Op`, `op x`: refused as `op-dev` / `op-x-dev`. `role activate` through `.overrides/roles/<slug>.toml` for `squads`, `operator`, `op-boss`, `Boss`: refused. `list`: accepted (F7).
- `--as squads`, `SQUADS`, `@squads`, `@SQUADS`, `Squads` on item comment, finding comment, board post, the importer's event `as` and its `--as` default, with a hand-written operator holding `squads`: all exit 1, tree unchanged. `--as operator` with no entry writes the anonymous header.
- 0.16 migration on a 0.15 squad holding operators `qa`, `squads`, `operator`, `Bad Slug`, `OP-UP`, a retired `oldie`, two `op-ann` (one of them importer-created with no `extra.slug`) and an importer-created `imp-orted`: exit 1, 10 lines, each entry once, ROLE-5 named as the other holder of `qa`. A sha256 of every file outside `.git` was identical before and after. Running the MANUAL remedy with 0.15.0 then migrating again: exit 0, 4 headers rewritten, `sq check` clean.
- Targeted tests: the nine touched test files, `-n0`: 252 passed.

The `monkeypatch.context()` question: the three fixtures that use it depend on `svc`, so `project` has already done its chdir, and leaving the context undoes only the `_check_roster_slug` patch. No test in the diff calls `monkeypatch.undo()`, `os.chdir` or `Path.cwd`. No test in the diff resolves the repository's own squad.

The A1 grammar, the `--as squads` refusal and the migration's atomicity hold on every shape tried. The defect is in what the check and the duplicate guard can see: they key on `extra.slug`, which importer-created operators do not store (F1). The remedy text has gaps (F2).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1055 add-finding "…" --severity medium`; track with `sq review 1055 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Importer operators escape the duplicate guard and roster_slug_valid

<!-- sq:finding:F1:body -->
**Driven.** Two scratch squads, dev build:

1. `sq operator add "Ann Lee"` gives `op-ann` (OP-21). Then `sq import` of `{"op":"create","type":"operator","title":"Ann Smith"}` exits 0 and creates OP-22, also `op-ann`.
2. In reverse order: one import file creating "Ann Smith" and "Ann Jones", then `sq operator add "Ann Lee"`. All three succeed, and `sq operator list` shows three live `op-ann`.

`sq check` reports `no issues` in both squads. The same happens with `op-untitled` for any two imported names that slugify to nothing (driven: `!!!` and `Ζωή Ελ` in one import).

**Mechanism (read).** The importer's operator create goes through `_create_model` / `_create_core` and stores no `extra.slug` and no `full_name`. Three readers key on `extra.slug` only:

- `roster_slug_breaches` (`_models/_participants.py`): `if slug := it.extra.get(X.SLUG)`, so the entry is skipped.
- `roster_item` (`_services/_base.py`): no fallback for operators, so `_refuse_duplicate_slug` in `add_operator` does not see the imported holder.
- The importer never calls `_refuse_duplicate_slug` at all.

Meanwhile `resolve_slug_or_raise` reads `operators()`, which falls back to `it.slug`, so `--as op-ann` resolves for any of the holders.

**Why this is new.** Before this change the importer derived `slugify(title)` (`ann-smith`), so a collision needed two identical full names. It now derives `op-<first name>` (ST1), which makes collisions routine, and the check meant to catch merged duplicates (A3) cannot see the shape that produces them.

**The check and the migration disagree on the same corpus.** The 0.16 migration's `_read_roster` falls back to the frontmatter `slug` and the file name, so it did report the importer-created `op-ann` (driven: `OP-000029-op-ann.md ... not unique; also held by OP-26`). The predicate is shared, but its input is not.

**Tests miss it** because every breach fixture in `test_check_reports_a_roster_slug_that_breaks_its_grammar.py` builds entries with `extra={X.SLUG: …}`. None builds the importer shape.

**Fix direction.** Either the importer's operator create stores `extra.slug` and `full_name` the way `add_operator` does, and is refused on a duplicate, or `roster_slug_breaches` and `roster_item` read `extra.get(X.SLUG, it.slug)` for operators, the way the migration and `operators()` do. Ideally both. Add an importer-shaped row to the breach and duplicate tables.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T12:03:01Z] Elias Python:
  - Fixed. Every operator path now goes through _create_model: it stores slug and full_name and refuses a duplicate slug (importer, batch and operator add alike). roster_item and roster_slug_breaches use the stored slug or the entry's own slug, as operators() and the migration do. Tests build importer-shaped and 0.15-shaped entries (no stored slug), including op-untitled twice. Falsified 4 mutants, all red: duplicate guard off (6 red), breach fallback off (1), roster_item fallback off (1), importer storing slug/full_name off (1).
- [2026-10-16T12:10:20Z] Paul Reviewer:
  - Verified 2026-10-16: add-then-import and import-then-add of a shared first name are both refused with nothing written; two imported op-untitled refused; imported operators now store slug and full_name; legacy-shaped entries (no stored slug) are reported by sq check. On one 0.15 roster with 8 breaches, the migration refusal and the dev sq check name the same 8 entries (the check adds only the A7 verb role, which the migration must not refuse).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Shared-slug remedy fails as printed

<!-- sq:finding:F2:body -->
**Driven.** I gave an imported operator `extra.slug: op-ann` beside OP-21 `op-ann` and ran `sq repair`. `sq check` then reports both, with the remedy `sq operator OP-21 rm --purge, then sq operator add "Ann Lee"`. Following it word for word, the purge succeeds and the add fails: `an operator with slug 'op-ann' already exists`. `operator add` re-derives `op-` plus the first name, which is the shared slug. The entry the user meant to keep is now gone, and the printed remedy does not bring it back. It needs a `--slug`.

The 0.16 MANUAL text does say "unless you pass a compliant `--slug`", but the `sq check` remedy does not. Driven on the migration side too: Ann Two's purge-and-add with 0.15.0 was refused for the same reason.

**Two related gaps in the same remedy text (read and driven):**

- For a role that is only the other holder of a shared slug, such as bundled ROLE-5 `qa` beside operator `qa`, the check prints the role remedy: "rename the project role file to a compliant slug, run sq role activate…". The role breaks no rule of its own and has no project file. The entry to replace is the operator. The migration's MANUAL handles this ("replace the one that breaks a rule"), but the check message does not.
- For a retired breaching operator, purge-and-add re-creates it Active. Driven: Old Timer, Archived, came back Active as `op-old`. Neither the check remedy nor the MANUAL says to set its status back.

**Fix direction.**

- For a shared slug, the remedy carries `--slug op-<something>`, or it says that a compliant `--slug` is needed when the derived slug is the one that is shared.
- For the holder that breaks no rule of its own, the remedy points at the other holder.
- For a retired entry, add the status step.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T12:03:03Z] Elias Python:
  - Fixed. The check remedy re-adds with --slug <compliant slug>; an entry that breaks no rule of its own is told to replace the holders that do; a retired operator gets a final status step to retire it again. Falsified 3 mutants: --slug dropped (1 red), pointing at the culprit off (1), status step off (1).
- [2026-10-16T12:10:22Z] Paul Reviewer:
  - Verified: the remedy carries --slug <compliant slug>; the holder that breaks no rule points at the culprit; a retired entry gets the status step. Followed word for word on a scratch squad, check ends clean. Wording nit filed as F9.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Skill author exemption hides any unregistered skill author

<!-- sq:finding:F3:body -->
**Driven.** I imported `{"op":"create","type":"skill","title":"Pairing","as":"qa"}` and a task authored by `qa`, then ran `sq role qa rm --purge`. `sq check` warns only for the task (`author 'qa' is not a registered agent or operator`). SKILL-21's stored `author: qa` is not reported.

**Mechanism (read).** `_agent_registered` skips the `author` attribute on every skill item:

```python
if attr == "author" and ctx.item.type == ROSTER_SKILL:
    continue
```

ST1 and the handoff describe the exemption as "a skill item's own author", meaning a skill authored by its own slug, as `add_skill` writes it. The code exempts any author on a skill. Before this change `registered_slugs` included skill slugs, so a self-authored skill passed, and an unregistered author on a skill was reported. The change hides that case.

**Fix direction.** Exempt only `ctx.item.author == ctx.item.extra.get(X.SLUG, ctx.item.slug)` on a skill. Add a row to the `agent_registered` table with a skill authored by an unregistered slug.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T12:03:05Z] Elias Python:
  - Fixed. The skill author exemption applies only when the author is the skill's own slug; a table row covers a skill authored by an unregistered slug. Falsified 1 mutant: exemption widened back (1 red).
- [2026-10-16T12:10:23Z] Paul Reviewer:
  - Verified on scratch d: SKILL-21 authored by purged qa is reported again; self-authored bundled skills are not.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Operator refusal message false for op- shapes

<!-- sq:finding:F4:body -->
**Driven.**

- `sq operator add "Zed Q" --slug op-` gives `operator slug 'op-' must start with 'op-' and be lowercase letters, digits and hyphens`. The slug does start with `op-`, so the first clause is false for every shape that already has the prefix: `op-`, `op--x`, `op-é`, `op-ａ`, `op-anna.x`. `operator_slug_problem` already distinguishes the two cases (`does not start with` / `is not 'op-' followed by …`), and the check and the migration use that distinction. Creation throws it away for one fixed sentence.
- `sq board post --as squads` gives `cannot comment as 'squads'`. A board notice is not a comment. One shared message for every writer is fine, but it could say "act as" or "write as".

Both strings are new. ST5 will quote them in the docs, so settle them first.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T12:03:08Z] Elias Python:
  - Fixed. The operator refusal says 'must be op- followed by lowercase letters, digits and hyphens' when the prefix is present and 'must start with op- and be ...' when it is not; the system-slug refusal reads 'cannot act as ...'. Falsified 2 mutants: one message for both (6 red), old board wording (2 red, a test now pins it).
- [2026-10-16T12:10:24Z] Paul Reviewer:
  - Verified: op-, op--x, op-é now read "must be 'op-' followed by …"; unprefixed shapes keep "must start with 'op-'"; board post says "cannot act as".
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — roster_slug_valid is not selectable as A3 and ST2 state

<!-- sq:finding:F5:body -->
ADR-979 A3 says `roster_slug_valid` is "on by default at `error`". ST2's acceptance says "selectable and severity-overridable like the other default rules; the bundled spec lists it".

The rule is wired as a squad-global rule (`SQUAD_GLOBAL_CATALOG`). I read the engine: squad-global rules run unconditionally at a fixed `error` and are not part of any type's selection. So the implementation matches its precedent, `default_designation_duplicated`, and the developer flagged the departure in the ST2 handoff.

This is not a code defect. But the ADR text and the subtask acceptance now promise a switch that does not exist, and ST5 will document from them.

**Disposition needed (architect / tech lead).** Either add a dated note to A3 saying it is always on, like the other squad-global rules, and amend ST2's acceptance, or make squad-global rules selectable (a larger change, out of this task's scope). My recommendation: the note. An adopter has no legitimate reason to switch off an identity check.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T11:53:33Z] Robert Architect:
  - - Fixed by the dated note under ADR-979 A3 (2026-10-16): `roster_slug_valid` is squad-global, always on at a fixed `error`, not selectable. ST2's acceptance correction is asked of @tech-lead on TASK-1048.
- [2026-10-16T12:10:25Z] Paul Reviewer:
  - Verified: the dated note under A3 is in ADR-979. The ST2 acceptance line ("selectable and severity-overridable") is still in TASK-1048 pending the tech lead.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Migration refusal test hashes only md and toml

<!-- sq:finding:F6:body -->
ST3's acceptance says "Every file in the squad hashes identically before and after". `_hash` in `test_the_header_migration_refuses_a_roster_slug_in_breach.py` keeps only `.md` files and `.squads.toml`, so a refusal that wrote `.squads.json` or `.reflog.jsonl` would pass.

Driven: the real refusal leaves every file outside `.git` byte-identical (sha256 diff of the whole tree, 0.15 squad with 10 breaches). The behaviour is right and only the test is narrower than its acceptance.

`tests/_helpers.py::squad_tree`, added in the same change, already hashes every file outside `.git`. Use it here.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T12:03:10Z] Elias Python:
  - Fixed. The migration refusal test hashes the whole tree with squad_tree. The run rebuilds .squads.json from the files before its first step, so the test asserts every other file identical to the original and the whole tree stable across a second refused run. Falsification not applicable beyond the existing 7 mutants of that table, still red.
- [2026-10-16T12:10:26Z] Paul Reviewer:
  - Verified by reading: the refusal test now hashes with squad_tree; a full-tree sha256 on a driven 0.15 refusal is identical apart from the empty lock file.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Role slug equal to a sq role verb is unaddressable

<!-- sq:finding:F7:body -->
**Driven.** I added `.overrides/roles/list.toml` and ran `sq role activate list`. It exits 0 (ROLE-21). Then `sq role list show` fails with `Got unexpected extra argument(s) (show)`, because the group verb wins. The generated agent pointer tells an agent to run `sq role <slug> show` to load its definition, so for this role that instruction cannot work.

The change closed this for operators (`--slug list` is refused because it lacks `op-`, and the old test pinning `list` as unaddressable was rewritten). The role grammar in A1 does not exclude `sq role` verbs (`list`, `catalog`, `activate`, …).

This is outside TASK-1048 and was not introduced by it. I file it so that it gets a disposition: an ADR-979 follow-up (reserve the `sq role` verbs for roles) or WontFix with a reason. The same question applies to skill slugs and `sq skill` verbs.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-16T11:53:34Z] Robert Architect:
  - - Proposed as ADR-979 A7 (2026-10-16): roles and skills refuse a verb of their `sq` group as a slug, at activation or creation, and `roster_slug_valid` reports one already held. Stays Open until op-pierre confirms A7.
- [2026-10-16T12:03:12Z] Elias Python:
  - Fixed (ADR-979 A7). The roster creation seam refuses a role slug equal to a sq role group verb (activate, catalog, list) and a skill slug equal to the sq skill verb (add), on the project role file, catalog entry, importer and skill add paths, writing nothing. The verb sets are constants pinned to the live registered commands by a new meta test (the models sit below the CLI, as with the reserved top-level verbs). roster_slug_valid reports an existing holder with a remedy; the migration does not refuse (a test proves it). Falsified 5 mutants, all red: seam off (11), skill group dropped (3), verb sets crossed (3), check reporting off (4), migration made to refuse (1).
- [2026-10-16T12:10:27Z] Paul Reviewer:
  - Verified: list, catalog, activate are refused on the per-slug override, the roles.toml catalog document, the importer (role and skill, explicit and derived), and skill add (add, Add), with nothing written. Leaf verbs stay addressable (role show via sq role show show, skill link-role). Dev roles unaffected (list-dev). The meta test goes red on a dropped or an extra verb (falsified in-process). Mechanism vs ADR wording filed as F8.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — A7 says verbs are read from the CLI; they are pinned constants

<!-- sq:finding:F8:body -->
ADR-979 A7 says: "The verb set is read from the CLI group's registered commands, not a hand-kept list, so a verb added later is covered without an edit here". The amendment summary repeats it twice ("read from the registered commands").

What was built is the opposite mechanism: hand-kept constants, `ROLE_GROUP_VERBS = {"activate", "catalog", "list"}` and `SKILL_GROUP_VERBS = {"add"}` in `_models/_participants.py`. The developer gives the reason (the models sit below the CLI and cannot import the Typer app). `tests/meta/test_roster_group_verbs_match_the_live_command_table.py` pins the constants to the live command table by equality.

I falsified the meta test in-process: a dropped verb goes red, and an extra verb goes red. So a verb added later fails CI until someone edits the constant.

The guard is sound. The ADR text describes a mechanism the code does not have, and ST5 will document from it.

**Disposition (architect).** Add a dated note to A7: constants below the CLI, pinned to the registered commands by a meta test, so a new verb fails CI rather than being covered silently. The alternative is to read the verbs at runtime, which would need a layering change.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-16T12:12:18Z] Robert Architect:
  - Fixed in ADR-979: dated note (2026-10-16) under A7 records that the verb set is held as ROLE_GROUP_VERBS / SKILL_GROUP_VERBS below the CLI (same arrangement as RESERVED_CLI_VERBS), pinned by equality to the live command table in tests/meta/test_roster_group_verbs_match_the_live_command_table.py, so drift in either direction fails CI; no released build can differ from a runtime read. The obligations line now says "held in step with the registered commands (A7 note)".
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Shared-slug remedy says 'which break' for a single culprit

<!-- sq:finding:F9:body -->
Driven (scratch squad, bundled role `qa` beside a hand-written operator `qa`): `sq check` prints

`error ROLE-5: role slug 'qa' is not unique; it is also held by OP-98 — remedy: replace OP-98, which break a rule of their own`

With one culprit, the verb should be "breaks" and the pronoun "its own". The text is built in `_slug_breach_remedy` (`_services/_validators.py`) from `', '.join(culprits)` with a fixed plural. ST5 will quote this message, so fix the wording first: agree with the count, or use a form that reads correctly for both.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-16T12:16:09Z] Elias Python:
  - Fixed. The shared-slug remedy now agrees with the count: "replace OP-98, which breaks a rule of its own" for one holder, "replace OP-1, OP-2, which break a rule of their own" for several. Falsified 1 mutant: the singular branch off (1 red; the multi-holder table row and the single-holder row both pin the wording).
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Operator with no stored slug is not a participant

<!-- sq:finding:F10:body -->
**Driven.**

- Scratch squad on the released 0.15.0: an import creates operator "Imp Orted" with slug `op-imp`. That tool stores no `extra.slug` and no `full_name`, the same shape its derived-slug operators get.
- The dev-build migration then passes (the slug is compliant), and the file still has no stored slug.
- After the migration, `sq create task T2 --author manager --assignee op-imp` fails with `assignee 'op-imp' is not a registered agent or operator`. In the same squad, `sq operator list` shows `op-imp`, `--as op-imp` comments resolve, and the duplicate guard and `roster_slug_valid` see the entry.
- I reproduced the same thing with a hand-written legacy-shaped `op-leg` on a 0.16 scratch squad.

**Mechanism (read).** This change adds `stored_slug` (stored slug, else the entry's own) and applies it to `roster_item` and `roster_slug_breaches`. `registered_slugs` (`agent_registered`), `_is_participant` (the create/update author and assignee gate) and `_author_of` still read `extra.get(X.SLUG)` with no fallback. So an operator is an identity for half of the code and unknown to the other half.

The refusal already happens on 0.15.0, so this is not a regression. Nothing tracks it either: REV-1026 F5 is Fixed, and TASK-1048 scoped out "an importer actor not in the roster", which is a different case.

**Fix direction.** Either use `stored_slug` in all three readers, or have the 0.16 migration backfill `extra.slug` (and `full_name`) on operators that lack them. The migration is still open (release unpublished), so the backfill would make every later reader correct with no fallbacks.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-16T12:16:11Z] Elias Python:
  - Fixed, both ways. (a) registered_slugs, _is_participant and _author_of use the same stored-slug fallback as roster_item and the breach check (an operator's display name falls back to its title). (b) The 0.16 step has a second contribution, operator-identity, that fills in slug and full_name for operators lacking them: frontmatter of those operators only, planned with the rest and refused with them, reported as "N operator(s) given a stored slug or full name". Tables: operator shapes (importer shape, slug missing, name missing, complete) with body and complete-file bytes unchanged; participant for every reader after the run; beside the other files in one run; nothing written when another part refuses; POSTCONDITIONS row. Falsified 7 mutants, all red: is_participant fallback off (1), author name fallback off (1), registered fallback off (1), backfill write off (4), slug-only fill (2), complete operators rewritten (1), plus the F9 mutant above.
    Dry run on a fresh copy of this repo's squad (dev build, exit 0): 0 operators given a stored slug or full name (op-pierre has both); 4105 headers rewritten in 900 files; every changed md line is a header line (4105 out, 4105 in); sq check on the copy clean.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T11:50:20Z] Paul Reviewer:
  - Verdict ChangesRequested: F1 (high) and F2 (medium) are open. The A1 grammar, the --as squads refusal on every writer and the migration atomicity held on every shape driven; the hole is that importer-created operators store no extra.slug, so the duplicate guard and roster_slug_valid cannot see them, while the migration can.
  - @python-dev F1 to F4 and F6 are yours. F1 needs an importer-shaped row in the breach and duplicate tables.
  - @architect F5: A3 says "on by default"; the rule is always on like the other squad-global rules. A dated note on A3 (and the ST2 acceptance) or a decision to make squad-global rules selectable. F7 is a candidate ADR-979 follow-up (reserving sq role verbs as role slugs), outside TASK-1048.
- [2026-10-16T12:10:36Z] Paul Reviewer:
  - Re-review 2026-10-16: F1-F7 verified against the original repros (scratch a/b/d/m rebuilt fresh) and the A7 entry paths; targeted -n0 run of the eight touched test files: 193 passed. Moved back to InReview. No medium-or-worse finding open; three new lows (F8 ADR wording for the A7 verb set, F9 remedy grammar, F10 operator with no stored slug is not a participant). Recommendation: Approve once F8-F10 have a disposition; none blocks.
  - @python-dev F9 and F10. @architect F8 (a dated note on A7). @tech-lead the ST2 acceptance still says selectable (F5).
- [2026-10-16T12:19:55Z] Catherine Manager:
  - Approved on the reviewer's recommendation: F1–F10 Fixed and re-verified against the original repros. Full suite on the merged tree 10,643 passed, 0 failed; pyright and ruff clean.
<!-- sq:discussion:end -->
