---
id: FEAT-1271
sequence_id: 1271
type: feature
title: Sources spec and pull
status: Ready
parent: EPIC-1268
author: product-owner
refs:
- MILE-1269:targets
- FEAT-1270:depends-on
description: Declare sources in sources.toml and pull opted-in issues into items
subentities:
- local_id: US1
  title: Sources declared in a sources.toml spec document
  status: Todo
- local_id: US2
  title: A durable source identity on each item
  status: Todo
- local_id: US3
  title: Map attribute kind and operator identities
  status: Todo
- local_id: US4
  title: sq source pull creates and refreshes items
  status: Todo
- local_id: US5
  title: The source_description view
  status: Todo
- local_id: US6
  title: Source-owned fields refused, broken links checked
  status: Todo
- local_id: US7
  title: List sources, unlink and relink an item
  status: Todo
- local_id: US8
  title: Comments carry attributes
  status: Todo
- local_id: US9
  title: Source credentials held where the squad is served
  status: Todo
created_at: '2026-11-03T15:57:07Z'
updated_at: '2026-11-03T23:18:11Z'
---
<!-- sq:body -->
A squad declares the trackers it pulls from, and `sq source pull` turns each opted-in issue into an item that agents work on. The tracker owns the issue's title, description, mapped fields and comments; the squad owns status, assignee, labels, type after creation, sub-entities, refs and its own comments. Nothing is written back to the tracker.

Sources are declared in a fourth spec document, `sources.toml`, beside the workflow, roles and playbook documents: the bundled file declares connector defaults and no source; `squads/.overrides/sources.toml` declares the project's sources. `.squads.toml` is unchanged.

Every source command runs where the squad is served: on the local daemon, in process when there is none, and on the server for a hosted squad. That side holds the tracker credentials, in a store outside the repository read at pull time; no client sends a token and no credential is read from the daemon's process environment.

Every mapping (issue type or label to item type, tracker value to badge value, issue link to ref kind) is declared in the spec and validated when it loads; no type, label, field or status name appears in code.

Sourced items and comments are authored by `source:<name>`. The colon, which the slug grammar forbids, makes the `<word>:` author namespace squads' own; `source` is its first word and becomes a reserved slug. Attribution resolves to an operator at read time, through the tracker's immutable user ID recorded in the operator's `identities`.

Open design points for an ADR before building: the core `source` key and its index lookup, the `map` attribute kind and nested frontmatter records, comment attributes and their storage, the `source:` author prefix, the `sources.toml` document and its merge, the credential store, and the schema bump with its migration.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1271 add-story "As a <role>, I want … so that …"`; track with `sq feature 1271 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Sources declared in a sources.toml spec document

<!-- sq:story:US1:body -->
As an adopter, I declare my sources in one spec document and nothing else.

Done when:
- A bundled `sources.toml` declares connector defaults (type, field and link maps per connector version) and no source; `squads/.overrides/sources.toml` declares sources as `[sources.<name>]` with `connector`, `version`, base URL, filter (label, or JQL for Jira), `trusted`, `enabled`, and per-source map overrides.
- `version` may be left out only when the connector has exactly one registered version; otherwise the source fails at load, listing the known versions.
- It loads through the shared spec loader and merge, once per invocation, and `sq override` scaffolds and diffs it.
- Declaring a source activates it; `enabled = false` pauses it; a fresh squad has none.
- Every map target is checked at load against the workflow spec (declared type, badge field and value, ref kind); a bad target fails with a message naming the source, the map and the value.
- A source name follows the slug grammar; the name `source` itself is a reserved slug no role or operator can take.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — A durable source identity on each item

<!-- sq:story:US2:body -->
As the pull, I link an item to its issue durably, even when the issue is moved.

Done when:
- A sourced item's frontmatter carries a core `source` record, a nested object: source name, the tracker's immutable ID, the full readable key (`owner/repo#12`, `group/project#12`, `PROJ-45`; never a bare `#12`), state (`open`, `closed`, `out-of-filter`, `gone`), `updated_at`, and the author's immutable ID and handle. Nothing else is stored.
- The issue URL is derived by the connector from the source's base URL and the key, never stored.
- The item's core `author` is `source:<name>`; `labels` and `assignee` stay squad-owned and are never written by the pull.
- Matching an issue to its item uses the immutable ID; a moved issue updates the key on the same item.
- `sq repair` rebuilds the index's source lookup from the item files alone.
- A schema bump with an `sq migrate up` runner; squads with no source are carried unchanged.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Map attribute kind and operator identities

