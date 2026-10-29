---
id: REV-1235
sequence_id: 1235
type: review
title: Review of the DTO refactor's delivered tasks
status: ChangesRequested
author: reviewer
refs:
- FEAT-1226
- TASK-1227
- TASK-1228
description: Batch review of FEAT-1226's delivered tasks, one commit at a time, against
  ADR-1224, ADR-1225 and ADR-1172
subentities:
- local_id: F1
  title: 'Display and rendered_body become reserved names: an override declaring such
    an attribute stops loading'
  status: Verified
  severity: high
- local_id: F2
  title: The import guards miss relative imports, importlib and a renderer reaching
    the spec or service through _common
  status: Verified
  severity: medium
- local_id: F3
  title: 'No test sees the moved documents'' JSON key order or show''s new keys: both
    mutations pass the suite'
  status: Verified
  severity: medium
- local_id: F4
  title: 'The JSON-native guard reads declared fields only: computed fields and allowed
    extras escape it'
  status: Verified
  severity: low
- local_id: F5
  title: Item requests require the type, against ADR-1225's id-only item routes
  status: Verified
  severity: low
- local_id: F6
  title: CLAUDE.md's architecture section misses the _api package, the new modules
    and the CLI import rule
  status: Verified
  severity: low
- local_id: F7
  title: _main.py gains a _services import for tree's sort while on the shrinking
    pending list
  status: Verified
  severity: low
- local_id: F8
  title: display.target_date is keyed on the literal milestone type in a served contract
  status: Verified
  severity: low
- local_id: F9
  title: Show prints no panel before a missing-file error; unknown option now exits
    2; exit-4 path unexercised
  status: Noted
  severity: info
- local_id: F10
  title: Transitional verb set and second gate copy are not on TASK-1232's deletion
    list
  status: Deferred
  severity: info
  deferred_to: TASK-1232
- local_id: F11
  title: JSON mode prints no response warnings, so the language notice goes once the
    root callback stops printing it
  status: Deferred
  severity: info
  deferred_to: TASK-1232
- local_id: F12
  title: The labelled-attribute case asserts a substring of --raw, runs on an override,
    and leaves the panel line unasserted
  status: Verified
  severity: low
- local_id: F13
  title: Stale sub-entity read verbs under a renamed kind crash with KeyError instead
    of refusing
  status: Verified
  severity: medium
- local_id: F14
  title: display.priority names one field and keeps a fallback list and mine dropped
  status: Verified
  severity: low
- local_id: F15
  title: display.pronouns on tree nodes is asserted by no case
  status: Verified
  severity: low
- local_id: F16
  title: CHECK and VOCABULARY modes put fallback policy and a squadless build outside
    the composition root
  status: Verified
  severity: medium
- local_id: F17
  title: Key order of 14 moved --json row shapes is asserted by no case
  status: Verified
  severity: medium
- local_id: F18
  title: workflow view --json fails on a broken view template though it prints only
    the source
  status: Open
  severity: low
- local_id: F19
  title: workflow view --json sources are private serializer copies that no longer
    match their commands
  status: Verified
  severity: low
- local_id: F20
  title: workflow lint --json prints its refusal on stdout
  status: Verified
  severity: low
- local_id: F21
  title: memory forget --json returns only the slug while board clear returns the
    notice
  status: Verified
  severity: info
- local_id: F22
  title: 'Roster rows never see [display] pronouns = false: ignoring the switch passes
    the suite'
  status: Verified
  severity: low
- local_id: F23
  title: The role view disable --json case writes a workflow override, against ADR-1172
    scope and the F12 ruling
  status: Verified
  severity: low
- local_id: F24
  title: Write responses wrap {entry, ...} where item status prints the row; column
    keys mix row keys and dotted paths
  status: Verified
  severity: low
- local_id: F25
  title: 'Catalog on a malformed .squads.toml and role show --json on a missing file
    now exit 1: changelog lines'
  status: Open
  severity: info
- local_id: F26
  title: Roster comment bridge, a stale registrar comment and two duplicates are on
    no deletion list
  status: Deferred
  severity: info
  deferred_to: TASK-1232
- local_id: F27
  title: 'TASK-1227 tests: an unmarked milestone case asserting three forms, and an
    extended types case'
  status: Open
  severity: low
- local_id: F28
  title: 'TASK-1228 tests: pronouns and lead-badge checks appended to tree cases;
    mine --json asserts one row'
  status: Open
  severity: low
- local_id: F29
  title: 'TASK-1230 tests: pronouns switch appended to dev list --json, ANY in role
    add, seven tests left unmarked'
  status: Open
  severity: low
- local_id: F30
  title: 'TASK-1231 tests: an override-backed view case against F12/F23, and shape
    or prefix asserts instead of whole output'
  status: Open
  severity: medium
- local_id: F31
  title: 'TASK-1229 tests: an unmarked comment refusal, and create and edit --json
    checked against the CLI''s own output'
  status: Open
  severity: low
created_at: '2026-10-28T23:26:20Z'
updated_at: '2026-10-29T04:27:33Z'
---
<!-- sq:body -->
Batch review of FEAT-1226's delivered tasks, one commit at a time, against ADR-1224, ADR-1225 (section 9) and ADR-1172.

## Scope

- TASK-1227, commit 3b3cfbd9: the `_api` package (envelope, operation table, `Api`, wire form, item DTOs), `LocalApi` and the binding table, the four guards, `sq <type> <n> show`, `sq list` and `sq <type> <n> status` (with `--json`) on operations, display content for items, and the removal of the seeded-request code.
- Later tasks of FEAT-1226 join this review as they land.

## Method

- Parity: the parent commit and this commit, each extracted to its own tree, run side by side on one scratch squad that carries an override (a custom `incident` type with an alias, a badge field on its own collection and two attributes), sub-entities with bodies and comments, a milestone with a target date and a view tag, a deferred finding, and 8 item addresses. 138 command lines per tree: every show flag combination, piped, `FORCE_COLOR`, `NO_COLOR`, `-C` into a subdirectory and outside the squad, wrong-type, unknown, malformed and foreign-prefix addresses, `--help` on an unknown item, the `list` filters and sorts, and status moves with a valid actor, an `@`-prefixed mixed-case one, the system slug and an unknown one, compared byte for byte. Then a pseudo-terminal run of `show --full --comments` and `list --all`, the four prompt sites answered "n" under a pseudo-terminal, a duplicate id with an invalid working language, and five broken-squad states (bad override, corrupt index, missing item file, schema behind, corrupt frontmatter).
- JSON: every changed document checked key by key (old keys kept in order, values equal, keys only appended), and every produced show and list document round-tripped through its DTO and `Response[T]` with an order-sensitive comparison.
- Structure: pyright probes of mismatched bindings; the two import guards, the JSON-native guard and the surface suite falsified on a third copy of the tree.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1235 add-finding "…" --severity medium`; track with `sq review 1235 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Display and rendered_body become reserved names: an override declaring such an attribute stops loading

<!-- sq:finding:F1:body -->
`ROW_ADDED_KEYS` gains `display` and `rendered_body` (`_models/_attributes.py`). That tuple feeds `_reserved_item_keys` in `_workflow/_validity.py`, which refuses an attribute or a field code of that name at spec load. So a squad whose override declares an attribute named `display` (or `rendered_body`), valid under the released 0.17, stops loading: every command answers the "workflow override could not be loaded" error until the adopter renames the attribute and rewrites every item that stores it. No migration step, changelog line or `sq migrate chlog` manual step tells them.

An attribute named `display` that the override does not declare (a hand-written or imported frontmatter key) is not refused, but `to_row()` now drops it from every `--json` row, and the row's `display` key changes type from the adopter's string to the display object.

Reproduced on a scratch squad, parent commit against this one:

```
# .overrides/workflow.toml
[items.incident.attributes]
customer = { kind = "str" }
display = { kind = "str" }

sq incident 14 update --set display=wallboard
sq list --type incident --json
```

- parent: `updated INC-14`, then the row carries `"display": "wallboard"`; `workflow lint` reports the spec OK.
- this commit: `error: this squad's workflow override could not be loaded ... 'incident': attribute 'display' is a reserved key — pick another name`, exit 1, on every command including `list`, `check` and the update itself.

The design question behind it is wider than these two names: rows carry stored attributes flat at the top level (ADR-1224 point 2), so every display key later tasks append to a row (labels, headings, `columns`-style keys on row DTOs) is another name taken from adopters. Tier 3's additive rule does not make such an addition additive for a squad that already uses the name. Options for the architect: keep the reservation and ship the rename as a migration manual step with a refusal that names the remedy; or nest the stored attributes under one row key, so display keys never compete with adopter names (a Tier 3 change, so a schema change). @architect for the decision; the fix lands with whichever.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-28T23:31:56Z] `architect` Robert Architect:
  - Ruled in ADR-1224 point 2 (comments ad65a70 and the F8 one after it): `display` is the one name item rows reserve, and every display value goes inside it, so `rendered_body` becomes `display.body` and stops being reserved. Nesting the stored attributes was rejected, because it would change a frozen Tier 3 shape for every adopter in order to protect the ones who use this one name. A collision is handled as it already is for `views`: a declared attribute is refused at load, naming the key, and an undeclared stored key stays out of the row. The remedy reaches the adopter through the changelog, the 0.18 migration's manual step and the Tier 3 list of reserved names. @python-dev is implementing it on TASK-1227 (my comment there).
- [2026-10-28T23:42:36Z] `python-dev` Elias Python:
  - Fixed (uncommitted, round 2 of TASK-1227): only `display` is reserved; `rendered_body` left ROW_ADDED_KEYS and moved to `display.body` on show. The load refusal now names the remedy: "'task': attribute 'display' is a reserved key every --json item row adds — rename the attribute in the workflow override and in the items that store it" (a badge field gets "... — rename the field in the workflow override"). No 0.18 migration runner exists yet, so the chlog manual step waits for the task that adds the 0.18 schema change.
- [2026-10-28T23:51:57Z] `reviewer` Paul Reviewer:
  - Verified on 5b0a5936 (scratch squad, override on a custom type). An attribute named display is refused at load with: attribute display is a reserved key every --json item row adds — rename the attribute in the workflow override and in the items that store it. A badge field coded display gets: field code display shadows a reserved key every --json item row adds — rename the field in the workflow override. An attribute named rendered_body now loads, stores and shows (it left the reserved set). An undeclared display key in a file stays out of the row (show --json keeps the display object). The changelog entry, the Tier 3 reserved-name line and the 0.18 manual step are on TASK-1234, as ADR-1224 point 2 requires.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — The import guards miss relative imports, importlib and a renderer reaching the spec or service through _common

<!-- sq:finding:F2:body -->
The two structural guards ADR-1224 points 2 and 5 rely on ("this is what makes 'the renderer never calls the service' structural, not a convention") match import statements by absolute module name only. Each of these passes both guards on this commit (all four applied at once on a copy of the tree, `import squads._cli` still succeeds, the two guard modules report 4 passed):

1. `_cli/_calls.py` (not pending): `from .._services._service import Service` at module level. A relative import has `node.module == "_services._service"`, which `_imports_services` does not see.
2. `_cli/_calls.py`: `importlib.import_module("squads._services._service")`.
3. `_cli/_render/_items.py`: `from squads._cli._common import get_active_spec, get_service`. The renderer guard forbids `_workflow`, `_paths` and the config model, but `_common` re-exports the spec accessor and the service builder, so a renderer reads the vocabulary and builds a service while both guards stay green. This is the likely real-world slip: the old renderers lived in `_common`, and `_common.e`, `status_text(status, spec)` and friends are the helpers a renderer author reaches for.
4. `_cli/_render/_items.py`: `from ... import _workflow` (relative, `node.module is None`).

Repro: apply any of the four on a copy, then `uv run --all-extras pytest -n0 tests/meta/test_renderers_read_neither_the_vocabulary_nor_the_configuration.py tests/meta/test_the_cli_imports_the_service_layer_only_in_the_local_api_factory.py` stays green.

Suggested fix: resolve relative imports against the module's package before matching (or ban relative imports with ruff's TID252, which closes 1 and 4 project-wide); add `squads._cli._common` (and any `_cli` module on the pending list) to the renderer guard's forbidden set; flag `importlib.import_module`/`__import__` calls with a literal argument naming a forbidden module. The remote-client import guard of ADR-1225 section 5 will catch the runtime half later, but not a renderer reading the spec through `_common` in local mode.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-28T23:42:39Z] `python-dev` Elias Python:
  - Fixed: both guards read imports through tests/_import_scan.py, which resolves relative imports against the module package and counts importlib.import_module/__import__ with a string literal; the renderer guard also forbids squads._services, squads._cli._common and every pending module. All four reproduced bypasses go red. Still unseen: a computed module name, attribute access through an already-imported package object, sys.modules lookups, and transitive imports through an allowed module.
- [2026-10-28T23:51:59Z] `reviewer` Paul Reviewer:
  - Verified on 5b0a5936: each of my four bypasses (relative _services import in _calls.py, importlib literal, renderer importing _common, renderer relative _workflow import) turns a guard red, and so does from squads import _services in a renderer. Three paths still pass both guards, in the classes the dev listed as unseen: a renderer importing squads._cli._calls (then calling local_api(), or reaching _calls.common), importlib.import_module with a relative literal and a package argument, and a computed module name. The first is a one-line fix if wanted: add squads._cli._calls to the renderer guard FORBIDDEN tuple, since a renderer has no use for the call module. Not reopened: what the finding reproduced is closed.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — No test sees the moved documents' JSON key order or show's new keys: both mutations pass the suite

<!-- sq:finding:F3:body -->
The surface suite cannot see two properties this task claims: the JSON key order of the moved documents, and the new keys of `show --json`.

