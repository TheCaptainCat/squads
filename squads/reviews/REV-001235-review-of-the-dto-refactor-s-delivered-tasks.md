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
- TASK-1233
- TASK-1238
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
  status: Verified
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
  status: Noted
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
  status: Verified
  severity: low
- local_id: F28
  title: 'TASK-1228 tests: pronouns and lead-badge checks appended to tree cases;
    mine --json asserts one row'
  status: Verified
  severity: low
- local_id: F29
  title: 'TASK-1230 tests: pronouns switch appended to dev list --json, ANY in role
    add, seven tests left unmarked'
  status: Verified
  severity: low
- local_id: F30
  title: 'TASK-1231 tests: an override-backed view case against F12/F23, and shape
    or prefix asserts instead of whole output'
  status: Verified
  severity: medium
- local_id: F31
  title: 'TASK-1229 tests: an unmarked comment refusal, and create and edit --json
    checked against the CLI''s own output'
  status: Verified
  severity: low
- local_id: F32
  title: Comment and sub-entity not-found answer invalid (400), not not_found (404)
  status: Verified
  severity: medium
- local_id: F33
  title: The added comment is read back as the discussion's last comment
  status: Verified
  severity: low
- local_id: F34
  title: Remove without --yes refuses a bad address or --as after the prompt
  status: Noted
  severity: low
- local_id: F35
  title: The comment removal preview route is not in ADR-1225's grammar
  status: Noted
  severity: info
- local_id: F36
  title: Remove prompts and the comment preview print on stdout under --json
  status: Verified
  severity: low
- local_id: F37
  title: ref rm --json answers kind null though the removed kind is known
  status: Verified
  severity: info
- local_id: F38
  title: Refusals of a missing option checked in the command body declare an incidental
    parameter
  status: Verified
  severity: low
- local_id: F39
  title: TreeNode.slug is null on items and skills where list and show rows give the
    item's slug
  status: Verified
  severity: medium
- local_id: F40
  title: The three new TreeNode keys sit mid-object and are missing from the stability
    doc's tree table
  status: Verified
  severity: low
- local_id: F41
  title: TreeRequest.label has no sq tree flag, and dropping it passes the suite
  status: Verified
  severity: low
- local_id: F42
  title: The renderer guard lets _tui import _discussion, _badges, _spec_documents
    or any _cli module
  status: Verified
  severity: low
- local_id: F43
  title: The skill pronoun fix on tree --json is confirmed, and reverting it passes
    the suite
  status: Verified
  severity: info
- local_id: F44
  title: 'TUI parity: an @-prefixed assignee now matches, and a stale undeclared badge
    no longer sorts'
  status: Noted
  severity: info
- local_id: F45
  title: _tui/_filter.py copies the engine's closed category set
  status: Verified
  severity: info
- local_id: F46
  title: Repair-corridor guard no longer reaches the producers; adopt and migrate
    can drop unreadable
  status: Verified
  severity: medium
- local_id: F47
  title: Grant guard checks operations only; a CLI leaf with no call passes unseen
  status: Verified
  severity: low
- local_id: F48
  title: Working-language notice is lost on every refused call, not only the three
    listed
  status: Verified
  severity: low
- local_id: F49
  title: init prompts for role names on a mismatched squad before the gate refuses
  status: Verified
  severity: low
- local_id: F50
  title: 'Sweep leftovers: open_service and TARGET_DATE dead, docstrings name the
    deleted bridge'
  status: Verified
  severity: low
- local_id: F51
  title: New --json cases cover only empty reports; migration rows asserted by no
    case
  status: Verified
  severity: low
- local_id: F52
  title: Ladder modes share names with document choices of a different meaning
  status: Verified
  severity: info
- local_id: F53
  title: Write guard misses stdlib writers imported by name (from os import unlink)
  status: Verified
  severity: low
- local_id: F54
  title: Lazy type groups cache an override-built app across run() calls; leaks between
    squads
  status: Verified
  severity: medium
- local_id: F55
  title: SQUADS_SPANS=yes crashes every command; empty or 1 prints since-boot marks
  status: Verified
  severity: low
- local_id: F56
  title: Comments still say the root table is built at import time; _spans missing
    from CLAUDE.md
  status: Verified
  severity: low
- local_id: F57
  title: Lazy-group guard misses annotated and from-import Typer definitions
  status: Verified
  severity: low
- local_id: F58
  title: Releasing runbook does not run bench_local_mode.py as the task requires
  status: Verified
  severity: low
- local_id: F59
  title: 'Benchmark: fixed old-first order, repo-specific --task default, no-op SQUADS_DAEMON'
  status: Verified
  severity: info
- local_id: F60
  title: drop_type_apps is a src test hook over a module cache; a per-root type-app
    cache needs none
  status: Verified
  severity: low
- local_id: F61
  title: Stability Tier 5 says backends self-register on import; the registry is a
    literal table
  status: Verified
  severity: low
- local_id: F62
  title: Display keys documented as one shape; roster, statuses, sub-entity rows and
    show's summary differ
  status: Verified
  severity: medium
- local_id: F63
  title: 'CHANGELOG lead-badge entry: tree shows the next declared field''s badge,
    not none'
  status: Verified
  severity: low
- local_id: F64
  title: Provisional write fields list omits nothing_to_clear and view
  status: Verified
  severity: low
- local_id: F65
  title: CLAUDE.md lists RetypeOpsMixin second while claiming MRO order; it is fourth
  status: Verified
  severity: low
- local_id: F66
  title: CONTRIBUTING.md still describes registration side-effects and wiring commands
    onto app
  status: Verified
  severity: low
- local_id: F67
  title: Per-payload display table has no row for add-<kind>, which gains display
    {item, body_command}
  status: Verified
  severity: low
created_at: '2026-10-28T23:26:20Z'
updated_at: '2026-10-29T12:38:38Z'
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
- [2026-10-29T04:29:59Z, edited 2026-10-29T04:30:19Z] `architect` Robert Architect:
  - @python-dev Ruling: when the role and self sources expand the body, they skip the tag of the view being resolved. The source is the view's input, so it cannot contain that view's own output. Steps:
  - `show_item` and `show_role_entry` (or the body expansion they call) take an optional view name to leave unexpanded. The view source passes the view it resolves. That tag stays in `display.body` exactly as it is written in the stored body, and every other tag expands as `show` expands it. `show` and `role show` pass nothing and do not change.
  - This keeps the F19 promise. The source has the command's shape, key for key. Only the content of `display.body` differs, and that is a display-class value whose content is not frozen (ADR-1224 point 5), so neither ADR-1224 nor the stability text needs to change.
  - Tests, on the bundled spec with no template override (F12, F30): one case each for the role kind (`role_definition` on a bundled role) and the self kind (`greeting_skill` on the bundled skill). `--json` prints the source with the view's own tag left as written in `display.body`. Assert the whole document. Falsify once by passing no view name: the rendered text then appears in place of the tag. A broken-template case would need an override, so it waits for the override-backed run.
  - Out of scope here, for the reviewer to check: a host whose body holds a different view with a broken template still fails `show --json`, the same as the command does.
- [2026-10-29T04:34:57Z] `python-dev` Elias Python:
  - Fixed in 09c079e8 (on release/0.18 90e64424), per the architect ruling 6b98f7a. `expand_view_tags` takes `keep`, a view name whose tag is left exactly as written. `read_body`, `show_item` and `show_role_entry` take an optional `keep_view` that is passed through to it. The role and self view sources pass the view being resolved, so their `--json` no longer renders that view template. `show` and `role show` pass nothing and are unchanged.
  - New case on the bundled seeded squad, test_view_json_leaves_the_views_own_tag_unexpanded_in_its_source. It asserts the whole document: `role_definition` equals `sq role manager show --json` except `display.body`, which is the role_definition tag as written. `greeting_skill` equals `sq show <id> --json` plus `spec`, with the greeting_skill tag in `display.body`. Falsified: dropping `keep_view` from either source turns it red.
- [2026-10-29T05:37:20Z] `reviewer` Paul Reviewer:
  - - Verified on e6462b5e (fix in f81fd561), against its parent 361913e6.
    - Repro on a scratch squad with `views/role_definition.md.j2` and `views/greeting_skill.md.j2` overridden to `{{ nope.undefined_thing }}`. `workflow view role_definition ROLE-1 --json` and `workflow view greeting_skill SKILL-5 --json` exit 1 on the parent. Here they exit 0 and print the source, with `display.body` holding the view's own tag as written. Human mode still exits 1 with the render error.
    - On an unbroken squad, the role source equals `role reviewer show --json` key for key, `display.body` aside. The self source equals `show SKILL-5 --json` plus `spec`, again `display.body` aside.
    - `role manager show` (plain, `--json` and `--raw`), `role reviewer show --json`, `show ROLE-1 --json`, `show SKILL-5` (plain and `--json`) and `skill greeting show` (plain and `--json`) are byte-identical to the parent.
    - The architect's out-of-scope point holds as ruled. On a task carrying `greeting_skill` and a broken `memory_skill` tag, `workflow view greeting_skill TASK-21 --json` fails on `memory_skill`, exactly as `show TASK-21 --json` does.
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
- [2026-10-29T12:09:44Z] `tech-writer` Theo Writer:
  - CHANGELOG 0.18.0, Changed: "`sq role catalog` with a malformed `.squads.toml` fails." (exit 1 with the parse error, human and `--json`) and "`sq role <slug> show --json` fails when the role's item file is missing." (exit 1, `run sq repair`). Both checked on a scratch squad: dev 1, released 0.17.0 0.
- [2026-10-29T12:38:33Z] `manager` Catherine Manager:
  - Noted: the CHANGELOG 0.18.0 line quoted above landed in cf27bbc8.
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
- [2026-10-29T04:55:38Z] `reviewer` Paul Reviewer:
  - - Item 1 verified on 90e64424. `COMMENT_VERBS`, `_resolve_for_comments`, `_comment_target`, `resolve_agent_addr` and the `ctx.obj["id"]` lambdas have no hit left in src or tests. `_role.py`, `_skill.py` and `_operator.py` build their host through `roster_comments`. The refusal order is back to the parent's: `sq role nobody comment -m x` answers "--as is required: the actor's slug" (exit 1), as at fd56122e. Items 2 and 3 stay with TASK-1232.
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
- [2026-10-29T04:51:38Z] `python-dev` Elias Python:
  - Fixed in 80ddec81 (branch worktree-agent-a1374e50d83d80ba6, based on 09c079e8). The milestone case is now one marked case per form: `test_show_prints_a_declared_attribute_under_its_label` (`<type> show`), `test_show_json_lists_a_declared_attribute_with_its_label` (`--json`) and `test_show_raw_prints_a_declared_attribute_under_its_label` (`--raw`). Each one checks its setup exit codes. These could not be folded into the task show cases, because task declares no labelled attribute, so the forms need the milestone (net +2). `workflow types --json` asserts the whole document as text (`tests/cli/_bundled_documents.py`). Falsified: setting the label to the key in the attribute display DTO turns all three cases red, and swapping two keys in `TYPES` turns the types case red.
- [2026-10-29T05:07:42Z] `reviewer` Paul Reviewer:
  - Verified on 3e312c1c. The milestone case is split into human, --json and --raw cases, each marked, and workflow types --json asserts the whole document.
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
- [2026-10-29T04:51:47Z] `python-dev` Elias Python:
  - Fixed in 80ddec81. `tree --json`: the pronouns run is now two named cases, `test_json_shows_a_roles_pronouns_on_its_node` and `test_json_leaves_the_pronouns_out_when_the_display_setting_turns_them_off`, and both check their setup exit codes. `tree --status`: the lead badge has its own case, `test_a_node_leads_with_its_first_badge_field_when_a_second_is_set`, and the `--status` case checks only its own filter again. `mine --json` asserts the whole document as text. Falsified:
    - `shown_pronouns` ignoring `[display] pronouns` turns only the switch case red.
    - `shown_pronouns` returning `{}` turns the shown case red.
    - `lead_badge` taking the last badge turns the lead case red and leaves `--status` green.
    - A label change turns `mine --json` red.
- [2026-10-29T05:07:43Z] `reviewer` Paul Reviewer:
  - Verified on 3e312c1c. The pronouns cases and the lead-badge case are separate and named, each checks its setup exit code, and mine --json asserts the whole output. Falsified on a copy: ignoring [display] pronouns turns the tree switch case red, and leading with the last badge turns the lead-badge case red.
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
- [2026-10-29T04:29:16Z] `architect` Robert Architect:
  - @python-dev ADR-1172 rule 3 is amended (2026-10-29). Restore the deleted markers as `covers("<key>")` on each case that runs the command with none of its parameters (the plain-output cases of `dev list`, `regen`, `sync`, `migrate help`, `workflow lint` and the others), and keep `covers("<key>", "--json")` on the JSON cases. The coverage guard gains two checks: it fails on any `tests/cli/` test function without a marker, and the `invoke` fixture records `(key, None)` for a bare call on any leaf, not only a parameterless one. Falsify each check once (an unmarked test, and a key-only marker on a call that passes a flag). The rest of F29 (a separate switch case, a literal body instead of ANY) stands as the reviewer wrote it.
- [2026-10-29T04:51:48Z] `python-dev` Elias Python:
  - Fixed in 80ddec81.
    - `dev list --json`: the pronouns switch has its own case, `test_list_json_drops_the_pronouns_from_the_name_when_the_display_setting_turns_them_off`.
    - `role add`: `display.body` is the literal `SCOUT_BODY`.
    - Amended rule 3: every `tests/cli` test now carries a marker. 271 tests had none. That includes the seven named here, now key-only `dev list`, `role regen` and `skill regen`. The coverage guard fails on an unmarked test. It accepts a key-only marker on any leaf and calls it stale only on a key that is not a leaf. `reached_pairs` (the `invoke` fixture) records `(key, None)` only when a call passes none of its leaf's parameters.
    - Falsified: an unmarked probe test turns the guard red. `covers("<type> show")` on a call that passes `--raw` fails the `invoke` teardown. A `shown_pronouns`/`_shows_pronouns` that ignores the setting turns the switch case red. A one-word change turns the body case red.
- [2026-10-29T05:07:44Z] `reviewer` Paul Reviewer:
  - Verified on 3e312c1c. The dev list pronouns switch is its own case, and role add asserts a literal body. Every tests/cli test carries a marker (827 of 827). Falsified on a copy: returning True from _shows_pronouns turns the dev switch case red. Removing a marker fails the coverage guard: "unmarked test (every CLI test declares a covers marker)".
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
- [2026-10-29T04:29:18Z] `architect` Robert Architect:
  - @python-dev The marker gap for the five sync, migrate help and lint tests is ruled in ADR-1172 rule 3, amended 2026-10-29 (see F29): key-only `covers("<key>")` on the plain cases. The override-backed view template case goes, as in F12 and F23: assert the view's rendered output on the bundled template, and its override behaviour waits for the override-backed run. Whole-output asserts as the finding says.
- [2026-10-29T04:51:49Z] `python-dev` Elias Python:
  - Fixed in 80ddec81.
    - The override-backed view-template case is gone.
    - `migrate help --json`, the eight `workflow <listing> --json` cases and `override diff --json` assert the whole document as text. The workflow and migration documents are in `tests/cli/_bundled_documents.py`, and `_assert_row`, `_json`, `_one` and `_named` are deleted.
    - `board post` compares the read-back as a dict again.
    - The five sync, migrate help and lint tests carry key-only markers.
    - The view-source case from 09c079e8 asserts both sources (role and self) as literal documents. This pins the bundled spec digest, just as the catalog documents pin the spec.
    - Falsified: one mutation per document, and each case went red. Reverting the 09c079e8 source fix turns the view-source case red.
- [2026-10-29T05:07:45Z] `reviewer` Paul Reviewer:
  - Verified on 3e312c1c. The view-template override case is gone. migrate help --json, the eight workflow listings and override diff --json each assert the whole document (the listings and migrations against literal documents in tests/cli/_bundled_documents.py). The board post read-back is a plain comparison again, and the five tests are marked.
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
- [2026-10-29T04:51:51Z] `python-dev` Elias Python:
  - Fixed in 80ddec81. `test_comment_refuses_json_before_a_verb` carries `covers("<host> comment", "--json")`. Both `create --json` cases assert literal documents as text. They are renamed `test_json_prints_the_created_item` and `test_create_guide_json_prints_the_created_guide`, since they no longer compare with show. `comment edit --json` asserts the literal document as text. Falsified: a key swap in the task document, a wrong path in the guide document and a wrong previous body each turn their case red.
- [2026-10-29T04:55:37Z] `reviewer` Paul Reviewer:
  - - A fourth case of the same class on 90e64424: `test_comment_json_prints_the_added_comment` takes `hash` and `short_hash` from the listing, which is the CLI's own output. Under the frozen clock both are fixed values, so they can be literals. Fold it into this finding's fix. F33 also asks that case to add to a discussion that already holds a comment.
- [2026-10-29T05:07:46Z] `reviewer` Paul Reviewer:
  - Verified on 3e312c1c. The refusal before a verb is marked. Both create --json cases and the comment edit --json case assert literal documents as text.
<!-- sq:finding:F31:discussion:end -->
<!-- sq:finding:F31:end -->

<!-- sq:finding:F32 -->
### F32 — Comment and sub-entity not-found answer invalid (400), not not_found (404)

<!-- sq:finding:F32:body -->
ADR-1225 section 3 says a `comment remove` whose confirmed comment was edited or removed in between "answers `404 not_found` and removes nothing", and FEAT-1140 US2 relies on it. TASK-1229's test approach leaves that answer to "the error table's 404 row in TASK-1218's route tests". But the error table maps only `ItemNotFoundError` and `RoleNotFoundError` to `not_found`, and the comment lookup raises a bare `SquadsError`, so the wire type is `invalid` (400).

Reproduced on 90e64424 by wrapping `_calls.call` to print `error_type(exc)` for each failed call (a probe script, not a test):

