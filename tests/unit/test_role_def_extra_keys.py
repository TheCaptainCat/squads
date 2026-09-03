"""``RoleDef``'s stored ``extra``: the short residue a role item still carries, and the exact
key set exempted from the skew guard (``PERMITTED_EXTRA_SKEW``).

A role's *definition* is no longer stored on its item. Title, mission, responsibilities,
agreements, colour, spawn authority and description are catalog answers resolved on every read,
and the resolved full name lands on the item's own ``title`` field rather than in ``extra``. So
``to_extra()`` writes what no document answers: the dispatch ``slug``, plus ``model`` for a
developer role, whose model is an operator setting (``sq dev add --model``) that
``dev_base_from_item`` reads straight back off the item.

``extra_keys()`` reads both key columns rather than any instance's ``to_extra()`` *output*, so
the exempt set and the values it is paired with cannot drift apart, and the ``is_dev`` branch
cannot silently shrink the guard's vocabulary.
"""

from squads._itemfile import PERMITTED_EXTRA_SKEW
from squads._models._extras import ExtraKey as X
from squads._roles._catalog import PREDEFINED, RoleDef, dev_role

#: Every key the definition used to be mirrored under. Named once, as a literal, so each
#: assertion below tests the same removal rather than a hand-copied subset of it.
_REMOVED_FROM_THE_MIRROR = (
    X.FULL_NAME,
    X.TITLE,
    X.MISSION,
    X.RESPONSIBILITIES,
    X.AGREEMENTS,
    X.COLOR,
    X.CAN_SPAWN,
    X.DESCRIPTION,
)


def test_extra_keys_covers_every_bundled_role_s_to_extra_keys() -> None:
    exempt = RoleDef.extra_keys()
    for role in PREDEFINED:
        assert set(role.to_extra()) <= exempt, role.slug


def test_extra_keys_covers_a_dev_role_s_to_extra_keys() -> None:
    assert set(dev_role("python").to_extra(is_dev=True)) <= RoleDef.extra_keys()


def test_to_extra_stores_none_of_the_definition_fields() -> None:
    """The negative clause the whole change turns on: none of the fields the role catalog
    answers is written back onto the item, for a bundled role or a developer one."""
    for role in PREDEFINED:
        stored = role.to_extra()
        for key in _REMOVED_FROM_THE_MIRROR:
            assert key not in stored, f"{role.slug} still stores {key!r}"
    dev_stored = dev_role("python").to_extra(is_dev=True)
    for key in _REMOVED_FROM_THE_MIRROR:
        assert key not in dev_stored, f"a dev role still stores {key!r}"


def test_model_is_written_for_a_dev_role_and_withheld_from_a_bundled_one() -> None:
    """The one conditional key. A developer's model has no catalog answer to resolve from, so
    it is stored; a bundled role's comes from the catalog, so storing it would be a mirror
    again. The flag is the caller's, not a function of the slug's spelling."""
    assert dev_role("python", model="opus").to_extra(is_dev=True)[X.MODEL] == "opus"
    assert X.MODEL not in dev_role("python", model="opus").to_extra()
    for role in PREDEFINED:
        assert X.MODEL not in role.to_extra(), role.slug


def test_slug_is_stored_for_every_role_shape() -> None:
    for role in PREDEFINED:
        assert role.to_extra()[X.SLUG] == role.slug
    assert dev_role("python").to_extra()[X.SLUG] == "python-dev"


def test_permitted_extra_skew_membership_is_pinned_exactly() -> None:
    """Pinned to the literal key names, not re-derived from `RoleDef.extra_keys()` -- that
    would be circular and pass even if the table silently grew a member. This test exists to
    catch an unreviewed **widening**, which is the unsafe direction: a key that leaves the set
    is compared like any other field again, which can only produce a spurious (repair-clearable)
    refusal, never a masked skew.

    The literal is deliberately much shorter than it was. `full_name`, `title`, `mission`,
    `responsibilities`, `agreements`, `color` and `can_spawn` left with the mirror they
    belonged to -- the definition is resolved on read now, and nothing writes those keys, so
    there is nothing left for the guard to forgive on them. `is_default` never was a member of
    this pin's purpose in the first place and is written only by `sq role set-default`;
    `description` was reconciled but deliberately never exempt, and is no longer written at all.
    A narrower pin can only start failing by catching a widening nobody reviewed."""
    expected = frozenset({X.SLUG, X.MODEL})
    assert expected == PERMITTED_EXTRA_SKEW
    for key in _REMOVED_FROM_THE_MIRROR:
        assert key not in PERMITTED_EXTRA_SKEW, key
    assert X.IS_DEFAULT not in PERMITTED_EXTRA_SKEW
