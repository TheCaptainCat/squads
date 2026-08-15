"""``roles`` is keyed by slug — the generated skill renders one H2 section per slug — so a
playbook override that spreads the bundled array and re-adds a slug the bundled array already
carries must be refused, not silently accepted into a document the renderer would then split
into two sections for one role. Also pins that the shipped scaffold example itself no longer
demonstrates the defect it used to (a spread of ``qa`` onto ``task``, which already has ``qa``).
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._interactions._loader import load_playbook
from squads._overrides._service import scaffold_playbook
from squads._roles._catalog import get_catalog
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio


def _write_playbook_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "playbook.toml").write_text(content, encoding="utf-8")


def test_spreading_a_slug_the_bundled_array_already_carries_is_refused(tmp_path: Path) -> None:
    _write_playbook_override(
        tmp_path,
        '[types.task]\nroles = ["$(*self)", { slug = "qa", do = ["Verify the fix"] }]\n',
    )
    spec = load_workflow_spec()
    with pytest.raises(SquadsError) as exc_info:
        load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)
    assert "slug 'qa' appears twice" in str(exc_info.value)


def test_two_wholly_new_guides_for_the_same_new_slug_is_also_refused(tmp_path: Path) -> None:
    """Not only a duplicate of a bundled guide — two hand-written guides for the SAME new
    slug in one array must be refused too (the rule is about the document, not the splat)."""
    _write_playbook_override(
        tmp_path,
        '[types.task]\nroles = [{ slug = "architect", do = ["a"] }, '
        '{ slug = "architect", do = ["b"] }]\n',
    )
    spec = load_workflow_spec()
    with pytest.raises(SquadsError) as exc_info:
        load_playbook(get_catalog(), spec=spec, squad_dir=tmp_path)
    assert "slug 'architect' appears twice" in str(exc_info.value)


async def test_the_shipped_scaffold_example_no_longer_duplicates_a_bundled_guide(
    project,
) -> None:
    """Uncommenting the scaffold's own worked example exactly as shipped must not reproduce
    the defect: the example slug must not already be in the bundled ``task`` entry."""
    dest = scaffold_playbook(project.squad_dir)
    text = dest.read_text(encoding="utf-8")

    # Extract the commented example block and uncomment it, the way the scaffold's own
    # instructions tell an adopter to.
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if "Worked example" in ln)
    example_lines = [
        ln.removeprefix("# ").removeprefix("#")
        for ln in lines[start + 1 :]
        if ln.startswith("#") and "---" not in ln
    ]
    example = "\n".join(example_lines)
    assert 'slug = "qa"' not in example  # the defect this pins: "qa" is already on task

    (project.squad_dir / ".overrides" / "playbook.toml").write_text(
        f"# squads:override-base:0.0.0\n{example}\n", encoding="utf-8"
    )
    spec = load_workflow_spec()
    merged = load_playbook(get_catalog(), spec=spec, squad_dir=project.squad_dir)  # must not raise
    slugs = [g.slug for g in merged.types["task"].roles]
    assert len(slugs) == len(set(slugs))  # no duplicate section
