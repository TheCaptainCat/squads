"""The role definition view renders a Responsibilities section only when the role has one, and
never a placeholder; a non-empty section and the agreements list render as before."""

from types import SimpleNamespace

from squads._rendering import _engine as engine


def _render_with(**overrides: object) -> str:
    base: dict[str, object] = {
        "full_name": "Ada Dev",
        "title": "Developer",
        "slug": "ada-dev",
        "mission": "Ship it.",
        "responsibilities": ["Build"],
        "agreements": [],
    }
    return engine.render(
        "views/role_definition.md.j2",
        from_squad=None,
        source=SimpleNamespace(**{**base, **overrides}),
    )


def test_an_empty_responsibilities_list_renders_no_section() -> None:
    out = _render_with(responsibilities=[])
    assert "## Responsibilities" not in out
    assert "## Mission\n\nShip it.\n\n## Working agreements" in out
    assert "_TODO" not in out


def test_present_sections_keep_their_spacing_and_agreements_add_bullets() -> None:
    out = _render_with(agreements=["Be kind"])
    assert (
        "## Mission\n\nShip it.\n\n## Responsibilities\n\n- Build\n\n## Working agreements" in out
    )
    assert "\n- Be kind\n" in out