| Command | Wire type |
|---|---|
| `task 21 comment <full hash of an edited comment> remove --as tech-lead --yes` | `invalid` |
| `task 21 comment ffff show` / `remove` | `invalid` |
| `task 21 subtask 9 update --title x` ("no subtask ST9 in TASK-21") | `invalid` |
| `task 21 subtask 9 comment -m x --as tech-lead` | `invalid` |
| `task 999 comment …`, `role nobody comment …`, `skill nope comment …` | `not_found` |

So a removed comment or sub-entity answers 400 over HTTP, and a route test written against an unknown item stays green.

Second, the text. After a preview, the remove call sends the full hash, so the refusal names 64 hex characters the user never typed: `error: no comment cbaab16914ce…6248 in TASK-21's discussion (edited or removed since it was read?)`. The preview showed none of that hash.

Fix: raise a not-found error class from `_discussion.resolve_hash`'s no-hit branch and from the sub-entity lookups, and map it to `not_found`. Its base (a new `NotFoundError`, or a subclass of `ItemNotFoundError`) is for @python-dev, with the error table's owner. Make the message name the displayed short hash. Local mode needs no new surface case, since exit 1 and the text are unchanged. The 404 belongs in TASK-1218's route tests, with a comment case beside the item case.
<!-- sq:finding:F32:body:end -->

#### Discussion

<!-- sq:finding:F32:discussion -->
- [2026-10-29T05:20:17Z] `python-dev` Elias Python:
  - Fixed in ed808d64: new CommentNotFoundError (resolve_hash, both no-hit branches) and SubentityNotFoundError (the sub-entity lookup, and a missing sub-entity discussion on comment add/locate), both mapped to not_found in _api/_errors.py. A full 64-char hash is named by its first 7 characters, as the preview shows it; a typed prefix is named as typed. Verified with r1229/errtype.py on a scratch squad: comment remove after an edit, comment ffff show/remove, subtask 9 update/show/comment all answer not_found; human text and exit 1 unchanged (parity run: 218 byte-identical). @reviewer
- [2026-10-29T05:26:32Z] `reviewer` Paul Reviewer:
  - - Verified on ed499a68 with `r1229/errtype.py`. These now answer `not_found` (`CommentNotFoundError` or `SubentityNotFoundError`): comment `ffff` show and remove, on an item and on a role; `subtask 9` update, show, body, remove and comment add; and `step 9` comment show. An unknown item still answers `not_found`, as before.
    - The edit-between run (`between.py`, with an edit injected after the preview) refuses with "no comment cbaab16 in TASK-21's discussion (edited or removed since it was read?)", exit 1, and the edited comment remains. The message names the 7-character prefix the preview row carries. It is always 7 characters, even when the discussion widens its displayed hashes on a collision, but that is still a valid prefix to type. Accepted.
<!-- sq:finding:F32:discussion:end -->
<!-- sq:finding:F32:end -->

<!-- sq:finding:F33 -->
### F33 — The added comment is read back as the discussion's last comment

<!-- sq:finding:F33:body -->
`_add_comment` (`_services/_item_write_ops.py`) writes the comment in one transaction (`self.comment`). Then it reads the discussion again and reports `comments[-1]` as the comment it added. Any comment appended between the two (a second `sq` process now, or a concurrent request once the daemon serves this route) is reported as `entry` in place of the caller's. `Service.comment` returns the `Item`, not the hash it wrote.

The surface case cannot see this. `test_comment_json_prints_the_added_comment` adds to an empty discussion, so `comments[0]` and `comments[-1]` are the same comment. Mutation on a copy of 90e64424: change `comments[-1]` to `comments[0]`, and test_comment_verbs plus the role, skill, operator and sub-entity modules give 333 passed. A known-positive mutation (`copies + 1`) turns 2 red, so the harness reaches the code.

Fix: have the write return the new comment's hash (it is computed inside `_comment_core` as the entry is formatted) and resolve `entry` by that hash. In the existing `--json` case, add to a discussion that already holds a comment, so the expected document tells the two apart.
<!-- sq:finding:F33:body:end -->

#### Discussion

<!-- sq:finding:F33:discussion -->
- [2026-10-29T05:20:19Z] `python-dev` Elias Python:
  - Fixed in ed808d64: Service.comment answers the hash it wrote (computed in _comment_core under the lock, the importer unpacks it), and the operation resolves entry by that hash. test_comment_json_prints_the_added_comment now adds to a discussion that already holds a comment; the comments[0] mutation turns it red. @reviewer
- [2026-10-29T05:26:35Z] `reviewer` Paul Reviewer:
  - - Verified on ed499a68. `_add_comment` resolves `entry` by the hash the write returns. The mutation "read back the discussion's first comment" turns `test_comment_json_prints_the_added_comment` red (1 failed), where at 90e64424 it survived with 333 passed.
    - Callers of the new return value: the operation uses the hash, and the importer unpacks `_comment_core`'s `(item, hash)`. The two fixture calls in `tests/cli/_readable.py` and the one in `tests/meta/test_an_item_file_is_written_once_per_unit_of_work.py` ignore the result, which is safe. No other caller exists in src, `_tui` or tests.
<!-- sq:finding:F33:discussion:end -->
<!-- sq:finding:F33:end -->

<!-- sq:finding:F34 -->
### F34 — Remove without --yes refuses a bad address or --as after the prompt

<!-- sq:finding:F34:body -->
Dev deviation 2. `<type> <n> remove` and `<kind> <k> remove` without `--yes` now ask before the call. So an unknown item, a wrong-type address or an unknown `--as` is refused only after the user answers y, and the prompt can name an id that does not exist:

| Command (stdin `y`) | d9916956 | 90e64424 |
|---|---|---|
| `task 999 remove` | refused, no prompt | `Remove TASK-999? …` then the same refusal |
| `bug 21 remove` (21 is a task) | `21 is TASK-21 (task), not a bug`, no prompt | `Remove BUG-21? …` then the refusal |
| `task 28 remove --as nobody` | `unknown slug 'nobody'…`, no prompt | prompt, then the refusal |
| `task 21 subtask 1 remove --as nobody` | refused, no prompt | prompt, then the refusal |
| `task 21 subtask 9 remove` | prompt, then refused | unchanged |

Exit codes and error text are unchanged, nothing is removed, and with `--yes` nothing changes.

Against ADR-1224 point 1, this is what the ADR rules. Group callbacks only parse, and "neither the item removal nor the sub-entity removal prompt shows squad data, so each still makes one call". A preview read before the prompt, as `comment remove` makes, would need an amendment. Read as written, the ADR leaves no room for it. One premise is wrong, though: Context 7 says item removal and sub-entity removal "ask before reading anything". Before this change, the item callback resolved the address and `apply_edit_actor` checked `--as` before the prompt, so the refusals above came first.

Recommendation: keep one call. The cost is one keystroke on a command that removes nothing. A pre-read would add a round trip to every interactive removal in remote mode, and it would still not check `--as` unless it were a write-scoped preview. @architect: correct Context 7 and confirm. @tech-writer: one changelog line ("`remove` without `--yes` asks before checking the address and `--as`; a bad one is refused after the answer").
<!-- sq:finding:F34:body:end -->

#### Discussion

<!-- sq:finding:F34:discussion -->
- [2026-10-29T04:58:59Z] `architect` Robert Architect:
  - @python-dev Confirmed: one call (ADR-1224 point 1, with Context 7 corrected 2026-10-29). Keep the current flow, no code change. @tech-writer, changelog line: "`remove` without `--yes` asks before checking the address and `--as`, so a bad one is refused after the answer".
- [2026-10-29T05:26:56Z] `reviewer` Paul Reviewer:
  - Noted: one call is confirmed and Context 7 is corrected (architect 5977790). The changelog line is with @tech-writer on TASK-1234.
<!-- sq:finding:F34:discussion:end -->
<!-- sq:finding:F34:end -->

<!-- sq:finding:F35 -->
### F35 — The comment removal preview route is not in ADR-1225's grammar

<!-- sq:finding:F35:body -->
Dev deviation 4. The preview that `comment remove` makes without `--yes` is served at `GET …/comments/{hash}/removal`, five times over: items, sub-entities, and roles, skills and operators. ADR-1225 section 1 has no such form. A `GET` on `…/comments[/{hash}]` is `show`, and a sub-resource named after an action is a `POST` (`…/status`, `…/retype`). Section 3 says only that "the preview returns the full hash with the comments it addresses".

The preview is not `show`. It returns the whole duplicate group (`CommentSelection`) and refuses an actor who is not the author before the prompt (`find_comment(..., as_slug=…)`), and `show` does neither. As a read, it is rightly a `GET`. So a separate operation is justified, and only its path is unruled.

@architect: add the row to the section 1 table, or name the path. I see no defect either way. No client depends on it before MILE-868.
<!-- sq:finding:F35:body:end -->

#### Discussion

<!-- sq:finding:F35:discussion -->
- [2026-10-29T04:59:00Z] `architect` Robert Architect:
  - @python-dev Path ruled as you built it: `GET …/comments/{hash}/removal`, now in ADR-1225 section 1 for items, sub-entities and roster entries. No change.
- [2026-10-29T05:26:53Z] `reviewer` Paul Reviewer:
  - Noted: the path is ruled as built (ADR-1225 section 1, architect d17a310), so no code change.
<!-- sq:finding:F35:discussion:end -->
<!-- sq:finding:F35:end -->

<!-- sq:finding:F36 -->
### F36 — Remove prompts and the comment preview print on stdout under --json

<!-- sq:finding:F36:body -->
ADR-1224 point 3a, Prompts: "`--json` never puts a prompt on stdout." The three prompts this task moved all do when `--json` is given without `--yes`. Each prints the prompt text to stdout before the document, and `comment remove` also prints its preview listing there:

```
$ echo y | sq task 21 subtask 2 remove --json 2>/dev/null
Remove subtask ST2 from TASK-21? This cannot be undone. [y/N]: {
  "removed": "subtask ST2",
  "item": "TASK-21"
}
$ echo y | sq task 21 comment 2390 remove --as reviewer --json 2>/dev/null
2026-10-29T02:11:00Z reviewer: - Ack
Remove this comment? [y/N]: [
```

The parent commit prints the same text, so this is not a regression. But the ADR rule is stated for these commands, and this task is the increment that implements them, so it is open now. A `… --json | jq` in a script fails to parse.

Fix: under `--json`, print the preview and the prompt on stderr (`typer.confirm(..., err=True)`, and the preview through `err_console`). Alternatively, refuse `--json` without `--yes` as a usage error. @python-dev, unless @architect prefers the refusal. The surface case for the item, the sub-entity and the comment removal is one `--json` run, answering y on stdin, whose stdout parses as the whole document.
<!-- sq:finding:F36:body:end -->

#### Discussion

<!-- sq:finding:F36:discussion -->
- [2026-10-29T04:59:02Z] `architect` Robert Architect:
  - @python-dev Ruling: stderr, not a refusal (ADR-1224 point 3a, amended). Under `--json`, the item, sub-entity and comment removal prompts use `typer.confirm(..., err=True)`, and `comment remove` prints its preview through `err_console`. Human mode stays as it is. Add one surface case per removal, covering the item, the sub-entity and the comment: `--json` without `--yes`, `y` on stdin, and stdout asserted as the whole document. Falsify once with the prompt back on stdout. @tech-writer, changelog line: "under `--json`, removal prompts and the comment removal preview go to stderr".
- [2026-10-29T05:20:22Z] `python-dev` Elias Python:
  - Fixed in ed808d64 per the ruling: under --json the item, sub-entity and comment removal prompts use err=True and the comment preview prints through err_console; human mode unchanged. Three cases (one per removal) assert the whole stdout document and the prompt on stderr; each red with the prompt (or the preview) back on stdout. The in-process runner echoes the typed answer on its stdout, so the cases expect that echo before the document; a real pipe (echo y | sq ... --json 2>/dev/null) prints the document alone. @reviewer
- [2026-10-29T05:26:42Z] `reviewer` Paul Reviewer:
  - - Reopened on ed499a68. The prompts and the preview now go to stderr, and the three mutations (prompts back on stdout, preview back on stdout) turn the three cases red. One byte of the prompt still reaches stdout, though. Click's `confirm(err=True)` writes the prompt to stderr and then reads the answer with `input(" ")`, which writes a space to stdout.
    - Real pipe, `echo y | sq task 21 subtask 2 remove --json 2>/dev/null | od -An -tx1`: `20 7b 0a …`, which is a space and then the document. When the call is refused after the answer (`echo y | sq task 24 remove --json`, where 24 is an incident), stdout is the single byte `20` instead of empty. `jq` and `json.loads` accept the leading space. A consumer that checks for empty stdout on failure, or compares the document byte for byte, does not. So the statement that a real pipe prints the document alone is off by that byte.
    - The tests: the `" y\n"` expected before the document is that real space plus the in-process runner echoing the typed `y`, which no user sees. Under ADR-1172 rule 5 the case should assert what the user sees, which is the document alone. It currently asserts a runner artifact and pins the stray byte as correct.
    - Fix (@python-dev): under `--json`, print the prompt through `err_console` and read the answer from stdin without Click's `input(" ")`. Then stdout is exactly the document, or empty on a refusal, and the runner echo disappears with it. The three cases then assert `result.stdout == document`, and the prompt text on stderr.
- [2026-10-29T05:31:47Z] `python-dev` Elias Python:
  - Fixed again: under --json the removal prompts no longer go through Click; common.confirm prints the prompt on stderr through err_console and reads the answer with sys.stdin.readline, so nothing reaches stdout. Real pipe (echo y | sq ... --json 2>err): stdout starts 7b/5b, and is empty (size 0) when the call is refused after the answer. The three cases now assert result.stdout == the document alone and the prompt on stderr; reading stdin directly means the in-process runner echoes nothing. Each case is red with Click's confirm(err=True) back. @reviewer
- [2026-10-29T05:37:18Z] `reviewer` Paul Reviewer:
  - - Verified on e6462b5e (fix in e6891723). Real pipe with `f36probe.sh`: item, sub-entity and comment `remove --json`, answered `y`, print exactly the document on stdout (first byte `{` or `[`). The prompt and the comment preview go to stderr. A refused or aborted call leaves stdout empty, where it used to hold one stray byte.
    - Answer handling matches Click's in human mode: y, Y, yes, YES and " y " confirm; empty, n and EOF abort (exit 1, "Aborted."); "x" re-asks with "Error: invalid input". Human mode is unchanged.
    - Mutations: the prompt back on stdout, or Click's `confirm(err=True)` restored, each turn the three cases red (3 failed). They now assert `stdout == document`, which is what the user sees (ADR-1172 rule 5).
<!-- sq:finding:F36:discussion:end -->
<!-- sq:finding:F36:end -->

<!-- sq:finding:F37 -->
### F37 — ref rm --json answers kind null though the removed kind is known

<!-- sq:finding:F37:body -->
`ref rm --json` answers `{entry, target, kind: null}`. `kind` is the outcome field ADR-1224 point 3a names for both `ref add` and `ref rm`, yet `rm` never fills it, although it knows the kind it removed. Run on the scratch squad: `task 21 ref rm INC-24 --json` removed `INC-24:caused-by` and printed `"kind": null`. The DTO documents the field as "for an added ref, its kind".

The shape is provisional until MILE-868, so nothing breaks today. A client that shows "removed TASK-21 → INC-24 (caused by)" has to diff `entry.refs` against an earlier read to learn the kind. Recommend filling `kind` with the removed ref's kind (`rm_ref` removes every ref to the target, so a list if several can coexist). Otherwise, document that `kind` is always null on `rm`. @architect for the shape, then @python-dev.
<!-- sq:finding:F37:body:end -->

#### Discussion

<!-- sq:finding:F37:discussion -->
- [2026-10-29T04:59:03Z] `architect` Robert Architect:
  - @python-dev Ruling (ADR-1224 point 3a, amended): `ref rm --json` answers `{entry, target, kinds}`, where `kinds` lists the kind of each ref it removed, in stored order and as `refs --json` reports it. It is never null and holds one entry in the usual case. `ref add` keeps `kind`. Give the two verbs their own response DTOs, and correct the `kind` docstring. Update the `ref rm --json` expectation and falsify once with an empty `kinds`.
- [2026-10-29T05:20:25Z] `python-dev` Elias Python:
  - Fixed in ed808d64 per the ruling: ref add answers ItemRefAdded {entry, target, kind}, ref rm answers ItemRefRemoved {entry, target, kinds} with the kind of each removed ref in stored order (bare refs as the default kind, as refs --json reports them). Expectation updated; red with an empty kinds. @reviewer
- [2026-10-29T05:26:37Z] `reviewer` Paul Reviewer:
  - - Verified on ed499a68. `ref rm --json` answers `{entry, target, kinds}`. The mutation that drops each `kinds.append` (empty `kinds`) turns `test_ref_rm_json_prints_the_items_row_without_the_ref` red (1 failed).
<!-- sq:finding:F37:discussion:end -->
<!-- sq:finding:F37:end -->

<!-- sq:finding:F38 -->
### F38 — Refusals of a missing option checked in the command body declare an incidental parameter

<!-- sq:finding:F38:body -->
The dev's caveat is a hole. A refusal that our own code raises for a missing option cannot declare the parameter it refuses, so these cases name whatever parameter they had to pass. The ruling that a refusal declares the parameter it refuses is unmet for them, and the guard stays green.

`reached_pairs` (`tests/_cli_surface.py`) records a parameter in two cases: the call gives it a value, or `_missing` predicts that Click's own missing-parameter error names it. A check in the command body (`require_as`, a template's `pass --tech`, `role add`'s "missing required fields") is invisible to it. Probed with the fixture on 3e312c1c: `board post` records only `("board post", None)`, and `dev add` records only `("dev add", None)`.

Cases that declare an incidental parameter:
- `test_board.py::test_post_as_is_required` refuses a missing `--as` but declares `--message`.
- `test_board.py::test_post_needs_a_message_or_a_file` refuses a missing `-m`/`--file` but declares `--as`.
- In `test_comment_verbs.py`:
  - `test_comment_refuses_a_call_with_no_author` declares `--message`.
  - `test_comment_refuses_a_call_with_no_text` declares `--as`.
  - `test_edit_refuses_a_call_with_no_author` declares `--message`.
  - `test_edit_refuses_a_call_with_no_text` declares `--as`.
  - `test_remove_refuses_a_call_with_no_author` declares `--yes`.
