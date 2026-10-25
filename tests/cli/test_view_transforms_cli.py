"""The user-visible contract of an override view transform: found from ``-C``, reported by lint."""

import json
from pathlib import Path

import pytest

from _helpers import create_item, make_service

pytestmark = pytest.mark.anyio


async def _install_transform(project, source: str, declared: str = "transforms/t.py") -> str:
    overrides = project.squad_dir / ".overrides"
    (overrides / "transforms").mkdir(parents=True)
    (overrides / "transforms" / "t.py").write_text(source)
    (overrides / "workflow.toml").write_text(
        f'[views.milestone_rollup]\ntransform = {{ path = "{declared}", function = "f" }}\n'
    )
    return str((await create_item(make_service(project), "milestone", "M")).item.sequence_id)


async def test_dash_c_finds_the_transform_of_the_named_squad_not_the_working_directory(
    project, invoke, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    number = await _install_transform(project, "def f(source):\n    return {'marker': 'mine'}\n")
    decoy = tmp_path_factory.mktemp("decoy")
    (decoy / ".overrides" / "transforms").mkdir(parents=True)
    (decoy / ".overrides" / "transforms" / "t.py").write_text(
        "def f(source):\n    return {'marker': 'decoy'}\n"
    )
    monkeypatch.chdir(decoy)

    shown = await invoke(["-C", str(project.root), "milestone", number, "show", "--json"])

    assert shown.exit_code == 0, shown.output
    assert json.loads(shown.output)["views"] == {"milestone_rollup": {"marker": "mine"}}


async def test_lint_and_check_refuse_a_transform_that_escapes_the_overrides_folder(
    project, invoke, tmp_path: Path
) -> None:
    outside = tmp_path.parent / "outside_transform.py"
    outside.write_text("def f(source):\n    return {}\n")
    await _install_transform(project, "")
    link = project.squad_dir / ".overrides" / "transforms" / "t.py"
    link.unlink()
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"cannot create symlinks here: {exc}")

    await invoke(["override", "update", "workflow"])
    linted = await invoke(["workflow", "lint"])
    checked = await invoke(["check"])

    assert linted.exit_code == 1 and "outside" in linted.output
    assert "outside .overrides/" in " ".join(checked.output.split())
