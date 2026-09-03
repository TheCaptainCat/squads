"""The default-ref-kind encoding convergence table: five on-disk encodings of one edge, each
checked against an index that already holds the canonical form for its kind. This asserts
CONVERGENCE, not merely the absence of a false-refuse warning -- a fold-level unit test on
``fold_legacy_kinds`` in isolation would not have caught the regression this guards, since the
fold's output is correct as a mechanical function; what broke was which encoding reaches disk
and the index in the first place.

Per row: ``frontmatter_skew`` is empty, ``sq repair`` stores the canonical encoding, the next
ordinary mutation writes it, and ``sq check`` stays clean throughout. The three default-kind
rows (bare, spelled default, legacy map naming the default) all converge on **bare**; the two
non-default controls (spelled, legacy map) converge on the spelled form, ``ID:blocks``,
unchanged -- preserving the leg ``test_legacy_ref_kinds_map_does_not_false_refuse`` was
narrowed to (see ``test_frontmatter_skew_guard.py``) while this file restores the default-kind
legs it lost.

The load-bearing assertion sits in its own test below: the legacy-map row and the bare row
produce byte-identical ``to_frontmatter_dict()`` output -- the property the disk/index split
actually depends on, asserted rather than relied on as a coincidence.
"""

from typing import Any

import pytest

from _helpers import create_item
from squads import _itemfile as itemfile
from squads._models._item import Item
from squads._sections import join_frontmatter, split_frontmatter

pytestmark = pytest.mark.anyio


def _plant_disk_refs(
    svc, item, *, refs: list[str], ref_kinds: dict[str, str] | None = None
) -> None:
    """Hand-rewrite *item*'s file frontmatter to an exact ``refs``/``extra.ref_kinds`` wire
    shape -- bypassing every normalising writer (``add_ref``, ``update_frontmatter``'s own
    round trip) so the row controls precisely which of the five encodings disk carries,
    independent of whatever the index already holds for the same edge."""
    path = svc.paths.abspath(item.path)
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    fm["refs"] = refs
    fm.pop("extra", None)
    if ref_kinds:
        fm["extra"] = {"ref_kinds": ref_kinds}
    path.write_text(join_frontmatter(fm, body), encoding="utf-8")


async def _seed_canonical_edge(svc, *, kind: str) -> tuple[Any, Any]:
    """Two items with a real, normally-written edge between them -- ``add_ref`` is the
    production writer, so the INDEX this leaves behind already holds the canonical encoding
    for *kind* (bare for the declared default, spelled for anything else) before any row's
    disk-side hand-plant runs."""
    a = (await create_item(svc, "task", "Ref source")).item
    b = (await create_item(svc, "task", "Ref target")).item
    await svc.add_ref(a.id, b.id, kind=kind)
    return a, b


# label, disk refs-fn, disk legacy-map-fn, kind passed to add_ref, expected canonical ref
_ROWS: list[tuple[str, Any, Any, str, Any]] = [
    ("bare", lambda bid: [bid], lambda bid: None, "related", lambda bid: bid),
    (
        "spelled-default",
        lambda bid: [f"{bid}:related"],
        lambda bid: None,
        "related",
        lambda bid: bid,
    ),
    (
        "legacy-map-default",
        lambda bid: [bid],
        lambda bid: {bid: "related"},
        "related",
        lambda bid: bid,
    ),
    (
        "control-spelled-nondefault",
        lambda bid: [f"{bid}:blocks"],
        lambda bid: None,
        "blocks",
        lambda bid: f"{bid}:blocks",
    ),
    (
        "control-legacy-map-nondefault",
        lambda bid: [bid],
        lambda bid: {bid: "blocks"},
        "blocks",
        lambda bid: f"{bid}:blocks",
    ),
]


def _no_errors(issues) -> bool:
    return not any(i.level == "error" for i in issues)


@pytest.mark.parametrize(
    ("label", "refs_fn", "legacy_fn", "kind", "canonical_fn"),
    _ROWS,
    ids=[row[0] for row in _ROWS],
)
async def test_row_converges_on_the_canonical_encoding(
    svc, label, refs_fn, legacy_fn, kind, canonical_fn
):
    a, b = await _seed_canonical_edge(svc, kind=kind)
    canonical_ref = canonical_fn(b.id)

    # sq check is clean on the freshly-seeded, normally-written edge, before any hand-plant.
    assert _no_errors(await svc.check())

    _plant_disk_refs(svc, a, refs=refs_fn(b.id), ref_kinds=legacy_fn(b.id))

    default_kind = svc.spec.default_ref_kind()
    disk_text = svc.paths.abspath(a.path).read_text(encoding="utf-8")
    index_item = await svc.get(a.id)
    # frontmatter_skew is empty: the disk-side fold normalises this row's encoding to exactly
    # what the index already holds, whatever wire shape the row started from.
    assert itemfile.frontmatter_skew(disk_text, index_item, default_kind=default_kind) == []
    assert _no_errors(await svc.check())

    # sq repair stores the canonical encoding.
    result = await svc.repair()
    assert result.db.get(a.id) is not None
    assert result.db.get(a.id).refs == [canonical_ref]  # type: ignore[union-attr]
    assert _no_errors(await svc.check())

    # The next ordinary mutation writes the canonical encoding to disk.
    await svc.update(a.id, description="touch")
    on_disk_after, _ = split_frontmatter(svc.paths.abspath(a.path).read_text(encoding="utf-8"))
    assert on_disk_after["refs"] == [canonical_ref]
    assert _no_errors(await svc.check())