- `test_show_json_prints_the_item_as_one_object`, the `covers("<type> show", "--json")` case, asserts 8 picked keys and the sub-entity ids, not the whole document (ADR-1172 rule 5). The task body says the `show` expectations "gain the display keys" and that review checks each edited expectation; there was none to edit, so `display`, `rendered_body` and every sub-entity's `display` on `show --json` are asserted nowhere.
- Every JSON assertion compares parsed objects with `==`, which ignores key order. ADR-1224 point 2 declares DTO fields "in today's emitted order", and `_TrailingKeys` exists only to keep it, but nothing fails when it breaks.

Falsified on a copy of the tree: `_TrailingKeys._ordered` changed to return the keys reversed, and `ItemShow.rendered_body` excluded from the dump. `sq task 10 show --json` then opens with `"discussion"` and has no `rendered_body`; `pytest -n 4 tests/cli tests/check tests/meta` gives 1559 passed and the same 7 environment-only failures as the unmutated copy (the manifest tests that need git history). Both mutations survive.

This matters most for the next task: Tier 3 freezes the emitted order of `search`, `tree` and `graph`, and TASK-1228 will copy this pattern and these assertions. Suggested fix: make the `show --json` case assert the whole document, and compare JSON as text or as `list(doc.items())` (order-sensitive) in the shared helper the whole-document cases use, so an order change fails.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-28T23:42:41Z] `python-dev` Elias Python:
  - Fixed: the show, list and status --json cases compare the whole document as text (json.dumps of the ordered expectation), so key order is held; show now asserts every key including display and the sub-entity displays. Your two mutations (reversed order, trailing keys dropped) each turn all three red.
- [2026-10-28T23:52:02Z] `reviewer` Paul Reviewer:
  - Verified on 5b0a5936: the reversed-key-order mutation turns the show, status and list --json cases red (3 failed); dropping display.body, and separately display.attributes, from the show dump turns the show case red. Show now asserts the whole document as text.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — The JSON-native guard reads declared fields only: computed fields and allowed extras escape it

<!-- sq:finding:F4:body -->
`test_every_dto_field_is_json_native` walks `cls.model_fields`, which holds declared fields only. Two ways a non-JSON-native value reaches a DTO's dump past it:

- a `@computed_field` (pydantic leaves computed fields out of `model_fields`);
- the extras of a model with `extra="allow"` (`ItemRow` and its subclass `ItemShow`), which are validated against nothing.

Repro on a copy of the tree, a probe DTO added to `_api/_dto/_display.py` with `extra="allow"`, a `name: str` field and a computed `when -> datetime`: the guard passes (2 passed); `Probe(name="x", where=Path("/tmp"))` dumps `{"name": "x", "where": "/tmp", "when": "2026-01-01T00:00:00"}`, and `Probe.model_validate_json(p.model_dump_json()) == p` is `False`, the round-trip property ADR-1224 point 2 states.

No current DTO does either (the item rows' extras come from `to_row()` in JSON mode, and a round trip of every show and list document this review produced compares equal), so this is a gap for later tasks, not a live defect. Suggested fix: have the guard also walk `model_computed_fields` (their return annotation), and assert that `extra="allow"` appears only on the classes it lists. A model serializer (`_TrailingKeys`) can still emit anything; that one is small enough to leave to review.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-28T23:42:44Z] `python-dev` Elias Python:
  - Fixed: the guard also checks model_computed_fields return types, and refuses extra="allow" outside ItemRow/ItemShow (their extras are to_row() in JSON mode). A static rule over a round-trip check because it catches the class at declaration, with no instance to build. Probe with a datetime computed field, and probe with extra="allow", each red.
- [2026-10-28T23:52:04Z] `reviewer` Paul Reviewer:
  - Verified on 5b0a5936: a computed datetime field, extra=allow on a new DTO, extra=allow through ConfigDict on a Display subclass, and a tuple field each turn the guard red.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Item requests require the type, against ADR-1225's id-only item routes

<!-- sq:finding:F5:body -->
`ItemAddress.type` is required, so `ItemShowRequest` and `ItemStatusRequest` cannot be sent without the item's type. ADR-1225 section 1 addresses items "by id only ... The route does not depend on the type", and its route table maps both `sq <type> <n> show` and `sq show <id>` to `GET /v1/items/{id}`. Over HTTP the type travels as a required query parameter, so a web client that holds only an id gets a validation refusal for `GET /v1/items/TASK-12`.

The dev flagged this (deviation 3) and expects TASK-1228 to relax it when `sq show <id>` moves. The request shape is the contract that task copies, so the cheaper moment is now: make `type` optional, and have `addressed_item` check the type only when one is given (that is the only thing ADR-1224 point 1 asks the operation to check: "has the type the command named"). If it stays for TASK-1228, record it on that task so it is not lost.

The `address` field itself is fine against the ADRs: neither fixes the request fields, and it is what keeps today's "5 is FEAT-5 (feature), not a task" text now that the CLI turns the number into an id before the call.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-28T23:32:25Z] `tech-lead` Olivia Lead:
  - Fixed in TASK-1227 now, before TASK-1228 copies the request shape: type becomes optional and the operation checks it only when given. Not carried to TASK-1228.
- [2026-10-28T23:42:46Z] `python-dev` Elias Python:
  - Fixed: ItemAddress.type is optional; without it addressed_item resolves the id alone (resolve_any_id, now raising ItemNotFoundError for an unknown number). The CLI still sends the type. No surface command sends an id alone yet, so that branch is first exercised when sq show <id> moves (TASK-1228).
- [2026-10-28T23:52:06Z] `reviewer` Paul Reviewer:
  - Verified on 5b0a5936 through LocalApi with an id-only ItemShowRequest: TASK-10 and bare 10 resolve to TASK-10, INC-14 to the custom type, FEAT-10 is refused as FEAT-10 is TASK-10 (task), TASK-999 raises ItemNotFoundError. The CLI still sends the type, and its 138-line parity capture is unchanged.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — CLAUDE.md's architecture section misses the _api package, the new modules and the CLI import rule

<!-- sq:finding:F6:body -->
CLAUDE.md's architecture section still describes the layering before this commit:

- "the 13 `Service` bases, in MRO order" — `Service` now has 14, with `ItemOpsMixin` first;
- no entry for `squads/_api/` (envelope, operation table, `Api`, wire form, DTOs) or its place in the layering line (`_cli → _services → …`, `_models shared`), although `_cli → _api` and `_services → _api` are new rows in the import-edge table;
- no entry for `_cli/_render/`, `_cli/_calls.py` (the one `_services` import of the CLI), `_services/_local_api.py`, `_bindings.py`, `_item_ops.py` and `_item_dto.py`, or the rule that the CLI imports `_services` only in the `LocalApi` factory.

The dev reported the 13-bases line as stale in the handback. CLAUDE.md here is the contributor guide later agents load first, and the next four tasks fork from this commit, so the layering rule they must follow should be written where they read it. Suggested fix: one paragraph for `_api/`, one line each for the new `_services` and `_cli` modules, and the guard named beside them.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-28T23:46:44Z] `tech-writer` Theo Writer:
  - Fixed in CLAUDE.md (outside the managed region): layering block gains _api and the _cli to _services rule with the pending modules; new _api/ bullet; _services bullet names _item_ops first (14 bases) plus _bindings, _local_api, _item_dto; _cli bullet describes _calls.py and _render/ with their guards. Checked against the code: the draft's exit 2 for vocabulary refusals is false (parse_status raises SquadsError, exit 1), so it was dropped; Api.call is async; the pending list is named, not enumerated.
- [2026-10-29T00:01:42Z] `reviewer` Paul Reviewer:
  - Verified against the code at d6db6779: the Service base list (14, ItemOpsMixin first, same MRO order as _service.py), the _api package contents and its imports, json_field, _bindings, _local_api, _item_dto, _calls and _render all match. One nit for the next edit: the renderer guard now also forbids squads._cli._calls (added in d6db6779), which the _render line does not name.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — _main.py gains a _services import for tree's sort while on the shrinking pending list

<!-- sq:finding:F7:body -->
`_cli/_main.py` gains a new import of the service layer, `from squads._services._item_dto import badge_rank`, used by `tree`'s `--sort`. `_main.py` is on the guard's pending list, so the guard allows it, but the pending list is meant to shrink as commands move; here a moved helper went into `_services` and a not-yet-moved command reached back into it, so the pending module's service dependency grew. The same commit moved `_badge_rank` out of `_main.py` for `list`, which is the right home for the operation, and left `tree` depending on it across the boundary.

Small, and `tree` moves in TASK-1228, which removes the import. Suggested fix: either leave a local copy in `_main.py` until `tree` moves, or note the import in TASK-1228's scope so its removal is checked there rather than relying on the pending list to flag it (it will not: `_main.py` keeps other `_services` imports).
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-28T23:42:48Z] `python-dev` Elias Python:
  - Fixed: badge_rank moved to squads._badges (type, field code, value, spec); list sorts through it in _services and tree imports it from _badges, so _main.py gains no _services import.
- [2026-10-28T23:52:09Z] `reviewer` Paul Reviewer:
  - Verified on 5b0a5936: badge_rank lives in squads._badges; _main.py has no new _services import; list and tree --sort outputs are byte-identical to the parent commit.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — display.target_date is keyed on the literal milestone type in a served contract

<!-- sq:finding:F8:body -->
`ItemShowDisplay.target_date` is a field of the display contract that only one item type can fill: `show_display` sets it when `item.type == "milestone"`, a literal type name in service code. The literal is carried over from the old `print_item` (marked "a one-off" there too), but it now becomes a key of a DTO that is served over HTTP and documented under `/v1`: an adopter who renames or re-prefixes the milestone type, or declares a date attribute on their own type, gets no `target_date` and no other way to see a dated attribute in `display`.

The project's direction is that only the roster types are reserved and every work-item type is fully overridable. A generic shape costs little now and nothing later: for example `display.attributes`, each declared attribute with a value, as `{key, label, value}` in declared order, which the milestone's `target_date` falls out of. The spec declares no attribute label today, so this needs a small spec decision first. @architect, since the display shape is provisional until the web front consumes it, deciding before TASK-1228 copies it is cheaper than a schema bump later.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-28T23:31:57Z] `architect` Robert Architect:
  - @python-dev Decided in ADR-1224 point 5 (amended 2026-10-29). In TASK-1227's round:
  - `AttributeSpec` gains `label: str | None = None`. The bundled `[items.milestone.attributes]` becomes `target_date = { kind = "date", label = "target date" }`. `sq workflow types --json` adds `label` to each attribute (`null` when absent). Merge and override handling are those of any other attribute key.
  - `ItemShowDisplay.target_date` is replaced by `attributes: list[AttributeDisplay]`, with `AttributeDisplay{key, label, value}` in `_api/_dto/_display.py`. It holds one entry per attribute the item's type declares with a `label` and the item stores, in declared order. `value` is display text: a date or str as stored, a list joined with ", ", a bool as "yes"/"no". `show_display` loses the `item.type == "milestone"` literal.
  - The renderers print `[bold]{label}:[/bold] {value}` (and `- **{label}:** {value}` in markdown) where target date prints today, so milestone output stays byte-identical. Tests: the `show --json` expectation for a milestone, one case for an adopter type that declares a labelled attribute, and the workflow types catalog expectation. Falsify the labelled-attribute case once.
- [2026-10-28T23:42:51Z] `python-dev` Elias Python:
  - Fixed per the architect: display.target_date and the milestone literal are gone; show carries display.attributes ({key, label, value} per declared attribute with a label and a value, declared order); AttributeSpec gains optional label; the bundled milestone declares target_date with label "target date"; workflow types --json carries label (null when absent). Milestone show output (panel, raw, full, comments, styled) is byte-identical to the baseline.
- [2026-10-28T23:52:23Z] `reviewer` Paul Reviewer:
  - Reopened on 5b0a5936. The milestone literal is gone, milestone output is byte-identical to the parent commit (panel, raw, full, comments, styled), and `display.attributes` holds `{"key": "target_date", "label": "target date", "value": "2026-12-01"}`. Two parts of the architect's ruling (ADR-1224 point 5, comment 4620bae) are not met:
    
    1. **`value` is not display text.** The ruling says "`value` as display text: a date or str as stored, a list joined with ", ", a bool as "yes"/"no"". `AttributeDisplay.value` is `JsonValue` and carries the raw stored value. The renderer joins lists itself (`_text`) and prints a bool with `str()`. Repro on a scratch squad whose override declares `paged = { kind = "bool", label = "Paged" }` and `systems = { kind = "list", label = "Systems" }` on a custom type, after `sq incident 14 update --set paged=false`:
       - `show` prints `Paged: False`, and `--raw` prints `- **Paged:** False`; the ruling says `no`.
       - `show --json` gives `{"key": "paged", "label": "Paged", "value": false}` and `{"key": "systems", ..., "value": ["api", "db"]}`, so a web client has to format them itself, which is what point 5 moves into the operation.
       Fix: make `value: str`, format it in `show_display` (date or str as stored, list joined with ", ", bool as yes/no), and drop `_text` from the renderer.
    2. **The three tests the ruling asks for are missing:** the milestone `show --json` expectation, one case for a type that declares a labelled attribute, and the `workflow types --json` catalog expectation. Falsified on a copy of the tree:
       - deleting `"label": a.label` from `_type_catalog`: `tests/cli tests/check tests/meta` gives 1562 passed, plus the same 7 failures the unmutated copy has (manifest tests that need git history);
       - removing `label = "target date"` from the bundled milestone, which drops the `target date:` line from every milestone `show`: no surface case fails. Only the manifest-hash guards notice, because the bundled file changed.
       One more note: the `show --json` cases that exist assert `"attributes": []` on a task, which cannot tell a broken projection from an empty one.
       The suite's scope is the bundled spec (ADR-1172), so the labelled-attribute case has to be the bundled milestone's `target_date`, with its human line and its `display.attributes` entry. The catalog case is `sq workflow types --json` asserted whole, or at least the milestone row.
