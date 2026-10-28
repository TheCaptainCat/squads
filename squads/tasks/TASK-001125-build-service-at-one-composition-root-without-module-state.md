---
id: TASK-1125
sequence_id: 1125
type: task
title: Build Service at one composition root, without module state
status: Done
parent: FEAT-1092
author: tech-lead
priority: medium
refs:
- REV-956:addresses
- TASK-1124:depends-on
- ADR-1128:depends-on
description: 'REV-956 F15: one composition function, collaborators passed in, renderer
  squad dir explicit, literal backend table.'
subentities:
- local_id: ST1
  title: Route every Service construction through one function
  status: Done
  story: US2
- local_id: ST2
  title: Pass store and backends in; make the registry a table
  status: Done
  story: US2
- local_id: ST3
  title: Pass the squad directory to the renderer explicitly
  status: Done
  story: US2
- local_id: ST4
  title: Resolve the spec documents once at the root
  status: Done
  story: US2
created_at: '2026-10-24T21:53:44Z'
updated_at: '2026-10-28T12:46:04Z'
---
<!-- sq:body -->
## Goal

Build `Service` in one place, load each spec document once, and drop the process-wide state construction leans on, with no change to what `sq` does. Finding F15, and the composition root ADR-1128 decides on in place of a DI container (F14).

## Acceptance

- Every production `Service` construction goes through one composition function.
- **Load once.** Per invocation and per document (workflow spec, role catalog, playbook): the packaged TOML is parsed at most once, the project override is read at most once, and each model (bundled, and merged when an override exists) is built at most once. A bare `sq --version` loads none. This holds on every path: ordinary commands, `--help`, `sq check` and each fallback mode.
- Code below the root receives the loaded document. It never calls a loader with a squad directory to get it again. A lazily resolved document is memoised at the root, so its first use is its only load.
- No module-level squad state: no active-squad-dir `ContextVar`, no backend registration side effect.

## Re-measured on 2026-10-25 (HEAD 565e1671, read)

- Ten production `Service(...)` constructions: `init` and `adopt` (`src/squads/_services/_service.py:173`, `:262`), three `open_service` branches (`:343`, `:356`, `:373`), three in the CLI bypass ladder (`src/squads/_cli/_common.py:1665`, `:1674`, `:1679`) and two `sq check` fallbacks (`src/squads/_cli/_main.py:1565`, `:1572`). Four of them pass the bundled playbook (`get_playbook_spec()`) rather than a resolved one (`_common.py:1665`, `:1674`, `_main.py:1565`, `:1572`).
- Four CLI accessors: `get_service` (`_cli/_common.py:1539`), `_build_plain_service` (`:1580`), `get_service_bypassing_index_cross_check` (`:1605`) and `_build_bypass_fallback_service` (`:1656`).
- `ServiceCore.__init__` calls `set_active_squad_dir` (`src/squads/_services/_base.py:570`), and the CLI accessors re-assert it on memo hits (`_cli/_common.py:1572`, `:1642`) because each `anyio.run` crossing copies the `ContextVar`. `render` (`src/squads/_rendering/_engine.py:304`) has 13 call sites outside the engine; `scaffold_body` has two (`_services/_base.py:611`, `_services/_validators.py:768`).
- The backend registry (`src/squads/_backends/_registry.py`) is a module-global `_REGISTRY` dict filled by importing two packages for their side effect, behind `global _loaded`.

**Excess loads**, measured by the architect on release/0.17 with a profiler wrapper (parse / override read / build; rows that break the load-once rule):

| Command | Workflow | Roles | Playbook |
|---|---|---|---|
| `show`, `list` | 1/-/1 | 1/-/1 | 2/-/1 |
| `check` | 1/-/1 | 170/-/170 | 2/-/1 |
| `--help`, with overrides | 3/1/3 | 1/0/1 | 0/0/0 |
| `show`, `list`, with overrides | 3/1/3 | 2/1/2 | 2/1/1 |
| `check`, with overrides | 3/1/3 | 172/171/172 | 3/1/2 |

Sources:

