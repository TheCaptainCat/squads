"""Repo gate: no sub-entity kind, plural or local prefix the bundled spec declares is spelled in
`src/squads` outside the spec layer and the released runners."""

from squads._workflow import bundled_spec
from tests.meta import _vocabulary as vocabulary
from tests.meta._roots import REPO_ROOT


def test_no_bundled_subentity_kind_name_appears_outside_the_spec_layer() -> None:
    hits = vocabulary.tree_hits(REPO_ROOT, bundled_spec(), vocabulary.KIND)
    assert not hits, (
        "the source names a sub-entity kind the bundled spec declares; resolve it from the "
        f"active spec instead:\n{vocabulary.report(hits)}"
    )
