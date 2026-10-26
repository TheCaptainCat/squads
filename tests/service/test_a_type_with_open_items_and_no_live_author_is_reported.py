"""`sq check` reports a non-roster type that holds an item at a status that is not settled while
no live role is an in-lane author of it, when the squad selects `type_has_live_author`. The
finding names what brings an author back: the catalog or roster role to activate or reactivate
(for a capability lane, each role holding the capability), a developer to add, or nothing when
no guide authors the type at all.
"""

from dataclasses import dataclass, field

import pytest

from _helpers import create_item
from _selection_table import DECLARED_ROWS, override_toml, write_override
from squads import __version__
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_FRAGMENT = "no live role authors it"
_INCIDENT = override_toml(next(r for r in DECLARED_ROWS if r.type == "incident"), ())
_RETIRED = (
    '[statuses.Retired]\nrole = "retired"\n\n[lifecycles.agent.transitions]\n'
    'Active = ["Archived", "Retired"]\nArchived = ["Active"]\nRetired = []\n'
)
_DESELECTED = "[squad]\nvalidators = []\n"
_AS_ERROR = '[squad]\nvalidators = ["type_has_live_author@error"]\n'
_KEPT = '[squad]\nvalidators = ["$(*squad.validators)", "dependency_acyclic"]\n'
_PLAN_AUTHORS_TASK = (
    '[types.task]\nroles = [{ slug = "*plan", authors = true, do = ["plan it"] }]\n'
)
_DEV_AUTHORS_BUG = '[types.bug]\nroles = [{ slug = "*dev", authors = true, do = ["fix it"] }]\n'


@dataclass(frozen=True)
class Shape:
    item_type: str
    live: tuple[str, ...] = ()
    moved: dict[str, str] = field(default_factory=dict)  # live role slug -> status it moves to
    developers: tuple[str, ...] = ()  # technologies of developers added, then archived
    settled: bool = False
    workflow: str = ""
    playbook: str = ""
    level: str = "warn"
    expect: tuple[str, ...] | None = None  # fragments of the one finding, None for silence
    absent: tuple[str, ...] = ()  # fragments the finding must not carry


_SHAPES: dict[str, Shape] = {
    "sole-author-live": Shape("review", live=("reviewer",)),
    "sole-author-never-activated": Shape(
        "review", expect=("type 'review'", "`sq role activate reviewer`")
    ),
    "sole-author-archived": Shape(
        "review",
        live=("reviewer",),
        moved={"reviewer": "Archived"},
        expect=("`sq role reviewer status Active`",),
        absent=("sq role activate", "--force"),
    ),
    "sole-author-archived-and-only-settled-items": Shape(
        "review", live=("reviewer",), moved={"reviewer": "Archived"}, settled=True
    ),
    "non-revivable-author-is-forced-back": Shape(
        "review",
        live=("reviewer",),
        moved={"reviewer": "Retired"},
        workflow=_RETIRED,
        expect=("`sq role reviewer status Active --force`", "Retired has no edge to Active"),
    ),
    "two-authors-one-live": Shape("guide", live=("architect",)),
    "two-authors-none-live": Shape(
        "guide", expect=("`sq role activate architect`", "`sq role activate tech-writer`")
    ),
    "capability-author-and-no-developer": Shape(
        "bug",
        playbook=_DEV_AUTHORS_BUG,
        expect=("add a developer", "sq dev add"),
        absent=("sq role activate",),
    ),
    "capability-author-held-by-a-catalog-role": Shape(
        "task",
        playbook=_PLAN_AUTHORS_TASK,
        expect=("`sq role activate tech-lead`",),
        absent=("add a developer",),
    ),
    "capability-author-held-by-an-archived-developer": Shape(
        "bug",
        playbook=_DEV_AUTHORS_BUG,
        developers=("python",),
        expect=("`sq role python-dev status Active`",),
        absent=("add a developer",),
    ),
    "type-no-guide-authors": Shape(
        "incident", workflow=_INCIDENT, expect=("type 'incident'",), absent=("activate", "—")
    ),
    "deselected": Shape("review", workflow=_DESELECTED),
    "raised-to-error": Shape(
        "review", workflow=_AS_ERROR, level="error", expect=("type 'review'",)
    ),
    "kept-in-a-replacing-list": Shape("review", workflow=_KEPT, expect=("type 'review'",)),
}


async def _findings(project, shape: Shape) -> list[tuple[str, str]]:
    if shape.workflow:
        write_override(project.squad_dir, shape.workflow)
    if shape.playbook:
        path = project.squad_dir / ".overrides" / "playbook.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# squads:override-base:{__version__}\n{shape.playbook}", encoding="utf-8")
    svc = service.open_service(client_cwd=project.squad_dir)
    roles = {slug: await svc.activate_role(slug) for slug in shape.live}
    item = (await create_item(svc, shape.item_type, "x")).item
    if shape.settled:
        await svc.update(item.id, status="Approved", force=True)
    for tech in shape.developers:
        developer = await svc.activate_role(None, from_template="dev", tech=tech)
        await svc.set_status(developer.id, "Archived")
    for slug, status in shape.moved.items():
        await svc.set_status(roles[slug].id, status)
    return [(i.level, i.message) for i in await svc.check() if _FRAGMENT in i.message]


@pytest.mark.parametrize("shape", _SHAPES)
async def test_a_type_is_reported_exactly_when_it_has_open_items_and_no_live_author(
    project, shape: str
) -> None:
    row = _SHAPES[shape]
    found = await _findings(project, row)
    if row.expect is None:
        assert found == []
        return
    assert len(found) == 1
    level, message = found[0]
    assert level == row.level
    assert all(fragment in message for fragment in row.expect)
    assert not any(fragment in message for fragment in row.absent)