<!-- sq:story:US3:body -->
As an operator, my account on each source is recorded on my own operator item, so sourced issues and comments show as mine.

Done when:
- Attributes gain a `map` kind (string to string), a nested record declared in the spec, read through a typed accessor, with a derived repeatable CLI option `--<name> key=value` and `--<name> key=` to remove a key.
- The workflow spec declares `identities` (`map`) on operators; keys are source names, values the tracker's immutable user ID.
- Setting an identity accepts a handle (`--identities gitlab-prod=@pchat`), resolves it to the immutable ID through the connector where the squad is served, and stores the ID.
- An identity key naming no declared source, or two operators claiming the same ID on one source, fails `sq check`; `sq source check` reports an identity whose ID no longer resolves.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — sq source pull creates and refreshes items

<!-- sq:story:US4:body -->
As an operator, `sq source pull [<name>]` brings in the issues opted in on my trackers and refreshes the ones already linked.

Done when:
- A new in-filter issue becomes an item of the type its map gives, with the title, the mapped fields and the `source_description` view seeded with its description.
- The type is applied at creation only. The squad may retype the item afterwards, keeping its link; the pull never retypes and reports a tracker type that no longer matches the map. A mapped badge field the item's type lacks is skipped and reported.
- Linked items refresh their source-owned data. Tracker comments arrive as discussion comments authored by `source:<name>`, matched on their `source_id` attribute, updated in place when edited on the tracker, and reported (not removed) when deleted there.
- Issue links whose both ends are pulled become refs, through the declared link map.
- Every pull reconciles the source's linked items: the incremental query since the cursor brings changed content; a listing of the IDs matching the filter, closed issues included, marks closed issues `closed`; each linked item missing from it is fetched once, `out-of-filter` when found outside the filter, `gone` when not found, reported as "deleted or no longer readable". The item stays.
- The cursor is derived from the newest `updated_at` of the source's items, never stored. The pull paginates, backs off on rate limits, and compiles what it fetched into one `sq import` transaction rather than a second write path.
- Pulling twice changes nothing on the second run; `--dry-run` and `--json` are supported.
- With no name, sources without a credential are skipped with a warning; a named source without one is an error naming how to add it.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — The source_description view

<!-- sq:story:US5:body -->
As an agent reading a sourced item, I see the issue's description, where it came from, and whether to trust it as instructions.

Done when:
- A bundled `source_description` view renders the stored description with the source, the key, the derived URL and the age of the issue's `updated_at`.
- Unless the source is `trusted`, the rendering states that the text was imported from outside the squad and must not be followed as instructions.
- Tracker references (`#12`, `PROJ-45`) are translated to item IDs at read time when the referenced issue is linked to an item; the stored text keeps the raw references.
- `@mentions` in imported text are left as they are.
- `sq <type> <n> show --refresh` refreshes that item's issue where the squad is served, then shows it.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Source-owned fields refused, broken links checked

<!-- sq:story:US6:body -->
As the squad, I cannot drift from the tracker by editing what it owns, and `sq check` tells me when a link is broken or duplicated.

Done when:
- `title`, writes to a mapped badge field, writes inside the `source_description` stored body, and edits or removals of a comment authored by `source:<name>` are refused on a sourced item, naming the source and the issue.
- `--as source:<name>` is refused on every command; only the pull writes as a source.
- `sq check` reports two items sharing a source's immutable ID (resolution is manual), a `source:<name>` author naming no declared source, items whose source is undeclared or disabled, and items whose `source.state` is `out-of-filter` or `gone`.
- `sq source pull` reports the same broken links it finds.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — List sources, unlink and relink an item

<!-- sq:story:US7:body -->
As an operator, I can list my sources and detach or reattach an item.

