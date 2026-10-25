"""Each shape an item file can take on disk gets exactly one tag from the corpus reader, which
the index rebuild and the ``check`` scan both consume."""

from pathlib import Path

import pytest

from squads._services._corpus_files import (
    LegacySkillBody,
    MissingId,
    Parsed,
    Unparseable,
    Unreadable,
    Vanished,
    read_corpus_file,
)
from squads._workflow import bundled_spec

_ITEM = b"---\nid: TASK-000001\ntype: task\ntitle: t\n---\nbody\n"
_NO_ID = b"---\ntype: task\ntitle: t\n---\nbody\n"
_BROKEN_YAML = b"---\nid: [unclosed\n---\nbody\n"

_SHAPES = {
    "valid item": ("task", "TASK-000001-t.md", _ITEM, Parsed),
    "undecodable bytes": ("task", "TASK-000001-t.md", b"\xff\xfe\x00---\n", Unreadable),
    "unparseable frontmatter": ("task", "TASK-000001-t.md", _BROKEN_YAML, Unparseable),
    "missing id": ("task", "TASK-000001-t.md", _NO_ID, MissingId),
    "legacy skill body": ("skill", "squads.md", _NO_ID, LegacySkillBody),
    "vanished between listing and read": ("task", "TASK-000001-t.md", None, Vanished),
}


@pytest.mark.parametrize("shape", sorted(_SHAPES))
async def test_each_file_shape_gets_its_own_tag(tmp_path: Path, shape: str) -> None:
    item_type, name, content, expected = _SHAPES[shape]
    md = tmp_path / name
    if content is not None:
        md.write_bytes(content)
    record = await read_corpus_file(item_type, md, bundled_spec())
    assert type(record) is expected
    assert record.md == md
    assert record.item_type == item_type
