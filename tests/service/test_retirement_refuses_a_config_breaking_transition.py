"""The roster retirement gate (``no_live_role``/``preloaded_skill``): a status transition that
would leave generated backend config structurally invalid is refused, ``--force`` never lifts
either clause, and ``--unlink`` is the one mechanised escape — severing exactly the edges the
refusing finding named and re-checking, never suppressing a refusal.

The gate is delta-scoped: it refuses only findings *this* transition introduces, never a
pre-existing violation. A squad already sitting in a broken state keeps every transition
available to it, the repairing ones included.

Companion to ``tests/unit/test_roster_config_integrity_predicates.py`` (the pure clause
predicates, exercised directly) and ``tests/service/test_check_flags_a_roster_entry_already_
config_invalid.py`` (the report-mode reporter for state that already exists). This module is the
third caller's shape: refusing a *transition*, not reporting a pre-existing one.
"""

import pytest

from _helpers import create_item
from squads._errors import ConfigIntegrityError, SquadsError
from squads._index._resolver import item_file
from squads._itemfile import update_frontmatter
from squads._models._item import make_ref
from squads._workflow import ROSTER_ROLE, bundled_spec
from squads._workflow._models import Lifecycle, StatusSpec, WorkflowSpec

pytestmark = pytest.mark.anyio


async def _hand_plant_status(svc, item_id: str, status: str) -> None:
    """Reach *status* directly, bypassing the retirement gate — the recorded-repro shape
    (``sq check``'s reporter tests use the same bypass) — while keeping the on-disk frontmatter
    in sync with the index, so a later real service call against the same item does not trip
    the skew guard against a file this bypass never touched."""
    async with svc.store.transaction() as db:
        item = db.get(item_id)
        assert item is not None
        base = item.model_copy(deep=True)
        item.status = status
        await update_frontmatter(item_file(svc.paths, item), item, base)


async def _hand_plant_refs(svc, item_id: str, refs: list[str]) -> None:
    """Same bypass as :func:`_hand_plant_status`, for a direct ``refs`` write."""
    async with svc.store.transaction() as db:
        item = db.get(item_id)
        assert item is not None
        base = item.model_copy(deep=True)
        item.refs = refs
        await update_frontmatter(item_file(svc.paths, item), item, base)


# --------------------------------------------------------------------------- no_live_role


async def test_no_live_role_refuses_retiring_the_last_live_role_while_a_backend_is_active(svc):
    manager = await svc.roster_item("role", "manager")

    with pytest.raises(ConfigIntegrityError, match="no role entry is live"):
        await svc.set_roster_status(manager.id, "Archived")


async def test_no_live_role_allows_retiring_the_last_live_role_with_no_active_backend(
    tmp_path, monkeypatch
):
    from squads._services import _service as service
    from squads._services._service import Service

    monkeypatch.chdir(tmp_path)
    result = await service.init(
        root=tmp_path, backend=[], roles_spec="minimal", _skip_skill_seed=True
    )
    no_backend_svc = Service(result.paths)
    manager = await no_backend_svc.roster_item("role", "manager")
    assert manager is not None

    outcome = await no_backend_svc.set_roster_status(manager.id, "Archived")

    assert outcome.item.status == "Archived"


async def test_no_live_role_allows_retiring_a_non_last_live_role(svc):
    await svc.activate_role("qa")
    qa = await svc.roster_item("role", "qa")

    outcome = await svc.set_roster_status(qa.id, "Archived")

    assert outcome.item.status == "Archived"


# --------------------------------------------------------------------------- default role: warn


async def test_retiring_the_default_role_is_no_longer_refused_and_warns_instead(svc):
    """The withdrawn ``no_default_role`` clause: the state is legitimate, so the transition
    succeeds — with a warning that the default-role designation was lost, never a refusal."""
    await svc.activate_role("qa")  # a second live role, so no_live_role is satisfied
    manager = await svc.roster_item("role", "manager")

    outcome = await svc.set_roster_status(manager.id, "Archived")

    assert outcome.item.status == "Archived"
    assert any("default-role designation" in w for w in outcome.warnings)
    assert any(manager.id in w for w in outcome.warnings)


