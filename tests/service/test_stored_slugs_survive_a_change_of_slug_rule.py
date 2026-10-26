"""A slug stored under the earlier accent-dropping rule stays the identity of its entry: sync
and check leave it (and its files) alone, and re-adding the same person, skill or developer is
refused rather than forked into a second entry."""

from pathlib import Path

import pytest

from _helpers import make_service
from squads import _util
from squads._errors import SquadsError
from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
async def svc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return make_service(result.paths)


@pytest.fixture
def earlier_rule():
    """Run creation under the rule that dropped accented letters; ``.undo()`` restores the
    current rule."""
    patch = pytest.MonkeyPatch()
    for target in (
        "squads._util.slugify",
        "squads._services._roster.slugify",
        "squads._roles._templates.slugify",
        "squads._memory._store.slugify",
    ):
        patch.setattr(target, _util.legacy_slugify)
    yield patch
    patch.undo()


def _errors(issues):
    return [i for i in issues if i.level == "error"]


async def test_a_dev_role_keeps_its_stored_slug_and_pointer_through_sync(svc, earlier_rule):
    item = await svc.activate_role(None, from_template="dev", tech="Élixir")
    assert item.slug == "lixir-dev"
    pointer = svc.paths.root / ".claude" / "agents" / "lixir-dev.md"
    assert pointer.is_file()
    agents = sorted(p.name for p in pointer.parent.iterdir())

    earlier_rule.undo()
    await svc.sync()

    (again,) = [i for i in await svc.list_items(item_type="role") if i.id == item.id]
    assert again.slug == "lixir-dev"
    assert sorted(p.name for p in pointer.parent.iterdir()) == agents
    assert not _errors(await svc.check())


async def test_an_operator_keeps_resolving_by_its_stored_slug(svc, earlier_rule):
    item = await svc.add_operator("Élodie Martin")
    assert item.slug == "op-lodie"

    earlier_rule.undo()
    await svc.sync()

    assert (await svc.roster_item("operator", "op-lodie")) is not None
    assert (await svc.roster_item("operator", "op-elodie")) is None
    assert not _errors(await svc.check())


async def test_a_skill_keeps_resolving_by_its_stored_slug(svc, earlier_rule):
    item = await svc.add_skill("Réduire")
    assert item.slug == "r-duire"

    earlier_rule.undo()
    await svc.sync()

    assert (await svc.roster_item("skill", "r-duire")) is not None
    assert (await svc.roster_item("skill", "reduire")) is None


async def test_a_memory_entry_keeps_its_filename_stem(svc, earlier_rule):
    entry = await svc.memory_add("manager", "Élodie prefers short replies")
    earlier_rule.undo()

    shown = await svc.memory_show("manager", entry.slug)

    assert shown.slug == entry.slug


# (verb, first name added under the earlier rule, second name added under the current rule)
_REFUSED = [
    pytest.param("operator", "Élodie Martin", "Élodie Martin", "op-lodie", id="operator"),
    pytest.param("skill", "Réduire", "Réduire", "r-duire", id="skill"),
    pytest.param("dev", "Élixir", "Élixir", "lixir-dev", id="dev"),
]


async def _add(svc, verb: str, name: str):
    if verb == "operator":
        return await svc.add_operator(name)
    if verb == "skill":
        return await svc.add_skill(name)
    return await svc.activate_role(None, from_template="dev", tech=name)


@pytest.mark.parametrize(("verb", "first", "again", "stored"), _REFUSED)
async def test_re_adding_is_refused_and_names_the_stored_slug(
    svc, earlier_rule, verb, first, again, stored
):
    await _add(svc, verb, first)
    earlier_rule.undo()

    with pytest.raises(SquadsError, match=stored):
        await _add(svc, verb, again)


async def test_an_explicit_operator_slug_is_compared_exactly(svc, earlier_rule):
    await svc.add_operator("Élodie Martin")
    earlier_rule.undo()

    other = await svc.add_operator("Élodie Martin", slug="op-elodie-two")

    assert other.slug == "op-elodie-two"


async def test_creation_reads_the_override_under_the_slug_the_role_is_stored_with(svc):
    roles_dir = svc.paths.squad_dir / ".overrides" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "node-js-dev.toml").write_text('full_name = "Custom Nodeperson"\n')

    item = await svc.activate_role(None, from_template="dev", tech="Node.js")

    assert item.slug == "node-js-dev"
    assert item.title == "Custom Nodeperson"
