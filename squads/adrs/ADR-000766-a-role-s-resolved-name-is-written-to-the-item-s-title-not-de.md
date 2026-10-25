---
id: ADR-766
sequence_id: 766
type: decision
title: A role's resolved name is written to the item's title, not derived
status: Accepted
author: architect
refs:
- BUG-756:addresses
- ADR-955
- ADR-1007
- ADR-777
description: The reconciler projects a resolved full_name/mission onto the item's
  own title/description; rendering stays generic
created_at: '2026-08-21T19:44:27Z'
updated_at: '2026-10-25T21:42:15Z'
---
<!-- sq:body -->
## Context

A role's definition resolves from the role catalog, a project's `.overrides/roles.toml` and its
per-slug file (ADR-754), and two of its fields have a counterpart on the item every generic
surface reads: `full_name` and the item's `title`, `mission` and the item's `description`. When
this was decided, the one path that carried an override onto a live role item merged only the
resolved definition's extra-key output, so a declared `full_name` or `mission` reached the role's
`extra` mapping while `title` and `description` kept what `create` stamped at activation.

Driven on a fresh squad (`sq init --default-names`; `sq override scaffold --role architect`; the
scaffold given `full_name`, `title`, `mission`, `description`; `sq sync` exit 0):

- frontmatter and index both held `title: Robert Architect` beside `extra.full_name: Ada Lovelace`;
- `sq list -t role`, `sq show ROLE-2` (styled, `--raw`, `--json`), `sq list --json -t role` and
  `sq tree ROLE-2` rendered the stale name, while the `sq role architect show` card, `sq role list`
  and the compiled `CLAUDE.md` roster rendered the declared one;
- `sq search Robert` matched, reporting the hit as `title: Robert Architect`: the superseded name
  was indexed, not merely displayed;
- `sq check` reported nothing.

A declared `mission` split the same way: `sq role architect show` printed the declared mission in
its card and the bundled mission in the body beneath it.

Those two are the whole set. Of the fields a role override may declare, only
`full_name`/`title` and `mission`/`description` are pairs: the others have no top-level
counterpart, `slug` is pinned to the filename, and a colliding `is_default` is already a
`sq check` error.

## Decision

**1. The resolved value is written to the item's own field. Rendering learns nothing.**

`Item.title` is the authoritative display name for every item type, roster types included, and
`Item.description` its summary. The one writer that resolves a role's definition projects the
resolved `full_name` onto `title` and the resolved `mission` onto `description`.

The resolved `full_name` of an existing role is its stored name. The name comes from `--name` or
from the configuration (bundled catalog, `.overrides/roles.toml`, per-slug file, developer pool)
only when the role is created; afterwards no configuration change renames an active role, and a
rename goes through the role's update verb (ADR-777 §3). The resolver pins the stored `title` over
every layer (`pinned_name_of`), so the `title` projection carries the stored name back onto itself
and the `description` projection is the one an override moves.

**2. The pairing is declared as data, beside the tables it mirrors.**

`RoleDef` declares `_ITEM_FIELD_PROJECTION` next to its attribute tables (`_ATTRIBUTE_FIELDS`,
`_DEV_ATTRIBUTE_FIELDS`): `title` from `full_name` and `description` from `mission`. The
reconciler (`_refresh_catalog_attributes`) loops over `to_item_fields()` exactly as it loops over
`to_attributes()`. The defect class is "one fact, two stored homes, and a writer that knows one of
them". A declared table makes a `RoleDef` field that also lands on a core item field impossible to
half-wire, because the pairing is stated once, in the same class, in the same shape as the tables
that already work.

**3. The frontmatter write lands where the catalog refresh already writes.**

The catalog refresh writes markdown inside the transaction and commits the index last. The
projected fields ride the same single `update_frontmatter` call: it is not a new write and it does
not move in the order, so invariant 8 is satisfied by the write it rides. A change confined to the
projected fields is not skipped as a no-op, and the in-memory rollback on a skipped write restores
the projected fields as well as the attributes, so the item never claims a value the disk does not
have.

**4. The projection changes `title`. It never routes through the rename path.**

