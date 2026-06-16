"""Tests for FEAT-000138 / TASK-000140: multi-active backend runtime and sq check rule.

Covers:
- US1: multi-active sync writes both backends' files (CLAUDE.md + AGENTS.md).
- US2: empty active_backends=[] verifies nothing (sq-only squad); deactivated backend
  files are ignored not flagged.
- Dedup semantics: repeated backend names collapse to one.
- --backend none sentinel (sq-only squad).
- managed_paths probe.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._models._config import SquadsConfig
from squads._services import _service as service

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_squad(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A temp dir to run sq commands in."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# US1: Multi-active sync: CLAUDE.md + AGENTS.md both written
# ---------------------------------------------------------------------------


class TestMultiActiveSync:
    def test_both_backends_scaffolded_on_init(self, tmp_squad: Path) -> None:
        """sq init with two backends creates both CLAUDE.md and AGENTS.md."""
        service.init(
            root=tmp_squad,
            backend=["claude_code", "agents_md"],
            roles_spec="minimal",
        )
        assert (tmp_squad / "CLAUDE.md").exists(), "CLAUDE.md must exist for claude_code backend"
        assert (tmp_squad / "AGENTS.md").exists(), "AGENTS.md must exist for agents_md backend"

    def test_both_backends_synced(self, tmp_squad: Path) -> None:
        """sq sync with two active backends refreshes both files."""
        result = service.init(
            root=tmp_squad,
            backend=["claude_code", "agents_md"],
            roles_spec="minimal",
        )
        svc = service.Service(result.paths)
        svc.sync()
        assert (tmp_squad / "CLAUDE.md").exists()
        assert (tmp_squad / "AGENTS.md").exists()

    def test_config_stores_active_backends_list(self, tmp_squad: Path) -> None:
        """sq init writes active_backends as a TOML array."""
        import tomllib

        service.init(
            root=tmp_squad,
            backend=["claude_code", "agents_md"],
            roles_spec="minimal",
        )
        with (tmp_squad / ".squads.toml").open("rb") as fh:
            cfg = tomllib.load(fh)
        assert cfg.get("active_backends") == ["claude_code", "agents_md"]
        assert "default_backend" not in cfg


# ---------------------------------------------------------------------------
# US2: Empty active_backends=[] — sq-only squad, check verifies nothing
# ---------------------------------------------------------------------------


class TestEmptyActiveBackends:
    def test_empty_backends_no_scaffold(self, tmp_squad: Path) -> None:
        """active_backends=[] means no backend files are created."""
        service.init(
            root=tmp_squad,
            backend=[],
            roles_spec="minimal",
        )
        assert not (tmp_squad / "CLAUDE.md").exists(), "sq-only squad must not create CLAUDE.md"
        assert not (tmp_squad / "AGENTS.md").exists(), "sq-only squad must not create AGENTS.md"

    def test_empty_backends_check_clean(self, tmp_squad: Path) -> None:
        """sq check reports no backend errors for an empty active_backends squad."""
        result = service.init(
            root=tmp_squad,
            backend=[],
            roles_spec="minimal",
        )
        svc = service.Service(result.paths)
        issues = svc.check()
        backend_issues = [i for i in issues if "managed file missing" in i.message]
        assert not backend_issues, (
            "sq-only squad (active_backends=[]) must not have backend check errors: "
            f"{backend_issues}"
        )

    def test_deactivated_backend_files_not_flagged(self, tmp_squad: Path) -> None:
        """Lingering files from a deactivated backend are not flagged by sq check."""
        # Init with claude_code backend — creates CLAUDE.md.
        service.init(
            root=tmp_squad,
            backend=["claude_code"],
            roles_spec="minimal",
        )
        assert (tmp_squad / "CLAUDE.md").exists()

        # Now manually switch to sq-only (deactivate claude_code).
        import tomllib

        cfg_path = tmp_squad / ".squads.toml"
        with cfg_path.open("rb") as fh:
            cfg_data = tomllib.load(fh)
        cfg_data["active_backends"] = []
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

        # CLAUDE.md still exists (deactivation = ignore, not delete).
        assert (tmp_squad / "CLAUDE.md").exists()

        # sq check must not flag CLAUDE.md (deactivated backend is not probed).
        from squads._paths import resolve

        svc = service.Service(resolve())
        issues = svc.check()
        backend_issues = [i for i in issues if "managed file missing" in i.message]
        assert not backend_issues, (
            f"Deactivated backend's lingering files must not be flagged: {backend_issues}"
        )


# ---------------------------------------------------------------------------
# Back-compat: legacy default_backend → active_backends on read (ADR-141 §5)
# ---------------------------------------------------------------------------


class TestLegacyDefaultBackendRead:
    def test_legacy_default_backend_loads_as_active_backends(self) -> None:
        """A hand-written .squads.toml with legacy ``default_backend = "claude_code"`` (schema 0.3)
        must load as ``active_backends = ["claude_code"]``.

        This test is intentionally non-vacuous: it reads the config through
        ``SquadsConfig.from_toml_dict`` (the same path the CLI uses) and verifies the
        translation.  Removing the back-compat branch in ``from_toml_dict`` would cause this
        to fail with ``active_backends == ["claude_code"]`` coming from the model default —
        *but only if the test also asserts that ``default_backend`` is absent from the raw
        dict*, which we do in the precondition check below, and that the value maps correctly
        even for a non-default backend name.
        """
        # Simulate a legacy 0.3 TOML that was never migrated — only default_backend, no
        # active_backends.
        raw: dict[str, object] = {
            "schema_version": "0.3",
            "squad_dir": "squads",
            "default_backend": "agents_md",  # non-default name, so the fallback can't fake it
            "default_role": "manager",
            "squads_version": "0.3.0",
        }
        # Precondition: the raw dict has no active_backends key.
        assert "active_backends" not in raw, (
            "test setup error: raw dict must not have active_backends"
        )

        cfg = SquadsConfig.from_toml_dict(raw)  # type: ignore[arg-type]

        assert cfg.active_backends == ["agents_md"], (
            "legacy default_backend must be translated to active_backends on read"
        )

    def test_legacy_default_backend_absent_falls_back_to_claude_code(self) -> None:
        """A toml with neither key defaults to ``active_backends = ["claude_code"]`` — never
        silently sq-only."""
        raw: dict[str, object] = {
            "schema_version": "0.3",
            "squad_dir": "squads",
            "default_role": "manager",
            "squads_version": "0.3.0",
        }
        cfg = SquadsConfig.from_toml_dict(raw)  # type: ignore[arg-type]
        assert cfg.active_backends == ["claude_code"], (
            "missing backend key must default to claude_code, not sq-only"
        )


# ---------------------------------------------------------------------------
# Dedup semantics (ADR-141 §2)
# ---------------------------------------------------------------------------


class TestDedup:
    def test_dedup_on_read(self) -> None:
        """Duplicate entries in active_backends are silently collapsed."""
        cfg = SquadsConfig(active_backends=["claude_code", "claude_code", "agents_md"])
        assert cfg.active_backends == ["claude_code", "agents_md"]

    def test_dedup_preserves_first_occurrence_order(self) -> None:
        """Dedup preserves first-occurrence order, not insertion order of duplicates."""
        cfg = SquadsConfig(active_backends=["agents_md", "claude_code", "agents_md"])
        assert cfg.active_backends == ["agents_md", "claude_code"]

    def test_dedup_single_run_only_once(self, tmp_squad: Path) -> None:
        """A duplicated backend name must only scaffold/sync once (write once)."""
        result = service.init(
            root=tmp_squad,
            backend=["claude_code", "claude_code"],
            roles_spec="minimal",
        )
        # The config must have the deduplicated list — only one "claude_code".
        assert result.paths.config.active_backends == ["claude_code"]


# ---------------------------------------------------------------------------
# --backend none sentinel (ADR-141 §3)
# ---------------------------------------------------------------------------


class TestNoneSentinel:
    def test_none_sentinel_creates_empty_backends(self, tmp_squad: Path, runner: CliRunner) -> None:
        """sq init --backend none writes active_backends=[] to config."""
        import tomllib

        r = runner.invoke(app, ["init", "--backend", "none", "--no-claude", "--roles", "minimal"])
        assert r.exit_code == 0, r.output
        with (tmp_squad / ".squads.toml").open("rb") as fh:
            cfg = tomllib.load(fh)
        assert cfg.get("active_backends") == []

    def test_none_sentinel_case_insensitive(self, tmp_squad: Path, runner: CliRunner) -> None:
        """--backend NONE (upper-case) is treated as the none sentinel."""
        import tomllib

        r = runner.invoke(app, ["init", "--backend", "NONE", "--no-claude", "--roles", "minimal"])
        assert r.exit_code == 0, r.output
        with (tmp_squad / ".squads.toml").open("rb") as fh:
            cfg = tomllib.load(fh)
        assert cfg.get("active_backends") == []

    def test_none_combined_with_real_backend_raises(
        self, tmp_squad: Path, runner: CliRunner
    ) -> None:
        """--backend none combined with a real backend name is an error."""
        r = runner.invoke(
            app,
            ["init", "--backend", "none", "--backend", "claude_code", "--roles", "minimal"],
        )
        assert r.exit_code == 1, r.output
        assert "none" in r.output.lower() or "cannot be combined" in r.output.lower()


# ---------------------------------------------------------------------------
# CLI --backend multiple
# ---------------------------------------------------------------------------


class TestCliMultiBackend:
    def test_init_with_two_backends_output(self, tmp_squad: Path, runner: CliRunner) -> None:
        """sq init --backend X --backend Y prints both in the 'agent backends' line."""
        r = runner.invoke(
            app,
            ["init", "--backend", "claude_code", "--backend", "agents_md", "--roles", "minimal"],
        )
        assert r.exit_code == 0, r.output
        assert "agent backends" in r.output.lower()
        assert "claude_code" in r.output
        assert "agents_md" in r.output
