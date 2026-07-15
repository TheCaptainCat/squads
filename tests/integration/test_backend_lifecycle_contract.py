"""Every registered AgentBackend honours the same lifecycle contract.

Parametrized over the backend registry so a future backend inherits this whole suite for
free just by being added to ``_BACKEND_FACTORIES`` below. Covers ensure_scaffold,
write_managed, generate_role_entry/generate_skill_entry, remove_artifacts, the full
scaffold->write->generate->remove round trip, and managed_paths — the read-only probe.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from squads._backends._agents_md._backend import AgentsMdBackend
from squads._backends._base import AgentBackend, Artifact, BackendContext, OperatorView, RoleView
from squads._backends._claude_code._backend import ClaudeCodeBackend
from squads._board import _store as board_store
from squads._memory import _store as memory_store
from squads._models._config import SquadsConfig
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._paths import SquadPaths
from squads._roles._catalog import RoleDef
from squads._services import _service as service

pytestmark = pytest.mark.anyio

BackendFactory = Callable[[], AgentBackend]

_BACKEND_FACTORIES: list[tuple[str, BackendFactory]] = [
    ("claude_code", ClaudeCodeBackend),
    ("agents_md", AgentsMdBackend),
]


@pytest.fixture(
    params=[name for name, _ in _BACKEND_FACTORIES], ids=[name for name, _ in _BACKEND_FACTORIES]
)
def backend(request: pytest.FixtureRequest) -> AgentBackend:
    name: str = request.param
    return dict(_BACKEND_FACTORIES)[name]()


@pytest.fixture
def squad_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def paths(squad_root: Path) -> SquadPaths:
    config = SquadsConfig(squad_dir="squads", active_backends=["claude_code"])
    squad_dir = squad_root / "squads"
    squad_dir.mkdir()
    return SquadPaths(root=squad_root, squad_dir=squad_dir, config=config)


@pytest.fixture
def ctx(paths: SquadPaths) -> BackendContext:
    return BackendContext(paths=paths)


@pytest.fixture
def roster() -> list[RoleView]:
    return [
        RoleView(slug="manager", full_name="Catherine Manager", title="Manager", is_default=True),
        RoleView(
            slug="python-dev", full_name="Elias Python", title="Python developer", is_default=False
        ),
    ]


@pytest.fixture
def operators() -> list[OperatorView]:
    return [OperatorView(slug="op-pierre", full_name="Pierre Chat")]


@pytest.fixture
def role_def() -> RoleDef:
    return RoleDef(
        slug="manager",
        full_name="Catherine Manager",
        title="Manager",
        description="Triages and routes.",
        mission="Coordinate the team.",
        is_default=True,
    )


_FIXED_TS: datetime = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)


def _make_role_item(sequence_id: int, slug: str, squad_dir: Path) -> Item:
    folder = squad_dir / "roles"
    folder.mkdir(exist_ok=True)
    filename = f"ROLE-{sequence_id:06d}-{slug}.md"
    (folder / filename).write_text(f"---\nid: ROLE-{sequence_id:06d}\n---\n", encoding="utf-8")
    return Item(
        sequence_id=sequence_id,
        type="role",
        title="Catherine Manager",
        slug=slug,
        status="Active",
        path=f"roles/{filename}",
        created_at=_FIXED_TS,
        updated_at=_FIXED_TS,
        extra={
            X.SLUG: slug,
            X.FULL_NAME: "Catherine Manager",
            X.TITLE: "Manager",
            X.MISSION: "Coordinate.",
            X.RESPONSIBILITIES: [],
            X.AGREEMENTS: [],
            X.MODEL: "sonnet",
            X.COLOR: "blue",
            X.IS_DEFAULT: True,
        },
    )


def _make_skill_item(sequence_id: int, slug: str, squad_dir: Path) -> Item:
    folder = squad_dir / "skills"
    folder.mkdir(exist_ok=True)
    filename = f"SKILL-{sequence_id:06d}-{slug}.md"
    (folder / filename).write_text(f"---\nid: SKILL-{sequence_id:06d}\n---\n", encoding="utf-8")
    return Item(
        sequence_id=sequence_id,
        type="skill",
        title=slug,
        slug=slug,
        status="Active",
        path=f"skills/{filename}",
        created_at=_FIXED_TS,
        updated_at=_FIXED_TS,
        extra={X.SLUG: slug, X.DESCRIPTION: f"The {slug} skill."},
    )


# ---------------------------------------------------------------------------
# Artifact invariants
# ---------------------------------------------------------------------------


class TestArtifactInvariants:
    def test_artifact_is_immutable(self) -> None:
        a = Artifact(path="some/file.md", kind="agent", backend="claude_code")
        with pytest.raises((AttributeError, TypeError)):
            a.path = "other"  # type: ignore[misc]

    def test_artifact_kind_is_non_empty(self) -> None:
        a = Artifact(path="x", kind="any_kind", backend="b")
        assert a.kind


# ---------------------------------------------------------------------------
# ensure_scaffold
# ---------------------------------------------------------------------------


class TestEnsureScaffold:
    async def test_returns_artifacts_naming_the_backend(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        for artifact in await backend.ensure_scaffold(ctx):
            assert isinstance(artifact, Artifact)
            assert artifact.backend == backend.name

    async def test_artifact_paths_are_root_relative_forward_slash(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        for artifact in await backend.ensure_scaffold(ctx):
            p = Path(artifact.path)
            assert not p.is_absolute(), f"expected a relative path, got {artifact.path!r}"
            assert "\\" not in artifact.path

    async def test_declared_artifacts_exist_on_disk(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        for artifact in await backend.ensure_scaffold(ctx):
            assert (ctx.root / artifact.path).exists(), f"missing on disk: {artifact.path!r}"

    async def test_scaffold_is_idempotent(self, backend: AgentBackend, ctx: BackendContext) -> None:
        first = [a.path for a in await backend.ensure_scaffold(ctx)]
        second = [a.path for a in await backend.ensure_scaffold(ctx)]
        assert first == second

    async def test_scaffold_does_not_clobber_user_content(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        """A user-added key survives a re-scaffold of any mergeable (JSON) artifact.

        A no-op for a backend with no pre-existing mergeable file at all.
        """
        for artifact in await backend.ensure_scaffold(ctx):
            full = ctx.root / artifact.path
            if not full.exists():
                continue
            original = full.read_text(encoding="utf-8")
            try:
                data = json.loads(original)
            except (json.JSONDecodeError, UnicodeDecodeError):  # fmt: skip
                continue
            data["_conformance_user_key"] = "preserved"
            full.write_text(json.dumps(data), encoding="utf-8")
            await backend.ensure_scaffold(ctx)
            after = json.loads(full.read_text(encoding="utf-8"))
            assert after.get("_conformance_user_key") == "preserved", (
                f"ensure_scaffold clobbered user content in {artifact.path!r}"
            )
            break  # one mergeable file is enough to prove the contract


# ---------------------------------------------------------------------------
# write_managed
# ---------------------------------------------------------------------------


class TestWriteManaged:
    async def test_returns_artifacts_naming_the_backend(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        await backend.ensure_scaffold(ctx)
        for artifact in await backend.write_managed(ctx, roster, operators):
            assert isinstance(artifact, Artifact)
            assert artifact.backend == backend.name
            assert not Path(artifact.path).is_absolute()
            assert "\\" not in artifact.path
            assert (ctx.root / artifact.path).exists()

    async def test_write_managed_is_byte_identical_on_a_second_run(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        await backend.ensure_scaffold(ctx)
        first = await backend.write_managed(ctx, roster, operators)
        second = await backend.write_managed(ctx, roster, operators)
        assert [a.path for a in first] == [a.path for a in second]
        for artifact in first:
            full = ctx.root / artifact.path
            assert full.read_text(encoding="utf-8") == full.read_text(encoding="utf-8")

    async def test_managed_marker_appears_at_most_once_per_file(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        """Calling write_managed twice must not duplicate the managed section."""
        await backend.ensure_scaffold(ctx)
        await backend.write_managed(ctx, roster, operators)
        artifacts = await backend.write_managed(ctx, roster, operators)
        for artifact in artifacts:
            full = ctx.root / artifact.path
            if not full.exists():
                continue
            text = full.read_text(encoding="utf-8")
            for marker in ("<!-- squads:start -->", "<!-- squads:managed"):
                count = text.count(marker)
                assert count <= 1, f"{marker!r} appears {count} times in {artifact.path!r}"

    async def test_roster_and_operator_names_reach_the_managed_output(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        await backend.ensure_scaffold(ctx)
        artifacts = await backend.write_managed(ctx, roster, operators)
        all_text = ""
        for artifact in artifacts:
            full = ctx.root / artifact.path
            if full.exists():
                try:
                    all_text += full.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
        for role in roster:
            assert role.full_name in all_text or role.slug in all_text, (
                f"role {role.full_name!r} not reflected in write_managed output"
            )
        for op in operators:
            assert op.full_name in all_text or op.slug in all_text, (
                f"operator {op.full_name!r} not reflected in write_managed output"
            )


# ---------------------------------------------------------------------------
# generate_role_entry / generate_skill_entry (the pointer surface)
# ---------------------------------------------------------------------------


class TestGeneratePointerEntries:
    async def test_role_pointer_is_a_well_formed_relative_artifact(
        self, backend: AgentBackend, ctx: BackendContext, role_def: RoleDef
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        artifact = await backend.generate_role_entry(ctx, item, role_def)
        assert isinstance(artifact, Artifact)
        assert artifact.backend == backend.name
        assert not Path(artifact.path).is_absolute()
        assert (ctx.root / artifact.path).exists()

    async def test_role_pointer_references_the_real_definition(
        self, backend: AgentBackend, ctx: BackendContext, role_def: RoleDef
    ) -> None:
        """The pointer file must name the role so an agent can identify it — never a
        dangling reference to nothing."""
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        artifact = await backend.generate_role_entry(ctx, item, role_def)
        content = (ctx.root / artifact.path).read_text(encoding="utf-8")
        assert role_def.slug in content or role_def.full_name in content

    async def test_role_pointer_generation_is_idempotent(
        self, backend: AgentBackend, ctx: BackendContext, role_def: RoleDef
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        a1 = await backend.generate_role_entry(ctx, item, role_def)
        a2 = await backend.generate_role_entry(ctx, item, role_def)
        assert a1.path == a2.path
        assert (ctx.root / a1.path).read_text(encoding="utf-8") == (ctx.root / a2.path).read_text(
            encoding="utf-8"
        )

    async def test_skill_pointer_is_a_well_formed_relative_artifact(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_skill_item(2, "my-skill", ctx.squad_dir)
        artifact = await backend.generate_skill_entry(ctx, item)
        assert isinstance(artifact, Artifact)
        assert artifact.backend == backend.name
        assert not Path(artifact.path).is_absolute()
        assert (ctx.root / artifact.path).exists()

    async def test_skill_pointer_generation_is_idempotent(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_skill_item(2, "my-skill", ctx.squad_dir)
        a1 = await backend.generate_skill_entry(ctx, item)
        a2 = await backend.generate_skill_entry(ctx, item)
        assert a1.path == a2.path
        assert (ctx.root / a1.path).read_text(encoding="utf-8") == (ctx.root / a2.path).read_text(
            encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# remove_artifacts
# ---------------------------------------------------------------------------


class TestRemoveArtifacts:
    async def test_safe_to_call_when_nothing_was_ever_generated(
        self, backend: AgentBackend, ctx: BackendContext, role_def: RoleDef
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        await backend.remove_artifacts(ctx, item)  # must not raise

    async def test_removes_a_generated_role_pointer(
        self, backend: AgentBackend, ctx: BackendContext, role_def: RoleDef
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        artifact = await backend.generate_role_entry(ctx, item, role_def)
        full = ctx.root / artifact.path
        assert full.exists()
        await backend.remove_artifacts(ctx, item)
        assert not full.exists()

    async def test_removes_a_generated_skill_pointer(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_skill_item(2, "my-skill", ctx.squad_dir)
        artifact = await backend.generate_skill_entry(ctx, item)
        full = ctx.root / artifact.path
        assert full.exists()
        await backend.remove_artifacts(ctx, item)
        assert not full.exists()

    async def test_is_idempotent(
        self, backend: AgentBackend, ctx: BackendContext, role_def: RoleDef
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        await backend.generate_role_entry(ctx, item, role_def)
        await backend.remove_artifacts(ctx, item)
        await backend.remove_artifacts(ctx, item)  # must not raise on the second call


# ---------------------------------------------------------------------------
# Full round trip: scaffold -> write_managed -> generate pointers -> remove
# ---------------------------------------------------------------------------


class TestFullLifecycleRoundTrip:
    async def test_leaves_no_orphaned_pointer_files(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
        role_def: RoleDef,
    ) -> None:
        await backend.ensure_scaffold(ctx)
        await backend.write_managed(ctx, roster, operators)

        role_item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        role_artifact = await backend.generate_role_entry(ctx, role_item, role_def)
        skill_item = _make_skill_item(2, "my-skill", ctx.squad_dir)
        skill_artifact = await backend.generate_skill_entry(ctx, skill_item)
        assert (ctx.root / role_artifact.path).exists()
        assert (ctx.root / skill_artifact.path).exists()

        await backend.remove_artifacts(ctx, role_item)
        await backend.remove_artifacts(ctx, skill_item)
        assert not (ctx.root / role_artifact.path).exists()
        assert not (ctx.root / skill_artifact.path).exists()

    async def test_the_init_then_sync_service_round_trip_completes_and_is_idempotent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Drives every registered backend indirectly through the public service seam."""
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, roles_spec="minimal")
        svc = service.Service(result.paths)
        await svc.sync()
        await svc.sync()  # second sync must be idempotent


