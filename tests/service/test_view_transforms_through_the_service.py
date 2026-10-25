"""View transforms end to end through the service: where an override file is found from, what an
override may declare, which tags yield data, and what ``sq check`` reports."""

import sys
from pathlib import Path

import pytest

from _helpers import create_item, make_service
from squads._errors import SquadsError
from squads._services._service import init, open_service
from squads._view_transforms import milestone_rollup
from squads._workflow import bundled_spec
from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME, load_workflow_spec

pytestmark = pytest.mark.anyio

_OVERRIDE = """
[views.milestone_rollup]
transform = { path = "transforms/t.py", function = "f" }
"""


def _write_override(squad_dir: Path, text: str) -> None:
    target = squad_dir / WORKFLOW_OVERRIDE_FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


async def _squad_with_transform(root: Path, marker: str) -> tuple[Path, str]:
    """A squad under *root* whose milestone rollup transform returns *marker*; returns the
    project root and the milestone's id."""
    root.mkdir(parents=True)  # noqa: ASYNC240
    result = await init(root=root, roles_spec="minimal", _skip_skill_seed=True)
    squad_dir = result.paths.squad_dir
    (squad_dir / ".overrides" / "transforms").mkdir(parents=True)
    (squad_dir / ".overrides" / "transforms" / "t.py").write_text(
        f"def f(source):\n    return {{'marker': {marker!r}}}\n"
    )
    _write_override(squad_dir, _OVERRIDE)
    milestone = (await create_item(make_service(result.paths), "milestone", "M")).item
    return root, milestone.id


async def test_an_override_transform_is_found_from_the_client_squad_not_the_process_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, mid = await _squad_with_transform(tmp_path / "project", "project")
    decoy, decoy_mid = await _squad_with_transform(tmp_path / "decoy", "decoy")
    (project / "src" / "deep").mkdir(parents=True)

    # The process runs in the decoy squad; the client is in a subdirectory of the project.
    monkeypatch.chdir(decoy)
    served = open_service(client_cwd=project / "src" / "deep")
    assert await served.view_data(mid) == {"milestone_rollup": {"marker": "project"}}

    # A second client of the same process gets its own squad's file.
    other = open_service(client_cwd=decoy)
    assert await other.view_data(decoy_mid) == {"milestone_rollup": {"marker": "decoy"}}
    assert not [name for name in sys.modules if name.startswith("_squads_view_transform_")]


async def test_a_transform_that_fails_stops_every_read_of_the_host_that_places_its_view(
    tmp_path: Path,
) -> None:
    project, mid = await _squad_with_transform(tmp_path / "project", "x")
    (project / "squads" / ".overrides" / "transforms" / "t.py").write_text(
        "def f(source):\n    raise ValueError('bad data')\n"
    )
    svc = open_service(client_cwd=project)
    with pytest.raises(SquadsError, match="bad data"):
        await svc.view_data(mid)
    with pytest.raises(SquadsError, match="bad data"):
        await svc.read_body(mid)
    assert await svc.read_stored_body(mid)  # the stored text is unaffected


async def test_check_reports_a_transform_defect_but_loading_the_spec_imports_nothing(
    tmp_path: Path,
) -> None:
    project, mid = await _squad_with_transform(tmp_path / "project", "x")
    touched = tmp_path / "imported"
    (project / "squads" / ".overrides" / "transforms" / "t.py").write_text(
        f"open({str(touched)!r}, 'w')\nraise RuntimeError('import time')\n"
    )
    svc = open_service(client_cwd=project)
    assert not touched.exists()
    assert (await svc.get(mid)).id == mid

    issues = await svc.check()

    found = [i for i in issues if i.item == "views.milestone_rollup.transform"]
    assert len(found) == 1 and found[0].level == "error" and "import time" in found[0].message


_REFUSED_OVERRIDES = [
    ('transform = { module = "squads._view_transforms", function = "f" }', "may not name `module`"),
    ('transform = { path = "t.py" }', "may not name `module`"),
    ('transform = { function = "f" }', "may not name `module`"),
]


@pytest.mark.parametrize(("declaration", "message"), _REFUSED_OVERRIDES)
def test_an_override_may_declare_a_path_transform_and_nothing_else(
    tmp_path: Path, declaration: str, message: str
) -> None:
    _write_override(tmp_path, f"[views.milestone_rollup]\n{declaration}\n")
    with pytest.raises(SquadsError, match=message):
        load_workflow_spec(squad_dir=tmp_path)


def test_an_override_path_replaces_the_bundled_module_and_a_splat_copy_keeps_it(
    tmp_path: Path,
) -> None:
    _write_override(
        tmp_path,
        '[views.milestone_rollup]\ntransform = { path = "t.py", function = "f" }\n'
        '[views.copy]\nsource = { kind = "ref", name = "targets" }\n'
        'transform = "$(views.milestone_rollup.transform)"\n',
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    replaced = spec.views["milestone_rollup"].transform
    assert replaced is not None and replaced.module is None and replaced.path == "t.py"

    _write_override(
        tmp_path,
        '[views.copy]\nsource = { kind = "ref", name = "targets" }\n'
        'transform = "$(views.milestone_rollup.transform)"\n',
    )
    copied = load_workflow_spec(squad_dir=tmp_path).views["copy"].transform
    assert copied is not None and copied.module == "squads._view_transforms"


def test_an_attribute_named_views_is_refused_at_load(tmp_path: Path) -> None:
    _write_override(tmp_path, '[items.task.attributes]\nviews = { kind = "str" }\n')
    with pytest.raises(SquadsError, match="views"):
        load_workflow_spec(squad_dir=tmp_path)


async def test_view_data_holds_only_enabled_resolvable_views_that_declare_a_transform(
    project, svc
) -> None:
    milestone = (await create_item(svc, "milestone", "M")).item
    task = (await create_item(svc, "task", "T")).item
    assert set(await svc.view_data(milestone.id)) == {"milestone_rollup"}
    assert await svc.view_data(task.id) == {}

    await svc.disable_view(milestone.id, "milestone_rollup")
    assert await svc.view_data(milestone.id) == {}


@pytest.mark.parametrize(
    ("statuses", "delivered", "outstanding", "settled"),
    [
        ([], [], [], []),
        ([("bug", "Open")], [], ["bug:Open"], []),
        ([("decision", "Accepted")], ["decision:Accepted"], [], []),
        ([("bug", "Cancelled")], [], [], ["bug:Cancelled"]),
    ],
)
def test_the_rollup_partitions_members_on_status_roles(
    statuses: list[tuple[str, str]],
    delivered: list[str],
    outstanding: list[str],
    settled: list[str],
) -> None:
    from squads import _clock as clock
    from squads._models._item import Item

    now = clock.now()
    members = [
        Item(
            sequence_id=10 - n,
            type=kind,
            title=f"m{n}",
            slug=f"m{n}",
            status=status,
            path="x.md",
            created_at=now,
            updated_at=now,
            prefix=kind.upper(),
        )
        for n, (kind, status) in enumerate(statuses)
    ]
    out = milestone_rollup(members, spec=bundled_spec())
    label = lambda rows: [f"{r['type']}:{r['status']}" for r in rows]  # noqa: E731
    assert (label(out["delivered"]), label(out["outstanding"]), label(out["settled"])) == (
        delivered,
        outstanding,
        settled,
    )
