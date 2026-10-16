"""A stale index *encoding* is not a divergence, and the refusal must say so rather than
naming a cause the reader can open the file and disprove.

Two states, driven end to end against both message surfaces (the write-seam refusal and the
matching ``sq check`` finding), which share :func:`~squads._itemfile.frontmatter_skew` by
design:

1. **Stale index encoding.** The index holds the spelled default ref kind, and the file holds
   the identical bytes — nothing diverged, only the load-time fold. Refused (the index really
   does hold a non-canonical encoding), but the message must not claim the file diverged.
2. **An ordinary hand-edited divergence** (a title changed on disk only) keeps the divergence
   wording on both surfaces.

A third case mixes one stale-encoded key with one genuinely diverged key on the same item and
asserts both are reported, neither described as the other.
"""

import pytest

from _helpers import create_item
from squads import _itemfile as itemfile
from squads import _sections as sections
from squads._errors import SquadsError
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


def _edit_frontmatter(path, **fields: object) -> None:
    """Directly rewrite frontmatter fields on a squad-data file, bypassing the service — the
    only way to construct a frontmatter/index mismatch these tests need."""
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm.update(fields)
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")


async def _plant_index_refs(svc, item_id: str, refs: list[str]) -> None:
    """Overwrite *item_id*'s ``refs`` in the index directly — bypassing every writer, so the
    index can be made to hold a value no real write path would ever produce (the spelled
    default), exactly the pre-0.14 state a squad can be left holding on disk and in the index
    alike."""
    db = await svc.store.load()
    item = db.get(item_id)
    assert item is not None
    item.refs = refs
    await svc.store.overwrite(db)


async def _check_message(svc, item_id: str) -> str:
    issues = await svc.check()
    hit = next(i for i in issues if i.item == item_id)
    assert hit.level == "warn"
    return hit.message


# ----------------------------------------------------------------------- state 1: stale encoding


async def test_a_spelled_default_kind_consistent_on_both_sides_is_reported_as_stale_encoding(svc):
    a = (await create_item(svc, "task", "Ref source")).item
    b = (await create_item(svc, "task", "Ref target")).item
    default_kind = svc.spec.default_ref_kind()
    spelled = f"{b.id}:{default_kind}"

    # Same bytes on both sides — the file is rewritten to the spelled form, and so is the
    # index, directly. Nothing diverged; only the fold that reads this back changed.
    _edit_frontmatter(svc.paths.abspath(a.path), refs=[spelled])
    await _plant_index_refs(svc, a.id, [spelled])

    reloaded = await svc.get(a.id)
    text = svc.paths.abspath(a.path).read_text(encoding="utf-8")
    diverging = itemfile.frontmatter_skew(text, reloaded, default_kind=default_kind)
    assert [(k.name, k.stale_encoding) for k in diverging] == [("refs", True)]

    # The write seam still refuses ...
    with pytest.raises(SquadsError) as excinfo:
        await svc.set_status(a.id, "InProgress", force=True)
    message = str(excinfo.value)
    assert message == itemfile.skew_message(reloaded, diverging)
    # ... but must name the true cause, not a divergence the reader can disprove.
    assert "diverged" not in message
    assert "non-canonical encoding of refs" in message
    assert "run `sq repair`" in message

    # ``sq check`` reports the identical state, in the same words, at the same severity.
    check_message = await _check_message(svc, a.id)
    assert "diverged" not in check_message
    assert "non-canonical encoding of refs" in check_message

    # The advertised remedy works: repair re-derives it bare, the next ordinary write
    # canonicalises the file, and check goes clean.
    await svc.repair()
    await svc.set_status(a.id, "InProgress", force=True)
    final = await svc.get(a.id)
    assert final.refs == [b.id]
    issues = await svc.check()
    assert not any(i.item == a.id for i in issues)


# --------------------------------------------------------------------- state 3: ordinary divergence


async def test_a_hand_edited_title_keeps_todays_divergence_wording(svc):
    task = (await create_item(svc, "task", "original title")).item
    default_kind = svc.spec.default_ref_kind()
    _edit_frontmatter(svc.paths.abspath(task.path), title="hand-edited title")

    reloaded = await svc.get(task.id)
    text = svc.paths.abspath(task.path).read_text(encoding="utf-8")
    diverging = itemfile.frontmatter_skew(text, reloaded, default_kind=default_kind)
    assert [(k.name, k.stale_encoding) for k in diverging] == [("title", False)]

    with pytest.raises(SquadsError) as excinfo:
        await svc.set_status(task.id, "InProgress", force=True)
    message = str(excinfo.value)
    assert "on-disk frontmatter has diverged from the index (title)" in message
    assert "non-canonical encoding" not in message

    check_message = await _check_message(svc, task.id)
    assert "title drift between frontmatter and index" in check_message
    assert "non-canonical encoding" not in check_message


# --------------------------------------------------------------------------- mixed item


async def test_a_mixed_item_reports_both_and_conflates_neither(svc):
    a = (await create_item(svc, "task", "original title")).item
    b = (await create_item(svc, "task", "Ref target")).item
    default_kind = svc.spec.default_ref_kind()
    spelled = f"{b.id}:{default_kind}"

    # refs: stale-encoded, same bytes both sides.
    _edit_frontmatter(svc.paths.abspath(a.path), refs=[spelled])
    await _plant_index_refs(svc, a.id, [spelled])
    # title: a genuine hand edit, on disk only.
    _edit_frontmatter(svc.paths.abspath(a.path), title="hand-edited title")

    reloaded = await svc.get(a.id)
    text = svc.paths.abspath(a.path).read_text(encoding="utf-8")
    diverging = itemfile.frontmatter_skew(text, reloaded, default_kind=default_kind)
    assert sorted((k.name, k.stale_encoding) for k in diverging) == [
        ("refs", True),
        ("title", False),
    ]

    with pytest.raises(SquadsError) as excinfo:
        await svc.set_status(a.id, "InProgress", force=True)
    message = str(excinfo.value)
    assert "on-disk frontmatter has diverged from the index (title)" in message
    assert "non-canonical encoding of refs" in message
    # Neither state describes the other's.
    assert "non-canonical encoding of title" not in message
    assert "diverged from the index (refs)" not in message

    check_message = await _check_message(svc, a.id)
    assert "title drift between frontmatter and index" in check_message
    assert "non-canonical encoding of refs" in check_message
    assert "non-canonical encoding of title" not in check_message
    assert "refs drift" not in check_message
