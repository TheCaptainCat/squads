"""A partial ``<tech>-dev.toml`` override, driven at the three CLI surfaces that resolve a
developer role: ``sq sync``, ``sq role <slug> show``, and ``sq check``. Each used to refuse a
file that ``sq dev add`` itself honours; each now loads it, with the overridden field taking
the override's value and every other field coming from the live role's own stored values.

Service-level proof of the merge/rename semantics lives in tests/service/test_partial_dev_
role_override_is_honoured_by_sync.py; the resolver-level proof lives in tests/unit/test_dev_
role_base_is_supplied_not_inferred.py and tests/unit/test_a_role_resolves_from_one_base_
chosen_by_its_stored_facts.py. This file is the CLI smoke test the acceptance criteria call for,
plus the check-report retirement (a file that now loads must not still be flagged) and the ``show``
card fallback fix.
"""

import json
from pathlib import Path

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio


def _place_dev_toml(squad_dir: Path, slug: str, content: str) -> None:
    target = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


async def test_sync_and_role_show_both_exit_0_on_a_partial_dev_override(
    project, svc, invoke
) -> None:
    await svc.activate_role(None, from_template="dev", tech="python")
    _place_dev_toml(project.squad_dir, "python-dev", 'title = "Senior Python developer"\n')

    shown = await invoke(["role", "python-dev", "show"])
    synced = await invoke(["sync"])

    assert shown.exit_code == 0, shown.output
    assert synced.exit_code == 0, synced.output
    assert "Senior Python developer" in shown.output


async def test_check_is_clean_on_a_squad_carrying_a_partial_dev_override(
    project, svc, invoke
) -> None:
    """The report this exact shape used to get is retired in the same change that makes the
    shape load -- leaving it would flag a file that now works."""
    await svc.activate_role(None, from_template="dev", tech="python")
    _place_dev_toml(
        project.squad_dir,
        "python-dev",
        f'# squads:override-base:{__version__}\ntitle = "Senior Python developer"\n',
    )

    result = await invoke(["check"])

    assert result.exit_code == 0, result.output
    assert "does not load" not in result.output


async def test_check_still_exits_non_zero_on_a_broken_dev_override(project, svc, invoke) -> None:
    await svc.activate_role(None, from_template="dev", tech="python")
    _place_dev_toml(project.squad_dir, "python-dev", 'model = "opuss"\n')

    result = await invoke(["check"])

    assert result.exit_code == 3, result.output
    assert "opuss" in result.output


async def test_a_live_dev_roles_show_renders_the_full_card_not_the_three_line_fallback(
    project, svc, invoke
) -> None:
    """Before this fix, ``resolve_role`` raised for every dev slug (override or not), so `show`
    degraded to the three-line item fallback (name, id, status). With a base it renders the
    full card like every other role -- title, model, spawn, creates, skills -- plus the
    resolved definition beneath it (mission, responsibilities) -- even with no override file
    present at all."""
    await svc.activate_role(None, from_template="dev", tech="python")

    result = await invoke(["role", "python-dev", "show"])

    assert result.exit_code == 0, result.output
    assert "can spawn:" in result.output
    assert "## Mission" in result.output
    assert "## Responsibilities" in result.output


async def test_a_live_dev_roles_json_show_carries_the_full_fields(project, svc, invoke) -> None:
    await svc.activate_role(None, from_template="dev", tech="python")

    result = await invoke(["role", "python-dev", "show", "--json"])
    data = json.loads(result.output)

    assert data["mission"]
    assert data["responsibilities"]
    assert data["title"] == "Python developer"


async def test_a_dev_toml_for_a_tech_with_no_roster_entry_is_reported_as_a_layer_with_no_base(
    project, svc, invoke
) -> None:
    """No ``sq dev add`` has run for this tech, so there is no role under the file: ``sq check``
    says so and the card refuses."""
    _place_dev_toml(project.squad_dir, "rust-dev", 'title = "Rust wrangler"\n')

    checked = await invoke(["check"])
    shown = await invoke(["role", "rust-dev", "show"])

    assert checked.exit_code != 0, checked.output
    assert "no role under it" in " ".join(checked.output.split())
    assert shown.exit_code == 1, shown.output


async def test_declaring_full_name_renames_nothing_via_the_sync_cli_command(
    project, svc, invoke
) -> None:
    await svc.activate_role(None, from_template="dev", tech="python")
    second = await svc.activate_role(None, from_template="dev", tech="typescript")
    _place_dev_toml(project.squad_dir, "typescript-dev", 'full_name = "Zara Typescript"\n')

    result = await invoke(["sync"])
    shown = await invoke(["role", "typescript-dev", "show", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(shown.output)["full_name"] == second.title


async def test_omitting_full_name_preserves_it_via_the_sync_cli_command(
    project, svc, invoke
) -> None:
    await svc.activate_role(None, from_template="dev", tech="python")
    second = await svc.activate_role(None, from_template="dev", tech="typescript")
    _place_dev_toml(project.squad_dir, "typescript-dev", 'title = "Senior TypeScript developer"\n')

    result = await invoke(["sync"])
    shown = await invoke(["role", "typescript-dev", "show", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(shown.output)["full_name"] == second.title
