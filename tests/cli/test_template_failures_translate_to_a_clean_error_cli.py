"""``sq create`` over an item-creation template overridden with a reference to an undefined
variable — the CLI-level half of ``squads._rendering._engine.render``'s ``jinja2.TemplateError``
→ ``SquadsError`` translation (service-level coverage in
``tests/service/test_template_failures_translate_to_a_clean_error.py``). A *view* template
failure and an item-creation template failure produce the identical clean CLI message.
"""

import pytest

from squads._rendering._engine import invalidate_squad_dir

pytestmark = pytest.mark.anyio


def _declare_broken_item_template(squad_dir, item_type: str) -> None:
    templates_dir = squad_dir / ".overrides" / "templates" / "items"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / f"{item_type}.md.j2").write_text(
        "<!-- sq:body -->\n{{ this_variable_does_not_exist }}\n<!-- sq:body:end -->\n",
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


async def test_create_with_a_broken_override_template_exits_1_with_a_clean_message(
    project, invoke
) -> None:
    """Driven through the real ``@common.command`` error boundary, not asserted about in
    isolation: exit 1, the CLI's clean message naming the template, no Python traceback."""
    _declare_broken_item_template(project.squad_dir, "task")

    r = await invoke(["create", "task", "T", "--author", "manager"])

    assert r.exit_code == 1
    assert "task.md.j2" in r.output
    assert "Traceback" not in r.output
    assert "jinja2" not in r.output.lower()
