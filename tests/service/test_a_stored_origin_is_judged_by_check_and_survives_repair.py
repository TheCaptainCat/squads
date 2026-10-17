"""The ``origin`` a role or skill file stores, crossed with every surface that reads or writes it.

One table: the stored value (shape) by what ``sq check`` says, what the typed accessor reads,
whether ``update --set`` may replace it, and whether deleting the index and running ``sq repair``
brings the same value back. A value outside the two words is reported and left as written.
"""

import re
from pathlib import Path

import pytest

from squads import _sections as sections
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models import _attributes as attrs
from squads._models._attributes import AttributeKey
from squads._models._item import Item

pytestmark = pytest.mark.anyio

#: shape -> (the YAML line to store, or None to drop the key; accessor value; check message)
SHAPES: dict[str, tuple[str | None, str | None, str | None]] = {
    "system": ("origin: system", "system", None),
    "project": ("origin: project", "project", None),
    "absent": (None, None, "missing required attribute 'origin'"),
    "wrong-case": ("origin: System", None, "attribute 'origin': expected one of system, project"),
    "empty-string": ("origin: ''", None, "attribute 'origin': expected one of system, project"),
    "a-list": ("origin: [system]", None, "attribute 'origin'"),
    "null": ("origin: null", None, "missing required attribute 'origin'"),
    "unknown-word": ("origin: bundled", None, "attribute 'origin': expected one of"),
}

#: item kind -> a way to make one
KINDS = ("role", "skill")


async def _make(svc, kind: str) -> Item:
    if kind == "role":
        return await svc.activate_role("architect")
    return await svc.add_skill("Release Runbook", description="Ship a release safely.")


def _store(path: Path, line: str | None) -> None:
    text = path.read_text(encoding="utf-8")
    replacement = f"{line}\n" if line is not None else ""
    path.write_text(re.sub(r"^origin: .*\n", replacement, text, count=1, flags=re.M), "utf-8")


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("shape", list(SHAPES))
async def test_check_reports_a_stored_origin_by_shape(kind, shape, svc, invoke) -> None:
    line, _accessor, message = SHAPES[shape]
    item = await _make(svc, kind)
    _store(item_file(svc.paths, item), line)

    result = await invoke(["check"])

    if message is None:
        assert result.exit_code == 0, result.output
        assert "error" not in result.output
    else:
        assert result.exit_code == 3, result.output
        assert message in result.output
        assert item.id in result.output


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("shape", list(SHAPES))
async def test_the_accessor_reads_only_the_two_words(kind, shape, svc) -> None:
    line, accessor, _message = SHAPES[shape]
    item = await _make(svc, kind)
    path = item_file(svc.paths, item)
    _store(path, line)
    stored, _body = sections.split_frontmatter(path.read_text(encoding="utf-8"))
    reloaded = Item.from_frontmatter_verbatim(stored, path=item.path)

    assert attrs.origin(reloaded) == accessor


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("shape", list(SHAPES))
async def test_update_set_origin_is_refused_whatever_is_stored(kind, shape, svc) -> None:
    line, _accessor, _message = SHAPES[shape]
    item = await _make(svc, kind)
    path = item_file(svc.paths, item)
    _store(path, line)
    before = path.read_bytes()

    with pytest.raises(SquadsError, match=r"not a settable field|authoring surface"):
        await svc.update(item.id, set_attributes={"origin": "project"})
    with pytest.raises(SquadsError, match=r"not a settable field|authoring surface"):
        await svc.update(item.id, unset_attributes=["origin"])

    assert path.read_bytes() == before


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("shape", list(SHAPES))
async def test_repair_rebuilds_the_index_with_the_stored_value_verbatim(
    kind, shape, svc, invoke
) -> None:
    line, _accessor, _message = SHAPES[shape]
    item = await _make(svc, kind)
    path = item_file(svc.paths, item)
    _store(path, line)
    before = path.read_bytes()
    stored, _body = sections.split_frontmatter(path.read_text(encoding="utf-8"))
    (svc.paths.squad_dir / ".squads.json").unlink()

    result = await invoke(["repair"])

    assert result.exit_code == 0, result.output
    assert path.read_bytes() == before
    rebuilt = (await svc.store.load()).items[item.sequence_id]
    assert rebuilt.attribute(AttributeKey.ORIGIN) == stored.get("origin")
