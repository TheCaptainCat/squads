---
id: REV-1301
sequence_id: 1301
type: review
title: Rendered skill pointers and role skills implementation
status: Approved
author: reviewer
refs:
- ADR-1294
- TASK-1295
subentities:
- local_id: F1
  title: A skill or role description holding a backslash makes the pointer frontmatter
    invalid YAML
  status: Verified
  severity: medium
- local_id: F2
  title: Migrating a pre-0.5 squad leaves its legacy skill files and pointers behind,
    with nine sq check errors
  status: Verified
  severity: medium
- local_id: F3
  title: The comment_attributes_valid check flags prose that mentions sq:attrs, in
    bodies too; the reader is right
  status: Verified
  severity: medium
- local_id: F4
  title: The 0.20 manual tells adopters to rename a skill, which no sq verb can do
  status: Verified
  severity: low
- local_id: F5
  title: show --raw expands tab characters to spaces, so rendered bodies are not the
    stored text
  status: Verified
  severity: low
- local_id: F6
  title: AGENTS.md role bodies send agents to the sq-how-to skill, which an AGENTS.md
    host does not have
  status: Verified
  severity: low
- local_id: F7
  title: Keep RoleView mission and responsibilities for the playbook source; its docstring
    is now false
  status: Verified
  severity: low
- local_id: F8
  title: The pointer shell test starts a subprocess inside tests/cli, against ADR-1172
    rule 4
  status: Verified
  severity: low
- local_id: F9
  title: Every role_playbook test is bundled_only; the override squad playbook never
    reaches the view
  status: Verified
  severity: low
- local_id: F10
  title: The refusal of a system skill beside the legacy skill it would replace has
    no test
  status: Verified
  severity: low
- local_id: F11
  title: comment_authors still scans the whole file, so a body example names an undeclared
    source author
  status: Verified
  severity: low
- local_id: F12
  title: The playbook lifecycle and commands fields load but nothing renders them;
    retire both
  status: Verified
  severity: low
created_at: '2026-11-05T01:40:06Z'
updated_at: '2026-11-05T02:48:06Z'
---
<!-- sq:body -->
## Scope

The Python side of ADR-1294 under TASK-1295: the diff `2cd5af0d..542beb09` over `src`, `tests` and `scripts`, plus the round 1 to 3 commits `fb5a3fda`, `7ea2a27c` and `a20f9f40`. The TASK-1300 test commit `2cd5af0d` and the client commit `fe5cda7d` are out of scope.

## Method

- Read from a detached worktree at `542beb09`. Gates there: pyright 0 errors, ruff clean, `tests/meta` 748 passed.
- Drove the built `sq` in scratch squads under `/home/pchat/.cache/sq-review-1295/`: pointers, `show --raw` and `--no-header` in local and daemon mode under `FORCE_COLOR=3 COLUMNS=40`, `memory list --raw`, `board list --raw`, role rename, `sq check`.
- Ran each pointer line under bash and zsh with `sq` absent from the PATH. Every line exits 0 and prints its echo.
- Ran the migration on a squad made by the 0.4.0 release, once with this build and once with the build before the change (`973058e5`).
- Mutated two branches of the migration runner and ran `tests/cli/test_migrate.py`.

## What holds

- The pointer shape, the YAML-list grant naming exactly the commands each pointer runs, the regeneration comment and the agent pointer's two commands match ADR-1294 §1 to §3. The slug and echo-text guards in `_pointer_lines.py` hold: slugs are validated at create time, and the echo character set cannot close the quote.
- `--raw` prints no ESC byte and does not wrap, in local mode and through the daemon. `--no-header` without `--raw` is refused with empty stdout. An unknown item prints nothing on stdout.
- A role rename re-renders the role skill's description. Retiring a role removes both pointers, and `sq check` flags drift.
- The 0.19 runner scans before it writes, and a refused run leaves the files as they were. Because `migrate up` stamps the config last, the pre-0.15 prose exemption keys on the starting schema, as intended. Narrowing that exemption turns the 0.14 chain tests red.
- Layering: the renderers stay off `_workflow`, `_config` and `_services`. The `read_body` move to `ServiceCore` and the `role_bodies` hand-off follow the backend rule.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1301 add-finding "…" --severity medium`; track with `sq review 1301 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A skill or role description holding a backslash makes the pointer frontmatter invalid YAML

