"""`sq check` reports a roster entry that already sits in a config-invalid state — the
config-integrity clauses (C1-C3), evaluated against state already on disk rather than gating a
transition. The retirement gate now refuses each of these transitions interactively (see
``tests/service/test_retirement_refuses_a_config_breaking_transition.py``), so the invalid
states here are reached the way a real one would be: before the gate existed, or by any other
means that bypasses the service layer (a direct index write, mirroring
``tests/integration/test_check_detects_structural_corruption.py``'s pattern) — never through
``svc.set_status``, which would now correctly refuse them.
"""

from pathlib import Path

import pytest

from squads._services import _service as service
from squads._services._results import CheckIssue
from squads._services._service import Service
from squads._workflow import ROSTER_ROLE, bundled_spec
from squads._workflow._models import Lifecycle, StatusSpec, WorkflowSpec

pytestmark = pytest.mark.anyio


def _messages(issues: list[CheckIssue], needle: str) -> list[CheckIssue]:
    return [i for i in issues if needle in i.message]


async def test_check_flags_a_foundation_skill_archived_before_the_guard_existed(svc):
    """The recorded repro: a fresh squad's always-on skill sits Archived — reached by a direct
    index write since the interactive gate now refuses this transition — and the reporter must
    still catch the resulting config-invalid state."""
    await svc.seed_bundled_skills()
    squads_skill = await svc.roster_item("skill", "squads")
    assert squads_skill is not None

    async with svc.store.transaction() as db:
        db.items[squads_skill.sequence_id].status = "Archived"

    issues = await svc.check()
    hits = _messages(issues, "config integrity")
    assert any(i.item == squads_skill.id for i in hits)
    hit = next(i for i in hits if i.item == squads_skill.id)
    assert hit.level == "error"
    assert "permanent floor" in hit.message


async def test_check_reports_nothing_on_a_clean_freshly_seeded_squad(svc):
    await svc.seed_bundled_skills()
    issues = await svc.check()
    assert _messages(issues, "config integrity") == []


async def test_check_flags_a_type_implied_skill_archived_while_its_role_stays_live(svc):
    await svc.seed_bundled_skills()
    await svc.activate_role("tech-lead")  # tech-lead's playbook interacts with task
    sq_task = await svc.roster_item("skill", "sq-task")
    assert sq_task is not None

    async with svc.store.transaction() as db:
        db.items[sq_task.sequence_id].status = "Archived"

    issues = await svc.check()
    hits = _messages(issues, "config integrity")
    hit = next(i for i in hits if i.item == sq_task.id)
    assert "implied by declared type" in hit.message
    assert "task" in hit.message


async def test_check_flags_a_custom_skill_still_scoped_to_a_live_role(svc):
    role = await svc.roster_item("role", "manager")
    skill = await svc.add_skill("Custom Helper")
    await svc.link_role(skill.id, role.id)

    async with svc.store.transaction() as db:
        db.items[skill.sequence_id].status = "Archived"

    issues = await svc.check()
    hits = _messages(issues, "config integrity")
    hit = next(i for i in hits if i.item == skill.id)
    assert "scoped to live role" in hit.message
    assert "manager" in hit.message


async def test_check_suppresses_c1_when_no_backend_is_active(tmp_path: Path, monkeypatch):
    """With no roles at all and no active backend, C1 must stay silent — the sq-only squad is
    explicitly blessed and must not quietly get un-blessed by this validator."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, backend=[], roles_spec="", _skip_skill_seed=True)
    empty_backend_svc = Service(result.paths)

    issues = await empty_backend_svc.check()
    assert _messages(issues, "no role entry is live") == []


async def test_check_fires_c1_on_the_same_empty_roster_once_a_backend_is_active(
    tmp_path: Path, monkeypatch
):
    """The mirror of the previous case: same empty roster, but an active backend turns the
    absent live role into a real finding — proving the previous test's silence is because
    of the empty backend list, not because an empty roster is unconditionally exempt."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(
        root=tmp_path, backend=["claude_code"], roles_spec="", _skip_skill_seed=True
    )
    active_backend_svc = Service(result.paths)

    issues = await active_backend_svc.check()
    assert _messages(issues, "no role entry is live") != []


async def test_check_does_not_false_positive_c1_when_a_role_sits_on_a_second_live_status(svc):
    """A lifecycle may declare several live statuses at once. C1's cardinality check must
    test membership in that set, never equality against one status name, or a role parked on
    the *other* live status reads as retired."""
    base = bundled_spec()
    custom_lifecycles = {
        **base.lifecycles,
        "dual_live_agent": Lifecycle(
            initial="Active",
            transitions={"Active": ["OnCall", "Archived"], "OnCall": ["Archived"], "Archived": []},
        ),
    }
    custom_items = {
        **base.items,
        ROSTER_ROLE: base.items[ROSTER_ROLE].model_copy(update={"lifecycle": "dual_live_agent"}),
    }
    custom_statuses = {**base.statuses, "OnCall": StatusSpec(role="active")}  # also live
    custom_spec = WorkflowSpec.model_validate(
        {
            "items": custom_items,
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
    assert custom_spec.live_statuses(ROSTER_ROLE) == frozenset({"Active", "OnCall"})

    custom_svc = Service(svc.paths, spec=custom_spec)
    role = await custom_svc.roster_item("role", "manager")
    assert role is not None
    await custom_svc.set_status(role.id, "OnCall")  # the OTHER live status, not "Active"

    issues = await custom_svc.check()
    assert _messages(issues, "no role entry is live") == []
