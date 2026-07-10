"""The advisory create-lane warning at the CLI surface: sq create prints it (exit 0, item
still created), --json carries the lane_warning field, and sq role show surfaces the
role's creates: lane (text + JSON). Service-level facts live in
tests/service/test_create_lane_advisory.py.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_out_of_lane_create_prints_the_warning_and_exits_0(project, svc, invoke) -> None:
    await svc.add_dev("python")
    r = await invoke(["create", "feature", "Bad Feature", "--author", "python-dev"])
    assert r.exit_code == 0, r.output
    assert "advisory" in r.output
    assert "python-dev" in r.output
    assert "product-owner" in r.output
    assert "created" in r.output  # the item is still created despite the warning


async def test_in_lane_create_prints_no_warning(project, svc, invoke) -> None:
    await svc.activate_role("tech-lead")
    r = await invoke(["create", "task", "A task", "--author", "tech-lead"])
    assert r.exit_code == 0, r.output
    assert "advisory" not in r.output


async def test_manager_is_exempt_no_warning_on_the_cli(project, invoke) -> None:
    r = await invoke(["create", "feature", "Manager Feature", "--author", "manager"])
    assert r.exit_code == 0, r.output
    assert "advisory" not in r.output


async def test_create_guide_out_of_lane_also_prints_the_warning(project, svc, invoke) -> None:
    await svc.add_dev("python")
    r = await invoke(["create", "guide", "My Guide", "--author", "python-dev"])
    assert r.exit_code == 0, r.output
    assert "advisory" in r.output


async def test_json_output_carries_the_lane_warning_field_when_out_of_lane(
    project, svc, invoke
) -> None:
    await svc.add_dev("python")
    r = await invoke(["create", "feature", "JSON Feature", "--author", "python-dev", "--json"])
    data = json.loads(r.output)
    assert data["lane_warning"] is not None
    assert "advisory" in data["lane_warning"]


async def test_json_output_has_no_lane_warning_when_in_lane(project, svc, invoke) -> None:
    await svc.activate_role("tech-lead")
    r = await invoke(["create", "task", "In-lane task", "--author", "tech-lead", "--json"])
    assert json.loads(r.output).get("lane_warning") is None


async def test_advisory_wording_makes_no_enforcement_grade_claims(project, svc, invoke) -> None:
    await svc.add_dev("python")
    r = await invoke(["create", "feature", "Test Feature", "--author", "python-dev"])
    out = r.output.lower()
    assert "advisory" in out or "best-effort" in out
    for forbidden in ("tamper-evident", "forge-proof", "security", "blocked", "prevented"):
        assert forbidden not in out


class TestRoleShowSurfacesCreateLane:
    async def test_prints_a_creates_row(self, project, invoke) -> None:
        r = await invoke(["role", "product-owner", "show"])
        assert r.exit_code == 0, r.output
        assert "creates:" in r.output

    async def test_lists_every_type_in_the_lane(self, project, invoke) -> None:
        r = await invoke(["role", "product-owner", "show"])
        assert "feature" in r.output and "epic" in r.output

    async def test_an_empty_lane_shows_the_advisory_note(self, project, invoke) -> None:
        r = await invoke(["role", "devops", "show"])
        assert "out-of-lane creates warn" in r.output

    async def test_json_includes_the_create_lane_array(self, project, invoke) -> None:
        r = await invoke(["role", "product-owner", "show", "--json"])
        data = json.loads(r.output)
        assert set(data["create_lane"]) == {"feature", "epic"}

    async def test_json_create_lane_is_empty_for_a_dev(self, project, svc, invoke) -> None:
        await svc.add_dev("python")
        r = await invoke(["role", "python-dev", "show", "--json"])
        assert json.loads(r.output)["create_lane"] == []

    async def test_json_create_lane_for_tech_lead(self, project, invoke) -> None:
        r = await invoke(["role", "tech-lead", "show", "--json"])
        assert json.loads(r.output)["create_lane"] == ["task"]
