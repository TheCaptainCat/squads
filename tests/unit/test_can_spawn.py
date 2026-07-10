"""RoleDef.can_spawn: manager and tech-lead can spawn, every leaf/dev role cannot, the
field defaults to False, and it round-trips through extra.

The rendered pointer denylist and ``sq role show`` surfacing live in
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


def test_can_spawn_round_trips_through_extra_both_ways() -> None:
    for slug in ("manager", "tech-lead"):
        role = next(r for r in PREDEFINED if r.slug == slug)
        restored = RoleDef.from_extra(role.to_extra())
        assert restored.can_spawn is True

    architect = next(r for r in PREDEFINED if r.slug == "architect")
    restored = RoleDef.from_extra(architect.to_extra())
    assert restored.can_spawn is False
