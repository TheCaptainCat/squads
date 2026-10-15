"""`ref_rule_target_typed` at the CLI: `sq check` exits 0 for a finding at `warn` and 3 at
`@error` and its `--json` carries the item; `sq create --ref` with a misdirected ref exits 1
only at `@error`; `ref add` is not gated, and the item's next `update` is refused until
`ref rm`; `sq workflow lint` refuses the check on a type with no typed rule.
"""

import json

import pytest

from _helpers import create_item
from _selection_table import write_override
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_RULES = '[items.feature]\nref_rules = [{ kind = "implements", target = "contract" }]\n'


def _toml(entry: str) -> str:
    return _RULES + f'validators = ["{entry}"]\n'


@pytest.mark.parametrize(
    ("entry", "exit_code", "level"),
    [("ref_rule_target_typed", 0, "warn"), ("ref_rule_target_typed@error", 3, "error")],
)
async def test_check_exit_code_follows_the_level_after_ref_add(
    project, invoke, entry, exit_code, level
) -> None:
    write_override(project.squad_dir, _RULES)
    svc = service.open_service()
    feature = (await create_item(svc, "feature", "source")).item
    wrong = (await create_item(svc, "task", "wrong")).item
    write_override(project.squad_dir, _toml(entry))

    added = await invoke(
        ["feature", str(feature.sequence_id), "ref", "add", wrong.id, "--kind", "implements"]
    )
    assert added.exit_code == 0, added.output
    text = await invoke(["check"])
    assert text.exit_code == exit_code, text.output
    assert "refs must point at a contract" in text.output
    rows = [
        r
        for r in json.loads((await invoke(["check", "--json"])).output)
        if r.get("item") == feature.id
    ]
    assert [r["level"] for r in rows] == [level]

    updated = await invoke(["feature", str(feature.sequence_id), "update", "--add-label", "x"])
    assert updated.exit_code == (1 if level == "error" else 0), updated.output
    removed = await invoke(["feature", str(feature.sequence_id), "ref", "rm", wrong.id])
    assert removed.exit_code == 0, removed.output
    assert (await invoke(["check"])).exit_code == 0


@pytest.mark.parametrize(
    ("entry", "create_exit"),
    [("ref_rule_target_typed", 0), ("ref_rule_target_typed@error", 1)],
)
async def test_create_with_a_misdirected_ref_is_refused_only_at_error(
    project, invoke, entry, create_exit
) -> None:
    write_override(project.squad_dir, _RULES)
    wrong = (await create_item(service.open_service(), "task", "wrong")).item
    write_override(project.squad_dir, _toml(entry))
    created = await invoke(
        ["create", "feature", "f", "--author", "manager", "--ref", f"{wrong.id}:implements"]
    )
    assert created.exit_code == create_exit, created.output


async def test_lint_refuses_the_check_on_a_type_with_no_typed_rule(project, invoke) -> None:
    write_override(project.squad_dir, '[items.task]\nvalidators = ["ref_rule_target_typed"]\n')
    linted = await invoke(["workflow", "lint"])
    assert linted.exit_code == 1, linted.output
    assert "ref_rules" in linted.output
