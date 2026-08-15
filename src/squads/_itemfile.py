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
from pathlib import Path
from typing import Any, cast

from squads import _aio
from squads._errors import SquadsError
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._roles._catalog import RoleDef
from squads._sections import join_frontmatter, replace_frontmatter, split_frontmatter

#: The durability model's permitted skew, as a property of the *field* rather than of whichever
#: writer happens to persist it: the role's resolved-skills cache (``X.SKILLS``) and every
#: catalog-merged identity field a predefined role's ``extra`` carries (``RoleDef.to_extra()``'s
#: key set, via :meth:`RoleDef.extra_keys`). Derived from ``RoleDef.extra_keys()`` (not a
#: hand-duplicated list of key names) so a field later added to the catalog is exempt
#: automatically, the same day it starts being written this way -- never a second list to
#: remember to update.
#:
#: The two halves are exempt for different reasons, and only one of them is still structural:
#:
#: - ``X.SKILLS`` is written by a roster-regen path that never opens ``store.transaction()``
#:   (`link-role`/`unlink-role`'s partial resync, `sync`'s full sweep), so the index-loaded
#:   side of the comparison cannot carry its current generation -- not even on a fully healthy
#:   role that was never interrupted. Comparing it like an ordinary field would refuse the very
#:   next mutation through any *other* seam after such a resync ever ran.
#: - The catalog-merged fields used to be in that same position and no longer are:
#:   ``_refresh_catalog_extra`` now mirrors its merge into the index inside the transaction
#:   that writes the frontmatter, because those values carry a project role override's title
#:   onto the item and every consumer of a role title reads the index. Their exemption is kept
#:   deliberately, for the *legacy* case it still covers: a squad last synced by a release
#:   without that mirror has an index that already lags on these keys, and comparing them would
#:   refuse the very sync that would otherwise converge them.
#:
#: This is the *whole* permitted set -- which of it actually applies to a given item is a
#: further, per-item question (see :func:`_exempt_extra_keys`): these are ``extra`` key
#: *names*, and the same name can legitimately belong to a different item type/role shape
#: that neither regen writer ever touches (e.g. a skill item's own ``model``, or a dev role
#: RoleDef.MODEL, which is a plain transaction-guarded field for a dev role since
#: ``_refresh_catalog_extra`` explicitly skips dev roles).
PERMITTED_EXTRA_SKEW: frozenset[str] = frozenset({X.SKILLS, *RoleDef.extra_keys()})


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

    - A dev role (``extra.is_dev`` truthy) never goes through ``_refresh_catalog_extra``
      (it explicitly skips dev roles), so none of ``RoleDef.extra_keys()`` is exempt for
      one -- only ``extra.skills`` is, since ``_refresh_role_skills_extra`` resyncs every
      role's resolved-skills cache this way, dev roles included. Every other field
      (``model``, ``title``, ...) is an ordinary, transaction-guarded field on a dev role,
      and must be compared like any other -- the exact loss class this exemption otherwise
      reopens: interrupt a dev role's ``--set model=haiku``, then edit it through any other
      seam, and the stale index-loaded value would silently overwrite the committed one.
    - Any other role gets the whole permitted set. A role is identified here by
      ``extra.mission`` -- the one key only a role's own ``RoleDef.to_extra()`` merge ever
      writes (skill/operator/work-item extra never carries it) -- rather than by asking
      whether its slug resolves in the *bundled* catalog. ``_refresh_catalog_extra`` itself
      resolves through ``resolve_role``, which also merges a project-override role defined
      under a brand-new slug; this module has no ``squad_dir`` to replicate that resolution,
      so it widens to "any non-dev role" instead of narrowing to "any bundled-slug role".
      That is deliberately the safe direction: under-exempting degrades to a real (if
      spurious) refusal -- annoying, but `sq repair` clears it and nothing is lost; over-
      exempting a key nothing actually writes this way risks masking a genuine skew on it
      instead. The corresponding gap: a role item whose slug resolves in *neither* the
      bundled catalog nor an override (its backing definition vanished after the role was
      activated) is, by this same widening, still exempted even though
      ``_refresh_catalog_extra`` no longer touches it -- a real skew on such an orphaned
      role's catalog fields would go undetected. That's narrower than the false refusal
      this widening fixes (which hit *every* override-defined role), and the same
      under/over tradeoff resolves it the same way.
    - Anything else (no ``extra.mission`` at all) gets none of it -- a coincidental
      key-name collision with another item's own ``extra`` (e.g. a skill item's own
      ``model``) is never this exemption's business.
    """
    if item.extra.get(X.IS_DEV):
        return frozenset({X.SKILLS})
    if X.MISSION in item.extra:
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


def frontmatter_skew(text: str, base: Item) -> list[str]:
    """The frontmatter keys on which *text*'s on-disk frontmatter diverges from what *base*
    — the item as loaded before the pending mutation's own delta — would itself serialize.

    Both sides are put through the identical round trip
    (``Item.from_frontmatter(...).to_frontmatter_dict()``), which structurally collapses every
    known load/parse-time correction (the legacy ``extra.severity`` location, the pre-0.2
    ``extra.ref_kinds`` map, a padded id recomputed from prefix + sequence number, key order,
    and absent-versus-``None``) — so a non-empty result means a real skew, not a by-design
    divergence. *base*'s own ``path`` is passed to ``from_frontmatter`` deliberately: that
    field is a keyword argument of the reconstruction, and the wrong one only risks a
    constructor error (an invalid derived slug), never a spurious divergence, since ``path``
    itself is not part of ``to_frontmatter_dict()``'s output.

    In the normal case the two sides are identical — the last successful mutation wrote both
    from one item — so an empty return is the expected result, not evidence the check is inert.

    Whichever of :data:`PERMITTED_EXTRA_SKEW` actually applies to *base* (see
    :func:`_exempt_extra_keys`) is excluded from every comparison unconditionally, for every
    caller — a property of those particular ``extra`` keys *on this item*, not something a
    writer opts into. They are the durability decision's named permitted skew: "re-derivable
    regions of an item ``.md`` the committing transaction did not mirror into the index" (the
    role's resolved-skills cache; a non-dev role's catalog-merged fields). Those write
    their value to the file WITHOUT ever going through ``store.transaction()``, so the
    index-loaded ``base`` never carries the current generation of that value even in the fully
    healthy case — disk is *permanently* ahead of the index on those keys, by design, not
    because of an interrupted write. Comparing them like an ordinary field would false-refuse
    the very next mutation, through *any* seam, after any such resync ever ran — which is
    exactly what happened before this exclusion moved here: it used to be an opt-in a writer
    passed (``ignore_extra_keys``), so every other seam compared the field anyway. This is not
    a load/parse-time correction the round trip can be taught — the two sides are reading
    genuinely different sources of truth for these keys — so they are named here explicitly
    rather than folded into the general round trip.

    The exclusion is conditioned on *base* actually being the shape a regen writer touches
    this way (a dev role only for ``extra.skills``; any other role for the whole set) — never
    on the key names alone, which the same ``extra`` bag can carry for an unrelated reason
    (a dev role's own, transaction-guarded ``model``; a skill item's own ``model``).
    """
    disk_data, _ = split_frontmatter(text, source=base.path)
    disk_dict = Item.from_frontmatter(disk_data, path=base.path).to_frontmatter_dict()
    base_dict = base.to_frontmatter_dict()
    disk_dict = _without_permitted_extra_skew(disk_dict, base)
    base_dict = _without_permitted_extra_skew(base_dict, base)
    keys = (disk_dict.keys() | base_dict.keys()) - _invented_timestamps(disk_data)
    return sorted(k for k in keys if disk_dict.get(k) != base_dict.get(k))


def _invented_timestamps(disk_data: dict[str, Any]) -> frozenset[str]:
    """Which of :data:`INVENTED_WHEN_ABSENT` the on-disk frontmatter carries no value for, and
    which the round trip therefore filled in with an invented ``now`` on *this* read.

    Read off the **raw** parsed frontmatter, before the round trip — once the value has been
    invented the two cases are indistinguishable, which is precisely why the comparison had to
    be told about them here rather than being able to work it out from its own two inputs.
    """
    return frozenset(k for k in INVENTED_WHEN_ABSENT if disk_data.get(k) is None)


def skew_message(base: Item, diverging: list[str]) -> str:
    """The shared, human-readable report for a confirmed skew on *base* — reused by the
    refusal raised at a single-mutation write seam, the skip-and-report line ``sq sync``
    emits for a drifted roster item, and the ``ImportIssue`` the bulk importer's pre-pass
    collects for a drifted pre-existing target."""
    fields = ", ".join(diverging)
    return (
        f"{base.id}: on-disk frontmatter has diverged from the index ({fields}) — "
        f"run `sq repair` before mutating {base.id} again"
    )


def ensure_no_skew(text: str, base: Item) -> None:
    """Raise :class:`SquadsError` when *text*'s on-disk frontmatter has drifted from *base*.

    Writing over it now — substituting the whole frontmatter block from an index-derived
    item — would silently discard whatever survived on disk since the index last saw it.
    Every single-mutation write seam calls this before every rewrite; the two roster-regen
    writers that persist an ADR-named never-mirrored-into-the-index value get the same
    exemption everyone else does, since :func:`frontmatter_skew` excludes
    :data:`PERMITTED_EXTRA_SKEW` unconditionally rather than by caller opt-in — that permitted,
    permanent skew is never mistaken for a real one at *any* seam. Batch paths call
    :func:`frontmatter_skew` directly instead, since their response is not a plain refusal.
    """
    diverging = frontmatter_skew(text, base)
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


async def update_frontmatter(path: Path, item: Item, base: Item) -> None:
    """Rewrite the frontmatter from the item; body is preserved verbatim.

    The read is :func:`read_item_text`, so a stale index-derived *path* (an interrupted
    rename/retype) reports cleanly instead of a raw ``FileNotFoundError``. Refuses
    (:class:`SquadsError`) if the on-disk frontmatter has diverged from what *base* — the item
    as loaded before this mutation's own delta, captured by the caller's pure half — would
    itself have serialized: see :func:`ensure_no_skew`.
    """
    text = await read_item_text(path, item.id)
    ensure_no_skew(text, base)
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
