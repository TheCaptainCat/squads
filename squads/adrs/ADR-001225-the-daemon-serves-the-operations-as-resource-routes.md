---
id: ADR-1225
sequence_id: 1225
type: decision
title: The daemon serves the operations as resource routes
status: Accepted
author: architect
refs:
- FEAT-1140
- MILE-1152
- ADR-1052
- ADR-1224
- ADR-1172
description: Resource routes under /v1 generated from the operation table replace
  POST /v1/commands; HttpApi or LocalApi chosen per invocation; ADR-1052 amended on
  acceptance
created_at: '2026-10-28T20:58:41Z'
updated_at: '2026-10-29T07:04:37Z'
---
<!-- sq:body -->
## Context

ADR-1052 gave the daemon one command endpoint: `POST /v1/commands` takes a command line and answers with its exit code, stdout and stderr (option I). The operator ruled for it on 2026-10-25 (ADR-1052, comment ec061f4). On 2026-10-28 he reversed that ruling (FEAT-1140, comment b4c77e9; MILE-1152, comment e7119a6). The API becomes resource endpoints that a Vue or Angular front will call. The CLI in remote mode calls the same endpoints, through a layer that makes either the HTTP call or the local service call depending on the mode. Both this and the refactor that makes it possible ship in 0.18.

ADR-1224 (operations and DTOs) defines the operation table, the `Response[T]` envelope, the `Api` protocol with its `LocalApi` and `HttpApi` implementations, and the rule that the CLI never imports `_services` outside the local API's factory. This decision covers the HTTP side: the routes, the wire format, errors, how a mode is chosen, the daemon's request scope, and what changes in ADR-1052, ADR-1172 and the delivered TASK-1217.

ADR-1052 rejected resource routes (its option II) for two reasons. First, every service method and every result type would need a wire form. Under ADR-1224 that work is the refactor itself: the wire surface is about 90 operations, not the 91 fine-grained service methods, and their DTOs are JSON-native by construction. Second, the client would still pay for building the CLI. That cost is measured below and held to a budget (section 5).

Facts, read or measured on `release/0.18` at 44389bb4 on 2026-10-28:

1. **The CLI needs the vocabulary to parse.** The item commands of a custom type, and option help such as the priority codes, are built from the active spec (`_CustomTypeGroup.get_command`, `build_item_app`).
2. **Cost of the CLI.** The released `sq task 1217 show` takes a median 915 ms in local mode, and 867 ms with `--json`, over 31 interleaved runs. Importing `squads._cli` alone takes about 0.61 s of wall time, about 0.18 s of it in interpreter teardown. A client of `typer`, `rich`, `http.client` and the workflow spec, without `_services`, takes a median 402 ms for the same show. ADR-1052 budgeted about 0.1 s for its standard-library forwarder. Point 5 breaks these numbers down.
3. **What TASK-1217 delivered** (commits 22ce7f65, e0cfaea8 and 4a4a30ae):
   - `run(argv, *, seed)`, the one entry from a command line to an exit code;
   - consoles built per invocation;
   - `RequestContext` fields `start_dir`, `attachments`, `terminal`, `documents` and `consoles`;
   - `client_path` reads served from attachments;
   - the `NeedsTerminal` signal, raised through `confirm_or_signal` and `prompt_or_signal`;
   - `path_from_process_dir` spelled from `start_dir`.

   REV-1223 deferred its findings F3, F4, F6 and F8, all about the seeded terminal facts and `NeedsTerminal`.
4. **Messages name paths relative to the directory the user started from.** A remedy such as an override path is spelled by `path_from_process_dir`.
5. **Per-invocation metadata.** The reflog records `SQUADS_SESSION_ID` and `SQUADS_PARENT_SESSION_ID`, read from the environment. The root option `--at` overrides the clock, and `--as` sets the actor.
6. **Errors.** `SquadsError` has 13 subclasses in `_errors.py`, among them `ItemNotFoundError`, `RoleNotFoundError`, `InvalidTransitionError`, `AlreadyInitializedError`, `IndexLockTimeoutError` and `ConfigIntegrityError`. The CLI prints `error: <error_text(exc)>` and exits 1.

## Decision

### 1. Routes

The routes are the `method` and `path` fields of the operation table. One table therefore drives the daemon's router and `HttpApi`, and no second list of routes exists. The rules:

- **Everything sits under `/v1`.** `GET /v1/daemon` and `POST /v1/daemon/stop` are kept as ADR-1052 has them.
- **Items are addressed by id only:** `/v1/items/{id}`, where the id is `TASK-12` for example. The route does not depend on the type, so a custom type needs no new route. Roster entries are addressed under `/v1/roles/{addr}`, `/v1/skills/{addr}` and `/v1/operators/{addr}`, where `addr` is a slug, an id or a number, as on the CLI.
- **A roster entry's discussion** is a sub-resource of its roster route: `/v1/roles/{addr}/comments[/{hash}]`, `/v1/skills/{addr}/comments[/{hash}]` and `/v1/operators/{addr}/comments[/{hash}]`, with the methods of the item comment routes. The operation resolves `addr` within the route's roster kind, as every roster route does; an address that resolves to no entry answers `404 not_found` with today's text. The kind belongs to the operation, never to a request field that could contradict the path, and the request and response DTOs are the item comment routes' with `addr` in place of `id`. The CLI holds only the address, and only the operation may resolve it (ADR-1224, point 1), so the item route would cost a second call to learn the id, and a slug on `/v1/items/` would be ambiguous across the three kinds. A roster entry is also an item, so its id on the item comment routes reaches the same discussion.
- **`GET` reads and never mutates.** This is ADR-1052's admission rule, and the cross-site defence relies on it. Filters are query parameters. A request DTO for a `GET` holds only flat fields, a repeated list item repeats its key (`?badge=priority=high&badge=severity=major`), and a `tests/meta` guard rejects a nested field on a `GET` request.
- **Writes:** `POST` on a collection creates, `PATCH` updates part of a resource, `PUT …/body` replaces a body, and `DELETE` removes.
- **An action that is not create, update or delete** is a `POST` on a sub-resource named after it: `…/status`, `…/retype`, `…/activate`, `…/regen`. An operation over the whole squad is a `POST` under `/v1/squad/` (`sync`, `repair`, `renumber`, `migrate`, `repad`, `rename-type`, `rename-status`, `import`). These run synchronously, as a command does.

Examples (the table is authoritative):

