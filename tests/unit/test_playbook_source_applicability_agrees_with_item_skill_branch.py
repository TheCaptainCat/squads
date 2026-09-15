"""A per-item-type skill's rich/thin split — role sections rendered or not — is decided in
exactly one place now: ``PlaybookSource.lane``, a plain ``playbook.types.get(target_type)``
resolved once by ``squads._views._resolve_playbook_source`` and read by
``templates/views/item_skill.md.j2`` (``source.lane`` truthiness, both directly and through the
``item_skill_role_sections`` filter). This pins the template's own *rendered* shape — driven
through the real resolver and the real template, not a re-derivation of the expression — against
the raw ``playbook.types.get(item_type) is not None`` question, so a future edit that swaps the
template's test for something narrower (e.g. ``laned_types()``, which asks a different question —
"has an *in-lane author* role", not "carries a playbook entry at all") is caught here rather than
only where it happens to be first noticed.

``laned_types()`` (``_interactions.laned_types``) is proven to disagree with the raw
entry-presence question on a lane whose only role guide sets no ``authors = true`` (the synthetic
override below gives the renamed type exactly that lane) — substituting it for ``source.lane`` in
the template is exactly the regression this test exists to catch.

Swept over every declared non-roster type on the bundled spec, and again on a synthetic override
that shadows the bundled ``guide`` type into a custom type ``doc``: ``doc`` starts unlaned purely
from the rename (playbook coverage is required only for *bundled* type names still active in the
spec — see ``_interactions._loader._check_coverage`` — so a renamed type owes nothing until a
project writes one), and a second variant of the same override gives ``doc`` a lane back via
``.overrides/playbook.toml``. One override, both directions: a type losing a lane, and a type
gaining one.
"""

from pathlib import Path

import pytest

from squads._interactions import item_skill_name, laned_types
from squads._interactions._models import PlaybookSpec
from squads._services._service import Service, resolve_playbook
from squads._views import PlaybookSource, render_resolved_source, resolve_source
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import WorkflowSpec

pytestmark = pytest.mark.anyio


def _item_skill_types(spec: WorkflowSpec) -> list[str]:
    return sorted(t for t, ts in spec.items.items() if ts.category != "roster")


def _carries_a_lane(item_type: str, playbook: PlaybookSpec) -> bool:
    return playbook.types.get(item_type) is not None


async def _rendered_is_rich(svc: Service, item_type: str) -> bool:
    """Resolves ``item_skill`` for a throwaway ``sq-<item_type>`` skill host through the real
    subject-derivation + resolver pipeline (``resolve_source`` -> ``_resolve_playbook_source`` ->
    ``_playbook_subject``, the exact chain a read expands a placement tag through) and reports
    whether the resolved ``PlaybookSource.lane`` is present — driven through the real slug ->
    type inversion (a throwaway item whose slug is ``sq-<item_type>``, not *item_type* handed in
    directly), so a regression in the subject derivation itself (the wrong type's lane resolved,
    or none at all) is caught here, not only a template-side branch.

    Also renders the template and cross-checks that its own rich/thin surface (role sections
    present) never *exceeds* what ``lane`` allows — a lane with no role guides still renders
    rich (overview/commands) with no "## For " sections, so "some role sections" implies a lane
    but the converse does not hold, which is why this is an implication, not an equality."""
    view = svc.spec.views["item_skill"]
    probe_item = _probe_skill_item(item_skill_name(item_type))
    db = await svc.store.load()
    result = resolve_source(
        view,
        "item_skill",
        probe_item,
        db,
        svc.spec,
        svc.playbook,
        lambda: svc.roster_from_db(db),
        svc.paths.squad_dir,
    )
    assert isinstance(result, PlaybookSource)
    rendered = render_resolved_source(
        "item_skill", view, result, probe_item, svc.spec, svc.paths.config.squad_dir
    )
    if "## For " in rendered:
        assert result.lane is not None, f"{item_type}: rendered role sections with no lane"
    return result.lane is not None


def _probe_skill_item(slug: str):
    from squads import _clock as clock
    from squads._models._item import Item
    from squads._workflow._models import ROSTER_SKILL

    now = clock.now()
    return Item(
        sequence_id=0,
        type=ROSTER_SKILL,
        title=slug,
        slug=slug,
        status="Active",
        path=f"agents/skills/{slug}.md",
        created_at=now,
        updated_at=now,
    )


async def test_the_rendered_branch_agrees_with_carries_a_lane_on_every_bundled_type(svc) -> None:
    for item_type in _item_skill_types(svc.spec):
        assert _carries_a_lane(item_type, svc.playbook) == await _rendered_is_rich(
            svc, item_type
        ), item_type


def _write_renamed_guide_override(squad_dir: Path, *, give_it_back_a_lane: bool) -> None:
    """Replaces ``guide`` with a same-shaped custom type ``doc`` — ``[selected]`` drops
    ``guide`` (a shadowed key still needs dropping by name, or it survives the merge
    alongside its replacement and collides on prefix/folder) while every other bundled type
    stays kept. The lane ``give_it_back_a_lane`` restores declares no ``authors = true`` guide
    — ``doc`` carries an entry but no in-lane author, the fixture that proves ``laned_types()``
    and the raw entry-presence question can disagree."""
    bundled = load_workflow_spec()
    kept = sorted([t for t in bundled.items if t != "guide"] + ["doc"])
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"[selected]\nitems = {kept!r}\n\n"
        "[items.doc]\n"
        'prefix = "$(items.guide.prefix)"\n'
        'folder = "$(items.guide.folder)"\n'
        'lifecycle = "$(items.guide.lifecycle)"\n',
        encoding="utf-8",
    )
    if give_it_back_a_lane:
        (override_dir / "playbook.toml").write_text(
            "[types.doc]\n"
            'overview = "A doc."\n'
            'lifecycle = "Draft -> Done"\n'
            'commands = ["sq create doc"]\n'
            'roles = [{ slug = "tech-writer" }]\n',
            encoding="utf-8",
        )


@pytest.mark.parametrize("give_it_back_a_lane", [False, True], ids=["unlaned", "laned"])
async def test_rendered_agrees_with_carries_a_lane_when_a_renamed_types_lane_lapses_or_returns(
    svc, give_it_back_a_lane: bool
) -> None:
    squad_dir = svc.paths.squad_dir
    _write_renamed_guide_override(squad_dir, give_it_back_a_lane=give_it_back_a_lane)
    merged_spec = load_workflow_spec(squad_dir=squad_dir)
    merged_playbook = resolve_playbook(merged_spec, squad_dir)
    project_svc = Service(svc.paths, spec=merged_spec, playbook=merged_playbook)

    # The one type this override actually touches: settle its own direction before the
    # blanket sweep below, so a failure here names the exact case rather than surfacing only
    # as one entry among many.
    assert _carries_a_lane("doc", merged_playbook) is give_it_back_a_lane

    if give_it_back_a_lane:
        # The disagreement fixture: an entry with a role guide that declares no in-lane
        # author. `laned_types()` asks a narrower question than "carries an entry at all"
        # and must not be substituted for it in the template's own rich/thin test.
        assert "doc" not in laned_types(merged_playbook)

    for item_type in _item_skill_types(merged_spec):
        assert _carries_a_lane(item_type, merged_playbook) == await _rendered_is_rich(
            project_svc, item_type
        ), item_type
