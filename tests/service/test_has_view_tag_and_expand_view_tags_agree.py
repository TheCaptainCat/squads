"""``has_view_tag`` and ``expand_view_tags`` each decide, independently, whether a span in a
body counts as a view tag — the first as the fast-path recognition check
``Service.read_body`` bails on, the second in its own per-span loop over the same
``iter_marker_spans`` output. Nothing pins that the two agree.

If one recogniser widens (or narrows) without the other, the failure is silent everywhere it
matters: a body carrying a tag one side treats as real and the other does not renders that tag
as literal text on every read surface, ``sq check`` stays clean (it does not ask the recognition
question at all — its own finding gates on a different predicate, name resolution, not shape
recognition), and no exception is raised anywhere in the read path.

Driven at the text/recognition level (no read-time gating, no host-applicability question):
every shape either both recognisers accept or both refuse, and where a shape is accepted, actual
expansion follows through (the bundled ``ref``-source view resolves on any host, so a positive
case here is never confounded by an unresolvable-source refusal).
"""

import pytest

from _helpers import create_item
from squads._models import _markers as markers
from squads._views import expand_view_tags, has_view_tag

pytestmark = pytest.mark.anyio

_BUNDLED_VIEW = "milestone_rollup"

#: Shapes a real view tag placement can never produce, alongside plain prose — each must be
#: refused by both recognisers. See ``tests/unit/test_unpaired_view_tag_shape_recognition.py``
#: for the same shapes pinned against the bare recogniser directly.
_NOT_A_VIEW_TAG = {
    "no marker at all": "just prose, nothing here",
    "a different marker family": "prose <!-- sq:note --> more prose",
    "a look-alike prefix (viewpoint, not view)": "prose <!-- sq:viewpoint:x --> more prose",
    "the bare word with no name": "prose <!-- sq:view --> more prose",
    "the close-marker spelling": "prose <!-- sq:view:milestone_rollup:end --> more prose",
}


async def _fixture(svc):
    item = (await create_item(svc, "task", "T")).item
    db = await svc.store.load()
    return (
        item,
        db,
        svc.spec,
        svc.playbook,
        await svc.roster(),
        svc.paths.squad_dir,
        svc.paths.config.squad_dir,
    )


async def test_a_real_view_tag_is_recognised_by_both_and_actually_expands(svc) -> None:
    item, db, spec, playbook, roster, squad_dir, squad_dir_display = await _fixture(svc)
    text = f"prose <!-- sq:{markers.view_tag(_BUNDLED_VIEW)} --> more prose"

    assert has_view_tag(text) is True
    expanded = expand_view_tags(
        text, item, db, spec, playbook, lambda: roster, squad_dir, squad_dir_display
    )
    assert expanded != text
    assert markers.view_tag(_BUNDLED_VIEW) not in expanded


@pytest.mark.parametrize("shape", list(_NOT_A_VIEW_TAG.values()), ids=list(_NOT_A_VIEW_TAG))
async def test_a_non_view_shape_is_refused_by_both_and_never_expands(svc, shape: str) -> None:
    item, db, spec, playbook, roster, squad_dir, squad_dir_display = await _fixture(svc)

    assert has_view_tag(shape) is False
    assert (
        expand_view_tags(
            shape, item, db, spec, playbook, lambda: roster, squad_dir, squad_dir_display
        )
        == shape
    )


async def test_agreement_holds_with_a_recognised_tag_alongside_a_non_view_marker(svc) -> None:
    """A mixed body — one real view tag plus one near-miss — must still expand only the real
    tag; the near-miss neither recogniser touches."""
    item, db, spec, playbook, roster, squad_dir, squad_dir_display = await _fixture(svc)
    text = (
        f"before <!-- sq:viewpoint:x --> middle <!-- sq:{markers.view_tag(_BUNDLED_VIEW)} --> after"
    )

    assert has_view_tag(text) is True
    expanded = expand_view_tags(
        text, item, db, spec, playbook, lambda: roster, squad_dir, squad_dir_display
    )
    assert "<!-- sq:viewpoint:x -->" in expanded
    assert markers.view_tag(_BUNDLED_VIEW) not in expanded