| Command | Route |
|---|---|
| `sq <type> <n> show`, `sq show <id>` | `GET /v1/items/{id}` |
| `sq list …` | `GET /v1/items?type=&status=&assignee=&badge=&sort=&all=` |
| `sq tree [root]`, `sq graph`, `sq search` | `GET /v1/tree?root=…`, `GET /v1/graph`, `GET /v1/search?q=…` |
| `sq inbox <role>`, `sq mine <role>` | `GET /v1/inbox/{slug}`, `GET /v1/mine/{slug}` |
| `sq create <type>` | `POST /v1/items` (the type in the body) |
| `sq <type> <n> update` | `PATCH /v1/items/{id}` |
| `sq <type> <n> status <S>` | `POST /v1/items/{id}/status` |
| `sq <type> <n> body` | `PUT /v1/items/{id}/body` |
| `sq <type> <n> ref add` / `ref rm` | `POST /v1/items/{id}/refs`, `DELETE /v1/items/{id}/refs/{target}` |
| `sq <type> <n> comment …` | `POST`, `GET`, `PATCH` and `DELETE` on `/v1/items/{id}/comments[/{hash}]`; the removal preview of section 3 is `GET /v1/items/{id}/comments/{hash}/removal` |
| `sq role <addr> comment …`, and the skill and operator forms | the same methods on `/v1/roles/{addr}/comments[/{hash}]`, `/v1/skills/{addr}/comments[/{hash}]`, `/v1/operators/{addr}/comments[/{hash}]`, and the removal preview at `…/comments/{hash}/removal` under each |
| `sq <type> <n> <kind> <k> …` | `/v1/items/{id}/subentities[/{local}]`, plus `/body` and `/comments` under it, the removal preview included |
| `sq workflow types` and the other catalogs | `GET /v1/workflow/{catalog}` |
| `sq role add`, `sq role <addr> update` | `POST /v1/roles`, `PATCH /v1/roles/{addr}` |
| `sq repair`, `sq migrate up` | `POST /v1/squad/repair`, `POST /v1/squad/migrate` |
| (no command) the API's description | `GET /v1/openapi.json` (section 6) |

The removal preview is a read, so it is a `GET`, on a sub-resource named for what it returns: the comments a removal of that hash would take, with the actor's right to remove them checked. That is why it is not the `GET` on `…/comments/{hash}`, which is `show`.

### 2. Requests

- **Body.** Fields that are not in the path go in the query string for a `GET` and in a UTF-8 JSON body for every other method. The body is the request DTO.
- **Metadata travels as headers,** which `HttpApi` writes from the invocation's `RequestContext` and the daemon binds back into the request's:
  - `Squads-Actor`, the actor from `--as`. It is declarative: the daemon records whatever actor the header names, and it authenticates no one (below);
  - `Squads-At`, the `--at` time;
  - `Squads-Session-Id` and `Squads-Parent-Session-Id`;
  - `Squads-Client-Dir`, the directory paths in messages are spelled from. Without it they are spelled from the squad's root, which is what a web client gets.
  - `Squads-Vocabulary`, the hash of the vocabulary the CLI parsed the command with (section 5). A client that parses nothing, such as the web front, does not send it.
  - `Squads-Schema`, the schema version of the client's package (`SCHEMA_VERSION`). Every client sends it (section 3).
  - `If-Match`, the ETag of the item a write addresses, when the client read it first (section 3).
  - `Squads-Client: 1` is still required on every request that is not a `GET` (ADR-1052, point 5).
- **The actor is declared, not authenticated.** A web client sets `Squads-Actor` for the person at the keyboard, and the CLI sets it from `--as`. Anyone who can reach a listener can write under any actor, so the actor recorded on an item, a comment or a reflog line is a claim, with the same untrusted, observability-only standing the reflog's session ids already have in `docs/stability.md`. Authentication arrives with the MILE-868 mode. The adopter documentation (TASK-1221) states this beside the header.
- **Files.** The CLI reads `--file`, `-` and the import file itself, as local mode always has, and sends their text in the request DTO's field, `body: str` for example. Nothing is attached, and the daemon never reads a path a client names.

### 3. Responses and errors

- **Success.** An operation that ran answers 200 with the `Response[T]` envelope: `data`, `omitted` and `warnings`. A partial read is a 200 with a non-empty `omitted`. The CLI turns that into exit 4 itself, so the browser gets the report in the body rather than as a line of stderr.
- **Errors.** A `SquadsError` answers `{"error": {"type": "...", "message": "...", "warnings": [...]}}`. `warnings` has the meaning of a response's `warnings` (the working-language notice among them) and is an empty list when there is none, so a refusal prints the same notices in remote mode as in local mode. `HttpApi` puts them on the `SquadsError` it raises, and the CLI prints them on stderr before the error.
  - `message` is `error_text(exc)`: the same sentence local mode prints, spelled from `Squads-Client-Dir`.
  - `type` is an open set derived from the exception class.
  - `HttpApi` raises a `SquadsError` with that message, and `@handle_errors` prints `error: <message>` and exits 1, exactly as in local mode.
  - The HTTP status comes from one table in the server:

| Status | `type` | Raised by |
|---|---|---|
| 404 | `not_found` | `ItemNotFoundError`, `RoleNotFoundError`, an unknown comment hash or sub-entity |
| 409 | `conflict` | `InvalidTransitionError`, `AlreadyInitializedError`, a schema behind the package (ADR-955) |
| 409 | `vocabulary_mismatch` | a `Squads-Vocabulary` header that differs from the daemon's own hash (section 5); nothing has run |
| 409 | `schema_mismatch` | a `Squads-Schema` header that differs from the daemon's `SCHEMA_VERSION`; nothing has run |
| 409 | `changed_since_read` | an `If-Match` that differs from the addressed item's current ETag; nothing has run |
| 423 | `locked` | `IndexLockTimeoutError` |
| 400 | `invalid` | any other `SquadsError` |
| 500 | `internal` | an exception that is not a `SquadsError`. Its traceback goes to the daemon log, and the message says to read it. |

- **Refusals before running.** `503 {"not_executed": "retiring"}` is the only answer after which the client sends the call again: to `LocalApi` when the endpoint has a local mode, otherwise once more to the re-resolved endpoint (section 5; ADR-1052, points 2 and 13). The `needs_terminal` reason goes, because prompts run in the CLI between calls. The `other_squad` reason goes too: the CLI resolves the squad before it chooses an endpoint, reaches the daemon by that squad's key, and checks the daemon's identity over TCP (ADR-1052, point 8). The admission refusals, 421 and 403, are unchanged.

#### Client and server compatibility

The operator ruled on 2026-10-28 that the DTOs are tied to the schema version, and that a client and a server on different schema versions refuse each other the way a package and a squad on different schema versions already do (comment 8de91f7).

- **An incompatible DTO change is a schema change.** Removing, renaming or retyping a DTO field, or changing an operation's route, request or meaning incompatibly, bumps `SCHEMA_VERSION` and ships a migration runner. The runner may only stamp the new version when the corpus itself does not change. The existing path then applies: the package refuses a squad at another schema (the hard stop), and `sq migrate up` brings the squad forward. An additive change (a new field, a new operation) needs no bump.
- **Which shapes may change at all** is still `docs/stability.md`'s call. A Tier 3 frozen shape changes incompatibly only at a new major, and then also as a schema change. A provisional shape (ADR-1224, point 3) may change in any release, and still only as a schema change. The schema bump is how the change reaches the wire; the tier is whether it may happen.
- **`/v1` versions the route grammar and the envelope** (`Response[T]`, the error body, the headers), not the DTOs. `/v2` is reserved for a change to those.
- **The check.** Every client sends `Squads-Schema` with its package's `SCHEMA_VERSION`. The daemon compares it with its own before anything else and answers `409 schema_mismatch` on any difference, with both versions. A request without the header (a web client of an earlier build) is answered, and the web front sends the header from the OpenAPI document's `info.version`, which is the schema version.
- **The CLI's message,** exit 1, with no fall back:
  - client behind: `error: squads <version> speaks schema v<A>, and the squad served at <endpoint> runs schema v<B>. Install a squads release at schema v<B>, then re-run.`
  - client ahead: `error: squads <version> speaks schema v<A>, and the squad served at <endpoint> runs schema v<B>. The squad's server must be upgraded and the squad migrated (sq migrate up) before this client can use it.`
