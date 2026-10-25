---
id: REV-1142
sequence_id: 1142
type: review
title: 'Review TASK-1125: composition root and load-once'
status: Approved
author: reviewer
refs:
- TASK-1125
- ADR-1128
description: 'Review of commit 12fd2afa: compose_service, the spec-document resolver,
  renderer from_squad, the backend table, and their tests.'
subentities:
- local_id: F1
  title: sq check and sq sync re-read overrides outside the load path
  status: Verified
  severity: medium
- local_id: F2
  title: sq adopt loads the workflow override twice
  status: Verified
  severity: low
- local_id: F3
  title: sq workflow lint reads the workflow override three times
  status: Verified
  severity: low
- local_id: F4
  title: Load-count test cannot see raw reads or any fallback path
  status: Verified
  severity: medium
- local_id: F5
  title: sq check builds backends outside the composition root
  status: Verified
  severity: low
- local_id: F6
  title: Docs claim no code below the root reloads a document
  status: Verified
  severity: low
- local_id: F7
  title: Non-UTF-8 workflow/playbook override crashes check and repair
  status: WontFix
  severity: low
- local_id: F8
  title: Lazy re-raises one exception instance, growing its traceback
  status: Verified
  severity: info
- local_id: F9
  title: 'Composition table: vacuous asserts, roles+playbook shape missing'
  status: Verified
  severity: info
- local_id: F10
  title: Skill-view test helper renders without the squad directory
  status: Verified
  severity: info
- local_id: F11
  title: Load-count test docstring narrates history
  status: Verified
  severity: info
- local_id: F12
  title: Load table allows an unneeded bundled playbook build
  status: Verified
  severity: medium
created_at: '2026-10-25T12:59:20Z'
updated_at: '2026-10-25T15:58:29Z'
---
<!-- sq:body -->
## Scope

Commit 12fd2afa on release/0.17, delivering TASK-1125 under ADR-1128:

- `compose_service`, `build_service`, `Mode` and the fallback tables (`_services/_service.py`);
- the document resolver (`_spec_documents.py`) and the shared parse (`_specload.py`);
- renderer `from_squad` threading (`_rendering/_engine.py`);
- the literal backend table (`_backends/_registry.py`);
- the two new test tables, about 90 mechanically edited test files, and the CLAUDE.md, `docs/internals.md` and `docs/backends.md` updates.

## Method

- Read the diff against the task acceptance and the ADR.
- Drove a dev build in scratch squads with a probe that counts every read of a `.overrides/*.toml` file and every TOML parse, not only the two functions the new test counts. Commands: `--help`, show, list, check, sync, repair, init, adopt, migrate up, workflow lint, role catalog, override diff and check, ui --help, plus broken and non-UTF-8 overrides.
- Compared behaviour against an export of 12fd2afa~1.
- Falsified the fallback tables and the parse-copy isolation in an exported copy.
- Gates on the tree: pyright 0 errors, ruff check and format clean, tests/meta 458 passed. The two new test files and the render-isolation file pass (18).

## What holds

- **Fallback modes.** Every mode picks the same spec and playbook as the site it replaces. The two substitutions (reusing `ctx.active_spec`, and the bundled singleton where an equal copy was built before) are equal in content.
- **Existing tests cover the fallback tables.** Swapping the `CHECK_FALLBACKS` rows turns 2 integration tests red. Pointing `MIGRATE_FALLBACKS` at the bypass ladder turns 11 red.
- **The cached parse is isolated.** Each caller gets a deepcopy of the one packaged parse. Removing the copy turns 21 tests red.
- **Renderer.** `from_squad` is required at every entry point, so pyright enforces it. Every production call site passes the service's squad directory. The cache is keyed on that directory, so two squads in one process cannot collide.
- **Registry.** It is a literal read-only table with no import side effect, and the mutable-state allowlist entry is gone.
- **Ordinary commands.** show, list, `--help`, repair, init, role and migrate up read each override once.

## What does not hold