async def test_no_warning_when_another_live_role_already_carries_the_default(svc):
    await svc.activate_role("qa")
    qa_role = await svc.roster_item("role", "qa")
    manager = await svc.roster_item("role", "manager")
    await svc.update(qa_role.id, set_extra={"is_default": "true"})
    await svc.update(manager.id, unset_extra=["is_default"])

    outcome = await svc.set_roster_status(manager.id, "Archived")

    assert outcome.item.status == "Archived"
    assert outcome.warnings == []


async def test_no_warning_retiring_a_role_that_never_carried_the_default(svc):
    await svc.activate_role("qa")
    qa = await svc.roster_item("role", "qa")

    outcome = await svc.set_roster_status(qa.id, "Archived")

    assert outcome.warnings == []


# --------------------------------------------------------------------------- preloaded_skill


async def test_preloaded_skill_refuses_retiring_a_custom_skill_still_scoped_to_a_live_role(svc):
    role = await svc.activate_role("qa")
    skill = await svc.add_skill("Custom Helper")
    await svc.link_role(skill.id, role.id)

    with pytest.raises(ConfigIntegrityError, match="scoped to live role"):
        await svc.set_roster_status(skill.id, "Archived")


async def test_preloaded_skill_refuses_retiring_a_type_implied_skill_and_names_a_real_remedy(
    svc,
):
    """A ``sq-<type>`` implication's remedy is real, now that it is resolved against the active
    spec rather than the bundled one on every request: reactivate the skill, or drop the
    implicating type."""
    await svc.activate_role("tech-lead")  # tech-lead's playbook interacts with task
    skill = await svc.add_skill("Sq Task")  # slug "sq-task" — matches task's implied skill name

    with pytest.raises(ConfigIntegrityError) as exc_info:
        await svc.set_roster_status(skill.id, "Archived")
    message = str(exc_info.value)
    assert "implied by declared type" in message
    assert "task" in message
    assert "make the skill live again" in message
    assert "drop the implicating type" in message


async def test_preloaded_skill_refuses_retiring_the_always_on_skill_with_no_remedy_offered(svc):
    await svc.seed_bundled_skills()
    squads_skill = await svc.roster_item("skill", "squads")

    with pytest.raises(ConfigIntegrityError) as exc_info:
        await svc.set_roster_status(squads_skill.id, "Archived")
    message = str(exc_info.value)
    assert "permanent floor" in message
    assert "no remedy" in message


async def test_preloaded_skill_reports_both_kinds_for_a_doubly_dependent_skill(svc):
    """A skill that is simultaneously scoped to a live role AND implied by a declared type
    names both dependencies, not just one."""
    role = await svc.activate_role("tech-lead")
    skill = await svc.add_skill("Sq Task")
    await svc.link_role(skill.id, role.id)

    with pytest.raises(ConfigIntegrityError) as exc_info:
        await svc.set_roster_status(skill.id, "Archived")
    message = str(exc_info.value)
    assert "scoped to live role" in message
    assert "implied by declared type" in message


# --------------------------------------------------------------------------- --force


async def test_force_does_not_override_no_live_role(svc):
    manager = await svc.roster_item("role", "manager")

    with pytest.raises(ConfigIntegrityError):
        await svc.set_roster_status(manager.id, "Archived", force=True)


async def test_force_does_not_override_preloaded_skill(svc):
    role = await svc.activate_role("qa")
    skill = await svc.add_skill("Custom Helper")
    await svc.link_role(skill.id, role.id)

    with pytest.raises(ConfigIntegrityError):
        await svc.set_roster_status(skill.id, "Archived", force=True)


async def test_force_combined_with_unlink_still_does_not_override_no_live_role(svc):
    manager = await svc.roster_item("role", "manager")

    with pytest.raises(ConfigIntegrityError):
        await svc.set_roster_status(manager.id, "Archived", force=True, unlink=True)