- **Order of the checks:** schema first, then vocabulary, then the operation's `grant` against the squad's on-disk schema (ADR-955). Two packages at different schema versions usually ship different bundled specs too, and the schema message is the one that names the remedy.
- A local daemon is keyed per squads version and installation (ADR-1052, point 8), so a local client and its daemon always agree. This rule is what holds for a squad hosted elsewhere.
- **The cost:** a wire-only change forces every adopter through `sq migrate up` with a stamp-only runner, daemon or not. That is the price of one compatibility rule instead of two.

#### Concurrent writes: ETags

The same ruling (comment 8de91f7) makes a write on an item changed since it was read answer 409.

- **The ETag is the SHA-256 of the item file's bytes** as the operation reads them, sent as a strong ETag (`"<64 hex>"`). The file is the source of truth (invariant 1). The index is rebuildable and can lag, so it is not used, and nothing new is stored. `updated_at` is not used either: a hand edit or a `git checkout` can change the file without changing it, it has one-second resolution, and not every mutation is required to bump it.
- **What carries it.** Every single-item read answers with an `ETag` header, and every write on an item answers with the new one: `GET /v1/items/{id}` and the sub-entity routes under it. A sub-entity's state lives in the parent item's frontmatter, so its ETag is the parent item's. A roster entry is an item, so the same rule covers role, skill and operator writes. The show DTO also carries `etag`, so the web front can keep it beside the data; the key is provisional under ADR-1224, point 3.
- **How the ETag travels.** `If-Match` and `ETag` are conditional-request metadata, not resource data, so they travel on the request context, as the other headers do, and not in a DTO or the envelope.
  - The daemon binds `If-Match` onto the request's `RequestContext` with the other metadata headers (section 7), and the transaction reads it from there.
  - A write records the addressed item's new ETag on the same `RequestContext`, computed inside the transaction and under the lock from the bytes that item's file holds at its end: the bytes the write wrote, or the bytes it read when it left that file unchanged. Re-reading the file after the commit would not do: a local-mode writer may already have changed it.
  - The generic endpoint writes the `ETag` header from it. The addressed item is the route's: the created item for `POST /v1/items`, the parent for a sub-entity route, the entry for a roster route. A remove answers with none.
  - `LocalApi` records it too, and the CLI ignores it.
  - Rejected: an `etag` field in the envelope, which every other operation would carry empty. The front is served from the browser listener's own origin and reads response headers like any HTTP client; a front on another origin would also need `Access-Control-Expose-Headers: ETag`, which is MILE-868's. Also rejected: an `etag` field on the write responses, which reuse the list row, so every listing would either hash every item file or carry an empty field. The show DTO keeps its `etag` key (above).
- **Which writes check it:** the item-level writes: update, status, body, retype, remove, refs and views, and sub-entity add, update, body and remove, whose state is the item's frontmatter, for items and roster entries alike. Creation addresses no existing item, and the corpus-wide operations address none, so neither checks one.
- **Comments need no ETag.** A comment's hash is already derived from its content: `_discussion.comment_hash` is the SHA-256 of the item's sequence number, the discussion scope, the author's slug, the header timestamp and the text, so an edited comment gets a new hash and its old one stops resolving. A comment edit or removal addresses the comment by that hash, which plays the precondition's role. Adding a comment appends to the discussion, so it needs none.
- **The check is optional and atomic.** A write that sends `If-Match` is compared inside the store's transaction, after the file is re-read under the lock, so no other writer can slip between the check and the write. A mismatch answers `409 changed_since_read` and nothing runs. The web front always sends `If-Match`, because it shows data and then edits it.
- **The CLI sends no precondition** on its one-call writes, which is almost all of them, and this is safe. A CLI write never sends a resource rebuilt from an earlier read. It sends a field-level change (a status, a field, a ref, an appended comment), which the operation validates against the current state under the lock, as local mode does today, so nothing the user did not ask to change is overwritten. The one whole-value write, `body` without `--append`, replaces the body with text the user supplied, which is the command's meaning in both modes. The CLI's only read-then-write flow is `comment remove` without `--yes`, below, which relies on the comment hash.
- **The CLI's message,** should it ever receive one (exit 1): `error: <id> changed since it was read; nothing was written. Read it again and re-run.`

#### `comment remove` after a confirmation

No new mechanism is needed. A hash prefix resolves to exactly one full hash in its discussion, or is refused as ambiguous (`_discussion.resolve_hash`), and every comment it addresses carries that full hash. The preview returns the full hash with the comments it addresses, and after the user confirms, the remove request sends that full hash instead of the prefix the user typed.

- A comment that was edited or removed in between no longer has that hash, so the remove answers `404 not_found` and removes nothing.
- Because the full hash is sent, a short prefix that has since come to match a second, different comment changes nothing: the call does not resolve the prefix again.
- The full hash can address more or fewer comments than were shown only when a byte-identical copy of the confirmed comment (same author, timestamp and text, as a merge can leave) was added or removed in between. The remove deletes the copies present at that moment, as `comment remove` already does with a duplicate group: they are the comment the user confirmed.
- With `--yes` there is one call, and it resolves the typed prefix at that moment, as today.

#### Timeouts

The operation table gives each operation a `timeout` class (ADR-1224, point 4), and `HttpApi` applies it:

| Class | Operations | Connect | Answer |
|---|---|---|---|
| `standard` | every read and every item, roster, board, memory, override and `sync` write | 5 s | 300 s |
| `long` | `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status`, `repair`, `renumber`, `import` | 5 s | none: the client waits until the daemon answers |

- The answer timeout counts time spent queued: requests run one at a time, so a read sent during a migration waits for it. 300 s covers that on squads of the size measured here; a `long` operation is never cut off by its own client.
- A `long` call prints `waiting for the daemon (<operation>)…` on stderr once it has waited 10 s, so a silent wait is not mistaken for a hang.
- **A timeout or Ctrl-C ends the client's wait, never the operation.** A call the daemon has started runs to completion (ADR-1052, point 10). The client is never told how it ended, so it never replays and never falls back, since a write may have committed. A timeout prints `error: no answer from the squad served at <endpoint> after <n> s; the operation may still complete. Check its result before running it again.` and exits 1. Ctrl-C prints the same sentence without the duration and exits 130.
- A connect timeout means nothing was sent. It is handled as an unreachable daemon: implicit start or local mode for a local endpoint, an error for a hosted one (section 5).

### 4. What the web front gets that the command endpoint would not give it

- A typed JSON body for every operation, and an OpenAPI 3.1 document (`GET /v1/openapi.json`, section 6) to generate its types from. With the command endpoint it would have parsed human text for the commands that had no `--json`.
- HTTP semantics. Reads are `GET` and can be cached or retried. A failure is told by its status (404 against 409 against 423) and a machine `type`, not by an exit code and a line of stderr.
- The partial-read report and warnings in the body.
- No command lines to assemble or quote, and no terminal facts, stream encodings or attachments to fake.

### 5. The remote client

