"""SquadsConfig.active_backends: dedup semantics and legacy single-key back-compat.

Pure model tests — no filesystem, no service. The multi-backend runtime behaviour (sync
writing both files, none-sentinel CLI wiring) lives in
tests/integration/test_multi_active_backends.py.
"""

from squads._models._config import SquadsConfig


def test_duplicate_backend_names_collapse_to_one() -> None:
    cfg = SquadsConfig(active_backends=["claude_code", "claude_code", "agents_md"])
    assert cfg.active_backends == ["claude_code", "agents_md"]


def test_dedup_preserves_first_occurrence_order_not_insertion_order() -> None:
    cfg = SquadsConfig(active_backends=["agents_md", "claude_code", "agents_md"])
    assert cfg.active_backends == ["agents_md", "claude_code"]


def test_legacy_singular_backend_key_loads_as_a_one_element_list() -> None:
    """A hand-written config with the pre-multi-backend ``default_backend`` key (schema 0.3)
    loads as ``active_backends``, translated on read."""
    raw: dict[str, object] = {
        "schema_version": "0.3",
        "squad_dir": "squads",
        "default_backend": "agents_md",  # a non-default name so the fallback can't fake it
        "default_role": "manager",
        "squads_version": "0.3.0",
    }
    assert "active_backends" not in raw  # precondition: raw dict predates the list-shaped key
    cfg = SquadsConfig.from_toml_dict(raw)  # type: ignore[arg-type]
    assert cfg.active_backends == ["agents_md"]


def test_legacy_config_with_neither_key_defaults_to_claude_code_not_sq_only() -> None:
    raw: dict[str, object] = {
        "schema_version": "0.3",
        "squad_dir": "squads",
        "default_role": "manager",
        "squads_version": "0.3.0",
    }
    cfg = SquadsConfig.from_toml_dict(raw)  # type: ignore[arg-type]
    assert cfg.active_backends == ["claude_code"]