<!-- sq:finding:F1:body -->
**Where.** `src/squads/_rendering/templates/claude/pointer_skill.md.j2:4` and `pointer_agent.md.j2:4` render `description: "{{ description }}"`. The value goes through `oneline` (`src/squads/_backends/_claude_code/_frontmatter.py:43`), which turns `"` into `'` and leaves backslashes alone.

**Problem.** A description that holds a backslash makes the pointer's frontmatter invalid YAML. Driven: `sq skill add "Win paths" --desc 'Read C:\data\new files'` writes `description: "Read C:\data\new files"`, and `yaml.safe_load` fails with `ScannerError while scanning a double-quoted scalar` (`\d` is not a YAML escape). A description that ends in `\` leaves the scalar unterminated. `\n` or `\t` in a description are read silently as escapes. A role's `description` goes into the agent pointer the same way. The template predates this change, but the frontmatter now carries the `allowed-tools` grant that makes the first render work in an untrusted workspace, so a host that rejects the frontmatter loses the grant, the name and `user-invocable` together. `sq check` cannot see it, because the drifted file equals a fresh render.

**Fix.** Emit the scalar through a YAML-safe filter: either `json.dumps(text)` (a JSON string is a valid YAML double-quoted scalar), or escape `\` before `"` in `oneline`. Add one `sync` case with a backslash in a project skill's description, asserting the whole pointer file and that its frontmatter parses.

**Severity.** Medium.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-11-05T02:01:11Z] `python-dev` Elias Python:
  - Fixed: oneline doubles backslashes before quoting; sync test with a backslash description asserts the whole pointer and that its frontmatter parses.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Migrating a pre-0.5 squad leaves its legacy skill files and pointers behind, with nine sq check errors

<!-- sq:finding:F2:body -->
**Where.** `src/squads/_migrations/_v0_4_to_v0_5.py:188`. The loop iterates `bundled_skill_slugs()`, which now gives `sq-greeting`, `sq-how-to` and `sq-memory`, and looks for `<slug>.md`. The per-type seeding it relied on was removed in `42c38d84`.

**Problem.** On a squad created by the 0.4.0 release, the slug-named legacy files `greeting.md`, `squads.md` and `sq-<type>.md` are never matched, so no migration step indexes, renames or removes them. Driven: `sq init` with v0.4.0, then `sq migrate up` with `542beb09`. The run exits 0, and the result has these problems:
- `squads/agents/skills/` keeps nine unindexed files (`greeting.md`, `squads.md`, and `sq-bug.md` through `sq-task.md`) beside the new `SKILL-…-sq-greeting/sq-how-to/sq-memory` items.
- `.claude/skills/` keeps the stale `greeting`, `squads` and seven `sq-<type>` pointer directories. These are the old redirect pointers, and they name skills that no longer exist.
- `sq check` reports nine errors (`missing sq:body region … restore the marker pair`), with a remedy that does not fit the case.

The same squad migrated with `973058e5` indexes all of them as `SKILL-10…20`, and the 0.20 runner would then retire them. Manager ruling cc51e9f/b3a284a assumed that a pre-0.5 squad simply has no `squads`/`greeting` item; the files on disk were not considered.

**Fix.** In the 0.4 to 0.5 runner, map the legacy slugs (`squads` to `sq-how-to`, `greeting` to `sq-greeting`) the way `_current_skill_slug` does in 0.14 to 0.15, and seed per-type `sq-<type>.md` files as before so that 0.20 removes them. Alternatively, have the 0.20 runner also sweep unindexed `greeting.md`, `squads.md` and `sq-<type>.md` (author == slug) files and their pointer directories. Add a migrate case from a pre-0.5 corpus fixture.

**Severity.** Medium.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-11-05T02:01:12Z] `python-dev` Elias Python:
  - Fixed: the 0.4 to 0.5 runner pins the 0.4 skill table (greeting, squads, sq-<type>). It also rendered pointers through the live template, which failed on the new grants variables, so the 0.4 to 0.5 and 0.8 to 0.10 runners now render through one backend function. The 0.20 runner drops the unindexed sq-greeting.md and sq-how-to.md an earlier live-backend step writes. Reproduced with a v0.4.0 worktree (removed). New small fixture corpus/v0_4 and a migrate test: three skill files, four pointer dirs, sq check clean.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — The comment_attributes_valid check flags prose that mentions sq:attrs, in bodies too; the reader is right