#### Choosing between the HTTP and the local call

- **The root callback picks the API once per invocation** (ADR-1224, point 4). It picks `HttpApi` when ADR-1052's endpoint resolution finds the daemon enabled and reachable, or starts it: settings and `SQUADS_DAEMON` (point 7), discovery (point 8), implicit start and fall back (point 11). Otherwise it picks `LocalApi` where the endpoint has a local mode; for a squad hosted elsewhere, an unreachable server is an error (below).
  - A command that makes no call never contacts or starts a daemon: `docs`, `migrate help`, `migrate chlog`, `--version`, `--help` and completion.
  - Neither does a local-only operation (`init`, `adopt`), nor `daemon`. `sq ui` selects by the same rule and keeps the rule for its whole session, re-resolving the endpoint after a retirement or a refused connection (ADR-1224, point 7).
- **Fall back is per call, and only where a local mode exists.** The `Endpoint` says whether it does (below): a local daemon has one, a squad hosted elsewhere (FEAT-33) has none.
  - **Local daemon.** A `not_executed` answer makes `HttpApi` rerun that call on `LocalApi`, silently. A daemon that cannot be reached or started gives way to `LocalApi` as ADR-1052, point 11, says.
  - **Squad hosted elsewhere.** A `503 retiring` answer makes `HttpApi` resolve the endpoint again and send the call once more, which is safe because nothing ran. A second refusal fails with `error: the squad served at <endpoint> is restarting; re-run the command in a moment.` A server that cannot be reached fails with `error: cannot reach the squad served at <endpoint>: <cause>.` Both exit 1, and nothing runs locally.
  - **Either endpoint.** A `vocabulary_mismatch` is never retried and never falls back. A connection lost after the request was sent is an error and is never replayed (ADR-1052, point 10). Ctrl-C stops the client's wait, and a call the daemon has started runs to completion.
- **The forwarder in `squads.__main__` goes.** The remote client is the CLI itself, which parses, validates, renders and never imports `_services`. Its cost is held to the budget below.
- **Parity.** The mode-parity CI job of ADR-1172 reruns the surface suite with `HttpApi` against the daemon's application served in-process. What it proves is that a DTO round-trips through JSON (ADR-1224, point 2) and that the error table keeps messages and exit codes.

#### What the client reads, and the vocabulary hash

The operator ruled on 2026-10-28 that in remote mode the CLI reads nothing from the squad (comment 88165cc), and that the client's repository carries the same overrides and vocabulary as the server: the CLI parses with its own vocabulary and sends a hash of it with its one call, and the server refuses on a mismatch, with no vocabulary fetch and no cache (comment 7f4f1d5). The two hold together because of what each reads:

- **The squad** is what lies behind the API: items, the index, discussions, roster entries, memory, notices, and the derived state computed from them. The remote client reads none of it.
- **The repository's configuration** is the set of committed files every checkout carries. The client reads two parts of it:
  - for endpoint resolution, the `.squads.toml` that the walk-up finds, of which it uses `squad_dir` and `[daemon]` only;
  - for parsing, the bundled `workflow.toml` of its own installed package and the checkout's `<squad_dir>/.overrides/workflow.toml`.

  Local mode also checks the override against the index before parsing (`validate_against_index_fail_closed`). That reads the squad, so in remote mode it is the daemon's, inside its composition.

**What the hash covers** is exactly what the CLI reads before its call, and nothing else:

| Document | In | Why |
|---|---|---|
| The bundled `workflow.toml` | yes | the base of the merged spec. Two versions that ship the same bundled spec give the same hash, so the hash follows the vocabulary, not the version number. |
| `<squad_dir>/.overrides/workflow.toml`, or its absence | yes | types, aliases, statuses, badge fields and codes: the command tree, option help and the exit-2 checks |
| The playbook, bundled and override | no | it shapes skills and guidance text, which only operations produce |
| The role catalog, bundled and override, and per-role override files | no | roster slugs are checked by the operation (ADR-1224, point 1) |
| `.overrides/templates/` and view transforms | no | the operation renders and runs them (ADR-1224, point 5) |
| `.squads.toml`: `schema_version` | no | the schema gate is the operation's `grant`, checked by the daemon |
| `.squads.toml`: `working_language`, `[display]`, `active_backends`, `init_names` | no | they reach the client as DTO content or warnings, or concern `init` only |
| `.squads.toml`: `squad_dir`, `[daemon]` | no | they choose the endpoint; a client that resolved another squad reaches another daemon, by the key |

A document is in the hash if and only if the CLI reads it before its call. The hash and the CLI's spec loading take their bytes from the one function that reads the documents (`spec_sources`), so what is hashed is what was parsed. A `tests/meta` guard fails if the parser reaches a document the hash leaves out.

**How both sides compute it.** One standard-library function in `_api` hashes canonical bytes, not the parsed spec:

- The input is a fixed sequence: the format tag `squads-vocabulary-1`, then for each document in a fixed order its name and either the marker `absent` or its text. The text is the file decoded as UTF-8 with a leading byte-order mark removed and CRLF or CR line ends turned into LF. Every field is length-prefixed.
- The hash is the SHA-256 of that sequence, as 64 hexadecimal digits. It takes 0.2 ms for both documents (measured).
- The daemon computes it at startup from the bytes it loaded, beside ADR-1052's retirement fingerprint, and reports it with one digest per document at `GET /v1/daemon`.
- Bytes rather than the parsed spec, because the result does not depend on the loader's code: a client and a daemon of different versions compare what they actually hold. The cost is that an edit to comments or layout alone changes the hash. That is a refusal the remedy clears, never a wrong parse. Line ends are normalised because a Windows checkout with `core.autocrlf` would otherwise never match a POSIX daemon.

**The mismatch answer.** The daemon checks the header before running anything:

1. It runs its retirement check first (ADR-1052, point 13). If its configuration changed since it started, it answers `503 {"not_executed": "retiring"}`, which the client handles as any retirement: locally against a local daemon, by one retry against the re-resolved endpoint for a hosted squad. Against a local daemon this is what a mismatch normally is: a daemon older than the checkout's last edit.
2. If its configuration did not change, the divergence is real. It answers `409` with the error type `vocabulary_mismatch` and the per-document digests. The CLI compares them with its own and names what differs:

   `error: this checkout's workflow vocabulary differs from the squad served at <endpoint> (<document> differs). Bring this checkout in line with the squad, by pulling its configuration or installing the squads version it runs, then re-run.`

   It exits 1 and does not fall back: a local run would answer from a vocabulary the squad does not hold.

For a local daemon the second case needs a configuration the daemon never loaded, which the retirement check rules out, so it signals a defect. For a squad hosted elsewhere (FEAT-33) it is the expected way a stale checkout is caught.

#### Every other read of the squad's directory, and its remote answer

