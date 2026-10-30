"""Read/write the markdown file backing an item, keeping frontmatter and body in sync.

The ``.md`` frontmatter is the durable source of truth; ``sq`` rewrites only the frontmatter
(and marker sections), never the agent-authored body.

Every writer here (``write_new``, ``update_frontmatter``, ``write_text``, ``rewrite_ids``)
goes through :func:`squads._aio.atomic_write_text` (temp file, fsync, ``os.replace``), so a
killed process leaves the file complete-or-previous, never truncated. A mutation core reaches
for this module only; a bare ``_aio.write_text`` on an item ``.md`` reintroduces the hazard.

Ordering rule callers must keep: within a transaction every markdown write happens before the
body returns and the index commit is the last write, so a crash leaves the markdown ahead of
or equal to the index and ``sq repair`` converges on the file. Several files in one
transaction are not atomic across files, but each is durable before the index commits, so a
crash between two leaves the same one-sided, repair-safe skew.
"""

import contextlib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from squads import _aio
from squads._errors import SquadsError
from squads._models._item import INVENTED_WHEN_ABSENT, Item
from squads._sections import (
    conform_line_endings,
    join_frontmatter,
    replace_frontmatter,
    split_frontmatter,
)


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


@dataclass(frozen=True, slots=True)
class SkewKey:
    """One frontmatter key on which :func:`frontmatter_skew` found disk and index disagreeing.

    Classified so a refusal never asserts a cause the reader can disprove: ``stale_encoding`` is
    true when the raw on-disk value (before the load round trip) already equals what the index
    holds, so the round trip alone produced the diverging value.
    """

    name: str
    stale_encoding: bool


def _classify_skew(key: str, disk_data: dict[str, Any], base_dict: dict[str, Any]) -> SkewKey:
    """*key*'s :class:`SkewKey` verdict — the stale-encoding-versus-divergence test applied
    at the one site that already holds both the raw on-disk frontmatter and the
    index-serialized *base_dict*."""
    return SkewKey(key, stale_encoding=disk_data.get(key) == base_dict.get(key))


def stale_encoding_clause(fields: Iterable[str]) -> str:
    """The shared explanation for a stale-index-encoding skew on *fields* — reused by
    :func:`skew_message` and ``sq check``'s finding wording
    (``_services/_check.py::_drift_message``) so one state is explained in the same
    words on both surfaces. States the true cause — a non-canonical index
    encoding — rather than a divergence the reader can open the file and disprove."""
    return f"the index holds a non-canonical encoding of {', '.join(fields)}, not a divergence"


def frontmatter_skew(text: str, base: Item, *, default_kind: str) -> list[SkewKey]:
    """The keys on which *text*'s on-disk frontmatter diverges from what *base* would serialize.

    *base* is the item as loaded before the pending mutation's own delta; each key is a
    :class:`SkewKey` (a real divergence, or a stale index encoding). The disk side goes through
    the load round trip (``Item.from_frontmatter(...).to_frontmatter_dict()``), which collapses
    every load-time correction (a spelled-default ref folded to bare, a padded id recomputed, key
    order, absent versus ``None``), so a non-empty result is a real skew. Unknown keys take part on
    both sides. *base* is serialized directly, so *default_kind* is folded in on the disk side
    only; *base*'s ``path`` is passed to ``from_frontmatter`` because reconstruction needs one. An
    empty return is the normal case, since the last mutation wrote both from one item.
    """
    disk_data, _ = split_frontmatter(text, source=base.path)
    disk_dict = Item.from_frontmatter(
        disk_data, path=base.path, default_kind=default_kind
    ).to_frontmatter_dict()
    base_dict = base.to_frontmatter_dict()
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
    """The human-readable report for a confirmed skew on *base*.

    Shared by the refusal at a single-mutation write seam, the skip line ``sq sync`` emits for a
    drifted roster item, and the ``ImportIssue`` the bulk importer's pre-pass collects. A real
    divergence and a stale index encoding (:func:`stale_encoding_clause`) get their own wording,
    never one describing the other; a mixed item reports both.
    """
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

    Writing over it would discard whatever survived on disk since the index last saw it, so every
    single-mutation write seam calls this before a rewrite; batch paths call
    :func:`frontmatter_skew` directly, since their response is not a plain refusal.
    *default_kind* is a required keyword, resolved once per pass by the caller (a ``Service`` mixin
    with ``self.spec``), so a spec declaring the wrong number of default ref kinds fails as one
    refusal naming the spec, not partway through a rebuild.
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
    """Read *item_id*'s file at *path*, turning a missing file into :func:`missing_file_error`.

    An interrupted title-changing update or retype can move a file before the index commits,
    leaving *path* stale. :func:`~squads._aio.read_text` propagates ``FileNotFoundError`` for the
    two callers that read it as a signal (``check``'s confirm round and the bulk importer's pre-pass
    skew guard, both in ``_services/``); every other reader wants the content, so the error becomes
    a message naming the item and pointing at ``sq repair``, the read side of the clean refusals in
    :func:`ensure_no_skew`.
    """
    try:
        return await _aio.read_text(path)
    except FileNotFoundError as exc:
        raise missing_file_error(item_id) from exc


