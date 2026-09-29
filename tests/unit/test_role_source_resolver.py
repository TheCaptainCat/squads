"""``squads._views._resolve_role_source`` — the ``role`` source's resolver: delegates to
``resolve_role_for_item`` (``squads._roles._resolver``), the one seam every consumer of a live
role item's full ``RoleDef`` goes through, rather than re-deriving its two-call resolution.
Delegation is pinned by a spy rather than an equality check — once this resolver is a one-line
call to that seam, ``_resolve_role_source(item, dir) == resolve_role_for_item(item, dir)`` holds
for any implementation that happens to return the same value on the happy path; it would not
catch a reimplementation that quietly dropped the seam's own degrade branch. Three happy-path
cases exercised through the resolver's own return value: a bundled role, a developer role, and a
role with a project override. The degrade case — an identity that resolves against neither the
catalog nor a project override still resolves via ``RoleDef.from_extra_or_item`` rather than
raising — is pinned at the module-function level in
``test_view_source_applicability_predicate.py`` and, through the real service seams the failure
actually reaches (an orphaned project role whose override file is deleted after activation), in
``tests/service/test_role_playbook_self_views_end_to_end.py``.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from squads import __version__
from squads import _views as views
from squads._roles._resolver import resolve_role_for_item

pytestmark = pytest.mark.anyio


async def test_resolve_role_source_delegates_to_the_documented_seam(svc) -> None:
    item = await svc.activate_role("tech-writer")

    with patch.object(views, "resolve_role_for_item", wraps=resolve_role_for_item) as spy:
        resolved = views._resolve_role_source(item, svc.paths.squad_dir)

    spy.assert_called_once_with(item, svc.paths.squad_dir)
    assert resolved.slug == "tech-writer"
    assert resolved.mission


async def test_a_developer_role_resolves_the_activated_definition(svc) -> None:
    item = await svc.add_dev("python", name="Test Dev")

    resolved = views._resolve_role_source(item, svc.paths.squad_dir)

    assert resolved.slug == "python-dev"
    assert resolved.full_name == "Test Dev"


async def test_an_overridden_role_resolves_the_override_layered_over_the_catalog(
    svc, tmp_path: Path
) -> None:
    """The resolver reads straight from disk on every call (the same statelessness
    ``resolve_role_with_base`` documents), so writing the override file after activation and
    before resolving is exactly the ordering a project override reaches at read time."""
    item = await svc.activate_role("tech-writer")
    override_dir = svc.paths.squad_dir / ".overrides" / "roles"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "tech-writer.toml").write_text(
        f'# squads:override-base:{__version__}\nmission = "A project-specific mission."\n',
        encoding="utf-8",
    )

    resolved = views._resolve_role_source(item, svc.paths.squad_dir)

    assert resolved.mission == "A project-specific mission."
    # Fields the override didn't touch still come from the catalog, not blanked.
    assert resolved.title == "technical writer"