<!-- sq:finding:F3:body -->
**Where.** `src/squads/_discussion.py:118-125` (`malformed_attribute_comments`), reported by rule `comment_attributes_valid` in `src/squads/_services/_source_checks.py:153`. This code comes from the sources feature (`17b323ad`), not from TASK-1295, but it is what fails the dry-run migration of this repo.

**Problem.** The rule flags any line directly under a comment header that merely contains the substring `sq:attrs` (`ATTRS_TAG in after`), and it scans the whole file text (`_region_lines(text)`), not only the discussion regions. The reader is correct: `parse_attributes_line` is anchored (`^  <!-- sq:attrs {...} -->$`) and reads both cases below as comment text. So nothing is misparsed, and the check alone reports an error that does not exist. Reproduced in a scratch squad with the reviewed build:
- `sq task 15 comment --as tech-lead -m 'The sq:attrs line is the payload under a header.'` gives `error TASK-15: the comment by tech-lead … has an sq:attrs line that is not one JSON object of strings` (the REV-1281 case).
- A feature *body* holding a fenced example ``- [2026-11-02T09:14:00Z] `tech-lead` Olivia Lead:`` followed by `  sq:attrs {...}` gives an error for a comment that does not exist (the ADR-1274 case, which sits in the decision body, not in a comment).

The first case leaves a squad with an error it can clear only by rewording a comment, and only the author can do that.

**Fix.** Judge the shape, not the substring: report a line only when it has the attribute line's shape (indented, `<!--`, `sq:attrs`, `-->`, as `is_attributes_line` or the 0.20 runner's `_is_attribute_line` test) and its payload does not parse. Scan only the discussion regions (`sq:discussion` and the sub-entity discussions), as the reader does. With that fix, ADR-1274 and REV-1281 need no corpus change. Add two check cases, one per shape above, both expecting a clean `check`.

**Severity.** Medium. Recommend a bug against the sources code, fixed before this squad is migrated.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-11-05T02:01:12Z] `python-dev` Elias Python:
  - Fixed: a line is reported only when it has the shape of an attribute line (indented, comment open, sq:attrs, close) and does not parse, and only inside discussion regions. A check test holds both reviewer shapes clean.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — The 0.20 manual tells adopters to rename a skill, which no sq verb can do

<!-- sq:finding:F4:body -->
**Where.** `src/squads/_migrations/_v0_19_to_v0_20.py:83` and `:85` (MANUAL items 6 and 7).

**Problem.** Both items tell the adopter to "Rename the skill" or "Rename the project skill first". A skill's slug never changes: `sq skill <slug> update` says "its slug never changes", and no verb renames one in 0.19 or 0.20. An adopter who follows the manual finds no command to run.

**Fix.** State the steps that exist: create the replacement under a new name (`sq skill add`, with its body copied through `sq skill <new> body --file`), re-point the refs, then remove the old one (`sq skill <old> remove --purge`). All of this runs with the 0.19 release, like items 1, 2 and 5. Regenerate the frozen `migrate help --json` document.

**Severity.** Low.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-11-05T02:01:12Z] `python-dev` Elias Python:
  - Fixed: MANUAL items 6 and 7 name the verbs that exist (skill add under a new name, body --file, re-point refs, remove --purge); frozen migrate help document regenerated.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — show --raw expands tab characters to spaces, so rendered bodies are not the stored text

<!-- sq:finding:F5:body -->
**Where.** `src/squads/_cli/_render/_raw.py:32` (`print_raw`). It is used by every `--raw` show and by `memory list --raw` and `board list --raw`.

**Problem.** Rich's `console.print` expands tab characters to spaces (tab size 8). Driven: a feature body holding a Makefile fence with a tab-indented recipe prints eight spaces under `show --raw --no-header`, and the stored file keeps the tab. `--raw` is the contract every pointer renders through, and ADR-1294 §1 calls it plain markdown with the body as written. A skill or role body holding a Makefile, a Go snippet or a TSV reaches the agent altered, and a copied recipe then fails. The item raw path had this before. It now applies to every rendered skill.

**Fix.** Write the raw text to the console's file directly (`console.file.write(text + "\n")`), or print a `Text` with tab expansion off. Extend `test_show_raw_no_header_prints_the_body_alone` with a body holding a tab.

