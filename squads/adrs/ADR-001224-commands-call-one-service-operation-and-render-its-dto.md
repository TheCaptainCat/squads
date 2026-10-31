---
id: ADR-1224
sequence_id: 1224
type: decision
title: Commands call one service operation and render its DTO
status: Accepted
author: architect
refs:
- FEAT-1140
- MILE-1152
- ADR-1052
- ADR-1225
- ADR-1261
description: Each command validates, calls one operation through an Api (local or
  HTTP) and renders the DTO it returns; --json prints the DTO; the CLI never imports
  the service
created_at: '2026-10-28T20:58:31Z'
updated_at: '2026-10-30T20:27:15Z'
---
<!-- sq:body -->
## Context

The operator set the 0.18 architecture on 2026-10-28 (FEAT-1140, comment b4c77e9; MILE-1152, comment e7119a6): a CLI command validates its inputs, calls the service once where that is possible, and hands the result to the CLI renderer. The renderer never calls the service: it receives DTOs that carry what it displays, and the `--json` payload comes from those DTOs, not from CLI-side builders. The same release serves those results as the daemon's resource endpoints; that half is decided in ADR-1225.

What the code does today, read on `release/0.18` at 44389bb4 on 2026-10-28:

1. **Size.** `src/squads/_cli/` is 10,099 lines, `_common.py` 2,703 of them. It defines 113 command functions: 110 registered by decorator, plus `create <type>`, `add-<kind>` and the sub-entity `update`, registered by call. ADR-1172 folds the 267 leaf commands onto about 111 keys; the 113 functions are those keys plus the group callbacks.
2. **Service calls per command,** measured statically: an AST walk from each command function through every `_cli` helper it calls, counting the distinct `Service` methods reached. Branches are all counted, so this is an upper bound on what one run does.
   - Leaving out roster lookups: 34 functions reach no service method, 57 reach one, 12 reach two, 7 reach three or more. `sq <type> <n> show` and `sq show` reach eight (`get`, `read_body`, `read_stored_body`, `read_discussion`, `comments`, `view_data`, `get_block` once per sub-entity, `duplicate_id_error`). `tree` calls `tree_view`, plus `list_items` for the hidden count and `blocked` for `--json`. `workflow view` reaches eight.
   - 44 functions resolve an `--as`, `--author` or `--assignee` slug against the roster (`roster`, `roster_all`, `operators`, `operators_all`, `roster_item`) before making their own call.
   - Every `sq <type> <n> …` verb is preceded by the group callback, which resolves the number against the store. So `command` crosses the sync/async bridge twice, and `get_service` memoises the service on the Click root context so that both crossings share it.