# --------------------------------------------------------------------------- operator / board


async def test_retiring_the_last_operator_is_never_refused(svc):
    op = await svc.add_operator("Solo Operator")

    outcome = await svc.set_roster_status(op.id, "Archived")

    assert outcome.item.status == "Archived"


async def test_retiring_an_operator_is_never_refused_even_in_an_already_broken_squad(svc):
    """No clause examines an operator, so an operator's own transition must proceed even when
    ``no_live_role`` is already violated for an unrelated reason — the exemption is
    unconditional, not merely true today because nothing else happens to be broken."""
    op = await svc.add_operator("Solo Operator")
    manager = await svc.roster_item("role", "manager")
    await _hand_plant_status(svc, manager.id, "Archived")  # already violated, unrelated to op

    outcome = await svc.set_roster_status(op.id, "Archived")

    assert outcome.item.status == "Archived"


async def test_operator_unlink_severs_nothing_even_with_a_stray_severable_kind_ref(svc):
    """The operator exemption sits *above* severance, not merely harmless because operators
    happen never to carry a severable-kind ref today. Hand-plant one (impossible through any
    real command) and prove it survives ``--unlink`` untouched."""
    op = await svc.add_operator("Solo Operator")
    role = await svc.roster_item("role", "manager")
    await _hand_plant_refs(svc, op.id, [make_ref(role.id, "scopes")])

    outcome = await svc.set_roster_status(op.id, "Archived", unlink=True)

    assert outcome.item.status == "Archived"
    assert outcome.severed == []
    assert await svc.refs_out(op.id) == [(role.id, "scopes")]


async def test_retiring_a_role_with_open_assigned_work_warns_and_proceeds(svc):
    await svc.activate_role("qa")
    task = (await create_item(svc, "task", "flaky test", assignee="qa")).item
    assert svc.spec.is_open(task.status)  # sanity: still open

    outcome = await svc.set_roster_status((await svc.roster_item("role", "qa")).id, "Archived")

    assert outcome.item.status == "Archived"  # proceeds despite the open work
    assert any(task.id in w for w in outcome.warnings)


async def test_retiring_a_role_with_no_open_assigned_work_carries_no_warning(svc):
    await svc.activate_role("qa")

    outcome = await svc.set_roster_status((await svc.roster_item("role", "qa")).id, "Archived")

    assert outcome.warnings == []


# --------------------------------------------------------------------------- --unlink


async def test_unlink_severs_a_scopes_edge_and_the_transition_succeeds_on_its_own_merits(svc):
    role = await svc.activate_role("qa")
    skill = await svc.add_skill("Custom Helper")
    await svc.link_role(skill.id, role.id)

    outcome = await svc.set_roster_status(skill.id, "Archived", unlink=True)

    assert outcome.item.status == "Archived"
    assert len(outcome.severed) == 1
    assert outcome.severed[0].referrer == skill.id
    assert outcome.severed[0].target == role.id
    assert outcome.severed[0].kind == "scopes"
    assert await svc.refs_out(skill.id) == []


async def test_unlink_severs_only_the_refusing_clauses_edges_leaving_an_unrelated_one_intact(svc):
    """A custom skill scoped to two roles, one live and one already retired. The retired role's
    edge was never part of the dependency the clause refused on (only a *live* role's scoping
    counts) — ``--unlink`` must not touch it, and the retired role's own file must stay
    byte-identical."""
    live_role = await svc.activate_role("qa")
    retired_role = await svc.activate_role("devops")
    await svc.set_roster_status(retired_role.id, "Archived")
    skill = await svc.add_skill("Custom Helper")
    await svc.link_role(skill.id, live_role.id)
    await svc.link_role(skill.id, retired_role.id)
    retired_path = svc.paths.abspath((await svc.get(retired_role.id)).path)
    retired_before = retired_path.read_text(encoding="utf-8")

    outcome = await svc.set_roster_status(skill.id, "Archived", unlink=True)

    assert outcome.item.status == "Archived"
    assert len(outcome.severed) == 1
    assert outcome.severed[0].target == live_role.id
    remaining = await svc.refs_out(skill.id)
    assert remaining == [(retired_role.id, "scopes")]  # the retired role's edge survives
    assert retired_path.read_text(encoding="utf-8") == retired_before  # byte-identical


