"""SquadsConfig's [init.names] table: pure model round-trip through TOML.

The service/CLI behaviour that actually *applies* these names at init time lives in
tests/service/test_agent_naming_precedence.py and tests/cli/test_init_naming_flags.py.
"""

import tomllib

from squads._models._config import SquadsConfig


def _config(**names: str) -> SquadsConfig:
    return SquadsConfig(
        squad_dir="squads",
        active_backends=["claude_code"],
        default_role="manager",
        squads_version="0.1.0",
        init_names=names,
    )


def test_to_toml_writes_the_init_names_section() -> None:
    toml = _config(architect="Ada Lovelace", manager="Grace Hopper").to_toml()
    assert "[init.names]" in toml
    assert 'architect = "Ada Lovelace"' in toml
    assert 'manager = "Grace Hopper"' in toml


def test_to_toml_omits_the_section_when_no_names_are_set() -> None:
    assert "[init.names]" not in _config().to_toml()


def test_from_toml_dict_hoists_init_names() -> None:
    data = {
        "schema_version": "0.3",
        "squad_dir": "squads",
        "active_backends": ["claude_code"],
        "default_role": "manager",
        "squads_version": "0.1.0",
        "init": {"names": {"architect": "Ada Lovelace"}},
    }
    assert SquadsConfig.from_toml_dict(data).init_names == {"architect": "Ada Lovelace"}


def test_from_toml_dict_with_no_init_section_gives_an_empty_dict() -> None:
    data = {
        "schema_version": "0.3",
        "squad_dir": "squads",
        "active_backends": ["claude_code"],
        "default_role": "manager",
        "squads_version": "0.1.0",
    }
    assert SquadsConfig.from_toml_dict(data).init_names == {}


def test_round_trips_through_real_toml_parsing() -> None:
    original = _config(qa="Mara Tester", manager="Grace Hopper")
    reloaded = SquadsConfig.from_toml_dict(tomllib.loads(original.to_toml()))
    assert reloaded.init_names == original.init_names
