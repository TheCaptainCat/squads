"""Three small, otherwise-unexercised CLI command surfaces: ``sq <type> <n> refs`` (the "none"
direction), ``sq <type> <n> ref rm``, ``sq <type> <n> remove``, and ``sq dev add``'s own
console output.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_refs_with_no_outgoing_edges_prints_a_clean_none_message(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "refs"])
    assert r.exit_code == 0, r.output
    assert "none" in r.output


async def test_ref_rm_removes_a_previously_added_forward_reference(project, invoke) -> None:
    await invoke(["create", "task", "A", "--author", "manager"])
    await invoke(["create", "task", "B", "--author", "manager"])
    await invoke(["task", "2", "ref", "add", "TASK-3", "--kind", "related"])
    assert "TASK-3" in (await invoke(["task", "2", "refs"])).output

    r = await invoke(["task", "2", "ref", "rm", "TASK-3"])
    assert r.exit_code == 0, r.output
    assert "TASK-3" not in (await invoke(["task", "2", "refs"])).output


async def test_remove_requires_confirmation_supports_json_and_severs_refs_with_force(
    project, invoke
) -> None:
    await invoke(["create", "task", "A", "--author", "manager"])
    await invoke(["create", "task", "B", "--author", "manager"])
    await invoke(["task", "3", "ref", "add", "TASK-2", "--kind", "related"])  # B -> A

    aborted = await invoke(["task", "2", "remove"], input="n\n")
    assert aborted.exit_code != 0

    blocked = await invoke(["task", "2", "remove", "--yes"])
    assert blocked.exit_code != 0  # a live ref still points at it; force is required

    r = await invoke(["task", "2", "remove", "--yes", "--force", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["removed_id"] == "TASK-2"
    assert "TASK-3" in data["severed_refs"]


async def test_remove_plain_output_names_the_removed_id_and_the_severed_referrers(
    project, invoke
) -> None:
    await invoke(["create", "task", "A", "--author", "manager"])
    await invoke(["create", "task", "B", "--author", "manager"])
    await invoke(["task", "3", "ref", "add", "TASK-2", "--kind", "related"])  # B -> A

    r = await invoke(["task", "2", "remove", "--yes", "--force"])
    assert r.exit_code == 0, r.output
    assert "removed TASK-2" in r.output
    assert "severed refs in" in r.output and "TASK-3" in r.output


async def test_dev_add_prints_the_slug_full_name_and_id(project, invoke) -> None:
    r = await invoke(["dev", "add", "--tech", "dotnet"])
    assert r.exit_code == 0, r.output
    assert "dotnet-dev" in r.output
    assert "ROLE-2" in r.output