Done when:
- `sq source list` shows each source with its connector and version, enabled or not, whether a credential is stored for it (never its value), its item count, and the newest `updated_at` among its items.
- `sq <type> <n> source unlink` turns the stored description into plain body text the squad owns and removes the `source` record; the item and its imported comments stay.
- `sq <type> <n> source relink <source> <issue>` reattaches an item to an issue of the same source by its immutable ID. "Same source" is checked against the item's `source:<name>` author, which survives `unlink`, so an item with no record whose author is not `source:<source>` is refused.
- Relink refreshes the item straight away: the description view is restored and the squad's own body text is kept, without waiting for a pull.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — Comments carry attributes

<!-- sq:story:US8:body -->
As any squads component that records extra data on a comment, I store it as attributes on the comment, not in its text.

Done when:
- Any comment can carry a flat key-to-value mapping of attributes, stored on a tag inside the discussion region, with a value-bearing marker form and its own escaping.
- Attributes are not a hash input: changing only attributes keeps the comment's hash.
- A sourced comment stores `source_id`, `author_id`, `author_handle`, `author_name` and `source_updated_at`; `source` is derived from the `source:<name>` author and the author URL from the base URL and the handle.
- `show --comments`, `--json` and the TUI display a sourced comment's author as the source handle plus the local slug when an identity matches, e.g. `op-pierre Pierre Chat via gitlab-prod @pchat`, or `Pierre Chat via gitlab-prod @pchat` with no match.
- Mentions in sourced comments reach the inbox. Unless the source is `trusted`, the comment and its inbox line carry an "imported, untrusted" notice, derived at read time from the author and the source's `trusted` flag, never stored.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — Source credentials held where the squad is served

<!-- sq:story:US9:body -->
As an operator, I store each source's credential where the squad is served, once, and every source command finds it.

Done when:
- Credentials live in a store outside the repository, on the side that serves the squad; the local daemon, an in-process run and a hosted server all read it at pull time, never from a process environment captured at start-up.
- One command adds, replaces or removes a source's credential without printing it; no credential value is ever stored in the squad or printed.
- A source has one credential, typically a service account; attribution never depends on whose credential it is.
- The store fits the authentication mode MILE-868 decides for a hosted squad.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-03T15:57:36Z] `op-pierre` Pierre Chat:
  - Rulings (2026-11-03):
    - Operator handles go under a sub-object, `identities.<source>`, not a bare `gitlab` attribute.
    - Maps are declared in specs; sources in a `sources.toml` document with an override counterpart, not in `.squads.toml`. Declaring a source activates it.
    - Broken links: the pull warns; the state is part of the stored source snapshot (`source.state`).
- [2026-11-03T16:17:49Z] `architect` Robert Architect:
  - @product-owner board check against the accepted ADRs and existing work:
    - US2 and US3, conflict with ADR-1007 §1 ("no nested container on any wire surface"; "keeping a nested container under another name" rejected). `subentities` is a structured core key, so `source` has a precedent, but the `map` attribute kind needs §1 and the kind list amended.
    - US2, `source.labels` and `source.author` sit beside the core keys `labels` and `author`; say whether tracker labels feed `item.labels` or stay in the snapshot only.
    - US4, imported comments conflict with ADR-979 (a comment header carries a registered slug, so a tracker author with no `identities` entry has none) and ADR-1013 (only the author edits a comment, yet the pull edits one attributed to an operator). "Keyed by their tracker ID" has no home: the header grammar has no slot, and the comment hash changes on every edit.
    - US4, an incremental pull cannot see `out-of-filter` or `gone`: a filtered query since the cursor never returns an issue that lost its label or was deleted. Detecting either needs a full listing or a fetch per linked item.
    - US1 and US4, tokens from the environment conflict with ADR-1261: a served command reads only a fixed list of client variables, and `token_env` names are dynamic. This repo runs in daemon mode, so the token in the operator's shell never reaches the pull. Options: make `sq source` local-only, or send tokens over the socket.
    - US5, the untrusted-text notice covers the description view only; imported comments carry none, and with `@mentions` left as they are, an `@role` written on the tracker lands in that agent's inbox.
    - US6, retype of a sourced item is not addressed (the type is applied at creation only).
    - US4, reuse: `sq import` (ADR-622) already has one transaction with a per-event clock and actor; the pull can compile to import events instead of a second write path.
