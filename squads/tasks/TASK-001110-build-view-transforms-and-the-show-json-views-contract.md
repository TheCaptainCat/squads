---
id: TASK-1110
sequence_id: 1110
type: task
title: Build view transforms and the show --json views contract
status: InProgress
parent: FEAT-1108
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-1109:implements
description: Transform declaration, safe loading, views key and milestone roll-up
  data.
subentities:
- local_id: ST1
  title: Declare a view transform in the spec with shape-only load checks and override
    precedence
  status: Todo
  assignee: python-dev
  story: US1
- local_id: ST2
  title: Load, bind and call a transform, validate its JSON output, and feed it to
    the template as data
  status: Todo
  assignee: python-dev
  story: US1
- local_id: ST3
  title: Resolve override transforms from the threaded squad dir, confined to .overrides/
    after symlinks
  status: Todo
  assignee: python-dev
  story: US2
- local_id: ST4
  title: Report unresolvable override transforms in sq check and sq workflow lint
  status: Todo
  assignee: python-dev
  story: US1
- local_id: ST5
  title: Return the stored body and a views key from every item show --json payload
  status: Todo
  assignee: python-dev
  story: US3
- local_id: ST6
  title: Give milestone_rollup a bundled transform and render its template from data
  status: Todo
  assignee: python-dev
  story: US4
- local_id: ST7
  title: Show a commented transform in the workflow override scaffold
  status: Todo
  assignee: python-dev
  story: US5
- local_id: ST8
  title: Document the transform key, signature, path rule and trust model
  status: Todo
  assignee: tech-writer
  story: US5
- local_id: ST9
  title: Write the 0.17.0 CHANGELOG entries for view transforms
  status: Todo
  assignee: tech-writer
  story: US3
created_at: '2026-10-24T13:16:43Z'
updated_at: '2026-10-24T13:28:01Z'
---
<!-- sq:body -->
## Goal

Build FEAT-1108 exactly as ADR-1109 decides it: a view may declare a Python transform whose return value feeds both its Jinja template (as `data`) and a new `views` key in `show --json`, and `show --json` `body` returns the stored text with its view tags as tags. The bundled `milestone_rollup` view gets the first transform. ADR-1109 is the authority on every rule below; where this body and the ADR differ, the ADR wins and this body is corrected.

## Approach

### Declaration and load-time checks (`src/squads/_workflow/_models.py`, `src/squads/_workflow/_loader.py`)

- New frozen, `extra="forbid"` model `ViewTransform` with `module: str | None`, `path: str | None`, `function: str`. `ViewSpec` gains `transform: ViewTransform | None = None`.
- Shape checks only, no filesystem access and no import, appended to `_check_views`'s collect-all `errors` list so `sq workflow lint` reports them with every other view finding: exactly one of `module`/`path`; `function` is an identifier and not a keyword (`str.isidentifier` plus `keyword.iskeyword`); `path` is relative, POSIX (no backslash, no drive), ends in `.py`, has no `..` segment; `module` is a dotted identifier starting `squads.`.
- Pre-merge raw-override check next to `_retired_view_grammar_violations`, run at both call sites (`load_workflow_spec` around line 300 and `lint_workflow_spec` phase 2 around line 1434): a `views.<name>.transform` **table** the override writes that names `module`, or lacks `path` or `function`, is a `MergeViolation` whose hint names `path` as the fix. A splat-ref string value is not a table and passes, so copying a bundled transform stays allowed.
- Post-merge step, one helper called on both load paths, for the override path only: drop `module` from any merged transform that also carries `path` (the leaf merge in `src/squads/_specmerge.py` keeps the bundled `module` leaf). The bundled document loads without this step, so a bundled view declaring both is still refused.
- `views` joins `ROW_ADDED_KEYS` in `src/squads/_models/_attributes.py`; `_reserved_item_keys` picks it up, so a declared attribute named `views` is refused at load with the name in the message.

### Transform engine (new `src/squads/_transform.py`)

