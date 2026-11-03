---
id: TASK-1276
sequence_id: 1276
type: task
title: Sources spec, source record, credentials and sq source pull
status: Draft
parent: FEAT-1271
author: tech-lead
refs:
- ADR-1274:implements
- MILE-1269:targets
- TASK-1275:depends-on
description: sources.toml, GitLab connector and harness, source record, map kind and
  identities, comment attributes, credentials, pull as import events, refusals, check
  rules
subentities:
- local_id: ST1
  title: sources.toml spec document and its validation
  status: Todo
  maps_to: US1
- local_id: ST2
  title: Source record, derived lookups, namespaced author
  status: Todo
  maps_to: US2
- local_id: ST3
  title: Map attribute kind and operator identities
  status: Todo
  maps_to: US3
- local_id: ST4
  title: Comment attributes and sourced-comment display
  status: Todo
  maps_to: US8
- local_id: ST5
  title: Credential store and the hidden prompt
  status: Todo
  maps_to: US9
- local_id: ST6
  title: sq source pull compiled to import events
  status: Todo
  maps_to: US4
- local_id: ST7
  title: The source_description view and show --refresh
  status: Todo
  maps_to: US5
- local_id: ST8
  title: Ownership refusals and sq check reports
  status: Todo
  maps_to: US6
- local_id: ST9
  title: Source list, unlink and relink
  status: Todo
  maps_to: US7
- local_id: ST10
  title: HTTP helper, loopback harness, GitLab connector
  status: Todo
  maps_to: US4
created_at: '2026-11-03T23:02:45Z'
updated_at: '2026-11-03T23:19:00Z'
priority: high
---
<!-- sq:body -->
## Goal

A squad declares its trackers in `sources.toml`, stores their credentials where it is served, and `sq source pull [<name>]` turns each opted-in issue into an item whose title, description, mapped fields and comments the tracker owns, compiled into one `sq import` transaction. Sourced items and comments are authored by `source:<name>`, operators carry their tracker `identities`, and `sq check` reports broken and duplicated links (FEAT-1271 US1 to US9).

## ADR-1274 sections implemented

- §1 the `source` record, the two derived lookups, the derived cursor.
- §2 nested records and the `map` attribute kind (amends ADR-1007 §1 and §4).
- §3 identities and handle resolution.
- §5 comment attributes, sourced-comment escaping, display and the untrusted notice.
- §6 sourced authors and the reserved `source` slug (amends ADR-979 §2 and §2b).
- §7 where source commands run, the credential store, the hidden prompt (amends ADR-1261 §5).
- §8 `sources.toml`, the fourth spec document.
- §9 the connector interface (every method but the probes), the connector and converter tables, the `gitlab-md` row, the vocabulary guard, and read-time reference translation.
- §14 implementation details: the seams and the GitLab connector as the first connector, the `source` view kind, reference translation by the connector, two items under one `(name, id)`, unlink and relink, and the smaller rules.
- §10 the pull compiled to import events (amends ADR-622).
- §11 ownership refusals, retype, unlink, relink, `show --refresh`.
- §12 every `sq check` report except the paired-tag findings (done with stored view bodies).

## The first connector

ADR-1274 §14 settles it: this task owns the connector interface and both literal tables, and brings the GitLab connector forward (without its probes, which land with `sq source check`). Every pull case runs against it: recorded GitLab API responses served on a loopback port that the source's `base_url` names, so each case runs the real command, the real pull and the real HTTP path. No test-only connector row exists and no fixture patches either table. ST10 builds this, with the one shared fetch phase that every fetching command (the pull, `show --refresh`, `relink`, handle resolution) goes through, and is done first, before ST1. The source check task adds the access probes at the start of that phase, so no second fetch path is built. A disabled source is refused only by the fetching commands; a pull with no name skips it, and every command needing no tracker data works on it as on an enabled source (§14).

## Layers and expected files

