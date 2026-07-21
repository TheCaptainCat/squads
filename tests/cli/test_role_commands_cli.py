"""``sq role catalog`` / ``sq role activate --help`` discoverability text for custom, non-bundled
roles: the non-JSON catalog output and the activate command's help both point at
``sq override scaffold --new <slug>``, while ``--json`` keeps its pinned bundled-only shape
(machine contract, tested at tests/cli/test_json_output_shape.py — this file only re-asserts it
stays unaffected by the new hint text).
"""

import json
import re

import pytest

pytestmark = pytest.mark.anyio


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text)


async def test_catalog_plain_output_points_at_the_scaffold_new_command(project, invoke) -> None:
    r = await invoke(["role", "catalog"])
    assert r.exit_code == 0, r.output
    output = _collapse_whitespace(r.output)
    assert "sq override scaffold --new" in output
    assert "sq role activate" in output


async def test_catalog_json_output_is_unaffected_bundled_roles_only(project, invoke) -> None:
    r = await invoke(["role", "catalog", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data  # bundled roles present
    assert all(set(row) == {"slug", "full_name", "title", "is_default"} for row in data)
    assert "scaffold" not in r.output


async def test_activate_help_mentions_the_custom_role_scaffold_path(project, invoke) -> None:
    r = await invoke(["role", "activate", "--help"])
    assert r.exit_code == 0, r.output
    output = _collapse_whitespace(r.output)
    assert "sq override scaffold --new" in output or ".overrides/roles" in output
