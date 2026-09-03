"""Adopter template overrides on the leaf-verb render path.

``sq <type> <n> <verb>`` crosses the sync/async bridge twice for one user-facing invocation —
the item-type group's id-resolving callback, then the leaf verb — as two sequential
``anyio.run`` calls sharing one Click root context. A view's presentation template (and every
other template rendered off the leaf verb) must resolve an adopter's
``.overrides/templates/`` override on that two-crossing path, not just when a test calls
``render()``/``Service.render_view`` directly in one construction.

The first test overrides the bundled milestone roll-up in a test squad, then reads it back
through ``sq milestone <n> show`` — both rendered forms — with ``sq workflow view`` pinned
alongside as a second surface onto the same template.

The second is the guard: it enumerates render() call sites reached from double-bridge leaf
verbs (a view template, and the sub-entity block/head/summary templates) by instrumenting the
rendering engine itself, so a future leaf verb that starts rendering something new trips it
automatically rather than needing a matching new test.

The third falsifies the harness rather than the code under test: it disables the leaf-verb
re-assertion via a monkeypatch (opening the seam without touching production source) and asserts
the resulting bundled-template fallback is actually observed. ``tests/conftest.py``'s ``invoke``
fixture resets the ambient render ContextVar/cache before every call, so this test needs no
manual reset of its own: without that harness-level reset, the leak the ``project`` fixture's
in-process ``service.init(...)`` leaves in the ambient context (``invoke`` copies the calling
context per call) would mask the break.
"""

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

import pytest
from jinja2 import Environment, Template

from squads._overrides._stamp import read_template_stamp, write_template_stamp
from squads._rendering import _engine as engine

pytestmark = pytest.mark.anyio


def _created_id(output: str) -> str:
    return output.split("→")[0].removeprefix("created").strip()


def _override_milestone_rollup(squad_dir: Path, marker: str) -> None:
    """Scaffold the bundled view template via the real CLI-adjacent helper, then overwrite its
    body with *marker* while keeping the stamp — proving the override machinery (not a
    hand-authored file) is what the leaf verb ends up reading."""
    target = squad_dir / ".overrides" / "templates" / "views" / "milestone_rollup.md.j2"
    assert target.is_file(), "sq override scaffold did not write the expected path"
    stamp = read_template_stamp(target.read_text(encoding="utf-8"))
    assert stamp is not None
    target.write_text(write_template_stamp(f"{marker}\n", stamp), encoding="utf-8")
    engine.invalidate_squad_dir(squad_dir)


async def test_milestone_rollup_override_renders_through_show_show_raw_and_workflow_view(
    project, invoke
) -> None:
    marker = "OVERRIDE-RENDERED-MILESTONE-ROLLUP"

    r = await invoke(["create", "milestone", "Ship it", "--author", "manager"])
    assert r.exit_code == 0, r.output
    mile_id = _created_id(r.output)

    r = await invoke(["override", "scaffold", "views/milestone_rollup.md.j2"])
    assert r.exit_code == 0, r.output
    _override_milestone_rollup(project.squad_dir, marker)

    # The two-crossing form: an item-type group id-resolving callback, then the leaf verb.
    r = await invoke(["milestone", mile_id, "show"])
    assert r.exit_code == 0, r.output
    assert marker in r.output
    assert "## Delivered" not in r.output
    assert "## Outstanding" not in r.output

    r = await invoke(["milestone", mile_id, "show", "--raw"])
    assert r.exit_code == 0, r.output
    assert marker in r.output
    assert "## Delivered" not in r.output

    # The dedicated view command resolves the same override template.
    r = await invoke(["workflow", "view", "milestone_rollup", mile_id])
    assert r.exit_code == 0, r.output
    assert marker in r.output


