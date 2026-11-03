---
id: ADR-1274
sequence_id: 1274
type: decision
title: 'External sources: source record, stored views, sourced comments'
status: Accepted
author: architect
refs:
- EPIC-1268:addresses
- FEAT-1270:addresses
- FEAT-1271:addresses
- FEAT-1272:addresses
- FEAT-1273:addresses
- ADR-880
- ADR-776
- ADR-1007
- ADR-979
- ADR-1261
- ADR-622
- ADR-1013
- ADR-1109
description: Source record and derived lookup, nested records, stored view bodies,
  comment attributes, namespaced authors, server-side credentials, sources.toml, pull
  as import events, schema 0.20
created_at: '2026-11-03T22:41:36Z'
updated_at: '2026-11-03T23:51:29Z'
---
<!-- sq:body -->
## Context

EPIC-1268 lets agents work on issues humans file on GitLab, GitHub and Jira. An issue opted in on its tracker becomes a squad item; the tracker owns its title, description, mapped fields and comments, and the squad owns everything else. Nothing is written back. The scope and the operator's rulings (op-pierre, 2026-11-03) are on EPIC-1268 and FEAT-1270 to FEAT-1273; this record turns them into rules and settles the design they leave to the architect. The operator ruled the remaining choices on this record (op-pierre, 2026-11-03, comment a7b791e, cited below as "ruling a7b791e"). Rulings are cited as such; everything else here is this record's own decision.

The epic collides with six accepted decisions, each amended below at the clause named:

- ADR-880 §4: the view tag is unpaired, and a paired form "is the proposal to rebuild the stored region".
- ADR-776 §1: no file squads stores holds derived content the CLI can compute.
- ADR-1007 §1: no nested container on any wire surface.
- ADR-979 §2: a comment header carries a roster slug.
- ADR-1261 §1, §5: a served command sees a fixed list of client variables, and a prompt answer is one echoed line.
- ADR-622: one actor per event, a registered slug; no op for a source record, a stored view body or a comment edit.

Board notice 22 applies throughout: a hosted squad (FEAT-33) has no local squad and no local fallback, so nothing below reads a client-side resource in the serving process or runs only on the client.

## Decision

### 1. The `source` record and its lookup

**A core key.** `source` joins the core keys of ADR-1007 §1. It is absent on an item no tracker feeds. On a sourced item it is a nested record with exactly these keys, all strings (ruling 7238207, extended by 2980084):

| key | meaning |
|---|---|
| `name` | the source's name in `sources.toml` |
| `id` | the tracker's immutable issue ID (GitLab global ID, GitHub node ID, Jira issue ID) |
| `key` | the full readable key: `owner/repo#12`, `group/project#12`, `PROJ-45`; never a bare `#12` |
| `state` | `open`, `closed`, `out-of-filter` or `gone` |
| `updated_at` | the issue's last update on the tracker, ISO UTC |
| `author_id` | the issue author's immutable user ID |
| `author_handle` | the issue author's handle |

```yaml
source:
  name: gitlab-prod
  id: gid://gitlab/Issue/48211
  key: platform/api#12
  state: open
  updated_at: '2026-11-03T20:41:07Z'
  author_id: '4567'
  author_handle: pchat
```

- Nothing else is stored. The issue URL is derived by the connector from the source's base URL and `key`; labels, assignees, milestone and fetch time are not kept (ruling 7238207).
- Being core, its shape is checked at the load boundary like every core key (ADR-1007 §5): a record with a missing or extra key, or a non-string value, refuses the item and names the file.
- The item's core `author` is `source:<name>` (§6). Its `labels` and `assignee` stay squad-owned; the pull never writes them.

**The lookup is derived, never persisted.** `SquadsDB` builds, on load, two in-memory maps from the items it holds: `(name, id) → sequence ids` for matching an issue to its item, and `(name, key) → sequence ids` for translating tracker references (§9). They are inversions like `backrefs`, so `.squads.json` gains no structure and `sq repair` rebuilds them by rebuilding the items. Two items under one `(name, id)` are both kept, both listed and both refreshed by the pull; `sq check` reports them (§12, §14).

**The cursor is derived.** A source's incremental cursor is the newest `source.updated_at` among its items (ruling on US4). The connector's query is inclusive at the cursor, so an update in the same second is fetched again and the pull's idempotence (§10) absorbs it.

### 2. Nested records in frontmatter (amends ADR-1007 §1 and §4)

**§1 is narrowed** (ruling 2dc1246): a nested object is allowed on a wire surface when it is a **declared record with a known shape and one owner**; an open bag of undeclared keys is still refused. Three cases meet the rule: `subentities` (core, owned by the sub-entity verbs), `source` (core, owned by the pull and the `source` verbs) and an attribute of kind `map` (declared in the spec, owned by its option). The retired `extra` stays refused, and "keeping a nested container under another name" stays rejected, because a container whose keys nobody declares is what it names.

**§4 gains a fifth kind.** `kind = "map"` is a mapping of string keys to string values.

- Stored as a nested mapping under the attribute's name; `--json` item rows carry it as an object.
- Read through one typed accessor, `map_attribute(item, key)`, which treats a stored value of another shape as unset; `sq check`'s `attribute_valid` reports it, as for every kind.
- Set through a derived, repeatable option on the type's update verb: `--<name> key=value` sets one key, `--<name> key=` removes it. The option is derived from the spec when parameters resolve (`_field_options.py`), and `_workflow/_derived_names.py` refuses one that collides. `--set` refuses a map attribute and names the option.
- `sq import`'s `update` op sets and removes keys the same way: `"attributes": {"<name>": {"<key>": "<value>", "<key>": null}}`.
- ADR-1007 §7 holds per key: a write removes only the keys its option names.

