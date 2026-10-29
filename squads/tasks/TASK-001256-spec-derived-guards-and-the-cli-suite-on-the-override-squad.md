---
id: TASK-1256
sequence_id: 1256
type: task
title: Spec-derived guards and the CLI suite on the override squad
status: InReview
parent: FEAT-1249
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-1250:implements
- MILE-1241:targets
- TASK-1253:depends-on
- TASK-1254:depends-on
description: Guards read names from the bundled spec with no allow-lists; tests/cli
  and CI on the override squad; repo squad migration
subentities:
- local_id: ST1
  title: Vocabulary guards derived from the bundled spec
  status: Done
  story: US9
- local_id: ST2
  title: Generated-text guard on the override squad
  status: Done
  story: US9
- local_id: ST3
  title: CLI surface suite on both squads
  status: Done
  story: US10
- local_id: ST4
  title: CI job on the override squad
  status: Done
  story: US10
- local_id: ST5
  title: Acceptance scenario on both squads
  status: Done
  story: US10
- local_id: ST6
  title: Migrate this repository's squad at the cut
  status: Todo
  story: US6
created_at: '2026-10-29T19:55:11Z'
updated_at: '2026-10-29T23:19:56Z'
---
<!-- sq:body -->
## Goal

The vocabulary guards read what they look for from the bundled spec and keep no exception, the CLI surface suite runs on the override test squad in CI, and the acceptance scenario of the feature holds (ADR-1250 sections 9 and 10; FEAT-1249 US9, US10; the repository squad's migration of US6).

## Scope

- Rewrite every vocabulary guard in `tests/meta` to read type names, kind names, field codes, collection names, statuses, ref kinds and aliases from `bundled_spec()`, with no literal set and no per-hit allow-list, sanctioned table or exception entry. Scope: `src/squads` outside `_specs/` and `_migrations/`. A hit is fixed by deriving the name in the source.
- The generated-text guard renders for the override squad.
- `tests/cli` runs on the bundled squad and on the override squad, with the same coverage and verb-parity guards; a CI job runs it on the override squad on every pull request.
- The feature's acceptance scenario on the override squad.
- This repository's squad migrated to 0.19, at the release cut.

## Expected files

- `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py`, `test_no_bundled_ref_kind_literal_outside_the_spec_layer.py`, `test_no_bundled_roster_status_literal_outside_the_spec_layer.py`, `test_no_bundled_subentity_kind_literal_outside_the_spec_layer.py`, `test_render_paths_never_hardcode_a_field_code_literal.py`, `test_badge_values_are_read_through_the_generic_accessor.py`, `test_override_kind_uniformity.py`, and any other guard found to keep a literal set or exception list
- `tests/conftest.py`, `tests/cli/conftest.py`, `tests/_cli_surface.py`, `tests/_squads.py`, and most `tests/cli/test_*.py` where a case names a bundled type or kind directly
- `.github/workflows/test.yml`
- Source files where a rewritten guard finds a hit
- `squads/` (the repository squad, migration subtask only)

## Runs beside

The rename-field task. Source files are not shared; `tests/cli/test_migrate.py` and `tests/check/` are. This task merges last and rebases its parametrization over the rename-field cases.

## Tests

No new behaviour cases beyond the acceptance scenario (about 2); the suite's case count on the override squad roughly doubles by parametrization, and some guards shrink. State the before and after counts in the handback.

## Size

L.

## Working rules

- Work in your own git worktree off `origin/release/0.19`. At most two Python developers run in parallel on this feature; the "Runs beside" line says who shares files with you.
- Gates before handback: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, the tests your diff selects plus the floor (`tests/meta`, `tests/cli`, `tests/check` for any change under `_specs/`, `_rendering/templates/` or `_cli/`), and `sq check` clean for the items you touched. The main loop runs the full suite.
- Tests follow ADR-1172 as amended: CLI surface cases with `@pytest.mark.covers(...)`, one case per behaviour plus its boundary refusals, no unit tests on internal functions, no shape tables. A check rule gets its `@pytest.mark.breaches(...)` case. Once the override test squad exists, the override-side cases run on it rather than on a squad built inline. Falsify each new test once (break the code, see it red, restore) and say so in the handback.
- Any edit under `src/squads/_rendering/templates/` runs `python scripts/gen_template_manifest.py` in the same change (the working version is 0.19.0, so the regen writes the 0.19.0 key).
- Comments and docstrings: one or two sentences, present tense, no ticket IDs, release versions or history. No ticket IDs or process words in test names.
- No bundled type, kind, field, collection, status or alias literal in code outside `_specs/` and `_migrations/`: derive it from the active spec (ADR-1250 section 1).
- CHANGELOG and adopter docs are the tech writer's. Report every adopter-visible change (what an adopter now does or sees differently, and why) in your handback comment; do not edit `CHANGELOG.md` or `docs/`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1256 add-subtask "<title>"`; track with `sq task 1256 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Vocabulary guards derived from the bundled spec

<!-- sq:subtask:ST1:body -->
Every vocabulary guard in `tests/meta` reads the names it looks for from `bundled_spec()` and keeps no literal set, allow-list, sanctioned table or exception entry. The scope is `src/squads` outside `_specs/` and `_migrations/`. Each hit is fixed in the source by deriving the name, not by listing it. Each guard is shown to fail once against a known positive (a bundled name added to a scratch copy of a source file), and a search of the vocabulary guards for allow-list constructs finds none. Scan whole logical units with whitespace collapsed (ast and tokenize), since a line grep misses a wrapped token.

Tests: guard rewrites only; report each guard's falsification.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Generated-text guard on the override squad

<!-- sq:subtask:ST2:body -->
The guard on generated agent text renders the squads skill, the CLAUDE.md section, the managed skills and pointers for the override test squad, and fails on any name the bundled spec declares and the override drops.

Tests: the guard itself, falsified once by reintroducing a bundled example line.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — CLI surface suite on both squads

<!-- sq:subtask:ST3:body -->
The `tests/cli` surface suite runs on the bundled squad and on the override squad, with the same coverage and verb-parity guards. A case that names a type, kind, field or alias resolves it from the active squad's spec (for example "the type hosting a mapping kind") instead of naming `feature` or `story`; a case that is about the bundled spelling stays bundled-only and says so in its marker.

Tests: parametrization; state the case counts per squad.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — CI job on the override squad

<!-- sq:subtask:ST4:body -->
A CI job in `.github/workflows/test.yml` runs the `tests/cli` suite on the override squad on every pull request. A case that passes on the bundled squad and fails on the override squad fails the job, shown once by reintroducing a static `--priority` option in a scratch branch. Hugo Ops reviews the workflow change.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Acceptance scenario on both squads

<!-- sq:subtask:ST5:body -->
The feature's acceptance scenario on the override squad: no CLI option, column, help text, error message, import key, stored key, `--json` key or generated skill line names a dropped type, kind, field or alias; the bundled squad keeps `--priority`, `--story`, `add-story` and `f`.

Tests (about 2): one scenario on each squad, driving create, add-kind with the mapping, list, tree, import and skill show.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Migrate this repository's squad at the cut

<!-- sq:subtask:ST6:body -->
This repository's squad migrates to 0.19 with the runner, and `sq check` is clean afterwards. It runs at the release cut, when the operator says so: migrating earlier makes the released `sq` that the team uses for board work refuse this squad. Commit the tree before running `sq migrate up`, run it from the merged release branch, and verify the item count and `sq check` after.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
- [2026-10-29T23:19:41Z] `python-dev` Elias Python:
  - Runs at the release cut when the operator says so; not run here.
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T23:19:22Z] `python-dev` Elias Python:
  - @manager Handback for TASK-1256 (ST1 to ST5 done; ST6 stays Todo and runs at the release cut). Branch worktree-agent-af29a58938d6ca5a9, rebased on origin/release/0.19 (5ba0f467), head 3cf5bf00; nothing pushed.
    
    Commits: bf65308b guards (ST1, ST2), c0f64a86 squad selection and derivation names, d89b3953 suite on the override squad (ST3), bc26591b CI job, scenario and profile guard (ST4, ST5), 3cf5bf00 scenario merged into one case.
    
    **ST1.** One scanner (tests/meta/_vocabulary.py) reads every name from a WorkflowSpec: type names, prefixes, aliases, kinds, plurals, local prefixes, field codes, collection names, badge codes, statuses (of every lifecycle), ref kinds. It finds a name as a bare string, as a flag or verb of it (--x, --no-x, --min-x, add-x), inside a code span or command line of a string or template (f-strings read whole), and as a quoted literal in a template tag. The roster types are skipped because the spec says so (item_is_roster). Docstrings, comments and Jinja comments are prose. A one-letter alias is read only after "sq". No literal set, allow-list, sanctioned table or exception entry remains in the vocabulary guards: the ref kind, status, kind, item type and field guards are thin files over the scanner. The scanner leaves out words the engine defines for itself, read from the engine (colour intents, role capabilities), for two exact-string coincidences: info and review. Falsified: a planted bundled string in src/squads/_probe.py turned each of the five guards red (ref kind, status, kind, item type, field code), and so did a code span with a bundled flag and an f-string command; the getattr guard went red on a planted getattr(obj, f.code); a bundled example line in workflow.md.j2 turned the generated-text guard red. test_override_kind_uniformity.py now derives its type from the spec.
    
    Source literals the guards found and I fixed: _badges.primary_field_code default "severity" (default removed; returns "" and review.md.j2 omits the field line); review.md.j2 wrote "sq review" (now item.type); milestone.md.j2 wrote MILE-, "targets" and "sq milestone" (now prefix, the view's source name, item.type); greeting_skill.md.j2 wrote Archived and Active for operators (now first_settled_status and live_initial of operator); help examples "status Archived" in the operator, role and skill groups (now "status <status>"); "TASK-<n>" and "FEAT-<n>" in two help texts (now "<PREFIX>-<n>"); the "bug" example in the playbook scaffold comment (now "<type>"); the Blocked and Deferred headers of the role catalog and the Open and Closed workload headers (headers are the title-cased key, titled_columns); the _SIDE_PRIORITY status-name table in _lifecycle_order.py (deleted).
    
    Adopter-visible: linearize_lifecycle now lists side states in discovery order, so the work lifecycle reads "(+ Cancelled, Blocked)" and the bug lifecycle "(+ WontFix, Cancelled, Blocked)" in sq workflow, the squads skill and sq-<type> skills (it was Blocked first because of a name table). The review item template omits the severity line when the finding kind declares no field. Help examples show a placeholder instead of a status or ID prefix. The manifest was regenerated (0.19.0 key) and the content store rebuilt.
    
    **ST2.** test_generated_agent_text_names_no_bundled_vocabulary.py builds the override test squad with both backends under a non-default squad directory and reads CLAUDE.md, AGENTS.md, .claude/ and the squad agents folder from disk. It fails on any name the bundled spec declares and that squad drops, inside a code span or command line (the override fixture now also drops the bundled lifecycles it does not use, so statuses are dropped too), on a bundled role slug the roster lacks, and on the default squad directory. Falsified with the example line above. Finding for you: with the full role roster the AGENTS.md role responsibilities (src/squads/_specs/roles.toml, tech-lead and product-owner, "bundled default: sq create task ...") name task, FEAT, story, fixes, feature. That is spec-layer text, so the guard runs on the minimal roster; an adopter with the bundled roles and a dropped workflow reads it. Needs a ruling (derive it, or leave it to the roles override).
    
    **ST3.** pytest --squad override (or SQUADS_TEST_SQUAD) selects the squad for the whole run. tests/_profile.py holds both profiles (reference type, kind, target kind, host, badge field, flags and so on); tests/cli/conftest.py gives project, seeded_project, populated_project and full_project the selected squad (populated override squad mirrors the bundled numbers 2, 3, 4). Cases read names from the profile (about 900 string literals rewritten). A case about bundled spelling carries bundled_only("reason"); the collection hook refuses a marker with no reason. Guard: every profile entry resolves against its squad's spec. Derived options are named by derivation in covers markers and in the surface (--<field>, --no-<field>, --min-<field>, --<target-kind>, --no-<target-kind>, --<attribute:str|list|date>), applied only on the type-bound commands. This is F13 and F17: the override-squad markers are re-declared, and the invoke fixture records derived flags under their derivation name. The tree built outside a squad by bundled_known no longer stays memoised. Counts: tests/cli bundled 952 before, 968 after (includes TASK-1255 cases and the new scenario); override run 787 passed, 181 skipped (bundled_only), 968 collected. Whole suite bundled: 1770 passed in 49 s wall with -n 4. Override run of tests/cli: 30 s wall with -n 4. Both are far under the ADR-1172 bounds on this box; CI times not measured.
    Honest gap: 181 of 968 cases (19 percent) are bundled_only. Module breakdown: test_override 29, test_workflow 26, test_item_verbs 26, test_subentity_verbs 21, test_create 15, test_migrate 13, test_repair 9, test_adopt 8, test_import 7, test_renumber 7, test_show 6, others fewer. test_override, migrate, adopt, repair and renumber are about bundled documents and legacy squads; the item, sub-entity, create, show and workflow ones are convertible by a richer profile (retype target, ref-kind tables, severity-like field, placeholder text) and are the follow-up if you want the ratio lower.
    
    **ST4.** .github/workflows/test.yml gets an override-squad job (ubuntu-latest, same SHA-pinned actions, uv sync --frozen --all-extras, uv run pytest --squad override tests/cli), run on every pull request through the existing triggers. Falsification: a static --priority option added in _field_options turned test_the_scenario_prints_the_squads_own_vocabulary_and_no_dropped_word red on the override squad only (it passed on bundled); three override-project cases went red on both. Not pushed; needs devops review (Windows and macOS are not in the job; the bundled matrix stays as it was).
    
    **ST5.** tests/cli/test_a_squad_shows_only_its_own_vocabulary.py is one scenario run on whichever squad the run is on: create with the badge flag and parent, add-<kind> with the mapping option, list, tree, show, import --dry-run, help of create, update, add-<kind>, list and tree; it fails on any flag, verb or JSON key the bundled spec declares and the squad drops, and on the bundled squad it holds --priority, --story, add-story and the alias f. Counted as one case per squad run.
    
    **ST6.** Not run. No sq migrate up, nothing under squads/ touched. It runs at the release cut.
    
    Open points for others: F18 and F19 were TASK-1254's; nothing of mine overlaps. F8 note respected: vocabulary is matched only in code spans, flags and keys, never as bare English words.
<!-- sq:discussion:end -->
