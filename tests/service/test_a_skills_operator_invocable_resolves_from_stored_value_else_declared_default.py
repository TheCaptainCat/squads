"""``operator_invocable`` resolves to the squad's stored boolean, else the default the skill's
bundled definition declares, else invocable; one resolver answers the value and whether it is
the squad's own. A table over skill shape by stored value."""

from datetime import UTC, datetime

import pytest

from _helpers import make_service, plant_attribute
from _invocable_squad import SHAPES, build_squad
from squads._interactions._skills import (
    OPERATOR_INVOCABLE_DEFAULTS,
    SKILL_DESCRIPTIONS,
    bundled_skill_slugs,
    resolve_operator_invocable,
)
from squads._models._attributes import AttributeKey
from squads._models._item import Item
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio

_NOW = datetime(2026, 6, 7, 10, 0, tzinfo=UTC)

#: (id, stored value, whether it counts as the squad's own)
STORED = [
    ("absent", None, False),
    ("true", True, True),
    ("false", False, True),
    ("string-no", "no", False),
    ("string-false", "false", False),
    ("int-one", 1, False),
    ("int-zero", 0, False),
    ("list", [True], False),
    ("empty-list", [], False),
]

#: The shapes the bundled spec alone can resolve (a project-declared type needs its override).
BUNDLED_SHAPES = [name for name, (slug, _) in SHAPES.items() if slug != "sq-incident"]


def _skill(slug: str, stored: object) -> Item:
    attributes = {} if stored is None else {AttributeKey.OPERATOR_INVOCABLE: stored}
    return Item(
        type="skill",
        sequence_id=1,
        title=slug,
        slug=slug,
        status="Active",
        path=f"agents/skills/{slug}.md",
        created_at=_NOW,
        updated_at=_NOW,
        attributes=attributes,
    )


@pytest.mark.parametrize("stored_id,stored,is_set", STORED, ids=[row[0] for row in STORED])
@pytest.mark.parametrize("shape", BUNDLED_SHAPES)
async def test_resolution_by_shape_and_stored_value(shape, stored_id, stored, is_set) -> None:
    slug, declared = SHAPES[shape]
    value, got_set = resolve_operator_invocable(slug, _skill(slug, stored), bundled_spec())
    assert got_set is is_set
    assert value is (stored if is_set else declared)


async def test_a_project_declared_types_skill_follows_the_per_type_default(
    tmp_path, monkeypatch, invoke
) -> None:
    paths = await build_squad(tmp_path, monkeypatch, invoke)
    svc = make_service(paths)
    item = await svc.roster_item("skill", "sq-incident")
    assert item is not None
    r = await invoke(["skill", "sq-incident", "show", "--json"])
    assert '"operator_invocable": false' in r.output
    assert '"operator_invocable_set": false' in r.output


@pytest.mark.parametrize("slug", ["squads", "sq-memory", "greeting", "sq-task"])
async def test_a_stored_value_equal_to_the_default_still_counts_as_the_squads_own(slug) -> None:
    spec = bundled_spec()
    assert resolve_operator_invocable(slug, _skill(slug, False), spec) == (False, True)


async def test_no_item_resolves_the_declared_default() -> None:
    spec = bundled_spec()
    assert resolve_operator_invocable("squads", None, spec) == (False, False)
    assert resolve_operator_invocable("onboarding", None, spec) == (True, False)


async def test_a_hand_stored_non_boolean_in_a_squad_resolves_as_absent(
    tmp_path, monkeypatch, invoke
) -> None:
    paths = await build_squad(tmp_path, monkeypatch, invoke)
    svc = make_service(paths)
    for slug, value in (("onboarding", "no"), ("squads", 1), ("sq-onboarding", ["x"])):
        item = await svc.roster_item("skill", slug)
        assert item is not None
        await plant_attribute(svc, item.id, AttributeKey.OPERATOR_INVOCABLE, value)
    for slug, declared in (("onboarding", True), ("squads", False), ("sq-onboarding", True)):
        row = (await invoke(["skill", slug, "show", "--json"])).output
        assert f'"operator_invocable": {str(declared).lower()}' in row
        assert '"operator_invocable_set": false' in row


async def test_every_always_on_skill_declares_exactly_one_default() -> None:
    assert set(OPERATOR_INVOCABLE_DEFAULTS) == set(SKILL_DESCRIPTIONS)
    assert set(OPERATOR_INVOCABLE_DEFAULTS) <= set(bundled_skill_slugs())
