"""An omitted field with a declared default is stored at creation; one without stays unset; a
given value wins; existing items are not backfilled."""

import json

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


# (type, fields given, field read back, expected stored code)
CREATES = {
    "omitted, declared default": ("bug", None, "severity", "medium"),
    "omitted, no default": ("bug", None, "priority", None),
    "given beats the default": ("bug", {"severity": "low"}, "severity", "low"),
    "type without the field": ("task", None, "severity", None),
}


@pytest.mark.parametrize("case", list(CREATES))
async def test_create_stores_the_default_only_for_an_omitted_declared_field(svc, case) -> None:
    item_type, fields, field, expected = CREATES[case]

    created = (await create_item(svc, item_type, "T", fields=fields)).item

    assert created.badge_value(field) == expected
    assert (await svc.get(created.id)).badge_value(field) == expected


async def test_the_import_create_op_stores_the_default(svc) -> None:
    line = json.dumps({"op": "create", "type": "bug", "title": "Imported", "as": "manager"})

    result = await svc.import_events(line, default_as="manager")

    assert result.plan.ok, [i.message for i in result.plan.issues]
    bug = next(i for i in await svc.list_items(item_type="bug") if i.title == "Imported")
    assert bug.badge_value("severity") == "medium"


async def test_an_existing_item_with_no_stored_value_still_shows_none(svc) -> None:
    bug = (await create_item(svc, "bug", "Old")).item
    path = item_file(svc.paths, bug)
    text = path.read_text(encoding="utf-8")
    frontmatter = read_frontmatter(text=text)
    frontmatter.pop("severity", None)
    path.write_text(sections.replace_frontmatter(text, frontmatter), encoding="utf-8")
    await svc.repair()

    assert (await svc.get(bug.id)).badge_value("severity") is None