- New package `src/squads/_sources/`: `_spec.py` (models and loader of `sources.toml`), `_registry.py` (connector table, `gitlab` row), `_connector.py` (the interface), `_http.py` (the shared standard-library HTTP helper), `_gitlab.py` (the GitLab connector), `_converters.py` (converter table, `gitlab-md` row), `_credentials.py` (the store), `_compile.py` (fetch result to import events). Reached only from `_services`; the shim imports none of it. New rows in `tests/meta/test_package_import_edges_match_the_recorded_table.py`.
- Spec documents: new `src/squads/_specs/sources.toml` (connector defaults, no source), `src/squads/_spec_documents.py` (lazy, memoised, like the catalog), `src/squads/_specload.py` (a `SpecDocument`), `src/squads/_overrides/` (scaffold and diff), `src/squads/_specs/workflow.toml` (`identities` on `operator`, the `source_description` view), `src/squads/_workflow/` (the `map` kind, the pin, derived-name collisions).
- Models: `src/squads/_models/_item.py` (`Item.source`), `src/squads/_models/_attributes.py` (`CORE_KEYS`, `map_attribute`), `src/squads/_models/_index.py` (derived lookups), `src/squads/_models/_participants.py` (reserved `source`), `src/squads/_models/_markers.py` (attribute line form), `src/squads/_itemfile.py`.
- Discussion: `src/squads/_discussion.py` (header grammar, attribute line, canonical text, display).
- Services: `_import.py` and `_import_model.py` (internal ops and actor), `_collab.py` (inbox, comment edit and removal), `_items.py`, `_retype.py`, `_validators.py` and `_check_rules.py` (new rules), `_base.py` (`reject_markers` widening), `_roster.py` (identity resolution on operator update), new `_sources_ops.py` (pull, list, credential, unlink, relink, refresh handlers), `_bindings.py`, `_item_read_dto.py`, `_item_dto.py`.
- API: `src/squads/_api/_ops.py` (one section for sources), new `src/squads/_api/_dto/_sources.py`, `_api/_dto/_comments.py` (comment `attributes` and derived fields).
- CLI: new `src/squads/_cli/_source.py` (`sq source pull|list|credential set|credential remove`), `_cli/__init__.py` (`LAZY_GROUPS` row), `_cli/_items.py` (`show --refresh`, `source unlink|relink` on every item type), `_cli/_field_options.py` (the derived map option), `_cli/_render/` (source list, pull report, sourced comment author).
- Shim and daemon: `src/squads/_shim.py` (`LONG_COMMANDS` rows for pull; the hidden prompt), `src/squads/_daemon/_commands.py` (the `hidden` prompt answer kept out of `output` and the digest), `src/squads/_daemon/_admission.py` (credential verbs only on the owner-only CLI listener and in process).
- Views: `src/squads/_workflow/_models.py` (`ViewSource.kind = "source"`), `src/squads/_views.py` (resolves the kind through a provider the service hands in; imports nothing from `_sources`).
- Templates: new `src/squads/_rendering/templates/views/source_description.md.j2`; regenerate the manifest.
- Guards: a new `tests/meta` module holding squad vocabulary literals out of connector modules.
- Migration: extend the open `_v0_19_to_v0_20.py` only if a pre-flight case is missing; no new bump.

## Tests (about 55 new)

Per subtask below. Fixtures: an override squad declaring one `gitlab` source with maps; recorded GitLab responses under `tests/fixtures/sources/gitlab/`, scrubbed of real tokens, hosts and personal data, served by the loopback harness; a credential store under the test's `tmp_path` reached through the platform path variables (`XDG_CONFIG_HOME`), never the developer's own. CI never reaches a network host.

## Schema

No bump here: stored view bodies carries 0.20 and its runner, which already refuses the three pre-existing conflicts. Extend that unreleased runner if the implementation finds a fourth.

## CHANGELOG

Report to the tech writer: the `gitlab` connector (base URLs, token, label filter, how notes and links arrive), `sources.toml` and its override, `sq source` and its verbs, the credential store location and permissions, `show --refresh`, `source unlink|relink`, the `map` kind and `identities`, the `source:<name>` author and the reserved `source` slug (and that more words may be reserved), comment attributes in `--json`, the untrusted notice, the new `sq check` reports, and that a pull holds the daemon's serial lock for its whole run.

## Depends on

The stored view bodies task (the pair, `set_view_body`, the 0.20 schema).

## Size

XL. Ten subtasks over one coherent surface; each is a reviewable commit. Order: ST10 first, then ST1 to ST9.

## Working rules

