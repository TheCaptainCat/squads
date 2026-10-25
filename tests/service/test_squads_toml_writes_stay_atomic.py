"""`.squads.toml` is squad data, not a regenerable artifact, so a truncated config makes the
squad unresolvable. `init`'s config write and the one `sq migrate up` makes must leave it
complete-or-previous under an interrupted write, never a truncated prefix.
"""

import pathlib

import pytest

from _helpers import make_service
from squads._paths import load_config, resolve
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
    assert load_config(config_path) == result.paths.config


async def test_an_interrupted_migrate_config_write_leaves_the_previous_config_intact(svc):
    config_path = svc.paths.config_path
    current = svc.paths.config.schema_version
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            f'schema_version = "{current}"', 'schema_version = "0.14"'
        ),
        encoding="utf-8",
    )
    previous_bytes = config_path.read_bytes()
    real_replace = pathlib.Path.replace

    def _fail_for_the_config(self, target):
        if pathlib.Path(target) == config_path:
            raise OSError("simulated crash after the temp write, before the replace")
        return real_replace(self, target)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pathlib.Path, "replace", _fail_for_the_config)
        with pytest.raises(OSError, match="simulated crash"):
            await make_service(resolve(client_cwd=svc.paths.root)).run_pending_migrations()

    assert config_path.read_bytes() == previous_bytes
    assert load_config(config_path).schema_version == "0.14"
