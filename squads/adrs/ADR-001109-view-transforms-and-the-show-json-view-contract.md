---
id: ADR-1109
sequence_id: 1109
type: decision
title: View transforms and the show --json view contract
status: Accepted
author: architect
refs:
- REV-1099:addresses
- FEAT-1108
description: Spec-declared Python transforms feed a view's template and a views key
  in show --json; body returns the stored text
created_at: '2026-10-24T13:07:46Z'
updated_at: '2026-10-24T14:40:30Z'
---
<!-- sq:body -->
## Context

A view is a declared source plus a Jinja template, rendered wherever a `sq:view:<name>` tag sits in a body (ADR-880). `ItemsMixin.read_body` is the one body-read boundary and expands every tag, so `show --json` returns `body` with each view already rendered. REV-1099 F5 shows the cost: a milestone body read through `show --json` and written back with `body --force --file` stores the rendered roll-up as frozen prose next to the live tag, and `sq check` does not notice. JSON readers also have no data form of a view: the roll-up's Delivered/Outstanding/Settled partition exists only inside `templates/views/milestone_rollup.md.j2`.

The operator's rulings on F5 (op-pierre, 2026-10-24) fix the shape. A view may declare a Python transform. It is called with the resolved source and returns plain data, and that data feeds both the template and JSON. `show --json` returns the stored body with its tags as tags, plus a `views` key. User transforms are trusted, like a `conftest.py`. This record states those rulings as rules and settles what they leave open.

Grounding: `src/squads/_views.py` (`resolve_source`, `render_source_view`, `expand_view_tags`), `ViewSpec`/`ViewSource` and `_check_views` in `src/squads/_workflow/_models.py`, `[views.*]` in `src/squads/_specs/workflow.toml`, `_view_json_payload` in `src/squads/_cli/_workflow_cmd.py`, `build_item_json` in `src/squads/_cli/_common.py`, the raw-override pre-checks in `src/squads/_workflow/_loader.py`, `SquadPaths.abspath` in `src/squads/_paths.py`, `RequestContext.client_cwd` in `src/squads/_context.py`, and the Tier 3 clauses of `docs/stability.md`.

## Decision

### Declaration

- `ViewSpec` gains an optional `transform` table. It takes one of two forms:
  - `transform = { module = "<dotted.module>", function = "<name>" }`, bundled only: imported with `importlib.import_module`, like any import. The module must lie under `squads.`.
  - `transform = { path = "<relative/file.py>", function = "<name>" }`, for overrides: a file relative to `<squad-dir>/.overrides/` and confined to it.
- **Overrides cannot write `module`.** A pre-merge check on the raw override, of the same kind as `_retired_view_grammar_violations`, refuses any `views.<name>.transform` table the override writes that names `module`, and any such table that lacks either `path` or `function`. The refusal names `path` as the fix. A splat-ref that copies a bundled `transform` value is allowed, because it can only reach code squads ships.
- **Override precedence on a bundled view.** The leaf merge keeps the bundled `module` leaf when an override writes `path` + `function` onto a bundled view. After the merge the loader drops `module` from any transform that also carries `path`, so a `path` always comes from the override and replaces the bundled transform.
- **Load-time checks are shape only, with no filesystem access and no import.** They run in `_check_views`'s collect-all pass, so `sq workflow lint` lists them together. The checks: exactly one of `module`/`path`; `function` is an identifier that is not a keyword; `path` is relative, POSIX, ends in `.py` and has no `..` segment; `module` is a dotted identifier under `squads.`. Loading the spec on every command therefore costs no file stat and no import.
- **Filesystem and code checks run in `sq check` and `sq workflow lint`, and again at render.** The file must exist, be a regular file, and still lie inside `.overrides/` after its symlinks are resolved. The module must import, `function` must be a callable that is not a coroutine function, and its signature must be accepted (see Call). Both commands import override transform files, which runs their top-level code; this is documented together with the trust rule. Bundled transforms are covered by the test suite, not by `sq check`.

### Path resolution

- The base is `Service.paths.squad_dir / ".overrides"`. `paths` was resolved from `RequestContext.client_cwd` (what `-C` sets) at the CLI edge or in a daemon handler. Transform resolution never calls `paths.resolve()`, `process_dir()` or `Path.cwd()`, and it takes no directory argument of its own: the squad directory comes threaded in, already resolved. Under the daemon (ADR-1052) the server's cwd therefore never takes part.
- The confinement guard is the one `SquadPaths.abspath` already applies: `(base / rel).resolve()` must satisfy `is_relative_to(base.resolve())`. It is lifted into one shared helper in `_paths.py` that both callers use, so the check exists once.
- **Symlinks are followed, and only the target counts.** A symlink inside `.overrides/` that resolves inside `.overrides/` is accepted; one that resolves outside is refused with the resolved target named. A `.overrides` directory that is itself a symlink is accepted, because the base is compared after resolution.

