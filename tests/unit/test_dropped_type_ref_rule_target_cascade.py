"""Dropping a non-reserved bundled type through ``[selected].items`` must leave the squad
usable with no second edit in another type's block — the same courtesy
``_prune_orphaned_type_owned_views`` already gives a dropped type's own bundled view (see
``test_milestone_view_deselect_cascade.py``), extended to the ``RefRule.target``/
``ref_rule_target_present:<T>`` coupling onto ``contract``.

Both halves of that coupling are driven, from their two different sources: ``feature``'s
``ref_rules`` entry targeting ``contract`` is bundled, while a ``ref_rule_target_present:
contract`` validator over it is opt-in — nothing bundled selects it — so the validator half is
exercised through an override that declares it, which is the only way an adopter can meet it.

Driven across the bundled non-roster surface: dropping most types is already a clean no-op
(nothing targets them); ``contract`` is the one bundled type another type's block actually
names, so it is the one this cascade exists for. ``parents`` stays a deliberately unchanged,
pre-existing coupling — ``epic``/``feature`` are excluded here on purpose.
"""

from pathlib import Path

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import load_workflow_spec
from squads._workflow._loader import lint_workflow_spec

_WITHOUT_CONTRACT = (
    '[selected]\nitems = ["epic", "feature", "task", "bug", "decision", "milestone", '
    '"review", "guide", "role", "skill", "operator"]\n'
)


def _write_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


def test_dropping_contract_strips_the_stale_ref_rules_entry_from_feature(
    tmp_path: Path,
) -> None:
    _write_override(tmp_path, _WITHOUT_CONTRACT)

    spec = load_workflow_spec(squad_dir=tmp_path)

    assert "contract" not in spec.items
    assert all(rr.target != "contract" for rr in spec.items["feature"].ref_rules)


def test_dropping_contract_strips_an_opted_in_validator_selecting_it(tmp_path: Path) -> None:
    """The validator half of the same cascade. It has to be declared here to be tested at all:
    the bundled document types ``feature``'s implements edge without requiring it, so a squad
    only carries ``ref_rule_target_present:contract`` if its own override adds it — and that
    squad is exactly the one whose spec would otherwise refuse to load after the drop, with the
    offending line sitting in a type block it never edited."""
    _write_override(
        tmp_path,
        _WITHOUT_CONTRACT
        + '\n[items.feature]\nvalidators = ["ref_rule_target_present:contract"]\n',
    )

    spec = load_workflow_spec(squad_dir=tmp_path)

    assert "contract" not in spec.items
    assert spec.items["feature"].validators == []


def test_dropping_contract_lints_clean_not_just_loads_clean(tmp_path: Path) -> None:
    """The strip must run wherever the merged mapping is validated, not only in the fail-fast
    loader — otherwise ``sq workflow lint`` reports the stale coupling as an error on a squad
    that ``open_service`` accepts, and the two disagree about the same override."""
    _write_override(tmp_path, _WITHOUT_CONTRACT)

    findings = lint_workflow_spec(tmp_path)

    assert [f for f in findings if f[0] == "error"] == []


@pytest.mark.parametrize("drop_type", ["task", "bug", "decision", "milestone", "review", "guide"])
def test_dropping_any_other_non_reserved_type_stays_a_clean_no_op(
    tmp_path: Path, drop_type: str
) -> None:
    """Every other bundled non-roster type drops with no companion edit already — nothing
    else's ``ref_rules``/``validators`` names it. Proven across the whole set so a future
    coupling added elsewhere is caught by this same test, not assumed clean by omission."""
    kept = [
        t
        for t in (
            "epic",
            "feature",
            "task",
            "bug",
            "decision",
            "contract",
            "milestone",
            "review",
            "guide",
        )
        if t != drop_type
    ] + ["role", "skill", "operator"]
    _write_override(tmp_path, f"[selected]\nitems = {kept!r}\n")

    spec = load_workflow_spec(squad_dir=tmp_path)

    assert drop_type not in spec.items


def test_epic_and_feature_still_fail_on_their_own_pre_existing_parents_coupling(
    tmp_path: Path,
) -> None:
    """Scope proof: the strip targets ``ref_rules``/``validators`` only, never ``parents`` —
    dropping ``epic`` still bricks ``feature`` (its ``parents = ["epic"]``), unchanged, because
    that coupling is deliberately out of scope here."""
    _write_override(
        tmp_path,
        '[selected]\nitems = ["feature", "task", "bug", "decision", "contract", '
        '"milestone", "review", "guide", "role", "skill", "operator"]\n',
    )
    with pytest.raises(SquadsError, match="parent type 'epic' not declared"):
        load_workflow_spec(squad_dir=tmp_path)
