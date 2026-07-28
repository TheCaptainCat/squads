"""RoleDef.extra_keys(): the key-name view of to_extra(), derived from the same field/key
table so the two can never drift apart, and computable without constructing a throwaway
instance (a required field added to RoleDef must not turn this into a startup crash).
"""

from squads._roles._catalog import PREDEFINED, RoleDef, dev_role


def test_extra_keys_is_a_superset_of_every_bundled_role_s_to_extra_keys() -> None:
    exempt = RoleDef.extra_keys()
    for role in PREDEFINED:
        assert set(role.to_extra()) <= exempt, role.slug


def test_extra_keys_is_a_superset_of_a_dev_role_s_to_extra_keys() -> None:
    assert set(dev_role("python").to_extra()) <= RoleDef.extra_keys()


def test_extra_keys_excludes_description() -> None:
    """`description` is deliberately not part of `to_extra()`'s output (it isn't a
    catalog-merged extra field); the key set must stay exactly that, not grow silently."""
    assert "description" not in RoleDef.extra_keys()
