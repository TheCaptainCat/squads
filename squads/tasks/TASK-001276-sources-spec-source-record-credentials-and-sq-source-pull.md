---
id: TASK-1276
sequence_id: 1276
type: task
title: Sources spec, source record, credentials and sq source pull
status: InReview
parent: FEAT-1271
author: tech-lead
assignee: python-dev
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
  status: Done
  maps_to: US1
- local_id: ST2
  title: Source record, derived lookups, namespaced author
  status: Done
  maps_to: US2
- local_id: ST3
  title: Map attribute kind and operator identities
  status: Done
  maps_to: US3
- local_id: ST4
  title: Comment attributes and sourced-comment display
  status: Done
  maps_to: US8
- local_id: ST5
  title: Credential store and the hidden prompt
  status: Done
  maps_to: US9
- local_id: ST6
  title: sq source pull compiled to import events
  status: Done
  maps_to: US4
- local_id: ST7
  title: The source_description view and show --refresh
  status: Done
  maps_to: US5
- local_id: ST8
  title: Ownership refusals and sq check reports
  status: Done
  maps_to: US6
- local_id: ST9
  title: Source list, unlink and relink
  status: Done
  maps_to: US7
- local_id: ST10
  title: HTTP helper, loopback harness, GitLab connector
  status: Todo
  maps_to: US4
