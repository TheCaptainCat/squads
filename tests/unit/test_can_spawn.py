"""RoleDef.can_spawn: manager and tech-lead can spawn, every leaf/dev role cannot, and the
field defaults to False.

``can_spawn`` is a catalog answer resolved on every read, never stored on the role item -- that
it is absent from ``to_extra()`` is pinned in tests/unit/test_role_def_extra_keys.py, and the
rendered pointer denylist and ``sq role show`` surfacing live in
tests/integration/test_can_spawn_surfaces.py.
"""

from squads._roles._catalog import PREDEFINED, RoleDef, dev_role


def test_manager_and_tech_lead_can_spawn() -> None:
    for slug in ("manager", "tech-lead"):
        role = next(r for r in PREDEFINED if r.slug == slug)
        assert role.can_spawn is True


def test_leaf_bundled_roles_cannot_spawn() -> None:
    leaf_slugs = {"architect", "reviewer", "qa", "devops", "product-owner", "tech-writer"}
    for role in PREDEFINED:
        if role.slug in leaf_slugs:
            assert role.can_spawn is False, role.slug


def test_dev_roles_of_any_tech_cannot_spawn() -> None:
    for tech in ("python", "dotnet", "go", "rust", "typescript"):
        assert dev_role(tech).can_spawn is False


def test_default_can_spawn_is_false() -> None:
    role = RoleDef(
        slug="custom",
        full_name="Custom Role",
        title="custom",
        description="A custom role.",
        mission="Do custom things.",
    )
    assert role.can_spawn is False
