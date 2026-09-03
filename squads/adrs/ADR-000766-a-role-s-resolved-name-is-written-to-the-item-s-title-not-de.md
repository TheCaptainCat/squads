---
id: ADR-766
sequence_id: 766
type: decision
title: A role's resolved name is written to the item's title, not derived
status: Accepted
author: architect
refs:
- BUG-756:addresses
description: The reconciler projects a resolved full_name/mission onto the item's
  own title/description; rendering stays generic
created_at: '2026-08-21T19:44:27Z'
updated_at: '2026-09-02T13:14:46Z'
---
<!-- sq:body -->
## Context

A role override merges field-wise over a base, and a declared `full_name` renames the role
(ADR-754). The one path that carries an override onto a live role item merges only the resolved
definition's `to_extra()` output (read: `_services/_maintenance.py:645-651`), so a declared name
reaches `extra.full_name` while the item's own `title:` keeps what `create` stamped at activation
— which is the same name, from the same source, passed as the item title (read:
`_services/_roster.py:50`).

Driven on a fresh squad (`sq init --default-names`; `sq override scaffold --role architect`; the
scaffold given `full_name`, `title`, `mission`, `description`; `sq sync` exit 0):

- frontmatter and index both hold `title: Robert Architect` beside `extra.full_name: Ada Lovelace`
- `sq list -t role`, `sq show ROLE-2`, `sq show ROLE-2 --raw`, `sq show ROLE-2 --json`,
  `sq list --json -t role` and `sq tree ROLE-2` render the stale name; the `sq role architect show`
  card, `sq role list` and the compiled `CLAUDE.md` roster render the declared one
- `sq search Robert` matches, reporting the hit as `title: Robert Architect` — the superseded name
  is not merely displayed, it is indexed
- `sq check` reports nothing

**The same split exists on a second pair.** `create` also stamps `description=role.mission` (read:
`_services/_roster.py:51`) and `to_extra()` carries `mission` into extra, so a declared `mission`
updates `extra.mission` and leaves the item's `description:` on the bundled text — driven: both
frontmatter and index keep the bundled mission. The visible result is a contradiction inside a
single command's output: `sq role architect show` prints the declared mission in its card and the
bundled mission under `## Mission` in the body beneath it, because `agents/role.md.j2:8` renders
`description or extra.get('mission')` and the stale copy wins.

Those two are the whole set. Driven against the eleven fields a role override may declare (read:
`_roles/_models.py`, the `RoleSpec` field block): `title`, `responsibilities`, `agreements`, `model`, `color` and
`can_spawn` have no top-level counterpart and land in `extra` alone; `slug` is validated against
the filename rather than mirrored anywhere; `is_default` has no top-level counterpart, and a
declaration that collides with another role's is already caught — driven, `sq check` on the same
squad: `error: more than one live role carries the default-role designation: ROLE-1, ROLE-2`. Only
`full_name`/`title` and `mission`/`description` are pairs.

One adjacent defect, driven, of a different shape: `description` — the one-liner the generated
pointer carries — is absent from `_EXTRA_FIELD_KEYS` (read: `_roles/_catalog.py:41-52`), so a
declared `description` reaches nothing at all. The generated `.claude/agents/architect.md` kept
`description: "System design and architecture decisions (ADRs)."` while the override declared
otherwise. That is a field the reconciler never carries, not two homes disagreeing; it lives on
this same seam and needs its own item.

## Decision

**1. The resolved value is written to the item's own field. Rendering learns nothing.**

`Item.title` remains the authoritative display name for every item type, roster types included. A
role's resolved `full_name` is projected into it by the one writer that already resolves the
override, and its `mission` into `Item.description` the same way.

**2. The pairing is declared as data, beside the pairing it mirrors.**

`RoleDef` gains a second projection table next to `_EXTRA_FIELD_KEYS` (`_roles/_catalog.py:41-52`)
— the item-field column, `title` from `full_name` and `description` from `mission` — and the
reconciler loops over it exactly as it loops over `to_extra()`. This is the load-bearing half. The
defect class is "one fact, two stored homes, and a writer that knows one of them"; it has already
produced two instances plus a third variant in the dropped `description`. Two hand-written
assignments fix the instances and leave the trap intact. A declared table makes a `RoleDef` field
that also lands on a top-level item field impossible to half-wire, because the pairing is stated
once, in the same class, in the same shape as the pairing that already works.

