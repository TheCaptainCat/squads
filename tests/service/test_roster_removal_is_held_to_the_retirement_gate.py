"""Removing a roster entry is refused wherever archiving it is refused, carries the warnings
archiving gives, and is recorded in the reflog."""

from collections.abc import Awaitable, Callable
from pathlib import Path

import anyio
import pytest

from squads._errors import ConfigIntegrityError
from squads._services import _service as service
from squads._services._service import Service

pytestmark = pytest.mark.anyio

Build = Callable[[Service], Awaitable[str]]


async def _last_live_role(svc: Service) -> str:
    return (await svc.get("ROLE-000001")).id


async def _seeded_skill(svc: Service) -> str:
    return (await svc.roster_item("skill", "squads")).id  # pyright: ignore[reportOptionalMemberAccess]


async def _type_implied_skill(svc: Service) -> str:
    await svc.activate_role("tech-lead")  # its playbook interacts with task
    return (await svc.roster_item("skill", "sq-task")).id  # pyright: ignore[reportOptionalMemberAccess]


async def _default_role_with_a_spare(svc: Service) -> str:
    await svc.activate_role("architect")
    return (await svc.get("ROLE-000001")).id


async def _role_with_open_work(svc: Service) -> str:
    architect = await svc.activate_role("architect")
    await svc.create("task", "t", author="manager", assignee="architect")
    return architect.id


async def _operator_with_open_work(svc: Service) -> str:
    operator = await svc.add_operator("Pierre Chat")
    await svc.create("task", "t", author="manager", assignee=operator.slug)
    return operator.id


async def _custom_skill(svc: Service) -> str:
    return (await svc.add_skill("Pairing")).id


# name -> (builder, whether archiving the entry is refused)
SHAPES: dict[str, tuple[Build, bool]] = {
    "last-live-role": (_last_live_role, True),
    "seeded-skill": (_seeded_skill, True),
    "type-implied-skill": (_type_implied_skill, True),
    "default-role-with-a-spare": (_default_role_with_a_spare, False),
    "role-with-open-work": (_role_with_open_work, False),
    "operator-with-open-work": (_operator_with_open_work, False),
    "custom-skill": (_custom_skill, False),
}


async def _squad(root: Path, monkeypatch: pytest.MonkeyPatch) -> Service:
    await anyio.Path(root).mkdir()
    monkeypatch.chdir(root)
    return Service((await service.init(root=root, roles_spec="minimal")).paths)


def _normalized(warnings: list[str]) -> list[str]:
    """Warnings without the closing hint that only fits one of the two operations."""
    return sorted(w.split(", or reactivate")[0] for w in warnings)


async def _archive(svc: Service, item_id: str) -> tuple[str, list[str]]:
    try:
        result = await svc.set_roster_status(item_id, "Archived")
    except ConfigIntegrityError:
        return "refused", []
    return "allowed", _normalized(result.warnings)


async def _purge(svc: Service, item_id: str) -> tuple[str, list[str]]:
    try:
        result = await svc.remove_item(item_id, purge=True)
    except ConfigIntegrityError:
        return "refused", []
    return "allowed", _normalized(result.warnings)


@pytest.mark.parametrize("name", list(SHAPES))
async def test_a_purge_is_refused_and_warned_as_an_archive_is(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build, archive_refused = SHAPES[name]
    archived = await _archive(*await _built(build, tmp_path / "archive", monkeypatch))
    purged = await _purge(*await _built(build, tmp_path / "purge", monkeypatch))

    assert archived[0] == ("refused" if archive_refused else "allowed")
    assert purged == archived


async def _built(build: Build, root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Service, str]:
    svc = await _squad(root, monkeypatch)
    return svc, await build(svc)


@pytest.mark.parametrize("name", [n for n, (_, refused) in SHAPES.items() if refused])
async def test_a_refused_removal_changes_nothing_and_logs_nothing(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc, item_id = await _built(SHAPES[name][0], tmp_path / "squad", monkeypatch)
    before = {
        p.relative_to(svc.paths.squad_dir): p.read_bytes()
        for p in sorted(svc.paths.squad_dir.rglob("*"))
        if p.is_file()
    }

    for purge in (True, False):
        with pytest.raises(ConfigIntegrityError, match=f"cannot remove {item_id}"):
            await svc.remove_item(item_id, purge=purge)

    after = {
        p.relative_to(svc.paths.squad_dir): p.read_bytes()
        for p in sorted(svc.paths.squad_dir.rglob("*"))
        if p.is_file()
    }
    assert after == before
    assert await svc.read_reflog(op_filter="remove") == []


@pytest.mark.parametrize("name", [n for n, (_, refused) in SHAPES.items() if not refused])
async def test_an_allowed_removal_appends_one_reflog_entry(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc, item_id = await _built(SHAPES[name][0], tmp_path / "squad", monkeypatch)

    await svc.remove_item(item_id, purge=True)

    entries = await svc.read_reflog(op_filter="remove")
    assert [e.target for e in entries] == [item_id]


async def test_an_archived_entry_is_removed_without_the_gate_or_warnings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc, item_id = await _built(_role_with_open_work, tmp_path / "squad", monkeypatch)
    await svc.set_roster_status(item_id, "Archived")

    result = await svc.remove_item(item_id, purge=True)

    assert result.warnings == []
    assert [e.target for e in await svc.read_reflog(op_filter="remove")] == [item_id]
