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
created_at: '2026-10-28T23:26:20Z'
updated_at: '2026-10-29T00:06:58Z'
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
<!-- sq:discussion:end -->