**3. Where the frontmatter write lands in the order: exactly where the existing one already does.**

`_refresh_catalog_extra` (`_services/_maintenance.py:596`) already writes markdown inside the
transaction body and commits the index last — `update_frontmatter` then `db.add` at `:655-657`,
with the `os.replace` after the body returns. The projection adds fields to the frontmatter block
that single `update_frontmatter` call already writes. It is not a new write and it does not move
in the order; invariant #8 is satisfied by the write it rides. Concretely: the top-level
assignments belong in the pure half at `:648-651`, ahead of the transaction at `:655`, and must
reach the `if not previous` gate at `:652` so a name-only change is not skipped as a no-op. The
rollback at `:659-663` is `extra`-shaped and needs a top-level counterpart, or a skipped write
leaves the in-memory item claiming a value disk does not have — the property that rollback exists
to hold.

**4. The projection changes `title`. It must not route through the rename path.**

A title change through `_update_model` recomputes `slug = slugify(title)` and moves the file (read:
`_services/_items.py:411-425`). A roster item's path slug is its role slug, not a slug of its title
— driven: `agents/roles/ROLE-000002-architect.md` carries `title: Robert Architect`. Title and slug
are already decoupled for roster items and stay so; renaming here would move a file whose name no
override asked to change.

**5. The skew guard does not change, and must not.**

`title` and `description` are top-level frontmatter keys. `_without_permitted_extra_skew` (read:
`_itemfile.py:160-181`) trims only the nested `extra` mapping, so the exemption machinery
structurally cannot reach either of them, and `frontmatter_skew` (`:182`) compares them as ordinary
fields. That is the correct treatment, not an oversight to correct: the reconciler writes markdown
then index in one transaction, so a completed projection leaves the two sides equal, and an
interrupted one leaves markdown ahead — the one sanctioned direction, which `sq repair` heals by
adopting the file's value (read: `_index/_store.py:24-40`). `PERMITTED_EXTRA_SKEW`
(`_itemfile.py:70`) does not widen, and `RoleDef.extra_keys()`, which feeds it, must not gain a
member as a side effect of this change.

**6. The `extra` copies stay.**

Rejected: dropping `full_name` and `mission` from `to_extra()` so the top-level fields become the
single stored home. That is the shape "don't store what you can derive" points at, and it is the
right instinct aimed at the wrong copy — but its cost lands in the integrity core.
`PERMITTED_EXTRA_SKEW` is derived from `RoleDef.extra_keys()` (`_itemfile.py:70`); a key that
leaves the table leaves the exemption, and that exemption is what lets a corpus whose index lags on
those keys converge instead of being refused outright (read: the same reasoning stated at
`_services/_maintenance.py:632-637`). Removing a member therefore means re-adding it by hand as a
legacy name the model no longer writes — trading a duplicated string for a hand-maintained
exception inside the guard. It also moves a documented storage location (`docs/overrides.md:1215`
names `extra.full_name` as where the chosen name is stored) and owes a corpus migration, for no
behavioural difference once a single writer owns both fields.

The roster views' `extra.get(X.FULL_NAME, it.title)` and `extra.get(X.MISSION, it.description)`
fallbacks (read: `_services/_base.py:1088`, `:1091`, `:1104`, `:1107`, `:1121`, `:1133`) stay, as
the fallback for an item predating those keys. Once one writer owns both fields they stop being
load-bearing.

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

- A declared `full_name` or `mission` reaches the item's own record, and the record stops
  disagreeing with itself. Every reader counted above is then correct with no change of its own,
  including the two model dumps, the two matchers and the client, because the field they read is
  the field that was fixed.
