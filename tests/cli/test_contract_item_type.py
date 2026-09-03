"""``sq contract`` — the CLI surface for the ``contract`` (PRD) item type: creation via its
declared aliases, its dedicated lifecycle, no sub-entity surface, and the forward
``implements``/``supersedes`` edges the living<->historic model rests on.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def _create(invoke, item_type: str, title: str) -> str:
    r = await invoke(["create", item_type, title, "--author", "manager", "--json"])
    assert r.exit_code == 0, r.output
    return json.loads(r.output)["id"]


async def test_create_contract_writes_a_prd_prefixed_item_under_contracts(project, invoke):
    prd = await _create(invoke, "contract", "Search")
    assert prd.startswith("PRD-")

    r = await invoke(["contract", prd, "show"])
    assert r.exit_code == 0, r.output
    assert "contract" in r.output.lower()
    assert "Draft" in r.output


@pytest.mark.parametrize("alias", ["prd", "c"])
async def test_the_declared_aliases_route_to_the_same_command_tree(project, invoke, alias):
    prd = await _create(invoke, "contract", "Search")
    r = await invoke([alias, prd, "show"])
    assert r.exit_code == 0, r.output
    assert prd in r.output


async def test_the_lifecycle_reaches_both_terminals(project, invoke):
    a = await _create(invoke, "contract", "Search")
    r = await invoke(["contract", a, "status", "Active"])
    assert r.exit_code == 0, r.output

    b = await _create(invoke, "contract", "Search v2")
    r = await invoke(["contract", a, "ref", "add", b, "--kind", "supersedes"])
    assert r.exit_code == 0, r.output
    r = await invoke(["contract", a, "status", "Superseded"])
    assert r.exit_code == 0, r.output

    r = await invoke(["contract", b, "status", "Active"])
    assert r.exit_code == 0, r.output
    r = await invoke(["contract", b, "status", "Deprecated"])
    assert r.exit_code == 0, r.output
    r = await invoke(["contract", b, "status", "Active"])  # the revive edge
    assert r.exit_code == 0, r.output


async def test_check_is_clean_on_a_contract_with_ordinary_headings_and_no_sub_entities(
    project, invoke
):
    prd = await _create(invoke, "contract", "Search")
    r = await invoke(["check"])
    assert r.exit_code == 0, r.output
    assert prd not in r.output


async def test_a_feature_carries_a_forward_implements_ref_and_the_contract_inverts_it(
    project, invoke
):
    prd = await _create(invoke, "contract", "Search")
    feat = await _create(invoke, "feature", "Search UI")
    r = await invoke(["feature", feat, "ref", "add", prd, "--kind", "implements"])
    assert r.exit_code == 0, r.output

    # nothing stored on the contract itself — recovered purely by backref inversion
    r = await invoke(["contract", prd, "refs", "--in"])
    assert r.exit_code == 0, r.output
    assert feat in r.output

    r = await invoke(["contract", prd, "show"])
    assert feat not in r.output


async def test_a_superseded_contract_with_no_incoming_supersedes_edge_is_reported(project, invoke):
    """No new code for this — the `records` category bundle already selects
    `supersedes_incoming`, the same validator `decision` uses."""
    prd = await _create(invoke, "contract", "Search")
    await invoke(["contract", prd, "status", "Active"])
    await invoke(["contract", prd, "status", "Superseded"])

    r = await invoke(["check"])
    assert "no incoming supersedes edge" in r.output
