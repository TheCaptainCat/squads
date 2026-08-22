"""``sq check``'s ``backend_reconciled`` rule widened to per-entry backend pointers
(one ``.claude/agents/<slug>.md``/``.claude/skills/<slug>/SKILL.md`` per live role/skill) —
not just each backend's fixed top-level file. ``agents_md`` declares no per-entry pointer at
all: its ``AgentBackend.managed_entry_paths`` override was removed once this backend stopped
staging one file per role/skill (see ``AgentsMdBackend``'s module docstring), so it never
contributes an entry to this rule's report — see ``test_agents_md_declares_no_per_entry_pointer``
below.

The hard constraint this whole rule turns on: the declared per-entry set is scoped to the
roster's *currently-live* entries (:func:`~squads._interactions.is_live_roster_entry`), never
a fixed or historical slug list, so a retire/reactivate cycle never produces a false positive
or a false negative on either side of the transition — the first test below drives exactly
that cycle end to end, not as a snapshot.

The reader every one of these is written against is a fresh clone, not a file this test
deleted by hand: `sq check` is a pure, present-only read of the filesystem
(``Path.exists()``), so it cannot distinguish "never written on this checkout" from "written,
then removed" — the two shapes are the same input to the rule, and are treated as such here
(see ``TestFreshCloneShape`` for the literal git-clone-style construction of the first, on top
of the deletion shape everywhere else).
"""

import shutil
from pathlib import Path

import pytest

from squads._services import _service as service
from squads._services._results import CheckIssue
from squads._services._validators import SQUAD_GLOBAL_CATALOG, SquadGlobalContext

pytestmark = pytest.mark.anyio


