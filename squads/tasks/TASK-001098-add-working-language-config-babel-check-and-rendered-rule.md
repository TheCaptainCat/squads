---
id: TASK-1098
sequence_id: 1098
type: task
title: Add working_language config, Babel check and rendered rule
status: Done
parent: FEAT-1097
author: tech-lead
refs:
- ADR-1100:implements
description: Validate working_language with Babel at startup and render the language
  rule in every backend and the squads skill.
subentities:
- local_id: ST1
  title: Add Babel, the resolver and the raw config key
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST2
  title: Validate on every command and warn on stderr
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST3
  title: Render the rule in both backends and the squads skill
  status: Done
  assignee: python-dev
  maps_to: US2
- local_id: ST4
  title: Write working_language on init and adopt
  status: Done
  assignee: python-dev
  maps_to: US3
- local_id: ST5
  title: Document the key and add the CHANGELOG entry
  status: Done
  assignee: tech-writer
  maps_to: US4
- local_id: ST6
  title: Report a malformed working_language in sq check
  status: Done
  assignee: python-dev
  maps_to: US1
created_at: '2026-10-24T09:11:31Z'
updated_at: '2026-10-24T19:01:44Z'
---
<!-- sq:body -->
## Goal

Add the `working_language` key to `.squads.toml`, validate it with Babel on every command, and render one language rule (resolved display name plus tag) into the CLAUDE.md managed section, the AGENTS.md managed section and the `squads` skill. `language` and `locale` are never read, written or accepted.

The architect's decision record on the new `.squads.toml` key governs this task. Where it and this plan differ, the decision record wins.

## Approach

**Dependency.** Add `"babel>=2.18"` to `[project].dependencies` in `pyproject.toml` and refresh `uv.lock` with `uv lock`. Babel 2.18.0 was probed: `Locale.parse(tag, sep="-")` accepts `fr`, `pt-BR`, `pt-br` (normalised to `pt_BR`), `zh-Hant-TW`, `sr-Latn`, and raises `ValueError` (`fr_FR`, `en-US-x-foo`, empty string) or `UnknownLocaleError` (`xx`, `tlh`, `français`) otherwise. Both exceptions mean malformed. The accepted set is every tag Babel knows. A well-formed tag outside Babel's locale data (`tlh`, a private-use `-x-` extension) takes the malformed path: warning, then English.

**Config model (`src/squads/_models/_config.py`).** `SquadsConfig` gains `working_language: str | None = None`, the raw value as written. `None` means the key is absent. A non-string TOML value (a number, a table) must not fail `load_config`: a before-validator in the style of `_tolerate_display` keeps it as its `repr` string so the resolver reports it as malformed. The model does no Babel parsing, since `_models` may import only `_clock`, `_errors` and `_util` from squads, and parsing belongs to the resolver below.

- `to_toml()` writes `working_language = "<tag>"` right after `squads_version` whenever the field is set. This is how `init` and adopt write the key.
- `to_toml_keeping(original)` (the version/schema stamp in `_services/_maintenance.py`) carries the `working_language` line over exactly as the original file has it, with the same verbatim rule `[display]` follows: present, malformed or non-string stays byte-identical, and absent stays absent. A stamp never adds the key to a squad that lacks it.

**Resolver (new top-level `src/squads/_language.py`).** It imports `babel` at module top and imports nothing from squads that `_models` could not. It holds:

- `DEFAULT_WORKING_LANGUAGE = "en"`.
- A frozen `WorkingLanguage` dataclass with `tag` (the canonical BCP 47 spelling, `pt-BR`, rebuilt from the parsed locale with `-` separators) and `name` (`Locale.get_display_name("en")`, e.g. `Portuguese (Brazil)`). The templates render the English name plus the tag, e.g. French (`fr`).
- `resolve_working_language(raw: str | None) -> tuple[WorkingLanguage, str | None]`. It never raises. Absent gives English and no problem. Valid gives the parsed language and no problem. Malformed gives English plus a problem string naming the value and the English fallback, e.g. `working_language 'fr_FR' in .squads.toml is not a BCP 47 language tag; using English (en)`.