| What the CLI reads today | Where | In remote mode |
|---|---|---|
| The `.squads.toml` walk-up (`_paths.resolve`) | the root callback and most commands | endpoint resolution only: `squad_dir` and `[daemon]` |
| The workflow spec and its override (`bind_active_spec`, `resolve_spec_for_ctx`, `_CustomTypeGroup`) | parsing, option help, `--help`, completion | read from the checkout and hashed (above). `--help` and completion make no call. |
| The override's cross-check against the index | `bind_active_spec` | the daemon's composition; a contradiction comes back as the operation's error |
| The schema gate (`require_current_schema`, `apply_gate`, `config.schema_version` in `migrate`) | the root callback and the gated groups | the operation's `grant` (ADR-1224, point 4), checked by the daemon; the hard stop is a `409 conflict` with today's text |
| The working-language notice | the root callback | a `warnings` entry, on a response or on a refused call's error; a refusal the CLI makes before any call (a vocabulary exit 2) carries none, since the CLI does not read the configuration, and the next call that runs prints it |
| `[display] pronouns` and role resolution against the squad directory | role, operator and dev rendering | DTO content (ADR-1224, point 5) |
| Template overrides (`from_squad`) | `workflow view`, the rendered body of `show` | DTO content |
| The playbook and role catalog (`invocation_sources`) | the cheatsheet, roster commands | operations |
| Override scans, `workflow lint`, `check`'s own composition | `override …`, `workflow lint`, `check` | operations |
| `.squads.toml` and the process directory in `init` and `adopt` | squad creation | local only, by definition |
| `-C` checks (`effective_dir`), `--file`, `-` and the import file | the client's own directories and files | unchanged: they are the client's, and their text travels in the request DTO |
| `path_from_process_dir` | message spelling | no read: the `Squads-Client-Dir` header |
| Session ids, `--at`, `--as` | environment and options | headers |

**Endpoint resolution** is the one read that locates the squad. It reads, in order: `SQUADS_DAEMON`; the `.squads.toml` found by the walk-up from the effective directory, for `squad_dir` and `[daemon]`; the real path of the squad directory, a path operation that reads none of its contents, to make the key; and in the per-user runtime directory, `<key>.json` and `<key>.sock` (ADR-1052, point 8). It is also why a remote client needs a checkout. The function returns an `Endpoint`: transport, address, how to check the daemon's identity, and whether a local fallback exists. For a squad hosted elsewhere (FEAT-33), it gains a source ahead of the local key, an endpoint the client's own settings name, and returns the same `Endpoint` with no local fallback. `HttpApi`, the hash and the table above do not change; the client then leaves out `Squads-Client-Dir`, so paths in messages are spelled from the squad's root.

#### The client budget

The operator ruled on 2026-10-28 that the remote client aims lower than about 0.3 s, with a measured budget as a 0.18 criterion (comment 8017910). Measured on 2026-10-28 on the WSL2 development host, Python 3.14.8: a prototype client that makes one call over a Unix socket to a server answering with TASK-1217's `show` payload, then renders it. Medians of 31 interleaved runs:

| Run | Median | p25-p75 |
|---|---|---|
| Today: local `show`, released package | 915 ms | 870-1005 |
| Today: local `show --json` | 867 ms | 812-951 |
| Client of `typer`, `rich`, `http.client` and the vocabulary, no levers | 402 ms | 359-441 |
| All levers, the checkout's vocabulary, human | 266 ms | 253-304 |
| All levers, the checkout's vocabulary, `--json` | 228 ms | 212-271 |
| All levers, no vocabulary, human | 215 ms | 192-245 |
| All levers, no vocabulary, `--json` | 159 ms | 142-179 |
| The bare interpreter | 13 ms | 12-17 |

The levers, each measured on its own:

| Lever | Measured effect |
|---|---|
| Never import `_services` (ADR-1224, point 2) | `import squads._cli` 0.61 s wall; the client set 0.30-0.40 s |
| `gc.freeze()` once output is flushed, before the interpreter exits | today's full CLI import 608 to 427 ms; the client 369 to 314 ms. Teardown spends this collecting module objects. |
| `gc.disable()` for the start-up | 314 to 281 ms on the client |
| Lazy command modules: the root group maps a command name to its module and imports only that one; root `--help` still loads all | Typer converts the whole tree on every invocation, 76-84 ms; one group 0.5-2 ms |
| `__version__` without `importlib.metadata` at import | 23-49 ms in-process |
| DTOs in one module per resource, with pydantic's `defer_build` | 180 models: 119-124 ms eager, 34-46 ms deferred |
| `rich.markdown` imported only when a body is rendered | 23-50 ms in-process; `--json` never pays it |
| `asyncio` without `anyio` on the client | `anyio` 12-30 ms in-process |
| Off the client path: `jinja2`, `yaml`, `filelock` | 12-30, 13 and 6 ms |
| The loader path trimmed to what loading needs (the override scaffolding and manifest modules are not) | about 15 ms of the 43-53 ms the loader chain takes |

The vocabulary is the ruling's price: 51 ms human and 69 ms `--json` (the two pairs of rows above). Of it, the spec model module takes 44-58 ms, the loader, merge and override modules 43-53 ms, the TOML parse, merge and validation 2 ms, and the hash 0.2 ms. The model module stays without a cache, which is ruled out.

**The budget,** a 0.18 release criterion: the client's overhead, which is the process's wall time minus the daemon's handler time (sent by the daemon in a `Server-Timing` header), as the median of 31 interleaved runs of `sq <type> <n> show` on the reference host, is at most **275 ms** in human mode and **235 ms** with `--json`. That is 30 % and 27 % of today's local-mode time for the same command. The prototype meets it with 9 and 7 ms to spare; it lacks the real CLI's dispatch and renderer modules (an estimated 10-20 ms), which the loader trim offsets. The daemon's own work comes on top: a warm `show` takes 45-60 ms in the daemon (measured, inside the read scope), and composing the service once at start-up 74-91 ms.

How it is held:

- **A deterministic guard** in `tests/meta` imports the remote path (root callback, `HttpApi`, the renderer) in a subprocess and fails if `sys.modules` holds `squads._services`, `squads._index`, `jinja2`, `yaml`, `anyio`, `filelock`, `importlib.metadata`, `starlette` or `uvicorn`, or holds `rich.markdown` before a body is rendered.
- **A benchmark script** measures the budget. The release runbook runs it on the reference host and records the numbers with the release. CI runs it as a report, not a gate: this host alone spread 40-90 ms between p25 and p75.

What the budget costs in design: a literal command-name table at the root, guarded against the registered tree; DTO modules split by resource; a version string that does not come from package metadata; `gc` handling in `main`; `anyio` confined to the service side; and renderer modules that import only `rich` and `_api`. Local mode gets the same levers, apart from the ones that only remove `_services`.

### 6. The HTTP server: Starlette on uvicorn

The operator ruled on 2026-10-28 that the daemon's HTTP server uses a framework, FastAPI or Starlette, rather than the standard library (comment 8017910). Measured on 2026-10-28 in a throwaway environment, Python 3.14.8, with FastAPI 0.162.0, Starlette 1.10.0, uvicorn 0.54.0 and pydantic 2.14.1:

| | Starlette | FastAPI | uvicorn |
|---|---|---|---|
| Import, wall (bare interpreter 11 ms, pydantic 68 ms) | 98 ms | 316 ms | 115 ms |
| An application with 90 routes | 2-9 ms | 129-214 ms, plus 199-246 ms for its first `openapi()` | |
| Packages added to squads' dependencies | `starlette` (its `anyio` is already one) | `fastapi`, `opentelemetry-api`, `annotated-doc`, plus Starlette's | `uvicorn`, `h11`, `click` |
| Size on disk | 0.7 MB | 1.9 MB, plus 0.5 MB for `opentelemetry` | 0.6 MB, `h11` 0.1 MB, `click` 0.9 MB |

