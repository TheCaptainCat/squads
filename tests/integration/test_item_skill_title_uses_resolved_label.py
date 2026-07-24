"""The Claude Code backend's per-type item-skill section title (retargeted from an ad-hoc
``item_type.capitalize()`` to ``label_for(item_type, "singular", spec)``) renders the
spec's pinned display label when one is declared, for both a kept
built-in type and a project-declared custom type — and still falls back to the derived
form (byte-identical to the old ``.capitalize()`` behaviour) when no ``labels`` table is
present at all.
"""

import pytest

from squads._services import _service as service
from squads._workflow import bundled_spec
from squads._workflow._models import ItemSpec, LabelSpec

pytestmark = pytest.mark.anyio


def _item_skill_title(text: str) -> str:
    return next(ln for ln in text.splitlines() if ln.startswith("# ")).removeprefix("# ")


async def test_a_kept_built_ins_pinned_singular_label_is_rendered_in_its_skill_title(project):
    base = bundled_spec()
    pinned_bug = base.items["bug"].model_copy(update={"labels": LabelSpec(singular="Defect")})
    spec = base.model_copy(update={"items": {**base.items, "bug": pinned_bug}})
    await service.Service(project, spec=spec).refresh_managed()
    body = (project.squad_dir / "agents" / "skills" / "sq-bug.md").read_text(encoding="utf-8")
    assert _item_skill_title(body) == "Defect items"


async def test_a_custom_types_pinned_singular_label_is_rendered_in_its_skill_title(project):
    base = bundled_spec()
    custom = ItemSpec(
        prefix="ARD",
        folder="ards",
        lifecycle="work",
        labels=LabelSpec(singular="ADR"),
    )
    spec = base.model_copy(update={"items": {**base.items, "adr": custom}})
    await service.Service(project, spec=spec).refresh_managed()
    body = (project.squad_dir / "agents" / "skills" / "sq-adr.md").read_text(encoding="utf-8")
    assert _item_skill_title(body) == "ADR items"


async def test_a_type_with_no_labels_table_still_falls_back_to_the_capitalized_form(project):
    body = (project.squad_dir / "agents" / "skills" / "sq-task.md").read_text(encoding="utf-8")
    assert _item_skill_title(body) == "Task items"
