"""RoleDef.extra_keys(): the exact key set exempted from the skew guard
(``PERMITTED_EXTRA_SKEW``), derived from ``_EXTRA_FIELD_KEYS`` alone so the exempt set and the
values it's paired with can never drift apart.

``to_extra()``'s own output is a *superset* of ``extra_keys()``, not the reverse: it also
carries ``_RECONCILED_EXTRA_KEYS`` (today, just ``description``) — reconciled into a role
item's ``extra`` on every sync exactly like the exempt fields, but deliberately withheld from
``extra_keys()`` so landing it never widens the skew guard's exemption.
"""

from squads._itemfile import PERMITTED_EXTRA_SKEW
from squads._models._extras import ExtraKey as X
from squads._roles._catalog import PREDEFINED, RoleDef, dev_role


def test_extra_keys_is_a_subset_of_every_bundled_role_s_to_extra_keys() -> None:
    exempt = RoleDef.extra_keys()
    for role in PREDEFINED:
        assert exempt <= set(role.to_extra()), role.slug


def test_extra_keys_is_a_subset_of_a_dev_role_s_to_extra_keys() -> None:
    assert RoleDef.extra_keys() <= set(dev_role("python").to_extra())


def test_extra_keys_excludes_description() -> None:
    """`description` is reconciled into `to_extra()`'s output (so a declared override reaches
    the generated pointer) but deliberately excluded from `extra_keys()` — and so from
    `PERMITTED_EXTRA_SKEW` — because unlike the fields in `_EXTRA_FIELD_KEYS` it has no legacy
    corpus that ever wrote `extra.description` outside a transaction, so there is no lagging
    index for the exemption to forgive."""
    assert "description" not in RoleDef.extra_keys()
    assert "description" in PREDEFINED[0].to_extra()


def test_to_extra_carries_description_alongside_the_exempt_fields() -> None:
    for role in PREDEFINED:
        assert "description" in role.to_extra(), role.slug
    assert "description" in dev_role("python").to_extra()


def test_permitted_extra_skew_membership_is_pinned_exactly() -> None:
    """Pinned to the literal key names, not re-derived from `RoleDef.extra_keys()` -- that
    would be circular and pass even if the table silently grew a member. A dev who lands a
    reconciled-but-not-exempt field (like `description`, see above) by naively appending it to
    `_EXTRA_FIELD_KEYS` instead of `_RECONCILED_EXTRA_KEYS` widens this frozenset -- the unsafe
    direction -- and this is the test built to catch exactly that.

    `X.SKILLS` dropped out of this set with the resolved-skills cache it existed for: the
    cache was never a member of `RoleDef.extra_keys()` (its exemption was the separate first
    term of a union, not a catalog field), and it dies with the writer that persisted it. A
    narrower pin is the safe direction for this particular test -- it can only start failing
    by catching a *widening* nobody reviewed, never by silently accepting one -- so the
    literal below is intentionally reduced rather than re-padded to match the old shape."""
    expected = frozenset(
        {
            X.FULL_NAME,
            X.SLUG,
            X.TITLE,
            X.MISSION,
            X.RESPONSIBILITIES,
            X.AGREEMENTS,
            X.MODEL,
            X.COLOR,
            X.IS_DEFAULT,
            X.CAN_SPAWN,
        }
    )
    assert expected == PERMITTED_EXTRA_SKEW
    assert X.DESCRIPTION not in PERMITTED_EXTRA_SKEW
