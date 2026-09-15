"""``item_skill_shadowed`` (``_services/_validators.py``, declared in ``[items.skill]``'s own
``validators`` list) — the ``sq check`` advisory for the case ``strict_empty``
(``_services/_maintenance.py::_converge_body_tag``) correctly refuses to overwrite an authored
``sq-<slug>`` skill body once that slug's type is later declared, but nothing else says the
declared type's generated guidance (lifecycle, verbs, sub-entity footer) then has nowhere to
render. This member is that report — a warn-level advisory naming the skill and the shadowed
type, not a guard: not destroying the authored content stays exactly as ``strict_empty`` left
it.

Both directions matter equally here: the finding fires only when authored content AND a live
declared type collide on the same slug — either alone is silent.
"""

import pytest

from squads._interactions import ITEM_SKILL_VIEW_NAME
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._sections import replace_section
from squads._services._validators import CATALOG, ValidatorContext
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_WIDGET_OVERRIDE = (
    '[lifecycles.widget]\ninitial = "Open"\n[lifecycles.widget.transitions]\nOpen = ["Done"]\n'
    'Done = []\n\n[items.widget]\nprefix = "WID"\nfolder = "widgets"\nlifecycle = "widget"\n'
)


def _raw_text(svc, item) -> str:
    return svc.paths.abspath(item.path).read_text(encoding="utf-8")


def _declare_widget_type(svc):
    override_dir = svc.paths.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_WIDGET_OVERRIDE, encoding="utf-8")
    return load_workflow_spec(squad_dir=svc.paths.squad_dir)


async def test_flags_an_authored_skill_documenting_a_now_declared_type(svc):
    item = await svc.add_skill("sq-widget", description="An authored runbook")
    await svc.set_body(item.id, "AUTHORED CONTENT — this body is storage, not a rendering.")
    declared_spec = _declare_widget_type(svc)
    db = await svc.store.load()
    resolved = db.get(item.id)

    ctx = ValidatorContext(item=resolved, spec=declared_spec, raw_text=_raw_text(svc, resolved))
    issues = CATALOG["item_skill_shadowed"](ctx)

    assert len(issues) == 1
    assert issues[0].level == "warn"
    assert issues[0].item == item.id
    assert "widget" in issues[0].message
    assert "authored content" in issues[0].message


async def test_is_silent_when_the_documented_type_is_not_declared(svc):
    """Same authored body, no matching declaration — nothing to shadow."""
    item = await svc.add_skill("sq-widget", description="An authored runbook")
    await svc.set_body(item.id, "AUTHORED CONTENT — this body is storage, not a rendering.")
    db = await svc.store.load()
    resolved = db.get(item.id)

    ctx = ValidatorContext(item=resolved, spec=svc.spec, raw_text=_raw_text(svc, resolved))

    assert CATALOG["item_skill_shadowed"](ctx) == []


async def test_is_silent_for_a_template_owned_skill_on_a_declared_type(svc):
    """A body region converged onto the ``item_skill`` placement tag — exactly what
    ``_converge_body_tag`` leaves behind for a genuinely template-owned per-item-type skill —
    is not authored content, whatever declared type its slug happens to name."""
    item = await svc.add_skill("sq-widget", description="A per-item-type skill")
    declared_spec = _declare_widget_type(svc)
    db = await svc.store.load()
    resolved = db.get(item.id)
    tag_line = markers.open_marker(markers.view_tag(ITEM_SKILL_VIEW_NAME))
    converged_text = replace_section(_raw_text(svc, resolved), markers.BODY, tag_line)

    ctx = ValidatorContext(item=resolved, spec=declared_spec, raw_text=converged_text)

    assert CATALOG["item_skill_shadowed"](ctx) == []


async def test_is_silent_for_a_genuinely_empty_body_on_a_declared_type(svc):
    """The other template-owned shape: a body region with nothing in it at all (a freshly
    seeded skill before its first convergence)."""
    item = await svc.add_skill("sq-widget", description="A per-item-type skill")
    declared_spec = _declare_widget_type(svc)
    db = await svc.store.load()
    resolved = db.get(item.id)
    emptied_text = replace_section(_raw_text(svc, resolved), markers.BODY, "")

    ctx = ValidatorContext(item=resolved, spec=declared_spec, raw_text=emptied_text)

    assert CATALOG["item_skill_shadowed"](ctx) == []


async def test_is_silent_for_a_permanently_system_skill_even_when_authored(svc):
    """``squads``/``greeting``/``sq-memory`` never document a declared *type* at all —
    ``item_type_for_skill_slug`` returns ``None`` for all three, so this member never reaches
    the body check for them regardless of what their ``sq:body`` holds."""
    await svc.seed_bundled_skills()
    db = await svc.store.load()
    squads_skill = next(
        it
        for it in db.items.values()
        if it.type == "skill" and it.extra.get(X.SLUG, it.slug) == "squads"
    )

    ctx = ValidatorContext(item=squads_skill, spec=svc.spec, raw_text=_raw_text(svc, squads_skill))

    assert CATALOG["item_skill_shadowed"](ctx) == []