async def test_unlink_is_a_reported_no_op_when_nothing_is_severable(svc):
    skill = await svc.add_skill("Unscoped Helper")  # never linked to any role

    outcome = await svc.set_roster_status(skill.id, "Archived", unlink=True)

    assert outcome.item.status == "Archived"
    assert outcome.severed == []


async def test_unlink_still_refuses_no_live_role_which_has_no_severable_edge(svc):
    manager = await svc.roster_item("role", "manager")

    with pytest.raises(ConfigIntegrityError, match="no role entry is live"):
        await svc.set_roster_status(manager.id, "Archived", unlink=True)


async def test_unlink_on_a_non_retiring_transition_is_refused_as_meaningless(svc):
    role = await svc.activate_role("qa")
    await svc.set_roster_status(role.id, "Archived")

    with pytest.raises(ConfigIntegrityError) as exc_info:
        await svc.set_roster_status(role.id, "Active", unlink=True)

    message = str(exc_info.value)
    assert message == (
        f"--unlink is meaningless here: {role.id} is moving from 'Archived' to 'Active', "
        "which is not a move out of a live status — the flag only applies to a retirement"
    )
    assert "which is live" not in message  # the false claim the fix corrected


async def test_unlink_on_a_non_live_to_non_live_move_is_refused_as_meaningless(svc):
    """A retirement is a move *out of* a live status, not merely "the new status is not live"
    — a custom lifecycle with two non-live statuses must refuse ``--unlink`` on a move between
    them, since nothing is being retired."""
    base = bundled_spec()
    custom_lifecycles = {
        **base.lifecycles,
        "two_non_live": Lifecycle(
            initial="Active",
            transitions={
                "Active": ["Archived"],
                "Archived": ["Suspended"],
                "Suspended": [],
            },
        ),
    }
    custom_items = {
        **base.items,
        ROSTER_ROLE: base.items[ROSTER_ROLE].model_copy(update={"lifecycle": "two_non_live"}),
    }
    custom_statuses = {**base.statuses, "Suspended": StatusSpec(role="pending")}  # non-live
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
        }
    )
    assert custom_spec.live_statuses(ROSTER_ROLE) == frozenset({"Active"})

    from squads._services._service import Service

    custom_svc = Service(svc.paths, spec=custom_spec)
    await custom_svc.activate_role("qa")  # a second live role so no_live_role stays satisfied
    role = await custom_svc.roster_item("role", "qa")
    assert role is not None
    # Active -> Archived: a real retirement.
    await custom_svc.set_roster_status(role.id, "Archived")

    with pytest.raises(ConfigIntegrityError) as exc_info:
        # Archived -> Suspended: non-live to non-live, nothing is being retired.
        await custom_svc.set_roster_status(role.id, "Suspended", unlink=True)

    message = str(exc_info.value)
    assert message == (
        f"--unlink is meaningless here: {role.id} is moving from 'Archived' to 'Suspended', "
        "which is not a move out of a live status — the flag only applies to a retirement"
    )
    # 'Archived' is not live, and the message must not claim otherwise.
    assert "'Archived', which is live" not in message
    assert "not a move out of a live status" in message


async def test_unlink_severs_then_still_refuses_when_a_different_finding_remains(svc):
    """A skill that is BOTH scoped-edge (a stored ``scopes`` edge) and type-implied (a declared
    type's ``sq-<type>`` implication) at once: severing the scopes edge satisfies the
    scoped-edge reading, but the type implication is not a reference and stays refused. The
    whole transaction must abort, leaving the skill's own refs — the edge ``--unlink`` computed
    severing in memory — byte-identical to before the command."""
    role = await svc.activate_role("tech-lead")
    skill = await svc.add_skill("Sq Task")  # slug "sq-task" collides with task's implied name
    await svc.link_role(skill.id, role.id)
    before = svc.paths.abspath(skill.path).read_text(encoding="utf-8")

    with pytest.raises(ConfigIntegrityError, match="implied by declared type"):
        await svc.set_roster_status(skill.id, "Archived", unlink=True)

    after = svc.paths.abspath(skill.path).read_text(encoding="utf-8")
    assert after == before
    assert await svc.refs_out(skill.id) == [(role.id, "scopes")]  # never severed on disk


