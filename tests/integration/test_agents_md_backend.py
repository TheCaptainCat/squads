"""agents_md backend-specific behaviour beyond the shared conformance suite.

Scaffold/user-prose preservation, managed-marker discipline, and the "usefulness pin":
AGENTS.md must carry workflow content and role mission text compiled from staging files,
not just a roster stub — regression coverage for a staging-file-never-read bug class.
"""

import pytest

from squads._backends._agents_md._backend import AgentsMdBackend
from squads._backends._agents_md._managed import END, START
from squads._backends._base import BackendContext, OperatorView, RoleView
from squads._models._config import SquadsConfig
from squads._paths import SquadPaths
from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
def squad_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def ctx(squad_root):
    config = SquadsConfig(squad_dir="squads", active_backends=["agents_md"])
    squad_dir = squad_root / "squads"
    squad_dir.mkdir()
    return BackendContext(paths=SquadPaths(root=squad_root, squad_dir=squad_dir, config=config))


@pytest.fixture
def backend():
    return AgentsMdBackend()


@pytest.fixture
def roster():
    return [
        RoleView(slug="manager", full_name="Catherine Manager", title="Manager", is_default=True),
        RoleView(
            slug="python-dev", full_name="Elias Python", title="Python developer", is_default=False
        ),
    ]


@pytest.fixture
def operators():
    return [OperatorView(slug="op-pierre", full_name="Pierre Chat")]


class TestScaffold:
    async def test_creates_agents_md_at_the_project_root(self, backend, ctx, squad_root):
        agents_md = squad_root / "AGENTS.md"
        assert not agents_md.exists()
        await backend.ensure_scaffold(ctx)
        assert agents_md.exists()

    async def test_does_not_clobber_existing_user_prose(self, backend, ctx, squad_root):
        agents_md = squad_root / "AGENTS.md"
        agents_md.write_text("# My project\n\nUser prose here.\n", encoding="utf-8")
        await backend.ensure_scaffold(ctx)
        assert "User prose here." in agents_md.read_text(encoding="utf-8")


class TestWriteManaged:
    async def test_managed_markers_delimit_the_section(
        self, backend, ctx, squad_root, roster, operators
    ):
        await backend.ensure_scaffold(ctx)
        await backend.write_managed(ctx, roster, operators)
        text = (squad_root / "AGENTS.md").read_text(encoding="utf-8")
        assert START in text
        assert END in text

    async def test_user_prose_outside_the_markers_survives_write_managed(
        self, backend, ctx, squad_root, roster, operators
    ):
        agents_md = squad_root / "AGENTS.md"
        agents_md.write_text("# My project\n\nUser prose here.\n", encoding="utf-8")
        await backend.write_managed(ctx, roster, operators)
        assert "User prose here." in agents_md.read_text(encoding="utf-8")

    async def test_managed_markers_are_not_duplicated_on_a_second_write(
        self, backend, ctx, squad_root, roster, operators
    ):
        await backend.ensure_scaffold(ctx)
        await backend.write_managed(ctx, roster, operators)
        await backend.write_managed(ctx, roster, operators)
        text = (squad_root / "AGENTS.md").read_text(encoding="utf-8")
        assert text.count(START) == 1
        assert text.count(END) == 1


class TestUsefulnessPin:
    """AGENTS.md must be genuinely useful, not a roster-only stub — the regression class
    is a staging file written by the service but never read by write_managed."""

    async def test_workflow_commands_and_status_machine_reach_agents_md_after_sync(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        await svc.sync()
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "sq create task" in text
        assert "Todo" in text
        assert "InProgress" in text
        assert "Canonical" in text  # the type-alias table header

    async def test_role_mission_text_is_compiled_into_agents_md_after_sync(
        self, tmp_path, monkeypatch
    ):
        """Regression guard: role missions are written to a staging file by the service and
        must actually be read by write_managed, not orphaned."""
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        await svc.sync()
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Role definitions" in text
        assert "**Mission:**" in text
        assert "first point of contact" in text  # the manager's real mission, not a title stub


class TestCliRoundTrip:
    async def test_sq_init_with_backend_agents_md_produces_a_valid_file(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        agents_md = tmp_path / "AGENTS.md"
        assert agents_md.exists()
        text = agents_md.read_text(encoding="utf-8")
        assert START in text
        assert "Catherine Manager" in text

    async def test_sq_sync_refreshes_agents_md_idempotently(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        await svc.add_operator("Pierre Chat")
        await svc.sync()
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Pierre Chat" in text and "op-pierre" in text
        await svc.sync()
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == text

    async def test_agents_md_only_backend_never_creates_a_claude_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        assert not (tmp_path / ".claude").exists()