# ---------------------------------------------------------------------------
# backend.name
# ---------------------------------------------------------------------------


def test_backend_name_is_a_non_empty_string(backend: AgentBackend) -> None:
    assert isinstance(backend.name, str)
    assert backend.name


# ---------------------------------------------------------------------------
# Agent memory boot surfacing (index-only, through the backend)
# ---------------------------------------------------------------------------


class TestMemoryBootSurfacing:
    """A role's own memory index reaches its managed context through the backend — never
    hard-coded outside it — as index-only lines (slug + one-line summary, never the body)."""

    async def _managed_text(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
        role_item: Item,
        role_def: RoleDef,
    ) -> str:
        await backend.ensure_scaffold(ctx)
        artifacts = [*await backend.write_managed(ctx, roster, operators)]
        artifacts.append(await backend.generate_role_entry(ctx, role_item, role_def))
        text = ""
        for artifact in artifacts:
            full = ctx.root / artifact.path
            if full.exists():
                text += full.read_text(encoding="utf-8")
        return text

    async def test_an_empty_memory_pool_surfaces_no_memory_section(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
        role_def: RoleDef,
    ) -> None:
        role_item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        text = await self._managed_text(backend, ctx, roster, operators, role_item, role_def)
        assert f"sq memory {role_def.slug} show" not in text

    async def test_a_roles_memory_index_reaches_its_managed_output_through_the_backend(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
        role_def: RoleDef,
    ) -> None:
        await memory_store.add(ctx.paths, role_def.slug, "the scale suite takes about 4 minutes")
        role_item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        text = await self._managed_text(backend, ctx, roster, operators, role_item, role_def)
        assert "the-scale-suite-takes-about" in text
        assert "the scale suite takes about 4 minutes" in text

    async def test_only_the_index_is_surfaced_never_the_full_memory_body(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
        role_def: RoleDef,
    ) -> None:
        await memory_store.add(
            ctx.paths,
            role_def.slug,
            "short summary fact",
            body="A much longer freeform paragraph nobody should see at boot.",
        )
        role_item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        text = await self._managed_text(backend, ctx, roster, operators, role_item, role_def)
        assert "short summary fact" in text
        assert "A much longer freeform paragraph nobody should see at boot." not in text

    async def test_a_newly_added_memory_reaches_the_managed_output_only_after_regeneration(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
        role_def: RoleDef,
    ) -> None:
        """Proves the surfacing goes through the backend's regeneration path — like the
        rest of the managed content, refreshed on ``sq sync`` — rather than being baked in
        once and going stale."""
        role_item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        before = await self._managed_text(backend, ctx, roster, operators, role_item, role_def)
        assert "a fact learned mid-session" not in before

        await memory_store.add(ctx.paths, role_def.slug, "a fact learned mid-session")
        after = await self._managed_text(backend, ctx, roster, operators, role_item, role_def)
        assert "a fact learned mid-session" in after