The load-once rule breaks on `sq check` (F1), `sq sync` (F1), `sq adopt` (F2) and `sq workflow lint` (F3). The new load-count test cannot see any of these, and it has no fallback rows (F4).

## The three behaviours the dev flagged

1. The index-check-skipped mode pairs the merged spec with the bundled playbook. It is used only by `sq repair`, which rebuilds the index and never reads the playbook to write anything. Defensible, no finding.
2. `sq role catalog` building the service first: the output is identical to 12fd2afa~1 for a broken roles override beside a playbook override. No finding. The underlying "playbook config invalid" label for a roles failure is older than this commit and is noted in F9.
3. `sq workflow lint` reading the override twice: it is three times, and it is a finding (F3).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1142 add-finding "…" --severity medium`; track with `sq review 1142 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — sq check and sq sync re-read overrides outside the load path

<!-- sq:finding:F1:body -->
ADR-1128 says the project override is read at most once per invocation, on every path, `sq check` included. Today `sq check` and `sq sync` read the override files again outside the load path, through `Path.read_text` + `tomllib.loads`.

Measured (driven, dev build of 12fd2afa, scratch squad with the load test's three overrides, probe wrapping `Path.read_text` and `tomllib.loads`):

| Command | workflow.toml | roles.toml | playbook.toml |
|---|---|---|---|
| `check` | 2 | 2 | 4 |
| `sync` | 1 | 1 | 3 |

Where they come from:

- `_interactions/_loader._override_types`, called twice per run by `playbook_override_guide_pairs` and `playbook_override_command_lines`. Callers: `_services/_validators.py:1703`, `:1722` (check) and `_services/_maintenance.py:700`, `:720` (sync).
- `_overrides/_service._check_workflow_override_issues`, `_check_roles_catalog_override_issues` and `_check_playbook_override_issues`, one read each in `sq check`.
- Read, not driven: the stamp-drift shadows predicates (`workflow_override_shadows_bundled`, `playbook_override_shadows_bundled`, `_roles_catalog_override_shadows_bundled`) read the override again. The roles one also re-parses the packaged roles.toml with `tomllib.loads(bundled_roles_toml_text())`, which skips the shared parse. My stale-stamp probe did not reach them.

Failure scenario: an editor save or a concurrent agent rewrites `.overrides/playbook.toml` during one `sq check`. The merged playbook the service holds and the raw guide-pair/command-line provenance then describe two different files. Check either reports a dropped guide that the loaded playbook still has, or misses one.

Fix direction: parse the raw override once where the document is loaded (keep it next to the merged model on the sources), and pass it to these consumers instead of a squad directory.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-25T13:32:38Z] `python-dev` Elias Python:
  - Fixed: override text is read once through OverrideFiles on the service; the stamp, shadow and guide/command-line readers in check and sync take it, and the roles shadow check uses the shared packaged parse.
- [2026-10-25T13:45:53Z] `reviewer` Paul Reviewer:
  - Verified on 6393caab by driving it with the file-level probe on a scratch squad that has all three overrides, plus a stale-stamp squad. Each override file is now opened once per run on every command family I tried:
    
    - `check` and `sync`;
    - `list` and `show`;
    - `repair` and `--help`;
    - `workflow lint`;
    - `init` and `adopt`;
    - the fallback squads: broken playbook, broken workflow, broken roles beside a playbook override, and a workflow override refused by the index check, each under `check`, `repair` and `sync`.
    
    The playbook text is still parsed three times in `check` and `sync` (once by `read_override`, twice by `_override_types`). All three parse the same cached text, so the two-different-files scenario is closed.
    
    Falsified: pointing `_override_types` back at a raw read turned 5 load-table rows red.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — sq adopt loads the workflow override twice

<!-- sq:finding:F2:body -->
When `.squads.toml` is absent, `adopt` calls `_init_time_spec(root / squad_dir)` before it writes the config and calls `_init_time_spec(sp.squad_dir)` again after the mkdir (`_services/_service.py`). Each call runs `load_workflow_spec(squad_dir)`.

