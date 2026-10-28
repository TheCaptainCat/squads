"""Repo-hygiene gate: every dedicated create-time CLI flag that writes an attribute (e.g. ``sq
create guide --tech``) must back a key that the type declares settable, so the generic ``sq
<type> <n> update --set <field>=<value>`` door reaches it too."""

import re
from pathlib import Path

from squads._models._attributes import AttributeKey
from squads._workflow import bundled_spec

_ASSIGNMENT_RE = re.compile(r"attributes\[AttributeKey\.(\w+)\]\s*=")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _dedicated_attribute_keys(source: str) -> list[str]:
    """The attribute names behind every ``attributes[AttributeKey.<NAME>] = …`` assignment found
    in *source*, resolved to their string values."""
    return [getattr(AttributeKey, name) for name in _ASSIGNMENT_RE.findall(source)]


def _settable_on_guide() -> set[str]:
    return {k for k, a in bundled_spec().item_attributes("guide").items() if a.settable}


def test_every_dedicated_create_flag_attribute_is_settable_via_generic_set() -> None:
    path = _repo_root() / "src" / "squads" / "_cli" / "_create.py"
    keys = _dedicated_attribute_keys(path.read_text(encoding="utf-8"))
    assert keys, "expected to find at least the guide --tech/--tag assignments — scan regressed"
    unreachable = [k for k in keys if k not in _settable_on_guide()]
    assert not unreachable, (
        "a dedicated create-time flag writes an attribute the guide type does not declare "
        f"settable — declare it under [items.guide.attributes]: {unreachable}"
    )


def test_the_scan_would_catch_a_planted_undeclared_key() -> None:
    planted = "attributes[AttributeKey.WHEN_TO_USE] = text\n"  # a real key the guide never declares
    keys = _dedicated_attribute_keys(planted)
    assert keys == [AttributeKey.WHEN_TO_USE]
    assert AttributeKey.WHEN_TO_USE not in _settable_on_guide()