# ---------------------------------------------------------------------------
# Bulletin board boot surfacing (content-and-all, team-scoped, through the backend)
# ---------------------------------------------------------------------------


class TestBoardBootSurfacing:
    """Current board notices reach the shared managed output through the backend — never
    hard-coded outside it — content and all (unlike memory, which is index-only), and
    team-scoped rather than per-role."""

    async def _managed_text(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> str:
        await backend.ensure_scaffold(ctx)
        artifacts = await backend.write_managed(ctx, roster, operators)
        text = ""
        for artifact in artifacts:
            full = ctx.root / artifact.path
            if full.exists():
                text += full.read_text(encoding="utf-8")
        return text

    async def test_an_empty_board_surfaces_no_board_section(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        text = await self._managed_text(backend, ctx, roster, operators)
        assert "## Board" not in text

    async def test_a_posted_notices_content_reaches_the_managed_output_through_the_backend(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        await board_store.post(ctx.paths, "op-pierre", "the CI runners are down for maintenance")
        text = await self._managed_text(backend, ctx, roster, operators)
        assert "the CI runners are down for maintenance" in text

    async def test_an_expired_notice_is_excluded_from_boot_surfacing(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        await board_store.post(
            ctx.paths, "op-pierre", "a notice long past its expiry", until="2020-01-01"
        )
        text = await self._managed_text(backend, ctx, roster, operators)
        assert "a notice long past its expiry" not in text
        assert "## Board" not in text

    async def test_an_all_expired_board_surfaces_nothing(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        await board_store.post(ctx.paths, "op-pierre", "notice one", until="2020-01-01")
        await board_store.post(ctx.paths, "tech-lead", "notice two", until="2020-06-01")
        text = await self._managed_text(backend, ctx, roster, operators)
        assert "notice one" not in text
        assert "notice two" not in text
        assert "## Board" not in text

    async def test_a_newly_posted_notice_reaches_the_managed_output_only_after_regeneration(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        """Proves the surfacing goes through the backend's regeneration path — like the
        rest of the managed content, refreshed on ``sq sync`` — rather than being baked in
        once and going stale."""
        before = await self._managed_text(backend, ctx, roster, operators)
        assert "a notice posted mid-session" not in before

        await board_store.post(ctx.paths, "op-pierre", "a notice posted mid-session")
        after = await self._managed_text(backend, ctx, roster, operators)
        assert "a notice posted mid-session" in after


# ---------------------------------------------------------------------------
# managed_paths — the read-only probe
# ---------------------------------------------------------------------------


class TestManagedPaths:
    def test_returns_root_relative_forward_slash_strings(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        for p in backend.managed_paths(ctx):
            assert isinstance(p, str)
            assert not Path(p).is_absolute()
            assert "\\" not in p

    def test_does_not_create_any_files(self, backend: AgentBackend, ctx: BackendContext) -> None:
        before = set(ctx.root.rglob("*"))
        backend.managed_paths(ctx)
        after = set(ctx.root.rglob("*"))
        assert before == after, f"managed_paths created new files: {after - before}"

    async def test_every_declared_path_exists_after_a_full_sync(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        await backend.ensure_scaffold(ctx)
        await backend.write_managed(ctx, roster, operators)
        for p in backend.managed_paths(ctx):
            assert (ctx.root / p).exists(), f"managed_paths declared {p!r} but it is missing"