A title change through `_update_model` recomputes `slug = slugify(title)` and moves the file. A
roster item's path slug is its role slug, not a slug of its title (`agents/roles/ROLE-000002-architect.md`
carries `title: Robert Architect`). The projection assigns `item.title` directly, so title and
slug stay decoupled for roster items and no file moves.

**5. The skew guard treats the projected fields as ordinary fields.**

`title` and `description` are core frontmatter keys, and `frontmatter_skew` compares them like any
other. The reconciler writes markdown then index in one transaction, so a completed projection
leaves the two sides equal, and an interrupted one leaves markdown ahead: the one sanctioned
direction. `sq repair` heals it by adopting the file's value on a squad at the package's schema;
while the squad's schema is behind the package, the reconcile that `sq migrate up` runs before
its first runner does it (ADR-955).

The skew guard's exemption, `PERMITTED_ATTRIBUTE_SKEW`, is derived from `RoleDef.attribute_keys()`
and holds `model` alone. It applies to a non-developer role only: a developer's `model` is an
operator setting and is compared like any other field, and no other item type is exempted.
Membership is pinned by test against an unreviewed widening, which is the only direction that can
mask a real skew; narrowing it is safe, since a key that leaves it can only produce a
repair-clearable refusal. The exemption is unconditional, with no corpus precondition: neither the
remaining key nor anything else in it can hold an operator answer a masked skew could lose, and it
is kept for a squad whose index lags on that key, where comparing it would refuse the sync that
converges it.

**6. There is no second stored copy.**

A role item stores `full_name` and `mission` nowhere but in `title` and `description`. Every other
field of its definition resolves from the catalog on every read. The item stores only what a
dedicated verb sets and no document answers: its slug, its name, `is_default`, a developer's `tech`
and `model`, `pronouns`, `origin`. `full_name` and `mission` are not attributes (ADR-1007,
ADR-776).

**7. Why deriving the display name at render loses.**

The count, driven and read: **27** reads of a generic item's `title` on paths a role item reaches.

In-process, 20. Eleven display sites: the shared item panel (`_cli/_common.py:490`), the `--raw`
dossier heading (`:742`), the `sq list` / `sq mine` table (`_cli/_main.py:220`, called at `:510`
and `:1112`), `sq tree` (`:633`), `sq search` (`:804`), `sq inbox` (`:879`), `sq blocked` for the
target and its blockers (`:911`, `:913`), and three in the terminal browser — `_tui/_tree.py:49`,
`_tui/_search.py:49`, and `_tui/_browse.py:47`, which sorts by it. Seven JSON sites:
`_cli/_main.py:618`, `:790`, `:860`, `:897`, `:899`, plus two whole-model dumps — `sq list --json`
at `:499` and `sq show --json` at `_cli/_common.py:891`. And two matchers, where the title is read
as data rather than printed: the search title region (`_services/_collab.py:423`) and `sq inbox`'s
admission of an `@mention` found in an item's title or description (`:177`).

Out of process, seven more. The VS Code client renders `item.title` in `itemDirectory.ts:35`,
`metaView.ts:48`, `listView.ts:90`, `recordsView.ts:58`, `treeMapping.ts:45`,
`searchResults.ts:28` and `graphDiagrams.ts:94`, off those same payloads, and reads no `extra`
field anywhere (driven: `grep -rn 'extra\.' clients/vscode/src/` returns a single comment).

Three of those groups are unreachable from a rendering helper. The two model dumps reproduce the
field verbatim, so resolving there means the `title` a dump reports is not the `title` the model
holds. The two matchers sit in the service core, so resolution would have to move into search and
inbox rather than into rendering. The client is a separate process and cannot be taught the rule
without exporting per-type name resolution across the boundary, into every future client. Deriving
at render does not scatter resolution into two renderers; it scatters it across three layers and a
process boundary — and even then leaves `sq search <superseded name>` matching and
`sq search <declared name>` missing, because the stored string is what is indexed.


## Consequences

- A declared `mission` reaches the item's own record, and the record never disagrees with itself.
  Every reader counted above is correct with no change of its own, including the two model
  dumps, the two matchers and the client, because the field they read is the field the
  projection writes.
- `sq search` matches the name and summary the squad uses.
- The reflog is untouched. Its create and update deltas record the title as it stood at the time;
  a log line is a historical record, not a projection, and is never refreshed.