- `ViewTransformError(SquadsError)`: the one error class. Message: view name, host item id, declaration (`<path>:<function>` or `<module>:<function>`), cause.
- Resolution of a `path` transform takes the already-resolved squad directory as an argument and builds `squad_dir / ".overrides"`. It never calls `_paths.resolve()`, `process_dir()` or `Path.cwd()` and takes no other directory input. Confinement goes through one helper lifted out of `SquadPaths.abspath` into `src/squads/_paths.py` (resolve `base / rel`, require `is_relative_to(base.resolve())`, return the resolved target so the caller can name it); `abspath` keeps its `InvalidIdError` and its unresolved return value, built on the helper. Then: regular file, still inside after symlink resolution.
- Loading: `importlib.util.spec_from_file_location` under a module name derived from a hash of the resolved path, inserted in `sys.modules` only around `exec_module` and removed in a `finally`. `sys.path` is never touched. A per-call `TransformLoader` instance (not a module global, not a `Service` attribute) memoises loaded files, so one body placing two views from one file executes it once; the instance is created by each top-level read (`expand_view_tags` call, `views` computation for one JSON payload) and dropped after. Bundled `module` transforms load with `importlib.import_module` and stay cached as ordinary code.
- Call: read `inspect.signature`; the first parameter must accept a positional; pass `item`/`spec` when a parameter of that name exists, both when `**kwargs` exists; refuse any other required parameter by name; refuse a coroutine function and a non-callable; a callable whose signature cannot be read is refused cleanly. `source` and `item` are deep copies per call (`model_copy(deep=True)`, element by element for a list); `spec` passed as is. Catch `Exception` only; report type, message and the last traceback frame inside the transform's own file as `file:line`.
- Output: a strict recursive walk (never `json.dumps(default=...)`) over the return value: top level `dict` or `list`; inside, `dict` with `str` keys, `list`, `str`, `int`, finite `float`, `bool`, `None`. Anything else is refused with the JSON path of the first offender (`$.delivered[3].when`).
- Keep `_transform.py` free of module-level mutable state (`tests/meta/test_no_unallowlisted_module_level_mutable_state.py`); record each new import edge in `tests/meta/test_package_import_edges_match_the_recorded_table.py` as the guard reports it.

### Rendering (`src/squads/_views.py`, `src/squads/_services/_views.py`)

- `render_source_view` takes an optional transform output and passes `data=` to the template only when the view declares a transform, so a template reading `data` on a transform-less view fails under `StrictUndefined`. `source`, `item`, `spec`, `squad_dir` are unchanged.
- `expand_view_tags` runs the transform after `resolve_source` for each resolvable tag that declares one. `ViewTransformError` propagates (loud on `sq show`, `--raw`, `show --json`, text `sq workflow view`); it is not rewrapped by `_render_resolved_source_or_raise`. Unresolvable tags stay literal and never run a transform.
- `ViewsMixin.render_view` (text `sq workflow view`) runs the transform; `resolve_view_source` and `sq workflow view --json` keep returning the source and never run it.

### `show --json` (`src/squads/_services/_items.py`, `src/squads/_cli/_common.py`, `src/squads/_cli/_skill.py`, `src/squads/_cli/_workflow_cmd.py`)

- New `ItemsMixin.read_stored_body(item_id)`: the `sq:body` region, stripped as `read_body` strips it, tags as tags. `read_body` is unchanged and stays the boundary for every text surface.
- New service read `view_data(item_id) -> dict[str, JsonValue]`: for each enabled tag in the stored body that passes `resolve_view_target` and declares a transform, its output under the view name; disabled, transform-less and unresolvable tags are absent; `{}` when nothing qualifies, with no index load when the body has no tag.
- `build_item_json` uses `read_stored_body` for `body` and adds `views` always. The skill `show --json` builder in `_cli/_skill.py` does the same (`body` stored, `views` present). The `self` kind of `sq workflow view --json` inherits both through `build_item_json`. Sub-entity payloads get no `views`.
- `sq workflow views --json` rows (`_view_catalog`) gain `transform`: `null` or the merged declaration (`{module, function}` or `{path, function}`). The text table is unchanged.
- Consumers: the TUI reader (`src/squads/_tui/_reader.py`) calls `read_body` directly and keeps rendered text; the VS Code client (`clients/vscode/src/sqAdapter.ts`) reads only `discussion`/`subentities`/`type` from `show --json` and the body from `--raw`. Confirm both by reading the code; no change is expected.

### `sq check` and `sq workflow lint`

