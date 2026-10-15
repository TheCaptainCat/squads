"""`body_written` over the body states of every type that accepts it: an item is reported
exactly when a plain `set_body` (no force) would be accepted as a first write, so the check and
the overwrite guard share one meaning of "unwritten". Each state is built on every row, scaffold
shapes included (a rendered view tag, empty headings, an interpolated field, a project template).
"""

from collections.abc import Awaitable, Callable

import pytest

from _helpers import create_item
from _selection_table import (
    BODY_WRITTEN,
    BODY_WRITTEN_MEMBER,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)
from squads import _sections as sections
from squads import _views as views
from squads._errors import SquadsError
from squads._models import _markers as markers
from squads._models._item import Item
from squads._rendering._engine import invalidate_squad_dir
from squads._services import _service as service

pytestmark = pytest.mark.anyio

type Build = Callable[[service.Service, TypeRow], Awaitable[Item]]


def _scaffold_prose(svc: service.Service, item: Item) -> str:
    scaffold = svc.pristine_body(item)
    assert scaffold is not None
    return views.strip_view_tags(scaffold).strip()


async def _created(svc: service.Service, row: TypeRow) -> Item:
    return (await create_item(svc, row.type, "t")).item


async def _created_with_a_body(svc: service.Service, row: TypeRow) -> Item:
    return (await create_item(svc, row.type, "t", body=BODY_WRITTEN)).item


async def _written_afterwards(svc: service.Service, row: TypeRow) -> Item:
    item = await _created(svc, row)
    return await svc.set_body(item.id, BODY_WRITTEN)


async def _appended_to_the_scaffold(svc: service.Service, row: TypeRow) -> Item:
    item = await _created(svc, row)
    return await svc.set_body(item.id, BODY_WRITTEN, append=True)


async def _replaced_with_the_scaffold(svc: service.Service, row: TypeRow) -> Item:
    item = await _created(svc, row)
    return await svc.set_body(item.id, _scaffold_prose(svc, item))


async def _scaffold_with_other_whitespace(svc: service.Service, row: TypeRow) -> Item:
    item = await _created(svc, row)
    return await svc.set_body(item.id, f"\n\n{_scaffold_prose(svc, item)}\n\n")


def _edit_file(svc: service.Service, item: Item, edit: Callable[[str], str]) -> None:
    path = svc.paths.squad_dir / item.path
    path.write_text(edit(path.read_text(encoding="utf-8")), encoding="utf-8")


async def _empty_region(svc: service.Service, row: TypeRow) -> Item:
    item = await _created(svc, row)
    _edit_file(svc, item, lambda text: sections.replace_section(text, markers.BODY, ""))
    return item


async def _no_region(svc: service.Service, row: TypeRow) -> Item:
    item = await _created(svc, row)
    drop = (markers.open_marker(markers.BODY), markers.close_marker(markers.BODY))
    _edit_file(svc, item, lambda text: text.replace(drop[0], "").replace(drop[1], ""))
    return item


async def _template_no_longer_renders(svc: service.Service, row: TypeRow) -> Item:
    item = await _created(svc, row)
    templates = svc.paths.squad_dir / ".overrides" / "templates" / "items"
    templates.mkdir(parents=True, exist_ok=True)
    (templates / f"{row.type}.md.j2").write_text(
        "<!-- sq:body -->\n{{ no_such_variable }}\n<!-- sq:body:end -->\n", encoding="utf-8"
    )
    invalidate_squad_dir(svc.paths.squad_dir)
    return item


#: State -> (how the item gets into it, whether `body_written` reports it).
_STATES: dict[str, tuple[Build, bool]] = {
    "created-with-no-body": (_created, True),
    "created-with-a-body": (_created_with_a_body, False),
    "written-afterwards": (_written_afterwards, False),
    "appended-to-the-scaffold": (_appended_to_the_scaffold, False),
    "replaced-with-the-scaffold": (_replaced_with_the_scaffold, True),
    "scaffold-with-other-surrounding-whitespace": (_scaffold_with_other_whitespace, True),
    "empty-body-region": (_empty_region, True),
    "no-body-region": (_no_region, False),
    "template-no-longer-renders": (_template_no_longer_renders, False),
}
#: The overwrite guard has nothing to say about a file with no body region at all.
_NOT_GUARDED = frozenset({"no-body-region"})


@pytest.mark.parametrize("state", _STATES)
@pytest.mark.parametrize("row", BODY_WRITTEN_MEMBER.accepting_rows(), ids=lambda r: r.id)
async def test_an_item_is_reported_exactly_when_a_first_body_write_would_be_accepted(
    project, row: TypeRow, state: str
) -> None:
    build, expected = _STATES[state]
    item = await build(service_with(project.squad_dir, override_toml(row, ())), row)

    svc = service_with(project.squad_dir, override_toml(row, ("body_written",)))
    found = member_findings(await svc.check(), BODY_WRITTEN_MEMBER)
    assert [i for _, i, _ in found] == ([item.id] if expected else []), state

    if state in _NOT_GUARDED:
        return
    try:
        await svc.set_body(item.id, "A first body.")
    except SquadsError:
        accepted = False
    else:
        accepted = True
    assert accepted is expected, state
