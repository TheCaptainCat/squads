---
id: REV-1158
sequence_id: 1158
type: review
title: 'Review TASK-1137 ST3: init/adopt --roles use the squad catalog'
status: Approved
author: reviewer
refs:
- TASK-1137
description: 'Review of commit 5922d04f: init and adopt --roles resolve against the
  squad role catalog (BUG-1045).'
subentities:
- local_id: F1
  title: 'Refusal-before-write ordering is unpinned: moving resolution after the config
    write stays green'
  status: Verified
  severity: medium
- local_id: F2
  title: A catalog without the all bundle makes bare init/adopt fail with no predefined
    role all, naming no bundles
  status: Verified
  severity: low
- local_id: F3
  title: 'Load-count guard has no init row: shared-sources claim unpinned, workflow.toml
    read twice'
  status: Verified
  severity: low
- local_id: F4
  title: 'Interactive init prompt path never runs against an override: bundled-catalog
    mutation stays green'
  status: Verified
  severity: low
- local_id: F5
  title: CHANGELOG entry says nothing changes without an override, but the unknown
    --roles wording changed for every squad
  status: Verified
  severity: low
created_at: '2026-10-26T03:48:40Z'
updated_at: '2026-10-26T04:14:15Z'
---
<!-- sq:body -->
Review of commit 5922d04f: `sq init --roles` and `sq adopt --roles` resolve bundles and slugs against the squad's role catalog (`.overrides/roles.toml` merged over the bundled one). Fixes BUG-1045.

## Verified (driven on a scratch copy of 5922d04f)

- An override bundle (`ops`), an override slug (`manager,sre`) and an extended `all` resolve on `init`, `init --force` and `adopt`.
- Interactive `init --roles ops` under a pty prompts for manager and sre and creates both. The CLI passes its `SpecSources` to `init`, so the prompt path and the service use one memoised catalog.
- A template name (`--roles dev`, or a `[templates.sre]` entry) is refused, because `resolve_roles` reads `catalog.roles` only.
- A `[selected]` keep-list that drops a role is caught by the loader's bundle check before init writes anything. `--roles qa` with qa selected away is refused.
- A malformed override gets the loader's message ("malformed role catalog override ..."), and nothing is written.
- On a fresh directory, a refusal leaves only the pre-placed `squads/.overrides`. Under `init --force`, `.squads.toml` comes through a refusal byte-identical.
- `adopt` with `.squads.toml` naming `team/`: the catalog comes from `team/.overrides`, and a broken `squads/.overrides/roles.toml` beside it is ignored.
- Mutation: pointing `resolve_roles` back at the bundled catalog turns the six override rows red.
- ruff and pyright are clean on the changed files.

## Gaps

Recorded as findings below.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1158 add-finding "…" --severity medium`; track with `sq review 1158 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Refusal-before-write ordering is unpinned: moving resolution after the config write stays green

<!-- sq:finding:F1:body -->
The commit moves role resolution in `init` and `adopt` ahead of the first write, so a refused `--roles` writes nothing. That claim holds when driven, but no test pins it.

**Mutation (scratch copy).** Move both `role_defs = resolve_roles(...)` lines back to their pre-fix place, just before `activate_role` (after `.squads.toml`, the folders and the index are written). The new table and `tests/cli/test_init_naming_flags.py` stay green: 34 passed. The exit-1 rows only assert the exit code, a message substring, and that "squads initialized" is absent.

**Failure scenario.** A later refactor puts resolution after the config write again. `sq init --roles nobody` then leaves a `.squads.toml`, an index and folders behind. A retry without `--force` meets `AlreadyInitializedError`, and the suite stays green.

**Fix.** On every exit-1 row, assert the tree after the command: no `.squads.toml` on a fresh `init` or `adopt`, and `.squads.toml` byte-identical under `init --force`. Also tighten `_MALFORMED = "roles.toml"` to the loader's own prefix ("malformed role catalog override"). Any message that names the path matches today.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T03:59:17Z] `python-dev` Elias Python:
  - Fixed in the working tree (see TASK-1137 comment); each guard mutated red.
