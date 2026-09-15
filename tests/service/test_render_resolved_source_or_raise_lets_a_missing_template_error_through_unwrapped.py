"""``_views._render_resolved_source_or_raise`` translates a real engine render failure into a
:class:`SquadsError` naming the item the tag was read from (see
``test_template_failures_translate_to_a_clean_error.py`` for that half). ``render_view``'s own
pre-check — the named view has no presentation template at all — is a different failure mode,
raised before the rendering engine is ever reached, and stays a :class:`ViewTemplateMissingError`
unwrapped: no item-naming prefix added, and the message is not doubled onto itself.
"""

import pytest

from _helpers import create_item
from squads import _views as views
from squads._services._service import Service
from squads._workflow._models import ViewSource, ViewSpec

pytestmark = pytest.mark.anyio


async def test_render_resolved_source_or_raise_lets_a_missing_template_error_through_unwrapped(
    project,
) -> None:
    svc = Service(project)
    epic = (await create_item(svc, "epic", "E")).item
    projection = views.Projection(fields=[], group_by=None, groups=[])
    # A "ref" source with no records — the pre-check refusal fires before `project()`'s output
    # would matter, so an empty record list exercises the exact same refusal an unresolvable
    # view name hits in real read-time expansion.
    view = ViewSpec(source=ViewSource(kind="ref", name="related"))

    with pytest.raises(views.ViewTemplateMissingError) as direct:
        views.render_view("no_such_template_view", projection)

    with pytest.raises(views.ViewTemplateMissingError) as via_expansion:
        views._render_resolved_source_or_raise(
            "no_such_template_view", view, [], epic, svc.spec, svc.paths.config.squad_dir
        )

    # Unwrapped: the same message render_view itself raises, verbatim -- not re-prefixed with
    # "view ... failed to render on <item>", which would double the message onto itself.
    assert str(via_expansion.value) == str(direct.value)
    assert "failed to render on" not in str(via_expansion.value)
