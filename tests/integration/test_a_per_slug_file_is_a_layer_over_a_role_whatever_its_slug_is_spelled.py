"""A per-slug role file is a layer over a role, whatever its slug is spelled: it never defines
a role, and a slug ending ``-dev`` is no exception.

A slug with a role item is decided by the stored base: a partial file over an activated
``-dev``-suffixed role that defines itself is an ordinary layer. A slug with no role item at
all has nothing under its file, so ``sq check`` reports a layer with no base and ``sq role
<slug> show`` refuses, naming the command that turns the file into a role.
"""

import json

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio


def _place_role_toml(project, slug: str, content: str, *, stamped: bool = False) -> None:
    target = project.squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    stamp = f"# squads:override-base:{__version__}\n" if stamped else ""
    target.write_text(f"{stamp}{content}", encoding="utf-8")


async def test_a_partial_layer_over_a_dev_suffixed_role_that_defines_itself_is_an_ordinary_layer(
    project, svc, invoke
) -> None:
    await svc.add_role(
        "data-dev",
        name="Dana Analyst",
        job_title="data steward",
        description="Curates the datasets.",
        mission="Keep the catalog accurate.",
    )
    _place_role_toml(project, "data-dev", 'title = "Senior data steward"\n')

    checked = await invoke(["check"])
    shown = await invoke(["role", "data-dev", "show", "--json"])

    assert shown.exit_code == 0, shown.output
    assert json.loads(shown.output)["title"] == "Senior data steward"
    assert "no role under it" not in checked.output
    assert "Traceback" not in checked.output and "Traceback" not in shown.output


@pytest.mark.parametrize("content", ['title = "Senior Rust developer"\n', 'full_name = "Rita"\n'])
async def test_a_dev_shaped_file_with_no_role_item_is_a_layer_with_no_base(
    project, invoke, content: str
) -> None:
    """No role exists for ``rust-dev``, so its file has nothing under it; the slug's spelling
    decides nothing."""
    _place_role_toml(project, "rust-dev", content, stamped=True)

    checked = await invoke(["check"])
    shown = await invoke(["role", "rust-dev", "show"])

    assert checked.exit_code != 0, checked.output
    assert "no role under it" in " ".join(checked.output.split())
    assert shown.exit_code == 1, shown.output
    assert "no role" in shown.output