- Work in your own git worktree off `origin/release/0.20`.
- Gates before handback: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, the tests your diff selects (grep the names you changed across `tests/`) plus the floor (`tests/meta`, `tests/cli`, `tests/check`, `tests/daemon` for any change under `_specs/`, `_rendering/templates/`, `_cli/`, `_shim.py` or `_daemon/`), and `~/.local/bin/sq check` clean for the items you touched. The main loop runs the full suite.
- Tests follow ADR-1172: CLI surface cases with `@pytest.mark.covers(...)`, one case per behaviour plus its boundary refusals, no unit tests on internal functions, no shape tables. Each new check rule gets its `@pytest.mark.breaches(...)` case. Falsify each new test once and say so in the handback.
- Any edit under `src/squads/_rendering/templates/` runs `python scripts/gen_template_manifest.py` in the same change.
- No credential value in any output, log line, reflog entry, test golden or fixture file committed to the repository; test credentials are fake strings written by the test.
- No module-level mutable state: thread the request's spec, playbook and sources document. A new module-level table goes on the mutable-state guard's allowlist as a code constant.
- No bundled type, kind, field, status, ref-kind or view literal in code outside `_specs/` and `_migrations/`.
- Comments and docstrings: one or two sentences, present tense, no ticket IDs, release versions or history. No ticket IDs or process words in test or file names.
- CHANGELOG and adopter docs are the tech writer's: report, do not edit `CHANGELOG.md` or `docs/`.
- Use `~/.local/bin/sq` for board operations; the dev tree only through `uv run --project <repo> sq -C <scratch>` on a scratch squad under the session scratchpad.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1276 add-subtask "<title>"`; track with `sq task 1276 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sources.toml spec document and its validation