### Loading

- An override file is loaded by reading its bytes, compiling them, and running them with `exec()` in a fresh module named from a hash of its resolved path. No bytecode is read or written under `.overrides/`. The module is placed in `sys.modules` only while that code runs, so that `dataclasses` and `typing` find it, and is removed afterwards. Nothing about a loaded transform outlives the request, which keeps two squads served by one daemon from sharing a cached `transforms.py` and keeps an edited file from going stale.
- A file is loaded once per request: a body placing two views from the same file executes it once. There is no cross-request cache.
- `sys.path` is never changed. A transform file imports the standard library, installed packages, and nothing else, so its helpers live in the same file.
- Bundled modules import normally and stay cached in `sys.modules`. They are code, not request data (the `_context.py` triage rule).

### Call

- The call is `fn(source, *, item, spec)`, run synchronously. `source` is the value `resolve_source` returns, in its native shape (`list[Item]`, `list[SubEntity]`, `RoleDef`, `PlaybookSource`, `Item`). `item` is the host and `spec` is the active `WorkflowSpec`.
- **sq passes only the keywords the function declares.** It reads `inspect.signature(fn)`. The first parameter must accept a positional argument. `item` and `spec` are passed when a parameter of that name exists, and both are passed when the function takes `**kwargs`. A function that requires any other parameter is refused, with the parameter named. A keyword sq adds later is therefore never a breaking change for an existing transform.
- **Read-only, enforced by copying.** `Item` and `SubEntity` are mutable pydantic models, and `WorkflowSpec`'s `frozen=True` blocks attribute assignment but not changes to its `dict` fields. Under a daemon the parsed spec stays warm across requests, so a mutation of any argument could leak into a later request. So `source`, `item` and `spec` are all passed as deep copies (`model_copy(deep=True)`, element by element for a list) made for each call. Copying the bundled spec costs about 0.4 ms. Nothing a transform returns or mutates reaches disk, because the read path has no write.

### Output

- A transform returns a JSON value whose top level is a `dict` or a `list`. Allowed inside it: `dict` with `str` keys, `list`, `str`, `int`, finite `float`, `bool` and `None`. Tuples, sets, pydantic models, datetimes, NaN and infinity are refused. The value is checked by a strict walk, never by `json.dumps(default=...)`, so the template and JSON receive exactly the same value.
- **Jinja gets the output alongside the source.** The template receives `data` (the transform output) in addition to `source`, `item`, `spec` and `squad_dir`. `data` is not defined for a view without a transform, so a template that reads it fails under `StrictUndefined`. Because `source` keeps its meaning, an adopter's existing template override of a view keeps working when that view gains a transform. A template for a transform-bearing view reads `data`, so its text matches the JSON.

### Errors

- **One error class, `ViewTransformError(SquadsError)`, covering every failure:** a file missing or escaping `.overrides/`, a failed import, a missing or uncallable function, a rejected signature, an exception raised inside the transform, a wrong top-level type, or a non-JSON value.
- Its message names the view, the host item, the declaration (`<path>:<function>` or `<module>:<function>`) and the cause. For an exception, the cause is its type, its message, and the last traceback frame inside the transform's own file (`file:line`). For a bad return, the cause is the JSON path of the first offending value (`$.delivered[3].when`). It reads as a clean `@handle_errors` exit 1, never a traceback.
- **The failure is loud on every surface that computes the view:** `sq show` (styled and `--raw`), `show --json`, and `sq workflow view`. This follows the precedent of a template render failure (`_render_resolved_source_or_raise`). `Exception` and `SystemExit` raised by a transform, at import or at call, become `ViewTransformError`; `sys.exit()` in user code is a failure, never an exit. Every other `BaseException` propagates: `KeyboardInterrupt` still interrupts, and `asyncio.CancelledError` still cancels a daemon request.
- An unresolvable tag (undeclared view, missing template, inapplicable source) stays literal and quiet, as today. The transform never runs for it.

### `show --json`