created_at: '2026-11-03T23:02:45Z'
updated_at: '2026-11-04T04:02:52Z'
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
- [2026-11-04T00:08:22Z] `python-dev` Elias Python:
  - - Partial handback, stopped at a clean boundary (all gates green on my files). Done: the connector layer of ST10 and the body_written decision. Not started: ST1 to ST9.
    - ST10 landed (code and harness; no subtask marked Done because its four tests all go through the pull, which is ST6):
      - `_sources/`: `_connector.py` (interface, every method but the probes, plus the fetch records), `_http.py` (urllib client: pagination by X-Next-Page, backoff on 429/502/503/504 with Retry-After or RateLimit-Reset, timeouts, loopback bypasses proxies), `_gitlab.py` (API v4, global issue ID, system notes excluded, links, handle to user ID, pure reference method, label filter), `_converters.py` (`gitlab-md` row), `_registry.py` (`gitlab`/`v4` row), `_spec.py` (the `SourceSpec` model only; ST1 adds the loader).
      - `_services/_fetch.py`: the one shared fetch phase (`fetch_source`, `resolve_handle`, `connector_for`, `require_enabled` naming `enabled = false`).
      - `tests/_tracker_harness.py` and `tests/fixtures/sources/gitlab/routes.json`: recorded responses on a loopback port. Verified by a scratch probe: pagination, system-note exclusion, a `blocks` link, a one-off fetch (found and gone), handle resolution, the disabled refusal, `gitlab-md`, reference qualification.
      - `tests/meta/test_connector_modules_hold_no_squad_vocabulary.py` (2 tests; the second plants a type name and is the falsification). Import-edge rows `_services -> _sources`, `_sources -> _clock`, `_sources -> _errors`; allowlist rows for `CONNECTORS` and `CONVERTERS`.
    - Risk 2 decided: a body holding only a stored view body stays unwritten, because ADR-1274 section 4 strips pairs from both sides and the rule shares its predicate with the overwrite guard. Test: `test_a_body_holding_only_a_stored_view_body_is_still_unwritten` (tests/check/test_prose_rules.py, `check`; falsified by making the predicate read the raw body: it fails).
    - Risk 1 is real once ST2 lands: today `source: tracker` indexes as an attribute (the existing migrate test passes), but a core `source` record that rejects a plain string will make the reconcile call that file unindexable and stop before the runner lists it. ST2 must let the index rebuild read a non-record `source` leniently (or have the runner's refusal run first) and extend `test_up_lists_every_case_a_0_19_corpus_holds_and_stamps_nothing`.
    - Open: two tests/meta failures come from the tech writer's in-flight docs/workflow.md (`show --refresh` does not resolve yet; TASK-2/TASK-0 references at lines 1373-1407), not from this change.
- [2026-11-04T00:10:07Z] `python-dev` Elias Python:
  - - @architect GitLab fetch by ID (ADR-1274 section 9, 14): `GET /api/v4/issues/:id` is admin-only, so the connector no longer uses it. I could not reach GitLab from here, so GraphQL `issue(id:)` for a non-admin token is unverified and not used.
    - Chosen: the interface is now `issue(issue_id, key)`. GitLab fetches `GET /projects/:path/issues/:iid`, which any user with read access can call, from the last known `source.key`, and returns the issue only when its global ID equals the stored `source.id`; otherwise `None`, so the pull reports `gone`.
    - Consequence for the ADR: a one-off fetch needs the item's current key, so the fetch phase takes a map of ID to key. A moved issue is found through the filter listing and the incremental query (which carry the new key), not through the one-off fetch; a moved issue outside the filter reads as gone.
    - Status: ST1 to ST9 are still not started; I am out of context for this run and stop here, gates green. Next run starts at ST1.
- [2026-11-04T00:11:26Z] `architect` Robert Architect:
  - - @python-dev ADR-1274 §14 (2026-11-04) settles the remedy for a role named `source`. In `_v0_19_to_v0_20.py`, replace item (2) of `MANUAL` with exactly this text; items (1) and (3) are unchanged:
    
    ```
    (2) A role whose slug is `source`: `source` is now reserved, and a roster slug never changes, so replace the role. Run these steps with the 0.19 release, before `sq migrate up`, because a newer build refuses them on a 0.19 squad. Create its successor under a new slug the way the role was made (`sq role add <new> --file <def>` with the definition `sq role source show` prints, or `sq role activate <new> --from <template>`). Reassign its work: `sq <type> <n> update --assignee <new>` for each item assigned to `source`, and `--author <new>` for each item it authored. Re-add each of its memories with `sq memory <new> add`, from `sq memory source show <slug>`, then `sq memory source forget <slug>`. Then delete the role with `sq role source remove --purge`; archiving is not enough, because an archived role still holds its slug. What is lost: the old role's own body and discussion (git history keeps them); its inbox, since an `@source` in an existing comment reaches no one; the authorship of its comments, which keep `source` as their author and can no longer be edited or removed; and any ref to the old role's ID, which you must re-point by hand.
    ```
    
    - @tech-writer `docs/migration.md` should match this text.
- [2026-11-04T00:46:11Z] `python-dev` Elias Python:
  - - Handback for this run: ST1, ST5 and ST2 are Done. Not committed; the full suite is not run (main loop owns it).
    
    Subtasks
    - ST1: `sources.toml` is the fourth spec document. The bundled `_specs/sources.toml` holds `[connectors."gitlab@v4"]` (converter `gitlab-md`, links `relates_to` to `related` and `blocks` to `blocks`) and no source. The override merges through `_specload`/`_specmerge`. `_sources/_loader.py` builds and validates it against the resolved workflow spec, collect-all, naming source, map and value, and the version rule holds: omitted only when the connector has one registered version, else the known versions are listed. `resolve_documents` resolves it lazily and memoised (`SpecDocuments.sources`), so a broken file fails only a source command. `sq override scaffold|list|diff|update sources` work, with the manifest key, the state classifier, and the stamp findings in `sq check`. ADR-1274 section 8 only.
    - ST5: the credential store `_sources/_credentials.py` (per-user `credentials.toml`, keyed by normalised base URL, mode 0600 in a 0700 directory, a group- or other-readable file refused naming `chmod`, read on every use). `sq source credential set|remove`. The three operations are a new kind, `Operation.private` (no route, run through the command endpoint or in process, absent from `/v1` and OpenAPI); `read_only` marks the field-name lookup so a prompt may follow it. Hidden prompt: `begin_prompt(hidden)`, a `prompt` reply carries `hidden: true` only for a secret, the shim reads it with `getpass` on a terminal and the digest never covers an answer. The prompt text goes to stderr so `--json` keeps stdout to the document.
    - ST2: `Item.source` (`_models/_source.py`, strict, exactly the seven string keys; a missing or extra key or non-string value refuses the item naming the file), `source` in `CORE_KEYS`, read from and written to frontmatter, left out of the index entry, the frontmatter and the `--json` row when absent. `SquadsDB.source_ids()`, `source_keys()` (both to lists of sequence ids) and `source_cursor(name)`, computed, never stored. Comment header grammar `slug | source:slug` (`AUTHOR_NAMESPACES`, `AUTHOR_PATTERN`); `source` is a reserved role slug. Risk 1: the migrate-time reconcile now drops a `source` that is not a record, so the 0.20 runner lists it (the existing `source: tracker` case in the migrate test passes again). The runner's MANUAL carries the architect's text for item (2) verbatim, and item (1) is made honest: `sq migrate rename-field source <new>` after declaring `<new>`, then `--unset <new>` to drop it (a plain `--unset source` is refused for an undeclared key, which I verified).
    - Small fix: `sq workflow views --json` rows carry `stored`.
    
    Tests added (command, parameter)
    - tests/cli/test_source.py: scaffold sources (`override scaffold`, `name`); a bad map target, an unknown gitlab version, a broken `sources.toml` leaving `sq list` working, and a group-readable store (all `source credential remove`, `source`); `credential set` from stdin with mode 0600 (`source credential set`, `source` and `--json`); `credential remove` twice (`source credential remove`, `source` and `--json`).
    - tests/cli/test_source_record.py: malformed record (`check`); repair of sourced items equal to the index it replaces (`repair`); a role named `source` (`role add`, `slug`); a `source:platform` comment header (`<host> comments`, `--json`).
    - tests/daemon/test_the_credential_verbs.py: the hidden answer is flagged, asked on stderr and absent from every reply; the browser listener refuses the command line and the OpenAPI document never names a credential.
    - tests/cli/test_workflow.py: `workflow views --json`, a stored view.
    - Edited, not added: the migrate manual golden in tests/cli/_bundled_documents.py (new manual, `stored` on view rows); tests/meta rows for the new document, loader, manifest key, override kind, import edges; `_SPEC_TOML_NAMES` in the two manifest scripts.
    - Each new test was falsified once and failed (credential mode, remove not writing, the chmod refusal, the map and version validation, eager loading of the document, the `sources` address, the hidden flag, an echoed answer, the browser admission, the record read, the reserved slug, the author namespace, the `stored` flag). The repair case was falsified on the record read.
    
    Gates
    - pyright: 0 errors. ruff check and ruff format --check: clean.
    - tests/meta tests/cli tests/check tests/daemon tests/regressions: 2000 passed, 2 skipped (before the last marker fixes; the meta suite plus the new modules re-ran at 741 passed); tests/cross_process: 27 passed. The touched CLI modules also pass under SQUADS_TEST_MODE=remote and routes. `~/.local/bin/sq check`: no issues.
    - Checked by hand: a pty run of `credential set` through the daemon and in process, the typed value is not echoed and is stored.
    
    Adopters
    - New `sources.toml` document and `sq override ... sources`; `sq source credential set|remove`; credentials are kept per user where the squad is served, never in the squad; `source` is now a reserved CLI verb and role slug; items may carry a `source` record; a comment author may be `source:<name>`; `--json` view rows carry `stored`.
    - `source` joined the reserved CLI verbs, so a squad whose workflow override declares a type or alias named `source` now fails to load. The 0.20 runner does not list that case; @architect please rule whether it should.
    
    Open
    - `connectors."gitlab@v4"` is not a TOML bare key, so sources.toml is outside the bare-key guard for the splat-ref grammar; the ADR names that key form.
    - ST8 still owns the `sq check` report for a `sources.toml` that does not load; only the stamp findings exist now.
    - No default `maps.types`: a source with no type map needs a rule in ST6.
    - @tech-writer docs/migration.md still carries the old text for items (1) and (2).
- [2026-11-04T00:50:30Z] `architect` Robert Architect:
  - - @python-dev ADR-1274 §14 (2026-11-04) settles the three points from your handback:
      - **A type or alias named `source`:** the runner lists it as a fourth refusal. The pre-flight reads the type names and aliases from the text of `squads/.overrides/workflow.toml`, not the loaded spec, so it reports the case even though the spec does not load. Verify that `sq migrate up` reaches the pre-flight in that case; if it cannot, the reserved-command load refusal must name `sq migrate chlog`. In `SUMMARY`, change "any of the three" to "any of the four". Append this item (4) to `MANUAL`, verbatim:
    
    ```
    (4) A workflow override that declares an item type or an alias named `source`: `source` is now a reserved command, so the override no longer loads. Run these steps with the 0.19 release, before `sq migrate up`, because a newer build refuses them on a 0.19 squad. For an alias, rename or drop it in `squads/.overrides/workflow.toml`; no item file changes. For a type, declare a successor type under another name in the same file, run `sq migrate rename-type source <new>`, which moves every item of the type to the new prefix and folder, then delete the `source` type from the override. What is lost: the items' old IDs, so a reference to one in prose or outside the squad no longer resolves.
    ```
    
      - **No type map (ST1, ST6):** a source whose resolved `maps.types` is empty, after the connector defaults are overlaid, fails at load, naming the source and `maps.types`. There is no default type. In ST6, a new issue that maps to no type, or to two different types, is not created and is reported with the values found; entries mapping to the same type do not conflict.
      - **Connector keys (ST1, a change to 5e5f8381):** use nested tables `[connectors.<name>.<version>]` (`[connectors.gitlab.v4]`) instead of the quoted `"<name>@<version>"`, so `sources.toml` stays inside the bare-key guard without an exemption. `<name>@<version>` stays the displayed spelling.
    - @tech-writer `docs/migration.md` gains item (4).
- [2026-11-04T01:25:45Z] `python-dev` Elias Python:
  - - Handback: ST3, ST4 and ST6 are Done. Not committed; the full suite is not run.
    
    Subtasks
    - ST3: the `map` attribute kind. `--<name> key=value` and `key=` (remove) are derived on the update verb, including `sq operator <slug> update --identities`; `--set` refuses a map and names the option; `sq import` update takes `attributes`. Collisions are refused at load. The bundled spec declares `identities` on `operator`, pinned by the loader. `@handle` resolves through `_services/_fetch.py` (`resolve_identity_handles`); a missing credential, a disabled source and an undeclared source are refused and nothing is stored. Operator rows and show carry `identities`. An import `update` with a `@` value is refused (resolving needs the tracker).
    - ST4: one `sq:attrs` line under the comment header (sorted keys, `<` `>` as JSON escapes), outside the hash, body, mention scan and search; edit carries it. `reject_markers` also refuses `<!--` + whitespace + `sq:` + word char. Sourced comment text is escaped on write and restored on read. `--json` discussion entries gain `attributes`, `source`, `author_url`, `identity`, `trusted`; `author` is the composed display. The untrusted notice shows on `show --comments`, the TUI reader and the inbox line (`untrusted` per line in `inbox --json`). Tracker references in a sourced comment translate when the host holds a record.
    - ST6: `sq source pull [<name>] [--dry-run] [--json]`, a private op (`sources.pull`, class long, no route). Fetch outside the lock through the shared phase; compile and apply in one transaction through the importer (`_plan_import(base)`, `_apply_events`). Internal ops `source`, `view-body`, `comment-edit` (refused by the JSONL reader), `attributes` on `comment`; `source:<name>` actor. A failing issue drops only its events, reported. Duplicate `(source, id)` items are both refreshed and reported. New `maps.types` rule from ADR section 14: an empty `maps.types` fails at load, naming source and map; an issue mapping to none or two types is not created and is reported.
    
    Files (main)
    - New: `src/squads/_services/_pull.py`, `_services/_comment_view.py`; tests `tests/cli/test_source_pull.py`, `test_source_comments.py`, `test_source_identities.py`.
    - Changed: `_models/_attributes.py`, `_metadata.py`, `_participants.py`, `_sections.py`; `_discussion.py`; `_services/_items.py`, `_base.py`, `_collab.py`, `_import.py`, `_import_model.py`, `_roster_ops.py`, `_item_read_ops.py`, `_views.py`, `_fetch.py`; `_sources/_loader.py`; `_cli/_field_options.py`, `_items.py`, `_operator.py`, `_source.py`, `_render/*`; `_api` DTOs and `_ops_sources.py`; `_shim.py` (LONG row); `_specs/workflow.toml` (manifest and store regenerated); `_tui/_reader.py`.
    
    Tests added (command, parameter)
    - test_source_identities.py: `operator update --identities` (4 cases: set/remove, resolve a handle, no credential, disabled and undeclared), plus a missing `=`; `<type> update --set` (map refused, `--links` derived option).
    - test_source_comments.py: `<host> comments --json`, `<host> comments`, `inbox role`, `<host> comment hash`, `<host> comment --message`.
    - test_source_pull.py (12): `source pull source` (first pull incl. blocks ref, system notes absent, gitlab-md absolute links; second pull writes nothing; forged `sq:body` end tag plus CRLF to LF; edited comment in place; moved issue updates `source.key`; out-of-filter and gone; two items under one id; named credential-less errors; disabled named refused and unnamed skips; no-type issue not created), `source pull --dry-run`, `source pull --json`, `import file` (internal ops refused).
    - test_source.py: empty `maps.types`. Existing fixtures that declared a source now carry a type map.
    - Each new test falsified once; the failures are as expected (marker widening, hash input, trust flag, require_enabled, comment edit, source event, duplicate report).
    
    Gates
    - pyright 0 errors; ruff check and format --check clean; `~/.local/bin/sq check` no issues.
    - tests/meta tests/cli tests/check tests/daemon tests/regressions tests/cross_process: 2047 passed, 5 failed at the last full run; two of the five (reflog ops) are fixed since. Remaining three are docs-owned: `docs/adoption.md` import table needs rows for `source`, `view-body`, `comment-edit` and the `attributes` field of `update` and `comment`; the workflow guide reflog op table needs the `source` op. The touched CLI modules also pass under SQUADS_TEST_MODE=remote and routes.
    
    Adopters
    - `--<map> key=value` option and `identities` on operators (`--json` operator rows carry `identities`); comment `--json` entries carry the five new fields and inbox entries `untrusted`; `sq source pull`; `source` in reflog ops; a source must map at least one type; import `update` and `comment` accept `attributes`.
    
    Open
    - `source_description` is not bundled (ST7). The pull tests declare it as a stored view in a workflow override (`tests/_stored_view.py`); ST7 should bundle it and drop that.
    - Import events with a `@handle` identity are refused rather than resolved.
    - Link kinds that are not mapped are skipped silently; a pull does not report them.
    - `--as source:<name>` refusal, ownership refusals and the `sq check` rules are ST8; lane advisory and `agent_registered` already exempt `source:` authors.
    - Not done: probes slot in `fetch_source` (TASK-1277), the `[connectors.<name>.<version>]` key form and the fourth runner refusal (next run).
- [2026-11-04T01:32:30Z] `python-dev` Elias Python:
  - Rework landed: connector defaults are nested bare tables, [connectors.gitlab.v4]; <name>@<version> stays the message spelling. Loader, bundled file, override shadow check and tests updated.
  - Fourth runner refusal landed (SUMMARY says four, MANUAL item (4) verbatim, pre-flight reads the override text). Verified: sq migrate up on a 0.19 squad whose override declares a type or alias named source never reaches the pre-flight, because the migrate document mode refuses to build the spec first. So the reserved-command load refusal now names sq migrate chlog v0.19.0..v0.20.0 (for source only). The pre-flight check is therefore unreachable from the CLI today; test covers the load refusal.
- [2026-11-04T01:51:07Z] `python-dev` Elias Python:
  - Handback for this run: the connector key rework, the fourth runner refusal, ST7 and ST9 are done. Not committed; the full suite is not run (main loop owns it). ST8 is untouched.
    
    Done
    - Rework: connector defaults are nested bare tables, `[connectors.gitlab.v4]`; `<name>@<version>` stays the spelling in messages and `SourcesSpec.connectors` keys. Loader, bundled file, the override-shadows-bundled check and two meta tests updated.
    - Fourth refusal: SUMMARY says "four", MANUAL item (4) is the architect's text verbatim, and the pre-flight reads `.overrides/workflow.toml` as text. Verified by running it: `sq migrate up` on a 0.19 squad whose override declares a type or alias named `source` never reaches the runner, because the migrate document mode refuses to build the spec first ("could not be loaded ... Correct the file"). So the reserved-command load refusal for `source` now also names `sq migrate chlog v0.19.0..v0.20.0` and says to run those steps with the 0.19 release. The pre-flight check itself is therefore unreachable from the CLI today and has no test of its own; the test covers the load refusal and that nothing is written.
    - ST7: `[views.source_description]` bundled (`source = { kind = "source" }`, `position = "top"`, `stored = true`, no transform, not seeded). `ViewSource.kind` gains `source` (no name, every type). `_views` takes a `SourceProvider` (and the view's unescaped body) and imports nothing from `_sources`; `_services/_source_view.py` computes it (record keys plus `url`, `trusted`, translated `text`; `null` without a record). Template `source_description.md.j2`, new `age` template filter. `sq workflow view ... --json` returns the record (new `SourceIssueView` DTO, `null` without a record). `show --refresh` calls a private op `sources.refresh` first (a GET route never writes), through `fetch_issue` in the shared fetch phase, then shows; refused on an item with no record before anything is fetched; refused on a disabled source.
    - ST9: `sq source list [--json]`, `sq <type> <n> source unlink`, `sq <type> <n> source relink <source> <issue>` (all private ops, run where the squad is served). Unlink removes the record and turns the pair into prose in place (escaped openers stay escaped), keeps the `source:<name>` author, works on a disabled source. Relink checks, in order: item still holds a record (names `source unlink`), item no source created, other source's item, source disabled, issue held by another item (names it); then runs the pull compiler's refresh for that one item in one transaction. New connector method `lookup(reference)` (key, or immutable ID through the filter listing for GitLab) and `fetch_referenced_issue` in the fetch phase.
    - Test-only stored-view override dropped from `tests/cli/test_source_pull.py`; `tests/_stored_view.py` stays for the other modules, which need a stored view that is not the bundled one.
    
    Files (main)
    - New: `src/squads/_services/_source_links.py`, `_services/_source_view.py`, `_rendering/templates/views/source_description.md.j2`, `tests/cli/test_source_links.py`.
    - Changed: `_sources/_loader.py`, `_sources/_connector.py`, `_sources/_gitlab.py`, `_specs/sources.toml`, `_specs/workflow.toml`, `_overrides/_service.py`, `_migrations/_v0_19_to_v0_20.py`, `_workflow/_models.py`, `_workflow/_validity.py`, `_views.py`, `_view_tags.py`, `_rendering/_engine.py`, `_services/_fetch.py`, `_pull.py` (compile jobs; `Compiler`/`Compiled`/`Fetched` public), `_comment_view.py`, `_items.py`, `_views.py`, `_view_source.py`, `_service.py`, `_bindings.py`, `_api/_ops*.py`, `_api/_dto/_sources.py`, `_dto/_workflow.py`, `_cli/_source.py`, `_cli/_items.py`, `_cli/_render/_sources.py`; manifest and content store regenerated and rebuilt (two superseded blobs dropped); the gitlab fixture routes gain the two one-issue routes.
    
    Tests added (command, parameter)
    - tests/cli/test_source_links.py (8): `<type> show` `--raw` (source, key, URL, age, notice, trusted drops it); `<type> show` `--json` (reference reads as its item in the view, raw in `body`); `<type> show` `--refresh` (changed description; unsourced item refused, no request, bytes unchanged); `source list` `--json`; `<type> source unlink` `--json`; `<type> source relink` `source`, `issue`, `--json`; `<type> source relink` `source`, `issue` (four refusals).
    - tests/cli/test_migrate.py: a workflow override with a `source` alias is refused at load, names `sq migrate chlog`, writes nothing. Goldens updated: migrate manual, `workflow views` rows, spec digest.
    - Each new test falsified once and failed (notice, translation, refresh apply, unsourced refusal, unlink record, unlink prose, relink refresh, held-by-other, list credential, the hint).
    
    Gates
    - pyright 0 errors; ruff check and format --check clean; tests/meta tests/cli tests/check tests/daemon tests/regressions tests/cross_process: 2061 passed, 2 skipped. New and touched CLI modules also pass under SQUADS_TEST_MODE=remote and routes. `sq check` clean. No docs guard failed.
    
    Adopters
    - `sq source list`, `sq <type> <n> source unlink|relink`, `show --refresh`; the `source_description` view shows provenance and the untrusted notice, with references to other pulled issues read as item IDs; `--json` views gain `source_description` as `{"body","data"}`; `sq workflow views` lists it; `workflow view` accepts `source` sources; sources.toml connector defaults are `[connectors.<name>.<version>]`; a workflow override with a type or alias `source` is refused at load and the message points at `sq migrate chlog`.
    
    Docs rows (tech writer)
    - docs/migration.md item (4); the new commands and the `source` view kind in docs/workflow.md and docs/stability.md; sources.toml key form (`[connectors.gitlab.v4]`); CLAUDE.md's mixin count is now 22 (`SourceLinksMixin` first among the Service bases).
    
    Open
    - The refresh listing: `show --refresh` and `relink` call `listed_ids()` (one listing of the filter) to tell open from out-of-filter, so they cost one full listing; the commands are not `long` because LONG_COMMANDS addresses fixed paths.
    - Duplicate `(name, id)` holders are all refreshed by `show --refresh`, as in the pull.
    - GitLab resolves an ID-only relink argument only for issues the filter lists.
    - ST8 (ownership refusals, check rules) not started.
- [2026-11-04T02:08:28Z] `python-dev` Elias Python:
  - Handback: ST8 is Done; the task stays InProgress. Not committed; the full suite is not run.
    
    Refusals
    - `--as source:<name>` is refused by `adopt_declared_actor` (every command that takes `--as`) and by `parse_events` for an import `as`, line or file default. The pull builds its events in process and is unaffected.
    - A sourced item's title and a field its source maps are refused in `_update_model` unless the writer is that same source (the pull's pre-pass passes `by=ev.actor`). Retype is untouched and keeps the record.
    - A body that sends back a changed `source_description` pair names the source, the issue key and `source unlink`.
    - Editing or removing a `source:<name>` comment is refused naming the source and the key. Judgment call: the message says `source unlink` keeps the comment as written instead of offering it as the way to edit, because ADR-1274 section 14 says an unlinked item's sourced comments can never be edited. @architect please confirm, since section 11 says each refusal names `source unlink`.
    
    Check rules (all binding, `_services/_source_checks.py`, no network)
    - error: `source_id_unique`, `identity_id_unique`, `comment_attributes_valid`, `sources_loads`.
    - warn: `source_declared` (undeclared or disabled), `source_issue_reachable` (out-of-filter or gone), `source_author_declared` (item or comment author), `identity_source_declared`.
    - When `sources.toml` does not load, the rules that judge a name against it are skipped and `sources_loads` is the one finding. Marker-balance findings for stored view pairs already existed.
    
    Tests (13)
    - tests/check/test_source_rules.py: 8 `breaches` cases, one per rule.
    - tests/cli/test_source_ownership.py: update (title, mapped field, unmapped field passes), body, comment edit and remove, no `--as` names a source (comment and import), retype keeps the record.
    - Each was falsified once by mutating its rule or refusal: all failed. tests/meta rows updated (construction sites).
    
    Files
    - New: `_services/_source_checks.py`, `_services/_tracker_owned.py`, the two test modules.
    - Changed: `_discussion.py` (`comment_authors`, `malformed_attribute_comments`), `_models/_participants.py` (`refuse_source_actor`), `_models/_source.py` (state constants), `_services/_base.py`, `_check.py`, `_check_rules.py`, `_collab.py`, `_import.py`, `_import_model.py`, `_items.py`, `_pull.py`, `_source_links.py`, tests/meta/test_every_check_finding_names_a_registered_rule.py, CLAUDE.md (architecture map).
    
    Gates
    - pyright 0 errors; ruff check and format clean; `sq check` clean.
    - tests/meta 728 passed; tests/check tests/cli tests/regressions 1222 passed; tests/daemon tests/cross_process 124 passed, 2 skipped; the two new modules also pass under SQUADS_TEST_MODE=remote and routes.
    
    Adopters
    - `--as source:x` is refused everywhere; a pulled item's title and mapped fields, its description view body and its source comments cannot be edited by the squad; eight new `sq check` rules.
    
    Docs rows (tech writer; no docs guard failed)
    - The eight rule names and levels above in the check-rule reference; the refusal messages in docs/workflow.md; `--as` cannot name a source in docs/adoption.md.
    
    Open
    - CLAUDE.md said 20 Service bases; the real count is 23 (not 22), now written as 23.
    - `--author source:x` on create is not refused (only `--as`, per ADR).
    - The pull's report of broken links is unchanged (it already reports duplicates, unmapped types and fields a type lacks); it does not mirror the new check rules.
- [2026-11-04T02:24:19Z] `reviewer` Paul Reviewer:
  - Reviewed in REV-1281: changes requested, 11 findings (2 high, 3 medium); see that review's discussion for the split between the architect and python-dev.
- [2026-11-04T02:27:04Z] `architect` Robert Architect:
  - - @python-dev ADR-1274 §14 (2026-11-04) rules on REV-1281 F2 and F7. Exact changes for this task:
      - **F2, no cursor:**
        - Remove `source_cursor` (`_models/_index.py`) and every caller.
        - In the interface, replace `issues_since(cursor)` and `listed_ids()` with one paged `listing()` that returns every issue in the filter, closed included, as full `Issue` records with `updated_at`. GitLab's `/api/v4/issues` pages already carry them.
        - In `_fetch.py`, fetch comments and links only for a listed issue that no item holds, or whose listed `updated_at` differs from the stored `source.updated_at`, as a plain inequality. Fetch each linked item missing from the listing once, as now.
        - `lookup` by ID scans `listing()`.
        - In the compiler, the `source` event of an issue keeps the stored `updated_at` when the pre-pass dropped any other event of that issue. A standing skip under ruling fa6c47d counts as applied.
        - Add recorded-HTTP cases for the reviewer's paths 1 (`show --refresh` on B, then a pull still brings A's change) and 2 (an unmapped issue is created by the pull after the map is fixed), plus one for path 3 (a dropped event is retried and reported on the next pull).
      - **F7, comment refusal:** the refusal to edit or remove a sourced comment names the source and the key, with no `source unlink` hint. The title, mapped-field and description refusals keep the hint. The GitLab fetch by path and number is recorded as built, so no code change is needed there.
      - **F4 waits** for op-pierre's ruling on ADR-1274; leave the display as it is until then.
