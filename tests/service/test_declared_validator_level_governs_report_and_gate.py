"""A validator's declared level governs both halves of the engine: how loud ``sq check``
reports a finding, and whether it can abort a create/update at the gate. Proven end to end —
a real project opts a member's level up or down through its own ``.overrides/workflow.toml``,
exactly the supported path (mirrors ``test_ref_rule_target_present_validator.py``'s
``_opted_in_service`` fixture shape) — never a hand-built ``ValidatorContext``, so the
gate/report wiring this declaration surface depends on is genuinely exercised.

Two members, one for each direction, both chosen because nothing *outside* the catalog
independently blocks the condition (unlike, say, an unregistered assignee, which
``Service.create`` refuses on its own regardless of any validator): ``parent_in`` (bundled
error, raised nowhere else) proves lowering to warn stops a create/update from aborting;
``dangling_ref`` (bundled warn) proves raising to error makes one that never gated before.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._errors import SquadsError
from squads._services import _service as service

pytestmark = pytest.mark.anyio


def _service_with_override(squad_dir: Path, override_body: str) -> service.Service:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{override_body}", encoding="utf-8"
    )
    return service.open_service()


# --------------------------------------------------------------------------- error -> warn


async def test_the_bundled_default_level_refuses_a_create_with_a_wrong_type_parent(svc):
    """Falsification baseline: ``parent_in``'s bundled default is error, and it gates. A
    dangling (nonexistent) parent id is caught earlier by an unrelated existence pre-check
    (``_check_parent``, a distinct error type/message) — a wrong-*type* parent is the shape
    only the catalog's own ``parent_in`` ever reports."""
    other_task = (await create_item(svc, "task", "u")).item
    with pytest.raises(SquadsError, match="got task"):
        await create_item(svc, "task", "t", parent=other_task.id)


async def test_a_declared_warn_override_lets_the_same_create_through(project):
    """``parent_in`` carries no floor — a project may dial it down to warn — and once it is,
    the identical create the baseline test above proves refused now succeeds."""
    svc = _service_with_override(
        project.squad_dir, '[items.task]\nvalidators = ["parent_in@warn"]\n'
    )
    other_task = (await create_item(svc, "task", "u")).item
    result = await create_item(svc, "task", "t", parent=other_task.id)
    assert result.item.parent == other_task.id

    issues = await svc.check()
    matching = [i for i in issues if i.item == result.item.id and "got task" in i.message]
    assert len(matching) == 1
    assert matching[0].level == "warn"


# --------------------------------------------------------------------------- warn -> error


async def test_the_bundled_default_level_does_not_gate_a_dangling_ref(svc):
    """Falsification baseline: ``dangling_ref``'s bundled default is warn, so it is never a
    create/update blocker — the create below succeeds, and the finding only ever surfaces as
    an advisory in ``check()``."""
    result = await create_item(svc, "task", "t", refs=["FEAT-999999"])
    issues = await svc.check()
    matching = [i for i in issues if i.item == result.item.id and "dangling ref" in i.message]
    assert len(matching) == 1
    assert matching[0].level == "warn"


async def test_a_declared_error_override_gates_the_same_dangling_ref(project):
    """Raised to error, the identical create the baseline test above proves succeeds is now
    refused at the gate — the level is what changed, not the rule."""
    svc = _service_with_override(
        project.squad_dir, '[items.task]\nvalidators = ["dangling_ref@error"]\n'
    )
    with pytest.raises(SquadsError, match="dangling ref"):
        await create_item(svc, "task", "t", refs=["FEAT-999999"])