### 3. Identities and handle resolution

- The bundled workflow spec declares `identities = { kind = "map" }` on `operator`, and the loader **pins** it beside the other roster minimum semantics (ADR-1007 §3), because attribution reads it. Keys are source names; values are the tracker's immutable user ID (rulings 782f6e7, 2980084).
- **A value starting with `@` is a handle; any other value is an ID** (ruling a7b791e, point 6). `sq operator <slug> update --identities gitlab-prod=@pchat` resolves the handle to the immutable ID through the source's connector and stores the ID. `--identities gitlab-prod=4567` stores `4567` as given. Resolution is part of the update operation, so it runs where the squad is served, with that side's credential (§7); a handle that does not resolve refuses the write and stores nothing.
- Attribution is computed at read time: an `author_id` held in an operator's `identities` under the same source shows as that operator. Nothing is rewritten when an identity is added later.
- `sq check` reports an identity key naming no declared source, and two operators holding one ID on one source. `sq source check` reports an identity whose ID no longer resolves (FEAT-1272).

### 4. Stored view bodies (amends ADR-880 §4 and ADR-776 §1)

**ADR-776 §1 is narrowed, not reversed.** The rule becomes: **no file squads stores holds derived content the CLI can compute from the squad alone.** Text whose only source is outside the squad (an issue description) cannot be recomputed on read, so storing it is not duplication. Everything ADR-776 retired stays retired.

**The declaration.** `[views.<name>]` takes `stored = true` (default `false`). Only a stored view has a stored body. Declaring it is the claim that the view's content cannot be derived locally; the bundled `source_description` view is the one bundled stored view, declared in §14.

**ADR-880 §4 is narrowed.** The tag of a non-stored view stays unpaired, byte for byte as today. The tag of a stored view is **paired**: an opening tag and an end tag, each on its own line in the usual HTML-comment wrapper (shown here without it), with the escaped body between them:

```
sq:view:source_description
…escaped stored body…
sq:view:source_description:end
```

- The end tag names the view, never its state: disabling a stored view rewrites the opening tag to `sq:view:<name>:disabled` and leaves the end tag and the body in place. A disabled stored view keeps its body.
- `_models/_markers.py` gains a close counterpart for view tags, used only for stored views. ADR-880 §4's closing sentence stands for every view whose content is derivable locally: giving such a view a body is still the proposal to rebuild the stored region.
- The pair lives inside `sq:body`, like every view tag. An empty pair is a stored view with no body yet.

**The escape grammar.** A stored body is opaque text that may hold anything, including a forged `sq:body` end tag in its HTML-comment wrapper. On write, every run of one or more `!` that follows `<` and precedes `--` gains one `!` (`<!--` becomes `<!!--`, `<!!--` becomes `<!!!--`); on read, every such run of two or more loses one. The escaped text contains no `<!--` at all, so no marker of any spelling (`MARKER_RE`, whitespace and case variants, the comment-attribute form of §5) can open, close or be forged inside it, and the round trip is exact for every input. Only HTML-comment openers change on disk; all other bytes are stored as given.

**One operation writes a stored body.** `set_view_body(item, view, text)` is a service operation, not a CLI verb and not a `sq import` op a file can name (§10). It runs inside an index transaction, refuses a view that is not declared stored, escapes the text, and writes the pair through `_sections.py`, placing it through the ADR-880 §6 routine when absent. Its callers are the pull, `show --refresh`, `source relink` and `source unlink` (§11).

**Body writes keep stored bodies intact.** The ADR-880 §6 routine treats a pair, opening tag to end tag, as one tag:

- stripping removes the whole pair, and re-insertion puts it back with its bytes unchanged;
- a new body that omits a pair gets it re-placed at its view's position with its stored body;
- a new body that carries a pair identical to the stored one is accepted, so a `show --json` body round-trips; one that carries a pair with any other content is refused, naming the view and `sq <type> <n> show --refresh`;
- `reject_body_overwrite` strips pairs from both sides before comparing prose.

**Reads never write.** Expansion at `read_body` hands the view's transform (ADR-1109) and its template the unescaped body as `body`, and an empty string for an empty pair or a non-stored view. No read path writes a stored body: not `show`, the TUI, `--raw`, nor the daemon's GET routes. `show --json` returns `body` as stored (pairs with their escaped text) and the unescaped stored body inside that view's entry under `views`, in the shape §14 gives. The bundled non-stored views render exactly as before.

**Check and repair learn the pair.** The marker-balance check accepts a balanced pair, and reports an opening tag of a stored view with no end tag, an end tag with no opening tag, a pair outside `sq:body`, and a pair for a view not declared stored. The ADR-776 §8 repair sweep still distinguishes by marker shape: no `sq:view:` tag, paired or not, is ever on its list. The index and `sq repair` never read a stored body.

### 5. Comment attributes

Any comment can carry a flat mapping of string keys to string values (rulings 260abbe, 2980084). The pull is the first writer; the capability is generic, and no CLI verb sets attributes.

**Storage.** One line directly after the comment's header, indented like its bullets: an HTML comment holding `sq:attrs`, one space and a JSON payload (shown here without the wrapper):