- `test_init.py::test_force_is_required_to_start_over_a_configured_directory` refuses a missing `--force` but declares `--roles`.
- `test_role.py::test_add_names_every_required_field_it_is_missing` and `test_add_names_the_one_field_it_is_missing` refuse missing `--name`, `--job-title` and `--mission` but declare `SLUG`.

This is not false coverage: each refused parameter has an effect case of its own. But the marker no longer says which refusal a parameter has, so op-pierre's ruling that every parameter gets a refusal case cannot be audited from the markers.

Suggested fix (@architect for the rule, then @python-dev): on a call that exits non-zero, the fixture also records a parameter whose flag appears in the error line. Or add a `refuses=` argument to the marker, checked against the output. Then re-mark the 10 cases.
<!-- sq:finding:F38:body:end -->

#### Discussion

<!-- sq:finding:F38:discussion -->
- [2026-10-29T05:08:57Z] `architect` Robert Architect:
  - @python-dev Ruling: the first option, with no new marker syntax (ADR-1172 rule 3, amended 2026-10-29). On a call that exits non-zero, `reached_pairs` also records each parameter of the leaf that has one of its flags (any of its opts, short or long) in the output. Re-mark the 10 cases with the parameter they refuse: `--as`, `--message` for `-m`/`--file`, `--force`, and `--name`/`--job-title`/`--mission` for `role add`, one marker each where the message names several.
  - If a refusal's message does not name its flag, that message is the defect: name the flag in it, so the user sees it too.
  - Falsify once: a refusal case marked with a flag that its message does not name goes red at teardown.
- [2026-10-29T05:13:49Z] `python-dev` Elias Python:
  - Fixed in 3ceaa761, on 49bbfda1.
    - `reached_pairs` takes the output of a call that exited non-zero, and `invoke` passes it. It records each option, of the command the call ended on, that has one of its flags (short or long, matched as a whole token) in that output. A group the call ends on counts too, for `<host> comment -m x`.
    - The 10 cases are re-marked:
      - `board post`: `--as` and `--message`.
      - The five comment refusals: `--as` or `--message`.
      - `init`: `--force`.
      - `role add`: `--name`, `--job-title`, `--desc` and `--mission` on the every-field case, and `--mission` on the one-field case.
    - No `src` change: every one of these refusals already names its flag in its message.
    - Falsified:
      - `covers("<host> comment", "--file")` on the no-author refusal fails at teardown.
      - Without the output check, all 10 re-marked cases fail.
      - A new meta case pins the flag boundary: dropping the lookahead lets `--as` match inside `--as-slug`.
- [2026-10-29T05:26:40Z] `reviewer` Paul Reviewer:
  - - Verified on ed499a68 (from b10c9957). With `_named` returning nothing, the 10 re-marked cases error at teardown (191 passed, 10 errors). Marking `test_comment_refuses_a_call_with_no_author` with `--file` instead of `--as` errors at teardown (1 error).
    - A residual blind spot, noted and not reopened: the guard credits every flag a refusal mentions, including one it only suggests as the remedy. `reached_pairs` for `task 3 update --parent ""` with the message "use --no-parent to clear the parent" records `--no-parent`. For `--priority x --no-priority` it records both. So a marker naming the suggested flag would pass on a case that never exercises it. No current case does this; I checked the three refusal messages that name another option. If @architect wants it closed, the rule can require that a credited flag also appears in the call's own arguments or in Click's missing-parameter set. Otherwise the review has to catch it.
<!-- sq:finding:F38:discussion:end -->
<!-- sq:finding:F38:end -->

<!-- sq:finding:F39 -->
### F39 — TreeNode.slug is null on items and skills where list and show rows give the item's slug

<!-- sq:finding:F39:body -->
`TreeNode.slug` reuses the item row's key name with another meaning. On `sq list --json` and `sq <type> <n> show --json`, `slug` is the item's own slug, on every item. On `sq tree --json` and the subtree view source it is now `null` on every work and record item and on every skill, and set only on roles and operators. Tier 3 freezes a key's meaning, so 0.18 would freeze two meanings for one name across sibling documents.

Repro on a scratch squad at 611c505e (FEAT-20 "Refunds", SKILL-43 with slug `manager`):

- `sq list -a --json`: FEAT-20 `slug` = `refunds`, TASK-41 `zeta-closed-task-x`, SKILL-43 `manager`, ROLE-1 `manager`.
- `sq task 41 show --json`: `slug` = `zeta-closed-task-x`.
- `sq tree -a --json`: FEAT-20, TASK-41 and SKILL-43 `slug` = `null`; ROLE-1 `manager`.

What the TUI needs is "which notebook this node opens", not the slug. Two ways out, for @architect:

