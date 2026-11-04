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
updated_at: '2026-11-04T15:34:34Z'
---
<!-- sq:body -->
## Context

EPIC-1268 lets agents work on issues humans file on GitLab, GitHub and Jira. An issue in a source's scope on its tracker, accepted by the source's filter and typed by its map, becomes a squad item; the tracker owns its title, description, mapped fields and comments, and the squad owns everything else. Nothing is written back. The scope and the operator's rulings (op-pierre, 2026-11-03) are on EPIC-1268 and FEAT-1270 to FEAT-1273; this record turns them into rules and settles the design they leave to the architect. The operator ruled the remaining choices on this record (op-pierre, 2026-11-03, comment a7b791e, cited below as "ruling a7b791e"). Rulings are cited as such; everything else here is this record's own decision.

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
| `updated_at` | the issue's last update on the tracker, ISO UTC; empty on an item created by a pull that dropped one of its issue's events (§14) |
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

**The lookup is derived, never persisted.** `SquadsDB` builds, on load, two in-memory maps from the items it holds: `(name, id) → sequence ids` for matching an issue to its item, and `(name, key) → sequence ids` for translating tracker references (§9). They are inversions like `backrefs`, so `.squads.json` gains no structure and `sq repair` rebuilds them by rebuilding the items. Matching and translation consult them for every declared source on one tracker (§14, **Links across sources**). Two items holding one issue are both kept, both listed and both refreshed by the pull; `sq check` reports them (§12, §14).

**No cursor.** A pull keeps no cursor, stored or derived. It compares each issue the scope lists with the `source.updated_at` of the items that hold it, and fetches details only where they differ or no item holds the issue (§14). A cursor derived from the newest `updated_at` loses data: a refresh of one issue moves it past another's change, and an issue held back once is never asked for again.

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

**The declaration.** `[views.<name>]` takes `stored = true` (default `false`). Only a stored view has a stored body. Declaring it is the claim that the view's content cannot be derived locally; the bundled `source_description` view is the one bundled stored view, declared in §14. `stored = true` is accepted only on a view whose source kind has a writer, which today is `source` alone (§14).

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

**Display** is composed at read time, in one form for every sourced author (§14): the operator slug when an identity matches; then the name, the roster name unquoted when matched and the tracker's display name in double quotes when not; then `via <source>` and `@<handle>`. Matched: `op-pierre Pierre Chat via gitlab-prod @pchat`; unmatched: `"John Doe" via gitlab-prod @jdoe`. `--json` discussion entries gain `attributes` (the stored mapping) and the derived `source`, `author_url`, `identity` (the matched slug or `null`) and `trusted`; their `author` is the same form.

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
- **`[connectors.<name>.<version>]`** (bundled; the key form is in §14): per connector version, its default `converter` and default `maps`. A default map may name bundled vocabulary; it is validated only through a source that inherits it.
- **`[sources.<name>]`** (override only; the bundled file declares none): `connector` (`gitlab`, `jira`, …), `version` (optional only when the connector has one registered version, §14), `base_url`, exactly one scope key (`project` or `group` for GitLab, `repository` for GitHub, `jql` for Jira; required, §14), `filter` (optional, a table of one boolean expression per side, evaluated in squads, §14), `trusted` (default `false`), `enabled` (default `true`), optional `converter`, and `maps`. Declaring a source activates it; `enabled = false` pauses it.
- **Maps.** `maps.types.<side>` (tracker value to item type), `maps.fields.<badge field>.<side>` (tracker value to badge value), `maps.links` (tracker link type to ref kind). A side names where the value is read on the tracker (§14). A source's map overlays its connector default key by key; an entry set to `""` unmaps the tracker value.
- **Load-time validation**, collect-all, against the resolved workflow spec: every map target is a declared type, badge field and value, or ref kind; a source name follows the slug grammar; `connector`, `version` and `converter` exist in their registries. A failure names the source, the map and the value.
- An edit to the override retires the daemon like any `.overrides/` edit (ADR-1052, point 13).

### 9. Connectors and converters

- **Connector registry:** a literal `(name, version) → class` table with no registration side effect (ruling 4f4a607). The interface: the listing of every issue in the source's scope, closed included, paged, each with the fields the pull compiles and its `updated_at` (§14); one issue by its immutable ID and last known key (§14); its comments and links; the URL of an issue from base URL and key, and of a user from a handle; handle to immutable user ID; the tracker references in a text, each qualified to a full key against the host issue's key (§14); its probes for `sq source check`; its default converter.
- **Converter registry:** a literal name → function table (`adf`, `jira-wiki`, `gitlab-md`, `github-md`), pure functions of the text, the base URL and the host issue's web URL (§14), with no network access.
- **Vocabulary stays out of code.** A `tests/meta` guard keeps squad vocabulary literals (item types, badge fields and values, ref kinds, statuses) out of connector modules; tracker API names are allowed, and a fixed set of tracker API names that spells like squad vocabulary is exempted per constant (§14).
- **Reference translation is read-time.** The `source_description` projection and the comment render translate a tracker reference to an item ID when the `(name, key)` lookup of §1 finds exactly one item (§14); the stored text keeps the raw reference.
- Connectors are reached only from `_services`; the shim imports none of them, and HTTP uses the standard library client.

### 10. The pull compiles to `sq import` events (amends ADR-622)

**One write path.** `sq source pull [<name>]` has three phases:

1. **Fetch**, outside the index lock: the access probes, then for each source the full listing of its scope, a fetch of each linked item missing from it, and the comments and links of each listed issue that no item holds or whose listed `updated_at` differs from the stored one (rulings 8c0a817, 2980084; §14). It paginates and backs off on rate limits.
2. **Compile**, inside one `IndexStore.transaction()`: diff the fetched data against the items as they stand under the lock and emit only the events that change something.
3. **Apply** through the importer's validate-first pre-pass and apply pass, in the same transaction, as one import.

A second pull with nothing new compiles to no events and writes nothing. `--dry-run` stops after the pre-pass; `--json` reports per-source counts, the created IDs and every report line.

**Timestamps** (ruling a7b791e, point 2). A sourced comment's header carries the tracker comment's creation time, so the discussion shows when it was written. Every other event carries the pull's time, so an item's `created_at` is when it entered the squad; the issue's age is shown from `source.updated_at`. An edit mark written by `comment-edit` carries the pull's time.

**Events per issue.** A new selected issue (§14, **Source selection**): `create` with `type` from the map (applied at creation only, ruling fa6c47d), `title`, mapped `fields`, the `source` record, then `view-body` seeding `source_description`. A linked issue: `update` for the title and mapped fields that changed, `source` for the record (key, state, `updated_at`), `view-body` when the description changed, a `comment` per new tracker comment with its attributes, a `comment-edit` per edited one, a `ref` per new link whose both ends are held, resolved and read from either end (§14, **Links across sources**).

**ADR-622 gains:**