```
- [2026-11-02T09:14:00Z] `source:gitlab-prod` gitlab-prod:
  sq:attrs {"author_handle":"pchat","author_id":"4567","author_name":"Pierre Chat","source_id":"gid://gitlab/Note/9912","source_updated_at":"2026-11-02T09:20:31Z"}
  - The endpoint returns 500 when the body is empty.
```

- The payload is one JSON object, keys sorted, values strings, written on one line, with `<` and `>` written as `\u003c` and `\u003e`. JSON's own escaping carries every other character, so the payload never holds `-->` or `<!--`, and `json.loads` restores it exactly.
- `MARKER_RE` does not match the form (it carries a payload), so `find_markers` and the region machinery never see it. `reject_markers` widens to refuse any `<!--` followed by optional whitespace and `sq:` and a word character, so no prose can forge an attribute line; the documented `<!-- sq:* -->` spelling stays accepted.
- The line is recognised only in that position. A malformed one is reported by `sq check` and read as comment text.

**Not a hash input** (ruling 2980084). The canonical text of ADR-1013 §1 excludes the attribute line, so changing only attributes keeps the hash. The line is also excluded from the comment's rendered `body`, from the inbox's mention scan and from search. Edit and removal (ADR-1013 §4, §5) carry it with the comment's span.

**A sourced comment** stores `source_id`, `author_id`, `author_handle`, `author_name` and `source_updated_at`. `source` is derived from the header's `source:<name>` and the author URL from the base URL and the handle; neither is stored (ruling 2980084).

**Display** is composed at read time: the local slug and name when an identity matches, then `via <source> @<handle>`: `op-pierre Pierre Chat via gitlab-prod @pchat`, or `Pierre Chat via gitlab-prod @pchat` with no match. `--json` discussion entries gain `attributes` (the stored mapping) and the derived `source`, `author_url`, `identity` (the matched slug or `null`) and `trusted`.

**The untrusted notice** is derived from the `source:<name>` author and that source's `trusted` flag, never stored; it shows on the comment and on its inbox line. Mentions in sourced comments reach the inbox as written (ruling 8577dca).

**Imported comment text is escaped** with §4's grammar on write and restored on read, keyed on the `source:` author, so tracker text holding a marker cannot fail the pull or forge a region. Comments by any other author are unchanged.

### 6. Sourced authors (amends ADR-979 §2 and §2b)

- **The header grammar** accepts a namespaced author: ``author = slug | word ":" slug``, inside the same backticks. The first word is `source`; the header's name is the source name. The display name of ADR-979 §3 is the source name for the same reason a role's is its title: it is what the author is.
- **The `<word>:` author namespace belongs to squads** (ruling d4943bc). A colon cannot occur in a slug, so a namespaced author never collides with a role or operator, and the earlier load-time rule that a source name differ from every slug is withdrawn.
- **Each word is a reserved slug.** The mention pattern stops at the colon, so `@source:x` reads as `@source`; `source` therefore joins `operator` and `squads` as a reserved participant slug no role can take. `roster_slug_valid` reports a role that holds it. The adopter documentation states that squads may reserve more words, and that each one is refused as a role slug from the release that reserves it.
- **Only the pull writes as a source.** `--as source:<name>` is refused on every command, `sq import`'s `as` included. ADR-1013 §9 holds as written: no `--as` can match a `source:` header, so a sourced comment is edited or removed only by the pull.
- `sq check` validates `<name>` against the declared sources (§12). Item frontmatter `author` takes the same grammar.

### 7. Where source commands run, and the credential store (amends ADR-1261)

**Every source command runs where the squad is served** (ruling e7b6635): `sq source pull`, `sq source check`, `sq source list`, `show --refresh`, `source relink`, the identity resolution of §3 and the credential verbs below run in the local daemon, in process when there is none, and on the server for a hosted squad. None is in the shim's local-only table. `pull` and `check` are classed `long`. ADR-1261 §1 is unchanged in substance: no credential is in `SENT_ENVIRONMENT`, and none is read from the daemon's process environment, which was captured when it was spawned.

**The store.** One TOML file per user of the serving process, outside every repository:

| platform | path |
|---|---|
| Linux and other POSIX | `$XDG_CONFIG_HOME/squads/credentials.toml`, else `~/.config/squads/credentials.toml` |
| macOS | `~/Library/Application Support/squads/credentials.toml` |
| Windows | `%APPDATA%\squads\credentials.toml` |

```toml
["https://gitlab.example.com"]
token = "…"

["https://acme.atlassian.net"]
user = "svc-squads@acme.example"
token = "…"
```

- An entry is keyed by the source's normalised base URL (scheme, host, port and path, no trailing slash; ruling a7b791e, point 1), so every clone and worktree of a squad, and every squad pulling from that tracker, finds it. It holds the fields its connector names (`token`; `user` and `token` for `jira@cloud-v3`). One credential per source, typically a service account; attribution never depends on whose it is (ruling e7b6635).
- It is read at the moment a source command needs it, every time; nothing caches it across requests, and editing it needs no daemon restart.
- On POSIX the file is created with mode `0600` in a `0700` directory, and a file readable by group or others is refused with a message naming `chmod`. On Windows it inherits the user profile's ACL.
- The runtime directory is not used: it is volatile, and a credential must survive a reboot.

**Filling it.** `sq source credential set <source>` asks for each field the connector names with a hidden prompt (or reads it from a non-terminal stdin), and writes the entry; `sq source credential remove <source>` deletes it. Neither prints a value, and no value reaches `--json`, the reflog, a log line or the squad. `sq source list` shows only whether an entry exists.

