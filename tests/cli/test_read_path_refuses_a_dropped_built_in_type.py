"""The read path (``sq <type> <n> <verb>``) for a built-in type dropped from the active spec
(via ``[selected]``): the type must stop being advertised by ``sq --help``, and resolving an
item ID against the dropped type must give the one accurate, ``[selected]``-provenance-bearing
refusal — the read-path counterpart of the create-path fix in
tests/cli/test_create_refuses_a_dropped_built_in_type.py.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

_DROP_GUIDE = """\
# squads:override-base:0.12.3
[selected]
items = ["epic", "feature", "task", "bug", "decision", "review", "role", "skill", "operator"]
"""


def _write_override(squad_dir: Path, toml: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(toml, encoding="utf-8")


async def test_a_dropped_type_is_not_offered_by_root_help(project, invoke) -> None:
    _write_override(project.squad_dir, _DROP_GUIDE)

    help_result = await invoke(["--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "guide" not in help_result.output
    # Surviving built-ins are still offered.
    assert "task" in help_result.output
    assert "bug" in help_result.output


async def test_an_undropped_squad_still_offers_every_built_in_type_at_the_root(
    project, invoke
) -> None:
    """No override present — byte-identical to today: nothing is hidden."""
    help_result = await invoke(["--help"])
    for t in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
        assert t in help_result.output


async def test_resolving_an_item_of_a_dropped_type_names_it_as_dropped_by_the_override(
    project, invoke
) -> None:
    _write_override(project.squad_dir, _DROP_GUIDE)

    result = await invoke(["guide", "1", "show"])
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "unknown item type 'guide'" in result.output
    assert "[selected]" in result.output
    assert "selected.items" in result.output
    # Never the misleading "declare it or check for a typo" advice — declaring it does not
    # restore it, and it is not a typo.
    assert "check for a typo" not in result.output


async def test_resolving_an_item_of_a_dropped_type_by_its_alias_gives_the_same_refusal(
    project, invoke
) -> None:
    _write_override(project.squad_dir, _DROP_GUIDE)

    result = await invoke(["g", "1", "show"])
    assert result.exit_code != 0
    assert "unknown item type 'guide'" in result.output
    assert "[selected]" in result.output


async def test_resolving_a_type_that_never_existed_at_all_names_no_false_provenance(
    project, invoke
) -> None:
    """A type that was never bundled and never declared must NOT be told it was "dropped from
    a [selected] list" — distinct scenario, same membership gate, different branch."""
    from squads._cli._common import resolve_item_id_typed
    from squads._errors import SquadsError
    from squads._services._service import open_service

    svc = open_service()
    with pytest.raises(SquadsError) as exc_info:
        await resolve_item_id_typed("1", "totally-bogus-type", svc)
    message = str(exc_info.value)
    assert "unknown item type 'totally-bogus-type'" in message
    assert "[selected]" not in message
    assert "dropped" not in message
    assert "check for a typo" in message
