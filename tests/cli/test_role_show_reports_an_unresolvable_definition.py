"""``sq role <slug> show``'s definition pane, when the role's own resolution fails.

An activated custom role's catalog card and its resolved definition are the same resolution
(``resolve_role_with_base``, kept as ``r`` past the try/except in ``show_role``) — but the
definition pane reads the item's body through ``read_body`` regardless of whether ``r`` resolved,
because the tag's own ``role`` source (``resolve_role_for_item``) degrades a broken project
override to ``RoleDef.from_extra_or_item`` rather than raising. That degrade renders a
plausible-looking definition even when the catalog card above it has already fallen back to the
item's bare fields — so the definition pane needs its own signal that resolution failed, or an
operator has no way to tell a genuinely resolved role from a quietly degraded one.
"""

from pathlib import Path

import pytest

from squads._overrides._service import scaffold_new_role

pytestmark = pytest.mark.anyio


async def _activate_custom_role(svc, squad_dir: Path, slug: str) -> Path:
    path = scaffold_new_role(squad_dir, slug=slug)
    text = path.read_text(encoding="utf-8")
    import re

    for field, value in {
        "full_name": "Sam Custom",
        "title": "custom role",
        "description": "A project-defined role.",
        "mission": "Do the custom thing.",
    }.items():
        text = re.sub(
            rf'^{field} = ".*"$', f'{field} = "{value}"', text, count=1, flags=re.MULTILINE
        )
    path.write_text(text, encoding="utf-8")
    await svc.activate_role(slug)
    return path


async def test_a_resolvable_custom_role_prints_no_advisory(project, svc, invoke) -> None:
    """Control: a healthy custom role — its override file intact — gets no advisory at all."""
    await _activate_custom_role(svc, project.squad_dir, "custom-analyst")

    r = await invoke(["role", "custom-analyst", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "could not be resolved" not in r.output


async def test_a_role_whose_override_vanished_after_activation_prints_the_advisory(
    project, svc, invoke
) -> None:
    """The reproduction: activate against a real override, then let the override go missing
    (a hand-edited/deleted ``.overrides/roles/<slug>.toml`` — the only way a slug with no
    catalog entry loses its resolution once it already has a live item). ``resolve_role_with_base``
    then has neither a predefined entry nor an override file for this slug, and raises
    ``RoleNotFoundError`` — the branch ``show_role`` falls back to the item's own fields for.
    """
    override_path = await _activate_custom_role(svc, project.squad_dir, "custom-analyst")
    override_path.unlink()

    r = await invoke(["role", "custom-analyst", "show", "--raw"])

    assert r.exit_code == 0, r.output
    # The catalog card still degrades to the item's own fields (unchanged behaviour).
    assert "Sam Custom" in r.output or "custom-analyst" in r.output
    # The definition pane's own advisory.
    assert "could not be resolved" in r.output
    assert "sq check" in r.output


async def test_the_advisory_does_not_replace_the_degraded_definition(project, svc, invoke) -> None:
    """The degrade-rather-than-raise behaviour stays exactly as it is: the body still renders
    (off ``RoleDef.from_extra_or_item``) — the advisory is an addition, not a replacement."""
    override_path = await _activate_custom_role(svc, project.squad_dir, "custom-analyst")
    override_path.unlink()

    r = await invoke(["role", "custom-analyst", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "could not be resolved" in r.output
    # The degraded definition (from the item's own extra/title/description) still renders —
    # `read_body` resolves the `role` source through `resolve_role_for_item`'s own degrade,
    # which is not what raised `RoleNotFoundError` above (that was the catalog-card
    # resolution, a separate call).
    assert "custom role" in r.output or "Do the custom thing." in r.output
