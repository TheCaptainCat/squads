"""A render context exposes the item flat: an attribute is read as ``item.<key>``, and there is no
``extra`` variable. A table over the bundled templates that read an attribute, each with the
attribute set and unset, and one over an adopter template reading an undeclared key."""

from datetime import UTC, datetime
from typing import Any

import pytest

from squads._errors import SquadsError
from squads._models._item import Item
from squads._rendering._engine import render, set_active_squad_dir
from squads._workflow import bundled_spec

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _item(item_type: str, attributes: dict[str, Any]) -> Item:
    spec = bundled_spec()
    return Item(
        sequence_id=1,
        type=item_type,
        prefix=spec.items[item_type].prefix,
        title="Example",
        slug="example",
        status="Draft",
        path=f"{spec.items[item_type].folder}/x.md",
        created_at=_NOW,
        updated_at=_NOW,
        attributes=attributes,
    )


#: (id, template, item type, attributes, fragment the render holds exactly when they are set)
ROWS = [
    (
        "review-target",
        "items/review.md.j2",
        "review",
        {"target_ref": "FEAT-2"},
        "**Target:** `FEAT-2`",
    ),
    (
        "skill-when-to-use",
        "agents/skill.md.j2",
        "skill",
        {"when_to_use": "Before a release"},
        "Before a release",
    ),
]


@pytest.mark.parametrize(
    ("template", "item_type", "attributes", "fragment"),
    [r[1:] for r in ROWS],
    ids=[r[0] for r in ROWS],
)
def test_a_bundled_template_reads_a_stored_attribute_from_the_item(
    template: str, item_type: str, attributes: dict[str, Any], fragment: str
) -> None:
    spec = bundled_spec()
    with_it = render(template, item=_item(item_type, attributes), description="", spec=spec)
    without = render(template, item=_item(item_type, {}), description="", spec=spec)

    assert fragment in with_it
    assert fragment not in without


def test_an_adopter_template_reads_an_undeclared_attribute_as_an_item_field(tmp_path) -> None:
    override = tmp_path / ".overrides" / "templates" / "items"
    override.mkdir(parents=True)
    (override / "guide.md.j2").write_text(
        "<!-- sq:body -->\n{{ item.hand_key }} {{ item.title }} {{ item.id }}\n"
        "<!-- sq:body:end -->\n",
        encoding="utf-8",
    )
    set_active_squad_dir(tmp_path)
    try:
        out = render(
            "items/guide.md.j2", item=_item("guide", {"hand_key": "keep-me"}), spec=bundled_spec()
        )
    finally:
        set_active_squad_dir(None)

    assert "keep-me Example GUIDE-1" in out


def test_a_template_reading_the_extra_variable_fails_to_render(tmp_path) -> None:
    override = tmp_path / ".overrides" / "templates" / "items"
    override.mkdir(parents=True)
    (override / "guide.md.j2").write_text("{{ extra.get('hand_key') }}\n", encoding="utf-8")
    set_active_squad_dir(tmp_path)
    try:
        with pytest.raises(SquadsError, match="extra"):
            render("items/guide.md.j2", item=_item("guide", {"hand_key": "x"}), spec=bundled_spec())
    finally:
        set_active_squad_dir(None)