**Severity.** Low.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-11-05T02:01:13Z] `python-dev` Elias Python:
  - Fixed: print_raw writes to the console file directly, so tabs stay; show test with a tab-indented body, also green in remote and routes modes.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — AGENTS.md role bodies send agents to the sq-how-to skill, which an AGENTS.md host does not have

<!-- sq:finding:F6:body -->
**Where.** `src/squads/_rendering/templates/views/role_definition.md.j2:29` and the bundled playbook lines (`src/squads/_specs/playbook.toml:79, 97, 157, 387, 403`). These are compiled into AGENTS.md by `agents_section.md.j2` through `ctx.role_bodies`.

**Problem.** AGENTS.md now compiles each role body whole, and every role definition and several playbook guides tell the agent to "see the `sq-how-to` skill's comment-scoping convention". An AGENTS.md host has no skills (ADR-1294 §7), and AGENTS.md does not carry that section, so the reference points nowhere. A fresh `agents_md` squad shows 13 such lines in AGENTS.md.

**Fix.** Point to a surface both hosts have: `sq skill sq-how-to show` (a command, not a skill load), or a `sq docs` topic. Alternatively, include the comment-scoping section in the AGENTS.md section as it includes `workflow.md.j2`.

**Severity.** Low.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-11-05T02:01:13Z] `python-dev` Elias Python:
  - Fixed: role definition and playbook lines point to the comment-scoping convention in `sq skill sq-how-to show`, a command both hosts can run, instead of a skill load.
- [2026-11-05T02:06:54Z] `reviewer` Paul Reviewer:
  - Reopened at 2a11964b. The new reference names `sq skill sq-how-to show`, but a squad whose only backend is `agents_md` has no skill items at all. Driven: `sq init --default-names --backend agents_md`, then `sq skill sq-how-to show` gives `error: no skill with slug, ID, or number 'sq-how-to'`, and AGENTS.md holds no comment-scoping section. The pointer therefore still goes nowhere on exactly the host this finding is about. Fix: point to a surface every squad has, such as an `sq docs` topic that holds the comment-scoping rule, or include that section in the AGENTS.md managed section, as it already includes `workflow.md.j2`.
- [2026-11-05T02:40:22Z] `python-dev` Elias Python:
  - Fixed: the role definition and the five playbook lines point to "Scope the comment to the right discussion" in `sq docs agents` (present in docs/agents.md), which runs on any squad. Tests: role show golden, and a bundled-only case asserting no `sq skill sq-how-to` in the tech lead playbook.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Keep RoleView mission and responsibilities for the playbook source; its docstring is now false

<!-- sq:finding:F7:body -->
**Where.** `src/squads/_roles/_projection.py:9-14` (`RoleView` docstring). Manager question cc51e9f asks whether `RoleView.mission` and `RoleView.responsibilities` go.

**Judgement.** Keep the fields. They still feed `PlaybookRosterEntry.mission` and `.responsibilities` in `src/squads/_services/_view_source.py:107-108`. These are part of the `playbook` view source, which `sq workflow view <name> <id> --json` prints and which an adopter's template override can read (`_api/_dto/_workflow.py:271-272`). Removing them changes that contract for no gain.

**Problem.** The docstring says RoleView "carries every role field a backend renders into a compiled managed region, `mission` and `responsibilities` included". No backend renders either field any more, so the statement is false.

**Fix.** Say what is true: the fields are carried for the playbook view source's roster entries. Keep the rule that any field a backend renders is declared here.

**Severity.** Low.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-11-05T02:01:14Z] `python-dev` Elias Python:
  - Fixed: RoleView docstring states the fields are carried for the playbook view source roster entries; fields kept.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — The pointer shell test starts a subprocess inside tests/cli, against ADR-1172 rule 4

<!-- sq:finding:F8:body -->
**Where.** `tests/cli/test_sync.py:127-160` (`_ran_without_sq`, `test_every_line_of_a_pointer_exits_0_and_names_its_command_when_sq_is_absent`).

**Problem.** ADR-1172 rule 4 says "No test starts a subprocess", and puts behaviour seen only in a separate process in the cross-process set. This case starts `bash -c` and `zsh -c` from inside `tests/cli`, and skips when a shell is missing. It will skip zsh on most CI runners, and both shells on Windows. The behaviour is worth holding: it is the only proof that a line exits 0 without `sq`. It belongs in the cross-process set.