def new_item_text(item: Item, rendered_body: str) -> str:
    """The text of a brand-new item file: frontmatter + the rendered (templated) body."""
    return join_frontmatter(item.to_frontmatter_dict(), rendered_body)


async def write_new(path: Path, item: Item, rendered_body: str) -> None:
    """Create a brand-new item file: frontmatter + the rendered (templated) body.

    No prior file to diverge from — a create never goes through the skew guard.
    """
    await _aio.mkdir(path.parent, parents=True, exist_ok=True)
    await _aio.atomic_write_text(path, new_item_text(item, rendered_body))


async def update_frontmatter(path: Path, item: Item, base: Item, *, default_kind: str) -> None:
    """Rewrite the frontmatter from the item; the body is preserved verbatim.

    It reads through :func:`read_item_text`, so a stale index-derived *path* reports cleanly.
    Refuses with :class:`SquadsError` when the on-disk frontmatter diverges from what *base* (the
    item before this mutation's delta) would serialize; see :func:`ensure_no_skew`, which
    receives *default_kind*.
    """
    text = await read_item_text(path, item.id)
    ensure_no_skew(text, base, default_kind=default_kind)
    await write_text(path, replace_frontmatter(text, item.to_frontmatter_dict(), source=str(path)))


async def write_text(path: Path, text: str) -> None:
    """Atomically overwrite an existing item file with fully-formed new text.

    The exit for callers that built the whole new contents themselves (a section edit, a
    sub-entity block rewrite, a retype), so every write of an item ``.md`` funnels through this
    module. The text takes the file's line endings (:func:`~squads._sections.conform_line_endings`):
    shared lines keep theirs, added or changed lines use the dominant one.
    """
    with contextlib.suppress(FileNotFoundError):
        text = conform_line_endings(await _aio.read_text(path, verbatim=True), text)
    await _aio.atomic_write_text(path, text)


def remap_ids_text(text: str, remap: dict[str, str]) -> str:
    """Whole-word substitution of every old ID → new ID in *text*.

    Replaces all occurrences of ``\\bOLD\\b → NEW`` (exact whole-word match so e.g. a longer ID
    sharing a prefix is not touched).
    """
    for old, new in remap.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    return text


async def rewrite_ids(paths: Iterable[Path], remap: dict[str, str]) -> list[Path]:
    """Apply :func:`remap_ids_text` to each file in *paths*, writing the ones it changes.

    Returns the list of paths that were actually modified.
    """
    touched: list[Path] = []
    for path in paths:
        text = await _aio.read_text(path)
        new_text = remap_ids_text(text, remap)
        if new_text != text:
            await write_text(path, new_text)
            touched.append(path)
    return touched
