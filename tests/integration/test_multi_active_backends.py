"""Multi-active-backend runtime: sync writes every active backend's files, an empty
active_backends list verifies nothing (sq-only squad), a deactivated backend's lingering
files are ignored not flagged, and the ``--backend none`` sentinel wires through the CLI.

Config-model-only facts (dedup, legacy single-key read) live in
tests/unit/test_active_backends_config.py.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
def tmp_squad(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestBothBackendsWritten:
    async def test_init_scaffolds_both_managed_files(self, tmp_squad: Path) -> None:
        await service.init(
            root=tmp_squad, backend=["claude_code", "agents_md"], roles_spec="minimal"
        )
        assert (tmp_squad / "CLAUDE.md").exists()
        assert (tmp_squad / "AGENTS.md").exists()

    async def test_sync_refreshes_both(self, tmp_squad: Path) -> None:
        result = await service.init(
            root=tmp_squad, backend=["claude_code", "agents_md"], roles_spec="minimal"
        )
        await service.Service(result.paths).sync()
        assert (tmp_squad / "CLAUDE.md").exists()
        assert (tmp_squad / "AGENTS.md").exists()

    async def test_config_toml_stores_the_backend_list(self, tmp_squad: Path) -> None:
        import tomllib

        await service.init(
            root=tmp_squad, backend=["claude_code", "agents_md"], roles_spec="minimal"
        )
        with (tmp_squad / ".squads.toml").open("rb") as fh:
            cfg = tomllib.load(fh)
        assert cfg.get("active_backends") == ["claude_code", "agents_md"]
        assert "default_backend" not in cfg


class TestEmptyActiveBackends:
    async def test_no_managed_files_are_created(self, tmp_squad: Path) -> None:
        await service.init(root=tmp_squad, backend=[], roles_spec="minimal")
        assert not (tmp_squad / "CLAUDE.md").exists()
        assert not (tmp_squad / "AGENTS.md").exists()

    async def test_check_reports_no_backend_errors(self, tmp_squad: Path) -> None:
        result = await service.init(root=tmp_squad, backend=[], roles_spec="minimal")
        svc = service.Service(result.paths)
        issues = await svc.check()
        backend_issues = [i for i in issues if "managed file missing" in i.message]
        assert not backend_issues

    async def test_a_deactivated_backends_lingering_files_are_not_flagged(
        self, tmp_squad: Path
    ) -> None:
        await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
        assert (tmp_squad / "CLAUDE.md").exists()

        import tomllib

        from squads._paths import resolve

        cfg_path = tmp_squad / ".squads.toml"
        with cfg_path.open("rb") as fh:
            cfg_data = tomllib.load(fh)
        lines = [
            "# squads project configuration",
            f'schema_version = "{cfg_data["schema_version"]}"',
            f'squad_dir = "{cfg_data["squad_dir"]}"',
            "active_backends = []",
            f'default_role = "{cfg_data["default_role"]}"',
            f'squads_version = "{cfg_data["squads_version"]}"',
            "",
        ]
        cfg_path.write_text("\n".join(lines), encoding="utf-8")

        assert (tmp_squad / "CLAUDE.md").exists()  # deactivation ignores, never deletes
        svc = service.Service(resolve())
        issues = await svc.check()
        backend_issues = [i for i in issues if "managed file missing" in i.message]
        assert not backend_issues


class TestDedupSingleRunOnly:
    async def test_a_duplicated_backend_name_scaffolds_only_once(self, tmp_squad: Path) -> None:
        result = await service.init(
            root=tmp_squad, backend=["claude_code", "claude_code"], roles_spec="minimal"
        )
        assert result.paths.config.active_backends == ["claude_code"]


class TestNoneSentinel:
    def test_backend_none_writes_an_empty_active_backends_list(
        self, tmp_squad: Path, runner: CliRunner
    ) -> None:
        import tomllib

        r = runner.invoke(
            app,
            ["init", "--no-seed-skills", "--backend", "none", "--no-claude", "--roles", "minimal"],
        )
        assert r.exit_code == 0, r.output
        with (tmp_squad / ".squads.toml").open("rb") as fh:
            cfg = tomllib.load(fh)
        assert cfg.get("active_backends") == []

    def test_backend_none_is_case_insensitive(self, tmp_squad: Path, runner: CliRunner) -> None:
        import tomllib

        r = runner.invoke(
            app,
            ["init", "--no-seed-skills", "--backend", "NONE", "--no-claude", "--roles", "minimal"],
        )
        assert r.exit_code == 0, r.output
        with (tmp_squad / ".squads.toml").open("rb") as fh:
            cfg = tomllib.load(fh)
        assert cfg.get("active_backends") == []

    def test_backend_none_combined_with_a_real_backend_is_rejected(
        self, tmp_squad: Path, runner: CliRunner
    ) -> None:
        r = runner.invoke(
            app,
            [
                "init",
                "--no-seed-skills",
                "--backend",
                "none",
                "--backend",
                "claude_code",
                "--roles",
                "minimal",
            ],
        )
        assert r.exit_code == 1, r.output
        assert "none" in r.output.lower() or "cannot be combined" in r.output.lower()


class TestCliMultiBackendOutput:
    def test_two_backend_flags_both_named_in_the_init_summary(
        self, tmp_squad: Path, runner: CliRunner
    ) -> None:
        r = runner.invoke(
            app,
            [
                "init",
                "--no-seed-skills",
                "--backend",
                "claude_code",
                "--backend",
                "agents_md",
                "--roles",
                "minimal",
            ],
        )
        assert r.exit_code == 0, r.output
        assert "agent backends" in r.output.lower()
        assert "claude_code" in r.output
        assert "agents_md" in r.output