- One function in `_transform.py` checks every `path` transform of the active spec without calling it: file exists, regular, confined after symlinks, imports, function present, callable, not a coroutine, signature accepted. It imports the file and so runs its top-level code. Called from a squad-level rule in `src/squads/_services/_validators.py` and from `workflow_lint` in `src/squads/_cli/_workflow_cmd.py` after `lint_workflow_spec` returns clean (`_workflow` sits below `_transform`, so `lint_workflow_spec` itself does not import it). Bundled transforms are covered by tests, not checked here.

### `milestone_rollup` (new `src/squads/_view_transforms.py`, `src/squads/_specs/workflow.toml`, `src/squads/_rendering/templates/views/milestone_rollup.md.j2`)

- `[views.milestone_rollup]` declares `transform = { module = "squads._view_transforms", function = "milestone_rollup" }`. The module imports only `_models` and `_workflow`.
- Partition on status roles only: `delivered` = `spec.is_delivered(type, status)`; `settled` = `spec.role_for(status).settled` and not delivered; `outstanding` = the rest. Rows `{id, type, title, status, assignee}` (`assignee` `null` when unset), each list sorted by `(type, sequence_id)` case-sensitively.
- The template reads `data` and does no partitioning or sorting of its own; its rendered text stays byte-identical to today's for the same corpus. Update the `[views.milestone_rollup]` comment in `workflow.toml` that says the template partitions.

### Override scaffold

- `src/squads/_overrides/_service.py` workflow scaffold: extend the commented `[views.related_incidents]` example with a commented `transform = { path = "transforms/related_incidents.py", function = "related_incidents" }` line and a two-line note that the file is trusted code run with the user's permissions.

## Tests

Service-level plus a CLI smoke per behaviour, table-driven over input shapes rather than one test per branch. Falsify each new test: break the code it covers, watch it go red, restore. Run `tests/meta`, `tests/integration` and `tests/cli` whatever else is selected, because a bundled spec, a template and CLI payloads change.

### Path resolution (one table: where the command runs × where the file is)

Each row writes a project with `.overrides/transforms/t.py` returning a marker value and asserts that exact value under `views.<name>` (and in the rendered text), plus a decoy whose own `.overrides/transforms/t.py` returns a different marker:

- run from the project root;
- run from a subdirectory of the project (`monkeypatch.chdir(project / "src" / "deep")`);
- `sq -C <project>` from an unrelated directory that holds the decoy squad and decoy file; the decoy value never appears;
- daemon-like: `open_service(client_cwd=project)` while the process cwd is the decoy squad; then a second `open_service(client_cwd=decoy)` in the same process returns the decoy's own value, and `sys.modules` holds no transform module after either call;
- the same file edited between two calls in one process: the second call returns the new value (no cross-call staleness);
- `path` with `..` (refused at load), absolute `path` (refused at load), backslash path (refused at load), not `.py` (refused at load);
- a symlink inside `.overrides/` whose target is outside: refused at render, at `sq check` and at `sq workflow lint`, with the resolved target named; the outside file is never executed (it writes a sentinel file at import; assert the sentinel is absent);
- a symlink inside `.overrides/` whose target stays inside: accepted and runs;
- `.overrides` itself a symlink to a directory elsewhere: accepted (base compared after resolution);
- missing file, a directory at the path: `ViewTransformError` naming the view and the path.

Skip the symlink rows where the platform cannot create symlinks, with a reason; do not let a failed `os.symlink` pass silently.

### Signature variants (one table)

Accepted, and asserting which keywords arrived: `def f(source)`, `def f(source, *, item)`, `def f(source, *, spec)`, `def f(source, *, item, spec)`, `def f(source, **kwargs)` (both arrive), `def f(source, extra=1)` (not passed), a callable instance. Refused, with the parameter or reason named: `def f()`, `def f(*, source)`, `def f(source, extra)`, `def f(source, *, other)`, `async def f(source)`, a module attribute that is not callable, a missing function name, a builtin whose signature cannot be read.

### Bad return values (one table)

