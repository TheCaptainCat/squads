"""``_actor.seed_session``/``current_session``: an explicit call sets the (session, parent)
pair; it falls back to reading the pair from the environment when not given explicitly;
an absent env var and an empty-string env var both resolve to "no session"; ``set_actor``
(who's acting) never changes the session — the two are orthogonal; and the session defaults
to ``None`` with no seeding at all.
"""

from squads import _actor as actor

# The session pair is reset before/after every test by the root conftest's autouse
# `_reset_session_seed` — no local leak-guard needed here.


def test_explicit_seed_session_sets_the_pair() -> None:
    actor.seed_session("sess-abc", "parent-xyz")
    assert actor.current_session() == ("sess-abc", "parent-xyz")


def test_from_env_reads_both_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("SQUADS_SESSION_ID", "env-sid")
    monkeypatch.setenv("SQUADS_PARENT_SESSION_ID", "env-psid")
    actor.seed_session(from_env=True)
    assert actor.current_session() == ("env-sid", "env-psid")


def test_from_env_with_both_vars_absent_resolves_to_no_session(monkeypatch) -> None:
    monkeypatch.delenv("SQUADS_SESSION_ID", raising=False)
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)
    actor.seed_session(from_env=True)
    assert actor.current_session() == (None, None)


def test_from_env_with_both_vars_set_to_empty_string_also_resolves_to_no_session(
    monkeypatch,
) -> None:
    monkeypatch.setenv("SQUADS_SESSION_ID", "")
    monkeypatch.setenv("SQUADS_PARENT_SESSION_ID", "")
    actor.seed_session(from_env=True)
    assert actor.current_session() == (None, None)


def test_set_actor_never_changes_the_session_the_two_are_orthogonal() -> None:
    actor.seed_session("locked-sid", "locked-psid")
    actor.set_actor("python-dev")
    assert actor.current_actor() == "python-dev"
    assert actor.current_session() == ("locked-sid", "locked-psid")
    actor.set_actor(None)


def test_session_defaults_to_none_with_no_seeding_at_all() -> None:
    assert actor.current_session() == (None, None)