# ---------------------------------------------------------------------------------- delta scoping
#
# A pre-existing violation must never refuse an unrelated transition, and two co-existing
# violations must each be repairable independently.


async def test_an_already_broken_squad_still_allows_an_unrelated_transition(svc):
    """The recorded repro: a hand-planted archived foundation skill must not refuse an
    unrelated role's retirement."""
    await svc.seed_bundled_skills()
    await svc.activate_role("qa")
    squads_skill = await svc.roster_item("skill", "squads")
    await _hand_plant_status(svc, squads_skill.id, "Archived")  # pre-existing violation

    outcome = await svc.set_roster_status((await svc.roster_item("role", "qa")).id, "Archived")

    assert outcome.item.status == "Archived"


async def test_a_transition_that_repairs_the_only_violation_succeeds(svc):
    """A squad already violating ``preloaded_skill`` can still perform the transition that
    fixes it — reactivating the archived floor skill."""
    await svc.seed_bundled_skills()
    squads_skill = await svc.roster_item("skill", "squads")
    await _hand_plant_status(svc, squads_skill.id, "Archived")

    outcome = await svc.set_roster_status(squads_skill.id, "Active")

    assert outcome.item.status == "Active"


async def test_two_coexisting_violations_can_each_be_repaired_independently(svc):
    """Two unrelated pre-existing violations must not block each other's own repair."""
    await svc.seed_bundled_skills()
    greeting_skill = await svc.roster_item("skill", "greeting")
    memory_skill = await svc.roster_item("skill", "sq-memory")
    await _hand_plant_status(svc, greeting_skill.id, "Archived")
    await _hand_plant_status(svc, memory_skill.id, "Archived")

    outcome_1 = await svc.set_roster_status(greeting_skill.id, "Active")
    assert outcome_1.item.status == "Active"

    outcome_2 = await svc.set_roster_status(memory_skill.id, "Active")
    assert outcome_2.item.status == "Active"


async def test_a_shrinking_pre_existing_scoped_edge_violation_does_not_refuse_the_retirement(
    svc,
):
    """The delta compared whole ``ConfigIntegrityFinding`` objects, and ``message``/
    ``severable_targets`` both enumerate the currently-live scoping roles — so a pre-existing
    violation whose enumeration merely *shrinks* was a different object, absent from ``before``,
    and read as newly introduced. A skill archived while scoped to two live roles; retiring one
    of the two roles strictly reduces the violation (one fewer live role preloading a missing
    skill) and must not be refused for it."""
    live_role = await svc.activate_role("qa")
    other_role = await svc.roster_item("role", "manager")
    skill = await svc.add_skill("Custom Helper")
    await svc.link_role(skill.id, live_role.id)
    await svc.link_role(skill.id, other_role.id)
    await _hand_plant_status(svc, skill.id, "Archived")  # pre-existing: scoped to qa AND manager

    outcome = await svc.set_roster_status(live_role.id, "Archived")  # shrinks to manager alone

    assert outcome.item.status == "Archived"


async def test_a_growing_scoped_edge_violation_still_refuses_a_reactivation(svc):
    """The mirror of the shrinking case: reactivating a role that would newly preload an
    already-non-live scoped skill introduces a violation that did not exist before this
    transition, and must still be refused."""
    role = await svc.activate_role("qa")
    skill = await svc.add_skill("Custom Helper")
    await svc.link_role(skill.id, role.id)
    await svc.set_roster_status(role.id, "Archived")  # role retires first (skill still live)
    await svc.set_roster_status(skill.id, "Archived")  # skill retires (role already non-live)

    with pytest.raises(ConfigIntegrityError, match="scoped to live role"):
        await svc.set_roster_status(role.id, "Active")  # reactivation: growing violation


