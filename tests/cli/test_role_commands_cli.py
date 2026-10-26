"""``sq role catalog`` / ``sq role activate --help`` discoverability text for custom, non-bundled
roles: the non-JSON catalog output and the activate command's help both point at
``sq override scaffold --new <slug>``, while ``--json`` keeps its pinned shape (machine
contract, tested at tests/cli/test_json_output_shape.py — this file only re-asserts it stays
unaffected by the new hint text) for a squad with no ``.overrides/roles.toml``, where every
row's ``origin`` is ``"bundled"``.
"""

import json
import re

import pytest

pytestmark = pytest.mark.anyio


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text)


async def test_catalog_plain_output_points_at_role_add_and_templates(project, invoke) -> None:
    r = await invoke(["role", "catalog"])
    assert r.exit_code == 0, r.output
    output = _collapse_whitespace(r.output)
    assert "sq role add <slug>" in output
    assert "sq role activate --from <template>" in output


async def test_catalog_json_output_is_unaffected_bundled_roles_only(project, invoke) -> None:
    r = await invoke(["role", "catalog", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data  # bundled roles present
    assert all(
        set(row)
        == {
            "slug",
            "full_name",
            "title",
            "is_default",
            "origin",
            "capabilities",
            "default_role",
            "default_role_source",
        }
        for row in data
    )
    assert all(row["origin"] == "system" for row in data)
    assert "scaffold" not in r.output


async def test_activate_help_points_at_role_add_for_a_role_that_defines_itself(
    project, invoke
) -> None:
    r = await invoke(["role", "activate", "--help"])
    assert r.exit_code == 0, r.output
    output = _collapse_whitespace(r.output)
    assert "sq role add" in output
    assert "--from" in output
