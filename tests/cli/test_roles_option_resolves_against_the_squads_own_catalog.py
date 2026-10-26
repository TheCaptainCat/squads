"""``--roles`` on ``sq init`` and ``sq adopt`` names the bundles and roles of the squad's own
role catalog: the bundled one, with the project's ``.overrides/roles.toml`` merged in when present.

One table: override state by command, asserting exit code, message and the roles created.
"""

from pathlib import Path

import pytest

from _helpers import make_service
from squads import __version__
from squads._cli import app
from squads._paths import resolve
from squads._roles._catalog import BUNDLES

_SRE = (
    '[[roles]]\nslug = "sre"\nfull_name = "Sam Reliable"\ntitle = "SRE"\n'
    'description = "Keeps it running."\nmission = "Keep production healthy."\n'
)
_ALL = [*BUNDLES["all"], "sre"]
_OPS_BUNDLE = f'\n[bundles]\nall = {_ALL!r}\nops = ["manager", "sre"]\n'
_ALL_ONLY = f"\n[bundles]\nall = {_ALL!r}\n"

_NONE = None
_BUNDLE = _SRE + _OPS_BUNDLE
_ROLE = _SRE + _ALL_ONLY
_BROKEN = "[[roles]\n"

_DROPS_ALL = '\n[selected]\nbundles = ["core", "minimal"]\n'
_TEMPLATE = '\n[templates.sre]\ntitle = "SRE"\ndescription = "d"\nmission = "m"\n'

_UNKNOWN = "no bundle or role 'sre' (bundles: all, core, minimal; roles: manager"
_MALFORMED = "malformed role catalog override"
_DEFAULT = "no bundle or role 'all' (the --roles default) (bundles: core, minimal; roles: manager"
_TEMPLATE_HINT = "it is a role template, build a role from it with `sq role activate --from`"


def _override(squad: Path, body: str) -> None:
    folder = squad / ".overrides"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "roles.toml").write_text(f"# squads:override-base:{__version__}\n{body}")


def _live_names() -> dict[str, str]:
    import anyio

    async def _names() -> dict[str, str]:
        svc = make_service(resolve())
        return {i.slug: i.title for i in await svc.list_items(item_type="role")}

    return anyio.run(_names)


def _live_roles() -> set[str]:
    return set(_live_names())


@pytest.mark.parametrize("command", ["init", "init-force", "adopt"])
@pytest.mark.parametrize(
    ("override", "roles", "exit_code", "message", "created"),
    [
        (_NONE, "manager", 0, "", {"manager"}),
        (_BUNDLE, "ops", 0, "", {"manager", "sre"}),
        (_ROLE, "manager,sre", 0, "", {"manager", "sre"}),
        (_NONE, "sre", 1, _UNKNOWN, set()),
        (_ROLE, "nobody", 1, "no bundle or role 'nobody'", set()),
        (_BROKEN, "ops", 1, _MALFORMED, set()),
        (_DROPS_ALL, "", 1, _DEFAULT, set()),
        (_TEMPLATE, "sre", 1, _TEMPLATE_HINT, set()),
    ],
    ids=[
        "no-override",
        "override-bundle",
        "override-role-slug",
        "no-override-project-slug",
        "unknown-name",
        "invalid-override",
        "dropped-default-bundle",
        "template-name",
    ],
)
def test_roles_resolves_against_the_squads_own_catalog(
    command,
    override,
    roles,
    exit_code,
    message,
    created,
    runner,
    tmp_path,
    monkeypatch,
    frozen_time,
) -> None:
    monkeypatch.chdir(tmp_path)
    squad = tmp_path / "squads"
    flags = ["--no-claude", "--no-seed-skills"] if command != "adopt" else ["--no-claude"]
    config = tmp_path / ".squads.toml"
    if command == "init-force":
        assert runner.invoke(app, ["init", *flags, "--roles", "", "--default-names"]).exit_code == 0
    before = config.read_bytes() if config.exists() else None
    if override is not None:
        _override(squad, override)
    verb = "adopt" if command == "adopt" else "init"
    extra = ["--force"] if command == "init-force" else []
    if verb == "init":
        extra.append("--default-names")

    result = runner.invoke(app, [verb, *flags, *extra, *(["--roles", roles] if roles else [])])

    assert result.exit_code == exit_code, result.output
    assert message in result.output
    if exit_code == 0:
        assert _live_roles() == created
    else:
        # A refusal writes nothing: no config on a fresh directory, the old one untouched.
        assert (config.read_bytes() if config.exists() else None) == before
        assert not (squad / ".squads.json").exists() or command == "init-force"


def test_interactive_init_prompts_for_the_roles_of_the_squads_own_catalog(
    runner, tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("squads._cli._main._is_tty", lambda: True)
    _override(tmp_path / "squads", _BUNDLE)

    result = runner.invoke(
        app, ["init", "--no-claude", "--no-seed-skills", "--roles", "ops"], input="Ada\nGrace\n"
    )

    assert result.exit_code == 0, result.output
    assert "Name for 'manager'" in result.output and "Name for 'sre'" in result.output
    assert _live_names() == {"manager": "Ada", "sre": "Grace"}
