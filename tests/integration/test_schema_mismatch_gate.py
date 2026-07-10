"""The root CLI callback's schema hard-stop: an ordinary command refuses to run against a
squad whose on-disk schema is behind this build, points the user at `sq migrate up`, and
`migrate` itself is exempt from the gate so it can actually perform the upgrade.
"""

import pytest

from squads import _sections as sections
from squads._models._schema import SCHEMA_VERSION
from squads._services._service import Service

pytestmark = pytest.mark.anyio


async def test_an_ordinary_command_hard_stops_until_migrate_up_runs(project, invoke):
    svc = Service(project)
    task = (await svc.create("task", "T")).item
    guide = (await svc.create("guide", "G")).item

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
    assert "sq migrate up" in " ".join(blocked.output.split())  # tolerate Rich line-wrapping

    # migrate is exempt from the gate and performs the upgrade.
    done = await invoke(["migrate", "up"])
    assert done.exit_code == 0, done.output
    assert "migrated" in done.output and f"v{SCHEMA_VERSION}" in done.output

    assert f'schema_version = "{SCHEMA_VERSION}"' in cfg.read_text(encoding="utf-8")
    text = task_md.read_text(encoding="utf-8")
    assert "ref_kinds" not in text
    assert (await invoke(["list"])).exit_code == 0
