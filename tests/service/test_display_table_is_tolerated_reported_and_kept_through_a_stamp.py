"""The ``[display]`` table of ``.squads.toml`` never stops a command: an unusable part falls back to
its default and ``sq check`` names it. A version or schema stamp writes the table back exactly as
it was read, whether it holds a default, an unusable value or an unknown key. One table crosses
the file contents with the exit code, the resolved setting, the check output and the stamped
file."""

from typing import Any

import pytest

from squads import __version__
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
# An unknown top-level key is not part of the table; a stamp does not keep it.
KEPT = [c for c in CONTENTS if c[0] != "injected-problem"]
_KEPT_IDS = [c[0] for c in KEPT]


async def _file_with(svc: Service, tail: str) -> tuple[str, str]:
    """The config text with *tail* appended and the version stale, and the text a stamp must
    produce from it."""
    path = svc.paths.config_path
    current = path.read_text(encoding="utf-8")
    stale = current.replace(f'squads_version = "{__version__}"', 'squads_version = "0.0.1"')
    assert stale != current
    path.write_text(stale + tail, encoding="utf-8")
    return stale + tail, current + tail


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


@pytest.mark.parametrize(("case", "tail", "setting", "reported"), KEPT, ids=_KEPT_IDS)
async def test_a_stamp_writes_the_display_table_back_byte_for_byte(
    svc: Service, invoke: Any, case: str, tail: str, setting: bool, reported: list[str]
) -> None:
    _before, expected = await _file_with(svc, tail)

    result = await invoke(["sync"])

    assert result.exit_code == 0, result.output
    assert svc.paths.config_path.read_text(encoding="utf-8") == expected


@pytest.mark.parametrize(("case", "tail", "setting", "reported"), KEPT, ids=_KEPT_IDS)
async def test_a_second_stamp_changes_nothing(
    svc: Service, invoke: Any, case: str, tail: str, setting: bool, reported: list[str]
) -> None:
    await _file_with(svc, tail)
    await invoke(["sync"])
    once = svc.paths.config_path.read_bytes()

    await invoke(["sync"])

    assert svc.paths.config_path.read_bytes() == once


async def test_there_is_no_config_verb(invoke: Any) -> None:
    result = await invoke(["config", "get", "display"])

    assert result.exit_code != 0
