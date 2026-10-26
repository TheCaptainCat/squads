"""An item file saved with CRLF endings reads exactly as the same file with LF endings, on every
read surface, and its template body can be replaced without --force."""

from typing import Any

import pytest

from _helpers import create_item
from squads._sections import split_lines

pytestmark = pytest.mark.anyio


async def _host(svc: Any, kind: str, host: str) -> tuple[str, Any]:
    item = (await create_item(svc, host, "Host")).item
    await svc.add_block(item.id, kind, "first")
    await svc.comment(item.id, ["a note"], as_slug="manager")
    return item, svc.paths.abspath((await svc.get(item.id)).path)


def _surfaces(item: Any, kind: str) -> list[list[str]]:
    n = item.sequence_id
    t = item.type
    return [
        [t, str(n), "show"],
        [t, str(n), "show", "--full", "--comments"],
        [t, str(n), "show", "--json"],
        [t, str(n), "show", "--full", "--json"],
        [t, str(n), kind, "1", "show"],
        [t, str(n), kind, "1", "show", "--json"],
        [t, str(n), kind, "1", "show", "--full", "--comments"],
        ["list"],
    ]


@pytest.mark.parametrize(
    ("host", "kind"), [("task", "subtask"), ("feature", "story"), ("review", "finding")]
)
async def test_every_read_surface_matches_the_lf_twin(svc, invoke, host: str, kind: str) -> None:
    item, path = await _host(svc, kind, host)
    surfaces = _surfaces(item, kind)
    lf = [(await invoke(args)).stdout for args in surfaces]
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

    crlf = [(await invoke(args)).stdout for args in surfaces]

    assert all("\r" not in out for out in crlf)
    assert crlf == lf


async def test_a_crlf_task_whose_body_is_the_template_takes_a_new_body(svc, invoke) -> None:
    item = (await create_item(svc, "task", "Host")).item
    path = svc.paths.abspath((await svc.get(item.id)).path)
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

    result = await invoke(["task", str(item.sequence_id), "body", "-m", "a real body"])

    assert result.exit_code == 0, result.output
    assert "a real body" in path.read_text()
    assert all(ln.endswith("\r\n") for ln in split_lines(path.read_bytes().decode(), keepends=True))
