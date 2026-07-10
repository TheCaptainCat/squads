"""``sq create <type> ... --ref``: the create-time ref resolves a bare number or a full
``ID:kind`` token exactly like ``ref add`` does post-creation, rejects an unknown ref kind,
and a bare ID with no kind defaults to the generic ``related`` kind.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_ref_accepts_a_bare_number_and_errors_cleanly_on_an_unknown_one(
    project, invoke
) -> None:
    await invoke(["create", "feature", "F", "--author", "manager"])  # FEAT-2

    ok = await invoke(["create", "task", "T", "--author", "manager", "--ref", "2"])
    assert ok.exit_code == 0, ok.output

    bad = await invoke(["create", "task", "Bad", "--author", "manager", "--ref", "999"])
    assert bad.exit_code == 1
    assert "999" in bad.output


async def test_ref_with_an_explicit_kind_is_validated_and_a_bare_id_defaults_to_related(
    project, invoke
) -> None:
    await invoke(["create", "feature", "F", "--author", "manager"])  # FEAT-2

    bad_kind = await invoke(
        ["create", "task", "T-bad", "--author", "manager", "--ref", "FEAT-2:banana"]
    )
    assert bad_kind.exit_code == 1
    assert "banana" in bad_kind.output

    good_kind = await invoke(
        ["create", "task", "T-ok", "--author", "manager", "--ref", "FEAT-2:implements"]
    )
    assert good_kind.exit_code == 0, good_kind.output

    bare = await invoke(["create", "task", "T-bare", "--author", "manager", "--ref", "FEAT-2"])
    assert bare.exit_code == 0, bare.output
    shown = await invoke(["show", "4", "--json"])
    import json

    data = json.loads(shown.output)
    assert "FEAT-2" in data["refs"]  # bare id, no ":kind" suffix -> defaulted to related