async def test_reactivation_scoped_edge_refusal_does_not_offer_the_meaningless_unlink_flag(svc):
    """The scoped-edge remedy was written for the retirement direction ("pass --unlink,
    or run ... first"), and the same finding is rendered on this reactivation, where the gate
    itself refuses ``--unlink`` as meaningless. The refusal must name only steps this command
    will actually accept."""
    role = await svc.activate_role("qa")
    skill = await svc.add_skill("Custom Helper")
    await svc.link_role(skill.id, role.id)
    await svc.set_roster_status(role.id, "Archived")
    await svc.set_roster_status(skill.id, "Archived")

    with pytest.raises(ConfigIntegrityError) as exc_info:
        await svc.set_roster_status(role.id, "Active")

    message = str(exc_info.value)
    assert message == (
        f"cannot move {role.id} to 'Active': the resulting projection would be structurally "
        "invalid:\n"
        f"- {skill.id}: not live (status 'Archived') but still scoped to live role(s): qa "
        "— remedy: sever the edge with `sq skill <addr> unlink-role <role>`, or reactivate "
        "the skill"
    )
    assert "--unlink" not in message


async def test_an_unrelated_pre_existing_scoped_edge_violation_does_not_block_another_retirement(
    svc,
):
    """Two different roles, each violating ``preloaded_skill`` in its own way (one already
    scoped to an archived custom skill); retiring a third, unrelated role must still succeed."""
    role_a = await svc.activate_role("qa")
    role_b = await svc.activate_role("devops")
    await svc.activate_role("tech-lead")  # a third live role, untouched by this transition
    skill = await svc.add_skill("Custom Helper")
    await svc.link_role(skill.id, role_a.id)
    await _hand_plant_status(svc, skill.id, "Archived")  # pre-existing preloaded_skill violation

    outcome = await svc.set_roster_status(role_b.id, "Archived")

    assert outcome.item.status == "Archived"
    # role_c stays untouched and available for a later assertion; the pre-existing violation
    # (skill still scoped to role_a) is unaffected by role_b's retirement.
    assert (await svc.roster_item("role", "tech-lead")).status == "Active"


# ------------------------------------------------------------- composed end-to-end message
#
# Every case above asserts a substring — a fragment of the condition, or a fragment of the
# remedy — which is exactly the gap that let a duplicated phrase through: each half read fine on
# its own. These assert the *whole* line a real refusal raises, end to end through the service
# (the same string the CLI prints via `error: {message}`), for every clause and every
# ``preloaded_skill`` kind — the composition, not just a fragment of it. No clause/kind
# identifier is ever printed.


async def test_no_live_role_composed_message_names_the_condition_and_the_remedy_exactly_once(svc):
    manager = await svc.roster_item("role", "manager")

    with pytest.raises(ConfigIntegrityError) as exc_info:
        await svc.set_roster_status(manager.id, "Archived")

    message = str(exc_info.value)
    assert message == (
        "cannot move ROLE-1 to 'Archived': the resulting projection would be structurally "
        "invalid:\n"
        "- ROLE-1: no role entry is live, but backend(s) claude_code are active — the "
        "generated config can present no agent — remedy: activate another role first"
    )
    assert message.count("remedy") == 1
    for label in ("no_live_role", "C1", "C2", "C3"):
        assert label not in message


async def test_scoped_edge_composed_message_names_the_condition_and_the_remedy_exactly_once(svc):
    role = await svc.activate_role("qa")
    skill = await svc.add_skill("Custom Helper")
    await svc.link_role(skill.id, role.id)

    with pytest.raises(ConfigIntegrityError) as exc_info:
        await svc.set_roster_status(skill.id, "Archived")

    message = str(exc_info.value)
    assert message == (
        f"cannot move {skill.id} to 'Archived': the resulting projection would be structurally "
        "invalid:\n"
        f"- {skill.id}: not live (status 'Archived') but still scoped to live role(s): qa "
        "— remedy: pass --unlink, or run `sq skill <addr> unlink-role <role>` first"
    )
    assert message.count("remedy") == 1
    for label in ("scoped_edge", "preloaded_skill", "C3"):
        assert label not in message


