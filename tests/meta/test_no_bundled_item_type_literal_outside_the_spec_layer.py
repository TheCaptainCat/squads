"""Repo gate: no work-item type, ID prefix or alias the bundled spec declares is spelled in
`src/squads` outside the spec layer and the released runners."""

from squads._workflow import bundled_spec
from tests.meta import _vocabulary as vocabulary
from tests.meta._roots import REPO_ROOT


def test_no_bundled_item_type_name_appears_outside_the_spec_layer() -> None:
    hits = vocabulary.tree_hits(REPO_ROOT, bundled_spec(), vocabulary.TYPE)
    assert not hits, (
        "the source names an item type the bundled spec declares; resolve it from the active "
        f"spec instead:\n{vocabulary.report(hits)}"
    )
