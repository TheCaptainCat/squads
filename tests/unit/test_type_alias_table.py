"""The bundled spec's type-alias table: no alias appears twice, and no alias collides with
a canonical type name. CLI-surface alias resolution (deep-chain equivalence, JSON/error
canonical naming) lives in tests/cli/test_type_aliases_cli.py.
"""

from _helpers import WORK_TYPES
from squads._workflow import load_workflow_spec


def test_no_alias_is_declared_twice_across_the_bundled_types() -> None:
    spec = load_workflow_spec()
    all_aliases = [a for t in WORK_TYPES for a in spec.items[t].aliases]
    assert len(all_aliases) == len(set(all_aliases))


def test_no_alias_collides_with_a_canonical_type_name() -> None:
    spec = load_workflow_spec()
    all_aliases = [a for t in WORK_TYPES for a in spec.items[t].aliases]
    canonical = set(WORK_TYPES)
    for alias in all_aliases:
        assert alias not in canonical, f"alias {alias!r} clashes with a canonical type name"
