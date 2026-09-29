"""``item_skill_shadowed`` is a warn-level ``sq check`` advisory naming an authored
``sq-<slug>`` skill body whose slug's type is now declared, firing only when both conditions
collide on the same slug."""

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
    """An authored body with no matching declared type has nothing to shadow."""
    item = await svc.add_skill("sq-widget", description="An authored runbook")
    await svc.set_body(item.id, "AUTHORED CONTENT — this body is storage, not a rendering.")
    db = await svc.store.load()
    resolved = db.get(item.id)

    ctx = ValidatorContext(item=resolved, spec=svc.spec, raw_text=_raw_text(svc, resolved))

    assert CATALOG["item_skill_shadowed"](ctx) == []


async def test_is_silent_for_a_template_owned_skill_on_a_declared_type(svc):
    """A body region converged onto the placement tag is not authored content."""
    item = await svc.add_skill("sq-widget", description="A per-item-type skill")
    declared_spec = _declare_widget_type(svc)
    db = await svc.store.load()
    resolved = db.get(item.id)
    tag_line = markers.open_marker(markers.view_tag(ITEM_SKILL_VIEW_NAME))
    converged_text = replace_section(_raw_text(svc, resolved), markers.BODY, tag_line)

    ctx = ValidatorContext(item=resolved, spec=declared_spec, raw_text=converged_text)

    assert CATALOG["item_skill_shadowed"](ctx) == []


async def test_is_silent_for_a_genuinely_empty_body_on_a_declared_type(svc):
    """A genuinely empty body region, before its first convergence, is also silent."""
    item = await svc.add_skill("sq-widget", description="A per-item-type skill")
    declared_spec = _declare_widget_type(svc)
    db = await svc.store.load()
    resolved = db.get(item.id)
    emptied_text = replace_section(_raw_text(svc, resolved), markers.BODY, "")

    ctx = ValidatorContext(item=resolved, spec=declared_spec, raw_text=emptied_text)

    assert CATALOG["item_skill_shadowed"](ctx) == []


async def test_flags_the_tag_plus_prose_shape_without_claiming_nowhere_to_render(svc):
    """A tag plus stray prose is flagged without claiming the tag itself has nowhere to render."""
    item = await svc.add_skill("sq-widget", description="An authored runbook")
    declared_spec = _declare_widget_type(svc)
    db = await svc.store.load()
    resolved = db.get(item.id)
    tag_line = markers.open_marker(markers.view_tag(ITEM_SKILL_VIEW_NAME))
    region = f"{tag_line}\n\nAUTHORED CONTENT — this body is storage, not a rendering."
    tagged_and_authored = replace_section(_raw_text(svc, resolved), markers.BODY, region)

    ctx = ValidatorContext(item=resolved, spec=declared_spec, raw_text=tagged_and_authored)
    issues = CATALOG["item_skill_shadowed"](ctx)

    assert len(issues) == 1
    assert issues[0].level == "warn"
    assert "nowhere to render" not in issues[0].message
    assert "take the type out of the active spec" in issues[0].message


async def test_the_one_remedy_never_offers_a_rename_for_either_a_bundled_or_a_project_type(svc):
    """The one remedy never offers a rename, for either a bundled or a project-declared type."""
    await svc.seed_bundled_skills()
    bundled_item = await svc.roster_item("skill", "sq-task")
    assert bundled_item is not None
    tag_line = markers.open_marker(markers.view_tag(ITEM_SKILL_VIEW_NAME))
    region = f"{tag_line}\n\nAUTHORED CONTENT — this body is storage, not a rendering."
    bundled_tagged = replace_section(_raw_text(svc, bundled_item), markers.BODY, region)
    bundled_ctx = ValidatorContext(item=bundled_item, spec=svc.spec, raw_text=bundled_tagged)
    bundled_issues = CATALOG["item_skill_shadowed"](bundled_ctx)

    project_item = await svc.add_skill("sq-widget", description="An authored runbook")
    declared_spec = _declare_widget_type(svc)
    db = await svc.store.load()
    resolved = db.get(project_item.id)
    project_tagged = replace_section(_raw_text(svc, resolved), markers.BODY, region)
    project_ctx = ValidatorContext(item=resolved, spec=declared_spec, raw_text=project_tagged)
    project_issues = CATALOG["item_skill_shadowed"](project_ctx)

    for issues in (bundled_issues, project_issues):
        assert len(issues) == 1
        assert "take the type out of the active spec" in issues[0].message
        assert "rename" not in issues[0].message


async def test_names_the_move_first_remedy_and_never_doubles_the_quote(svc):
    """The remedy names the move-to-a-fresh-skill step first, then the clear step, with no
    doubled quote around the type name."""
    item = await svc.add_skill("sq-widget", description="An authored runbook")
    await svc.set_body(item.id, "AUTHORED CONTENT — this body is storage, not a rendering.")
    declared_spec = _declare_widget_type(svc)
    db = await svc.store.load()
    resolved = db.get(item.id)

    ctx = ValidatorContext(item=resolved, spec=declared_spec, raw_text=_raw_text(svc, resolved))
    issues = CATALOG["item_skill_shadowed"](ctx)

    assert len(issues) == 1
    message = issues[0].message
    assert "sq skill add <new-slug>" in message
    clear_cmd = 'sq skill sq-widget body -m "" --force'
    assert clear_cmd in message
    assert message.index("sq skill add <new-slug>") < message.index(clear_cmd)
    assert "''" not in message


async def test_is_silent_for_a_permanently_system_skill_even_when_authored(svc):
    """A permanently-system skill is silent regardless of what its body holds."""
    await svc.seed_bundled_skills()
    db = await svc.store.load()
    squads_skill = next(
        it
        for it in db.items.values()
        if it.type == "skill" and it.extra.get(X.SLUG, it.slug) == "squads"
    )

    ctx = ValidatorContext(item=squads_skill, spec=svc.spec, raw_text=_raw_text(svc, squads_skill))

    assert CATALOG["item_skill_shadowed"](ctx) == []