Driven: `sq adopt` over a folder with the three overrides already in place reads workflow.toml through `read_override` twice and builds the merged model twice. `sq init` reads it once. This breaks the load-once rule on a path the acceptance covers.

Failure scenario: an override edited between the two calls (unlikely, but the second result is the one that scaffolds folders). The validation that gated the config write and the spec that scaffolds the squad can disagree, which is exactly what `_init_time_spec`'s docstring says it prevents.

Fix: keep the first result and reuse it.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-25T13:32:40Z] `python-dev` Elias Python:
  - Fixed: adopt keeps the spec it validated before writing the config and reuses it.
- [2026-10-25T13:45:55Z] `reviewer` Paul Reviewer:
  - Verified by driving `sq adopt` over a folder with all three overrides already in place: workflow.toml is opened once and the merged model is built once.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — sq workflow lint reads the workflow override three times

<!-- sq:finding:F3:body -->
Driven: `sq workflow lint` on a squad with a workflow override reads it through `read_override` three times, plus once more in `_read_toml_stamp`:

1. the root callback's `bind_active_spec` (through `invocation_sources`);
2. `lint_workflow_spec` -> `_read_raw_override`;
3. `check_view_transforms(load_workflow_spec(squad_dir), squad_dir)` at `_cli/_workflow_cmd.py:1037`.

The handoff says lint reads it twice and leaves it out of the measured table. ADR-1128 applies the rule to every path that uses the document, and lint is one.

Failure scenario: lint is the diagnostic an adopter reruns while editing the file. Three reads in one run can produce a collect-mode finding list and a transform check that describe two different saves, so one lint output carries contradictory findings.

Fix: build the transform check from the spec the invocation already resolved (`invocation_sources(...).workflow()`, or the merge lint already did), and take the stamp from the same text.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-25T13:32:43Z] `python-dev` Elias Python:
  - Fixed: workflow lint reads through the invocation's OverrideFiles and takes the merged spec the root callback built (lint_workflow_spec loaded=), so the file is read once and the model built once.
- [2026-10-25T13:45:58Z] `reviewer` Paul Reviewer:
  - Verified by driving `sq workflow lint` with a workflow override: the file is opened once and `_read_toml_stamp` no longer reads it. The cached text is parsed twice, which is fine.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Load-count test cannot see raw reads or any fallback path

<!-- sq:finding:F4:body -->
`tests/cli/test_each_spec_document_is_loaded_at_most_once_per_invocation.py` is the proof ADR-1128 asks for. As written it cannot fail on most of the ways the rule breaks.

- **It counts only two functions.** It profiles `_specload._parse_bundled` and `_specload.read_override`. A read through `Path.read_text` + `tomllib.loads` is invisible to it, and so is a raw `tomllib.loads` of a packaged file. It passes today with playbook.toml read four times under `check` (F1; I ran it green on 12fd2afa).
- **The rows are two shapes only:** no overrides, or all three. Missing:
  - one document overridden alone. A playbook override with no workflow override takes a different branch of `resolve_playbook`, and a roles override alone does too.
  - any broken override.
  - any refusal followed by a fallback: `repair` after a cross-check refusal, `check` with a broken playbook, workflow or roles override.
  - the commands `repair`, `sync`, `init`/`adopt`, `workflow lint` and `migrate up`.

  The acceptance says "This holds on every path: ordinary commands, `--help`, `sq check` and each fallback mode." The fallback rows exist only as a hand-measured table in the handoff comment, so nothing pins them.

Failure scenario: a later change adds a raw re-read in a validator, or makes a fallback mode re-run `load_workflow_spec`. The test stays green, which is exactly how F1 got through.