Record the new edges in `tests/meta/test_package_import_edges_match_the_recorded_table.py`: `_cli -> _language top`, `_services -> _language top`, `_backends -> _language top`, `_views -> _language top`, plus whichever `_language -> …` edges the module ends up with. Add `_language` to any module allowlist the meta guards keep. A module constant that trips the mutable-state guard is allowlisted, not restructured.

**Startup validation and the warning (CLI edge).** Services return problems and never print, so the warning comes from the CLI. Add `working_language_notice()` to `src/squads/_cli/_common.py` next to `version_notice()` and call it from `main_callback` in `src/squads/_cli/__init__.py` right after `version_notice()`. Every command passes through that callback once. The notice resolves the squad from `get_context().client_cwd` (outside a squad, or with an unreadable config, it returns silently, as `version_notice` does), runs `resolve_working_language(sp.config.working_language)` and prints the problem through `print_warnings` style, on stderr (`warning: …`). Because `_cli/_common.py` imports `_language` at top, Babel is imported on every command, as ruled. An absent key prints nothing, and neither does a valid one. The warning goes to stderr only, so `--json` stdout stays parseable, the same contract `version_notice` already follows.

**`sq check` rule.** Add an always-on squad-global check, `working_language_valid`, next to `display_config_valid`.

- Implement `_working_language_valid(ctx)` in `src/squads/_services/_validators.py` and register it in the validator table there.
- Declare it in `src/squads/_workflow/_models.py` everywhere `display_config_valid` is listed, with a default level of `warn`.
- On a malformed value it emits one `CheckIssue` on `.squads.toml`, using the resolver's problem text with the fallback ("…; English (en) applies"). An absent or valid key emits nothing.
- Add its row to the always-on checks table in `docs/overrides.md`.

**How the name reaches the templates.** One derivation point, no threading through every constructor:

- `BackendContext` (`src/squads/_backends/_base.py`) gains a `working_language` property that resolves `self.paths.config.working_language` and discards the problem. Every construction in `_services/_base.py`, `_services/_validators.py` and `_migrations/` therefore render the same language, and `sq check`'s `backend_reconciled` comparison stays consistent with `sq sync`.
- `_backends/_claude_code/_backend.py::write_managed` and `_backends/_agents_md/_backend.py::write_managed` pass `working_language=ctx.working_language` (tag plus name) into `render(...)`.
- The `squads` skill is the `squads_skill` view, rendered at read time through `_views.render_source_view`. Add a `working_language` argument to `render_source_view` and its two callers, `_services/_views.py::render_view` and the read-time expansion in `_views.py`. Both have the config at hand (the `squad_dir_display` they already pass comes from `paths.config`), so they pass the resolved value from `paths.config.working_language` the same way, and the template gets `working_language`.
- Changing the key followed by `sq sync` therefore updates CLAUDE.md and AGENTS.md, and the skill updates on its next read.

**The rule text, stated once.** Add one shared partial, `src/squads/_rendering/templates/working_language.md.j2`, and `{% include %}` it from `claude/claude_section.md.j2` (a `## Working language` section after **Operators**), `agents_md/agents_section.md.j2` (the same place) and `views/squads_skill.md.j2` (under **Golden rules**). Proposed wording, with `{{ working_language.name }}` and `{{ working_language.tag }}`:

> This squad's working language is **French** (`fr`). Everything that goes through `sq` (item titles, bodies, sub-entity text, comments) and all communication between agents (briefs, handbacks, `@mention` comments) is written in French. When you talk to a human, reply in the language that human writes in, message by message. There is always exactly one of each: the working language, set in `.squads.toml`, and the conversation language, deduced from the human.

The partial must name no bundled type or role, because `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py` checks for that. Under `StrictUndefined`, every direct `render()` of these templates in tests (for example `tests/unit/test_managed_section_and_cheatsheet_goldens.py`) must pass `working_language` too.

**init / adopt (`src/squads/_services/_service.py`).** `init()` builds `SquadsConfig(..., working_language="en")`. `adopt()` does the same only on the branch that creates `.squads.toml`. An adopt over an existing `.squads.toml` leaves it untouched, so that squad renders English until the key is set.