- **internal ops**, which the compiler emits and the JSONL reader refuses: `source` (set, replace or remove an item's source record), `view-body` (§4's operation) and `comment-edit` (replace a comment's text and attributes, addressed by an attribute value, `{"key": "source_id", "value": "…"}`);
- `attributes` on `comment` and `comment-edit`;
- an internal actor: events compiled by the pull carry `as = source:<name>`, which only the pull's compiler can produce (§6).

**Per-issue failures never block a source.** An issue whose events would fail the pre-pass (a title holding a marker, a mapped badge field the item's type no longer has, a tracker type that no longer matches the map on a retyped item) has its offending events dropped and is reported; the rest of the pull applies. The type is never changed by a pull (ruling fa6c47d).

**Identical tracker comments.** Attributes are not a hash input, and every sourced comment of one source has the same author, so two tracker comments with the same text in the same second share a hash and ADR-1013 §6 would refuse the second. The compiler skips the second and reports it, naming both tracker comment IDs (ruling a7b791e, point 3).

**Reporting.** Closed issues become `closed`; a linked issue the source no longer selects (outside its scope, or rejected by its filter; §14) becomes `out-of-filter`; one not found becomes `gone`, reported as "deleted or no longer readable" (ruling 8c0a817). A comment deleted on the tracker is reported, not removed. The item always stays.

**Credentials and access.** With no name, a source with no stored credential is skipped with a warning; a named one is an error naming `sq source credential set <name>`. A source failing its access probes is handled as §14 says.

### 11. Ownership and refusals

- While an item carries a `source` record, the squad cannot write what the tracker owns (FEAT-1271 US6): its `title`, a badge field its source maps, the stored body of `source_description`, and a comment authored by `source:<name>`. Each refusal names the source and the issue key. The refusals of the title, a mapped field and the description also name `source unlink`; the refusal of a sourced comment does not, because unlink leaves those comments uneditable (§14).
- **Retype** works on a sourced item and keeps its record (ruling fa6c47d); a mapped field the new type lacks is skipped by later pulls and reported.
- **`source unlink`** removes the record and turns the stored description into plain body prose at the pair's position, with any escaped HTML-comment opener left escaped, so no marker enters the prose. The imported comments stay, authored by `source:<name>`.
- **`source relink <source> <issue>`** reattaches an item that `source:<source>` created to an issue of that source, resolving a key to its immutable ID through the connector, and refreshes the item at once, leaving the squad's own body text (§14).
- **`show --refresh`** pulls that one item's issue through the same three phases, then shows it; on an item with no record it is refused (§14).

### 12. What `sq check` reports

`sq check` never calls the network. It reports: two items holding one issue of one tracker, across sources (§14); a `source:<name>` author, on an item or a comment, naming no declared source; an item whose source is undeclared or disabled; an item whose `source.state` is `out-of-filter` or `gone`; an identity key naming no declared source; two operators holding one ID on one source; a malformed comment-attribute line; the paired-tag findings of §4; and a `sources.toml` that does not load.

### 13. Schema 0.20 and its migration

The schema moves from `0.19` to `0.20`. The bump is owed even though a squad with no source changes no byte: a 0.19 build would read `source` as an unknown attribute, an attribute line as comment text (changing hashes), and a pair as an unbalanced tag, and the gate keeps it off a squad that holds them.

The `0.19 → 0.20` runner writes nothing to item files. Its pre-flight, run over the whole corpus before the stamp, refuses and lists every case:

- an item frontmatter carrying a top-level `source` key, which is now core;
- a role whose slug is `source`, now reserved;
- a workflow override declaring an item type or an alias named `source`, now a reserved command (§14);
- a discussion line, directly after a header, that matches the comment-attribute grammar.

Remedies go in the migration's `manual` text (§14 gives the ones for a role, a type and an alias named `source`). A squad clear of all four is stamped and carried unchanged.

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

**A role named `source` before 0.20** (amendment, 2026-11-04; completes §13).

- A roster slug never changes, so the role cannot be renamed. The remedy replaces it: create a successor under a new slug, move what commands can move, then delete the old role for good.
- Archiving is not enough: an archived role still holds its slug, and `agent_registered` still counts it as registered.
- A 0.20 build refuses every non-migration command on a 0.19 squad, so the steps run with the 0.19 release, before `sq migrate up`.
- What moves: the role's definition (re-created on the successor), items assigned to it (`update --assignee`), items it authored (`update --author`) and its memories (re-added under the successor, then forgotten).
- What is lost, stated in the manual text:
  - the old role item's own body and discussion, which only git history keeps;
  - its inbox: an `@source` in an existing comment reaches no one from 0.20 on;
  - the authorship of its comments, which keep `source` as their author, an author no role holds, so no one can edit or remove them;
  - any ref to the old role's ID, which must be re-pointed by hand.

**A type or alias named `source` before 0.20** (amendment, 2026-11-04; completes §13).

- `source` is a top-level command from 0.20 on, so an item type or an alias named `source` collides with it, and the workflow override no longer loads. It is the same reservation as the role slug, on another surface, and the runner lists it as a fourth refusal.
- The pre-flight reads the declared type names and aliases from the override file's text, not from the loaded spec, so it reports the case even though the spec cannot load. If `sq migrate up` cannot reach the pre-flight, the load refusal for a reserved command names `sq migrate chlog` for the manual step.
- Remedy, run with the 0.19 release:
  - An alias: rename or drop it in the override. No item file changes.
  - A type: declare a successor type, run `sq migrate rename-type source <new>`, which moves every item with its new prefix and folder, then delete the `source` type from the override.
  - What is lost: the old item IDs, which `rename-type` replaces, so a reference to an old ID in prose or outside the squad no longer resolves.

**A source with no type map** (amendment, 2026-11-04; completes §8 and §10).

- A source whose `maps.types`, after its connector's defaults are overlaid, holds no entry fails at load, naming the source and `maps.types`. No default type exists: a default would be a vocabulary name chosen in code, or one the adopter never declared.
- At pull time, a new selected issue whose tracker type or labels map to no type, or to two different types, is not created: one mapping to no type is counted, one mapping to two is named with the values it found (§14, **What becomes an item**). Entries that map to the same type do not conflict.
- An item that already exists is never affected: the type is applied at creation only (ruling fa6c47d).

**Connector keys are bare** (amendment, 2026-11-04; replaces §8's quoted key).

- Connector defaults are declared as nested tables, `[connectors.<name>.<version>]` (`[connectors.gitlab.v4]`, `[connectors.jira.cloud-v3]`), never as a quoted key `"<name>@<version>"`.
- Every key in a bundled document stays a TOML bare key, so a splat-ref can address it, and the `tests/meta` guard holds for `sources.toml` without an exemption.
- `<name>@<version>` stays the spelling of a connector everywhere a person reads one: messages, `sq source list` and the docs (ruling 4f4a607). The table is the `(name, version)` pair it already is.

**The pull diffs the listing; no cursor** (amendment, 2026-11-04; replaces §1's derived cursor and §10's incremental query).

- The connector's listing returns every issue in the source's scope, closed included (ruling 8c0a817), and the filter is evaluated on its rows (§14, **Source selection**), each with the fields the pull compiles (title, description, state, type and labels, author, key) and its tracker `updated_at`. It is paged, and it is complete on every pull: without stored state there is no incremental listing.
- An issue the listing returns is fetched in detail (its comments and links) when no item holds its `(name, id)`, or when its listed `updated_at` differs from the `source.updated_at` of an item that holds it. "Differs" is not "newer", so a tracker clock moving backwards still refreshes. Any other listed issue costs nothing beyond its listing row.
- A linked item missing from the listing is fetched once by ID, as before: `out-of-filter` or `gone`.
- The record's `updated_at` advances only when every other event of that issue applied, links included. When a pull drops one (§10), the issue's `source` event keeps the stored `updated_at` on an existing item, and writes it empty on an item the same pull creates. An empty value differs from every listed one, so the next pull fetches, retries and reports the issue again, and stores the real value once everything applies. No new state is stored. A standing skip under ruling fa6c47d (a mapped field the item's new type lacks, or a tracker type that no longer matches the map) counts as applied, so it is reported without refetching forever.
- An issue held back for want of a type map (§14) has no item, so every pull counts it from its listing row until the map covers it, and then creates it.
- Cost: one listing pass per pull, about the size of the scope divided by the tracker's page size, plus details for what changed. The listing of IDs already cost that pass, and the incremental query is gone. It grows with the closed issues the scope keeps; while pulls are manual this is accepted, and a narrower scope is the adopter's lever: the filter reduces what is written, not what is listed.
- Limit: a comment edited or deleted on a tracker whose issue `updated_at` does not move with it is picked up at the issue's next change, or by `show --refresh`.

**GitLab fetches one issue by project path and number** (amendment, 2026-11-04; completes §9).

- GitLab's `GET /issues/:id` is for administrators only, so the interface's single-issue fetch takes the immutable ID and the last known key. GitLab fetches `/projects/<path>/issues/<iid>` from that key and accepts the answer only when its global ID equals the stored one.
- A linked issue outside the scope whose project was renamed or transferred is therefore reported `gone`, since its last known key no longer leads to it. While the scope lists it, the listing still finds it under its new key.
- `relink` by immutable ID resolves on GitLab only an issue the scope lists, found by scanning the listing. `relink` by key resolves any issue the credential can read.

**Credential verbs carry an operation-level mark** (amendment, 2026-11-04; completes §7).

- Today the command endpoint is admitted only on the owner-only CLI listener, so `sq source credential set` and `remove` are reachable from nowhere else. Nothing on the two operations themselves says they must stay there.
- Before FEAT-33 admits the command endpoint on a listener that reaches beyond the machine, the two credential operations carry their own mark (for example `owner_only = True` on the operation). That listener refuses a command line that runs a marked operation until MILE-868 can tell callers apart, while `pull`, `relink` and the other source operations stay admitted. The mark lands no later than FEAT-33, and FEAT-33 tests against it.

**Concurrency** (amendment, 2026-11-04; corrects the Consequences).

- The daemon has no serial command lock: it serves commands concurrently, and the only lock is the index file lock that `IndexStore.transaction()` takes. Ruling a7b791e point 4 answered a question that assumed such a lock; the behaviour below is what holds.
- A pull, `show --refresh` and `relink` fetch outside every lock, then compile and apply in one transaction. The compile reads the index loaded under the lock, never the snapshot taken before the fetch, so what it diffs against is current.
- Two concurrent pulls of one source therefore cannot both create an issue: the second compiles after the first commits, finds the item, and refreshes it instead. A fetch decision made on the earlier snapshot can only cost an extra detail fetch, never a duplicate.
- A command that fetched for one particular item checks under the lock that the item still is what it fetched for, and refuses otherwise ("changed while the issue was fetched; run it again"). `relink` checks that the item still has no record and that no other item holds the issue. `show --refresh` checks that the item still carries the same `(name, id)`, and it never creates an item.
- A long pull holds the index lock only for its compile and apply, so other commands wait for that part alone.

**Unlink, then a pull** (amendment, 2026-11-04; completes §11).

- `source unlink` removes the record and keeps nothing (§11). An issue the source still selects is then held by no item, so the next pull imports it again as a new item, with the tracker's comments copied afresh. The unlinked item stays as it is: plain prose, the squad's own.
- This is the rule, and squads does not try to prevent it. Recognising the unlinked item later would need its `(name, id)`, which is exactly what unlink drops. Matching on title or prose would be a guess.
- `source unlink` says so when it runs. When the record's `state` was `open` or `closed` (the source selected it), its output carries a warning: the issue is still selected by `<name>`, the next pull imports it as a new item, and changing the source's filter so it rejects the issue (for example `and not <label>` in its `labels` expression), or moving the issue out of the scope, prevents that. With `out-of-filter` or `gone`, no warning is shown.
- To stop following an issue's text while keeping one item, the adopter makes the source stop selecting it. To undo an unlink, the adopter runs `relink` (§14).

**A source failing access on an unnamed pull** (amendment, 2026-11-04; completes §10).

- A named pull stops at its source's first blocking access failure, prints that line and writes nothing.
- An unnamed pull reports a source that fails its access probes with the probe's own line, fetches nothing from it, and goes on with the others: their events compile and apply as usual. The command then exits `1`, so a script sees the failure, and `--json` lists the failed source with its line.
- A missing credential is still a skip with a warning and exit `0` (§10), since that host simply does not pull that source. An expired token, an unreachable host or a refused permission is a failure of a source meant to work.

**Tracker API enums in connector modules** (amendment, 2026-11-04; narrows §9's guard).

- Some tracker API values are spelled like squad vocabulary, such as GitLab's issue type `task` and link type `blocks`. They are fixed per connector version, so a connector may hold them, and its probes check map keys against them.
- The `tests/meta` guard keeps one reviewed table of `(module, constant name)` pairs, each with a one-line reason. A listed constant must be a module-level tuple or frozenset of string literals naming one fixed set of tracker API names: an enum's values (GitLab's link types), or an object's field names (Jira's `_ISSUE_FIELDS`). The guard skips the string literals inside a listed constant and nowhere else: the same word anywhere else in the module still fails.
- The probes check `maps.links` keys against the connector's link-type enum, and a key outside it is a blocking vocabulary failure. They check each `maps.types` and `maps.fields` key against its own side (§14): a `type` key against the issue-type enum or the tracker's type list, a `labels` key against the tracker's labels, a `priority` key against the tracker's priorities. A key that a listable side does not hold is blocking. When the tracker cannot list a side (Jira Data Center's labels, GitHub's issue types), a key that no issue in the scope carries is a warning instead, since its absence cannot be proven (amendment, 2026-11-04).

**Converters receive the host issue's web URL** (amendment, 2026-11-04; completes §9).

- A converter is called as `(text, base_url, issue_url)`, where `issue_url` is the connector's web URL of the issue the text belongs to: its description, or the issue that holds the comment. It is still a pure function, with no network access.
- `gitlab-md` resolves an `/uploads/...` link against the issue's project (the part of `issue_url` before `/-/issues/`), which is how GitLab resolves it. `github-md` resolves a relative link against `issue_url`, as a browser on the issue page would. A root-relative link resolves against the host of `base_url`, and an absolute link is kept.

**`stored = true` needs a writer** (amendment, 2026-11-04; completes §4).

- `check_views` refuses `stored = true` on a view whose source kind has no writer. Only `source` has one today (the pull, `show --refresh`, `relink` and `unlink`), so an adopter's `stored = true` on a `self`, `role` or any other kind fails at load, naming the view. Otherwise the pair could only ever be empty, and no refusal could name a command that fills it.
- The refusal of a body write that alters a stored pair names `show --refresh` when the item holds a `source` record. On an item without one, it says that nothing in the squad writes this view until the item is linked to an issue.
- The stored-body mechanism stays generic (ruling ec05545). A future writer widens the rule by adding its kind.

**Connector decisions for GitHub and Jira** (amendment, 2026-11-04; completes §1, §3, §8 and §9).

- **Maps are keyed by tracker side.** A label anyone can type must never stand in for a tracker field, so each map reads one side at a time:

  ```toml
  [sources.jira-prod.maps.types.type]
  Bug = "bug"
  [sources.jira-prod.maps.types.labels]
  needs-design = "feature"
  [sources.jira-prod.maps.fields.priority.priority]
  High = "high"
  [sources.jira-prod.maps.fields.priority.labels]
  urgent = "high"
  ```

  - A side is a name the connector version declares. All of them expose `labels`. GitLab and GitHub expose `type` (the issue type). Jira exposes `type` (the issue type) and `priority`.
  - An undeclared side fails at load, listing the sides that version has. The connector carries each side as its own value on the fetched issue, never mixed into the labels.
  - When the sides of one map yield different values, the value is not set: an issue is not created and is named in the report with the values it found (§14, **What becomes an item**), and a badge field is left alone and reported the same way. Values that agree do not conflict.
- **Jira link keys are the directional phrase** (`blocks`, `is blocked by`). A link read from its inward side maps from that side, so `"is blocked by" = "depends-on"` gives the right direction. A link gives the same refs whichever end it is read from (§14, **Links across sources**): with the default `blocks = "blocks"`, the inward issue's `is blocked by` makes the ref from the outward issue. The phrases are edited by each instance's admins, so the probes check `maps.links` keys against that instance's `/issueLinkType`.
- **The Jira Cloud handle is the `accountId`.** Cloud has no username, and the `accountId` is the only stable public handle. The display name stays the readable part (§5). `@<accountId>` resolves to itself through an exact lookup, never through a search.
- **Restricted comments are not pulled.** A comment with a `visibility` restriction is skipped on both Jira versions. So is an agent-only service desk comment: `jsdPublic = false` on Cloud, and on Data Center the comment property `sd.public.comment` with `internal: true`, read with `expand=properties`. Squad files are readable by everyone with the repository. A comment pulled and later restricted on the tracker reads as deleted under §10: it is reported, stays in the squad, and no command removes it (§6).
- **The issue author is the immutable creator.** Jira's `author_id` and `author_handle` come from `creator`, never from the editable `reporter`, matching §1's "immutable user ID" and the other connectors. A request raised on someone's behalf is therefore attributed to whoever created it.
- **Every source names one scope.** The required `filter` is replaced by a required scope key and an optional filter (§14, **Source selection**, ruling f6cbdfc).

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
- The `source_description` record and the comment render look up each full key in `(name, key)` across every declared source on the host source's tracker, and replace the span with the item ID when exactly one item holds that key. Otherwise the reference stays as written.
- A sourced comment on an item that carries no `source` record has no host key, and renders untranslated.

**Two items holding one issue** (completes §1).

- Both lookups map to lists of sequence ids.
- The pull refreshes every item linked to a fetched issue, each through its own events, and reports the duplicate on every run.
- An issue is new only when no item on its tracker holds it (§14, **Links across sources**), so a pull never creates a third.

**Unlink and relink** (replaces §11's relink bullet).

- `source unlink` removes the record and nothing else of the authorship: the item's `author` stays `source:<name>`, and its imported comments stay authored by `source:<name>`. They are the item's history. No `--as` matches them (§6), so they can no longer be edited or removed. Unlink on an item with no record is refused.
- `source relink <source> <issue>` is accepted only on an item that carries no `source` record and whose `author` is `source:<source>`: that author is what "the same source" is checked against. It is refused, each time naming why, on an item that still holds a record (naming `source unlink`), on an item no source created, on an item another source created (naming it), and for an issue another item on the same tracker already holds (naming that item; §14, **Links across sources**).
- Relink resolves `<issue>`, a key or an immutable ID (for GitLab, an ID only when the scope lists the issue; §14), through the connector, then runs the three phases of §10 for that one issue, with the record as one more event: the record, the title, the mapped fields, the description view and the comments, matched by `source_id`, land in one transaction. The prose unlink left in the body stays the squad's. The type is not changed.
- Relink does not leave the description to the next pull: relink stores the issue's current `updated_at`, and a pull fetches details only for an issue whose listed `updated_at` differs from the stored one, so a pull would never restore the view.

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

**One author form for sourced comments** (amendment, 2026-11-04; replaces §5's display; ruling ad8aaba).

- The form is, in order: the operator slug, only when an identity matches (§3); the name; `via <source>`; `@<author_handle>`.
- A matched author's name is the operator's name from the roster, unquoted; the tracker's `author_name` is not shown. An unmatched author's name is `author_name` in double quotes, inside which `"` and `\` take a backslash, and control, format and line or paragraph separator characters are written `\uXXXX`, so the name stays on one line, cannot close its own quotes and cannot reorder the text around it. An empty `author_name` is left out: `via gitlab-prod @jdoe`.
- A matched line starts with a slug and an unmatched one with a quote (or with `via` when it has no name), so they never read alike, on a trusted source or not. A tracker user who sets their display name to `op-pierre Pierre Chat` reads `"op-pierre Pierre Chat" via gitlab-prod @mallory`.
- `author` in a `--json` discussion entry is the same string; `identity` still carries the matched slug or `null`.

**Source selection: a scope on the tracker, a filter in squads** (amendment, 2026-11-04; rulings f6cbdfc and ec3c412; replaces §8's `filter`, the required filter of **Connector decisions** and every connector's tracker-side filter).

Measured on a self-hosted GitLab 19.5 (2026-11-04):

- `GET /projects/<url-encoded path>/issues` and `GET /groups/<path>/issues` return only that project's or that group's issues, the group's subgroups included.
- `labels=a,b` is an AND on the server. `or[labels]=a,b` is silently ignored on `/issues`, which then returns every issue on the instance.
- The instance-wide `GET /issues?labels=<filter>` the connector used returned issues of any project carrying the label, and other projects on the same instance used the same scoped-label scheme.

A label is therefore no selection a squad can rely on: it spans the instance, it cannot say "any of", and covering one project took one source per label, which lost the links between them (BUG-1284).

**The scope.** A source names exactly one scope, under a key its connector version declares. The pull lists every issue of the scope, in every state, with no tracker-side condition.

| connector | key | value | listing |
|---|---|---|---|
| `gitlab@v4` | `project` | a project's full path, `group/project` | `GET /projects/<url-encoded path>/issues` |
| `gitlab@v4` | `group` | a group's full path, `group` or `group/subgroup` | `GET /groups/<url-encoded path>/issues`, subgroups included |
| `github@v3` | `repository` | `owner/repo` | `GET /repos/<owner>/<repo>/issues`, pull requests skipped |
| `jira@cloud-v3`, `jira@dc-v2` | `jql` | a JQL query | the version's JQL search |

- The registry declares each version's scope keys beside its sides. No scope key, two of them, or an empty value fails at load, naming the source and listing the keys its version takes; another connector's scope key is an unknown key. A value of the wrong shape, and a `jql` holding `ORDER BY`, fail at load too (**Scope values, quoted characters and restricted link targets**, below).
- **GitHub has no organisation scope** (ruling ec3c412). `GET /orgs/<org>/issues` exists, but what it lists depends on its `filter` parameter and on the kind of token, and it has not run against a live instance; neither has the repository listing. Several repositories are several sources, which the link rule below keeps linked. An `organization` key can be added later without changing any source that loads today.
- **For Jira the JQL is the scope.** JQL can express any selection, so squads does not parse it, and the filter applies to what it returns, with the same grammar as every other connector. A JQL that spans projects is the adopter's explicit choice.

**The filter.** `filter` is an optional table, evaluated in squads on each listed issue. It is keyed by side, like the maps, and each side takes one boolean expression, a string:

```toml
[sources.platform]
connector = "gitlab"
base_url = "https://gitlab.example.com"
project = "group/project"

[sources.platform.filter]
labels = '(type::epic or type::story) and not "help wanted"'
type = 'issue or incident'
```

- A value in an expression is true when it is on the side: one of the issue's labels, or its type or priority. Values match exactly as the tracker spells them, case included, like map keys. A side the issue has no value on makes every value false.
- An issue is **selected** when it is in the scope and every expression the filter names is true for it: the sides are ANDed. A source without `filter` selects every issue of its scope.
- The expression is parsed when `sources.toml` loads, by a parser of its own in `_sources/_filter.py`. No existing parser fits: the `$(self)` splat-ref of `_specmerge.py` is a whole-string token, not an expression.

**The expression grammar** (EBNF; whitespace, a space, a tab or a line break (LF or CRLF), may separate any two tokens and is required only between two words):

```ebnf
expression = disjunction ;
disjunction = conjunction , { "or" , conjunction } ;
conjunction = negation , { "and" , negation } ;
negation   = "not" , negation | primary ;
primary    = value | "(" , disjunction , ")" ;
value      = bare | quoted ;
bare       = bare char , { bare char } ;            (* not "or", "and" or "not" in any case *)
bare char  = "A".."Z" | "a".."z" | "0".."9" | ":" | "-" | "_" | "." ;
quoted     = '"' , quoted char , { quoted char } , '"' ;
quoted char = any character but '"', "\" or a control character (Unicode Cc: U+0000-U+001F, U+007F-U+009F)
           | '\"' | '\\' ;
```

- `not` binds tightest, then `and`, then `or`; `and` and `or` group from the left. `a or b and not c` reads `a or (b and (not c))`.
- A line break between tokens is whitespace, so a TOML multi-line literal string (`'''...'''`) loads; a long expression can be laid out over several lines.
- The keywords are `or`, `and` and `not`, lowercase. A bare word that spells one in another case (`OR`, `Not`) is refused, so `a OR b` never reads as three labels; a label spelled like a keyword is written quoted (`"or"`).
- A bare word is ASCII letters, digits, `:`, `-`, `_` and `.`, and ends at any other character. Any other label is quoted: one with a space, a `/`, a non-ASCII letter. Inside quotes `\"` is a `"` and `\\` is a `\`; every other character stands for itself. A quoted value is never empty.
- TOML reads the string first. A literal string (`'...'`) passes the expression through unchanged, so the docs write every filter that way; in a basic string (`"..."`) each `"` and `\` of the expression needs its own TOML escape.

**Refusals at load.** Each names the source and the side (`sources.platform.filter.labels`), and a parse error its 1-based line and column in the expression string, counted in characters:

- `filter` that is not a table, or an empty one; a side value that is not a string.
- A side the connector version does not have, listing its sides.
- An empty expression, or one holding only whitespace.
- A malformed expression: a character outside the grammar (outside quotes: anything but a bare char, a parenthesis or whitespace; a control character other than a tab or a line break, a lone CR included; a control character inside quotes, a tab and a line break included), an unterminated quoted value, a backslash followed by anything but `"` or `\`, an empty quoted value, a keyword in another case, a value or `(` where `and`, `or` or `)` is expected (`help wanted` unquoted, `a b`), an operator or `)` where a value is expected (`a and`, `or b`, `()`), and an unbalanced parenthesis (an unclosed `(` is reported at its own column).

**Room to grow.** What loads now keeps its meaning in every later release:

- Every `filter` key that is not a side of the connector version is refused, and so is a `filter` that is not a table, so an OR across sides (one filter-wide expression) can come later as a new key or form without reinterpreting any filter that loads now.
- A new operator uses characters refused today outside quotes (`*`, `=`, `,`, `!`, …), never a new word: every bare word that is not a keyword is a value today.
- A `key` side naming single issues is a new side, declared by the registry like the others.

**Why the filter is no longer required** (ruling ec3c412: the scope is required, `filter` optional). The required filter bounded what a token listed: without it, a GitHub token listed every issue of every repository it could read into a committed squad. The required scope now bounds it, and names exactly what the adopter chose to follow. The filter decides what is written among what the scope lists; a listed issue it rejects stays in memory for that command, and is never written, logged or named in a report. Exposure inside the scope is the next rule's concern.

**Restricted issues are not pulled, with no opt-out** (ruling ec3c412; extends the restricted-comment rule of **Connector decisions** to issues, on the same ground: squad files are readable by everyone with the repository). A GitLab issue marked `confidential` and a Jira issue carrying a security level are treated as not returned, by the listing, by ID, by lookup and, where the link record says so, as a link's other end (**Scope values, quoted characters and restricted link targets**, below); a GitLab internal note (`internal: true`) is skipped like a restricted Jira comment. An item whose issue becomes restricted reads as `gone`, is reported and stays. No source key pulls them. GitHub has no per-issue restriction: the repository's visibility is the scope's. None of these fields has been read from a live instance.

**States under a full listing.**

- The state a pull compares and stores for a listed issue is the one it would write: the tracker's `open` or `closed` when the filter accepts the issue, `out-of-filter` when it rejects it. An out-of-filter item is therefore not fetched again on every pull, and one the filter accepts again is.
- Listed, accepted, held by no item: created when its type maps to one type; counted when it maps to none, named when it maps to two (below).
- Listed, accepted, held: refreshed when its listed `updated_at` or state differs, as before.
- Listed, rejected, held by no item: ignored, at the cost of its listing row. The pull counts them (`filtered out <n>` on the source's line, `filtered_out` in `--json`) and names none.
- Listed, rejected, held: `out-of-filter`, refreshed like any held issue, so its title, description and comments still follow the tracker.
- Held, not listed: the issue left the scope (moved, transferred, or no longer selected by the JQL). It is fetched once by ID, `out-of-filter` when the tracker returns it and `gone` when it does not. One state covers both ways out of the selection because the squad does the same for both; the report line says which ("rejected by the filter", "outside the scope"), decided at pull time and never stored.
- A single-issue command (`show --refresh`, `relink`) decides selection without listing the scope: it evaluates the filter on the issue, and the connector says whether the issue is in the scope, from its key for GitLab (the project path equals `project`, or starts with `group/`, ignoring case) and GitHub (the repository equals `repository`, ignoring case), and with one search for Jira (`id = <id> AND (<jql>)`, which a scope without `ORDER BY` keeps valid).

**What becomes an item.** The scope and the filter select; the type map decides what becomes an item. A selected issue whose type and labels map to no type is not created and is not named: the pull counts it on the source's line (`skipped <n> (no type)`) and in `--json` (`skipped_no_type`), beside the `filtered out` count. Leaving a value out of the map is therefore how an adopter leaves those issues out, with no filter needed. A selected issue whose values map to two different types is a data error on the tracker: it is not created, and every pull names it on one report line with the values it found, until the tracker or the map is corrected (ruling af70274). Both are decided on the listing row, before any detail fetch, so such an issue costs its row and not its comments and links.

The guard against a mistyped map is `sq source check`, not the pull: its probes verify that every `maps.types` and `maps.fields` key, and every value a filter expression names, exists on its side of the tracker (**Tracker API enums**). A misspelled key on a listable side fails there, and on a side the tracker cannot list it is a warning when no issue in the scope carries it.

**Links across sources** (settles BUG-1284).

- **One tracker.** Two sources are on the same tracker when their normalised base URLs are equal, the key of the credential store (§7). An immutable issue ID is unique on its tracker (GitLab's global ID, GitHub's node ID, Jira's issue ID), so an issue is its tracker and its ID, whichever source lists it.
- **Resolution.** A link's other end, a tracker reference in text (§9) and relink's "already held" check look up `(name, id)` and `(name, key)` for every declared source on the host source's tracker, not for the host source alone. The lookups stay derived (§1): the union is formed from `sources.toml` when a command compiles, and nothing is stored. An item whose source is no longer declared has no tracker and matches nothing; `sq check` already reports it.
- **One holder.** A pull creates an item only when no item on its tracker holds the issue. When scopes overlap (a group and a project inside it), a source whose scope lists an issue another source's item holds leaves it to that source and reports `held by <ID> of source <other>`; the holder refreshes it. `source_id_unique` reports two items holding one issue of one tracker, across sources.
- **Either end.** A connector's link carries its type as read from the host and its inverse, as read from the other end: fixed for GitLab (`blocks` and `is_blocked_by`, `relates_to` both ways) and GitHub (`blocking` and `blocked_by`), and taken from the link type's `outward` and `inward` phrases for Jira. The compiler makes host → target from `maps.links[type]` and target → host from `maps.links[inverse]`, each when mapped. A link therefore gives the same refs whichever end is read, and every connector returns a link on both of its issues.
- **When links are read.** Links are compiled for every issue fetched in detail, and an unchanged issue is not read again for them. That suffices: an issue enters the squad through a detail fetch, and its own links, read from its end, make every ref to the items already there. A ref therefore appears at the latest when the second of its issues is pulled, by whichever source and in whichever order. Reading every listed issue's links on every pull would cost one request per issue of the scope, per pull, to catch only the limit below.
- **Limit.** A link added on the tracker between two issues already held appears at the next change of either issue, or with `show --refresh`, like an edited comment. Whether adding a link moves an issue's `updated_at` is unverified on every tracker.
- **A dropped link is reported.** A mapped link whose other end no item on the tracker holds makes no ref and one line per host issue: `<key>: <n> link(s) not followed, no item holds <target key>, …`. The ref follows when that issue is pulled. A link type no map names is still skipped without a line, as a choice the map made, and so is a link to an issue the tracker restricts, where the link record says so (**Scope values, quoted characters and restricted link targets**, below).

**Probes.** The access probe reads the scope: an unknown or unreadable project, group, repository or JQL fails, naming its key. An empty scope, and a filter that accepts no listed issue, are warnings, since a new project has no issues yet. The value checks of a filter expression are those of the map keys, above.

**No migration.** Nothing of the sources feature is released, so the grammar changes in place, with no schema change and no migration step. A `sources.toml` written for development builds (`filter = "<label>"`) fails at load, saying that `filter` is a table and naming the scope keys its connector takes. This repository's squad declares no source. The delivered text owes:

- `docs/sources.md`: the key table (scope keys, `filter` optional), the filter's expression grammar with its precedence, quoting and TOML literal-string advice, the "`filter` is required" paragraph replaced by the scope rule, each connector's `filter` bullet replaced by its scope key and listing, restricted issues and internal notes, the states, the `filtered out` and `skipped (no type)` counts, an unmapped type as the way to leave issues out, links resolved across one tracker's sources and from either end, the dropped-link line, the unlink warning's remedy, and the Jira link bullet.
- `CHANGELOG.md`, in the unreleased section: the external-sources entry, each connector's "the filter is a label" or "a JQL query" (the scope key, and a filter expression per side), the no-type count replacing the per-issue report of an unmapped issue (an issue mapping to two types is still named), and the `sq source pull`, `source unlink` and `sq source check` entries ("the filter readable" becomes "the scope readable").
- The `sq override scaffold sources` text and its worked example, and the `sources.toml` grammar in `docs/stability.md`, the filter expression grammar included.

**Scope values, quoted characters and restricted link targets** (amendment, 2026-11-04; REV-1292 F2, F3, F5, F11 and F12; completes **Source selection** and **Links across sources**).

- **Scope shapes, checked at load** (F12). A path segment is one or more ASCII letters, digits, `_`, `-` or `.`, and is neither `.` nor `..`. GitLab `project` is two or more segments joined by `/`, `group` one or more, and GitHub `repository` exactly two, `owner/repo`. No leading, trailing or doubled `/`, and no whitespace. A value of another shape fails at load like a missing scope key, naming the source, the key and the shape it takes (`group/subgroup/project`), so a value reaches a listing URL only as the path it names. The shape is checked, not each tracker's full naming rules: a well-shaped value that names nothing fails the access probe. `jql` keeps only the non-empty rule and the next one.
- **No `ORDER BY` in a Jira scope** (F2). The single-issue search wraps the scope as `id = <id> AND (<jql>)`, and JQL takes `ORDER BY` only at the end of a query, never inside parentheses. A `jql` holding the words `order` and `by` in a row (any case, any whitespace between) outside a JQL quoted string (`"..."` or `'...'`, with backslash escapes) fails at load, saying that the pull lists the whole scope in no order and that the clause is to be removed. JQL reserves `order`, so outside quotes the two words can only be the clause. This is the one lexical reading squads makes of a JQL: the pull, the probes and the single-issue search send it as written.
- **GitLab paths compare ignoring case** (F3). GitLab resolves namespace and project paths regardless of case and returns keys in their canonical spelling, so the in-scope check compares the key's project path with `project`, and its prefix with `group/`, ignoring ASCII case, as GitHub's check does for `repository`. Map keys and filter values still match exactly: they name tracker values, not paths.
- **What a quoted value refuses** (F11). A control character is one of Unicode category Cc: U+0000 to U+001F and U+007F to U+009F, the tab, LF and CR among them. Inside quotes that is the only refusal besides an unescaped `"` or `\`. A no-break space, a zero-width space or joiner, a line or paragraph separator and a bidirectional control stand for themselves, since a label can hold them and a refused character could never be matched. Outside quotes, a character a quoted value accepts is refused with the advice to quote it; a control character is refused without that advice. The EBNF above says so.
- **A link to a restricted issue makes no line** (F5). A restricted issue is never pulled, so the dropped-link line's promise, that the ref follows when the other end is pulled, cannot hold for it, and the line would name it on every report. A connector drops a link whose record marks its other end restricted, as its listing drops such an issue: no ref, no line, no count. GitLab's link record is an issue record and carries `confidential`. Jira's link record carries no security level, and reading each target to learn it would cost one request per link, so a Jira link to an issue under a security level stays on the dropped-link line, by key only (no title or text); that limit is documented. GitHub has no per-issue restriction.
- Delivered text owed: `docs/sources.md` (the scope shapes, the Jira scope bullet's `ORDER BY` refusal, the GitLab case rule, the characters a quoted value refuses, the restricted-link rule and its Jira limit beside the dropped-link line), `docs/stability.md` (the scope shapes and the quoted-character rule in the `sources.toml` grammar), and the CHANGELOG external-sources entry where it states the scope keys or the filter grammar.

## Rejected

- **A locked item body for the description.** Ruled out (ruling ec05545): the description is a view's stored body, refreshed by an operation.
- **Paired tags for every view.** It would let a locally derivable view cache its rendering, which ADR-776 forbids. The pair is declared per view.
- **Escaping only well-formed `sq:` markers in a stored body.** Whitespace and case variants, and the attribute form, would each need their own case; escaping every HTML-comment opener has one rule and an exact inverse.
- **Comment attributes in frontmatter.** A comment has no stable key a frontmatter record could use: its hash changes on every edit.
- **A persisted source index.** It would store what the items already hold.
- **A cursor, stored or derived** (§14). A stored one is derivable, and a derived one loses issues and changes.
- **Tokens from the client's environment, a client-sent token per pull, or `sq source` as a local-only command** (ruling e7b6635, board notice 22).
- **The OS keyring.** It is absent on a headless server and under WSL, and adds a dependency the store does not need.
- **A test-only connector row** (§14). The pull would be tested against a connector whose behaviour its test author invented.
- **The `self` view source for the description** (§14). Its resolver and a transform see neither the sources document nor the lookup.
- **Selecting on the tracker by label** (§14, ruling f6cbdfc). A label listing spans the instance, and GitLab cannot OR labels; the scope selects on the tracker and the filter in squads.
- **`any`, `all` and `none` lists per side** (§14, ruling ec3c412). Lists cannot nest, so `(a and b) or c` has no spelling, and each later combination would be one more operator key; three operators and parentheses say any combination of one side's values.
- **Naming each issue that maps to no type on every pull** (§14, rulings ec3c412 and af70274). An unmapped type is the adopter's way to leave issues out, and a line per issue on every pull is noise; a mistyped map is caught by the probes. An issue mapping to two types stays named, as a tracker data error.
- **A load-time satisfiability check on a one-value side** (§14, ruling af70274). An expression that can select nothing (`type = 'issue and incident'`) loads; the empty pull and the `sq source check` warning for a filter that accepts no listed issue already show it.
- **Stripping a trailing `ORDER BY` from the scope JQL** (§14, REV-1292 F2). It rewrites the adopter's query out of sight; a refusal at load says it once, and every JQL is sent as written.
- **Refusing format characters in a quoted value** (§14, REV-1292 F11). A label can hold them (a no-break space, an emoji joined by U+200D), and a refused character could never be matched.
- **Reading every listed issue's links on every pull** (§14). One request per issue of the scope, per pull, for a link added between two unchanged issues.
- **A second write path for the pull.** The importer already has the transaction, the per-event clock and actor, the pre-pass and the reflog.

## Consequences

- `Item` gains `source: SourceRecord | None`; `CORE_KEYS` gains `source`; the comment model gains `attributes`; `SquadsDB` gains the two derived lookups, each to a list of sequence ids.
- The attribute kinds are `str`, `list`, `bool`, `date` and `map`; the operator type carries the pinned `identities`.
- `_models/_markers.py` gains the stored-view close tag and the attribute-line form; `reject_markers` widens as §5 says; `place_view_tags` handles pairs; `ViewSource.kind` gains `source`, resolved through a provider the service layer hands to `_views`.
- A new `_sources` package holds the spec loader for `sources.toml`, both registries, the connectors and the pull's compiler; `tests/meta`'s import-edge table gains its rows.
- `docs/stability.md` needs the nested-record rule, the `map` kind, the `source` record, the namespaced author grammar and the reserved `source` slug, the paired view tag and its escape, the `source` view source kind, the attribute line, the `sources.toml` grammar and the credential store's location; the adopter docs say that more author words may be reserved, and keep a source connector apart from the MCP connector of FEAT-319.
- ADR-880 §2 and §4, ADR-776 §1, ADR-1007 §1 and §4, ADR-979 §2 and §2b, ADR-1261 §5 and ADR-622 are narrowed in place, each with a dated note pointing here.
- A source names one scope key and an optional `filter` table of one expression per side, parsed by `_sources/_filter.py`; the connector registry declares each version's scope keys, a connector answers whether one issue is in its scope, and a link carries its inverse type. Issue identity, link and reference resolution and `source_id_unique` span every source of one tracker, derived from `sources.toml` (§14).
- A pull does not block other served commands: the daemon serves commands concurrently, and a pull holds only the index lock, for its compile and apply (§14). Its network fetch runs outside every lock.
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
- [2026-11-04T00:11:26Z] `architect` Robert Architect:
  - Amended (2026-11-04): section 14 replaces the section 13 remedy for a role named source (no command changes a slug) with a replace-and-purge procedure run on 0.19, and states what is lost; the runner text is on TASK-1276 for python-dev.
- [2026-11-04T00:50:31Z] `architect` Robert Architect:
  - Amended (2026-11-04): section 14 adds the 0.20 refusal and remedy for a type or alias named source (section 13 now lists four cases), refuses a source with no type map at load and skips an issue that maps to no type or to two types, and makes connector keys nested bare tables, connectors.<name>.<version>; runner text is on TASK-1276.
- [2026-11-04T02:27:04Z] `architect` Robert Architect:
  - - @op-pierre two points from REV-1281 touch your ruling 2980084 and ruling 8c0a817. The first needs your call.
      1. **F4, blocks the display fix in TASK-1276.** Your ruling gives the unmatched form as `Pierre Chat via gitlab-prod @pchat`. A tracker user can set their display name to `op-pierre Pierre Chat`. The reviewer reproduced it: the spoofed line then reads like the real matched `op-pierre Pierre Chat via gitlab-prod @pchat`, and only the handle differs. On a `trusted` source no notice shows at all.
         - Recommendation: a matched author starts with the operator's slug, followed by the operator's name from the squad's own roster, never the tracker's: `op-pierre Pierre Chat via gitlab-prod @pchat`. An unmatched author always starts with the handle, with the tracker's name quoted after it (quotes and control characters escaped): `@mallory "op-pierre Pierre Chat" via gitlab-prod`. One form starts with a slug, the other with `@`, so the two can never read alike, trusted or not. `--json` `author` follows the same rule.
         - Alternative: drop the tracker display name from the unmatched form, giving `@mallory via gitlab-prod`. It is safer still, but loses the name.
      2. **F2, decided, for your information.** Your ruling 8c0a817 describes the pull as an incremental query since the cursor plus a full listing. The derived cursor loses issues and changes (F2, reproduced). ADR-1274 §14 now drops the cursor: the pull diffs the full listing, which your ruling already requires on every pull, against each item's stored `updated_at`. It keeps your invariants: no stored state, closed, `out-of-filter` and `gone` detected on every pull, and the item always stays.
- [2026-11-04T02:27:19Z] `architect` Robert Architect:
  - Amended (2026-11-04) for REV-1281: the pull drops the cursor and diffs the listing (sections 1, 9, 10, 14, Rejected), GitLab fetches one issue by path and number (sections 9, 14), the unlink hint is limited to the title, mapped fields and description (section 11), and the credential verbs carry an operation-level mark before FEAT-33 (section 14). The display point (F4) is in the previous comment for op-pierre.
- [2026-11-04T02:53:09Z] `architect` Robert Architect:
  - Amended (2026-11-04) for REV-1281 F3: an item created by a pull that drops one of its issue events stores an empty updated_at (sections 1 and 14), so the dropped event is retried on new items too.
- [2026-11-04T03:28:21Z] `architect` Robert Architect:
  - - @op-pierre the premise of your ruling a7b791e point 4 was false, and I asked the question that carried it. The daemon has no serial command lock: it serves commands concurrently, and the only lock is the index file lock that transactions take. A pull fetches outside every lock, then compiles and applies in one transaction, against the index as it stands under that lock. Other commands therefore wait only for that last part, and two concurrent pulls cannot create the same issue twice. ADR-1274 Consequences and §14 now say so. No decision is needed, unless you want pulls serialised.
- [2026-11-04T03:29:35Z] `architect` Robert Architect:
  - Amended (2026-11-04): section 14 states that unlink keeps nothing, so a pull re-imports an issue the filter still lists as a new item; unlink warns when the record was open or closed. Brief for python-dev on TASK-1276.
- [2026-11-04T03:33:17Z] `architect` Robert Architect:
  - Amended (2026-11-04) for REV-1282: unnamed pull with a source failing access (section 10, 14), the tracker-enum exemption in the vocabulary guard (sections 9, 14), the issue web URL handed to converters (sections 9, 14), and stored = true accepted only on a kind with a writer (sections 4, 14).
- [2026-11-04T05:00:43Z] `architect` Robert Architect:
  - Amended (2026-11-04) for REV-1283 F7: maps are keyed by tracker side (section 8), Jira link phrases, the Cloud accountId handle, restricted comments skipped, the creator as author, filter required for every source, and the guard exemption covers fixed sets of API names (sections 9, 14).
- [2026-11-04T05:32:11Z] `architect` Robert Architect:
  - Amended (2026-11-04) for REV-1283 F12: the vocabulary probe blocks only on a listable side; an unlistable side gives a warning for a key no in-filter issue carries.
- [2026-11-04T08:04:30Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-04): keep the source view kind (kind = "source") as built.
  - Acknowledged: the pull diffs the full listing instead of the incremental query of ruling 8c0a817, and ruling 4 rested on a false premise (the daemon serialises only the index write); both corrections stand.
  - Acknowledged: side-keyed maps and the required filter in sources.toml.
- [2026-11-04T08:12:51Z] `op-pierre` Pierre Chat:
  - Ruling on F4 (2026-11-04): one form for every sourced comment author, in this order: the operator slug if matched; then the name, quoted when unverified (the roster name when matched, the tracker name quoted when not); then "via <source>" and the tracker handle. Matched: op-pierre Pierre Chat via gitlab-prod @pchat. Unmatched: "John Doe" via gitlab-prod @jdoe. --json author follows the same rule.
- [2026-11-04T08:14:43Z] `architect` Robert Architect:
  - Amended (2026-11-04) for REV-1281 F4 per ruling ad8aaba: §5 Display and a new §14 entry give one author form (slug if matched, roster name or quoted escaped tracker name, via <source> @handle); a spoof reads "op-pierre Pierre Chat" via gitlab-prod @mallory.
- [2026-11-04T09:11:47Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-04), source selection: a source names a scope on the tracker (for GitLab a project or a group) and the pull fetches every issue of that scope; which issues become items is decided by a filter evaluated in squads, with room for a richer filter grammar later. No label is required on the tracker. Found in a live GitLab run: a single-label filter is instance-wide, GitLab cannot OR labels (or[labels] is silently ignored), so covering a project took one source per label and lost the links between them (BUG-1284).
- [2026-11-04T09:19:42Z] `architect` Robert Architect:
  - - Amended (2026-11-04) per ruling f6cbdfc: new §14 entry **Source selection** and **Links across sources**, with pointer edits in §1, §8, §9, §10, §12 and the §14 entries that named the filter.
      - Scope keys: gitlab `project` | `group` (subgroups included), github `repository`, jira `jql`; exactly one, required. The pull lists the whole scope, no tracker-side condition.
      - `filter` is an optional table evaluated in squads, keyed by side like the maps, with `any`, `all`, `none`; unknown keys refused, so it can grow.
      - Full listing: rejected and unheld issues are ignored (counted as `filtered out`); a held one the filter rejects or that left the scope is `out-of-filter`; unmapped types are reported but no longer fetched in detail.
      - BUG-1284: issue identity, link targets, reference translation and `source_id_unique` span every source with the same normalised base URL; a link carries its inverse type so either end makes the same refs; a mapped link with no held target is reported.
      - No migration (unreleased); the docs and CHANGELOG items owed are listed in the entry.
    - @op-pierre three points are yours; my recommendation follows each:
      - 1. `filter` optional, scope required. This reverses the required filter you acknowledged in 247d922; the scope now bounds what a token lists. Recommend: optional.
      - 2. Restricted issues are not pulled: GitLab confidential issues and internal notes, Jira issues with a security level, like restricted Jira comments today. Dropping the opt-in label makes these reachable in a committed squad. Recommend: yes, with no opt-out.
      - 3. GitHub org scope stays out: one repository per source, an `organization` key later once verified live. Recommend: out.
- [2026-11-04T09:34:27Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-04) on the questions of the source-selection amendment:
    
    - The scope is required; `filter` is optional.
    - The type map decides what becomes an item. A selected issue that maps to no type is counted (for example `skipped 3 (no type)`), not reported on every pull; `sq source check` still verifies that every mapped value exists on the tracker.
    - `filter` is a table of one boolean expression per side, replacing the any/all/none operators:
    
      ```toml
      [sources.platform.filter]
      labels = '(type::epic or type::story) and not "help wanted"'
      ```
    
      Operators `or`, `and`, `not` and parentheses; `not` binds tightest, then `and`, then `or`. A value is a bare word (letters, digits, `:`, `-`, `_`, `.`) or a double-quoted string. The sides a filter names are ANDed. A malformed expression is refused at load with its position. An OR across sides (one filter-wide expression) is left for later, without changing what a file that loads now means.
    - No existing parser to reuse (the `$(self)` splat-ref is a whole-string token, not an expression); the parser is new, kept in its own module under `_sources/`.
    - Restricted issues are skipped with no opt-out, and GitHub has no organisation scope until verified live, as recommended.
- [2026-11-04T09:38:22Z] `architect` Robert Architect:
  - Amended §14 per ruling ec3c412: one boolean expression per filter side (EBNF, precedence, quoting, load refusals with column, room to grow; parser in `_sources/_filter.py`), unmapped types counted as `skipped <n> (no type)` with the probes as the map guard, restricted issues and the GitHub organisation scope recorded as ruled, and the unlink, docs, CHANGELOG, Rejected and Consequences references updated.
- [2026-11-04T09:51:29Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-04) on the filter grammar choices: bare words stay ASCII-only; an issue mapping to two types is named in the report (a tracker data error), only an issue mapping to no type is just counted; a line break in an expression counts as whitespace; drop the load-time satisfiability check on one-value sides (an empty pull and the source check probe already show it).
- [2026-11-04T09:52:23Z] `architect` Robert Architect:
  - Amended §14 per ruling af70274: bare words ASCII-only, an issue mapping to two types named on the report (only no-type counted), LF/CRLF as whitespace with line and column in parse errors, the one-value satisfiability refusal dropped (Rejected), and the Context wording aligned with the scope ruling.
- [2026-11-04T15:34:34Z] `architect` Robert Architect:
  - Amended §14 (2026-11-04) for REV-1292, new entry **Scope values, quoted characters and restricted link targets**, with pointer edits in **Source selection**, the EBNF, the load refusals, **Restricted issues**, the single-issue bullet, **Links across sources** and Rejected:
    - F2: a `jql` holding `ORDER BY` outside a JQL quoted string is refused at load; the JQL is never rewritten and is sent as written everywhere.
    - F3: the GitLab in-scope check compares `project` and the `group/` prefix ignoring ASCII case, like GitHub's `repository`.
    - F11: a quoted value refuses only Unicode Cc controls (U+0000-U+001F, U+007F-U+009F) besides an unescaped `"` or `\`; format characters and separators stand for themselves; EBNF aligned.
    - F5: a link whose record marks its other end restricted (GitLab `confidential`) is dropped with no ref, no line, no count; Jira's link record cannot tell, so its key stays on the not-followed line, a documented limit.
    - F12: scope shapes checked at load: ASCII segments of letters, digits, `_`, `-`, `.`, not `.` or `..`; GitLab `project` two or more, `group` one or more, GitHub `repository` exactly two; no empty, leading or trailing `/`, no whitespace.
<!-- sq:discussion:end -->