**ADR-1261 §5 gains a hidden prompt.** A `prompt` answer carries `hidden: true` for a prompt Click would read with `hide_input`; the shim then reads the line without echo. The answer travels once, in that request's `answers`, over the CLI listener, and is never written into `output` or the prompt digest. This is the one path by which a secret crosses the command endpoint, and it only fills the store; no source command takes a credential from its caller.

**The fit with MILE-868.** The store holds outbound credentials to trackers; MILE-868 decides inbound authentication for the browser port, and FEAT-33 applies that mode to every listener reaching beyond the machine. The two never share a file. The credential verbs are operations of the private command endpoint only: no resource route under `/v1` reads or writes the store, and the OpenAPI document does not name it, so the unauthenticated browser port cannot reach it. **They are admitted only on the owner-only local CLI listener and in process** (ruling a7b791e, point 5): on a hosted squad an operator runs them on the server's own host. A listener that reaches beyond the machine refuses them until MILE-868's authentication can tell callers apart.

### 8. `sources.toml`, the fourth spec document

- A `SpecDocument` beside the workflow, roles and playbook documents: bundled `_specs/sources.toml`, project override `squads/.overrides/sources.toml`, read and merged once per invocation through `_specload.py` and `_specmerge.py`, scaffolded and diffed by `sq override`. `.squads.toml` is unchanged (ruling cd28e40).
- `resolve_documents` resolves it lazily and memoised, like the role catalog (ruling a7b791e, point 7): a broken `sources.toml` fails every command that reads a source, and `sq check` reports it, while the rest of the squad keeps working.
- **Top-level keys:** `connectors`, `sources`, `selected`.
- **`[connectors."<name>@<version>"]`** (bundled): per connector version, its default `converter` and default `maps`. A default map may name bundled vocabulary; it is validated only through a source that inherits it.
- **`[sources.<name>]`** (override only; the bundled file declares none): `connector` (`gitlab`, `jira`, …), `version` (optional only when the connector has one registered version, §14), `base_url`, `filter` (a label, or JQL for Jira), `trusted` (default `false`), `enabled` (default `true`), optional `converter`, and `maps`. Declaring a source activates it; `enabled = false` pauses it.
- **Maps.** `maps.types` (tracker type or label to item type), `maps.fields.<badge field>` (tracker value to badge value), `maps.links` (tracker link type to ref kind). A source's map overlays its connector default key by key; an entry set to `""` unmaps the tracker value.
- **Load-time validation**, collect-all, against the resolved workflow spec: every map target is a declared type, badge field and value, or ref kind; a source name follows the slug grammar; `connector`, `version` and `converter` exist in their registries. A failure names the source, the map and the value.
- An edit to the override retires the daemon like any `.overrides/` edit (ADR-1052, point 13).

### 9. Connectors and converters

- **Connector registry:** a literal `(name, version) → class` table with no registration side effect (ruling 4f4a607). The interface: issues changed since a cursor; the IDs matching the filter, closed included; one issue by ID; its comments and links; the URL of an issue from base URL and key, and of a user from a handle; handle to immutable user ID; the tracker references in a text, each qualified to a full key against the host issue's key (§14); its probes for `sq source check`; its default converter.
- **Converter registry:** a literal name → function table (`adf`, `jira-wiki`, `gitlab-md`, `github-md`), pure functions of text and base URL, with no network access.
- **Vocabulary stays out of code.** A `tests/meta` guard keeps squad vocabulary literals (item types, badge fields and values, ref kinds, statuses) out of connector modules; tracker API names are allowed.
- **Reference translation is read-time.** The `source_description` projection and the comment render translate a tracker reference to an item ID when the `(name, key)` lookup of §1 finds exactly one item (§14); the stored text keeps the raw reference.
- Connectors are reached only from `_services`; the shim imports none of them, and HTTP uses the standard library client.

### 10. The pull compiles to `sq import` events (amends ADR-622)

**One write path.** `sq source pull [<name>]` has three phases:

1. **Fetch**, outside the index lock: the access probes, then for each source the incremental query since the cursor, the listing of IDs in the filter, a fetch of each linked item missing from it, and the comments and links of what changed (rulings 8c0a817, 2980084). It paginates and backs off on rate limits.
2. **Compile**, inside one `IndexStore.transaction()`: diff the fetched data against the items as they stand under the lock and emit only the events that change something.
3. **Apply** through the importer's validate-first pre-pass and apply pass, in the same transaction, as one import.

A second pull with nothing new compiles to no events and writes nothing. `--dry-run` stops after the pre-pass; `--json` reports per-source counts, the created IDs and every report line.

**Timestamps** (ruling a7b791e, point 2). A sourced comment's header carries the tracker comment's creation time, so the discussion shows when it was written. Every other event carries the pull's time, so an item's `created_at` is when it entered the squad; the issue's age is shown from `source.updated_at`. An edit mark written by `comment-edit` carries the pull's time.

**Events per issue.** A new in-filter issue: `create` with `type` from the map (applied at creation only, ruling fa6c47d), `title`, mapped `fields`, the `source` record, then `view-body` seeding `source_description`. A linked issue: `update` for the title and mapped fields that changed, `source` for the record (key, state, `updated_at`), `view-body` when the description changed, a `comment` per new tracker comment with its attributes, a `comment-edit` per edited one, a `ref` per new link whose both ends are linked.

**ADR-622 gains:**

