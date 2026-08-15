"""``SquadsConfig`` tolerates unknown keys in an existing ``.squads.toml``: a field name a
later squads version stops writing (e.g. a retired one still present in a file on disk)
loads cleanly, with no migration and no schema bump, because the model's ``extra="ignore"``
silently drops what it doesn't recognize during validation.
"""

from squads._models._config import SquadsConfig


def test_a_stale_unrecognized_key_loads_cleanly_without_error() -> None:
    raw = {
        "schema_version": "0.11",
        "squad_dir": "squads",
        "active_backends": ["claude_code"],
        "default_role": "manager",  # retired field name; still present in an old file on disk
        "squads_version": "0.12.3",
    }
    cfg = SquadsConfig.from_toml_dict(raw)
    assert cfg.squad_dir == "squads"
    assert cfg.active_backends == ["claude_code"]
    assert not hasattr(cfg, "default_role")


def test_a_freshly_written_config_never_declares_the_retired_role_default() -> None:
    cfg = SquadsConfig(squad_dir="squads", active_backends=["claude_code"], squads_version="0.12.3")
    assert "default_role" not in cfg.to_toml()