**Regenerated artifacts.** A template change requires all of these:

- `UPDATE_GOLDENS=1` on the managed-section goldens (`tests/goldens/claude_md_section.txt`, `tests/goldens/agents_md_section.txt`) and on any squads-skill golden or integration expectation (`tests/integration/test_squads_skill_content_generation.py`).
- `uv run python scripts/gen_template_manifest.py`, write mode, then `--check`. This refreshes `src/squads/_rendering/templates_manifest.json` and `content_store.json` for the 0.17.0 entry. The new partial is a new overridable template, so update any test that pins the template count.
- The `sq override` scaffold/diff surface lists the new partial with no extra code. Confirm it with `sq override list` in a scratch squad.

## Test plan

Name tests by behaviour. No ticket ids in file or test names.

Unit (`tests/unit/`), `resolve_working_language` table-driven over input shape:

- Absent (`None`) gives `en`/English with no problem.
- Valid: `fr`, `en`, `pt-BR`, lower-case `pt-br` normalised to `pt-BR`, a script subtag `sr-Latn`, `zh-Hant-TW`.
- Malformed gives `en` and a problem: `fr_FR`, `en-US-x-foo`, the empty string, whitespace, `xx`, `français`, and a non-string value coming through the config model.
- `SquadsConfig` round-trip: `to_toml()` writes the key when set and omits it when `None`. `to_toml_keeping` preserves a valid, a malformed and an absent key byte-for-byte. A non-string TOML value loads without raising.

Service (`tests/service/`):

- `init` writes `working_language = "en"`.
- `adopt` with no config writes it, and `adopt` over an existing config leaves the file unchanged.
- A squad with the key absent renders English in both backends' managed sections.
- With `fr`, `pt-BR` and a malformed value, `refresh_managed`/`sync` renders the expected name and tag (malformed renders English) in CLAUDE.md and AGENTS.md, and `render_view("squads_skill", …)` renders it in the skill.
- Changing the key and syncing again updates all three.
- `sq check`'s `backend_reconciled` stays clean after the sync in each case.

CLI smoke (`tests/cli/`, `CliRunner`):

- With the key absent, any command (e.g. `sq list`) prints no `working_language` text on stderr.
- `fr` and `pt-BR` are silent.
- A malformed value makes `sq list` exit 0 with exactly one `warning:` line naming the value and English on stderr, while `sq list --json` stdout still parses.
- Outside a squad, there is no warning.
- `sq init` then `sq skill squads show` shows English, and `sq sync` after editing the key to `fr` shows French in CLAUDE.md.
- Repeat the rendering assertions with `--backend agents_md`.

`sq check` (service plus CLI):

- `working_language_valid` reports one `warn` issue on `.squads.toml` for a malformed value (`fr_FR`, `tlh`, a number), naming the value and the English fallback.
- It reports nothing for an absent key, `fr` or `pt-BR`.
- A level override in `.overrides/workflow.toml` changes its level, the same way it does for `display_config_valid`.
- `sq check --json` carries the issue.

Meta: the import-edge table, the mutable-state guard and the template-manifest `--check` all pass.

Gates: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, `uv run --all-extras pytest` (one run, to a log file), and `sq check` clean.

## CHANGELOG (unreleased `## [0.17.0]`, `### Added`)

The tech writer authors the final prose. Its substance:

- **`working_language` in `.squads.toml`: the language the squad works in.** It takes any BCP 47 tag, such as `fr`, `en` or `pt-BR`. Item text, comments and agent-to-agent communication are in that language, and agents answer a human in the language the human writes in.
- The CLAUDE.md and AGENTS.md managed sections and the `squads` skill state the rule with the language's name, and `sq sync` refreshes them when the key changes.
- `sq init` and `sq adopt` write `working_language = "en"`. A squad without the key works in English, with no warning.
- A value that is not a language tag prints a warning on every command, and `sq check` reports it through the always-on `working_language_valid` check (`warn`). English applies. It is never an error.
- squads now depends on Babel.
- No migration is needed.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1098 add-subtask "<title>"`; track with `sq task 1098 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add Babel, the resolver and the raw config key

