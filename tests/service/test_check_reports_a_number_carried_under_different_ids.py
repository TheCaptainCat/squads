"""`check` reports a sequence number carried by files under different ids, naming every file, and
stays clean when every number belongs to one id."""

from pathlib import Path

import pytest

from squads._sections import replace_frontmatter, split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
async def svc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return service.Service(result.paths)


async def _item(svc, item_type: str):
    created = await svc.create(item_type, f"A {item_type}", author="manager")
    return created.item, created.path


def _carry_number_of(source: Path, other_prefix_id: str, folder: Path) -> Path:
    """A copy of *source* whose id has *other_prefix_id*'s type prefix and *source*'s number."""
    text = source.read_text()
    data = split_frontmatter(text)[0]
    prefix = other_prefix_id.rsplit("-", 1)[0]
    data["id"] = f"{prefix}-{data['sequence_id']:06d}"
    folder.mkdir(exist_ok=True)
    target = folder / f"{data['id']}-copy.md"
    target.write_text(replace_frontmatter(text, data))
    return target


# (type holding the number, types whose files then claim it)
_SHAPES = [
    pytest.param("task", ["bug"], id="task-and-bug"),
    pytest.param("bug", ["task"], id="bug-and-task"),
    pytest.param("task", ["feature"], id="task-and-feature"),
    pytest.param("task", ["bug", "feature"], id="three-way"),
]


def _shared(issues):
    return [i for i in issues if "under different ids" in i.message]


@pytest.mark.parametrize(("holder", "claimants"), _SHAPES)
async def test_a_number_under_two_ids_is_an_error_naming_every_file(svc, holder, claimants):
    _, md = await _item(svc, holder)
    names = [md.name]
    for claimant in claimants:
        other, _ = await _item(svc, claimant)
        folder = svc.paths.squad_dir / svc.spec.items[claimant].folder
        names.append(_carry_number_of(md, other.id, folder).name)

    found = _shared(await svc.check())

    assert len(found) == 1
    assert found[0].level == "error"
    assert all(name in found[0].message for name in names)
    assert f"{len(names)} files" in found[0].message


async def test_distinct_numbers_across_types_stay_clean(svc):
    for item_type in ("task", "bug", "feature"):
        await _item(svc, item_type)

    assert _shared(await svc.check()) == []
