"""The meta-type (`role`/`skill`/`operator`) item-first address grammar, beyond the `show`
happy path already homed at tests/cli/test_role_activate_with_override_cli.py and
tests/service/test_operator_lifecycle.py: the mutating `regen`/`rm` verbs resolve an address
by bare number, full ID, or slug exactly like `show` does; a wrong-type token is a clean
`SquadsError`, never a traceback; and the literal (unaddressable) token `list` falls through
to the same clean unknown-address error rather than leaking the internal `_addr` subgroup name.
"""

import pytest

pytestmark = pytest.mark.anyio


# --------------------------------------------------------------------------- list-removed


async def test_role_list_falls_through_to_a_clean_unknown_address_error(project, invoke):
    result = await invoke(["role", "list"])
    assert result.exit_code == 1
    assert "list" in result.output
    assert "_addr" not in result.output
    assert "Traceback" not in result.output

    available = await invoke(["role", "list", "--available"])
    assert available.exit_code == 1
    assert "list" in available.output
    assert "_addr" not in available.output
    assert "Traceback" not in available.output


async def test_skill_list_falls_through_to_a_clean_unknown_address_error(project, invoke):
    result = await invoke(["skill", "list"])
    assert result.exit_code == 1
    assert "list" in result.output
    assert "_addr" not in result.output
    assert "Traceback" not in result.output


async def test_operator_list_falls_through_to_a_clean_unknown_address_error(project, invoke):
    result = await invoke(["operator", "list"])
    assert result.exit_code == 1
    assert "list" in result.output
    assert "_addr" not in result.output
    assert "Traceback" not in result.output


# --------------------------------------------------------------------------- role: regen/rm


async def test_role_regen_resolves_by_bare_number_and_full_id(project, invoke):
    await invoke(["role", "activate", "qa"])  # ROLE-2

    by_number = await invoke(["role", "1", "regen"])
    assert by_number.exit_code == 0, by_number.output

    by_full_id = await invoke(["role", "ROLE-000002", "regen"])
    assert by_full_id.exit_code == 0, by_full_id.output


async def test_role_rm_resolves_by_bare_number(project, invoke):
    await invoke(["role", "activate", "qa"])  # ROLE-2

    result = await invoke(["role", "2", "rm"])
    assert result.exit_code == 0, result.output


async def test_role_regen_on_a_wrong_type_token_is_a_clean_error(project, invoke):
    await invoke(["create", "feature", "F", "--author", "manager"])  # FEAT-2

    result = await invoke(["role", "2", "regen"])
    assert result.exit_code == 1
    assert "feature" in result.output and "not a role" in result.output
    assert "Traceback" not in result.output


# --------------------------------------------------------------------------- skill: regen/rm


async def test_skill_regen_resolves_by_bare_number_and_full_id(project, invoke):
    await invoke(["skill", "add", "first-skill"])  # SKILL-2
    await invoke(["skill", "add", "second-skill"])  # SKILL-3

    by_number = await invoke(["skill", "2", "regen"])
    assert by_number.exit_code == 0, by_number.output

    by_full_id = await invoke(["skill", "SKILL-000003", "regen"])
    assert by_full_id.exit_code == 0, by_full_id.output


async def test_skill_rm_resolves_by_bare_number(project, invoke):
    await invoke(["skill", "add", "removable-skill"])  # SKILL-2

    result = await invoke(["skill", "2", "rm"])
    assert result.exit_code == 0, result.output


async def test_skill_show_resolves_by_its_slug(project, invoke):
    """The exact-slug branch of the address resolver — distinct from the bare-number/full-ID
    forms the other tests in this module already cover."""
    await invoke(["skill", "add", "my-skill", "--desc", "test skill"])  # SKILL-2

    result = await invoke(["skill", "my-skill", "show"])
    assert result.exit_code == 0, result.output
    assert "my-skill" in result.output


async def test_skill_regen_on_a_wrong_type_token_is_a_clean_error(project, invoke):
    # seq 1 is the manager role after `project`'s minimal init.
    result = await invoke(["skill", "1", "regen"])
    assert result.exit_code == 1
    assert "not a skill" in result.output
    assert "Traceback" not in result.output


# --------------------------------------------------------------------------- operator: rm
# (operators have no `regen` verb — they carry no Claude pointer, CLAUDE.md's Operators section)


async def test_operator_rm_resolves_by_bare_number_and_full_id(project, invoke):
    await invoke(["operator", "add", "First User"])  # OP-2
    await invoke(["operator", "add", "Second User"])  # OP-3

    by_number = await invoke(["operator", "2", "rm"])
    assert by_number.exit_code == 0, by_number.output

    by_full_id = await invoke(["operator", "OP-000003", "rm"])
    assert by_full_id.exit_code == 0, by_full_id.output


async def test_operator_rm_on_a_wrong_type_token_is_a_clean_error(project, invoke):
    # seq 1 is the manager role after `project`'s minimal init.
    result = await invoke(["operator", "1", "rm"])
    assert result.exit_code == 1
    assert "not an operator" in result.output or "role" in result.output
    assert "Traceback" not in result.output


# --------------------------------------------------------------------------- role: catalog


async def test_role_catalog_renders_a_table_of_slug_name_title_and_default_marker(project, invoke):
    result = await invoke(["role", "catalog"])
    assert result.exit_code == 0, result.output
    assert "manager" in result.output
    assert "Slug" in result.output and "Title" in result.output
