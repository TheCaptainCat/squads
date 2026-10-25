"""What the playbook gives a role, by role shape and by document.

One row per (document, slug) for the role-to-type, role-to-skill and create-lane answers, then the
lane exemption, the lane owners, the per-role skill sections for a roster, and the example
assignee a generated command shows. A slug is judged by its spelling, so ``platform-dev`` answers
as ``python-dev`` does; the rows record those answers as they stand.
"""

import pytest

from _helpers import role_of
from squads._interactions._models import PlaybookSpec, RoleGuideSpec
from squads._interactions._playbook import get_playbook_spec
from squads._interactions._role_guidance import (
    allowed_create_types,
    example_assignee_slug,
    in_lane_owner,
    is_lane_exempt,
    item_skill_role_sections,
    item_types_for_role,
    skills_for_role,
)
from squads._roles._projection import RoleView
from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec


def _with_authoring_guides() -> PlaybookSpec:
    base = get_playbook_spec()
    bug = base.types["bug"]
    guides = [
        *bug.roles,
        RoleGuideSpec(slug="guardian", authors=True, do=["Guard."]),
        RoleGuideSpec(slug="*dev", authors=True),
    ]
    return base.model_copy(
        update={"types": {**base.types, "bug": bug.model_copy(update={"roles": guides})}}
    )


def _without_task() -> WorkflowSpec:
    spec = bundled_spec()
    return spec.model_copy(update={"items": {k: v for k, v in spec.items.items() if k != "task"}})


_DOCS: dict[str, tuple[WorkflowSpec, PlaybookSpec]] = {
    "bundled": (bundled_spec(), get_playbook_spec()),
    "playbook-adds-an-authoring-guide": (bundled_spec(), _with_authoring_guides()),
    "workflow-drops-a-type": (_without_task(), get_playbook_spec()),
}
_ALWAYS = ["squads", "greeting", "sq-memory"]
_DEV_TYPES = ["task", "bug", "contract", "review"]
_DEV_SKILLS = [*_ALWAYS, "sq-task", "sq-bug", "sq-contract", "sq-review"]
_ARCHITECT_TYPES = ["epic", "decision", "contract", "guide"]
_ARCHITECT_SKILLS = [*_ALWAYS, "sq-epic", "sq-decision", "sq-contract", "sq-guide"]
_NOTHING = ([], _ALWAYS, set[str]())

#: (document, slug) -> (item types, skills, create lane).
_ANSWERS: dict[tuple[str, str], tuple[list[str], list[str], set[str]]] = {
    ("bundled", "architect"): (_ARCHITECT_TYPES, _ARCHITECT_SKILLS, {"decision", "guide"}),
    ("bundled", "python-dev"): (_DEV_TYPES, _DEV_SKILLS, set()),
    ("bundled", "platform-dev"): (_DEV_TYPES, _DEV_SKILLS, set()),
    ("bundled", "guardian"): _NOTHING,
    ("bundled", "op-alice"): _NOTHING,
    ("bundled", "nobody"): _NOTHING,
    ("playbook-adds-an-authoring-guide", "architect"): (
        _ARCHITECT_TYPES,
        _ARCHITECT_SKILLS,
        {"decision", "guide"},
    ),
    ("playbook-adds-an-authoring-guide", "python-dev"): (_DEV_TYPES, _DEV_SKILLS, {"bug"}),
    ("playbook-adds-an-authoring-guide", "platform-dev"): (_DEV_TYPES, _DEV_SKILLS, {"bug"}),
    ("playbook-adds-an-authoring-guide", "guardian"): (
        ["bug"],
        [*_ALWAYS, "sq-bug"],
        {"bug"},
    ),
    ("playbook-adds-an-authoring-guide", "op-alice"): _NOTHING,
    ("playbook-adds-an-authoring-guide", "nobody"): _NOTHING,
    ("workflow-drops-a-type", "architect"): (
        _ARCHITECT_TYPES,
        _ARCHITECT_SKILLS,
        {"decision", "guide"},
    ),
    ("workflow-drops-a-type", "python-dev"): (
        ["bug", "contract", "review"],
        [*_ALWAYS, "sq-bug", "sq-contract", "sq-review"],
        set(),
    ),
    ("workflow-drops-a-type", "platform-dev"): (
        ["bug", "contract", "review"],
        [*_ALWAYS, "sq-bug", "sq-contract", "sq-review"],
        set(),
    ),
    ("workflow-drops-a-type", "guardian"): _NOTHING,
    ("workflow-drops-a-type", "op-alice"): _NOTHING,
    ("workflow-drops-a-type", "nobody"): _NOTHING,
}


