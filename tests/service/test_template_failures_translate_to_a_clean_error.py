"""``squads._rendering._engine.render`` translates a ``jinja2.TemplateError`` — most commonly
an undefined-variable failure under ``StrictUndefined`` — into :class:`SquadsError`, once, in
the one funnel every rendering path in the codebase goes through.

This covers the adopter-visible property that funnel gives: an item-creation template
overridden with a reference to an undefined variable fails the same clean way a broken view
template does, at both the service and the CLI layer. ``pristine_body`` catches that
``SquadsError`` and returns ``None``.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads._errors import SquadsError
from squads._rendering._engine import invalidate_squad_dir
from squads._services._service import Service

pytestmark = pytest.mark.anyio


def _declare_broken_item_template(squad_dir: Path, item_type: str) -> None:
    """Override the item-creation template for *item_type* with one that references a
    variable no rendering context ever supplies — the shape a typo'd adopter override takes."""
    templates_dir = squad_dir / ".overrides" / "templates" / "items"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / f"{item_type}.md.j2").write_text(
        "<!-- sq:body -->\n{{ this_variable_does_not_exist }}\n<!-- sq:body:end -->\n",
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


async def test_create_with_a_broken_override_template_raises_a_clean_squads_error(
    project,
) -> None:
    _declare_broken_item_template(project.squad_dir, "task")
    svc = Service(project)

    with pytest.raises(SquadsError) as excinfo:
        await create_item(svc, "task", "T")
    # A clean, named SquadsError -- not a bare jinja2.TemplateError/UndefinedError leaking
    # through, and the message names the offending template.
    assert type(excinfo.value) is SquadsError
    assert "task.md.j2" in str(excinfo.value)


async def test_pristine_body_still_swallows_a_broken_template_and_returns_none(project) -> None:
    """``pristine_body`` catches a broken template's rendering failure and returns ``None``.
    Create with the working bundled template first, then break the override afterward so the
    failure is reached only by a direct ``pristine_body`` call, not by ``create`` itself."""
    svc = Service(project)
    task = (await create_item(svc, "task", "T")).item

    _declare_broken_item_template(project.squad_dir, "task")
    # A fresh Service instance so the newly-broken override is what its template loader sees
    # (self.spec/env resolution is fixed at construction elsewhere in this suite's convention).
    svc2 = Service(project)

    assert svc2.pristine_body(task) is None


async def test_create_with_a_working_override_template_is_unaffected(project) -> None:
    """Control: no other renderer's success path changes — a template that renders cleanly
    keeps doing so through the same funnel."""
    templates_dir = project.squad_dir / ".overrides" / "templates" / "items"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "task.md.j2").write_text(
        "<!-- sq:body -->\nCustom scaffold for {{ item.title }}.\n<!-- sq:body:end -->\n\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n",
        encoding="utf-8",
    )
    invalidate_squad_dir(project.squad_dir)
    svc = Service(project)

    task = (await create_item(svc, "task", "My Task")).item
    body = await svc.read_body(task.id)
    assert "Custom scaffold for My Task." in body
