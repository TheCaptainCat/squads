"""The ``[display]`` table of ``.squads.toml`` never stops a command: an unusable part falls back to
its default and ``sq check`` names it. ``sq sync`` leaves the file exactly as it was read,
whether the table holds a default, an unusable value or an unknown key. One table crosses the
file contents with the exit code, the resolved setting, the check output and the synced file."""

from typing import Any

import pytest

from squads._paths import load_config
from squads._services._service import Service

pytestmark = pytest.mark.anyio

# (id, text appended to the file, resolved pronouns setting, fragments `sq check` reports)
CONTENTS: list[tuple[str, str, bool, list[str]]] = [
    ("no-table", "", True, []),
    ("explicit-default", "\n[display]\npronouns = true\n", True, []),
    ("off", "\n[display]\npronouns = false\n", False, []),
    ("quoted-false", '\n[display]\npronouns = "false"\n', True, ["pronouns must be true or false"]),
    ("integer", "\n[display]\npronouns = 1\n", True, ["pronouns must be true or false"]),
    ("unknown-key", "\n[display]\npronuns = false\n", True, ["unknown key 'pronuns'"]),
    (
        "unknown-key-beside-off",
        "\n[display]\npronouns = false\nextra = 1\n",
        False,
        ["unknown key 'extra'"],
    ),
    ("not-a-table", "display = 3\n", True, ["[display] must be a table"]),
    ("dotted-key", "display.pronouns = false\n", False, []),
    ("injected-problem", 'display_problems = ["injected"]\n', True, []),
    ("hand-comment-inside", "\n[display]\n# off, on purpose\npronouns = false\n", False, []),
]
_IDS = [c[0] for c in CONTENTS]


async def _file_with(svc: Service, tail: str) -> str:
    """Append *tail* to the config and return the resulting text."""
    path = svc.paths.config_path
    text = path.read_text(encoding="utf-8") + tail
    path.write_text(text, encoding="utf-8")
    return text


@pytest.mark.parametrize(("case", "tail", "setting", "reported"), CONTENTS, ids=_IDS)
async def test_a_display_table_is_read_tolerantly_and_check_names_what_is_unusable(
    svc: Service, invoke: Any, case: str, tail: str, setting: bool, reported: list[str]
) -> None:
    await _file_with(svc, tail)

    config = load_config(svc.paths.config_path)
    listed = await invoke(["list"])
    checked = await invoke(["check"])

    assert config.display.pronouns is setting
    assert listed.exit_code == 0, listed.output
    assert checked.exit_code == 0, checked.output
    warnings = [line for line in checked.output.splitlines() if ".squads.toml" in line]
    assert len(warnings) == len(reported)
    for fragment in reported:
        assert any(fragment in w for w in warnings)
    assert "injected" not in checked.output


@pytest.mark.parametrize(("case", "tail", "setting", "reported"), CONTENTS, ids=_IDS)
async def test_a_sync_leaves_the_display_table_byte_for_byte(
    svc: Service, invoke: Any, case: str, tail: str, setting: bool, reported: list[str]
) -> None:
    expected = await _file_with(svc, tail)

    result = await invoke(["sync"])

    assert result.exit_code == 0, result.output
    assert svc.paths.config_path.read_text(encoding="utf-8") == expected


async def test_there_is_no_config_verb(invoke: Any) -> None:
    result = await invoke(["config", "get", "display"])

    assert result.exit_code != 0
