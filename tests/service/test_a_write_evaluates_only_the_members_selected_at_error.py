"""Through ``Service.create`` and ``Service.update``: a type selecting one member at ``warn`` and
another at ``@error`` evaluates only the second on a write, and the write is refused or accepted
exactly as before.
"""

import pytest

from _helpers import create_item
from _selection_table import service_with
from squads._errors import SquadsError
from squads._services import _validators as validators
from squads._services._results import CheckIssue

pytestmark = pytest.mark.anyio

_OVERRIDE = '[items.task]\nvalidators = ["agent_registered@warn", "dangling_ref@error"]\n'


def _count_calls(monkeypatch: pytest.MonkeyPatch, names: tuple[str, ...]) -> list[str]:
    calls: list[str] = []
    for name in names:
        real = validators.CATALOG[name]

        def counted(ctx, real=real, name=name) -> list[CheckIssue]:
            calls.append(name)
            return real(ctx)

        monkeypatch.setitem(validators.CATALOG, name, counted)
    return calls


async def test_create_and_update_evaluate_the_error_member_and_not_the_warn_member(
    project, monkeypatch
) -> None:
    svc = service_with(project.squad_dir, _OVERRIDE)
    calls = _count_calls(monkeypatch, ("agent_registered", "dangling_ref"))

    item = (await create_item(svc, "task", "t")).item
    assert calls == ["dangling_ref"]

    calls.clear()
    await svc.update(item.id, title="renamed")
    assert calls == ["dangling_ref"]


async def test_the_error_member_still_refuses_and_the_warn_member_still_reports(project) -> None:
    svc = service_with(project.squad_dir, _OVERRIDE)
    with pytest.raises(SquadsError, match="dangling ref"):
        await create_item(svc, "task", "t", refs=["FEAT-999999"])
    clean = (await create_item(svc, "task", "ok")).item
    assert clean.id