- [2026-10-28T23:57:49Z] `python-dev` Elias Python:
  - Fixed (uncommitted, TASK-1227 round 3): `AttributeDisplay.value` is now `str`, built in the operation by `attribute_text` (date or string as stored, list joined with ", ", bool as yes/no); the renderer prints it verbatim. Tests: milestone `show --json` asserted whole as ordered text, with its `display.attributes` entry; a labelled bool and list attribute (override on task) asserted in `--raw` and `display.attributes`; `workflow types --json` asserts the milestone row attributes with `label`. Falsified: catalog label dropped, bundled milestone label dropped, raw value instead of text — each red. Also `squads._cli._calls` joins the renderer guard's forbidden list (falsified).
- [2026-10-29T00:01:45Z] `reviewer` Paul Reviewer:
  - Verified on d6db6779: AttributeDisplay.value is a string built by attribute_text in the operation, and the renderer prints it as given. A bool shows yes/no and a list is joined. The three cases exist and each goes red on its mutation: bool via str(), list via str(), catalog label dropped, milestone label dropped. The renderer guard now forbids _cli._calls. A gap remains in the new tests themselves: see F12.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Show prints no panel before a missing-file error; unknown option now exits 2; exit-4 path unexercised

<!-- sq:finding:F9:body -->
Two behaviour changes outside the dev's parity proof, both consequences of ADR-1224's "one call, then render", recorded so they are not mistaken for regressions later:

- `sq task 10 show` on a squad whose indexed item file is missing: the parent printed the metadata panel on stdout, then `error: TASK-10's file is missing from its indexed location ...` and exit 1. This commit prints only the error line, exit 1 (the DTO is built before anything renders). `--json` and `--raw` are unchanged (error only in both).
- `sq task 999 show --bogus` now exits 2 with Click's "No such option" usage error instead of exit 1 with "no item with number 999". Same principle as the dev's deviation 2: parsing refusals come before squad data (ADR-1224 point 1).

Also: none of `show`, `list` or `status` can produce an omission, so the `omitted` line and exit 4 path of `calls.finish` is not exercised by this task; the acceptance line for it is vacuous here and the first real check is `inbox` in TASK-1228.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-28T23:29:01Z] `reviewer` Paul Reviewer:
  - Noted: nothing to fix. Both changes follow ADR-1224 point 1 (parse refusals first, output only after the call); recorded so the writer can mention the missing-file case if it is judged adopter-visible, and so TASK-1228 knows the exit-4 path is first exercised there.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Transitional verb set and second gate copy are not on TASK-1232's deletion list

<!-- sq:finding:F10:body -->
Two transitional mechanisms are not named in the task that removes them:

- `_VERBS_ON_OPERATIONS` in `_cli/_items.py` and the `_resolve_in_store` branch of the item group callback. Every later task appends verbs to the set; once all item verbs are on operations the store branch is dead. ADR-1224 point 1 wants group callbacks that only parse, so the set and branch have to go.
- A second copy of the schema gate in `_api/_api.py` (`Ground`, `Grant`) and `_services/_local_api.py` (`check_grant` with the two gate messages), beside `_cli/_common.py`'s `Ground`, `GateGrant` and `apply_gate`; and `_api.Mode`, a four-member copy of `_services._service.Mode` converted by value. The texts match today (verified on a squad at schema 0.16: identical refusal from both trees, from the root gate).

TASK-1232's body names the CLI-side gates (`require_current_schema`, `apply_gate`, `Ground`/`past_the_gate`) but not `_VERBS_ON_OPERATIONS`. The duplication is acceptable as a bridge; suggested disposition: add the set and the store branch to TASK-1232's deletion list, and close this as Noted.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-28T23:32:28Z] `tech-lead` Olivia Lead:
  - Deferred to TASK-1232 ST4: its deletion list now names _VERBS_ON_OPERATIONS, the _resolve_in_store branch, and the bridge gate copy (_api Ground/Grant/Mode and check_grant against the CLI Ground/GateGrant/apply_gate), keeping one.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — JSON mode prints no response warnings, so the language notice goes once the root callback stops printing it

<!-- sq:finding:F11:body -->
In `--json` mode the moved commands print no response warnings (`calls.print_warnings` runs in human mode only). Today the working-language notice still reaches stderr in `--json` mode, because the root callback prints it for every command. Once TASK-1232 removes that callback-side notice, `sq list --json` and `sq <type> <n> show --json` on a squad with an unrecognised `working_language` will stop warning on stderr, a local-mode change no surface case pins.

Observed on a scratch squad with `working_language = "klingon!!"`: parent and this commit both print the warning line on stderr before the JSON document of `show --json` and `list --json`.

ADR-1224 point 3 says "human mode renders data and prints warnings on stderr" and is silent on `--json`. Nothing to fix in this commit; recorded so TASK-1232 decides it on purpose: print response warnings on stderr in `--json` mode too (stdout stays one document), or accept the change and have the writer note it.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-28T23:32:30Z] `tech-lead` Olivia Lead:
  - Deferred to TASK-1232 ST5. Decided: in --json mode the CLI prints response warnings on stderr, one line each, as omitted already goes to stderr, so stdout stays one document. One surface case pins it (show --json with an unrecognised working_language); TASK-1232 now expects 9 new cases.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — The labelled-attribute case asserts a substring of --raw, runs on an override, and leaves the panel line unasserted

<!-- sq:finding:F12:body -->
`test_show_prints_labelled_attributes_as_text` (added in d6db6779) breaks ADR-1172 rule 5 and leaves the human panel line unasserted.

- It asserts a substring of the `--raw` output (`"- **Paged:** no\n- **Systems:** api, db\n" in raw`). Rule 5 asks for the whole output, so a wrong line before or after the attribute lines, or a duplicated one, passes.
- Nothing asserts the panel line `[bold]{label}:[/bold] {value}`. Falsified on a copy of the tree by changing that line to print `a.value.upper()`: `tests/cli/test_item_verbs.py` and `tests/cli/test_workflow.py` give 120 passed. The milestone's `target date:` line in the human `show` has no case either.
- The case also writes an override that declares labelled attributes on `task`. ADR-1172's scope section keeps the surface suite on the bundled spec. The architect's F8 ruling asked for "a type that declares a labelled attribute", and a bool or list label exists only through an override, so this conflicts with the ADR and needs a decision rather than a silent exception. @architect: either allow override-backed cases for spec grammar the bundled spec cannot express, or move the bool and list formatting proof elsewhere.

The other mutations are caught: a bool rendered with `str()`, a list rendered with `str()`, the catalog's `label` dropped, and the milestone label dropped are each red.

Suggested fix: assert the whole `--raw` output and the whole human `show` output in this case (or in the milestone case, which needs no override for its panel line).
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-29T00:02:38Z] `architect` Robert Architect:
  - @python-dev Ruling: drop the override case and make no exception. ADR-1172 keeps the surface suite on the bundled spec, and it already names where override-backed cases go: a later second squad build that declares against the same keys. A labelled bool or list attribute is custom vocabulary, so its case belongs there, and ADR-1172 is not amended.
  - Instead, in this round, run the milestone case on the bundled spec and assert the whole output (rule 5) of both the human `show` and `--raw`, so that the `target date:` panel line and the markdown line are both held. Falsify it once by changing the panel line, as the reviewer did.
  - Until the override-backed run exists, nothing at the surface tests the bool and list display text. That is accepted, and it becomes one of that run's first cases. Do not add a unit test to make up for it.
- [2026-10-29T00:04:56Z] `python-dev` Elias Python:
  - Fixed per the ruling (uncommitted, tests/cli/test_item_verbs.py only): the override-backed bool/list case is gone; the milestone case on the bundled spec now asserts the whole --json document, the whole human show output (panel with "target date: 2026-12-01") and the whole --raw output. Falsified by changing the attribute panel line in the renderer: red; restored: green. Bool and list display text stays unproven at the surface until the override-backed squad build exists, as ruled.
- [2026-10-29T00:06:57Z] `reviewer` Paul Reviewer:
  - Verified on 98b13ffe. The override case is gone, and the milestone case asserts the whole show --json, human show and --raw output on the bundled spec. Mutations, all red: panel value with x appended, the panel separator changed, the raw attribute line changed. The upper-case mutation passes only because 2026-12-01 has no letters, so it changes no byte; the value mutation covers that path.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Stale sub-entity read verbs under a renamed kind crash with KeyError instead of refusing

<!-- sq:finding:F13:body -->
Under a renamed sub-entity kind, the two sub-entity reads this task moved crash with a Python traceback instead of the refusal the parent commit printed. The dev's handback says a stale verb under a renamed kind keeps its refusal; that holds for the verbs not yet moved (`update`, `add-<kind>`), not for the plural listing and `<kind> <k> show`.

Repro on a scratch squad (bundled spec, task 9 with two subtasks), override:

```
[subentity_kinds.step]
lifecycle = "subentity"
completion = "Done"
plural = "steps"
local_prefix = "SP"
placeholder = "_Describe this step._"
maps_parent_story = true

[items.task]
subentity_kind = "step"
```

| command | e0b36809 | 42ac2937 |
|---|---|---|
| `sq task 9 subtasks` (also `--json`) | `error: TASK-9 is a task, which does not host subtasks (tasks host steps)`, exit 1 | Rich traceback, `KeyError: 'type'`, exit 1 |
| `sq task 9 subtask 1 show` | same refusal | same traceback |
| `sq task 9 subtask 1 update --status Done`, `sq task 9 add-subtask x` | refusal | refusal (unchanged) |
| `sq task 9 steps`, `sq task 9 step 1 show` | table / panel | identical |

Cause: the item group callback parses only for `_VERBS_ON_OPERATIONS` and `_subentity_verbs(item_type)`, which names the live kind's verbs (`steps`, `step`). A stale `subtasks` takes the `_resolve_in_store` branch, which puts no `type`/`address` on `ctx.obj`, then `list_sub` and `s_show` call `_address(ctx)` (`_cli/_items.py:96`) and raise `KeyError`. The kind group's own branch skips the store for `show`, so the stale `subtask N show` reaches the same lookup.

Suggested fix: have the callback parse for every sub-entity read verb (live and stale), so the operation's `_check_type` gives the refusal, or have `_address` fall back to the store-resolved id. The case needs an override, so per ADR-1172 its surface case belongs to the override-backed squad build; the fix should not wait for it.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-10-29T01:13:48Z] `python-dev` Elias Python:
  - Fixed in b55fdf1f (TASK-1228 round 2): `_address` in `_cli/_items.py` sends the id alone when the group resolved it against the store, and type and address only when it parsed them, so no verb is special-cased; the operation then reaches `_check_type` with the stale kind. Checked on a scratch squad with your override (task kind renamed to `step`): `subtasks`, `subtasks --json`, `subtask 1 show`, `subtask 1 show --json`, `subtask 1 update`, `add-subtask`, `subtask 1 body` all print `error: TASK-7 is a task, which does not host subtasks (tasks host steps)`, exit 1; `steps` and `step 1 show` unchanged. No surface case: it needs an override, which ADR-1172 keeps out of the bundled-spec suite (F12 ruling). Seen in passing, not in scope: `subtask 1 comment` under the renamed kind still succeeds (a comment-verb path, TASK-1229).
- [2026-10-29T04:26:59Z] `reviewer` Paul Reviewer:
  - - Verified on 79eac7ad with the original override (task kind renamed to `step`). `subtasks`, `subtasks --json`, `subtask 1 show`, `subtask 1 show --json`, `subtask ST1 show`, `subtask 99 show`, `subtask 1 update`, `add-subtask` and `subtask 1 body` all refuse with "TASK-10 is a task, which does not host subtasks (tasks host steps)", exit 1. At a8081afe, five of these crash with the KeyError traceback. `steps` and `step ST1 show` are unchanged. Other shapes held: `task 9 subtasks` and `task 9 steps` on a feature number refuse with "9 is FEAT-9 (feature), not a task", and an unknown number refuses as before. The stale `subtask 1 comment` still succeeds, as the dev noted (TASK-1229). There is no surface case, per the F12 ruling.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — display.priority names one field and keeps a fallback list and mine dropped

<!-- sq:finding:F14:body -->
Tree and graph nodes gain `display.priority`, a display key named after one field code. `_item_read_dto.priority_badge` renders it through `resolve_collection(type, "priority")`, which falls back to the same-named collection when the type no longer declares the field. `list` (since TASK-1227) and now `mine` render the declared field's badge only, and show the raw code otherwise. So one stored value renders two ways in one squad.

Repro (deviation 4 of the handback), scratch squad on the bundled spec, then an override with `[items.task] fields = []`. TASK-9 still stores `priority: high`:

- `sq tree`: `TASK-9 🟠 high · Parse the tokeniser queries (Draft)` (same as the parent commit).
- `sq mine architect`: Priority cell `🟠 high` on e0b36809, `high` on 42ac2937.
- `sq list --type task`: `🟠 high` before TASK-1227 (3b3cfbd9^), `high` since. That change was not recorded in that task's parity proof or in the changelog.

Two points:

1. **The display contract names one field.** `display.badges` already carries every declared badge field generically, with its rendered badge. `display.priority` duplicates `display.badges.priority` for a declared field. It differs only in the undeclared case, where it applies the same-name fallback. A web client now has two places to read the priority from, and they disagree in exactly that case. This is the same class as F8 (a literal type in a served display key).
2. **No single rule.** Either the declared-field rule (raw code once the type stops declaring the field, as in `list` and `mine`) or the fallback (as in `tree` and `graph`) is defensible. Having both is not.

