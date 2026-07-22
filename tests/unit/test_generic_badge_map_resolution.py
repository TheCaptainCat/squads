"""The shared generic badge-map resolver ``squads._badges.resolve_badges`` — one path
for ``sq graph``/``sq tree``/``sq list``/``sq show``'s generic per-item ``badges`` map. Proven
once here against the bundled spec's own field/collection vocabulary; the CLI surfaces reuse
this exact function rather than re-deriving the map (see ``tests/cli/test_item_json_badges_map.py``
for the end-to-end surface proof).
"""

from squads._badges import resolve_badges
from squads._workflow import bundled_spec


def test_resolves_every_declared_field_with_a_non_null_value() -> None:
    spec = bundled_spec()
    values = {"priority": "high"}
    assert resolve_badges(spec, "task", values.get) == {"priority": "high"}


def test_omits_a_declared_field_whose_value_is_none() -> None:
    spec = bundled_spec()
    assert resolve_badges(spec, "task", lambda _code: None) == {}


def test_a_type_with_no_declared_fields_resolves_to_an_empty_map() -> None:
    spec = bundled_spec()
    # role is a roster type: no badge fields declared.
    assert resolve_badges(spec, "role", lambda _code: "whatever") == {}


def test_resolves_multiple_declared_fields_on_the_same_type() -> None:
    spec = bundled_spec()
    values = {"priority": "high", "severity": "critical"}
    assert resolve_badges(spec, "bug", values.get) == {
        "priority": "high",
        "severity": "critical",
    }


def test_resolves_by_subentity_kind_the_same_way_as_by_item_type() -> None:
    spec = bundled_spec()
    values = {"severity": "info"}
    assert resolve_badges(spec, "finding", values.get) == {"severity": "info"}


def test_an_undeclared_type_or_kind_degrades_to_an_empty_map_not_a_crash() -> None:
    spec = bundled_spec()
    assert resolve_badges(spec, "not-a-real-type-or-kind", lambda _code: "x") == {}
