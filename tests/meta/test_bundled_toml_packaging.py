"""Bundled TOML assets ship as package data: accessible via importlib.resources and present
in the built wheel at the path their own package implies. One parametrized test over the
asset list — covers the playbook, role catalog, and workflow TOMLs — rather than a
near-duplicate test per asset; the wheel itself is built exactly once per test session
(``built_wheel_names`` below) and every asset check reads that one manifest, since a wheel
build failure isn't asset-specific — rebuilding per asset would only slow the suite down,
not buy any real independence between the checks.
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
    ("squads._specs", "playbook.toml", b"[types.task]"),
    ("squads._specs", "roles.toml", b"manager"),
    ("squads._specs", "workflow.toml", b"[lifecycles.work]"),
]


@pytest.mark.parametrize(("package", "filename", "needle"), _ASSETS, ids=[a[1] for a in _ASSETS])
def test_asset_is_accessible_via_importlib_resources(
    package: str, filename: str, needle: bytes
) -> None:
    content = (resources.files(package) / filename).read_bytes()
    assert content
    assert needle in content


@pytest.fixture(scope="session")
def built_wheel_names(tmp_path_factory: pytest.TempPathFactory) -> list[str]:
    """Build the wheel once for the whole session and return its member names.

    A missing ``uv`` skips — a contributor without the toolchain installed is a legitimate,
    unrelated situation. A build that runs and fails is not: that means something is
    genuinely broken, so it fails the test rather than degrading to a skip.
    """
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv not found on PATH — cannot build wheel")

    out_dir = tmp_path_factory.mktemp("wheel")
    result = subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(out_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(Path(__file__).resolve().parents[2]),
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"wheel build failed (exit {result.returncode}): {result.stderr[:500]}")

    wheels = list(out_dir.glob("*.whl"))
    assert wheels, f"no wheel produced in {out_dir}"
    with zipfile.ZipFile(wheels[0]) as whl:
        return whl.namelist()


@pytest.mark.parametrize(("package", "filename", "needle"), _ASSETS, ids=[a[1] for a in _ASSETS])
def test_asset_ships_in_the_built_wheel(
    package: str, filename: str, needle: bytes, built_wheel_names: list[str]
) -> None:
    expected_path = f"{package.replace('.', '/')}/{filename}"
    assert expected_path in built_wheel_names, (
        f"{expected_path} not found in wheel: {built_wheel_names}"
    )