- The role resolver reloads the catalog on every resolution: `_predefined_for_slug` and `resolve_pronouns` (`src/squads/_roles/_resolver.py:74`, `:433`) call `load_role_catalog(squad_dir)`, about three times per role for each roster check in `_config_integrity.check_all` and `_validators`. 170 loads in `sq check`, scaling with the roster.
- The coverage check parses the packaged playbook a second time: `_check_coverage` calls `_bundled_type_names` (`src/squads/_interactions/_loader.py:312`, `:300`) inside the build that already parsed it. With an override, the bundled playbook built for `bundled_skill_slugs` (`_interactions/_skills.py:167`) parses it again.
- Under a workflow override, `validate_against_index` (`src/squads/_workflow/_loader.py:1290`, via `_collect_badge_alignment_errors` at `:1113`) rebuilds the bundled spec instead of using the one already built: three parses, bundled model built twice.
- Under a roles override, the merged catalog re-parses the packaged file instead of reusing the bundled parse.

## Approach

1. **One composition function** takes the squad paths and a mode (normal, skip the index cross-check, playbook unavailable, bundled fallback) and returns the service. All ten sites call it. The fallback order becomes one readable table in one module, replacing the try/except ladders in `_cli/_common.py` and `_cli/_main.py`. Each mode keeps exactly the spec and playbook today's site chooses. If a site's choice looks accidental, report it to the operator; do not change it here.
2. **Documents resolved together, once.** One function resolves the workflow spec, the role catalog and the playbook for a squad, on the shared load path in `src/squads/_specload.py`, and absorbs `resolve_playbook` (`src/squads/_services/_service.py:59`). Each packaged file is parsed once and that parse feeds both the bundled and the merged model. The composition function calls it. `open_service` does not read the role catalog today, so loading it eagerly would make a malformed roles override a hard stop for every command. Resolve the catalog lazily, on first use, memoised at the root, so each command fails exactly where it fails today; making it a hard stop instead is a behaviour change the operator decides, not this task. The role resolver, the coverage check and `validate_against_index` take the loaded document instead of loading it.
3. **Collaborators passed in.** The `IndexStore` and the backend list are constructed by the composition function and passed to `ServiceCore.__init__`, not built inside it.
4. **Renderer takes the squad directory.** `render` and `scaffold_body` take the squad directory from the caller that already holds `paths`. `set_active_squad_dir`, its `ContextVar`, both re-asserts and their docstring go. The Jinja environment cache stays keyed on the squad directory passed in: the daemon retires when anything under `.overrides/` changes (ADR-1052 point 13), so no long-lived process holds an environment built before an override template appeared, and no content keying is needed.
5. **Backend registry as a literal table.** A name-to-class mapping with no registration side effect. The active backends are instantiated once in the composition function. The two backend package inits lose their registration side effect, and CLAUDE.md's non-empty-init list and the mutable-state allowlist entry for `_REGISTRY` follow.

## Tests

The existing suite is the net, with no assertion edited.

- **One table, "service composition by mode"**, with only these rows: normal; index cross-check skipped; playbook override that fails to load; workflow override that fails to load (bundled fallback); roles override that fails to load (a command that never reads the catalog still runs). Each row checks which spec and playbook the service holds and that it opens the squad given. The rows cover the four ad-hoc ladders this replaces. Add a row for a squad with a playbook override running `sq repair` after a cross-check refusal, so that behaviour is pinned by a driven test.
- **One table, "document loads per invocation"**: rows `--version`, `--help`, `show`, `list` and `check`, each without and with workflow, roles and playbook overrides. Each row counts packaged parses, override reads and model builds per document and asserts at most one of each per model (none for `--version`). The `check` row with a roster of several roles is the boundary that today reads 170.
- **Rendering under two squads in one process:** one test where two squads with different template overrides render in turn and each gets its own. This is the case the ambient squad directory exists for, and it must stay right without it.
- `tests/meta`: drop the `_REGISTRY` allowlist entry so the mutable-state guard enforces the removal.

Falsify each new row once by breaking the mode table, reintroducing one reload, or dropping the render argument, and record the red in the handoff.

## Generated output

None. Generated files are byte-identical before and after on a pinned roster in a scratch squad. The template manifest is unchanged.

## CHANGELOG substance

No adopter-visible behaviour change; `sq check` on a large roster gets faster. Report that to the writer. CLAUDE.md's architecture section changes: the composition function, the inits, and the removal of the ambient render state.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1125 add-subtask "<title>"`; track with `sq task 1125 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Route every Service construction through one function

<!-- sq:subtask:ST1:body -->
Write one composition function taking the squad paths and a mode (normal, index cross-check skipped, playbook unavailable, bundled fallback), with the fallback order as one table. Route all ten production `Service(...)` constructions and the four CLI accessors through it. Each mode keeps today's spec and playbook choice; report any choice that looks accidental instead of changing it. Add the composition-by-mode table.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Pass store and backends in; make the registry a table

