# The squad API

A running daemon (see [daemon.md](daemon.md)) serves the squad as an HTTP API. Every command of the
CLI is one operation of this API, and the CLI in remote mode calls it exactly as any other client
would: the terminal browser, a script, or a web front. This page is the reference for writing such
a client. The exact routes, parameters and result schemas are in the OpenAPI document the daemon
serves; this page explains the rules around them.

## Reaching the daemon

`sq daemon status` (or `--json`) lists the daemon's listeners:

- **the CLI listener:** on Linux, macOS and WSL2 a Unix socket, `<runtime-dir>/<key>.sock`; on
  native Windows a loopback port, `127.0.0.1:<port>`;
- **the browser listener,** when `browser = true` in the `[daemon]` table: a loopback port,
  `127.0.0.1:<port>` and `[::1]:<port>`.

A port is chosen when the daemon starts and changes at each start, so read it from
`sq daemon status --json` (or from `<key>.json` in the runtime directory) rather than storing it.
The daemon must be running: a command in remote mode starts it, and a client of its own reads it
only while it runs.

```
$ curl -s --unix-socket /run/user/1000/squads/aebdaea5929e.sock http://localhost/v1/items/TASK-<n>
$ curl -s http://127.0.0.1:34973/v1/items/TASK-<n>
```