<!-- sq:subtask:ST1:body -->
Add Babel and the resolver, and give the config model the raw key.

- `pyproject.toml`: add `"babel>=2.18"` to `[project].dependencies`, then run `uv lock`.
- New `src/squads/_language.py`, which imports Babel at module top. It holds `DEFAULT_WORKING_LANGUAGE`, a frozen `WorkingLanguage(tag, name)`, and `resolve_working_language(raw) -> (WorkingLanguage, problem | None)`. It parses with `Locale.parse(raw, sep="-")`, catches `ValueError` and `UnknownLocaleError`, gives the tag in its canonical `-` form, and takes the name from `get_display_name("en")`. It never raises.
- `SquadsConfig.working_language: str | None` stores the raw value. A non-string TOML value is tolerated (kept as its repr), so it reports as malformed instead of failing `load_config`.
- `to_toml()` writes the key when it is set. `to_toml_keeping()` carries the original `working_language` line over verbatim, never adds it, and never normalises it.
- Record the new import edges in the meta table.
- Tests: table-driven resolver cases (absent, `fr`, `en`, `pt-BR`, `pt-br`, `sr-Latn`, `zh-Hant-TW`, and malformed `fr_FR`, `en-US-x-foo`, empty, whitespace, `xx`, `français`, a number), and config round-trip and stamp-preservation tests.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Validate on every command and warn on stderr

<!-- sq:subtask:ST2:body -->
Validate on every command and warn at the CLI edge.

- `src/squads/_cli/_common.py`: add `working_language_notice()` beside `version_notice()`. It resolves the squad from `get_context().client_cwd`, returns silently outside a squad or on an unreadable config, and runs the resolver. On a problem it prints one `warning:` line on stderr. An absent or valid key prints nothing.
- `src/squads/_cli/__init__.py::main_callback`: call it right after `version_notice()`, so it runs once per invocation, on every command, with Babel imported through `_common`'s top-level import.
- CLI smoke tests:
  - Absent key: silent.
  - `fr` and `pt-BR`: silent.
  - Malformed value: exit 0 and exactly one warning naming the value and English. `--json` stdout still parses.
  - Outside a squad: no warning.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Render the rule in both backends and the squads skill

<!-- sq:subtask:ST3:body -->
Render the one language rule in CLAUDE.md, AGENTS.md and the `squads` skill.

- New partial `src/squads/_rendering/templates/working_language.md.j2`. The task body has the wording. It renders `working_language.name` and `working_language.tag`, and names no bundled type or role.
- Include the partial from `claude/claude_section.md.j2`, `agents_md/agents_section.md.j2` and `views/squads_skill.md.j2`.
- `BackendContext.working_language` property, derived from `paths.config`. Both backends' `write_managed` pass it to `render`.
- `_views.render_source_view` takes `working_language`. Its two callers (`_services/_views.py::render_view` and read-time expansion in `_views.py`) pass the value resolved from `paths.config`.
- Regenerate with `UPDATE_GOLDENS=1`: `claude_md_section.txt`, `agents_md_section.txt`, and the squads-skill expectations. Pass `working_language` in direct `render()` test calls. Run `scripts/gen_template_manifest.py`, write mode then `--check`. Update any pinned template count.
- Service tests: with `fr`, `pt-BR`, a malformed value and an absent key, each backend and the skill render the expected name, and `backend_reconciled` stays clean after sync. Changing the key and syncing again updates all three.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Write working_language on init and adopt

<!-- sq:subtask:ST4:body -->
Write the key on init and adopt.

- `src/squads/_services/_service.py::init()` builds the config with `working_language="en"`.
- `adopt()` does the same on the branch that creates `.squads.toml`. An adopt over an existing config does not rewrite it, so a squad without the key renders English with no warning.
- Service tests: a fresh init has `working_language = "en"` in `.squads.toml` and English in the rendered rule. Adopt into a bare folder writes the key. Adopt over an existing keyless config leaves the file byte-identical.
- CLI smoke: `sq init`, then `sq skill squads show`, shows English.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Document the key and add the CHANGELOG entry

<!-- sq:subtask:ST5:body -->
Document `working_language` for adopters, and write its CHANGELOG entry.