- [2026-11-03T16:27:40Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-03): tracker comments are real comments in the item's discussion, not a separate tracker-owned cache. Any comment needs a way to store extra info (such as the tracker's user ID and handle), possibly through a new tag.
- [2026-11-03T16:27:41Z] `architect` Robert Architect:
  - @product-owner design notes on the ruling above; they replace the ADR-979/ADR-1013 point of comment 09a27ed. For the ADR, not drafted yet:
    - Comment attributes: a flat key-to-value mapping any comment can carry, generic like item attributes (ADR-1007); the pull is only the first writer. A sourced comment carries e.g. `source`, `source_id` (the tracker comment's immutable ID), `author_id`, `author_handle`, `author_name`, `author_url`, `source_updated_at`.
    - Storage: a tag on the comment inside the discussion region. Comments live only in the body and have no stable ID a frontmatter record could key on (the hash changes on every edit). The marker grammar carries no payload today, so the tag needs a value-bearing form with its own escaping.
    - Header author is the source name, display name the tracker handle: the ADR-979 grammar is unchanged. The source is the comment's author, so only the pull edits or removes it, and ADR-1013 holds as written.
    - The pull matches a comment by its `source_id` attribute, never by hash, so a tracker-side edit updates the same comment in place.
    - Attribution resolves at read time: when `author_handle` is in an operator's `identities`, the comment shows as that operator's. Nothing is rewritten when an identity is added later.
    - A source name must not equal a role or operator slug, refused at load.
    - Mentions reach the inbox, per the ruling, so each sourced comment from an untrusted source needs its own "imported, untrusted" marker; the description notice does not cover comments.
    - Open for the ADR: whether attributes are a hash input. Recommendation: no, so a metadata-only refresh keeps the hash.
- [2026-11-03T21:25:40Z] `op-pierre` Pierre Chat:
  - - Ruling (2026-11-03), replacing the token-from-environment rule and the "make `sq source` local-only" option for ADR-1261: `sq source pull`, `sq source check` and `show --refresh` run where the squad is served, and that side holds the tracker credentials. A hosted squad (FEAT-33) has no local squad to write to, so a local-only command cannot work. A client-sent token is ruled out: a secret on the wire, a squad-wide pull tied to one caller, and no client at all for the later timer and webhook pulls.
      - Credentials are read at pull time from a store outside the repository, never from the daemon's process environment, which is captured when the daemon is spawned. Without a daemon, the same store is read in process.
      - One credential per source, typically a service account; attribution goes through `identities` at read time. Per-user tokens are a write-back concern, out of scope.
      - `sq source check` probes from the serving side, because reachability and permissions are those the pull will see.
      - For the ADR: the store's location and format, how an operator fills it, and its fit with the MILE-868 authentication mode.
- [2026-11-03T21:35:36Z] `op-pierre` Pierre Chat:
  - - Ruling (2026-11-03) on detecting `out-of-filter` and `gone` (US4): every pull, not only a full one, reconciles the source's linked items in three steps.
      - The incremental query since the cursor brings in changed content, as before.
      - A listing of the IDs matching the filter, closed issues included, tells which linked items are still in the filter; an issue in that listing but closed is `closed`.
      - Each linked item missing from the listing is fetched once: found outside the filter is `out-of-filter` (a move to a project the filter does not cover included), not found is `gone`.
      - A 404 cannot tell a deleted issue from one the credential can no longer read, so the `gone` report says "deleted or no longer readable". No extra heuristic: the state is only reported, the item stays, and the next pull corrects a wrong one.
- [2026-11-03T21:43:09Z] `op-pierre` Pierre Chat:
  - - Ruling (2026-11-03): the source snapshot is a nested object in the frontmatter. The flat-frontmatter rule asked for earlier (ADR-1007) was to get rid of the catch-all `extra` object; it does not ban nesting. Nested objects must be allowed in contexts like this one.
- [2026-11-03T21:43:09Z] `product-owner` Nina Product:
  - - @architect for the epic's ADR: ADR-1007 §1 ("no nested container on any wire surface") needs amending per the ruling above, for the `source` snapshot and the `map` attribute kind alike. Proposed line between the two cases: a nested object is allowed when it is a declared record with a known shape and one owner (`subentities`, `source`, a `map` attribute), and refused when it is an open bag of undeclared keys (the retired `extra`).
- [2026-11-03T21:51:11Z] `op-pierre` Pierre Chat:
  - - Ruling (2026-11-03) on the `source` snapshot's contents (US2): source name, the tracker's immutable ID, the full readable key (`owner/repo#12`, `group/project#12`, `PROJ-45`; never a bare `#12`), state, `updated_at` and the author handle. Nothing else is stored.
      - The URL is not stored: each connector derives it from the source's base URL and the key, so a moved instance needs no pull.
      - Labels, assignees and milestone are not stored: the maps already turn what matters into a type or a badge, and `sq source check` asks the tracker live. The core `labels` and `assignee` keys stay squad-owned.
      - `fetched_at` is not stored: it changes on every pull. The age US5 shows is the issue's `updated_at`.
- [2026-11-03T22:03:38Z] `op-pierre` Pierre Chat:
  - - Ruling (2026-11-03) on the author of sourced items and comments: it is `source:<name>`, e.g. `source:gitlab-prod`, using a colon, which the slug grammar forbids, as a namespace prefix. That replaces the load-time rule that a source name must differ from every role and operator slug. Attribution still resolves to an operator at read time through `identities`. Further slug prefixes may be reserved in the future, and adopters must be warned about it.
- [2026-11-03T22:03:38Z] `product-owner` Nina Product:
  - - @architect for the epic's ADR, from the ruling above:
      - ADR-979's comment header grammar accepts `source:<slug>` beside a slug; `sq check` validates `<name>` against the declared sources.
      - `--as source:<name>` is refused on every command; only the pull writes as a source.
      - The mention pattern stops at the colon, so `@source:x` reads as `@source`: the bare word `source` becomes a reserved slug, like `squads` and `operator`.
      - Every later prefix reserves its bare word the same way, which can collide with an adopter's existing role. The ADR states that the `<word>:` author namespace belongs to squads, and the adopter docs warn that more words may be reserved.
- [2026-11-03T22:05:10Z] `op-pierre` Pierre Chat:
  - - Ruling (2026-11-03) on mentions in imported comments (US4, US5): mentions reach the inbox. The "imported, untrusted" notice is derived at read time from the comment's `source:<name>` author and that source's `trusted` flag, never stored on the comment. It shows wherever the comment does: in the discussion and on the inbox line. Declaring a source `trusted` later removes every notice without rewriting anything.
- [2026-11-03T22:08:57Z] `op-pierre` Pierre Chat:
  - - Ruling (2026-11-03) on retyping a sourced item (US4, US6): the squad owns the type once the item exists. `sq retype` works on a sourced item, which keeps its `source` snapshot and its link. The pull never retypes; a tracker-side type that no longer matches the map is reported only. When the new type lacks a badge field the source maps, the refresh skips that field and reports it instead of failing.
- [2026-11-03T22:18:29Z] `op-pierre` Pierre Chat:
  - - Ruling (2026-11-03) on comment attributes and identities:
      - Comment attributes are not a hash input.
      - A sourced comment stores `source_id`, `author_id`, `author_handle`, `author_name` and `source_updated_at`. `source` is derived from the `source:<name>` header author and `author_url` from the base URL and the handle, so neither is stored.
      - `identities` match on the tracker's immutable user ID, not the handle. The item snapshot stores the author's immutable ID beside the handle for the same reason.
      - Display shows the handle, clearly from the source, plus the local slug when an identity matches, e.g. `op-pierre Pierre Chat via gitlab-prod @pchat`; with no match, `Pierre Chat via gitlab-prod @pchat`.
- [2026-11-03T22:18:29Z] `product-owner` Nina Product:
  - - @architect open detail from the ruling above, for the ADR: an operator knows their handle, not their immutable ID. Proposed: `sq operator <slug> update --identities gitlab-prod=@pchat` accepts a handle, resolves it to the immutable ID through the connector where the squad is served, and stores the ID; `sq source check` reports an identity whose ID no longer resolves.
- [2026-11-03T23:12:30Z] `product-owner` Nina Product:
  - US7 relink reworded per ADR-1274 section 14: same-source check uses the surviving source:<name> author, and relink refreshes the item at once.
- [2026-11-03T23:18:11Z] `product-owner` Nina Product:
  - US1 reworded per ADR-1274 section 14: version may be omitted only when the connector has one registered version; otherwise the source fails at load listing known versions.
<!-- sq:discussion:end -->