def _rule(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """The top-level-only half of the widened rule — ``backend_reconciled`` itself no longer
    reports a per-entry pointer directly (that claim is cross-source now: it reads the index
    as well as the disk), so this bypass is only valid for the error-level, disk+config-only
    checks below. Per-entry pointer behaviour is exercised through ``svc.check()`` instead,
    the same confirmed path a real ``sq check`` invocation takes — see ``_issues`` below."""
    return SQUAD_GLOBAL_CATALOG["backend_reconciled"](ctx)


async def _ctx(svc) -> SquadGlobalContext:
    index = await svc.store.load()
    return SquadGlobalContext(index=index, on_disk={}, spec=svc.spec, paths=svc.paths)


async def _issues(svc) -> list[CheckIssue]:
    """Per-entry pointer issues, driven through the real confirmed path
    (``svc.check()``) rather than calling ``backend_reconciled`` directly — that rule no
    longer produces them; they are candidates confirmed by ``check``'s own confirm round
    (see ``squads._services._validators.backend_entry_candidates``/``backend_entry_missing``).
    """
    return await svc.check()


@pytest.fixture
def tmp_squad(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --------------------------------------------------------------------------- the hard constraint


class TestRetirementCycleStaysClean:
    """The criterion that fails on a fix keyed on the wrong (fixed/historical) slug list —
    written first, per the task's own instruction."""

    async def test_activate_retire_reactivate_stays_clean_at_every_step(
        self, tmp_squad: Path
    ) -> None:
        result = await service.init(
            root=tmp_squad, backend=["claude_code", "agents_md"], roles_spec="minimal"
        )
        svc = service.Service(result.paths)

        item = await svc.activate_role("qa")
        assert (await svc.check()) == [] or not any(i.level == "error" for i in await svc.check())
        issues = await svc.check()
        assert not any("qa" in i.message and "missing" in i.message for i in issues), issues

        await svc.set_status(item.id, "Archived")
        issues = await svc.check()
        assert not any("qa" in i.message and "missing" in i.message for i in issues), (
            f"a retired role's absent pointer must not be reported: {issues}"
        )

        await svc.set_status(item.id, "Active")
        issues = await svc.check()
        assert not any("qa" in i.message and "missing" in i.message for i in issues), (
            f"reactivating must leave the pointer present and check clean: {issues}"
        )


# --- per-entry gap, both backends


class TestPerEntryPointerReported:
    async def test_missing_role_pointer_is_flagged_at_warn(self, tmp_squad: Path) -> None:
        result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
        svc = service.Service(result.paths)
        (tmp_squad / ".claude" / "agents" / "manager.md").unlink()

        issues = await _issues(svc)
        hit = next(i for i in issues if "manager.md" in i.item)
        assert hit.level == "warn"
        assert "claude_code" in hit.message

    async def test_missing_skill_pointer_is_flagged_at_warn(self, tmp_squad: Path) -> None:
        result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
        svc = service.Service(result.paths)
        await svc.sync()
        skills_dir = tmp_squad / ".claude" / "skills"
        one_skill = next(p for p in skills_dir.iterdir() if p.is_dir())
        shutil.rmtree(one_skill)

        issues = await _issues(svc)
        hit = next(i for i in issues if one_skill.name in i.item)
        assert hit.level == "warn"

    async def test_agents_md_declares_no_per_entry_pointer(self, tmp_squad: Path) -> None:
        """agents_md has no per-entry file at all any more (see ``AgentsMdBackend``'s module
        docstring): ``sq check`` never names one of its paths or reports it missing, whether
        or not a legacy ``.agents_md`` directory happens to exist on disk."""
        result = await service.init(root=tmp_squad, backend=["agents_md"], roles_spec="minimal")
        svc = service.Service(result.paths)
        await svc.activate_role("qa")

        issues = await _issues(svc)
        assert not any("agents_md" in i.message for i in issues)
        assert not any(".agents_md" in i.item for i in issues)

    async def test_whole_directory_loss_is_flagged_the_same_as_one_file(
        self, tmp_squad: Path
    ) -> None:
        result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
        svc = service.Service(result.paths)
        shutil.rmtree(tmp_squad / ".claude" / "agents")

        issues = await _issues(svc)
        assert any("manager.md" in i.item for i in issues)

    async def test_partial_loss_names_only_the_missing_entry(self, tmp_squad: Path) -> None:
        result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
        svc = service.Service(result.paths)
        await svc.activate_role("qa")
        (tmp_squad / ".claude" / "agents" / "qa.md").unlink()

        issues = await _issues(svc)
        missing = [i.item for i in issues if "missing" in i.message]
        assert any("qa.md" in m for m in missing)
        assert not any("manager.md" in m for m in missing)

    async def test_a_second_active_backend_with_no_per_entry_pointer_reports_nothing_extra(
        self, tmp_squad: Path
    ) -> None:
        """claude_code's missing pointer is still flagged with two backends active; agents_md
        — declaring no per-entry pointer at all — contributes nothing alongside it."""
        result = await service.init(
            root=tmp_squad, backend=["claude_code", "agents_md"], roles_spec="minimal"
        )
        svc = service.Service(result.paths)
        (tmp_squad / ".claude" / "agents" / "manager.md").unlink()

        issues = await _issues(svc)
        hit = next(i for i in issues if "manager.md" in i.item)
        assert hit.level == "warn"
        assert "claude_code" in hit.message
        assert not any("agents_md" in i.message for i in issues)

    async def test_top_level_file_still_errors(self, tmp_squad: Path) -> None:
        """Regression guard: the widening must not soften the existing top-level contract."""
        result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
        svc = service.Service(result.paths)
        (tmp_squad / "CLAUDE.md").unlink()

        ctx = await _ctx(svc)
        issues = _rule(ctx)
        hit = next(i for i in issues if i.item.endswith("CLAUDE.md"))
        assert hit.level == "error"


class TestActiveBackendsScoping:
    async def test_no_active_backends_reports_nothing(self, tmp_squad: Path) -> None:
        result = await service.init(root=tmp_squad, backend=[], roles_spec="minimal")
        svc = service.Service(result.paths)
        ctx = await _ctx(svc)
        assert _rule(ctx) == []

    async def test_only_the_active_backend_is_probed(self, tmp_squad: Path) -> None:
        result = await service.init(
            root=tmp_squad, backend=["claude_code", "agents_md"], roles_spec="minimal"
        )
        (tmp_squad / ".claude" / "agents" / "manager.md").unlink()

        # Deactivate claude_code without touching the file — a still-configured-but-inactive
        # backend must not be probed at all.
        cfg = result.paths.config.model_copy(update={"active_backends": ["agents_md"]})
        (tmp_squad / ".squads.toml").write_text(cfg.to_toml(), encoding="utf-8")
        from squads._paths import resolve

        svc2 = service.Service(resolve())
        ctx = await _ctx(svc2)
        issues = _rule(ctx)
        assert not any("claude_code" in i.message for i in issues)


# --- second predicate clause


async def test_orphaned_skill_type_pointer_is_not_reported(tmp_squad: Path) -> None:
    """The second clause of ``is_live_roster_entry``: a live ``SKILL`` item whose slug no
    longer names a type the active spec declares is withdrawn deliberately (its pointer is
    genuinely absent), so it must never be reported as a missing pointer — its own dedicated
    ``sq check`` complaint (``_orphaned_skill_issues``) is the one that fires instead."""
    from squads._workflow import bundled_spec

    result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)
    await svc.seed_bundled_skills()
    pointer = tmp_squad / ".claude" / "skills" / "sq-guide"
    assert pointer.is_dir()

    kept = sorted(set(bundled_spec().items) - {"guide"})
    override_dir = result.paths.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(f"[selected]\nitems = {kept!r}\n", encoding="utf-8")

    from squads._services._service import open_service

    dropped_svc = open_service(dir_override=str(result.paths.squad_dir))
    await dropped_svc.sync()  # withdraws the now-orphaned skill's pointer
    assert not pointer.exists()

    ctx = await _ctx(dropped_svc)
    issues = _rule(ctx)
    assert not any("sq-guide" in i.item for i in issues), issues


# --------------------------------------------------------------------------- fresh-clone shape


class TestFreshCloneShape:
    async def test_never_written_reports_the_same_as_deleted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A checkout that never had a backend's directory at all (an adopter who gitignored
        it and cloned fresh) — built here by copying a synced squad *without* its ``.claude``
        directory, the same shape a real ``git clone`` of a gitignored repo would produce,
        rather than deleting a file this test just created."""
        origin = tmp_path / "origin"
        origin.mkdir()
        monkeypatch.chdir(origin)
        result = await service.init(root=origin, backend=["claude_code"], roles_spec="minimal")
        svc = service.Service(result.paths)
        await svc.activate_role("qa")

        clone = tmp_path / "clone"

        def _skip_claude_per_entry_dirs(src: str, names: list[str]) -> set[str]:
            # Only `.claude/agents` and `.claude/skills` — never `squads/agents`, the real
            # markdown items' own folder, which the clone must keep intact.
            if Path(src) == origin / ".claude":
                return {"agents", "skills"}
            return set()

        shutil.copytree(origin, clone, ignore=_skip_claude_per_entry_dirs)
        assert not (clone / ".claude" / "agents").exists()  # sanity: the clone never had it
        assert not (clone / ".claude" / "skills").exists()
        assert (clone / ".claude" / "settings.json").exists()

        monkeypatch.chdir(clone)
        from squads._paths import resolve

        clone_svc = service.Service(resolve())
        issues = await _issues(clone_svc)
        assert any("manager.md" in i.item and i.level == "warn" for i in issues)
        assert any("qa.md" in i.item and i.level == "warn" for i in issues)
        # The gitignored-per-entry-pointer shape must not fail this repo's/any adopter's gate.
        assert not any(i.level == "error" for i in issues)


# --------------------------------------------------------------------------- no new I/O


async def test_no_new_index_load(tmp_squad: Path) -> None:
    """The live set comes from ``ctx.index`` — already loaded by the caller — never a second
    ``store.load()`` from inside the rule itself."""
    result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)

    load_calls = 0
    orig_load = svc.store.load

    async def counted_load(**kwargs):
        nonlocal load_calls
        load_calls += 1
        return await orig_load(**kwargs)

    svc.store.load = counted_load  # type: ignore[method-assign]
    index = await svc.store.load()
    assert load_calls == 1
    ctx = SquadGlobalContext(index=index, on_disk={}, spec=svc.spec, paths=svc.paths)
    _rule(ctx)
    assert load_calls == 1, "backend_reconciled must not load the index itself"
