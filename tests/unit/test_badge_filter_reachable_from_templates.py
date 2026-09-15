"""``squads._badges.status_badge`` registered as the Jinja ``badge`` filter
(``_rendering/_engine.py``, beside ``slugify``/``open_marker``/``idnum``) — so a view template
can write ``{{ status | badge }}`` instead of hand-writing emoji. Proven by a throwaway
template placed as a project override and actually rendered through the real engine, not by
inspecting the filter registry."""

from pathlib import Path

from squads._rendering._engine import invalidate_squad_dir, render, set_active_squad_dir
from squads._workflow import bundled_spec


def _place_probe_template(squad_dir: Path, content: str) -> None:
    target = squad_dir / ".overrides" / "templates" / "views" / "badge_probe.md.j2"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    invalidate_squad_dir(squad_dir)


def test_the_badge_filter_renders_the_same_emoji_and_label_status_badge_does(
    tmp_path: Path,
) -> None:
    _place_probe_template(tmp_path, "{{ status | badge }}")
    set_active_squad_dir(tmp_path)

    rendered = render("views/badge_probe.md.j2", status="InProgress")

    assert rendered.strip() == "🟡 In Progress"


def test_the_badge_filter_accepts_an_explicit_spec_argument(tmp_path: Path) -> None:
    """``{{ status | badge(spec) }}`` — the two-argument call shape a project-overridden spec's
    own custom badge needs, not just the bundled default the no-arg form falls back to."""
    _place_probe_template(tmp_path, "{{ status | badge(spec) }}")
    set_active_squad_dir(tmp_path)

    rendered = render("views/badge_probe.md.j2", status="InProgress", spec=bundled_spec())

    assert rendered.strip() == "🟡 In Progress"
