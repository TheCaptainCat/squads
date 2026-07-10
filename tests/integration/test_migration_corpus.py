"""Migration corpus: one frozen squad per released schema version, migrated to current and
checked clean via both the service call `sq migrate up` uses and the real CLI.

**Standing rule** (see `tests/fixtures/corpus/README.md`): every future schema bump must add a
new `vN_M` fixture here. This module — not the frozen fixtures themselves — is where that rule
is enforced; never hand-edit anything under `tests/fixtures/corpus/`.
"""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._models._config import SquadsConfig
from squads._models._schema import SCHEMA_VERSION
from squads._paths import SquadPaths
from squads._services._service import Service

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"

_CORPUS_CASES: list[tuple[str, str]] = [
    ("0.1", "v0_1"),
    ("0.2", "v0_2"),
    ("0.3", "v0_3"),
    ("0.4", "v0_4"),
    ("0.5", "v0_5"),
    ("0.7", "v0_7"),
    ("0.8", "v0_8"),
]


def _load_paths(squad_dir: Path) -> SquadPaths:
    import tomllib

    with (squad_dir / ".squads.toml").open("rb") as fh:
        cfg_data = tomllib.load(fh)
    cfg = SquadsConfig.from_toml_dict(cfg_data)
    resolved = squad_dir / cfg.squad_dir
    return SquadPaths(root=squad_dir, squad_dir=resolved, config=cfg)


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
async def test_corpus_migrates_to_current_schema_and_passes_check(
    schema_label: str, corpus_name: str, tmp_path: Path
) -> None:
    src = _CORPUS_DIR / corpus_name
    assert src.is_dir(), f"corpus fixture {corpus_name!r} not found at {src}"
    dst = tmp_path / corpus_name
    shutil.copytree(src, dst)

    paths = _load_paths(dst)
    svc = Service(paths)
    applied = await svc.run_pending_migrations()

    import tomllib

    with (dst / ".squads.toml").open("rb") as fh:
        final_cfg = tomllib.load(fh)
    assert final_cfg["schema_version"] == SCHEMA_VERSION, (
        f"corpus {corpus_name!r} did not reach schema {SCHEMA_VERSION!r}; "
        f"applied: {[m.version for m in applied]}"
    )

    issues = await svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors, (
        f"sq check produced errors after migrating {corpus_name!r} from {schema_label!r}:\n"
        + "\n".join(f"  [{i.level}] {i.item}: {i.message}" for i in errors)
    )


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
def test_corpus_cli_migrate_up_and_check_both_exit_clean(
    schema_label: str, corpus_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = _CORPUS_DIR / corpus_name
    dst = tmp_path / corpus_name
    shutil.copytree(src, dst)
    monkeypatch.chdir(dst)
    runner = CliRunner()

    migrate_result = runner.invoke(app, ["migrate", "up"])
    assert migrate_result.exit_code == 0, (
        f"sq migrate up failed on {corpus_name!r} ({schema_label!r}):\n{migrate_result.output}"
    )

    check_result = runner.invoke(app, ["check"])
    assert check_result.exit_code == 0, (
        f"sq check failed after migrating {corpus_name!r} ({schema_label!r}):\n"
        f"{check_result.output}"
    )


async def test_v0_2_migration_rewrites_the_legacy_backend_key(tmp_path: Path) -> None:
    """A v0.2 squad's `.squads.toml` ends with `active_backends` (the canonical shape), never
    the legacy `default_backend` — via the schema-stamp step, not an explicit toml rewrite."""
    import tomllib

    src = _CORPUS_DIR / "v0_2"
    dst = tmp_path / "v0_2"
    shutil.copytree(src, dst)

    with (dst / ".squads.toml").open("rb") as fh:
        pre = tomllib.load(fh)
    assert "default_backend" in pre and "active_backends" not in pre  # precondition

    paths = _load_paths(dst)
    svc = Service(paths)
    await svc.run_pending_migrations()

    with (dst / ".squads.toml").open("rb") as fh:
        post = tomllib.load(fh)
    assert "active_backends" in post and "default_backend" not in post
    assert post["active_backends"] == ["claude_code"]
