"""`sq role <slug> show` ends with how to change the role, in text output only."""

import json

import pytest

pytestmark = pytest.mark.anyio


def _scaffold_line(slug: str) -> str:
    return (
        "To change its mission or responsibilities: "
        f"`sq override scaffold --role {slug}`, edit the file, then `sq sync`. "
        f"To change its model: `sq role {slug} update --model …`."
    )


_OWN_FILE_LINE = "To change it: edit `.overrides/roles/auditor.toml`, then `sq sync`."


async def test_an_activated_bundled_role_ends_with_the_scaffold_line(svc, invoke) -> None:
    await svc.activate_role("reviewer")
    result = await invoke(["role", "reviewer", "show"])
    assert result.exit_code == 0, result.output
    assert result.output.rstrip().splitlines()[-1] == _scaffold_line("reviewer")


async def test_a_bundled_role_that_is_not_activated_ends_with_the_scaffold_line(
    project, invoke
) -> None:
    result = await invoke(["role", "reviewer", "show"])
    assert result.exit_code == 0, result.output
    assert result.output.rstrip().splitlines()[-1] == _scaffold_line("reviewer")


async def test_a_templated_developer_ends_with_the_scaffold_line(svc, invoke) -> None:
    await svc.activate_role(None, from_template="dev", tech="python")
    result = await invoke(["role", "python-dev", "show"])
    assert result.exit_code == 0, result.output
    assert result.output.rstrip().splitlines()[-1] == _scaffold_line("python-dev")


async def test_a_role_that_defines_itself_points_at_update(project, svc, invoke) -> None:
    await svc.add_role(
        "auditor",
        name="Alma Auditor",
        job_title="auditor",
        description="Audits.",
        mission="Audit the work.",
    )
    result = await invoke(["role", "auditor", "show"])
    assert result.exit_code == 0, result.output
    assert result.output.rstrip().splitlines()[-1] == (
        "To change its definition: `sq role auditor update --mission …` (or --file)."
    )


async def test_a_role_with_no_backing_definition_says_what_is_missing(project, svc, invoke) -> None:
    await svc.create(
        "role", "Alma Auditor", description="Audits.", slug="auditor", author="auditor"
    )
    result = await invoke(["role", "auditor", "show"])
    assert result.exit_code == 0, result.output
    tail = " ".join(result.output.split())
    assert "Nothing backs its definition" in tail
    assert "sq role auditor update --job-title" in tail


async def test_json_output_carries_no_change_hint(svc, invoke) -> None:
    await svc.activate_role("reviewer")
    result = await invoke(["role", "reviewer", "show", "--json"])
    assert result.exit_code == 0, result.output
    assert "sq override scaffold" not in result.output
    assert json.loads(result.output)["slug"] == "reviewer"
