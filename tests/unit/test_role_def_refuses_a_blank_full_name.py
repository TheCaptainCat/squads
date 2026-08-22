"""``RoleDef.__post_init__`` is the single seam that refuses a blank/whitespace-only
``full_name``, pinned directly rather than only through the two CLI commands that reach it
(``sq dev add --name``, ``sq role activate --name`` -- see the CLI-level drive in
``tests/cli/test_blank_role_name_is_refused_at_the_shared_seam.py``).

All three construction paths converge here: the override merge
(``_apply_override``/``role_spec_to_def``), ``activate_role``'s ``dataclasses.replace`` (which
re-runs ``__post_init__`` on a frozen dataclass exactly like the constructor), and ``add_dev``'s
``dev_role()`` call. One rule, enforced once, at the point they all actually meet.
"""

import dataclasses

import pytest

from squads._errors import SquadsError
from squads._roles._catalog import PREDEFINED, RoleDef, dev_role


def _role(full_name: str) -> RoleDef:
    return RoleDef(
        slug="example",
        full_name=full_name,
        title="Example role",
        description="Does example things.",
        mission="Do example things.",
    )


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"], ids=["empty", "spaces", "tab-newline"])
def test_constructing_a_roledef_directly_with_a_blank_full_name_is_refused(blank):
    with pytest.raises(SquadsError) as excinfo:
        _role(blank)
    assert "full_name" in str(excinfo.value)


@pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "spaces"])
def test_dataclasses_replace_with_a_blank_full_name_is_refused(blank):
    """The exact mechanism ``activate_role`` uses (``dc_replace(role, full_name=name)``) --
    pinned on a frozen dataclass to confirm ``__post_init__`` re-runs on ``replace``, not only
    on the original constructor call."""
    base = PREDEFINED[0]
    with pytest.raises(SquadsError) as excinfo:
        dataclasses.replace(base, full_name=blank)
    assert "full_name" in str(excinfo.value)


@pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "spaces"])
def test_dev_role_with_an_explicit_blank_name_is_refused(blank):
    """The exact mechanism ``add_dev`` uses. ``dev_role`` tests ``name is not None`` (not a
    falsy check), so an explicitly-passed blank name is not silently treated as "no name
    given" -- it reaches the same seam and is refused."""
    with pytest.raises(SquadsError) as excinfo:
        dev_role("go", name=blank)
    assert "full_name" in str(excinfo.value)


def test_dev_role_with_no_name_falls_back_to_the_pool_unaffected():
    """``name=None`` (omitted entirely) is not the blank case -- it still falls back to the
    pool name, unchanged by this fix."""
    role = dev_role("go")
    assert role.full_name.strip()
    assert role.full_name != ""


def test_a_valid_full_name_with_internal_whitespace_is_unaffected():
    role = _role("Ada Lovelace")
    assert role.full_name == "Ada Lovelace"


def test_leading_and_trailing_whitespace_around_real_content_is_preserved_not_trimmed():
    """Decision: padding around real content is accepted and stored verbatim -- ``.strip()``
    is used only to test for blankness, never to normalise the stored value, matching the
    override path's own ``_refuse_blank_strings``."""
    role = _role("  Ada Lovelace  ")
    assert role.full_name == "  Ada Lovelace  "


def test_the_bundled_catalog_still_constructs_cleanly():
    """Every bundled role's real ``full_name`` must not trip the new check."""
    assert len(PREDEFINED) == 8
    for role in PREDEFINED:
        assert role.full_name.strip()