- **internal ops**, which the compiler emits and the JSONL reader refuses: `source` (set, replace or remove an item's source record), `view-body` (§4's operation) and `comment-edit` (replace a comment's text and attributes, addressed by an attribute value, `{"key": "source_id", "value": "…"}`);
- `attributes` on `comment` and `comment-edit`;
- an internal actor: events compiled by the pull carry `as = source:<name>`, which only the pull's compiler can produce (§6).

**Per-issue failures never block a source.** An issue whose events would fail the pre-pass (a title holding a marker, a mapped badge field the item's type no longer has, a tracker type that no longer matches the map on a retyped item) has its offending events dropped and is reported; the rest of the pull applies. The type is never changed by a pull (ruling fa6c47d).

**Identical tracker comments.** Attributes are not a hash input, and every sourced comment of one source has the same author, so two tracker comments with the same text in the same second share a hash and ADR-1013 §6 would refuse the second. The compiler skips the second and reports it, naming both tracker comment IDs (ruling a7b791e, point 3).

**Reporting.** Closed issues become `closed`; a linked issue outside the filter becomes `out-of-filter`; one not found becomes `gone`, reported as "deleted or no longer readable" (ruling 8c0a817). A comment deleted on the tracker is reported, not removed. The item always stays.

**Credentials.** With no name, a source with no stored credential is skipped with a warning; a named one is an error naming `sq source credential set <name>`.

### 11. Ownership and refusals

- While an item carries a `source` record, the squad cannot write what the tracker owns (FEAT-1271 US6): its `title`, a badge field its source maps, the stored body of `source_description`, and a comment authored by `source:<name>`. Each refusal names the source, the issue key and `source unlink`.
- **Retype** works on a sourced item and keeps its record (ruling fa6c47d); a mapped field the new type lacks is skipped by later pulls and reported.
- **`source unlink`** removes the record and turns the stored description into plain body prose at the pair's position, with any escaped HTML-comment opener left escaped, so no marker enters the prose. The imported comments stay, authored by `source:<name>`.
- **`source relink <source> <issue>`** reattaches an item that `source:<source>` created to an issue of that source, resolving a key to its immutable ID through the connector, and refreshes the item at once, leaving the squad's own body text (§14).
- **`show --refresh`** pulls that one item's issue through the same three phases, then shows it; on an item with no record it is refused (§14).

### 12. What `sq check` reports

`sq check` never calls the network. It reports: two items sharing one `(source, id)`; a `source:<name>` author, on an item or a comment, naming no declared source; an item whose source is undeclared or disabled; an item whose `source.state` is `out-of-filter` or `gone`; an identity key naming no declared source; two operators holding one ID on one source; a malformed comment-attribute line; the paired-tag findings of §4; and a `sources.toml` that does not load.

### 13. Schema 0.20 and its migration

The schema moves from `0.19` to `0.20`. The bump is owed even though a squad with no source changes no byte: a 0.19 build would read `source` as an unknown attribute, an attribute line as comment text (changing hashes), and a pair as an unbalanced tag, and the gate keeps it off a squad that holds them.

The `0.19 → 0.20` runner writes nothing to item files. Its pre-flight, run over the whole corpus before the stamp, refuses and lists every case:

- an item frontmatter carrying a top-level `source` key, which is now core;
- a role whose slug is `source`, now reserved;
- a discussion line, directly after a header, that matches the comment-attribute grammar.

Remedies go in the migration's `manual` text. A squad clear of all three is stamped and carried unchanged.

### 14. Implementation details (amendment, 2026-11-04)

Settled when the epic's tasks were planned, within the rulings above. Each point binds the implementation; where it changes an earlier section, that section points here.

**Stored views in `show --json` and the transform's `body` keyword** (amendment, 2026-11-04; completes §4, narrows ADR-1109's Call and `show --json`).

- Under `views`, a **stored** view's entry is always an object with two keys: `{"body": <unescaped stored body>, "data": <transform output, or null>}`. The `body` is `""` for an empty pair or an unpaired tag.
- A stored view gets an entry whether or not it declares a transform, so `source_description`, which has none, carries its body. The other ADR-1109 gates hold: the tag must be placed, enabled and pass `resolve_view_target`, so a disabled stored view has no entry.
- A **non-stored** view's entry is unchanged: the transform's output itself, and no entry without a transform. Every bundled view other than `source_description` therefore prints byte for byte as before.
- The body sits under a fixed key beside `data`, never merged into the transform's output, so no output a transform returns can collide with it.
- A transform may declare a `body` parameter. Like `item` and `spec` it is passed only when declared, or when the function takes `**kwargs`. It receives the unescaped stored body, or `""` for a non-stored view. An existing transform's signature is unaffected (ADR-1109: a keyword sq adds later is never a breaking change).
- `docs/stability.md` and `docs/workflow.md`, which state that each `views` value is the transform's output, need the stored-view shape and the `body` keyword.

**A stored body's line endings** (amendment, 2026-11-04; completes §4's escape grammar).

- On write, `set_view_body` normalises line endings to LF: every `\r\n` and every lone `\r` becomes `\n`. Item files are LF, a Windows checkout with git `autocrlf` would rewrite a CR inside a body anyway, and tracker text is display text.
- Apart from that normalisation, the §4 escape is the only transformation, so the round trip is exact for LF text.
- On disk, the text between the opening tag and the end tag is the escaped body, framed by exactly one `\n` after the opening tag and one `\n` before the end tag. The two frame newlines are not part of the body: a read strips exactly those two, then unescapes.
- A write whose normalised, escaped body equals the stored one writes nothing, so refreshing an unchanged description leaves the file and the reflog untouched.

**Seams and the first connector.**