- [2026-11-04T02:46:40Z] `python-dev` Elias Python:
  - Handback for REV-1281: F1, F2, F3, F5, F6, F9, F10, F11 Fixed and F7's code half done (each finding has its own comment). F4 untouched. Not committed; no full suite.
    
    - F1: redirects are followed only within the tracker's scheme, host and port; otherwise the command fails naming both addresses and nothing is sent.
    - F2: no cursor; one listing() per pull, details only for unheld issues or a differing listed (updated_at, state); a dropped link keeps the host's stored updated_at; `sq source list` computes the newest updated_at inline.
    - F3: a ref whose target fails is dropped alone and reported; created is empty unless applied or a dry run.
    - F5, F6, F9, F10, F11 as in their comments. Connector table is data; the class loads in _services/_fetch only. `require_title` now rejects marker tags for every item and sub-entity title.
    - F9 judgments: migration pre-flight deleted and its summary says three (the load refusal still names the manual, whose range now lives in _migrations/_reserved.py, read in a function: new import-edge row `_workflow -> _migrations local`). The holder check moved into the transaction by trace, no race test. `show --refresh` and relink still read one full listing; the ADR accepts that cost.
    - Open for @architect: a NEW host item whose link target fails keeps its real updated_at (nothing stored to keep), so that link is not retried until the host changes; the line reports it.
    - Gates: pyright 0, ruff clean, sq check clean; tests/meta tests/check tests/cli tests/regressions tests/daemon tests/cross_process pass (2081 + the two meta fixes re-run, 728 meta); the source modules also pass under remote and routes modes.
    - Docs rows: pull fetches by listing diff (no cursor); redirects refused across origins; credential store modes and lock.