<!-- sq:subtask:ST1:body -->
`sources.toml` as the fourth `SpecDocument` (ADR-1274 §8): bundled `_specs/sources.toml` with `[connectors."<name>@<version>"]` defaults (the `gitlab` row's default converter and maps) and no source; override `squads/.overrides/sources.toml` with `[sources.<name>]` (`connector`, `version`, optional only when the connector has exactly one registered version, which the source then uses (no ordering of versions exists; with several, a source without `version` fails at load naming the source and listing the known versions, a case TASK-1278 ST1 owns because it has the two Jira rows), `base_url`, `filter`, `trusted`, `enabled`, optional `converter`, `maps.types`, `maps.fields.<field>`, `maps.links`; `""` unmaps a value). Read and merged once per invocation through `_specload.py`/`_specmerge.py`; `resolve_documents` resolves it lazily and memoised, so a broken file fails only the commands that read a source. `sq override` scaffolds and diffs it. Collect-all validation against the resolved workflow spec: each map target a declared type, badge field and value, or ref kind; the source name follows the slug grammar; `connector`, `version` and `converter` exist in their tables. An edit to the override retires the daemon like any `.overrides/` edit.

Tests (4), each on a `gitlab` source, which resolves to its only version: `sq override` scaffolds `sources.toml`; a bad map target fails a source command naming the source, the map and the value; an unknown `gitlab` version lists the known ones; a broken `sources.toml` leaves `sq list` working while `sq source list` fails (the `sq check` report is ST8's).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Source record, derived lookups, namespaced author

<!-- sq:subtask:ST2:body -->
`source` joins `CORE_KEYS` as a nested record with exactly `name`, `id`, `key`, `state`, `updated_at`, `author_id`, `author_handle`, all strings (ADR-1274 §1); a missing or extra key or a non-string value refuses the item at the load boundary and names the file (ADR-1007 §5). `SquadsDB` builds on load the derived `(name, id)` and `(name, key)` maps, both to lists of sequence ids (ADR-1274 §14), never persisted. The cursor is derived from the newest `source.updated_at`. The namespaced author (§6): `author = slug | word ":" slug` in the comment header and in item frontmatter `author`; the display name is the source name; `source` joins the reserved participant slugs and `roster_slug_valid` reports a role holding it.

Tests (3): a fixture item with a malformed `source` record is refused naming the file; `sq repair` on a corpus of sourced items rebuilds an index equal to the one before (the lookup is derived); `sq role` creation of a role named `source` is refused as reserved.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Map attribute kind and operator identities

<!-- sq:subtask:ST3:body -->
The `map` attribute kind (ADR-1274 §2): string keys to string values, stored nested under the attribute's name, an object in `--json` rows, read through `map_attribute(item, key)` (another shape reads as unset and `attribute_valid` reports it). A derived repeatable option on the update verb, `--<name> key=value` and `--<name> key=` to remove, derived in `_cli/_field_options.py`, collisions refused by `_workflow/_derived_names.py`; `--set` refuses a map attribute and names the option; `sq import`'s `update` takes `{"<name>": {"<key>": "<value>", "<key>": null}}`; a write removes only the keys it names. Identities (§3): the bundled spec declares `identities = { kind = "map" }` on `operator`, pinned by the loader with the roster minimum semantics. A value starting with `@` is a handle, resolved through the source's connector via the shared fetch phase (ST10) where the squad is served, with that side's credential, and the ID is stored; a handle that does not resolve refuses the write and stores nothing; a handle on a source with no stored credential is refused naming `sq source credential set <source>`; a handle on a disabled source is refused naming `enabled = false`, and on an undeclared source naming the declared ones (§14). Any other value is stored as given, with no credential and no network.

Tests (6): `operator <slug> update --identities src=4567` then `--identities src=` sets and removes one key, `show --json` an object; `--identities src=@handle` stores the resolved ID from a recorded GitLab response; an unresolvable handle is refused and nothing stored; a handle on a source with no credential is refused naming `sq source credential set <source>` and nothing stored; a handle on a disabled source and one on an undeclared source are refused (one case, both refusals); `--set identities=…` is refused naming the option. The two identity `sq check` rules are ST8's.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Comment attributes and sourced-comment display

<!-- sq:subtask:ST4:body -->
Comment attributes (ADR-1274 §5): one `sq:attrs` line in its HTML-comment wrapper directly after the header, indented like the bullets, holding one JSON object with sorted keys, string values, one line, `<` and `>` written as the JSON escapes `\u003c` and `\u003e`. `MARKER_RE` never matches it; `reject_markers` widens to refuse `<!--`, optional whitespace, `sq:` and a word character, keeping the documented `<!-- sq:* -->` spelling accepted. Recognised only in that position; a malformed one reads as text (reported in ST8). Excluded from ADR-1013 §1's canonical text (not a hash input), from the rendered comment body, the inbox mention scan and search; edit and removal carry it with the comment's span. Text of a `source:` comment is escaped with the stored-body grammar on write and restored on read. Display at read time: `op-pierre Pierre Chat via <source> @<handle>` when an `author_id` matches an identity of that source, else `Pierre Chat via <source> @<handle>`; `--json` discussion entries gain `attributes` and the derived `source`, `author_url`, `identity` and `trusted`. `trusted` is a boolean, `false` exactly when the notice shows: `true` for a comment no source authored, the source's flag for a sourced comment, `false` when that source is not declared. On a comment no source authored, `source`, `author_url` and `identity` are `null` (§14). The comment render translates tracker references through the connector's reference method against the host's `source.key`; a sourced comment on an item with no record renders untranslated. The untrusted notice, derived from the author and the source's `trusted`, shows on the comment and its inbox line; mentions reach the inbox.

Tests (4), on fixture items carrying sourced comments: `show --comments` and `--json` show the composed author with and without a matching identity (one case each), the `--json` case also asserting `trusted` and the `null` fields on a squad-authored comment beside it; a mention in an untrusted sourced comment reaches `sq inbox` with the notice, and declaring the source `trusted` removes it; changing only the attribute line keeps the comment hash (`comment <hash> show` still resolves); `comment -m` with a forged `<!-- sq:attrs {...} -->` line is refused.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Credential store and the hidden prompt

<!-- sq:subtask:ST5:body -->
The credential store (ADR-1274 §7): one TOML file per user of the serving process, `$XDG_CONFIG_HOME/squads/credentials.toml` else `~/.config/squads/credentials.toml` on POSIX, `~/Library/Application Support/squads/` on macOS, `%APPDATA%\squads\` on Windows. Entries keyed by the normalised base URL (scheme, host, port, path, no trailing slash), holding the fields the connector names. Read on every use, never cached across requests. POSIX: file `0600` in a `0700` directory, and a group- or other-readable file is refused naming `chmod`. `sq source credential set <source>` prompts for each field with a hidden prompt (or reads a non-terminal stdin); `sq source credential remove <source>` deletes the entry. Both work on a disabled source. No value reaches `--json`, the reflog, a log line or the squad. ADR-1261 §5: a `prompt` answer carries `hidden: true` for a `hide_input` prompt, the shim reads it without echo, and the daemon keeps it out of `output` and the prompt digest. The credential operations are admitted only on the owner-only local CLI listener and in process; no `/v1` route and no OpenAPI entry names them.

Tests (5): `credential set` from stdin writes the entry with mode `0600` and prints no value; `credential remove` deletes it; a group-readable store is refused naming `chmod`; over the daemon's CLI socket, the hidden answer is absent from `output` (tests/daemon); a credential operation arriving on a non-owner listener is refused (tests/daemon, beside the admission cases).
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — sq source pull compiled to import events

<!-- sq:subtask:ST6:body -->
`sq source pull [<name>]` (ADR-1274 §10), served and classed `long`, holding the daemon's serial lock for its whole run. Fetch outside the index lock, through the shared fetch phase (ST10): per source the incremental query since the cursor (inclusive), the listing of IDs in the filter (closed included), one fetch per linked item missing from it, and the comments and links of what changed; paginated, backing off on rate limits. Compile inside one `IndexStore.transaction()`, diffing against the items as they stand, emitting only changing events. Apply through the importer's pre-pass and apply pass as one import. New internal ops the JSONL reader refuses: `source`, `view-body` (calls `set_view_body`), `comment-edit` addressed by `{"key": "source_id", "value": …}`; `attributes` on `comment` and `comment-edit`; the internal actor `source:<name>`. Timestamps: a sourced comment's header carries the tracker creation time, every other event the pull's time. Two items under one `(name, id)`: the pull refreshes every linked item, each through its own events, and reports the duplicate on every run; an issue is new only when no item holds its `(name, id)`. A named pull of a disabled source is refused naming `enabled = false`; an unnamed pull skips it. Per-issue failures drop that issue's events and are reported; a second identical comment in the same second is skipped and reported naming both IDs; `closed`, `out-of-filter` and `gone` ("deleted or no longer readable") reported, the item stays; a deleted tracker comment reported, not removed. No name: a source without a credential is skipped with a warning; a named one errors naming `sq source credential set <name>`. Type applied at creation only. `--dry-run` stops after the pre-pass; `--json` reports per-source counts, created IDs and report lines.

Tests (9): first pull creates an item with type, title, mapped field, `source` record and `source_description` body; a second pull writes nothing (file bytes and reflog unchanged); a description holding a forged `sq:body` end tag round-trips through `show` and leaves the markers balanced (the stored-body escape case); an edited tracker comment updates the same comment in place; a linked issue absent from the listing becomes `out-of-filter` or `gone` from the one-off fetch (one case, two recorded issues); `--dry-run` writes nothing; a named source without a credential errors with the remedy; two fixture items holding one `(name, id)` are both refreshed and the duplicate reported, with no third item created; a named pull of a disabled source is refused and writes nothing.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — The source_description view and show --refresh

<!-- sq:subtask:ST7:body -->
The bundled `[views.source_description]` (ADR-1274 §4, §14; FEAT-1271 US5): `source = { kind = "source" }`, `position = "top"`, `stored = true`, no transform, seeded by no creation template (`set_view_body` places the pair). `kind = "source"` is a new `ViewSource.kind`: no `name`, valid on every type, resolved through a provider the service hands to `_views` (like the roster), so `_views` imports nothing from `_sources`. It resolves to `null` without a `source` record, else to the record's keys plus `url` (the connector's issue URL), `trusted` (the declared flag, `false` when undeclared) and `text` (the unescaped stored body with references translated); the template also gets `body`, untranslated. `templates/views/source_description.md.j2` renders `text` with the source name, the key, the URL and the age of `source.updated_at`, plus the untrusted notice unless `trusted`; with a `null` source it renders the stored body alone. Translation calls the connector's reference method (text and host key, giving spans and full keys) and replaces a span only when exactly one item holds that key; `@mentions` are left as written. `sq <type> <n> show --refresh` runs the pull's three phases for that one item where the squad is served, fetching through the shared fetch phase (ST10), then shows it; on an item with no `source` record it is refused naming the item, and nothing is fetched, written or shown; on a disabled source it is refused naming `enabled = false`.

Tests (4): `show` of a pulled item renders source, key, URL, age and the notice, and a `trusted` source drops the notice; a reference to another pulled issue renders as its item ID while `show --json` `body` keeps the raw reference; `show --refresh` picks up a changed recorded description; `show --refresh` on an unsourced item is refused and the loopback harness records no request and the file stays byte-identical.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Ownership refusals and sq check reports

<!-- sq:subtask:ST8:body -->
Ownership (ADR-1274 §11): on an item with a `source` record, writing `title`, a badge field its source maps, the stored body of `source_description`, or editing or removing a `source:<name>` comment is refused, naming the source, the issue key and `source unlink`. `--as source:<name>` is refused on every command, `sq import`'s `as` included. Retype works and keeps the record; a later pull skips and reports a mapped field the new type lacks. `sq check` (§12), never calling the network: two items sharing one `(source, id)`; a `source:<name>` author on an item or a comment naming no declared source; an item whose source is undeclared or disabled; `source.state` `out-of-filter` or `gone`; an identity key naming no declared source; two operators holding one ID on one source; a malformed comment-attribute line; a `sources.toml` that does not load. The pull reports the same broken links it finds.

Tests (12): one refusal case covering `title` and a mapped field (`update`), one for a sourced comment `edit`; `--as source:x` refused; retype of a sourced item keeps `source` in `show --json`; one `breaches` case per new check rule (8).
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Source list, unlink and relink

<!-- sq:subtask:ST9:body -->
`sq source list` (ADR-1274 §7, FEAT-1271 US7): each source with connector and version, enabled or not, whether a credential entry exists (never its value), its item count and the newest `updated_at` among its items; `--json`. `sq <type> <n> source unlink` (ADR-1274 §11, §14): removes the `source` record and turns the stored description into plain body prose at the pair's position, escaped openers left escaped; the item's `author` stays `source:<name>` and the imported comments stay authored by it, so they can no longer be edited or removed; unlink on an item with no record is refused, and unlink works on a disabled source (it fetches nothing). `sq <type> <n> source relink <source> <issue>`: accepted only on an item with no `source` record whose `author` is `source:<source>`; refused, naming why, on an item that still holds a record (naming `source unlink`), on an item no source created, on another source's item (naming it), for an issue whose `(name, id)` another item holds (naming that item), and on a disabled source. `<issue>` is a key or an immutable ID, resolved through the connector via the shared fetch phase (ST10) where the squad is served; relink then runs the pull's three phases for that one issue in one transaction, writing the record, title, mapped fields, description view and comments (matched by `source_id`). The prose unlink left stays the squad's; the type is not changed.

Tests (4): `source list --json` on a squad with one credentialed and one uncredentialed source; `unlink` leaves the description as body prose, `show --json` without `source` and the author still `source:<name>`; `relink` restores the record and the view in one command while keeping the body prose; the relink refusals (item still holding a record, item no source created, another source's item, issue held by another item) in one case.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — HTTP helper, loopback harness, GitLab connector

<!-- sq:subtask:ST10:body -->
Done first, before ST1 (ADR-1274 §9, §14). The shared HTTP helper `_sources/_http.py` over `urllib.request`: pagination, backoff on rate limits (429 and the tracker's rate headers), timeouts, no third-party dependency. The shared fetch phase (ADR-1274 §10 phase 1, §14): one function, in `_services`, that every fetching command calls — the pull (ST6), `show --refresh` (ST7), `relink` (ST9) and handle resolution (ST3) — and that refuses a disabled source naming `enabled = false`; the source check task adds the access probes at its start. The loopback recorded-response harness in `tests/`: serves recorded API responses on a loopback port that the source's `base_url` names. The GitLab connector `_sources/_gitlab.py` (API v4, gitlab.com and a self-hosted base URL, personal or project token) implementing every interface method except the probes: issues changed since a cursor (inclusive), IDs matching the label filter (closed included), one issue by ID, notes as comments (system notes excluded), related and blocking links, issue and user URLs, handle to immutable user ID, and the reference method (text and host key in, spans and full keys out, `#12` and `project#12` qualified against the host key; pure, no network). Type and field maps read labels, scoped labels included. Immutable ID: the issue's global ID; a moved issue keeps its item. The `gitlab` row in the connector table and the `gitlab-md` row in the converter table (relative upload and image links made absolute; nothing downloaded). The `tests/meta` vocabulary guard: no squad vocabulary literal (item type, badge field or value, ref kind or status the bundled spec declares) in a connector module; tracker API names allowed.

Tests (4): a pull from recorded responses creates items with comments (system notes absent) and a `blocks` link mapped to a ref; a recorded move updates `source.key` on the same item; a description with relative upload and image links renders them absolute through `gitlab-md`; the vocabulary guard, falsified once by planting a bundled type name in the connector.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-03T23:11:23Z] `architect` Robert Architect:
  - - @tech-lead ADR-1274 §14 (2026-11-04) settles this task's open point and changes its scope:
      - Open point settled: this task owns the connector interface (every §9 method except the probe method) and both literal tables. Its tests pull from the **GitLab connector**, brought forward. No test-only row, and no fixture patches a table.
      - Add a first subtask, before ST1: the shared HTTP helper (`_sources/_http.py`), the loopback recorded-response harness, the GitLab connector without probes, the `gitlab-md` converter row with its recorded sample case, and the `tests/meta` vocabulary guard. Take over TASK-1278 ST2's pull and move tests and ST1's guard test. ST1's validation cases then name `gitlab`.
      - ST3: add a case where `--identities src=@handle` on a source with no credential is refused, naming `sq source credential set <source>`, and nothing is stored. A handle on a disabled or undeclared source is refused too.
      - ST4: `trusted` in `--json` is a boolean, `false` exactly when the notice shows (`true` for a comment no source authored, `false` for an undeclared source); `source`, `author_url` and `identity` are `null` on a comment no source authored.
      - ST6: the pull refreshes every item under one `(name, id)` and reports the duplicate on each run; an issue is new only when no item holds it. Both lookups map to lists. A named pull of a disabled source is refused.
      - ST7: the view is `source = { kind = "source" }`, `position = "top"`, `stored = true`, no transform, not seeded. That is a new `ViewSource.kind`: no `name`, every type, resolved through a provider the service hands to `_views` (`_views` imports nothing from `_sources`). It resolves to `null` without a record, else to the record plus `url`, `trusted` and `text` (translated). Translation calls the connector's reference method (text and host key, giving spans and full keys) and replaces a span only when exactly one item holds the key. Add a case: `show --refresh` on an unsourced item is refused, and nothing is fetched or written.
      - ST9: `relink` is accepted only on an item with no record whose `author` is `source:<source>`. It is refused on an item that still holds a record (naming `source unlink`), on an item no source created, on another source's item, and for an issue another item holds. It runs the three pull phases for that issue at once, writing the record, title, fields, view and comments. `unlink` keeps the `source:<name>` author on the item and its comments. Replace the "relink then pull" case with "relink restores record and view in one command, keeping the body prose", and add one case for the refusals.
- [2026-11-03T23:15:37Z] `tech-lead` Olivia Lead:
  - Scope updated to ADR-1274 §14 per @architect's comment: body and subtasks revised; see the subtask table for what moved.
- [2026-11-03T23:17:26Z] `architect` Robert Architect:
  - - @tech-lead ADR-1274 §14 (2026-11-04), three more rules for this task:
      - ST1: `version` is optional only when the connector has exactly one registered version. With several, a source without `version` fails at load, naming the source and listing the known versions. No ordering and no "newest" exist. Replace "defaulting to the newest registered" in the ST1 text. The `gitlab` cases resolve to its only version. The several-version refusal case belongs to TASK-1278 ST1, which has the two Jira rows.
      - ST6, ST7, ST9, ST3: the pull, `show --refresh`, `relink` and handle resolution go through one shared fetch phase. TASK-1277 adds the access probes at its start, so build no second fetch path.
      - ST9 and ST5: `source unlink` and `sq source credential set` and `remove` work on a disabled source. Only fetching commands refuse it, and a pull with no name skips it.
<!-- sq:discussion:end -->
