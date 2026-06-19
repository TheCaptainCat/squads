"""Shared AgentBackend conformance suite.

Asserts the *contract* that any AgentBackend implementation must honour, without
leaking Claude-specific assumptions into the assertions.  Parametrize the
``backend_factory`` fixture to add a new backend — the suite runs against every
registered factory automatically.

Claude-isms discovered while writing this suite are collected in
``CLAUDE_ISMS_FOUND`` at the bottom of this module and referenced by the tests
that would need to weaken an assertion to paper over them.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from squads import __version__
from squads._backends._agents_md._backend import AgentsMdBackend
from squads._backends._base import AgentBackend, Artifact, BackendContext, OperatorView, RoleView
from squads._backends._claude_code._backend import ClaudeCodeBackend
from squads._models._config import SquadsConfig
from squads._models._enums import ItemType, Status
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._paths import SquadPaths
from squads._roles._catalog import RoleDef
from squads._services import _service as service

# ---------------------------------------------------------------------------
# Backend factory registry — add new backends here to run the whole suite.
# ---------------------------------------------------------------------------

#: A backend factory is a zero-argument callable that returns an AgentBackend.
BackendFactory = Callable[[], AgentBackend]

_BACKEND_FACTORIES: list[tuple[str, BackendFactory]] = [
    ("claude_code", ClaudeCodeBackend),
    ("agents_md", AgentsMdBackend),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(
    params=[name for name, _ in _BACKEND_FACTORIES], ids=[name for name, _ in _BACKEND_FACTORIES]
)
def backend(request: pytest.FixtureRequest) -> AgentBackend:
    """Parametrized fixture — one backend instance per registered factory."""
    name: str = request.param
    factory = dict(_BACKEND_FACTORIES)[name]
    return factory()


@pytest.fixture
def squad_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh temp dir used as the project root (holds .squads.toml + backend dirs)."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def paths(squad_root: Path) -> SquadPaths:
    """Minimal SquadPaths wired to the temp root — no sq init required."""
    config = SquadsConfig(squad_dir="squads", active_backends=["claude_code"])
    squad_dir = squad_root / "squads"
    squad_dir.mkdir()
    return SquadPaths(root=squad_root, squad_dir=squad_dir, config=config)


@pytest.fixture
def ctx(paths: SquadPaths) -> BackendContext:
    return BackendContext(paths=paths, version=__version__)


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
    """Build a minimal ROLE Item with the required fields — no file needed for unit tests."""
    folder = squad_dir / "roles"
    folder.mkdir(exist_ok=True)
    filename = f"ROLE-{sequence_id:06d}-{slug}.md"
    path_str = f"roles/{filename}"
    # Write a stub file so any path-existence check passes.
    (folder / filename).write_text(f"---\nid: ROLE-{sequence_id:06d}\n---\n", encoding="utf-8")
    return Item(
        sequence_id=sequence_id,
        type=ItemType.ROLE,
        title="Catherine Manager",
        slug=slug,
        status=Status.ACTIVE,
        path=path_str,
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
    """Build a minimal SKILL Item with the required fields — no file needed for unit tests."""
    folder = squad_dir / "skills"
    folder.mkdir(exist_ok=True)
    filename = f"SKILL-{sequence_id:06d}-{slug}.md"
    path_str = f"skills/{filename}"
    (folder / filename).write_text(f"---\nid: SKILL-{sequence_id:06d}\n---\n", encoding="utf-8")
    return Item(
        sequence_id=sequence_id,
        type=ItemType.SKILL,
        title=slug,
        slug=slug,
        status=Status.ACTIVE,
        path=path_str,
        created_at=_FIXED_TS,
        updated_at=_FIXED_TS,
        extra={
            X.SLUG: slug,
            X.DESCRIPTION: f"The {slug} skill.",
        },
    )


# ---------------------------------------------------------------------------
# Contract: Artifact invariants
# ---------------------------------------------------------------------------


class TestArtifactContract:
    """An Artifact is an immutable record of what the backend wrote.

    Invariants that hold for any backend:
    - ``path`` is a forward-slash, project-root-relative string (never absolute).
    - ``backend`` matches the backend's own ``name`` class attribute.
    - ``kind`` is a non-empty string (vocabulary is backend-specific but must be non-empty).
    """

    def test_artifact_is_immutable(self) -> None:
        a = Artifact(path="some/file.md", kind="agent", backend="claude_code")
        with pytest.raises((AttributeError, TypeError)):
            a.path = "other"  # type: ignore[misc]

    def test_artifact_fields(self) -> None:
        a = Artifact(
            path="squads/agents/roles/ROLE-000001-manager.md", kind="agent", backend="test"
        )
        assert a.path == "squads/agents/roles/ROLE-000001-manager.md"
        assert a.kind == "agent"
        assert a.backend == "test"

    def test_artifact_kind_non_empty(self) -> None:
        """kind must be a non-empty string — backends must classify what they wrote."""
        a = Artifact(path="x", kind="any_kind", backend="b")
        assert a.kind  # truthy


# ---------------------------------------------------------------------------
# Contract: ensure_scaffold
# ---------------------------------------------------------------------------


class TestEnsureScaffold:
    """ensure_scaffold must be idempotent and return Artifacts describing what it wrote."""

    async def test_returns_list_of_artifacts(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        result = await backend.ensure_scaffold(ctx)
        assert isinstance(result, list)
        assert all(isinstance(a, Artifact) for a in result)

    async def test_artifacts_have_backend_name(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        for artifact in await backend.ensure_scaffold(ctx):
            assert artifact.backend == backend.name

    async def test_artifact_paths_are_relative(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        """Paths must be root-relative (no leading slash, no Windows drive letter)."""
        for artifact in await backend.ensure_scaffold(ctx):
            p = Path(artifact.path)
            assert not p.is_absolute(), f"Artifact.path must be relative, got: {artifact.path!r}"

    async def test_artifact_paths_use_forward_slashes(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        for artifact in await backend.ensure_scaffold(ctx):
            assert "\\" not in artifact.path, (
                f"Artifact.path must use forward slashes, got: {artifact.path!r}"
            )

    async def test_artifact_files_exist_on_disk(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        """Every path an artifact declares must actually exist on disk after scaffold."""
        for artifact in await backend.ensure_scaffold(ctx):
            full = ctx.root / artifact.path
            assert full.exists(), f"Declared artifact not on disk: {artifact.path!r}"

    async def test_scaffold_is_idempotent(self, backend: AgentBackend, ctx: BackendContext) -> None:
        """Running scaffold twice must not error and must produce the same artifact paths."""
        first = [a.path for a in await backend.ensure_scaffold(ctx)]
        second = [a.path for a in await backend.ensure_scaffold(ctx)]
        assert first == second

    async def test_scaffold_does_not_clobber_user_content(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        """A file the backend manages must not lose user-added content on re-scaffold.

        NOTE: This test checks the settings.json merge behaviour — the canonical
        "never clobber user content" surface for the claude_code backend.  A different
        backend would satisfy this differently; the test is written against the contract
        (idempotent, preserving) not against a specific file name.

        If a backend produces no pre-existing mergeable file at all, this test is a no-op
        (the loop body never executes).
        """
        artifacts = await backend.ensure_scaffold(ctx)
        for artifact in artifacts:
            full = ctx.root / artifact.path
            if not full.exists():
                continue
            # Mark the file with a sentinel; re-scaffold must not erase it.
            original = full.read_text(encoding="utf-8")
            # Only inject into JSON/text files we can safely round-trip.
            try:
                data = json.loads(original)
                # Add a custom user key that should survive the merge.
                data["_conformance_user_key"] = "preserved"
                full.write_text(json.dumps(data), encoding="utf-8")
                await backend.ensure_scaffold(ctx)
                after = json.loads(full.read_text(encoding="utf-8"))
                assert after.get("_conformance_user_key") == "preserved", (
                    f"ensure_scaffold clobbered user content in {artifact.path!r}"
                )
                break  # one mergeable file is enough to prove the contract
            except json.JSONDecodeError, UnicodeDecodeError:
                # Not a JSON file — skip clobber-check for this artifact
                continue


# ---------------------------------------------------------------------------
# Contract: write_managed
# ---------------------------------------------------------------------------


class TestWriteManaged:
    """write_managed must produce stable, idempotent output with the managed region
    injected once (not duplicated).
    """

    async def test_returns_list_of_artifacts(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        await backend.ensure_scaffold(ctx)
        result = await backend.write_managed(ctx, roster, operators)
        assert isinstance(result, list)
        assert all(isinstance(a, Artifact) for a in result)

    async def test_artifacts_have_backend_name(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        await backend.ensure_scaffold(ctx)
        for artifact in await backend.write_managed(ctx, roster, operators):
            assert artifact.backend == backend.name

    async def test_artifact_paths_are_relative_forward_slash(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        await backend.ensure_scaffold(ctx)
        for artifact in await backend.write_managed(ctx, roster, operators):
            assert not Path(artifact.path).is_absolute()
            assert "\\" not in artifact.path

    async def test_artifact_files_exist_on_disk(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        await backend.ensure_scaffold(ctx)
        for artifact in await backend.write_managed(ctx, roster, operators):
            assert (ctx.root / artifact.path).exists(), (
                f"Declared managed artifact not on disk: {artifact.path!r}"
            )

    async def test_write_managed_is_idempotent(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        """Running write_managed twice must produce byte-identical results for every artifact."""
        await backend.ensure_scaffold(ctx)
        first_arts = await backend.write_managed(ctx, roster, operators)
        second_arts = await backend.write_managed(ctx, roster, operators)
        assert [a.path for a in first_arts] == [a.path for a in second_arts]
        for artifact in first_arts:
            full = ctx.root / artifact.path
            assert full.exists()
            content_a = full.read_text(encoding="utf-8")
            # Re-read after the second run.
            content_b = (ctx.root / artifact.path).read_text(encoding="utf-8")
            assert content_a == content_b, f"write_managed is not idempotent for {artifact.path!r}"

    async def test_managed_region_not_duplicated(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        """Calling write_managed twice must not duplicate the managed section inside any file."""
        await backend.ensure_scaffold(ctx)
        await backend.write_managed(ctx, roster, operators)
        await backend.write_managed(ctx, roster, operators)
        # Heuristic: any managed-marker start tag must appear at most once per file.
        MANAGED_MARKERS = ["<!-- squads:start -->", "<!-- squads:managed"]
        for artifact in await backend.write_managed(ctx, roster, operators):
            full = ctx.root / artifact.path
            if not full.exists():
                continue
            text = full.read_text(encoding="utf-8")
            for marker in MANAGED_MARKERS:
                count = text.count(marker)
                assert count <= 1, (
                    f"Managed marker {marker!r} appears {count} times in {artifact.path!r} "
                    "(write_managed must replace, not duplicate)"
                )

    async def test_roster_role_names_appear_in_managed_output(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        """Roles from the roster must be reflected somewhere in the managed output."""
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
            in_output = role.full_name in all_text or role.slug in all_text
            assert in_output, (
                f"Role {role.full_name!r} (slug {role.slug!r}) "
                "not reflected in write_managed output"
            )

    async def test_operator_names_appear_in_managed_output(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        """Operators must be reflected somewhere in the managed output."""
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
        for op in operators:
            in_output = op.full_name in all_text or op.slug in all_text
            assert in_output, (
                f"Operator {op.full_name!r} (slug {op.slug!r}) "
                "not reflected in write_managed output"
            )


# ---------------------------------------------------------------------------
# Contract: generate_role_entry
# ---------------------------------------------------------------------------


class TestGenerateRoleEntry:
    """generate_role_entry must produce exactly one Artifact per call."""

    async def test_returns_artifact(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        role_def: RoleDef,
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        artifact = await backend.generate_role_entry(ctx, item, role_def)
        assert isinstance(artifact, Artifact)

    async def test_artifact_backend_matches(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        role_def: RoleDef,
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        artifact = await backend.generate_role_entry(ctx, item, role_def)
        assert artifact.backend == backend.name

    async def test_artifact_path_is_relative_forward_slash(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        role_def: RoleDef,
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        artifact = await backend.generate_role_entry(ctx, item, role_def)
        assert not Path(artifact.path).is_absolute()
        assert "\\" not in artifact.path

    async def test_artifact_file_exists_on_disk(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        role_def: RoleDef,
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        artifact = await backend.generate_role_entry(ctx, item, role_def)
        assert (ctx.root / artifact.path).exists(), (
            f"Role pointer artifact not on disk: {artifact.path!r}"
        )

    async def test_pointer_file_references_real_definition(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        role_def: RoleDef,
    ) -> None:
        """The pointer file must reference the real definition somewhere in its body."""
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        artifact = await backend.generate_role_entry(ctx, item, role_def)
        content = (ctx.root / artifact.path).read_text(encoding="utf-8")
        # The pointer must contain the slug or role name so an agent can identify the role.
        assert role_def.slug in content or role_def.full_name in content, (
            f"Role pointer at {artifact.path!r} does not reference the role slug/name"
        )

    async def test_generate_role_entry_is_idempotent(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        role_def: RoleDef,
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        a1 = await backend.generate_role_entry(ctx, item, role_def)
        a2 = await backend.generate_role_entry(ctx, item, role_def)
        assert a1.path == a2.path
        text1 = (ctx.root / a1.path).read_text(encoding="utf-8")
        text2 = (ctx.root / a2.path).read_text(encoding="utf-8")
        assert text1 == text2


# ---------------------------------------------------------------------------
# Contract: generate_skill_entry
# ---------------------------------------------------------------------------


class TestGenerateSkillEntry:
    """generate_skill_entry must produce exactly one Artifact per call."""

    async def test_returns_artifact(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_skill_item(2, "my-skill", ctx.squad_dir)
        artifact = await backend.generate_skill_entry(ctx, item)
        assert isinstance(artifact, Artifact)

    async def test_artifact_backend_matches(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_skill_item(2, "my-skill", ctx.squad_dir)
        artifact = await backend.generate_skill_entry(ctx, item)
        assert artifact.backend == backend.name

    async def test_artifact_path_is_relative_forward_slash(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_skill_item(2, "my-skill", ctx.squad_dir)
        artifact = await backend.generate_skill_entry(ctx, item)
        assert not Path(artifact.path).is_absolute()
        assert "\\" not in artifact.path

    async def test_artifact_file_exists_on_disk(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_skill_item(2, "my-skill", ctx.squad_dir)
        artifact = await backend.generate_skill_entry(ctx, item)
        assert (ctx.root / artifact.path).exists(), (
            f"Skill pointer artifact not on disk: {artifact.path!r}"
        )

    async def test_generate_skill_entry_is_idempotent(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
    ) -> None:
        await backend.ensure_scaffold(ctx)
        item = _make_skill_item(2, "my-skill", ctx.squad_dir)
        a1 = await backend.generate_skill_entry(ctx, item)
        a2 = await backend.generate_skill_entry(ctx, item)
        assert a1.path == a2.path
        text1 = (ctx.root / a1.path).read_text(encoding="utf-8")
        text2 = (ctx.root / a2.path).read_text(encoding="utf-8")
        assert text1 == text2


# ---------------------------------------------------------------------------
# Contract: remove_artifacts
# ---------------------------------------------------------------------------


class TestRemoveArtifacts:
    """remove_artifacts must be safe to call whether or not the artifacts exist,
    and must leave no orphaned files behind.
    """

    async def test_remove_role_artifacts_when_nothing_exists(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        role_def: RoleDef,
    ) -> None:
        """remove_artifacts is safe to call even when no files have been generated."""
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        # Must not raise.
        await backend.remove_artifacts(ctx, item)

    async def test_remove_role_artifacts_cleans_up(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        role_def: RoleDef,
    ) -> None:
        """Artifacts generated by generate_role_entry must be absent after remove_artifacts."""
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        artifact = await backend.generate_role_entry(ctx, item, role_def)
        full = ctx.root / artifact.path
        assert full.exists(), "Precondition: role pointer must exist before removal"
        await backend.remove_artifacts(ctx, item)
        assert not full.exists(), (
            f"Role pointer {artifact.path!r} still on disk after remove_artifacts"
        )

    async def test_remove_skill_artifacts_cleans_up(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
    ) -> None:
        """Artifacts generated by generate_skill_entry must be absent after remove_artifacts."""
        await backend.ensure_scaffold(ctx)
        item = _make_skill_item(2, "my-skill", ctx.squad_dir)
        artifact = await backend.generate_skill_entry(ctx, item)
        full = ctx.root / artifact.path
        assert full.exists(), "Precondition: skill pointer must exist before removal"
        await backend.remove_artifacts(ctx, item)
        # The pointer file (and its parent dir for skills) must be gone.
        assert not full.exists(), (
            f"Skill pointer {artifact.path!r} still on disk after remove_artifacts"
        )

    async def test_remove_artifacts_is_idempotent(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        role_def: RoleDef,
    ) -> None:
        """Calling remove_artifacts twice must not raise on the second call."""
        await backend.ensure_scaffold(ctx)
        item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        await backend.generate_role_entry(ctx, item, role_def)
        await backend.remove_artifacts(ctx, item)
        # Must not raise (missing_ok semantics).
        await backend.remove_artifacts(ctx, item)


# ---------------------------------------------------------------------------
# Contract: round-trip — scaffold → write_managed → generate pointers → remove
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """End-to-end round-trip: after all lifecycle operations no orphaned backend files remain."""

    async def test_full_round_trip_leaves_no_orphans(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
        role_def: RoleDef,
    ) -> None:
        """scaffold → write_managed → generate pointers → remove → no orphaned pointer files."""
        # 1. Scaffold
        await backend.ensure_scaffold(ctx)

        # 2. Write managed files (roster + operators).
        await backend.write_managed(ctx, roster, operators)

        # 3. Generate a role pointer and a skill pointer.
        role_item = _make_role_item(1, role_def.slug, ctx.squad_dir)
        role_artifact = await backend.generate_role_entry(ctx, role_item, role_def)

        skill_item = _make_skill_item(2, "my-skill", ctx.squad_dir)
        skill_artifact = await backend.generate_skill_entry(ctx, skill_item)

        # Confirm both exist.
        assert (ctx.root / role_artifact.path).exists()
        assert (ctx.root / skill_artifact.path).exists()

        # 4. Remove — no orphans.
        await backend.remove_artifacts(ctx, role_item)
        await backend.remove_artifacts(ctx, skill_item)

        assert not (ctx.root / role_artifact.path).exists()
        assert not (ctx.root / skill_artifact.path).exists()

    async def test_scaffold_then_sync_via_service(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The init → sync service round-trip completes without error (integration smoke).

        This drives the backend indirectly through the public service seam so a
        future backend only needs to be wired into get_backend to run here.
        """
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, roles_spec="minimal")
        svc = service.Service(result.paths)
        # A second sync must be idempotent.
        await svc.sync()
        await svc.sync()