- No `sq check` rule compares a stored title with the resolved name: the projection repairs it on
  the next sync, so the disagreement is transient by construction. An interrupted write is a
  different state, reported by `sq check` as frontmatter-vs-index drift (ADR-783).

## Falsification the implementation owes

- An override declaring only `mission` is asserted on four surfaces: frontmatter, index,
  `sq list -t role`, and `sq role <slug> show`. Drop the row from the projection table and the
  test goes red naming the bundled value. Assert the declared string, never agreement between two
  copies.
- An override declaring `full_name` on an existing role leaves its stored `title` unchanged; the
  name is renamed only through the role's update verb.
- An override declaring neither field leaves `title` and `description` byte-identical, which
  catches a projection writing unconditionally instead of on a diff.
- Cover the file shapes, not only the fields: a bundled-slug override, a `<tech>-dev.toml` on the
  second of two developers (the other developer's record must be untouched), an override on a
  retired role, and one declaring a value equal to the current one, which takes the no-op path.
- The item's path is unchanged across a projection. Route it through the title-rename path instead
  and that test goes red on a moved file.
- `sq check` is clean on a squad carrying a `mission`-declaring override, before and after the sync
  that applies it.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T19:47:10Z] `manager` Catherine Manager:
  - Verified the two claims this ruling turns on before accepting. PERMITTED_EXTRA_SKEW is literally frozenset({X.SKILLS, *RoleDef.extra_keys()}) at _itemfile.py:70, so dropping a key from that table would shrink the guard exemption and trade a duplicated string for a hand-maintained exception in the integrity core. The second field pair is real: _services/_roster.py:51 and :82 stamp description from role.mission, and templates/agents/role.md.j2:8 renders description or extra.get(mission), so a declared mission makes one command contradict itself. Accepted as written, projection table included.
- [2026-08-21T19:47:48Z] `op-pierre` Pierre Chat:
  - No sq check rule for a stored title disagreeing with the resolved full_name. The projection repairs it on the next sync, so the disagreement is transient by construction, and a gate that fires on every pre-fix corpus until someone syncs is noise in a repo where sq check must stay clean.
- [2026-08-22T10:01:24Z] `architect` Robert Architect:
  - Section 5 confirmed by drive, not just by structure. Simulated the interrupted write both ways on fresh core-roles squads: with the divergence confined to extra.full_name (the pre-projection shape, still reachable since that key is exempt), sq sync exits 0 with no warning and overwrites markdown Ada Lovelace with the index stale Robert Architect — a committed markdown value destroyed silently, sq check clean throughout. With the divergence on the projected title, the whole write is skipped, markdown is preserved on title AND full_name, and sq repair adopts the file value. So the guard exemption was hiding the one skew direction _index/_store.py:18-38 forbids, and section 5 was right for a stronger reason than it states.
  - The reporting half this decision deferred as a separate policy call is now ruled on ADR-783 (@manager @qa). Nothing here changes.
- [2026-10-11T20:19:26Z] `architect` Robert Architect:
  - 2026-10-11: narrowed in place, on the operator's ruling of this date recorded on MILE-934. One dated note, after decision 5, which states that `sq repair` heals an interrupted projection; the note also covers the two restatements in the 2026-09-02 amendment note (sections 1 and 4) by reference. It says the claim holds at the package's schema, and that while a squad's schema is behind the package the gate refuses `sq repair` and the reconcile inside `sq migrate up` is the recovery path (ADR-955 and its amendments of 2026-10-09). Nothing else in the body changed; `related` ref to ADR-955 added.
- [2026-10-25T21:42:15Z] `architect` Robert Architect:
  - 2026-10-25 audit: body rewritten in present tense; decision unchanged. Folded the 2026-09-02 amendment and the ADR-955 and ADR-1007 notes: decision 6 now states there is no second stored copy (full_name/mission live only in title/description), decision 5 names PERMITTED_ATTRIBUTE_SKEW (model only). Decision 1 records that an existing role keeps its stored name (pinned_name_of; ADR-777 section 3, op-pierre 2026-10-16), so the projection moves description. Related ref to ADR-777.
<!-- sq:discussion:end -->