**Fix.** Move the case to the cross-process set (beside the daemon/shim process tests), without a `covers` marker. In `tests/cli` keep the whole-file pointer assertions, which already pin the `|| echo '…'` text.

**Severity.** Low.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-11-05T02:01:14Z] `python-dev` Elias Python:
  - Fixed: moved to tests/cross_process, using the real sq sync and the suite helpers; removed from tests/cli.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Every role_playbook test is bundled_only; the override squad playbook never reaches the view

<!-- sq:finding:F9:body -->
**Where.** `tests/cli/test_role.py:1532, 1556, 1580, 1598, 1612`. Every `role_playbook` case is `@pytest.mark.bundled_only`.

**Problem.** ADR-1172 has a case reach its host through the squad profile. The override squad has its own `playbook.toml` with role guides for `initiative`, `job` and `record`. The view is built for exactly that case: an adopter's types and guides rendered into the role skill. Today the view is never exercised on a vocabulary other than the bundled one. A regression that hard-codes a bundled type or label in `role_playbook.md.j2` or in `role_playbook_sections` would pass both runs.

**Fix.** Rewrite at least the definition-then-own-section case and the disable case to read the role, type and guide text from the profile and the squad's playbook. Keep `bundled_only` only for the capability-guide case if the override playbook has no capability guide.

**Severity.** Low.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-11-05T02:01:15Z] `python-dev` Elias Python:
  - Fixed: two override_only cases (definition then the squad own sections, and disable) read the types from the profile and run on the override playbook. The bundled cases stay bundled_only.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — The refusal of a system skill beside the legacy skill it would replace has no test

<!-- sq:finding:F10:body -->
**Where.** `src/squads/_migrations/_v0_19_to_v0_20.py:211-214`. This branch refuses a system `sq-how-to` or `sq-greeting` that sits beside the legacy `squads` or `greeting` skill it would replace.

**Problem.** No test holds the branch. Mutated it to `elif False and old in legacy:` and `tests/cli/test_migrate.py` still passes (72 passed). Without the branch, the rename gives two skill items the same slug. The handback's "name-holder rule" mutation covered the project-origin branch only.

**Fix.** Add the system twin to the refusal case `test_up_lists_every_skill_it_refuses_and_what_the_skill_holds` (one more expected line), rather than adding a new test.

**Severity.** Low.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-11-05T02:01:15Z] `python-dev` Elias Python:
  - Fixed: the refusal case now holds a system sq-greeting beside the legacy greeting; mutating the branch turns it red.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — comment_authors still scans the whole file, so a body example names an undeclared source author

<!-- sq:finding:F11:body -->
**Where.** `src/squads/_discussion.py:113` (`comment_authors`), read by `src/squads/_services/_source_checks.py:105`.

**Problem.** F3 limited the attribute rule to the discussion regions, but its sibling rule still scans the whole file text. A comment-header-shaped line in a body, such as a fenced example, is taken as a comment author. Driven on the fixed build: appending a fenced body example whose header names `` `source:nowhere` `` gives `warn FEAT-15: an author source:nowhere names no source declared in sources.toml`. This is the remaining warning on the migrated dry-run copy of this squad (ADR-1274, body line 138), so the repository's must-pass `sq check` is still not clean after migration.

**Fix.** Read the comment authors from `_discussion_regions(text)` as `malformed_attribute_comments` now does, and check any other `_headed_lines(text)` caller for the same scope. Add a check case for a body example naming an undeclared source, expecting a clean check.

**Severity.** Low.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-11-05T02:40:23Z] `python-dev` Elias Python:
  - Fixed: comment_authors reads only the discussion regions. Check case: a body example naming source:nowhere gives a clean check; restoring the whole-file scan turns it red.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — The playbook lifecycle and commands fields load but nothing renders them; retire both

<!-- sq:finding:F12:body -->
**Where.** `src/squads/_interactions/_models.py:43-44` (`ItemPlaybookSpec.lifecycle`, `.commands`), `src/squads/_interactions/_loader.py:313` (an empty `lifecycle` is a load error) and the bundled `src/squads/_specs/playbook.toml` (18 such keys). The tech-writer raised this as an open question, and docs/overrides.md:2639 now documents the gap.

