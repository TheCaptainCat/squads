"""Error text renders at the width the suite pins, so a remedy command stays one literal token.

Rich does not render at ``COLUMNS``; ``Console.__init__`` latches ``COLUMNS - legacy_windows``
as the console's width.  ``legacy_windows`` is true whenever Rich cannot get console features
out of the handle it is writing to -- which is exactly what happens on Windows when stdout is a
captured pipe, as it is under ``CliRunner`` and in CI.  So the suite's ``COLUMNS=80`` pin
silently meant 79 there, an error message long enough to reflow wrapped one word earlier, and
the ``sq ...`` command the message tells the operator to run straddled the inserted newline --
so the literal the test looked for was nowhere in the output, on that one platform, with
nothing about the platform in the assertion.  The root conftest pins Rich's legacy-console
detection off; these tests hold the pin and prove it is load-bearing on every platform, not
only the one that exposed it.
"""

import pytest
from rich.console import Console

from squads._cli import _common as common

pytestmark = pytest.mark.anyio

#: The refusal that exposed this: long enough to reflow, and the tail Rich moves to the next
#: line is the remedy command a caller greps for and an operator copies.
_REMEDY = "sq role tech-writer status Active"


async def _refusal(invoke) -> str:
    await invoke(["role", "activate", "tech-writer"])
    await invoke(["role", "tech-writer", "status", "Archived"])
    result = await invoke(["role", "activate", "tech-writer"])
    assert result.exit_code == 1, result.output
    return result.output


async def test_a_remedy_command_survives_as_one_unbroken_token(project, invoke) -> None:
    assert _REMEDY in await _refusal(invoke)


async def test_a_legacy_console_really_would_break_it_proving_the_pin_is_load_bearing(
    project, invoke, monkeypatch
) -> None:
    """Falsify the pin by emulating the platform difference rather than needing the platform:
    consoles built the way a legacy Windows console builds them lose a column, the refusal wraps
    a word earlier, and the remedy command the test above relies on is split in two.

    The flag has to be passed to the constructor, not set on a live console: the subtraction
    happens once in ``Console.__init__`` and is latched into the width, so flipping the attribute
    afterwards changes nothing and would make this falsification silently vacuous.
    """
    monkeypatch.setattr(common, "console", Console(legacy_windows=True))
    monkeypatch.setattr(common, "err_console", Console(stderr=True, legacy_windows=True))

    output = await _refusal(invoke)

    assert _REMEDY not in output
    assert "sq role tech-writer status \nActive" in output
