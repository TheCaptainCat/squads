"""``render_source_view`` — the template context a ``role``/``playbook``/``self`` source
receives: ``source=`` (that kind's own resolved shape, under the fixed name every such template
reads), ``item=``/``spec=``/``squad_dir=`` always, unconditionally across all three kinds — not
``self`` alone. Proven end-to-end through the real Jinja engine with a throwaway template per
kind, not by inspecting the context dict the function builds."""

import pytest

from _helpers import create_item
from squads import _views as views
from squads._rendering._engine import invalidate_squad_dir, set_active_squad_dir
from squads._workflow._models import ViewSource, ViewSpec

pytestmark = pytest.mark.anyio


def _place_probe_template(squad_dir, name: str, content: str) -> None:
    target = squad_dir / ".overrides" / "templates" / "views" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    invalidate_squad_dir(squad_dir)


async def test_a_role_source_receives_source_item_spec_and_squad_dir(svc) -> None:
    squad_dir = svc.paths.squad_dir
    _place_probe_template(
        squad_dir,
        "role_probe.md.j2",
        "{{ source.slug }}|{{ item.id }}|{{ spec.items|length }}|{{ squad_dir }}\n",
    )
    set_active_squad_dir(squad_dir)
    role_item = await svc.activate_role("tech-writer")
    result = views._resolve_role_source(role_item, squad_dir)

    rendered = views.render_source_view(
        "role_probe", result, role_item, svc.spec, svc.paths.config.squad_dir
    )

    slug, item_id, n_items, sd = rendered.strip().split("|")
    assert slug == "tech-writer"
    assert item_id == role_item.id
    assert int(n_items) == len(svc.spec.items)
    assert sd == svc.paths.config.squad_dir


async def test_a_playbook_source_receives_source_item_spec_and_squad_dir(svc) -> None:
    squad_dir = svc.paths.squad_dir
    _place_probe_template(
        squad_dir,
        "playbook_probe.md.j2",
        "{{ source.item_type }}|{{ source.roster|length }}|{{ item.id }}|{{ squad_dir }}\n",
    )
    set_active_squad_dir(squad_dir)
    task = (await create_item(svc, "task", "T")).item
    roster = await svc.roster()
    view = ViewSpec(source=ViewSource(kind="playbook"))
    result = views._resolve_playbook_source(view, task, svc.playbook, lambda: roster, svc.spec)

    rendered = views.render_source_view(
        "playbook_probe", result, task, svc.spec, svc.paths.config.squad_dir
    )

    item_type, n_roster, item_id, sd = rendered.strip().split("|")
    assert item_type == "task"
    assert int(n_roster) == len(roster)
    assert item_id == task.id
    assert sd == svc.paths.config.squad_dir


async def test_a_playbook_source_carries_the_whole_active_playbook_not_only_its_own_lane(
    svc,
) -> None:
    """The field the embedded workflow cheatsheet needs (every type's own authoring lane) is
    not answerable from ``lane`` (one type's own entry) — this is what closes that gap."""
    task = (await create_item(svc, "task", "T")).item
    roster = await svc.roster()
    view = ViewSpec(source=ViewSource(kind="playbook"))
    result = views._resolve_playbook_source(view, task, svc.playbook, lambda: roster, svc.spec)

    assert result.playbook is svc.playbook


async def test_a_self_source_receives_source_item_spec_and_squad_dir(svc) -> None:
    squad_dir = svc.paths.squad_dir
    _place_probe_template(
        squad_dir, "self_probe.md.j2", "{{ source.id }}|{{ item.id }}|{{ squad_dir }}\n"
    )
    set_active_squad_dir(squad_dir)
    task = (await create_item(svc, "task", "T")).item
    result = views._resolve_self_source(task)

    rendered = views.render_source_view(
        "self_probe", result, task, svc.spec, svc.paths.config.squad_dir
    )

    rec_id, item_id, sd = rendered.strip().split("|")
    assert rec_id == task.id
    assert item_id == task.id
    assert sd == svc.paths.config.squad_dir
