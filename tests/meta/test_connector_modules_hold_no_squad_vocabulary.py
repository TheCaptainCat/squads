"""Repo gate: a connector module spells no name the bundled spec declares, whether an item type, a
badge field or value, a ref kind or a status; the tracker's own API names are allowed."""

from pathlib import Path

from squads._workflow import bundled_spec
from tests.meta import _vocabulary as vocabulary
from tests.meta._roots import REPO_ROOT

_CATEGORIES = (
    vocabulary.TYPE,
    vocabulary.FIELD,
    vocabulary.REF,
    vocabulary.STATUS,
    vocabulary.KIND,
)


def _connector_hits(root: Path) -> list[vocabulary.Hit]:
    return [
        hit
        for hit in vocabulary.tree_hits(root, bundled_spec(), *_CATEGORIES)
        if hit.path.startswith("src/squads/_sources/")
    ]


def test_no_connector_module_spells_a_bundled_vocabulary_name() -> None:
    hits = _connector_hits(REPO_ROOT)
    assert not hits, (
        "a connector module names squad vocabulary; map tracker values through the source's "
        f"maps instead:\n{vocabulary.report(hits)}"
    )


def test_the_scan_sees_a_type_name_planted_in_a_connector_module(tmp_path: Path) -> None:
    spec = bundled_spec()
    planted = sorted(vocabulary.vocabulary(spec, vocabulary.TYPE))[0]
    module = tmp_path / "src" / "squads" / "_sources" / "_planted.py"
    module.parent.mkdir(parents=True)
    module.write_text(f"KIND = {planted!r}\n", encoding="utf-8")
    assert [hit.name for hit in _connector_hits(tmp_path)] == [planted]


def test_a_vocabulary_word_outside_the_exempt_constant_of_the_same_module_is_caught(
    tmp_path: Path,
) -> None:
    module, constant, _ = vocabulary.EXEMPT_TRACKER_ENUMS[0]
    spec = bundled_spec()
    planted = sorted(vocabulary.vocabulary(spec, vocabulary.TYPE))[0]
    target = tmp_path / module
    target.parent.mkdir(parents=True)
    target.write_text(f"{constant} = ({planted!r},)\nOTHER = ({planted!r},)\n", encoding="utf-8")
    assert [(hit.name, hit.lineno) for hit in _connector_hits(tmp_path)] == [(planted, 2)]