async def test_type_implied_composed_message_names_the_condition_and_the_remedy_exactly_once(svc):
    await svc.activate_role("tech-lead")  # tech-lead's playbook interacts with task
    skill = await svc.add_skill("Sq Task")  # slug "sq-task" — matches task's implied skill name

    with pytest.raises(ConfigIntegrityError) as exc_info:
        await svc.set_roster_status(skill.id, "Archived")

    message = str(exc_info.value)
    assert message == (
        f"cannot move {skill.id} to 'Archived': the resulting projection would be structurally "
        "invalid:\n"
        f"- {skill.id}: not live (status 'Archived') but implied by declared type(s): "
        "task — remedy: make the skill live again, or drop the implicating type via "
        "`[selected]` in .overrides/workflow.toml"
    )
    assert message.count("remedy") == 1


async def test_always_on_floor_composed_message_states_the_floor_once_with_no_remedy_line(svc):
    """The exact regression the coordinator caught driving this live: before the fix, this
    message repeated "a permanent floor of the roster contract" and followed "no remedy exists"
    with "remedy: none — this is a permanent floor of the roster contract". Now the condition
    states the fact once and nothing is appended, since there is nothing to append."""
    await svc.seed_bundled_skills()
    squads_skill = await svc.roster_item("skill", "squads")

    with pytest.raises(ConfigIntegrityError) as exc_info:
        await svc.set_roster_status(squads_skill.id, "Archived")

    message = str(exc_info.value)
    assert message == (
        f"cannot move {squads_skill.id} to 'Archived': the resulting projection would be "
        "structurally invalid:\n"
        f"- {squads_skill.id}: not live (status 'Archived') but every role preloads it "
        "unconditionally — a permanent floor of the roster contract; no remedy exists"
    )
    assert message.count("permanent floor of the roster contract") == 1
    assert message.count("remedy") == 1  # the one mention, inside "no remedy exists" — no tail
    assert "remedy:" not in message  # no dangling "remedy: <text>" clause was appended


async def test_doubly_dependent_composed_message_lists_both_findings_on_their_own_lines(svc):
    role = await svc.activate_role("tech-lead")
    skill = await svc.add_skill("Sq Task")
    await svc.link_role(skill.id, role.id)

    with pytest.raises(ConfigIntegrityError) as exc_info:
        await svc.set_roster_status(skill.id, "Archived")

    message = str(exc_info.value)
    lines = [line.strip() for line in message.splitlines() if line.strip().startswith("- ")]
    assert len(lines) == 2  # one finding per dependency, never collapsed to the "worst" one
    assert "scoped to live role" in lines[0]  # scoped_edge before type_implied (declared order)
    assert "implied by declared type" in lines[1]


# ------------------------------------------------------------------ one gated entry point


async def test_the_generic_update_seam_refuses_a_roster_status_change(svc):
    """There are two pure-half status-transition seams in the service
    (``_set_status_model``/``_update_model``) and only one evaluates the config-integrity
    clauses. ``Service.update(status=...)`` must refuse on a roster item rather than silently
    writing a status the gate never saw — the roster status axis has exactly one gated path."""
    role = await svc.roster_item("role", "manager")

    with pytest.raises(SquadsError, match="status cannot change through `update`"):
        await svc.update(role.id, status="Archived")

    still_manager = await svc.get(role.id)
    assert still_manager.status == "Active"


async def test_the_generic_update_seam_still_updates_a_roster_items_other_fields(svc):
    """The guard is scoped to ``status`` alone — every other metadata field on a roster item
    still updates normally through the generic seam."""
    role = await svc.roster_item("role", "manager")

    updated = await svc.update(role.id, description="A new description")

    assert updated.description == "A new description"