**The daemon uses Starlette, served by uvicorn.**

- **Routing from the operation table.** The router is a loop over the table: one Starlette `Route` per operation, all with one generic endpoint that validates the request DTO (from the query for a `GET`, from the JSON body otherwise), awaits `LocalApi`, and writes the `Response[T]` envelope or the error of point 3. FastAPI's strength is deriving parsing and documentation from each endpoint's signature. Here that would mean generating about 90 signatures to restate what the table already declares.
- **OpenAPI from the table.** `GET /v1/openapi.json` returns an OpenAPI 3.1 document built from the table: for each operation, its method and path, its path and query parameters from the request DTO's fields, its body and response schemas from pydantic (`models_json_schema`, JSON Schema 2020-12, which OpenAPI 3.1 uses as is), and the error envelope for each status of point 3. It is built at the first request. A `tests/meta` guard checks that it describes every operation. It replaces a separate schema route.
- **Admission rules as one ASGI middleware,** ahead of routing: the `Host`, `Origin`, `Content-Type` and `Squads-Client` checks of ADR-1052, point 5, decided by the listener a connection arrived on.
- **Listeners.** The daemon binds its own sockets, with the permissions and ports ADR-1052 sets: the Unix socket in the `0700` runtime directory with mode `0600` on POSIX, the loopback CLI port on native Windows, and the browser port when enabled. It hands all of them to one `uvicorn.Server` (`serve(sockets=[…])`), so one application serves every listener. uvicorn runs on the asyncio loop on POSIX and on native Windows. Its `standard` extra (`uvloop`, `httptools`) is not used; `h11` is enough for one local client at a time.
- **pydantic v2 DTOs** need nothing from the framework beyond `model_validate` and `model_dump_json`.
- **Import time** is paid by the daemon at start only: about 0.2 s for Starlette and uvicorn, against about 0.43 s for FastAPI and uvicorn plus its route building. The CLI never imports either (section 5).

**The remote client stays `HttpApi` on `http.client`.** It makes one request per call over a Unix socket or loopback TCP. Neither framework is a client, and `httpx` would add a dependency and client import time for nothing it needs.

**Packaging: required dependencies, not an extra.** `starlette` and `uvicorn` join `[project] dependencies`. The daemon is on by default (ADR-1052, point 7), and an extra would leave most adopters who run `pip install squads` in local mode without telling them why. The two weigh about 2.3 MB of pure Python with `h11` and `click`, and the client never imports them, so the budget does not pay for them. One install shape means one test matrix.

### 7. The daemon's request scope

The scope replaces ADR-1052, point 12, and is still one context manager beside the composition function (ADR-1128). For each request it:

- runs in a fresh `contextvars.Context`;
- binds a `RequestContext` from the headers and the documents loaded at startup;
- checks `Squads-Schema`, then `Squads-Vocabulary` (section 3, section 5), then the squad's schema against the operation's `grant` (ADR-955);
- gets the service for the operation's `mode`. The normal-mode service is built once at startup, and a fallback mode is composed for the request from the documents already loaded;
- opens the read scope (ADR-753), awaits the handler, serialises the envelope and closes everything.

It does not redirect stdio, set environment variables, build consoles or parse a command line. Requests still run one at a time, behind one `asyncio.Lock` around the handler, so writes order as they do today and no new concurrency is introduced in 0.18. Because nothing patches process state any more, ADR-1052's change condition "commands must run concurrently" now costs only the worker pool.

### 8. ADR-1052: amended on acceptance, not superseded

Board rule 6 decides between the two. Transport, admission, security, settings, discovery, lifecycle, staleness, writes and version skew still hold, so this is a clause-level change: ADR-1052 is narrowed in place, its discussion records what changed, and the two decisions are linked `related`. The amendment:

- **Title and summary.** "one command API" becomes "the daemon's transports, lifecycle and requests", and the summary points to this decision for the API's shape.
- **Context.** The 2026-10-25 "one command endpoint" bullet gains the 2026-10-28 reversal.
- **Options and decision.** Option I is replaced by this decision. Option II's rejection, and with it FEAT-33's `RemoteService`, are recorded as reconsidered here.
- **Point 1.** `POST /v1/commands` and its wire encoding (argv, `cwd`, `env`, `terminal`, attachments in base64) are removed. `GET /v1/daemon`, which now also reports the vocabulary hash, `POST /v1/daemon/stop` and "UTF-8 JSON bodies" stay, and `GET /v1/openapi.json` joins them.
- **Point 2.** `not_executed` keeps only `retiring`.
- **Point 3.** The standard-library server is replaced by Starlette on uvicorn (section 6), which adds two required dependencies. The client stays on `http.client`.
- **Point 9.** The standard-library forwarder, the attachments, the file-argument table and its guard, and the shared client-file helper are removed. The shared endpoint-resolution function stays and is now called by the root callback. It reads only what section 5 lists under endpoint resolution, and returns an `Endpoint` that a hosted squad's source can later produce too.
- **Point 10.** Writing the received stdout and stderr, and the forwarder's Windows stream setup, are removed. Running a `not_executed` call locally applies only where the endpoint has a local mode (section 5). No replay after sending, Ctrl-C and output at the end stay.
- **Point 12.** Replaced by section 7 above. Serial execution stays. The `needs_terminal` prompt branch and its "built without a test" note are removed.
- **Unchanged:** points 4 to 8, 11 and 13 to 15. Point 13's retirement check now also decides how a vocabulary mismatch is answered (section 5).
- **Consequences.** "The CLI layer changes before the daemon can run it" now points to ADR-1224. "Remote mode is faster only because the forwarder skips CLI construction" becomes the client budget of section 5. The `FEAT-33` bullet names `HttpApi` as the seam instead of the command endpoint.

ADR-1172 is amended on acceptance as well. Its section "The daemon's command endpoint" becomes "The daemon's routes". The parity run (above) covers every operation over HTTP, so route tests are kept only for what it cannot see: one case per row of the error table, a vocabulary mismatch on an unchanged and on a changed configuration, the OpenAPI document covering every operation, a partial read's envelope, the binding of each metadata header, a `GET` that does not mutate, and the admission negatives already listed in ADR-1052. They follow rules 4 to 6 and carry no `covers` marker. The cross-process set and the mode-parity job are unchanged.

### 9. TASK-1217's delivered code

Kept:

- `run(argv)`, the entry `squads.__main__:main` calls;
- consoles built per invocation;
- `RequestContext.start_dir`, now seeded from `Squads-Client-Dir`, with `path_from_process_dir` spelling from it;
- `RequestContext.documents`, the daemon's startup documents;
- `_paths.process_dir()` as the one read of the process directory.

Removed once the remote client is the CLI:

- `RequestContext.attachments`, `terminal` and `consoles` as request seeds, and `run`'s `seed` parameter;
- `client_path` served from attachments;
- `NeedsTerminal`, `confirm_or_signal` and `prompt_or_signal`, which become plain `typer.confirm` and `typer.prompt` again;
- the root callback's copying of seeded terminal facts.

REV-1223's deferred F3, F4, F6 and F8 lose their subject with that removal. Their disposition is the reviewer's.

