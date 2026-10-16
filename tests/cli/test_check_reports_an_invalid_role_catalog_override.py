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

# name -> (override body, fragment of the loader's own message)
_REFUSALS = {
    "all-bundle-misses-a-new-role": (
        _NEW_ROLE + '\n[bundles]\nops = ["manager", "sre"]\n',
        "'all' bundle missing roles: ['sre']",
    ),
    "unknown-top-level-key": ("bogus = 1\n", "bogus"),
    "bundle-names-an-unknown-role": ('[bundles]\nops = ["manager", "nobody"]\n', "nobody"),
    "new-role-missing-required-fields": ('[[roles]]\nslug = "sre"\n', "sre"),
    "malformed-toml": ("[[roles\n", "malformed role catalog override"),
}


@pytest.mark.parametrize("per_slug", [False, True], ids=["no-per-slug-file", "per-slug-file"])
@pytest.mark.parametrize("name", list(_REFUSALS))
async def test_invalid_catalog_override_is_an_error_finding(
    project, invoke, name, per_slug
) -> None:
    body, fragment = _REFUSALS[name]
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(parents=True, exist_ok=True)
    (overrides / "roles.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    if per_slug:
        (overrides / "roles").mkdir()
        (overrides / "roles" / "qa.toml").write_text(
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
