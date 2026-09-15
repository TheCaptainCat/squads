"""``ClaudeCodeBackend``'s three system-skill and two per-item-type-skill call sites
(``write_managed``, ``_write_item_skills``), gated on ``self.spec.views`` the same way
``ServiceCore._create_core``'s role branch and ``MaintenanceMixin._repair_body_tag``'s
classifier already gate their own writers.

The declaration site names its own writers two lines above the constant
(``_interactions/__init__.py``'s ``SYSTEM_SKILL_VIEW_NAMES``/``ITEM_SKILL_VIEW_NAME``
docstrings: "the two writers this table is shared between") — the repair-time gate and the
role-creation gate cover one each, but the *skill* creation writer had no ``spec.views`` check
anywhere on its path: a newly created skill body under a dropped ``squads_skill``/
``greeting_skill``/``memory_skill``/``item_skill`` view minted a fresh dangling tag regardless,
so every skill a squad created after dropping the view grew ``sq check``'s error count by one.

Mirrors ``test_role_activation_seeds_no_tag_for_an_undeclared_view.py`` on the skill side.
"""

from pathlib import Path

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section
from squads._services import _service as service
from squads._workflow import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

pytestmark = pytest.mark.anyio

#: Drops `squads_skill` — one of the three permanently-system slugs — from the declared view
#: set. Every other bundled view stays selected, including `milestone_rollup`.
_DROP_SQUADS_SKILL = """\
[selected]
views = ["milestone_rollup", "role_definition", "greeting_skill", "memory_skill", "item_skill"]
"""


def _write_override(squad_dir: Path, content: str) -> None:
    from squads import __version__

    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


