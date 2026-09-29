"""A newly created system or per-item-type skill under a dropped view seeds no dangling tag,
gated on ``self.spec.views`` the same way the repair-time classifier is."""

from pathlib import Path

import pytest

from squads import _sections as sections
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
    from ``views``."""
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
    """A newly created system skill under a dropped view also leaves its body empty."""
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


async def test_the_seed_and_a_real_body_write_produce_identical_bytes(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """The seed's bytes agree with a real writer's (``view add``), both through the same
    placement routine, never a hand-built tag string."""
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init_result.paths)
    await svc.seed_bundled_skills()

    seeded = await svc.roster_item("skill", "squads")
    assert seeded is not None
    seeded_bytes = item_file(svc.paths, seeded).read_text(encoding="utf-8")

    other = await svc.roster_item("skill", "sq-bug")
    assert other is not None
    path = item_file(svc.paths, other)
    path.write_text(
        sections.replace_section(path.read_text(encoding="utf-8"), markers.BODY, ""),
        encoding="utf-8",
    )
    placed = await svc.add_view(other.id, "item_skill")
    assert placed is True
    written_bytes = path.read_text(encoding="utf-8")

    assert get_section(seeded_bytes, markers.BODY) == (
        f"\n{markers.open_marker(markers.view_tag('squads_skill'))}\n"
    )
    assert get_section(written_bytes, markers.BODY) == (
        f"\n{markers.open_marker(markers.view_tag('item_skill'))}\n"
    )


async def test_the_seed_actually_calls_the_placement_routine(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """The seed actually calls the placement routine, not a hand-built tag string."""
    import squads._backends._claude_code._backend as backend_module

    calls: list[tuple[str, str | None, frozenset[str]]] = []
    original = backend_module.place_view_tags

    def spy(region, edit, **kw):
        calls.append((region, edit, kw["seeded"]))
        return original(region, edit, **kw)

    monkeypatch.setattr(backend_module, "place_view_tags", spy)
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(init_result.paths)

    await svc.seed_bundled_skills()

    assert calls, "the seed must call place_view_tags, not compose the tag itself"
    assert (
        "",
        None,
        frozenset({"squads_skill"}),
    ) in calls


async def test_a_newly_created_per_type_skill_under_a_declared_view_still_seeds_the_tag(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """The untouched path, with no view dropped, still seeds the tag exactly as before."""
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
    with `item_skill` and `role_definition` both dropped from `views`."""
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


async def test_repeated_skill_creation_under_a_dropped_view_adds_no_check_findings(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """Repeated skill creation under a dropped view adds no check findings; the skill-side
    count stays flat, unlike the role-side count, which is deliberate."""
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    base = load_workflow_spec()

    one_type = service.Service(init_result.paths, spec=_spec_with_types(base, "incident"))
    before = await one_type.check()
    dangling_before = [i for i in before if "no declared view" in i.message]
    skill_dangling_before = [i for i in dangling_before if "item_skill" in i.message]

    await one_type.activate_role("reviewer")
    await one_type.sync()
    after_one = await one_type.check()
    skill_dangling_after_one = [
        i for i in after_one if "no declared view" in i.message and "item_skill" in i.message
    ]
    assert len(skill_dangling_after_one) == len(skill_dangling_before)

    two_types = service.Service(
        init_result.paths, spec=_spec_with_types(base, "incident", "gadget")
    )
    await two_types.activate_role("qa")
    await two_types.sync()
    after_two = await two_types.check()
    skill_dangling_after_two = [
        i for i in after_two if "no declared view" in i.message and "item_skill" in i.message
    ]
    assert len(skill_dangling_after_two) == len(skill_dangling_before)
