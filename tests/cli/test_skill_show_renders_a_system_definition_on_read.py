"""``sq skill <slug> show``: where the body comes from is decided by the same ``kind:`` the panel
prints, and by nothing else.

A **system** skill's definition is rendered on this call, so it prints in full even though the
item file stores nothing; a **custom** skill's body is read from the item, because that is the
only place it lives. The panel above the body, ``--raw``, and ``--json`` are unchanged either way.

The empty case is the one that had to change meaning: for a system skill an empty answer no
longer means "unwritten, run a sync", it means the item type this skill described is no longer
declared — and the hint has to say what it means rather than name a command with no such effect.
"""

import json

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio

#: Drops the bundled ``guide`` type. ``sq-guide`` stays a template-owned slug (that membership is
#: deliberately bundled-blind), so its skill is still system — but there is no longer a type for
#: it to describe, so there is nothing to render.
_DROP_GUIDE = """\
[selected]
items = [
  "epic", "feature", "task", "bug", "decision", "contract", "milestone",
  "review", "role", "skill", "operator",
]
"""


@pytest.fixture
async def seeded(tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return result.paths


def _write_workflow_override(squad_dir, content: str) -> None:
    from squads import __version__

    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


async def test_show_prints_a_system_definition_although_the_item_stores_nothing(
    seeded, invoke
) -> None:
    svc = service.Service(seeded)
    item = await svc.roster_item("skill", "sq-task")
    assert item is not None
    assert await svc.read_body(item.id) == ""  # nothing stored

    r = await invoke(["skill", "sq-task", "show", "--raw"])
    assert r.exit_code == 0, r.output
    assert "system (template-owned)" in r.output
    assert "**Lifecycle:**" in r.output
    assert "sq task <n> subtask <k> body" in r.output


async def test_show_json_carries_every_field_including_system_and_no_body(seeded, invoke) -> None:
    r = await invoke(["skill", "sq-task", "show", "--json"])
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert set(payload) == {
        "id",
        "slug",
        "title",
        "status",
        "description",
        "when_to_use",
        "allowed_tools",
        "path",
        "system",
    }
    assert payload["slug"] == "sq-task"
    assert payload["system"] is True

    svc = service.Service(seeded)
    custom = await svc.add_skill("Release Runbook", description="Ship a release safely.")
    r = await invoke(["skill", str(custom.sequence_id), "show", "--json"])
    assert json.loads(r.output)["system"] is False


async def test_a_system_skill_for_an_undeclared_type_says_so_instead_of_naming_a_sync(
    seeded, invoke
) -> None:
    _write_workflow_override(seeded.squad_dir, _DROP_GUIDE)

    r = await invoke(["skill", "sq-guide", "show", "--raw"])
    assert r.exit_code == 0, r.output
    assert "system (template-owned)" in r.output
    assert "no longer declared" in r.output
    assert "sq sync" not in r.output


async def test_an_unwritten_custom_skill_body_points_at_the_body_verb(seeded, invoke) -> None:
    svc = service.Service(seeded)
    custom = await svc.add_skill("Release Runbook", description="Ship a release safely.")
    await svc.set_body(custom.id, "", force=True)

    r = await invoke(["skill", "release-runbook", "show", "--raw"])
    assert r.exit_code == 0, r.output
    assert "custom (authored)" in r.output
    assert "sq skill release-runbook body" in r.output
