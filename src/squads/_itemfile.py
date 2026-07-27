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
"""

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from squads import _aio
from squads._errors import SquadsError
from squads._models._item import Item
from squads._sections import join_frontmatter, replace_frontmatter, split_frontmatter


def read_frontmatter(path: Path | None = None, *, text: str | None = None) -> dict[str, Any]:
    if text is None:
        if path is None:
            raise ValueError("read_frontmatter requires a path or text")
        text = path.read_text(encoding="utf-8")
    return split_frontmatter(text)[0]


def _without_extra_keys(data: dict[str, Any], keys: frozenset[str]) -> dict[str, Any]:
    """*data* (a ``to_frontmatter_dict()`` output) with *keys* removed from its nested
    ``extra`` mapping, if present — the mechanics behind ``frontmatter_skew``'s
    ``ignore_extra_keys``. A no-op copy when *keys* is empty or ``extra`` doesn't carry any
    of them, so callers that never pass *keys* never allocate anything extra."""
    if not keys:
        return data
    extra = data.get("extra")
    if not isinstance(extra, dict):
        return data
    extra_typed = cast("dict[str, Any]", extra)
    if not (extra_typed.keys() & keys):
        return data
    trimmed = {k: v for k, v in extra_typed.items() if k not in keys}
    out = dict(data)
    if trimmed:
        out["extra"] = trimmed
    else:
        out.pop("extra", None)
    return out


def frontmatter_skew(
    text: str, base: Item, *, ignore_extra_keys: frozenset[str] = frozenset()
) -> list[str]:
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

    ``ignore_extra_keys`` exists for exactly one category: an ``extra`` sub-key the
    durability decision names as the permitted skew — "re-derivable regions of an item
    ``.md`` the committing transaction did not mirror into the index" (the role's
    resolved-skills cache; a role's catalog-merged fields). Those two write their value to
    the file WITHOUT ever going through ``store.transaction()``, so the index-loaded
    ``base`` never carries the current generation of that value even in the fully healthy
    case — disk is *permanently* ahead of the index on that one key, by design, not because
    of an interrupted write. Comparing it like every other field would false-refuse on the
    very first mutation after any such resync ever ran. This is not a load/parse-time
    correction the round trip can be taught — the two sides are reading genuinely different
    sources of truth for that key — so it is
    named here explicitly rather than silently folded into the general round trip.
    """
    disk_data, _ = split_frontmatter(text)
    disk_dict = Item.from_frontmatter(disk_data, path=base.path).to_frontmatter_dict()
    base_dict = base.to_frontmatter_dict()
    disk_dict = _without_extra_keys(disk_dict, ignore_extra_keys)
    base_dict = _without_extra_keys(base_dict, ignore_extra_keys)
    keys = disk_dict.keys() | base_dict.keys()
    return sorted(k for k in keys if disk_dict.get(k) != base_dict.get(k))


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


def ensure_no_skew(
    text: str, base: Item, *, ignore_extra_keys: frozenset[str] = frozenset()
) -> None:
    """Raise :class:`SquadsError` when *text*'s on-disk frontmatter has drifted from *base*.

    Writing over it now — substituting the whole frontmatter block from an index-derived
    item — would silently discard whatever survived on disk since the index last saw it. The
    single-mutation write seams call this before every rewrite (never passing
    ``ignore_extra_keys`` — the exclusion list stays empty there); the two roster-regen
    writers that persist an ADR-named never-mirrored-into-the-index cache pass their own key
    so that permitted, permanent skew isn't mistaken for a real one (see
    :func:`frontmatter_skew`). Batch paths call :func:`frontmatter_skew` directly instead,
    since their response is not a plain refusal.
    """
    diverging = frontmatter_skew(text, base, ignore_extra_keys=ignore_extra_keys)
    if diverging:
        raise SquadsError(skew_message(base, diverging))


async def write_new(path: Path, item: Item, rendered_body: str) -> None:
    """Create a brand-new item file: frontmatter + the rendered (templated) body.

    No prior file to diverge from — a create never goes through the skew guard.
    """
    text = join_frontmatter(item.to_frontmatter_dict(), rendered_body)
    await _aio.mkdir(path.parent, parents=True, exist_ok=True)
    await _aio.atomic_write_text(path, text)


async def update_frontmatter(
    path: Path, item: Item, base: Item, *, ignore_extra_keys: frozenset[str] = frozenset()
) -> None:
    """Rewrite the frontmatter from the item; body is preserved verbatim.

    Refuses (:class:`SquadsError`) if the on-disk frontmatter has diverged from what *base*
    — the item as loaded before this mutation's own delta, captured by the caller's pure
    half — would itself have serialized: see :func:`ensure_no_skew`, including what
    ``ignore_extra_keys`` is for and why it stays unused outside the two named roster-regen
    writers.
    """
    text = await _aio.read_text(path)
    ensure_no_skew(text, base, ignore_extra_keys=ignore_extra_keys)
    await _aio.atomic_write_text(path, replace_frontmatter(text, item.to_frontmatter_dict()))


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
