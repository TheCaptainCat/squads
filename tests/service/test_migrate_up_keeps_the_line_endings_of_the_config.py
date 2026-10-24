"""``sq migrate up`` changes the schema value of a CRLF ``.squads.toml`` and nothing else, line
endings included."""

from typing import Any

import pytest

pytestmark = pytest.mark.anyio


async def test_a_crlf_config_keeps_its_line_endings(svc: Any, invoke: Any) -> None:
    path = svc.paths.config_path
    current = svc.paths.config.schema_version
    text = path.read_text(encoding="utf-8").replace(
        f'schema_version = "{current}"', 'schema_version = "0.14"'
    )
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    expected = text.replace("0.14", current).replace("\n", "\r\n")
    assert path.read_bytes() == expected.encode("utf-8")