async def test_the_legacy_map_row_and_the_bare_row_are_byte_identical_after_the_fold(svc):
    """The load-bearing property: two on-disk encodings of the SAME semantic edge (bare, and a
    legacy map naming the declared default) fold to byte-identical ``to_frontmatter_dict()``
    output -- the property the disk/index split's correctness actually depends on, not a
    coincidence this suite merely fails to falsify."""
    a, b = await _seed_canonical_edge(svc, kind="related")
    default_kind = svc.spec.default_ref_kind()

    bare_data = {
        "id": a.id,
        "sequence_id": a.sequence_id,
        "type": "task",
        "title": a.title,
        "status": a.status,
        "refs": [b.id],
    }
    legacy_map_data = {
        **bare_data,
        "refs": [b.id],
        "extra": {"ref_kinds": {b.id: "related"}},
    }

    bare_item = Item.from_frontmatter(bare_data, path=a.path, default_kind=default_kind)
    legacy_item = Item.from_frontmatter(legacy_map_data, path=a.path, default_kind=default_kind)

    assert bare_item.to_frontmatter_dict() == legacy_item.to_frontmatter_dict()
    assert bare_item.refs == [b.id]  # bare, unspelled -- the shared canonical form


async def test_corpus_level_check_repair_check_mutate_check_converges(svc):
    """One corpus-level row over the whole five-encoding set: check -> repair -> check ->
    mutate EVERY item -> check, catching an asymmetry introduced at any of the three
    ``Item.from_frontmatter`` call sites rather than only at the one a per-row test happens to
    exercise. ``sq repair`` converges rather than oscillates: a second repair back-to-back
    must reproduce byte-identical ``refs`` for every item, not
    just for the five rows this file plants."""
    items: list[tuple[str, Any, Any]] = []
    for label, refs_fn, legacy_fn, kind, canonical_fn in _ROWS:
        a, b = await _seed_canonical_edge(svc, kind=kind)
        _plant_disk_refs(svc, a, refs=refs_fn(b.id), ref_kinds=legacy_fn(b.id))
        items.append((label, a, canonical_fn(b.id)))

    assert _no_errors(await svc.check())

    first = await svc.repair()
    for _label, a, canonical_ref in items:
        assert first.db.get(a.id).refs == [canonical_ref]  # type: ignore[union-attr]
    assert _no_errors(await svc.check())

    # Idempotent: a second repair, run immediately after, reproduces byte-identical refs for
    # every item in the index -- not just the five this test planted.
    second = await svc.repair()
    refs_first = {seq: it.refs for seq, it in first.db.items.items()}
    refs_second = {seq: it.refs for seq, it in second.db.items.items()}
    assert refs_second == refs_first

    for _label, a, canonical_ref in items:
        await svc.update(a.id, description=f"touch {a.id}")
        on_disk, _ = split_frontmatter(svc.paths.abspath(a.path).read_text(encoding="utf-8"))
        assert on_disk["refs"] == [canonical_ref]

    assert _no_errors(await svc.check())


# --------------------------------------------------------------------------- the write door
#
# Every row above starts from a FILE already on disk -- they exercise the read side (the
# fold), never the write door a fresh `create` opens. A create-time ref is validated then
# stored straight onto the new `Item` with no normalisation of its own (`_services/_base.py`'s
# `_create_model`), a sibling gap to the one the read-side fix closed: a caller-supplied
# "ID:<default-kind>" reached both the index (verbatim, via the constructed `Item`) and disk
# (verbatim, via `to_frontmatter_dict()`) already spelled -- consistently on both sides, so
# `frontmatter_skew` never even had a divergence to fold away; `sq check` warned on the very
# next scan regardless, because A1 forbids spelling the default full stop, not only when the
# two sides disagree.


@pytest.mark.parametrize(
    ("kind", "expect_spelled"),
    [
        pytest.param("related", False, id="default-kind-lands-bare"),
        pytest.param("blocks", True, id="control-nondefault-stays-spelled"),
    ],
)
async def test_create_with_an_explicitly_spelled_kind_lands_canonical_on_both_sides(
    svc, kind, expect_spelled
):
    """A ref supplied at creation time, spelled explicitly (``--ref ID:<kind>`` at the CLI,
    ``refs=["ID:<kind>"]`` against the service directly) -- never a file on disk, never a
    legacy map, the write door itself. The declared default lands bare in BOTH the freshly
    written file and the freshly committed index, with `sq check` clean immediately and no
    `sq repair` required to get there; the non-default control keeps its spelling, unchanged,
    proving this isn't a blanket strip of every kind."""
    target = (await create_item(svc, "task", "Ref target")).item

    result = await svc.create("task", "Ref source", author="manager", refs=[f"{target.id}:{kind}"])
    source = result.item

    expected_ref = f"{target.id}:{kind}" if expect_spelled else target.id
    # In the index, immediately after create -- no repair, no reload through the fold.
    assert source.refs == [expected_ref]

    # On disk, the file `create` itself just wrote.
    on_disk, _ = split_frontmatter(result.path.read_text(encoding="utf-8"))
    assert on_disk["refs"] == [expected_ref]

    # Clean immediately: no drift, no divergence, nothing for `sq repair` to fix.
    assert _no_errors(await svc.check())
    default_kind = svc.spec.default_ref_kind()
    disk_text = result.path.read_text(encoding="utf-8")
    assert itemfile.frontmatter_skew(disk_text, source, default_kind=default_kind) == []
