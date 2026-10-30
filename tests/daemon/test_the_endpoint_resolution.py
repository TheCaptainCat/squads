"""Which squad a directory addresses, whether its daemon may be used, and the key that names it."""

from pathlib import Path

import pytest

from squads._endpoint import endpoint_for

LOCAL_MODE = "every command runs in local mode until it is fixed"


def resolve(root: Path, daemon_table: str = "", **environ: str):
    (root / ".squads.toml").write_text(
        f'schema_version = "0.19"\nsquad_dir = "squads"\n{daemon_table}', encoding="utf-8"
    )
    (root / "squads").mkdir(exist_ok=True)
    endpoint = endpoint_for(
        root, environ={"XDG_RUNTIME_DIR": str(root / "run"), **environ}, platform="linux"
    )
    assert endpoint is not None
    return endpoint


@pytest.mark.parametrize(
    ("table", "environ", "enabled", "problems"),
    [
        ("", {}, True, ()),
        ("[daemon]\nenabled = false\n", {}, False, ()),
        ("[daemon]\nenabled = false\n", {"SQUADS_DAEMON": "on"}, True, ()),
        ("[daemon]\nenabled = true\n", {"SQUADS_DAEMON": "off"}, False, ()),
        ("[daemon]\nport = 1\n", {}, True, ()),
        (
            "[daemon]\nidle_timeout_minutes = -1\n",
            {},
            False,
            (
                "[daemon] idle_timeout_minutes must be a whole number of minutes, 0 or more, "
                f"got -1; {LOCAL_MODE}",
            ),
        ),
        (
            "",
            {"SQUADS_DAEMON": "sometimes"},
            False,
            (f"SQUADS_DAEMON must be on or off, got 'sometimes'; {LOCAL_MODE}",),
        ),
    ],
)
def test_settings_and_the_environment_decide_whether_the_daemon_is_used(
    tmp_path, table, environ, enabled, problems
) -> None:
    endpoint = resolve(tmp_path, table, **environ)
    assert (endpoint.enabled, endpoint.problems) == (enabled, problems)


def test_a_link_and_a_walk_up_reach_the_same_key(tmp_path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    direct = resolve(root)
    link = tmp_path / "link"
    Path(link).symlink_to(root)
    nested = root / "docs" / "notes"
    nested.mkdir(parents=True)

    environ = {"XDG_RUNTIME_DIR": str(root / "run")}
    through_link = endpoint_for(link, environ=environ, platform="linux")
    from_inside = endpoint_for(nested, environ=environ, platform="linux")

    assert through_link is not None
    assert from_inside is not None
    assert {direct.key, through_link.key, from_inside.key} == {direct.key}
    assert direct.squad_dir == (root / "squads").resolve()


def test_the_key_follows_the_version_and_the_installation(tmp_path) -> None:
    resolve(tmp_path)
    environ = {"XDG_RUNTIME_DIR": str(tmp_path / "run")}

    keys = set()
    for version, package in (("1", "/a"), ("2", "/a"), ("1", "/b"), ("1", "/a")):
        endpoint = endpoint_for(
            tmp_path, environ=environ, platform="linux", version=version, package_dir=Path(package)
        )
        assert endpoint is not None
        keys.add(endpoint.key)

    assert len(keys) == 3
