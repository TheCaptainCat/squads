"""``sq sync`` reports a per-entry backend pointer it had to regenerate — reporting only, no
write-path change (the previous silent regeneration behaviour is unchanged). The set of paths
that *should* exist is exactly the roster-scoped ``managed_entry_paths`` set ``sq check``'s
own ``backend_reconciled`` rule uses (see
``squads._backends._base.AgentBackend.managed_entry_paths``), so the two can never disagree
about which pointer belongs to which state.

The anti-chatty requirement is acceptance, not advice: a healthy sync's report list stays
empty, asserted directly (not only "the same text as before" — there is no "before" build to
diff against here, so the assertion is the same thing that text-diff would have shown: no
line at all on a clean squad).
"""

from pathlib import Path

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
def tmp_squad(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --------------------------------------------------------------------------- anti-chatty baseline


async def test_a_healthy_squad_reports_nothing(tmp_squad: Path) -> None:
    result = await service.init(
        root=tmp_squad, backend=["claude_code", "agents_md"], roles_spec="minimal"
    )
    svc = service.Service(result.paths)
    await svc.sync()  # the init-time sync already wrote everything

    notices = await svc.sync()
    assert notices == [], (
        "a sync over an already-healthy squad must report nothing — an implementation that "
        f"reports per entry unconditionally fails here: {notices}"
    )


# --- the regeneration report itself


class TestRegeneratedPointerIsReported:
    async def test_missing_role_pointer_is_reported_naming_file_and_backend(
        self, tmp_squad: Path
    ) -> None:
        result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
        svc = service.Service(result.paths)
        pointer = tmp_squad / ".claude" / "agents" / "manager.md"
        pointer.unlink()

        notices = await svc.sync()
        hit = next(n for n in notices if "manager.md" in n)
        assert "regenerated" in hit
        assert "claude_code" in hit
        assert pointer.exists()

    async def test_missing_skill_pointer_is_reported(self, tmp_squad: Path) -> None:
        import shutil

        result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
        svc = service.Service(result.paths)
        skills_dir = tmp_squad / ".claude" / "skills"
        one_skill = next(p for p in skills_dir.iterdir() if p.is_dir())
        shutil.rmtree(one_skill)

        notices = await svc.sync()
        assert any(one_skill.name in n and "regenerated" in n for n in notices)
        assert (one_skill / "SKILL.md").exists()

    async def test_agents_md_never_appears_in_the_regeneration_report(
        self, tmp_squad: Path
    ) -> None:
        """agents_md has no per-entry pointer at all any more (see ``AgentsMdBackend``'s
        module docstring): a sync over a squad using it — with or without a leftover
        ``.agents_md`` directory from a pre-upgrade version — never names it as regenerated."""
        result = await service.init(root=tmp_squad, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        leftover = tmp_squad / ".agents_md" / "roles" / "manager.md"
        leftover.parent.mkdir(parents=True, exist_ok=True)
        leftover.write_text("stale leftover from a pre-upgrade version\n", encoding="utf-8")

        notices = await svc.sync()
        assert not any("agents_md" in n for n in notices)
        assert not leftover.exists()

    async def test_partial_loss_names_only_the_missing_entry(self, tmp_squad: Path) -> None:
        result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
        svc = service.Service(result.paths)
        await svc.activate_role("qa")
        (tmp_squad / ".claude" / "agents" / "qa.md").unlink()

        notices = await svc.sync()
        regen = [n for n in notices if "regenerated" in n]
        assert any("qa.md" in n for n in regen)
        assert not any("manager.md" in n for n in regen)

    async def test_a_second_active_backend_with_no_per_entry_pointer_adds_nothing(
        self, tmp_squad: Path
    ) -> None:
        result = await service.init(
            root=tmp_squad, backend=["claude_code", "agents_md"], roles_spec="minimal"
        )
        svc = service.Service(result.paths)
        (tmp_squad / ".claude" / "agents" / "manager.md").unlink()

        notices = await svc.sync()
        regen = [n for n in notices if "regenerated" in n and "manager.md" in n]
        assert len(regen) == 1
        assert "claude_code" in regen[0]
        assert not any("agents_md" in n for n in notices)

    async def test_duplicate_suppression_one_line_per_missing_file(self, tmp_squad: Path) -> None:
        result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
        svc = service.Service(result.paths)
        (tmp_squad / ".claude" / "agents" / "manager.md").unlink()

        notices = await svc.sync()
        regen = [n for n in notices if "manager.md" in n and "regenerated" in n]
        assert len(regen) == 1


# --------------------------------------------------------------------------- exit code / CLI


async def test_cli_sync_exit_code_is_unchanged_while_reporting_a_regeneration(
    tmp_squad: Path, invoke
) -> None:
    await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
    (tmp_squad / ".claude" / "agents" / "manager.md").unlink()

    r = await invoke(["sync"])
    assert r.exit_code == 0, r.output
    assert "manager.md" in r.output
    assert "regenerated" in r.output.lower()


# --- retirement is never a fault


async def test_retire_sync_reactivate_sync_cycle_never_reports_the_retired_pointer(
    tmp_squad: Path,
) -> None:
    """A role's own status transition already materialises/withdraws its pointer immediately
    (``ServiceCore._project_roster_transition`` — a separate path from ``sync``), so by the
    time ``sync`` runs after either leg the pointer is already in the state it should be in
    and there is nothing to regenerate. This is the point being asserted: retirement is never
    a fault, and neither is a reactivation that has already happened before ``sync`` ran — see
    ``test_dropped_type_skill_orphan_is_withdrawn_and_flagged``-style tests for the shape where
    a reactivation *is* left for ``sync`` to discover (a dropped type's spec override reversed
    by hand, with no per-item transition to do the work first)."""
    result = await service.init(
        root=tmp_squad, backend=["claude_code", "agents_md"], roles_spec="minimal"
    )
    svc = service.Service(result.paths)
    item = await svc.activate_role("qa")
    await svc.sync()

    await svc.set_status(item.id, "Archived")
    notices = await svc.sync()
    assert not any("qa" in n and "regenerated" in n for n in notices), notices

    await svc.set_status(item.id, "Active")
    notices = await svc.sync()
    assert not any("qa" in n and "regenerated" in n for n in notices), notices


# --------------------------------------------------------------------------- fresh-clone shape


async def test_fresh_clone_shape_reports_the_whole_absent_roster_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A checkout that never had the per-entry pointers at all (an adopter who gitignored
    them and cloned fresh): the first ``sq sync`` on it reports what it created, one line per
    live role/skill, rather than treating a never-existed file as ordinary. This is
    proportionate, not the chatty case the anti-chatty test above guards against: it fires
    exactly once, on the one run that actually had work to do, and never again once the squad
    is healthy."""
    import shutil

    origin = tmp_path / "origin"
    origin.mkdir()
    monkeypatch.chdir(origin)
    result = await service.init(root=origin, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)
    await svc.activate_role("qa")
    await svc.sync()

    clone = tmp_path / "clone"

    def _skip_claude_agents_dir(src: str, names: list[str]) -> set[str]:
        # Only `.claude/agents` — leave `.claude/skills` alone so the expected regeneration
        # count below stays exactly the two live roles, deterministic across a roster whose
        # seeded-skill count is not this test's concern.
        if Path(src) == origin / ".claude":
            return {"agents"}
        return set()

    shutil.copytree(origin, clone, ignore=_skip_claude_agents_dir)
    assert not (clone / ".claude" / "agents").exists()
    assert (clone / ".claude" / "skills").exists()

    monkeypatch.chdir(clone)
    from squads._paths import resolve

    clone_svc = service.Service(resolve())
    notices = await clone_svc.sync()
    regen = [n for n in notices if "regenerated" in n]
    assert any("manager.md" in n for n in regen)
    assert any("qa.md" in n for n in regen)
    assert len(regen) == 2  # one per live role, not one per file-system write underneath

    # Healthy on the very next run.
    assert await clone_svc.sync() == []
