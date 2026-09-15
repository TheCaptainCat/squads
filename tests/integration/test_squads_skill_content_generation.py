"""The bundled ``squads`` meta-skill's own generated content: priority guidance derives from
whichever collection is actually active (never falling back to a hardcoded priority list);
the ``create`` example lists only active work types; the direct-operator rule and the
full-comments/handle-vs-body briefings are present; and the sub-entity comment-scoping
convention is taught with a concrete example per sub-entity kind.
"""

import re

import pytest

from _helpers import resolved_skill_definition
from squads._models._extras import ExtraKey as X
from squads._services import _service as service
from squads._workflow._models import ROSTER_SKILL

pytestmark = pytest.mark.anyio

#: Matches ``squads_skill.md.j2``'s own ``squad_dir`` phrasing — see the sibling pattern in
#: ``claude/claude_section.md.j2`` (``_CLAUDE_MD_SQUAD_DIR_RE`` below) for the surface this is
#: compared against.
_SKILL_SQUAD_DIR_RE = re.compile(r"`([^`]+)/`, indexed in `([^`]+)/\.squads\.json`")

#: Matches ``claude/claude_section.md.j2``'s own ``squad_dir`` phrasing.
_CLAUDE_MD_SQUAD_DIR_RE = re.compile(r"under `([^`]+)/` and indexed in `([^`]+)/\.squads\.json`")


async def _squads_skill_body(svc) -> str:
    """The ``squads`` skill definition as this squad resolves it — rendered on read, so *svc*
    must carry the spec under test."""
    return await resolved_skill_definition(svc, "squads")


async def test_priority_guidance_derives_from_the_active_collection_not_a_hardcoded_list(
    project,
):
    """A custom priority collection (renamed codes) must show up in the guidance verbatim —
    the skill must never fall back to the bundled urgent|high|medium|low literal."""
    from squads._services import _service as service
    from squads._workflow import bundled_spec
    from squads._workflow._models import Badge, Collection

    base = bundled_spec()
    custom = Collection(label="Priority", ordered=True, badges=[Badge(code="p0", label="P0")])
    spec = base.model_copy(update={"collections": {**base.collections, "priority": custom}})
    body = await _squads_skill_body(service.Service(project, spec=spec))
    assert "p0" in body
    assert "urgent|high|medium|low" not in body


async def test_create_example_lists_only_active_work_types(project):
    from squads._services import _service as service
    from squads._workflow import bundled_spec

    base = bundled_spec()
    dropped = {k: v for k, v in base.items.items() if k != "guide"}
    spec = base.model_copy(update={"items": dropped})
    body = await _squads_skill_body(service.Service(project, spec=spec))
    assert "guide" not in body.split("# also:")[1].splitlines()[0]


async def test_direct_operator_rule_is_present(svc):
    body = await _squads_skill_body(svc)
    assert "Working directly with the operator" in body
    assert "never the chat" in body


async def test_teaches_full_comments_briefing_as_the_standard_dossier_move(svc):
    body = await _squads_skill_body(svc)
    assert "--full --comments" in body
    assert "show --full --comments" in body


async def test_teaches_the_comment_scoping_convention_with_one_example_per_subentity_kind(
    svc,
):
    body = await _squads_skill_body(svc)
    assert "Scope your comment to the right discussion" in body
    assert "story <k> comment" in body
    assert "subtask <k> comment" in body
    assert "finding <k> comment" in body
    assert "sq inbox" in body  # the no-gap-when-using-sub-entity-discussions rule


async def test_skill_carries_the_lifecycle_table_and_no_diagram_markup(svc):
    """Agents read the skill as raw text, where diagram markup never renders — the lifecycle
    table and the prose hierarchy bullet carry the same facts in a form they can read."""
    body = await _squads_skill_body(svc)
    assert "```mermaid" not in body
    assert "stateDiagram" not in body
    assert "flowchart" not in body
    assert "| Prefix | Type | Lifecycle |" in body
    assert "- Hierarchy: epic → feature → task." in body