Suggested: one rule for all four commands. The simplest is the declared-field rule. Under it the tree and graph line reads the lead badge from `display.badges`, `display.priority` goes before it is frozen, and `_PRIORITY_FIELD` goes with it. Whichever rule is kept, the human-output change (list and mine, or tree and graph) gets a changelog line. @architect for the display shape (whether a tree or graph line may name a lead badge field, and how). The fix lands on this task.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-10-29T01:06:02Z] `architect` Robert Architect:
  - @python-dev Ruling (ADR-1224 point 5, amended 2026-10-29). Use the declared-field rule for all four commands. No display key is named after a field code. Steps for TASK-1228's F13/F15 round:
  - Remove `display.priority` from the tree and graph node DTOs, and remove `priority_badge` and `_PRIORITY_FIELD` from `_item_read_dto.py`. Build node `display.badges` exactly as `list` does (declared fields, declared order, no `resolve_collection` same-name fallback).
  - The tree and graph renderers print the first entry of `display.badges` (its `badge`) where the priority goes today. On the bundled spec this is `priority` for every type, `bug` included, so the output does not change. `list` and `mine` keep reading their Priority column from `display.badges.priority`, with the raw code when the entry is missing.
  - Tests: update the tree and graph `--json` expectations (the `display` key is removed, not added, so call it out in the handback). Falsify once by rendering the last entry instead of the first. Add no override-backed case (F12 ruling).
  - Changelog, for the writer (TASK-1234): on a type whose override drops the priority field, `list` and `mine` show the stored code unbadged and `tree` and `graph` show no badge.
- [2026-10-29T01:14:00Z] `python-dev` Elias Python:
  - Fixed in b55fdf1f per the ruling: `display.priority` is removed from tree and graph node DTOs, and `priority_badge` and `_PRIORITY_FIELD` are removed from `_item_read_dto.py`. Node `display.badges` holds the declared fields in declared order, as for `list`. The tree and graph lines lead with the first entry (`lead_badge` in `_render/_style.py`); `list` and `mine` read the Priority column through `display.badges`. Removed key, provisional display: `display.priority` on tree and graph nodes; the tree and graph `--json` expectations drop it. Bundled-spec before/after (tree, graph incl. dot/mermaid, list, mine; plain and styled, 28 records): byte-identical. Falsified by rendering the last entry: the existing `tree --status Verified` case now sets the bug severity first and goes red. The changelog line is the writer's (TASK-1234).
- [2026-10-29T04:27:01Z] `reviewer` Paul Reviewer:
  - - Verified on 79eac7ad with the override `[items.task] fields = []`. TASK-10 stores `high`. `tree` shows no badge. The Priority cells of `list` and `mine` are empty, matching the reconciled ruling (151f11e). `tree --json` keeps the raw `priority` and an empty `display.badges`, and has no `display.priority`. On the bundled spec, `tree` and `graph` (with a fixes edge to a bug) lead with the priority badge. A renamed field code (`prio`) gets the badge in tree and show and an empty Priority cell in list, which is the declared-field rule. Mutation (lead_badge takes the last entry): `test_status_keeps_one_status_even_when_it_is_closed` goes red, 1 failed.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — display.pronouns on tree nodes is asserted by no case

<!-- sq:finding:F15:body -->
`display.pronouns` on tree nodes is asserted by no case, and neither is the `[display] pronouns = false` switch that empties it. The terminal UI is to read it instead of its two roster calls (task body, ST4). ST4 says the display content is "held by the guard and the existing human-output cases", but the human tree does not print pronouns.

Falsified on a copy of 42ac2937: `tree_node(...)` built with `pronouns=None` always, then `pytest -n 2` over the 8 edited test modules, `test_skill.py`, `test_operator.py` and `tests/meta`. The result is 999 passed and the same 7 failures the unmutated copy has (the manifest tests that need git history). The same run with the inbox `regions` emptied also survives. That gap is older than this commit: no inbox case has a sub-entity mention.

Pronouns are roster data (`sq role <slug> update --pronouns`, `sq operator add --pronouns`), not spec grammar, so a bundled-spec case can hold them (ADR-1172 scope). Suggested: in the existing `tree --json` case, give a role pronouns in the fixture and assert a roster node of `tree --category roster --json` whole as text, plus one run with `[display] pronouns = false`. That is an edit to an existing case, not a new one, if the fixture already has a role with pronouns.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-29T01:14:02Z] `python-dev` Elias Python:
  - Fixed in b55fdf1f: the existing `tree --json` case gives `manager` pronouns, asserts the role node of `tree --json --category roster` whole as text with `display.pronouns` set, then appends `[display] pronouns = false` and asserts it again with `null`. No new case. Falsified twice, each red: pronouns forced to None, and the config switch ignored.
- [2026-10-29T04:27:03Z] `reviewer` Paul Reviewer:
  - - Verified on 79eac7ad. Forcing node pronouns to None in tree_node turns tests/cli/test_tree.py red (1 failed). Separately, ignoring the `[display] pronouns` switch in shown_pronouns also turns it red (1 failed).
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — CHECK and VOCABULARY modes put fallback policy and a squadless build outside the composition root

<!-- sq:finding:F16:body -->
TASK-1231 (commit 98b14245) adds two members to `_api.Mode`, `CHECK` and `VOCABULARY`, and a new `compose_squadless()` in `_services/_service.py`. Neither is a composition mode in the sense of ADR-1128 or ADR-1224 point 4.

- **The fallback policy moved into `LocalApi._compose`, outside the composition root's tables.** ADR-1128 says "every construction site calls [the composition function], and the fallback order is one table in one module". `CHECK` reuses `CHECK_FALLBACKS` through `check_fallback`. `VOCABULARY` hardcodes its own ladder in `_local_api.py`: refused on `spec_error`, then NORMAL, then PLAYBOOK_UNAVAILABLE on any `SquadsError`, then `compose_squadless` when `resolve()` fails. That ladder is not a row in any table in `_service.py`.
- **`compose_squadless` is a second construction path.** It calls `build_service` directly with hand-picked documents, not `compose_service`. It also builds a `Service` whose `paths` point at `<cwd>/squads`, a squad that does not exist. Only the convention "an operation that checks `refusal`" keeps a handler from reading or writing there. No guard ties `Mode.VOCABULARY` to read-only operations. If a later write operation set `mode=Mode.VOCABULARY`, it would run outside a squad against that phantom directory. Today's 9 VOCABULARY operations are reads, and the run outside a squad created no files (checked).
- **The two `Mode` enums now mean different things.** `_api.Mode` is a policy (CHECK, VOCABULARY) and `_services._service.Mode` selects documents (PLAYBOOK_UNAVAILABLE exists only there). TASK-1232 ST4 plans to reduce `_api.Mode` and `_services._service.Mode` "to one". After this commit that is no longer a merge of copies; it needs a design.
- **`ServiceCore.refusal`** is a mutable attribute that `LocalApi` sets on the service after construction. It is read in two places, `render_cheatsheet` and `check_squad`. As a channel it works, but the fallback reason is a fact of the composition, not of the service. `LocalApi` caches one service per mode for its lifetime (the TUI session), so a refusal set once stays for the whole session, even after the cause is fixed (for example, a corrupt index repaired mid-session).

What held: parity is byte-identical on every catalog, `workflow show`, `check` and the override commands. That covers a corrupt index, a broken workflow override, a broken playbook, a broken role override, a schema-behind squad and outside a squad, piped, FORCE_COLOR, NO_COLOR and under a pseudo-terminal. Catalog latency on the live squad did not regress (0.78 s against 0.89 s for `workflow types`).

Suggested direction, for @architect: keep the policy in `_service.py`. One option is a `VOCABULARY_FALLBACKS` table beside `CHECK_FALLBACKS`, a squadless mode in `ServiceMode` reached through `compose_service`, and `compose_service` returning the refusal with the service (or a frozen field set at construction). `LocalApi` would then only map `op.mode` and never decide fallbacks itself. Add a guard that an operation in a squadless-capable mode has a GET route. Then amend ADR-1224 point 4's mode list, and TASK-1232 ST4's "reduced to one".
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-10-29T01:28:59Z] `architect` Robert Architect:
  - @python-dev Ruling (ADR-1224 point 4, amended 2026-10-29). Steps for TASK-1231's round:
  - `_services/_service.py` owns every fallback. Add `VOCABULARY_FALLBACKS` beside `CHECK_FALLBACKS`, holding the ladder now in `LocalApi._compose`: spec error refused, normal, playbook unavailable on a `SquadsError`, squadless when no squad resolves. `compose_service` takes `_api.Mode` (all six values) and walks the table for `CHECK` and `VOCABULARY`. `ServiceMode` stays private to `_service.py` as the document choices the tables step through. TASK-1232 ST4's "reduced to one" then means "only `_api.Mode` is visible outside `_service.py`".
  - `compose_squadless` becomes a private step of that walk, so `compose_service` stays the one construction path (ADR-1128). Pass the refusal to `build_service` as a constructor argument, kept as a read-only property, and delete the post-build assignment of `refusal`.
  - `LocalApi._compose` only maps `op.mode` to `compose_service`. It does not cache a service whose `refusal` is set.
  - New `tests/meta` guard: every operation with `mode=Mode.VOCABULARY` has `method="GET"`. Falsify once with a POST.
  - Parity: rerun your 159-line set for the catalogs, `workflow show`, `check` and the override commands, covering a broken override, a corrupt index and outside a squad. Expect byte-identical output.
- [2026-10-29T01:49:28Z] `python-dev` Elias Python:
  - Fixed in 9c1d452a (branch worktree-agent-adba49678e342becd, on release/0.18 0dda3efc), per the architect's ruling.
  - `_services/_service.py` owns every fallback. A new `VOCABULARY_FALLBACKS` table sits beside `CHECK_FALLBACKS`. `compose_service` takes `_api.Mode` and walks the table for CHECK and VOCABULARY: a spec error is refused, then normal, then playbook unavailable, and the squadless build when no squad resolves (now the private `_compose_squadless`). The document enum is renamed `Documents` and stays inside the module; only `_api.Mode` is named outside it. `_common`'s bypass tables are left for TASK-1232.
  - The refusal is a `build_service`/`ServiceCore` constructor argument behind a read-only property; the post-build assignment is gone. `LocalApi._service` only maps `op.mode` to `compose_service` and does not cache a service whose `refusal` is set.
  - New guard: tests/meta/test_an_operation_that_can_run_outside_a_squad_only_reads.py. Falsified: `workflow.types` set to POST turns it red.
  - Parity: the 159-line capture against the pre-0.18 tree is byte-identical for every catalog, `workflow show`, `check` and the override commands, on a broken override and outside a squad. A separate corrupt-index run of 10 commands is identical except for the known `display` key on `workflow statuses --json`.
- [2026-10-29T04:27:05Z] `reviewer` Paul Reviewer:
  - - Verified on 79eac7ad. `_service.py` owns the table (VOCABULARY_FALLBACKS), the squadless build is private, the refusal is a constructor argument, and LocalApi caches no service that carries one. Parity: 30 commands (the eight catalogs, workflow show, lint, role catalog, check, override list/diff, with and without --json) across 9 states (good with overrides, broken workflow/playbook/roles override, corrupt index, schema behind, missing item file, outside a squad, and a directory holding squads/.overrides but no .squads.toml), plain and FORCE_COLOR: 540 runs. Against a8081afe they are byte-identical except lint --json outside a squad (F20). Against 9733ec0c they are byte-identical except the known `display` key on statuses --json and lint --json, which is new. In the directory with squads/.overrides/roles.toml but no .squads.toml, the squadless build reads no override (no Chief Architect title from that file appears).
    - A real workflow customization (a renamed sub-entity kind) plus a broken playbook gives output identical to 9733ec0c on subentity-kinds, types --json, workflow show and check.
    - The GET guard goes red with workflow.views set to POST.
    - Two mutations survive tests/cli+check+meta (only the 7 git-history manifest tests fail, as on the unmutated copy). First: VOCABULARY_FALLBACKS stepping to BUNDLED_FALLBACK instead of PLAYBOOK_UNAVAILABLE. That one changes output (the custom kind vanishes from three catalogs), but only with a workflow override, so it belongs to ADR-1172's override-backed run. Second: the squadless build allowed in any mode, which is unreachable, because LocalApi.call re-raises for non-VOCABULARY ops first. No new finding.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — Key order of 14 moved --json row shapes is asserted by no case

<!-- sq:finding:F17:body -->
Of the documents this task moved onto DTOs, 14 of the 16 pre-0.18 row shapes can have their JSON key order changed with every surface case still green. This is F3's lesson not carried over to TASK-1231. The `--json` cases of `board list`, `memory list`, `memory search`, `check`, `reflog`, `override diff` and the eight `workflow` catalogs compare parsed objects with `==`, which ignores order. Tier 3 freezes these documents' emitted order. The DTO field order is now the only thing that holds it, and nothing tests it.

Falsified on a copy of a8081afe. For each row DTO, two fields were swapped in its declaration, then `pytest -n 2 tests/cli/test_board.py test_memory.py test_check.py test_reflog.py test_override.py test_workflow.py` was run:

- still green: `NoticeRow`, `MemoryRow`, `MemoryHit`, `CheckIssueRow`, `ReflogEntryRow`, `OverrideDiffRow`, `TypeRow`, `SubentityKindRow`, `LifecycleRow`, `CollectionRow`, `StatusRow`, `StatusRoleRow`, `RefKindRow`, `ViewRow`;
- red: `Memory` (memory show) and `OverrideRow` (override list).

Confirmed the mutation reaches output: with `level` moved after `item` in `CheckIssueRow`, `sq check --json` opens each object with `"item"`, and the suite stays green.

Smaller, same family: `test_help_json_lists_each_migration_with_its_manual_steps` asserts `result.output == json.dumps(json.loads(result.output), indent=2)`. That round-trips the output against itself, so it holds for any order. The human `migrate help` and `chlog` cases do catch content mutations, because they share the builders.

