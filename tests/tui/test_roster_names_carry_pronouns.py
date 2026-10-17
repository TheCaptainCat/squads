"""``sq ui`` prints a role's or operator's name with its pronouns in the tree, under the display
setting, and an item's own node is unchanged."""

from dataclasses import replace
from typing import Any

import pytest

pytest.importorskip("textual")

from textual.widgets import Tree

from _helpers import create_item
from squads._paths import load_config
from squads._tui._app import SquadsApp

pytestmark = pytest.mark.anyio


def _labels(tree: Tree[Any]) -> list[str]:
    out: list[str] = []

    def walk(node: Any) -> None:
        out.append(str(node.label))
        for child in node.children:
            walk(child)

    walk(tree.root)
    return out


# (id, display on, role value, operator value, expected role label, expected operator label)
CASES = [
    ("on", True, "she/her", "he/him", "Robert Architect (she/her)", "Alex Rivera (he/him)"),
    ("off", False, "she/her", "he/him", "Robert Architect", "Alex Rivera"),
    ("unset", True, None, None, "Robert Architect", "Alex Rivera"),
    ("brackets", True, "[x]", "[x]", "Robert Architect ([x])", "Alex Rivera ([x])"),
]


@pytest.mark.parametrize(
    ("case", "on", "role", "op", "role_label", "op_label"), CASES, ids=[c[0] for c in CASES]
)
async def test_the_roster_nodes_print_name_and_pronouns_under_the_setting(
    svc, case, on, role, op, role_label, op_label
):
    await svc.activate_role("architect", pronouns=role)
    await svc.add_operator("Alex Rivera", pronouns=op)
    task = (await create_item(svc, "task", "A task", author="architect")).item
    if not on:
        path = svc.paths.config_path
        path.write_text(
            path.read_text(encoding="utf-8") + "\n[display]\npronouns = false\n", encoding="utf-8"
        )
        svc = type(svc)(replace(svc.paths, config=load_config(path)))

    app = SquadsApp(svc)
    async with app.run_test() as pilot:
        await pilot.pause()
        labels = _labels(app.screen.query_one(Tree))

    assert any(role_label in label and "()" not in label for label in labels)
    assert any(op_label in label and "()" not in label for label in labels)
    assert any(f"{task.id} A task" in label for label in labels)
    if not on:
        assert not any("(she/her)" in label or "(he/him)" in label for label in labels)
