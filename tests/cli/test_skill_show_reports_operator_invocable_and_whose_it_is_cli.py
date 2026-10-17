"""``sq skill <addr> show`` prints a skill's resolved ``operator_invocable`` and whether the squad
set it; ``--json`` carries ``operator_invocable`` and ``operator_invocable_set`` on every row."""

import pytest

from _invocable_squad import SHAPES, build_squad, skill_show

pytestmark = pytest.mark.anyio

JSON_KEYS = {
    "id",
    "slug",
    "title",
    "status",
    "description",
    "when_to_use",
    "allowed_tools",
    "operator_invocable",
    "operator_invocable_set",
    "path",
    "origin",
    "body",
}


@pytest.mark.parametrize("stored", [None, "yes", "no"])
@pytest.mark.parametrize("shape", SHAPES)
async def test_text_and_json_report_the_value_and_whose_it_is(
    shape, stored, tmp_path, monkeypatch, invoke
) -> None:
    slug, declared = SHAPES[shape]
    await build_squad(tmp_path, monkeypatch, invoke)
    if stored is not None:
        r = await invoke(["skill", slug, "update", "--operator-invocable", stored])
        assert r.exit_code == 0, r.output
    resolved = declared if stored is None else stored == "yes"

    row = await skill_show(invoke, slug)
    assert set(row) == JSON_KEYS
    assert row["operator_invocable"] is resolved
    assert row["operator_invocable_set"] is (stored is not None)

    r = await invoke(["skill", slug, "show", "--raw"])
    owner = "declared default" if stored is None else "set by this squad"
    assert f"operator invocable: {'yes' if resolved else 'no'} ({owner})" in r.output


async def test_a_value_equal_to_the_default_is_set_until_default_is_chosen(
    tmp_path, monkeypatch, invoke
) -> None:
    await build_squad(tmp_path, monkeypatch, invoke)
    await invoke(["skill", "squads", "update", "--operator-invocable", "no"])
    row = await skill_show(invoke, "squads")
    assert (row["operator_invocable"], row["operator_invocable_set"]) == (False, True)

    await invoke(["skill", "squads", "update", "--operator-invocable", "default"])
    row = await skill_show(invoke, "squads")
    assert (row["operator_invocable"], row["operator_invocable_set"]) == (False, False)