**Judgement.** Both fields should go. The per-type skill was their only renderer, and it is retired. `role_playbook.md.j2` derives the lifecycle line from `spec.machine_for(...)`, and nothing bundled renders `commands`. Today an adopter must write a non-empty `lifecycle` line that no output shows, and that line can contradict the workflow spec it duplicates: stored data that can be derived. `commands` is loaded and checked for capability tokens and then dropped. The only remaining reader is the `playbook` view source's JSON (`PlaybookLane.lifecycle`/`commands`, `_services/_view_source.py:87-88`), which a template override could read. That does not justify a required, duplicated field.

**Fix.** Retire both fields: make the loader tolerate them for one release and say so in the 0.20 manual, or drop them in the 0.20 schema step, since the unreleased runner is the place for it (board notice 17). Remove them from the bundled playbook, `ItemPlaybook` and `PlaybookLane`. If a lifecycle line is wanted in the source, expose the derived `linearize_lifecycle` value instead. This changes the playbook grammar, so the architect should record it in the ADR that owns that grammar before the dev round.

**Severity.** Low.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-11-05T02:40:24Z] `python-dev` Elias Python:
  - Fixed per ADR-226: lifecycle and commands removed from the bundled playbook (9 entries), ItemPlaybookSpec, ItemPlaybook, PlaybookLane and the view source; empty-lifecycle check, commands in the capability-token check and playbook_override_command_lines removed. Load refusal names every types.<type>.lifecycle/commands in one error. Tests: migrate up refuses and writes nothing; sq check reports playbook_loads. 0.20 MANUAL step 8, docs/migration.md, docs/overrides.md Format and CHANGELOG written; override-squad fixture and goldens regenerated.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T01:41:53Z] `reviewer` Paul Reviewer:
  - Verdict: request changes. The design is implemented as ADR-1294 states it, the gates are green (pyright 0, ruff clean, tests/meta 748 passed), and the pointer lines hold under bash and zsh with sq absent. Three medium findings block acceptance:
    - F1: a backslash in a skill or role description produces an invalid pointer frontmatter, so the grant is lost.
    - F2: the pre-0.5 migration path regressed. It leaves nine legacy skill files and pointers behind, with nine check errors. The build before this change indexed them.
    - F3: the sq:attrs check is a check defect, not a parser defect. The reader is anchored and reads both quotes as comment text; the check rule matches the substring, and also in bodies. ADR-1274 and REV-1281 need no corpus change once the rule is fixed. The code is from the sources feature, so I recommend a bug fixed before this squad is migrated.
    
    F4 to F10 are low. F7 answers the RoleView question: keep the fields, because the playbook view source still serves them, and fix the docstring.
    
    Out of the code's scope: FEAT-1290's acceptance criteria and US7 still describe the raw header as a YAML front-matter block, which op-pierre's ruling c30d364 replaced.
    
    @manager the next step is a python-dev round for F1, F2, F4 to F10, and a qa bug for F3. @product-owner please align FEAT-1290's US7 and acceptance text with ruling c30d364.
- [2026-11-05T01:43:51Z] `product-owner` Nina Product:
  - FEAT-1290 aligned with op-pierre's raw-header ruling: the acceptance criterion and US7 now state the header as the panel's rows in a '- **key:** value' list (item: H1 then type row; roster shows: no H1; frontmatter not in --json). No other story mentions a YAML header. sq check clean.
- [2026-11-05T02:06:54Z] `reviewer` Paul Reviewer:
  - Verified at 2a11964b. Every case below is my own probe on the fixed build, separate from the dev's tests:
    - F1: a description holding backslashes now parses back to the original text, for a project skill and for a trailing backslash.
    - F2: a squad made by the 0.4.0 release migrates to three skills, no stray files or pointer directories, and a clean `sq check`. Making `_drop_stray_body` a no-op turns the v0_4 test red.
    - F3: prose and a body example no longer trip the rule, and a wrapped malformed line is still reported in both an item discussion and a sub-entity discussion. Scanning the whole text again turns the new case red.
    - F5: tabs survive both locally and through the daemon.
    - F10: the twin line is in the refusal case.
    - F4, F7, F8 and F9: I read the changes, and the moved test and the override-only tests pass.
