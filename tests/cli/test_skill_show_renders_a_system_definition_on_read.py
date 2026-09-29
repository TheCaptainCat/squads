"""``sq skill <slug> show``: a system skill's body renders its declared view tag in full, a
custom skill's reads back its own authored content, and each empty case names a distinct hint."""

import json

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio

#: Drops the bundled ``guide`` type.
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


async def test_show_prints_a_system_definition_although_the_item_stores_only_its_own_tag(
    seeded, invoke
) -> None:
    from squads import _sections as sections
    from squads._models import _markers as markers

    svc = service.Service(seeded)
    item = await svc.roster_item("skill", "sq-task")
    assert item is not None
    stored = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    region = (sections.get_section(stored, markers.BODY) or "").strip("\n")
    assert region == markers.open_marker(markers.view_tag("item_skill"))

    r = await invoke(["skill", "sq-task", "show", "--raw"])
    assert r.exit_code == 0, r.output
    assert "system (template-owned)" in r.output
    assert "**Lifecycle:**" in r.output
    assert "sq task <n> subtask <k> body" in r.output


async def test_show_json_carries_every_field_including_system_and_the_exact_body(
    seeded, invoke
) -> None:
    """``--json``'s ``body`` is the same tag-expanded read every other reader gets, isolated
    with nothing else on stdout."""
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
        "body",
    }
    assert payload["slug"] == "sq-task"
    assert payload["system"] is True

    svc = service.Service(seeded)
    assert payload["body"] == await svc.read_body(await _sq_task_id(svc))

    custom = await svc.add_skill("Release Runbook", description="Ship a release safely.")
    r = await invoke(["skill", str(custom.sequence_id), "show", "--json"])
    custom_payload = json.loads(r.output)
    assert custom_payload["system"] is False
    assert custom_payload["body"] == await svc.read_body(custom.id)


async def _sq_task_id(svc: service.Service) -> str:
    item = await svc.roster_item("skill", "sq-task")
    assert item is not None
    return item.id


async def test_a_system_skill_for_an_undeclared_type_says_so_instead_of_naming_a_sync(
    seeded, invoke
) -> None:
    """A skill whose type is dropped is reclassified custom, and its hint names the drop."""
    _write_workflow_override(seeded.squad_dir, _DROP_GUIDE)

    r = await invoke(["skill", "sq-guide", "show", "--raw"])
    assert r.exit_code == 0, r.output
    assert "custom (authored)" in r.output
    assert "system (template-owned)" not in r.output
    assert "no longer" in r.output
    assert "declared" in r.output
    assert "sq sync" not in r.output


async def test_an_unwritten_custom_skill_body_points_at_the_body_verb(seeded, invoke) -> None:
    svc = service.Service(seeded)
    custom = await svc.add_skill("Release Runbook", description="Ship a release safely.")
    await svc.set_body(custom.id, "", force=True)

    r = await invoke(["skill", "release-runbook", "show", "--raw"])
    assert r.exit_code == 0, r.output
    assert "custom (authored)" in r.output
    assert "sq skill release-runbook body" in r.output