- The connector interface (§9, every method but the probes), the connector table and the converter table land with the pull, because the pull, handle resolution, reference translation and the `sources.toml` validation all call them. The probe method lands with the probe framework of `sq source check`.
- The GitLab connector lands with them, with the shared standard-library HTTP helper, the `gitlab-md` converter row and the §9 vocabulary guard, and the pull is tested against it. Its tests serve recorded API responses on a loopback port that the source's `base_url` names, so every case runs the real command, the real pull and the real HTTP path, and CI reaches no tracker.
- No test-only connector row exists, and no fixture patches either table: a fake connector would test the pull against behaviour its own author invented, and its reference grammar and probes would be fiction.
- A converter is a pure function of text (§9), so a converter's case pulls through the GitLab connector with the source's `converter` set; it needs no connector of its own format.

**The `source_description` view** (extends ADR-880 §2's source grammar with a seventh kind).

```toml
[views.source_description]
source = { kind = "source" }
position = "top"
stored = true
```

- `kind = "source"` takes no `name` and applies to every item type. It resolves to `null` when the host carries no `source` record, and otherwise to one record: the host's `source` keys, plus `url` (the connector's issue URL from the base URL and the key), `trusted` (the declared source's flag, `false` when the source is not declared) and `text` (the view's stored body, unescaped, with tracker references translated as below). The template also receives `body` as §4 says, untranslated.
- `self` cannot serve: its resolver hands back the host alone, and a transform (ADR-1109) sees only its source, the host and the workflow spec, while the URL, the trust flag and the translation need the sources document, the connector and the `(name, key)` lookup. A new resolver is the reason for a new kind.
- The record is computed in `_services` and reaches `_views` as a provider, like the roster, so connectors stay reachable from `_services` only (§9) and `_views` imports nothing from `_sources`.
- `position = "top"`: the issue's description leads the body and the squad's prose follows it. The view has no transform. No creation template seeds its tag; `set_view_body` places the pair when absent (§4).
- With a `null` source the bundled template renders the stored body alone, with no provenance and no notice.

**Reference translation is the connector's job** (replaces §9's "reference pattern").

- The interface method takes a text and the host issue's `key`, and returns each tracker reference in the text as its span and the full key it names, qualifying a short form (`#12`, `project#12`) against the host key. It is a pure function, with no network access.
- The `source_description` record and the comment render look up each full key in `(name, key)` and replace the span with the item ID when exactly one item holds that key. Otherwise the reference stays as written.
- A sourced comment on an item that carries no `source` record has no host key, and renders untranslated.

**Two items under one `(name, id)`** (completes §1).

- Both lookups map to lists of sequence ids.
- The pull refreshes every item linked to a fetched issue, each through its own events, and reports the duplicate on every run.
- An issue is new only when no item holds its `(name, id)`, so a pull never creates a third.

