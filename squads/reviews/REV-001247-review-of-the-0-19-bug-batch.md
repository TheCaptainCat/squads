---
id: REV-1247
sequence_id: 1247
type: review
title: Review of the 0.19 bug batch
status: ChangesRequested
author: reviewer
refs:
- TASK-1244
- TASK-1245
- TASK-1246
subentities:
- local_id: F1
  title: migrate chlog still accepts non-version bounds such as v1x..v2y and answers
    no manual steps
  status: Verified
  severity: low
- local_id: F2
  title: init over a shared-number corpus writes .squads.toml before the repair refusal;
    a plain re-run is refused
  status: Verified
  severity: low
- local_id: F3
  title: 'create guide skips the spec-aware create class: override fields and the
    --priority help refresh miss it'
  status: Verified
  severity: low
- local_id: F4
  title: 'Existing untitled sub-entities stay invisible: sq check does not report
    the now-required title'
  status: Verified
  severity: low
- local_id: F5
  title: 'import with no op still prints pydantic wording: Unable to extract tag using
    discriminator ''op'''
  status: Verified
  severity: low
- local_id: F6
  title: Several new refusal cases assert a prefix or exit code instead of the whole
    output (ADR-1172 rule 5)
  status: Verified
  severity: low
- local_id: F7
  title: No tests/cli boundary case for a comment on a missing sub-entity, nor for
    an adopt --squad-dir refusal
  status: Verified
  severity: low
- local_id: F8
  title: 'tests/regressions: eight duplicated fixtures, one module holding two bugs,
    uneven docstrings'
  status: Verified
  severity: info
- local_id: F9
  title: unlink-role on a skill not scoped to the role still reports success, the
    BUG-1184 shape
  status: Verified
  severity: low
- local_id: F10
  title: SubentityAddRequest.title still defaults to empty, so the API contract advertises
    it as optional
  status: Verified
  severity: info
- local_id: F11
  title: repair --renumber leaves the scaffold hint naming the old number (pre-existing,
    for QA)
  status: Verified
  severity: info
- local_id: F12
  title: The depth option's min=0 makes Click say 'deep' is not a valid integer range;
    regression pins Click wording
  status: Verified
  severity: low
- local_id: F13
  title: unlink-role refusal says 'has no ref' when the skill holds another kind of
    ref to the role
  status: Verified
  severity: low
- local_id: F14
  title: Playbook guide command, README and CHANGELOG still give guide --tag after
    the --tags rename
  status: Verified
  severity: low
- local_id: F15
  title: 'create attribute options skip the --set coercion for list values: comma-joined
    and blank tags stored'
  status: Verified
  severity: low
- local_id: F16
  title: 'New create-attribute meta test cannot fail: it never reads the built CLI'
  status: Verified
  severity: info
- local_id: F17
  title: adopt --renumber does not say which item it gave a new number
  status: Open
  severity: low
- local_id: F18
  title: Same-id renumber leaves the scaffold hint on the old number
  status: Open
  severity: low
- local_id: F19
  title: CHANGELOG misstates what adopt --renumber moves and prints
  status: Open
  severity: low
created_at: '2026-10-29T17:02:38Z'
updated_at: '2026-10-29T20:03:06Z'
---
<!-- sq:body -->
## Scope

The 0.19 bug batch on `release/0.19`, sixteen bugs in three tasks:

- TASK-1244 (commits 5a6c61d3, 391a9d85): BUG-1187, BUG-1188, BUG-1189, BUG-1190, BUG-1191.
- TASK-1245 (commits f3fe8028, 9389aceb): BUG-1193, BUG-1194, BUG-1195, BUG-1196, BUG-1197, BUG-1200.
- TASK-1246 (commit 118cd69e): BUG-1183, BUG-1184, BUG-1185, BUG-1186, BUG-1240.

BUG-1192 is out of scope here (moved to TASK-1243).

## Method

- Read every diff, task, bug and handback, and the op-pierre rulings on BUG-1185.
- Drove each fix from the dev tree in scratch squads under the session scratchpad, against the released 0.17.0 tool where a comparison mattered. That covered: init, adopt and init `--force` over a corpus with a shared number, plus the `sq repair --renumber` remedy each message names; `migrate up` on a copy of the v0.14 fixture corpus with a shared number; `adopt`/`init --squad-dir` edge values; chlog range edges; `list`/`tree` badge and sort codes in mixed case; `--depth` wording; roster `ref rm` and `unlink-role`; an import with a missing `op` and a missing or blank sub-entity title; a hand-arranged untitled sub-entity through `show`, `update --status`, `body`, `comment`, `repair`, `subtasks --json` and `sq check`; and an override that declares a field on `guide` and `task`.
- Falsification (ADR-1172): a scratch worktree at 0ae6a3ab (no fixes) with HEAD's `tests/regressions/` copied in. All 22 regression cases fail, each on its own bug's symptom. In a scratch worktree at HEAD, the `_refuse_shared_numbers` call alone was reverted: the regression case and the `tests/cli/test_repair.py` case went red, then green again after the restore.
- In the HEAD worktree, `tests/meta` plus `tests/regressions` pass (710 passed). The full suite was not run (the main loop owns it).

## Judgment points

- **BUG-1191 remedy.** Plain `repair` over a corpus whose files share a number refuses and names `sq repair --renumber`. `init` (with or without `--force`) and `adopt` refuse before writing anything and name `sq adopt --renumber`, which needs no configuration. `migrate up` never reaches the new refusal, because its pre-runner fit check already refuses a shared number with hand-renumber instructions, which is the right answer on a behind-schema corpus where `sq repair` is gated. See F2.
- **repad width 32.** Thirty-two digits, a 60-character slug and a short prefix stay well inside 255 bytes. The bound is checked in the service before the index is loaded, so nothing is renamed.
- **`--depth deep`.** Click's `IntRange` gives "'deep' is not a valid integer range.", which reads as if a range were expected. See the findings.
- **BUG-1183.** `create guide` is still hand-written and is not built with the spec-aware create command class. Override-declared fields therefore do not reach it. This gap predates the batch (0.17.0 behaves the same), so it is not a regression, but ST1 asked for the derived form.
- **BUG-1185 on an existing untitled sub-entity.** Every read and every non-title write keeps working, and `sq check` stays silent. See the findings.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1247 add-finding "…" --severity medium`; track with `sq review 1247 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — migrate chlog still accepts non-version bounds such as v1x..v2y and answers no manual steps

<!-- sq:finding:F1:body -->
`_parse_span` in `src/squads/_cli/_migrate.py` checks each bound with `_VERSION = re.compile(r"\d[\w.+-]*")`. That pattern accepts letters and dots anywhere after the first digit, so a typo can still come back as "nothing to do", which is the defect BUG-1189 fixed. Driven on the dev tree:

- `sq migrate chlog v1x..v2y` prints `no manual steps for v1x..v2y` and exits 0.
- `sq migrate chlog v0.1.0..v0.2.0..v0.3.0` exits 0 and prints the v0.2.0 steps: the upper bound `0.2.0..v0.3.0` matches the pattern, and `version_tuple` falls back silently.

Fix: validate each bound against the PEP 440 pattern `version_tuple` already uses (`_util._VERSION_RE`, full match), not a looser pattern of its own. Add the `v1x..v2y` row to the existing parametrised surface case.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-29T17:17:48Z] `python-dev` Elias Python:
  - Fixed in 9dc8388a (branch worktree-agent-a4a27e01490d44cc2).
- [2026-10-29T19:09:52Z] `reviewer` Paul Reviewer:
  - Verified at cc772bc0 (1df93668): bounds go through is_version (the version_tuple pattern). Driven: v1x..v2y and v0.1.0..v0.2.0..v0.3.0 are refused with the range message; v0.1..v0.2 and a padded bound still answer. Both rows are in the surface case.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — init over a shared-number corpus writes .squads.toml before the repair refusal; a plain re-run is refused

<!-- sq:finding:F2:body -->
`init` writes `.squads.toml`, the root `.gitignore`, the squad folder and the empty index before it calls `svc.repair()`. Over a corpus whose files share a number, the new refusal therefore comes after those writes. Driven: a copy of a squad with TASK-14 and BUG-14, `.squads.toml` removed.

- `sq init --default-names --roles minimal` exits 1 with the refusal, which names `sq repair --renumber`.
- `.squads.toml` is now on disk. `sq repair --renumber` works, but running `sq init` again gives `.squads.toml already exists (use --force to overwrite)`, exit 1. Nothing tells the adopter that the first init stopped half-way, with no roles activated and no backend files.

This is the write-before-refuse shape of BUG-1187, reached through a different refusal. `adopt` is fine: a second `adopt` reads the config it wrote and completes after the renumber (driven). `init --force` is fine too.

Fix options: in `init`, when the folder already holds item files, run the shared-number check (`shared_number_groups` over the carriers) before the first write. Or make the refusal on this path say to run `sq init --force` again after `sq repair --renumber`. The first option matches what TASK-1244 set out to guarantee.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-29T17:17:49Z] `python-dev` Elias Python:
  - Fixed in 9dc8388a: init checks for shared numbers before it writes .squads.toml.
- [2026-10-29T19:10:39Z] `reviewer` Paul Reviewer:
  - Reopened at cc772bc0. The refusal now comes before any write (driven: no `.squads.toml` after the refused `init`), but the remedy it names cannot run on this path. Driven on a copy of a squad with TASK-23 and BUG-23, `.squads.toml` removed:
    
    - `sq init --default-names --roles minimal` exits 1: "... run `sq repair --renumber` to give one of them a new number".
    - `sq repair --renumber` then exits 1: "no .squads.toml found in this or any parent directory — run `sq init`". The two messages send the adopter in a loop.
    - `sq init --force` gives the same refusal.
    - The only way out found: `sq adopt` (refused, but it writes the config), then `sq repair --renumber`, then `sq adopt` again. Nothing says so.
    
    Fix: on the init path, name a remedy that works without a configuration. Either init writes the config and the refusal says to run `sq repair --renumber` then `sq init --force`, or the refusal on init names the adopt sequence. Add the follow-through (run the named remedy, then init again) to the regression case, so it proves the remedy and not only the refusal.
- [2026-10-29T19:14:48Z] `python-dev` Elias Python:
  - Fixed in b742e368: init names the adopt, repair --renumber, adopt sequence; the regression follows it to a successful adopt.
- [2026-10-29T19:21:08Z] `reviewer` Paul Reviewer:
  - Kept Open at 1ad3f7b5: the remedy now runs end to end (D: init refused, then `sq adopt` refused, `sq repair --renumber` gave TASK-17, `sq adopt` succeeded), but it is not the simplest rule an adopter can predict.
    
    - Step 1 works only because a refused `sq adopt` writes `.squads.toml` and `squads/.squads.json` before it stops (D: both present after the refusal). The regression module's own docstring says a refused init or adopt writes nothing, and the new test now pins that half-write as a step. If adopt is ever made to refuse before writing, as init does, the remedy breaks.
    - Proposal, one step: `sq adopt --renumber` runs the adopt rebuild as `repair(renumber=True)` (the service already takes the flag). Plain `sq adopt` checks shared numbers before writing anything, as init does. Both refusals then name the same single command: run `sq adopt --renumber`. Size S: one option, one argument, two message strings, and the regression test drives the one command.
    - If a new option is out of scope for 0.18.1, the fallback is to keep the current text and record the half-written refused adopt as a separate finding. I would still prefer the option.
- [2026-10-29T19:24:54Z] `python-dev` Elias Python:
  - Fixed in ac46f4c4: plain adopt and init refuse before writing and name sq adopt --renumber; adopt --renumber resolves and adopts in one step.
- [2026-10-29T19:49:18Z] `reviewer` Paul Reviewer:
  - Verified at 7ed41e73. Driven on a scratch squad (TASK-14 and BUG-14 sharing a number, no `.squads.toml`, no index, no `.gitignore`): `sq init`, `sq adopt` and `sq init --force` each exit 1 with the refusal naming `sq adopt --renumber`, and `diff -r` against a pristine copy shows nothing written. `sq adopt --renumber` then exits 0 (TASK-14 moved to TASK-15), `sq check` exits 0, and a later plain or `--renumber` adopt exits 0. Targeted tests: 61 passed. Falsified in a scratch worktree: dropping adopt's pre-write check turns the regression case red; dropping `renumber=renumber` from the repair call turns it and the new `tests/cli/test_adopt.py` case red. One gap in the new option's output is filed as F17.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — create guide skips the spec-aware create class: override fields and the --priority help refresh miss it

<!-- sq:finding:F3:body -->
`create guide` gained hand-added `--priority`, `--label` and `--ref`, and the reported bug is fixed: the options work and show on `guide N show --json`. It is still registered with no `cls=_create_command_cls("guide")`, unlike every `_make` command, and so are its hidden aliases. Two consequences:

- An override-declared field on `guide` gets no option. Driven with an override declaring `sev` (severity) on both `task` and `guide`: `create task --help` lists `--sev`, while `create guide g --sev high` is refused with `No such option: --sev`.
- The new `--priority` help is computed once from the bundled spec. `_refresh_priority_help` never runs for guide, so an override that drops guide's priority field leaves the flag visible and its help stale, where the other types hide it.

This predates the batch (0.17.0 behaves the same), so it is not a regression. But ST1 asked for the derived form ("so a field declared on guide in an override also reaches it"), and the handback does not say why it was not done. Fix: register `create_guide` and its aliases with `_create_command_cls("guide")`, take `ctx`, and pass `fields=_given_fields(ctx) or {}`.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-29T17:09:28Z] `manager` Catherine Manager:
  - Root cause: the generic create command derives options from badge fields only, not from the attributes a type declares ([items.<type>.attributes]); guide declares tags and tech, so it was excluded by a guide literal in _cli/_create.py and kept as a copy that drifted (BUG-1183). Fix: generic create derives one option per declared create-time attribute; drop the guide exclusion, its hand-written command and the guide exception in the tests/meta guards; ADR-1172 rule 2 wording needs the architect.
- [2026-10-29T19:09:54Z] `reviewer` Paul Reviewer:
  - Verified at cc772bc0 (e3bb9356, 14c77354): create guide is built by the shared create class and its aliases with it. Driven with an override declaring field sev and attributes audience (str) and due (date) on guide: create guide --help lists --sev, --tags, --tech, --audience, --due; all write; create g takes --sev; with the override dropping priority, --priority leaves the help. The verb-set guard now fails a create command the shared builder did not build.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Existing untitled sub-entities stay invisible: sq check does not report the now-required title

<!-- sq:finding:F4:body -->
The op-pierre ruling makes the title required on add, update and import, and those writes now refuse a missing or blank title. On an adopter corpus that already holds an untitled sub-entity, nothing reports it. Driven on a scratch squad, with ST1's `title: ''` arranged in the frontmatter:

- `show --full` renders `=== ST1 —   ⚪ Todo ===` and an empty Title cell. `update --status InProgress`, `body -m`, `comment`, `repair` and `subtasks --json` (`"title": ""`) all exit 0.
- `sq check` reports nothing about it.

So "required everywhere" holds for writes only: an existing violation is invisible until someone tries to retitle it. Either add a `sq check` rule (warning, remedy `sq <type> N <kind> K update --title "…"`), or record a ruling that pre-existing untitled sub-entities are tolerated. The dev's handback asked the same question, and it is still open. The tech writer needs the answer for the changelog line.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-29T19:09:57Z] `reviewer` Paul Reviewer:
  - Verified at cc772bc0 (14c77354): subentity_title_present (warn, work bundle). Driven: an empty subtask title on a task and a whitespace-only finding title on a review are each reported with the update --title remedy; running the named remedy clears both. Falsified in a scratch worktree: with the rule emptied, both tests/check cases go red; restored, green.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — import with no op still prints pydantic wording: Unable to extract tag using discriminator 'op'

<!-- sq:finding:F5:body -->
`_validation_message` in `src/squads/_services/_import_model.py` rewrites `union_tag_invalid` (an unknown `op`) and drops the empty-location separator. A line with no `op` at all raises `union_tag_not_found`, which still prints pydantic's text. Driven: `{"as":"manager"}` gives `line 1: Unable to extract tag using discriminator 'op'`.

This is the same defect as BUG-1200 (pydantic wording instead of squads' own) one error type over. Fix: map `union_tag_not_found` to, for example, `missing op; valid ops: …`, and add the case to the regression test.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-29T17:13:11Z] `python-dev` Elias Python:
  - Fixed in 50277923: a line with no op reads "missing op; valid ops: ..."; regression test added.
- [2026-10-29T19:09:59Z] `reviewer` Paul Reviewer:
  - Verified at cc772bc0 (e07a89b8): a line with no op reads "missing op; valid ops: ..." (driven), with a regression case asserting the whole output.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Several new refusal cases assert a prefix or exit code instead of the whole output (ADR-1172 rule 5)

<!-- sq:finding:F6:body -->
ADR-1172 rule 5 (assert the exit code and the whole message or JSON) is applied for most cases, but several new cases assert a fragment:

- `tests/cli/test_tree.py::test_depth_refuses_a_negative_value` and `tests/cli/test_graph.py::test_depth_refuses_a_negative_value`: `any("Invalid value for '--depth'" in line ...)`.
- `tests/cli/test_reflog.py::test_op_refuses_an_operation_the_log_does_not_know`: `startswith("error: unknown operation 'ghost' (one of: create, ")`. The regression module asserts the whole line, so the surface case can too.
- `tests/cli/test_init.py::test_squad_dir_refuses_an_absolute_empty_or_escaping_folder` and the regression `test_an_unusable_squad_folder_leaves_the_folder_untouched_for_the_retry`: `startswith("error: --squad-dir must ")` plus a line count. Three different messages, none of them pinned.
- `missing.exit_code == 2` with no output, in both `test_add_refuses_a_missing_or_blank_title` and `test_a_subtask_cannot_be_added_without_a_title_or_with_a_blank_one`.
- `tests/regressions/...unknown_value...::test_a_negative_depth_is_refused`: one box line, `out[3]` (see the `--depth` finding).

Each of these passes for a wrong refusal that happens to share the prefix. Fix: assert the full output for each.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-29T17:13:14Z] `python-dev` Elias Python:
  - My part fixed in 50277923: negative --depth on tree/graph and reflog --op assert the whole output. Other cases in this finding are not mine; left Open.
- [2026-10-29T17:17:50Z] `python-dev` Elias Python:
  - TASK-1244 part done in 9dc8388a: the --squad-dir refusals assert the whole output. Other tasks parts remain.
- [2026-10-29T17:25:39Z] `python-dev` Elias Python:
  - Missing-title exit-2 cases now assert the whole output (0553c825). Other F6 cases belong to TASK-1244 and TASK-1245.
- [2026-10-29T19:10:12Z] `reviewer` Paul Reviewer:
  - Verified at cc772bc0 (1df93668, e07a89b8, 14c77354): every case listed here now asserts the exit code and the whole output: tree/graph negative depth, reflog --op, init --squad-dir (surface and regression, one message per value), both missing-title exit-2 cases, and the regression negative depth.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — No tests/cli boundary case for a comment on a missing sub-entity, nor for an adopt --squad-dir refusal

<!-- sq:finding:F7:body -->
Two refusals added in this batch have no surface case in `tests/cli`. ADR-1172 rule 1 asks for each pair's boundary refusals, and only regression cases cover these, which ADR-1172 says do not stand in for surface coverage:

- A comment on a missing sub-entity (BUG-1186). TASK-1246 ST4 named `tests/cli/test_comment_verbs.py` for it, and no case was added there. The only case is `tests/regressions/test_comment_on_a_missing_subentity_names_it.py`.
- `adopt --squad-dir` with an absolute, empty or escaping value. `_checked_squad_dir` guards adopt too (driven: `../up`, blank and `a/../../x` are all refused), but only `init --squad-dir` has a refusal case.

Fix: one case each, with `covers` on the sub-entity comment host key and on `("adopt", "--squad-dir")`.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-29T17:17:51Z] `python-dev` Elias Python:
  - TASK-1244 part done in 9dc8388a: adopt --squad-dir boundary case added. The sub-entity comment case belongs to the other task.
- [2026-10-29T17:25:38Z] `python-dev` Elias Python:
  - Missing sub-entity comment boundary case added in tests/cli/test_comment_verbs.py (0553c825). The adopt --squad-dir half belongs to TASK-1244.
- [2026-10-29T19:10:15Z] `reviewer` Paul Reviewer:
  - Verified at cc772bc0: tests/cli/test_adopt.py has the adopt --squad-dir refusal (1df93668) and tests/cli/test_comment_verbs.py the comment on a missing subtask (14c77354), each with whole-output asserts and covers markers.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — tests/regressions: eight duplicated fixtures, one module holding two bugs, uneven docstrings

<!-- sq:finding:F8:body -->
Layout of `tests/regressions/`, written by three devs in parallel:

- Seven modules each define a local `populated` / `populated_project` fixture (`copy_squad("populated", init_populated)`), identical to `tests/cli/conftest.py::populated_project`, and one more redefines `readable`. A `tests/regressions/conftest.py` holding `populated_project` (and `readable`) removes eight copies. That is real duplication, and the set will only grow.
- `test_a_hit_that_repeats_the_summary_shows_once.py` also holds the import unknown-op test (BUG-1200). The module is named for one behaviour and holds two, against the "named for the behaviour the bug broke" rule. Move the import case to a module of its own.
- BUG-1194 got two regression tests (unknown value, unknown field) where one parametrised test would do.
- The five TASK-1246 modules have no module docstring, while the others do. A one-line docstring keeps the set consistent.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-29T17:30:54Z] `python-dev` Elias Python:
  - Fixed in eaaac5a7: shared fixtures in tests/regressions/conftest.py, helpers moved to tests/, memory-search and import tests split, badge cases merged, docstrings on every module. Also removed the dead hand-written-create branch in tests/_cli_surface.py fold_path.
- [2026-10-29T19:10:18Z] `reviewer` Paul Reviewer:
  - Verified at cc772bc0 (6be4facd): tests/regressions/conftest.py holds the shared fixtures, no module redefines one, the import cases have their own module, the BUG-1194 cases are merged and every module has a docstring.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — unlink-role on a skill not scoped to the role still reports success, the BUG-1184 shape

<!-- sq:finding:F9:body -->
`rm_ref` gained `missing_ok`, and `unlink_role` passes `missing_ok=True`. So `sq skill <slug> unlink-role <role>` on a skill that is not scoped to that role still reports success. Driven twice in a row on the same skill: `SKILL-12 unscoped from ROLE-1 (role resynced)`, exit 0 both times.

That is the false success line BUG-1184 removed from `ref rm`, kept on purpose on a sibling verb. Either refuse it like `ref rm` (`SKILL-12 is not scoped to ROLE-1`), or keep it idempotent but say so (`already unscoped`). Needs a decision rather than a silent default.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-29T19:10:20Z] `reviewer` Paul Reviewer:
  - Verified at cc772bc0 (14c77354): unlink-role on an unscoped skill exits 1 (driven twice in a row; regression and surface cases). The refusal text is wrong when the skill holds another kind of ref to the role: see F13.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — SubentityAddRequest.title still defaults to empty, so the API contract advertises it as optional

<!-- sq:finding:F10:body -->
`SubentityAddRequest.title` in `src/squads/_api/_dto/_item_writes.py` still defaults to `""`. The API contract, and the OpenAPI document the daemon serves from it, therefore advertise the title as optional, while the service now refuses a blank one with `title must not be empty`. A remote client finds out only from the refusal. Make the field required, as the import event models now do.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-29T19:10:23Z] `reviewer` Paul Reviewer:
  - Verified at cc772bc0 (14c77354): SubentityAddRequest JSON schema now lists title as required (id, kind, title).
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — repair --renumber leaves the scaffold hint naming the old number (pre-existing, for QA)

<!-- sq:finding:F11:body -->
The batch makes `sq repair --renumber` the remedy that `repair`, `init` and `adopt` name. Driven on a scratch squad: after the renumber moved TASK-14 to TASK-15, the task's scaffolded hint above the sub-entity region still reads `_Add with sq task 14 add-subtask "<title>"; track with sq task 14 subtask <n> update --status <Status>._`. That command now addresses the other item (BUG-14 holds number 14).

This predates the batch and is outside its scope. Recorded so it gets a disposition: it belongs to QA as a bug against renumber.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-29T17:11:42Z] `qa` Mara Tester:
  - Filed as BUG-1248 (reproduced on both repair --renumber and sq renumber).
- [2026-10-29T19:10:25Z] `reviewer` Paul Reviewer:
  - Verified at cc772bc0 via BUG-1248 (1df93668): driven, repair --renumber moved TASK-22 to TASK-23 and its add/track hint now names 23; sq renumber --by is covered by tests/cli/test_renumber.py. Falsified in a scratch worktree: with _rehint short-circuited, the surface and regression cases go red; restored, green. File read allowed by the op-pierre rule 5 exception on ADR-1172.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — The depth option's min=0 makes Click say 'deep' is not a valid integer range; regression pins Click wording

<!-- sq:finding:F12:body -->
`depth_option` gained `min=0`, so Click now types `--depth` as `IntRange`. A non-integer is now refused with Click's range wording: `Invalid value for '--depth': 'deep' is not a valid integer range.` (driven on `tree` and `graph`; 0.17.0 says `'deep' is not a valid int.`). The user gave a word, not a range, so the message names the wrong problem. Two surface goldens were updated to the new wording rather than questioned.

`test_a_negative_depth_is_refused` in `tests/regressions/` pins Click's own phrasing (`-1 is not in the range x>=0.`) as the contract, and only one box line of it. A Click upgrade that rewords it turns the test red with no squads defect.

Fix: keep the plain `int` type and refuse a negative value in a callback (`typer.BadParameter("must be 0 or more")`). Assert the whole refusal in the surface and regression cases.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-29T17:13:13Z] `python-dev` Elias Python:
  - Fixed in 50277923: depth uses a callback refusing negatives ("must be 0 or more"); a non-integer keeps the plain integer message; goldens and regression pin our wording.
- [2026-10-29T19:10:28Z] `reviewer` Paul Reviewer:
  - Verified at cc772bc0 (e07a89b8): plain int with a callback. Driven: deep gives "is not a valid integer.", -2 gives "must be 0 or more" on tree and graph (-d too); goldens and the regression assert the whole box.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — unlink-role refusal says 'has no ref' when the skill holds another kind of ref to the role

<!-- sq:finding:F13:body -->
`unlink_role` calls `rm_ref(..., kind=<scopes>)`, and `rm_ref` refuses with "`<id>` has no ref to `<target>`" whatever kind it was asked to remove. When the skill holds another kind of ref to the role, the message is false. Driven at cc772bc0:

- `sq skill deploy-notes ref add ROLE-1 --kind related`, then `sq skill deploy-notes refs` shows `→ refs  ROLE-1  related`.
- `sq skill deploy-notes unlink-role manager` exits 1 with `error: SKILL-24 has no ref to ROLE-1`.

The refusal itself is right (op-pierre ruling on F9). Fix: when `kind` is given, name it, for example `SKILL-24 is not scoped to ROLE-1` from `unlink_role`, or `has no scopes ref to ROLE-1` from `rm_ref`. Add the related-edge case to the existing surface case's file.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-10-29T19:21:09Z] `reviewer` Paul Reviewer:
  - Verified at 1ad3f7b5. D: with only a related ref, unlink-role prints "SKILL-3 has no scopes ref to ROLE-1" and exits 1. The new tests/cli case fails against the earlier refs code and the related ref survives. With kind=None the message keeps the old wording.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Playbook guide command, README and CHANGELOG still give guide --tag after the --tags rename

<!-- sq:finding:F14:body -->
The op-pierre ruling renamed guide's `--tag` to `--tags`, but three texts still give `--tag`:

- `src/squads/_specs/playbook.toml:416`: `sq create guide "…" --author architect [--tech …] [--tag …]`. This is generated agent guidance: `sq skill sq-guide show` on a fresh scratch squad prints it (line 19), and running it gives `No such option: --tag`.
- `README.md:300`: "guides take `--tech`/`--tag` in place of `--label`/`--ref`/`--priority`". Both halves are false: guides take `--tags`, and they take `--label`, `--ref` and `--priority` like every type.
- `README.md:339`: `sq create guide TITLE [--tech] [--tag]`.

`CHANGELOG.md` has no 0.19.0 entry yet for the rename, which the ruling asked for as one breaking line, nor for `--target-date`/`--target-ref`. Fix: the playbook line with the dev (it regenerates the skill, so `sq sync` and the template manifest follow); README and CHANGELOG with the tech writer.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-10-29T19:21:15Z] `reviewer` Paul Reviewer:
  - Still Open, as planned: it ships with the version bump. The dev updates the playbook guide command and @tech-writer updates the README and CHANGELOG lines that still give guide --tag.
- [2026-10-29T19:48:37Z] `python-dev` Elias Python:
  - Code half done in 1a0e8a8c: playbook.toml names --tags, version bumped to 0.19.0 with the manifest 0.19.0 entry appended (0.18.0 entry byte-identical to the tag), CHANGELOG heading renamed. README and changelog entries remain for the tech writer.
- [2026-10-29T19:55:26Z] `tech-writer` Theo Writer:
  - README/CHANGELOG half done (uncommitted, for the manager): README create synopsis now lists `--<attribute> VALUE` with guide `--tech`/`--tags`, milestone `--target-date`, review `--target-ref`; the guide line gives `--tags` and the shared create options; adopt synopsis gains `[--renumber]`; repair line says shared numbers are refused. CHANGELOG 0.19.0 has the batch: Added (attribute create options, adopt --renumber, subentity_title_present), Changed (BREAKING guide --tags, required sub-entity titles, ref rm/unlink-role refusals; repair/init/adopt shared-number refusal; filter, chlog, depth, repad, squad-dir, backend and workflow view refusals), Fixed (renumber hints, missing sub-entity comment, import op messages, memory search). @manager
- [2026-10-29T20:02:53Z] `reviewer` Paul Reviewer:
  - Verified at 10938808: playbook.toml:416 gives --tags; README 285-345 and the CHANGELOG carry the --tags rename and --target-date/--target-ref; create guide --tag exits 2, --tags a,b --tags c stores a, b, c. The repo own sq-guide skill still says --tag until it is re-synced with 0.19 (release runbook). New CHANGELOG wording issues are F18 and F19.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — create attribute options skip the --set coercion for list values: comma-joined and blank tags stored

<!-- sq:finding:F15:body -->
`_coerced_create_attributes` (`src/squads/_services/_item_write_ops.py`) says each value is "checked as `update --set` checks it ... a list as its parts", but a value that arrives as a list is stored without coercion. Driven at cc772bc0:

- `sq create guide G --tags a,b --tags c` stores `["a,b", "c"]`, while `sq guide N update --set tags=a,b` stores `["a", "b"]`. The flag and the key now share a name, so the two read alike and parse differently.
- `sq create guide G2 --tags "" --tags " "` stores `["", " "]`; `update --set "tags= , "` stores `[]`.
- Read, not driven: through the API, a list sent for a `str` attribute (`"tech": ["a"]`) skips `coerce` and is stored as a list.

Blank list values predate this batch (the old `--tag` stored them too), but the new helper claims the `--set` checks and its list branch skips them. Fix: coerce each element of a list value (strip, drop blanks, decide on comma splitting so both doors agree) and refuse a list for a non-list attribute; or narrow the docstring to what it does.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-29T19:21:11Z] `reviewer` Paul Reviewer:
  - Verified at 1ad3f7b5. Create now coerces through coerce_attribute, the same function update --set uses. D: `--tags 'x, y' --tags ' ' --tags z` stores [x, y, z]; a blank-only `--tags` stores [], as `update --set 'tags= '` does; `--target-date soon` is refused. A list given for a single-valued attribute is refused. The new test fails against the old coercion.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — New create-attribute meta test cannot fail: it never reads the built CLI

<!-- sq:finding:F16:body -->
`tests/meta/test_every_create_attribute_option_writes_a_settable_attribute.py` replaced the scan of hand-written create assignments. It computes the settable `str`/`list`/`date` attributes from the bundled spec and asserts three of them are present. It never reads the built CLI, and `_declared_attribute_options` already filters on `settable`, so the property in its name holds by construction. Mutation, read not run: dropping the `settable` filter from `_declared_attribute_options` leaves it green, and the verb-set guard does not catch it either, since no bundled creatable type declares a non-settable attribute.

What it does pin is that the bundled spec keeps those three attributes settable, a spec shape the surface cases in `tests/cli/test_create.py` already exercise. Under ADR-1172 a test that cannot fail on its subject is a finding. Fix: delete it, or make it build `create <type>` against a spec with a non-settable attribute and assert no flag is derived for it.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-10-29T19:21:13Z] `reviewer` Paul Reviewer:
  - Verified at 1ad3f7b5. The guard now reads the real `create guide --help` under an override, so it can fail. Falsified in a git-archive extract: dropping the settable check, and dropping str from CREATE_ATTRIBUTE_KINDS, each turn it red; the restored code turns it green.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — adopt --renumber does not say which item it gave a new number

<!-- sq:finding:F17:body -->
`sq adopt --renumber` gives a file a new number without saying which. Driven: over TASK-14 and BUG-14 it moved TASK-14 to TASK-15, and the panel said only "imported: 15 existing item(s)". `sq repair --renumber` prints one line per moved item (`render_repair` prints `report.renumbered`), but `AdoptReport` has no field for those lines, so neither the panel nor `--json` shows them. An adopter whose commits or documents cite TASK-14 has no way to learn it moved, other than diffing the folder.

Fix: carry the repair's renumbered lines on `AdoptReport` and print them in the adopt renderer as `render_repair` does. Assert the line in `test_renumber_gives_a_shared_number_a_new_one_and_adopts`.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-10-29T19:54:49Z] `python-dev` Elias Python:
  - Fixed in bfb2896e: AdoptReport.renumbered, printed like repair; repair now also lists distinct-id moves.
- [2026-10-29T20:02:39Z] `reviewer` Paul Reviewer:
  - Reopened at 10938808. The human output is right: adopt and repair now print each move. The JSON shape is presentation, not data. Driven (adopt --renumber --json over a same-id pair and a cross-type pair):
    
    ```
    "renumbered": [
      "TASK-18: 2 files, different slugs",
      "  kept       tasks/TASK-000018-beta.md",
      "  renumbered tasks/TASK-000018-beta-copy.md -> TASK-20 (tasks/TASK-000020-beta-copy.md)",
      "  no references",
      "  renumbered TASK-17 -> TASK-21"
    ]
    ```
    
    Two line formats, a heading row, indentation and column padding: a client has to parse the renderer's layout back into ids. ADR-1224 point 2 makes the DTO the data the renderer displays, and the sibling `renumber` already carries the same fact as data (`moved: [{old, new}]`). My fix text asked for the lines; that was the wrong prescription.
    
    Repair has the same defect: its `renumbered` (0.18, provisional in docs/stability.md) already held the same-id block as lines, and eaf82823 appends the cross-type lines to it.
    
    Expected shape, on both `RepairReport` and `AdoptReport`:
    - `renumbered: [{old, new, file, target}]`, one per moved file, cross-type and same-id alike (`file`/`target` are the paths, needed because a same-id `old` names two files);
    - `references: [{id, file, where, text}]`, the references to an old id left unchanged; `references_left` stays as is.
    The renderers build today's lines from these. Repair's retype is a schema change on a provisional shape; it rides the open 0.19 migration. The CHANGELOG line ("a renumbered array holding those lines") follows the fix. S.
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — Same-id renumber leaves the scaffold hint on the old number

<!-- sq:finding:F18:body -->
`sq repair --renumber` and `sq adopt --renumber` leave the scaffold hint on the old number when the collision is a same-id pair (two files with id TASK-18, different slugs). Driven at 10938808 on a scratch squad: repair moved `tasks/TASK-000018-beta-copy.md` to TASK-21, and TASK-000021-beta-copy.md still reads `_Add with sq task 18 add-subtask "<title>"; track with sq task 18 subtask <n> ..._`. TASK-18 is the kept twin, so the hint addresses another item, the BUG-1248 symptom.

The BUG-1248 fix covers the cross-type path (`_renumber`, driven: TASK-17 -> TASK-20 gets `sq task 20`) and `sq renumber`. The same-id path, `_renumber_files` in `src/squads/_services/_duplicate_ids.py`, rewrites only `id`, `sequence_id` and the file name. The CHANGELOG Fixed entry ("`sq renumber` and `sq repair --renumber` update the hint") is false for this case.

Fix: apply the same hint rewrite in `_renumber_files` (an edited hint left as is, as elsewhere), with a regression case for the same-id pair. S.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — CHANGELOG misstates what adopt --renumber moves and prints

<!-- sq:finding:F19:body -->
Two CHANGELOG 0.19.0 Added entries misstate `--renumber`, checked against the driven behaviour at 10938808:

- "`sq adopt --renumber`. It gives every file that shares a number with a file of another id a new number". It keeps one file of each collision and moves the others, and it also moves same-id twins (two files carrying TASK-18 with different slugs), which the sentence excludes. The README adopt line ("`--renumber` gives them new numbers first") reads the same way.
- "Each item given a new number prints one line, such as `renumbered TASK-24 -> TASK-28`". A same-id move prints a four-line block (`TASK-18: 2 files, different slugs`, `kept ...`, `renumbered <file> -> TASK-20 (<file>)`, references). The `--json` half of that entry follows F17.

Every other claim in the section and in README lines 282-345 holds at HEAD (see the review comment). @tech-writer, after F17 and F18 land. S.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T17:06:17Z] `reviewer` Paul Reviewer:
  - Verdict: ChangesRequested. All sixteen fixes are correct as reported, and each regression test was shown red against the unfixed code. Requested: F1, F2, F5 and F12 (residues of the bugs fixed here) and F6, F7 (ADR-1172 assertion and boundary gaps). F3, F4 and F9 need a fix or a ruling. F8, F10 and F11 are info. F11 belongs to QA as a bug. @python-dev @manager
- [2026-10-29T17:08:52Z] `op-pierre` Pierre Chat:
  - 2026-10-29 rulings: F4: add an sq check rule flagging a sub-entity with no title, naming the update --title remedy; no migration. F9: skill unlink-role refuses (exit 1) a skill not scoped to the role, like ref rm. F3: create guide is derived from the spec like the other types, in this batch; adapt the tests/meta guards for its guide-only --tag and --tech.
- [2026-10-29T17:08:53Z] `manager` Catherine Manager:
  - Fix routing: TASK-1244 dev: F1, F2, F7 (adopt --squad-dir), F6 (squad-dir cases), F11 once QA files it. TASK-1245 dev: F5, F12, F6 (depth, reflog cases). TASK-1246 dev: F3, F4, F9, F10, F7 (missing sub-entity comment), F6 (missing-title cases). F8 (tests/regressions conftest, helpers out of tests/cli, module split, docstrings) runs after the three land, to avoid conflicts.
- [2026-10-29T17:19:31Z] `op-pierre` Pierre Chat:
  - 2026-10-29: a create option derived from a declared attribute is named --<key>: guide --tag becomes --tags (breaking, one CHANGELOG line). milestone --target-date and review --target-ref follow the same rule.
- [2026-10-29T17:39:37Z] `architect` Robert Architect:
  - Vocabulary audit (architect, 2026-10-29): bundled type/kind/field words and per-type surfaces outside `_specs/`, `_migrations/` and tests. Read at 6be4facd; driven against the dev tree on a scratch squad whose override drops epic/feature/task/contract/guide and story/subtask, and adds `initiative` (INI, kind `outcome`/OC, field `urgency` on the priority collection) and `job` (JOB, parent_required initiative, kind `action`/AC with maps_parent_story and field `impact`). D = driven, R = read, I = inferred.
    
    | # | Location | What | Class | Evidence | Fix, size |
    |---|---|---|---|---|---|
    | 1 | `_cli/_create.py:50-80,375`, `_api/_dto/_item_writes.py:28` | `create --priority` is still a static option; the derived `--<code>` path skips it (`taken`) | gap, same family as `create guide` | R: `_declared_field_options` docstring says "--priority is a static option". D: create help shows only `--urgency` | Drop the static option and `ItemCreateRequest.priority`; priority goes through the derived path. S |
    | 2 | `_cli/_items.py:190-210,393-477`, `ItemUpdateRequest.priority/clear_priority`, `_services/_base.py:1329`, `_services/_items.py:262-310` | item `update --priority/--no-priority` is hand-written, and no `--<code>` is derived | gap. ADR-323 §5 allows it on the grounds that Typer options are fixed at import, but create and `add-<kind>` disprove that | D: `initiative 2 update --urgency low` gives "No such option"; `--set urgency=low` works; `--no-priority` on a type with no priority field exits 0 "updated" | Derive `--<code>`/`--no-<code>` the way sub-entity update does, delete the dedicated fields, supersede ADR-323 §5. M |
    | 3 | `_cli/_main.py:80-94,342-427` | list/tree `--priority`/`--min-priority` sugar | gap (ADR-323 §5) | D: in a squad with no priority field, `list --priority high` and `--min-priority high` print "no items" and exit 0; `--badge bogus=x` lists "urgency, priority, severity" as valid | Drop the sugar (or derive it from the first ordered field) and refuse codes no type declares. S |
    | 4 | `_services/_item_dto.py:28-36` | `LIST_COLUMNS` has a fixed "Priority" column keyed `display.badges.priority` | gap | D: `sq list` shows an empty Priority column for INI-2 (urgency=high); `sq tree` shows "🟠 high" | Derive the column and its header from `first_ordered_field`. S |
    | 5 | `_api/_dto/_tree.py:47`, `_graph.py:37`; VS Code `domain/graphDiagrams.ts:152` | `priority` key on tree/graph nodes; the VS Code graph label reads only that key | key frozen (stability Tier 3, tree/graph tables); client gap | D: `tree --json` gives `priority: null`, `badges: {urgency: high}`. R: client | Keep the key. Have the client label from `badges`/`display`. S |
    | 6 | `_models/_attributes.py` CORE_KEYS, `Item.priority/severity`, `SubEntity.severity`, `_validity._FIELD_ELIGIBLE_*` | priority/severity are core frontmatter keys and typed slots | frozen (Tier 1 "Frontmatter is flat", ADR-323 §4) | R | None before a major release. Record it as debt. |
    | 7 | `_workflow/_models.py:96-121`, `_cli/_common.py:330-400`, `_validity.py:418-435` | `RESERVED_CLI_ALIASES` keeps bundled aliases reserved even after their owner type is dropped | gap. Tier 2 freezes what the bundled aliases mean, not a reservation in a squad that dropped the owner | D: `initiative.aliases = ["i","f"]` with feature dropped makes spec load refuse: "alias 'f' shadows the built-in sq f alias of the 'feature' command" | Resolve root aliases from the active spec and keep the table only as a guard for bundled squads. M |
    | 8 | `_workflow/_models.py:625-634,1110-1125` | `_BUNDLED_CONTAINER_HEADINGS` (story to "User Stories", …) | gap, minor | D: a new kind gets `plural.title()` ("## Actions"); no spec key sets a heading | Add `heading` to SubentityKindSpec, declare the three in the bundled spec, delete the table. S |
    | 9 | `_cli/_items.py:850-1002`, `_services/_subentities.py:560-702`, `_discussion.py:519`, `_cli/_render/_subentities.py:32`, `subentities/head.md.j2` | story-mapping wording: `--story/--no-story`, help "as US<n>", "user story X not found", "subtasks still map to it", "don't map to a parent story", the "Story" column, the "story:" label, "Implements:" | gap in wording. ADR-348 §7 keeps the mechanism as a bounded built-in | D: AC→OC1 mapping works; `add-action --help` reads "--story … as `US<n>`"; `--story OC9` gives "user story OC9 not found in INI-2"; table header and show print Story/story | Name the option, column and messages after the target kind (`--outcome`, with `--story` kept as an alias) and take the help from the target `local_prefix`. ADR superseding 348 §7. M |
    | 10 | `SubEntity.story`, `SubentityAdd/UpdateRequest.story/clear_story`, `display.story`, `AddSubEvent.story`; VS Code `types.ts:227`, `previewDocument.ts:764`; TUI `_reader.py:101` | `story` as a storage/wire key | frozen (Tier 1 §"Sub-entity state lives in frontmatter"; Tier 3 sub-entity row `story`) | D: `actions --json` gives `"story": "OC1"` | Keep the keys. Clients take the label from the target kind ("Story:" is hardcoded in VS Code). S |
    | 11 | `_services/_validators.py:428-430`; validator `subtask_story_mapping`; spec key `maps_parent_story` | `or "story"` fallback; bundled words in grammar names | names frozen (validator catalog is override grammar; `maps_parent_story` is in Tier 3 subentity-kinds json); fallback is a gap | R: with no parent_required, `host="parent"`, so the kind lookup returns None and the message says "story" | Use the actual parent's kind for the fallback. Add neutral alias names later. S |
    | 12 | `_services/_import_model.py:101-170`, `_services/_import.py:128-148` | import fronts `add-story/add-subtask/add-finding`; comment selectors `story/subtask/finding` | gap. ADR-622 allows them; not in stability Tier 2 | D (dry-run): `add-story` on INI-2 gives "is a initiative, which does not host storys (initiatives host outcomes)"; there is no `add-outcome`; `"story":"OC1"` gives "no story OC1 in JOB-3"; generic `add-sub` and `sub` accepted | Make the fronts aliases of `add-sub`/`sub` and stop documenting them, or derive `add-<kind>` per declared kind. Amend ADR-622. M |
    | 13 | `templates/workflow.md.j2:89`, `views/squads_skill.md.j2:25-29,121` | alias example `sq f 26 story 4 show`; "(story/subtask/finding blocks)"; `_kind_notes` keyed by bundled kinds | gap (generated agent guidance) | D: scratch `sq skill squads show` carries both lines (152, 210); `sq f 2 show` refuses there | Build the example from the first aliased type and its kind; drop the parenthetical. S |
    | 14 | `templates/items/review.md.j2:17` | hint hardcodes `sq review` (feature/task use `item.type`) | harmless | R | Use `item.type`. S |
    | 15 | `templates/items/{epic,…}.md.j2` | per-bundled-type templates | harmless default | D: initiative/job render from `_default` with "## Outcomes"/"## Actions" | None. |
    | 16 | `_workflow/_lifecycle_order.py:14-20` | `_SIDE_PRIORITY` keyed by WontFix/Blocked/Cancelled/Rejected/Deprecated | harmless (display tie-break), but bundled vocabulary in code | R | Order by status role or declaration order. S |
    | 17 | `_badges.py:64` | `primary_field_code(default="severity")` | harmless fallback | R | Default to None; the template guards. S |
    | 18 | `_discussion.set_head` + `subentities/head.md.j2` (typed severity/story slots) | only caller is `_migrations/_v0_2_to_v0_3.py` | harmless (migration-only code outside `_migrations`) | R: rg finds that one caller | Move it under `_migrations`. S |
    | 19 | `_models/_attributes.py:59-62` | `AttributeKey.TAGS` (guide), `TARGET_REF` (review) | harmless, dead | R: no reference | Delete. S |
    | 20 | `_validators.py:878` | "no incoming supersedes edge found" | gap, wording | R: literal text, whatever kind is declared | Name the declared supersession kind. S |
    | 21 | `_view_transforms.milestone_rollup` | transform named after a bundled type | harmless (generic mechanism) | R | Add a neutral alias. S |
    | 22 | VS Code `domain/displayNode.ts:97-105` | `ICON_BY_TYPE` | harmless (`squads.typeIcons` overrides it) | R | None. |
    | 23 | `templates/claude/claude_section.md.j2:80-110` | orchestration prose names reviews/findings | harmless (template override) | D: present in the scratch CLAUDE.md; I: still there when review is dropped | Optional. S |
    
    Clean (R): `_roles`, `_backends`, `_interactions`, `_views.py`/`_view_tags.py`, `_tui` (beyond #10), ref-kind and status handling (semantic roles, docstrings only).
    
    Side defects (D): the article helper writes "a initiative" (create error, import message) and "a action's" (squads skill line 44); the import plural is naive ("storys"); the `add-action --impact` help omits the collection codes that create lists.
    
    Priority order: 1+2+3+4 (one priority surface, M), 7, 12, 9, then the S wording batch (8, 11, 13, 14, 16-20).
- [2026-10-29T19:11:20Z] `reviewer` Paul Reviewer:
  - Verification at cc772bc0, read-only. Verified: F1, F3, F4, F5, F6, F7, F8, F9, F10, F11 (BUG-1248), F12. Reopened: F2 (the init refusal names `sq repair --renumber`, which cannot run without the config init no longer writes). New: F13, F14, F15 (low), F16 (info). Review stays ChangesRequested.
    
    Method: diffs of 1df93668, e07a89b8, e3bb9356, 14c77354, 6be4facd; 451 targeted tests pass (regressions, check sub-entity rules and the touched tests/cli modules); ruff clean; each fix driven from the dev tree on scratch squads. Falsified in a scratch worktree at HEAD: emptying `_subentity_title_present` and short-circuiting `_rehint` each turn their surface and regression cases red, and they go green again once restored. `_story_kind` (14c77354, outside the findings) driven: `--story US1`/`1` map, `US9` refused. @manager: F2 and F13/F15/F16 for the TASK-1244/1246 devs, F14 needs the dev for the playbook line and @tech-writer for README and the CHANGELOG lines.
- [2026-10-29T19:21:24Z] `reviewer` Paul Reviewer:
  - - Round 3 at 1ad3f7b5, read-only. Verified: F13, F15, F16. Kept Open: F2 (simplicity, see its comment) and F14 (ships with the version bump and @tech-writer). Review stays ChangesRequested.
    - Method: diffs of d95c404e and 1ad3f7b5; 117 targeted tests pass; ruff clean; each fix driven from the dev tree on scratch squads. The new tests were falsified in a git-archive extract: pre-fix code for F13 and F15, and two mutations of the create option derivation for F16.
    - @manager F2: the three-step remedy works, but step 1 depends on a refused adopt leaving a config and an index behind. Proposed one-step rule: `sq adopt --renumber`, with plain adopt refusing before it writes. S.
- [2026-10-29T19:50:22Z] `reviewer` Paul Reviewer:
  - Round 4 at 7ed41e73, read-only. Verified: F2 (init, adopt and init --force refuse before writing and name `sq adopt --renumber`; that command resolves and adopts; both new tests falsified). New: F17 (low), `sq adopt --renumber` does not report which item it renumbered. Kept Open: F14 (playbook with the version bump, README and CHANGELOG with the tech writer). Retitled for 0.19 and updated the scope line and the BUG-1191 judgment point to the current remedy. @manager F17 for the TASK-1244 dev, size S; with F14 and F17 closed I recommend Approved.
- [2026-10-29T20:03:05Z] `reviewer` Paul Reviewer:
  - Round 5 at 10938808, read-only. Verified: F14. Reopened: F17 (the JSON `renumbered` holds the printed lines; repair's existing field has the same defect). New: F18 (same-id renumber keeps the old hint, a gap in the BUG-1248 fix), F19 (two CHANGELOG `--renumber` sentences). Review stays ChangesRequested, so the bugs stay Fixed.
    
    - Method: diff of eaf82823 and 10938808; 706 targeted tests pass (test_adopt, test_repair, the hint regression, tests/meta); adopt and repair `--renumber` driven with and without `--json` on scratch squads.
    - CHANGELOG 0.19.0 and README 282-345 driven claim by claim at HEAD: create attribute options (`--target-date nope`, `--tags a,b --tags c`, guide `--priority/--label/--ref`), the three BREAKING entries (guide `--tag` exit 2; add-subtask missing/blank title exit 2/1, `update --title ""`, import missing and blank title; `ref rm` and `unlink-role` refusals, a related ref to the role included), repair and init/adopt shared-number refusals, sort/badge/min-badge/reflog/chlog/depth refusals, repad 33, init/adopt `--squad-dir`/`--backend` refused with nothing written, `workflow view memory_skill SKILL-2`, the subentity_title_present warning, comment on a missing subtask, import op messages, memory search. All hold except F18 and F19.
    - Outside the batch, for @manager: uv.lock pins typer 0.26.7, whose vendored click formats a no-such-option suggestion as a tuple repr (`No such option: --tag ('(Possible options: --tags)',)`); the released tool on typer 0.27.3 prints it clean. The dev tree and CI run the garbled one; an install resolving the lock would ship it. Bump the lock.
    - @manager: F17 and F18 for the TASK-1244 dev (S each), F19 for @tech-writer after them. With those closed I recommend Approved.
<!-- sq:discussion:end -->