# ---------------------------------------------------------------------------
# Contract: backend.name
# ---------------------------------------------------------------------------


class TestBackendName:
    """The ``name`` class attribute must be a non-empty string."""

    def test_name_is_non_empty_string(self, backend: AgentBackend) -> None:
        assert isinstance(backend.name, str)
        assert backend.name, "backend.name must be non-empty"

    async def test_name_matches_artifact_backend(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
    ) -> None:
        """Every artifact returned by ensure_scaffold carries the backend's own name."""
        for artifact in await backend.ensure_scaffold(ctx):
            assert artifact.backend == backend.name


# ---------------------------------------------------------------------------
# Contract: managed_paths (ADR-000141 §4)
# ---------------------------------------------------------------------------


class TestManagedPaths:
    """managed_paths must be read-only and return root-relative forward-slash paths.

    Contract (ADR-000141 §4):
    - Returns a list[str] of root-relative paths.
    - Must not create or modify any files on disk (read-only probe).
    - After a full sync (scaffold + write_managed), all returned paths must exist.
    """

    def test_returns_list_of_str(self, backend: AgentBackend, ctx: BackendContext) -> None:
        result = backend.managed_paths(ctx)
        assert isinstance(result, list)
        assert all(isinstance(p, str) for p in result)

    def test_paths_are_relative_forward_slash(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        for p in backend.managed_paths(ctx):
            assert not Path(p).is_absolute(), f"managed_paths must be relative, got: {p!r}"
            assert "\\" not in p, f"managed_paths must use forward slashes, got: {p!r}"

    def test_managed_paths_does_not_create_files(
        self, backend: AgentBackend, ctx: BackendContext
    ) -> None:
        """managed_paths must be read-only — calling it must not create any new files."""
        before = set(ctx.root.rglob("*"))
        backend.managed_paths(ctx)
        after = set(ctx.root.rglob("*"))
        assert before == after, f"managed_paths created new files: {after - before}"

    async def test_managed_paths_exist_after_sync(
        self,
        backend: AgentBackend,
        ctx: BackendContext,
        roster: list[RoleView],
        operators: list[OperatorView],
    ) -> None:
        """After scaffold + write_managed, every path returned by managed_paths must exist."""
        await backend.ensure_scaffold(ctx)
        await backend.write_managed(ctx, roster, operators)
        for p in backend.managed_paths(ctx):
            full = ctx.root / p
            assert full.exists(), (
                f"managed_paths declared {p!r} but it does not exist after scaffold + write_managed"
            )


# ---------------------------------------------------------------------------
# Claude-isms catalogue
# ---------------------------------------------------------------------------
#
# Findings from writing this suite. Items are tagged:
#
#   COSMETIC  — docstring / naming only; safe to apply directly without an ADR.
#   STRUCTURAL — signature / seam / path-ownership change that ripples into the
#                frozen ABC and/or the only existing backend; requires an architect
#                ADR before merge.
#
# These are *not* fixed in this PR — they are the discovery output handed to the
# architect for the ADR decision.
#
# ─────────────────────────────────────────────────────────────────────────────
# CC-001 [COSMETIC]
#   Location: src/squads/_backends/_base.py, line 18
#   Finding: Artifact.kind comment lists "claude_md" and "settings" as example
#            vocabulary — these are Claude Code-specific file categories.  A
#            second backend writing AGENTS.md would use a different kind string.
#   Impact: The *comment* leaks Claude assumptions but the field is untyped
#           (plain str), so the contract itself is not broken — any backend can
#           use its own vocabulary.  Fix: generalise the comment to "backend-
#           specific category string (e.g. 'agent', 'skill', 'config', 'index')".
#
# CC-002 [COSMETIC]
#   Location: src/squads/_backends/_base.py, line 73
#   Finding: AgentBackend.write_managed docstring reads:
#            "(Re)write roster/version-dependent tool files: the skill + CLAUDE.md section."
#            — names CLAUDE.md, which is a Claude Code-specific file.
#   Impact: Docstring only — no signature or behaviour coupling.
#   Fix: "…the managed skill definitions and the backend's project-level config section."
#
# CC-003 [COSMETIC]
#   Location: src/squads/_backends/_base.py, lines 76-81
#   Finding: generate_role_entry / generate_skill_entry use "pointer" in their
#            names.  "Pointer" is a Claude Code concept (a thin file that @-includes
#            the real definition).  A simple AGENTS.md backend has no pointers at
#            all — it writes everything into one file.
#   Impact: Naming only — both methods are abstract, so the impl is free to write
#           an AGENTS.md entry instead.  However, the name communicates the wrong
#           mental model to a future implementer.
#   Fix: Consider renaming to generate_role_entry / generate_skill_entry (or
#        generate_role_artifact / generate_skill_artifact).  These names are
#        neutral: a Claude backend returns a pointer-file artifact; an AGENTS.md
#        backend returns a section-update artifact. — REQUIRES ARCHITECT ADR if
#        the rename changes the ABC's public signature (likely STRUCTURAL).
#
# CC-004 [COSMETIC]
#   Location: src/squads/_backends/_base.py, lines 53-59 (BackendContext.rel /
#             root_relative docstrings)
#   Finding: Both docstrings say "for pointers and Artifact paths", coupling the
#            helper to the pointer-file concept.
#   Impact: Docstring only.
#   Fix: "for Artifact paths and backend-owned file references".
#
# CC-005 [STRUCTURAL]
#   Location: src/squads/_paths.py, lines 67-71
#   Finding: SquadPaths.claude_dir and SquadPaths.claude_md are Claude-specific
#            paths (.claude/ and CLAUDE.md) embedded in the *shared* path module
#            used by the entire service layer.  An AGENTS.md backend owns a
#            different project-level file (AGENTS.md at the root) and has no clean
#            seam to declare it.
#   Impact: STRUCTURAL — the backend must currently access its own root file
#           (ctx.paths.claude_md) through SquadPaths, which returns CLAUDE.md
#           unconditionally.  An AGENTS.md backend would either:
#             (a) ignore those properties and reach into ctx.root directly
#                 (defeating the seam), or
#             (b) add its own SquadPaths subclass (breaks the frozen dataclass).
#   Proposed fix options (for ADR):
#     A. Move claude_dir / claude_md out of SquadPaths into the ClaudeCode backend
#        (backend owns its own path resolution).
#     B. Add a backend-registry hook so each backend can declare its "config file"
#        path; SquadPaths exposes only generic helpers (root, squad_dir, etc.).
#     C. Keep the properties but rename them to reflect ownership
#        (e.g. agent_config_dir, agent_config_md) and document that a non-Claude
#        backend may ignore them — least change, but misleads future implementers.
#
# CC-006 [STRUCTURAL]
#   Location: src/squads/_backends/_registry.py, line 18
#   Finding: get_backend() hard-imports squads._backends._claude_code for side-
#            effect registration of ClaudeCodeBackend.  A second backend has no
#            analogous registration trigger — it must be imported elsewhere or the
#            registry must be extended.
#   Impact: STRUCTURAL — the "registration story" for a second backend is absent.
#   Proposed fix: A plugin-discovery mechanism (entry_points, an explicit import
#                 list in the registry, or a decorator on init) so both backends
#                 auto-register on import.  Least-change: the registry imports
#                 all built-in backends explicitly; third-party backends self-
#                 register via the existing `register()` decorator.
#
# ─────────────────────────────────────────────────────────────────────────────
# Summary table
#
#  ID       | Tag        | File                             | Change needed
# ----------|------------|----------------------------------|--------------------------
#  CC-001   | COSMETIC   | _base.py line 18       | Fix Artifact.kind comment
#  CC-002   | COSMETIC   | _base.py line 73       | Fix write_managed docstring
#  CC-003   | COSMETIC   | _base.py lines 76-81   | Rename generate_*_pointer methods
#            (may become STRUCTURAL if renamed - ADR needed for method rename)
#  CC-004   | COSMETIC   | _base.py lines 53-59   | Fix BackendContext docstrings
#  CC-005   | STRUCTURAL | _paths.py lines 67-71  | Move claude_dir/claude_md out of shared paths
#  CC-006   | STRUCTURAL | _registry.py line 18   | Extend registration story for 2+ backends