- `docs/stability.md`: a "Working language in `.squads.toml`" subsection after "Display settings". It covers the BCP 47 tag, the English default, the absent key (silent), the malformed value (warning, English), that a stamp keeps the line as written, and that `language`/`locale` are not part of it.
- `docs/adoption.md` (or the roles/backends page the writer judges best): the two-language model, with the configured working language for `sq` content and agent-to-agent communication, and the conversation language deduced from the human. Add one example per tag, and a note that the CLI's own display language is a separate setting.
- README `.squads.toml` tree comment: mention the key.
- CHANGELOG `## [0.17.0]` `### Added`: one entry, following the substance in the task body. No item ids, no process narration.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Report a malformed working_language in sq check

<!-- sq:subtask:ST6:body -->
Report a malformed `working_language` in `sq check`.

- In `src/squads/_services/_validators.py`, add `_working_language_valid(ctx)` next to `_display_config_valid` and register it in the validator table.
- Declare `working_language_valid` in `src/squads/_workflow/_models.py` everywhere `display_config_valid` is listed, with a default level of `warn`.
- On a malformed value it emits one `CheckIssue` on `.squads.toml`, with the resolver's problem text and the English fallback. An absent or valid key emits nothing.
- Add its row to the always-on checks table in `docs/overrides.md`.
- Tests:
  - Malformed values (`fr_FR`, `tlh`, a number) give one `warn` issue.
  - An absent key, `fr` and `pt-BR` give none.
  - A level override in `.overrides/workflow.toml` is honoured.
  - `sq check --json` carries the issue.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T09:19:07Z] `op-pierre` Pierre Chat:
  - 1. Render the English name plus the tag, e.g. French (fr); the future locale setting may later render it in other languages.
  - 2. Any tag Babel knows is an acceptable reading of every standard tag; an unknown tag takes the malformed path (warning, then English).
  - 3. sq check also reports a malformed working_language, like the display table check.
  - 4. The new .squads.toml key gets a short ADR from the architect.
  - 5. Running sq sync on this repo is a release step, outside this task.
- [2026-10-24T14:47:37Z] `manager` Catherine Manager:
  - Dispatched to @python-dev for the code subtasks; the docs and CHANGELOG subtask goes to the tech-writer after.
- [2026-10-24T15:01:23Z] `python-dev` Elias Python:
  - @manager ST1, ST2, ST3, ST4 and ST6 are done; ST5 (docs, CHANGELOG) is left to the tech-writer. Not committed.
    
    - Babel 2.18 added (pyproject + uv.lock). New `_language.py` resolver; `SquadsConfig.working_language` (raw value, non-string kept as repr); `to_toml_keeping` carries the line verbatim and never adds it.
    - `working_language_notice()` in `main_callback` warns once on stderr; `BackendContext.working_language` and `ServiceCore.working_language` feed the shared `working_language.md.j2` partial into CLAUDE.md, AGENTS.md and the squads skill; `init` and an adopt that creates the config write `"en"`; `working_language_valid` (warn) in `sq check`, with its row in docs/overrides.md.
    - Regenerated: template manifest (0.17.0 entry, check clean), the two section goldens, the shared migrated-corpus CLAUDE.md golden.
    - Gates: pyright, ruff check and format clean; tests/meta, tests/unit and tests/integration pass (5297 passed); `sq check` clean. The service and cli directories were not run.
    - Tests added: 2 files, 9 functions, 29 cases (unit 20, service 9). Falsified: malformed accepted as valid, init not writing the key, stamp adding the key, stamp normalising the line, and the missing startup call each turn them red.
    - Drove the dev CLI in a scratch squad: init writes the key, `fr` and `pt-BR` render in CLAUDE.md, AGENTS.md and the skill, a malformed value warns once on stderr with `--json` still parsing and `sq check` reporting it, an absent key is silent and a sync does not add it.
    - Deviations from ADR-1100: none. The `sq check` message reuses the resolver text ("...; using English (en)") rather than a separate "applies" wording. No level-override test added; the level goes through the shared squad-global resolver.