<!-- sq:subtask:ST2:body -->
Construct the `IndexStore` and the backends in the composition function and pass them to `ServiceCore.__init__`. Turn `_backends/_registry.py` into a literal name-to-class table with no import side effect or `global` flag, and drop its mutable-state allowlist entry.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Pass the squad directory to the renderer explicitly

<!-- sq:subtask:ST3:body -->
Pass the squad directory to `render` and `scaffold_body` from callers that hold `paths`, and keep the Jinja environment cache keyed on that directory (Approach step 4). Remove `set_active_squad_dir`, its `ContextVar`, the call in `ServiceCore.__init__` and the two re-asserts in `_cli/_common.py`. Add the two-squads-in-one-process render test.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Resolve the spec documents once at the root

<!-- sq:subtask:ST4:body -->
Write the one resolver for the workflow spec, the role catalog and the playbook on `_specload.py`, absorbing `resolve_playbook`, and call it from the composition function. Parse each packaged file once and build the bundled and merged models from that parse. Resolve the role catalog lazily, memoised at the root, so a malformed roles override fails where it fails today. Remove each excess load in "Re-measured": the role resolver takes the catalog instead of `squad_dir` (`_predefined_for_slug`, `resolve_pronouns` and their callers), `_check_coverage` reuses the parse it runs inside, and `validate_against_index` takes the bundled spec already built. Add the "document loads per invocation" table.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T21:56:15Z] `tech-lead` Olivia Lead:
  - @op-pierre this task waits on the DI container decision (REV-956 F14), which you ruled is made in 0.17 with this work. Recommendation: no container. Build the one composition function this task describes. The reviewer's measurements still hold: a six-node graph, 0.17 ms to construct, four 0.x packages to add, and a bare `NameError` on hints that are importable only under `TYPE_CHECKING`. The required parameters and the passed-in collaborators from TASK-1124 and this task make the classes injectable, so if the daemon's per-request scope turns out to need a scoped injector, it replaces one function when FEAT-33 is designed. Adopting soupape now would buy nothing that one function does not.
    @architect two inputs: record the DI decision as an ADR once op-pierre rules, and settle the Jinja environment cache keying before ST3 (renderer squad directory).
- [2026-10-24T21:59:27Z] `architect` Robert Architect:
  - @tech-lead the DI decision this task waits on is ADR-1128 (Proposed, recommends A, which is this task as written); ruling pending from op-pierre. Jinja cache keying is not covered there.
- [2026-10-25T04:36:21Z] `tech-lead` Olivia Lead:
  - Approach step 2 added from TASK-1124 ST4: one resolver for spec, role catalog and playbook, catalog loaded lazily; making a broken roles override a hard stop is an operator call. Test table gains a roles-override row.
- [2026-10-25T10:51:42Z] `architect` Robert Architect:
  - ADR-1128 is Accepted (option A). Its decision adds an acceptance rule for this task: per invocation and per document, the packaged TOML is parsed at most once, the override read at most once, and each distinct model (bundled, merged) built at most once; a path that needs no document (bare `sq --version`) loads none.
    
    Measured on release/0.17 HEAD (9b2ec16e, exported clean), driven with `uv run --all-extras` and a profiler wrapper (no src edit) counting `_specload.bundled_raw` (parse), `_specload.read_override` (override read) and each loader's model builder (build). Scratch squads: default init, 8 roles, one task; "custom" adds scaffolded workflow, roles and playbook overrides (comment-only files, so present and read). Format: parse / override read / build. All runs exit 0.
    
    | Command | Workflow | Roles | Playbook |
    |---|---|---|---|
    | `--version` | 0/0/0 | 0/0/0 | 0/0/0 |
    | `--help` | 1/-/1 | 1/-/1 | 0/-/0 |
    | `task 21 show` | 1/-/1 | 1/-/1 | **2**/-/1 |
    | `list` | 1/-/1 | 1/-/1 | **2**/-/1 |
    | `check` | 1/-/1 | **170/-/170** | **2**/-/1 |
    | custom `--help` | **3**/1/**3** | 1/0/1 | 0/0/0 |
    | custom `task 21 show`, `list` | **3**/1/**3** | **2**/1/2 | **2**/1/1 |
    | custom `check` | **3**/1/**3** | **172/171/172** | **3**/1/2 |
    
    Bold breaks the rule. Where the extra loads come from (stack traces):
    - Roles in `sq check`: `_roles/_resolver.py` reloads the catalog on every role resolution (`_predefined_for_slug`, `resolve_pronouns`, about three per role, for each roster check in `_config_integrity.check_all` and `_validators`). Scales with the roster.
    - Playbook: `_check_coverage` re-parses the packaged file (`_bundled_type_names`) inside the build that already parsed it; in custom `check`, the bundled playbook singleton is also built for `bundled_skill_slugs` (claude_code backend pointer descriptions).
    - Workflow with an override: `validate_against_index` (`_collect_badge_alignment_errors`) rebuilds the bundled spec instead of using the import-time singleton, so the packaged file is parsed three times and the bundled model built twice.
    - Roles with an override: the bundled singleton plus one merged load; the merged one is the extra parse.
