"""A single-line ``error:`` refusal keeps a remedy command as one literal token, on any console.

Rich does not render at ``COLUMNS``; ``Console.__init__`` latches ``COLUMNS - legacy_windows``
as the console's width.  ``legacy_windows`` is true whenever Rich cannot get console features
out of the handle it is writing to -- which is exactly what happens on Windows when stdout is a
captured pipe, as it is under ``CliRunner`` and in CI.  That used to mean the suite's
``COLUMNS=80`` pin silently meant 79 on such a console, an error message long enough to reflow
wrapped one word earlier, and the ``sq ...`` command the message tells the operator to run
straddled the inserted newline -- so the literal the test looked for was nowhere in the output,
on that one platform, with nothing about the platform in the assertion.

The single-line ``error:`` refusal sites (the ``handle_errors``/``command`` decorators and the
dynamically registered refusal shims) now print with ``soft_wrap=True``, which makes them
immune to the console's latched width altogether -- ``legacy_windows`` included.  The second
test below holds that: even a console built the way a legacy Windows terminal builds one still
keeps the remedy on one line.  The root conftest's ``detect_legacy_windows`` pin remains
load-bearing elsewhere -- for stdout tables/panels and the *multi-line* advisory ``err_console``
prints (schema-mismatch, version-notice, per-file degradation loops) that still wrap on purpose.
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


async def test_a_legacy_console_no_longer_breaks_it_thanks_to_soft_wrap(
    project, invoke, monkeypatch
) -> None:
    """Emulate the platform difference rather than needing the platform: a console built the
    way a legacy Windows console builds one loses a column off its latched width, which used to
    wrap the refusal a word earlier and split the remedy in two (see the module docstring).  The
    ``soft_wrap=True`` on this print site now makes that irrelevant here.

    The flag has to be passed to the constructor, not set on a live console: the subtraction
    happens once in ``Console.__init__`` and is latched into the width, so flipping the attribute
    afterwards would change nothing and make this exercise silently vacuous.
    """
    monkeypatch.setattr(common, "console", Console(legacy_windows=True))
    monkeypatch.setattr(common, "err_console", Console(stderr=True, legacy_windows=True))

    assert _REMEDY in await _refusal(invoke)