Fix: count at the file level, meaning any open or read of a path under `.overrides/` and any TOML parse of a packaged spec. Make the table document x {absent, present, broken} x command family {help, read, check, repair after refusal, sync, adopt, lint}.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-25T13:32:45Z] `python-dev` Elias Python:
  - Fixed: the load test is table-driven (9 shapes x 7 command families, file-level override opens, packaged reads, builds, fresh interpreter); before the fixes it was red on 18 rows (check, sync, adopt, lint, refused fallbacks).
- [2026-10-25T13:46:00Z] `reviewer` Paul Reviewer:
  - Verified. The table is 9 shapes x 7 command families, and reads are counted at the `io.open` level. Falsified in an export of 6393caab:
    
    - `_override_types` reading raw: 5 rows red;
    - the workflow `Lazy` bypassing `OverrideFiles`: 8 rows red, including `refused-check`, a fallback row.
    
    One gap is left in the build bound. It is filed as a separate finding.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — sq check builds backends outside the composition root

<!-- sq:finding:F5:body -->
ADR-1128: the composition function "builds the IndexStore and the active backends and passes them in". Task approach 5: "The active backends are instantiated once in the composition function". CLAUDE.md now says `build_service` "makes the IndexStore and the backends and hands them in".

The code still builds fresh backend instances below the root:

- `_services/_check.py:879`: `get_backend(backend_name)` per drift candidate;
- `_services/_validators.py:1304`, `:1350`: `get_backend(name)` in `_backend_reconciled` and `backend_entry_candidates`;
- `_migrations/_v0_11_to_v0_14.py:237`, `:305`.

So one `sq check` builds each backend several times, and none of those instances are the ones the service holds.

This is harmless today because the backends are stateless. Failure scenario: a test or a future backend injects a backend through `build_service`, such as a fake in a test or a backend with a per-instance cache or daemon-scoped resource. `sq check`'s managed-file and drift rules then ignore it and judge a fresh default instance instead, so check and sync can disagree about the same backend.

Fix: put the service's backends on `SquadGlobalContext` (or pass a name -> instance lookup built from them) and use those in check. If the migration runners are meant to stay frozen, say so in the code.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-25T13:32:47Z] `python-dev` Elias Python:
  - Fixed: SquadGlobalContext carries the service's backends and check uses them; the migration runner keeps its own, now commented as frozen. Test: check_judges_the_backends_the_service_holds.
- [2026-10-25T13:46:03Z] `reviewer` Paul Reviewer:
  - Verified. No `get_backend` call is left under `_services/`: check and the validators use the service's backends. The migration runner keeps its own and says why. The new test passes.
    
    One note: the test injects through `svc._backends` with a `reportPrivateUsage` ignore, which goes against the no-private-reach-in convention. `tests/_helpers.backends_of` exists and could be passed through a constructor instead.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Docs claim no code below the root reloads a document

<!-- sq:finding:F6:body -->
The new architecture prose states a guarantee the code does not keep:

- CLAUDE.md: "Each document is loaded once per invocation, at the root; code below it takes `Service.spec`/`.playbook`/`.catalog` and never calls a loader with a squad directory."
- `docs/internals.md`: "the three spec documents are resolved once through `_spec_documents.py` and passed down — nothing below the root loads one again."
- `_spec_documents.py` module docstring: "each built from one read of its packaged file and of its project override", and "everything below the composition root receives what it built instead of loading again."

Counter-examples in the tree:

- the raw override readers in check and sync (F1);
- `_cli/_workflow_cmd.py:1037` `load_workflow_spec(squad_dir)` (F3);
- `_cli/_common.py:333` `_read_spec_from_disk`, the help/completion path, which loads on its own and not through `invocation_sources`;
- `_services/_service._init_time_spec` (twice in adopt, F2).

Failure scenario: CLAUDE.md is what the next agent trusts. A reviewer reading "never calls a loader with a squad directory" will not look for the re-reads, the way this review nearly did not.

Fix: make the claims true (F1-F3), or narrow them to what holds today.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-25T13:32:50Z] `python-dev` Elias Python:
  - Fixed: CLAUDE.md, internals.md and the _spec_documents docstring now state what holds (entry points load once; below them OverrideFiles and the documents are passed down).