1. Name the key for what it holds (for example `notebook`: the memory notebook's slug, `null` on items that have none).
2. Carry the item's slug unchanged, as the rows do, and let the TUI tell a role or operator from a skill some other way. The type catalog does not say today which types have a notebook, so this one needs a catalog field.

Option 1 is the smaller change: one key renamed, and the two `tests/cli` expectations that pin it.
<!-- sq:finding:F39:body:end -->

#### Discussion

<!-- sq:finding:F39:discussion -->
- [2026-10-29T06:09:14Z] `architect` Robert Architect:
  - @python-dev Ruling: option 1 (ADR-1224 point 3, amended 2026-10-29). Rename `TreeNode.slug` to `notebook`: the slug of the memory notebook the node opens, set on roles and operators and `null` elsewhere. Update the TUI's reads, the two `tests/cli` expectations and the subtree view source. Falsify once by filling it on a skill.
- [2026-10-29T06:18:03Z] `python-dev` Elias Python:
  - - Fixed in 33fc48de. `TreeNode.slug` is renamed `notebook`: the role's or operator's notebook slug, `null` on every other node. The rename covers the DTO, the builder, the TUI reads and the tree and workflow expectations. Falsified: filling `notebook` on every node (`notebook = it.slug or None`) turns the new skill-sharing-slug `tree --json` case red.
- [2026-10-29T10:08:57Z] `reviewer` Paul Reviewer:
  - Verified on 06b8982c (e0a97f6d). On my scratch squad, `tree -a --json` puts `notebook` = `manager` on ROLE-1 and `op-ann` on OP-17, and `null` on FEAT-20, TASK-41, INC-36, SKILL-42 and SKILL-43. No node carries `slug` any more. `list -a --json` still gives each item's own slug (`refunds`, `zeta-closed-task-x`, `manager`), so the name now has one meaning. Mutation `notebook = it.slug or None`: 3 cases go red (two in tree, one in workflow view).
<!-- sq:finding:F39:discussion:end -->
<!-- sq:finding:F39:end -->

<!-- sq:finding:F40 -->
### F40 — The three new TreeNode keys sit mid-object and are missing from the stability doc's tree table

<!-- sq:finding:F40:body -->
The three new `TreeNode` keys are not appended at the end. They sit between keys that already existed: `slug` after `title`, `closed` after `blocked`, and `updated_at` after `anchor`. `docs/stability.md` lists the tree's fields "in emitted order" (Tier 3, "Search, tree and graph") and lists none of the three. The subtree view source (`workflow view --json`) has the same node shape.

Repro: `sq tree -a --json` at 611c505e prints node keys in this order: `id, type, title, slug, status, priority, assignee, blocked, closed, badges, anchor, updated_at, children, display`. At 658ed963 the order was `id, type, title, status, priority, assignee, blocked, badges, anchor, children, display`.

No value changed, and the order of the old keys among themselves is kept. The handback calls these keys "appended". In this review "appended" has meant placed after the last existing key, and that is the rule the parity checks applied to TASK-1227 through TASK-1231.

- @architect: rule whether additive DTO keys must go after the last key (here after `display`), or whether this interleaving is acceptable.
- @tech-writer: the stability doc's tree table needs `slug` (or its renamed form, see F39), `closed` and `updated_at`, with their classes. The changelog needs a line for the three new keys on `tree --json` and the subtree view source.

Answers to the review brief:
- `updated_at` is not a duplicate: no field of the node carried it before. Its format matches the list row's, because both serialise through the same pydantic path; the values are equal for the same item.
- `closed` is not a duplicate on the node either: `display.dimmed` means path-only, and `display.status.intent` is a colour. It could be derived by joining `workflow statuses` (status to role) with `workflow roles` (`hidden`), which is the join the stability doc tells readers to make. Keeping it on the node is a convenience, not redundant state.
<!-- sq:finding:F40:body:end -->

#### Discussion

<!-- sq:finding:F40:discussion -->
- [2026-10-29T06:09:16Z] `architect` Robert Architect:
  - @python-dev Ruling (ADR-1224 point 3, amended 2026-10-29): an added key goes after the last key its object already emits. Move `notebook` (F39), `closed` and `updated_at` after `display`, in that order, on the tree node and the subtree view source, so the node order is `id, type, title, status, priority, assignee, blocked, badges, anchor, children, display, notebook, closed, updated_at`. Assert the whole `tree --json` document as text so that the order is held.
  - @tech-writer: the stability doc's tree table gains `notebook` (an id-like slug or `null`), `closed` (boolean: the status's role is hidden) and `updated_at` (ISO timestamp, the same as the list row's), listed after `display`. Add the general rule that new keys are appended at the end of their object. Changelog: the three keys on `tree --json` and on the subtree view source.
- [2026-10-29T06:18:04Z] `python-dev` Elias Python:
  - - Fixed in 33fc48de. `notebook`, `closed` and `updated_at` now come after `display`, in that order, on the tree node and on the subtree view source. The `tree --json` cases and the `workflow view --json` case compare the whole document as text, so the order is pinned.
- [2026-10-29T10:08:59Z] `reviewer` Paul Reviewer:
  - Verified on 06b8982c for the code. Every node of `tree -a --json` on my scratch squad has the keys `id, type, title, status, priority, assignee, blocked, badges, anchor, children, display, notebook, closed, updated_at`, a single shape. The first eleven are the 658ed963 order unchanged, and the three new keys come last, as ruled. The tree and workflow view cases compare the whole document as text. The doc part of the ruling is not in this commit: `docs/stability.md` has no `notebook` row and no append rule, and TASK-1234's body does not name them. That is carried as a comment on TASK-1234.
<!-- sq:finding:F40:discussion:end -->
<!-- sq:finding:F40:end -->

<!-- sq:finding:F41 -->
### F41 — TreeRequest.label has no sq tree flag, and dropping it passes the suite

<!-- sq:finding:F41:body -->
`TreeRequest.label` has no CLI path. `sq list` has `--label` and `sq tree` does not, so only the TUI's filter screen reaches the field. Nothing in the surface suite exercises it.

Mutation, on a copy of 611c505e: in `_item_read_ops.py`, `label=req.label` becomes `label=None`. Then `tests/cli/test_tree.py`, `test_workflow.py` and `test_list.py` pass (89 passed, `-n 2`). The label filter works today: my headless run gives an identical tree on 658ed963 and 611c505e for `label=nope`. But this run is the only evidence for it.

Recommendation, for @architect: `sq tree` gains `--label` (`help="Show only items carrying this label."`, as on `sq list`), with one `covers("tree", "--label")` case asserting the whole output. The arguments for it:

- ADR-1224 point 7 says the tree request "takes the same filter fields as `sq tree`". A field with no CLI flag breaks that statement in the other direction.
- `list` and `tree` would filter alike.
- ADR-1172 tests only through the CLI surface, so an API-only field stays untested until the HTTP surface has its own suite.

The alternative is to keep the field API-only, and then point 7's wording should say so.
<!-- sq:finding:F41:body:end -->

#### Discussion

<!-- sq:finding:F41:discussion -->
- [2026-10-29T06:09:17Z] `architect` Robert Architect:
  - @python-dev Ruling: add `sq tree --label` (help "Show only items carrying this label.", as on `sq list`), mapped to `TreeRequest.label`, with one `covers("tree", "--label")` case asserting the whole output. Falsify once with `label=None` in the operation, the reviewer's mutation. ADR-1224 point 7 already says the tree request takes `sq tree`'s filter fields, so it needs no amendment. @tech-writer: changelog line for the new flag.
- [2026-10-29T06:18:05Z] `python-dev` Elias Python:
  - - Fixed in 33fc48de. `sq tree --label` is added ("Show only items carrying this label."), mapped to `TreeRequest.label`, with one `covers("tree", "--label")` case that asserts the whole output. Falsified with your mutation (`label=None` in the operation): the case goes red.
- [2026-10-29T10:09:01Z] `reviewer` Paul Reviewer:
  - Verified on 06b8982c. `sq tree --label nope` draws TASK-22 and TASK-30, and `--json` gives the same ids. `sq list --label nope --json` gives the same ids. An unused label prints `no items` (exit 0). Mutation `label=None` in the operation: `test_label_keeps_the_items_carrying_it` goes red. The changelog line for the flag is still owed (TASK-1234).
<!-- sq:finding:F41:discussion:end -->
<!-- sq:finding:F41:end -->

<!-- sq:finding:F42 -->
### F42 — The renderer guard lets _tui import _discussion, _badges, _spec_documents or any _cli module

<!-- sq:finding:F42:body -->
The renderer guard reads direct imports only. For `_tui`, three kinds of import pass it even though they reach the forbidden set:

- `squads._discussion`, which imports `_paths`, `_models._config` and `_workflow`;
- `squads._badges` and `squads._spec_documents`, which import `_workflow`;
- any `squads._cli.*` module outside `_calls`, `_common` and the pending modules. Importing one runs `squads._cli/__init__`, which loads every command and `_services`.

Repro: on a copy of 611c505e, append one import to `_tui/_board.py`, then run `test_no_renderer_imports_the_vocabulary_or_the_configuration`. These pass the guard: `from squads import _badges`, `from squads._discussion import split_discussion`, `from squads._spec_documents import resolve_documents`, `from squads._cli._render._roster import _name`. These fail it: `_cli._common`, `_cli._calls`, `_services._service`. At runtime, importing each module that passes and listing `sys.modules` shows what it loads. `_discussion` brings in `_paths`, `_models._config` and `_workflow`. `_badges` and `_spec_documents` bring in `_workflow`. `_cli._render._roster` brings in `_services`, `_paths`, `_models._config` and `_workflow`.

Another guard covers part of this. With `from squads._discussion import split_discussion` appended, `test_the_tree_imports_exactly_the_recorded_edges` goes red (the unmutated control passes). So a new `_tui -> _discussion` edge needs a table row that a reviewer sees. But a `_tui -> _cli` edge would be one row, and the row says nothing about why the edge is forbidden.

What holds today: `import squads._tui._app` loads none of `_services`, `_workflow`, `_paths`, `_models._config` or `_cli`, checked through `sys.modules`. So the claim in the handback is true. It is just not guarded.

Suggested fix (@python-dev): for `_tui`, forbid `squads._cli` whole. Then either follow the import closure (`imports_of` over each module the scan reaches, skipping `TYPE_CHECKING` blocks) or add `_discussion`, `_badges`, `_spec_documents`, `_board._store` and `_memory._store` to the list. The guard's docstring should say which of the two it does.
<!-- sq:finding:F42:body:end -->

#### Discussion

<!-- sq:finding:F42:discussion -->
- [2026-10-29T06:18:06Z] `python-dev` Elias Python:
  - - Fixed in 33fc48de. A second guard test follows each `_tui` module's import closure and forbids the renderer set plus `squads._cli` as a whole.
    - The closure takes in every import outside `TYPE_CHECKING` blocks, function-level ones included, plus each package `__init__`. `tests/_import_scan.py` gained `typing=False` to skip those blocks.
    - Check: the static closure of `_tui/_app.py` equals what importing it puts in `sys.modules` at runtime (43 modules).
    - Your probe, one import at a time in `_tui/_board.py`: `_badges`, `_discussion`, `_spec_documents`, `_cli._render._roster`, `_cli._common`, `_cli._calls`, `_services._service`, `_board._store` and `_memory._store` each turn it red. The control, `_clock`, stays green.
- [2026-10-29T10:09:03Z] `reviewer` Paul Reviewer:
  - Verified on 06b8982c. The control (tree, workflow and 3 meta modules) gives 106 passed. In a copy, `test_the_terminal_ui_loads_neither_the_vocabulary_nor_the_cli` goes red for each of these:
    - one import appended to `_tui/_board.py`: `_badges`, `_discussion`, `_spec_documents`, `_cli._render._roster` or `_board._store`;
    - a function-level `_discussion` import;
    - a `_workflow` import added to `_api/_dto/_tree.py`, which the TUI loads, so the closure is truly transitive;
    - a literal `importlib.import_module("squads._services._service")` in `_api/_dto/_memory.py`.
    
    An `_clock` import stays green. A `TYPE_CHECKING`-only `_services` import in `_tui` is skipped by the closure and caught by the direct test.
<!-- sq:finding:F42:discussion:end -->
<!-- sq:finding:F42:end -->

<!-- sq:finding:F43 -->
### F43 — The skill pronoun fix on tree --json is confirmed, and reverting it passes the suite

<!-- sq:finding:F43:body -->
The pronoun fix is real, and nothing pins it.

Before (658ed963): `tree_node` looked up pronouns by `it.slug` on every item. A skill whose slug matches a role's took that role's pronouns on `sq tree --json` and on the subtree view source. Repro on a scratch squad: `sq skill add manager`, with `manager` at she/her. At 658ed963, `tree --json` gives SKILL-43 `display.pronouns` = `she/her`. At 611c505e it gives `null`. ROLE-1 and OP-17 are unchanged. The TUI was never affected: it already gated on role and operator. The human `sq tree` shows no pronouns at all.

Mutation, on a copy of 611c505e: put back `pronouns=pronouns.get(it.slug) if it.slug else None`. Then `tests/cli/test_tree.py`, `test_workflow.py`, `test_role.py` and `test_skill.py` pass (247 passed).

ADR-1172 sends a verified bug to `tests/regressions/`, which is later work. So this is a regression-set candidate (a skill sharing a role's slug carries no pronouns on `tree --json`), plus a changelog line for the fix (@tech-writer).
<!-- sq:finding:F43:body:end -->

#### Discussion

<!-- sq:finding:F43:discussion -->
- [2026-10-29T06:18:07Z] `python-dev` Elias Python:
  - - Fixed in 33fc48de. The bundled squad can express it (`sq skill add Manager` gives the slug `manager`), so a `tree --json` case on the bundled spec pins it. With `manager` at she/her, the skill node carries `notebook: null` and `pronouns: null`, and the case compares the whole document as text. Falsified: restoring the old `pronouns.get(it.slug)` lookup turns it red.
- [2026-10-29T10:09:05Z] `reviewer` Paul Reviewer:
  - Verified on 06b8982c. On my scratch squad, SKILL-43 (slug `manager`, with `manager` at she/her) has `pronouns` = `null` and `notebook` = `null`, while ROLE-1 keeps she/her and OP-17 keeps they/them. Putting back `pronouns.get(it.slug)` turns `test_json_gives_a_skill_sharing_a_roles_slug_neither_its_notebook_nor_its_pronouns` red. The case is a surface case under `covers("tree", "--json")`, not a regression-set test. That is acceptable, since it asserts the whole document. The changelog line for the fix is still owed (TASK-1234).
<!-- sq:finding:F43:discussion:end -->
<!-- sq:finding:F43:end -->

<!-- sq:finding:F44 -->
### F44 — TUI parity: an @-prefixed assignee now matches, and a stale undeclared badge no longer sorts

<!-- sq:finding:F44:body -->
The headless parity run turned up two differences that the handback does not list. Both bring the TUI in line with `sq tree`:

1. **An `@`-prefixed, mixed-case assignee now matches.** The filter screen with assignee `@Manager` shows TASK-28 (assigned to `manager`) at 611c505e, and an empty tree at 658ed963. The `tree` operation normalises the slug the same way `sq tree --assignee` does.
2. **A stale, undeclared badge no longer counts in a badge sort.** TASK-22 is a task that still carries `severity: medium` in its frontmatter, and the task type declares no severity field. Sorted by severity, it came first at 658ed963, because the sort read `item.badge_value`. At 611c505e it comes last, because the sort reads `node.badges`, which holds only declared fields. The header line already ignored the stale value at both commits.

Both are improvements, and neither needs a code change. Item 1 earns a line in the changelog's `sq ui` entry beside the two changes the handback lists (@tech-writer).
<!-- sq:finding:F44:body:end -->

#### Discussion

<!-- sq:finding:F44:discussion -->
- [2026-10-29T12:09:45Z, edited 2026-10-29T12:10:04Z] `tech-writer` Theo Writer:
  - CHANGELOG 0.18.0, Changed, `sq ui` entry: "An assignee filter takes `@` and any letter case (`@Manager` matches `manager`), and an unknown assignee shows an error and keeps the current view. A sort on a badge field reads only the fields an item's type declares, so a stale code its type no longer declares sorts last." The second sentence is item 2, from your TASK-22 repro; I did not run `sq ui` myself.
- [2026-10-29T12:38:36Z] `manager` Catherine Manager:
  - Noted: the CHANGELOG 0.18.0 line quoted above landed in cf27bbc8.
<!-- sq:finding:F44:discussion:end -->
<!-- sq:finding:F44:end -->

<!-- sq:finding:F45 -->
### F45 — _tui/_filter.py copies the engine's closed category set

<!-- sq:finding:F45:body -->
`_tui/_filter.py` defines `_CATEGORIES = ("roster", "work", "records")`. That is a copy of the engine's closed category set, `squads._workflow.CATEGORIES`, which comes from the `Literal` on `ItemSpec.category`. It sits beside `_tui/_tree.py`'s `_GROUP_LABELS` and `_GROUP_ORDER`, which hold the same set. Before this commit the filter read the engine constant directly. No test ties the two copies to the engine. If a category is added to the engine:

- the filter screen silently does not offer it;
- `populate_tree` raises a `KeyError` on `_GROUP_LABELS[...]` for the first node of that category.

Adopters cannot add a category, so this is engine drift, not adopter risk. The type catalog already carries `category` on every row, so the filter could take the distinct categories from `catalogs.types`, in `_GROUP_ORDER` order. A catalog of categories would also do, if one is ever wanted.
<!-- sq:finding:F45:body:end -->

#### Discussion

<!-- sq:finding:F45:discussion -->
- [2026-10-29T06:18:08Z] `python-dev` Elias Python:
  - - Fixed in 33fc48de. The filter's category choices and the tree's groups now both come from the type catalog's `category`, in the order the catalog first names each. Both copies (`_CATEGORIES`, and `_GROUP_LABELS`/`_GROUP_ORDER`) are gone, and so is their entry in the mutable-state allowlist.
    - One visible change: the filter's category select now reads Work, Records, Roster (it was Roster, Work, Records), the same order as the tree's groups. The tree itself is unchanged in a headless before/after capture.
- [2026-10-29T10:09:07Z] `reviewer` Paul Reviewer:
  - Reopened. The copies are gone, but the fix changes which order the tree groups come in. `categories()` takes the order in which the type catalog first names each category, and the type catalog is sorted by each type's `order`. So an adopter's type order now rearranges the top level of `sq ui`.
    
    Repro: on my scratch squad, add `[items.guide]` with `order = 5` to `.overrides/workflow.toml`, then capture headless with the real `sq ui`.
    - At 658ed963 and 611c505e: groups Work, Records, Roster.
    - At 06b8982c: groups Records, Work, Roster, and the filter's category select reads Records, Work, Roster.
    - With the bundled order, 06b8982c gives Work, Records, Roster, and my full parity capture matches 611c505e except for the filter select's order, which the dev reported.
    
    Two more consequences:
    - A category that no type names now loses its group, where the old docstring promised each group "present even when empty".
    - The dev's "tree unchanged" holds only for the bundled order.
    
    This is not a crash, and it is arguably defensible. But it is unasked behaviour, it reaches an adopter, and the changelog does not say it. @architect, rule which one holds:
    - (a) the group order follows the type catalog, as now, plus a changelog line and an eye-check item;
    - (b) a fixed presentation order in `_tui` (Work, Records, Roster), with any category it does not know appended after them. That is a client presentation constant, like `_ROLE_STYLES`, not a vocabulary copy.
- [2026-10-29T10:10:32Z] `architect` Robert Architect:
  - @python-dev Ruling: (a). The groups follow the type catalog, the order the adopter already controls through `order`. A fixed order in `_tui` would bring back the copy of the category set that this finding removed. A category no type names has nothing to show, so it gets no group. Steps: correct `populate_tree`'s docstring to say so, if any wording still promises a group "even when empty", and make no code change. @tech-writer, changelog line: "`sq ui` orders its top-level groups, and the filter's category choices, by the first type of each category in the type catalog's `order`; a category with no type has no group".
- [2026-10-29T10:13:42Z] `python-dev` Elias Python:
  - - Fixed in ef76e3f8 per ruling (a), with no code change. The docstrings of `populate_tree`, `categories()` and `NodeData` now say the groups follow the first type of each category in the type catalog's `order`, and that a category no type names has no group. The `_tui/_filter.py` docstring promised no order, so it is unchanged.
- [2026-10-29T10:14:21Z] `manager` Catherine Manager:
  - Verified on a363231c: docstring-only change in _tui/_tree.py and _tui/_session.py now states the catalog-order rule and drops the empty-group promise; pyright and ruff clean.
- [2026-10-29T12:09:46Z] `tech-writer` Theo Writer:
  - CHANGELOG 0.18.0, Changed, `sq ui` entry, per ruling (a): "The top-level groups, and the category choices of the filter screen, follow the first type of each category in the type catalog's `order`, so a type override's `order` can rearrange them; a category with no type has no group."
<!-- sq:finding:F45:discussion:end -->
<!-- sq:finding:F45:end -->

<!-- sq:finding:F46 -->
### F46 — Repair-corridor guard no longer reaches the producers; adopt and migrate can drop unreadable

<!-- sq:finding:F46:body -->
The repair-corridor guard (`tests/meta/test_repair_corridor_consumer_sites_are_exhaustively_classified.py`) exists to find every site that consumes a repair, migration, sync or adopt result, so that none drops the unreadable or skipped channel. After this commit its discovery no longer reaches the producers.

- The producer calls moved out of `_cli`: `self.repair()`, `self.run_pending_migrations()` and the bare-name `adopt(...)` now run in `_services/_corpus_ops.py` and `_services/_creation_ops.py`, where each result is mapped onto a DTO. The guard scans `src/squads/_cli` only.
- The bare-name target the guard keeps for adopt is `svc_adopt`, which no longer exists anywhere under `src/`. The new call is `adopt(...)`, so that half of the discovery cannot match anything.
- The sites it now classifies are the renderers and commands that read `report.unreadable` off the DTO. That proves a renderer reads the field. It does not prove the field was filled.

Repro (copy of d40232df): in `_creation_ops.adopt_squad` and `_corpus_ops.migrate_squad`, replace `unreadable=unreadable_lines(...)` with `unreadable=[]`. Then run `pytest -n 2 tests/meta tests/cli/test_repair.py tests/cli/test_migrate.py tests/cli/test_adopt.py`: 714 passed, 7 failed, and the 7 are the git-history manifest tests that also fail on an unmutated archive. So `sq adopt` and `sq migrate up` can lose the unreadable files, and with them exit 1, and no test goes red. The same mutation in `repair_squad` is caught, by `test_renumber_leaves_an_id_two_files_carry_to_be_merged_by_hand`.

Direction: extend the scan to the operation handlers under `_services` that call a corridor producer, and replace `svc_adopt` with `adopt` in the bare-name targets. Then falsify the discovery once with a new handler that drops the field. Alternatively, add one surface case each for `adopt` and `migrate up` on a corpus with an unreadable file. ADR-1172 rule 5 allows that arrangement for both commands.
<!-- sq:finding:F46:body:end -->

#### Discussion

<!-- sq:finding:F46:discussion -->
- [2026-10-29T07:01:54Z] `python-dev` Elias Python:
  - - Fixed in 6d1facf3. The guard now scans `_cli` and the operation handler modules (`_services/*_ops.py`), the bare-name target is `adopt`, and each classified site lists the channels it must read; a new test checks every site reads them.
    - Falsified: `unreadable=[]` in `adopt_squad`, `unreadable=[]` in `migrate_squad` and `skipped=[]` in `migrate_squad` each turn the guard red.
- [2026-10-29T07:11:02Z] `reviewer` Paul Reviewer:
  - Verified on a927563b. The repro from this finding is fixed. With `unreadable=[]` in `adopt_squad` (line 62) or in `migrate_squad` (line 147), `test_every_site_reads_the_channels_it_is_classified_for` goes red. Baseline: 7 failed, 727 passed, the 7 being the git-history manifest tests. Each mutant: 8 failed.
    
    One gap remains, recorded for the record and not reopened. The guard proves that a site reads the attribute, not that the value reaches the DTO. A decoy that reads the attribute and still drops the value (`unreadable_lines(result.repair.unreadable)[:0]`, in either handler) passes `tests/meta` and the repair, migrate, adopt and renumber surface files. No surface case runs `adopt` or `migrate up` on a corpus with an unreadable file, so a behavioural check is still missing. That is the place to close it if it matters.
- [2026-10-29T07:18:53Z] `python-dev` Elias Python:
  - - Gap closed in 95083231. The `adopt --json` case now runs on an adoptable folder that holds an unreadable file, and asserts the row and exit 1.
    - `unreadable_lines(...)[:0]` in `adopt_squad` turns it red, and so does the same change in `repair_squad` for the repair `--json` case.
    - `migrate_squad`'s row cannot be reached from the command line: `migrate up` refuses a legacy squad that holds an unreadable or duplicated file before any migration runs.
- [2026-10-29T07:25:04Z] `reviewer` Paul Reviewer:
  - Gap closed on 347cd0ad. `adopt --json` now asserts the unreadable row and exit 1. A `[:0]` decoy in `adopt_squad` turns `test_json_prints_the_squad_adopted_and_what_it_held` red, and one in `repair_squad` turns `test_repair_json_prints_what_the_rebuild_found` (and the renumber case) red. The claim about `migrate_squad` holds as far as input can reach. On the v0.14 fixture, the pre-run check refuses (exit 1, "no migration has run", schema unchanged) a file with no frontmatter id, malformed frontmatter, or a duplicate id. So the trailing rebuild's unreadable row can only come from a runner that itself leaves an unreadable file, which no CLI input arranges. The plain drop there is still caught by the corridor guard. The new case writes an item file only to arrange the corpus, which ADR-1172 rule 5 allows for adopt. It carries its `covers` marker and asserts the whole output.
<!-- sq:finding:F46:discussion:end -->
<!-- sq:finding:F46:end -->

<!-- sq:finding:F47 -->
### F47 — Grant guard checks operations only; a CLI leaf with no call passes unseen

<!-- sq:finding:F47:body -->
The grant guard used to run every top-level command and group, plus every `migrate`/`override` verb, through the CLI on a squad stamped behind and on one stamped ahead. It now calls each operation through `LocalApi` directly. Its docstring covers what remains with an assumption: "A command that makes no call reads only the package's own data, so the gate has nothing to refuse there."

What held up on d40232df:

- The operation half is sound. Making `check_grant` skip local-only operations turns both directions red. Every operation in the table gets a call, and the literal sets match the grants.
- The CLI half holds today. No module under `_cli/` or `_tui/` writes a file (`grep` for `write_text`, `os.replace`, `unlink`, `shutil`, `open(...'w')`: zero hits). On behind and ahead squads, every command line in the 43-line parity set (review comment of this round) refuses with exit 1 and the gate text, except `docs`, `migrate help`, `migrate chlog` and the usage errors. Every squad tree is byte-identical. `sq ui` on a behind squad still prints the gate error and exits 1.

What is no longer guarded: whether each CLI leaf reaches an operation at all. A command that makes no call, or one that writes through `_index`, `_sections` or `_migrations` (which the `_services` import guard does not cover), would get past the hard stop, and nothing would go red. The old CLI walk would have caught it.

Direction: keep a thin CLI-side check next to the operation walk. Either every leaf on a behind squad exits 1 with the gate text, except a literal no-call set (`docs`, `migrate help`, `migrate chlog`, plus `--help` and completion as ADR-1225 lists them), or every leaf except that set makes exactly one call, observed through a recording `Api` bound in the context.
<!-- sq:finding:F47:body:end -->

#### Discussion

<!-- sq:finding:F47:discussion -->
- [2026-10-29T07:01:57Z] `python-dev` Elias Python:
  - - Fixed in 6d1facf3: new guard `tests/meta/test_the_cli_and_the_terminal_ui_write_no_file_themselves.py`. No `_cli`/`_tui` module imports a writer (`_index` except `_reflog`, `_sections`, `_migrations` except `_registry`, `_aio`, `_itemfile`, `_overrides`, `shutil`, `tempfile`), calls a writing path method, `os.replace`, or opens a file for writing.
    - Falsified: an `_sections` import in `_cli/_main.py`, an `_index._store` import in `_tui/_app.py`, a `write_text`, an `open(..., "w")` and an `os.replace` in a `_cli` module each turn it red.
- [2026-10-29T07:11:15Z] `reviewer` Paul Reviewer:
  - Reopened on a927563b. The guard is a denylist of eight module names plus a few call shapes. It is not the rule its docstring states ("no module under `_cli/` or `_tui/` writes a file itself"). I put a probe module under `src/squads/_cli/` and ran the guard alone. Each of these passes:
    
    - `from squads._board._store import post` (it writes the board through `_aio.atomic_write_text`)
    - `from squads._memory._store import add` (writes the memory notebook)
    - `from squads._backends._managed_region import inject` (writes CLAUDE.md and AGENTS.md)
    - `from squads._index._reflog import append_line`, which the `READERS` exemption lets through although it appends to the reflog (`path.open("a")`, line 127)
    - `with Path("x").open("w")`, because only a bare `open(...)` name is checked, not the `.open(mode)` method
    - `io.open("x", "w")`
    
    `os.rename` is caught.
    
    Direction: derive the writer set instead of listing it. Run the same AST write-primitive scan over every module outside `_cli`/`_tui`, and treat any module containing a write (directly, or through `_aio`) as a writer, so a new store is covered without an edit here. Exempt a module only by its names that do not write, not by the whole module. Check `.open(<mode>)` method calls the same way as `open()`. Then falsify with a board or memory import and a `Path.open("w")`.
- [2026-10-29T07:18:50Z] `python-dev` Elias Python:
  - - Fixed in 95083231. The guard now derives its writers from the source. A top-level function or class writes when its body uses a write primitive, or calls a function that writes, computed to a fixed point. The primitives are:
      - `write_text`, `unlink`, `mkdir` and the like;
      - a one-argument `.replace` or `.rename`, and `os.replace`, `os.rename` or `os.remove`;
      - any `shutil` or `tempfile` call;
      - `open` in any form (builtin, `io.open` or a `.open` method) with a write mode or a non-literal one.
    - `LocalApi` is the one exempt route. No `_cli` or `_tui` unit may write, call a writer, or import one by name.
    - Falsified with a probe module under `_cli/`. Each of these turns it red: `_board._store.post`, `_memory._store.add`, `_backends._managed_region.inject`, `_index._reflog.append_line`, `Path('x').open('w')`, `io.open('x', 'w')`, `os.rename`, `_aio.atomic_write_text` and `Path.replace`.
    - A second test checks that the scan finds the first four of those and `_aio.atomic_write_text` as writers.
- [2026-10-29T07:25:01Z] `reviewer` Paul Reviewer:
  - Verified on 347cd0ad. The guard now derives writers from the source, to a fixed point. I placed a probe module under `_cli` and ran the guard. Each of these goes red: the board, memory, managed-region and reflog writer imports, `Path("x").open("w")`, `io.open("x", "w")`, `_aio.atomic_write_text` (through `from squads import _aio`), `_aio.path_rename`, `os.open`, a module alias (`import squads._board._store as s; s.post(...)`) and a package import (`from squads._board import _store; _store.post(...)`). `test_the_scan_derives_the_known_writers` anchors the derivation on known positives.
    
    Three shapes still pass. I record them as known limits and do not reopen:
    - A writer reached through an object a non-writing factory returns: `get_backend("claude_code").write_managed(sp)`. `get_backend` builds the backend without writing, and the method call on what it returns is not resolved. Closable cheaply by counting a function as a writer when its return annotation names a writer class (`-> AgentBackend`).
    - `os.makedirs("x")`: `makedirs` is missing from the primitives (the `.mkdir` attribute is caught).
    - `importlib.import_module("squads._board._store").post(...)`. This is dynamic, so out of reach for an AST scan.
    
    @python-dev, if you want the first two closed.
- [2026-10-29T07:31:54Z] `python-dev` Elias Python:
  - - Two of the known limits closed in 95ffe9eb:
      - A function now counts as a writer when its return annotation names a writing class. A class whose subclass writes is a writer too. So `get_backend` and `AgentBackend` are writers, and the known-writers test pins both.
      - The `os` primitives now include `makedirs`, `mkdir`, `rmdir`, `unlink`, `removedirs`, `renames`, `symlink`, `link`, `truncate` and `chmod`. `Path.mkdir` was already caught.
    - The bypass self-check is now 12 probe shapes, all red. The three new ones are `get_backend('claude_code').write_managed(sp)`, `os.makedirs('x')` and `Path('x').mkdir(parents=True)`. Removing the return-type rule turns the known-writers test red.
    - `importlib.import_module` stays a limit of the scan, and the guard's docstring says so.
- [2026-10-29T07:37:19Z, edited 2026-10-29T07:38:20Z] `reviewer` Paul Reviewer:
  - Checked on 931168f7. The two limits recorded last round are closed: `get_backend("claude_code").write_managed(sp)` and `os.makedirs("x")` both go red, and so does returning `ClaudeCodeBackend` from a `_cli` function. The return-type and subclass rules make no false positive on legitimate reads. With a probe module under `_cli` holding `calls.call(ops.REPAIR, RepairRequest())`, or `_paths.resolve()`, the guard stays green. The rule also fails loudly (red), never silently.
    
    One shape family still passes: a standard-library writer imported by name. The checks match the dotted spelling (`os.<name>`, `shutil.*`, or a `.method` attribute), and a bare name is never resolved through the module's imports. With a probe module under `_cli`:
    - `from os import unlink` then `unlink("x")`: 2 passed
    - `from os import makedirs` then `makedirs("x")`: 2 passed
    - `from shutil import rmtree` then `rmtree("x")`: 2 passed
    
    Tracked as F53. Fix: resolve a call's name through `_aliases` before matching, so `unlink` reads as `os.unlink` and `rmtree` as `shutil.rmtree`; then falsify with the three probes above. `importlib` is still out of reach, as the docstring now says.
<!-- sq:finding:F47:discussion:end -->
<!-- sq:finding:F47:end -->

<!-- sq:finding:F48 -->
### F48 — Working-language notice is lost on every refused call, not only the three listed

<!-- sq:finding:F48:body -->
The working-language notice is now attached to a response only when the call succeeds. `LocalApi.call` appends it after the handler returns, so a call that raises carries no notice. The handback names three cases where the notice no longer prints: an exit-2 vocabulary refusal, `docs` and `migrate help`. In fact every refused call loses it, which covers every error exit 1 an operation raises.

Repro: a squad with `working_language = "zz-not-a-lang"` in `.squads.toml`, NO_COLOR, piped.

- `sq task 99 show`: at 658ed963 stderr reads `warning: working_language "zz-not-a-lang" in .squads.toml is not a language tag squads recognises; using English (en)`, then `error: no item with number 99 …`. At d40232df stderr holds only the error. Exit 1 on both.
- The same happens on `sq task 19 status Bogus`, `renumber --by 1` (the unsafe offset), `migrate rename-type nosuch task`, `init --default-names` on an existing squad and `init --force --roles nosuch`. In the parity sweep these are the only differences on that squad, and stdout and the tree are identical.

An adopter with a mistyped language tag gets the notice on successful commands, so the information is not lost completely. This is low severity: the notice drops on the error path, which is exactly where the operator is reading stderr. Either attach the notice to the error as well (the error envelope already reaches `handle_errors`), or record the narrower behaviour in ADR-1225's row "The working-language notice | the root callback | a `warnings` entry", and correct the handback's list.
<!-- sq:finding:F48:body:end -->

#### Discussion

<!-- sq:finding:F48:discussion -->
- [2026-10-29T07:01:59Z] `python-dev` Elias Python:
  - - Fixed in 6d1facf3. `LocalApi.call` attaches the notice to a `SquadsError` raised past the schema gate (`SquadsError.warnings`, a new attribute), and `handle_errors` (and `workflow lint`) print it on stderr before the error, deduplicated with the response path. A gate refusal still carries none, as the root gate refused before the notice.
    - Probe against the old tree, unrecognised language: `task 99 show` (with and without `--json`), `migrate rename-type nosuch task`, `init --default-names` on a squad, `init --force --roles nosuch` print warning then error, as before. Falsified: dropping the attachment loses the warning on `task 99 show`.
    - Still without the notice: a refusal the CLI makes before any call (`task 1 status Bogus`, unknown `--type`), since the CLI no longer reads the configuration for it.
    - @architect: the local path needs no wire change. For `HttpApi`, should the error envelope (ADR-1225 section 3) carry an optional `warnings` list so a daemon's refusal brings the notice too? Not added.
- [2026-10-29T07:04:38Z] `architect` Robert Architect:
  - @python-dev Rulings (ADR-1225, amended 2026-10-29).
  - (1) Yes. The error envelope is `{"error": {type, message, warnings}}`, with `warnings` always present (`[]` when there is none). Add it to `ErrorBody` in `_api/_errors.py`, fill it from `SquadsError.warnings` on the daemon side when TASK-1218/1219 serve errors, and have `_http.py`'s parse put it back on the raised `SquadsError`. Add one wire-helper test for the round trip if `_http` already has its cases; otherwise it comes with the daemon's route suite.
  - (2) The gap is accepted. A vocabulary exit 2 or an unknown `--type` is about the command line, the CLI does not read the configuration for it, and the next call that runs prints the notice. Correct the handback's list to name exactly that case. No code.
- [2026-10-29T07:11:05Z] `reviewer` Paul Reviewer:
  - Verified on a927563b. On the bad-language squad, NO_COLOR, I counted the notice on stderr, old tree against round 2. `task 99 show`, `task 99 show --json`, `migrate rename-type nosuch task`, `renumber --by 1`, `init --default-names`, `init --force --roles nosuch` and `role add architect` print it once, as at 658ed963. A successful `status` still prints it once. Only `task 19 status Bogus` still lacks it: the refusal comes before the call, which is the gap now with the architect.
    
    Note: no test holds this. With the `exc.warnings` attachment removed, `tests/cli` plus `tests/meta` gives 1530 passed, and the only 7 failures are the manifest tests. If it is to stay fixed, ADR-1172 puts a regression test in `tests/regressions/`.
- [2026-10-29T07:18:55Z] `python-dev` Elias Python:
  - - Pinned in 95083231: a new case runs `show 99` on a squad with `working_language = "klingon!!"`. It asserts that stderr is the warning then the error, stdout is empty, and the exit code is 1.
    - Removing the attachment in `LocalApi.call`, or the print in `handle_errors`, turns it red.
- [2026-10-29T07:25:05Z] `reviewer` Paul Reviewer:
  - Gap closed on 347cd0ad. `test_a_refused_show_prints_the_notices_before_the_error` asserts the exit code, an empty stdout and the whole stderr (the warning, then the error). It carries its `covers` marker. With the `exc.warnings` attachment removed it goes red (1 failed, 9 passed in test_show.py). Editing `.squads.toml` to arrange an unrecognised language follows the earlier `--json` notice case: no CLI path writes one.
<!-- sq:finding:F48:discussion:end -->
<!-- sq:finding:F48:end -->

<!-- sq:finding:F49 -->
### F49 — init prompts for role names on a mismatched squad before the gate refuses

<!-- sq:finding:F49:body -->
Under a pseudo-terminal, `sq init --force --roles minimal` on a squad stamped behind (v0.16) now asks `Name for 'manager' (Enter to keep default 'Catherine Manager'):` and only then refuses with the gate text, exit 1. At 658ed963 the root gate refused before any prompt. Nothing is written, and the squad tree is identical to its template afterwards.

This happens because the prompt sits before the call (ST3), while the gate now lives in the call. It is the same class as the usage-before-gate deviation, but here the operator types answers that are then thrown away, once per role (`--roles all` asks for 8).

Options: accept it as WontFix and record why, or skip the prompt when a squad resolves whose schema differs. That check reads only `.squads.toml`, which init already reads for `init_names` a few lines earlier.
<!-- sq:finding:F49:body:end -->

#### Discussion

<!-- sq:finding:F49:discussion -->
- [2026-10-29T07:02:02Z] `python-dev` Elias Python:
  - - Fixed in 6d1facf3: `init` skips the role-name prompt when the directory resolves to a squad at another schema, so the call refuses with the gate text and nothing is asked.
    - Probe under a pseudo-terminal on v0_14 with `init --force --roles minimal`: no prompt, gate error, exit 1. Falsified: without the check the prompt comes back before the refusal.
- [2026-10-29T07:11:07Z] `reviewer` Paul Reviewer:
  - Verified on a927563b, under a pseudo-terminal. On behind (v0.16) and ahead (v9.9) squads, `init --force --roles minimal` asks for nothing, prints the gate text and exits 1, and both trees are byte-identical to their templates. On a current squad the prompt is still asked and init completes (exit 0).
<!-- sq:finding:F49:discussion:end -->
<!-- sq:finding:F49:end -->

<!-- sq:finding:F50 -->
### F50 — Sweep leftovers: open_service and TARGET_DATE dead, docstrings name the deleted bridge

<!-- sq:finding:F50:body -->
Dead code and stale prose the removal sweep left behind. Vulture at d40232df against 658ed963 shows three new entries outside the TUI line shifts:

- `open_service` (`_services/_service.py:497`) has no caller left in `src/` or `tests/`. Seven docstrings still name it as the composition entry point (`_context.py:11`, `_errors.py:82`, `_workflow/_loader.py:31, 316, 355, 1363, 1576`, `_cli/_workflow_cmd.py:12, 15`), and so does CLAUDE.md's composition-root paragraph. Delete it and reword those mentions to `compose_service`, or keep it with a caller.
- `AttributeKey.TARGET_DATE` (`_models/_attributes.py:64`): its two readers were the deleted `_common.py` builders, and nothing else reads `target_date`.
- `Grant.ground` (`_api/_api.py`) is read by nothing, and the old `GateGrant.ground` never was either. It records why an operation has a grant, so keeping it is fine. If it stays, add it to vulture's `ignore_names` with that reason.

Stale prose that describes deleted code:

- `_index/_store.py:633`, the `enter_read_scope` docstring: "``_cli/_common.py``'s ``command`` bridge uses it … opens the scope on the first and closes it via ``ctx.call_on_close``". The bridge is gone. Its only caller is now `LocalApi._scoped`.
- `_cli/_common.py:816`, the `_click_root_context` docstring: "``command``-wrapped functions are only ever invoked *by* Click". The decorator is gone, and the function now also runs through `invocation_sources` as `LocalApi`'s sources callable.
- `_services/_corpus_ops.migrate_squad` keeps the ahead refusal ("newer than this squads (v…); upgrade the squads package"). The MIGRATE grant refuses an ahead squad first, with the gate text, so this branch cannot be reached through `LocalApi`. It could not be reached through the old group gate either, so this is not a regression. Delete it, or say what reaches it.
- CLAUDE.md lines 27 and 248 and docs/internals.md lines 463 and 475 still name `get_service` and `require_current_schema`. The handback already flagged these for @tech-writer.

Two items the brief asked about, which are not defects of this commit:

- The duplicate `e()` (`_cli/_common.py:647` and `_cli/_render/_style.py:34`) already existed at 658ed963. Renderers may not import `_common` (renderer guard), but `_common` may import from `_render._style`, so the copy in `_common` could become a re-export of the one in `_style`.
- The three `_resolve_addr` group callbacks (`_role.py:270`, `_skill.py:138`, `_operator.py:123`) differ only in their help text, and each one parses without resolving. They came from the earlier roster tasks and are unchanged here. One shared registrar would match ADR-1172 rule 2. The name now overstates what the callback does.
<!-- sq:finding:F50:body:end -->

#### Discussion

<!-- sq:finding:F50:discussion -->
- [2026-10-29T07:02:05Z] `python-dev` Elias Python:
  - - Fixed in 6d1facf3: `open_service` deleted and its mentions reworded to `compose_service` (`_context.py`, `_errors.py`, `_workflow/_loader.py`, `_cli/_workflow_cmd.py`, `_cli/_common.py`, `_overrides/_service.py`, `_services/_service.py`). `AttributeKey.TARGET_DATE` deleted. `enter_read_scope`, `read_scope` and `_click_root_context` docstrings rewritten, and `LocalApi` now uses `read_scope`. The unreachable ahead branch in `migrate_squad` is removed. `ground` is in vulture's `ignore_names` with its reason.
    - CLAUDE.md and docs/internals.md left for @tech-writer. `e()` and `_resolve_addr` untouched.
- [2026-10-29T07:11:10Z] `reviewer` Paul Reviewer:
  - Verified on a927563b for the code. `open_service`, `TARGET_DATE` and the unreachable ahead branch are gone. The `enter_read_scope`/`read_scope` and `_click_root_context` docstrings describe current code. `ground` sits in vulture's `ignore_names` with its reason, and vulture adds nothing new over 658ed963 (`TARGET_REF` was already listed there). The CLAUDE.md and docs/internals.md lines are still with @tech-writer.
<!-- sq:finding:F50:discussion:end -->
<!-- sq:finding:F50:end -->

<!-- sq:finding:F51 -->
### F51 — New --json cases cover only empty reports; migration rows asserted by no case

<!-- sq:finding:F51:body -->
The 8 new `--json` cases are whole-document, carry their `covers` markers, and each one I falsified went red (`init --json` with the prompt left on, and `print_json` without the stderr warnings). They only cover the empty or trivial shape of each report, though:

- `migrate up --json` runs on a current squad (`applied: []`, `reconciled: null`, `manual_span: null`). The keys and order of `AppliedMigration` and `Reconciled`, which are the whole point of the document on a squad that is actually behind, are asserted by no case. `grep '"from_schema"' tests/cli` only hits the `migrate help` documents.
- `repair --json` asserts `renumbered: []` and `unreadable: []`. `renumber --json` asserts `warning: null` and `notice: null`.

This is the same class as F17. ADR-1172 asks for one case per parameter, not one per shape, so adding cases is not the remedy. Each existing case could instead run on the arranged corpus its command's neighbouring cases already use: `migrate up --json` on the v0.14 fixture, which rule 5 allows, and `repair --renumber --json` on the twin-numbered corpus that `test_renumber_gives_a_shared_number_a_new_one` builds. Then the nested rows are asserted at no extra case count.
<!-- sq:finding:F51:body:end -->

#### Discussion

<!-- sq:finding:F51:discussion -->
- [2026-10-29T07:02:07Z] `python-dev` Elias Python:
  - - Fixed in 6d1facf3, case count unchanged. `migrate up --json` runs on the v0_14 fixture and asserts the three applied migrations, the reconcile row, the dropped config key, the notice and `manual_span`. `repair --json` runs with `--renumber` on the duplicate-id corpus (unreadable row, exit 1). `renumber --json` runs with `--by 10` (warning set).
- [2026-10-29T07:11:13Z] `reviewer` Paul Reviewer:
  - Verified on a927563b. The three `--json` cases now assert populated reports: three applied migrations with their reports, the reconcile row, the dropped config key, the notice and `manual_span` on the v0.14 fixture; the duplicate-id unreadable row with exit 1; and the `--by` warning. Mutation: swapping two keys in `AppliedMigration` and in `Reconciled` turns `test_up_json_reports_each_migration_run_on_an_older_squad` red. Restored, all 42 pass. The `missing` row is no longer exercised by the repair case, but it is a flat list of strings, so this is fine.
<!-- sq:finding:F51:discussion:end -->
<!-- sq:finding:F51:end -->

<!-- sq:finding:F52 -->
### F52 — Ladder modes share names with document choices of a different meaning

<!-- sq:finding:F52:body -->
The composition matches ADR-1128 and the F16 ruling. `_compose_first_of` is private, `compose_service` is still the one construction path, and `LocalApi` only maps `op.mode`. No module outside `_service.py` names `Documents`, `ServiceMode` or a fallback table (grep over `src/` and `tests/`). `refusal` is now carried on the ladder services. Its only readers are `render_cheatsheet` and `check_squad`, which no corpus operation reaches, so the output is unchanged. The parity sweep below confirms this on the corrupt-index and broken-override squads.

Two points for whoever next touches `_service.py`:

- `_api.Mode.INDEX_CHECK_SKIPPED` and `_api.Mode.MIGRATE` now mean "normal, then the ladder". The `Documents` members with the same names mean the documents themselves. Every other mode with no table is mapped by value (`Documents(mode.value)`), so if a mode were dropped from `_ladder`, it would silently switch to the direct document choice and skip the normal attempt. A different name on one side, or an exhaustive `match`, would remove that trap.
- There are now two fallback shapes: `_fallbacks` (the first row matching the error class) and `_ladder` (the first rung that builds). ADR-1224 point 4 describes "a table … beside `CHECK_FALLBACKS`". Both shapes satisfy that wording, but the ADR names only the first.
<!-- sq:finding:F52:body:end -->

#### Discussion

<!-- sq:finding:F52:discussion -->
- [2026-10-29T07:31:55Z] `python-dev` Elias Python:
  - - Done in 95ffe9eb. `compose_service` maps a mode with neither a fallback table nor a ladder through `_direct_documents`, an explicit `match` over every `_api.Mode`. The four modes that have one raise `ValueError` there, so dropping a mode from `_ladder` can no longer fall back to the direct document choice.
    - Behaviour is unchanged: `pytest -n 2 tests/meta tests/cli` gives 1539 passed. Falsified: removing `MIGRATE` from `_ladder` turns 3 `migrate` cases red.
- [2026-10-29T07:37:17Z] `reviewer` Paul Reviewer:
  - Verified on 931168f7. `_direct_documents` maps NORMAL and BUNDLED_FALLBACK to their documents, which is what `Documents(mode.value)` gave for the only two modes with no table, and it refuses the four table and ladder modes. Behaviour is unchanged:
    - `repair`, `check`, `workflow types`, `show`, `list`, `migrate up` and `override list` on the current, corrupt-index, broken-override and behind squads are byte-identical between 347cd0ad and 931168f7 (28 runs, output and exit code).
    - `tests/meta` plus the repair, migrate, check and show surface files pass, apart from the 7 git-history manifest tests that fail on any archive.
    
    The trap is removed. With `Mode.INDEX_CHECK_SKIPPED` dropped from `_ladder`, `sq repair` on the corrupt-index squad now stops with `ValueError: mode index-check-skipped composes through its fallback table or ladder` instead of silently composing the skipped-check documents.
<!-- sq:finding:F52:discussion:end -->
<!-- sq:finding:F52:end -->

<!-- sq:finding:F53 -->
### F53 — Write guard misses stdlib writers imported by name (from os import unlink)

<!-- sq:finding:F53:body -->
The write guard under `tests/meta/` (`..._and_the_terminal_ui_write_no_file_themselves.py`) matches a standard-library writer only by its dotted spelling (`os.<name>`, `shutil.*`) or as a `.method` attribute. A call to a bare name is never resolved through the module's imports, so a writer imported by name passes. On 931168f7, with a probe module under `src/squads/_cli/`:

- `from os import unlink` then `unlink("x")`: 2 passed
- `from os import makedirs` then `makedirs("x")`: 2 passed
- `from shutil import rmtree` then `rmtree("x")`: 2 passed

The same module written with `import os` and `os.makedirs("x")` goes red, so the gap is in how the name is spelled, not in the rule.

Fix: resolve a call's name through the module's import aliases (`_aliases` already maps `unlink` to `os.unlink` and `rmtree` to `shutil.rmtree`) before matching it against `OS_WRITERS` and `WRITING_MODULES`. Then falsify with the three probes above.
<!-- sq:finding:F53:body:end -->

#### Discussion

<!-- sq:finding:F53:discussion -->
- [2026-10-29T10:10:15Z] `python-dev` Elias Python:
  - - Fixed in d80a00ab. The guard now reads each called name through the module's imports before matching it, so `unlink` imported from `os` is matched as `os.unlink` and `sh.rmtree` as `shutil.rmtree`.
    - The bypass self-check is now 17 shapes, all red. The five new ones are `from os import unlink`, `from os import makedirs`, `from shutil import rmtree`, `import shutil as sh` and `from os import replace as r`, each followed by a call.
    - Falsified: without the resolution, four of the five go green: `unlink`, `makedirs`, `rmtree` and the aliased `r`. `sh.rmtree` stays red even then, because the `.rmtree` attribute rule already catches it.
    - Gates: pyright 0 errors, ruff check and format clean on `src tests`, `pytest -n 2 tests/meta tests/cli` 1539 passed.
- [2026-10-29T10:14:10Z] `reviewer` Paul Reviewer:
  - Verified on 72a3f24e. With a probe module under `src/squads/_cli/`, every writer imported by name now fails the guard:
    - `from os import unlink` / `makedirs`
    - `from shutil import rmtree`
    - `from os import remove as rm`
    - `import shutil as sh` with `sh.copy`
    - `import os as o` with `o.makedirs`
    - `from tempfile import mkstemp`
    - `builtins.open("x", "a")`
    - `Path(...).write_text`
    
    There are no false positives on reads: `path.exists`, `getcwd`, `environ.get`, `Path.read_text`, `open(...)` with no mode or `"rb"`, two-argument `str.replace`, `os.path.join` and `os.listdir` stay green. The unprobed tree is green too.
    
    Known limits, recorded rather than filed:
    - **Writer passed as a value, not called by its name.** `md = os.makedirs; md("x")`, `functools.partial(os.makedirs, "x")()` and `asyncio.to_thread(os.makedirs, "x")` pass. A one-line closing exists if `to_thread` use in `_tui` ever makes this real: treat any loaded reference to an `os`/`shutil` writer as a write, not only a call.
    - **Renamed `open`.** `from io import open as iopen; iopen("x", "w")` passes, because `_is_open` matches the name `open` only.
    - **Dynamic references.** `importlib`, `getattr` on a string and `exec` stay out of reach, as the docstring says.
    - **Read-only `shutil` calls are flagged (fails safe).** `shutil.get_terminal_size()` and `shutil.which()` turn the guard red, because every call into `shutil` counts as a write. No CLI or TUI code calls them today. The fix is to list `shutil`'s writing functions instead of the whole module.
<!-- sq:finding:F53:discussion:end -->
<!-- sq:finding:F53:end -->

<!-- sq:finding:F54 -->
### F54 — Lazy type groups cache an override-built app across run() calls; leaks between squads

<!-- sq:finding:F54:body -->
`_type_app` (`src/squads/_cli/__init__.py`) is a process-wide `functools.cache`, and it calls `build_item_app(item_type)` with no spec. `build_item_app` then falls back to `common.get_active_spec()`. Before this change every bundled type app was built once at import time, so it always came from the bundled spec, and `_dynamic_subentity_group_cls` depends on that (its docstring says the sub-entity commands are "baked in at import time from the bundled spec", and it rebuilds only when the live signature differs from the bundled one).

Now a type app is built on its first lookup. The root resolves the addressed type before its callback binds the spec, so that one is still built from the bundled spec. But when `--help` is present, `HelpAwareGroup.resolve_command` runs after the root callback and walks the whole root tree (`help_requested` -> `_value_options_of(root)`). That builds every other type from the squad's override spec, and the cache keeps those apps for the life of the process.

Reproduced in-process (scratch probe `leak2.py`). Squad A overrides `[items.bug] subentity_kind = "subtask"`. Squad B is plain. In one process:
1. `run(["-C", A, "task", "1", "show", "--help"])`
2. `run(["-C", B, "bug", "--help"])` now lists `add-subtask`/`subtask`/`subtasks`, and `sq bug 1 add-subtask x` dispatches (exit 1, "is ROLE-1, not a bug") where 0aec4439 answers exit 2, no such command.

Without step 1, or on 0aec4439 with or without it, B's output is correct. A one-shot CLI process is not affected, because only one command runs. Affected: every multi-invocation host of `run()`, which breaks its own contract ("nothing it binds is visible to the next call"). That includes the in-process CLI tests on xdist workers, where results now depend on test order, and the planned daemon (ADR-1225).

Fix: build with `spec=bundled_spec()` in `_type_app`, which restores the invariant the dynamic group relies on. Add a test that runs the two calls above in sequence.
<!-- sq:finding:F54:body:end -->

#### Discussion

<!-- sq:finding:F54:discussion -->
- [2026-10-29T11:27:52Z] `python-dev` Elias Python:
  - Fixed in 6e65283e: _type_app builds from bundled_spec(). New CLI test runs an override squad's 'task 1 show --help' then a plain squad's 'bug 1 add-subtask x' in one process and expects exit 2; it fails (exit 1) without the fix and passes with it. The override squad is unavoidable: the leak only exists when a spec differs from the bundled one.
- [2026-10-29T11:32:49Z] `reviewer` Paul Reviewer:
  - Reopened: the code fix holds, but the regression test is order-dependent. The leak2 repro on fe8df57d is clean (in one process, the plain squad's `bug --help` and `bug 1 add-subtask x` are unchanged after the override squad's `task 1 show --help`).
    
    Why a whole-text compare "stopped showing the leak": the help path and the dispatch path both read the same `root.commands["bug"]` entry, so this is not a second bug. The cause is a second cache. The root `conftest.py` memoises `typer.main.get_command(app)` per process (`_build_command`), and that cached root's `_LazyCommands` keeps every group it has built. `_type_app.cache_clear()` does not reset it. Any earlier call that builds `bug` in the same worker leaves the bundled build in the cached root, and the poison step can no longer replace it. A whole-text compare that renders the clean `bug --help` first builds `bug` itself, so it can never fail.
    
    Measured with the fix reverted in a scratch copy (`-n 0`):
    - the new test alone: 1 failed (good);
    - the same test after one earlier test that runs `bug --help`: 2 passed. In the full run it therefore guards nothing whenever an earlier test on its worker touched `bug`.
    
    A whole-output version is possible and does fail with the fix reverted, whatever ran before it. Call a helper that runs `_type_app.cache_clear()` and `conftest._build_command.cache_clear()` (better: a fixture that hands the test a fresh root) before each step. Then:
    1. Clear, run `-C plain bug 1 add-subtask x`, and keep its exit code and output.
    2. Clear, run `-C overridden task 1 show --help`.
    3. Run `-C plain bug 1 add-subtask x` again, and assert `(exit_code, output)` equals step 1.
    
    Or assert step 3 against the literal refusal: exit 2, and the whole text `Usage: sq bug [OPTIONS] N COMMAND [ARGS]...` / `Try 'sq bug --help' for help.` / the boxed `No such command 'add-subtask'.`. With the fix reverted it fails with `(1, 'error: 1 is ... not a bug')` != `(2, 'Usage: ...')`. With the fix it passes (checked with `-n 2`). That meets ADR-1172's whole-output rule.
- [2026-10-29T11:35:56Z] `python-dev` Elias Python:
  - Reworked in the new commit: a fresh_command_tree fixture clears the conftest-memoised command tree and the type-app cache around the test; it runs the override squad's task 1 show --help, then the plain squad's bug 1 add-subtask x, and asserts the whole refusal (exit 2, usage lines, boxed No such command). With the one-line fix reverted it fails alone and after a bug --help test (-n 0); with the fix it passes.
- [2026-10-29T11:41:53Z] `reviewer` Paul Reviewer:
  - Verified on 94e275c3. With the fix in place: the test plus a prior bug --help test, 2 passed (-n 2). With the one-line fix reverted (-n 0): alone, 1 failed; after a test that runs bug --help, 1 failed with (1, error: 1 ... not a bug) != (2, Usage: ...). fresh_command_tree makes the test falsifiable whatever ran before it, and the assert is the whole literal refusal. On the hook shape, see F60.
<!-- sq:finding:F54:discussion:end -->
<!-- sq:finding:F54:end -->

<!-- sq:finding:F55 -->
### F55 — SQUADS_SPANS=yes crashes every command; empty or 1 prints since-boot marks

<!-- sq:finding:F55:body -->
`_spans.mark` does `float(os.environ["SQUADS_SPANS"] or 0)`. The module docstring says spans are written "when `SQUADS_SPANS` is set", so a contributor will naturally try `SQUADS_SPANS=1`, `=yes` or `=on`. Measured on the scratch copy:
- `SQUADS_SPANS=yes sq list --json`: a ValueError traceback from `main_callback`, exit 1, no output. Every command fails the same way.
- `SQUADS_SPANS=` or `=1`: exit 0 and stdout unchanged, but `startup`, `call_done` and `end` print about 140874596 ms (time since boot minus 0 or 1 s). The `span(...)` durations are correct.

The variable carries two things at once: the on/off switch and the launcher's `perf_counter` reading. It also relies on `perf_counter` being comparable across processes, which Python does not promise (it does hold for CLOCK_MONOTONIC on Linux). Suggest keeping the switch on presence, ignoring `mark` (or printing only the `span` durations) when the value is not a float, and documenting the value in the docstring.
<!-- sq:finding:F55:body:end -->

#### Discussion

<!-- sq:finding:F55:discussion -->
- [2026-10-29T11:27:53Z] `python-dev` Elias Python:
  - Fixed in 6e65283e: any non-empty SQUADS_SPANS enables spans. Only the form t=<float> sets the time origin; otherwise times run from the module's import, so no boot-relative values and no crash. Checked with yes, 1 and empty.
- [2026-10-29T11:33:01Z] `reviewer` Paul Reviewer:
  - Verified on fe8df57d: SQUADS_SPANS empty is off (no stderr); 1, yes, t=, t=abc all exit 0 with stdout byte-identical under list --json and marks timed from import (~200-270 ms); t=<perf_counter> times from the launcher. The bench --spans run reports all marks and the exit tail.
<!-- sq:finding:F55:discussion:end -->
<!-- sq:finding:F55:end -->

<!-- sq:finding:F56 -->
### F56 — Comments still say the root table is built at import time; _spans missing from CLAUDE.md

<!-- sq:finding:F56:body -->
These comments still describe the eager registration that this change removed:
- `_cli/__init__.py`: the `_CustomTypeGroup` docstring ("Built-in commands are registered statically at import time"); the `get_command` comments ("The static table binds every bundled alias at import time", "the statically-built command table", "Statically-registered types are always in the static table").
- `_cli/_common.py`: `static_alias_is_stale` ("The root table binds every bundled alias at import time") and the docstring near line 1082 ("A statically registered command is built at import time").
- `_cli/_items.py` `_dynamic_subentity_group_cls` ("baked in at import time from the bundled spec"). This claim is now false for any type built after the root callback (see the cross-squad cache finding).

CLAUDE.md's architecture map also does not list `_spans.py` or the `SQUADS_SPANS` variable, and `scripts/bench_local_mode.py` is not mentioned in any contributor doc.
<!-- sq:finding:F56:body:end -->

#### Discussion

<!-- sq:finding:F56:discussion -->
- [2026-10-29T11:27:54Z] `python-dev` Elias Python:
  - Fixed in 6e65283e: the stale 'registered statically / bound at import time' comments in _cli/__init__.py, _common.py and _items.py now describe the lazily built command table. CLAUDE.md left to the writer.
- [2026-10-29T11:33:04Z] `reviewer` Paul Reviewer:
  - Verified (code comments): the import-time wording is gone from _CustomTypeGroup, get_command, static_alias_is_stale, spec_error_command, spec_aware_command_cls and _dynamic_subentity_group_cls; each now matches the lazy table built from the bundled spec. The CLAUDE.md half is with the writer, as briefed.
- [2026-10-29T12:09:33Z] `tech-writer` Theo Writer:
  - CLAUDE.md half done (uncommitted, for review): the `_cli/` entry now describes the lazy command table (`LAZY_GROUPS`, type apps built from the bundled spec once per root command, `sq --help` building all) and its guard `tests/meta/test_lazy_command_groups_match_the_typer_groups.py`; a new `_spans.py` entry names `SQUADS_SPANS` (`t=<float>` origin) and `scripts/bench_local_mode.py` with its inputs. docs/internals.md section 13 documents `SQUADS_SPANS` for contributors reading the installed tool.
<!-- sq:finding:F56:discussion:end -->
<!-- sq:finding:F56:end -->

<!-- sq:finding:F57 -->
### F57 — Lazy-group guard misses annotated and from-import Typer definitions

<!-- sq:finding:F57:body -->
`tests/meta/test_lazy_command_groups_match_the_typer_groups.py::_group_typers` matches only `ast.Assign` nodes whose call is the attribute form `typer.Typer(...)`. Falsified on a scratch copy: appending `extra_app = typer.Typer()` to `_cli/_board.py` turns the guard red (1 failed, 3 passed), but `extra_app: typer.Typer = typer.Typer()` (an annotated assignment, the form strict pyright pushes toward) leaves it green (4 passed). A `from typer import Typer; x = Typer()` would also slip through, since its `func` is an `ast.Name`. Suggest matching `ast.AnnAssign` too, and accepting a `Name` whose id is `Typer`. Otherwise the guard follows ADR-1172 (in `tests/meta`, no timing assertions) and goes red when a group is added without a table row.
<!-- sq:finding:F57:body:end -->

#### Discussion

<!-- sq:finding:F57:discussion -->
- [2026-10-29T11:27:55Z] `python-dev` Elias Python:
  - Fixed in 6e65283e: the guard matches annotated assignments and a bare Typer(...) call. Falsified with 'extra_app: typer.Typer = typer.Typer()' (red) and 'from typer import Typer; extra_app = Typer()' (red); green on the clean tree.
- [2026-10-29T11:33:06Z] `reviewer` Paul Reviewer:
  - Verified by falsification on a scratch copy: appending to _cli/_board.py each of plain assign, annotated assign, from typer import Typer + bare call, and a string-annotated assign turns the guard red (1 failed, 3 passed); restored, 4 passed.
<!-- sq:finding:F57:discussion:end -->
<!-- sq:finding:F57:end -->

<!-- sq:finding:F58 -->
### F58 — Releasing runbook does not run bench_local_mode.py as the task requires

<!-- sq:finding:F58:body -->
The task's test approach says the script "is a release-time check ... and the releasing runbook runs it", and the criterion says the numbers are recorded "with the release". `scripts/bench_local_mode.py` is not referenced from the releasing-squads skill or any doc (grep over `squads/agents/skills/` and the repo). Until the runbook names it, with the inputs it needs (a released `sq` path, a squad copy and an item number), the check will not run at the 0.18 cut.
<!-- sq:finding:F58:body:end -->

#### Discussion

<!-- sq:finding:F58:discussion -->
- [2026-10-29T12:09:36Z] `tech-writer` Theo Writer:
  - The releasing-squads skill (SKILL-508), section 1 Gates, now runs `scripts/bench_local_mode.py`: copy `.squads.toml` and `squads/` to `~/.cache/sq-bench/squad`, `--old ~/.local/bin/sq --new "$PWD/.venv/bin/sq" --task <n>`, expect `new/old median` <= 1.0 on show, list and tree, raise anything above with the operator, and post the table as a comment on the release milestone. Smoke-run of that exact command at 8b9dc64b, 3 runs: show 0.751, list 0.705, tree 0.719. A schema-bump release cannot compare (the old build refuses the copy); the step says to record the new build spans then.
- [2026-10-29T12:38:38Z] `manager` Catherine Manager:
  - Verified: SKILL-508 Gates section runs scripts/bench_local_mode.py against the released sq on a copied squad and records the medians with the release.
<!-- sq:finding:F58:discussion:end -->
<!-- sq:finding:F58:end -->

<!-- sq:finding:F59 -->
### F59 — Benchmark: fixed old-first order, repo-specific --task default, no-op SQUADS_DAEMON

<!-- sq:finding:F59:body -->
`scripts/bench_local_mode.py` measures what the criterion asks: 31 runs by default, old and new interleaved, one warm-up each, and the median with inclusive p25-p75. Smaller points:
- Each pair always runs old first, then new. A fixed order can carry a small systematic bias (cache and CPU frequency state left by the previous run). Alternating the order per round costs nothing.
- `--task` defaults to 1238, an item number specific to this repo, so it fails on any other squad.
- The script runs in the `--squad` directory as given and does not copy it. The criterion's "one copy of a squad" relies on the caller passing one.
- `SQUADS_DAEMON=off` is not read by anything in either tree yet, so it has no effect for now. That is harmless, but it is worth knowing when reading the numbers.
- `--spans` fails with a StatisticsError if the build reports no `end` mark.
<!-- sq:finding:F59:body:end -->

#### Discussion

<!-- sq:finding:F59:discussion -->
- [2026-10-29T11:27:57Z] `python-dev` Elias Python:
  - Fixed in 6e65283e: the build that runs first alternates per round, --task is required, the squad is copied to a temp dir, --spans no longer needs an end mark, and the SQUADS_DAEMON=off setting is dropped since nothing reads it.
- [2026-10-29T11:33:09Z] `reviewer` Paul Reviewer:
  - Verified: order alternates per round, --task is required, the squad is copied to a temp dir, SQUADS_DAEMON dropped, --spans skips the tail without an end mark. Smoke runs (3 runs compare, 2 runs --spans) completed. Note only: --squad is copied whole, so pass a directory holding just the squad (passing a repo root would copy .venv and .git).
<!-- sq:finding:F59:discussion:end -->
<!-- sq:finding:F59:end -->

<!-- sq:finding:F60 -->
### F60 — drop_type_apps is a src test hook over a module cache; a per-root type-app cache needs none

<!-- sq:finding:F60:body -->
`drop_type_apps()` in `src/squads/_cli/__init__.py` exists only for the root conftest's `fresh_command_tree` fixture. Nothing in `src` calls it, and `uv run --all-extras vulture` reports it ("unused function 'drop_type_apps' (60% confidence)", line 98). It does work, and it is better than a private reach-in to `_type_app.cache_clear()`. But it is a test hook in the product, and it guards a module-level mutable cache that only exists to share one Typer between a type's name and its aliases.

A cleaner shape removes both. Keep that sharing per root command instead of per process: `_lazy_builders()` (or `_LazyCommands`) holds a local dict from type to its built Typer, and the alias builders read from it. Each `typer.main.get_command(app)` then starts with no type apps. The fixture's `_build_command.cache_clear()` alone gives a fresh tree, and `drop_type_apps`, `_type_app` and the `functools.cache` go away. Cost is unchanged for a CLI run (one root per process). A multi-call host rebuilds a type app per root, the same as it already re-converts each Click group per root.

If the hook stays, add it to `[tool.vulture] ignore_names` with a one-line reason, as CLAUDE.md asks for an intentional false positive.
<!-- sq:finding:F60:body:end -->

#### Discussion

<!-- sq:finding:F60:discussion -->
- [2026-10-29T11:47:59Z] `python-dev` Elias Python:
  - Fixed in d9d97731: type apps are held per root command (a local dict in _lazy_builders, shared by a type and its aliases); _type_app, drop_type_apps and the fixture's call are gone, so _build_command.cache_clear() alone gives a fresh tree. The F54 test passes; building from the active spec again makes it fail alone and after a bug --help test (-n 0). Vulture shows nothing new.
- [2026-10-29T11:49:30Z] `manager` Catherine Manager:
  - Verified on 3ebdf978: drop_type_apps and the module-level _type_app cache are gone (grep over src, tests, conftest.py is empty); the type-app cache is local to _lazy_builders; full suite 1655 passed, pyright 0, ruff clean.
<!-- sq:finding:F60:discussion:end -->
<!-- sq:finding:F60:end -->

<!-- sq:finding:F61 -->
### F61 — Stability Tier 5 says backends self-register on import; the registry is a literal table

<!-- sq:finding:F61:body -->
`docs/stability.md`, Tier 5 (line 1155): "Backends self-register on import; see backends.md for the registration hook and a worked example." Neither half is true. `src/squads/_backends/_registry.py` is a literal `MappingProxyType` table of the two built-in backends ("A new backend is a row here"); nothing registers on import, and `docs/backends.md` § "Registering one" tells the reader to add a row to that table, not to call a hook.

Fix: "The backends are a literal table in `_registry.py`; see [backends.md § Registering one](backends.md#registering-one) for adding one and a worked example." The writer flagged the line on TASK-1234 but left it. Note for the same paragraph: "the same conformance suite a third-party backend is held to" sits oddly beside a closed table, since a third party adds a backend by editing the package; worth a look while the sentence is open.
<!-- sq:finding:F61:body:end -->

#### Discussion

<!-- sq:finding:F61:discussion -->
- [2026-10-29T12:26:19Z] `tech-writer` Theo Writer:
  - Fixed (uncommitted): Tier 5 now says the backends are a literal table in `_backends/_registry.py`, that adding one is a class plus a row there (a change to the package), and links backends.md § "Registering one". The "conformance suite a third-party backend is held to" claim is gone (no such suite under tests/), and "A third-party backend written against the documented seven" reads "A backend …". Checked against `_registry.py` and backends.md.
- [2026-10-29T12:28:33Z] `reviewer` Paul Reviewer:
  - Verified at 28fc68cc: Tier 5 now names the literal table in _backends/_registry.py and backends.md Registering one; the seven methods match the 7 abstract methods in _backends/_base.py.
<!-- sq:finding:F61:discussion:end -->
<!-- sq:finding:F61:end -->

<!-- sq:finding:F62 -->
### F62 — Display keys documented as one shape; roster, statuses, sub-entity rows and show's summary differ

<!-- sq:finding:F62:body -->
`docs/stability.md` Tier 3 "Display keys" describes one `display` content for "every item row, tree and graph node, search hit, sub-entity, roster row and `workflow statuses` row": `type`, `status: {badge, intent}`, `badges`, the assignee's name. The CHANGELOG `display` entry says the same. Measured on a scratch squad with the dev tree:

- `role list --json` row: `display` is `{name, pronouns, live}`: no `type`, `status` or `badges`, and `live` is documented nowhere.
- `workflow statuses --json` row: `display` is `{intent}` only.
- sub-entity list rows (`sq task N subtasks --json`) carry no `display.kind`; only the single sub-entity entry does (`kind: {name, label, plural, heading}`). The CHANGELOG says "a sub-entity carries its kind's label, plural and heading"; stability's narrower "on a sub-entity's `show`" is closer.
- `show --json` `display` carries `summary` (`{kind, columns, rows}`, where `columns` is a list of header strings), undocumented, and it contradicts the stated `columns` shape of `{key, header}` objects.
- "Role and operator names in it follow `[display] pronouns`": `display.assignee` on an item row is the bare name (`Robert Architect`) with pronouns on or off. Only roster `display.name` and the tree node's `display.pronouns` follow the setting.
- CHANGELOG: "A table or listing carries `columns`". Under `--json` every listing prints only `items` and drops `columns`, except `dev list` (the one operation with `columns` and no `json_field`). Stability says so; the CHANGELOG does not, so an adopter running `sq list --json` finds no `columns`.

Since the display keys are frozen "once their shape is", the documented key set has to be the emitted one. Fix: state `display` per payload kind (item-like rows, roster rows, statuses rows, sub-entity entry versus row, show's additions including `summary`), and add the HTTP-only caveat for `columns` to the CHANGELOG.
<!-- sq:finding:F62:body:end -->

#### Discussion

<!-- sq:finding:F62:discussion -->
- [2026-10-29T12:26:22Z] `tech-writer` Theo Writer:
  - Fixed (uncommitted): stability Tier 3 "Display keys" is now a per-payload table measured on a scratch squad (item row, show incl. `summary` {kind, columns as header strings, rows}, tree node, graph node, sub-entity list row without `kind`, one sub-entity with `kind`/`discussion`, role list {name, pronouns, live}, operator/dev list {name, pronouns}, role/skill/operator show, refs {kind}, workload {assignee}, statuses {intent}); `columns` is its own paragraph saying only `dev list` carries it under --json. CHANGELOG display entry rewritten to match, with the --json caveat for `columns`. Pronouns: only roster `display.name`/`display.pronouns` and the tree node `display.pronouns` are documented as following `[display] pronouns`; `display.assignee` on item rows stays the bare name with pronouns on or off (measured), which I left undocumented as a possible defect against ADR-1224 point 5, for routing.
- [2026-10-29T12:28:35Z] `reviewer` Paul Reviewer:
  - Verified at 28fc68cc: every row of the per-payload display table matches the display annotation of its DTO (all 23 DTOs that carry display enumerated); show summary is null on a milestone; dev list is the one --json document with columns. One payload the table leaves out is filed as F67.
<!-- sq:finding:F62:discussion:end -->
<!-- sq:finding:F62:end -->

<!-- sq:finding:F63 -->
### F63 — CHANGELOG lead-badge entry: tree shows the next declared field's badge, not none

<!-- sq:finding:F63:body -->
CHANGELOG, Changed: "On a type whose override no longer declares `priority`, `sq tree` and `sq graph` show no badge and the Priority cell is empty". This holds only when `priority` was the type's only field. Reproduced: a bundled `bug` (priority high, severity low), with an override that leaves `fields = [{ code = "severity", ... }]`, shows `BUG-23 🟢 low · Bug one` on `sq tree`, which is the severity badge, the first declared field, as the first sentence of the same entry says. The Priority cell is empty, as stated.

`docs/overrides.md` "Where a field's badge shows" states the rule correctly. Fix: drop "show no badge" or narrow it to "show the next declared field's badge, or none".
<!-- sq:finding:F63:body:end -->

#### Discussion

<!-- sq:finding:F63:discussion -->
- [2026-10-29T12:26:25Z] `tech-writer` Theo Writer:
  - Fixed (uncommitted): CHANGELOG now says the Priority cell is empty and tree/graph show the next declared field badge, or none when the type declares no other. Reproduced: bug with priority high and severity low, override `[items.bug] fields = [severity]`: tree `BUG-24 🟢 low · Bug one`, list Priority cell empty. overrides.md "Where a field badge shows" had the same "shows none" clause; corrected likewise.
- [2026-10-29T12:28:38Z] `reviewer` Paul Reviewer:
  - Verified at 28fc68cc: the CHANGELOG and overrides.md now say the next declared field leads; matches the bug override probe (severity badge shown, Priority cell empty).
<!-- sq:finding:F63:discussion:end -->
<!-- sq:finding:F63:end -->

<!-- sq:finding:F64 -->
### F64 — Provisional write fields list omits nothing_to_clear and view

<!-- sq:finding:F64:body -->
Stability Tier 3, provisional list: "what the command reports is a field beside it (`severed`, `changed`, `cleared`, `was_present`, `target`, `kind` on `ref add`, `kinds` on `ref rm`)". This reads as the full set, but it omits fields the DTOs emit:

- `nothing_to_clear` on item `update` (`ItemUpdated`) and sub-entity `update` (`SubentityUpdated`); `sq task N update --priority high --json` prints `{entry, nothing_to_clear}`;
- `view` beside `changed` and `was_present` on `view add` and `view disable` (`ItemViewChanged`);

Provisional or not, the key names are what a client binds to. Fix: list them, or mark the parenthesis "such as" (as the CHANGELOG does) and point at the command reference.
<!-- sq:finding:F64:body:end -->

#### Discussion

<!-- sq:finding:F64:discussion -->
- [2026-10-29T12:26:27Z] `tech-writer` Theo Writer:
  - Fixed (uncommitted): the provisional list now has a table of the fields beside `entry`, printed from every `_api/_dto` model with an `entry` field: nothing_to_clear (item/sub-entity update), target+kind (item ref add, skill ref add/rm), target+kinds (item ref rm), old_id/old_status/status_reset/rewritten (retype), view/changed/was_present (view add/disable), severed (role/skill/operator status), changed/cleared (set-default), role (link-role/unlink-role, memory add/forget), prefilled (override scaffold); every other one-resource write answers {entry}. Spot-checked override scaffold, link-role, operator status and view add on the scratch squad.
- [2026-10-29T12:28:40Z] `reviewer` Paul Reviewer:
  - Verified at 28fc68cc: the fields-beside-entry table matches every operation whose response has entry (47 enumerated), and every unlisted one answers {entry} alone.
<!-- sq:finding:F64:discussion:end -->
<!-- sq:finding:F64:end -->

<!-- sq:finding:F65 -->
### F65 — CLAUDE.md lists RetypeOpsMixin second while claiming MRO order; it is fourth

<!-- sq:finding:F65:body -->
CLAUDE.md, `_services/` paragraph: "the concern **mixins** that are the 20 `Service` bases, in MRO order: ... (`ItemWriteOpsMixin` and `RetypeOpsMixin` in `_item_write_ops`, `ItemReadOpsMixin` ..., `RosterOpsMixin` ..., `ItemOpsMixin` ...". `Service.__mro__` (and the class statement in `_services/_service.py`) runs ItemWriteOps, ItemReadOps, RosterOps, **RetypeOps**, ItemOps, SquadStateOps, CorpusOps, then Import ... Views. Grouping the two `_item_write_ops` classes puts `RetypeOpsMixin` second instead of fourth. The count (20), the domain-mixin tail and every module named are right.

Fix: list in MRO order with the module after each name, or drop "in MRO order".
<!-- sq:finding:F65:body:end -->

#### Discussion

<!-- sq:finding:F65:discussion -->
- [2026-10-29T12:26:30Z] `tech-writer` Theo Writer:
  - Fixed (uncommitted): CLAUDE.md lists the operation mixins in `Service.__mro__` order, printed from the code: ItemWriteOps (_item_write_ops), ItemReadOps, RosterOps, RetypeOps (_item_write_ops), ItemOps, SquadStateOps, CorpusOps, then the 13 domain mixins.
- [2026-10-29T12:28:43Z] `reviewer` Paul Reviewer:
  - Verified at 28fc68cc: the list now runs ItemWriteOps, ItemReadOps, RosterOps, RetypeOps, ItemOps, SquadStateOps, CorpusOps, matching Service.__mro__.
<!-- sq:finding:F65:discussion:end -->
<!-- sq:finding:F65:end -->

<!-- sq:finding:F66 -->
### F66 — CONTRIBUTING.md still describes registration side-effects and wiring commands onto app

<!-- sq:finding:F66:body -->
The commit brings CLAUDE.md and docs/internals.md onto the operation layer, but CONTRIBUTING.md still describes the removed structure:

- line 72-73: "`_backends/_claude_code/__init__` the registration side-effect": that `__init__` is a one-line docstring, and the backends are a literal table in `_registry.py`;
- line 162-163, "How to add things", **A command**: "wire it onto `app` in `_cli/__init__`, and route logic through `Service`". A command now builds a request DTO and calls an operation through `_calls.call`; the operation is a row in `_api/_ops.py` bound in `_services/_bindings.py`; a new command group is a `LAZY_GROUPS` row, which `tests/meta/test_lazy_command_groups_match_the_typer_groups.py` holds.

It is contributor-facing, not adopter docs, but it is the page a new contributor follows to add a command. Fix: rewrite both lines to the operation path.
<!-- sq:finding:F66:body:end -->

#### Discussion

<!-- sq:finding:F66:discussion -->
- [2026-10-29T12:26:32Z] `tech-writer` Theo Writer:
  - Fixed (uncommitted): CONTRIBUTING.md Conventions now names the backends literal table (no registration on import) and `squads._services._service`; "How to add things / A command" is the operation path: DTOs and the Operation row in `_api/_ops.py` + OPERATIONS, the handler on a `_services/_*_ops.py` mixin bound in `_bindings.py`, the CLI calling `calls.call`/`print_json`/`finish`, top-level commands on `app` in `_main.py`, a new group as a LAZY_GROUPS row held by its tests/meta guard, and its tests/cli cases.
- [2026-10-29T12:28:45Z] `reviewer` Paul Reviewer:
  - Verified at 28fc68cc: calls.call, calls.print_json, calls.finish, Operation.grant, the json_field guard, @app.command in _cli/_main.py and LAZY_GROUPS all exist as described; the registration side-effect line is gone.
<!-- sq:finding:F66:discussion:end -->
<!-- sq:finding:F66:end -->

<!-- sq:finding:F67 -->
### F67 — Per-payload display table has no row for add-<kind>, which gains display {item, body_command}

<!-- sq:finding:F67:body -->
The per-payload `display` table in `docs/stability.md` Tier 3 (added in 28fc68cc) says `display` "holds one of these sets, by payload", but one payload that carries `display` has no row: the answer of `add-<kind>` (`SubentityAdded`, `AddedDisplay`) carries `display: {item, body_command}`. Measured on a scratch squad:

- dev tree: `sq task 22 add-subtask "Three" --json` prints `{local_id, path, region, start_line, end_line, display: {item: "TASK-22", body_command: "sq task 22 subtask ST3 body -m \"…\""}}`;
- released 0.17.0: the same command prints `{local_id, path, region, start_line, end_line}`, with no `display`.

So `add-<kind>` gains a key in this release, appended last as the rule asks, but neither the table nor the CHANGELOG names it. Smaller point in the same table: a sub-entity `update`'s `entry` carries the "one sub-entity" set (`kind`, `discussion`), not only `<kind> <k> show`. Fix: add an `add-<kind>` row (`item`, `body_command`), and widen the one-sub-entity row to the sub-entity writes' `entry`.
<!-- sq:finding:F67:body:end -->

#### Discussion

<!-- sq:finding:F67:discussion -->
- [2026-10-29T12:35:28Z] `tech-writer` Theo Writer:
  - Fixed (uncommitted): stability display table gains an `add-<kind>` row (`item`, `body_command`), and the one-sub-entity row now covers the `entry` of sub-entity `update` and `body`; the CHANGELOG display entry names both. Checked at bd7aab88: `sq feature 21 add-story --json` gives `display: {item: "FEAT-21", body_command: "sq feature 21 story US2 body -m \"…\""}`; `subtask 1 update --json` and `subtask 1 body --json` entries carry `kind` and `discussion`. Same round: `display.assignee` following `[display] pronouns` is in the CHANGELOG pronouns entry, stability (Display settings and the table note) and roles.md, verified on list/graph/search/sub-entity update (on) and list/tree (off).
- [2026-10-29T12:35:54Z] `manager` Catherine Manager:
  - Verified: the stability display table has the add-<kind> row (item, body_command) and the one-sub-entity row covers update/body entries; the writer's dev-tree run printed both shapes.
<!-- sq:finding:F67:discussion:end -->
<!-- sq:finding:F67:end -->
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
- [2026-10-29T04:29:19Z] `architect` Robert Architect:
  - Rulings on the test audit (35950c3), 2026-10-29.
  - Covers markers: ADR-1172 rule 3 is amended. The key-only marker declares the bare call on any leaf, every `tests/cli/` test carries a marker, and the guard and fixture enforce both. Steps for @python-dev are on F29.
  - `json_field` `ALLOWED`: it stays a literal list, now documented in ADR-1224 point 3 as a deliberate contract tripwire. It never grows, and it shrinks only through a schema change that amends the ADR. No derivation, since nothing in the code records which documents Tier 3 froze.
  - `[display] pronouns`: the output is right and the doc is wrong. The names in `display` are presentation, so they follow the setting on every surface (ADR-1224 point 5, amended). @tech-writer: the doc correction is on TASK-1234.
- [2026-10-29T04:53:23Z] `architect` Robert Architect:
  - @python-dev Rulings on the audit-fix questions (ADR-1172 rule 3, amended 2026-10-29).
  - (1) A refusal case declares the parameter the refusal is about: `test_title_is_required` becomes `covers("create <type>", "TITLE")`. The `invoke` fixture records `(key, param)` for the parameter a Click `MissingParameter`/`BadParameter` names, so the marker is checked against the call. Falsify once with a refusal case whose marker names another parameter. A refusal squads raises itself about an absent value declares the key alone, or the parameters the call passes.
  - (2) Move the 5 tests of `tests/cli/test_squad_fixtures.py` to `tests/meta/`, next to `test_squad_copies_are_isolated_in_any_order`. They guard the suite's fixtures and run no command, so they carry no marker.
  - (3) Confirmed: both are rule 5 violations, and they get fixed in this round. Assert the whole `tree --json` document as text, and the whole pointer file in the `role add` case (rule 5 allows reading generated files), not a substring.
- [2026-10-29T04:55:55Z] `reviewer` Paul Reviewer:
  - - TASK-1229 (90e64424) reviewed. New: F32 (medium); F33, F34 and F36 (low); F35 and F37 (info). F31 gains a fourth instance, and F26 item 1 is verified.
      - **Held up: parity.** I compared d9916956 and 90e64424 side by side on one scratch squad. It has an override with a custom `incident` type and its `inc` alias, its own `step` sub-entity kind with a badge field on a new `impact` collection, two labelled attributes, a custom ref kind and a playbook entry, plus an operator and comments on all five hosts. Each tree ran 224 command lines under a fixed `--at`:
        - create: every option, aliases, guide, `--file`, stdin, and 12 refusals;
        - `update`: every flag with its clear and `no-` forms, `--force`, and a repeated and combined `--clear-assignee`;
        - `status` with and without `--force`;
        - `body`: set, refused replace, `--force`, `--append`, `--file`, stdin, a missing file, and a marker in the text;
        - refs (an embedded kind, the custom kind, refusals) and views;
        - comment add, show, edit and remove by short and full hash on items, sub-entities, roles, skills and operators, with refusals;
        - sub-entity add, update, body and remove, including a deferral and the custom kind;
        - retype (an id change, a status reset, rewritten refs);
        - item and sub-entity remove, answering y, n, or `--yes`.
        
        The new `--json` lines ran without the flag on the parent.
      - **Results.** 189 lines are byte-identical on stdout, stderr and exit code, with the same set of changed files after each one. 11 `--json` documents only append keys. The 24 that differ are all explained: 21 are the new `--json` flags, plus the F26 refusal order, the `comment --json HASH show` usage error, and F34's two prompts. The final tree (item files, `.squads.json`, `.reflog.jsonl`, CLAUDE.md, AGENTS.md, `.claude/`) is byte-identical.
      - **Confirmed removal.** I ran a concurrent edit between the preview and the remove call (a wrapper around `_calls.call`). The remove refuses, and the edited comment remains. Answering n prints the listing once, then `Aborted.`, and nothing else. A `--yes` call resolves the typed prefix. The wire type of that refusal is F32.
      - **MRO.** `ItemWriteOpsMixin` first and `RetypeOpsMixin` after `RosterOpsMixin`: every Service attribute present at d9916956 resolves to the same class at 90e64424. No new name shadows another base, and 54 attributes are new.
      - **Deletions.** None of the 15 deleted helper and bridge names has a hit in src or tests. `_create.py` and `_items.py` reach no service: no `get_service` and no `svc`. So the shorter pending list is real. `named_markup` still has no caller, which is F26/TASK-1232's.
      - **`status --json`** is `{entry: ItemRow}`, as ruled.
      - **Deviations.** (1) Parse refusals first: accepted, the same as TASK-1227 and TASK-1230. (2) The prompt before the refusal is F34: within ADR-1224 point 1 as written, but Context 7's premise is wrong. I recommend keeping one call, with a changelog line. (3) Additive keys: accepted, and checked key by key in the parity run. (4) The `…/removal` route is F35, for an architect ruling.
      - @python-dev: F32, F33 and F36. @architect: F34 (Context 7), F35 (the route row) and F37 (the shape), and F36 if the refusal form is preferred. @tech-writer: F34's changelog line.
      - The review stays ChangesRequested.
- [2026-10-29T05:00:20Z] `python-dev` Elias Python:
  - The rulings in 3ee1e6b are applied in f450241b, on top of 80ddec81.
    - Refusals: the `invoke` fixture (`reached_pairs`) records the required parameter that Click's missing-parameter error names at the leaf: the first one Click processes that the call leaves out. A parameter given a bad value was already reached. 12 Click refusals now declare the parameter they refuse, e.g. `test_title_is_required` is `covers("create <type>", "TITLE")`. Refusals that squads raises itself keep the key alone or the parameters they pass.
    - `tests/cli/test_squad_fixtures.py` moved to `tests/meta/test_the_squad_fixtures_hold_what_they_promise.py`, without markers.
    - `tree --json` asserts one whole document (`tree 2 --json --depth 1`). `role add` compares the whole pointer file.
    - Falsified:
      - `covers("renumber", "--by")` on `test_from_is_required` fails at teardown.
      - Without the fixture change, all 12 re-marked cases fail.
      - One mutation in the tree document turns its case red.
      - One mutation in the pointer turns its case red.
    - Count: unchanged at 1630.
- [2026-10-29T05:08:10Z] `reviewer` Paul Reviewer:
  - Recheck of the ADR-1172 audit (comment 35950c3) on 3e312c1c: F27 to F31 Verified. All 18 items fixed. 827 of 827 tests/cli tests carry a marker. Removing a marker fails the coverage guard. Four mutations on a copy all turn red (two pronouns switches, lead badge, marker removal).
  - Sweep of 73454c4c and 3e312c1c: no new partial assert, substring, ANY, or expected value built from CLI output. Net growth is +8 tests beside TASK-1229 (+3 split show cases, +3 tree, +1 dev, +3 guard, -1 init, -1 replaced workflow view), as stated.
  - New F38 (low): the dev's fixture caveat is a real hole. Ten refusal cases for a missing option checked in the command body (--as, -m/--file, --force, role add fields) declare an incidental parameter. @architect @python-dev
  - Still open: docs/stability.md (Display settings) still says --json is unchanged by [display] pronouns. @tech-writer
- [2026-10-29T05:26:59Z] `reviewer` Paul Reviewer:
  - Round 2 of TASK-1229 checked on ed499a68: F32, F33, F37 and F38 are Verified (probes and mutations re-run), and F34 and F35 are Noted as ruled. F36 is reopened: Click's confirm(err=True) still writes one space byte to stdout, so the cases pin that byte plus the runner's echo. Details are on F36. @python-dev F36. The review stays ChangesRequested.
- [2026-10-29T06:07:49Z] `reviewer` Paul Reviewer:
  - - I reviewed TASK-1233 (611c505e, against 658ed963). New findings: F39 (medium); F40, F41 and F42 (low); F43, F44 and F45 (info).
      - **Held up: headless parity.** I extended the dev's pilot capture so that it drives the real `sq ui` with a fixed `--at`. I ran it on 3 squads at both commits:
        - the main squad: a custom `incident` type with an `impact` collection, roles with and without pronouns, an operator, two skills sharing role slugs, closed and cancelled items, a mapped subtask, an edited operator comment, memories on 3 notebooks, and 2 notices;
        - the same squad with `[display] pronouns = false`;
        - the same squad with a corrupt item file.
      - **What the capture covered.** Every tree label with its spans, the reader for every node, every memory entry, the board, 6 searches (type, status and closed-status filters, no hit, opening a hit), the filter choices, 17 filter states and 7 sorts with closed items shown.
      - **Results.** Everything is identical except for the explained differences: the closed-status filter and the unknown-assignee toast (both in the handback), plus F44's two.
      - **Held up: refusals.** Outside a squad, a bad override, a schema behind and a corrupt item give the same stderr and exit code at both commits. On a corrupt index, 658ed963 started the app and crashed inside it with a traceback (exit 0). 611c505e refuses cleanly before the app starts (exit 1). So `open_session` running first is a fix.
      - **Held up: imports.** `import squads._tui._app` loads no `_services`, `_workflow`, `_paths`, config model or `_cli`. The guard fails on direct imports of `_cli._common`, `_cli._calls` and `_services`. Transitive reach is F42.
      - **Pronouns.** On 658ed963, a skill sharing a role's slug carried that role's pronouns on `tree --json`. The fix is confirmed but unpinned: F43.
      - **Deviations.**
        - Catalogs load once: accepted, since TASK-1219 owns the reload.
        - Opening view preloaded: accepted.
        - The DTO fields: see F39, F40 and F41.
        - Pronoun gate: accepted, see F43.
        - Closed items under a closed-status filter: accepted.
        - Unknown-assignee toast: accepted.
        - 0 tests: accepted under ADR-1172. F41 asks for one surface case if `--label` is added.
      - **Questions to route.** @architect: F39 (the key's name), F40 (where an added key goes) and F41 (`sq tree --label`). @python-dev: F42 and F45. @tech-writer: changelog and stability doc lines for F40, F43 and F44.
      - ST2 stays InProgress for the operator's eye-check. The review stays ChangesRequested.
- [2026-10-29T06:49:43Z] `reviewer` Paul Reviewer:
  - TASK-1232 (d40232df) reviewed. Findings F46 to F52. Recommended verdict: changes requested for F46. The others are low or info.
    
    Parity, 658ed963 against d40232df, both extracted and run from one scratch path with `--at` frozen and FORCE_COLOR on. For each squad: 43 command lines (repair, repair --renumber, renumber with --by, --onto and the refusals, migrate up/repad/rename-type/rename-status/help/chlog, import dry-run, applied, refused, error-finding, missing-file and stdin, init with --force, --roles and bundles, adopt, plus check, sync, docs, show, list, a status move, a create, override list/scaffold and the bare groups). Ten squads: current, behind (v0.16), ahead (v9.9), corrupt index, broken workflow override, unreadable item file, duplicate id, number collision, unrecognised working language, and the v0.14 fixture. After every line I compared stdout, stderr, the exit code and a hash of the whole tree, reflog and index included. A further 27-line `--json` set ran on seven of those squads.
    
    - Every tree is identical on all 457 runs. Writes are identical, and every refused write wrote nothing.
    - Output is identical except: `renumber --from` without --onto/--by and `import <missing file>`, which now give the usage or file error before the gate; `docs`, which runs on a mismatched squad; and the working-language notice lost on refused calls (F48).
    - `migrate up` on the v0.14 fixture is byte-identical, tree included. `repair --renumber` on a collision and both commands on the corrupt-index and broken-override squads are identical too.
    - `--json`: every new document parses as one JSON object on stdout. On behind and ahead squads every `--json` form refuses with the gate text on stderr and an empty stdout. With a duplicate id, `show --json` now prints the same duplicate warning on stderr that human mode prints, and stdout is unchanged.
    
    Verdicts on the deviations:
    
    - Usage errors before the gate: not a hole. Nothing reaches a write before the call, and no module under `_cli` or `_tui` writes a file.
    - Bare `migrate`/`override` exit 2 with usage: identical to 658ed963 on every squad.
    - `docs` on a mismatched squad: matches ADR-1225 ("a command that makes no call: docs, migrate help, migrate chlog"). It reads only package data. Fine.
    - `import <missing file>` named before the gate: it is the client's file read (ADR-1225 section 2) and writes nothing. Fine.
    - `--json` warnings on stderr: correct. Stdout stays one document, and the duplicate-id and language notices are what a scripted caller should be told.
    - The notice deviation is broader than the handback says: see F48.
    - init/adopt through `LOCAL_BINDINGS` build no service. `init --force` on a behind or ahead squad is still refused with the gate text, but only after the role-name prompts (F49).
    
    What held up: the grant guard goes red when local-only operations skip the gate. The `init --json` and `--json` warnings cases go red when their fix is reverted. `sq ui` on a behind squad still exits 1 with the gate text. Composition matches ADR-1128 and the F16 ruling (F52). `vulture` on `_cli` adds nothing new.
    
    @tech-lead for routing F46-F52. @tech-writer: F50 lists the stale CLAUDE.md, docs/internals.md and docstring mentions.
- [2026-10-29T07:11:23Z] `reviewer` Paul Reviewer:
  - Round 2 of TASK-1232 (dcc42a00) checked: F46, F48, F49, F50 and F51 are Verified. F47 is reopened: its guard is a denylist, and board, memory, backend and reflog writers, as well as Path.open("w"), all pass it. @python-dev for F47. F48 has no test holding it; the evidence is on the finding.
- [2026-10-29T07:37:22Z, edited 2026-10-29T07:38:23Z] `reviewer` Paul Reviewer:
  - Round 4 of TASK-1232 (ec833f5a) checked: F52 is Verified, behaviour unchanged. F47 stays Verified (Verified is final in the finding lifecycle), and its remaining gap is now F53, low: a standard-library writer imported by name (from os import unlink, from shutil import rmtree) passes the write guard. @python-dev for F53.
- [2026-10-29T10:09:20Z] `reviewer` Paul Reviewer:
  - - I rechecked the TASK-1233 fixes on 06b8982c (e0a97f6d), on a scratch copy, with targeted tests at `-n 2` (control: 106 passed).
      - F39, F40, F41, F42 and F43 are Verified. Each was shown by a CLI probe and by a mutation that turns its case red. F42's closure guard also goes red on an indirect import through a DTO module and on a literal `importlib` call.
      - F45 is reopened: the TUI's top-level group order now follows the adopter's type `order`. With guide at `order = 5`, the groups read Records, Work, Roster. @architect, please rule (a) or (b) on F45.
      - Headless parity at 06b8982c against 611c505e, with the bundled spec: identical apart from the filter's category order, which the dev reported.
      - The stability doc and changelog lines are not in this commit. They are listed on TASK-1234 for @tech-writer.
      - F25 and F44 stay Open. ST2 still waits for the operator's eye-check. The review stays ChangesRequested.
- [2026-10-29T12:21:48Z] `reviewer` Paul Reviewer:
  - - Docs commit 145cd933 (TASK-1234) reviewed against the dev tree on scratch squads. Findings: F61-F66 (1 medium, 5 low). @tech-writer for the docs lines, @tech-lead for disposition.
    - Verified as stated: `{entry}` on `status`; `{entry, target, kind}` / `{entry, target, kinds}` on `ref add`/`ref rm`; `{override, errors, warnings}` on `workflow lint`; `ui --json` and `workflow --json` exit 2; the 36 `json_field` operations match the Tier 3 list (8 catalogs, `source` for `workflow view`); `dev list` is the one listing that prints `columns`; tree node key order (`display`, `notebook`, `closed`, `updated_at`) and `display.{dimmed, anchor, pronouns}`; graph `display.{edge, edge_label}`; refs `display.kind`; `tree --label` dims ancestors; `[display] pronouns = false` on roster `display.name` and tree `display.pronouns`, with the roster `pronouns` key unchanged; the `display`/`title`/`views`/`extra` refusal texts; a badge field named `display` refused; the attribute `label` on `show`, `display.attributes` and `workflow types --json`; exit 2 for skill/memory with the argument missing; `role catalog` on a malformed toml exits 1 for both outputs; `role show --json` on a missing file exits 1; view render failure exits 0 with the warning; the `sq check` compile finding; removal prompt on stderr with stdout empty; `init --json` under a pty does not prompt; `_spans.py` names and marks; the benchmark flags and runbook steps; every module, guard file, `LAZY_GROUPS`, `check_grant`, `VOCABULARY_FALLBACKS` and `Mode` member CLAUDE.md names. No sq IDs or dev-process text in the added adopter-doc lines.
    - Not in this review's scope, raised for @qa: `sq workflow view <name> SKILL-2 --json` resolves a wrong-prefix id to whatever item has number 2 (ROLE-2 here), where `sq show SKILL-2` refuses with "SKILL-2 is ROLE-2 (role)". The released 0.17.0 behaves the same, so it is not a regression.
<!-- sq:discussion:end -->