- [2026-10-25T11:05:51Z] `architect` Robert Architect:
  - Jinja environment cache keying: keep it keyed on the squad directory passed to the renderer. ADR-1052 point 13 retires the daemon when anything under .overrides/ changes, so a long-lived process never holds an environment built before an override template appeared; no content keying is needed.
- [2026-10-25T11:32:45Z] `tech-lead` Olivia Lead:
  - Aligned with ADR-1128: load-once acceptance added; excess loads (role resolver, coverage re-parse, validate_against_index rebuild, roles merged re-parse) recorded in Re-measured; ST4 merges Approach step 2 with their removal and owns the load-count table; ST3 records the squad-directory cache keying. Line numbers re-read on 565e1671. ST4 maps to FEAT-1092 US2, which already covers loader unification.
- [2026-10-25T11:33:10Z] `manager` Catherine Manager:
  - Promoted to Ready at dispatch: ADR-1128 Accepted, load-once acceptance and ST4 folded in by the tech lead.
- [2026-10-25T12:38:52Z] `python-dev` Elias Python:
  - Implemented ST1-ST4. Not committed. Gates clean (`uv run --all-extras pyright`, `ruff check .`, `ruff format --check .`); targeted pytest results under Verification.
    
    ## ST1 - one composition function
    - `compose_service(paths, mode, resolved_spec=, sources=)` in `_services/_service.py` is the only path to a `Service`; `build_service` is the only `Service(...)` call. `init`, `adopt`, `open_service`, the CLI accessors and `sq check` all go through it. The four ladders are tables there: `BYPASS_FALLBACKS`, `MIGRATE_FALLBACKS`, `CHECK_FALLBACKS`, plus `Mode`.
    - Modes and what each holds (spec / playbook), identical to the site it replaces: normal = merged, index-checked / merged. index-check-skipped = merged / BUNDLED. migrate = merged / merged, each refusal worded as before. playbook-unavailable = merged (bundled if it will not load) / bundled. bundled-fallback = bundled / bundled.
    - Table "service composition by mode" (5 rows) plus the `sq repair` row: `tests/service/test_a_service_is_composed_from_the_documents_its_mode_chooses.py`.
    
    ## ST2 - collaborators passed in, registry a table
    - `ServiceCore.__init__(paths, spec, playbook, store, backends, catalog)`; the `IndexStore` and the backends are built in `build_service`. Backends are instantiated once, on first use, so an unknown backend name still fails where it fails today.
    - `_backends/_registry.py` is a literal table; `_REGISTRY`, `_loaded`, `register()` and the two backend inits' side effects are gone. Mutable-state allowlist, import-edge table and non-empty-init list updated.
    
    ## ST3 - explicit squad directory for the renderer
    - `render`, `has_template`, `template_source`, `creation_template_name`, `scaffold_body` take `from_squad`; `set_active_squad_dir`, its ContextVar, the call in `ServiceCore.__init__` and both re-asserts are gone. `from_squad` is threaded through `_views`, `_view_tags`, `_discussion`, the backends, the validators and the migrations that render. The Environment cache stays keyed on the directory.
    - Test: two squads overriding the same creation template differently each create from their own (`tests/service/test_override_render_cache_isolation.py`).
    
    ## ST4 - documents resolved once at the root
    - `_spec_documents.py` (new; not `_specload.py`, which the three loaders import, so a resolver there would cycle): `resolve_documents`, `resolve_playbook` (moved from `_service.py`), `SpecSources`. `_specload.bundled_raw` hands out copies of one parse per process; `Lazy` memoises a value or its `SquadsError`.
    - The role catalog is a `CatalogSource` (a lazy callable): the resolver functions, `BackendContext`, `SquadGlobalContext`, `MigrationContext`, the validators, the view sources and the override checks take it instead of `squad_dir`. A malformed roles override still fails only where the catalog is first used.
    - `_check_coverage` reads the key set from the shared parse; `validate_against_index` takes the bundled spec (`bundled=`); the playbook loader takes the squad's catalog (`project_catalog=`) instead of loading it.
    - `SpecSources` is shared per invocation (Click root meta, `invocation_sources`) by the root callback, a refused service and its fallback, so a refusal followed by a fallback reads each override once.
    - Table "document loads per invocation" (10 rows, fresh interpreter, profiled): `tests/cli/test_each_spec_document_is_loaded_at_most_once_per_invocation.py`.
    
    ## Loads per invocation (packaged parses / override reads / model builds)
    Squad: 8 bundled roles + one developer, one task. "Overrides" = workflow, roles and playbook override all present. Before = HEAD 556b8239 exported clean, counting `bundled_raw` calls; after = this tree, counting actual parses.
    
    | Command | Workflow before | after | Roles before | after | Playbook before | after |
    |---|---|---|---|---|---|---|
    | `--version` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
    | `--help` | 1/0/1 | 1/0/1 | 1/0/1 | 1/0/1 | 0/0/0 | 0/0/0 |
    | `show`, `list` | 1/0/1 | 1/0/1 | 1/0/1 | 1/0/1 | 2/0/1 | 1/0/1 |
    | `check` | 1/0/1 | 1/0/1 | 191/0/191 | 1/0/1 | 2/0/1 | 1/0/1 |
    | `--help`, overrides | 3/1/3 | 1/1/2 | 1/0/1 | 1/0/1 | 0/0/0 | 0/0/0 |
    | `show`, `list`, overrides | 3/1/3 | 1/1/2 | 2/1/2 | 1/1/2 | 2/1/1 | 1/1/1 |
    | `check`, overrides | 3/1/3 | 1/1/2 | 193/192/193 | 1/1/2 | 3/1/2 | 1/1/2 |
    
    Builds of 2 are the bundled model (built at import) and the merged one; no model is built twice.
    
    Fallback paths (override files broken or in conflict with the corpus), same cells:
    
    | Scenario, command | Workflow before | after | Roles before | after | Playbook before | after |
    |---|---|---|---|---|---|---|
    | priority codes shrunk under a live task, `repair` | 4/2/4 | 1/1/2 | 1/0/1 | 1/0/1 | 2/0/1 | 1/0/1 |
    | same, `check` | 4/1/3 | 1/1/2 | 192/191/192 | 1/1/2 | 2/0/1 | 1/0/1 |
    | malformed playbook override, `check` | 4/2/4 | 1/1/2 | 192/191/192 | 1/1/2 | 3/1/1 | 1/1/1 |
    | malformed playbook override, `repair` | 4/2/4 | 1/1/2 | 1/0/1 | 1/0/1 | 3/1/1 | 1/1/1 |
    | malformed workflow override, `check` | 1/1/1 | 1/1/1 | 192/191/192 | 1/1/2 | 2/0/1 | 1/0/1 |
    | malformed workflow override, `repair` | 1/2/1 | 1/1/1 | 1/0/1 | 1/0/1 | 2/0/1 | 1/0/1 |
    | malformed roles override, `check` | 4/2/4 | 1/1/2 | 68/66/2 | 1/1/1 | 3/1/1 | 1/1/1 |
    | malformed roles override, `repair` | 4/2/4 | 1/1/2 | 2/1/1 | 1/1/1 | 3/1/1 | 1/1/1 |
    
    Not measured: `sq workflow lint` (diagnostic; it loads the override once in collect mode and once more for the transform check), `sq migrate up`, the TUI.
    
    ## Generated output
    Two scratch squads on a pinned roster (claude_code and agents_md backends, 8 roles + a developer, an epic, a task with a comment, `--at 2026-01-01T00:00:00Z`; one plain, one with scaffolded workflow, roles and playbook overrides), `sq init`, `sq sync`, `sq check`. Whole tree compared with `diff -r` between HEAD 556b8239 (exported clean) and this tree: 53 and 56 files, no difference (empty diff, including CLAUDE.md, AGENTS.md, the `.claude/` pointers and skills). Each side was generated twice first to show the output is deterministic. The template manifest is unchanged (tests/meta green).
    
    ## Falsification (each new row broken once, restored, byte-compared)
    Composition table: normal row red when NORMAL takes the bundled playbook (also reddens the playbook-failure row, which then no longer refuses); "index cross-check skipped" red when that mode resolves the playbook; "playbook override that fails to load" red when that mode takes the bundled spec; "workflow override that fails to load" red when `BYPASS_FALLBACKS` loses its bundled rung; "roles override that fails to load" red when `resolve_documents` reads the catalog eagerly; the `sq repair` row red when the bypass ladder has no index-skipping rung (also reddens the workflow row).
    Loads table: 4 rows red (`--help`, `show`, `list`, `check` with overrides) when `validate_against_index` rebuilds the bundled workflow spec; the `check` with overrides row red when `Lazy` does not memoise (the catalog rebuilt per use); 7 rows red when the packaged file is parsed on every use; both `--version` rows red when `squads/__init__` imports the workflow package.
    Two squads: red when the creation render drops its `from_squad` argument (the existing engine-level test stays green, which is why the new one goes through `create`).
    
    ## Existing tests
    No assertion was weakened. One assertion changed because its subject's call shape changed: `test_role_source_resolver.py` now expects `resolve_role_for_item(item, squad_dir, catalog=catalog)`.
    Left red on purpose: `tests/unit/test_playbook_bundled_coverage_key_set_is_cached.py` pins 3+1 packaged reads for three `load_playbook` calls; the packaged file is parsed once per process now, so the count is 0 or 1. Superseded by the loads table; delete or rewrite on your call.
    Removed: `test_a_broken_leaf_verb_render_path_is_caught_once_the_harness_resets_ambient_state` (`tests/cli/test_leaf_verb_render_honours_overrides.py`): it disabled `_common.set_active_squad_dir`, which no longer exists. The first test there now records the `from_squad` each render receives.
    Retargeted, not rewritten: the lock-timeout CLI test patches `squads._services._service.IndexStore` (the store is built there now); the leaf-verb spy and the env-cache eviction tests drive `_env(squad_dir)`; `test_workflow_cross_check_once_per_invocation` spy accepts `sources`; `sabotaged_check` accepts `catalog`; conftest and the ambient-state guard now list no ambient values.
    Signature threading only: about 85 test files pass `catalog=catalog_of(...)` (new helper in `tests/_helpers.py`), `from_squad=`, `bundled=`, or build services through `make_service`.
    
    ## Reported, not changed
    - The index-check-skipped mode (and so `sq repair` after a refusal) pairs the merged workflow spec with the bundled playbook, ignoring a valid playbook override and without a coverage check against the merged spec. It looks accidental; kept as it was.
    - `sq role catalog` now builds the service before reading the catalog; with a broken roles override and a playbook override together the same message arrives as a `PlaybookConfigError` (as every other command already does).
    - docs/backends.md "Registering one" described the removed registration side effect; corrected.
    - Two content-equal substitutions in the fallback modes: they reuse the spec the root callback already resolved (`ctx.active_spec`) instead of loading it again, and a squad with no workflow override gets the bundled singleton where the old fallback built a second equal copy.
    - `sq workflow lint` still reads the override twice (collect-mode lint, then the transform check); not in the measured table.
    
    @tech-writer: no adopter-visible behaviour change; `sq check` on a large roster loads the role catalog once instead of once per role resolution (191 loads on a nine-role squad).
    @manager: ready for review. The full suite is yours to run.
    
    ## Verification
    All at `-n 4`, one run at a time, logs read; the full suite was not run.
    - tests/meta: 458 passed, 1 xfailed.
    - tests/unit: 3685 passed, 2 skipped, 1 failed (the superseded 3+1-reads test above).
    - tests/service: 5275 passed.
    - tests/cli: 3469 passed, 1 skipped. An earlier run failed 3 rows of `test_startup_work_per_command` (the spy on `_loader.load_workflow_spec` did not see the resolver's bound name); the resolver now calls through the module and those rows pass.
    - tests/integration: 1221 passed, 8 skipped.
    - tests/tui: 77 passed (one test built a service by hand and needed the new constructor).
    - `sq check`: clean.
- [2026-10-25T15:58:31Z] `manager` Catherine Manager:
  - Done: REV-1142 Approved; delivered in 12fd2afa, 6393caab, 88a9e14f.
<!-- sq:discussion:end -->
