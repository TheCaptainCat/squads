"""``linearize_lifecycle`` moved from ``env.globals`` to ``env.filters`` (the sanctioned
extension point for render-time logic) — correct, and not reverted here. What this covers is
the one-release compatibility alias that keeps the *old* calling shape working: an adopter who
ran ``sq override scaffold workflow.md.j2`` against squads 0.14.x and changed nothing still
calls it as ``{{ linearize_lifecycle(machine) }}`` — the global-callable form — never
``{{ machine | linearize_lifecycle }}``. Without the alias that override hard-fails to render
on 0.15.0 (``'linearize_lifecycle' is undefined``), for both ``sq workflow`` and
``sq skill squads show`` (which includes ``workflow.md.j2``).

Proven by a throwaway template placed as a project override and actually rendered through the
real engine — the same technique as ``test_badge_filter_reachable_from_templates.py`` — not by
inspecting the filter/global registries.
"""

from pathlib import Path

from squads._rendering._engine import invalidate_squad_dir, render, set_active_squad_dir
from squads._workflow import bundled_spec
from squads._workflow._models import linearize_lifecycle


def _place_probe_template(squad_dir: Path, content: str) -> None:
    target = squad_dir / ".overrides" / "templates" / "views" / "linearize_probe.md.j2"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    invalidate_squad_dir(squad_dir)


def test_the_old_global_call_shape_still_renders(tmp_path: Path) -> None:
    """The exact syntax a 0.14.x-scaffolded ``workflow.md.j2`` calls: a bare global function,
    not a filter."""
    _place_probe_template(tmp_path, "{{ linearize_lifecycle(machine) }}")
    set_active_squad_dir(tmp_path)
    machine = bundled_spec().machine_for("task")

    rendered = render("views/linearize_probe.md.j2", machine=machine)

    assert rendered.strip() == linearize_lifecycle(machine)


def test_the_global_and_filter_forms_agree_on_the_same_machine(tmp_path: Path) -> None:
    """Not two implementations under two names — one callable, reachable two ways. A future
    edit to ``linearize_lifecycle`` itself cannot make the two calling shapes disagree, since
    both dispatch to the same registered function."""
    _place_probe_template(
        tmp_path, "{{ linearize_lifecycle(machine) }}|{{ machine | linearize_lifecycle }}"
    )
    set_active_squad_dir(tmp_path)
    machine = bundled_spec().machine_for("review")

    rendered = render("views/linearize_probe.md.j2", machine=machine)

    global_form, filter_form = rendered.split("|")
    assert global_form == filter_form
    assert global_form == linearize_lifecycle(machine)


def test_the_bundled_workflow_template_itself_still_renders() -> None:
    """The real regression, not a probe: ``workflow.md.j2`` (bundled, filter-only, same
    context ``sq workflow`` builds — see ``_cli/_workflow_cmd.py``) still renders clean with
    the alias present — the alias is additive, so it cannot break a template that only ever
    calls the filter form."""
    rendered = render("workflow.md.j2", spec=bundled_spec(), roles=None, playbook=None)

    assert rendered.strip()