- [2026-10-25T13:46:05Z] `reviewer` Paul Reviewer:
  - Verified. CLAUDE.md, `docs/internals.md` and the `_spec_documents.py` docstring now claim one read per override file, which matches what I measured. They no longer claim that no code below the root ever touches a squad directory.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Non-UTF-8 workflow/playbook override crashes check and repair

<!-- sq:finding:F7:body -->
Driven: a `.overrides/workflow.toml` containing a 0xff byte makes `sq check` and `sq repair` end in a `UnicodeDecodeError` traceback. `sq list` refuses cleanly, with the file and cause. The 12fd2afa~1 export behaves the same, so this is not a regression.

This commit owns the path, though:

- the workflow and playbook `OverrideMessages` have `not_utf8=None`, so `read_override` re-raises the raw `UnicodeDecodeError` (roles has a message);
- `Lazy` memoises only `SquadsError`, so each attempt reads the file again;
- `compose_first_of` and `sq check`'s fallback catch only `SquadsError`, so the fallback table never runs.

`check` and `repair` are the two commands that must run beside a broken override, and a traceback breaks the "never a traceback" contract.

Fix: give the workflow and playbook documents a `not_utf8` message so the failure arrives as `OverrideReadError`. Add a non-UTF-8 row to the composition and load tables.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-25T13:02:49Z] `manager` Catherine Manager:
  - Same defect as BUG-1134, which TASK-1138 ST1 fixes now that the composition root has landed; tracked there, not in this fix round.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Lazy re-raises one exception instance, growing its traceback

<!-- sq:finding:F8:body -->
`Lazy.__call__` raises the stored `SquadsError` instance on every call. Each re-raise appends the current frames to that instance's `__traceback__`. Driven: four calls give tracebacks of 4, 6, 8 and 10 frames.

In `sq check` a broken roles override is asked for once per role resolution (`resolve_role_tolerantly` and friends), so the one exception object grows with the roster. In the daemon ADR-1128 describes, where documents are built once at startup and reused per request, it would grow on every request for the life of the process. `Lazy` also has no lock, so two threads can both build.

Fix: keep the traceback taken at the first failure and raise `self._error.with_traceback(self._tb)`, or raise a fresh exception chained to the stored one. Add a lock before the daemon shares a `Lazy`.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-25T13:32:52Z] `python-dev` Elias Python:
  - Fixed: Lazy keeps the first traceback and re-raises with it, and takes a lock; unit test pins one build and a constant traceback depth.
- [2026-10-25T13:46:08Z] `reviewer` Paul Reviewer:
  - Verified: four `Lazy` failures in a row give a constant traceback depth (4, 4, 4, 4; it was 4 to 10). The build runs once and is under a lock.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Composition table: vacuous asserts, roles+playbook shape missing

<!-- sq:finding:F9:body -->
In `tests/service/test_a_service_is_composed_from_the_documents_its_mode_chooses.py`:

- `assert svc.paths is project` cannot fail, because `build_service` passes `paths` straight through. `assert await svc.list_items() is not None` cannot fail either, because it returns a list. Neither proves "opens the squad given".
- No row covers a broken roles override beside a valid playbook override. That is the one shape where the lazy catalog is forced during composition: `resolve_playbook` -> `load_playbook` -> `project_role_slugs` calls the catalog, so the normal mode refuses with `PlaybookConfigError`, and `sq check` labels a roles failure "playbook config invalid". That labelling is not new (I compared it with the 12fd2afa~1 export), but it is the interaction the lazy-catalog design has to keep, and the roles row covers roles-broken alone.
- The `sq repair` row asserts exit codes only.

The fallback ordering is still guarded by the existing suite. I swapped `CHECK_FALLBACKS` rows and two integration tests went red. I pointed `MIGRATE_FALLBACKS` at the bypass ladder and 11 migrate tests went red.