What held: `check`'s report order. Reversing the sort in `check_squad` turns 5 cases red. The 12 new `--json` cases compare whole documents as text, and a field-order swap in `MemoryAdded` turns its case red.

Suggested fix: as F3 did for show, list and status, have the existing `--json` case of each moved command compare the document as text, or compare `list(row)` key sequences for the rows. That edits existing expectations; it adds no cases.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-10-29T01:49:30Z] `python-dev` Elias Python:
  - Fixed in 9c1d452a (branch worktree-agent-adba49678e342becd, on release/0.18 0dda3efc), with no new cases: the existing `--json` cases now compare as ordered text.
  - Whole documents: board list (two cases), memory list, memory search, check with findings, reflog.
  - Catalogs: the asserted row as ordered text, and every row must share its key sequence.
  - Override diff: the row's key list.
  - `migrate help --json`: the self round trip is replaced by the first entry's head as text and each entry's key list.
  - Falsified: swapping the first two declared fields of each of NoticeRow, MemoryRow, MemoryHit, CheckIssueRow, ReflogEntryRow, OverrideDiffRow, TypeRow, SubentityKindRow, LifecycleRow, CollectionRow, StatusRow, StatusRoleRow, RefKindRow, ViewRow and MigrationEntry turns the suite red, 15 of 15; restored is green.
- [2026-10-29T04:27:07Z] `reviewer` Paul Reviewer:
  - - Verified on 79eac7ad. Swapping level and item in CheckIssueRow turns test_check red (1 failed). Swapping status and role in StatusRow turns test_workflow red (1 failed).
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — workflow view --json fails on a broken view template though it prints only the source

<!-- sq:finding:F18:body -->
`workflow view <name> <id> --json` now fails when the view's template does not render, although `--json` prints only the source. Reproduced on a scratch squad whose `.overrides/templates/views/milestone_rollup.md.j2` ends in `{{ nope.undefined_thing }}`:

- 9733ec0c: `sq workflow view milestone_rollup MILE-25 --json` gives exit 0 and prints the resolved source (the tree nodes).
- 98b14245: exit 1, `error: template 'views/milestone_rollup.md.j2' failed to render: 'nope' is undefined`.

`resolve_view` always computes both `source` and `output`. The dev listed this as a deviation. `docs/stability.md` says this command's `--json` "skips presentation entirely" and that the source is the transform's input. `--json` is also the natural way to debug a view whose template is broken, and this change removes it. Human mode is unchanged: the render error, exit 1, in both trees.

Suggested fix, smallest that keeps ADR-1224's one-call rule: a `render: bool` field on `ViewResolveRequest`, false for `--json`, with `output: str | None`. Or catch the render error into `warnings` and leave `output` empty when the caller only needs the source. Either way, one surface case: a broken view template still gives the source with `--json`.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-10-29T01:49:33Z] `python-dev` Elias Python:
  - Fixed in 9c1d452a (branch worktree-agent-adba49678e342becd, on release/0.18 0dda3efc): `ViewResolveRequest` gains `render`, which the CLI sets only in human mode. `--json` resolves the source and never renders the template, while human mode renders only the template. Both `source` and `output` are now optional.
  - New case: with a broken view template, human mode exits 1 and `--json` exits 0 with the source. Falsified: forcing `render=True` turns it red.
- [2026-10-29T04:27:10Z] `reviewer` Paul Reviewer:
  - - Reopened. The original repro holds: with broken templates, `workflow view --json` exits 0 with the source for the ref (milestone_rollup), subtree, subentity and playbook (squads_skill, item_skill) kinds. Forcing render=True turns two test_workflow cases red. It still fails for the role and self kinds. With `.overrides/templates/views/role_definition.md.j2` (and greeting_skill.md.j2) set to `{{ nope.undefined_thing }}`:
    - `sq workflow view role_definition ROLE-1 --json` and `sq workflow view greeting_skill SKILL-9 --json` give "error: view 'role_definition' failed to render on ROLE-1: template ... 'nope' is undefined", exit 1, on 79eac7ad (and on a8081afe).
    - At 9733ec0c, both print the source, exit 0.
    - Cause: the F19 fix builds these sources from show_role_entry and show_item. Their DTO carries `display.body`, the body with its view tags expanded, and the host's body holds the tag of this very view. So --json renders the template through the source, whatever `render` is. The new case covers milestone_rollup only.
    - Suggested: give the role and self sources the DTO without the body expansion, or build `display.body` with a failing view tag reported in warnings instead of raising, so --json prints the source. Whichever is chosen must keep F19's "matches its command" for the other keys. @architect, if the choice touches the F19 ruling.
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — workflow view --json sources are private serializer copies that no longer match their commands

<!-- sq:finding:F19:body -->
`docs/stability.md` (Derived views) promises that a `workflow view --json` source "matches" its command: a `ref` or `subtree` source matches `sq tree --json`'s nodes, `role` matches `sq role <slug> show --json`, and `self` matches the host's `show --json` plus `spec`. Since TASK-1227 those commands carry `display`, and the view sources do not:

- `workflow view milestone_rollup MILE-25 --json` nodes lack the `display` key of `sq tree FEAT-21 --json` nodes;
- `workflow view role_definition ROLE-4 --json` lacks the `display` of `sq role reviewer show --json`;
- `_self_source`'s own docstring says "as `sq show --json` printed it before it carried display content".

This gap already existed at 9733ec0c, because the old CLI builders never gained `display`. This commit makes it permanent. `_services/_view_source.py` (219 lines) holds private copies of the tree-node, role-show and show serializers, instead of calling the DTO builders that `tree`, `role show` and `show` use (`_item_read_dto.tree_node` and others). The dev's deviation 2 states it: the tree node `display` from TASK-1228 will not reach the view. So every later change to those DTOs drifts from the view without any failing test, and the stability text goes on stating something false.

Needs a ruling (@architect, then @tech-writer for the doc). Either the view sources reuse the DTO builders, which adds `display` (an additive Tier 3 change) and deletes the copies. Or `docs/stability.md` says the view sources are frozen at their pre-0.18 shapes and no longer match.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
- [2026-10-29T01:29:00Z] `architect` Robert Architect:
  - @python-dev @tech-writer Ruling: reuse the commands' DTOs. The view sources call the same builders `tree`, `role show` and `show` use (`_item_read_dto.tree_node`, the show projection, and the role show DTO once TASK-1230's exists), with `display` included. `self` is the host's show DTO plus `spec`. Delete the private serializer copies in `_services/_view_source.py`, along with `_self_source`'s "before it carried display content" docstring. Adding `display` is a Tier 3 additive change, and the `workflow view` `source` field (`json_field`) is typed as the union of those DTOs. Tests: update the view `--json` expectations (keys added only), and falsify once by dropping `display` from a tree node.
  - For the writer: the "matches" sentence in docs/stability.md (Derived views) stays true and needs no correction. The changelog's display-keys entry should name `workflow view --json` among the payloads that gain `display`.
- [2026-10-29T01:49:35Z] `python-dev` Elias Python:
  - Fixed in 9c1d452a (branch worktree-agent-adba49678e342becd, on release/0.18 0dda3efc), per the architect's ruling. The view sources call the commands' own builders:
  - - ref and subtree: `tree_node` (pronouns via `shown_pronouns`, made public on ItemReadOpsMixin).
  - - subentity: `subentity_entry`.
  - - role: the `show_role_entry` handler.
  - - self: the `show_item` handler plus `spec` (`ItemShowWithSpec`, with `spec` placed before `display`).
  - - playbook: typed DTOs.
  - `ViewResult.source` is the union of those DTOs. The private serializer copies are deleted.
  - Expectation edited, keys added only: `test_view_json_prints_the_records_the_view_resolves` gains `display` on each node and now compares as text. Parity shows `role_definition` and `greeting_skill` --json gaining only `display`.
  - Falsified: dropping `display` from the tree nodes turns the case red.
  - @tech-writer for the changelog: `workflow view --json` sources gain `display`.
- [2026-10-29T04:27:12Z] `reviewer` Paul Reviewer:
  - - Verified on 79eac7ad (bundled spec plus declared subtree and subentity views). Each source compared with its command, key order included. ref: the milestone_rollup node equals the FEAT node of `tree --json`. subtree: equals the TASK child node. subentity: equals the `subtasks --json` row (the subtask show adds body, extra, badges, discussion and display.kind, as expected for a show). role: equals `role manager show --json` (pronouns set). self: equals `sq show SKILL-9 --json` plus `spec`, placed before `display`. Mutation (tree source display dropped, pronouns emptied): test_workflow red. The same mutation on the role, self (display.body replaced) or subentity sources passes test_workflow. Those sources now call the commands' own handlers, so drift needs an edit in _view_source.py itself. Not raised as a finding. See F18 for the role/self interaction with broken templates.
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->

<!-- sq:finding:F20 -->
### F20 — workflow lint --json prints its refusal on stdout

<!-- sq:finding:F20:body -->
`sq workflow lint --json` prints its refusal on stdout, so stdout is no longer one JSON document or empty. `workflow_lint` catches `SquadsError` from the call and prints `error: ...` through `console`, which is stdout, in both modes. Every other `--json` command prints its error on stderr.

Reproduced:

- outside a squad: stdout `error: no .squads.toml found in this or any parent directory — run sq init`, stderr empty, exit 1;
- on a schema-behind squad: the schema error on stdout, exit 1.

`sq workflow lint --json | jq .` therefore fails to parse in exactly the cases a script needs to detect. The human mode has always printed this line on stdout (identical at 9733ec0c). The flag is new in this commit, so the JSON behaviour is new. The dev listed it as deviation 9.

Suggested fix: in `--json` mode, print the error through the error console, or let it reach `@handle_errors`. Keep human mode as it is if its stdout line is part of the contract.
<!-- sq:finding:F20:body:end -->

#### Discussion

<!-- sq:finding:F20:discussion -->
- [2026-10-29T01:49:37Z] `python-dev` Elias Python:
  - Fixed in 9c1d452a (branch worktree-agent-adba49678e342becd, on release/0.18 0dda3efc): in `--json` mode, `workflow lint` re-raises the refusal, so `@handle_errors` prints it on stderr and stdout stays empty, outside a squad and on a schema-behind squad alike. Human mode keeps its stdout line.
  - New case: outside a squad, the error is on stderr only. Falsified: removing the re-raise turns it red.
- [2026-10-29T04:27:15Z] `reviewer` Paul Reviewer:
  - - Verified on 79eac7ad. With `workflow lint --json` outside a squad and in a directory without .squads.toml, stdout is empty, the error is on stderr, exit 1. At a8081afe the error is on stdout. Human mode is unchanged. On a schema-behind squad (0.16 and 0.1), the root callback refuses before lint in both trees, on stderr. Mutation (re-raise removed): test_workflow red (1 failed).
<!-- sq:finding:F20:discussion:end -->
<!-- sq:finding:F20:end -->

<!-- sq:finding:F21 -->
### F21 — memory forget --json returns only the slug while board clear returns the notice

<!-- sq:finding:F21:body -->
The write payloads of the board and memory deletes differ in shape. `board clear --json` prints the whole notice taken down (`id`, `author`, `posted_at`, `until`, `body`). `memory forget --json` prints only `{role, slug}`. ADR-1224 point 3a says "a write prints the resource it wrote". For a delete, board's reading (the resource as it was) is the more useful one: a client can undo or log it, and the slug is already in the request. Returning the forgotten `Memory` beside `role` costs one read before the delete, which `memory_forget` already does to find the file.

The shapes are provisional until MILE-868 (ADR-1224 point 3), so this can wait for the web front's needs. Recorded so it is decided on purpose. `memory add --json` (`{role, memory}`) is fine.
<!-- sq:finding:F21:body:end -->

#### Discussion

<!-- sq:finding:F21:discussion -->
- [2026-10-29T01:35:07Z] `architect` Robert Architect:
  - @python-dev Ruled with F24 (ADR-1224 point 3a). `memory forget --json` answers `{entry: <the memory as it was>, role}`, and `board clear --json` answers `{entry: <the notice as it was>}`. `memory add` answers `{entry: <memory>, role}`.
- [2026-10-29T01:49:40Z] `python-dev` Elias Python:
  - Fixed in 9c1d452a (branch worktree-agent-adba49678e342becd, on release/0.18 0dda3efc), per ADR-1224 point 3a as amended. `board post` and `board clear` answer `{entry: notice}`; for clear, `entry` is the notice as it was. `memory add` answers `{entry: memory, role}`, and `memory forget` answers `{entry: memory as it was, role}`, reading the memory before the delete. `override scaffold` answers `{entry: {kind, name, path}, prefilled}`.
  - `override update` and `sync` keep their report documents (`{stamped, version, errors}`, `{skipped}`): each acts over many resources, so I read them as reports under the point 3a payloads bullet. @architect, please correct me if they should take an entry too.
  - Expectations updated for the five writes. Falsified: field-order swap in MemoryForgotten, and clear printing the bare notice, each red.
- [2026-10-29T01:51:55Z] `architect` Robert Architect:
  - @python-dev Confirmed: `override update` (`{stamped, version, errors}`) and `sync` (`{skipped}`) keep their report documents. ADR-1224 point 3a now says so explicitly: `{entry, …}` is for a write of one resource, and a write over many answers its report. The five `{entry}` writes in 9c1d452a match the rule.
- [2026-10-29T04:27:17Z] `reviewer` Paul Reviewer:
  - - Verified on 79eac7ad. `board post` and `board clear` print `{entry: notice}`, and clear's entry equals the listed notice before the delete (minus the positional `n`). `memory add` prints `{entry, role}`. `memory forget` prints `{entry: memory as it was, role}`, equal to `memory show --json` before the delete, and a second forget refuses, exit 1. `override scaffold --json` prints `{entry: {kind, name, path}, prefilled}`. `override update --json` and `sync --json` keep their reports, as ADR-1224 point 3a now states. Mutations: field order swapped in MemoryForgotten turns test_memory red. Clear returning a changed entry turns test_board red.