**Unlink and relink** (replaces §11's relink bullet).

- `source unlink` removes the record and nothing else of the authorship: the item's `author` stays `source:<name>`, and its imported comments stay authored by `source:<name>`. They are the item's history. No `--as` matches them (§6), so they can no longer be edited or removed. Unlink on an item with no record is refused.
- `source relink <source> <issue>` is accepted only on an item that carries no `source` record and whose `author` is `source:<source>`: that author is what "the same source" is checked against. It is refused, each time naming why, on an item that still holds a record (naming `source unlink`), on an item no source created, on an item another source created (naming it), and for an issue whose `(name, id)` another item already holds (naming that item).
- Relink resolves `<issue>`, a key or an immutable ID, through the connector, then runs the three phases of §10 for that one issue, with the record as one more event: the record, the title, the mapped fields, the description view and the comments, matched by `source_id`, land in one transaction. The prose unlink left in the body stays the squad's. The type is not changed.
- Relink does not leave the description to the next pull: the incremental query returns only issues updated since the cursor, and an issue unchanged since the relink is not one, so a pull would never restore the view.

**Connector versions** (amendment, 2026-11-04; replaces §8's "default the newest registered").

- Versions of one connector are not ordered. A version names an API or a deployment (`jira@cloud-v3`, `jira@dc-v2`), and no rule could say which of two deployments is newer, so squads defines no ordering and never picks one.
- `version` may be omitted only when its connector has exactly one registered version, which the source then uses. When the connector has several, a source without `version` fails at load, naming the source and listing the known versions. An unknown version fails the same way.
- A release that registers a second version of a connector makes every source of that connector without a `version` fail at load. The failure is loud and names the remedy, and the release notes say so. A source is never moved silently to a different API.

**Access probes before every fetch** (completes §10, phase 1).

- Every command that fetches from a tracker runs that source's access probes first: a pull, `show --refresh`, `relink` and handle resolution. A blocking failure stops the command before anything is fetched or written, and prints the same line as `sq source check`.
- They share one fetch phase, so the probes run in one place.

**Smaller rules.**

- `show --refresh` on an item with no `source` record is refused, naming the item and that it has no source; nothing is fetched, written or shown.
- A disabled source fetches nothing into the squad: a named pull, `show --refresh`, `relink` and handle resolution refuse it, naming `enabled = false`, and a pull with no name skips it. Every command that needs no tracker data works on it as on an enabled source: `source unlink`, `sq source credential set` and `remove`, `sq source list` and `sq check`. `sq source check` still probes it, so a source can be checked before it is enabled.
- A handle (`@…`, §3) on a source with no stored credential is refused, naming `sq source credential set <source>`, and nothing is stored. A handle for an undeclared source is refused, naming the declared ones. A value without `@` needs no credential and no network, and is stored as given.
- `trusted` in a `--json` discussion entry is a boolean, `false` exactly when the untrusted notice shows: `true` for a comment no source authored, the source's flag for a sourced comment, and `false` when that source is not declared. On a comment no source authored, `source`, `author_url` and `identity` are `null`.

## Rejected

- **A locked item body for the description.** Ruled out (ruling ec05545): the description is a view's stored body, refreshed by an operation.
- **Paired tags for every view.** It would let a locally derivable view cache its rendering, which ADR-776 forbids. The pair is declared per view.
- **Escaping only well-formed `sq:` markers in a stored body.** Whitespace and case variants, and the attribute form, would each need their own case; escaping every HTML-comment opener has one rule and an exact inverse.
- **Comment attributes in frontmatter.** A comment has no stable key a frontmatter record could use: its hash changes on every edit.
- **A persisted source index.** It would store what the items already hold.
- **A stored cursor.** It is the newest `updated_at` of the source's items.
- **Tokens from the client's environment, a client-sent token per pull, or `sq source` as a local-only command** (ruling e7b6635, board notice 22).
- **The OS keyring.** It is absent on a headless server and under WSL, and adds a dependency the store does not need.
- **A test-only connector row** (§14). The pull would be tested against a connector whose behaviour its test author invented.
- **The `self` view source for the description** (§14). Its resolver and a transform see neither the sources document nor the lookup.
- **A second write path for the pull.** The importer already has the transaction, the per-event clock and actor, the pre-pass and the reflog.

## Consequences

- `Item` gains `source: SourceRecord | None`; `CORE_KEYS` gains `source`; the comment model gains `attributes`; `SquadsDB` gains the two derived lookups, each to a list of sequence ids.
- The attribute kinds are `str`, `list`, `bool`, `date` and `map`; the operator type carries the pinned `identities`.
- `_models/_markers.py` gains the stored-view close tag and the attribute-line form; `reject_markers` widens as §5 says; `place_view_tags` handles pairs; `ViewSource.kind` gains `source`, resolved through a provider the service layer hands to `_views`.
- A new `_sources` package holds the spec loader for `sources.toml`, both registries, the connectors and the pull's compiler; `tests/meta`'s import-edge table gains its rows.
- `docs/stability.md` needs the nested-record rule, the `map` kind, the `source` record, the namespaced author grammar and the reserved `source` slug, the paired view tag and its escape, the `source` view source kind, the attribute line, the `sources.toml` grammar and the credential store's location; the adopter docs say that more author words may be reserved, and keep a source connector apart from the MCP connector of FEAT-319.
- ADR-880 §2 and §4, ADR-776 §1, ADR-1007 §1 and §4, ADR-979 §2 and §2b, ADR-1261 §5 and ADR-622 are narrowed in place, each with a dated note pointing here.
- A pull holds the daemon's serial lock for its whole run, network fetch included (ADR-1261 §2), so other served commands wait for it. This holds while pulls are manual (ruling a7b791e, point 4); a timer or webhook pull reopens it.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-03T22:42:01Z] `architect` Robert Architect:
  - - Questions for the operator. Each is a real choice the rulings leave open; the body follows the recommendation where it needs one.
      1. Credential store key. Recommendation: one entry per tracker base URL, so every clone and worktree of a squad on that host, and every squad pulling from that tracker, finds it. Alternative: one entry per squad directory and source name, which lets two squads on one host use different service accounts, but every new clone or worktree needs `sq source credential set` again.
      2. Timestamps of pulled events. Recommendation: a sourced comment's header carries the tracker comment's creation time, so the discussion shows when it was written; the item's `created_at` and every other event carry the pull's time, so `created_at` means "entered the squad" (the issue's age is shown from `source.updated_at`). Alternative: tracker times everywhere, or the pull's time everywhere.
      3. Two identical tracker comments. Attributes are not a hash input, and every sourced comment has the author `source:<name>`, so two tracker comments with the same text in the same second (two "+1" from different users) share a hash, and ADR-1013 §6 refuses the second. Recommendation: the pull skips the second and reports it. Alternative: make `source_id` a hash input for sourced comments only, which keeps both but narrows the ruling that attributes are not a hash input.
      4. A long pull and the daemon's serial lock. A served command holds the daemon's one serial lock for its whole run (ADR-1261 §2), network fetch included, so a large pull blocks every other served command until it ends. Recommendation: accept it while pulls are manual, and document it. Alternative: run the fetch outside the serial lock, which is a concurrency change to the daemon.
      5. Who may set credentials on a hosted squad. Recommendation: the credential verbs run only on the owner-only local CLI listener and in process, so on a hosted squad they are run on the server's own host, until MILE-868's authentication can tell callers apart. Alternative: any caller FEAT-33 identifies may run them remotely.
      6. Where handles are resolved. Recommendation (as Nina proposed): `sq operator <slug> update --identities <source>=@<handle>` resolves the handle where the squad is served, and a value without `@` is stored as the ID. Alternative: a dedicated `sq source identify <source> <operator> <handle>`, which keeps the generic `map` option free of any network call.
      7. A broken `sources.toml`. Recommendation: it fails only the commands that read a source (resolved lazily, like the role catalog), and `sq check` reports it. Alternative: it fails every command, as a malformed workflow override does.
- [2026-11-03T22:42:02Z] `architect` Robert Architect:
  - @product-owner the ADR for EPIC-1268 is drafted: the four amendments of comment 3e699e5 (ADR-880 §4 with ADR-776 §1, ADR-1007 §1 and §4, ADR-979 §2 and §2b, ADR-1261 §5) and the new design (source record and derived lookup, map kind and identities, comment attributes, server-side credential store, sources.toml, the pull compiled to import events with internal ops, schema 0.20). Seven open choices are in the previous comment for @op-pierre. The amended ADRs get their dated in-place notes when this one is ruled.
- [2026-11-03T22:48:30Z] `op-pierre` Pierre Chat:
  - Rulings on the seven open questions (2026-11-03): the architect's recommendation stands on each.
    1. Credentials are keyed per tracker base URL.
    2. Comment headers carry the tracker's creation time; everything else carries the pull time.
    3. A second identical tracker comment in the same second is skipped and reported.
    4. The pull holds the daemon's serial lock while pulls are manual.
    5. On a hosted squad, credentials are set only on the owner-only local listener or in process, until MILE-868 can tell callers apart.
    6. Handles are resolved by `sq operator <slug> update --identities <source>=@<handle>`.
    7. A broken `sources.toml` fails only the commands that read a source.
- [2026-11-03T22:50:36Z] `architect` Robert Architect:
  - Folded the seven rulings of a7b791e (op-pierre) into the body as decisions: credential key per base URL (§7), timestamps (§10), identical comments skipped and reported (§10), serial lock while pulls are manual (Consequences), credential verbs owner-only local listener or in process (§7), handle resolution on operator update (§3), lazy sources.toml (§8). Dated notes pointing here are on ADR-880 §4, ADR-776 §1, ADR-1007 §1 and §4, ADR-979 §2 and §2b, ADR-1261 §5 and ADR-622 (The op set).
- [2026-11-03T22:53:13Z] `op-pierre` Pierre Chat:
  - Accepted ADR-1274 after the briefing on its commitments (live amendment notes, on-disk escaping, pull under the serial lock, the reserved author namespace, server-side credential setup).
- [2026-11-03T23:11:05Z] `architect` Robert Architect:
  - - Amended in place (2026-11-04): new §14 settles the gaps the tech lead found while planning EPIC-1268; §1, §4, §9, §11, Rejected and Consequences point to it. Binding for TASK-1276 to TASK-1278.
      - Seams: the connector interface (all but the probes) and both literal tables land with the pull, and so do the GitLab connector, the HTTP helper, the `gitlab-md` row and the vocabulary guard. Tests use recorded responses on a loopback port. No test-only row.
      - `source_description`: a new view source kind, `source`, at `position = "top"`; `self` cannot reach the sources document, the connector or the lookup. ADR-880 §2 carries the dated note.
      - Relink: only on an item with no record whose `author` is `source:<source>`; that author survives unlink. It refreshes the item at once, because the next incremental pull would never return an unchanged issue.
      - Duplicates: the pull refreshes every item under one `(name, id)` and reports the duplicate on each run.
      - Reference qualification (`#12` to a full key against the host key) is a connector method.
      - `show --refresh` without a record is refused; a handle with no credential is refused, naming `sq source credential set`; `trusted` is `false` exactly when the notice shows.
    - @product-owner FEAT-1271 US7 still says "the next pull restores the description view"; per §14, relink restores it itself.
- [2026-11-03T23:11:06Z] `architect` Robert Architect:
  - - @op-pierre one adopter-facing addition for you to confirm. §14 adds a seventh `[views]` source kind, `source`, for `source_description`. The template needs the issue URL, the source's `trusted` flag and translated references, and neither `self` nor a transform can see the sources document, the connector or the lookup.
      - Recommendation: keep the new kind. It touches one resolver, and the stability doc gains one row.
      - Alternative: keep `self` and widen every view's template context with the host's source record, URL and trust flag. That changes every view instead of adding one.
      - It blocks no development: TASK-1276 builds it as §14 says. Only TASK-1279 (the stability doc and changelog) waits for your answer before it documents the kind.
- [2026-11-03T23:17:25Z] `architect` Robert Architect:
  - - Amended in place (2026-11-04), three more gaps from the task planning, in §14 (§8 points to it):
      - Connector versions are not ordered, and squads never picks one. `version` may be omitted only when the connector has one registered version; with several, a source without `version` fails at load, listing the known versions. No ruling sets a default; 4f4a607 only makes versions separate connectors.
      - A disabled source fetches nothing. `source unlink`, `sq source credential set` and `remove`, `sq source list` and `sq check` work on it, and `sq source check` still probes it.
      - Every fetching command (pull, `show --refresh`, `relink`, handle resolution) runs the source's access probes first, through one shared fetch phase.
    - @product-owner FEAT-1271 US1 and FEAT-1273 US1 still say "default: newest"; per §14, `version` is optional only for a connector with one version.
- [2026-11-03T23:48:46Z] `architect` Robert Architect:
  - Amended (2026-11-04): section 14 records the stored-body byte rule for REV-1280 F1, namely an exact round trip with line endings included, the escape as the only transformation, one frame newline on each side outside the body, and no write when the escaped body is unchanged.
- [2026-11-03T23:51:29Z] `architect` Robert Architect:
  - Corrected (2026-11-04): the section 14 stored-body rule now normalises line endings to LF on write instead of promising a byte-exact round trip (item files are LF, git autocrlf would break that promise, tracker text is display text); the escape stays the only other transformation, the round trip is exact for LF text, and a write whose normalised, escaped body is unchanged writes nothing.
<!-- sq:discussion:end -->