Each refused with the JSON path of the first offender in the message, never a traceback: top-level `str`, `int`, `None`, `tuple`; `{1: "x"}` (non-str key); `{"a": float("nan")}`; `{"a": float("inf")}`; `{"a": {1, 2}}` (set); `{"a": object()}`; a pydantic model; a `datetime`; a tuple nested in a list (`$.rows[2]`); a deep path such as `$.delivered[3].when`. Accepted: `{}`, `[]`, nested dict/list mixes, `bool`, finite `float`.

### Runtime behaviour

- A transform that raises: `ViewTransformError` with view, host id, declaration, exception type and message, and `file:line` inside the transform file; exit 1, no `Traceback`, on `sq show`, `sq show --raw`, `show --json` and text `sq workflow view`. `sq workflow view --json` still returns the source.
- `KeyboardInterrupt` raised inside a transform propagates.
- A transform that mutates `source` and `item`: the next read is unaffected and the item file is byte-identical.
- One body placing two views from the same file: the file executes once (a module-level counter written to a temp file).
- A spec with a `path` transform whose file raises at import: `sq list` and `sq show` of an item without the tag succeed (spec load does not import); `sq check` and `sq workflow lint` report it.

### Declaration grammar (one table over raw override shapes)

`module` written by an override (refused, hint names `path`); a table without `function`; a table without `path`; both `module` and `path` in the bundled document (refused); `function = "class"`; `function = "1x"`; `module = "os"` in a bundled spec (refused, not under `squads.`); a splat-ref copying `views.milestone_rollup.transform` (allowed); an override writing `path` + `function` onto `milestone_rollup` (merged transform has no `module`, the override file runs). An attribute declared `views` is refused naming it.

### `show --json` contract

- `body` equals the stored region with raw tags for: a milestone (tag present), a role and a system skill (tag present, `views` is `{}` since those views declare no transform), a plain feature (no tag, `views` is `{}`).
- `views.milestone_rollup` present for an enabled tag; absent for a disabled tag; absent for an unresolvable tag (undeclared view, missing template); absent for a transform-less view.
- Read half of the round trip: the milestone `body` carries the tag and none of the rendered roll-up (no `## Delivered` heading). The write half, a body write that accepts the unchanged tag, is TASK-1103 ST2, and FEAT-1108 acceptance criterion 4 is verified there.
- `show`, `show --full` and `show --raw` still print the rendered roll-up; the TUI reader still renders it.
- `sq workflow view <name> <id> --json` for the `self` kind gains `views`; `sq workflow views --json` rows carry `transform`.

### `milestone_rollup`

Table over member sets: none; only delivered; only outstanding; a settled-not-delivered member (Cancelled, Superseded); a custom lifecycle from an override whose delivered status is not named `Done`; a mixed-case custom type name (case-sensitive sort); an unassigned member (`assignee: null`). For each: `views.milestone_rollup` counts and member ids equal the three text sections, and the rendered text equals today's output for the same corpus (`tests/service/test_milestone_rollup_section_order.py` stays green unchanged).

### Tests that flip, per ADR-1109

- `tests/cli/test_view_tag_expansion_at_read_time_cli.py::test_show_json_body_field_carries_the_expanded_text_not_the_literal_tag` reverses: the body carries the literal tag.
- `tests/cli/test_skill_show_renders_a_system_definition_on_read.py`: the key set gains `views`; `payload["body"] == read_body(...)` becomes the stored-body comparison.
- `tests/cli/test_skill_item_surface.py` line 52: compare to `read_stored_body`.

### Goldens and generated output

Regenerate and review the diff of: `tests/goldens/feature_show.json` and `tests/goldens/task_show.json` (gain `views: {}`), `tests/goldens/workflow_views.json` (gains `transform`), any other show golden the floor turns up, and the template manifest (`scripts/gen_template_manifest.py`) for the rewritten `milestone_rollup.md.j2`. `TASK-1103` also regenerates goldens and the manifest: sequence the two, do not run them in parallel.

## CHANGELOG substance (0.17.0)

The developer reports and the tech writer writes the entries (ST9).

