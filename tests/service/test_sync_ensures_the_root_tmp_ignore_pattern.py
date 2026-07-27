"""`sync` is the idempotent "bring this squad up to date" path, so a squad initialised before
the root ``.gitignore`` pattern existed still picks it up on its next sync rather than carrying
the hole -- an interrupted ``.squads.toml`` write's temp sibling lands at the *project root*,
outside the squad dir's own ``.gitignore``, and would otherwise stay untracked and unignored
forever.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_sync_adds_the_pattern_to_a_root_gitignore_that_predates_it(svc):
    gitignore = svc.paths.root / ".gitignore"
    gitignore.write_text("node_modules/\n*.log\n", encoding="utf-8")

    await svc.sync()

    text = gitignore.read_text(encoding="utf-8")
    assert ".squads.toml.*.tmp" in text.splitlines()
    # The adopter's own pre-existing content survives untouched.
    assert "node_modules/" in text
    assert "*.log" in text


async def test_sync_creates_a_root_gitignore_when_none_exists(svc):
    gitignore = svc.paths.root / ".gitignore"
    gitignore.unlink(missing_ok=True)

    await svc.sync()

    assert ".squads.toml.*.tmp" in gitignore.read_text(encoding="utf-8").splitlines()


async def test_sync_is_a_no_op_once_the_pattern_is_already_present(svc):
    gitignore = svc.paths.root / ".gitignore"
    await svc.sync()
    once = gitignore.read_text(encoding="utf-8")

    await svc.sync()
    twice = gitignore.read_text(encoding="utf-8")

    assert once == twice