### 10. Order of the work, and what gates what

- **D1, the daemon process** (TASK-1218, reshaped), on Starlette and uvicorn with the OpenAPI document. It starts once increment 0 of ADR-1224 has landed (the operation table, the envelope, the error form). The daemon routes from the table, so it serves each operation as the refactor adds it. Settings, discovery, lifecycle, admission and the browser port are ADR-1052's and do not wait for the refactor.
- **D2, remote mode** (TASK-1219, reshaped) follows D1: the root callback's API selection, endpoint resolution, implicit start, fall back, `HttpApi` and the vocabulary hash. The budget's levers and guard land with it. A command not yet moved onto an operation runs locally, so remote mode can be trialled early with `SQUADS_DAEMON=on` (ADR-1052, point 7).
- **The mode-parity job** is switched on with D2 and covers what has moved.
- **The release gate:** every command on an operation (ADR-1224's increment 5) and the TUI on the `Api` in both modes (its increment 6), the client budget of section 5 met on the reference host with its import guard green, and the parity job, the cross-process set and the surface suite green on Linux, macOS and native Windows.
- CI (TASK-1220), adopter documentation (TASK-1221, which now documents the routes, the envelope, the error table and the DTO schemas) and the dogfood (TASK-1222) keep their places.

Board changes that follow acceptance, for their owners:

- the product owner rewrites FEAT-1140's US1, US2, US3, US9 and US10 and its FEAT-33 boundary, and re-reads FEAT-33;
- the tech lead rewrites TASK-1218 and TASK-1219 and breaks the refactor into its tasks.

## Consequences

- One API serves two clients, as ruled on 2026-10-16: the CLI's remote mode and the web front call the same routes, and there is no second protocol.
- The command endpoint's machinery goes: argv over the wire, stdio and environment patching, terminal facts and attachments. So do the parity questions it raised about Rich's rendering in another process. The renderer always runs in the user's own process.
- A remote command costs the client budget, at most 275 ms in human mode and 235 ms with `--json` on the reference host, plus the operation's own work in the daemon, 45-60 ms for a warm `show`. Local mode takes 0.87-0.92 s today. ADR-1052's 0.1 s is not reached, because the client parses with the checkout's vocabulary and renders with Rich.
- Using a squad remotely needs a checkout that carries its workflow configuration. A divergence is refused before anything runs, never parsed around.
- Synchronising the workflow configuration between a client repository and a hosted squad is planned with a real remote mode (FEAT-33). The per-document digests that `GET /v1/daemon` and the mismatch answer already carry leave room for it.
- `starlette`, `uvicorn`, `h11` and `click` become dependencies of every install; only the daemon imports them.
- Adding a command means adding an operation, which gives it a route. The router, `HttpApi` and the parity run need no change.
- The HTTP surface is the DTO surface. A shape that had no `--json` before 0.18 is provisional until the web front consumes it (ADR-1224, point 3).

## Options considered and rejected

- **Keep `POST /v1/commands` beside the routes.** That is two protocols for one daemon, against the 2026-10-16 "one API" ruling. It would also keep every piece of machinery section 9 removes.
- **One RPC route per operation (`POST /v1/ops/{name}`).** It is the smallest router, but it loses `GET` semantics, which the admission rules use as the cross-site defence, and it is not the resource shape the operator asked for.
- **A standard-library forwarder that also renders,** to keep the 0.1 s client. It would be a second renderer, without Rich, that has to produce the same bytes as the first. That is the drift ADR-1224 exists to remove.
- **Fetch the vocabulary from the daemon,** at each call or cached on the client. Ruled out by the operator on 2026-10-28 in favour of the hash. Measured, a fetch at each call cost 15-40 ms over parsing with no vocabulary.
- **Hash the parsed spec** rather than the documents' bytes. Comment and layout edits would not change it, but the hash would depend on the loader's code, so two versions holding the same files could disagree, and the client would pay a model dump.
- **The standard-library server** of ADR-1052, point 3. Ruled out by the operator on 2026-10-28.
- **FastAPI.** It would give OpenAPI from signatures that the table makes redundant, at three times Starlette's import time, 0.13-0.21 s to build 90 routes, and two more packages.
- **A `squads[daemon]` extra.** Without it, the default would resolve to local mode silently, an explicit `enabled = true` or `SQUADS_DAEMON=on` would print ADR-1052's one line on stderr, and `sq daemon start` would refuse with the install command, as `sq ui` does for `tui`. Rejected because the daemon is on by default, so the extra would leave most adopters without it, for 2.3 MB saved.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T20:59:22Z] `architect` Robert Architect:
  - Drafted 2026-10-28 with ADR-1224. Reverses ADR-1052 option I per the op-pierre direction of 2026-10-28; ADR-1052 and ADR-1172 are amended only on acceptance, as section 7 lists (clause-level, board rule 6: related, not supersedes). Measured: a CLI without _services imports in 0.29-0.37 s against 0.83-1.12 s for a local show.
  - @op-pierre Q5 (remote-mode cost) and Q6 (stdlib server) are at the end of the body. On acceptance: @product-owner rewrites FEAT-1140 US1/US2/US3/US9/US10 and the FEAT-33 boundary; @tech-lead reshapes TASK-1218/1219 and breaks the refactor into tasks (ADR-1224 section 7).
- [2026-10-28T21:07:23Z] `op-pierre` Pierre Chat:
  - 2026-10-28 answers: Q5 do not settle for ~0.3 s: aim lower, with a measured client budget as a 0.18 criterion (propose the number and how to reach it). Q6 use a framework (FastAPI/Starlette) for the daemon's HTTP server rather than the standard library.
- [2026-10-28T21:16:29Z] `op-pierre` Pierre Chat:
  - 2026-10-28: in remote mode the CLI must not assume the squad's files are on its machine. It reads nothing from the squad itself; the vocabulary and everything else it needs comes through the API. Reading the spec from local files in remote mode is rejected.
- [2026-10-28T21:22:16Z] `op-pierre` Pierre Chat:
  - 2026-10-28, vocabulary in remote mode: the client's local repository must carry the same overrides and vocabulary as the server. The CLI parses with its local vocabulary and sends a hash of it with its single call; the server compares it with its own and refuses on a mismatch. No vocabulary fetch, no cache. The renderer still takes everything it displays from the DTO.
- [2026-10-28T21:31:34Z] `architect` Robert Architect:
  - Folded the 2026-10-28 op-pierre rulings (8017910, 88165cc, 7f4f1d5) into the body; the questions section is gone and "the squad is on this machine" is removed.
    - Remote reads (88165cc, 7f4f1d5): section 5 now separates the squad (behind the API) from the repository's configuration. The client reads only `.squads.toml` (`squad_dir`, `[daemon]`) for endpoint resolution, plus the bundled and override `workflow.toml` for parsing. `Squads-Vocabulary` carries a SHA-256 of canonical bytes over exactly those two documents; the playbook, roles, templates and other config keys are excluded, with reasons in a table. On a mismatch the daemon runs its retirement check first, so a stale local daemon answers 503 retiring and the client runs locally. A real divergence answers 409 `vocabulary_mismatch`, with no fallback. Section 5 also has an inventory of every client read with its remote answer, and an `Endpoint` seam for FEAT-33.
    - Q5 (8017910): the budget is the client overhead, the median of 31 runs of `show`: at most 275 ms human and 235 ms `--json` (today 915/867 ms). The prototype measured 266/228 ms. The measured levers: gc.freeze at exit, gc.disable at start, lazy command modules, version without metadata, deferred DTO modules, lazy rich.markdown, no anyio, loader trim. Parsing with the checkout's vocabulary costs 51-69 ms. A deterministic import guard holds the budget, and a benchmark script runs at release.
    - Q6 (8017910): Starlette on uvicorn (section 6). Measured imports: Starlette 98 ms, uvicorn 115 ms, FastAPI 316 ms (90 routes: 2-9 ms against 129-214 ms plus 199-246 ms for openapi). Routes come from the operation table, `GET /v1/openapi.json` is generated from the table (it replaces the schema route), admission is one ASGI middleware, and the daemon binds its own sockets and hands them to `serve(sockets=...)`. `starlette` and `uvicorn` become required dependencies, not an extra; the extra is listed as rejected, with how it would behave. `HttpApi` stays on the standard library.
    - ADR-1052's amendment list now also replaces point 3 and states point 9's endpoint read. The release gate adds the TUI and the budget.
- [2026-10-28T21:31:56Z] `architect` Robert Architect:
  - Added one Consequences line per the op-pierre note on FEAT-33: spec synchronisation between client repository and hosted squad is a later FEAT-33 change; the per-document digests leave room for it. Not designed here.
- [2026-10-28T21:44:38Z] `op-pierre` Pierre Chat:
  - 2026-10-28: fall back to local mode only when the resolved endpoint has a local mode (a local daemon). For a squad hosted elsewhere: on 503 retiring, retry the call once against the re-resolved endpoint, then fail with a clear error; an unreachable server fails with a clear error, exit 1, no fall back. The TUI follows the same rule. With that correction, ADR-1224 and ADR-1225 are accepted.
- [2026-10-28T21:46:05Z] `architect` Robert Architect:
  - Section 5 corrected per op-pierre 3fbbd10. Fall back is now conditional on the Endpoint having a local mode. A local daemon behaves as written. For a hosted squad, a 503 retiring gets one retry against the re-resolved endpoint, then a clear error; an unreachable server is a clear error, exit 1, with no fall back. vocabulary_mismatch is unchanged. The refusal bullet of section 3, the mismatch step 1 and the point 10 amendment line are aligned with it.
- [2026-10-28T21:48:12Z] `manager` Catherine Manager:
  - Accepted 2026-10-28 per op-pierre, with the conditional fall back; ADR-1052 and ADR-1172 amended accordingly.
- [2026-10-28T21:53:25Z] `op-pierre` Pierre Chat:
  - 2026-10-28, gaps raised by the manager: (1) client/server compatibility: the DTOs are tied to the schema version, and an incompatible change takes the path we already have for a schema change (schema version bump, hard stop, migrate); a client and server on different schema versions refuse the same way. (2) Writes carry an ETag / If-Match check: a write on an item changed since it was read answers 409. (3) comment remove sends the confirmed hashes and refuses if the selection changed. (4) Set the HttpApi timeout policy for long operations (migrate, repair, import, renumber). (5) State plainly in the ADR and the adopter docs that the Squads-Actor header is declarative, with no authentication.
- [2026-10-28T21:56:12Z] `architect` Robert Architect:
  - Amended in place per op-pierre 8de91f7, with the coordinator's follow-up on comments (board rule 6). Status is unchanged.
    - (1) Compatibility, a new subsection of section 3. An incompatible DTO change is a schema change: SCHEMA_VERSION bump, a migration runner (stamp-only when the corpus does not change), the hard stop and `sq migrate up`. The tier in docs/stability.md still decides whether the change may happen at all. `/v1` versions only the route grammar and the envelope.
      - Clients send `Squads-Schema`; any difference answers 409 `schema_mismatch` with a behind or ahead remedy, exit 1, no fall back.
      - The check order is schema, then vocabulary, then the grant.
      - The rule matters for a hosted squad; a local daemon is already keyed per version.
    - (2) ETags: the SHA-256 of the item file's bytes. It is derived, the file is the source of truth, and `updated_at` was rejected.
      - Returned on item and sub-entity reads and writes; the show DTO carries `etag`, provisional.
      - `If-Match` covers item-level and sub-entity writes. It is checked inside the transaction after the re-read, and a mismatch answers 409 `changed_since_read`.
      - Comments need no ETag: their content-derived hash already plays that role (verified in `_discussion.comment_hash`).
      - CLI one-call writes send no precondition, which is safe because they are field-level changes validated under the lock.
    - (3) `comment remove` without `--yes` sends the previewed full hash. A comment edited or removed since no longer resolves (404, nothing removed); a byte-identical duplicate copy added or removed meanwhile is handled as any duplicate group is today. No new error type.
    - (4) Timeouts are a `timeout` class in the operation table. `standard` is 5 s to connect and 300 s to answer, queue time included. `long` (migrate up/repad/rename-type/rename-status, repair, renumber, import) has no answer timeout, with a stderr notice after 10 s.
      - A timeout or Ctrl-C ends only the wait: no replay, no fall back, a "may still complete" message, exit 1 or 130.
      - A connect timeout is treated as an unreachable daemon.
    - (5) `Squads-Actor` is stated as declarative and unauthenticated, with the same untrusted standing as the session ids; TASK-1221's adopter docs must say so.
    - Pagination is left out (MILE-868).
- [2026-10-28T22:33:52Z] `architect` Robert Architect:
  - Amended in place 2026-10-28 for the open points TASK-1229 and TASK-1218 raised (board rule 6). Status unchanged.
  - Section 1, new bullet and table row: a roster entry's discussion is served at `/v1/{roles,skills,operators}/{addr}/comments[/{hash}]`, with the item comment methods and DTOs (`addr` in place of `id`). The operation resolves `addr` within the route's kind, and the kind is never a request field. An unresolved address answers 404 with today's text.
  - Section 3, ETags, new bullet "How the ETag travels": `If-Match` in and the new `ETag` out both go on the request's `RequestContext`, never in a DTO or the envelope. The write records the hash of the addressed file's bytes at the end of the transaction, under the lock, and the generic endpoint writes the header. A remove answers with none. Rejected and recorded: an envelope field and an etag on the write rows.
  - @tech-lead TASK-1229 and TASK-1218 can be updated.
- [2026-10-29T04:58:58Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for REV-1235 F35 (board rule 6). Status unchanged. Section 1: the comment removal preview is `GET …/comments/{hash}/removal` under items, sub-entities and roster entries. It is a read, on a sub-resource named for what it returns, and it is distinct from `show`.
- [2026-10-29T07:04:37Z] `architect` Robert Architect:
  - Amended in place 2026-10-29 for REV-1235 F48 (board rule 6). Status unchanged.
  - Section 3, errors: the envelope gains `warnings`, an empty list when there is none, with the meaning a response's `warnings` has. `HttpApi` attaches it to the `SquadsError` it raises.
  - Notice row: the notice rides on a response or on a refused call's error. A refusal the CLI makes before any call carries none, which is accepted, since the CLI does not read the configuration.
<!-- sq:discussion:end -->
