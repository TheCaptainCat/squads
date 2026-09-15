"""``squads._views._resolve_playbook_source`` — the ``playbook`` source's resolver: the named
type's playbook lane (or, absent a name, the type the host *speaks for* —
:func:`~squads._views._playbook_subject`), plus the live roster, resolved against the caller's
active playbook — never the bundled singleton. Cases: an explicit name; an absent name resolving
to an ordinary host's own type; the emptiness case (a type genuinely declared in ``[items]`` but
outside every guide's lane domain resolves with ``lane=None``, not a raise — see
``test_playbook_source_applicability_agrees_with_item_skill_branch.py`` for the same setup used
at the predicate level); and an absent name on a roster-skill host resolving the type its own
slug documents, gated so an ordinary item is never affected by the same slug convention.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import _views as views
from squads._interactions import item_skill_name
from squads._models._extras import ExtraKey as X
from squads._services._service import Service, resolve_playbook
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ViewSource, ViewSpec

pytestmark = pytest.mark.anyio


async def test_an_explicit_name_resolves_that_types_own_lane_not_the_hosts(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    view = ViewSpec(source=ViewSource(kind="playbook", name="bug"))
    roster = await svc.roster()

    result = views._resolve_playbook_source(view, task, svc.playbook, lambda: roster, svc.spec)

    assert result.item_type == "bug"
    assert result.lane == svc.playbook.types["bug"]
    assert result.roster == roster


async def test_an_absent_name_resolves_the_hosts_own_type(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    view = ViewSpec(source=ViewSource(kind="playbook"))
    roster = await svc.roster()

    result = views._resolve_playbook_source(view, task, svc.playbook, lambda: roster, svc.spec)

    assert result.item_type == "task"
    assert result.lane == svc.playbook.types["task"]


def _write_renamed_guide_override(squad_dir: Path) -> None:
    """Shadows bundled ``guide`` with an equally-shaped custom type ``doc`` that carries no
    playbook entry — coverage is required only for *bundled* type names still active in the
    spec (see ``_interactions._loader._check_coverage``), so ``doc`` is declared and real but
    genuinely unlaned."""
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


async def test_a_declared_type_with_no_lane_resolves_an_empty_lane_not_a_raise(svc) -> None:
    squad_dir = svc.paths.squad_dir
    _write_renamed_guide_override(squad_dir)
    merged_spec = load_workflow_spec(squad_dir=squad_dir)
    merged_playbook = resolve_playbook(merged_spec, squad_dir)
    project_svc = Service(svc.paths, spec=merged_spec, playbook=merged_playbook)
    doc_item = (await create_item(project_svc, "doc", "D")).item

    view = ViewSpec(source=ViewSource(kind="playbook"))
    result = views._resolve_playbook_source(
        view, doc_item, merged_playbook, lambda: [], merged_spec
    )

    assert result.item_type == "doc"
    assert result.lane is None


async def test_a_skill_hosts_absent_name_resolves_the_type_its_own_slug_documents(svc) -> None:
    skill = await svc.add_skill(item_skill_name("task"))
    view = ViewSpec(source=ViewSource(kind="playbook"))
    roster = await svc.roster()

    result = views._resolve_playbook_source(view, skill, svc.playbook, lambda: roster, svc.spec)

    assert result.item_type == "task"
    assert result.lane == svc.playbook.types["task"]


async def test_the_gate_prevents_an_ordinary_items_slug_from_naming_a_different_types_lane(
    svc,
) -> None:
    """The hazard the gate closes: ``Item.slug`` is the filename slug segment for every item,
    so an ordinary (non-skill) item whose title happened to slugify to a skill-naming shape
    must still resolve its *own* type, never the type that shape would document for a skill."""
    task = (
        await create_item(svc, "task", item_skill_name("bug"), slug=item_skill_name("bug"))
    ).item
    assert task.slug == item_skill_name("bug")  # the collision is real, not assumed
    view = ViewSpec(source=ViewSource(kind="playbook"))
    roster = await svc.roster()

    result = views._resolve_playbook_source(view, task, svc.playbook, lambda: roster, svc.spec)

    assert result.item_type == "task"


async def test_a_skill_hosts_undocumented_slug_falls_back_to_its_own_type(svc) -> None:
    """The emptiness case for a skill host: a slug naming no declared type — a permanently
    -system skill, or an author-created one sharing the ``sq-`` convention by coincidence —
    resolves the host's bare roster type (``skill``), never a raise."""
    skill = await svc.add_skill("sq-onboarding")
    assert skill.extra.get(X.SLUG) == "sq-onboarding"
    view = ViewSpec(source=ViewSource(kind="playbook"))

    result = views._resolve_playbook_source(view, skill, svc.playbook, lambda: [], svc.spec)

    assert result.item_type == "skill"
    assert result.lane is None
