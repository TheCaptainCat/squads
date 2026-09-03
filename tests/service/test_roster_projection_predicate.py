"""The materialisation predicate: a roster entry (role/skill) is materialised — its own backend
file(s) exist, and it is included in every managed region a backend compiles — if and only if
its status carries the ``live`` flag. Every other status is withdrawn through the existing
``AgentBackend.remove_artifacts``, the same method ``rm`` uses. Reactivation materialises again,
in full, through the same call path as first creation.

Also covers the per-caller projection audit: which of ``roster()``/``roster_all()`` a caller
takes is a correctness question, and this module falsifies it — each "full-set" caller is
asserted against a deliberately wrong (live-only) substitute to prove the test actually
catches the swap, not merely that the current code happens to pass.
"""

from pathlib import Path

import pytest

from squads._paths import SquadPaths
from squads._services import _service as service
from squads._workflow import bundled_spec
from squads._workflow._models import StatusSpec, WorkflowSpec

pytestmark = pytest.mark.anyio


def _pointer(project: SquadPaths, slug: str) -> Path:
    return project.root / ".claude" / "agents" / f"{slug}.md"


def _skill_pointer(project: SquadPaths, slug: str) -> Path:
    return project.root / ".claude" / "skills" / slug / "SKILL.md"


# --------------------------------------------------------------------------- materialise/withdraw


class TestMaterialiseWithdrawReactivate:
    async def test_activating_a_role_materialises_its_pointer(self, project, svc):
        await svc.activate_role("qa")
        assert _pointer(project, "qa").exists()

    async def test_retiring_a_role_withdraws_its_pointer_through_remove_artifacts(
        self, project, svc
    ):
        item = await svc.activate_role("qa")
        assert _pointer(project, "qa").exists()

        await svc.set_status(item.id, "Archived")
        assert not _pointer(project, "qa").exists()

    async def test_reactivating_a_retired_role_regenerates_the_pointer_in_full(self, project, svc):
        item = await svc.activate_role("qa")
        first = _pointer(project, "qa").read_text(encoding="utf-8")

        await svc.set_status(item.id, "Archived")
        assert not _pointer(project, "qa").exists()

        await svc.set_status(item.id, "Active")
        assert _pointer(project, "qa").exists()
        # Reactivation is the same call path as first creation, so the regenerated file is
        # byte-identical to what activation originally wrote (same inputs, same projection).
        assert _pointer(project, "qa").read_text(encoding="utf-8") == first

    async def test_retiring_a_skill_withdraws_its_pointer(self, project, svc):
        item = await svc.add_skill("my-skill")
        assert _skill_pointer(project, "my-skill").exists()

        await svc.set_status(item.id, "Archived")
        assert not _skill_pointer(project, "my-skill").exists()

    async def test_reactivating_a_retired_skill_regenerates_its_pointer(self, project, svc):
        item = await svc.add_skill("my-skill")
        await svc.set_status(item.id, "Archived")
        assert not _skill_pointer(project, "my-skill").exists()

        await svc.set_status(item.id, "Active")
        assert _skill_pointer(project, "my-skill").exists()

    async def test_a_retired_role_is_excluded_from_the_compiled_roster_table(self, project, svc):
        item = await svc.activate_role("qa")
        await svc.refresh_managed()  # the CLI's own post-activate step (svc.activate_role alone
        # does not recompile the managed regions, mirroring `sq role activate`'s two-step shape)
        claude_md_before = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Mara Tester" in claude_md_before

        await svc.set_status(item.id, "Archived")  # itself recompiles the managed regions
        claude_md_after = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Mara Tester" not in claude_md_after

    async def test_withdrawing_a_role_that_was_never_scaffolded_by_any_backend_is_a_clean_noop(
        self, project, svc
    ):
        """``remove_artifacts`` is missing-tolerant/idempotent by its own ABC contract — a
        retirement must not raise even against a backend with nothing to remove."""
        item = await svc.activate_role("qa")
        await svc.set_status(item.id, "Archived")
        assert not _pointer(project, "qa").exists()
        # A second retirement attempt (transitioning Archived -> Archived is refused by the
        # lifecycle itself, so exercise the ABC directly instead) must not raise.
        for backend in svc._backends():
            await backend.remove_artifacts(svc._ctx, await svc.get(item.id))
        assert not _pointer(project, "qa").exists()