- Added: a view may declare `transform = { module, function }` (bundled) or `transform = { path, function }` (override, relative to `.overrides/` and confined to it). The function is called as `fn(source, *, item, spec)` with only the keywords it declares, and returns JSON data that feeds the template as `data`.
- Added: `show --json` carries a `views` key: the data of each placed, enabled view that declares a transform. A milestone's `views.milestone_rollup` holds its `delivered` / `outstanding` / `settled` partition.
- Changed: `show --json` `body` (item `show`, `<type> <n> show`, `sq skill <addr> show`, and the `self` kind of `sq workflow view --json`) is now the stored text, with each `sq:view:<name>` tag left as a tag instead of rendered. Migration: read `views` for a view's data, and `sq show --raw` for the rendered text. A script that did `show --json | jq -r .body` now gets the tag.
- Changed: `views` is a reserved attribute name; a spec declaring an attribute named `views` is refused at load.
- Added: `sq workflow views --json` rows carry `transform`.
- Added: `sq check` and `sq workflow lint` report an override transform that cannot be found, escapes `.overrides/`, fails to import, or has a refused signature. Both import the file, which runs its top-level code.
- Override transforms are trusted code that runs with the user's permissions, like a `conftest.py`; there is no approval step.
- No schema change and no migration step.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1110 add-subtask "<title>"`; track with `sq task 1110 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare a view transform in the spec with shape-only load checks and override precedence

<!-- sq:subtask:ST1:body -->
Add `ViewTransform` (`module` | `path`, `function`) and `ViewSpec.transform` in `src/squads/_workflow/_models.py`, with the shape-only checks in `_check_views`'s collect-all pass: exactly one of `module`/`path`, `function` an identifier that is not a keyword, `path` relative POSIX `.py` with no `..`, `module` dotted under `squads.`. In `src/squads/_workflow/_loader.py`, add the raw pre-merge refusal of an override `transform` table that names `module` or lacks `path`/`function` (hint names `path`), at both the load and lint call sites, and one post-merge helper that drops `module` when `path` is present on the override path only. Add `views` to `ROW_ADDED_KEYS`. No filesystem access and no import at load. Tests: the declaration-grammar table in the task, including the splat-ref copy that stays allowed and the reserved `views` attribute.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Load, bind and call a transform, validate its JSON output, and feed it to the template as data

<!-- sq:subtask:ST2:body -->
New `src/squads/_transform.py`: `ViewTransformError`, bundled load via `importlib.import_module`, signature binding from `inspect.signature` (first parameter positional; `item`/`spec` passed when named or under `**kwargs`; any other required parameter, a coroutine function, a non-callable or an unreadable signature refused by name), per-call deep copies of `source` and `item`, `Exception`-only catch reporting type, message and the last `file:line` inside the transform, and the strict JSON walk that names the first offending JSON path. Thread the output into `render_source_view` as `data` only when the view declares a transform, run it in `expand_view_tags` and `ViewsMixin.render_view`, and leave `sq workflow view --json` on the source. No module-level mutable state; record the new import edges. Tests: the signature and bad-return tables, the raising, interrupting and mutating transforms, and the loud failure on every text surface.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Resolve override transforms from the threaded squad dir, confined to .overrides/ after symlinks

<!-- sq:subtask:ST3:body -->
Resolve a `path` transform against `squad_dir / ".overrides"` from the squad directory the service already holds (`Service.paths.squad_dir`, resolved from `RequestContext.client_cwd`), never `_paths.resolve()`, `process_dir()` or `Path.cwd()`. Lift the confinement check out of `SquadPaths.abspath` into one helper in `src/squads/_paths.py` that returns the resolved target; `abspath` keeps its error and return value on top of it. Follow symlinks and judge the target only. Load with `spec_from_file_location` under a hash-of-resolved-path module name, in `sys.modules` only during `exec_module`, `sys.path` untouched, memoised by a per-call loader instance. Tests: the path-resolution table in the task (root, subdirectory, `sq -C` with a decoy file in the process cwd, the daemon-like `open_service(client_cwd=...)` with a different process cwd and a second squad in the same process, an edited file between calls, `..`, absolute, backslash, outward and inward symlinks, a symlinked `.overrides`, missing file).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Report unresolvable override transforms in sq check and sq workflow lint