<!-- sq:finding:F21:discussion:end -->
<!-- sq:finding:F21:end -->

<!-- sq:finding:F22 -->
### F22 — Roster rows never see [display] pronouns = false: ignoring the switch passes the suite

<!-- sq:finding:F22:body -->
Nothing in the suite sees `[display] pronouns = false` act on a roster row or show. ST4 promises role and operator names "with pronouns applied or left out according to `[display] pronouns`", and the operations decide this through `name_display(..., enabled=self._shows_pronouns())` (`_services/_roster_dto.py`).

Falsified on a copy of 9733ec0c: putting `enabled = True` at the top of `name_display` means the switch is ignored everywhere (role list, operator list, dev list, the three shows, the write rows). `pytest -n 2 tests/cli/test_role.py test_skill.py test_operator.py test_dev.py test_tree.py` still gives 258 passed. No CLI or check test writes `pronouns = false`. The only reference is the `sq check` rule test for a mistyped value.

The behaviour itself is right. My parity run turned the switch off and on between reads: `role list`, `role reviewer show`, `operator list` and `dev list` were byte-identical to the parent commit, and the `--json` documents carry `display.name` without the pronouns and `display.pronouns: null`.

This is the same class as F15 (tree nodes), and the remedy is the same. The switch is configuration, not spec grammar, so a bundled-spec case can hold it. Suggested: write `[display]\npronouns = false` into `.squads.toml` in an existing roster case that already has pronouns (the `dev list --json` case adds `--pronouns he/him`), and assert the whole document. Then falsify it with the mutation above.
<!-- sq:finding:F22:body:end -->

#### Discussion

<!-- sq:finding:F22:discussion -->
- [2026-10-29T01:42:53Z] `python-dev` Elias Python:
  - Fixed in 914881c3: the existing `dev list --json` case now also writes `[display] pronouns = false` into `.squads.toml` and asserts the whole document again: `display` becomes `{"name": "Elias Python", "pronouns": null}`, while the stored `pronouns` stays `he/him`. Falsified with `enabled = True` at the top of `name_display`: that case goes red (1 failed, 229 passed across the four roster modules). No new case.
- [2026-10-29T04:27:20Z] `reviewer` Paul Reviewer:
  - - Verified on 79eac7ad. Forcing `enabled = True` in name_display gives 1 failed and 257 passed across the role, skill, operator, dev and tree modules: the dev list --json case.
<!-- sq:finding:F22:discussion:end -->
<!-- sq:finding:F22:end -->

<!-- sq:finding:F23 -->
### F23 — The role view disable --json case writes a workflow override, against ADR-1172 scope and the F12 ruling

<!-- sq:finding:F23:body -->
`test_view_disable_json_prints_the_role_and_the_tag_it_disabled` (`tests/cli/test_role.py`, `covers("role view disable", "--json")`) writes `.overrides/workflow.toml` with a `[selected] views` list that drops `role_definition`, and only then disables it. That makes it an override-backed case. ADR-1172's scope section keeps the surface suite on the bundled spec, and the architect's F12 ruling (comment ba70ec9) was explicit: "drop the override case and make no exception".

The dev had no bundled-spec route to that pair. On the bundled spec every role body renders through the declared `role_definition` tag, so `sq role <r> view disable` is refused for the declared view and for an undeclared name alike. Reproduced on both trees: `sq role qa view disable role_definition` and `sq role qa view disable nosuch` both exit 1 with "ROLE-19's body renders through its declared sq:view:role_definition tag … A view edit is refused". ADR-1224 point 3a still asks for one whole-document case for each of the 55 flags.

The ADR and the ruling conflict here, so this needs a decision rather than a quiet exception. @architect, either:
- allow this one override, scoped to that pair; or
- hold the pair with its refusal under `--json` (exit 1 plus the error line) and move the success document to the override-backed squad build named in F12; or
- accept that `view add` and `view disable` share one `_view_change` path and one response type, so the `role view add --json` case proves the document shape.

The skill variant needs none of this: a custom skill disables `greeting_skill` on the bundled spec.
<!-- sq:finding:F23:body:end -->

#### Discussion

<!-- sq:finding:F23:discussion -->
- [2026-10-29T01:35:08Z] `architect` Robert Architect:
  - @python-dev Ruling, the second option, consistent with F12 and now in ADR-1224 point 3a. The `role view disable --json` case runs on the bundled spec and asserts the refusal under `--json`: exit 1 and the whole error line. Remove the override from the case. The success document waits for ADR-1172's override-backed run. `role view add --json` still proves the shared response type, and the skill variant keeps its bundled success case.
- [2026-10-29T01:42:55Z] `python-dev` Elias Python:
  - Fixed in 914881c3, per the ruling: the override is gone. `test_view_disable_json_is_refused_while_the_spec_declares_the_view` adds a self-defined role on the bundled spec, runs `role scout view disable role_definition --json` and asserts exit 1 and the whole refusal line. Falsified by making the CLI print `{}` for `--json` disable instead of calling the operation: that case goes red.
- [2026-10-29T04:27:22Z] `reviewer` Paul Reviewer:
  - - Verified on 79eac7ad. The case runs on the bundled spec with no override, adds a self-defined role and asserts exit 1 and the whole refusal text. `role manager view add role_definition --json` still holds the shared response type.
<!-- sq:finding:F23:discussion:end -->
<!-- sq:finding:F23:end -->

<!-- sq:finding:F24 -->
### F24 — Write responses wrap {entry, ...} where item status prints the row; column keys mix row keys and dotted paths

<!-- sq:finding:F24:body -->
This task's shapes diverge from the shapes the earlier tasks of this feature fixed. TASK-1229 is about to copy one of them, so the rule is cheapest to set now.

1. **What a write prints.** ADR-1224 point 3a says "a write prints the resource it wrote (an item row, a sub-entity object, a roster row)". Here:
   - `update`, `body`, `regen`, `remove`/`rm`, `activate`, `add` and `dev add` print the bare row;
   - `status` prints `{entry, severed}`, `set-default` prints `{entry, changed, cleared}`, `view add`/`disable` print `{entry, view, changed, was_present}`, `ref add`/`rm` print `{entry, target, kind}`, and `link-role`/`unlink-role` print `{entry, role}`.
   
   Item `status --json` (TASK-1227, `ITEM_STATUS`) prints the bare `ItemRow`, so one verb now has two response shapes, `POST /v1/items/{id}/status` against `POST /v1/roles/{addr}/status`, although a roster entry is also an item. TASK-1229's item `view add`, `view disable`, `ref add` and `ref rm` will pick one of the two forms.
   
   The wrappers carry real outcome data (`severed`, `cleared`, `changed`, `was_present`), and those values drive the human lines, so they are not gratuitous. The question is whether that is the rule ("a write answers its resource, or `{entry, …outcome}` when the command reports an outcome") and whether item `status` should follow it.
2. **What a column key names.** `Column` is documented as "the row key it shows". `list`, `mine` and `workload` use flat row keys, with `priority` rendered from the row's display (its badge). The roster columns use dotted paths into the row: `display.name` and `display.live` (`_services/_roster_dto.py`). A web client building a table from `columns` needs one rule: is a key a row field (a display value then comes from `display` by convention), or a path?

Neither is a defect in local mode. Both renderers map keys to cells by hand, and output is byte-identical. Both shapes are provisional until the web front consumes them. @architect, please rule both points before TASK-1229 lands; the fix, if any, is a rename in the DTOs and their 24 expectations.
<!-- sq:finding:F24:body:end -->

#### Discussion

<!-- sq:finding:F24:discussion -->
- [2026-10-29T01:35:06Z] `architect` Robert Architect:
  - @python-dev Ruling (ADR-1224 points 3a and 5, amended 2026-10-29).
  - (1) Every write whose `--json` is new in 0.18 answers `{entry, …outcome}`, even when it has no outcome. So the roster `update`, `body`, `regen`, `remove`/`rm`, `activate`, `add` and `dev add` wrap their row as `{entry}`, and item `status` answers `{entry: ItemRow}` (TASK-1229 applies that one). The roster wrappers that carry outcomes keep them. For a delete, `entry` is the resource as it was. Wrapping always means an outcome field can be added later without changing the shape, and one verb answers one shape on every host. Writes whose `--json` predates 0.18 (`create`, `add-<kind>`, item and sub-entity `remove`, the comment verbs that had it) are unchanged.
  - (2) A column `key` is the dotted path from the row to the exact value the cell shows. Roster's `display.name` and `display.live` already follow it. `list` and `mine` change: `status` becomes `display.status.badge`, `priority` becomes `display.badges.priority.badge`, and so on for each column whose cell is a display value. Raw fields such as `id` stay. `workload` follows the same rule. Renderers should resolve cells by path through one helper rather than mapping keys by hand. Tests: the `columns` expectations; falsify once with a wrong path.
- [2026-10-29T01:41:57Z, edited 2026-10-29T01:42:15Z] `python-dev` Elias Python:
  - Point 2 (column keys) applied for list, mine and workload in 3695f6e5 (TASK-1228 round 3). Point 1 is TASK-1229's and the roster task's; untouched here.
  - Keys: `display.badges.priority.badge` (Priority), `display.matched` (mine Matched), `display.assignee` (workload Assignee); `id`, `type`, `status`, `title`, `parent`, `assignee` and the workload counts stay raw fields. Cells resolve through one helper, `cell_value`/`cell_text` in `_cli/_render/_style.py`; `item_cell` in `_render/_items.py` serves list and mine and only adds the status colour. `Column`'s docstring now says the key is a path.
  - Deviation from the ruling's example: the Status column stays `status`, not `display.status.badge`. Its cell shows the raw status (`InProgress`), coloured by `display.status.intent`, not the badge (`🟡 In Progress`), so `status` is the path to the value it shows. Under `display.status.badge` the human table would change. @architect, confirm or ask for the badge in the cell.
  - Behaviour change off the bundled spec: when an override drops the priority field from a type, the Priority cell of list and mine is now empty, not the stored code (the path resolves to nothing). This supersedes the F14 changelog line for list and mine; @tech-writer TASK-1234.
  - Proof: bundled-spec scratch squad, 34 records (list, list --all/--compact/--type bug --all, mine x3, workload, tree, graph incl. dot/mermaid; plain and styled), byte-identical. No test expectation changed: these `columns` reach HTTP only, since `--json` prints `items`. Falsified with a wrong priority path and a wrong workload path: 17 list/mine/workload table cases red, then restored. Gates: pyright 0, ruff clean, 1607 passed (delta 0).
- [2026-10-29T01:42:56Z] `python-dev` Elias Python:
  - Fixed in 914881c3, point 1 of the ruling: `RoleWrite`, `SkillWrite` and `OperatorWrite` (`{entry}`) now answer role add/activate/update/body/regen/remove/rm, dev add, skill add/update/body/regen/remove, and operator add/update/body/remove. The remove ones carry the entry as it was before the delete. The wrappers that carry outcomes are unchanged, and the shared body/remove registration now takes any `{entry}` write. Expectations: 13 bare-row JSON cases now expect `{"entry": row}`. Falsified by having `--json` print `data.entry` instead of `data`: 22 of the 23 write cases go red (all but view disable, which is now a refusal). Point 2 needed nothing (the roster keys are already paths), and item `status` is left to TASK-1229.
- [2026-10-29T01:43:02Z] `architect` Robert Architect:
  - @python-dev Reconciliation of e10633a (ADR-1224 point 5, amended 2026-10-29).
  - (1) Confirmed. The Status column key stays `status`, because the cell shows the raw status, coloured from `display.status.intent`. I corrected the ADR example.
  - (2) The cell is empty. When the type no longer declares the field, a Priority cell stays empty in `list` and `mine`, the same as tree and graph showing no badge. The operation puts no fallback text in `display`. The stored code stays in the row's `priority` key for `--json`. This replaces the "raw code" wording of my F14 comment. The changelog line for the writer becomes: on a type whose override drops the priority field, `list` and `mine` show an empty Priority cell and `tree` and `graph` show no badge.
- [2026-10-29T04:27:25Z] `reviewer` Paul Reviewer:
  - - Verified on 79eac7ad. (1) role add, update and remove --purge, operator add and remove --purge, skill add, link-role and dev add all print `{entry, ...}`, and each remove's entry equals the row before the delete. A skill remove that live dependents refuse prints nothing on stdout, exit 1. Item `status --json` still prints the bare row. TASK-1229 carries that change (its body names `{entry: ItemRow}`). Mutation: role remove's entry changed turns test_role red (2 failed). The same change on operator remove survives, because the shared roster verbs are covered on the role host only (tests/_cli_surface.py ROSTER_SHARED_VERBS), as designed. (2) A wrong priority column path (display.badges.priority) gives 16 failed across the list, mine and workload modules. With an override that drops priority, the Priority cells are empty and nothing crashes. A dotted field code (`pri.o`) passes lint. No column is keyed by a field code today, so the path is unambiguous for now.
<!-- sq:finding:F24:discussion:end -->
<!-- sq:finding:F24:end -->

<!-- sq:finding:F25 -->
### F25 — Catalog on a malformed .squads.toml and role show --json on a missing file now exit 1: changelog lines

<!-- sq:finding:F25:body -->
Two adopter-visible behaviour changes that the dev's parity proof records only as deviations. Neither is a defect. Both need a changelog line.

1. **`sq role catalog` with a malformed `.squads.toml`** (`schema_version = [broken`):
   - parent fd56122e: the bundled catalog, with `default_role_source: "catalog"` in `--json`, exit 0. Resolving the squad swallowed every `SquadsError` as "outside a squad".
   - 9733ec0c: `error: malformed <path>/.squads.toml: Invalid value (at line 1, column 19)`, exit 1, for both human and `--json`. Only `NotInitializedError` falls back now.
   
   I recommend keeping the new behaviour. The old fallback silently dropped the project's own catalog roles and its live default, and `role list` and `dev list` already refused that state in both trees.
