"""agents_md backend-specific tests.

These tests assert AGENTS.md-specific behaviour beyond what the shared
conformance suite covers: valid AGENTS.md structure, managed markers, user prose
preservation, roster/operator reflection in the managed section, and the
sq init --backend agents_md / sq sync CLI round-trip.
"""

import pytest

from squads._backends._agents_md._backend import AgentsMdBackend
from squads._backends._agents_md._managed import END, START
from squads._backends._base import BackendContext, OperatorView, RoleView
from squads._models._config import SquadsConfig
from squads._paths import SquadPaths
from squads._services import _service as service

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def squad_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def ctx(squad_root):
    config = SquadsConfig(squad_dir="squads", default_backend="agents_md")
    squad_dir = squad_root / "squads"
    squad_dir.mkdir()
    paths = SquadPaths(root=squad_root, squad_dir=squad_dir, config=config)
    from squads import __version__

    return BackendContext(paths=paths, version=__version__)


@pytest.fixture
def backend():
    return AgentsMdBackend()


@pytest.fixture
def roster():
    return [
        RoleView(slug="manager", full_name="Catherine Manager", title="Manager", is_default=True),
        RoleView(
            slug="python-dev",
            full_name="Elias Python",
            title="Python developer",
            is_default=False,
        ),
    ]


@pytest.fixture
def operators():
    return [OperatorView(slug="op-pierre", full_name="Pierre Chat")]


# ---------------------------------------------------------------------------
# AGENTS.md scaffold
# ---------------------------------------------------------------------------


class TestAgentsMdScaffold:
    def test_creates_agents_md(self, backend, ctx, squad_root):
        """ensure_scaffold creates AGENTS.md at the project root."""
        agents_md = squad_root / "AGENTS.md"
        assert not agents_md.exists()
        backend.ensure_scaffold(ctx)
        assert agents_md.exists()

    def test_does_not_clobber_existing_agents_md(self, backend, ctx, squad_root):
        """ensure_scaffold must not overwrite user prose already in AGENTS.md."""
        agents_md = squad_root / "AGENTS.md"
        agents_md.write_text("# My project\n\nUser prose here.\n", encoding="utf-8")
        backend.ensure_scaffold(ctx)
        text = agents_md.read_text(encoding="utf-8")
        assert "User prose here." in text

    def test_scaffold_idempotent(self, backend, ctx, squad_root):
        """Running ensure_scaffold twice does not change the file."""
        backend.ensure_scaffold(ctx)
        first = (squad_root / "AGENTS.md").read_text(encoding="utf-8")
        backend.ensure_scaffold(ctx)
        second = (squad_root / "AGENTS.md").read_text(encoding="utf-8")
        assert first == second


# ---------------------------------------------------------------------------
# write_managed — managed section content
# ---------------------------------------------------------------------------


class TestWriteManaged:
    def test_managed_markers_present(self, backend, ctx, squad_root, roster, operators):
        """The managed section is delimited by the stable squads markers."""
        backend.ensure_scaffold(ctx)
        backend.write_managed(ctx, roster, operators)
        text = (squad_root / "AGENTS.md").read_text(encoding="utf-8")
        assert START in text
        assert END in text

    def test_roster_roles_in_managed_section(self, backend, ctx, squad_root, roster, operators):
        """All roster roles appear in the managed section of AGENTS.md."""
        backend.ensure_scaffold(ctx)
        backend.write_managed(ctx, roster, operators)
        text = (squad_root / "AGENTS.md").read_text(encoding="utf-8")
        for role in roster:
            assert role.full_name in text or role.slug in text

    def test_operators_in_managed_section(self, backend, ctx, squad_root, roster, operators):
        """Operators appear in the managed section of AGENTS.md."""
        backend.ensure_scaffold(ctx)
        backend.write_managed(ctx, roster, operators)
        text = (squad_root / "AGENTS.md").read_text(encoding="utf-8")
        for op in operators:
            assert op.full_name in text or op.slug in text

    def test_user_prose_preserved(self, backend, ctx, squad_root, roster, operators):
        """User prose outside the managed markers is not modified by write_managed."""
        agents_md = squad_root / "AGENTS.md"
        agents_md.write_text("# My project\n\nUser prose here.\n", encoding="utf-8")
        backend.write_managed(ctx, roster, operators)
        text = agents_md.read_text(encoding="utf-8")
        assert "User prose here." in text

    def test_managed_section_not_duplicated(self, backend, ctx, squad_root, roster, operators):
        """Calling write_managed twice must not duplicate the managed markers."""
        backend.ensure_scaffold(ctx)
        backend.write_managed(ctx, roster, operators)
        backend.write_managed(ctx, roster, operators)
        text = (squad_root / "AGENTS.md").read_text(encoding="utf-8")
        assert text.count(START) == 1
        assert text.count(END) == 1


# ---------------------------------------------------------------------------
# Usefulness pin: AGENTS.md must carry workflow + role content, not just roster.
#
# This class guards the FEAT-000016 US1 acceptance criterion:
# "a valid AGENTS.md carrying roster, workflow and skill content."
# A regression to a roster-only stub causes these tests to fail.
# ---------------------------------------------------------------------------