<!-- sq:subtask:ST4:body -->
One function in `src/squads/_transform.py` checks every `path` transform of the active spec without calling it: file exists and is regular, stays inside `.overrides/` after symlinks, imports, names a callable non-coroutine function, and has an accepted signature. Wire it into a squad-level rule in `src/squads/_services/_validators.py` (`sq check`) and into `workflow_lint` in `src/squads/_cli/_workflow_cmd.py` after `lint_workflow_spec` is clean, since `_workflow` sits below `_transform`. Bundled transforms are left to the test suite. Tests: each defect reported by both commands with the view and path named, and a transform file that raises at import leaves `sq list` and a tag-free `sq show` working (spec load imports nothing).
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Return the stored body and a views key from every item show --json payload

<!-- sq:subtask:ST5:body -->
Add `ItemsMixin.read_stored_body` (the stored `sq:body` region, tags as tags) and a `view_data` service read (enabled, resolvable, transform-declaring tags only; `{}` otherwise; no index load without a tag) in `src/squads/_services/_items.py`. `build_item_json` in `src/squads/_cli/_common.py` and the skill `show --json` builder in `src/squads/_cli/_skill.py` emit the stored `body` and an always-present `views`; the `self` kind of `sq workflow view --json` inherits both. `_view_catalog` rows in `src/squads/_cli/_workflow_cmd.py` gain `transform`. `read_body` and every text surface are unchanged; confirm from the code that the TUI reader and the VS Code adapter need no change. Flip the three tests ADR-1109 names, regenerate `feature_show.json`, `task_show.json` and `workflow_views.json`, and cover the `views` membership table and the read half of the milestone round trip.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Give milestone_rollup a bundled transform and render its template from data

<!-- sq:subtask:ST6:body -->
New `src/squads/_view_transforms.py` (imports only `_models` and `_workflow`) with `milestone_rollup(source, *, spec)`: partition on `spec.is_delivered` and `spec.role_for(status).settled`, never a status name, into `delivered` / `outstanding` / `settled` lists of `{id, type, title, status, assignee}` rows sorted by `(type, sequence_id)` case-sensitively. Declare it on `[views.milestone_rollup]` in `src/squads/_specs/workflow.toml` and update that view's comment. Rewrite `templates/views/milestone_rollup.md.j2` to read `data` with no partitioning of its own, rendering text byte-identical to today's. Regenerate the template manifest. Tests: the member-set table in the task, asserting JSON counts and ids equal the text sections, with `test_milestone_rollup_section_order.py` green unchanged.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Show a commented transform in the workflow override scaffold

<!-- sq:subtask:ST7:body -->
Extend the commented `[views.related_incidents]` example in the workflow scaffold text in `src/squads/_overrides/_service.py` with a commented `transform = { path = "transforms/related_incidents.py", function = "related_incidents" }` line, the call signature in one line, and a note that the file is trusted code that runs with the user's permissions. Grep `tests/` for the scaffold text and update any test or golden that pins it; scaffold into a scratch squad and confirm the uncommented example loads and lints clean once the file exists.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Document the transform key, signature, path rule and trust model

<!-- sq:subtask:ST8:body -->
Document view transforms for adopters, from ADR-1109 and the developer handback. `docs/workflow.md` and `docs/overrides.md`: the `transform` key in both forms, the `fn(source, *, item, spec)` signature and keyword omission, the allowed return values, `data` in the template next to `source`, the path rule (relative to `.overrides/`, confined, symlink targets judged), the trust model (trusted like a `conftest.py`, runs with the user's permissions, no approval step; `sq check` and `sq workflow lint` import it), that a broken transform fails every read of an item placing its view, and a worked example. `docs/stability.md`: the `show --json` key list (`views`, the meaning of `body`), the reserved row-added keys, the `sq workflow views --json` `transform` field, the derived-views paragraph (`self` gains `views`), and the override layout.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Write the 0.17.0 CHANGELOG entries for view transforms

<!-- sq:subtask:ST9:body -->
Write the 0.17.0 CHANGELOG entries for view transforms from the task's CHANGELOG substance and the developer's handback, describing what an adopter now sees and does. The `show --json` `body` change goes under Changed with its migration note: read `views` for data and `sq show --raw` for rendered text. Mapped to US3 for the board; it covers US1 to US4.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T13:28:01Z] `manager` Catherine Manager:
  - Dispatched to @python-dev for ST1-ST7 (ST8 docs and ST9 CHANGELOG go to the tech-writer after). Operator go: 2026-10-24.
<!-- sq:discussion:end -->
