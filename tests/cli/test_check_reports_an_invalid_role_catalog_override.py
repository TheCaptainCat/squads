"""`sq check` loads the merged role catalog and reports a refusal as an error on
`.overrides/roles.toml`, with or without per-slug role overrides."""

import json

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

_NEW_ROLE = (
    '[[roles]]\nslug = "sre"\nfull_name = "Sam Sre"\ntitle = "SRE"\n'
    'description = "d"\nmission = "m"\n'
)

# name -> (override body as text or bytes, fragment of the loader's own message)
_REFUSALS = {
    "all-bundle-misses-a-new-role": (
        _NEW_ROLE + '\n[bundles]\nops = ["manager", "sre"]\n',
        "'all' bundle missing roles: ['sre']",
    ),
    "unknown-top-level-key": ("bogus = 1\n", "bogus"),
    "bundle-names-an-unknown-role": ('[bundles]\nops = ["manager", "nobody"]\n', "nobody"),
    "new-role-missing-required-fields": ('[[roles]]\nslug = "sre"\n', "sre"),
    "malformed-toml": ("[[roles\n", "malformed role catalog override"),
    "bundles-is-an-array": ('bundles = ["all"]\n', "'bundles' must be a table"),
    "bundles-is-an-int": ("bundles = 3\n", "'bundles' must be a table"),
    "roles-is-an-int": ("roles = 3\n", "'roles' must be an array or a table"),
    "not-utf8": (b"# \xff\xfe\n", "not valid UTF-8"),
}


@pytest.mark.parametrize("per_slug", [False, True], ids=["no-per-slug-file", "per-slug-file"])
@pytest.mark.parametrize("name", list(_REFUSALS))
async def test_invalid_catalog_override_is_an_error_finding(
    project, invoke, name, per_slug
) -> None:
    body, fragment = _REFUSALS[name]
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(parents=True, exist_ok=True)
    stamp = f"# squads:override-base:{__version__}\n".encode()
    (overrides / "roles.toml").write_bytes(
        stamp + (body if isinstance(body, bytes) else body.encode())
    )
    if per_slug:
        (overrides / "roles").mkdir()
        # manager is on the roster, so its per-slug file resolves against the catalog.
        (overrides / "roles" / "manager.toml").write_text(
            f'# squads:override-base:{__version__}\nmodel = "opus"\n', encoding="utf-8"
        )

    r = await invoke(["check", "--json"])

    assert r.exit_code == 3, r.output
    issues = json.loads(r.stdout)
    found = [i for i in issues if i["item"] == ".overrides/roles.toml"]
    assert len(found) == 1, issues
    assert found[0]["level"] == "error"
    assert found[0]["message"].startswith("role catalog override is invalid: ")
    assert fragment in found[0]["message"]
    assert not [i for i in issues if i["item"] == "corpus"], issues
    assert not [i for i in issues if i["item"].startswith(".overrides/roles/")], issues


async def test_stamp_findings_on_per_slug_files_survive_an_invalid_catalog(project, invoke) -> None:
    overrides = project.squad_dir / ".overrides"
    (overrides / "roles").mkdir(parents=True)
    (overrides / "roles.toml").write_text(
        f"# squads:override-base:{__version__}\nbogus = 1\n", encoding="utf-8"
    )
    (overrides / "roles" / "manager.toml").write_text('model = "opus"\n', encoding="utf-8")

    r = await invoke(["check", "--json"])

    assert r.exit_code == 3, r.output
    items = {i["item"] for i in json.loads(r.stdout)}
    assert items == {".overrides/roles.toml", ".overrides/roles/manager.toml"}
