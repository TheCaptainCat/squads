"""The writers that repair or re-stamp a squad-managed file keep its line endings, as every other
write does: lines they leave alone keep their bytes, and nothing they add is out of step."""

from pathlib import Path
from typing import Any

import pytest

from _helpers import create_item, make_service
from squads import _aio
from squads._models import _markers as markers
from squads._sections import split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio


def _all_crlf(data: bytes) -> bool:
    return b"\n" in data and data.count(b"\n") == data.count(b"\r\n")


@pytest.fixture
async def svc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return make_service(result.paths)


def _skill_file(svc: Any, slug: str) -> Path:
    (found,) = (svc.paths.squad_dir / "agents" / "skills").glob(f"SKILL-*-{slug}.md")
    return found


def _to_crlf(path: Path) -> None:
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))


async def test_a_sync_restamp_of_a_crlf_skill_file_keeps_it_crlf(svc) -> None:
    md = _skill_file(svc, "sq-task")
    fm, body = split_frontmatter(await _aio.read_text(md))
    fm.pop("id")
    md.write_text("---\n" + "".join(f"{k}: {v!r}\n" for k, v in fm.items()) + "---" + body)
    _to_crlf(md)

    await svc.sync()

    data = md.read_bytes()
    assert _all_crlf(data)
    assert split_frontmatter(data.decode())[0]["id"].startswith("SKILL-")


async def test_a_refresh_that_gives_a_crlf_skill_its_body_region_back_keeps_it_crlf(svc) -> None:
    md = _skill_file(svc, "squads")
    gone = {markers.open_marker(markers.BODY), markers.close_marker(markers.BODY)}
    kept = [ln for ln in md.read_text().splitlines(keepends=True) if ln.strip() not in gone]
    md.write_text("".join(kept))
    _to_crlf(md)

    await svc.refresh_managed()

    data = md.read_bytes()
    assert markers.open_marker(markers.BODY).encode() in data
    assert _all_crlf(data)


async def test_a_role_update_keeps_a_crlf_role_file_crlf(svc) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    md = svc.paths.abspath(role.path)
    _to_crlf(md)
    before = md.read_bytes()

    await svc.update_role(role.id, model="sonnet")

    after = md.read_bytes()
    assert after != before and _all_crlf(after)
    assert split_frontmatter(after.decode())[0].get("model") == "sonnet"


async def test_a_retype_rewrites_the_mentions_in_a_crlf_file_without_changing_its_endings(
    svc,
) -> None:
    target = (await create_item(svc, "task", "Target")).item
    other = (await create_item(svc, "task", "Other")).item
    await svc.set_body(other.id, f"waiting on {target.id}", force=True)
    md = svc.paths.abspath((await svc.get(other.id)).path)
    _to_crlf(md)

    retyped = (await svc.retype(target.id, "bug")).item

    data = md.read_bytes()
    assert retyped.id.encode() in data and target.id.encode() not in data
    assert _all_crlf(data)


async def test_a_container_heading_inside_the_body_is_not_taken_for_the_containers_own(svc) -> None:
    item = (await create_item(svc, "task", "Host")).item
    await svc.add_subtask(item.id, "first")
    await svc.set_body(item.id, "## Subtasks\n\nmy own plan for them", force=True)
    md = svc.paths.abspath((await svc.get(item.id)).path)
    gone = {markers.open_marker("subtasks"), markers.close_marker("subtasks")}
    text = md.read_text()
    kept = [ln for ln in text.splitlines(keepends=True) if ln.strip() not in gone]
    del kept[len(kept) - 1 - kept[::-1].index("## Subtasks\n")]
    md.write_text("".join(kept))
    assert md.read_text().count("## Subtasks\n") == 1  # only the body's own is left

    await svc.add_subtask(item.id, "second")

    after = md.read_text()
    assert after.count("## Subtasks\n") == 2
    assert after.index("## Subtasks\n") < after.index(markers.close_marker(markers.BODY))
    assert after.rindex("## Subtasks\n") > after.index(markers.close_marker(markers.BODY))
