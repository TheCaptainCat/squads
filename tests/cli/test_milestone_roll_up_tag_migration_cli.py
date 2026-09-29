"""CLI smoke test, through ``sq migrate up``: a milestone predating the roll-up tag gets it
seeded, the run reports the changed count, and the command exits clean."""

import re
import tomllib

import pytest

from squads import _aio
from squads._models import _markers as markers
from squads._sections import get_section, replace_section, strip_marker_lines

pytestmark = pytest.mark.anyio

_TAG = markers.view_tag("milestone_rollup")


def _strip_tag_from_body(text: str) -> str:
    """Remove the roll-up tag from *text*'s ``sq:body`` region, so it reads like a body written
    before this migration (or the tag's own placement) ever existed."""
    region = get_section(text, markers.BODY) or ""
    stripped_region, removed = strip_marker_lines(region, lambda raw: raw != f"sq:{_TAG}")
    assert removed
    return replace_section(text, markers.BODY, stripped_region)


async def _strip_tag_and_downgrade(project) -> None:
    folder = project.squad_dir / "milestones"
    (path,) = folder.glob("*.md")
    text = await _aio.read_text(path)
    stripped = _strip_tag_from_body(text)
    await _aio.write_text(path, stripped)

    cfg_text = await _aio.read_text(project.config_path)
    cfg_text = cfg_text.replace(
        f'schema_version = "{project.config.schema_version}"', 'schema_version = "0.14"'
    )
    await _aio.write_text(project.config_path, cfg_text)


async def test_migrate_up_seeds_the_roll_up_tag_and_reports_the_count(project, invoke) -> None:
    r = await invoke(["create", "milestone", "Ship it", "--author", "manager"])
    assert r.exit_code == 0, r.output
    await _strip_tag_and_downgrade(project)

    r = await invoke(["migrate", "up"])

    assert r.exit_code == 0, r.output
    assert "1 changed" in r.output, r.output

    folder = project.squad_dir / "milestones"
    (path,) = folder.glob("*.md")
    body = get_section(await _aio.read_text(path), markers.BODY)
    assert body is not None
    assert markers.open_marker(_TAG) in body

    with project.config_path.open("rb") as fh:
        assert tomllib.load(fh)["schema_version"] == "0.15"


async def test_migrate_up_on_a_milestone_already_tagged_prints_no_changed_count(
    project, invoke
) -> None:
    r = await invoke(["create", "milestone", "Already tagged", "--author", "manager"])
    assert r.exit_code == 0, r.output

    cfg_text = await _aio.read_text(project.config_path)
    cfg_text = cfg_text.replace(
        f'schema_version = "{project.config.schema_version}"', 'schema_version = "0.14"'
    )
    await _aio.write_text(project.config_path, cfg_text)

    r = await invoke(["migrate", "up"])

    assert r.exit_code == 0, r.output
    assert "changed" not in r.output, r.output


async def test_migrate_up_skips_a_damaged_milestone_by_id_and_still_reaches_current(
    project, invoke
) -> None:
    """A milestone the pass cannot safely act on is named by id, not aborted."""
    healthy = await invoke(["create", "milestone", "Healthy one", "--author", "manager"])
    assert healthy.exit_code == 0, healthy.output
    damaged = await invoke(["create", "milestone", "Damaged one", "--author", "manager"])
    assert damaged.exit_code == 0, damaged.output
    damaged_id = re.findall(r"MILE-\d+", damaged.output)[0]

    folder = project.squad_dir / "milestones"
    (damaged_path,) = [p for p in folder.glob("*.md") if "damaged" in p.name]
    damaged_path.unlink()

    cfg_text = await _aio.read_text(project.config_path)
    cfg_text = cfg_text.replace(
        f'schema_version = "{project.config.schema_version}"', 'schema_version = "0.14"'
    )
    await _aio.write_text(project.config_path, cfg_text)

    r = await invoke(["migrate", "up"])

    assert r.exit_code == 0, r.output
    assert damaged_id in r.output, r.output
    assert "skipped" in r.output.lower(), r.output

    with project.config_path.open("rb") as fh:
        assert tomllib.load(fh)["schema_version"] == "0.15"
    check = await invoke(["check"])
    assert check.exit_code == 0, check.output


async def test_migrate_up_skips_a_tag_moved_outside_the_body_region_check_stays_clean(
    project, invoke
) -> None:
    """A tag moved outside ``sq:body`` is not duplicated, and ``sq check`` stays clean."""
    r = await invoke(["create", "milestone", "Moved tag", "--author", "manager"])
    assert r.exit_code == 0, r.output
    moved_id = re.findall(r"MILE-\d+", r.output)[0]

    folder = project.squad_dir / "milestones"
    (path,) = folder.glob("*.md")
    text = await _aio.read_text(path)
    stripped = _strip_tag_from_body(text)
    moved = stripped.replace("## Discussion", f"{markers.open_marker(_TAG)}\n\n## Discussion", 1)
    assert moved != stripped
    await _aio.write_text(path, moved)

    cfg_text = await _aio.read_text(project.config_path)
    cfg_text = cfg_text.replace(
        f'schema_version = "{project.config.schema_version}"', 'schema_version = "0.14"'
    )
    await _aio.write_text(project.config_path, cfg_text)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert moved_id in result.output, result.output
    assert "skipped" in result.output.lower(), result.output
    assert "needs none of this" not in result.output
    assert "delete the outside line" in result.output
    assert (await _aio.read_text(path)).count(markers.open_marker(_TAG)) == 1

    with project.config_path.open("rb") as fh:
        assert tomllib.load(fh)["schema_version"] == "0.15"
    check = await invoke(["check"])
    assert check.exit_code == 0, check.output
    assert "duplicate" not in check.output.lower(), check.output
