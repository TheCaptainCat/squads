"""CLI smoke test for the schema 0.14 -> 0.15 migration, through the real ``sq migrate up``
entry point: a milestone created before this change gets its roll-up tag, the run reports how
many bodies it touched, and the command exits clean.
"""

import re
import tomllib

import pytest

from squads import _aio
from squads._models import _markers as markers
from squads._sections import get_section, remove_unpaired_marker

pytestmark = pytest.mark.anyio

_TAG = markers.view_tag("milestone_rollup")


async def _strip_tag_and_downgrade(project) -> None:
    # The one milestone this module ever creates per test — glob rather than compute the
    # padded filename, so this stays decoupled from the id-formatting internals.
    folder = project.squad_dir / "milestones"
    (path,) = folder.glob("*.md")
    text = await _aio.read_text(path)
    stripped, removed = remove_unpaired_marker(text, markers.BODY, _TAG)
    assert removed
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

    # Downgrade the schema only — leave the freshly-seeded tag in place.
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
    """A milestone this pass cannot safely act on no longer takes the whole run down with it —
    it is named by id in the output, and every ordinary command still works afterwards."""
    healthy = await invoke(["create", "milestone", "Healthy one", "--author", "manager"])
    assert healthy.exit_code == 0, healthy.output
    damaged = await invoke(["create", "milestone", "Damaged one", "--author", "manager"])
    assert damaged.exit_code == 0, damaged.output
    damaged_id = re.findall(r"MILE-\d+", damaged.output)[0]

    folder = project.squad_dir / "milestones"
    (damaged_path,) = [p for p in folder.glob("*.md") if "damaged" in p.name]
    damaged_path.unlink()  # the missing-indexed-file shape

    cfg_text = await _aio.read_text(project.config_path)
    cfg_text = cfg_text.replace(
        f'schema_version = "{project.config.schema_version}"', 'schema_version = "0.14"'
    )
    await _aio.write_text(project.config_path, cfg_text)

    r = await invoke(["migrate", "up"])

    # The healthy milestone already carries its tag from creation (the template seeds it
    # unconditionally) — nothing to change for it, so this run's own count is 0; the point of
    # this test is that a damaged sibling does not take the run down with it.
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
    """Inserting a second, in-region copy alongside one an author moved outside ``sq:body``
    would duplicate it — the exact regression a byte-count assertion would miss. The only proof
    that matters is ``sq check`` staying clean once the run completes."""
    r = await invoke(["create", "milestone", "Moved tag", "--author", "manager"])
    assert r.exit_code == 0, r.output
    moved_id = re.findall(r"MILE-\d+", r.output)[0]

    folder = project.squad_dir / "milestones"
    (path,) = folder.glob("*.md")
    text = await _aio.read_text(path)
    stripped, removed = remove_unpaired_marker(text, markers.BODY, _TAG)
    assert removed
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
    assert (await _aio.read_text(path)).count(markers.open_marker(_TAG)) == 1

    with project.config_path.open("rb") as fh:
        assert tomllib.load(fh)["schema_version"] == "0.15"
    check = await invoke(["check"])
    assert check.exit_code == 0, check.output
    assert "duplicate" not in check.output.lower(), check.output
