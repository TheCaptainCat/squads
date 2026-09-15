"""``_prune_orphaned_type_owned_views`` takes a *bundled* view with it when ``[selected].items``
drops the bundled type that owns it (``items.<type>.views``, read straight off the bundled
``workflow.toml`` — never an override-declared attachment, which an adopter fully controls on
both ends already). Scoped precisely so a genuinely freestanding view — one no type's own
``views`` list ever named — is never touched.

No bundled type carries that attachment any more: ``milestone_rollup`` — the last one that
did — moved onto a ``sq:view:milestone_rollup`` tag seeded straight into
``templates/items/milestone.md.j2`` instead, the same mechanism ``role_definition`` and the
four system-skill views already use. It is therefore **freestanding**, exactly like those
five: selecting or deselecting ``milestone`` changes nothing about whether it stays declared —
the first two tests below pin that directly.

The prune mechanism itself is not deleted by that change (only its one bundled example is), so
the remaining three tests keep it covered by monkeypatching ``_bundled_raw`` to simulate a
bundled type owning a view — reusing ``milestone_rollup``'s own declaration (a ``ref`` source,
so it applies to any host type) rather than inventing a second view, table-driven across the
three shapes that matter: a bundled attachment prunes when its one owner drops; a second owner
keeps the view alive after the first drops; an unrelated deselect touches neither.
"""

import copy
from pathlib import Path
from typing import Any

import pytest

from squads import __version__
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import _loader as loader
from squads._workflow import load_workflow_spec

#: Every bundled type except milestone and guide — the latter is this module's own stand-in
#: owner (see :func:`_bundled_raw_with_guide_owning_milestone_rollup`), kept out of the base
#: list so each test controls whether it is selected.
_BASE_ITEMS = [
    "epic",
    "feature",
    "task",
    "bug",
    "decision",
    "contract",
    "review",
    "role",
    "skill",
    "operator",
]


def _write_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


def _selected(items: list[str]) -> str:
    quoted = ", ".join(f'"{t}"' for t in items)
    return f"[selected]\nitems = [{quoted}]\n"


# --------------------------------------------------------------------------- current reality:
# milestone_rollup is freestanding


def test_milestone_rollup_is_freestanding_and_survives_deselecting_milestone(
    tmp_path: Path,
) -> None:
    _write_override(tmp_path, _selected([*_BASE_ITEMS, "guide"]))
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "milestone" not in spec.items
    assert "milestone_rollup" in spec.views  # no owner to prune it — it never had one


def test_an_adopter_declared_freestanding_view_is_never_touched_either(tmp_path: Path) -> None:
    """The ordinary, already-tested shape every other view mechanism test uses — an
    adopter-declared view no type's ``views`` list ever named — survives any deselect,
    same as the bundled example above."""
    _write_override(
        tmp_path,
        '[views.freestanding]\nsource = { kind = "ref", name = "related" }\n'
        'fields = [ { code = "id", label = "Id" } ]\n\n' + _selected([*_BASE_ITEMS, "guide"]),
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "milestone" not in spec.items
    assert "milestone_rollup" in spec.views
    assert "freestanding" in spec.views


# --------------------------------------------------------------------------- the prune mechanism
# itself, kept covered via a simulated bundled attachment


#: Captured before any test monkeypatches ``loader._bundled_raw`` — the fake below calls this,
#: never the (possibly already-patched) module attribute, so patching stays a one-level
#: substitution rather than a self-reference.
_real_bundled_raw = loader._bundled_raw


def _bundled_raw_with_guide_owning_milestone_rollup() -> dict[str, Any]:
    """The real bundled raw mapping, with one addition: ``guide`` attaches
    ``milestone_rollup`` the way ``milestone`` itself used to. Reuses the real declaration
    (a ``ref`` source, so it applies to any host type) rather than fabricating a second view,
    so this stays a minimal simulation of "a bundled type owns a bundled view", not a new
    fixture to keep in sync with the real one."""
    faked = copy.deepcopy(_real_bundled_raw())
    faked["items"]["guide"]["views"] = ["milestone_rollup"]
    return faked


@pytest.fixture
def guide_owns_milestone_rollup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loader, "_bundled_raw", _bundled_raw_with_guide_owning_milestone_rollup)


def test_a_bundled_type_owned_view_is_pruned_when_its_one_owner_drops(
    tmp_path: Path, guide_owns_milestone_rollup: None
) -> None:
    _write_override(tmp_path, _selected(_BASE_ITEMS))  # "guide" left out
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "guide" not in spec.items
    assert "milestone_rollup" not in spec.views


def test_dropping_an_unrelated_type_leaves_a_bundled_owned_view_declared(
    tmp_path: Path, guide_owns_milestone_rollup: None
) -> None:
    without_task = [t for t in _BASE_ITEMS if t != "task"]
    _write_override(tmp_path, _selected([*without_task, "guide"]))
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "task" not in spec.items
    assert "milestone_rollup" in spec.views
    assert spec.items["guide"].views == ["milestone_rollup"]


def test_a_bundled_owned_view_with_a_surviving_second_owner_is_not_pruned(
    tmp_path: Path, guide_owns_milestone_rollup: None
) -> None:
    """A second bundled type attaching the same view keeps it alive after the first is
    dropped — the prune is "no surviving owner left", not "this one owner was dropped". Adds
    the second attachment via override, on a *different* still-selected type (``contract``),
    proving the survivor need not itself be a bundled owner to count."""
    _write_override(
        tmp_path,
        '[items.contract]\nviews = ["milestone_rollup"]\n\n' + _selected(_BASE_ITEMS),
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "guide" not in spec.items
    assert "milestone_rollup" in spec.views
    assert spec.items["contract"].views == ["milestone_rollup"]
