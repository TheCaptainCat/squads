"""``milestone_rollup`` is the one bundled view, attached to the milestone type via
``items.milestone.views`` rather than named as its own source vocabulary — the milestone item
type never appears inside ``[views.milestone_rollup]`` itself (its source is the ``targets``
ref kind, which nothing about milestones being selected changes). So dropping ``milestone``
from ``[selected].items`` doesn't fail a referential check the way dropping a ref kind a view's
*source* names would; instead the loader (``_prune_orphaned_type_owned_views``) prunes the now
type-less view from the merged spec — the view goes with its type, and no adopter has to
remember a second ``[selected].views`` line for a view they never declared themselves.

Table-driven across the three shapes that matter: dropping the owning type prunes the view;
dropping an unrelated type leaves it; a hypothetical second owner keeps the view alive even
after one of its two owners drops (proving the prune is "no surviving owner", not "any drop").
"""

from pathlib import Path

import pytest

from squads import __version__
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import load_workflow_spec


def _write_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


def test_dropping_milestone_prunes_the_now_typeless_bundled_view(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        '[selected]\nitems = ["epic", "feature", "task", "bug", "decision", "contract", '
        '"review", "guide", "role", "skill", "operator"]\n',
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "milestone" not in spec.items
    assert "milestone_rollup" not in spec.views


def test_dropping_an_unrelated_type_leaves_the_view_declared(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        '[selected]\nitems = ["epic", "feature", "task", "bug", "decision", "contract", '
        '"milestone", "review", "role", "skill", "operator"]\n',
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "guide" not in spec.items
    assert "milestone_rollup" in spec.views
    assert spec.items["milestone"].views == ["milestone_rollup"]


def test_a_view_with_a_surviving_second_owner_is_not_pruned(tmp_path: Path) -> None:
    """A second bundled type attaching the same view keeps it alive after the first is
    dropped — the prune is "no surviving owner left", not "this one owner was dropped"."""
    _write_override(
        tmp_path,
        '[items.contract]\nviews = ["milestone_rollup"]\n\n'
        '[selected]\nitems = ["epic", "feature", "task", "bug", "decision", "contract", '
        '"review", "guide", "role", "skill", "operator"]\n',
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "milestone" not in spec.items
    assert "milestone_rollup" in spec.views
    assert spec.items["contract"].views == ["milestone_rollup"]


def test_a_freestanding_view_no_type_ever_attached_is_never_touched(tmp_path: Path) -> None:
    """The prune is scoped to *type-owned* bundled views — an adopter-declared view no type's
    own ``views`` list ever named (the ordinary, tested shape every other view mechanism test
    uses) survives any and every deselect untouched."""
    _write_override(
        tmp_path,
        '[views.freestanding]\nsource = { kind = "ref", name = "related" }\n'
        'fields = [ { code = "id", label = "Id" } ]\n\n'
        '[selected]\nitems = ["epic", "feature", "task", "bug", "decision", "contract", '
        '"review", "guide", "role", "skill", "operator"]\n',
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "milestone" not in spec.items
    assert "milestone_rollup" not in spec.views
    assert "freestanding" in spec.views


@pytest.mark.parametrize("keep_milestone", [True, False])
def test_the_attachment_and_the_view_move_together(tmp_path: Path, keep_milestone: bool) -> None:
    items = [
        "epic",
        "feature",
        "task",
        "bug",
        "decision",
        "contract",
        "review",
        "guide",
        "role",
        "skill",
        "operator",
    ]
    if keep_milestone:
        items.append("milestone")
    _write_override(tmp_path, f"[selected]\nitems = {items!r}\n".replace("'", '"'))
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert ("milestone" in spec.items) == keep_milestone
    assert ("milestone_rollup" in spec.views) == keep_milestone
