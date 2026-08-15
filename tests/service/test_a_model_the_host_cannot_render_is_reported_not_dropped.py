"""A role model the agent host's own frontmatter cannot express is *reported*, never dropped
in silence.

``normalize_model`` maps anything outside the four names Claude Code accepts to ``None``, and
the pointer template omits ``model:`` when it is ``None``. Nothing said so. The value was
durable in the role item's frontmatter, so an adopter reading their own declaration back
believed the agent ran on it; the generated ``.claude/agents/<slug>.md`` had no model line at
all and the agent ran on the session default. ``sq sync`` printed nothing and ``sq check``
reported no issues.

The refusal that *does* exist lives upstream and covers one path only: a role override naming
an unknown model is refused when the override is resolved. This is the backstop for every
other way a value reaches the item (``sq dev add --model``, an import, a migrated corpus) —
deliberately a report rather than a second validator, so the two can never disagree about the
same value: one refuses at declaration time, the other says what the write just failed to
render.
"""

import pytest

from squads._backends._base import BackendContext
from squads._backends._claude_code._backend import ClaudeCodeBackend
from squads._backends._claude_code._frontmatter import model_drop_warning, normalize_model
from squads._errors import SquadsError
from squads._roles._catalog import RoleDef
from squads._roles._resolver import resolve_role
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_UNRENDERABLE = "claude-opus-4-5"


@pytest.mark.parametrize("model", ["sonnet", "opus", "haiku", "inherit", None])
def test_a_model_the_host_accepts_reports_nothing(model):
    assert normalize_model(model) == model
    assert model_drop_warning("reviewer", model) is None


@pytest.mark.parametrize("model", [_UNRENDERABLE, "opuss", "gpt-5", "Sonnet", "", "  "])
def test_every_unrenderable_shape_is_both_dropped_and_reported(model):
    """One case per shape family, not one per branch: a plausible near-miss, a typo, another
    vendor's name, a case difference, and two falsy-but-present values — the last of which is
    the one a ``if model:`` guard would silently let through as "nothing declared"."""
    assert normalize_model(model) is None
    warning = model_drop_warning("reviewer", model)
    assert warning is not None
    assert repr(model) in warning  # the offending value is named, not just described
    assert "reviewer" in warning


async def test_sync_reports_a_dev_roles_unrenderable_model_and_the_pointer_omits_it(
    tmp_path, monkeypatch
):
    """End to end on the path that still reaches the backend: ``sq dev add --model`` takes a
    free-form string, so the item stores it and the pointer cannot render it."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)
    dev = await svc.add_dev("python", model=_UNRENDERABLE)
    assert dev.extra["model"] == _UNRENDERABLE  # durable, exactly as declared

    reported = await service.Service(result.paths).sync()

    pointer = (tmp_path / ".claude" / "agents" / "python-dev.md").read_text(encoding="utf-8")
    assert "model:" not in pointer  # still dropped -- this is a report, not a rescue
    assert any(_UNRENDERABLE in line and "python-dev" in line for line in reported), reported


async def test_a_role_override_naming_an_unknown_model_is_refused_before_it_can_be_stored(
    tmp_path, monkeypatch
):
    """The upstream half, pinned here so the two verdicts stay distinguishable: the override
    path refuses, and therefore never reaches the reporting backstop above."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, backend=["claude_code"], roles_spec="minimal")
    override = result.paths.squad_dir / ".overrides" / "roles" / "reviewer.toml"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(f'model = "{_UNRENDERABLE}"\n', encoding="utf-8")
    assert override.is_file()

    with pytest.raises(SquadsError, match=_UNRENDERABLE):
        resolve_role("reviewer", result.paths.squad_dir)


async def test_a_role_the_host_can_render_produces_no_warning_at_all(tmp_path, monkeypatch):
    """The negative case, so the report cannot be a constant: an ordinary roster syncs clean."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, backend=["claude_code"], roles_spec="all")
    assert await service.Service(result.paths).sync() == []


async def test_the_warning_travels_on_the_artifact_the_write_returned(tmp_path, monkeypatch):
    """Structural, not just observed through sync: the notice is carried by the ``Artifact``
    the per-entry write returns, which is the channel every caller of a backend already has."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)
    item = await svc.roster_item("role", "manager")
    assert item is not None
    role = RoleDef.from_extra({**item.extra, "model": _UNRENDERABLE})

    ctx = BackendContext(paths=result.paths, spec=svc.spec, playbook=svc.playbook)
    artifact = await ClaudeCodeBackend().generate_role_entry(ctx, item, role)

    assert artifact.warning is not None
    assert _UNRENDERABLE in artifact.warning