- [2026-10-26T04:11:33Z] `reviewer` Paul Reviewer:
  - Verified on 30c0b568: moving both resolutions after the writes reddens 10 rows (fresh init and adopt refusals). init-force rows stay green under that mutation, which is acceptable because the fresh rows pin the ordering.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — A catalog without the all bundle makes bare init/adopt fail with no predefined role all, naming no bundles

<!-- sq:finding:F2:body -->
`--roles` defaults to `all`. An override may legitimately keep only some bundles, for example `[selected] bundles = ["core", "minimal"]`. Running `sq init` or `sq adopt` on that squad without `--roles` then exits 1 with:

`error: no predefined role 'all' (known: manager, architect, tech-lead, reviewer, qa, devops, product-owner, tech-writer)`

(driven on 5922d04f). The message calls a bundle a role. It lists only slugs, never the bundles the catalog has, and it does not say that `all` is the default the user never typed. The `--help` of both commands still says "`all`, `core`, `minimal` or comma-separated slugs", whatever the squad's catalog declares. The same wording greets a template name (`--roles dev` gives "no predefined role 'dev'") with no pointer to `sq role activate --from`.

**Failure scenario.** An adopter commits a roles override that drops `all`, and a teammate runs a bare `sq adopt` on the checkout. They get a "no predefined role 'all'" error naming eight slugs and nothing to act on.

**Fix.** Word the refusal from the catalog: "no bundle or role 'all' (bundles: core, minimal; roles: ...)", with "(the --roles default)" added when the value was not given. Make the help generic ("a bundle of the squad's role catalog, or comma-separated slugs"). Add a table row for the dropped default bundle.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T03:59:19Z] `python-dev` Elias Python:
  - Fixed in the working tree (see TASK-1137 comment); each guard mutated red.
- [2026-10-26T04:11:34Z] `reviewer` Paul Reviewer:
  - Verified on 30c0b568: dropped all on bare init/adopt names the default and lists bundles and roles; a template name gets the role activate --from hint; an empty bundle set says bundles: none. The note shows on an explicit --roles all too. Accepted as is: all IS the default, so the note stays true, and telling the two cases apart costs a sentinel default for no adopter gain.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Load-count guard has no init row: shared-sources claim unpinned, workflow.toml read twice

<!-- sq:finding:F3:body -->
The handoff claims the CLI shares one `SpecSources` with `init`, so the interactive prompt path does no second catalog read. `test_each_spec_document_is_loaded_at_most_once_per_invocation` has an `adopt` row but no `init` row, so nothing pins that claim.

**Driven (scratch copy).** I added `"init": ["init", "--force", "--default-names", "--no-claude", "--roles", "manager"]` to `_COMMANDS`.
- Every roles shape passes at 5922d04f.
- Dropping `sources=sources` from the CLI call and forcing the prompt path turns `roles-present-init` red: roles.toml is read twice. The new row catches the regression the commit guards against; the shipped guard does not.
- Seven workflow rows fail at 5922d04f AND at its parent 7006946d: `workflow.toml` is read twice on `init`. This is pre-existing, not a regression. `_init_time_spec` calls `load_workflow_spec(squad_dir=...)` without the `OverrideFiles` that `init` now holds in `sources`, and another workflow read follows.

**Failure scenario.** A refactor builds a second `spec_sources` in the CLI or the service, and the suite stays green. The double workflow read stays invisible because init is outside the guard.

**Fix.** Add the `init` row to the guard. Resolve init's workflow through the `sources` it now carries (`sources.workflow()` with `_init_time_spec`'s lint hint), so the row passes for every shape.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-26T03:59:22Z] `python-dev` Elias Python:
  - Fixed in the working tree (see TASK-1137 comment); each guard mutated red.
- [2026-10-26T04:11:36Z] `reviewer` Paul Reviewer:
  - Verified on 30c0b568: init row added to the guard and every shape passes; dropping sources=sources from the CLI call reddens 7 init rows (workflow read twice). _init_time_spec now goes through sources.workflow and keeps the workflow lint hint (driven with a malformed workflow.toml, nothing written).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Interactive init prompt path never runs against an override: bundled-catalog mutation stays green

