"""The scaffold comment is the only place, alongside the adopter docs, where the playbook
override's role-slug rule is stated -- so it has to state the rule that is actually enforced.

It said every slug "must be in the role catalog". That has not been true since the slug authority
became the bundled catalog *union* the project's own `.overrides/roles/*.toml`: the scaffold told an
adopter the opposite of the capability built for them, and would have sent them away from
`sq override scaffold --new <slug>` -- the supported path, and the reason this override kind exists.

Asserted as claim-by-claim substrings against the text the command actually writes, not as a golden
blob: the point is that each *statement* is true, and a whole-file pin would go green on a reworded
paragraph that dropped one of them.

The ordering constraint rides along here on purpose. Being *defined* is not enough for a project
role -- it must be *activated*, or the guide loads clean and is dropped from the generated skill.
That is the same fact `sq check` now warns about, and the two must agree, so the scaffold names both
the activation step and the warning.
"""

import pytest

from squads._overrides._service import scaffold_playbook

pytestmark = pytest.mark.anyio


@pytest.fixture
def scaffold_text(project) -> str:
    return scaffold_playbook(project.squad_dir).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "claim",
    [
        # The three legal slug sources, each named.
        "a bundled catalog role",
        '"*dev" sentinel',
        ".overrides/roles/<slug>.toml",
        # The ordering constraint the check rule enforces, and where an adopter will meet it.
        "sq role activate <slug>",
        "`sq check` warns",
    ],
    ids=[
        "bundled_catalog_is_one_source",
        "dev_sentinel_is_one_source",
        "a_project_role_file_is_one_source",
        "activation_is_required",
        "check_reports_a_dropped_guide",
    ],
)
async def test_the_scaffold_states_each_part_of_the_slug_rule(scaffold_text, claim):
    assert claim in scaffold_text


async def test_the_scaffold_no_longer_claims_the_catalog_is_the_only_authority(scaffold_text):
    """The negative half, and the one that actually regresses: adding the new sentence while leaving
    the old absolute one in place would satisfy every assertion above and still tell the adopter
    their project role is invalid."""
    assert "must be in\n#     the role catalog" not in scaffold_text
    assert "must be in the role catalog" not in scaffold_text


async def test_the_rest_of_the_scaffolds_merge_rules_are_untouched(scaffold_text):
    """Guards the edit's blast radius: the scalar-vs-list split, the append idiom and the
    duplicate-slug refusal are all still stated, so this correction did not quietly drop one of
    them."""
    for claim in (
        "merge field-by-field",
        '"$(*self)"',
        "must not appear twice",
        "no [selected]",
    ):
        assert claim in scaffold_text