- `body` is the stored `sq:body` region text with its view tags as tags, read through a new service read of the stored region (`read_stored_body`). `read_body` keeps expanding tags and stays the boundary for every text surface: `sq show`, `--raw`, the TUI reader, the operator pane, and role/skill text show.
- A new `views` key, always present, maps view name to transform output: `{"milestone_rollup": {...}}`. It holds exactly the views whose tag is placed and enabled in the stored body, that pass `resolve_view_target` (the same gate text expansion uses, so text and JSON agree on which tags are live), and that declare a transform. A disabled tag is left out, as it is on text surfaces. A placed view without a transform is left out. `views` is `{}` when nothing qualifies. Sub-entity bodies never carry view tags, so sub-entities get no `views` key.
- The same rule applies to every item JSON payload that carries a `body`: `sq show <id> --json`, `sq <type> <n> show --json`, `sq skill <addr> show --json` (its builder documents itself as the same field), and the `self` kind of `sq workflow view --json`, which reuses `build_item_json`.
- `views` joins `ROW_ADDED_KEYS`, so an attribute may not be named `views`. A project that already declares one is refused at load, with the attribute named.

### `sq workflow view --json` and `sq workflow views --json`

- `sq workflow view <name> <id> --json` keeps emitting the resolved **source** in its kind's own shape, transform or not. That source is the transform's input, and this is the one surface where an author can see it. The output is on `show --json` under `views`. Text `sq workflow view` renders the template, which receives `data`.
- `sq workflow views --json` rows gain `transform`: `null`, or the declaration as merged (`{module, function}` or `{path, function}`). This is additive.

### `milestone_rollup`

- `[views.milestone_rollup]` declares `transform = { module = "squads._view_transforms", function = "milestone_rollup" }`. `squads._view_transforms` is a new private module that imports only `_models` and `_workflow`.
- It partitions the `targets` members on status roles alone, never on a status name. `delivered`: `spec.is_delivered(type, status)`. `settled`: `spec.role_for(status).settled` and not delivered (Cancelled, Superseded, and the like). `outstanding`: everything else.
- The output is `{"delivered": [row], "outstanding": [row], "settled": [row]}`. Each `row` is `{id, type, title, status, assignee}`, with `assignee` `null` when unset. Each list is sorted by type and then `sequence_id`, case-sensitively, the order the template uses today. Consumers that want more fields read `sq show <id> --json`.
- `templates/views/milestone_rollup.md.j2` is rewritten to read `data` and no longer partitions on its own.

### Schema

- No schema bump. `SCHEMA_VERSION` covers what is stored in item files and the index, and none of it changes: tags were already stored, transform output is never stored, and the declaration lives in spec TOML, which is package data or an override. An older `sq` meeting an override that declares `transform` refuses it through `ViewSpec`'s `extra="forbid"`, which is the ordinary result of a newer grammar.
- The change to what `show --json`'s `body` means for a tag-bearing body is a stated Tier 3 contract change. It goes in the CHANGELOG under Changed, with a migration note: read `views` for data and `--raw` for rendered text.

## Consequences

- F5 point 2 goes away on the read side: what `show --json` prints is what is stored. A full round-trip also needs the body write path to accept an unchanged, already-placed tag of a declared view instead of refusing it as a marker (F5 point 1). That is part of the F5 fix, which depends on this record.
- A JSON reader of a role or system skill gets the tag in `body`, not the rendered definition, since those views declare no transform. The rendered text remains on `show --raw` and text `show`.
- Reading a body with no transform view gets cheaper in `show --json`, since there is no expansion. A transform view costs one source resolution plus a deep copy per read.
- A buggy override transform fails every read of the items that place its view. `sq check` and `sq workflow lint` report file, import and signature defects before a read does. They cannot report a runtime exception that depends on the data.
- Under a daemon, a transform runs on the event-loop thread, so a slow transform delays other requests. Transforms are documented as pure computation over their arguments.
- The spec digest (ADR-970) covers the declaration, not the transform file's contents: editing a transform does not change the digest.
- An override cannot remove a bundled view's transform, because leaf merge has no delete. It can replace the transform with its own `path`, or override the template to ignore `data`.
- Tests that change: `test_show_json_body_field_carries_the_expanded_text_not_the_literal_tag` reverses; the skill `show --json` key-set and `body == read_body` assertions change; the `feature_show.json`/`task_show.json` goldens gain `views: {}`.
- `docs/stability.md` needs a refresh by the tech writer: the Tier 3 `show --json` key list (`views`, the meaning of `body`), the attribute-name rule's list of row-added keys, the `sq workflow views --json` row (`transform`), the derived-views paragraph (the `self` payload gains `views`), and the override layout (transform files under `.overrides/`, and the trust rule). `docs/overrides.md` and `docs/workflow.md` need the declaration grammar and a worked transform example, and `sq override scaffold workflow` should show one.

## Consumer inventory: `show --json` `body`