<!-- sq:finding:F4:body -->
The interactive branch of `_cli/_main.py::init` resolves `--roles` itself, to know which names to prompt for. No test runs that branch against an override: `CliRunner` is not a tty, and the table always passes `--default-names` to `init`.

**Mutation (scratch copy).** Replace `sources.catalog()` in that branch with the bundled `get_catalog()`. The new table and `test_init_naming_flags.py` stay green: 34 passed. Driven under a pty, the mutated build refuses `sq init --roles ops` with "no predefined role 'ops'" before any prompt. That is BUG-1045 back on the default interactive path.

**Failure scenario.** The default way a human runs `sq init` (a terminal, no `--default-names`) regresses on an override bundle, and only the non-interactive path stays covered.

**Fix.** Add a row that monkeypatches `_is_tty` to True, feeds names on stdin (`runner.invoke(..., input="A\nB\n")`), runs `--roles ops` against an override bundle, and asserts both prompts and the names on the created roles.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-26T03:59:24Z] `python-dev` Elias Python:
  - Fixed in the working tree (see TASK-1137 comment); each guard mutated red.
- [2026-10-26T04:11:37Z] `reviewer` Paul Reviewer:
  - Verified on 30c0b568: swapping the prompt-path catalog for the bundled one reddens the new interactive test.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — CHANGELOG entry says nothing changes without an override, but the unknown --roles wording changed for every squad

<!-- sq:finding:F5:body -->
The 0.17.0 Fixed entry for this change ends "Without an override nothing changes". Since 30c0b568 that is false. An unknown `--roles` value is refused on every squad with new wording, override or not: `no bundle or role 'x' (bundles: all, core, minimal; roles: ...)` instead of `no predefined role 'x' (known: ...)`. A template name now also gets a `sq role activate --from` hint. The entry also says nothing about the dropped-default refusal.

**Failure scenario.** An adopter whose script or CI greps for "no predefined role" reads "nothing changes" and skips the entry, and their check silently stops matching.

**Fix (tech writer).** Reword the entry: the bundles and roles of the squad's catalog resolve, and an unknown name is refused naming the catalog's bundles and roles (and the role-template route for a template name).
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-26T04:13:14Z] `tech-writer` Theo Writer:
  - CHANGELOG 0.17.0 init/adopt --roles entry rewritten: the refusal text applies to every squad (driven: `no bundle or role ...`, the `(the --roles default)` note, the role-template pointer for `dev`), it replaces "no predefined role", and a refused init/adopt writes nothing (driven). docs/ never quoted "no predefined role".
- [2026-10-26T04:13:51Z] `reviewer` Paul Reviewer:
  - Verified at 7f69ec17: CHANGELOG line 100 now states the new refusal wording for every squad, the default note, the template hint and the write-nothing ordering; each matches what I drove on 30c0b568.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T03:49:11Z] `reviewer` Paul Reviewer:
  - Verdict: changes requested, as test coverage only. The fix is correct for every shape I drove: override bundle and slug, extended all, a [selected] keep-list, a template name, a malformed override, init --force, adopt with a different squad dir, and interactive prompts sharing one catalog read. F1 (medium) to F4 (low) are guard gaps: three claims a mutation leaves green, plus a confusing refusal when the default all bundle is deselected. The workflow.toml double read on init (F3) predates this commit. CHANGELOG line written by the dev, so it goes to the writer per the board rule. @tech-lead
- [2026-10-26T04:11:49Z] `reviewer` Paul Reviewer:
  - Re-review of 30c0b568: F1 to F4 verified, each by the mutation that was green before; all three mutations now redden their guard. The dev note on F2 (the default note also shows on an explicit --roles all) is accepted: the statement stays true. New F5 (low): the CHANGELOG entry still says nothing changes without an override, which the new refusal wording makes false; a one-line fix for the tech writer. Leaving InReview until F5 is treated. @tech-lead
- [2026-10-26T04:13:53Z] `reviewer` Paul Reviewer:
  - All five findings verified fixed; approved.
<!-- sq:discussion:end -->
