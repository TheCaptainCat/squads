"""``sq sync`` generates a thin ``sq-<type>`` skill for a custom type end to end: the body
carries the type's own auto-linearized lifecycle and standard verbs (no "For <role>" sections,
no dead sub-entity footer lines), a SKILL item is allocated idempotently and always after every
bundled skill (no churn of existing bundled ids), and the pointer file is written. A bundled-only
squad gets none of this.
"""

from pathlib import Path

import pytest

from squads._interactions import bundled_skill_slugs
from squads._sections import split_frontmatter
from squads._services import _service as service
from squads._workflow import linearize_lifecycle
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

pytestmark = pytest.mark.anyio

_INCIDENT_TOML = """\
[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done", "WontFix"]
Done = []
WontFix = ["Open"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
aliases = ["inc"]
"""


def _write_override(squad_dir: Path) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_INCIDENT_TOML, encoding="utf-8")


def _spec_with_incident() -> WorkflowSpec:
    base = load_workflow_spec()
    triage = Lifecycle(
        initial="Open", transitions={"Open": ["Done", "WontFix"], "Done": [], "WontFix": ["Open"]}
    )
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
        }
    )


def _skill_file(paths) -> Path:
    skills_folder = paths.squad_dir / "agents" / "skills"
    convention = list(skills_folder.glob("SKILL-*-sq-incident.md"))
    legacy = skills_folder / "sq-incident.md"
    if convention:
        return convention[0]
    assert legacy.is_file(), "sq-incident skill body file not found"
    return legacy


async def test_sync_generates_a_thin_skill_with_lifecycle_and_standard_verbs(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    spec = _spec_with_incident()
    svc = service.Service(paths, spec=spec)

    await svc.sync()

    skill_text = _skill_file(paths).read_text(encoding="utf-8")
    expected_lifecycle = linearize_lifecycle(spec.machine_for("incident"))
    assert expected_lifecycle in skill_text
    for verb in ("create", "show", "list", "update", "status", "ref", "comment", "body"):
        assert verb in skill_text
    assert "## For " not in skill_text  # sections=[] degrades to no role-specific sections


async def test_seed_custom_skills_allocates_an_idempotent_skill_id_after_every_bundled_one(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal")
    paths = init_result.paths
    spec = _spec_with_incident()
    svc = service.Service(paths, spec=spec)

    await svc.sync()
    after_first = {
        it.extra.get("slug"): it.sequence_id for it in await svc.list_items(item_type="skill")
    }
    assert after_first.get("sq-incident") is not None
    for bslug in bundled_skill_slugs():
        if bslug in after_first:
            assert after_first[bslug] < after_first["sq-incident"]

    await svc.sync()  # idempotent: no duplicate, no churn of bundled ids
    after_second = {
        it.extra.get("slug"): it.sequence_id for it in await svc.list_items(item_type="skill")
    }
    assert after_second == after_first


async def test_sync_writes_the_pointer_file_for_the_custom_skill(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    svc = service.Service(paths, spec=_spec_with_incident())

    await svc.sync()

    pointer_path = paths.root / ".claude" / "skills" / "sq-incident" / "SKILL.md"
    assert pointer_path.is_file()
    fm, _ = split_frontmatter(pointer_path.read_text(encoding="utf-8"))
    assert fm is not None and fm.get("name") == "sq-incident"


async def test_a_bundled_only_squad_gets_no_custom_skill_at_all(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    svc = service.Service(paths)  # bundled spec — no custom types

    await svc.sync()

    assert not list((paths.squad_dir / "agents" / "skills").glob("*incident*"))
    assert not (paths.root / ".claude" / "skills" / "sq-incident" / "SKILL.md").exists()


async def test_the_thin_skill_has_no_dead_subentity_footer_and_its_create_command_runs(
    invoke, tmp_path, monkeypatch, frozen_time
) -> None:
    """F4: a custom type declares no sub-entity kind, so the footer must not advertise ``<kind>
    <k> body``/``show`` verbs; and the ``sq create incident ...`` line it DOES advertise runs."""
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    _write_override(paths.squad_dir)

    spec = load_workflow_spec(squad_dir=paths.squad_dir)
    svc = service.Service(paths, spec=spec)
    await svc.sync()

    skill_text = _skill_file(paths).read_text(encoding="utf-8")
    assert "<kind> <k> body" not in skill_text
    assert "<kind> <k> show" not in skill_text
    assert "show --full --comments" in skill_text

    result = await invoke(["create", "incident", "Disk full alert", "--author", "manager"])
    assert result.exit_code == 0, result.output
    assert "INC-" in result.output and "INCIDENT-" not in result.output
