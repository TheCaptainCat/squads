"""`.squads.toml` is squad data, not a regenerable artifact: `sq sync` only re-stamps its
version field, so a truncated config makes the squad unresolvable rather than costing a
re-sync. Every writer -- `init`/`adopt`'s config write and `_stamp_version`/`_stamp_schema` --
must leave it complete-or-previous under an interrupted write, never a truncated prefix.
"""

import pathlib

import pytest

from squads._paths import load_config
from squads._services import _service as service

pytestmark = pytest.mark.anyio


def _fail_before_replace(mp: pytest.MonkeyPatch) -> None:
    """Lets the temp write complete, then blows up right before `Path.replace` runs -- the
    exact window `atomic_write_text` exists to make harmless.

    Scoped to its own `MonkeyPatch` instance (never the test's shared `monkeypatch` fixture,
    which also owns the `project` fixture's `chdir` -- calling `.undo()` on that shared
    instance mid-test would roll the cwd back too), so it can be undone right after use
    without disturbing anything else.
    """

    def _raise(self, target):
        raise OSError("simulated crash after the temp write, before the replace")

    mp.setattr(pathlib.Path, "replace", _raise)


async def test_an_interrupted_stamp_leaves_the_previous_config_intact_and_still_loadable(svc):
    config_path = svc.paths.config_path
    previous_bytes = config_path.read_bytes()

    with pytest.MonkeyPatch.context() as mp:
        _fail_before_replace(mp)
        with pytest.raises(OSError, match="simulated crash"):
            await svc.sync()  # sync's last step is _stamp_version

    assert config_path.read_bytes() == previous_bytes
    # Still a complete, parseable config -- the squad stays resolvable.
    reloaded = load_config(config_path)
    assert reloaded.squads_version == svc.paths.config.squads_version


async def test_an_interrupted_schema_stamp_leaves_the_previous_config_intact(svc):
    config_path = svc.paths.config_path
    previous_bytes = config_path.read_bytes()

    with pytest.MonkeyPatch.context() as mp:
        _fail_before_replace(mp)
        with pytest.raises(OSError, match="simulated crash"):
            await svc._stamp_schema("9.9")  # pyright: ignore[reportPrivateUsage]

    assert config_path.read_bytes() == previous_bytes
    load_config(config_path)  # still parses


async def test_an_interrupted_init_config_write_never_leaves_a_truncated_squads_toml(tmp_path):
    config_path = tmp_path / ".squads.toml"

    with pytest.MonkeyPatch.context() as mp:
        _fail_before_replace(mp)
        with pytest.raises(OSError, match="simulated crash"):
            await service.init(root=tmp_path, _skip_skill_seed=True)

    # The create direction: target never existed, so an interrupted write must leave NO file
    # at all -- never a half-written one `load_config` would choke on.
    assert not config_path.exists()

    # A normal (uninterrupted) init afterwards succeeds -- nothing was left in a bad state.
    result = await service.init(root=tmp_path, _skip_skill_seed=True)
    assert config_path.exists()
    assert load_config(config_path).squads_version == result.paths.config.squads_version