def _spec_with_incident_and_dropped_view(*, drop: str) -> WorkflowSpec:
    """The bundled spec plus a freshly-declared ``incident`` custom type, with *drop* removed
    from ``views`` — the exact shape ``[selected].views`` produces, built directly rather than
    through the TOML loader so the test controls precisely one variable."""
    base = load_workflow_spec()
    triage = Lifecycle(initial="Open", transitions={"Open": ["Done"], "Done": []})
    return WorkflowSpec.model_validate(
        {
            "items": {
                **base.items,
                "incident": ItemSpec(prefix="INC", folder="incidents", lifecycle="triage"),
            },
            "statuses": base.statuses,
            "lifecycles": {**base.lifecycles, "triage": triage},
            "prefix_to_type": {**base.prefix_to_type, "INC": "incident"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
            "roles": base.roles,
            "ref_kinds": base.ref_kinds,
            "views": {k: v for k, v in base.views.items() if k != drop},
        }
    )


def _skill_body(svc, item) -> str:
    path = item_file(svc.paths, item)
    return (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()


async def test_a_newly_created_per_type_skill_under_a_dropped_view_leaves_the_body_empty(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    spec = _spec_with_incident_and_dropped_view(drop="item_skill")
    declared = service.Service(init_result.paths, spec=spec)

    await declared.sync()

    skill = await declared.roster_item("skill", "sq-incident")
    assert skill is not None
    assert _skill_body(declared, skill) == "", (
        "skill creation seeded a tag naming a view the spec no longer declares"
    )


async def test_a_newly_created_system_skill_under_a_dropped_view_leaves_the_body_empty(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """The system-skill body must be genuinely new when this checks it — placing the override
    *before* ``init`` runs (rather than after, as the per-type test above does) is what makes
    that true: ``init``'s own scaffold step is what writes ``squads``/``greeting``/``memory``'s
    bodies for the first time, so it must see the dropped view too, or a later ``sync()`` would
    only be confirming the byte-untouched-on-an-existing-file guarantee, not this gate."""
    squad_dir = tmp_path / "squads"
    squad_dir.mkdir(parents=True)
    _write_override(squad_dir, _DROP_SQUADS_SKILL)
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    spec = load_workflow_spec(squad_dir=init_result.paths.squad_dir)
    assert "squads_skill" not in spec.views, "precondition: the override did not take effect"
    declared = service.Service(init_result.paths, spec=spec)
    await declared.seed_bundled_skills()

    skill = await declared.roster_item("skill", "squads")
    assert skill is not None
    assert _skill_body(declared, skill) == "", (
        "skill creation seeded a tag naming a view the spec no longer declares"
    )


async def test_a_newly_created_per_type_skill_under_a_declared_view_still_seeds_the_tag(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """Regression control: the untouched path — no view dropped — must still seed the tag
    exactly as before."""
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    base = load_workflow_spec()
    spec = WorkflowSpec.model_validate(
        {
            "items": {
                **base.items,
                "incident": ItemSpec(prefix="INC", folder="incidents", lifecycle="triage"),
            },
            "statuses": base.statuses,
            "lifecycles": {
                **base.lifecycles,
                "triage": Lifecycle(initial="Open", transitions={"Open": ["Done"], "Done": []}),
            },
            "prefix_to_type": {**base.prefix_to_type, "INC": "incident"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
            "roles": base.roles,
            "ref_kinds": base.ref_kinds,
            "views": base.views,
        }
    )
    declared = service.Service(init_result.paths, spec=spec)

    await declared.sync()

    skill = await declared.roster_item("skill", "sq-incident")
    assert skill is not None
    assert _skill_body(declared, skill) == markers.open_marker(markers.view_tag("item_skill"))


def _spec_with_types(base: WorkflowSpec, *type_names: str) -> WorkflowSpec:
    """*base* plus one freshly-declared triage-lifecycle custom type per name in *type_names*,
    with `item_skill` and `role_definition` both dropped from `views` — two views, so the
    role-side gate (already fixed) can serve as this test's own flat regression control
    alongside the skill-side one under test."""
    items = dict(base.items)
    prefix_to_type = dict(base.prefix_to_type)
    for name in type_names:
        items[name] = ItemSpec(prefix=name[:3].upper(), folder=f"{name}s", lifecycle="triage")
        prefix_to_type[name[:3].upper()] = name
    return WorkflowSpec.model_validate(
        {
            "items": items,
            "statuses": base.statuses,
            "lifecycles": {
                **base.lifecycles,
                "triage": Lifecycle(initial="Open", transitions={"Open": ["Done"], "Done": []}),
            },
            "prefix_to_type": prefix_to_type,
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
            "roles": base.roles,
            "ref_kinds": base.ref_kinds,
            "views": {
                k: v for k, v in base.views.items() if k not in ("item_skill", "role_definition")
            },
        }
    )


@pytest.mark.gate_for("squads/_backends/_claude_code/_backend.py::_write_managed_skill")
async def test_repeated_skill_creation_under_a_dropped_view_adds_no_check_findings(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """The reviewer's own repro, driven at the service layer: creating one skill under a
    dropped view must not add a fresh `sq check` finding, and creating a second must not add a
    second one — the count stays flat, not growing by one per skill created. The role-side
    control (a role activated under the same dropped `role_definition`) stays flat throughout
    too, proving this isn't a general degradation of `sq check` under this override."""
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    base = load_workflow_spec()

    one_type = service.Service(init_result.paths, spec=_spec_with_types(base, "incident"))
    before = await one_type.check()
    dangling_before = [i for i in before if "no declared view" in i.message]

    await one_type.activate_role("reviewer")
    await one_type.sync()  # creates sq-incident
    after_one = await one_type.check()
    dangling_after_one = [i for i in after_one if "no declared view" in i.message]
    assert len(dangling_after_one) == len(dangling_before)

    two_types = service.Service(
        init_result.paths, spec=_spec_with_types(base, "incident", "gadget")
    )
    await two_types.activate_role("qa")
    await two_types.sync()  # sq-incident already exists (idempotent); sq-gadget is new
    after_two = await two_types.check()
    dangling_after_two = [i for i in after_two if "no declared view" in i.message]
    assert len(dangling_after_two) == len(dangling_before)
