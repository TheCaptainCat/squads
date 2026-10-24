"""``sq sync`` never writes ``.squads.toml``: whatever the file holds, it is the same bytes
afterwards."""

from typing import Any

import pytest

from squads._services._service import Service

pytestmark = pytest.mark.anyio

# (id, text appended to the generated file)
TAILS = {
    "inert-version-and-comment": 'squads_version = "0.0.1" # stale\n',
    "multi-line-value-with-a-table-like-line": 'note = """\n[x]\nsquads_version = "0.0.1"\n"""\n',
    "retired-keys": 'default_backend = "agents_md"  # legacy\ndefault_role = "manager"\n',
    "no-final-newline": "extra = 1",
}


@pytest.mark.parametrize("tail", TAILS.values(), ids=TAILS.keys())
async def test_a_sync_leaves_the_config_byte_for_byte(svc: Service, invoke: Any, tail: str) -> None:
    path = svc.paths.config_path
    head = path.read_text(encoding="utf-8")
    path.write_text(head + ("\n" if not head.endswith("\n") else "") + tail, encoding="utf-8")
    before = path.read_bytes()

    result = await invoke(["sync"])

    assert result.exit_code == 0, result.output
    assert path.read_bytes() == before
