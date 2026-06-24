"""Migration corpus tests — one frozen squad per released schema version.

Each fixture under ``tests/fixtures/corpus/`` is a minimal but representative squad captured at
the schema version indicated by its directory name.  These tests copy it to a tmp dir, apply
``run_pending_migrations()`` (the same path ``sq migrate up`` uses), and assert:

  - the squad reaches the current schema version (SCHEMA_VERSION),
  - ``await svc.check()`` reports zero error-level issues,
  - a CLI smoke test via ``sq migrate up`` + ``sq check`` both exit 0.

**Standing rule**: every future schema bump must add a new ``vN_M`` corpus fixture here.
See ``tests/fixtures/corpus/README.md`` for the authoring contract.
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

# Root directory for the committed fixture trees.
_CORPUS_DIR = Path(__file__).parent / "fixtures" / "corpus"

# Each entry is a (schema_version_label, corpus_subdir_name) pair.
# Extend this list whenever SCHEMA_VERSION is bumped and _registry.MIGRATIONS grows.
_CORPUS_CASES: list[tuple[str, str]] = [
    ("0.1", "v0_1"),
    ("0.2", "v0_2"),
    ("0.3", "v0_3"),
    ("0.4", "v0_4"),
    ("0.5", "v0_5"),
]


def _load_paths(squad_dir: Path) -> SquadPaths:
    """Load SquadPaths from a corpus fixture directory (squad_dir = '.' in its .squads.toml)."""
    import tomllib

    with (squad_dir / ".squads.toml").open("rb") as fh:
        cfg_data = tomllib.load(fh)
    cfg = SquadsConfig.from_toml_dict(cfg_data)
    resolved = squad_dir / cfg.squad_dir
    return SquadPaths(root=squad_dir, squad_dir=resolved, config=cfg)


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
async def test_corpus_migrates_to_current_and_passes_check(
    schema_label: str, corpus_name: str, tmp_path: Path
) -> None:
    """Copy the frozen corpus to tmp_path, migrate, and check — must reach SCHEMA_VERSION clean."""
    src = _CORPUS_DIR / corpus_name
    assert src.is_dir(), f"corpus fixture {corpus_name!r} not found at {src}"

    dst = tmp_path / corpus_name
    shutil.copytree(src, dst)

    paths = _load_paths(dst)
    svc = Service(paths)

    applied = await svc.run_pending_migrations()

    # After migration the config on disk must reflect the current schema.
    import tomllib

    with (dst / ".squads.toml").open("rb") as fh:
        final_cfg = tomllib.load(fh)
    assert final_cfg["schema_version"] == SCHEMA_VERSION, (
        f"corpus {corpus_name!r} did not reach schema {SCHEMA_VERSION!r} after migration; "
        f"got {final_cfg['schema_version']!r}. Applied: {[m.version for m in applied]}"
    )

    # No error-level check issues.
    issues = await svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors, (
        f"sq check produced errors after migrating {corpus_name!r} from schema {schema_label!r}:\n"
        + "\n".join(f"  [{i.level}] {i.item}: {i.message}" for i in errors)
    )


@pytest.mark.parametrize("schema_label,corpus_name", _CORPUS_CASES)
def test_corpus_cli_smoke(
    schema_label: str, corpus_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI smoke: ``sq migrate up`` + ``sq check`` both exit 0 on each corpus fixture."""
    src = _CORPUS_DIR / corpus_name
    dst = tmp_path / corpus_name
    shutil.copytree(src, dst)

    monkeypatch.chdir(dst)
    runner = CliRunner()

    migrate_result = runner.invoke(app, ["migrate", "up"])
    assert migrate_result.exit_code == 0, (
        f"sq migrate up failed on corpus {corpus_name!r} (schema {schema_label!r}):\n"
        + migrate_result.output
    )

    check_result = runner.invoke(app, ["check"])
    assert check_result.exit_code == 0, (
        f"sq check failed after migrating corpus {corpus_name!r} (schema {schema_label!r}):\n"
        + check_result.output
    )


async def test_v0_2_migration_rewrites_backend_key(tmp_path: Path) -> None:
    """After migrating a v0.2 corpus, .squads.toml must carry ``active_backends`` (not
    ``default_backend``).

    This pins the end-to-end contract: a squad migrated from 0.2 ends with the canonical
    ``active_backends`` shape on disk.  The canonicalization comes from the schema-stamp step
    in ``run_pending_migrations``: after the 0.2→0.3 runner returns, ``_stamp_schema`` re-
    serializes the config via ``SquadsConfig.to_toml()``, which only ever emits
    ``active_backends`` (never ``default_backend``), and ``from_toml_dict()`` already
    translated the legacy key on load.  There is no explicit toml-rewrite step in the runner
    itself — the stamp is the mechanism.  Do not add one looking for it.
    """
    import tomllib

    src = _CORPUS_DIR / "v0_2"
    dst = tmp_path / "v0_2"
    shutil.copytree(src, dst)

    # Precondition: the v0.2 fixture uses the legacy key.
    with (dst / ".squads.toml").open("rb") as fh:
        pre = tomllib.load(fh)
    assert "default_backend" in pre, "v0_2 fixture must carry default_backend (precondition)"
    assert "active_backends" not in pre, (
        "v0_2 fixture must not carry active_backends (precondition)"
    )

    paths = _load_paths(dst)
    svc = Service(paths)
    await svc.run_pending_migrations()

    with (dst / ".squads.toml").open("rb") as fh:
        post = tomllib.load(fh)

    assert "active_backends" in post, (
        "migrated .squads.toml must carry active_backends (canonical 0.3 shape)"
    )
    assert "default_backend" not in post, (
        "migrated .squads.toml must not carry legacy default_backend"
    )
    assert post["active_backends"] == ["claude_code"], (
        "active_backends must preserve the original default_backend value"
    )
