"""The root CLI callback's schema hard-stop: an ordinary command refuses to run against a
squad whose on-disk schema is behind this build, points the user at `sq migrate up`, and
`migrate` itself is exempt from the gate so it can actually perform the upgrade.
"""

import os
import subprocess
import sys

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._models._schema import SCHEMA_VERSION
from squads._services import _service as service
from squads._services._service import Service

pytestmark = pytest.mark.anyio


async def test_an_ordinary_command_hard_stops_until_migrate_up_runs(project, invoke):
    svc = Service(project)
    task = (await create_item(svc, "task", "T")).item
    guide = (await create_item(svc, "guide", "G")).item

    # Forge the pre-0.2 on-disk shape: an old schema version in config, plus a bare ref and
    # a legacy ref_kinds map on the task (the shape `sq migrate up` must fold away).
    cfg = project.config_path
    cfg.write_text(
        cfg.read_text(encoding="utf-8").replace(
            f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.1"'
        ),
        encoding="utf-8",
    )
    task_md = svc.paths.abspath(task.path)
    fm, _ = sections.split_frontmatter(task_md.read_text(encoding="utf-8"))
    fm["refs"] = [guide.id]
    fm["extra"] = {"ref_kinds": {guide.id: "implements"}}
    task_md.write_text(
        sections.replace_frontmatter(task_md.read_text(encoding="utf-8"), fm), encoding="utf-8"
    )

    blocked = await invoke(["list"])
    assert blocked.exit_code == 1
    assert "sq migrate up" in blocked.output

    # migrate is exempt from the gate and performs the upgrade.
    done = await invoke(["migrate", "up"])
    assert done.exit_code == 0, done.output
    assert "migrated" in done.output and f"v{SCHEMA_VERSION}" in done.output

    assert f'schema_version = "{SCHEMA_VERSION}"' in cfg.read_text(encoding="utf-8")
    text = task_md.read_text(encoding="utf-8")
    assert "ref_kinds" not in text
    assert (await invoke(["list"])).exit_code == 0


def _run_piped(tmp_path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """A real subprocess, stderr captured as a pipe would capture it (not a Rich render
    driven in isolation) -- the exact shape the reporting bug's own reproduction used."""
    return subprocess.run(
        [sys.executable, "-m", "squads", *args],
        cwd=tmp_path,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "COLUMNS": "80"},
    )


async def test_the_behind_branch_remedy_survives_a_real_piped_subprocess(tmp_path):
    """End-to-end reproduction of the reporting bug: a real schema mismatch, `COLUMNS=80`,
    stderr piped (never a Rich render driven in isolation), and the whole remedy command
    grep-able as one unbroken token."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    cfg = init.paths.config_path
    cfg.write_text(
        cfg.read_text(encoding="utf-8").replace(
            f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.1"'
        ),
        encoding="utf-8",
    )

    result = _run_piped(tmp_path, "list")

    assert result.returncode == 1
    stderr = result.stderr.decode("utf-8")
    assert "sq migrate up" in stderr, stderr
    assert "sq migrate\nup" not in stderr  # the exact split this bug reported


async def test_the_ahead_branch_remedy_survives_a_real_piped_subprocess_at_a_long_length(
    tmp_path,
):
    """The sibling branch (this build is *behind* the squad's on-disk schema): today's fixed
    wording happens to fit under 80 columns, so a short on-disk version string would pass this
    test even with the fix reverted. Force a version long enough to have wrapped before the
    fix, so the assertion actually exercises the wrap-prevention rather than riding on wording
    that happens to be short today."""
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    cfg = init.paths.config_path
    long_version = "99." + "9" * 40
    cfg.write_text(
        cfg.read_text(encoding="utf-8").replace(
            f'schema_version = "{SCHEMA_VERSION}"', f'schema_version = "{long_version}"'
        ),
        encoding="utf-8",
    )

    result = _run_piped(tmp_path, "list")

    assert result.returncode == 1
    stderr = result.stderr.decode("utf-8")
    assert f"schema v{long_version}, newer than squads" in stderr, stderr
    assert "Upgrade the squads package." in stderr