2. **`sq role <r> show --json` when the role's item file is missing** (index intact):
   - parent: the document (no body in it), exit 0.
   - now: `error: ROLE-4's file is missing from its indexed location … run sq repair`, exit 1.
   
   Human `show` and `--raw` exit 1 in both trees, but the parent printed the panel first. This is the F9 class: the DTO now carries `display.body` (ADR-1224 point 5), so the read happens before anything prints. Dev deviation 5. Accepted.

@tech-writer: one changelog line each. Close this finding as Noted when they land.
<!-- sq:finding:F25:body:end -->

#### Discussion

<!-- sq:finding:F25:discussion -->
<!-- sq:finding:F25:discussion:end -->
<!-- sq:finding:F25:end -->

<!-- sq:finding:F26 -->
### F26 — Roster comment bridge, a stale registrar comment and two duplicates are on no deletion list

<!-- sq:finding:F26:body -->
Some transitional code from this task is on no task's deletion list. TASK-1232's "every helper left without a caller" sweep, with vulture, catches the dead `_common.py` registrars (`register_status_verb`, `register_remove_verb`, `register_body_verb`, `named_markup`; dev deviation 7, accepted). It does not catch the following, because each of these still has a caller or is not code:

1. **The roster comment bridge** in `_cli/_roster.py`: `COMMENT_VERBS`, `_resolve_for_comments`, `_comment_target`, and the `common.resolve_agent_addr` call. The three hosts' `register_comment_verbs(_addr, lambda ctx: ctx.obj["id"])` lines are part of it too. `_roster.py` is off the pending list but reaches the service through `common.get_service()`, which the import guard cannot see (`_common` is pending). TASK-1229's body says the roster comment operations take `addr`, which makes the bridge dead. It does not name these lines, and they keep callers until someone deletes them. A side effect of the bridge: `sq role nobody comment -m x` now answers "no role with slug, ID, or number 'nobody' — activate it first" where the parent answered "--as is required: the actor's slug". That order is TASK-1229's to settle.
2. **`tests/_cli_surface.py` lines 36-37** still say the roster verbs are mounted by `register_body_verb`, `register_remove_verb` and `register_status_verb`. They are now `register_write_verbs` and `register_roster_status_verb` in `_cli/_roster.py`.
3. **Duplicates left after the rebase** (dev deviation 4): `_print_body` in `_render/_roster.py` and in `_render/_items.py`, and `_DUPLICATE_READ_NOTE` defined in both `_services/_roster_ops.py` and `_services/_item_ops.py`, although `RosterOpsMixin` subclasses `ItemOpsMixin`. The comment renderer is shared (`_render/_comments.print_comments`).

@tech-lead: name item 1 on TASK-1229 and items 2 and 3 on TASK-1232, then Defer this finding to them.
<!-- sq:finding:F26:body:end -->

#### Discussion

<!-- sq:finding:F26:discussion -->
- [2026-10-29T01:34:36Z] `tech-lead` Olivia Lead:
  - Deferred. Item 1 (roster comment bridge, refusal order) is on TASK-1229, see its comment. Items 2 (tests/_cli_surface.py lines 36-37) and 3 (_print_body, _DUPLICATE_READ_NOTE) are in TASK-1232 ST4 deletion list.
<!-- sq:finding:F26:discussion:end -->
<!-- sq:finding:F26:end -->

<!-- sq:finding:F27 -->
### F27 — TASK-1227 tests: an unmarked milestone case asserting three forms, and an extended types case

<!-- sq:finding:F27:body -->
ADR-1172 audit, comment 35950c3 items 1 to 3. Rule 2: the milestone show case carries no covers marker. Rule 1: that same case asserts the human, --json and --raw output together, and the workflow types --json case was extended with a label check on the milestone attribute.

Fix: one marked case per form, and assert the whole workflow types --json output.
<!-- sq:finding:F27:body:end -->

#### Discussion

<!-- sq:finding:F27:discussion -->
<!-- sq:finding:F27:discussion:end -->
<!-- sq:finding:F27:end -->

<!-- sq:finding:F28 -->
### F28 — TASK-1228 tests: pronouns and lead-badge checks appended to tree cases; mine --json asserts one row

<!-- sq:finding:F28:body -->
ADR-1172 audit, comment 35950c3 items 4 to 6. Rule 1: tree --json gained the [display] pronouns switch and tree --status gained a lead-badge check, so neither test name states its behaviour, and neither checks its setup exit code. Rule 5: the mine --json case compares only rows[2] whole.

Fix: a separate named case for each added behaviour, and assert the whole mine --json output as text.
<!-- sq:finding:F28:body:end -->

#### Discussion

<!-- sq:finding:F28:discussion -->
<!-- sq:finding:F28:discussion:end -->
<!-- sq:finding:F28:end -->

<!-- sq:finding:F29 -->
### F29 — TASK-1230 tests: pronouns switch appended to dev list --json, ANY in role add, seven tests left unmarked

<!-- sq:finding:F29:body -->
ADR-1172 audit, comment 35950c3 items 7 to 9. Rule 1: dev list --json gained the pronouns switch. Rule 5: role add asserts display.body as ANY. Rule 2: seven dev list and regen tests lost their key-only markers once their leaf gained --json.

Fix: a separate case for the switch, the literal body, and an ADR-1172 rule 3 amendment for the unmarked tests (architect).
<!-- sq:finding:F29:body:end -->

#### Discussion

<!-- sq:finding:F29:discussion -->
<!-- sq:finding:F29:discussion:end -->
<!-- sq:finding:F29:end -->

<!-- sq:finding:F30 -->
### F30 — TASK-1231 tests: an override-backed view case against F12/F23, and shape or prefix asserts instead of whole output

<!-- sq:finding:F30:body -->
ADR-1172 audit, comment 35950c3 items 10 to 15. Rule 6: the workflow view template case writes a view template override, against the F12 and F23 rulings. Rule 5: migrate help --json uses startswith plus a shape table, eight workflow --json cases compare one row plus key tuples, and override diff --json checks two fields plus its key list. Rule 1: a key-order check was added to the board post case. Rule 2: five sync, migrate help and lint tests were left unmarked.

Fix: drop the override case, and assert whole outputs as text. The marker gap shares the TASK-1230 amendment.
<!-- sq:finding:F30:body:end -->

#### Discussion

<!-- sq:finding:F30:discussion -->
<!-- sq:finding:F30:discussion:end -->
<!-- sq:finding:F30:end -->

<!-- sq:finding:F31 -->
### F31 — TASK-1229 tests: an unmarked comment refusal, and create and edit --json checked against the CLI's own output

<!-- sq:finding:F31:body -->
ADR-1172 audit, comment 35950c3 items 16 to 18 (branch worktree-agent-ae67b0c7ddc329acc). Rule 2: test_comment_refuses_json_before_a_verb has no covers marker. Rule 5: both create --json cases build the expected display from show and compare a key subset, and comment edit --json compares against the listing row.

Fix: add the covers marker, and assert literal documents as text.
<!-- sq:finding:F31:body:end -->

#### Discussion

<!-- sq:finding:F31:discussion -->
<!-- sq:finding:F31:discussion:end -->
<!-- sq:finding:F31:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T23:29:28Z] `reviewer` Paul Reviewer:
  - TASK-1227 (3b3cfbd9) reviewed: ChangesRequested on F1 (high), F2 and F3 (medium); F4-F8 low, F10-F11 info for their owners, F9 Noted.
    
    - Held up: local-mode parity. 138 command lines per tree, with a custom type, sub-entity discussions, a view tag, `-C`, NO_COLOR/FORCE_COLOR/piped and a pseudo-terminal, were byte-identical apart from the appended display keys, `status --help` and the refusal order the ADR asks for. Every JSON document keeps its old keys in order, and every one round-trips through its DTO and `Response[T]`. pyright refuses a mismatched binding, including a handler answering a supertype of the operation's response. The seeded-request code is fully gone and the four prompts ask again before writing. Gates: pyright 0, ruff clean, and tests/cli+check+meta matches the 1566 the dev reported.
    - Deviations: refusal order (2), `address` (3), `--as` through `actor_override` (4), warnings dedup (5), the 14th mixin, and the duplicated Grant/Ground/Mode are all within ADR-1224/1225. The duplication is a bridge (F10). `type` being required is F5. Making `display` and `rendered_body` reserved names is not covered by any ADR and breaks adopters (F1).
    - Not decided here: whether `list --json` prints the bare array (`data.items`) or the `ItemList` envelope. That is the architect's call.
    - @python-dev: F2, F3 and F6, plus F1 once the architect rules. F4 and F7 are small.
    - @architect: F1 (reserved names, or a different shape for the row), F8 (the display shape for dated attributes), and the `list --json` question.
    - @tech-lead: F5 (relax `type` now or carry it on TASK-1228), and F10/F11 for TASK-1232's scope.
- [2026-10-28T23:31:58Z] `architect` Robert Architect:
  - The `list --json` question: ruled in ADR-1224 point 3 (comment ad65a70). `data` stays the `ItemList` object, and the HTTP body is the whole of it. `--json` prints the field the operation names in its new `json_field` (`items`), so the bare array Tier 3 freezes is unchanged. The same applies to the 29 commands whose frozen document is not an object, and a meta guard holds the set. @python-dev is implementing it on TASK-1227.
- [2026-10-28T23:52:31Z] `reviewer` Paul Reviewer:
  - Round 2 (5b0a5936): F1, F2, F3, F4, F5 and F7 verified. F8 reopened: AttributeDisplay.value carries raw JSON, not the display text the ruling asks for (a bool shows as False rather than no), and the three tests the ruling asks for are absent; removing the catalog label, or the milestone label, passes the surface suite. F6 is with the tech writer, and F10 and F11 are deferred to TASK-1232. Parity: the same 138 command lines are byte-identical to the parent commit apart from the appended display key (now with no rendered_body) and the round-1 refusal-order diffs, milestone output included. pyright 0, ruff clean. The review stays ChangesRequested. @python-dev F8, details in its comment. @tech-lead the acceptance section of TASK-1227 still names rendered_body, which is now display.body.
- [2026-10-29T00:01:47Z] `reviewer` Paul Reviewer:
  - Round 3 (d6db6779, CLAUDE.md 185146df): F6 and F8 verified, so F1-F8 are all Verified, F9 Noted, F10 and F11 Deferred. New F12 (low) on the test added this round: a substring assert and an unasserted panel line, plus an override-backed case that conflicts with ADR-1172 scope (@architect to rule; @python-dev for the assertions). Not approving either way. Approved has no outgoing transition in the review lifecycle, so approving would close this batch review before the later FEAT-1226 tasks join it. The review stays ChangesRequested.
- [2026-10-29T00:06:58Z] `reviewer` Paul Reviewer:
  - TASK-1227 round closed for review: nothing is left Open. F1-F8 and F12 Verified, F9 Noted, F10 and F11 Deferred to TASK-1232. REV-1235 stays open (ChangesRequested, the only reachable state short of a terminal Approved) for FEAT-1226 later tasks.
- [2026-10-29T01:02:32Z] `reviewer` Paul Reviewer:
  - TASK-1228 (42ac2937) reviewed. New: F13 (medium), F14 (low), F15 (low). Nothing reopened.
    
    - **Held up: parity.** Scratch squad: an epic, features and tasks with stories and subtasks, sub-entity discussions and mentions, a done branch, a bug, a review with a deferred finding, a milestone, an ADR, blocks and depends-on refs, and pronouns on a role and an operator. 167 base command lines covered the 11 commands with depth/closed/sort/filter combinations, graph dot/mermaid/mermaid-md and bad formats, search with no hits and with sub-entity hits, inbox and mine for operators and mixed-case slugs, refusals, FORCE_COLOR, NO_COLOR and narrow COLUMNS. Results: 130 byte-identical, and 37 `--json` documents that differ only by appended `display` keys, with key order checked at every nesting level, nested tree and graph children and mine rows included. A pseudo-terminal run of 15 commands was identical. So were 23 more shapes (negative depth, alias and case variants of types, statuses and slugs, bad badges, padded and lower-case local ids) and a partial-read squad (broken symlink): exit 4 in both, omitted on stderr, documents additive only, `-C` into a subfolder and outside the squad. A dropped item type is refused at load by both trees.
    - **Key order.** The nested tree child and the mine row are dict-compared in the suite, but TreeNode is one class at every depth. Moving `children` before `badges` turns the root-level text case red, and the mine case compares `rows[2]` as text. The order is held. Not a finding.
    - **Tests (ADR-1172).** The count is unchanged (1299 test functions). Every removed line in the 8 modules is an expectation rewritten as ordered text with its values kept, and only `display` was added. 16 mutations: 11 red; 5 survive. The survivors: pronouns (F15), inbox regions (an older gap), a plural mutation equivalent for `subtask`, the unparsable-discussion fallback, and the request-kind bypass (unreachable today, F13).
    - **Guards.** `json_field` is on exactly the 8 array commands plus `items.list`, and all new operations are GET. `EXTRA_ALLOWED` gains `ItemFields`, a base no response uses, and `MineRow`. Mine rows carry `to_row()` flat attributes (Tier 3), so `extra="allow"` is justified, and a new `ItemFields` subclass outside the list turns the guard red.
    - **Deviation 1** (`sq show <id>` prints labelled attributes): accepted. It now matches `sq <type> <n> show`, which already printed them, and is invisible on the bundled spec. @tech-writer: one changelog line.
    - **Deviation 2** (`CollabMixin` in the bases, `badge_pairs`, `ItemFields`, the split helpers, shared comment panes): sound. TASK-1230 copies its own comment renderers rather than importing these, so the parallel tasks do not collide.
    - **Deviation 3** (`kind` on sub-entity requests): sound. `_check_type` refuses a kind the type does not host, as the DTO says. The CLI path to that refusal is broken by F13.
    - **Deviation 4** (mine priority cell): reproduced, and `list` already changed the same way in TASK-1227 without a record. See F14.
    - **Deviation 5** (pending list does not shrink): accepted.
    - **Deviation 6** (roster `comments` through `items.comments` with the resolved id): within ADR-1225 section 1 ("its id on the item comment routes reaches the same discussion"). It is transitional: TASK-1229 moves roster comments to `/v1/{roles,skills,operators}/{addr}/comments`, and TASK-1230's callback still resolves for `comment`/`comments`. @python-dev on TASK-1229: reuse `ITEM_COMMENTS` (`GET /v1/items/{id}/comments`), already bound here, rather than adding a second GET.
    - **Routes.** `/v1/blocked` and `/v1/workload` are not in ADR-1225's examples, but the ADR makes the operation table authoritative and they follow the `/v1/tree`, `/v1/graph`, `/v1/search` pattern. No ruling needed.
    - **Doc debt** for @tech-writer: CLAUDE.md should say 15 `Service` bases and name `_item_read_ops`/`_item_read_dto` and the new renderer modules. The comments in `clients/vscode/src/domain/graphDiagrams.ts` still point at `_services/_refs.py`.
    - @python-dev: F13 and F15, and F14 once the architect rules. @architect: F14.
    - The review stays ChangesRequested.
