"""A role's definition is resolved on every read and stored nowhere — the falsifiable guard on
the write path, driven rather than asserted from the key table.

Two halves, and both are needed. :mod:`tests.unit.test_role_def_extra_keys` pins the key table
itself; this drives a fresh squad through the real verbs (``activate_role``, ``add_dev``,
``sync``, ``repair``) and reads what actually lands on disk, so a *second* writer outside
``RoleDef.to_extra`` — a key spread into a create literal, a body rendered at activation —
still reddens it. That second writer is exactly what a table-only pin cannot see, and it is
what a corpus sweep would otherwise fight on alternate commands: strip on repair, restore on
sync.

The names below are the definition a role catalog answers. They are listed as a literal rather
than derived from ``RoleDef.extra_keys()``: deriving them would make this test agree with the
table by construction and pass on a table that silently regrew a member.
"""

import pytest

from squads import _sections as sections
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._roles._resolver import resolve_role_for_item

pytestmark = pytest.mark.anyio

#: Every ``extra`` key a role's definition used to be mirrored under.
_DEFINITION_KEYS = (
    "full_name",
    "title",
    "mission",
    "responsibilities",
    "agreements",
    "color",
    "can_spawn",
    "description",
)


async def _role_paths(svc):
    return [item_file(svc.paths, it) for it in await svc.list_roles()]


async def _drive_the_write_path(svc):
    """A fresh squad taken through every verb that creates or reconciles a role."""
    await svc.activate_role("architect")
    await svc.activate_role("qa", name="Grace Tester")
    await svc.add_dev("rust")
    await svc.sync()


async def test_no_role_file_stores_any_definition_key(svc):
    await _drive_the_write_path(svc)

    paths = await _role_paths(svc)
    assert len(paths) >= 4  # sanity: an empty roster would make every assertion below vacuous
    for path in paths:
        extra = read_frontmatter(path=path).get("extra", {})
        for key in _DEFINITION_KEYS:
            assert key not in extra, f"{path.name} stores {key!r}"


async def test_no_role_file_stores_its_rendered_definition(svc):
    """The other producer: activation used to render the whole definition into ``sq:body``.
    The region stays (its markers are the shape every item file shares) and is empty."""
    await _drive_the_write_path(svc)

    for path in await _role_paths(svc):
        text = path.read_text(encoding="utf-8")
        assert sections.has_section(text, markers.BODY), path.name
        assert not (sections.get_section(text, markers.BODY) or "").strip(), path.name


async def test_the_definition_is_still_answerable_for_every_role(svc):
    """The falsification of the two tests above: they would also pass if the definition had
    simply been lost. It has not — every field is resolvable on the call."""
    await _drive_the_write_path(svc)

    for item in await svc.list_roles():
        resolved = resolve_role_for_item(item, svc.paths.squad_dir)
        assert resolved.full_name.strip()
        assert resolved.title.strip()
        assert resolved.mission.strip()
        assert resolved.responsibilities


async def test_what_a_role_does_still_store(svc):
    """The residue, stated positively so a future removal has to argue with a test rather than
    with an absence: the dispatch slug for every role, and the developer identity — including
    a ``model`` a bundled role does not carry, because ``sq dev add --model`` is an operator
    setting with no catalog answer."""
    await _drive_the_write_path(svc)

    bundled = await svc.roster_item("role", "architect")
    assert bundled is not None
    assert bundled.extra == {X.SLUG: "architect"}

    dev = await svc.roster_item("role", "rust-dev")
    assert dev is not None
    assert dev.extra[X.SLUG] == "rust-dev"
    assert dev.extra[X.IS_DEV] is True
    assert dev.extra[X.TECH] == "rust"
    assert dev.extra[X.MODEL]  # a dev's model is stored; a bundled role's is not


async def test_a_repair_then_a_sync_restores_nothing(svc):
    """``repair`` then ``sync`` over a role corpus writes nothing back — byte-for-byte
    idempotence across the pair, not just within each command.

    That pair is the ordering a corpus sweep runs in (the sweep rides ``repair``'s corpus
    walk, and ``sync`` is what an operator runs next), so it is the pair that decides whether a
    sweep and a writer can end up undoing each other on alternate commands."""
    await _drive_the_write_path(svc)
    before = {path: path.read_text(encoding="utf-8") for path in await _role_paths(svc)}

    await svc.repair()
    await svc.sync()

    after = {path: path.read_text(encoding="utf-8") for path in await _role_paths(svc)}
    assert after == before
