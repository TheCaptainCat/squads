"""A project's catalog-document ``[dev]`` override (``.overrides/roles.toml``) reaching the
dev-role *preview* base for a ``<tech>-dev`` slug with no roster entry — the gap
``dev_base_for_slug`` left: it built its base from the bundled ``dev_role(...)`` singleton
unconditionally, while its sibling ``resolve_dev_role`` (the ``sq dev add`` path) already
threaded ``squad_dir`` through ``load_role_catalog(squad_dir).dev``. So a project's ``[dev]``
override reached what ``sq dev add`` creates and not what a not-yet-added slug previewed.

Three surfaces:

- ``sq role <tech>-dev show`` on an un-added slug (``_cli/_role.py``'s ``_role_base_for_show``)
  — the directly observable case, proven end to end against ``sq dev add``'s own result.
- ``_check_role_override_resolves`` (``_overrides/_service.py``) — the merge base a per-slug
  dev override is validated against when there is no roster item yet.
- ``_diff_role`` (``_overrides/_service.py``, via ``_shadowed_bundled_role_toml``) — the Δ-mine
  baseline a per-slug dev override is diffed against.
"""

import json
from pathlib import Path

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio


def _write_catalog_dev_override(squad_dir: Path, content: str) -> None:
    (squad_dir / ".overrides").mkdir(parents=True, exist_ok=True)
    (squad_dir / ".overrides" / "roles.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


def _write_slug_override(squad_dir: Path, slug: str, content: str) -> Path:
    target = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


# --------------------------------------------------------------------------- the observable:
# the preview agrees with what `sq dev add` then produces


async def test_the_unadded_preview_agrees_with_what_dev_add_then_produces(
    project, svc, invoke
) -> None:
    _write_catalog_dev_override(project.squad_dir, '[dev]\nmodel = "haiku"\n')

    before_add = await invoke(["role", "rust-dev", "show", "--json"])
    add_result = await invoke(["dev", "add", "--tech", "rust"])
    after_add = await invoke(["role", "rust-dev", "show", "--json"])

    assert before_add.exit_code == 0, before_add.output
    assert add_result.exit_code == 0, add_result.output
    assert after_add.exit_code == 0, after_add.output

    before_data = json.loads(before_add.output)
    after_data = json.loads(after_add.output)
    assert before_data["model"] == "haiku"
    assert after_data["model"] == "haiku"
    assert before_data["model"] == after_data["model"]


async def test_with_no_catalog_document_the_preview_stays_bundled(project, svc, invoke) -> None:
    result = await invoke(["role", "rust-dev", "show", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["model"] != "haiku"  # the bundled default, unaffected


# --------------------------------------------------------------------------- `_check_role_
# override_resolves`'s merge base (the "scaffold base" latent call site)


async def test_check_role_override_resolve_dev_base_is_threaded_with_the_squad(
    project, monkeypatch
) -> None:
    """Proves the exact wiring at ``_overrides/_service.py``'s ``_check_role_override_resolves``
    call site: ``dev_base_for_slug`` is called with this squad's own directory, not ``None`` —
    the call recorded here is the real one, not a stand-in, so this fails the moment the call
    site stops passing it."""
    import squads._roles._resolver as resolver_mod
    from squads._overrides._service import _check_role_override_resolves

    _write_catalog_dev_override(project.squad_dir, '[dev]\nmodel = "haiku"\n')
    _write_slug_override(project.squad_dir, "rust-dev", 'title = "Rust wrangler"\n')

    original = resolver_mod.dev_base_for_slug
    calls: list[tuple[str, Path | None]] = []

    def spy(slug: str, squad_dir: Path | None = None):
        calls.append((slug, squad_dir))
        return original(slug, squad_dir)

    monkeypatch.setattr(resolver_mod, "dev_base_for_slug", spy)

    issues = _check_role_override_resolves(project.squad_dir, "rust-dev", "display", {})

    assert issues == []
    assert calls == [("rust-dev", project.squad_dir)]


# --------------------------------------------------------------------------- `_diff_role`'s
# Δ-mine baseline (the other latent call site, via `_shadowed_bundled_role_toml`)


async def test_dev_role_delta_mine_shadows_against_the_project_dev_defaults(project) -> None:
    """A per-slug dev override merges field-wise over the *project's* dev-pool base when one
    is declared, not just the bundled one — so Δ-mine must show the project's model as the
    field replaced, not the bundled model."""
    from squads._overrides._service import diff_override

    _write_catalog_dev_override(project.squad_dir, '[dev]\nmodel = "haiku"\n')
    _write_slug_override(
        project.squad_dir,
        "rust-dev",
        f'# squads:override-base:{__version__}\nmodel = "opus"\n',
    )

    delta_mine = diff_override(project.squad_dir, "rust-dev", "role").delta_mine

    assert '+model = "opus"' in delta_mine
    assert '-model = "haiku"' in delta_mine  # the project's own default, not the bundled one
