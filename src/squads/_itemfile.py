"""Read/write the markdown file backing an item, keeping frontmatter and body in sync.

The ``.md`` frontmatter is the durable source of truth; ``sq`` rewrites only the frontmatter
(and marker sections), never the agent-authored body.

**Atomic by construction.** Every writer here (``write_new``, ``update_frontmatter``,
``write_text``, ``rewrite_ids``) goes through :func:`squads._aio.atomic_write_text` — temp file
+ fsync + ``os.replace`` in one thread hop — so a process killed mid-write leaves the file
complete-or-previous, never a truncated prefix. This is the *only* place a mutation core should
reach for; a bare ``_aio.write_text`` on an item ``.md`` reintroduces the truncation hazard.

**Ordering rule this module's callers must keep.** Within a transaction, every write to an
item's markdown — via this module's functions — happens inside the transaction body, before it
returns; the index commit (``IndexStore``'s own atomic replace) is always the transaction's
last write. A markdown write may never run after the commit — a killed process must always
leave the markdown ahead of (or equal to) the index, never behind, so ``sq repair`` can
converge on the file's state.

A transaction that writes several markdown files this way is still not atomic *across* those
files — there is no cross-file barrier, only the per-file one above. That is fine: each file is
durable, on its own, before the index commits, so the skew a crash between two of them leaves
is the same one-sided, repair-safe shape as a single-file write, just with more files on the
ahead side.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from squads import _aio
from squads._errors import SquadsError
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._roles._catalog import RoleDef
from squads._sections import join_frontmatter, replace_frontmatter, split_frontmatter
from squads._workflow._models import ROSTER_ROLE

#: The durability model's permitted skew, as a property of the *field* rather than of whichever
#: writer happens to persist it: every catalog-merged identity field a predefined role's
#: ``extra`` carries (``RoleDef.to_extra()``'s key set, via :meth:`RoleDef.extra_keys`).
#: Derived from ``RoleDef.extra_keys()`` (not a hand-duplicated list of key names) so a field
#: later added to the catalog is exempt automatically, the same day it starts being written
#: this way -- never a second list to remember to update.
#:
#: The case this covers is a *legacy* one. ``_refresh_catalog_extra`` mirrors its merge into
#: the index inside the transaction that writes the frontmatter, because those values carry a
#: project role override's title onto the item and every consumer of a role title reads the
#: index. The exemption is kept deliberately, for a squad last synced by a release that shipped
#: without that mirror: its index already lags on these keys, and comparing them would refuse
#: the very sync that would otherwise converge them.
#:
#: This is the *whole* permitted set -- which of it actually applies to a given item is a
#: further, per-item question (see :func:`_exempt_extra_keys`): these are ``extra`` key
#: *names*, and the same name can legitimately belong to a different item type/role shape
#: that ``_refresh_catalog_extra`` never touches (e.g. a skill item's own ``model``). A dev
#: role's own ``RoleDef`` fields (its ``model``, ``title``, ...) are *not* such a case --
#: ``_refresh_catalog_extra`` resolves a dev role too, against a base built from the item's
#: own stored identity and never a regenerated one, so those fields are ordinary,
#: transaction-guarded ones for a dev role exactly like for any other. See
#: :func:`_exempt_extra_keys` for what that means for the per-item exemption below.
PERMITTED_EXTRA_SKEW: frozenset[str] = frozenset(RoleDef.extra_keys())


#: The frontmatter keys whose absent-value default is *invented* at load time rather than
#: derived from the file (:func:`squads._models._item._parse_dt` falls back to ``clock.now()``
#: so a legacy or hand-authored ``.md`` loads at all).
#:
#: They are the one part of the ``from_frontmatter`` round trip that is not a function of the
#: file's own bytes: load the same absent-timestamp file twice and you get two different
#: values. A skew comparison that includes them therefore reports a divergence on a key the
#: file says *nothing* about — and does so on every read, so the item is refused for good, with
#: a "run `sq repair`" pointer that repair structurally cannot honour (repair rebuilds the
#: index from markdown; it never rewrites markdown, so the key stays absent and the next read
#: invents a new value again).
#:
#: The absence itself is not lost, only left out of the comparison: every write seam persists
#: the whole ``to_frontmatter_dict()`` (see :func:`update_frontmatter` and the service's
#: section-edit core), so the first successful mutation writes the index's value into the file
#: and heals it permanently. Excluding them is what makes that first mutation possible.
#:
#: This is narrow on purpose. It applies only when the raw on-disk frontmatter has no value for
#: the key at all; a timestamp the file *does* carry is compared like any other field, and one
#: it carries unparseably still fails the load boundary as a ``SquadsError``.
INVENTED_WHEN_ABSENT: frozenset[str] = frozenset({"created_at", "updated_at"})


def _exempt_extra_keys(item: Item) -> frozenset[str]:
    """The subset of :data:`PERMITTED_EXTRA_SKEW` that actually applies to *item* --
    answering "what does a regen writer persist outside a transaction for *this* item",
    not "what key names does the exemption know about in general".

    - A dev role (``extra.is_dev`` truthy) gets none of it. It once got a narrower exemption of
      its own -- ``extra.skills`` alone, since the resolved-skills cache resynced every role's
      ``extra`` this way, dev roles included -- but that cache and its writer are gone, and
      nothing replaced them. ``_refresh_catalog_extra`` *does* resolve a dev role too, against
      a base built from the item's own stored identity rather than a regenerated one, but it
      writes markdown first and mirrors into the index inside the same transaction, so no
      permanent index lag is introduced and nothing needs exempting on that account either.
      Every field on a dev role (``model``, ``title``, ...) is therefore an ordinary,
      transaction-guarded field, and must be compared like any other -- widening this would
      reopen the exact loss class the exemption otherwise guards against: interrupt a dev
      role's ``--set model=haiku``, then edit it through any other seam, and the stale
      index-loaded value would silently overwrite the committed one.
    - Any other role gets the whole permitted set. A role is identified here by
      ``item.type == ROSTER_ROLE`` -- the item's own declared type, not a key inside its
      ``extra`` -- rather than by asking whether its slug resolves in the *bundled* catalog.
      ``_refresh_catalog_extra`` itself resolves through ``resolve_role``, which also merges a
      project-override role defined under a brand-new slug; this module has no ``squad_dir``
      to replicate that resolution, so it widens to "any non-dev role" instead of narrowing to
      "any bundled-slug role". That is deliberately the safe direction: under-exempting
      degrades to a real (if spurious) refusal -- annoying, but `sq repair` clears it and
      nothing is lost; over-exempting a key nothing actually writes this way risks masking a
      genuine skew on it instead. The corresponding gap: a role item whose slug resolves in
      *neither* the bundled catalog nor an override (its backing definition vanished after the
      role was activated) is, by this same widening, still exempted even though
      ``_refresh_catalog_extra`` no longer touches it -- a real skew on such an orphaned
      role's catalog fields would go undetected. That's narrower than the false refusal this
      widening fixes (which hit *every* override-defined role), and the same under/over
      tradeoff resolves it the same way. Keying off the type rather than an ``extra`` key
      (``extra.mission``, previously) is what lets this discriminator outlive the mirror: the
      type is never a mirrored field and is never at risk of going stale or absent.
    - Anything else (not a role item) gets none of it -- a coincidental key-name collision
      with another item's own ``extra`` (e.g. a skill item's own ``model``) is never this
      exemption's business.
    """
    if item.extra.get(X.IS_DEV):
        return frozenset()
    if item.type == ROSTER_ROLE:
        return PERMITTED_EXTRA_SKEW
    return frozenset()


def read_frontmatter(
    path: Path | None = None, *, text: str | None = None, source: str | None = None
) -> dict[str, Any]:
    """Parse frontmatter from *path* or already-read *text*.

    The offending file's name reaches a malformed-YAML error via *source* (defaults to
    *path* when given, e.g. by a caller that already read the text itself but still holds
    the path it came from).
    """
    if text is None:
        if path is None:
            raise ValueError("read_frontmatter requires a path or text")
        text = path.read_text(encoding="utf-8")
    return split_frontmatter(text, source=source if source is not None else _label(path))[0]


def _label(path: Path | None) -> str | None:
    return str(path) if path is not None else None


def _without_permitted_extra_skew(data: dict[str, Any], item: Item) -> dict[str, Any]:
    """*data* (a ``to_frontmatter_dict()`` output) with *item*'s own :func:`_exempt_extra_keys`
    removed from its nested ``extra`` mapping, if present — the mechanics behind
    ``frontmatter_skew``'s unconditional exclusion. A no-op copy when ``extra`` doesn't carry
    any exempt keys, so the overwhelmingly common case (a non-role item, or a role nothing
    has ever resynced) never allocates anything extra."""
    extra = data.get("extra")
    if not isinstance(extra, dict):
        return data
    extra_typed = cast("dict[str, Any]", extra)
    exempt = _exempt_extra_keys(item)
    if not (extra_typed.keys() & exempt):
        return data
    trimmed = {k: v for k, v in extra_typed.items() if k not in exempt}
    out = dict(data)
    if trimmed:
        out["extra"] = trimmed
    else:
        out.pop("extra", None)
    return out


@dataclass(frozen=True, slots=True)
class SkewKey:
    """One frontmatter key on which :func:`frontmatter_skew` found disk and index to
    disagree, classified so a refusal never asserts a cause the reader can
    disprove.

    ``stale_encoding`` is true only when **both** hold: the *raw* on-disk value for this key
    (before the load round trip) already equals what the index holds, **and** the round trip
    produced the diverging value from that raw key alone. A fold that drew on a *second* raw
    key — the pre-0.2 ``extra.ref_kinds`` map folded into ``refs`` is the one case today — is
    information-adding even when the key's own raw value matches, because the map named a
    kind the index never held; that stays ``stale_encoding=False`` and keeps today's
    divergence wording, same as an ordinary hand-edit.
    """

    name: str
    stale_encoding: bool


def _drew_on_second_raw_key(key: str, disk_data: dict[str, Any]) -> bool:
    """Whether *key*'s fold, on this on-disk frontmatter, consulted a raw key other than
    itself to produce its round-tripped value.

    Only ``refs`` has such a dependency today: :func:`~squads._models._item.fold_legacy_kinds`
    merges a pre-0.2 ``extra.ref_kinds`` map into it (see :func:`~squads._models._item._read_refs`,
    whose own ``legacy_map`` this mirrors exactly — a non-mapping or empty ``ref_kinds``
    contributes nothing, same as there). A key with no such second-key dependency can never
    return true here, which is the safe default: it only ever *widens* what counts as a real
    divergence, never narrows it into a false stale-encoding claim.
    """
    if key != "refs":
        return False
    extra = disk_data.get("extra")
    if not isinstance(extra, dict):
        return False
    legacy = cast("dict[str, Any]", extra).get("ref_kinds")
    legacy_map = cast("dict[str, Any]", legacy) if isinstance(legacy, dict) else {}
    return bool(legacy_map)


def _classify_skew(key: str, disk_data: dict[str, Any], base_dict: dict[str, Any]) -> SkewKey:
    """*key*'s :class:`SkewKey` verdict — the stale-encoding-versus-divergence test applied
    at the one site that already holds both the raw on-disk frontmatter and the
    index-serialized *base_dict*."""
    raw_equal = disk_data.get(key) == base_dict.get(key)
    stale_encoding = raw_equal and not _drew_on_second_raw_key(key, disk_data)
    return SkewKey(key, stale_encoding=stale_encoding)


def stale_encoding_clause(fields: Iterable[str]) -> str:
    """The shared explanation for a stale-index-encoding skew on *fields* — reused by
    :func:`skew_message` and ``sq check``'s finding wording
    (``_services/_maintenance.py::_drift_message``) so one state is explained in the same
    words on both surfaces. States the true cause — a non-canonical index
    encoding — rather than a divergence the reader can open the file and disprove."""
    return f"the index holds a non-canonical encoding of {', '.join(fields)}, not a divergence"


def frontmatter_skew(text: str, base: Item, *, default_kind: str) -> list[SkewKey]:
    """The frontmatter keys on which *text*'s on-disk frontmatter diverges from what *base*
    — the item as loaded before the pending mutation's own delta — would itself serialize,
    each classified as :class:`SkewKey` (a real divergence, or a stale index encoding — see
    there for the test).

    The disk side is put through the load round trip
    (``Item.from_frontmatter(...).to_frontmatter_dict()``), which structurally collapses every
    known load/parse-time correction (the legacy ``extra.severity`` location, the pre-0.2
    ``extra.ref_kinds`` map — folded to canonical bare-or-spelled form against
    *default_kind*, see :func:`~squads._models._item.fold_legacy_kinds` — a padded id
    recomputed from prefix + sequence number, key order, and absent-versus-``None``) — so a
    non-empty result means a real skew, not a by-design divergence. **The two sides are not
    symmetric**: *base* is already a loaded, validated ``Item`` and is serialized directly
    (``base.to_frontmatter_dict()``), never re-run through ``from_frontmatter`` — the index
    side of this comparison never folds. That asymmetry is why *default_kind* must be
    resolved and folded in **on the disk side**, at read time, rather than reconciled after
    the fact: running the index side through the same fold does not converge it, since a
    legacy ``extra.ref_kinds`` map is real information the index side never held. *base*'s own
    ``path`` is passed to ``from_frontmatter`` deliberately: that field is a keyword argument
    of the reconstruction, and the wrong one only risks a constructor error (an invalid
    derived slug), never a spurious divergence, since ``path`` itself is not part of
    ``to_frontmatter_dict()``'s output.

    In the normal case the two sides are identical — the last successful mutation wrote both
    from one item — so an empty return is the expected result, not evidence the check is inert.

    Whichever of :data:`PERMITTED_EXTRA_SKEW` actually applies to *base* (see
    :func:`_exempt_extra_keys`) is excluded from every comparison unconditionally, for every
    caller — a property of those particular ``extra`` keys *on this item*, not something a
    writer opts into. They are the durability decision's named permitted skew: "re-derivable
    regions of an item ``.md`` the committing transaction did not mirror into the index" (a
    non-dev role's catalog-merged fields, on a squad a pre-mirror release last synced). Those
    fields were written to the file WITHOUT ever going through ``store.transaction()``, so an
    index loaded before that mirror landed never carries the current generation of that value
    even in the fully healthy case — disk is *permanently* ahead of the index on those keys,
    by design, not because of an interrupted write. Comparing them like an ordinary field
    would false-refuse the very next mutation, through *any* seam, on such a squad — which is
    exactly what happened before this exclusion moved here: it used to be an opt-in a writer
    passed (``ignore_extra_keys``), so every other seam compared the field anyway. This is not
    a load/parse-time correction the round trip can be taught — the two sides are reading
    genuinely different sources of truth for these keys — so they are named here explicitly
    rather than folded into the general round trip.

    The exclusion is conditioned on *base* actually being the shape a regen writer touches
    this way (any non-dev role, for the whole set) — never on the key names alone, which the
    same ``extra`` bag can carry for an unrelated reason (a dev role's own,
    transaction-guarded ``model``; a skill item's own ``model``).
    """
    disk_data, _ = split_frontmatter(text, source=base.path)
    disk_dict = Item.from_frontmatter(
        disk_data, path=base.path, default_kind=default_kind
    ).to_frontmatter_dict()
    base_dict = base.to_frontmatter_dict()
    disk_dict = _without_permitted_extra_skew(disk_dict, base)
    base_dict = _without_permitted_extra_skew(base_dict, base)
    keys = (disk_dict.keys() | base_dict.keys()) - _invented_timestamps(disk_data)
    diverging = sorted(k for k in keys if disk_dict.get(k) != base_dict.get(k))
    return [_classify_skew(k, disk_data, base_dict) for k in diverging]


def _invented_timestamps(disk_data: dict[str, Any]) -> frozenset[str]:
    """Which of :data:`INVENTED_WHEN_ABSENT` the on-disk frontmatter carries no value for, and
    which the round trip therefore filled in with an invented ``now`` on *this* read.

    Read off the **raw** parsed frontmatter, before the round trip — once the value has been
    invented the two cases are indistinguishable, which is precisely why the comparison had to
    be told about them here rather than being able to work it out from its own two inputs.
    """
    return frozenset(k for k in INVENTED_WHEN_ABSENT if disk_data.get(k) is None)


def skew_message(base: Item, diverging: list[SkewKey]) -> str:
    """The shared, human-readable report for a confirmed skew on *base* — reused by the
    refusal raised at a single-mutation write seam, the skip-and-report line ``sq sync``
    emits for a drifted roster item, and the ``ImportIssue`` the bulk importer's pre-pass
    collects for a drifted pre-existing target.

    A real divergence keeps today's wording unchanged; a stale index encoding gets
    :func:`stale_encoding_clause` instead, never the divergence wording it would falsify. A
    mixed item — one key of each — reports both clauses, neither describing the other's
    state."""
    diverged = [k.name for k in diverging if not k.stale_encoding]
    stale = [k.name for k in diverging if k.stale_encoding]
    clauses: list[str] = []
    if diverged:
        clauses.append(f"on-disk frontmatter has diverged from the index ({', '.join(diverged)})")
    if stale:
        clauses.append(stale_encoding_clause(stale))
    return f"{base.id}: {'; '.join(clauses)} — run `sq repair` before mutating {base.id} again"


def ensure_no_skew(text: str, base: Item, *, default_kind: str) -> None:
    """Raise :class:`SquadsError` when *text*'s on-disk frontmatter has drifted from *base*.

    Writing over it now — substituting the whole frontmatter block from an index-derived
    item — would silently discard whatever survived on disk since the index last saw it.
    Every single-mutation write seam calls this before every rewrite; the two roster-regen
    writers that persist an ADR-named never-mirrored-into-the-index value get the same
    exemption everyone else does, since :func:`frontmatter_skew` excludes
    :data:`PERMITTED_EXTRA_SKEW` unconditionally rather than by caller opt-in — that permitted,
    permanent skew is never mistaken for a real one at *any* seam. Batch paths call
    :func:`frontmatter_skew` directly instead, since their response is not a plain refusal.

    *default_kind* is threaded straight through to :func:`frontmatter_skew` — a **required**
    keyword, resolved by the caller (a ``Service`` mixin with ``self.spec`` in hand) once per
    pass rather than per item, so a spec declaring the wrong number of default ref kinds fails
    as one clean refusal naming the spec instead of raising partway through a rebuild.
    """
    diverging = frontmatter_skew(text, base, default_kind=default_kind)
    if diverging:
        raise SquadsError(skew_message(base, diverging))


def missing_file_error(item_id: str) -> SquadsError:
    """The clean, actionable error a missing indexed file converts into for a caller that
    wants the item's *content*, not a signal — see :func:`read_item_text`. Shared with the
    service layer's ``ServiceCore._read_item_file`` so the message is written once.
    """
    return SquadsError(
        f"{item_id}'s file is missing from its indexed location — an interrupted "
        "rename or retype likely left the index stale; run `sq repair`"
    )


async def read_item_text(path: Path, item_id: str) -> str:
    """Read *item_id*'s file at *path*, converting a missing file into :func:`missing_file_error`.

    An interrupted title-changing update or retype can physically move a file before the
    index commits, leaving *path* (built from the index-loaded item) stale. Unlike
    :func:`~squads._aio.read_text`, which propagates ``FileNotFoundError`` unchanged for the
    two callers that read it as a signal rather than a failure — ``check``'s confirm round
    stale-path fallback and the bulk importer's pre-pass skew guard, both in ``_services/`` —
    every other reader of an item's file wants the content outright and has no fallback of
    its own to try, so the exception becomes a message naming the item and pointing at
    ``sq repair``. This is the read side of the write seams that already refuse cleanly on a
    real skew (see :func:`ensure_no_skew`): both directions of "can't safely proceed on this
    item until it's repaired" now report the same way.
    """
    try:
        return await _aio.read_text(path)
    except FileNotFoundError as exc:
        raise missing_file_error(item_id) from exc


async def write_new(path: Path, item: Item, rendered_body: str) -> None:
    """Create a brand-new item file: frontmatter + the rendered (templated) body.

    No prior file to diverge from — a create never goes through the skew guard.
    """
    text = join_frontmatter(item.to_frontmatter_dict(), rendered_body)
    await _aio.mkdir(path.parent, parents=True, exist_ok=True)
    await _aio.atomic_write_text(path, text)


async def update_frontmatter(path: Path, item: Item, base: Item, *, default_kind: str) -> None:
    """Rewrite the frontmatter from the item; body is preserved verbatim.

    The read is :func:`read_item_text`, so a stale index-derived *path* (an interrupted
    rename/retype) reports cleanly instead of a raw ``FileNotFoundError``. Refuses
    (:class:`SquadsError`) if the on-disk frontmatter has diverged from what *base* — the item
    as loaded before this mutation's own delta, captured by the caller's pure half — would
    itself have serialized: see :func:`ensure_no_skew`. *default_kind* passes straight
    through to it.
    """
    text = await read_item_text(path, item.id)
    ensure_no_skew(text, base, default_kind=default_kind)
    await _aio.atomic_write_text(
        path, replace_frontmatter(text, item.to_frontmatter_dict(), source=str(path))
    )


async def write_text(path: Path, text: str) -> None:
    """Atomically overwrite an *existing* item file with fully-formed new text.

    The item-file layer's general-purpose exit for callers that have already built the whole
    new file contents themselves (a section edit, a sub-entity block rewrite, a retype's
    frontmatter+body rewrite, …) rather than growing a bespoke ``_aio.atomic_write_text`` import
    at each such call site — so every write of an item ``.md`` funnels through this module and
    "the item-file layer exposes only the atomic primitive" stays structurally true.
    """
    await _aio.atomic_write_text(path, text)


async def rewrite_ids(paths: Iterable[Path], remap: dict[str, str]) -> list[Path]:
    """Whole-word substitution of every old ID → new ID across the given files.

    Replaces all occurrences of ``\\bOLD\\b → NEW`` (exact whole-word match so e.g. a longer ID
    sharing a prefix is not touched).  Returns the list of paths that were actually modified.
    """
    touched: list[Path] = []
    for path in paths:
        text = await _aio.read_text(path)
        new_text = text
        for old, new in remap.items():
            new_text = re.sub(rf"\b{re.escape(old)}\b", new, new_text)
        if new_text != text:
            await _aio.atomic_write_text(path, new_text)
            touched.append(path)
    return touched