3. **Rendering calls the service.** 22 functions in `_common.py` call it directly, at 40 sites, among them `print_item`'s content, discussion and sub-entity panes, `build_item_json`, `build_role_json_payload`, `warn_duplicate_id` and the id resolvers. 23 `_cli` functions take a `Service` parameter.
4. **`--json` is assembled in the CLI**, from `Item.to_row()` plus added keys (`build_item_json`, `build_item_row_json`, `build_subentity_json`, `build_role_json_payload`, `_mine_row_json`, `_view_json_payload`, and others), and is printed by `print_json_clean` as `json.dumps(obj, indent=2)`. Tier 3 of `docs/stability.md` freezes each key's name, JSON type, presence and meaning, and for `search`, `tree` and `graph` the emitted order. A partial read prints its bare array on stdout, one `{"omitted": [...]}` line on stderr, and exits 4 (ADR-947). On ADR-1172's 111 coverage keys, 47 accept `--json` and 64 print only human text (recounted on 2026-10-28 from the live command tree).
5. **Result types.** `_services/_results.py` holds 35 result classes. Several carry the storage model `Item` (`TreeNode`, `SubentityDetail`, `CreateResult`). Others are already flat data (`SearchHit`, `WorkloadRow`, `ReflogEntry`, `InboxLine`).
6. **The service never prints.** No module under `_services/` or `_migrations/` writes to a console, so a command's output already exists only once its calls have returned.
7. **Prompts.** Four sites. Item removal and sub-entity removal ask without showing squad data, after the item group callback has resolved the address and the `--as` slug has been checked, so a bad address or slug is refused before the prompt. Comment removal first calls `find_comment`, lists the comments it is about to remove, then asks. `init` asks for role names before the squad exists.
8. **Other callers of the service.** The TUI (`_tui/`, eight modules, 1,107 lines) is read-only. `sq ui` builds a `Service` through `get_service` and hands it to the app, whose screens call 11 service methods: `tree_view` (with a filter and `include_closed`), `memory_list` once per role or operator in the tree, `roster_all` and `operators_all` for pronouns, `get`, `read_body`, `read_discussion` and `get_block` once per sub-entity for the reader, `memory_show`, `search` and `board_list`. They also read `svc.spec` (labels, the filter screen's choices) and `svc.paths.config.display.pronouns`, and the reader calls outside the read scope (ADR-753).
9. **Import cost,** measured on the dev tree on 2026-10-28 (3 runs each). `import squads._cli` takes 0.55-0.72 s, and `import squads._services._service` alone 0.50-0.53 s. `typer` plus `rich` take 0.08 s, `squads._workflow` with the bundled spec loaded 0.15 s, and `pydantic` alone 0.07-0.09 s. The released `sq task 1217 show` runs in 0.89-0.97 s end to end.

## Decision

### 1. One operation per command

A command does four things, in this order:

1. It parses its arguments and validates what the arguments and the vocabulary alone can decide: syntax, a type, status or badge code, mutually exclusive flags. These refusals keep exit code 2 and their current text. Parsing reads the vocabulary of the repository the command runs in. A command served by the daemon (ADR-1261) parses there, with the vocabulary the daemon loaded, which its retirement check ties to the checkout's files.
2. It builds one request DTO.
3. It calls one operation through the API layer (point 4).
4. It renders the response DTO.

Anything that needs squad data is the operation's job, not the CLI's:

- whether an addressed item exists and has the type the command named;
- whether an `--as`, `--author` or `--assignee` slug is on the roster;
- whether there is an assignee to clear;
- regenerating managed files after a roster write;
- the duplicate-id warning.

Group callbacks (`sq <type> <n>`, `<kind> <k>`, the roster addresses, the comment hash) only parse: a number becomes an id through the type's prefix, and nothing is called.

**What one command calls, after the change:**

| Shape | Commands | Calls | Why not one |
|---|---|---|---|
| Group callbacks, gates and refusal stubs | 12 | 0 | they parse; the operation checks existence and type |
| Package data (`docs`, `migrate help`, `migrate chlog`) | 3 | 0 | nothing in the squad is read |
| Reads: show, list, tree, graph, search, inbox, mine, blocked, workload, refs, comments, sub-entity lists and shows, role/skill/operator lists and shows, board, memory, workflow catalogs and views, overrides, reflog, check | 43 | 1 | |
| Writes: create, update, status, body, retype, remove, refs, views, comments, sub-entities, roster verbs, board, memory, override scaffold/update, sync | 45 | 1 | `comment remove` without `--yes` makes 2 |
| Corpus-wide: `repair`, `renumber`, `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status`, `import` | 7 | 1 | |
| Squad creation: `init`, `adopt` | 2 | 1, local only | they create the squad that a daemon is keyed on |
| `ui` | 1 | per screen, through `Api` | an interactive session (point 7) |

The one exception to a single call is `comment remove` without `--yes`. Its user confirms the comments shown before they go, so the command makes a preview operation (the comments the hash selects) and then the remove operation, which sends the full hash of the comments the user confirmed, so a comment edited or removed in between no longer resolves (ADR-1225, section 3). Neither the item removal nor the sub-entity removal prompt shows squad data, so each still makes one call. Since the address and `--as` checks move into that call, a bad address or slug is now refused after the answer rather than before the prompt; one keystroke on a command that removes nothing is cheaper than a preview round trip on every interactive removal. A prompt therefore always sits between two calls and never inside one.

### 2. DTOs

- **Where they live.** A new package, `squads/_api/`, holds the DTOs, the operation table, the API protocol, the HTTP client and the wire form of errors. It imports `pydantic`, `_models` (for `Omission`) and `_errors`, and nothing above them.
  - `_services` imports `_api` to build DTOs and to bind its handlers.
  - `_cli` imports `_api`. It imports `_services` in exactly one place: the function that builds the local API.
  - A `tests/meta` guard holds this: no `_cli` module other than that factory imports `squads._services`, at any position. The new edges are rows in the import-edge table.
  - This is what makes "the renderer never calls the service" structural, not a convention. It is also what keeps the TUI's remote path from paying the 0.5 s import of `_services` (fact 9). The CLI's remote client is the shim of ADR-1261, which imports no `squads` module beyond `_endpoint`.
- **Their form.** DTOs are pydantic v2 models, frozen, whose fields hold only JSON-native values: strings, numbers, booleans, `None`, lists, string-keyed objects and nested DTOs. Timestamps are the ISO strings the `--json` payloads print today. So `M.model_validate_json(m.model_dump_json()) == m` for every DTO, which is what lets the local API hand the object over directly while the HTTP API parses it from JSON, with the same rendering either way.
  - An item row carries the item's stored attributes flat at the top level, as `to_row()` does today, through `extra="allow"` on that one model.
  - So every key an item row adds is a name an attribute cannot take. The row adds one display key, `display`, and every display-class value an item row carries, now or later, goes inside it, never beside it: the body with its view tags expanded is `display.body` on `show`. The refactor therefore reserves one name and no more.
  - A collision is handled as for the keys already added (`badges`, `body`, `discussion`, `matched_subentities`, `views`): a workflow override that declares an attribute or a badge field named `display` is refused when the spec loads, with a message naming the type and the key, and a `display` key stored in an item file without a declaration stays in the file and out of the row. No migration renames such a key, since the new name is the adopter's to choose. `docs/stability.md` lists the reserved names in Tier 3's item rows, and the changelog names `display` with its refusal text and what to do, as it did for `views`. Reserving it needs no migration record and no schema bump.
  - Fields are declared in today's emitted order, which Tier 3 freezes for `search`, `tree` and `graph`.
- **Their relation to the models.** A DTO is a projection of `Item`, `SubEntity` and the other models, not a subclass of them, so the storage model can change without changing the contract. Projections are built in `_services`, where the data and the spec are. The flat dataclasses in `_results.py` become DTOs and move to `_api`; those that carry `Item` stay internal to the service and get a DTO counterpart.
- **Why pydantic, not dataclasses:** it is already a dependency. It validates a parsed response, so a client and a daemon that disagree fail at the boundary rather than in a renderer. And it exports a JSON Schema for each model, which the web front can turn into its types.

### 3. The response envelope, `--json` and exit codes

- Every operation returns `Response[T]`, with three fields:
  - `data: T`, the payload;
  - `omitted: list[Omission]`, the partial-read report of ADR-947, empty when nothing was left out;
  - `warnings: list[str]`, the notices the service has to pass on: the duplicate-id warning and the working-language notice.
- **`--json` prints `data`, or the one field of it that the operation names.** `data` is always an object, never a bare list, so a field can be added to any response, the HTTP body included. Where the document Tier 3 froze before 0.18 is not an object, the operation names in `json_field` (point 4) the field of `data` that holds that document, and `--json` prints that field alone. The fields beside it, such as `columns` and `hidden`, reach human mode and HTTP clients, not `--json`. Every other operation leaves `json_field` unset, and `--json` prints `data` whole. One CLI helper reads `json_field` off the operation, so no command chooses what it prints. The output goes through the same `json.dumps(…, indent=2)` as today. For the 47 commands that accept `--json`, the payload is today's document plus the display keys of point 5, which Tier 3's additive rule permits; where the document is an array, the keys are added to its rows.
  - **The commands that name a field** are those whose frozen document is an array, plus `workflow view`, whose document takes the shape of the view's source. The field is `items` where it holds rows and `source` for `workflow view`. By increment (point 8): 0, `list`; 1, `tree` (its root nodes), `search` (its hits), `inbox`, `mine`, `blocked`, `workload`, `<type> <n> comments` and the sub-entity lists (`<type> <n> <kinds>`); 2, `<host> comment <hash> remove` (the comments removed); 3, `role catalog`, `role list`, `operator list`; 4, `board list`, `memory list`, `memory search`, `override list`, `override diff`, `reflog`, `check`, the eight `workflow` catalogs and `workflow view`. That is 29 keys, and the set is closed: a shape new in 0.18 is an object and names no field.
  - A `tests/meta` guard checks that each `json_field` names a field of the operation's response type and that only an operation of these commands sets one. The guard holds those operations in a literal list on purpose: it is a contract tripwire, not a derived rule, because the set is fixed by what Tier 3 froze before 0.18 and nothing in the code records that. The list never grows, and it shrinks only through a schema change to one of those documents, which amends this point. `omitted` goes out as today's stderr line, followed by exit 4. Human mode renders `data` and prints `warnings` on stderr.
- **Exit codes come from the DTO:** 3 when a `check` or `import` report holds findings, 4 when `omitted` is not empty on a command of the partial-result class. A `SquadsError` is still exit 1, and usage errors are still exit 2.
- **One definition, one contract.** The DTO is the only definition of both the `--json` payload and the HTTP body, so the two cannot drift. The HTTP body is the whole `Response` with `data` whole, so a client of the daemon gets `columns` and `hidden` beside the rows, while `--json` prints `data` or the one field of it the operation names. Tier 3's additive rule applies to the DTO classes: a field may be added, while removing, renaming or retyping one breaks both surfaces at once. An added field goes after the last field its object already emits, never between two existing ones, so the emitted order Tier 3 freezes for `search`, `tree` and `graph` stays a prefix of the new order; this holds on every DTO, frozen or provisional. A new key also never reuses a name a sibling document gives another meaning: a tree node's notebook is `notebook`, not `slug`, which on item rows is the item's own slug. Such a change is allowed only where the shape's stability class allows it, and it always ships as a schema change: a `SCHEMA_VERSION` bump, the hard stop and `sq migrate up`, with a client and a daemon at different schema versions refusing each other (ADR-1225, section 3). `/v1` versions the route grammar and the envelope, not the DTOs. No schema snapshot is added. The surface suite asserts whole JSON documents (ADR-1172, rule 5), so it fails on a removed or renamed field.
- **Stability of the shapes that had no `--json`.** Their DTOs are documented and served under `/v1` from 0.18, and stay provisional until the web front consumes them (MILE-868); they are frozen then (op-pierre, 2026-10-28). Because a DTO is the only definition of both surfaces, the `--json` output of point 3a is provisional on exactly the same terms. `docs/stability.md` lists them in Tier 3 under a provisional mark.

### 3a. `--json` on every command that prints a result

The operator ruled on 2026-10-28 that the commands without `--json` get it in 0.18. Of the 64 keys without it, 55 get the flag, and the flag prints the response DTO's `data` under the rules above. Nine keys do not, because they print no result of their own: the seven group callbacks that only parse (the root, `<type>`, `<type> <kind>`, `memory`, `role`, `skill`, `operator`), `ui`, which is interactive, and the bare `workflow` group, which prints what `workflow show` prints and whose subcommands carry their own `--json`. The 55, by the increment that carries them (point 8):

| Increment | Keys | Count |
|---|---|---|
| 0, foundation | `status` | 1 |
| 2, item writes | `<host> comment` (adding one), `<type> update`, `body`, `retype`, `ref add`, `ref rm`, `view add`, `view disable`, `<type> <kind> update`, `<type> <kind> body` | 10 |
| 3, roster | `role add`, `activate`, `update`, `body`, `status`, `set-default`, `regen`, `remove`, `rm`, `view add`, `view disable`; `skill add`, `update`, `link-role`, `unlink-role`, `ref add`, `ref rm`, `regen`, `view add`, `view disable`; `operator add`, `update`; `dev add`, `dev list` | 24 |
| 4, the rest of the squad and package data | `board post`, `board clear`, `memory add`, `memory forget`, `override scaffold`, `override update`, `sync`, `workflow show`, `workflow lint`, `docs`, `migrate help`, `migrate chlog` | 12 |
| 5, corpus-wide and creation | `repair`, `renumber`, `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status`, `init`, `adopt` | 8 |

- A command gets its flag in the increment that moves it onto its operation, because the flag only prints the DTO that move creates. No increment adds a flag to a command still on the old path.
- **Coverage (ADR-1172).** Each flag is one new (command, `--json`) pair, so 55 pairs, each declared by one surface case that asserts the whole document (rule 5). The coverage guard fails on an increment that adds a flag without its case. Where the bundled spec refuses every call of a command, so that no success document can be reached without an override, its case asserts the refusal under `--json` (exit code and error line), and the success document waits for the override-backed run ADR-1172 names.
- **The payloads** are the DTOs, so a write prints the resource it wrote, a corpus-wide operation prints its report, and the package-data commands print their text or index as data. None is built in the CLI.
- **What a write answers.** Every write of one resource whose `--json` is new in 0.18 answers `{entry, …}`: `entry` is the resource it wrote (an item row, a sub-entity object, a roster row, a notice, a memory), or, for a delete, the resource as it was before it went; any outcome the command reports (`severed`, `changed`, `cleared`, `was_present`, a ref's `target`, with `kind` for the ref `ref add` added and `kinds` for the refs `ref rm` removed) is a field beside it. Outcome fields are then added without changing the shape, and one verb answers one shape on every host, item `status` included. A write whose `--json` predates 0.18 (`create`, `add-<kind>`, the item and sub-entity `remove`, the comment verbs that had it) keeps its document as `data`. A write that acts over many resources rather than one (`sync`, `override update`, and the corpus-wide operations of increment 5) answers its report, with no `entry`.
- **The package-data DTOs.** `docs`, `migrate help` and `migrate chlog` make no call (point 1), so their DTOs are not operation responses. They live in `_api/_dto/_package.py` and are built by a function beside the data they read: `_docfiles` for `docs`, the migration registry for `migrate help` and `migrate chlog`. The command calls that function directly and renders, or prints with `--json`, what it returns. They are not operations and have no route: an operation composes a service on a squad, these commands run outside one, and the daemon serves these commands as it serves any command line (ADR-1261), with no operation. A client that wants this data over HTTP later gets an operation that calls the same function, which is an additive change. The edges `_docfiles -> _api` and `_migrations -> _api` are rows in the import-edge table.
- **Prompts.** `--json` never puts a prompt on stdout: under `--json` a removal's prompt, and `comment remove`'s preview listing, go to stderr, and stdout holds only the document. `init --json` asks for no role names and keeps the defaults, as `--default-names` does. The `<host> comment` callback's flag applies when it adds a comment; given with a verb (`edit`, `remove`, `show`), which carry their own flag, it is a usage error.
- Commands added in 0.18 (the `daemon` group of ADR-1052) carry `--json` from the start wherever they print a result.

### 4. Operations and the API layer

- **The operation table.** `squads/_api/_ops.py` is one literal table with one entry per operation: `Operation[Req, Res]` holding a `name`, the HTTP `method` and `path` (decided in ADR-1225), the `request` and `response` types, and five more fields:
  - `mode`: the composition mode of ADR-1128 that the operation needs: normal, index check skipped, migrate, bundled fallback, `check` (the report that must run on a broken squad) or `vocabulary` (the catalogs and the cheatsheet, which also run outside a squad). This moves the choice between `get_service` and `get_service_bypassing_index_cross_check` out of the CLI. `_api.Mode` is the only mode enum outside the composition root. What each mode falls back to, and in what order, is a table in `_services/_service.py` beside `CHECK_FALLBACKS` (`VOCABULARY_FALLBACKS` among them), reached only through `compose_service`; the document choices those tables step through (a playbook left unavailable, the bundled spec) are private to that module. `LocalApi` maps `op.mode` to `compose_service` and decides no fallback itself.
  - **Outside a squad.** The last step of `VOCABULARY_FALLBACKS` is a squadless composition over the bundled documents, built inside `compose_service` like any other, not by a second construction path. Only a read may run there: a `tests/meta` guard holds every operation whose mode can compose squadless (`vocabulary` today) to a `GET` route.
  - **The refusal is part of the composition.** `compose_service` returns the service with the reason it fell back (the error that made it leave normal composition), fixed at construction and never set afterwards; the handler reads it to report why (`check`, the cheatsheet). A composition that fell back is not kept for the next call by `LocalApi` (below), so a squad repaired during a session composes normally again.
  - `grant`: what the operation may do while the squad's schema is behind the package (ADR-955), which moves today's `Ground` gate declarations out of the CLI.
  - `local_only`: true for `init` and `adopt`.
  - `timeout`: `standard` or `long`, the class `HttpApi` applies (ADR-1225, section 3).
  - `json_field`: the field of `data` that `--json` prints, unset for every operation but the 29 of point 3.
- **Handlers are `Service` methods.** One literal table in `_services` binds each operation to its method through `bind(OP, Service.method)`. Pyright checks each pair's request and response types. Like the backend registry, the table has no registration side effect. A `tests/meta` guard checks that every operation is bound exactly once.
- **The protocol** has one method:

  ```python
  class Api(Protocol):
      async def call[Req, Res](self, op: Operation[Req, Res], req: Req) -> Response[Res]: ...
  ```

  It has two implementations:
  - **`LocalApi`** (in `_services`) composes the service for `op.mode` through `compose_service`, opens the read scope (ADR-753) around the call, awaits the handler and returns its DTO as an object. Nothing is serialised, so local mode does the same work as today, minus the repeated lookups that point 1 folds into the operation. An instance keeps the service it composed for each mode for its own lifetime, which is one call for a command and a session for the TUI in local mode (point 7), except a composition that fell back, which it composes again on the next call.
  - **`HttpApi`** (in `_api`, standard library only) puts the request on the wire, parses `Response[Res]` and turns an error answer back into a `SquadsError` carrying the daemon's message.

  ADR-1225 gives the wire rules.
- **Which API a command uses:** a CLI process uses `LocalApi`, whether it is a command served by the daemon (the daemon's own `LocalApi`, ADR-1261 point 2) or the shim's local fallback. The root callback puts it on `RequestContext`, and a test harness may hand it another `Api`, `HttpApi` among them. `HttpApi`'s production caller is the TUI (point 7), selected by ADR-1225's rule. A command never builds a service. `get_service`, its memo on the Click root and the double bridge crossing are removed once no command needs them.
- **Request metadata** stays on `RequestContext`: the actor from `--as`, the `--at` clock, the session ids, and the directory that paths in messages are spelled from. `LocalApi` reads it in-process, from the request in a served command; `HttpApi` sends it as headers.

### 5. The renderer displays only what the DTO carries

The operator ruled on 2026-10-28 that everything the renderer displays is in the DTO, badges, labels and columns included, and that the renderer does not read the vocabulary (comment 8113cdc). The renderer therefore reads neither the workflow spec nor `.squads.toml`; parsing still does (point 1).

What a DTO carries beyond codes, built by the operation from the spec, the configuration and the squad's templates:

- **Per item, tree node, graph node, search hit and sub-entity:** a `display` object holding the type's label, the rendered status badge, each declared badge field as its label and rendered badge, and the assignee's display name. `show`'s existing `badges` key stays as Tier 3 has it. On an item row every display value sits inside `display` (point 2).
- **Badges, by one rule:** `display.badges` holds the type's declared badge fields only, in declared order, and no display key is named after a field code or a type. A stored code whose field the type no longer declares gets no display entry (the declared-field rule); there is no fallback to a same-named collection. A line that leads with a badge, such as a tree or graph node's, shows the first entry of `display.badges`, and a table column for a field reads that field's entry, its cell empty when there is none; the stored code stays in the row's own key.
- **Per shown item, its declared attributes:** `display.attributes`, one `{key, label, value}` per attribute the type declares with a `label` and the item stores, in declared order, `value` as display text. An attribute declaration takes an optional `label` (`target_date = { kind = "date", label = "target date" }` in the bundled milestone), an addition to the spec grammar, and `sq workflow types --json` carries it on each attribute, `null` when absent. An attribute without a label is not shown. No display field names an item type: the milestone's target date is one of these rows, not a field of its own.
- **Per table or listing:** `columns`, the ordered `{key, header}` pairs the human table shows. A `key` is the dotted path, from the row, of the exact value its cell shows (`status`, `display.badges.priority.badge`, `display.name`, `id`), so a client fills a table by following each path, with no convention of its own. This covers `list`, the sub-entity summaries, `workload` and the roster lists, whose column sets come from the spec today.
- **Headings and labels:** a sub-entity kind's plural and container heading, a ref kind's label on `refs` rows and graph edges.
- **Text the squad's templates produce:** the body with its view tags expanded (`display.body` on `show`, beside the stored `body`), and a view's output rendered through `.overrides/templates/`. Template overrides belong to the squad, so a client never renders them.
- **Names:** role and operator names with pronouns already applied or left out according to `[display] pronouns`. These are display values, so they follow the setting on every surface, `--json` and HTTP included; the `pronouns` key of a roster row keeps the resolved value whatever the setting says.
- **Notices:** the working-language notice, as a `warnings` entry.

Consequences for the contract:

- These keys are additions to payloads Tier 3 already freezes, which its additive rule permits. Their values are of the **display** class: the key is frozen, its content is not, and no client parses or compares it.
- Their shape (`display`, `columns` and the label keys) is provisional under the ruling of point 3 until the web front consumes it, on every payload, the frozen ones included. The codes beside them keep their current class, so a client that joins codes to the workflow catalogs, as Tier 3 tells it to, is unaffected.
- The rendering functions live in `_cli/_render/`, which a `tests/meta` guard keeps from importing `squads._workflow`, `squads._paths` or the configuration model: they take a DTO and a console, nothing else.

### 6. What does not change

- The composition root (ADR-1128), the store and its lock and commit order, the read scope (ADR-753), which is now opened per operation, and every invariant in ADR-71 to ADR-76.
- The surface tests of ADR-1172. They assert whole output, so a group of commands moved onto operations is proven unchanged by the suite passing as it stands. A test is touched only where it reached into an internal that has gone.

### 7. The TUI goes through the `Api` in 0.18

The operator ruled on 2026-10-28 that the TUI leaves the service in this release, and it was then agreed with him (comment 73f6e29) that it goes through the same `Api` abstraction as the CLI. `sq ui` runs in the client's process (it is in the shim's local-only table, ADR-1261 point 4) and hands the app an `Api` selected by ADR-1225, section 5: endpoint resolution, fall back per call and the vocabulary hash. The TUI is `HttpApi`'s only production caller. In local mode it calls `LocalApi` in-process. In remote mode it is a client of the daemon, like the web front, and the terminal stays with the TUI's own process.

Its screens map onto operations that the CLI increments create; it needs none of its own:

| Screen | Calls today | Operation |
|---|---|---|
| Browse tree | `tree_view(filter, include_closed)` | `tree`, whose request takes the same filter fields as `sq tree` |
| Browse tree, roster nodes | `memory_list` per role or operator, `roster_all`, `operators_all` | `memory list` per slug; the pronouns come from the tree DTO's display names (point 5), so the two roster calls go |
| Reader | `get`, `read_body`, `read_discussion`, `get_block` per sub-entity | `show`, whose DTO carries the rendered body, the discussion and every sub-entity block |
| Memory reader | `memory_show` | `memory show` |
| Search | `search(text, type, status)` | `search` |
| Board | `board_list` | `board list` |
| Filter screen, search filters | `svc.spec` (types, statuses, badge fields) | the workflow catalog operations (`workflow types`, `statuses`, `collections`) |

- The TUI is an interactive session, so it makes one call per screen load rather than one per invocation. In local mode each call opens its own read scope through `LocalApi`, which the reader skips today.
- **Display comes from the DTOs only,** as for the CLI renderer (point 5). Its screens use only operations whose DTOs carry what they show, and `_tui/` falls under the same guard as `_cli/_render/`: no `_tui` module imports `squads._services`, `squads._workflow`, `squads._paths` or the configuration model. Its sibling ordering and tree building (`sort_siblings`, `populate_tree`) work on DTOs instead of `TreeNode` and `Item`.
- **A long session against a daemon that can go away.** A command makes one call; the TUI makes calls for as long as it is open, while the daemon can retire on a configuration edit or exit on its idle timeout. So the TUI holds the selection rule, not one selected API:
  - A `503 retiring` answer is handled by ADR-1225, section 5: against a local daemon the call runs on `LocalApi`, and against a squad hosted elsewhere it is sent once more to the re-resolved endpoint. Either way the next call resolves the endpoint again, which reaches a daemon on the new configuration, so the TUI does not stay in local mode for the rest of the session.
  - A connection refused before the request is sent (a daemon that exited) also resolves the endpoint again for that call. A local daemon is started again, or `LocalApi` answers when that fails. For a squad hosted elsewhere the screen shows the error, nothing runs locally, and the session stays open for the user to refresh.
  - A connection lost after the request was sent is never replayed (ADR-1052, point 10). The screen shows the error and the user refreshes it.
  - The vocabulary hash is computed from the checkout on every call (0.2 ms), not once at start, because the TUI parses nothing with it. A configuration edited mid-session therefore retires the old daemon and matches the new one. After a retirement the TUI reloads the workflow catalogs that drive its filter choices.
- It goes after increment 4, once all of its operations exist (point 8).

### 8. Order of the work

The refactor cannot land in one change across 113 command functions. It goes in increments, each leaving every gate green: the surface suite unchanged, pyright, ruff and `sq check`.

0. **Foundation.** `squads/_api/` with `Response`, `Operation`, `Api`, `HttpApi`'s wire helpers and the error form, plus `LocalApi`, the binding table, the two guards and the `_cli/_render/` guard (point 5). The `_cli` import guard starts with a pending list of modules that still import `_services`, which shrinks with each increment. Item `show`, `list` and `status` are moved end to end as the reference that the later increments copy.
1. **Item reads** (about 15 commands): `sq show`, `tree`, `graph`, `search`, `inbox`, `mine`, `blocked`, `workload`, `refs`, `comments`, and the sub-entity list and show commands.
2. **Item writes** (about 22): create, update, body, retype, remove, refs, views, the comment verbs and the sub-entity verbs.
3. **Roster** (about 30): role, skill, operator and dev.
4. **Everything else that reads or writes the squad** (about 28): board, memory, the workflow catalogs and views, overrides, reflog and check.
5. **Corpus-wide operations and squad creation** (9). The pending list empties, and `get_service` and the CLI-side JSON builders are deleted.
6. **The TUI** (point 7). It needs only operations that increments 1, 3 and 4 create, so it can run beside increment 5. In remote mode it also needs ADR-1225's remote client (D2). The 0.18 release waits for it.

Increment 0 (for `status`) and increments 2 to 5 each add the `--json` flags of point 3a for the commands they move, with one surface case per flag. Reads come before writes because write responses reuse the read rows. Increment 0 comes first because it fixes the shapes the others copy. The daemon work that depends on this is ordered in ADR-1225.

## Consequences

- About 90 operations, each with a request DTO and a response DTO. The `--json` builders move from `_cli/_common.py` to service-side projections, and `_cli` keeps parsing, the input validation that needs only the vocabulary, and rendering from DTOs alone.
- Every command that prints a result has `--json` (point 3a): 55 new flags, 55 new coverage pairs and cases. Their shapes are provisional until the web front consumes them.
- Display strings travel in the payloads (point 5). That makes every payload larger and puts the presentation decisions in the service, where the web front gets them too; a client that wants different presentation still has the codes and the catalogs.
- The guard proves that no renderer reaches the service, and the edge table records the single function-level import that remains.
- The shim, the CLI's remote client, imports no `squads` module beyond `_endpoint` (ADR-1261, point 4); the TUI's remote path never imports `_services`. That is the 0.5 s of fact 9. The client import guard is the shim's.
- Local mode does the same work as today. Commands that used to repeat a lookup now do it once, inside the operation.
- Vocabulary checks can run twice: in the CLI for exit code 2, and in the operation for callers that are not the CLI. That is already the case today, where the service validates what it is given.
- The TUI calls operations through the `Api` like the CLI does, selected by ADR-1225's rule, and needs no operation of its own (point 7). In remote mode it is a daemon client, and it re-resolves the endpoint after a retirement or a refused connection.

## Options considered and rejected

- **Keep the fine-grained service methods and pass `Item` objects to the renderer.** The renderer still needs bodies, discussions, views and blocked flags, so it would go on calling the service, which is the thing the direction rules out.
- **A protocol with one method per operation,** implemented by `Service` and implemented again by `HttpApi`. That means three hand-written copies of about 90 signatures that have to agree. With a table and one generic `call`, each operation is declared once.
- **Use `Item` as the DTO.** It would freeze the storage model as the wire contract.
- **Dataclass DTOs.** They do not validate a parsed response and give no schema, and pydantic is already a dependency.
- **The renderer reads the vocabulary for presentation,** with DTOs carrying codes only. It would keep the payloads small, but every client would need the spec to display anything; the operator ruled for the strict reading (point 5).
- **No `--json` on the commands that lacked it,** leaving their DTOs to HTTP. Ruled out by the operator; agents and scripts would have had to parse human text for 55 commands that the daemon already answers in JSON.
- **The TUI wired to `LocalApi` only.** It would have stayed outside remote mode, so a hosted squad (FEAT-33) could not be browsed and the TUI would read the squad's files while every other client goes through the daemon.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T20:59:21Z] `architect` Robert Architect:
  - Drafted 2026-10-28 from the op-pierre direction (FEAT-1140 b4c77e9, MILE-1152 e7119a6). Measured on release/0.18 44389bb4: 113 command functions; after the change each makes one operation call except comment remove without --yes (preview + remove, 2); 12 callbacks and 3 package-data commands make none. Import of _services is 0.50-0.53 s of the CLI cost.
  - @op-pierre Q1-Q4 are at the end of the body, each with a recommendation. ADR-1225 holds the HTTP half and Q5-Q6.
- [2026-10-28T21:07:22Z] `op-pierre` Pierre Chat:
  - 2026-10-28 answers: Q1 the renderer reads the active vocabulary for presentation. Q2 HTTP shapes without an existing --json are documented under /v1 but provisional until the web front consumes them. Q3 yes: add --json to the commands that lack it, in 0.18. Q4 the TUI moves onto LocalApi in 0.18.
- [2026-10-28T21:18:35Z] `op-pierre` Pierre Chat:
  - 2026-10-28, Q1 revised: everything the renderer displays is in the DTO (badges, labels, columns included); the renderer does not read the vocabulary. No client-side cache of the vocabulary.
- [2026-10-28T21:31:33Z] `architect` Robert Architect:
  - Folded the 2026-10-28 op-pierre rulings (6394f82, 8113cdc) into the body; the questions section is gone.
    - Q1 (revised to the strict reading, 8113cdc): point 5 rewritten. The renderer reads neither the spec nor `.squads.toml`; DTOs carry a `display` object, `columns`, labels, `rendered_body`, resolved names and the working-language notice as a warning. These are additive keys of the display class, their shape provisional until the web front consumes it. A `_cli/_render/` guard keeps renderers off `_workflow`, `_paths` and the config model. Parsing still reads the checkout's vocabulary (point 1, ADR-1225 section 5).
    - Q2: point 3 states the provisional rule. New `--json` output is provisional on the same terms, because one DTO defines both surfaces.
    - Q3: new point 3a. Recounted on ADR-1172 keys: 111 keys, 47 with `--json`, 64 without. 55 get the flag; 9 do not (7 parse-only callbacks, `ui`, bare `workflow`). Each flag lands in the increment that moves its command (2: 11, 3: 24, 4: 12, 5: 8), adding 55 coverage pairs with one whole-document case each. `init --json` never prompts.
    - Q4: new point 7. The TUI is read-only; its 11 service calls map onto existing operations (tree, memory list/show, show, search, board list, workflow catalogs) and it needs none of its own. It stays in-process and joins the import guard. Increment 6 runs beside increment 5 and gates the release.
- [2026-10-28T21:39:57Z] `manager` Catherine Manager:
  - 2026-10-28, agreed with op-pierre: the TUI goes through the same Api abstraction as the CLI and selects LocalApi or HttpApi by the same rule (endpoint resolution, fall back, vocabulary hash), instead of being wired to LocalApi; it is a daemon client in remote mode.
- [2026-10-28T21:40:57Z] `architect` Robert Architect:
  - Point 7 amended per the manager's 73f6e29, agreed with op-pierre. The TUI goes through `Api` and selects `LocalApi` or `HttpApi` by the same rule as the CLI, so in remote mode it is a daemon client.
    - What this adds: the TUI's screens use only operations whose DTOs carry their display, and `_tui/` falls under the `_cli/_render/` guard (no `_services`, `_workflow`, `_paths` or config model).
    - Long sessions:
      - after a `503 retiring` or a refused connection, it re-resolves the endpoint per call rather than staying local;
      - a call lost after it was sent is never replayed;
      - it recomputes the vocabulary hash on every call;
      - it reloads its filter catalogs after a retirement.
    - Increment 6 also needs ADR-1225's D2 in remote mode. ADR-1225 section 5 and its release gate are updated to match.
- [2026-10-28T21:44:39Z] `op-pierre` Pierre Chat:
  - 2026-10-28: accepted, together with ADR-1225.
- [2026-10-28T21:46:06Z] `architect` Robert Architect:
  - Point 7 TUI long-session rule aligned with ADR-1225 section 5 per op-pierre 3fbbd10. A retirement runs locally only against a local daemon; for a hosted squad it gets one retry against the re-resolved endpoint. For a hosted squad, a refused connection shows the error with no local run, and the session stays open.
- [2026-10-28T21:48:10Z] `manager` Catherine Manager:
  - Accepted 2026-10-28 per op-pierre; ADR-1052 and ADR-1172 amended accordingly.
- [2026-10-28T21:56:13Z] `architect` Robert Architect:
  - Aligned with the ADR-1225 amendment for op-pierre 8de91f7 (board rule 6). Point 3: an incompatible DTO change ships as a schema change (bump, hard stop, migrate up) where its stability class allows it, and /v1 versions the route grammar and envelope, not the DTOs. This replaces "needs a new major and /v2 routes". Point 1: comment remove sends the confirmed full hash. Point 4: the operation table gains a `timeout` class (standard or long).
- [2026-10-28T22:33:51Z] `architect` Robert Architect:
  - Amended in place 2026-10-28 for the open points TASK-1227 and TASK-1231 raised (board rule 6). Status unchanged.
  - Point 3a table: `status --json` moves from increment 2 (now 10 keys) to a new increment 0 row (1 key), since status moves with the foundation. Point 8 says increment 0 adds that flag. Total still 55.
  - Point 3a, new bullet "The package-data DTOs": `docs`, `migrate help` and `migrate chlog` get DTOs in `_api/_dto/_package.py`, built by a function beside their data (`_docfiles`, the migration registry), which the command calls directly. They are not operations and have no route. New edges `_docfiles -> _api` and `_migrations -> _api`.
  - @tech-lead TASK-1227 and TASK-1231 can be updated.
- [2026-10-28T23:11:56Z, edited 2026-10-28T23:12:11Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for the two questions TASK-1227 raised (eb4503f, deviation 1 and the reserved names), board rule 6. Status unchanged.
  - Point 3: `--json` prints `data`, or the one field of it the operation names in a new `json_field`. `data` is always an object. The field is set only where the document frozen before 0.18 is not an object: 29 keys, listed by increment (`list` in 0; `tree`, `search`, `inbox`, `mine`, `blocked`, `workload`, `comments`, sub-entity lists in 1; `comment remove` in 2; `role catalog`, `role list`, `operator list` in 3; `board list`, `memory list`/`search`, `override list`/`diff`, `reflog`, `check`, the 8 catalogs and `workflow view` in 4). Field name `items` for rows, `source` for `workflow view`. New guard: the field exists on the response type, and only those operations set one. "One definition" now says the HTTP body is the whole `data`, so the front gets `columns` and `hidden`.
  - Point 4: the operation table's fifth field, `json_field`.
  - Point 2: an item row adds one display key, `display`; every display value on an item row goes inside it. `rendered_body` becomes `display.body` on `show`, so the refactor reserves one name. A collision uses the existing mechanism (load refusal for a declared attribute or badge field, an undeclared stored key stays out of the row); no migration. Stability doc and changelog name it, as for `views`.
  - Point 5: `rendered_body` references updated to `display.body`.
- [2026-10-28T23:31:55Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for REV-1235 F8 and F1 (board rule 6). Status unchanged.
  - Point 5: new bullet `display.attributes` on `show`, one `{key, label, value}` per declared attribute that has a `label` and a stored value, in declared order. Attribute declarations take an optional `label` (spec grammar addition; the bundled milestone's `target_date` gets `label = "target date"`), and `sq workflow types --json` carries it, `null` when absent. No display field names a type; `display.target_date` goes.
  - Point 2: the 0.18 migration's manual step (`sq migrate chlog`) names the `display` rename for an adopter who declares it.
- [2026-10-29T01:06:01Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for REV-1235 F14 (board rule 6). Status unchanged.
  - Point 5: new bullet "Badges, by one rule". `display.badges` holds the declared fields only, in declared order, and no display key is named after a field code or a type. An undeclared stored code gets no display entry, with no same-named-collection fallback. A badge-led line (tree, graph) shows the first entry of `display.badges`. A field's table column reads that field's entry and shows the raw code when there is none.
- [2026-10-29T01:28:58Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for REV-1235 F16 (board rule 6). Status unchanged.
  - Point 4, `mode`: the list adds `check` and `vocabulary`. `_api.Mode` is the only mode enum outside the composition root. Fallback order lives in tables in `_service.py` (`VOCABULARY_FALLBACKS` beside `CHECK_FALLBACKS`), reached only through `compose_service`, and `LocalApi` decides no fallback.
  - Point 4, new bullets. Outside a squad: the squadless composition is the last step of `VOCABULARY_FALLBACKS`, built inside `compose_service`, and a guard holds squadless-capable modes to `GET` routes. The refusal: it is fixed at construction and returned with the service. A composition that fell back is not cached, so a squad repaired mid-session composes normally again.
- [2026-10-29T01:35:05Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for REV-1235 F24, F21 and F23 (board rule 6). Status unchanged.
  - Point 3a, new bullet "What a write answers": every write whose `--json` is new in 0.18 answers `{entry, …outcome}`. `entry` is the resource written, or for a delete the resource as it was. Writes with `--json` before 0.18 keep their documents. Item `status` follows the rule.
  - Point 3a, coverage: where the bundled spec refuses every call, the case asserts the refusal under `--json`. The success document waits for ADR-1172's override-backed run.
  - Point 5, columns: a column `key` is the dotted path from the row to the exact value its cell shows.
- [2026-10-29T01:43:01Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for the TASK-1228 dev's question on REV-1235 F24 (e10633a), board rule 6. Status unchanged.
  - Point 5, badges: a field column whose type no longer declares the field shows an empty cell. There is no raw-code fallback, matching tree and graph. The stored code stays in the row's own key.
  - Point 5, columns: the example path for status is `status`, the raw status the list cell shows, not `display.status.badge`.
- [2026-10-29T01:51:54Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for REV-1235 F21 (board rule 6). Status unchanged. Point 3a, "What a write answers": `{entry, …}` applies to a write of one resource. A write over many resources (`sync`, `override update`, the corpus-wide operations) answers its report, with no `entry`.
- [2026-10-29T04:29:15Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for the REV-1235 test audit (35950c3), board rule 6. Status unchanged.
  - Point 3: the `json_field` guard's literal list is a deliberate contract tripwire, since no code records which documents Tier 3 froze. It never grows, and it shrinks only through a schema change that amends this point.
  - Point 5, names: pronoun-applied names are display values, so they follow `[display] pronouns` on every surface, `--json` and HTTP included. A roster row's `pronouns` key keeps the resolved value.
- [2026-10-29T04:58:56Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for REV-1235 F34, F36 and F37 (board rule 6). Status unchanged.
  - Context 7 corrected: before this change, item and sub-entity removal checked the address and `--as` before the prompt. Point 1 now says those checks run inside the one call, after the answer, and gives the reason.
  - Point 3a, prompts: under `--json`, a removal prompt and the `comment remove` preview go to stderr.
  - Point 3a, write outcomes: `ref add` answers `kind`, and `ref rm` answers `kinds`, the kinds of the refs it removed.
- [2026-10-29T06:09:13Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for REV-1235 F39 and F40 (board rule 6). Status unchanged. In point 3, "One definition, one contract": an added field goes after the last field its object already emits, on every DTO, frozen or provisional. A new key never reuses a name that a sibling document gives another meaning, so a tree node's notebook slug is `notebook`, not `slug`.
- [2026-10-29T06:47:29Z] `op-pierre` Pierre Chat:
  - 2026-10-29: accepted that display is a reserved row key; an override declaring an attribute or badge field named display is refused at load, with the 0.18 migration's manual step telling adopters to rename it.
- [2026-10-29T06:49:06Z] `op-pierre` Pierre Chat:
  - 2026-10-29: accepted that parse and vocabulary refusals (exit 2) come before the operation's own checks, so a command with two errors reports the usage error first; documented in the changelog.
- [2026-10-29T12:57:49Z] `op-pierre` Pierre Chat:
  - 2026-10-29: amend point 2. Reserving display needs no 0.18 migration record and no schema bump; the CHANGELOG entry with its refusal text and What to do is enough (tech-lead ruling on TASK-1234).
- [2026-10-29T12:58:37Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 per op-pierre (comment of 2026-10-29T12:57) and the tech-lead ruling on TASK-1234, board rule 6. Status unchanged. Point 2: the sentence about the 0.18 migration's manual step (`sq migrate chlog`) is removed. The rule now reads: the changelog names `display` with its refusal text and what to do, and reserving it needs no migration record and no schema bump.
- [2026-10-30T20:27:15Z] `architect` Robert Architect:
  - Amended in place 2026-10-30 on the acceptance of ADR-1261 (board rule 6, linked related, status unchanged).
    - Point 1: a served command parses in the daemon with the vocabulary the daemon loaded; the hash no longer applies to the CLI.
    - Point 2: the import-guard sentence now names the TUI's remote path, and the shim for the CLI.
    - Package-data DTOs: the daemon serves these commands as command lines, with no operation.
    - Point 4: a CLI process uses `LocalApi`, either the daemon's own or the shim's fallback, and a harness may hand it another `Api`. `HttpApi`'s production caller is the TUI. Request metadata comes from the request in a served command.
    - Point 7: `sq ui` runs in the client's process and is `HttpApi`'s only production caller; selection follows ADR-1225 section 5.
    - Consequences: the client import guard is the shim's.
    - Unchanged: points 3, 3a, 5, 6 and 8.
<!-- sq:discussion:end -->
