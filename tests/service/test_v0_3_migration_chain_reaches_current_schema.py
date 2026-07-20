"""Facts that historically lived in the session-lineage test file for the migration that
introduced it, but are really about migration correctness (cross-ref
tests/integration/test_migrations.py, which owns the rest of the migration-chain contract):
the 0.3->0.4 (session lineage) migration runner is a genuine no-op, ``SCHEMA_VERSION`` is the
current release schema, and running the pending-migrations chain on a downgraded-to-0.3 squad
walks every intermediate step and stamps the current schema at the end.
"""

import tomllib

import pytest

from squads import _aio
from squads._models._config import SquadsConfig
from squads._models._schema import SCHEMA_VERSION
from squads._paths import SquadPaths
from squads._services._service import Service

pytestmark = pytest.mark.anyio


def test_the_v0_3_to_v0_4_migration_runner_is_a_noop() -> None:
    from squads._migrations._v0_3_to_v0_4 import migrate

    assert migrate(None) == 0  # type: ignore[arg-type]


def test_schema_version_is_the_current_release_schema() -> None:
    assert SCHEMA_VERSION == "0.11"


async def test_running_pending_migrations_from_v0_3_walks_every_step_and_stamps_current(
    project, frozen_time
):
    # Downgrade the on-disk config to 0.3 to simulate a pre-migration squad.
    cfg_path = project.config_path
    cfg_text = await _aio.read_text(cfg_path)
    cfg_text_03 = cfg_text.replace(f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.3"')
    await _aio.write_text(cfg_path, cfg_text_03)

    with cfg_path.open("rb") as fh:
        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    paths_03 = SquadPaths(root=project.root, squad_dir=project.squad_dir, config=cfg)
    svc_03 = Service(paths_03)

    applied = await svc_03.run_pending_migrations()
    assert [a.from_schema for a in applied] == ["0.3", "0.4", "0.5", "0.7", "0.8", "0.10"]
    assert [a.to_schema for a in applied] == ["0.4", "0.5", "0.7", "0.8", "0.10", "0.11"]

    with cfg_path.open("rb") as fh:
        stamped = tomllib.load(fh)
    assert stamped["schema_version"] == SCHEMA_VERSION

    errors = [i for i in await svc_03.check() if i.level == "error"]
    assert not errors