Fix: replace the two vacuous asserts with ones that can fail, for example compose for two squads and check each service reads its own index. Add the roles-plus-playbook row.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-25T13:32:55Z] `python-dev` Elias Python:
  - Fixed: the vacuous asserts are replaced (store path and items compared with the index), a roles-plus-playbook row is added, and the repair row asserts the rebuilt-index output.
- [2026-10-25T13:46:10Z] `reviewer` Paul Reviewer:
  - Verified. The roles-plus-playbook row is in, and the store and index asserts can fail now. The repair row asserts the rebuilt-index output.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Skill-view test helper renders without the squad directory

<!-- sq:finding:F10:body -->
`tests/_helpers.resolved_skill_definition` renders with `from_squad=None` and `catalog=catalog_of(svc.paths.squad_dir)`, which reloads the roles override on each call. Production (`_services/_views.py:201`) passes `self.paths.squad_dir` and `self.catalog`.

Before this commit, `ServiceCore.__init__` set the ambient squad directory, so the helper rendered with the squad's template overrides. Now the nine tests that use it render bundled templates only, and nothing says so. A grep shows none of them places a template override today, so nothing passes falsely yet. But the helper no longer computes what production computes, and the next test that overrides a view template through it will pass against the bundled one.

Fix: pass `from_squad=svc.paths.squad_dir` and `catalog=svc.catalog`.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-25T13:32:57Z] `python-dev` Elias Python:
  - Fixed: the helper renders with from_squad=svc.paths.squad_dir and catalog=svc.catalog.
- [2026-10-25T13:46:12Z] `reviewer` Paul Reviewer:
  - Verified: the helper passes `from_squad=svc.paths.squad_dir` and `catalog=svc.catalog`, the same as production.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Load-count test docstring narrates history

<!-- sq:finding:F11:body -->
The module docstring of `tests/cli/test_each_spec_document_is_loaded_at_most_once_per_invocation.py` says the `check` row is "the case where the role catalog used to be loaded once per role resolution". That "before" exists only in the diff, so a reader of the test cannot observe it.

Fix: state it in the present tense, for example "the case where catalog reads would scale with the roster".
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-25T13:33:00Z] `python-dev` Elias Python:
  - Fixed: the load test docstring states the roster-scaling case in the present tense.
- [2026-10-25T13:46:14Z] `reviewer` Paul Reviewer:
  - Verified: the docstring now states the roster-scaling case in the present tense.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Load table allows an unneeded bundled playbook build

<!-- sq:finding:F12:body -->
The load table lets any overridden document reach `build <= 2`, and for the playbook it also does so when only the workflow is overridden. The bound counts builds without saying which model each build is, which causes two problems.

**1. The bundled playbook build is not needed.** I traced every playbook `_build_spec` call with only a workflow override present:

- `list` and `show` build only the merged playbook, against the merged spec.
- `check` and `sync` build the bundled playbook as a second model, and the one caller is `_interactions/_skills.bundled_skill_slugs` -> `_playbook.bundled_item_playbooks` -> `_bundled_playbook`:
  - in `check`, through `backend_entry_drift` -> `_skill_pointer_description` -> `is_system_skill`;
  - in `sync`, through `_restamp_managed_skill_frontmatter` -> `managed_skill_slugs`.

That caller needs only the set of type names squads ships a per-type skill for. That key set already comes from the shared parse (`_interactions/_loader._bundled_type_names`), or from `bundled_spec()`. Building and validating a whole second `PlaybookSpec` (coverage, referential checks against the bundled catalog) to get a set of names costs a build that ADR-1128's rule exists to remove. The comment in `_check` ("its merged model is built again for them") also misdescribes what the second build is: it is the bundled model, not a second merged one.

**2. The widened bound lets a real violation through.** Falsified in an export of 6393caab: I made `resolve_playbook` call `load_playbook` twice, so the merged playbook is built twice per invocation. That breaks the "each model built at most once" rule on every command. Only 9 of 63 rows went red, all of them `check`, `sync` or `adopt`, where the bundled build adds a third. Every `help`, `read`, `repair` and `lint` row stayed green, as did the `-present` shapes on `read`, while the merged model was built twice.

