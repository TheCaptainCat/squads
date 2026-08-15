"""Repo-hygiene gate: every dedicated create-time CLI flag that writes an ``Item.extra`` key
(e.g. ``sq create guide --tech``) must back a key that's also reachable through the generic
``sq <type> <n> update --set <field>=<value>`` door (``_models._metadata._GENERIC_FIELDS``).

The bug this guards against: ``guide``'s ``--tech`` flag wrote ``extra["tech"]`` at create time,
but ``tech`` was never registered in ``_GENERIC_FIELDS`` — so once a squad renamed or replaced the
``guide`` type (losing the dedicated flag, which is bound to the literal type name), ``tech`` had
no CLI path at all: not settable at create (no flag), not settable afterwards (``--set`` refuses
an unregistered key). ``tags`` sat right beside it, correctly registered, and kept working after a
rename — proving the fix is registration, not a structural rewrite.

This is a source-text scan (not a full AST walk): ``ExtraKey`` is a plain class of string
constants, not an enum, so ``extra[X.TECH]`` has no runtime membership to introspect without
executing the assignment; regex + ``getattr`` is the same shape squads already tolerates in a
prototype-vocabulary scan, applied to one narrow file.
"""

import re
from pathlib import Path

from squads._models._extras import ExtraKey
from squads._models._metadata import _GENERIC_FIELDS

_ASSIGNMENT_RE = re.compile(r"extra\[X\.(\w+)\]\s*=")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _dedicated_extra_keys(source: str) -> list[str]:
    """The ``ExtraKey`` attribute names behind every ``extra[X.<NAME>] = …`` assignment found
    in *source*, resolved to their string values."""
    names = _ASSIGNMENT_RE.findall(source)
    return [getattr(ExtraKey, name) for name in names]


def test_every_dedicated_create_flag_extra_key_is_settable_via_generic_set() -> None:
    path = _repo_root() / "src" / "squads" / "_cli" / "_create.py"
    keys = _dedicated_extra_keys(path.read_text(encoding="utf-8"))
    assert keys, "expected to find at least the guide --tech/--tag assignments — scan regressed"
    unreachable = [k for k in keys if k not in _GENERIC_FIELDS]
    assert not unreachable, (
        "a dedicated create-time flag writes an extra key with no generic --set path — register "
        f"it in squads._models._metadata._GENERIC_FIELDS: {unreachable}"
    )


def test_the_scan_would_catch_a_planted_unregistered_key() -> None:
    planted = "extra[X.MISSION] = mission\n"  # MISSION is a real ExtraKey, not in _GENERIC_FIELDS
    keys = _dedicated_extra_keys(planted)
    assert keys == [ExtraKey.MISSION]
    assert ExtraKey.MISSION not in _GENERIC_FIELDS