- [2026-11-05T02:07:15Z] `reviewer` Paul Reviewer:
  - Re-review at 2a11964b. Verdict: changes requested. Nine findings are Verified: F1, F2, F3, F4, F5, F7, F8, F9 and F10. Pyright 0, ruff and format clean; meta, check and the touched cli modules: 1358 passed; on the override squad, role and check: 281 passed. Remaining:
    - F6, reopened: `sq skill sq-how-to show` does not resolve on a squad whose only backend is `agents_md`.
    - F11, new: `comment_authors` still scans bodies. It leaves this squad's migrated `sq check` with one warning, on ADR-1274.
    - F12, new: retire the playbook `lifecycle` and `commands` fields. This settles the writer's question. It is a grammar change, so @architect records it first.
    
    The new 0.4 fixture and the stray-body drop in the 0.20 runner hold. Making the drop a no-op turns the v0_4 test red, and a squad made by the real 0.4.0 release migrates clean.
    
    @manager F6 and F11 go to python-dev. F12 goes to the architect, then python-dev.
- [2026-11-05T02:07:57Z] `manager` Catherine Manager:
  - F6: role bodies point to the comment-scoping section of sq docs agents (present in docs/agents.md since the docs pass), which every host can run. F6 and F11 go to python-dev after the current QA-bug round; F12 goes to the architect to record the playbook format change, then python-dev.
- [2026-11-05T02:10:47Z, edited 2026-11-05T02:11:07Z] `architect` Robert Architect:
  - F12 recorded: ADR-226 narrowed in place (section "Narrowed 2026-11-05", §1, §2, §3 rules 4 and 6), linked related to ADR-1294. Decision: the playbook entry keys `lifecycle` and `commands` are removed and refused at load; no deprecation release, no migration rewrite.
    @python-dev implements:
    - Drop both keys from the bundled `playbook.toml` (18), `ItemPlaybookSpec`, `ItemPlaybook`, `PlaybookLane` and `_playbook_source`; drop the empty-`lifecycle` check, `commands` from `_check_capability_tokens`, and `playbook_override_command_lines` with its `override_commands` parameter.
    - In the loader, refuse each `types.<type>.lifecycle` / `types.<type>.commands` in the merged mapping, all in one `PlaybookConfigError`, with the two messages verbatim from ADR-226 §3 rule 6 (before pydantic's generic extra-key error).
    - The 0.19 → 0.20 runner does not touch `.overrides/playbook.toml`. Add a test that `sq migrate up` on a 0.19 squad whose override sets `lifecycle` refuses with the rule 6 message and writes nothing, and one that `sq check` reports it.
    - Add a numbered step to the 0.20 `MANUAL` and `docs/migration.md`: delete both keys from every `[types.<t>]` in `.overrides/playbook.toml`, with 0.20 installed. Rewrite the Format section of `docs/overrides.md` (overview is the only prose field; the lifecycle line comes from the workflow spec; the paragraph at line ~2639 goes) and add a CHANGELOG entry. Regenerate the playbook goldens.
- [2026-11-05T02:47:25Z, edited 2026-11-05T02:47:35Z] `reviewer` Paul Reviewer:
  - Final re-review at 307c1030. Verdict: approve. All twelve findings are Verified.
    - F6: the role definition and the playbook lines point to "Scope the comment to the right discussion" in `sq docs agents`. That command runs on a squad whose only backend is `agents_md`, and the docs ship in the wheel.
    - F11: `comment_authors` reads only the discussion regions. The ADR-1274 warning is gone from the migrated dry-run copy, and scanning the whole text again turns `tests/check` red.
    - F12: `lifecycle` and `commands` are retired as ADR-226 now states. A playbook override that still sets either key is refused in one error, both by `sq check` and by `migrate up`, which writes nothing. MANUAL step 8 names the remedy.
    
    The writer's follow-ups hold:
    - The `sq-greeting` body refusal names `views/greeting_skill.md.j2`.
    - `role <slug> body` and `role <slug> view add`/`disable` regenerate AGENTS.md (driven).
    
    BUG-1302, BUG-1303, BUG-1305 and BUG-1306 (code half) are verified and set to Verified, since the bug lifecycle has no Done.
    
    Gates: pyright 0, ruff and format clean. Meta, check, cli and cross_process: 2151 passed. On the override squad, cli and check: 1196 passed, 0 failed.
    
    I set REV-1301 to Approved at the coordinator's request; @manager, please confirm it, since I authored this review.
- [2026-11-05T02:48:06Z] `manager` Catherine Manager:
  - Approval confirmed: all twelve findings Verified, full suite green at 307c1030 (2275 passed).
<!-- sq:discussion:end -->