async def test_squad_dir_renders_the_configured_folder_name_not_an_absolute_path(svc):
    """``{{ squad_dir }}`` in ``squads_skill.md.j2`` must render the squad's configured
    *folder name* (``svc.paths.config.squad_dir`` — e.g. ``"squads"``), the same value every
    backend template (``claude/claude_section.md.j2``, ``agents_md/agents_section.md.j2``)
    already renders under this exact key — never the absolute resolved ``Path``
    (``svc.paths.squad_dir``) ``_views.py`` also threads through the same call for role
    resolution. Nothing pinned this rendering before a regression once let the two collide,
    silently switching this skill's text to embed the operator's home directory."""
    body = await _squads_skill_body(svc)
    folder = svc.paths.config.squad_dir
    assert f"`{folder}/`, indexed in `{folder}/.squads.json`" in body
    assert str(svc.paths.squad_dir) not in body


async def test_squad_dir_agrees_with_claude_md_for_a_nested_squad_dir(tmp_path, monkeypatch):
    """The single-segment default (``"squads"``) cannot distinguish "the configured string,
    verbatim" from "the resolved Path's last segment" — both happen to be the same value there.
    A nested ``squad_dir`` (``docs/squad``) separates the two, and this drives the real read
    path (``sq skill squads show --raw`` -> ``ItemsMixin.read_body`` ->
    ``squads._views.expand_view_tags``) against a real seeded skill item, not a throwaway one.

    The property under test is *agreement between two independently-rendered surfaces* —
    this skill's view-rendered text and ``CLAUDE.md``'s backend-rendered managed section — not
    a fixed string pinned twice: both values are extracted from their own rendering and
    compared to each other, so a consistent wrong answer on both sides would still fail this
    the moment they diverge from *each other*, and a correct-looking value on one side alone
    proves nothing without the other."""
    monkeypatch.chdir(tmp_path)
    nested = "docs/squad"
    result = await service.init(root=tmp_path, squad_dir=nested, roles_spec="minimal")
    paths = result.paths
    svc = service.Service(paths)

    db = await svc.store.load()
    skill_item = next(
        it
        for it in db.items.values()
        if it.type == ROSTER_SKILL and it.extra.get(X.SLUG, it.slug) == "squads"
    )
    skill_body = await svc.read_body(skill_item.id)
    claude_md = (paths.root / "CLAUDE.md").read_text(encoding="utf-8")

    skill_match = _SKILL_SQUAD_DIR_RE.search(skill_body)
    claude_match = _CLAUDE_MD_SQUAD_DIR_RE.search(claude_md)
    assert skill_match is not None, f"squad_dir phrasing not found in skill body: {skill_body!r}"
    assert claude_match is not None, f"squad_dir phrasing not found in CLAUDE.md: {claude_md!r}"
    skill_folder = skill_match.group(1)
    claude_folder = claude_match.group(1)

    # The two independently-rendered surfaces must agree with each other...
    assert skill_folder == claude_folder
    # ...and agree with what was actually configured, nested slash included — proving this is
    # not a `Path.name`-style derivation that would silently truncate to "squad".
    assert skill_folder == nested
    assert claude_folder == nested

    assert str(paths.squad_dir) not in skill_body
    assert str(paths.squad_dir) not in claude_md


async def test_squad_dir_is_unchanged_on_the_existing_single_segment_case(svc):
    """The default single-segment ``squad_dir`` ("squads") must still render as itself —
    the fix must not regress the sibling pin above, which already covers this case."""
    body = await _squads_skill_body(svc)
    folder = svc.paths.config.squad_dir
    assert "/" not in folder  # sanity: this case is genuinely single-segment
    match = _SKILL_SQUAD_DIR_RE.search(body)
    assert match is not None
    assert match.group(1) == folder == match.group(2)