class TestEmptyActiveBackendsProjectsNothing:
    async def test_retiring_and_reactivating_a_role_touches_no_files_and_does_not_raise(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        result = await service.init(root=tmp_path, backend=[], roles_spec="minimal")
        svc = service.Service(result.paths)
        item = await svc.activate_role("qa")
        assert not (tmp_path / ".claude").exists()

        await svc.set_status(item.id, "Archived")
        await svc.set_status(item.id, "Active")
        assert not (tmp_path / ".claude").exists()  # sq-only squad stays exactly that


# --------------------------------------------------------------------------- full-set callers


class TestCandidateOrphansUsesTheFullRoster:
    async def test_a_retired_roles_leftover_pointer_is_not_reported_as_an_orphan(
        self, project, svc
    ):
        item = await svc.activate_role("qa")
        pointer = _pointer(project, "qa")
        assert pointer.exists()
        await svc.set_status(item.id, "Archived")
        assert not pointer.exists()
        # Simulate the pre-upgrade state a squad already on disk could carry: a leftover
        # pointer for an entry this squad knows about but has since retired.
        pointer.write_text("stale leftover from before this landed\n", encoding="utf-8")

        orphans = await svc.candidate_orphans()
        assert not any("qa.md" in o for o in orphans)

    async def test_a_genuinely_unmanaged_file_is_still_reported_as_an_orphan(self, project, svc):
        stray = project.root / ".claude" / "agents" / "totally-unknown-slug.md"
        stray.write_text("nobody manages this\n", encoding="utf-8")
        orphans = await svc.candidate_orphans()
        assert any("totally-unknown-slug.md" in o for o in orphans)

    async def test_falsify_feeding_the_live_only_projection_misreports_the_retired_entry(
        self, project, svc
    ):
        """The wrong-projection assertion this contract is most in need of: swap
        ``roster_all()`` for the live-only ``roster()`` (the exact bug this predicate exists
        to prevent) and prove the retired entry's own leftover file gets misreported as a
        foreign orphan."""
        from squads._interactions import bundled_skill_slugs, custom_skill_slugs
        from squads._models._extras import ExtraKey as X

        item = await svc.activate_role("qa")
        pointer = _pointer(project, "qa")
        await svc.set_status(item.id, "Archived")
        pointer.write_text("stale leftover\n", encoding="utf-8")

        skill_items = await svc.list_items(item_type="skill")
        skill_slugs = (
            {it.extra[X.SLUG] for it in skill_items if X.SLUG in it.extra}
            | set(bundled_skill_slugs())
            | set(custom_skill_slugs(svc.spec))
        )
        wrong_roster = await svc.roster()  # WRONG: live-only, the bug under test
        ctx = svc._ctx
        wrong_orphans: list[str] = []
        for backend in svc._backends():
            wrong_orphans += await backend.candidate_orphans(ctx, wrong_roster, skill_slugs)
        assert any("qa.md" in o for o in wrong_orphans), (
            "the live-only projection was expected to misreport the retired role's own "
            "leftover file as an orphan — if this fails, the falsification no longer proves "
            "candidate_orphans needs the full roster"
        )

        # And the real (fixed) method must not make that mistake.
        real_orphans = await svc.candidate_orphans()
        assert not any("qa.md" in o for o in real_orphans)


class TestAuthorshipDisplayUsesTheFullRoster:
    async def test_a_retired_roles_display_name_still_renders(self, svc):
        item = await svc.activate_role("qa")
        await svc.set_status(item.id, "Archived")
        assert await svc.author("qa") == "Mara Tester"

    async def test_falsify_a_live_only_lookup_would_fall_back_to_the_bare_slug(self, svc):
        """Same falsification shape as the orphan test: prove that filtering to live-only
        loses the retired role's display name (falls back to the slug itself), then confirm
        the real accessor does not."""
        item = await svc.activate_role("qa")
        await svc.set_status(item.id, "Archived")

        db = await svc.store.load()
        live_slugs = {r.slug for r in await svc.roster()}
        assert "qa" not in live_slugs  # sanity: qa really is excluded from the live set

        wrong_name = next(
            (
                it.extra.get("full_name", "qa")
                for it in db.items.values()
                if it.type == "role" and it.extra.get("slug") == "qa" and it.status in {"Active"}
            ),
            "qa",  # falls back to the bare slug when filtered to live-only, as _author_of
        )
        assert wrong_name == "qa", "the live-only filter was expected to lose the display name"
        assert await svc.author("qa") == "Mara Tester"  # the real, full-set-reading accessor


class TestRegisteredSlugsUsesTheFullRoster:
    async def test_sq_check_does_not_warn_about_a_comment_from_a_since_retired_role(self, svc):
        item = await svc.activate_role("qa")
        await svc.comment(item.id, ["noted"], as_slug="qa")
        await svc.set_status(item.id, "Archived")

        issues = await svc.check()
        assert not any("qa" in i.message and "not a registered" in i.message for i in issues)


# --------------------------------------------------------------------------- sync convergence


class TestSyncIsTheConvergencePoint:
    async def test_sync_withdraws_a_leftover_pointer_for_an_entry_already_retired_before_landing(
        self, project, svc
    ):
        item = await svc.activate_role("qa")
        await svc.set_status(item.id, "Archived")
        pointer = _pointer(project, "qa")
        assert not pointer.exists()
        # Simulate the exact upgrade scenario: a squad that reached this retired state before
        # the projection wiring landed, so the withdrawal never happened.
        pointer.write_text("leftover from before this landed\n", encoding="utf-8")

        await svc.sync()
        assert not pointer.exists()

    async def test_sync_is_idempotent_on_an_already_converged_retired_entry(self, project, svc):
        item = await svc.activate_role("qa")
        await svc.set_status(item.id, "Archived")
        await svc.sync()
        await svc.sync()  # second run must not raise or resurrect anything
        assert not _pointer(project, "qa").exists()

    async def test_sync_keeps_materialising_a_live_role_on_every_run(self, project, svc):
        await svc.activate_role("qa")
        await svc.sync()
        assert _pointer(project, "qa").exists()
        await svc.sync()
        assert _pointer(project, "qa").exists()


# --------------------------------------------------------------- two-live-status lifecycle


def _dual_live_role_spec() -> WorkflowSpec:
    """A custom roster lifecycle declaring TWO live statuses (``Active``, ``Trialling``)
    reachable from each other, both settling into the same non-live ``Archived`` — so
    ``live_statuses("role")`` has no single answer, exactly the case a floor requiring only
    "at least one" live status (rather than "exactly one") opens up."""
    base = bundled_spec()
    custom_statuses = {**base.statuses, "Trialling": StatusSpec(role="active")}
    agent_lifecycle = base.lifecycles["agent"]
    custom_lifecycles = {
        **base.lifecycles,
        "agent": agent_lifecycle.model_copy(
            update={
                "transitions": {
                    "Active": ["Archived", "Trialling"],
                    "Trialling": ["Archived", "Active"],
                    "Archived": ["Active"],
                }
            }
        ),
    }
    return WorkflowSpec.model_validate(
        {
            "items": dict(base.items),
            "statuses": custom_statuses,
            "lifecycles": custom_lifecycles,
            "prefix_to_type": dict(base.prefix_to_type),
            "alias_to_type": dict(base.alias_to_type),
            "collections": dict(base.collections),
            "subentity_kinds": dict(base.subentity_kinds),
            "roles": dict(base.roles),
            "ref_kinds": dict(base.ref_kinds),
            "views": dict(base.views),
        }
    )


class TestTwoLiveStatusCustomLifecycle:
    async def test_the_spec_declares_two_live_statuses(self):
        spec = _dual_live_role_spec()
        assert spec.live_statuses("role") == {"Active", "Trialling"}

    async def test_both_live_statuses_materialise_and_only_the_settled_one_withdraws(self, project):
        svc = service.Service(project, spec=_dual_live_role_spec())
        item = await svc.activate_role("qa")
        pointer = _pointer(project, "qa")
        assert pointer.exists()

        await svc.set_status(item.id, "Trialling")
        assert pointer.exists()  # still live — must not be withdrawn

        await svc.set_status(item.id, "Archived")
        assert not pointer.exists()  # settled and non-live — withdrawn

        await svc.set_status(item.id, "Active")
        assert pointer.exists()  # reactivated


# ------------------------------------------------------ reactivation regenerates in full


class TestReactivationRestoresAScopedSkill:
    """The transition-time projection and ``sync``'s roster sweep are two callers of one
    materialise-or-withdraw predicate, and used to hand the backend two differently-populated
    contexts — the transition path's carried no resolved preload map at all, so a role's
    ``scopes``-derived skill silently vanished from its regenerated pointer on reactivation,
    only repaired by the next ``sq sync``. Both directions now go through the same helper,
    which requires its caller to hand it a context already carrying the whole roster's
    resolved map.

    Claude Code is the only bundled backend this property is driven against: its pointer is
    the one file a scoped skill's list is rendered into. ``agents_md`` has no per-entry file
    at all any more (see ``AgentsMdBackend``'s module docstring), so there is nothing for a
    resolved-skills regression to corrupt on that side — the earlier agents_md-specific
    regression test for this predicate no longer has a surface to exercise.
    """

    async def test_reactivating_a_role_restores_a_scoped_skill_with_no_sync_in_between(
        self, project, svc
    ):
        role = await svc.activate_role("qa")
        skill = await svc.add_skill("Custom Helper")
        await svc.link_role(skill.id, role.id)
        pointer = _pointer(project, "qa")
        assert "custom-helper" in pointer.read_text(encoding="utf-8")

        await svc.set_status(role.id, "Archived")
        assert not pointer.exists()

        await svc.set_status(role.id, "Active")  # reactivate — no `sq sync` anywhere in between
        assert "custom-helper" in pointer.read_text(encoding="utf-8"), (
            "reactivation must regenerate the pointer with its full preload list, same as "
            "first creation — a scoped skill silently vanishing is exactly the regression "
            "this test exists to catch"
        )

    async def test_falsify_an_empty_role_skills_context_loses_the_scoped_skill(self, project, svc):
        """Same falsification shape as the orphan/authorship tests above: reconstruct the
        exact wrong context the old transition path handed the backend
        (``BackendContext(paths=..., spec=...)`` with no ``role_skills`` at all) and prove it
        loses the scoped skill, before confirming the real reactivation path does not."""
        from squads._backends._base import BackendContext
        from squads._roles._catalog import RoleDef

        role = await svc.activate_role("qa")
        skill = await svc.add_skill("Custom Helper")
        await svc.link_role(skill.id, role.id)

        wrong_ctx = BackendContext(paths=svc.paths, spec=svc.spec)  # WRONG: no role_skills
        role_item = await svc.get(role.id)
        for backend in svc._backends():
            await backend.generate_role_entry(
                wrong_ctx, role_item, RoleDef.from_extra(role_item.extra)
            )
        assert "custom-helper" not in _pointer(project, "qa").read_text(encoding="utf-8"), (
            "an empty role_skills context was expected to lose the scoped skill — if this "
            "fails, the falsification no longer proves the fix needs the resolved map"
        )

        await svc.set_status(role.id, "Archived")
        await svc.set_status(role.id, "Active")  # the real (fixed) reactivation path
        assert "custom-helper" in _pointer(project, "qa").read_text(encoding="utf-8")

    async def test_the_reactivated_pointer_is_byte_identical_to_what_sync_writes_next(
        self, project, svc
    ):
        """Reactivation is the same call path as first creation, so a sync immediately
        afterwards must be a pure no-op — asserted on the actual bytes, rather than on a
        substring."""
        role = await svc.activate_role("qa")
        skill = await svc.add_skill("Custom Helper")
        await svc.link_role(skill.id, role.id)
        await svc.set_status(role.id, "Archived")
        await svc.set_status(role.id, "Active")

        pointer = _pointer(project, "qa")
        reactivated = pointer.read_text(encoding="utf-8")
        await svc.sync()
        assert pointer.read_text(encoding="utf-8") == reactivated

    async def test_reactivating_a_skill_entry_regenerates_in_full_too(self, project, svc):
        """A skill entry's own materialise call carries no role_skills dependency, but it
        must go through the same single helper, not a parallel implementation that happens
        to agree today."""
        skill = await svc.add_skill("Custom Helper")
        pointer = _skill_pointer(project, "custom-helper")
        first = pointer.read_text(encoding="utf-8")

        await svc.set_status(skill.id, "Archived")
        assert not pointer.exists()
        await svc.set_status(skill.id, "Active")
        assert pointer.read_text(encoding="utf-8") == first


class TestOperatorTransitionHasNoPerEntryFile:
    async def test_retiring_and_reactivating_an_operator_only_ever_touches_the_managed_region(
        self, project, svc
    ):
        op = await svc.add_operator("Alice Tester")
        await svc.refresh_managed()
        claude_md = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Alice Tester" in claude_md

        await svc.set_status(op.id, "Archived")  # no per-entry file exists to remove
        assert "Alice Tester" not in (project.root / "CLAUDE.md").read_text(encoding="utf-8")

        await svc.set_status(op.id, "Active")
        assert "Alice Tester" in (project.root / "CLAUDE.md").read_text(encoding="utf-8")
