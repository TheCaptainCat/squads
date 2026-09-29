"""``milestone_rollup`` is a freestanding declared view — reached only by placing its own
``sq:view:milestone_rollup`` tag (seeded straight into ``templates/items/milestone.md.j2``),
never by declaring it against a type (see
``tests/unit/test_retired_view_grammar_keys_fail_at_load.py`` for the load-time refusal a spec
still declaring ``items.<type>.views`` hits). Deselecting the type that seeds a view's tag
therefore changes nothing about whether the view itself stays declared: there is no reciprocal
binding to strand or to prune.
"""

from pathlib import Path

from squads import __version__
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import load_workflow_spec

#: Every bundled type except milestone and guide — deselecting milestone below is the case
#: under test; guide stays selected as an ordinary unrelated survivor.
_BASE_ITEMS = [
    "epic",
    "feature",
    "task",
    "bug",
    "decision",
    "contract",
    "review",
    "role",
    "skill",
    "operator",
]


def _write_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


def _selected(items: list[str]) -> str:
    quoted = ", ".join(f'"{t}"' for t in items)
    return f"[selected]\nitems = [{quoted}]\n"


def test_milestone_rollup_is_freestanding_and_survives_deselecting_milestone(
    tmp_path: Path,
) -> None:
    _write_override(tmp_path, _selected([*_BASE_ITEMS, "guide"]))
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "milestone" not in spec.items
    assert "milestone_rollup" in spec.views  # no attachment mechanism left to prune it


def test_an_adopter_declared_freestanding_view_is_never_touched_either(tmp_path: Path) -> None:
    """The ordinary shape every other view mechanism test uses — an adopter-declared view,
    reached only by its own tag — survives any deselect, same as the bundled example above."""
    _write_override(
        tmp_path,
        '[views.freestanding]\nsource = { kind = "ref", name = "related" }\n\n'
        + _selected([*_BASE_ITEMS, "guide"]),
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "milestone" not in spec.items
    assert "milestone_rollup" in spec.views
    assert "freestanding" in spec.views
