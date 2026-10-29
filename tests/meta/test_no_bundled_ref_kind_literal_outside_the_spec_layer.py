"""Repo gate: no ref kind the bundled spec declares is spelled in `src/squads` outside the spec
layer and the released runners, as a string, a flag, in a code span or in a template literal."""

from squads._workflow import bundled_spec
from tests.meta import _vocabulary as vocabulary
from tests.meta._roots import REPO_ROOT


def test_no_bundled_ref_kind_name_appears_outside_the_spec_layer() -> None:
    hits = vocabulary.tree_hits(REPO_ROOT, bundled_spec(), vocabulary.REF)
    assert not hits, (
        "the source names a ref kind the bundled spec declares; resolve it from the active spec "
        f"instead:\n{vocabulary.report(hits)}"
    )