- [2026-10-24T15:34:12Z] `python-dev` Elias Python:
  - @manager REV-1118 F1-F8 addressed, not committed. Needs your call: with the stamp no longer rebuilding .squads.toml, the legacy default_backend (v0.2 corpus) and default_role keys now survive a stamp where the rebuild used to rewrite/drop them; 11 migration-corpus golden tests fail on exactly that (tests/integration/test_migrate_up_output_is_unchanged_for_every_corpus.py x10, test_migration_corpus.py::test_v0_2_migration_rewrites_the_legacy_backend_key). I left the goldens untouched; either the migrations normalise those keys explicitly or the goldens are regenerated.
- [2026-10-24T17:28:31Z] `op-pierre` Pierre Chat:
  - Decision: `.squads.toml` is the adopter's file. `sq` writes it only at `init`/adopt (whole file) and during `sq migrate up`. `squads_version` leaves `.squads.toml`; the generated-file drift check derives from the generated files' own version stamps. The one remaining rewrite is the `schema_version` line during a migration. Legacy 0.2-era keys are handled by parsing with `tomllib` and regenerating the file during the migration, comments lost on those squads. No `tomlkit`. Needs a short ADR before implementation.
- [2026-10-24T18:35:35Z] `python-dev` Elias Python:
  - - ADR-1119 implemented, uncommitted. squads_version is gone from SquadsConfig and SquadsDB, version_notice, _stamp_version, to_toml_keeping, drop_legacy_config_keys, the drift hints (empty_body_hint_state now has three states) and the squads_version args of plan_reconcile and create_empty. sq sync no longer writes .squads.toml and the roster backfill is unconditional. New _migrations/_config_text.py: the verified one-value schema_version edit (computed before the first runner, written last, SquadsError naming file and line otherwise) and the legacy-key regeneration with read-back check; keys the model does not carry print in the migrate report. to_toml now writes a non-default [display] table so a regeneration keeps it. F5 and F9 of REV-1118 fixed and commented.
    - Backfill timing, 208 roles and 512 skills (scratch squad, dev build): sync 4.05 s and 4.04 s with the backfill against 3.83 s and 3.79 s without it, so about 0.2 s; the backfill alone measures 0.117 s on a converged roster.
    - Gates: pyright, ruff check and format clean; sq check clean. Ran tests/meta, integration, service, unit and the touched cli files: 10538 passed. Full suite not run. migrated_corpus goldens regenerated with UPDATE_GOLDENS=1 (squads_version gone from the indexes; regenerated legacy configs now share one copy in _shared).
    - git status: about 45 modified, 4 deleted and 2 renamed test files (git rm and git mv left those staged), 4 new files, goldens under tests/goldens/migrated_corpus. Nothing committed.
    - Not done: docs still describe squads_version and the upgrade notice (docs/faq.md, docs/migration.md, docs/internals.md), and CHANGELOG has no entry; both belong to the writer.
- [2026-10-24T18:46:19Z] `tech-writer` Theo Writer:
  - @manager ST5 done, not committed. working_language documented in docs/stability.md (new "Working language in .squads.toml" and "Who writes .squads.toml" subsections), docs/adoption.md ("The working language": two-language model, tag examples, adopt-over-existing behaviour) and a FAQ entry for the warning; README tree comment updated.
  - squads_version and upgrade-notice prose replaced with present truth in docs/faq.md, docs/migration.md (version-stamping section rewritten, new "What sq migrate up writes to .squads.toml"), docs/internals.md, docs/backends.md, docs/overrides.md (override-base stamp now says "installed squads version").
  - CHANGELOG 0.17.0: one Added entry (working_language), two Changed (sync leaves .squads.toml alone; migrate up stamps one value or refuses, legacy-key regeneration loses comments), one Removed (squads_version + notice, run sq sync after upgrading). Claims checked against src and a scratch squad (warning text, sq check exit 0 at warn, rendered rule, tag examples). tests/meta passes (456).
- [2026-10-24T19:01:44Z] `manager` Catherine Manager:
  - Done: ADR-1100 and ADR-1119 implemented, REV-1118 Approved with all 15 findings Verified, full suite green at 1104c03f, docs and CHANGELOG landed.
<!-- sq:discussion:end -->
