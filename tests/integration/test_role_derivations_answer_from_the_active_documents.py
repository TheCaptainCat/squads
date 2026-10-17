"""What a role is given -- its pointer's skills, its create lane, the out-of-lane warning and the
config-integrity rules -- is derived from the squad's own workflow and playbook documents, on
every production surface, never from the bundled ones.

One table: an active-document state by the answer each surface gives for one role.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from squads import __version__
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio

_GUIDE_ON_CONTRACT = """# squads:override-base:{version}
[types.contract]
roles = [
    "$(*self)",
    {{ slug = "devops", enter = ["read the contract"], do = ["check it"], authors = {authors} }},
]
"""


def _playbook_with_devops_guide(authors: bool) -> str:
    return _GUIDE_ON_CONTRACT.format(version=__version__, authors=str(authors).lower())


def _workflow_dropping(item_type: str) -> str:
    kept = sorted(t for t in bundled_spec().items if t != item_type)
    return f"# squads:override-base:{__version__}\n[selected]\nitems = {kept!r}\n"


@dataclass(frozen=True)
class _Row:
    role: str
    item_type: str
    override_file: str | None
    override_body: str | None
    preloads_skill: bool
    lane_has_type: bool
    warns_on_create: bool | None
    archives_the_skill: bool
    check_flags_archived_skill: bool


_ROWS: dict[str, _Row] = {
    "bundled": _Row(
        role="devops",
        item_type="contract",
        override_file=None,
        override_body=None,
        preloads_skill=False,
        lane_has_type=False,
        warns_on_create=True,
        archives_the_skill=True,
        check_flags_archived_skill=False,
    ),
    "playbook-guide-reads-the-type": _Row(
        role="devops",
        item_type="contract",
        override_file="playbook.toml",
        override_body=_playbook_with_devops_guide(False),
        preloads_skill=True,
        lane_has_type=False,
        warns_on_create=True,
        archives_the_skill=True,
        check_flags_archived_skill=True,
    ),
    "playbook-guide-authors-the-type": _Row(
        role="devops",
        item_type="contract",
        override_file="playbook.toml",
        override_body=_playbook_with_devops_guide(True),
        preloads_skill=True,
        lane_has_type=True,
        warns_on_create=False,
        archives_the_skill=True,
        check_flags_archived_skill=True,
    ),
    "workflow-drops-the-type": _Row(
        role="architect",
        item_type="guide",
        override_file="workflow.toml",
        override_body=_workflow_dropping("guide"),
        preloads_skill=False,
        lane_has_type=False,
        warns_on_create=None,
        archives_the_skill=False,
        check_flags_archived_skill=False,
    ),
}


@pytest.mark.parametrize("name", list(_ROWS))
async def test_every_surface_answers_from_the_active_documents(name, project, svc, invoke) -> None:
    row = _ROWS[name]
    skill_name = f"sq-{row.item_type}"
    await svc.activate_role(row.role)
    if row.archives_the_skill:
        skill = await svc.add_skill(skill_name)
        await svc.set_status(skill.id, "Archived")

    if row.override_file is not None:
        assert row.override_body is not None
        overrides = project.squad_dir / ".overrides"
        overrides.mkdir(exist_ok=True)
        (overrides / row.override_file).write_text(row.override_body, encoding="utf-8")

    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output

    pointer = Path(project.root) / ".claude" / "agents" / f"{row.role}.md"
    pointer_text = pointer.read_text(encoding="utf-8")
    assert (f"- {skill_name}\n" in pointer_text) is row.preloads_skill, pointer_text

    shown = await invoke(["role", row.role, "show", "--json"])
    assert shown.exit_code == 0, shown.output
    payload = json.loads(shown.output)
    assert (row.item_type in payload["create_lane"]) is row.lane_has_type
    assert (skill_name in payload["skills"]) is row.preloads_skill

    text = await invoke(["role", row.role, "show"])
    assert text.exit_code == 0, text.output
    expected_lane = ", ".join(payload["create_lane"]) or "—"
    assert f"creates: {expected_lane}" in text.output

    if row.warns_on_create is not None:
        created = await invoke(["create", row.item_type, "A new item", "--author", row.role])
        assert created.exit_code == 0, created.output
        assert ("advisory" in created.output) is row.warns_on_create, created.output

    checked = await invoke(["check"])
    assert ("config integrity" in checked.output) is row.check_flags_archived_skill, checked.output


_MOVE_DESIGNATION = """# squads:override-base:{version}
[[roles]]
slug = "manager"
is_default = false

[[roles]]
slug = "tech-lead"
is_default = true
"""


@pytest.mark.parametrize(
    ("moved", "author", "warns"),
    [(False, "manager", False), (True, "manager", True)],
    ids=["bundled-designation", "moved-no-live-holder"],
)
async def test_the_lane_exemption_follows_the_designation_of_the_resolved_catalog(
    moved: bool, author: str, warns: bool, project, svc, invoke
) -> None:
    """With no live role holding the designation, the exemption goes to the default role of
    the catalog this squad resolves."""
    if moved:
        overrides = project.squad_dir / ".overrides"
        overrides.mkdir(exist_ok=True)
        (overrides / "roles.toml").write_text(
            _MOVE_DESIGNATION.format(version=__version__), encoding="utf-8"
        )
    created = await invoke(["create", "task", "A task", "--author", author])
    assert created.exit_code == 0, created.output
    assert ("advisory" in created.output) is warns, created.output