async def test_every_leaf_verb_render_call_sees_the_active_squad_dir(
    project, invoke, monkeypatch
) -> None:
    """Instrument the engine's template lookup to record, for every ``render()`` call made
    during a run of double-bridge commands, the template name and whatever squad dir
    ``render()`` actually resolved against. None of them may see ``None`` — a render that
    resolves against no squad dir silently falls back to the bundled tree — and the recorded set
    must include both a view template and a sub-entity template, so the guard is not pinned to
    the one call site the first test drives.
    """
    calls: list[tuple[str, Path | None]] = []
    orig_env = engine._env

    def spying_env() -> Environment:
        env = orig_env()
        if not getattr(env, "_leaf_verb_render_spy", False):
            real_get_template = env.get_template

            def get_template(
                name: str,
                parent: str | None = None,
                globals: MutableMapping[str, Any] | None = None,
            ) -> Template:
                calls.append((name, engine._active_squad_dir.get()))
                return real_get_template(name, parent, globals)

            env.get_template = get_template  # type: ignore[method-assign]
            env._leaf_verb_render_spy = True  # type: ignore[attr-defined]
        return env

    monkeypatch.setattr(engine, "_env", spying_env)

    r = await invoke(["create", "milestone", "Ship it", "--author", "manager"])
    assert r.exit_code == 0, r.output
    mile_id = _created_id(r.output)
    r = await invoke(["milestone", mile_id, "show"])
    assert r.exit_code == 0, r.output

    r = await invoke(["create", "task", "Do the work", "--author", "manager"])
    assert r.exit_code == 0, r.output
    task_id = _created_id(r.output)
    # add-subtask renders the block, then refreshes the head + summary — three template
    # families off one double-bridge leaf verb.
    r = await invoke(["task", task_id, "add-subtask", "Do a piece of it"])
    assert r.exit_code == 0, r.output
    r = await invoke(["task", task_id, "subtask", "1", "update", "--status", "InProgress"])
    assert r.exit_code == 0, r.output

    monkeypatch.undo()
    engine.invalidate_squad_dir(project.squad_dir)

    assert calls, "no render() calls were observed — the spy did not attach"
    seen_templates = {name for name, _ in calls}
    assert any(name.startswith("views/") for name in seen_templates)
    assert any(name.startswith("subentities/") for name in seen_templates)

    missing = [(name, sd) for name, sd in calls if sd is None]
    assert not missing, f"leaf-verb render() calls with no active squad dir: {missing}"
    wrong = [(name, sd) for name, sd in calls if sd is not None and sd != project.squad_dir]
    assert not wrong, f"leaf-verb render() calls resolved a different squad dir: {wrong}"


async def test_a_broken_leaf_verb_render_path_is_caught_once_the_harness_resets_ambient_state(
    project, invoke, monkeypatch
) -> None:
    """Falsification for the harness's per-invocation reset itself, rather than for the
    leaf-verb re-assertion that reset lets a test observe.

    Disables the leaf-verb re-assertion without touching production source, by monkeypatching
    ``squads._cli._common.set_active_squad_dir`` to a no-op. That opens the seam this module
    guards: the item-type group's crossing still sets the ContextVar via
    ``ServiceCore.__init__`` (a separate import binding in ``_services/_base.py``, untouched by
    this monkeypatch), but the leaf verb's crossing no longer re-asserts it, so its own
    ``render()`` call sees no active squad dir and falls back to the bundled template.

    With ``invoke`` correctly resetting the ambient ContextVar/cache before every call, that
    fallback is what actually happens here — asserted directly: the override marker is absent
    and a bundled heading renders instead. Without that per-invocation reset, the
    ambient context the ``project`` fixture leaves behind (its own in-process
    ``service.init(...)``) would leak into this same invocation and mask the break — the override
    would render despite it, the same false pass a test written the "obvious way" gives: one
    that passes whether or not the code under test established the state itself.
    """
    from squads._cli import _common

    monkeypatch.setattr(_common, "set_active_squad_dir", lambda _squad_dir: None)

    r = await invoke(["create", "milestone", "Ship it", "--author", "manager"])
    assert r.exit_code == 0, r.output
    mile_id = _created_id(r.output)

    r = await invoke(["override", "scaffold", "views/milestone_rollup.md.j2"])
    assert r.exit_code == 0, r.output
    _override_milestone_rollup(project.squad_dir, "OVERRIDE-RENDERED-MILESTONE-ROLLUP")

    r = await invoke(["milestone", mile_id, "show"])
    assert r.exit_code == 0, r.output
    assert "OVERRIDE-RENDERED-MILESTONE-ROLLUP" not in r.output
    assert "## Delivered" in r.output