class TestAgentsMdUsefulnessPin:
    """AGENTS.md must be genuinely useful — not a thin roster stub.

    Pins the three content dimensions from FEAT-000016 US1:
    1. Workflow content (sq commands, status machine, alias table).
    2. Role mission text (from staging files compiled by write_managed).
    3. Roster already covered by TestWriteManaged — not duplicated here.
    """

    def test_workflow_content_in_agents_md_after_sync(self, tmp_path, monkeypatch):
        """After sq init + sq sync the managed section contains workflow commands.

        Specifically checks for known phrases from workflow.md.j2 so that a future
        regression to a roster-only template fails immediately.
        """
        monkeypatch.chdir(tmp_path)
        result = service.init(root=tmp_path, backend="agents_md", roles_spec="minimal")
        svc = service.Service(result.paths)
        svc.sync()
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        # Phrases from workflow.md.j2 — any absent phrase indicates workflow is missing.
        assert "sq create task" in text, "workflow.md.j2 content missing: 'sq create task'"
        assert "Todo" in text, "workflow.md.j2 content missing: status machine ('Todo')"
        assert "InProgress" in text, "workflow.md.j2 content missing: status ('InProgress')"
        # Alias table header from workflow.md.j2
        assert "Canonical" in text, "workflow.md.j2 alias table missing"

    def test_role_mission_in_agents_md_after_sync(self, tmp_path, monkeypatch):
        """After sq init + sq sync the Role definitions section contains mission text.

        The manager role's mission is compiled from the staging file into AGENTS.md.
        A regression where staging files are orphaned (never read by write_managed)
        causes this test to fail.
        """
        monkeypatch.chdir(tmp_path)
        result = service.init(root=tmp_path, backend="agents_md", roles_spec="minimal")
        svc = service.Service(result.paths)
        svc.sync()
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        # The manager role's mission starts with "Be the operator's first point of contact"
        assert "Mission:" in text, "Role definitions section missing mission text"
        assert "first point of contact" in text, (
            "Manager mission text not compiled into AGENTS.md — "
            "staging files may be orphaned (not read by write_managed)"
        )

    def test_role_definitions_not_title_only_stub(self, tmp_path, monkeypatch):
        """Role definitions must carry more than a title stub.

        Before F1 was fixed, role definitions rendered only '**Role:** manager' with
        no mission content.  This test guards that regression.
        """
        monkeypatch.chdir(tmp_path)
        result = service.init(root=tmp_path, backend="agents_md", roles_spec="minimal")
        svc = service.Service(result.paths)
        svc.sync()
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        # There must be a Role definitions section with mission content, not just the
        # title line '**Role:** manager'.
        assert "Role definitions" in text, "Role definitions section header missing"
        assert "**Mission:**" in text, (
            "Role definitions section contains only title stubs — mission text is missing"
        )

    def test_workflow_alias_table_in_agents_md(self, backend, ctx, squad_root, roster, operators):
        """The type-alias table from workflow.md.j2 is present in the managed section.

        This is a unit-level check (no full sq init needed) that the template
        renders the alias table via the type_aliases context variable.
        """
        backend.ensure_scaffold(ctx)
        backend.write_managed(ctx, roster, operators)
        text = (squad_root / "AGENTS.md").read_text(encoding="utf-8")
        # The alias table has these columns regardless of the actual alias values.
        assert "Canonical" in text, "Type-alias table header missing from AGENTS.md"
        assert "sq create task" in text, "Workflow commands missing from AGENTS.md"


# ---------------------------------------------------------------------------
# CLI round-trip: sq init --backend agents_md / sq sync
# ---------------------------------------------------------------------------


class TestCLIRoundTrip:
    def test_sq_init_backend_agents_md(self, tmp_path, monkeypatch):
        """sq init --backend agents_md produces a valid AGENTS.md."""
        monkeypatch.chdir(tmp_path)
        service.init(root=tmp_path, backend="agents_md", roles_spec="minimal")
        agents_md = tmp_path / "AGENTS.md"
        assert agents_md.exists(), "AGENTS.md must exist after sq init --backend agents_md"
        text = agents_md.read_text(encoding="utf-8")
        assert START in text
        assert "Catherine Manager" in text  # manager in minimal roster

    def test_sq_sync_refreshes_agents_md(self, tmp_path, monkeypatch):
        """sq sync (via service) refreshes AGENTS.md idempotently."""
        monkeypatch.chdir(tmp_path)
        result = service.init(root=tmp_path, backend="agents_md", roles_spec="minimal")
        svc = service.Service(result.paths)

        # Add an operator and re-sync.
        svc.add_operator("Pierre Chat")
        svc.sync()

        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Pierre Chat" in text
        assert "op-pierre" in text

        # Second sync must be idempotent.
        svc.sync()
        text2 = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert text == text2

    def test_sq_init_agents_md_no_claude_dir(self, tmp_path, monkeypatch):
        """sq init --backend agents_md must not create a .claude directory."""
        monkeypatch.chdir(tmp_path)
        service.init(root=tmp_path, backend="agents_md", roles_spec="minimal")
        assert not (tmp_path / ".claude").exists(), (
            ".claude/ must not be created by the agents_md backend"
        )