- `sq search` stops matching a name the squad no longer uses, and starts matching the one it does.
- `agents/role.md.j2:8` renders `description or extra.get('mission')`. Once one writer owns both
  the precedence is moot, but the line should prefer `extra.get('mission')` to match the roster
  view's order (`_services/_base.py:1091`), so a squad that has not yet synced renders the declared
  mission rather than contradicting its own card.
- Nothing about the reflog changes. Its create and update deltas record the title as it stood at
  the time (`_services/_base.py:738`, `_services/_items.py:671`); a log line is a historical
  record, not a projection, and must not be refreshed.
- No new `sq check` rule follows from this. A corpus split by an earlier release converges on its
  next `sq sync` and says nothing meanwhile; whether the linter should report that divergence
  instead of letting it heal quietly is a separate policy call.

## Falsification the implementation owes

- The rename is the risk on both pairs, so each is its own test with the same shape: an override
  declaring only `full_name`, and one declaring only `mission`, each asserted on four surfaces —
  frontmatter, index, `sq list -t role`, and `sq role <slug> show`. Drop either row from the
  projection table and the matching test must go red naming the bundled value.
- A test asserting only that frontmatter agrees with `extra` passes on a projection that writes the
  stale value into both. Assert the declared string, never agreement between the two copies.
- An override declaring neither field must leave `title` and `description` byte-identical — the
  test that catches a projection writing unconditionally instead of on a diff, and the one that
  keeps the `if not previous` gate honest.
