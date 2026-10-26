"""Driven, end to end: an activated non-dev role whose slug happens to end in ``-dev`` (a
wholly custom ``data-dev`` role, unrelated to ``sq dev add``) used to crash both ``sq role
<slug> show`` and ``sq check`` with an unhandled ``KeyError: 'tech'`` -- a traceback, not the
documented exit-1/exit-3 contract. Both now resolve it through the ordinary path, exactly as
they did before the dev-role-override change that introduced the regression.

The base-selection table lives at
tests/unit/test_a_role_resolves_from_one_base_chosen_by_its_stored_facts.py; this file is the
CLI-level confirmation for the realistic shapes.
"""

import json

import pytest

from _helpers import add_role_from_toml

pytestmark = pytest.mark.anyio


async def test_an_activated_non_dev_dev_suffixed_role_shows_and_checks_without_a_traceback(
    project, svc, invoke
) -> None:
    await add_role_from_toml(
        svc,
        "data-dev",
        'full_name = "Dana Analyst"\ntitle = "data steward"\n'
        'description = "Curates the project\'s datasets."\n'
        'mission = "Keep the data catalog accurate."\n',
    )

    shown = await invoke(["role", "data-dev", "show"])
    shown_json = await invoke(["role", "data-dev", "show", "--json"])
    checked = await invoke(["check"])

    assert shown.exit_code == 0, shown.output
    assert "Traceback" not in shown.output
    assert "Dana Analyst" in shown.output

    assert shown_json.exit_code == 0, shown_json.output
    assert "Traceback" not in shown_json.output
    assert json.loads(shown_json.output)["full_name"] == "Dana Analyst"

    assert checked.exit_code == 0, checked.output
    assert "Traceback" not in checked.output


async def test_a_genuine_dev_role_still_shows_and_checks_cleanly_alongside_the_fix(
    project, svc, invoke
) -> None:
    """Regression guard: the fix narrows the dev-base gate, so a real developer role must keep
    getting one."""
    await svc.activate_role(None, from_template="dev", tech="python")

    shown = await invoke(["role", "python-dev", "show"])
    checked = await invoke(["check"])

    assert shown.exit_code == 0, shown.output
    assert "Traceback" not in shown.output
    assert "skills:" in shown.output  # the full card, not the old fallback

    assert checked.exit_code == 0, checked.output
    assert "Traceback" not in checked.output


async def test_a_slug_that_merely_contains_dev_with_no_hyphen_gets_a_clean_error(
    project, invoke
) -> None:
    """``"dev"`` (no hyphen) is not ``-dev``-shaped at all -- unrelated to this fix, but part of
    the boundary the fix must not blur: an unknown slug still gets the ordinary clean refusal,
    never a crash."""
    result = await invoke(["role", "dev", "show"])

    assert result.exit_code == 1, result.output
    assert "Traceback" not in result.output
    assert "error:" in result.output