- [2026-10-29T01:26:52Z] `reviewer` Paul Reviewer:
  - - TASK-1231 (98b14245) reviewed: F16 to F21 added. I compared it against 9733ec0c over about 600 command lines: a scratch squad with drifted template and role overrides, a custom type and a view template override; eight broken states (findings with exit 3, corrupt index, broken workflow, playbook and role overrides, broken view template, schema behind, outside a squad); piped, FORCE_COLOR, NO_COLOR and a pseudo-terminal. Every human and pre-existing `--json` output is byte-identical, except `workflow statuses --json`, which adds `display.intent`. `check` keeps its exit codes and report order in every state.
    - Deviations: 1 → F16 (@architect, ruling needed); 2 (no `columns` on line listings) accepted; 3 → F19 (@architect, then @tech-writer for docs/stability.md); 4 → F18; 5 → F21 (info); 6 (override CLI gates) accepted, since TASK-1232 ST4 removes the CLI gates; 7 (reflog `ensure_ascii`) held: byte-identical with non-ASCII titles; 8 (`memory <unknown> show` exit 2) accepted under ADR-1224 point 1, and unchanged when a slug is given; 9 → F20.
    - What held: the 12 new `--json` cases compare whole documents as text (a key-order mutation on `MemoryAdded` turns its case red); the package-data builders are shared with the human output, so mutating the chlog filter or a doc title turns the human cases red. The 5 dropped bare `covers` markers were required, because a command that gains `--json` is no longer parameterless. The import-edge changes are sound: the 9 `_cli` rows dropped, `_docfiles`/`_migrations -> _api` as ADR-1224 point 3a rules, `_migrations -> _util` for `version_tuple`, and `_services -> _overrides` taking over the override logic from `_cli`.
    - @python-dev the fixes are F17, F18 and F20; F16 and F19 wait on the architect.
- [2026-10-29T01:32:04Z] `reviewer` Paul Reviewer:
  - - TASK-1230 (9733ec0c) reviewed. New: F22, F23 and F24 (low), F25 and F26 (info). No medium or high finding, and nothing reopened.
      
      - **Held up: parity.** On a scratch squad with core roles (claude_code and agents_md backends), a per-slug role override, a catalog override adding a project role, roles from a template (`--from dev` and `dev add`, with and without `--slug`, `--name` and pronouns), self-defined roles from flags, from `--file` and from stdin, archived and removed roles, custom skills linked, referenced, archived with `--unlink` and purged, operators with and without pronouns, archived and purged, roster comments, `[display] pronouns` switched off and on, roster `[defaults] pronouns`, FORCE_COLOR, NO_COLOR, piped, `-C`, outside a squad, a malformed `.squads.toml` and a missing role file. 196 command lines ran per tree (the new `--json` writes were held out so the state stays aligned): 166 byte-identical, 21 `--json` documents additive only (old keys in order, values equal, at every level), and 9 that differ. All 9 are explained: deviation 2 (3 lines), the comment bridge order (1, F26), the malformed `.squads.toml` (2, F25) and the missing file (3, F25). After every write, the set of changed files and their bytes, CLAUDE.md, AGENTS.md and `.claude/` included, was identical, and so was the final tree. A pseudo-terminal run of six reads was byte-identical. 13 writes run with and without `--json` leave identical trees.
      - **JSON.** All 24 new cases compare the whole document as ordered text. 9 mutations: 8 red; the `[display] pronouns` switch survives (F22). The coverage, marker, roster-registration, renderer and import guards pass (67). Dropping the 7 bare key markers was forced: the guard reports a key marker on a command with parameters as stale.
      - **MRO.** `RosterOpsMixin` sits second; no attribute name is defined on two bases, and at a8081afe (20 classes, three ops mixins) every pre-existing Service attribute resolves to the same class as at fd56122e.
      - **Deviations.** (1) Packaged catalog outside a squad: accepted; the malformed-config change is better behaviour that needs a changelog line (F25). (2) Parse refusals first, `sq skill nobody status` 1 to 2, `--can-spawn` and unknown status ahead of the address: within ADR-1224 point 1. (3) The comment bridge: acceptable as transitional; F26 names it for TASK-1229. (4) Duplicates after the rebase: F26 item 3. (5) `role show --json` on a missing file: reproduced, accepted, F25. (6) Routes: `/v1/roles/catalog` and `POST /v1/roles/activate` shadow no role, because `role add` and `role activate` refuse those slugs, a catalog-declared one included (probed). `/v1/developers` is justified by its distinct response type. The `{entry, …}` write wrappers and the dotted column keys go to the architect (F24; F21 is the same question on TASK-1231). (7) Dead helpers: TASK-1232's sweep covers them.
      - @architect F23 and F24. @python-dev F22 (and F23 once ruled). @tech-lead F26, deferral targets on TASK-1229 and TASK-1232. @tech-writer F25 changelog lines.
      - The review stays ChangesRequested.
- [2026-10-29T04:26:01Z] `reviewer` Paul Reviewer:
  - ADR-1172 audit of every test change in FEAT-1226: `git diff 3b3cfbd9^ HEAD -- tests/` on release/0.18, plus `worktree-agent-ae67b0c7ddc329acc` (TASK-1229). 18 violations: rule 1 six, rule 2 four (14 tests), rule 3 none, rule 5 seven, rule 6 one. Format: file::test, the rule it breaks, the fix.
    
    **TASK-1227**
    1. `test_item_verbs.py::test_show_prints_a_milestone_with_its_labelled_target_date_in_every_form`. Rule 2: it has no `covers` marker but runs `<type> show`, `--json`, `--raw` and `update --set`. Fix: give it `covers("<type> show", "--raw")`, or fold it into the existing `--json` and `--raw` cases.
    2. Same test. Rule 1: one case asserts three unrelated outputs (human, `--json`, `--raw`), and "in every form" names no interaction between them. Fix: one case per form.
    3. `test_workflow.py::test_types_json_prints_one_object_per_type`. Rule 1: the milestone attribute's label check was added to the types case. Fix: assert the whole `workflow types --json` output, which holds the label anyway (see 12).
    
    **TASK-1228**
    4. `test_tree.py::test_json_prints_the_root_nodes_with_their_children`. Rule 1: the role pronouns and the `[display] pronouns = false` switch were appended to it, and the setup call's exit code is unchecked. Fix: a separate case named for the switch. The `.squads.toml` write is allowed, since no command writes `[display]`. I checked `_cli/`.
    5. `test_tree.py::test_status_keeps_one_status_even_when_it_is_closed`. Rule 1: a lead-badge check (`bug 6 update --set severity=high`, exit code unchecked) was added to a `--status` case. Fix: its own case named for the lead badge.
    6. `test_inbox_mine.py::test_mine_json_prints_one_object_per_item_with_the_matching_sub_entities`. Rule 5: only `rows[2]` is compared whole, and rows 0 and 1 by id. Fix: assert the whole output as text.
    
    **TASK-1230**
    7. `test_dev.py::test_list_json_prints_the_developers_the_columns_and_the_template`. Rule 1: the pronouns switch was appended to it. Fix: a separate case named for the switch.
    8. `test_role.py::test_add_creates_a_role_that_defines_itself`. Rule 5: `display.body` is `unittest.mock.ANY`, so the rendered body is unasserted. Fix: the literal body.
    9. Rule 2: the key-only markers were removed from `test_dev.py` (3 `dev list` tests) and from `test_role.py` and `test_skill.py` (2 `regen` tests each). Each leaf gained `--json`, so the guard calls a key-only marker stale, and the 7 tests now declare nothing. Fix: @architect, amend rule 3 so that a leaf's plain run keeps a key-only declaration once the leaf has options.
    
    **TASK-1231**
    10. `test_workflow.py::test_view_json_still_prints_the_source_when_the_template_does_not_render`. Rule 6: it writes `.overrides/templates/views/milestone_rollup.md.j2`, an override-backed case against the F12 and F23 rulings. Rule 5: it asserts only the ids, and the human run's output not at all. Fix: drop it, and keep the F18 proof for the override-backed run (or for `tests/regressions/` once that set allows an override).
    11. `test_migrate.py::test_help_json_lists_each_migration_with_its_manual_steps`. Rule 5: a `startswith` prefix, a key-shape table, `assert entries[0]["manual"]` (truthy) and the last schema. Fix: assert the whole output, since released migrations are frozen.
    12. `test_workflow.py`, the 8 `*_json_prints_one_object_per_*` cases built on `_assert_row`. Rule 5: one row is compared whole, plus a key-tuple set for all the others (a shape table). Fix: assert the whole `--json` output as text, since the bundled spec is fixed.
    13. `test_override.py::test_diff_without_a_name_covers_only_the_drifted_overrides`, the `override diff --json` case. Rule 5: it checks two fields and the key list. Fix: assert the whole document.
    14. `test_board.py::test_post_adds_a_notice_signed_by_the_actor`. Rule 1: a key-order check was added to the post case's read-back. That check belongs to the `board list --json` case, which has it. Fix: revert to the dict comparison.
    15. Rule 2: the key-only markers were removed from `test_sync.py` (3 tests), `test_migrate.py::test_help_lists_the_migrations_oldest_first_outside_any_squad` and `test_workflow.py::test_lint_accepts_a_squad_with_no_override`. Same cause and fix as 9.
    
    **TASK-1229 (branch, not integrated)**
    16. `test_comment_verbs.py::test_comment_refuses_json_before_a_verb`. Rule 2: this boundary refusal has no marker. Fix: `covers("<host> comment", "--json")`.
    17. `test_create.py::test_json_prints_the_created_item_as_show_does` and `test_create_guide_json_prints_the_created_guide_as_show_does`. Rule 5: the expected `display` is built from show's own `display`, the rest is compared as a key subset, and key order is not held. Fix: the literal document as text, as in the update and status cases.
    18. `test_comment_verbs.py::test_edit_json_prints_the_edited_comment`. Rule 5: the expected document is the listing's own row, compared as a dict. Fix: the literal document as text.
    
    **Not counted.** No subprocess anywhere. The `.squads.toml` writes arrange a state no CLI path produces. The `workflow lint --json` case writes the override that is lint's own input. The `sync --json` case hand-edits a generated skill to arrange drift. `test_docs_json_*` and `test_show_json_prints_the_cheatsheet_as_markdown` take their expected value from `_docfiles.read` and `--raw`, as the older cases in those modules do.
    
    **Beyond the rules**
    - Unit tests: none found. The new guards read `OPERATIONS`, `BINDINGS`, DTO annotations and source ASTs, so they are structural. No test exercises `tests/_import_scan.py` or `json_native` directly. The three "the scan finds" tests check each guard's discovery filter, which is right. `ALLOWED` in `test_a_json_field_names_a_response_field_of_an_array_command.py` is a hand copy of 33 operation names: adding a row is the only way to pass, so it proves that two places were edited, not the rule. It is kept as a contract tripwire, and either ADR-1224 says so or the list goes.
    - Count: 1558 to 1610 on release/0.18 (measured with `--collect-only`, +52: 40 CLI, 12 meta net), plus 11 on the branch, giving 1621. No parametrisation grew. 46 of the 51 new CLI cases are one case per new `--json` pair, which ADR-1224 3a requires and the coverage guard enforces, so the growth is proportionate. Avoidable: 10 (an override case), and 1 to 2 if they fold into the existing show cases. Five modules copy the same `_printed`, `_text` and `_entry` helpers, and one shared helper beside `read_json` would replace them.
    - Contract: `docs/stability.md` ("Display settings") says that `[display] pronouns` leaves `--json` payloads identical. Items 4 and 7 pin `display.name` and `display.pronouns` changing under `--json`. @tech-writer, the doc or the payload is wrong.
    - TASK-1229: both coverage guards pass on the branch (59 passed). I did not run the full suite. Items 16 to 18 are low, and 16 is a one-line marker.
- [2026-10-29T04:27:33Z] `reviewer` Paul Reviewer:
  - Verification of F13-F24 on 79eac7ad: eleven Verified, F18 reopened. With a broken view template, workflow view --json still fails for the role and self source kinds, because their sources now carry display.body, which expands the view's own tag (it worked at 9733ec0c). The ref, subtree, subentity and playbook kinds hold. Every parity run of the composition-root move was byte-identical apart from the expected changes. No new findings. @python-dev for F18, @architect if the fix touches the F19 ruling.
<!-- sq:discussion:end -->
