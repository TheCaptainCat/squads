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
from squads._roles._resolver import resolve_role_for_item
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
        resolved = resolve_role_for_item(role, svc.paths.squad_dir)
        assert resolved.responsibilities  # sanity: the catalog really does declare some
        for responsibility in resolved.responsibilities:
            assert f"- {responsibility}" in text

    async def test_a_full_sync_creates_no_staging_directory_at_all(self, tmp_path, monkeypatch):
        """The compiled section is built entirely from the roster view, never from a per-role
        staging file this backend renders one step earlier — driven here through the real
        ``sq init``/``sq sync`` path rather than calling ``write_managed`` directly.

        A prior version of this backend staged a markdown file per role under
        ``.agents_md/roles/`` purely so ``generate_role_entry`` had something to return; a bug
        in *that* file's own rendering (a relabelled ``**Mission:**`` line) used to be able to
        silently empty a mission out of the compiled AGENTS.md. That whole class of bug is now
        structurally impossible: this backend no longer writes such a file, so a full sync
        creates no ``.agents_md`` directory, and the mission still reaches AGENTS.md because
        ``write_managed`` never depended on it."""
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        await svc.sync()

        assert not (tmp_path / ".agents_md").exists()
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
    """Retiring a role excludes it from the compiled AGENTS.md region — the agents_md half of
    the projection, alongside the Claude backend's default-role-line/dev-gated-skill coverage
    in test_claude_code_backend.py. Neither direction touches a staging file any more: this
    backend no longer has one (see ``AgentsMdBackend``'s module docstring)."""

    async def test_retiring_a_role_excludes_it_from_the_compiled_agents_md(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        item = await svc.activate_role("qa")
        await svc.refresh_managed()  # the CLI's own post-activate step
        before = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Mara Tester" in before

        await svc.set_status(item.id, "Archived")
        after = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Mara Tester" not in after
        assert not (tmp_path / ".agents_md").exists()

    async def test_reactivating_restores_the_compiled_entry(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        item = await svc.activate_role("qa")
        await svc.set_status(item.id, "Archived")
        assert "Mara Tester" not in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")

        await svc.set_status(item.id, "Active")
        after = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "Mara Tester" in after
        assert not (tmp_path / ".agents_md").exists()


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


class TestUpgradedSquadCleansUpLegacyStagingFiles:
    """A squad that already carries ``.agents_md/roles/*.md``/``.agents_md/skills/*.md``
    staging files from a pre-upgrade version of this backend (see the module docstring)
    converges to a clean tree with no manual step: an ordinary ``sq sync`` removes a leftover
    file for any role/skill still in the roster, live or retired, because the same
    materialise/withdraw calls that project the roster now delete on both paths."""

    async def test_a_live_roles_legacy_staging_file_is_gone_after_one_sync(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        leftover = tmp_path / ".agents_md" / "roles" / "manager.md"
        leftover.parent.mkdir(parents=True, exist_ok=True)
        leftover.write_text("stale leftover from a pre-upgrade version\n", encoding="utf-8")

        await svc.sync()
        assert not leftover.exists()

    async def test_a_retired_roles_legacy_staging_file_is_gone_after_one_sync(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        item = await svc.activate_role("qa")
        await svc.set_status(item.id, "Archived")
        leftover = tmp_path / ".agents_md" / "roles" / "qa.md"
        leftover.parent.mkdir(parents=True, exist_ok=True)
        leftover.write_text("stale leftover from a pre-upgrade version\n", encoding="utf-8")

        await svc.sync()
        assert not leftover.exists()

    async def test_a_fully_removed_items_leftover_file_survives_sync_but_is_reported_as_an_orphan(
        self, tmp_path, monkeypatch
    ):
        """Nothing in a roster sweep ever visits a slug with no item at all — this is the one
        shape ``candidate_orphans`` still needs to catch, on the next ``sq adopt``."""
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        leftover = tmp_path / ".agents_md" / "roles" / "a-role-that-was-removed-outright.md"
        leftover.parent.mkdir(parents=True, exist_ok=True)
        leftover.write_text("nobody owns this any more\n", encoding="utf-8")

        await svc.sync()
        assert leftover.exists()

        orphans = await svc.candidate_orphans()
        assert any("a-role-that-was-removed-outright.md" in o for o in orphans)
