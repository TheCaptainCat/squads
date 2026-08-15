"""Dropping a type withdraws its own skill; a *surviving* type's prose can still name it.

The membership half is spec-driven and enforced: a workflow override that drops or renames a type
withdraws that type's preloaded skill and adds one for the type that replaced it. Guide **prose**
is free text and is not checked against the spec, so a line in another type's guidance that names
the dropped type by name survives the drop — the generated instruction is then confidently wrong
rather than absent, which is worse than silence.

That is a documented limitation with a supported remedy (override the playbook alongside the
workflow), not a defect awaiting a mechanical fix: templating the type name out was considered and
declined, because a placeholder costs an actionable command an agent cannot reconstruct. What
holds it in place instead is that the bundled prose keeps only the cross-type references that earn
their keep — so what this pins is the *bound*. A newly added gratuitous cross-reference fails
here, which is the regression this can actually catch; narrowing the bound further shows up as a
failure too, and the fix for that one is to tighten the expectation below.

Driven through a real `sq sync` against a real `.overrides/workflow.toml`, and read off the
preloaded pointer set, because that is what decides which guidance an agent actually boots with.
"""

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

#: `task` renamed to `job`: dropped from the selected set, re-declared under the new key with the
#: same shape. The playbook entry follows the spec, so `job` gets a guide and `task` loses one.
_TASK_RENAMED_TO_JOB = """
[selected]
items = [
  "epic", "feature", "job", "bug", "decision",
  "review", "guide", "role", "skill", "operator",
]

[items.job]
prefix = "JOB"
folder = "jobs"
lifecycle = "work"
parents = ["feature"]
aliases = ["j"]
order = 30
category = "work"
subentity_kind = "subtask"
parent_required = "feature"
fields = [{ code = "priority", label = "Priority", collection = "priority" }]
"""

#: What makes a reference *stale* rather than incidental: a runnable command addressed to the
#: dropped type. Prose that merely uses the English word instructs nobody to run anything.
_STALE_COMMAND_SHAPES = ("sq create task", "sq task ")


@pytest.fixture
async def squad(tmp_path, monkeypatch, frozen_time):
    """A squad on the **full** roster, not the shared `project` fixture's minimal one.

    Generated skill text is roster-dependent: each guide renders only for roles that are live, so
    a manager-only squad emits no product-owner section at all — and it is the product-owner
    guide on `feature` that carries the cross-type line this whole file is about. Reading a
    minimal squad here would report the limitation as already fixed.
    """
    from squads._services import _service as service

    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="all", _skip_skill_seed=True)
    await service.Service(result.paths).seed_bundled_skills()
    return result.paths


def _write_override(squad_dir, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


async def _preloaded_skill_bodies(paths, invoke) -> dict[str, str]:
    """Every skill an agent is preloaded with after a real sync, keyed by slug, body included.

    Keyed off the backend's pointer set rather than the skill corpus: a skill item stays on disk
    once written (`sq sync` never deletes an item), and what changes when a type is dropped is
    which pointers are written — so reading the corpus alone would report a withdrawn skill as
    still live.
    """
    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output  # the sync has to have happened to mean anything

    pointers = {p.name for p in (paths.root / ".claude" / "skills").iterdir() if p.is_dir()}
    bodies: dict[str, str] = {}
    for path in sorted((paths.squad_dir / "agents" / "skills").glob("*.md")):
        slug = path.stem.split("-", 2)[-1] if path.stem.startswith("SKILL-") else path.stem
        if slug in pointers:
            bodies[slug] = path.read_text(encoding="utf-8")
    assert pointers == set(bodies), pointers ^ set(bodies)  # every pointer resolved to a body
    return bodies


def _naming_the_dropped_type(bodies: dict[str, str]) -> set[str]:
    return {
        slug
        for slug, body in bodies.items()
        if any(shape in body for shape in _STALE_COMMAND_SHAPES)
    }


async def test_the_control_is_a_squad_where_naming_the_type_is_correct(squad, invoke):
    """Before any override, more than one preloaded skill addresses `task` and every one of them
    is right. Without this the assertions below could pass on a squad generating no prose at all."""
    bodies = await _preloaded_skill_bodies(squad, invoke)

    assert "sq-task" in bodies
    assert _naming_the_dropped_type(bodies) >= {"sq-task", "sq-feature"}


async def test_the_dropped_type_loses_its_preloaded_skill_and_the_new_one_gains_one(squad, invoke):
    """The membership half, which is enforced: playbook coverage is derived from the active spec,
    so the rename moves the guide and the preloaded skill with it."""
    _write_override(squad.squad_dir, _TASK_RENAMED_TO_JOB)
    bodies = await _preloaded_skill_bodies(squad, invoke)

    assert "sq-job" in bodies
    assert "sq-task" not in bodies
    assert "sq create job" in bodies["sq-job"]


async def test_the_surviving_prose_that_still_names_the_dropped_type_is_the_declared_bound(
    squad, invoke
):
    """The limitation itself, stated as a set rather than an example. `sq-feature` keeps the
    feature→task chain because a product-owner guide that cannot say how a feature gets broken
    down has lost its point; every other guide was written to survive the rename."""
    _write_override(squad.squad_dir, _TASK_RENAMED_TO_JOB)
    bodies = await _preloaded_skill_bodies(squad, invoke)

    assert _naming_the_dropped_type(bodies) == {"sq-feature"}