- `build_item_json` (`sq show --json`, `sq <type> <n> show --json`): reads `read_body` today. Needs the stored text plus `views`. This is the change itself.
- `sq workflow view --json`, `self` kind: reuses `build_item_json`. It inherits the new `body` and `views` and stays "host show --json plus `spec`".
- `sq skill <addr> show --json` (`_cli/_skill.py`): its own builder, reading `read_body`. Changes with the rule above. No known consumer needs rendered skill text in JSON.
- `sq role <slug> show --json`: no `body` key. Unaffected.
- `sq memory show --json`: `body` is the memory entry text, which carries no view tags. Unaffected.
- Sub-entity `body` (nested, and from a sub-entity's own `show --json`): the stored block prose, which can hold no view tags. Unaffected.
- VS Code client (`clients/vscode/src/sqAdapter.ts`): `getShowJson` reads only `discussion`, `subentities` and `type` (`SqShowJson`, `isSqShowJson`), and the dossier body comes from `sq show --raw` (`getRaw`). Needs nothing. It can later read `views` for structured roll-ups.
- TUI (`src/squads/_tui/_reader.py`): calls `svc.read_body` directly and never goes through JSON. Needs the rendered text and keeps it.
- Text surfaces (`_cli/_common.py` styled and raw show, `_cli/_operator.py`, role/skill text show): `read_body`. Unaffected.
- Tests: `tests/cli/test_view_tag_expansion_at_read_time_cli.py`, `tests/cli/test_skill_show_renders_a_system_definition_on_read.py`, `tests/cli/test_skill_item_surface.py`, and the `show` goldens under `tests/goldens/`.
- Adopters' scripts (`show --json | jq -r .body`, as in the REV-1099 report): they now get tags. That is the fix, and it is stated in the CHANGELOG.

## Options rejected

- A transform file found next to the template by name: the operator's later ruling moved the declaration into the spec, where lint can see it.
- `module` allowed in overrides: it would let an override name arbitrary importable code (`os:system`) without a file under `.overrides/`.
- Checking that the file and function exist at spec load: it would add a stat and an import to every command, and a filesystem fact is not a spec fact (the precedent is a missing template).
- Registering override modules in `sys.modules` for good: they would go stale under a daemon and collide across squads.
- Loading with `spec_from_file_location` + `exec_module`: the bytecode cache serves a stale file when it is edited within the same second.
- Passing the live objects with a read-only contract that nothing enforces: a mutation would leak across daemon requests.
- A read-only proxy over the spec: a wrapper for every nested container and method return value, against a 0.4 ms copy.
- Catching all of `BaseException`: it would swallow `KeyboardInterrupt` and a daemon's `CancelledError`.
- Transform output replacing `source` in Jinja: it would break every existing template override of a view that gains a transform.
- Degrading a transform error to a literal tag or a `null` entry: a quiet wrong answer, and inconsistent with how template failures behave.
- A `rendered_body` key next to `body`: it duplicates `--raw` and keeps the F5 round-trip trap one key away.
- Returning transform output from `sq workflow view --json`: it would hide the transform's input and change a frozen shape for no new capability.
- Listing a disabled or transform-less view in `views` as `null`: it is noise that a reader has to filter out, and text surfaces render nothing for it either.
- A schema bump: nothing stored changes.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T13:08:07Z] `architect` Robert Architect:
  - Drafted from the op-pierre rulings on REV-1099 F5; refs REV-1099 (addresses) and FEAT-1108. Open for operator ruling: skill show --json body also goes stored-text; workflow view --json keeps the source; transform errors are loud. @product-owner FEAT-1108 can cite this; docs/stability.md needs a tech-writer refresh once accepted.
- [2026-10-24T13:11:45Z] `op-pierre` Pierre Chat:
  - All five points accepted: sq skill show --json follows the same rule; sq workflow view --json keeps returning the source; a broken transform fails the read loudly; views becomes a reserved attribute name; the write-side acceptance of an unchanged placed tag belongs to the F5 fix.
- [2026-10-24T14:30:00Z] `architect` Robert Architect:
  - Amended 2026-10-24 after REV-1117 F1 and F4: spec is deep-copied per call like source and item (frozen=True does not protect its dicts), and a transform raising Exception or SystemExit, at import or call, becomes a ViewTransformError; every other BaseException propagates. Options rejected: a read-only spec proxy, catching all of BaseException.
- [2026-10-24T14:40:30Z] `architect` Robert Architect:
  - 2026-10-24: Loading bullet restated to the implemented rule (compile the bytes and `exec()` them, no bytecode under `.overrides/`, in `sys.modules` only while executing); `spec_from_file_location` + `exec_module` added to Options rejected (stale bytecode within one second). Per the accepted deviation on REV-1117.
<!-- sq:discussion:end -->