- [2026-11-04T02:53:08Z] `architect` Robert Architect:
  - - @python-dev REV-1281 F3, reopened. ADR-1274 §14 (2026-11-04) rules that when the pull that creates an item drops any of its issue's events (its links included), the item's `source` record is written with `updated_at = ""`. An existing item keeps its stored value, as now. The empty value differs from every listed `updated_at`, so the next pull re-reads the issue, retries the dropped event and reports it, and stores the real value once everything applies.
      - Change: extend `_keeping_stored_time` (or its caller) so that an issue with a dropped event and no stored record gets `""`, not the tracker value. The record shape check must accept `""` for `updated_at`. Every reader that formats or compares it (the age in `source_description`, the newest `updated_at` in `sq source list`) must treat `""` as unknown, not fail.
      - Test: extend `test_a_link_target_that_fails_costs_only_the_link_and_the_report_lists_what_exists` with the reviewer's second pull. Fix #13's title in the recorded responses, pull again, and assert that #13 is created, the host item's `refs` gain the link, and the host's `source.updated_at` is now the tracker value. A third pull must write nothing.
- [2026-11-04T03:28:22Z] `architect` Robert Architect:
  - - @python-dev concurrency check, ADR-1274 §14 (2026-11-04). The pull and `relink` compile inside the transaction against the fresh index, which is correct. `show --refresh` has a gap: `refresh_item` compiles through `_compile_source`, and if the item is unlinked (or unlinked and relinked) between the fetch and the transaction, `Compiler.issue` finds no holder and **creates a new item**.
      - Fix: give `refresh_item` its own compile job, like `relink_item`. Inside the transaction, re-read the addressed item and refuse with "changed while the issue was fetched; run it again" unless it still carries the same `(name, id)`. Then refresh only that item and its duplicates under the same `(name, id)`, and never emit a `create`.
      - Test: a refresh whose item is unlinked between fetch and apply. Drive it with a fixture that unlinks inside the recorded-HTTP handler; the refresh must be refused and the item count must not change.
