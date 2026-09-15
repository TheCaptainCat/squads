"""``squads._views.template_seeded_view_names`` — the one derivation answering "which
``sq:view:<name>`` tags does this type's creation template place in its ``sq:body`` region
today", read from the template's own source rather than a render. The one seam the retroactive
migration and the sibling ``sq check`` advisory both read, so table-driven coverage lives here
once rather than being re-proven by each consumer.
"""

from pathlib import Path

from squads._views import template_seeded_view_names
from squads._workflow import bundled_spec


def test_milestone_seeds_exactly_milestone_rollup() -> None:
    spec = bundled_spec()
    assert template_seeded_view_names("milestone", spec) == frozenset({"milestone_rollup"})


def test_role_seeds_exactly_role_definition() -> None:
    """A roster type answers correctly too — the derivation is generic over item type; it is
    the *migration*'s own choice to restrict iteration to non-roster types, not a limit of
    this function."""
    spec = bundled_spec()
    assert template_seeded_view_names("role", spec) == frozenset({"role_definition"})


def test_every_other_bundled_non_roster_type_seeds_nothing() -> None:
    spec = bundled_spec()
    for item_type in sorted(spec.non_roster_types() - {"milestone"}):
        assert template_seeded_view_names(item_type, spec) == frozenset(), item_type


def test_an_undeclared_type_seeds_nothing_rather_than_erroring() -> None:
    spec = bundled_spec()
    assert template_seeded_view_names("no-such-type", spec) == frozenset()


def test_an_override_template_dropping_the_tag_is_reflected(tmp_path: Path) -> None:
    """Override-aware: resolves through the same squad-scoped loader ``render()`` uses, so a
    project that re-templated ``milestone`` without the tag gets the overridden (empty)
    answer, never the bundled one."""
    from squads._rendering._engine import invalidate_squad_dir, set_active_squad_dir

    override_path = tmp_path / ".overrides" / "templates" / "items" / "milestone.md.j2"
    override_path.parent.mkdir(parents=True, exist_ok=True)
    override_path.write_text(
        "<!-- sq:body -->\nno tag here\n<!-- sq:body:end -->\n", encoding="utf-8"
    )
    set_active_squad_dir(tmp_path)
    try:
        invalidate_squad_dir(tmp_path)
        assert template_seeded_view_names("milestone", bundled_spec()) == frozenset()
    finally:
        set_active_squad_dir(None)
        invalidate_squad_dir(tmp_path)


def test_an_override_template_adding_a_tag_is_reflected(tmp_path: Path) -> None:
    """The reciprocal direction: a type whose bundled template seeds nothing can be
    overridden to seed one, and the derivation must pick that up too — not just the drop
    direction. Reads the template's raw text alone, so naming an existing bundled view here
    (``milestone_rollup``) needs no fresh ``[views]`` declaration of its own."""
    from squads._rendering._engine import invalidate_squad_dir, set_active_squad_dir

    override_path = tmp_path / ".overrides" / "templates" / "items" / "guide.md.j2"
    override_path.parent.mkdir(parents=True, exist_ok=True)
    override_path.write_text(
        "<!-- sq:body -->\n## Notes\n<!-- sq:view:milestone_rollup -->\n<!-- sq:body:end -->\n",
        encoding="utf-8",
    )
    set_active_squad_dir(tmp_path)
    try:
        invalidate_squad_dir(tmp_path)
        assert template_seeded_view_names("guide", bundled_spec()) == frozenset(
            {"milestone_rollup"}
        )
    finally:
        set_active_squad_dir(None)
        invalidate_squad_dir(tmp_path)


def test_a_tag_outside_the_body_region_is_not_counted(tmp_path: Path) -> None:
    """The derivation is scoped to the ``sq:body`` region specifically, not the whole
    template source — a tag sitting outside it (e.g. accidentally placed near the discussion
    heading) is not "seeded", the same restriction the placement verb itself imposes on where
    a tag may live."""
    from squads._rendering._engine import invalidate_squad_dir, set_active_squad_dir

    override_path = tmp_path / ".overrides" / "templates" / "items" / "guide.md.j2"
    override_path.parent.mkdir(parents=True, exist_ok=True)
    override_path.write_text(
        "<!-- sq:body -->\nno tag here\n<!-- sq:body:end -->\n\n"
        "<!-- sq:view:milestone_rollup -->\n",
        encoding="utf-8",
    )
    set_active_squad_dir(tmp_path)
    try:
        invalidate_squad_dir(tmp_path)
        assert template_seeded_view_names("guide", bundled_spec()) == frozenset()
    finally:
        set_active_squad_dir(None)
        invalidate_squad_dir(tmp_path)
