"""Headline proof for the category axis: a brand-new type declared purely in an override
(own prefix/folder/lifecycle, ``category = "records"``) is fully spec-driven with **zero**
code change — create (incl. the records bundle's ``no_parent`` refusal), retype to/from a
work type, ``sq list``/``sq list --category records``/``sq tree``, and backend skill
generation all follow the same generic path a bundled records type (``decision``/``guide``)
already takes. A bundled-only squad's generated output is unaffected.
"""

from pathlib import Path

import pytest

from squads._paths import SquadPaths
from squads._sections import split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_POLICY_TOML = """\
[lifecycles.policy]
initial = "Draft"
[lifecycles.policy.transitions]
Draft = ["Active"]
Active = ["Superseded"]
Superseded = []

[items.policy]
prefix = "POL"
folder = "policies"
lifecycle = "policy"
aliases = ["pol"]
category = "records"
order = 65
"""


def _write_override(squad_dir: Path) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_POLICY_TOML, encoding="utf-8")


# --------------------------------------------------------------------------- CLI: create,
# no_parent refusal, list, tree


async def test_create_allocates_writes_frontmatter_and_lands_in_the_declared_folder(
    project, invoke
) -> None:
    _write_override(project.squad_dir)

    created = await invoke(["create", "policy", "Data retention", "--author", "manager"])
    assert created.exit_code == 0, created.output
    assert "POL-" in created.output

    policies_dir = project.squad_dir / "policies"
    assert policies_dir.is_dir()
    files = list(policies_dir.glob("POL-*.md"))
    assert files
    fm, _ = split_frontmatter(files[0].read_text(encoding="utf-8"))
    assert fm is not None and fm["type"] == "policy" and fm["status"] == "Draft"


async def test_create_refuses_a_parent_via_the_records_bundles_no_parent_rule(
    project, invoke
) -> None:
    _write_override(project.squad_dir)
    await invoke(["create", "task", "T", "--author", "manager"])

    result = await invoke(
        ["create", "policy", "Data retention", "--author", "manager", "--parent", "TASK-2"]
    )
    assert result.exit_code == 1
    assert "takes no parent" in result.output


async def test_list_and_tree_surface_the_new_type_including_the_category_filter(
    project, invoke
) -> None:
    _write_override(project.squad_dir)
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["create", "policy", "Data retention", "--author", "manager"])

    listed = await invoke(["list"])
    assert "POL-3" in listed.output

    by_category = await invoke(["list", "--category", "records"])
    assert "POL-3" in by_category.output and "TASK-2" not in by_category.output

    tree = await invoke(["tree", "--category", "records"])
    assert "POL-3" in tree.output and "TASK-2" not in tree.output


# --------------------------------------------------------------------------- CLI: retype
# across work <-> records


async def test_retype_to_and_from_a_work_type_both_succeed_when_unparented(project, invoke) -> None:
    _write_override(project.squad_dir)

    to_records = await invoke(["create", "task", "T", "--author", "manager"])
    assert to_records.exit_code == 0
    r1 = await invoke(["task", "2", "retype", "policy"])
    assert r1.exit_code == 0, r1.output
    assert "POL-2" in r1.output

    r2 = await invoke(["policy", "2", "retype", "task"])
    assert r2.exit_code == 0, r2.output
    assert "TASK-2" in r2.output


async def test_retype_a_parented_item_into_the_records_type_is_refused(project, invoke) -> None:
    _write_override(project.squad_dir)
    await invoke(["create", "feature", "F", "--author", "manager"])
    await invoke(["create", "task", "T", "--author", "manager", "--parent", "FEAT-2"])

    result = await invoke(["task", "3", "retype", "policy"])
    assert result.exit_code == 1
    assert "takes no parent" in result.output


# --------------------------------------------------------------------------- backend skill
# generation follows the generic (non-roster) path, no records-name special-casing


def _skill_pointer(paths: SquadPaths, slug: str) -> Path:
    return paths.root / ".claude" / "skills" / slug / "SKILL.md"


async def test_sync_generates_a_thin_skill_for_the_records_type_like_any_non_roster_type(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bundled").mkdir()
    (tmp_path / "override").mkdir()
    bundled_init = await service.init(root=tmp_path / "bundled", roles_spec="minimal")
    bundled_svc = service.Service(bundled_init.paths)
    await bundled_svc.sync()
    bundled_skill_names = {
        p.parent.name for p in (bundled_init.paths.root / ".claude" / "skills").glob("*/SKILL.md")
    }

    override_init = await service.init(root=tmp_path / "override", roles_spec="minimal")
    _write_override(override_init.paths.squad_dir)
    from squads._workflow._loader import load_workflow_spec

    spec = load_workflow_spec(squad_dir=override_init.paths.squad_dir)
    override_svc = service.Service(override_init.paths, spec=spec)
    await override_svc.sync()
    override_skill_names = {
        p.parent.name for p in (override_init.paths.root / ".claude" / "skills").glob("*/SKILL.md")
    }

    # The override squad has exactly one more skill: the new records type's own thin skill —
    # every bundled skill it already had stays untouched (no churn from the category axis).
    assert override_skill_names - bundled_skill_names == {"sq-policy"}
    assert bundled_skill_names <= override_skill_names

    pointer = _skill_pointer(override_init.paths, "sq-policy")
    assert pointer.is_file()
    fm, _ = split_frontmatter(pointer.read_text(encoding="utf-8"))
    assert fm is not None and fm.get("name") == "sq-policy"