- [2026-11-04T03:29:34Z] `architect` Robert Architect:
  - - @python-dev ADR-1274 §14 (2026-11-04), "Unlink, then a pull": `unlink_item` adds one warning to its `Response.warnings` when the removed record's `state` was `open` or `closed`. Exact text:
    
    ```
    <key> still matches the filter of source '<name>': the next `sq source pull` imports it again as a new item; take it out of the filter on the tracker to prevent that
    ```
    
      - There is no warning for `out-of-filter` or `gone`, and nothing else changes; unlink still keeps no state.
      - Tests: unlink of an `open` item prints the warning on stderr and in `--json` `warnings`; unlink of an `out-of-filter` item prints none; a pull after the warned unlink creates a second item while the first keeps its prose.
- [2026-11-04T03:33:15Z] `architect` Robert Architect:
  - - @python-dev ADR-1274 §14 (2026-11-04) rules on REV-1282 F11:
      - In `check_views`, refuse `stored = true` on any view whose `source.kind` is not `source`, naming the view: "`stored = true` needs a source kind whose writer fills the body; only `source` has one". Add a `workflow lint` / load case for `[views.notes] source = { kind = "self" }, stored = true`.
      - In `_items.py`'s altered-pair refusal, name `sq <addr> show --refresh` only when the item holds a `source` record. Otherwise say that nothing in the squad writes this view until the item is linked to an issue.
      - F12 needs no ruling: `stored` goes after `transform` in `ViewRow`, per the stability rule that a new key never sits between two existing ones.
- [2026-11-04T04:02:52Z] `python-dev` Elias Python:
  - Done, not committed, no full suite: show --refresh has its own compile job (refuses unless the item still holds the same (name, id) inside the transaction; delegates to the compiler only after that, so it never creates; race test unlinks from the recorded-HTTP handler). Unlink warns for open/closed records with the architect's text (stderr; stdout document unchanged), tests for open, out-of-filter and the re-import after the warned unlink. REV-1282 F11 and F12 Fixed. tests/_stored_view.py now declares its view with source kind `source` (the new load rule). Gates: pyright 0, ruff clean, sq check clean, meta/check/cli/regressions/daemon/cross_process 2102 passed; links tests also pass in remote and routes modes.
<!-- sq:discussion:end -->
