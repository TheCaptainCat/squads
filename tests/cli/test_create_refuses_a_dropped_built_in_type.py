"""``sq create <type>`` for a built-in type dropped from the active spec (via ``[selected]``)
must give ONE clean, accurate refusal — no traceback, and no contradictory "no such command"
either — naming that the adopter's own override dropped it. It must also stop being advertised
by ``--help``/the command list. The read path already refuses cleanly for a dropped type; this
is the create-path counterpart.

The command stays registered and reachable (never hidden from Click's own dispatch): hiding it
there would let Click's unknown-command handler answer instead, whose did-you-mean suggestion
still sees the (merely help-hidden) name and would suggest the exact string the user typed —
contradicting the "unavailable" refusal in the same breath. Dispatching normally into
``svc.create`` lets its membership gate produce the one accurate message.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

# Drops `guide` and `bug` from the merged spec while keeping every other declared type
# (`milestone` included, and role/skill/operator, which are locked by key identity and must
# always be named in `selected.items` too).
_DROP_GUIDE_AND_BUG = """\
# squads:override-base:0.12.3
[selected]
items = [
    "epic", "feature", "task", "decision", "contract", "milestone",
    "review", "role", "skill", "operator",
]
"""


def _write_override(squad_dir: Path, toml: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(toml, encoding="utf-8")


async def test_creating_a_dropped_type_names_it_as_dropped_by_the_override(project, invoke) -> None:
    _write_override(project.squad_dir, _DROP_GUIDE_AND_BUG)

    guide_result = await invoke(["create", "guide", "Ghost", "--author", "manager"])
    assert guide_result.exit_code != 0
    assert "Traceback" not in guide_result.output
    assert "KeyError" not in guide_result.output
    # The one accurate refusal — never Click's "no such command" (which would contradict it by
    # reading the dropped name back as a typo suggestion of itself).
    assert "no such command" not in guide_result.output.lower()
    assert "unknown item type 'guide'" in guide_result.output
    assert "[selected]" in guide_result.output
    assert "selected.items" in guide_result.output

    bug_result = await invoke(["create", "bug", "Ghost bug", "--author", "manager"])
    assert bug_result.exit_code != 0
    assert "Traceback" not in bug_result.output
    assert "KeyError" not in bug_result.output
    assert "no such command" not in bug_result.output.lower()
    assert "unknown item type 'bug'" in bug_result.output
    assert "[selected]" in bug_result.output


async def test_creating_a_dropped_type_by_its_alias_gives_the_same_refusal(project, invoke) -> None:
    """An alias of a dropped type (``b`` for ``bug``) dispatches to the same canonical-type
    membership gate — the refusal names the canonical type, not the alias."""
    _write_override(project.squad_dir, _DROP_GUIDE_AND_BUG)

    result = await invoke(["create", "b", "Ghost via alias", "--author", "manager"])
    assert result.exit_code != 0
    assert "no such command" not in result.output.lower()
    assert "unknown item type 'bug'" in result.output


async def test_service_create_refuses_a_dropped_type_cleanly_even_bypassing_the_cli(
    project,
) -> None:
    """The membership gate lives at the service boundary, not only in the CLI's --help hiding —
    a caller that reaches ``svc.create()`` directly still gets the same clean, provenance-
    bearing ``SquadsError``, never the raw ``KeyError`` the mechanism used to raise."""
    from squads._errors import SquadsError
    from squads._services import _service as service

    _write_override(project.squad_dir, _DROP_GUIDE_AND_BUG)
    svc = service.open_service()
    with pytest.raises(SquadsError, match=r"unknown item type 'guide'.*\[selected\]"):
        await svc.create("guide", "Ghost", author="manager")
    with pytest.raises(SquadsError, match=r"unknown item type 'bug'.*\[selected\]"):
        await svc.create("bug", "Ghost bug", author="manager")


async def test_creating_a_type_that_never_existed_at_all_names_no_false_provenance(
    project,
) -> None:
    """A type that was never bundled and never declared by the override must NOT be told it
    was "dropped from a [selected] list" — that claim is only true for a former built-in.
    Distinct scenario from the dropped-built-in tests above; same membership gate, different
    branch."""
    from squads._errors import SquadsError
    from squads._services import _service as service

    svc = service.open_service()
    with pytest.raises(SquadsError) as exc_info:
        await svc.create("totally-bogus-type", "X", author="manager")
    message = str(exc_info.value)
    assert "unknown item type 'totally-bogus-type'" in message
    assert "[selected]" not in message
    assert "dropped" not in message


async def test_a_dropped_type_is_not_offered_by_create_help_or_the_command_list(
    project, invoke
) -> None:
    _write_override(project.squad_dir, _DROP_GUIDE_AND_BUG)

    help_result = await invoke(["create", "--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "guide" not in help_result.output
    assert "bug" not in help_result.output
    # Surviving built-ins are still offered.
    assert "epic" in help_result.output
    assert "task" in help_result.output


async def test_an_undropped_squad_still_offers_every_built_in_type(project, invoke) -> None:
    """No override present — byte-identical to today: nothing is hidden."""
    help_result = await invoke(["create", "--help"])
    for t in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
        assert t in help_result.output
