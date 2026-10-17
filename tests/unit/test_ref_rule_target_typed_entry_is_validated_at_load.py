"""The `ref_rule_target_typed` entry at spec load: it takes no parameter, and a type that
declares no ref rule with a target cannot select it. When the only typed rule was removed
because its target type was dropped through `[selected]`, the refusal says so.
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


def test_the_entry_takes_no_parameter(tmp_path: Path) -> None:
    _write_override(tmp_path, '[items.feature]\nvalidators = ["ref_rule_target_typed:contract"]\n')
    with pytest.raises(SquadsError, match="takes no param"):
        load_workflow_spec(squad_dir=tmp_path)


def test_the_check_is_refused_on_a_type_with_no_typed_rule(tmp_path: Path) -> None:
    _write_override(tmp_path, '[items.task]\nvalidators = ["ref_rule_target_typed"]\n')
    with pytest.raises(SquadsError) as raised:
        load_workflow_spec(squad_dir=tmp_path)
    text = str(raised.value)
    assert "item 'task'" in text
    assert "'ref_rule_target_typed'" in text
    assert "needs a ref_rules entry with a target" in text


def test_a_rule_without_a_target_does_not_make_the_check_selectable(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        '[items.task]\nref_rules = [{ kind = "fixes" }]\nvalidators = ["ref_rule_target_typed"]\n',
    )
    with pytest.raises(SquadsError, match="needs a ref_rules entry with a target"):
        load_workflow_spec(squad_dir=tmp_path)


def test_dropping_the_target_type_leaves_a_selecting_type_refused_and_says_why(
    tmp_path: Path,
) -> None:
    _write_override(
        tmp_path, _WITHOUT_CONTRACT + '\n[items.feature]\nvalidators = ["ref_rule_target_typed"]\n'
    )
    with pytest.raises(SquadsError) as raised:
        load_workflow_spec(squad_dir=tmp_path)
    assert "item 'feature'" in str(raised.value)
    assert "removed with it" in str(raised.value)
    errors = [f for f in lint_workflow_spec(tmp_path) if f[0] == "error"]
    assert any("removed with it" in f[2] for f in errors), errors


def test_dropping_the_target_type_is_clean_while_the_check_is_not_selected(tmp_path: Path) -> None:
    _write_override(tmp_path, _WITHOUT_CONTRACT)
    load_workflow_spec(squad_dir=tmp_path)
