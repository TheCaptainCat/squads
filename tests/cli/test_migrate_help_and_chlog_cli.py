"""`sq migrate help` (the changelog index) and `sq migrate chlog vA..vB` (manual steps for a
release range) — CLI entry points over the migration registry, distinct from `migrate up`.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_migrate_help_lists_the_changelog_index(project, invoke):
    result = await invoke(["migrate", "help"])
    assert result.exit_code == 0, result.output
    assert "0.2.0" in result.output and "changelog" in result.output


async def test_migrate_chlog_prints_manual_steps_for_a_range_that_includes_them(project, invoke):
    result = await invoke(["migrate", "chlog", "v0.1.1..v0.2.0"])
    assert result.exit_code == 0, result.output
    assert "manual steps" in result.output and "add-finding" in result.output


async def test_migrate_chlog_prints_nothing_for_a_range_with_no_manual_steps(project, invoke):
    result = await invoke(["migrate", "chlog", "v0.2.0..v0.2.0"])
    assert result.exit_code == 0, result.output
    assert "no manual steps" in result.output


async def test_migrate_chlog_rejects_a_malformed_range(project, invoke):
    result = await invoke(["migrate", "chlog", "0.2.0"])
    assert result.exit_code == 1, result.output
    assert "range" in result.output
