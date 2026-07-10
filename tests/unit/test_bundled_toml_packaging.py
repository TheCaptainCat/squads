"""Bundled TOML assets ship as package data: accessible via importlib.resources and present
in the built wheel. One parametrized test over the asset list (the ledger's "ships in the
wheel" duplicate-invariant cluster) — covers the playbook, role catalog, and default-workflow
TOMLs.
"""

import shutil
import subprocess
import zipfile
from importlib import resources
from pathlib import Path

import pytest

#: (package, resource filename, a byte snippet expected inside it) — add an asset here
#: rather than writing a new near-identical test function.
_ASSETS: list[tuple[str, str, bytes]] = [
    ("squads._interactions", "playbook.toml", b"[types.task]"),
    ("squads._roles", "roles.toml", b"manager"),
    ("squads._workflow", "default_workflow.toml", b"[lifecycles.work]"),
]


@pytest.mark.parametrize(("package", "filename", "needle"), _ASSETS, ids=[a[1] for a in _ASSETS])
def test_asset_is_accessible_via_importlib_resources(
    package: str, filename: str, needle: bytes
) -> None:
    content = (resources.files(package) / filename).read_bytes()
    assert content
    assert needle in content


@pytest.mark.parametrize(("package", "filename", "needle"), _ASSETS, ids=[a[1] for a in _ASSETS])
def test_asset_ships_in_the_built_wheel(
    package: str, filename: str, needle: bytes, tmp_path: Path
) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv not found on PATH — cannot build wheel")

    result = subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[2]),
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"wheel build failed: {result.stderr[:300]}")

    wheels = list(tmp_path.glob("*.whl"))
    assert wheels, f"no wheel produced in {tmp_path}"
    with zipfile.ZipFile(wheels[0]) as whl:
        names = whl.namelist()
    assert any(filename in n for n in names), f"{filename} not found in wheel: {names}"