@pytest.mark.parametrize(("doc", "slug"), list(_ANSWERS))
def test_the_playbook_answers_each_role_shape_per_document(doc: str, slug: str) -> None:
    spec, playbook = _DOCS[doc]
    types, skills, lane = _ANSWERS[doc, slug]
    assert item_types_for_role(role_of(slug), spec, playbook) == types
    assert skills_for_role(role_of(slug), spec, playbook) == skills
    assert allowed_create_types(role_of(slug), spec, playbook) == lane


@pytest.mark.parametrize(
    ("slug", "default_slug", "exempt"),
    [
        ("op-alice", None, True),
        ("architect", None, False),
        ("python-dev", None, False),
        ("guardian", None, False),
        ("nobody", None, False),
        ("guardian", "guardian", True),
        ("manager", "guardian", False),
    ],
)
def test_only_the_default_role_and_operators_are_exempt_from_the_lanes(
    slug: str, default_slug: str | None, exempt: bool
) -> None:
    assert is_lane_exempt(slug, default_slug) is exempt


@pytest.mark.parametrize(
    ("playbook", "item_type", "owners"),
    [
        (None, "task", ["tech-lead"]),
        (None, "bug", ["qa"]),
        (None, "review", ["reviewer"]),
        (None, "nothing", []),
        ("authoring", "bug", ["guardian", "qa"]),
        ("authoring", "task", ["tech-lead"]),
    ],
)
def test_the_lane_owners_of_a_type_never_include_the_dev_sentinel(
    playbook: str | None, item_type: str, owners: list[str]
) -> None:
    pb = _with_authoring_guides() if playbook else get_playbook_spec()
    assert sorted(in_lane_owner(item_type, pb, ())) == owners


def _view(slug: str, full_name: str, *capabilities: str) -> RoleView:
    return RoleView(
        slug=slug, full_name=full_name, title=slug, is_default=False, capabilities=capabilities
    )


_ARCHITECT = _view("architect", "Robert Architect")
_GUARDIAN = _view("guardian", "Gwen Guardian")
_PYTHON = _view("python-dev", "Elias Python", "dev")
_DECLARED = _view("backend-engineer", "Pat Platform", "dev")
_SUFFIXED = _view("platform-dev", "Pat Platform")


@pytest.mark.parametrize(
    ("roster", "titles"),
    [
        ([], []),
        ([_ARCHITECT, _GUARDIAN], []),
        ([_ARCHITECT, _PYTHON], ["`*dev`: Elias Python (`python-dev`)"]),
        ([_DECLARED], ["`*dev`: Pat Platform (`backend-engineer`)"]),
        (
            [_PYTHON, _DECLARED],
            ["`*dev`: Elias Python (`python-dev`), Pat Platform (`backend-engineer`)"],
        ),
        ([_SUFFIXED], []),
        ([_view("op-alice", "Alice")], []),
    ],
    ids=["empty", "no-holder", "templated", "declared", "two-holders", "suffixed-only", "operator"],
)
def test_a_capability_section_renders_only_while_a_live_role_holds_the_capability(
    roster: list[RoleView], titles: list[str]
) -> None:
    playbook = get_playbook_spec()
    for item_type in ("task", "bug"):
        sections = item_skill_role_sections(playbook.types[item_type], roster)
        assert [s["title"] for s in sections] == titles


def test_a_named_role_guide_renders_only_for_a_live_role_and_no_playbook_renders_nothing() -> None:
    playbook = _with_authoring_guides()
    sections = item_skill_role_sections(playbook.types["bug"], [_ARCHITECT, _GUARDIAN])
    assert [s["title"] for s in sections] == ["Gwen Guardian (`guardian`)"]
    assert item_skill_role_sections(None, [_PYTHON]) == []


@pytest.mark.parametrize(
    ("roles", "developers", "expected"),
    [
        (None, (), "<slug>"),
        ([], (), "<slug>"),
        ([{"slug": "architect"}, {"slug": "python-dev"}], ("python-dev",), "python-dev"),
        ([{"slug": "architect"}, {"slug": ""}], (), "architect"),
        ([{"x": "y"}], (), "<slug>"),
        ([_ARCHITECT, _PYTHON], ("python-dev",), "python-dev"),
        ([_ARCHITECT, _DECLARED], ("backend-engineer",), "backend-engineer"),
        ([_ARCHITECT, _SUFFIXED], (), "architect"),
        ([_ARCHITECT, _GUARDIAN], (), "architect"),
        ([_view("op-alice", "Alice")], (), "op-alice"),
    ],
    ids=[
        "absent",
        "empty",
        "mappings-prefer-developer",
        "mappings-skip-blank",
        "mapping-without-slug",
        "views-prefer-developer",
        "declared-developer",
        "suffixed-is-not-a-developer",
        "views-first",
        "operator",
    ],
)
def test_the_example_assignee_prefers_a_live_developer_then_the_first(
    roles: list[object] | None, developers: tuple[str, ...], expected: str
) -> None:
    assert example_assignee_slug(roles, developers) == expected  # pyright: ignore[reportArgumentType]
