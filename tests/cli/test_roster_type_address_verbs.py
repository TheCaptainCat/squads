"""The roster-type (`role`/`skill`/`operator`) item-first address grammar, beyond the `show`
happy path already homed at tests/cli/test_role_activate_with_override_cli.py and
tests/service/test_operator_lifecycle.py: the mutating `regen`/`rm`/`status` verbs resolve an
address by bare number, full ID, or slug exactly like `show` does; a wrong-type token is a
clean `SquadsError`, never a traceback. `role`/`operator` now have a real `list` group verb
(see tests/cli/test_role_list_command_cli.py / tests/cli/test_operator_list_command_cli.py);
`skill` does not, so the literal (unaddressable) token `list` still falls through to the same
clean unknown-address error there, rather than leaking the internal `_addr` subgroup name.

`status` additionally covers: the `--force` override, the off-lifecycle / disallowed-edge error
shapes, a bundled-but-not-activated role slug's "activate it first" fallback (role's own ctx
convention), the addressed-verb help/missing-verb text, and that a transitioned roster entity
leaves `sq check`/`sq repair`/`sq sync`/`sq list --json` consistent.

Retirement's observable effect rounds this out at the bottom of the file: a status
transition's projection into backend config — the pointer file materialising, withdrawing, and
regenerating on reactivation — and the participation gate (a retired slug refused as `--author`/
`--as`/`--assignee` while its already-authored items keep reading correctly).

`--unlink`'s CLI surface — presence/help text, the no-op reading, and the not-a-retirement
refusal — is covered near the end of the file; severance reporting for an actual scoped-skill
retirement lives in `tests/cli/test_skill_role_scoping_verbs.py` next to the other scoping verbs.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


# --------------------------------------------------------------------------- list dispatch


async def test_role_list_is_the_real_group_verb_not_an_address_fallthrough(project, invoke):
    result = await invoke(["role", "list"])
    assert result.exit_code == 0, result.output
    assert "_addr" not in result.output
    assert "Traceback" not in result.output

    # an unrecognized option on the real `list` command is a clean Typer usage error.
    available = await invoke(["role", "list", "--available"])
    assert available.exit_code != 0
    assert "Traceback" not in available.output


async def test_skill_list_falls_through_to_a_clean_unknown_address_error(project, invoke):
    result = await invoke(["skill", "list"])
    assert result.exit_code == 1
    assert "list" in result.output
    assert "_addr" not in result.output
    assert "Traceback" not in result.output


async def test_operator_list_is_the_real_group_verb_not_an_address_fallthrough(project, invoke):
    result = await invoke(["operator", "list"])
    assert result.exit_code == 0, result.output
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
    await invoke(["create", "feature", "F", "--author", "manager"])

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


# --------------------------------------------------------------------------- status: resolution


async def test_role_status_resolves_by_bare_number_full_id_and_slug(project, invoke):
    await invoke(["role", "activate", "qa"])  # ROLE-2

    by_slug = await invoke(["role", "qa", "status", "Archived"])
    assert by_slug.exit_code == 0, by_slug.output
    assert "ROLE-2" in by_slug.output and "Archived" in by_slug.output

    by_number = await invoke(["role", "2", "status", "Active"])
    assert by_number.exit_code == 0, by_number.output

    by_full_id = await invoke(["role", "ROLE-000002", "status", "Archived"])
    assert by_full_id.exit_code == 0, by_full_id.output


async def test_skill_status_resolves_by_bare_number_full_id_and_slug(project, invoke):
    await invoke(["skill", "add", "my-skill"])  # SKILL-2

    by_slug = await invoke(["skill", "my-skill", "status", "Archived"])
    assert by_slug.exit_code == 0, by_slug.output

    by_number = await invoke(["skill", "2", "status", "Active"])
    assert by_number.exit_code == 0, by_number.output

    by_full_id = await invoke(["skill", "SKILL-000002", "status", "Archived"])
    assert by_full_id.exit_code == 0, by_full_id.output


async def test_operator_status_resolves_by_bare_number_full_id_and_slug(project, invoke):
    await invoke(["operator", "add", "First User"])  # OP-2

    by_slug = await invoke(["operator", "op-first", "status", "Archived"])
    assert by_slug.exit_code == 0, by_slug.output

    by_number = await invoke(["operator", "2", "status", "Active"])
    assert by_number.exit_code == 0, by_number.output

    by_full_id = await invoke(["operator", "OP-000002", "status", "Archived"])
    assert by_full_id.exit_code == 0, by_full_id.output


# --------------------------------------------------------------------------- status: errors


async def test_role_status_on_a_bundled_but_not_activated_slug_gives_the_activate_first_error(
    project, invoke
):
    result = await invoke(["role", "product-owner", "status", "Active"])
    assert result.exit_code == 1
    assert "activate it first" in result.output
    assert "Traceback" not in result.output


async def test_role_status_on_a_wrong_type_token_is_a_clean_error(project, invoke):
    await invoke(["create", "feature", "F", "--author", "manager"])

    result = await invoke(["role", "2", "status", "Active"])
    assert result.exit_code == 1
    assert "feature" in result.output and "not a role" in result.output
    assert "Traceback" not in result.output


async def test_operator_status_on_a_wrong_type_token_is_a_clean_error(project, invoke):
    # seq 1 is the manager role after `project`'s minimal init.
    result = await invoke(["operator", "1", "status", "Active"])
    assert result.exit_code == 1
    assert "Traceback" not in result.output


async def test_role_status_rejects_a_status_outside_the_declared_lifecycle(project, invoke):
    await invoke(["role", "activate", "qa"])  # ROLE-2

    result = await invoke(["role", "qa", "status", "InProgress"])
    assert result.exit_code == 1
    assert "not a valid status for role" in result.output
    assert "Active" in result.output and "Archived" in result.output
    assert "Traceback" not in result.output


async def test_role_status_force_never_bypasses_the_vocabulary_even_for_the_dropped_draft_status(
    project, invoke
):
    """``Draft`` used to be part of the bundled role/skill/operator lifecycle and reachable via
    ``--force``; now that the lifecycle only declares Active/Archived, Draft is a vocabulary
    violation — ``--force`` overrides only the transition edge, never the vocabulary itself."""
    await invoke(["role", "activate", "qa"])  # ROLE-2 starts Active

    denied = await invoke(["role", "qa", "status", "Draft"])
    assert denied.exit_code == 1
    assert "not a valid status for role" in denied.output
    assert "Traceback" not in denied.output

    forced = await invoke(["role", "qa", "status", "Draft", "--force"])
    assert forced.exit_code == 1
    assert "not a valid status for role" in forced.output
    assert "Traceback" not in forced.output


# --------------------------------------------------------------------------- status: discovery


async def test_role_help_and_missing_verb_error_name_the_status_verb(project, invoke):
    help_result = await invoke(["role", "--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "status" in help_result.output

    missing_verb = await invoke(["role", "qa"])
    assert missing_verb.exit_code == 1
    assert "status" in missing_verb.output


async def test_skill_help_and_missing_verb_error_name_the_status_verb(project, invoke):
    help_result = await invoke(["skill", "--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "status" in help_result.output

    await invoke(["skill", "add", "my-skill"])
    missing_verb = await invoke(["skill", "my-skill"])
    assert missing_verb.exit_code == 1
    assert "status" in missing_verb.output


async def test_operator_help_and_missing_verb_error_name_the_status_verb(project, invoke):
    help_result = await invoke(["operator", "--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "status" in help_result.output

    await invoke(["operator", "add", "First User"])
    missing_verb = await invoke(["operator", "op-first"])
    assert missing_verb.exit_code == 1
    assert "status" in missing_verb.output


# --------------------------------------------------------------------------- status: consistency


async def test_a_transitioned_roster_entity_leaves_the_board_consistent(project, invoke):
    await invoke(["role", "activate", "qa"])  # ROLE-2

    transitioned = await invoke(["role", "qa", "status", "Archived"])
    assert transitioned.exit_code == 0, transitioned.output

    check = await invoke(["check"])
    assert check.exit_code == 0, check.output

    repair = await invoke(["repair"])
    assert repair.exit_code == 0, repair.output

    sync = await invoke(["sync"])
    assert sync.exit_code == 0, sync.output

    listed = await invoke(["list", "-t", "role", "--all", "--json"])
    rows = json.loads(listed.output)
    row = next(r for r in rows if r["slug"] == "qa")
    assert row["status"] == "Archived"  # `sq sync` did not revert the transition


# --------------------------------------------------------------------------- retirement: projection


async def _pointer_exists(project) -> bool:
    return (project.root / ".claude" / "agents" / "qa.md").exists()


async def test_retiring_a_role_withdraws_its_pointer_and_reactivating_regenerates_it(
    project, invoke
):
    await invoke(["role", "activate", "qa"])
    assert await _pointer_exists(project)

    retired = await invoke(["role", "qa", "status", "Archived"])
    assert retired.exit_code == 0, retired.output
    assert not await _pointer_exists(project)

    reactivated = await invoke(["role", "qa", "status", "Active"])
    assert reactivated.exit_code == 0, reactivated.output
    assert await _pointer_exists(project)


async def test_retiring_a_skill_withdraws_its_pointer_and_reactivating_regenerates_it(
    project, invoke
):
    await invoke(["skill", "add", "my-skill"])
    pointer = project.root / ".claude" / "skills" / "my-skill" / "SKILL.md"
    assert pointer.exists()

    retired = await invoke(["skill", "my-skill", "status", "Archived"])
    assert retired.exit_code == 0, retired.output
    assert not pointer.exists()

    reactivated = await invoke(["skill", "my-skill", "status", "Active"])
    assert reactivated.exit_code == 0, reactivated.output
    assert pointer.exists()


async def test_retiring_a_role_drops_it_from_the_compiled_roster_table(project, invoke):
    await invoke(["role", "activate", "qa"])
    claude_md = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Mara Tester" in claude_md

    await invoke(["role", "qa", "status", "Archived"])
    claude_md = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Mara Tester" not in claude_md


# ------------------------------------------------------------- participation: live-only gate


async def test_create_rejects_a_retired_role_as_author(project, invoke):
    await invoke(["role", "activate", "qa"])
    await invoke(["role", "qa", "status", "Archived"])

    result = await invoke(["create", "feature", "F", "--author", "qa"])
    assert result.exit_code == 1
    assert "is retired; reactivate it with" in result.output
    assert "Traceback" not in result.output


async def test_create_rejects_a_retired_role_as_assignee(project, invoke):
    await invoke(["role", "activate", "qa"])
    await invoke(["role", "qa", "status", "Archived"])

    result = await invoke(["create", "feature", "F", "--author", "manager", "--assignee", "qa"])
    assert result.exit_code == 1
    assert "is retired; reactivate it with" in result.output


async def test_update_rejects_a_retired_role_as_assignee(project, invoke):
    created = await invoke(["create", "feature", "F", "--author", "manager", "--json"])
    feature_id = json.loads(created.output)["id"]
    await invoke(["role", "activate", "qa"])
    await invoke(["role", "qa", "status", "Archived"])

    result = await invoke(["feature", feature_id, "update", "--assignee", "qa"])
    assert result.exit_code == 1
    assert "is retired; reactivate it with" in result.output


async def test_comment_rejects_a_retired_role_as_author(project, invoke):
    created = await invoke(["create", "feature", "F", "--author", "manager", "--json"])
    feature_id = json.loads(created.output)["id"]
    await invoke(["role", "activate", "qa"])
    await invoke(["role", "qa", "status", "Archived"])

    result = await invoke(["feature", feature_id, "comment", "-m", "hi", "--as", "qa"])
    assert result.exit_code == 1
    assert "is retired; reactivate it with" in result.output


async def test_a_retired_roles_already_authored_items_still_read_correctly(project, invoke):
    """A retired role stops being *live*, but its history stays intact: an item it authored
    while live must still show/list/json fine, and the author's display name still renders,
    after retirement."""
    await invoke(["role", "activate", "qa"])
    created = await invoke(["create", "bug", "found one", "--author", "qa", "--json"])
    assert created.exit_code == 0, created.output
    bug_id = json.loads(created.output)["id"]

    await invoke(["role", "qa", "status", "Archived"])

    shown = await invoke(["bug", bug_id, "show", "--json"])
    assert shown.exit_code == 0, shown.output
    data = json.loads(shown.output)
    assert data["author"] == "qa"

    check = await invoke(["check"])
    assert check.exit_code == 0, check.output
    assert "not a registered" not in check.output.lower()


async def test_mine_and_inbox_still_reach_a_retired_roles_assigned_and_mentioned_items(
    project, invoke
):
    """`--assignee`/`sq mine`/`sq inbox` are reads/filters, not authorship — a retired role's
    still-open assignment and past @mention must stay reachable for review — only the entry
    points that *write* a participant are gated."""
    await invoke(["role", "activate", "qa"])
    created = await invoke(
        ["create", "bug", "needs qa review", "--author", "manager", "--assignee", "qa", "--json"]
    )
    bug_id = json.loads(created.output)["id"]
    await invoke(["bug", bug_id, "comment", "-m", "please look @qa", "--as", "manager"])
    await invoke(["role", "qa", "status", "Archived"])

    mine = await invoke(["mine", "qa"])
    assert mine.exit_code == 0, mine.output
    assert bug_id in mine.output

    listed = await invoke(["list", "--assignee", "qa", "--json"])
    assert listed.exit_code == 0, listed.output
    rows = json.loads(listed.output)
    assert any(r["id"] == bug_id for r in rows)

    inbox = await invoke(["inbox", "qa"])
    assert inbox.exit_code == 0, inbox.output
    assert bug_id in inbox.output


# --------------------------------------------------------------------------- status --unlink


async def test_role_status_unlink_help_text_is_present(project, invoke):
    await invoke(["role", "activate", "qa"])
    result = await invoke(["role", "qa", "status", "--help"])
    assert result.exit_code == 0, result.output
    assert "--unlink" in result.output


async def test_skill_status_unlink_help_text_is_present(project, invoke):
    await invoke(["skill", "add", "my-skill"])
    result = await invoke(["skill", "my-skill", "status", "--help"])
    assert result.exit_code == 0, result.output
    assert "--unlink" in result.output


async def test_operator_status_unlink_help_text_is_present(project, invoke):
    await invoke(["operator", "add", "First User"])
    result = await invoke(["operator", "op-first", "status", "--help"])
    assert result.exit_code == 0, result.output
    assert "--unlink" in result.output


def _dewrapped(output: str) -> str:
    """Rich's help panel wraps prose mid-sentence and pads it with box-drawing border
    characters on every line — strip those before joining, or a phrase split across two wrapped
    lines reads as broken by a stray "│ │" that was never part of the text."""
    for ch in "╭╮╰╯│─":
        output = output.replace(ch, " ")
    return " ".join(output.split())


async def test_status_unlink_help_text_uses_adopter_vocabulary_with_no_engine_jargon(
    project, invoke
):
    """The help text presupposed a concept `--help` never defines ("the config-integrity
    clauses' severable edges"). Restated in the words `docs/roles.md` already uses — what the
    flag does, in terms an adopter has actually met — with no clause/kind identifier."""
    await invoke(["role", "activate", "qa"])
    result = await invoke(["role", "qa", "status", "--help"])
    assert result.exit_code == 0, result.output
    normalized = _dewrapped(result.output)
    assert "remove the scoping the refusal named" in normalized
    assert "a custom skill's link to a role" in normalized
    for banned in (
        "config-integrity",
        "clause",
        "no_live_role",
        "preloaded_skill",
        "scoped_edge",
        "type_implied",
        "always_on_floor",
        "C1",
        "C2",
        "C3",
    ):
        assert banned not in normalized


async def test_status_force_help_text_is_present_and_scoped_to_the_lifecycle_edge(project, invoke):
    """`--force` carried no help text at all, in the same options block as `--unlink` —
    the more dangerous of the two flags, and the one an adopter reaches for first."""
    await invoke(["role", "activate", "qa"])
    result = await invoke(["role", "qa", "status", "--help"])
    assert result.exit_code == 0, result.output
    normalized = _dewrapped(result.output)
    assert "lifecycle" in normalized
    assert "Never overrides" in normalized
    for banned in ("config-integrity", "clause", "C1", "C2", "C3"):
        assert banned not in normalized


async def test_unlink_is_a_reported_no_op_when_the_retiring_skill_has_nothing_severable(
    project, invoke
):
    await invoke(["skill", "add", "unscoped-skill"])

    result = await invoke(["skill", "unscoped-skill", "status", "Archived", "--unlink"])

    assert result.exit_code == 0, result.output
    assert "no references severed" in result.output


async def test_unlink_on_a_non_retiring_transition_is_refused_as_meaningless(project, invoke):
    await invoke(["role", "activate", "qa"])
    await invoke(["role", "qa", "status", "Archived"])

    result = await invoke(["role", "qa", "status", "Active", "--unlink"])

    assert result.exit_code == 1
    assert "meaningless" in result.output
    assert "Traceback" not in result.output


async def test_unlink_never_offered_on_the_work_item_status_verb(project, invoke):
    created = await invoke(["create", "feature", "F", "--author", "manager", "--json"])
    feature_id = json.loads(created.output)["id"]

    result = await invoke(["feature", feature_id, "status", "--help"])

    assert result.exit_code == 0, result.output
    assert "--unlink" not in result.output


# --------------------------------------------------------------------------- composed message


async def test_c3_tier3_refusal_states_the_permanent_floor_once_on_the_real_terminal(
    project, invoke
):
    """The exact regression a live drive of ``sq skill squads status Archived`` caught: the
    composed refusal repeated "a permanent floor of the roster contract" and followed "no
    remedy exists" with a second "remedy: none" clause. Normalises Rich's line-wrapping
    (a long phrase can wrap mid-word at terminal width) before counting occurrences, since a
    wrapped phrase is still one occurrence to a reader, never two."""
    from squads._services import _service as service

    await service.Service(project).seed_bundled_skills()  # this fixture skips seeding at init

    result = await invoke(["skill", "squads", "status", "Archived"])

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    normalized = " ".join(result.output.split())
    assert normalized.count("permanent floor of the roster contract") == 1
    assert normalized.count("remedy") == 1  # the one mention, inside "no remedy exists"
    assert "remedy:" not in normalized  # no dangling "remedy: <text>" clause was appended
