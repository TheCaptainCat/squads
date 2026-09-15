"""A structural guarantee for the ``role``/``playbook``/``self`` source path: no
``Cell``/``_RawRecord``/``ViewRecord`` is ever constructed on it — the exact flattening the
source-widening decision retired the middle layer to stop doing. Checked against the actual
parsed body of every function on that path (never by inspection or a comment), so a future edit
that starts routing one of the three new kinds through the projection wrapper fails this test on
sight."""

import ast
import inspect
from collections.abc import Callable

from squads import _views as views

#: Every function on the role/playbook/self path — the resolvers plus the two render functions
#: that dispatch a non-relation kind straight to its template, bypassing project()/Projection
#: entirely.
_NEW_KIND_PATH_FUNCTIONS = (
    views._resolve_role_source,
    views._resolve_playbook_source,
    views._resolve_self_source,
    views.render_source_view,
)

#: The middle layer's own names — a hit anywhere in the functions above means one of them
#: started flattening a non-relation result into a projectable row.
_MIDDLE_LAYER_NAMES = frozenset({"Cell", "_RawRecord", "ViewRecord"})


def _identifier_names(fn: Callable[..., object]) -> set[str]:
    tree = ast.parse(inspect.getsource(fn))
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }


def test_no_middle_layer_name_appears_in_any_new_kind_path_function() -> None:
    for fn in _NEW_KIND_PATH_FUNCTIONS:
        hit = _identifier_names(fn) & _MIDDLE_LAYER_NAMES
        assert not hit, f"{fn.__name__} references {hit} — the middle layer must stay out"


def test_the_check_actually_detects_a_middle_layer_reference() -> None:
    """Control: the *relation* path's own resolver genuinely does reference ``_RawRecord`` (its
    return type), proving the scan above is not vacuously passing over every function it's
    handed."""
    assert "_RawRecord" in _identifier_names(views._resolve_ref_source)


def test_render_resolved_source_branches_but_never_names_the_middle_layer_for_the_new_kinds() -> (
    None
):
    """``render_resolved_source`` itself DOES reference ``Projection``/``project`` for the
    relation half of its branch (by design — that half is unchanged) — this only pins the
    ``render_source_view`` half it delegates the three new kinds to, which is covered above; this
    test documents why ``render_resolved_source`` itself is deliberately absent from the sweep."""
    names = _identifier_names(views.render_resolved_source)
    assert "project" in names  # the relation half survives, unmodified
    assert not (names & _MIDDLE_LAYER_NAMES)  # no bare Cell/_RawRecord/ViewRecord reference