Over a TCP listener a request must meet the admission rules in [Admission](#admission).

## The OpenAPI document

`GET /v1/openapi.json` returns an OpenAPI 3.1 document describing every operation the daemon
serves: its method and path, its path and query parameters, its request body, its result schema,
the response headers it sends, and the error body of each status it can answer with. Generate a
client's types from it. Its `info.version` is the squad's schema version, which is the value to
send in `Squads-Schema` (see [Compatibility](#compatibility)).

The document is the same for every squad. A squad's own vocabulary (its item types, statuses, badge
fields, sub-entity kinds and attributes) travels in the results, not in the schemas; see
[How a result carries the squad's vocabulary](#how-a-result-carries-the-squads-vocabulary).

## Routes

Every route is under `/v1`. Each command of the CLI is one operation at one route:

| Command | Route |
|---|---|
| `sq <type> <n> show`, `sq show <id>` | `GET /v1/items/{id}` |
| `sq list …` | `GET /v1/items?type=…&status=…&badge=…` |
| `sq create <type> …` | `POST /v1/items` (the type in the body) |
| `sq <type> <n> update …` | `PATCH /v1/items/{id}` |
| `sq <type> <n> status <status>` | `POST /v1/items/{id}/status` |
| `sq <type> <n> body …` | `PUT /v1/items/{id}/body` |
| `sq <type> <n> remove` | `DELETE /v1/items/{id}` |
| `sq <type> <n> comment …` | `POST`, `GET`, `PATCH`, `DELETE` on `/v1/items/{id}/comments[/{hash}]` |
| `sq <type> <n> <kind> <k> …` | `/v1/items/{id}/subentities[/{local}]`, with `/body` and `/comments` under it |
| `sq role <addr> …`, `sq skill <addr> …`, `sq operator <addr> …` | `/v1/roles/{addr}`, `/v1/skills/{addr}`, `/v1/operators/{addr}` and the same sub-resources |
| `sq tree`, `sq graph`, `sq search` | `GET /v1/tree`, `GET /v1/graph`, `GET /v1/search` |
| `sq inbox <role>`, `sq mine <role>` | `GET /v1/inbox/{slug}`, `GET /v1/mine/{slug}` |
| `sq memory <role> show <slug>`, `sq memory <role> search <query>` | `GET /v1/memory/{role}/{slug}`, `GET /v1/search/memory/{role}?query=…` |
| `sq workflow types` and the other catalogs | `GET /v1/workflow/{catalog}` |
| `sq repair`, `sq migrate up`, `sq import`, … | `POST /v1/squad/repair`, `POST /v1/squad/migrate`, `POST /v1/squad/import`, … |

The OpenAPI document lists every route. The grammar behind them:

- **Items are addressed by id only,** `/v1/items/TASK-<n>`, whatever their type, so a custom type
  needs no route of its own. Roles, skills and operators are addressed by slug, id or number, as on
  the CLI.
- **`GET` reads and never changes anything.** `HEAD` is a `GET` without the body.
- **Writes:** `POST` on a collection creates, `PATCH` updates part of a resource, `PUT …/body`
  replaces a body, `DELETE` removes. Any other action is a `POST` on a sub-resource named after it
  (`…/status`, `…/retype`, `…/regen`).
- **Operations on the whole squad** are `POST` under `/v1/squad/`: `sync`, `repair`, `renumber`,
  `migrate`, `repad`, `rename-type`, `rename-status`, `rename-field`, `rename-kind`, `import`. They
  run to the end before answering, as the commands do.
- `sq init` and `sq adopt` create a squad in the directory they run in, which a daemon serving
  another squad cannot do, so they have no route.

## Requests

- **Parameters.** Fields that are not in the path go in the query string for a `GET`, and in a
  UTF-8 JSON body for every other method. A `GET` takes only flat values; a list parameter repeats
  its key: `?badge=priority=high&badge=severity=major`. A field the operation does not declare is
  refused with `400 invalid`.
- **File content travels as text.** Where a command takes `--file`, `-` or an import file, the
  client reads it and sends its text in the request. The daemon never reads a path a client names.

### Request headers

| Header | Meaning |
|---|---|
| `Squads-Actor` | the slug to record as the actor of a write (the CLI's `--as`). It must be a slug the squad knows, and it is **not verified**: see below |
| `Squads-At` | an ISO 8601 time to record instead of now (the CLI's `--at`) |
| `Squads-Session-Id`, `Squads-Parent-Session-Id` | the caller's session ids, recorded in the reflog |
| `Squads-Client-Dir` | an absolute path: paths in messages are spelled relative to it. Without it they are spelled from the squad's root. A relative path is refused with `400 invalid` |
| `Squads-Schema` | the schema version the client was built for (the OpenAPI document's `info.version`); see [Compatibility](#compatibility) |
| `Squads-Vocabulary` | the hash of the workflow vocabulary a client parsed its request with. The CLI sends it; a client that parses nothing leaves it out |
| `If-Match` | the `ETag` of the item a write addresses, to refuse the write if the item changed; see [Item versions](#item-versions) |
| `Squads-Client: 1` | required on every request that is not a `GET` or `HEAD` on a TCP listener; send it everywhere |

Header values are UTF-8, carried as the raw bytes of the field, so a `Squads-Client-Dir` of
`/tmp/café` arrives as written.

**The actor is declared, not authenticated.** The daemon records whatever actor `Squads-Actor`
names, as long as the squad knows the slug. Anyone who can reach a listener can write under any
actor, so the actor recorded on an item, a comment or a reflog line through the API is a claim. It
has the same standing as the reflog's session ids: useful to read, never proof of who acted. A
write that names no actor is recorded under `system`.

### Admission

On a TCP listener, a request is refused before it reaches any operation when:

- its `Host` is not `127.0.0.1:<port>`, `localhost:<port>` or `[::1]:<port>` for the port it was sent
  to: `421 misdirected`;
- on the Windows CLI port, it carries an `Origin`: `403 forbidden`;
- on the browser listener, a method other than `GET` or `HEAD` carries no `Origin`, or one other
  than `http://` followed by the `Host` it was sent to: `403 forbidden`;
- a method other than `GET` or `HEAD` lacks `Content-Type: application/json` or
  `Squads-Client: 1`: `403 forbidden`.

The checks run in that order and the first that fails answers. The Unix socket is open to your user
only, and applies none of them. No CORS header is ever sent and no preflight is answered, so a web
page served from another origin cannot write. For example, on the browser listener:

```
$ curl -s -X POST -H 'Content-Type: application/json' -H 'Squads-Client: 1' \
    -d '{"status":"InProgress"}' http://127.0.0.1:34973/v1/items/TASK-<n>/status
{"error":{"type":"forbidden","message":"a write needs an Origin equal to this listener's","warnings":[]}}
```

## Responses

An operation that ran answers `200` with this envelope:

```json
{"data": {…}, "omitted": [], "warnings": []}
```

- `data` is the operation's result. Its schema is in the OpenAPI document, and it is what the
  command's `--json` prints (or holds it, for a listing: `--json` prints `data.items`).
- `omitted` lists what a listing could not read, one `{code, source, message}` per entry, as the
  omissions report of `--json` does ([stability.md](stability.md#tier-3---json-output-shapes-stable-additive-changes-only)).
  A non-empty `omitted` on a `200` is a partial result; the CLI exits `4` on it.
- `warnings` holds the notices the CLI prints on stderr, one string each, without the `warning: `
  prefix: the working-language notice, the index lock's waiting notice, a reflog line that could not
  be appended or read.

Two response headers may accompany it: `ETag` (see [Item versions](#item-versions)) and
`Server-Timing: handler;dur=<ms>`, the time the operation took inside the daemon.

## Errors

A request that fails answers with an error status and this body:

```json
{"error": {"type": "not_found", "message": "no item with number 99 (use a full ID like TYPE-99 or bare 99)", "warnings": []}}
```

- `type` is the machine-readable kind of failure. Branch on it with the status, and handle a type
  you do not know as the generic failure of its status.
- `message` is the sentence the CLI prints after `error: `, the same in both modes.
- `warnings` has the meaning it has in the envelope, so a refused call still carries the notices
  that preceded it; it is an empty list when there is none.
- `details`, present only on `schema_mismatch` and `vocabulary_mismatch`, maps names to strings
  (see [Compatibility](#compatibility)).

| Status | `type` | When |
|---|---|---|
| 400 | `invalid` | any other refusal: a bad value, an unknown field, an unknown slug, a relative `Squads-Client-Dir` |
| 403 | `forbidden` | an admission rule refused the request (above) |
| 404 | `not_found` | an unknown item, roster entry, comment hash or sub-entity, or a path no route serves (`no such route`) |
| 405 | `invalid` | the path exists but not with this method; the `Allow` header lists the methods it takes |
| 409 | `conflict` | a refused status transition, or a squad whose schema is behind the daemon (run `sq migrate up`) |
| 409 | `changed_since_read` | the `If-Match` does not match the item's current `ETag`; nothing was written |
| 409 | `schema_mismatch` | `Squads-Schema` differs from the daemon's schema version; nothing ran |
| 409 | `vocabulary_mismatch` | `Squads-Vocabulary` differs from the daemon's vocabulary; nothing ran |
| 421 | `misdirected` | the `Host` header does not name the listener (above) |
| 423 | `locked` | the squad's file lock was held by another writer for too long; nothing was written, retry |
| 500 | `internal` | an unexpected failure; the message says the traceback is in the daemon's log |

One answer has another shape: `503` with `{"not_executed": "retiring"}`. The daemon's configuration
changed since it started, so it declined the request without running any of it and is exiting.
The request can be sent again to the next daemon, which the next `sq` command in remote mode
starts (the CLI itself runs the declined call in local mode). It is the only answer after which a
request may be sent again: after any other failure, or a connection lost after sending, the
operation may have run.

## How a result carries the squad's vocabulary

The schemas in the OpenAPI document name no type, status, badge field or sub-entity kind, so one
document serves every squad. A result carries the squad's vocabulary in maps and in plain keys:

- An item or sub-entity row holds its core keys, then each attribute its file stores, flat beside
  them (`"severity": "high"`). An attribute appears only when it is stored.
- `badges` maps each declared badge field that holds a value to its badge code, on every row.
  Read badge values from `badges`, never from a key named after a field.
- A sub-entity carries `maps_to` (the local id of the parent's sub-entity it maps to) and
  `deferred_to` (the item that carries a deferred sub-entity's work), each `null` when unset.
- `display` holds what the CLI shows: labels, rendered badges, display names. On a sub-entity it
  carries `maps_to` and `maps_to_kind` (`{name, label, plural, heading}` of the kind it maps to).

Take codes from the plain keys and `badges`, labels from `display` and from the workflow catalogs
(`GET /v1/workflow/types`, `…/collections`, `…/subentity-kinds`, …), as given. Which keys are
frozen and which are provisional, and what each value class promises, is in
[stability.md](stability.md#tier-3---json-output-shapes-stable-additive-changes-only).

## Item versions

Each answer that addresses one item carries an `ETag` header: the version of that item's file as
the operation left it. That is every read of one item (the item, its sub-entities, comments, refs,
and a role's, skill's or operator's show), every write on one, and every create. A sub-entity's
state lives in its item, so it shares the item's `ETag`. An answer that leaves the item's file gone
(a removal) carries none, and a retype carries the tag of the moved file. The show result also
carries it, as its last key `etag`, which `sq show <id> --json` prints too.

```
$ curl -s -I --unix-socket /run/user/1000/squads/aebdaea5929e.sock http://localhost/v1/items/TASK-<n>
HTTP/1.1 200 OK
server-timing: handler;dur=6.6
etag: "aa484060887441ea2f1fe3779e34363639004e6b995e6ef3d0ae882ca9c0548d"
content-type: application/json
```

Send the tag back as `If-Match` on a write to have it refused if the item changed since you read
it. A write whose `If-Match` no longer matches answers `409 changed_since_read`, with the message
`<id> changed since it was read; nothing was written. Read it again and re-run.`, and writes
nothing; the check and the write cannot be separated by another writer. `If-Match` is checked on
the writes to an existing item: update, status, body, retype, remove, refs and views, and the
sub-entity add, update, body and remove. A create and the operations on the whole squad address no
existing item and check none. Without `If-Match`, a write is applied to the item as it is when the
write runs.

Compare an `ETag` for equality only. It names the file's state, not the answer's: an answer also
holds derived data, such as backrefs and display names, that can change while the file does not. So
the daemon ignores `If-None-Match` and never answers `304`.

**Comments are addressed by their hash.** A comment's hash is derived from its content, so a comment
edited since you read it has a new hash, and its old one no longer resolves: an edit or removal
sent with the old hash answers `404 not_found` and changes nothing. To remove after a
confirmation, as `sq … comment <hash> remove` does without `--yes`, read
`GET …/comments/{hash}/removal` (the comments the removal would take), then send
`DELETE …/comments/{full hash}` with the full hash it returned.

## Compatibility

`/v1` versions the route grammar, the envelope, the error body and the headers. The result and
request schemas are tied to the squad's **schema version** instead: an incompatible change to one
of them ships as a schema change, so a client and a daemon at different schema versions never parse
each other's shapes.

- **`Squads-Schema`.** Send the schema version your client was built for, the OpenAPI document's
  `info.version`. The daemon compares it before anything else and answers any difference with
  `409 schema_mismatch`, `details` holding both versions:

  ```json
  {"error": {"type": "schema_mismatch", "message": "the client speaks schema v0.17 and this squad is served at schema v0.19", "warnings": [], "details": {"client": "0.17", "daemon": "0.19"}}}
  ```

  A request without the header is answered. Rebuild the client against the daemon's document, or
  bring the squad to the client's schema with `sq migrate up` and a matching squads release.
- **`Squads-Vocabulary`.** A client that parses commands with the squad's vocabulary, as the CLI
  does, sends the hash of the vocabulary it used. On a difference the daemon answers
  `409 vocabulary_mismatch` with one digest per document in `details` (`workflow.toml` and
  `.overrides/workflow.toml`), so the client can name the document that differs. `GET /v1/daemon`
  reports the same hash and digests. The remedy is a checkout carrying the squad's configuration,
  or the squads version the daemon runs.

The CLI's messages for both refusals are in
[daemon.md](daemon.md#client-and-daemon-versions). Which shapes may change at all, and when, is
[stability.md](stability.md#the-http-api)'s.

## The daemon's own routes

- `GET /v1/daemon` returns the daemon's identity: `pid`, `version`, `schema_version`, `squad_dir`,
  `started_at`, `idle_deadline` (`null` when it never idles out), `listeners` (one
  `{transport, address, kind}` each) and `vocabulary` (`{hash, documents}`). `sq daemon status
  --json` prints it as its `daemon` key.
- `POST /v1/daemon/stop` answers `{"stopping": true}` and asks the daemon to exit once the request
  in progress has finished.
- `GET /v1/openapi.json` returns the OpenAPI document.

These three are answered without waiting behind a running operation.