- Cover the file shapes, not only the fields: a bundled-slug override, a `<tech>-dev.toml` on the
  second of two developers (the other developer's `title` must be untouched), an override on a
  retired role, and one declaring a value equal to the current one, which must take the no-op path.
- Assert the item's path is unchanged across a `full_name` rename. Route the projection through the
  title-rename path instead and that test must go red on a moved file.
- `sq check` clean on a squad carrying a `full_name`-declaring override, both before and after the
  sync that applies it.

## Amendment note — 2026-09-02: §6 is overtaken, and the exemption stays unconditional

§6 ("The `extra` copies stay") rejected dropping the mirrored definition fields from
`RoleDef.to_extra()`. That rejection has since been reversed by ADR-776's third 2026-09-01
amendment §2(d), which retired the mirror key by key. This note records the reversal at this end —
§6 is the clause a reader is sent to, including by ADR-783's consequence "the exemption is
deliberate and ADR-766 §6 owns the trade" — and rules the question the reversal left open: whether
`PERMITTED_EXTRA_SKEW` is now a legacy-corpus exemption that should be conditioned on the corpus
rather than granted unconditionally.

### 1. What §6's cost argument got wrong

§6 blocked the removal on the ground that "a key that leaves the table leaves the exemption", so
removing a member "means re-adding it by hand as a legacy name the model no longer writes —
trading a duplicated string for a hand-maintained exception inside the guard".

Nothing was hand-re-added, and nothing needed to be. §6 treated leaving the exemption as a cost to
be bought back; it is the safe direction. A key that leaves is compared like any other field again,
and the worst that produces is a spurious refusal on a corpus whose index lags — which `sq repair`
clears by adopting the file's value, losing nothing. The unsafe direction is the other one: an
exempted key nothing writes that way masks a genuine skew silently, index-wins. §6 weighed a
duplicated string against a hand-maintained exception and never priced the asymmetry between those
two failure modes, which is the term that decides it.

### 2. Measured, before ruling — what the exemption still covers

`PERMITTED_EXTRA_SKEW` is `frozenset(RoleDef.extra_keys())`, derived rather than hand-listed.
Today that is **two keys: `slug` and `model`**, and per item (`_exempt_extra_keys`) it resolves to:

- a **developer** role — nothing exempt at all;
- any **other** role — both keys;
- anything that is not a role item — nothing.

On the one shape that is exempted, neither key carries an operator answer a masked skew could lose:

- **`slug`** is written by `to_extra()` for every role, at activation, inside the transaction that
  creates the item. It is the dispatch identity, frozen non-renamable (ADR-776's third amendment
  §2(d), citing ADR-85 §4); `sq role` exposes show, regen, rm, status and set-default and no verb
  that mutates it. Disk can only lead the index on it through a legacy corpus or a hand edit.
- **`model`** is not written for a non-developer role by anything. It sits in
  `RoleDef._DEV_EXTRA_FIELD_KEYS`, a separate table `to_extra()` adds only when `is_dev`; every
  other `X.MODEL` site in `src/` is a read; and a developer role — the one shape whose `model` *is*
  an operator setting — receives no exemption at all, so its `model` is compared like any ordinary
  transaction-guarded field.

The keys whose silent loss would matter are already outside the set, and outside it deliberately:
`is_default` (operator-settable through `sq role set-default`, whose silent reversion by the next
sync was a live defect) and `full_name` (operator-settable through `sq role activate --name` /
`sq dev add --name`). Both are retained as stored data no document answers, and both were kept out
of `_EXTRA_FIELD_KEYS` precisely so they would not inherit the exemption. Membership is pinned to
the literal pair by test, against an unreviewed widening, which is the only direction that can
introduce a masked skew.

### 3. Ruled: no corpus precondition

The exemption stays unconditional. Three reasons, in order of weight:

1. **There is nothing left to gate.** Conditioning exists to stop an exemption masking a live
   answer. On the exempted shape neither remaining key can hold one, so the grant costs no
   detection that anything would otherwise get. The finding this rules on was filed against a
   ten-key set that blanketed a role's whole definition; that set no longer exists.
2. **No vehicle is available.** ADR-776's fourth amendment §4 refuses the schema stamp as an axis
   for corpus behaviour, and a corpus precondition is exactly that axis. Gating would have to
   invent a second one for a two-key residue.
3. **The legacy case the exemption was narrowed *to* is still real.** A squad last synced by a
   release predating `_refresh_catalog_extra`'s index mirror holds an index that lags on these
   keys; comparing them would refuse the very sync that converges them. That is what is left, and
   it is what `_itemfile.py`'s justification now argues from — no longer the retired `link_role`
   writer it inherited the argument from.

### 4. What this does not change

No code changes on this ruling: the set, the per-item resolution and the justification paragraph
already stand where it lands. `sq repair` remains both the vehicle that clears a spurious refusal
and the one that strips the retired keys; that convergence is a consequence of repair rebuilding
the index from markdown in both cases, not a new coupling. Everything §6 said about `title` and
`description` — that they are top-level fields the exemption machinery structurally cannot reach —
is unaffected and stands; §5 stands entire.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T19:47:10Z] Catherine Manager:
  - Verified the two claims this ruling turns on before accepting. PERMITTED_EXTRA_SKEW is literally frozenset({X.SKILLS, *RoleDef.extra_keys()}) at _itemfile.py:70, so dropping a key from that table would shrink the guard exemption and trade a duplicated string for a hand-maintained exception in the integrity core. The second field pair is real: _services/_roster.py:51 and :82 stamp description from role.mission, and templates/agents/role.md.j2:8 renders description or extra.get(mission), so a declared mission makes one command contradict itself. Accepted as written, projection table included.
- [2026-08-21T19:47:48Z] Pierre Chat:
  - No sq check rule for a stored title disagreeing with the resolved full_name. The projection repairs it on the next sync, so the disagreement is transient by construction, and a gate that fires on every pre-fix corpus until someone syncs is noise in a repo where sq check must stay clean.
- [2026-08-22T10:01:24Z] Robert Architect:
  - Section 5 confirmed by drive, not just by structure. Simulated the interrupted write both ways on fresh core-roles squads: with the divergence confined to extra.full_name (the pre-projection shape, still reachable since that key is exempt), sq sync exits 0 with no warning and overwrites markdown Ada Lovelace with the index stale Robert Architect — a committed markdown value destroyed silently, sq check clean throughout. With the divergence on the projected title, the whole write is skipped, markdown is preserved on title AND full_name, and sq repair adopts the file value. So the guard exemption was hiding the one skew direction _index/_store.py:18-38 forbids, and section 5 was right for a stronger reason than it states.
  - The reporting half this decision deferred as a separate policy call is now ruled on ADR-783 (@manager @qa). Nothing here changes.
<!-- sq:discussion:end -->
