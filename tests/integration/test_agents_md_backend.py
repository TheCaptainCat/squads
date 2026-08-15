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
    return [OperatorView(slug="op-alice", full_name="Alice Tester")]


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
    """AGENTS.md must be genuinely useful, not a roster-only stub — every role field the
    section renders has to actually arrive there, from the roster view it is handed."""

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

    async def test_role_mission_and_responsibilities_are_compiled_into_agents_md_after_sync(
        self, tmp_path, monkeypatch
    ):
        """Both role prose fields reach the compiled section.

        ``responsibilities`` is the half that had never rendered once: the section template
        has always carried the block, and the value it looped over was an unconditional empty
        list, so the block was dead code that no test noticed because it emitted nothing."""
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        await svc.sync()
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Role definitions" in text
        assert "**Mission:**" in text
        assert "first point of contact" in text  # the manager's real mission, not a title stub
        assert "**Responsibilities:**" in text
        role = await svc.roster_item("role", "manager")
        assert role is not None
        for responsibility in role.extra["responsibilities"]:
            assert f"- {responsibility}" in text

    async def test_a_relabelled_role_entry_template_cannot_empty_the_compiled_section(
        self, tmp_path, monkeypatch
    ):
        """The compiled section is built from the roster view, never parsed back out of the
        per-role staging markdown this backend generated one step earlier.

        The staging entry's ``**Mission:**`` line used to be the carrier: ``write_managed``
        recovered the mission by matching that literal prefix, so relabelling the line in
        ``role_entry.md.j2`` — a rendering choice, not a declaration — silently emptied every
        mission from AGENTS.md with nothing reporting it. Driven here by rewriting the staged
        files to the relabelled shape and recompiling: the missions must survive."""
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        await svc.sync()

        staged = sorted((tmp_path / ".agents_md" / "roles").glob("*.md"))
        assert staged, "the per-role staging files should exist to be relabelled"
        for entry in staged:
            relabelled = entry.read_text(encoding="utf-8").replace("**Mission:**", "**Purpose:**")
            assert "**Purpose:**" in relabelled
            entry.write_text(relabelled, encoding="utf-8")

        await svc.refresh_managed()  # recompile only -- does not rewrite the staging files
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "first point of contact" in text
        assert "**Mission:**" in text

    async def test_the_compiled_section_needs_no_staging_files_at_all(
        self, backend, ctx, operators
    ):
        """The sharpest form of the same property: with no staging directory in existence,
        every role field still renders, because the view carries them."""
        roster = [
            RoleView(
                slug="qa",
                full_name="Mara Tester",
                title="QA engineer",
                is_default=False,
                mission="Break it before an adopter does.",
                responsibilities=("Write the failing case first",),
            )
        ]
        assert not (ctx.root / ".agents_md").exists()

        await backend.write_managed(ctx, roster, operators)

        text = (ctx.root / "AGENTS.md").read_text(encoding="utf-8")
        assert "Break it before an adopter does." in text
        assert "- Write the failing case first" in text


class TestRosterProjection:
    """Retiring a role withdraws its staging file and excludes it from the compiled
    AGENTS.md region — the agents_md half of the projection, alongside the Claude
    backend's default-role-line/dev-gated-skill coverage in test_claude_code_backend.py."""

    async def test_retiring_a_role_excludes_it_from_the_compiled_agents_md_and_withdraws_its_staging_file(  # noqa: E501
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        item = await svc.activate_role("qa")
        await svc.refresh_managed()  # the CLI's own post-activate step
        staging = tmp_path / ".agents_md" / "roles" / "qa.md"
        assert staging.exists()
        before = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Mara Tester" in before

        await svc.set_status(item.id, "Archived")
        assert not staging.exists()
        after = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Mara Tester" not in after

    async def test_reactivating_regenerates_the_staging_file_and_the_compiled_entry(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        item = await svc.activate_role("qa")
        staging = tmp_path / ".agents_md" / "roles" / "qa.md"
        await svc.set_status(item.id, "Archived")
        assert not staging.exists()

        await svc.set_status(item.id, "Active")
        assert staging.exists()
        after = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Mara Tester" in after


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
        await svc.add_operator("Alice Tester")
        await svc.sync()
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Alice Tester" in text and "op-alice" in text
        await svc.sync()
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == text

    async def test_agents_md_only_backend_never_creates_a_claude_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        assert not (tmp_path / ".claude").exists()