Fix:

- derive `bundled_skill_slugs` from the bundled key set, so no second playbook model is built;
- count builds per model, bundled versus merged (for example, record whether `squad_dir` was given to `load_playbook`, or tag the builder call), and assert at most one of each;
- tighten the playbook bound to 1 build when no playbook override exists.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-25T14:01:52Z] `python-dev` Elias Python:
  - Fixed: bundled_skill_slugs reads the bundled type-name set (no bundled playbook build); the load table counts bundled and merged builds and override parses separately, each at most one, one in all without a playbook override; override text is parsed once and shared.
- [2026-10-25T15:57:50Z] `reviewer` Paul Reviewer:
  - Verified on 88a9e14f, both by driving the commands and by falsifying the table in an export:
    
    - **Driven.** With only a workflow override, `check` and `sync` build the playbook model once, the merged one only. `bundled_type_names()` returns the same set as `bundled_item_playbooks()`. With all three overrides, each override text is parsed once.
    - **Falsified (the baseline run is 64 passed):**
      - Merged playbook built twice: 16 rows red, now including every `read` and `repair` row of `all`, `workflow-present` and `playbook-present` (it was 9 before). `help` and `lint` stay green, but they never build the playbook.
      - The bundled build restored in `bundled_skill_slugs`: 3 rows red (`workflow-present` check, sync, adopt).
      - `override_mapping` re-parsing instead of using the shared parse: 9 rows red.
    - **Side points.** Override parses are counted per document and the bounds are tightened. The F5 test now passes its backends through `make_service`/`build_service`, with no private reach-in.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T13:02:02Z] `reviewer` Paul Reviewer:
  - @manager review done, 11 findings. Recommended verdict: ChangesRequested.
    
    - Medium: F1 (check and sync re-read overrides outside the load path), F4 (the load-count test is blind to raw reads and has no fallback rows).
    - Low: F2, F3, F5, F6, F7.
    - Info: F8 to F11.
    
    F1 and F4 belong together: fixing the reads without widening the test leaves the rule unguarded. F6 (the CLAUDE.md and internals claims) closes with F1 to F3. F7 is older than this commit; it can get its own bug if it should not ride on this task.
    
    Every count in the findings was driven on a dev build in scratch squads, except the shadows-predicate reads in F1, which I only read in the code. I did not run the full suite.
    
    @python-dev the findings are yours once the manager routes them.
- [2026-10-25T13:46:35Z] `reviewer` Paul Reviewer:
  - @manager I re-verified the fixes in 6393caab by driving them with the file-level probe in scratch squads and by falsifying them in an export.
    
    - Verified: F1, F2, F3, F4, F5, F6, F8, F9, F10, F11. F5 has a note about a private reach-in in its test.
    - F7 stays WontFix, homed in BUG-1134 / TASK-1138.
    - New: F12 (medium). With only a workflow override, `check` and `sync` build a bundled `PlaybookSpec` they need only a key set from. Worse, the load table's `build <= 2` bound misses the merged playbook being built twice on every help, read, repair and lint row. I drove that: 9 of 63 rows went red, and all the others stayed green.
    
    Recommended verdict: ChangesRequested until F12 is fixed.
    
    Gates on 6393caab: ruff clean, pyright 0 errors. The targeted new tests pass (74).
- [2026-10-25T15:57:54Z] `reviewer` Paul Reviewer:
  - @manager F12 Verified on 88a9e14f, driven and falsified (details on F12). Every finding is now Verified except F7, which is WontFix and tracked in BUG-1134. Recommended verdict: Approved. The transition is yours.
- [2026-10-25T15:58:29Z] `manager` Catherine Manager:
  - Approved: F1-F6 and F8-F12 Verified by the reviewer, F7 tracked in BUG-1134 / TASK-1138; full suite green at 88a9e14f.
<!-- sq:discussion:end -->
