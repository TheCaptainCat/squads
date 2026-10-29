"""Repo gate: the agent-facing text squads generates for the override test squad names nothing the
bundled spec declares and that squad drops, and no bundled role slug its roster lacks.

The squad keeps the `minimal` roster and has every backend, so the `CLAUDE.md` and `AGENTS.md`
sections, the squads skill, the per-type skills, the memory and greeting skills and the role
pointers are read from disk as written.
"""

from pathlib import Path

import pytest

from squads._models._config import SquadsConfig
from squads._paths import SquadPaths
from squads._roles._catalog import get_catalog
from squads._workflow import bundled_spec
from squads._workflow._loader import load_workflow_spec
from tests._override_populated import OVERRIDE
from tests._squads import init_overridden
from tests.meta import _vocabulary as vocabulary

_CATEGORIES = (
    vocabulary.REF,
    vocabulary.STATUS,
    vocabulary.KIND,
    vocabulary.TYPE,
    vocabulary.FIELD,
)
_SQUAD_DIR = "team"


def _override_squad(root: Path) -> None:
    init_overridden(root, OVERRIDE, squad_dir=_SQUAD_DIR, backend=["claude_code", "agents_md"])


def _generated_files(root: Path) -> list[Path]:
    """Every markdown file squads wrote for an agent: the root files, `.claude/` and the squad's
    `agents/` folder."""
    found = [root / name for name in ("CLAUDE.md", "AGENTS.md")]
    found += sorted((root / ".claude").rglob("*.md"))
    found += sorted((root / _SQUAD_DIR / "agents").rglob("*.md"))
    return [path for path in found if path.is_file()]


def _hits(root: Path, names: vocabulary.Vocabulary) -> list[vocabulary.Hit]:
    return [
        hit
        for path in _generated_files(root)
        for hit in vocabulary.span_hits_in(
            path.read_text(encoding="utf-8"), path.relative_to(root).as_posix(), names
        )
    ]


def _dropped_names(squad_dir: Path) -> vocabulary.Vocabulary:
    kept = vocabulary.vocabulary(load_workflow_spec(squad_dir), *_CATEGORIES)
    return vocabulary.dropped(vocabulary.vocabulary(bundled_spec(), *_CATEGORIES), kept)


def test_generated_text_names_no_vocabulary_the_override_squad_dropped(
    copy_squad,
) -> None:
    paths: SquadPaths = copy_squad("generated-text", _override_squad)
    names = _dropped_names(paths.squad_dir)
    categories = {category for owners in names.values() for category in owners}
    assert categories == set(_CATEGORIES), "the override squad drops no name of some category"

    hits = _hits(paths.root, names)

    assert not hits, (
        "generated agent text names vocabulary the active spec dropped; derive it from the "
        f"active spec:\n{vocabulary.report(hits)}"
    )


def test_generated_text_reads_the_squad_directory_it_was_given(copy_squad) -> None:
    paths: SquadPaths = copy_squad("generated-text", _override_squad)
    default = SquadsConfig.model_fields["squad_dir"].default
    text = {path: path.read_text(encoding="utf-8") for path in _generated_files(paths.root)}

    assert any(f"{_SQUAD_DIR}/" in body for body in text.values()), "no text names the squad dir"
    stale = sorted(
        path.name for path, body in text.items() if f"{default}/" in body.replace(_SQUAD_DIR, "")
    )
    assert not stale, f"text still names the default squad directory: {stale}"


def test_generated_text_names_no_bundled_role_the_roster_lacks(copy_squad) -> None:
    paths: SquadPaths = copy_squad("generated-text", _override_squad)
    present = {
        path.stem.split("-", 2)[-1] for path in (paths.squad_dir / "agents" / "roles").glob("*.md")
    }
    absent = {
        role.slug: frozenset({"role"}) for role in get_catalog().roles if role.slug not in present
    }
    assert absent, "the minimal roster keeps every bundled role"

    hits = _hits(paths.root, absent)

    assert not hits, (
        "generated agent text names a bundled role the roster does not hold:\n"
        f"{vocabulary.report(hits)}"
    )


@pytest.mark.parametrize("name", ["CLAUDE.md", "AGENTS.md"])
def test_both_backends_write_their_section(copy_squad, name: str) -> None:
    paths: SquadPaths = copy_squad("generated-text", _override_squad)

    assert (paths.root / name).is_file()
